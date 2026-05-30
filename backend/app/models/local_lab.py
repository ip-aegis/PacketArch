# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Local sensor lab model.

A LocalLab is an app-managed (agent + Cyber Vision sensor + virtual SPAN) lab
running on the PacketArch host itself. The row is the DESIRED state; the
privileged host-agent (docker/packetarch-host-agent) reconciles host reality to
match it, which is what makes labs survive reboots. Mirrors the CML build-lab
workflow (see services/cml_service.py) but on-box instead of in a CML lab.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LocalLab(Base):
    """An app-managed local agent + CV-sensor lab on the PacketArch host."""

    __tablename__ = "local_labs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )
    # Short stable id that drives all per-lab resource names (veth, containers,
    # sensor networks/volume). Derived from id; kept distinct so resource names
    # stay short and stable even if name changes.
    slug: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )
    # The traffic agent this lab created (null until created / after delete).
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traffic_agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Parsed from the operator-pasted CV sensor compose.
    sensor_serial: Mapped[str | None] = mapped_column(String(128), nullable=True)
    registry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # The operator-pasted CV docker-compose YAML (verbatim).
    sensor_compose: Mapped[str] = mapped_column(Text, nullable=False)
    # Per-lab virtual SPAN interface names.
    gen_if: Mapped[str] = mapped_column(String(64), nullable=False)
    mon_if: Mapped[str] = mapped_column(String(64), nullable=False)
    # Lifecycle: pending | provisioning | running | degraded | stopped | error
    state: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )
    # Last status message surfaced from the host-agent status file.
    status_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<LocalLab {self.name} ({self.state})>"
