"""PCAP capture model for storing uploaded packet capture files and metadata."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProcessingStatus(str, Enum):
    """Status of PCAP file processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PcapCapture(Base):
    """PCAP capture model for uploaded packet capture files.

    This table stores metadata about uploaded PCAP files that are
    analyzed to learn traffic patterns for realistic generation.
    """

    __tablename__ = "pcap_captures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # File information
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Server-side path to stored PCAP file",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash for deduplication",
    )

    # Processing status
    status: Mapped[ProcessingStatus] = mapped_column(
        SQLEnum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Capture metadata (extracted from PCAP)
    capture_duration_ms: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="Total capture duration in milliseconds",
    )
    packet_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    flow_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of unique flows identified",
    )

    # Protocol breakdown (learned during analysis)
    protocol_stats: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Protocol distribution statistics",
    )

    # Device and network info extracted
    devices_detected: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Devices detected in capture (MAC, IP, vendor hints)",
    )

    # User-provided metadata
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    tags: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="User-assigned tags for categorization",
    )
    source_environment: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Source environment (lab, production, simulation)",
    )
    industry_vertical: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Industry vertical (manufacturing, water, energy)",
    )

    # Ownership
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Learning session grouping
    learning_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional learning session this capture belongs to",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    learned_patterns: Mapped[list["LearnedPattern"]] = relationship(
        "LearnedPattern",
        back_populates="pcap_capture",
        cascade="all, delete-orphan",
    )
    protocol_patterns: Mapped[list["LearnedProtocolPattern"]] = relationship(
        "LearnedProtocolPattern",
        back_populates="pcap_capture",
        cascade="all, delete-orphan",
    )
    # Learned templates (unified DeviceTemplate model)
    # No cascade - DeviceTemplate FK uses SET NULL. Cleanup handled explicitly.
    learned_templates: Mapped[list["DeviceTemplate"]] = relationship(
        "DeviceTemplate",
        foreign_keys="[DeviceTemplate.source_pcap_id]",
        passive_deletes=True,
    )
    learned_sequences: Mapped[list["LearnedSequence"]] = relationship(
        "LearnedSequence",
        back_populates="pcap_capture",
        cascade="all, delete-orphan",
    )
    learning_session: Mapped["LearningSession | None"] = relationship(
        "LearningSession",
        back_populates="pcap_captures",
    )

    def __repr__(self) -> str:
        return f"<PcapCapture {self.original_filename} ({self.status.value})>"


# Forward references for relationships
from app.models.learned_pattern import LearnedPattern  # noqa: E402, F401
from app.models.learned_protocol_pattern import LearnedProtocolPattern  # noqa: E402, F401
from app.models.device_template import DeviceTemplate  # noqa: E402, F401
from app.models.learned_sequence import LearnedSequence  # noqa: E402, F401
from app.models.learning_session import LearningSession  # noqa: E402, F401
