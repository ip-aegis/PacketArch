# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""EULA / license acknowledgment endpoints.

The frontend checks GET /acknowledgments/status on app load; if the response
has accepted=false it mounts a blocking modal whose only action POSTs to
/acknowledgments. Users are re-prompted whenever ACK_VERSION bumps.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.version import ACK_DOCUMENT, ACK_VERSION
from app.models.user_acknowledgment import UserAcknowledgment
from app.schemas.acknowledgment import (
    AcknowledgmentAccept,
    AcknowledgmentRecord,
    AcknowledgmentStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/acknowledgments", tags=["Acknowledgments"])


def _client_ip(request: Request) -> str | None:
    """Best-effort client IP, honoring reverse-proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/status", response_model=AcknowledgmentStatus)
async def get_status(
    current_user: CurrentUser,
    db: DBSession,
) -> AcknowledgmentStatus:
    """Has the current user accepted the current acknowledgment version?"""
    result = await db.execute(
        select(UserAcknowledgment)
        .where(
            UserAcknowledgment.user_id == current_user.id,
            UserAcknowledgment.document == ACK_DOCUMENT,
        )
        .order_by(UserAcknowledgment.accepted_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    return AcknowledgmentStatus(
        document=ACK_DOCUMENT,
        current_version=ACK_VERSION,
        accepted=latest is not None and latest.version == ACK_VERSION,
        accepted_version=latest.version if latest else None,
        accepted_at=latest.accepted_at if latest else None,
    )


@router.post("", response_model=AcknowledgmentRecord)
async def accept(
    payload: AcknowledgmentAccept,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
) -> AcknowledgmentRecord:
    """Record the user's acceptance of the acknowledgment document.

    Idempotent: if the user has already accepted this (document, version),
    the existing row is returned. The version is taken from the client
    payload, not the server constant, so re-submitting an old version still
    leaves the user 'not accepted' at the current version and re-prompts.
    """
    existing = await db.execute(
        select(UserAcknowledgment).where(
            UserAcknowledgment.user_id == current_user.id,
            UserAcknowledgment.document == payload.document,
            UserAcknowledgment.version == payload.version,
        )
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        return AcknowledgmentRecord.model_validate(row)

    row = UserAcknowledgment(
        user_id=current_user.id,
        document=payload.document,
        version=payload.version,
        ip_address=_client_ip(request),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    logger.info(
        "User %s accepted %s v%s",
        current_user.username, payload.document, payload.version,
    )
    return AcknowledgmentRecord.model_validate(row)
