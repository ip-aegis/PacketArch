"""Device profile model for storing OT device templates."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DeviceProfile(Base):
    """Device profile model for storing reusable device templates."""

    __tablename__ = "device_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    device_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Supported protocols: ["modbus_tcp", "ethernet_ip", "profinet"]
    supported_protocols: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Timing model: polling rates, jitter, etc.
    timing_model: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Payload templates: register definitions, data types
    payload_templates: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Behavioral model: startup/shutdown sequences, phases
    behavior_model: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Vendor fingerprint: MAC OUI, response times, etc.
    vendor_fingerprint: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Vertical hints: which industries this device is used in
    vertical_hints: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Whether this is a built-in profile (not user-editable)
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DeviceProfile {self.name} ({self.device_type})>"
