# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cyber Vision Center model.

One row per Cisco Cyber Vision Center this PacketArch server talks to. Each
center carries its own URL, SSL setting and BOTH API tokens: the classic
``/api/3.0`` token and the separate new-UI ``/cvapi/v1`` token (CV keeps two
token stores). Tokens are Fernet-encrypted (``core/encryption.py``).

Exactly one center is the default. Anything that doesn't name a center (the
setup wizard, a route called without ``center_id``, legacy objects) uses it.
Objects that live on a center record which one: ``local_labs.cv_center_id``
and ``scenario.definition['cyber_vision']['center_id']``. Those references are
what teardown and reconcile follow, never "whichever center is default now".

Replaces the four global ``cyber_vision_*`` system_settings rows, which are
migrated into the first (default) center on boot — see
``services/cv_centers.migrate_legacy_settings``.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CyberVisionCenter(Base):
    """A Cisco Cyber Vision Center PacketArch can provision into."""

    __tablename__ = "cyber_vision_centers"
    __table_args__ = (
        # At most one default center.
        Index(
            "uq_cyber_vision_centers_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default"),
            sqlite_where=text("is_default"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    # Base URL, no trailing slash (e.g. https://10.10.20.115).
    url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    # Encrypted classic /api/3.0 token.
    api_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Encrypted new-UI /cvapi/v1 token (optional; a separate CV token store).
    new_ui_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    verify_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CyberVisionCenter {self.name} {self.url}{' (default)' if self.is_default else ''}>"
