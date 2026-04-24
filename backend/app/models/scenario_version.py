# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Scenario version model for version history snapshots."""

import uuid
from datetime import datetime

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.scenario import Scenario
    from app.models.user import User

from app.core.database import Base


class ScenarioVersion(Base):
    """A snapshot of a scenario at a point in time."""

    __tablename__ = "scenario_versions"
    __table_args__ = (
        # Ensures version_number is unique per scenario
        {"comment": "Scenario version history snapshots"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    # Full scenario snapshot
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    definition: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    addressing_config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    total_duration_ms: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    # Version metadata
    label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="manual",
    )
    # Summary stats cached for list view (avoids re-parsing definition)
    device_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    flow_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    scenario: Mapped["Scenario"] = relationship(
        "Scenario",
        back_populates="versions",
    )

    def __repr__(self) -> str:
        return f"<ScenarioVersion {self.scenario_id} v{self.version_number}>"
