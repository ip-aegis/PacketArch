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

import asyncio
import logging
import uuid

from fastapi import APIRouter

from app.api.deps import AdminUser, CurrentUser, DBSession
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
    CmlDeployRequest,
    CmlDeployResponse,
    CmlLabDetail,
    CmlLabItem,
    CmlLabListResponse,
    CmlLabNode,
    CmlMimicStatusResponse,
    CmlPersonaResult,
    CmlTeardownResponse,
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
    """Device templates usable as Mimic personas, each with its certification: which
    server protocols it can convincingly emulate per deploy target, and whether it's
    a responder (server persona) or a client/software role (client-only persona)."""
    from app.mimic.certification import certify_template
    from app.services.device_templates import get_fingerprint_from_template

    items = []
    for t in get_all_templates():
        if not _MIMIC_PROTOCOLS.intersection(t.supported_protocols or []):
            continue
        fp = get_fingerprint_from_template(t.id) or {}
        cert = certify_template(fp, t.device_type, t.supported_protocols)
        # Present a device only if it can be a server SOMEWHERE or is a valid client.
        if not cert.client_capable and not any(cert.server_protocols.values()):
            continue
        items.append(TemplateItem(
            id=t.id, vendor=t.vendor, model_name=t.model_name,
            device_type=t.device_type, protocols=t.supported_protocols or [],
            role_class=cert.role_class, client_capable=cert.client_capable,
            server_protocols=cert.server_protocols,
        ))
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


def _certify_or_raise(devices: list, target: str) -> None:
    """Reject any authored persona that isn't certified to emulate its protocol
    convincingly on ``target`` — the deploy-time realism guardrail."""
    from app.mimic.certification import check_devices
    from app.services.device_templates import get_fingerprint_from_template
    by_id = {t.id: t for t in get_all_templates()}
    items = []
    for d in devices:
        tid = d.template_id if hasattr(d, "template_id") else d["template_id"]
        proto = d.protocol if hasattr(d, "protocol") else d.get("protocol")
        name = getattr(d, "name", None) or (d.get("name") if isinstance(d, dict) else None) or tid
        t = by_id.get(tid)
        if t is None:
            raise ValidationError(f"{name}: unknown device template {tid!r}")
        fp = get_fingerprint_from_template(tid) or {}
        items.append((name, t.device_type, fp, proto))
    errors = check_devices(items, target)
    if errors:
        raise ValidationError("Not certified for realistic emulation — " + "; ".join(errors))


@router.post("/cells/author", response_model=DeployCellResponse)
async def author_cell(req: AuthorCellRequest, _admin: AdminUser) -> DeployCellResponse:
    """Deploy a cell authored in the Studio canvas (device graph → scaffolded personas)."""
    if not host_agent_client.is_available():
        raise ValidationError("Host-agent not available — Mimic needs the on-box host-agent.")
    _certify_or_raise(req.devices, "onbox")
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


# --------------------------------------------------------------------------- #
# Off-box (CML): each persona is its own bare Alpine CML node running the slim
# native runtime; an optional IOSvL2 SPAN mirrors the OT segment to an auto-
# provisioned CV docker sensor node. No host-agent — the backend drives CML + CV
# directly. Labs are titled "Mimic: <name>" so we can list/tear-down without new
# persistence; the CV sensor serial (for cleanup) rides in the lab description.
# --------------------------------------------------------------------------- #

_CML_LAB_PREFIX = "Mimic: "
_CV_DEPLOYMENT = "mimic-cml-sensors"


async def _cml_service(db):
    from app.api.routes.cml import get_cml_settings
    from app.services.cml_service import CMLService
    url, user, pw, verify, server_url = await get_cml_settings(db)
    return CMLService(url, user, pw, verify_ssl=verify), server_url


async def _cv_service(db):
    from app.api.routes.cyber_vision import get_cv_settings
    from app.services.cyber_vision_service import CyberVisionService
    url, token, verify = await get_cv_settings(db)
    return CyberVisionService(url, token, verify_ssl=verify)


@router.get("/cml/status", response_model=CmlMimicStatusResponse)
async def cml_status(db: DBSession, _user: CurrentUser) -> CmlMimicStatusResponse:
    """Whether the off-box (CML) path is usable: CML reachable + CV configured."""
    cml_connected = False
    cv_configured = False
    msg = ""
    try:
        svc, _ = await _cml_service(db)
        await svc.list_labs()
        cml_connected = True
    except Exception as e:  # noqa: BLE001 — not-configured / unreachable both mean "no"
        msg = f"CML not available: {e}"
    try:
        await _cv_service(db)
        cv_configured = True
    except Exception:  # noqa: BLE001
        pass
    return CmlMimicStatusResponse(cml_connected=cml_connected, cv_configured=cv_configured, message=msg)


@router.post("/cml/deploy", response_model=CmlDeployResponse)
async def cml_deploy(req: CmlDeployRequest, db: DBSession, _admin: AdminUser) -> CmlDeployResponse:
    """Deploy an authored device graph OFF-BOX as slim personas on CML (optionally
    with an IOSvL2 SPAN + auto-provisioned CV sensor)."""
    from app.mimic.slim_author import resolve_cml_cell
    from app.mimic.slim_deploy import deploy_slim_cell
    from app.mimic.slim_sensor import deploy_cell_with_sensor

    svc, server_url = await _cml_service(db)
    if not server_url:
        raise ValidationError(
            "CML integration has no PacketArch server URL configured — the CML nodes "
            "need a URL to phone home to for the slim runtime + check-in.")
    _certify_or_raise(req.devices, "offbox")
    specs = resolve_cml_cell(devices=[d.model_dump() for d in req.devices],
                             relationships=[r.model_dump() for r in req.relationships])
    title = f"{_CML_LAB_PREFIX}{req.cell_name}"
    sensor_serial = None
    description = ""
    if req.with_sensor:
        cv = await _cv_service(db)
        await cv.create_deployment_token(_CV_DEPLOYMENT)
        sensor_serial = f"mimic-{scaffold_slug(req.cell_name)}-{uuid.uuid4().hex[:6]}"
        description = f"sensor:{sensor_serial}"
    lab_id = await svc.create_lab(title, description)
    if req.with_sensor:
        result = await deploy_cell_with_sensor(
            svc, cv, lab_id=lab_id, resolved_specs=specs, deployment_name=_CV_DEPLOYMENT,
            serial=sensor_serial, server=server_url)
    else:
        result = await deploy_slim_cell(svc, lab_id=lab_id, resolved_specs=specs, server=server_url)
    personas = [CmlPersonaResult(name=p.get("name"), data_ip=p.get("data_ip"), node_id=p.get("node_id"))
                for p in result.get("personas", [])]
    msg = ("Deploying off-box — nodes take a few minutes to boot, install the runtime, "
           "and come online. Watch the lab in CML.")
    return CmlDeployResponse(lab_id=lab_id, lab_title=title, personas=personas,
                             sensor_serial=sensor_serial, message=msg)


async def _cml_base_url(db) -> str:
    from app.api.routes.cml import get_cml_settings
    return (await get_cml_settings(db))[0] or ""


@router.get("/cml/labs", response_model=CmlLabListResponse)
async def cml_labs(db: DBSession, _user: CurrentUser) -> CmlLabListResponse:
    """List off-box (CML) Mimic labs (titled 'Mimic: …')."""
    svc, _ = await _cml_service(db)
    base = (await _cml_base_url(db)).rstrip("/")
    labs = await svc.list_labs()
    items = [CmlLabItem(lab_id=l.id, title=l.title, state=l.state, node_count=l.node_count,
                        cml_url=f"{base}/lab/{l.id}" if base else "")
             for l in labs if l.title.startswith(_CML_LAB_PREFIX)]
    return CmlLabListResponse(items=items)


@router.get("/cml/labs/{lab_id}", response_model=CmlLabDetail)
async def cml_lab_detail(lab_id: str, db: DBSession, _user: CurrentUser) -> CmlLabDetail:
    """One off-box lab's personas + live status — so you can pull it up in-app
    (and open it in CML). Persona liveness comes from the check-in registry."""
    from app.api.routes.agent_install import _MIMIC_CHECKINS
    svc, _ = await _cml_service(db)
    base = (await _cml_base_url(db)).rstrip("/")
    lab = await svc.get_lab(lab_id)
    nodes_raw = await svc._request("GET", f"/labs/{lab_id}/nodes", params={"data": "true"})  # noqa: SLF001
    # Persona check-ins are keyed by the original name; match by slug to the CML
    # node label (which the deploy set to the persona's slug).
    ci_by_slug = {scaffold_slug(k): v for k, v in _MIMIC_CHECKINS.items()}
    infra = {"unmanaged_switch", "external_connector", "iosvl2"}
    nodes = []
    for n in nodes_raw or []:
        if not isinstance(n, dict) or n.get("node_definition") in infra:
            continue
        ci = ci_by_slug.get(n.get("label", ""), {})
        nodes.append(CmlLabNode(
            name=n.get("label", ""), node_definition=n.get("node_definition", ""),
            state=n.get("state", "UNKNOWN"),
            up=ci.get("up") == "1", listening=ci.get("listening") == "1"))
    return CmlLabDetail(
        lab_id=lab_id, title=lab.title if lab else "", state=lab.state if lab else "UNKNOWN",
        cml_url=f"{base}/lab/{lab_id}" if base else "", nodes=nodes)


@router.delete("/cml/labs/{lab_id}", response_model=CmlTeardownResponse)
async def cml_teardown(lab_id: str, db: DBSession, _admin: AdminUser) -> CmlTeardownResponse:
    """Tear down an off-box Mimic lab: stop+wipe+delete the CML lab and remove its
    CV sensor object (serial stored in the lab description)."""
    svc, _ = await _cml_service(db)
    serial = None
    try:
        lab = await svc._request("GET", f"/labs/{lab_id}")  # noqa: SLF001
        desc = (lab or {}).get("description", "") if isinstance(lab, dict) else ""
        if "sensor:" in desc:
            serial = desc.split("sensor:", 1)[1].split()[0]
    except Exception:  # noqa: BLE001
        pass
    for method, path in (("PUT", f"/labs/{lab_id}/stop"), ("PUT", f"/labs/{lab_id}/wipe"),
                         ("DELETE", f"/labs/{lab_id}")):
        try:
            await svc._request(method, path)  # noqa: SLF001
            await asyncio.sleep(2)
        except Exception:  # noqa: BLE001 — best-effort; keep going through the sequence
            pass
    if serial:
        try:
            cv = await _cv_service(db)
            s = await cv.find_sensor_by_serial(serial)
            if s:
                await cv.delete_sensor(s["id"])
        except Exception:  # noqa: BLE001
            pass
    return CmlTeardownResponse(lab_id=lab_id, message="Torn down.")


def scaffold_slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-") or "cell"
