"""Schemas for traffic generation API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    """Request to start traffic generation."""

    scenario_id: UUID = Field(..., description="Scenario UUID to generate traffic for")
    duration_override_ms: int | None = Field(
        None,
        description="Override scenario duration in milliseconds",
        ge=1000,
        le=600000,
    )
    output_format: str = Field(
        "pcap",
        description="Output format (currently only 'pcap' supported)",
    )
    filename_prefix: str | None = Field(
        None,
        description="Optional prefix for output filename",
        max_length=50,
    )


class GenerationJobResponse(BaseModel):
    """Response with generation job details."""

    job_id: str = Field(..., description="Unique job identifier")
    scenario_id: UUID = Field(..., description="Scenario UUID")
    scenario_name: str | None = Field(None, description="Scenario name for display")
    status: str = Field(..., description="Job status (pending, running, completed, failed, cancelled)")
    progress: float = Field(0.0, description="Generation progress (0-100)", ge=0, le=100)
    total_duration_ms: int = Field(..., description="Total duration in milliseconds")
    output_path: str | None = Field(None, description="Path to output PCAP file")
    packets_generated: int = Field(0, description="Number of packets generated")
    file_size_bytes: int = Field(0, description="Output file size in bytes")
    error_message: str | None = Field(None, description="Error message if failed")
    created_at: datetime | None = Field(None, description="Job creation timestamp")
    started_at: datetime | None = Field(None, description="Job start timestamp")
    completed_at: datetime | None = Field(None, description="Job completion timestamp")

    class Config:
        from_attributes = True


class GenerationResultResponse(BaseModel):
    """Response with generation results."""

    job_id: str = Field(..., description="Job identifier")
    scenario_id: UUID = Field(..., description="Scenario UUID")
    status: str = Field(..., description="Generation status")
    pcap_path: str | None = Field(None, description="Path to generated PCAP file")
    packets_generated: int = Field(0, description="Total packets generated")
    duration_ms: float = Field(0, description="Generation duration in milliseconds")
    file_size_bytes: int = Field(0, description="File size in bytes")
    error_message: str | None = Field(None, description="Error message if failed")


class SupportedProtocolsResponse(BaseModel):
    """Response with list of supported protocols."""

    protocols: list[str] = Field(..., description="List of supported protocol types")


class JobListResponse(BaseModel):
    """Response with list of jobs."""

    jobs: list[GenerationJobResponse] = Field(..., description="List of generation jobs")
    total: int = Field(..., description="Total number of jobs")
