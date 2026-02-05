"""Learning session model for grouping related PCAP uploads."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SessionStatus(str, Enum):
    """Status of a learning session."""

    ACTIVE = "active"  # Session is open for new uploads
    ANALYZING = "analyzing"  # Aggregated analysis in progress
    COMPLETED = "completed"  # Analysis complete, patterns aggregated
    ARCHIVED = "archived"  # Session archived


class LearningSession(Base):
    """Learning session model for grouping related PCAP uploads.

    A learning session groups multiple PCAP captures that are related
    (e.g., from the same network, different time periods, same test scenario).
    This enables:
    - Aggregate pattern confidence across multiple samples
    - Cohesive analysis of related traffic
    - Session-level statistics and metadata
    """

    __tablename__ = "learning_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Session identification
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Session status
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus),
        default=SessionStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Session metadata
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
    network_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the source network",
    )
    tags: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="User-assigned tags for categorization",
    )

    # Aggregated statistics (calculated during analysis)
    capture_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of PCAP captures in this session",
    )
    total_packets: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total packets across all captures",
    )
    total_flows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total unique flows identified",
    )
    total_duration_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Total capture duration across all captures",
    )

    # Protocol coverage
    protocols_detected: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of protocols detected across all captures",
    )
    protocol_stats: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Aggregated protocol statistics",
    )

    # Aggregated confidence scores
    aggregate_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Overall confidence score based on all captures",
    )
    pattern_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of unique patterns extracted",
    )
    fingerprint_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of device fingerprints extracted",
    )
    sequence_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of learned sequences extracted",
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
    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When aggregated analysis was completed",
    )

    # Relationships
    pcap_captures: Mapped[list["PcapCapture"]] = relationship(
        "PcapCapture",
        back_populates="learning_session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<LearningSession {self.name} ({self.status.value}, {self.capture_count} captures)>"

    def update_statistics(self) -> None:
        """Update aggregated statistics from child captures.

        Call this after adding/removing captures or when captures complete processing.
        """
        self.capture_count = len(self.pcap_captures)
        self.total_packets = sum(
            c.packet_count or 0 for c in self.pcap_captures
        )
        self.total_flows = sum(
            c.flow_count or 0 for c in self.pcap_captures
        )
        self.total_duration_ms = sum(
            c.capture_duration_ms or 0 for c in self.pcap_captures
        )

        # Aggregate protocols
        protocols = set()
        protocol_counts = {}
        for capture in self.pcap_captures:
            if capture.protocol_stats:
                for protocol, count in capture.protocol_stats.items():
                    protocols.add(protocol)
                    protocol_counts[protocol] = protocol_counts.get(protocol, 0) + (
                        count if isinstance(count, int) else count.get("count", 0)
                    )

        self.protocols_detected = list(protocols)
        self.protocol_stats = protocol_counts if protocol_counts else None


# Forward reference for relationship
from app.models.pcap_capture import PcapCapture  # noqa: E402, F401
