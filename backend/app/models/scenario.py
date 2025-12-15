"""Scenario model for storing OT network scenarios."""

import uuid
from datetime import datetime

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.ip_range_allocation import IPRangeAllocation

from app.core.database import Base


class Scenario(Base):
    """Scenario model for storing complete OT network scenario definitions."""

    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    vertical: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    total_duration_ms: Mapped[int] = mapped_column(
        BigInteger,
        default=60000,
        nullable=False,
    )
    # Full scenario definition including devices, flows, zones, phases, events
    definition: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # Addressing configuration
    addressing_config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
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

    # Relationship to IP range allocation
    ip_range_allocation: Mapped["IPRangeAllocation | None"] = relationship(
        "IPRangeAllocation",
        back_populates="scenario",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Scenario {self.name}>"
