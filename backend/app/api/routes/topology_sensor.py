# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Multi-sensor topology ("Advanced Deployment") routes.

Phase 0 surface: a pure, side-effect-free preview that derives the L1
topology (per-zone IE3500 + IE9320 core) and per-flow SPAN segment plans
for a scenario. Deployment/teardown routes arrive with the provisioning
phase. Gated by RequireMultiSensorTopology (+ live-traffic) at mount.
"""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.models.scenario import Scenario
from app.schemas.topology import (
    TopologyDeploymentResponse,
    TopologyPreflightResponse,
    TopologyPreviewResponse,
    TopologyProvisionResponse,
)
from app.services import topology_planner, topology_provisioning_service

router = APIRouter(prefix="/scenarios/{scenario_id}/topology", tags=["Multi-Sensor Topology"])


@router.post("/preview", response_model=TopologyPreviewResponse)
async def preview_topology(
    scenario_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> TopologyPreviewResponse:
    """Derive the multi-sensor L1 topology and per-flow segment plans.

    No side effects: nothing is provisioned or persisted, and the source
    scenario definition is never mutated.
    """
    result = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    plan = topology_planner.preview(scenario.definition or {}, seed=str(scenario.id))
    return TopologyPreviewResponse(**plan)


@router.get("/preflight", response_model=TopologyPreflightResponse)
async def preflight(
    scenario_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> TopologyPreflightResponse:
    """Non-destructive pre-deploy summary: sensor count, RAM estimate, spans."""
    data = await topology_provisioning_service.preflight(db, scenario_id)
    return TopologyPreflightResponse(**data)


@router.post("/deploy", response_model=TopologyProvisionResponse, status_code=201)
async def deploy(
    scenario_id: str,
    db: DBSession,
    admin: AdminUser,
) -> TopologyProvisionResponse:
    """Provision one Local Sensor Lab per SPAN (zones + core).

    Reuses the Local Sensor Lab auto-provisioning (reusable CV deployment
    token) N+1 times. Agent tokens are returned once, per member lab.
    """
    data = await topology_provisioning_service.provision(
        db, scenario_id, created_by_id=admin.id
    )
    return TopologyProvisionResponse(**data)


@router.get("/deployment", response_model=TopologyDeploymentResponse)
async def deployment_status(
    scenario_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> TopologyDeploymentResponse:
    """Live status of this scenario's topology deployment member labs."""
    data = await topology_provisioning_service.status(db, scenario_id)
    return TopologyDeploymentResponse(**data)


@router.post("/start")
async def start_injection(
    scenario_id: str,
    db: DBSession,
    admin: AdminUser,
) -> dict:
    """Start live traffic — the core lab's agent (single conductor) injects
    each frame's per-segment copies onto every SPAN's veth. Requires the member
    labs to be running."""
    return await topology_provisioning_service.start_injection(db, scenario_id)


@router.post("/stop")
async def stop_injection(
    scenario_id: str,
    db: DBSession,
    admin: AdminUser,
) -> dict:
    """Stop the conductor's live injection."""
    return await topology_provisioning_service.stop_injection(db, scenario_id)


@router.post("/teardown", response_model=TopologyDeploymentResponse)
async def teardown(
    scenario_id: str,
    db: DBSession,
    admin: AdminUser,
) -> TopologyDeploymentResponse:
    """Tear down every member lab of this scenario's topology deployment."""
    result = await topology_provisioning_service.teardown(db, scenario_id)
    # Return the post-teardown status so the UI reconciles.
    return TopologyDeploymentResponse(
        scenario_id=scenario_id, sensor_count=0, members=[], torn_down=result["torn_down"]
    )
