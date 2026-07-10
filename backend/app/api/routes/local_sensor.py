# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Local sensor lab routes: app-managed on-box (agent + CV sensor + SPAN) labs.

Mirrors the CML route module, but the lab runs on the PacketArch host itself,
provisioned by the privileged host-agent over a shared-volume file-queue. Gated
exactly like CML/agents (setup complete + live traffic enabled); admin on
mutations, current-user on reads.
"""

import logging

from fastapi import APIRouter

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.schemas.local_sensor import (
    LocalHostStatusResponse,
    LocalLabBuildRequest,
    LocalLabBuildResponse,
    LocalLabItem,
    LocalLabListResponse,
    LocalLabTeardownResponse,
)
from app.services import host_agent_client, local_sensor_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/local-sensor", tags=["Local Sensor"])


@router.get("/host-status", response_model=LocalHostStatusResponse)
async def host_status(_user: CurrentUser) -> LocalHostStatusResponse:
    """Report whether the host-agent capability is present and initialized."""
    available = host_agent_client.is_available()
    seen = host_agent_client.host_agent_seen() if available else False
    if not available:
        msg = "Host-agent state volume not mounted — local sensor labs unavailable."
    elif not seen:
        msg = "Host-agent state volume mounted; waiting for the host-agent to initialize."
    else:
        msg = "Host-agent available."
    return LocalHostStatusResponse(available=available, host_agent_seen=seen, message=msg)


@router.get("/labs", response_model=LocalLabListResponse)
async def list_labs(db: DBSession, _user: CurrentUser) -> LocalLabListResponse:
    """List all local sensor labs with live status."""
    items = await local_sensor_service.list_labs(db)
    return LocalLabListResponse(items=[LocalLabItem(**i) for i in items])


@router.post("/build", response_model=LocalLabBuildResponse)
async def build(req: LocalLabBuildRequest, db: DBSession, admin: AdminUser) -> LocalLabBuildResponse:
    """Build a local agent + CV-sensor lab on the host. Returns the agent token
    once. Provisioning runs asynchronously in the host-agent; poll /labs."""
    result = await local_sensor_service.build_lab(
        db,
        name=req.name,
        agent_name=req.agent_name,
        created_by_id=admin.id,
    )
    return LocalLabBuildResponse(**result)


@router.get("/{lab_id}", response_model=LocalLabItem)
async def get_lab(lab_id: str, db: DBSession, _user: CurrentUser) -> LocalLabItem:
    """Get one local lab with its live host-agent status."""
    item = await local_sensor_service.get_lab(db, lab_id)
    if item is None:
        raise NotFoundError("Local lab not found.")
    return LocalLabItem(**item)


@router.post("/{lab_id}/teardown", response_model=LocalLabTeardownResponse)
async def teardown(lab_id: str, db: DBSession, _admin: AdminUser) -> LocalLabTeardownResponse:
    """Full-delete teardown: host resources + DB rows removed (kept in sync)."""
    result = await local_sensor_service.teardown_lab(db, lab_id)
    return LocalLabTeardownResponse(**result)
