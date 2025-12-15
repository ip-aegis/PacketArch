"""Learned device fingerprint model for storing device signatures from traffic."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeviceRole(str, Enum):
    """Role of device in OT network."""

    MASTER = "master"  # Initiates requests (HMI, SCADA, Engineering Station)
    SLAVE = "slave"  # Responds to requests (PLC, RTU, I/O)
    BOTH = "both"  # Can act as both (some PLCs)
    UNKNOWN = "unknown"


class LearnedDeviceFingerprint(Base):
    """Device fingerprints learned from PCAP traffic analysis.

    Stores device signatures including:
    - TCP stack characteristics
    - MAC OUI and vendor mapping
    - Response timing distributions
    - Protocol-specific identity info
    """

    __tablename__ = "learned_device_fingerprints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Source PCAP
    pcap_capture_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pcap_captures.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Network identity
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        index=True,
        comment="Device IP address observed in PCAP",
    )
    mac_address: Mapped[str | None] = mapped_column(
        String(17),
        nullable=True,
        comment="Device MAC address if available",
    )
    mac_oui: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        index=True,
        comment="First 3 octets of MAC (OUI)",
    )
    inferred_vendor: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Vendor inferred from OUI or protocol identity",
    )

    # TCP stack signature
    tcp_signature: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="TCP stack fingerprint: {ttl, window_size, mss, options, df_flag, etc.}",
    )

    # Response timing per protocol
    response_timings: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Response timing by protocol: {protocol: {min, max, mean, std, distribution}}",
    )

    # Protocol identity info
    protocol_identities: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Protocol-specific IDs: {modbus: {device_id}, s7: {szl_info}, enip: {identity}}",
    )

    # Behavioral patterns
    role: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        nullable=False,
        comment="Device role: master, slave, both, unknown",
    )

    # Communication partners
    communication_partners: Mapped[list | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of IPs this device communicates with",
    )

    # Active protocols
    active_protocols: Mapped[list | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Protocols observed for this device",
    )

    # Ports used
    ports_used: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Ports used: {tcp: [ports], udp: [ports]}",
    )

    # Packet statistics
    packets_sent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    packets_received: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    bytes_sent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    bytes_received: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # First/last seen timestamps in PCAP
    first_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Quality metrics
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Confidence score 0-1 based on data quality",
    )

    # Metadata
    name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Human-readable name for this fingerprint",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this fingerprint should be used",
    )

    # Timestamps
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

    # Relationships
    pcap_capture: Mapped["PcapCapture"] = relationship(
        "PcapCapture",
        back_populates="device_fingerprints",
    )

    def __repr__(self) -> str:
        vendor = self.inferred_vendor or "Unknown"
        return f"<LearnedDeviceFingerprint {self.ip_address} ({vendor})>"


# Forward reference for relationship
from app.models.pcap_capture import PcapCapture  # noqa: E402, F401
