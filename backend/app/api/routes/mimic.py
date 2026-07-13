# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PacketArch Mimic routes — interactive device-emulation deployment.

Deploy/list/teardown *device personas* (bound protocol servers + active-master
client loops) onto an existing Local Lab's SPAN, where the lab's CV sensor
classifies them. The unprivileged backend only writes specs to the host-agent
file-queue (see app.mimic.deploy); the privileged host-agent provisions the
netns cells. Gated by MIMIC_ENABLED (router-level dep); admin on mutations,
current-user on reads. No CV token — attaches to an already-provisioned sensor.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.deps import AdminUser, CurrentUser
from app.core.exceptions import NotFoundError, ValidationError
from app.mimic import deploy, presets, scaffold
from app.mimic.interfaces import PersonaSpec
from app.services import host_agent_client
from app.services.device_templates import get_all_templates
from app.services.local_lab_naming import gen_if as gen_if_for
from app.mimic.process_library import available_models
from app.schemas.mimic import (
    CellItem,
    CellListResponse,
    DeployCellRequest,
    DeployCellResponse,
    AuthorCellRequest,
    MimicStatusResponse,
    PresetListResponse,
    ProcessModelListResponse,
    TeardownResponse,
    TemplateItem,
    TemplateListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mimic", tags=["Mimic"])


@router.get("/status", response_model=MimicStatusResponse)
async def status(_user: CurrentUser) -> MimicStatusResponse:
    """Whether Mimic is usable here (enabled + host-agent present)."""
    available = host_agent_client.is_available()
    msg = "Mimic ready." if available else (
        "Host-agent state volume not mounted — Mimic needs the on-box host-agent."
    )
    return MimicStatusResponse(enabled=True, host_agent_available=available, message=msg)


# Protocols Mimic can currently emulate (server side).
_MIMIC_PROTOCOLS = frozenset({"modbus_tcp", "opc_ua", "bacnet_ip", "iec104"})


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(_user: CurrentUser) -> TemplateListResponse:
    """Device templates usable as Mimic personas (support an emulated protocol)."""
    items = [
        TemplateItem(
            id=t.id, vendor=t.vendor, model_name=t.model_name,
            device_type=t.device_type, protocols=t.supported_protocols or [],
        )
        for t in get_all_templates()
        if _MIMIC_PROTOCOLS.intersection(t.supported_protocols or [])
    ]
    return TemplateListResponse(items=items)


@router.get("/process-models", response_model=ProcessModelListResponse)
async def list_process_models(_user: CurrentUser) -> ProcessModelListResponse:
    """Process models available to back a persona's registers."""
    return ProcessModelListResponse(models=available_models())


@router.get("/presets", response_model=PresetListResponse)
async def list_presets(_user: CurrentUser) -> PresetListResponse:
    """One-click deployable device presets (full authoring is the Studio canvas)."""
    return PresetListResponse(items=presets.list_presets())


@router.get("/cells", response_model=CellListResponse)
async def list_cells(_user: CurrentUser) -> CellListResponse:
    """All Mimic cells with live status."""
    return CellListResponse(items=[CellItem(**c) for c in deploy.list_cells()])


@router.get("/cells/{cell_slug}", response_model=CellItem)
async def get_cell(cell_slug: str, _user: CurrentUser) -> CellItem:
    """One Mimic cell's status."""
    for c in deploy.list_cells():
        if c["cell_slug"] == cell_slug:
            return CellItem(**c)
    raise NotFoundError(f"Mimic cell {cell_slug!r} not found")


@router.post("/cells", response_model=DeployCellResponse)
async def deploy_cell(req: DeployCellRequest, _admin: AdminUser) -> DeployCellResponse:
    """Deploy a Mimic cell onto an existing lab's SPAN."""
    if not host_agent_client.is_available():
        raise ValidationError("Host-agent not available — Mimic needs the on-box host-agent.")
    personas = [PersonaSpec.from_dict(p.model_dump()) for p in req.personas]
    result = deploy.deploy_cell(
        lab_slug=req.lab_slug,
        gen_if=gen_if_for(req.lab_slug),
        cell_name=req.cell_name,
        personas=personas,
    )
    return DeployCellResponse(**result)


@router.post("/cells/author", response_model=DeployCellResponse)
async def author_cell(req: AuthorCellRequest, _admin: AdminUser) -> DeployCellResponse:
    """Deploy a cell authored in the Studio canvas (device graph → scaffolded personas)."""
    if not host_agent_client.is_available():
        raise ValidationError("Host-agent not available — Mimic needs the on-box host-agent.")
    result = scaffold.author_cell(
        lab_slug=req.lab_slug,
        gen_if=gen_if_for(req.lab_slug),
        cell_name=req.cell_name,
        devices=[d.model_dump() for d in req.devices],
        relationships=[r.model_dump() for r in req.relationships],
    )
    return DeployCellResponse(**result)


@router.delete("/cells/{cell_slug}", response_model=TeardownResponse)
async def teardown_cell(cell_slug: str, _admin: AdminUser) -> TeardownResponse:
    """Tear down a Mimic cell (personas + hub-bridge; the lab is untouched)."""
    rid = deploy.teardown_cell(cell_slug)
    return TeardownResponse(request_id=rid)
