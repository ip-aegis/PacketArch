# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Generation job model for persisting PCAP generation jobs."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.scenario import Scenario
    from app.models.user import User

from app.core.database import Base


class GenerationJobStatus(str, Enum):
    """Status of a generation job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationJob(Base):
    """Generation job model for tracking PCAP generation jobs."""

    __tablename__ = "generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=GenerationJobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    progress: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    total_duration_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    packets_generated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    output_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    # One entry per PCAP file produced by the run: {kind, filename, packets,
    # size_bytes}. Always includes the ``combined`` file (== output_filename);
    # attack-export runs also carry ``baseline`` and ``attack``. Nullable for
    # rows written before attack export existed.
    artifacts: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    scenario: Mapped["Scenario"] = relationship(
        "Scenario",
        backref="generation_jobs",
        lazy="selectin",
    )
    user: Mapped["User | None"] = relationship(
        "User",
        backref="generation_jobs",
        lazy="selectin",
    )

    @property
    def output_path(self) -> str | None:
        """Get full output path from filename."""
        if self.output_filename:
            from app.core.config import settings
            from pathlib import Path
            return str(Path(settings.pcap_output_dir) / self.output_filename)
        return None

    def artifact_path(self, kind: str = "combined") -> str | None:
        """Resolve the full path of a produced PCAP by kind.

        ``combined`` maps to the regular output file. ``baseline`` / ``attack``
        resolve from the ``artifacts`` list (attack-export runs only).
        """
        if kind == "combined" or not self.artifacts:
            return self.output_path
        from pathlib import Path

        from app.core.config import settings
        for art in self.artifacts:
            if art.get("kind") == kind and art.get("filename"):
                return str(Path(settings.pcap_output_dir) / art["filename"])
        return None

    def __repr__(self) -> str:
        return f"<GenerationJob {self.id} status={self.status}>"
