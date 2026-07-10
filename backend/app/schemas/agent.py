# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Pydantic schemas for traffic agent API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """Schema for creating a new traffic agent."""

    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    description: str | None = Field(None, description="Agent description")
    default_interface: str | None = Field(None, description="Default network interface")


class AgentUpdate(BaseModel):
    """Schema for updating a traffic agent."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    default_interface: str | None = None
    is_active: bool | None = None


class AgentResponse(BaseModel):
    """Schema for traffic agent response."""

    id: UUID
    name: str
    description: str | None
    default_interface: str | None
    status: str
    version: str | None
    hostname: str | None
    platform: str | None
    is_active: bool
    last_seen: datetime | None
    first_connected_at: datetime | None = Field(
        None,
        description="When the agent first connected (null if never connected)"
    )
    # CML deployment linkage (set when auto-deployed into a Modeling Labs lab)
    cml_lab_id: str | None = None
    cml_node_id: str | None = None
    cml_node_label: str | None = None
    local_lab_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentWithToken(AgentResponse):
    """Agent response including the authentication token (only on create)."""

    token: str = Field(..., description="Authentication token (shown only once)")


class AgentListResponse(BaseModel):
    """Paginated list of agents."""

    agents: list[AgentResponse]
    total: int
    page: int
    page_size: int
    standard_version: str | None = Field(None, description="Current standard/latest agent version available")


class AgentConnectionInfo(BaseModel):
    """Real-time connection info for a connected agent."""

    agent_id: UUID
    connected_at: datetime
    last_heartbeat: datetime
    hostname: str | None
    platform: str | None
    version: str | None
    cpu_percent: float
    memory_percent: float
    running_scenarios: list[str]


class DeploymentCreate(BaseModel):
    """Schema for deploying a scenario to an agent."""

    scenario_id: UUID
    interface: str | None = Field(None, description="Override default interface")
    adaptive_config: dict[str, Any] | None = Field(
        None,
        description="Optional adaptive config overrides (e.g. phase_schedule)",
    )
    attack_playbook: dict[str, Any] | None = Field(
        None,
        description="Optional attack playbook config (playbook_id, intensity, etc.)",
    )
    cell_isolation_override: dict[str, Any] | None = Field(
        None,
        description=(
            "Optional per-run override for Purdue cell isolation "
            "({'mode': ..., 'applies_to_levels': [...]}). Merged into the "
            "scenario definition before it is sent to the agent."
        ),
    )
    provision_cyber_vision: bool = Field(
        False,
        description=(
            "If true and Cyber Vision is configured, create a CV preset for "
            "this scenario at deploy time and schedule zone-group creation once "
            "CV has discovered the simulated devices."
        ),
    )


class DeploymentResponse(BaseModel):
    """Schema for deployment status."""

    id: UUID
    agent_id: UUID
    scenario_id: UUID
    state: str
    interface: str | None
    packets_sent: int
    error_message: str | None
    started_at: datetime
    stopped_at: datetime | None

    model_config = {"from_attributes": True}


class DeployNewLabRequest(BaseModel):
    """Schema for deploying a scenario to a brand-new, dedicated Local Lab.

    Mirrors DeploymentCreate (minus scenario_id living outside as a sibling
    field) plus the two Local Lab naming fields from LocalLabBuildRequest.
    The sensor is auto-provisioned via the Cyber Vision API; the scenario
    deploys automatically the moment the new agent comes online.
    """

    scenario_id: UUID
    lab_name: str = Field(..., min_length=1, max_length=128, description="Name for the new local lab")
    agent_name: str | None = Field(
        default=None,
        max_length=255,
        description="Name for the PacketArch agent; default derived from the lab slug",
    )
    adaptive_config: dict[str, Any] | None = Field(
        None,
        description="Optional adaptive config overrides (e.g. phase_schedule)",
    )
    attack_playbook: dict[str, Any] | None = Field(
        None,
        description="Optional attack playbook config (playbook_id, intensity, etc.)",
    )
    cell_isolation_override: dict[str, Any] | None = Field(
        None,
        description=(
            "Optional per-run override for Purdue cell isolation "
            "({'mode': ..., 'applies_to_levels': [...]}). Merged into the "
            "scenario definition before it is sent to the agent."
        ),
    )
    provision_cyber_vision: bool = Field(
        False,
        description=(
            "If true and Cyber Vision is configured, create a CV preset for "
            "this scenario once it deploys and schedule zone-group creation "
            "once CV has discovered the simulated devices."
        ),
    )


class DeployNewLabResponse(BaseModel):
    """Result of a deploy-new-lab request. The lab is still provisioning when
    this returns — the scenario deploys automatically once the agent connects."""

    success: bool
    message: str
    lab_id: str | None = None
    slug: str | None = None
    agent_id: str | None = None
    agent_token: str | None = Field(default=None, description="Agent token (shown only once)")
    sensor_serial: str | None = None
    state: str = "pending"


class InterfaceInfo(BaseModel):
    """Network interface information from agent."""

    name: str
    mac: str | None = None
    addresses: list[dict] = Field(default_factory=list)
    error: str | None = None


class AgentInterfacesResponse(BaseModel):
    """Response containing agent network interfaces."""

    agent_id: UUID
    interfaces: list[InterfaceInfo]


class AgentUpdateStatus(BaseModel):
    """Status of an in-progress agent update."""

    agent_id: UUID
    status: str = Field(
        ...,
        description="Update status: idle, initiated, downloading, loading, restarting, complete, failed, timeout"
    )
    progress: int | None = Field(None, description="Download progress percentage (0-100)")
    message: str = Field(..., description="Human-readable status message")
    target_version: str | None = Field(None, description="Version being updated to")
    initiated_at: datetime | None = Field(None, description="When the update was initiated")
    completed_at: datetime | None = Field(None, description="When the update completed (success or failure)")
    error: str | None = Field(None, description="Error message if update failed")
