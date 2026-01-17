"""Vendor fingerprint model for storing detailed device emulation profiles."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VendorFingerprint(Base):
    """Vendor fingerprint model for hyper-realistic device emulation.

    This table stores comprehensive device fingerprints that enable
    accurate emulation of vendor-specific network behavior, protocol
    responses, and timing patterns to fool vulnerability scanners.
    """

    __tablename__ = "vendor_fingerprints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Basic identification
    vendor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    vendor_family: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    firmware_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # MAC address OUI prefixes for this vendor
    oui_prefixes: Mapped[list | None] = mapped_column(
        ARRAY(String(17)),
        nullable=True,
    )

    # Protocol-specific identity responses (JSON structures)
    modbus_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Modbus FC 43 Read Device Identification response",
    )
    ethernet_ip_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="EtherNet/IP ListIdentity response data",
    )
    profinet_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="PROFINET DCP identity block data",
    )
    s7_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="S7comm SZL identity data (order_code, firmware_version)",
    )
    snmp_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="SNMP system identity (sys_descr, sys_object_id, sys_name)",
    )
    bacnet_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="BACnet I-Am identity (vendor_id, model_name, firmware_revision)",
    )

    # TCP/IP stack fingerprint characteristics
    tcp_stack: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="TCP stack fingerprint (TTL, window, MSS, etc.)",
    )

    # Response timing characteristics
    response_timing: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Response timing profile with distribution",
    )

    # Error handling behavior
    error_behavior: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Error response behavior configuration",
    )

    # Protocol-specific quirks and behaviors
    protocol_quirks: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Protocol-specific behavioral quirks",
    )

    # Whether this is a built-in fingerprint (not user-editable)
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<VendorFingerprint {self.vendor} {self.model or self.vendor_family or ''}>"
