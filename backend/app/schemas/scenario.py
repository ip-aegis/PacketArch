"""Scenario schemas for API validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ScenarioBase(BaseModel):
    """Base schema for scenario."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    vertical: str | None = Field(default=None, max_length=50)
    total_duration_ms: int = Field(default=60000, ge=1000, le=86400000)  # 1s to 24h


class ScenarioCreate(ScenarioBase):
    """Schema for creating a scenario."""

    definition: dict[str, Any] = Field(default_factory=lambda: {
        "devices": {},
        "flows": {},
        "zones": {},
        "phases": [],
        "events": []
    })
    addressing_config: dict[str, Any] | None = None


class ScenarioUpdate(BaseModel):
    """Schema for updating a scenario."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    vertical: str | None = None
    total_duration_ms: int | None = Field(default=None, ge=1000, le=86400000)
    definition: dict[str, Any] | None = None
    addressing_config: dict[str, Any] | None = None


class ScenarioResponse(ScenarioBase):
    """Schema for scenario response."""

    id: UUID
    user_id: UUID | None
    definition: dict[str, Any]
    addressing_config: dict[str, Any] | None
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReadinessCheck(BaseModel):
    """A single readiness check result."""

    name: str
    passed: bool
    severity: str  # "error" or "warning"
    message: str | None = None


class ReadinessSummary(BaseModel):
    """Scenario readiness summary for list view."""

    score: int = 0  # 0-100
    status: str = "not_ready"  # "ready", "warnings", "not_ready"
    error_count: int = 0
    warning_count: int = 0
    checks: list[ReadinessCheck] = []


class ScenarioSummaryResponse(BaseModel):
    """Schema for scenario summary (listing)."""

    id: UUID
    name: str
    description: str | None
    vertical: str | None
    total_duration_ms: int
    version: int
    device_count: int = 0
    flow_count: int = 0
    has_learned_patterns: bool = False
    protocols_enhanced: list[str] = []
    readiness: ReadinessSummary = Field(default_factory=ReadinessSummary)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    """Schema for listing scenarios."""

    items: list[ScenarioSummaryResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ScenarioExport(BaseModel):
    """Schema for exporting a scenario."""

    name: str
    description: str | None
    vertical: str | None
    total_duration_ms: int
    definition: dict[str, Any]
    addressing_config: dict[str, Any] | None
    version: int
    exported_at: datetime


class ScenarioImport(BaseModel):
    """Schema for importing a scenario."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    vertical: str | None = None
    total_duration_ms: int = Field(default=60000, ge=1000)
    definition: dict[str, Any]
    addressing_config: dict[str, Any] | None = None
