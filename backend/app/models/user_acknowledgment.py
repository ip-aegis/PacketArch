# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Records of a user's acceptance of the EULA / license acknowledgment.

A new row is written each time a user accepts a versioned document. If the
document version is bumped (see app.core.version.ACK_VERSION), users are
re-prompted on next login because no row exists for (user, document,
current_version).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserAcknowledgment(Base):
    """User's acceptance of a versioned EULA / license document."""

    __tablename__ = "user_acknowledgments"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "document", "version",
            name="uq_user_acknowledgments_user_doc_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # fits IPv6
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<UserAcknowledgment user={self.user_id} "
            f"{self.document} v{self.version}>"
        )
