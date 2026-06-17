# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Deployment schemas for API validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.scenario import ScenarioModes


class CyberVisionSummary(BaseModel):
    """Compact Cyber Vision provisioning summary for deployment badges."""

    status: str = "not_started"
    preset_label: str | None = None
    subnet: str | None = None
    group_count: int = 0
    device_count: int = 0


class UnifiedDeploymentResponse(BaseModel):
    """Schema for agent deployment responses."""

    id: UUID
    scenario_id: UUID
    scenario_name: str | None = None
    agent_id: UUID | None = None
    agent_name: str | None = None
    network_interface: str
    status: str  # Agent states: starting, running, stopping, stopped, error, disconnected
    run_mode: str = "perpetual"
    duration_ms: int | None = None
    packets_injected: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    created_at: datetime
    # Real-time attack state from agent (null if not available)
    attack: dict | None = None
    # Mode flags from the scenario definition so the UI can render badges
    # without making a second fetch per row.
    scenario_modes: ScenarioModes = Field(default_factory=ScenarioModes)
    # Cyber Vision provisioning summary (None when not provisioned).
    cyber_vision: CyberVisionSummary | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_agent_deployment(
        cls,
        deployment,
        agent=None,
        scenario=None,
        attack=None,
    ) -> "UnifiedDeploymentResponse":
        """Create from Agent deployment model.

        Args:
            deployment: AgentDeployment model instance
            agent: Optional TrafficAgent model instance
            scenario: Optional Scenario model instance
            attack: Optional attack state dict from traffic_dashboard
        """
        modes = ScenarioModes()
        cyber_vision = None
        if scenario is not None and scenario.definition:
            d = scenario.definition
            modes = ScenarioModes(
                clean_demo_mode=bool(d.get("clean_demo_mode", False)),
                broadcast_traffic_enabled=bool(
                    d.get("broadcast_traffic_enabled", True)
                ),
                cell_isolation_mode=str(
                    (d.get("cell_isolation") or {}).get("mode", "off")
                ),
            )
            cv = d.get("cyber_vision")
            if cv and cv.get("status"):
                cyber_vision = CyberVisionSummary(
                    status=cv.get("status", "not_started"),
                    preset_label=cv.get("preset_label"),
                    subnet=cv.get("subnet"),
                    group_count=len(cv.get("groups") or {}),
                    device_count=int(cv.get("device_count") or 0),
                )
        return cls(
            id=deployment.id,
            scenario_id=deployment.scenario_id,
            scenario_name=scenario.name if scenario else None,
            agent_id=deployment.agent_id,
            agent_name=agent.name if agent else None,
            network_interface=deployment.interface or "unknown",
            status=deployment.state,
            run_mode="perpetual",
            duration_ms=None,
            packets_injected=deployment.packets_sent,
            error_message=deployment.error_message,
            started_at=deployment.started_at,
            stopped_at=deployment.stopped_at,
            created_at=deployment.started_at,  # AgentDeployment uses started_at as creation time
            attack=attack,
            scenario_modes=modes,
            cyber_vision=cyber_vision,
        )


class UnifiedDeploymentListResponse(BaseModel):
    """Schema for listing deployments."""

    items: list[UnifiedDeploymentResponse]
    total: int
