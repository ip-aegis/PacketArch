# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Site-config overview endpoint.

Single structured view of every major subsystem so an admin can see what's
configured and what still needs attention without tab-hopping through
Settings. The frontend renders cards per subsystem and deep-links back to
the existing tabs for the actual editing flows.

Kept intentionally aggregation-only — no writes, no state changes, no
duplication of the per-subsystem CRUD endpoints.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import AdminUser, DBSession
from app.core.features import get_features
from app.core.version import (
    ACK_DOCUMENT,
    ACK_VERSION,
    LICENSE_ID,
    OWNER_EMAIL,
    OWNER_NAME,
)
from app.core.config import settings as app_settings
from app.models.settings import SystemSetting
from app.models.traffic_agent import TrafficAgent
from app.models.user import User
from app.models.user_acknowledgment import UserAcknowledgment
from app.services import ldap_service

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─── response schemas ──────────────────────────────────────────────────


class ProductSummary(BaseModel):
    name: str
    version: str
    owner_name: str
    owner_email: str
    license_id: str
    acknowledgment_document: str
    acknowledgment_version: str
    acknowledgments_on_current_version: int


class FeaturesSummary(BaseModel):
    ai_enabled: bool


class SubsystemStatus(BaseModel):
    """Shared shape for every subsystem card."""

    key: str                 # stable machine id — also the Settings tab key for deep-linking
    label: str
    status: str              # "ok" | "needs_attention" | "disabled" | "unknown"
    summary: str             # one-liner shown under the title
    detail: dict[str, str | int | bool | None] = {}


class SiteConfigResponse(BaseModel):
    generated_at: datetime
    product: ProductSummary
    features: FeaturesSummary
    subsystems: list[SubsystemStatus]


# ─── helpers ────────────────────────────────────────────────────────────


async def _get_setting(db, key: str) -> str | None:
    """Fetch a single SystemSetting value by key (unmasked; admin-only route)."""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


async def _subsystem_ai_provider(db) -> SubsystemStatus:
    features = get_features()
    key_present = bool(await _get_setting(db, "anthropic_api_key"))
    model = await _get_setting(db, "anthropic_model") or "claude-opus-4-8"

    if not features.ai_enabled:
        return SubsystemStatus(
            key="ai_provider", label="AI Provider",
            status="disabled",
            summary="AI features are disabled in this deployment (AI_ENABLED=false).",
            detail={"model": model, "api_key_set": key_present},
        )
    if not key_present:
        return SubsystemStatus(
            key="ai_provider", label="AI Provider",
            status="needs_attention",
            summary="Enabled, but no Anthropic API key has been set.",
            detail={"model": model, "api_key_set": False},
        )
    return SubsystemStatus(
        key="ai_provider", label="AI Provider",
        status="ok",
        summary=f"Configured · model {model}",
        detail={"model": model, "api_key_set": True},
    )


async def _subsystem_authentication(db) -> SubsystemStatus:
    config = await ldap_service.load_config(db)
    ldap_on = ldap_service.is_enabled(config)

    total_users = (await db.execute(
        select(func.count(User.id))
    )).scalar_one()
    admin_users = (await db.execute(
        select(func.count(User.id)).where(User.is_admin.is_(True))
    )).scalar_one()
    ldap_users = (await db.execute(
        select(func.count(User.id)).where(User.auth_source == "ldap")
    )).scalar_one()

    if ldap_on:
        summary = f"LDAP/AD enabled · {total_users} users ({ldap_users} via LDAP, {admin_users} admins)"
        status_ = "ok"
    else:
        summary = f"Local-only · {total_users} users, {admin_users} admins"
        status_ = "ok" if admin_users >= 1 else "needs_attention"
    return SubsystemStatus(
        key="ldap", label="Authentication",
        status=status_, summary=summary,
        detail={
            "ldap_enabled": ldap_on,
            "total_users": int(total_users),
            "admin_users": int(admin_users),
            "ldap_users": int(ldap_users),
        },
    )


async def _subsystem_cyber_vision(db) -> SubsystemStatus:
    url = await _get_setting(db, "cyber_vision_url")
    token = await _get_setting(db, "cyber_vision_api_token")
    if url and token:
        return SubsystemStatus(
            key="cyber_vision", label="Cisco Cyber Vision",
            status="ok",
            summary=f"Connected to {url}",
            detail={"url": url, "api_token_set": True},
        )
    return SubsystemStatus(
        key="cyber_vision", label="Cisco Cyber Vision",
        status="needs_attention",
        summary="Not configured — CV comparison / enrichment features unavailable.",
        detail={"url": url or "", "api_token_set": bool(token)},
    )


async def _subsystem_agents(db) -> SubsystemStatus:
    total = (await db.execute(
        select(func.count(TrafficAgent.id))
    )).scalar_one()
    online = (await db.execute(
        select(func.count(TrafficAgent.id)).where(TrafficAgent.status == "online")
    )).scalar_one()
    offline = int(total) - int(online)

    if total == 0:
        summary = "No traffic agents registered yet."
        status_ = "needs_attention"
    elif online == 0:
        summary = f"{total} registered · {offline} offline"
        status_ = "needs_attention"
    else:
        summary = f"{total} registered · {online} online, {offline} offline"
        status_ = "ok"
    return SubsystemStatus(
        key="agents", label="Traffic Agents",
        status=status_, summary=summary,
        detail={"total": int(total), "online": int(online), "offline": offline},
    )


async def _subsystem_licensing(db) -> SubsystemStatus:
    # Just reassurance that the license + EULA chain is in place.
    accepts = (await db.execute(
        select(func.count(UserAcknowledgment.id)).where(
            UserAcknowledgment.document == ACK_DOCUMENT,
            UserAcknowledgment.version == ACK_VERSION,
        )
    )).scalar_one()
    return SubsystemStatus(
        key="licensing", label="License & Ownership",
        status="ok",
        summary=f"Licensed under {LICENSE_ID} · {accepts} user acknowledgments on file",
        detail={
            "license_id": LICENSE_ID,
            "owner": f"{OWNER_NAME} <{OWNER_EMAIL}>",
            "ack_version": ACK_VERSION,
            "ack_count": int(accepts),
        },
    )


# ─── route ─────────────────────────────────────────────────────────────


@router.get("/site-config", response_model=SiteConfigResponse)
async def get_site_config(
    db: DBSession,
    _admin: AdminUser,
) -> SiteConfigResponse:
    """Aggregated configuration status across every major subsystem.

    Read-only. Each entry in `subsystems` carries a `key` that matches the
    Settings page tab key the frontend should switch to when the user
    clicks the card's Configure button.
    """
    accepts = (await db.execute(
        select(func.count(UserAcknowledgment.id)).where(
            UserAcknowledgment.document == ACK_DOCUMENT,
            UserAcknowledgment.version == ACK_VERSION,
        )
    )).scalar_one()

    product = ProductSummary(
        name=app_settings.app_name,
        version=app_settings.app_version,
        owner_name=OWNER_NAME,
        owner_email=OWNER_EMAIL,
        license_id=LICENSE_ID,
        acknowledgment_document=ACK_DOCUMENT,
        acknowledgment_version=ACK_VERSION,
        acknowledgments_on_current_version=int(accepts),
    )

    subsystems = [
        await _subsystem_licensing(db),
        await _subsystem_ai_provider(db),
        await _subsystem_authentication(db),
        await _subsystem_cyber_vision(db),
        await _subsystem_agents(db),
    ]

    return SiteConfigResponse(
        generated_at=datetime.utcnow(),
        product=product,
        features=FeaturesSummary(ai_enabled=get_features().ai_enabled),
        subsystems=subsystems,
    )
