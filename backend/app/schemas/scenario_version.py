# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Scenario version schemas for API validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class VersionSummary(BaseModel):
    """Summary of a version for the timeline list (no definition blob)."""

    id: UUID
    version_number: int
    name: str
    label: str | None = None
    source: str
    device_count: int = 0
    flow_count: int = 0
    created_at: datetime
    created_by: UUID | None = None

    class Config:
        from_attributes = True


class VersionDetail(VersionSummary):
    """Full version detail including definition (for diff/restore)."""

    description: str | None = None
    definition: dict[str, Any]
    addressing_config: dict[str, Any] | None = None
    total_duration_ms: int


class VersionListResponse(BaseModel):
    """Paginated list of versions."""

    items: list[VersionSummary]
    total: int
    page: int
    page_size: int


class CreateVersionRequest(BaseModel):
    """Request to create a named version (explicit save)."""

    label: str | None = Field(default=None, max_length=255)


class UpdateVersionRequest(BaseModel):
    """Request to update a version's label."""

    label: str | None = Field(default=None, max_length=255)


class DiffEntry(BaseModel):
    """A single change in the diff."""

    category: str  # "devices", "flows", "zones", "phases", "metadata"
    change_type: str  # "added", "removed", "modified"
    item_id: str | None = None
    item_name: str | None = None
    details: dict[str, Any] | None = None


class VersionDiffResponse(BaseModel):
    """Result of diffing two versions."""

    scenario_id: UUID
    base_version: int
    compare_version: int
    changes: list[DiffEntry]
    summary: dict[str, int]


class DiffSummaryResponse(BaseModel):
    """AI-generated plain-English summary of a version diff."""

    summary: str


class RollbackResponse(BaseModel):
    """Response after rolling back to a version."""

    scenario_id: UUID
    rolled_back_to_version: int
    new_version_number: int
    message: str
