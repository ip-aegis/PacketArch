"""Remote deployment schemas for API validation."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.remote_deployment import DeploymentStatus, RunMode


class DeploymentRequest(BaseModel):
    """Schema for starting a new deployment."""

    scenario_id: UUID
    docker_host_id: UUID
    network_interface: str = Field(..., min_length=1, max_length=100)
    run_mode: str = Field(
        default=RunMode.TIMED.value,
        pattern="^(timed|perpetual)$",
        description="Run mode: 'timed' (stops after duration) or 'perpetual' (runs until stopped)",
    )
    duration_ms: int | None = Field(
        default=60000,
        ge=1000,
        le=86400000,
        description="Duration in milliseconds (required for timed mode, ignored for perpetual)",
    )

    @model_validator(mode="after")
    def validate_duration_for_mode(self) -> Self:
        """Validate that duration is provided for timed mode."""
        if self.run_mode == RunMode.TIMED.value and self.duration_ms is None:
            raise ValueError("duration_ms is required for timed mode")
        return self


class DeploymentResponse(BaseModel):
    """Schema for deployment response."""

    id: UUID
    scenario_id: UUID
    scenario_name: str | None = None
    docker_host_id: UUID
    docker_host_name: str | None = None
    container_id: str | None
    container_name: str | None
    network_interface: str
    status: DeploymentStatus
    run_mode: str = RunMode.TIMED.value
    duration_ms: int | None
    packets_injected: int
    error_message: str | None
    started_at: datetime | None
    stopped_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, deployment, include_names: bool = True) -> "DeploymentResponse":
        """Create response from model with optional related names."""
        return cls(
            id=deployment.id,
            scenario_id=deployment.scenario_id,
            scenario_name=deployment.scenario.name if include_names and deployment.scenario else None,
            docker_host_id=deployment.docker_host_id,
            docker_host_name=deployment.docker_host.name if include_names and deployment.docker_host else None,
            container_id=deployment.container_id,
            container_name=deployment.container_name,
            network_interface=deployment.network_interface,
            status=DeploymentStatus(deployment.status),
            run_mode=deployment.run_mode,
            duration_ms=deployment.duration_ms,
            packets_injected=deployment.packets_injected,
            error_message=deployment.error_message,
            started_at=deployment.started_at,
            stopped_at=deployment.stopped_at,
            created_at=deployment.created_at,
        )


class DeploymentListResponse(BaseModel):
    """Schema for listing deployments."""

    items: list[DeploymentResponse]
    total: int


class DeploymentStatusUpdate(BaseModel):
    """Schema for deployment status update."""

    status: DeploymentStatus
    packets_injected: int | None = None
    error_message: str | None = None


class DeploymentLogsResponse(BaseModel):
    """Schema for deployment container logs."""

    deployment_id: UUID
    container_id: str | None
    logs: str
    timestamp: datetime
