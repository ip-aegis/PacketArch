# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cisco Modeling Labs (CML) routes: connection settings + agent auto-deploy.

Mirrors the Cyber Vision route module. Settings live in system_settings
(password encrypted); the deploy route reuses PacketArch's existing agent
registration (token + install.sh) and wires up a CML Ubuntu node via cloud-init.
"""

import logging

from sqlalchemy import or_, select

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.core.encryption import decrypt_value, encrypt_value
from app.core.exceptions import ConflictError, ExternalServiceError, NotFoundError, ValidationError
from app.services.agent_tokens import generate_agent_token, hash_token
from app.models.settings import SystemSetting
from app.models.traffic_agent import TrafficAgent
from app.schemas.cml import (
    CMLConnectionStatusResponse,
    CMLDeploymentItem,
    CMLDeploymentListResponse,
    CMLDeployRequest,
    CMLDeployResponse,
    CMLInterfaceResponse,
    CMLLabBuildRequest,
    CMLLabBuildResponse,
    CMLLabListResponse,
    CMLLabResponse,
    CMLNodeListResponse,
    CMLNodeResponse,
    CMLSettingsResponse,
    CMLSettingsUpdate,
    CMLTeardownLabRequest,
    CMLTeardownLabResponse,
    CMLTestConnectionRequest,
    CMLTestConnectionResponse,
    CMLUndeployRequest,
    CMLUndeployResponse,
)
from app.services.cml_service import CMLService

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cml", tags=["CML"])

_SETTING_KEYS = [
    "cml_url",
    "cml_username",
    "cml_password",
    "cml_verify_ssl",
    "cml_packetarch_server_url",
]


async def get_cml_settings(db) -> tuple[str | None, str | None, str | None, bool, str | None]:
    """Read and decrypt CML settings. Returns (url, username, password, verify_ssl, server_url)."""
    settings: dict[str, str | None] = {}
    result = await db.execute(select(SystemSetting).where(SystemSetting.key.in_(_SETTING_KEYS)))
    for setting in result.scalars().all():
        if setting.key == "cml_password" and setting.value:
            settings[setting.key] = decrypt_value(setting.value)
        else:
            settings[setting.key] = setting.value

    url = settings.get("cml_url")
    username = settings.get("cml_username")
    password = settings.get("cml_password")
    verify_ssl = (settings.get("cml_verify_ssl") or "false").lower() == "true"
    server_url = settings.get("cml_packetarch_server_url")
    return url, username, password, verify_ssl, server_url


async def get_cml_service(db) -> CMLService:
    """Build a CMLService from stored settings."""
    url, username, password, verify_ssl, _ = await get_cml_settings(db)
    if not url or not username or not password:
        raise ValidationError("CML is not configured. Please set URL, username, and password in settings.")
    return CMLService(url, username, password, verify_ssl)


async def _resolve_phone_home_url(db) -> str:
    """Resolve the URL a deployed agent should phone home to."""
    _, _, _, _, server_url = await get_cml_settings(db)
    if server_url:
        return server_url
    # Fall back to the configured site FQDN.
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "site.fqdn"))
    setting = result.scalar_one_or_none()
    fqdn = (setting.value if setting else "") or ""
    if not fqdn:
        raise ValidationError(
            "No phone-home URL: set 'Agent phone-home URL' in CML settings, or configure the site FQDN."
        )
    if fqdn.startswith("http://") or fqdn.startswith("https://"):
        return fqdn
    return f"https://{fqdn}"


# --- Settings ---------------------------------------------------------------

@router.get("/settings", response_model=CMLSettingsResponse)
async def get_settings(db: DBSession, _admin: AdminUser) -> CMLSettingsResponse:
    """Get CML settings (password masked)."""
    url, username, password, verify_ssl, server_url = await get_cml_settings(db)
    return CMLSettingsResponse(
        cml_url=url or "",
        cml_username=username or "",
        cml_password_set=bool(password),
        cml_verify_ssl=verify_ssl,
        cml_packetarch_server_url=server_url or "",
    )


@router.put("/settings", response_model=CMLSettingsResponse)
async def update_settings(update: CMLSettingsUpdate, db: DBSession, admin: AdminUser) -> CMLSettingsResponse:
    """Update CML settings."""
    updates: dict[str, str] = {}
    if update.cml_url is not None:
        updates["cml_url"] = update.cml_url
    if update.cml_username is not None:
        updates["cml_username"] = update.cml_username
    if update.cml_password is not None and update.cml_password != "":
        updates["cml_password"] = encrypt_value(update.cml_password)
    if update.cml_verify_ssl is not None:
        updates["cml_verify_ssl"] = str(update.cml_verify_ssl).lower()
    if update.cml_packetarch_server_url is not None:
        updates["cml_packetarch_server_url"] = update.cml_packetarch_server_url

    for key, value in updates.items():
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting is None:
            setting = SystemSetting(
                key=key,
                value=value,
                is_secret=(key == "cml_password"),
                category="cml",
                description=f"CML {key.replace('cml_', '').replace('_', ' ')}",
            )
            db.add(setting)
        else:
            setting.value = value
            setting.updated_by_id = admin.id

    await db.commit()
    return await get_settings(db, admin)


@router.get("/status", response_model=CMLConnectionStatusResponse)
async def get_status(db: DBSession, _user: CurrentUser) -> CMLConnectionStatusResponse:
    """Check CML connection status using stored credentials."""
    try:
        service = await get_cml_service(db)
        result = await service.test_connection()
        await service.close()
        return CMLConnectionStatusResponse(
            connected=result.success, message=result.message, version=result.version
        )
    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.exception("Error checking CML status")
        return CMLConnectionStatusResponse(connected=False, message=f"Connection error: {e}")


@router.post("/test-connection", response_model=CMLTestConnectionResponse)
async def test_connection(req: CMLTestConnectionRequest, db: DBSession, _admin: AdminUser) -> CMLTestConnectionResponse:
    """Test a CML connection with supplied credentials."""
    service = CMLService(req.url, req.username, req.password, req.verify_ssl)
    result = await service.test_connection()
    await service.close()
    return CMLTestConnectionResponse(success=result.success, message=result.message, version=result.version)


# --- Labs / nodes (pickers) -------------------------------------------------

@router.get("/labs", response_model=CMLLabListResponse)
async def list_labs(db: DBSession, _user: CurrentUser) -> CMLLabListResponse:
    """List CML labs."""
    service = await get_cml_service(db)
    try:
        labs = await service.list_labs()
    except Exception as e:
        logger.exception("Failed to list CML labs")
        raise ExternalServiceError(service="cml", message=f"Failed to list CML labs: {e}", original_error=e)
    finally:
        await service.close()
    return CMLLabListResponse(items=[
        CMLLabResponse(id=lab.id, title=lab.title, state=lab.state, node_count=lab.node_count, owner=lab.owner)
        for lab in labs
    ])


@router.get("/labs/{lab_id}/nodes", response_model=CMLNodeListResponse)
async def list_lab_nodes(lab_id: str, db: DBSession, _user: CurrentUser) -> CMLNodeListResponse:
    """List nodes in a lab (for the data-attachment element/port pickers)."""
    service = await get_cml_service(db)
    try:
        nodes = await service.list_lab_nodes(lab_id)
    except Exception as e:
        logger.exception("Failed to list nodes for lab %s", lab_id)
        raise ExternalServiceError(service="cml", message=f"Failed to list lab nodes: {e}", original_error=e)
    finally:
        await service.close()
    return CMLNodeListResponse(items=[
        CMLNodeResponse(
            id=n.id, label=n.label, node_definition=n.node_definition, state=n.state,
            is_infrastructure=n.is_infrastructure,
            interfaces=[
                CMLInterfaceResponse(id=i.id, label=i.label, slot=i.slot, is_connected=i.is_connected)
                for i in n.interfaces
            ],
        )
        for n in nodes
    ])


# --- Deploy / undeploy ------------------------------------------------------

@router.post("/deploy", response_model=CMLDeployResponse)
async def deploy(req: CMLDeployRequest, db: DBSession, admin: AdminUser) -> CMLDeployResponse:
    """Register a new agent and auto-deploy it as a node in a CML lab."""
    # 1. agent-name uniqueness
    existing = await db.execute(select(TrafficAgent).where(TrafficAgent.name == req.agent_name))
    if existing.scalar_one_or_none():
        raise ConflictError(
            f"Agent with name '{req.agent_name}' already exists", details={"name": req.agent_name}
        )

    # 2. mint token + create the agent row up front (so the token hashes to it)
    token = generate_agent_token()
    agent = TrafficAgent(
        name=req.agent_name,
        description="Auto-deployed into Cisco Modeling Labs",
        default_interface="ens3",
        token_hash=hash_token(token),
        cml_lab_id=req.lab_id,
        created_by_id=admin.id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # 3. resolve phone-home URL + verify-ssl posture
    _, _, _, verify_ssl, _ = await get_cml_settings(db)
    try:
        server_url = await _resolve_phone_home_url(db)
    except ValidationError:
        await db.delete(agent)
        await db.commit()
        raise

    # 4. orchestrate the CML deploy
    service = await get_cml_service(db)
    try:
        result = await service.deploy_agent(
            lab_id=req.lab_id,
            agent_name=req.agent_name,
            agent_token=token,
            packetarch_server_url=server_url,
            verify_server_ssl=verify_ssl,
            data_attachment=req.data_attachment.model_dump() if req.data_attachment else None,
            start_node=req.start_node,
            cpus=req.cpus,
            ram_mb=req.ram_mb,
        )
    finally:
        await service.close()

    # 5. persist linkage on success, roll back the orphan agent on failure
    if not result.success:
        await db.delete(agent)
        await db.commit()
        raise ExternalServiceError(service="cml", message=result.message)

    agent.cml_node_id = result.node_id
    agent.cml_node_label = result.node_label
    await db.commit()

    return CMLDeployResponse(
        success=True,
        message=result.message,
        agent_id=str(agent.id),
        agent_token=token,
        lab_id=req.lab_id,
        node_id=result.node_id,
        node_label=result.node_label,
        data_wired=result.data_wired,
        mgmt_wired=result.mgmt_wired,
        started=result.started,
        warnings=result.warnings,
    )


@router.post("/undeploy", response_model=CMLUndeployResponse)
async def undeploy(req: CMLUndeployRequest, db: DBSession, _admin: AdminUser) -> CMLUndeployResponse:
    """Tear down a CML-deployed agent: remove the node and/or deactivate the agent."""
    result = await db.execute(select(TrafficAgent).where(TrafficAgent.id == req.agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise NotFoundError(f"Agent {req.agent_id} not found")

    node_removed = False
    if req.remove_cml_node and agent.cml_lab_id and agent.cml_node_id:
        service = await get_cml_service(db)
        try:
            await service.undeploy_node(agent.cml_lab_id, agent.cml_node_id)
            node_removed = True
            agent.cml_node_id = None
        except Exception as e:
            logger.exception("Failed to remove CML node for agent %s", req.agent_id)
            await service.close()
            raise ExternalServiceError(service="cml", message=f"Failed to remove CML node: {e}", original_error=e)
        await service.close()

    agent_deactivated = False
    if req.deactivate_agent:
        agent.is_active = False
        agent_deactivated = True

    await db.commit()
    return CMLUndeployResponse(
        success=True,
        message="Undeploy complete",
        cml_node_removed=node_removed,
        agent_deactivated=agent_deactivated,
    )


@router.post("/build-lab", response_model=CMLLabBuildResponse)
async def build_lab(req: CMLLabBuildRequest, db: DBSession, admin: AdminUser) -> CMLLabBuildResponse:
    """Build a self-contained lab: agent + IOSvL2 SPAN switch + CV sensor host.

    Takes the docker-compose YAML CV generates for a docker sensor; PacketArch
    parses the serial + registry out of it and embeds the compose in the sensor
    node's cloud-init.
    """
    parsed = CMLService.parse_sensor_compose(req.sensor_compose)
    sensor_serial = req.sensor_serial or parsed.get("serial")
    registry = parsed.get("registry")
    if not parsed.get("token") or not sensor_serial or not registry:
        raise ValidationError(
            "Could not parse the CV docker-compose. It must contain 'image:', "
            "'SERIAL_NUMBER=', and 'PROVISIONING_TOKEN=' (paste the full YAML CV gives you)."
        )

    # Agent-name uniqueness, then mint token + create the agent row up front.
    existing = await db.execute(select(TrafficAgent).where(TrafficAgent.name == req.agent_name))
    if existing.scalar_one_or_none():
        raise ConflictError(
            f"Agent with name '{req.agent_name}' already exists", details={"name": req.agent_name}
        )
    token = generate_agent_token()
    agent = TrafficAgent(
        name=req.agent_name,
        description="Auto-deployed into a PacketArch-built CML lab",
        default_interface="ens3",
        token_hash=hash_token(token),
        created_by_id=admin.id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    _, _, _, verify_ssl, _ = await get_cml_settings(db)
    try:
        server_url = await _resolve_phone_home_url(db)
    except ValidationError:
        await db.delete(agent)
        await db.commit()
        raise

    service = await get_cml_service(db)
    try:
        result = await service.build_lab(
            lab_name=req.lab_name,
            agent_name=req.agent_name,
            agent_token=token,
            packetarch_server_url=server_url,
            verify_server_ssl=verify_ssl,
            sensor_compose=req.sensor_compose,
            sensor_serial=sensor_serial,
            registry=registry,
            start_lab=req.start_lab,
            agent_cpus=req.agent_cpus,
            agent_ram_mb=req.agent_ram_mb,
            sensor_cpus=req.sensor_cpus,
            sensor_ram_mb=req.sensor_ram_mb,
        )
        if not result.success:
            # Best-effort cleanup of a partially-built lab.
            if result.lab_id:
                try:
                    await service.teardown_lab(result.lab_id)
                except Exception:
                    logger.exception("Cleanup of partial lab %s failed", result.lab_id)
            await db.delete(agent)
            await db.commit()
            raise ExternalServiceError(service="cml", message=result.message)
    finally:
        await service.close()

    agent.cml_lab_id = result.lab_id
    agent.cml_node_id = result.agent_node_id
    agent.cml_node_label = req.agent_name
    await db.commit()

    return CMLLabBuildResponse(
        success=True,
        message=result.message,
        lab_id=result.lab_id,
        agent_id=str(agent.id),
        agent_token=token,
        agent_node_id=result.agent_node_id,
        switch_node_id=result.switch_node_id,
        sensor_node_id=result.sensor_node_id,
        sensor_serial=result.sensor_serial,
        started=result.started,
        warnings=result.warnings,
    )


@router.post("/teardown-lab", response_model=CMLTeardownLabResponse)
async def teardown_lab(req: CMLTeardownLabRequest, db: DBSession, _admin: AdminUser) -> CMLTeardownLabResponse:
    """Stop, wipe, and delete a PacketArch-built lab; deactivate its agent."""
    service = await get_cml_service(db)
    try:
        await service.teardown_lab(req.lab_id)
    except Exception as e:
        logger.exception("Failed to teardown lab %s", req.lab_id)
        await service.close()
        raise ExternalServiceError(service="cml", message=f"Failed to teardown lab: {e}", original_error=e)
    await service.close()

    if req.agent_id:
        result = await db.execute(select(TrafficAgent).where(TrafficAgent.id == req.agent_id))
        agent = result.scalar_one_or_none()
        if agent is not None:
            agent.is_active = False
            agent.cml_node_id = None
            await db.commit()

    return CMLTeardownLabResponse(success=True, message="Lab torn down")


@router.get("/deployments", response_model=CMLDeploymentListResponse)
async def list_deployments(db: DBSession, _user: CurrentUser) -> CMLDeploymentListResponse:
    """List PacketArch agents that were deployed into CML."""
    result = await db.execute(
        select(TrafficAgent).where(
            or_(TrafficAgent.cml_lab_id.isnot(None), TrafficAgent.cml_node_id.isnot(None))
        )
    )
    agents = result.scalars().all()
    return CMLDeploymentListResponse(items=[
        CMLDeploymentItem(
            agent_id=str(a.id),
            agent_name=a.name,
            status=a.status,
            is_active=a.is_active,
            cml_lab_id=a.cml_lab_id,
            cml_node_id=a.cml_node_id,
            cml_node_label=a.cml_node_label,
        )
        for a in agents
    ])
