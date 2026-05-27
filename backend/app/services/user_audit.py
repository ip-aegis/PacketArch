# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Helper for recording admin user-management actions to the audit log."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_audit import UserAuditLog


def record_user_audit(
    db: AsyncSession,
    *,
    actor: User | str,
    action: str,
    target: User | str | None = None,
    detail: str | None = None,
) -> None:
    """Stage a user-audit row on the session — the caller commits it together
    with the action, so the audit entry is atomic with the change it records.

    ``actor``/``target`` accept a User (id + username captured) or a bare string
    (e.g. "cli" / a username), so it works from routes and the reset CLI alike.
    """
    actor_id = actor.id if isinstance(actor, User) else None
    actor_name = actor.username if isinstance(actor, User) else str(actor)

    if isinstance(target, User):
        target_id, target_name = target.id, target.username
    else:
        target_id, target_name = None, target

    db.add(
        UserAuditLog(
            actor_user_id=actor_id,
            actor_username=actor_name[:255],
            target_user_id=target_id,
            target_username=(target_name[:255] if target_name else None),
            action=action[:32],
            detail=(detail[:512] if detail else None),
        )
    )
