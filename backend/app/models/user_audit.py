# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Audit log for administrative user-management actions."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserAuditLog(Base):
    """One row per admin user-management action (create/delete/role/status/
    password reset). Usernames are denormalized so entries stay readable after
    the actor or target user is deleted.
    """

    __tablename__ = "user_audit_log"
    __table_args__ = (Index("ix_user_audit_log_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Who performed the action. SET NULL on actor deletion; username kept for display.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_username: Mapped[str] = mapped_column(String(255), nullable=False)
    # Who it was done to (no FK — the target may be deleted by this very action).
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # create|delete|update|promote|demote|activate|deactivate|reset_password|change_password
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(512), nullable=True)

    def __repr__(self) -> str:
        return f"<UserAuditLog {self.action} {self.target_username} by {self.actor_username}>"
