"""Learned traffic pattern model for storing extracted timing and payload patterns."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PatternType(str, Enum):
    """Types of learned traffic patterns."""

    TIMING = "timing"  # Inter-arrival time patterns
    PAYLOAD = "payload"  # Payload value distributions
    SEQUENCE = "sequence"  # Request/response sequences
    FLOW = "flow"  # Complete flow patterns
    ERROR = "error"  # Error/exception patterns


class DistributionType(str, Enum):
    """Statistical distribution types for timing patterns."""

    GAUSSIAN = "gaussian"
    LOGNORMAL = "lognormal"
    EXPONENTIAL = "exponential"
    GAMMA = "gamma"
    UNIFORM = "uniform"
    MIXTURE = "mixture"  # Mixture of distributions


class LearnedPattern(Base):
    """Learned traffic pattern model for AI-enhanced generation.

    This table stores patterns extracted from PCAP analysis including:
    - Inter-arrival time distributions
    - Payload value distributions
    - Request/response sequences
    - Error injection patterns
    """

    __tablename__ = "learned_patterns"

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

    # Pattern identification
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    pattern_type: Mapped[PatternType] = mapped_column(
        SQLEnum(PatternType),
        nullable=False,
        index=True,
    )
    protocol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Protocol: modbus_tcp, ethernet_ip, profinet, etc.",
    )

    # Flow identification (for flow-specific patterns)
    source_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    destination_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    source_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    destination_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Timing pattern parameters (for TIMING type)
    distribution_type: Mapped[DistributionType | None] = mapped_column(
        SQLEnum(DistributionType),
        nullable=True,
    )
    timing_params: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Distribution parameters: mean, std, shape, scale, etc.",
    )

    # Sample statistics
    sample_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    min_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    max_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    mean_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    std_dev: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Distribution fit quality
    fit_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Goodness of fit score (KS test p-value)",
    )

    # Payload patterns (for PAYLOAD type)
    payload_patterns: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Payload value distributions by field",
    )

    # Sequence patterns (for SEQUENCE type)
    sequence_patterns: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Request/response sequence patterns",
    )

    # Error patterns (for ERROR type)
    error_patterns: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Error rate, types, and distribution",
    )

    # Complete pattern data (for complex patterns)
    pattern_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Complete pattern data structure",
    )

    # Metadata
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Confidence score 0-1 based on sample size and fit",
    )
    is_active: Mapped[bool] = mapped_column(
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
        back_populates="learned_patterns",
    )

    def __repr__(self) -> str:
        return f"<LearnedPattern {self.name} ({self.pattern_type.value}/{self.protocol})>"


# Forward reference for relationship
from app.models.pcap_capture import PcapCapture  # noqa: E402, F401
