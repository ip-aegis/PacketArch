# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Traffic generation models and data structures."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class JobStatus(str, Enum):
    """Status of a traffic generation job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GenerationResult:
    """Result of traffic generation."""

    job_id: str
    scenario_id: UUID
    status: JobStatus
    pcap_path: str | None = None
    packets_generated: int = 0
    duration_ms: float = 0
    file_size_bytes: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    # One entry per PCAP file produced by the run. Always contains at least
    # the ``combined`` file; when attack export is on it also carries
    # ``baseline`` and ``attack``. Shape: {kind, filename, packets, size_bytes}.
    artifacts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GenerationJob:
    """Traffic generation job metadata."""

    job_id: str
    scenario_id: UUID
    user_id: UUID | None
    status: JobStatus
    progress: float = 0.0
    total_duration_ms: int = 0
    output_path: str | None = None
    packets_generated: int = 0
    file_size_bytes: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
