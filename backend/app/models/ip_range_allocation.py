# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IP Range Allocation model for tracking scenario IP ranges."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.scenario import Scenario


class IPRangeAllocation(Base):
    """Tracks /16 IP range allocations for scenarios.

    Each scenario gets a unique 10.{n}.0.0/16 range where n is 1-254.
    This prevents IP address overlaps between scenarios.
    """

    __tablename__ = "ip_range_allocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        unique=True,  # One range per scenario
        nullable=False,
        index=True,
    )
    # The index in 10.{n}.0.0/16 (1-254)
    range_index: Mapped[int] = mapped_column(
        Integer,
        unique=True,  # Prevent overlaps: only one scenario can have each index
        nullable=False,
        index=True,
    )
    # Store CIDR notation for readability: "10.1.0.0/16"
    cidr_range: Mapped[str] = mapped_column(
        String(18),
        nullable=False,
    )
    # Track next available host offset for sequential IP assignment
    # Starts at 10 (first device gets 10.{n}.0.10)
    next_host_offset: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship to scenario (back_populates set in Scenario model)
    scenario: Mapped["Scenario"] = relationship(
        "Scenario",
        back_populates="ip_range_allocation",
    )

    def __repr__(self) -> str:
        return f"<IPRangeAllocation {self.cidr_range} for scenario {self.scenario_id}>"
