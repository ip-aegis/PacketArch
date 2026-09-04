# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""First-run setup wizard endpoints.

These three endpoints are reachable without authentication while
`setup.completed` is false. Once setup completes, /setup/complete returns 410
and the frontend SetupGate redirects /setup → /. /setup/status stays open
permanently so the frontend can fail-open during loading.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import DBSession
from app.core.config import settings
from app.core.encryption import encrypt_value
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.core.version import ACK_DOCUMENT, ACK_VERSION
from app.models.settings import SystemSetting
from app.models.user import User
from app.models.user_acknowledgment import UserAcknowledgment
from app.schemas.setup import (
    SetupCompleteRequest,
    SetupCompleteResponse,
    SetupStatusResponse,
    TestAIKeyRequest,
    TestAIKeyResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/setup", tags=["Setup"])


async def _is_setup_complete(db) -> bool:
    """Read the setup.completed flag. Treats missing row as not complete."""
    result = await db.execute(
        select(SystemSetting.value).where(SystemSetting.key == "setup.completed")
    )
    return result.scalar_one_or_none() == "true"


async def _upsert_setting(
    db,
    key: str,
    value: str,
    *,
    is_secret: bool = False,
    category: str | None = None,
) -> None:
    """Insert or update a SystemSetting row. Encrypts secrets at rest."""
    if is_secret and value:
        value = encrypt_value(value)
    row = (
        await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    ).scalar_one_or_none()
    if row is None:
        db.add(
            SystemSetting(
                key=key,
                value=value,
                is_secret=is_secret,
                category=category,
            )
        )
    else:
        row.value = value
        if category is not None:
            row.category = category


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(db: DBSession) -> SetupStatusResponse:
    """Public probe — used by the frontend SetupGate on every app boot."""
    completed = await _is_setup_complete(db)
    live_traffic = settings.live_traffic_enabled
    return SetupStatusResponse(
        setup_complete=completed,
        build_variant="full" if live_traffic else "pcap-only",
        ai_supported=True,  # AI is a runtime toggle; the install always supports it
        live_traffic_supported=live_traffic,
    )


@router.post("/complete", response_model=SetupCompleteResponse)
async def complete_setup(
    payload: SetupCompleteRequest,
    db: DBSession,
    request: Request,
) -> SetupCompleteResponse:
    """One-shot wizard completion.

    Wraps user creation + settings upsert + acknowledgment + setup-flag flip
    in a single DB transaction. Returns access + refresh tokens for the new
    admin so the frontend can drop the operator straight into the dashboard.
    """
    if await _is_setup_complete(db):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Setup is already complete. Use /api/v1/auth/login.",
        )

    if not payload.accept_acknowledgment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GPL acknowledgment is required to complete setup.",
        )

    # Reject if the requested username is taken (defensive — the table should
    # be empty at this point, but a malicious /register attempt during the
    # window could collide).
    existing = (
        await db.execute(
            select(User).where(User.username == payload.admin.username)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.admin.username}' is already taken.",
        )

    # 1. Admin user
    admin = User(
        username=payload.admin.username,
        email=payload.admin.email,
        password_hash=get_password_hash(payload.admin.password),
        is_admin=True,
        is_active=True,
        auth_source="local",
    )
    db.add(admin)
    await db.flush()  # populate admin.id without committing yet

    # 2. Site identity
    await _upsert_setting(db, "site.name", payload.site.name, category="setup")
    await _upsert_setting(db, "site.fqdn", payload.site.fqdn, category="setup")
    await _upsert_setting(
        db, "site.timezone", payload.site.timezone, category="setup"
    )

    # 3. AI provider
    if payload.ai.enabled and payload.ai.anthropic_api_key:
        await _upsert_setting(
            db,
            "anthropic_api_key",
            payload.ai.anthropic_api_key,
            is_secret=True,
            category="ai",
        )

    # 4. Cyber Vision (optional)
    if payload.cyber_vision.enabled:
        if payload.cyber_vision.url:
            await _upsert_setting(
                db,
                "cyber_vision_url",
                payload.cyber_vision.url,
                category="cyber_vision",
            )
        if payload.cyber_vision.api_token:
            await _upsert_setting(
                db,
                "cyber_vision_api_token",
                payload.cyber_vision.api_token,
                is_secret=True,
                category="cyber_vision",
            )
        await _upsert_setting(
            db,
            "cyber_vision_verify_ssl",
            "true" if payload.cyber_vision.verify_ssl else "false",
            category="cyber_vision",
        )

    # 5. License acknowledgment
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else None)
    )
    db.add(
        UserAcknowledgment(
            user_id=admin.id,
            document=ACK_DOCUMENT,
            version=ACK_VERSION,
            ip_address=client_ip,
        )
    )

    # 6. Flip setup.completed last so a partial failure leaves the wizard
    # reachable for retry.
    await _upsert_setting(db, "setup.completed", "true", category="setup")

    admin.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(admin)

    logger.info(
        "Setup wizard completed: admin user '%s' created", admin.username
    )

    token_data = {"sub": str(admin.id)}
    return SetupCompleteResponse(
        setup_complete=True,
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/test-ai-key", response_model=TestAIKeyResponse)
async def test_ai_key(
    payload: TestAIKeyRequest, db: DBSession
) -> TestAIKeyResponse:
    """Validate an Anthropic key by making a minimal request.

    Only callable while setup is incomplete — once setup is done, the operator
    uses Settings → AI Provider for key management. Returns a structured error
    so air-gapped sites can distinguish "bad key" from "no egress."
    """
    if await _is_setup_complete(db):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Setup is already complete. Manage keys in Settings.",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": payload.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "ping"}],
                },
            )
    except httpx.RequestError as exc:
        return TestAIKeyResponse(
            valid=False,
            error=(
                f"Could not reach api.anthropic.com ({type(exc).__name__}). "
                "Air-gapped sites can skip this check — the key is saved un-validated."
            ),
        )

    if resp.status_code == 200:
        return TestAIKeyResponse(valid=True)
    if resp.status_code in (401, 403):
        return TestAIKeyResponse(
            valid=False, error="Anthropic rejected the key (invalid or expired)."
        )
    return TestAIKeyResponse(
        valid=False,
        error=f"Unexpected response from Anthropic: HTTP {resp.status_code}",
    )
