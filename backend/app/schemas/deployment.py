"""Remote deployment schemas for API validation."""

from datetime import datetime
from enum import Enum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.remote_deployment import DeploymentStatus, RunMode


class DeploymentType(str, Enum):
    """Type of deployment target."""
    DOCKER = "docker"
    AGENT = "agent"


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


class UnifiedDeploymentResponse(BaseModel):
    """Unified schema for both Docker and Agent deployments."""

    id: UUID
    deployment_type: DeploymentType
    scenario_id: UUID
    scenario_name: str | None = None
    # Docker-specific fields (null for agent deployments)
    docker_host_id: UUID | None = None
    docker_host_name: str | None = None
    container_id: str | None = None
    container_name: str | None = None
    # Agent-specific fields (null for docker deployments)
    agent_id: UUID | None = None
    agent_name: str | None = None
    # Common fields
    network_interface: str
    status: str  # Using str to handle both DeploymentStatus and agent states
    run_mode: str = "perpetual"  # Agent deployments are always perpetual
    duration_ms: int | None = None
    packets_injected: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_docker_deployment(cls, deployment, include_names: bool = True) -> "UnifiedDeploymentResponse":
        """Create from Docker deployment model."""
        return cls(
            id=deployment.id,
            deployment_type=DeploymentType.DOCKER,
            scenario_id=deployment.scenario_id,
            scenario_name=deployment.scenario.name if include_names and deployment.scenario else None,
            docker_host_id=deployment.docker_host_id,
            docker_host_name=deployment.docker_host.name if include_names and deployment.docker_host else None,
            container_id=deployment.container_id,
            container_name=deployment.container_name,
            agent_id=None,
            agent_name=None,
            network_interface=deployment.network_interface,
            status=deployment.status,
            run_mode=deployment.run_mode,
            duration_ms=deployment.duration_ms,
            packets_injected=deployment.packets_injected,
            error_message=deployment.error_message,
            started_at=deployment.started_at,
            stopped_at=deployment.stopped_at,
            created_at=deployment.created_at,
        )

    @classmethod
    def from_agent_deployment(cls, deployment, agent=None, scenario=None) -> "UnifiedDeploymentResponse":
        """Create from Agent deployment model."""
        return cls(
            id=deployment.id,
            deployment_type=DeploymentType.AGENT,
            scenario_id=deployment.scenario_id,
            scenario_name=scenario.name if scenario else None,
            docker_host_id=None,
            docker_host_name=None,
            container_id=None,
            container_name=None,
            agent_id=deployment.agent_id,
            agent_name=agent.name if agent else None,
            network_interface=deployment.interface or "unknown",
            status=deployment.state,
            run_mode="perpetual",  # Agent deployments are always perpetual
            duration_ms=None,
            packets_injected=deployment.packets_sent,
            error_message=deployment.error_message,
            started_at=deployment.started_at,
            stopped_at=deployment.stopped_at,
            created_at=deployment.started_at,  # AgentDeployment uses started_at as creation time
        )


class UnifiedDeploymentListResponse(BaseModel):
    """Schema for listing unified deployments."""

    items: list[UnifiedDeploymentResponse]
    total: int


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
