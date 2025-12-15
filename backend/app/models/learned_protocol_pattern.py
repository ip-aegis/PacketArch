"""Learned protocol pattern model for storing deep protocol-specific patterns."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LearnedProtocolPattern(Base):
    """Protocol-specific patterns learned from PCAP analysis.

    Stores deep protocol analysis results including:
    - Function code frequency distribution
    - Register/address access patterns
    - Payload structure templates
    - Request/response pairs
    """

    __tablename__ = "learned_protocol_patterns"

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

    # Protocol identification
    protocol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Protocol: modbus_tcp, s7comm, ethernet_ip, dnp3, etc.",
    )

    # Function code analysis
    function_codes: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Function code distribution: {fc: {count, frequency, typical_payloads}}",
    )

    # Register/address patterns
    address_patterns: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Register access patterns: {ranges, hot_spots, access_frequency}",
    )

    # Payload structure templates
    payload_structures: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Payload structures by function code: {fc: {field_positions, sizes, value_ranges}}",
    )

    # Request/response pairs
    request_response_pairs: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Common request/response patterns: [{request_template, response_template, timing}]",
    )

    # Protocol-specific metadata
    protocol_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Protocol-specific data: unit_ids for Modbus, pdu_sizes for S7, etc.",
    )

    # Unit ID distribution (for Modbus)
    unit_id_distribution: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Distribution of unit IDs seen: {unit_id: frequency}",
    )

    # Exception/error patterns
    exception_patterns: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Exception code distribution and typical causes",
    )

    # Device identity info extracted from protocol
    device_identities: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Device identities from protocol: {ip: {vendor, product, version}}",
    )

    # Statistics
    sample_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total number of packets analyzed",
    )
    request_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of request packets",
    )
    response_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of response packets",
    )

    # Quality metrics
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Confidence score 0-1 based on sample size and pattern consistency",
    )

    # Metadata
    name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this pattern should be used in generation",
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
        back_populates="protocol_patterns",
    )

    def __repr__(self) -> str:
        return f"<LearnedProtocolPattern {self.protocol} ({self.sample_count} samples)>"


# Forward reference for relationship
from app.models.pcap_capture import PcapCapture  # noqa: E402, F401
