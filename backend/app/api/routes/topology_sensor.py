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

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.models.scenario import Scenario
from app.schemas.topology import TopologyPreviewResponse
from app.services import topology_planner

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
