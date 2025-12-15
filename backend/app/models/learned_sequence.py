"""Learned sequence model for storing operation sequences from traffic."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB, UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SequenceType(str, Enum):
    """Types of operation sequences."""

    STARTUP = "startup"  # Connection establishment, initialization
    SHUTDOWN = "shutdown"  # Graceful disconnection
    POLL_CYCLE = "poll_cycle"  # Regular polling pattern
    WRITE_SEQUENCE = "write_sequence"  # Write operation pattern
    ERROR_RECOVERY = "error_recovery"  # Error handling and recovery
    STATE_TRANSITION = "state_transition"  # State machine transitions
    HEARTBEAT = "heartbeat"  # Keep-alive patterns
    ALARM = "alarm"  # Alarm/event handling


class LearnedSequence(Base):
    """Operation sequences learned from PCAP analysis.

    Stores sequence patterns including:
    - Startup/shutdown sequences
    - Poll cycle patterns
    - State machine transitions
    - Error recovery patterns
    """

    __tablename__ = "learned_sequences"

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

    # Sequence identification
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    sequence_type: Mapped[SequenceType] = mapped_column(
        ENUM(
            'startup', 'shutdown', 'poll_cycle', 'write_sequence',
            'error_recovery', 'state_transition', 'heartbeat', 'alarm',
            name='sequencetype', create_type=False
        ),
        nullable=False,
        index=True,
    )
    protocol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Protocol: modbus_tcp, s7comm, ethernet_ip, etc.",
    )

    # Source/target devices
    initiator_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IP that initiates the sequence",
    )
    responder_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IP that responds in the sequence",
    )

    # Sequence definition
    steps: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Sequence steps: [{index, packet_template, direction, timing_to_next}]",
    )

    # State machine (if inferred)
    state_machine: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Inferred state machine: {states: [], transitions: [], initial, terminal}",
    )

    # Timing information
    average_duration_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Average total sequence duration in milliseconds",
    )
    timing_variance: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Variance in sequence timing",
    )
    inter_step_timings: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Timing distribution between each step",
    )

    # Repetition pattern (for poll cycles)
    repetition_interval_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Interval between sequence repetitions",
    )
    repetition_jitter_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Jitter in repetition interval",
    )

    # Statistics
    occurrence_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of times this sequence was observed",
    )
    step_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of steps in the sequence",
    )

    # Variations observed
    variations: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Variations of this sequence observed",
    )

    # Quality metrics
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Confidence score 0-1 based on occurrence count and consistency",
    )

    # Metadata
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this sequence should be used in generation",
    )

    # Tags for categorization
    tags: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tags for categorization: {industry, device_type, etc.}",
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
        back_populates="learned_sequences",
    )

    def __repr__(self) -> str:
        return f"<LearnedSequence {self.name} ({self.sequence_type.value}/{self.protocol})>"


# Forward reference for relationship
from app.models.pcap_capture import PcapCapture  # noqa: E402, F401
