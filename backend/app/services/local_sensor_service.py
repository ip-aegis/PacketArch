# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Local sensor lab service.

Orchestrates app-managed on-box labs by mirroring the CML build-lab workflow:
parse the operator-pasted CV sensor compose, mint an agent token, persist the
desired LocalLab + TrafficAgent rows, and hand a spec to the privileged
host-agent (via the shared-volume file-queue) which does the actual host work.

Reuses, verbatim:
  - CMLService.parse_sensor_compose()  (token/serial/image/registry)
  - agents.generate_agent_token / hash_token
The backend never touches the host — see services/host_agent_client.py.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select

from app.api.routes.agents import generate_agent_token, hash_token
from app.core.exceptions import ConflictError, ExternalServiceError, ValidationError
from app.models.local_lab import LocalLab
from app.models.settings import SystemSetting
from app.models.traffic_agent import TrafficAgent
from app.services import host_agent_client, local_lab_naming
from app.services.cml_service import CMLService

logger = logging.getLogger(__name__)


async def _resolve_server_url(db) -> str:
    """The URL the on-box agent phones home to. Site FQDN if set, else the local
    nginx (the agent runs host-networked, so localhost:443 reaches it)."""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "site.fqdn"))
    row = result.scalar_one_or_none()
    fqdn = (row.value if row else "") or ""
    if fqdn:
        return fqdn if fqdn.startswith("http") else f"https://{fqdn}"
    return "https://localhost"


def _spec_from_lab(lab: LocalLab, *, agent_token: str, agent_name: str,
                   server_url: str, registry: str | None) -> dict:
    """Build the host-agent spec dict from a persisted LocalLab row."""
    slug = lab.slug
    return {
        "slug": slug,
        "name": lab.name,
        "gen_if": lab.gen_if,
        "mon_if": lab.mon_if,
        "mtu": 1500,
        "registry": registry or "",
        "sensor_compose": lab.sensor_compose,
        "sensor_container": local_lab_naming.sensor_container(slug),
        "agent_container": local_lab_naming.agent_container(slug),
        "agent_token": agent_token,
        "agent_name": agent_name,
        "server_url": server_url,
        "insecure": True,  # on-box backend uses a self-signed cert
    }


async def build_lab(db, *, name: str, sensor_compose: str,
                    agent_name: str | None, created_by_id: uuid.UUID | None) -> dict:
    """Create a local sensor lab: persist desired state + queue host provisioning.

    Returns a dict suitable for LocalLabBuildResponse. The agent token is shown
    only once (in the return value); only its hash is stored.
    """
    if not host_agent_client.is_available():
        raise ExternalServiceError(
            service="host_agent",
            message="The host-agent is not available (its shared state volume isn't "
                    "mounted on the backend). Local sensor labs require the host-agent service.",
        )

    parsed = CMLService.parse_sensor_compose(sensor_compose)
    if not parsed.get("token") or not parsed.get("serial"):
        raise ValidationError(
            "Could not parse the CV sensor compose. Expected 'image:', "
            "'SERIAL_NUMBER=', and 'PROVISIONING_TOKEN=' (paste the full YAML CV gives you)."
        )

    # Name uniqueness (friendly error before hitting the DB constraint).
    existing = await db.execute(select(LocalLab).where(LocalLab.name == name))
    if existing.scalar_one_or_none():
        raise ConflictError(f"A local lab named '{name}' already exists.")

    lab_id = uuid.uuid4()
    slug = local_lab_naming.make_slug(lab_id)
    resolved_agent_name = agent_name or local_lab_naming.agent_name_default(slug)

    # Agent name uniqueness (TrafficAgent.name is unique).
    dup = await db.execute(select(TrafficAgent).where(TrafficAgent.name == resolved_agent_name))
    if dup.scalar_one_or_none():
        raise ConflictError(f"An agent named '{resolved_agent_name}' already exists.")

    token = generate_agent_token()
    agent = TrafficAgent(
        name=resolved_agent_name,
        description="Provisioned as part of a local sensor lab",
        default_interface=local_lab_naming.gen_if(slug),
        token_hash=hash_token(token),
        local_lab_id=str(lab_id),
        created_by_id=created_by_id,
    )
    db.add(agent)
    await db.flush()  # get agent.id

    lab = LocalLab(
        id=lab_id,
        name=name,
        slug=slug,
        agent_id=agent.id,
        sensor_serial=parsed.get("serial"),
        registry=parsed.get("registry"),
        sensor_compose=sensor_compose,
        gen_if=local_lab_naming.gen_if(slug),
        mon_if=local_lab_naming.mon_if(slug),
        state="provisioning",
        created_by_id=created_by_id,
    )
    db.add(lab)
    await db.commit()
    await db.refresh(lab)

    server_url = await _resolve_server_url(db)
    spec = _spec_from_lab(lab, agent_token=token, agent_name=resolved_agent_name,
                          server_url=server_url, registry=parsed.get("registry"))
    try:
        host_agent_client.submit_build(spec)
    except Exception as e:  # noqa: BLE001
        logger.exception("failed to queue host-agent build for lab %s", slug)
        lab.state = "error"
        lab.status_detail = f"failed to queue provisioning: {e}"
        await db.commit()
        raise ExternalServiceError(service="host_agent", message=str(e), original_error=e)

    return {
        "success": True,
        "message": "Local sensor lab queued for provisioning.",
        "lab_id": str(lab.id),
        "slug": slug,
        "agent_id": str(agent.id),
        "agent_token": token,
        "sensor_serial": parsed.get("serial"),
        "state": lab.state,
        "warnings": [],
    }


def _merge_live_status(item: dict, slug: str) -> dict:
    """Overlay the host-agent's live status file onto a LocalLab dict."""
    live = host_agent_client.read_status(slug)
    if live:
        item["state"] = live.get("state", item["state"])
        item["stage"] = live.get("stage")
        item["percent"] = live.get("percent")
        item["resources"] = live.get("resources")
        if live.get("message"):
            item["status_detail"] = live["message"]
    return item


async def list_labs(db) -> list[dict]:
    """All local labs, each enriched with live host-agent status + agent state."""
    result = await db.execute(select(LocalLab))
    labs = result.scalars().all()
    # Map agent_id -> agent
    agent_ids = [lab.agent_id for lab in labs if lab.agent_id]
    agents = {}
    if agent_ids:
        ar = await db.execute(select(TrafficAgent).where(TrafficAgent.id.in_(agent_ids)))
        agents = {a.id: a for a in ar.scalars().all()}
    items = []
    for lab in labs:
        a = agents.get(lab.agent_id)
        item = {
            "lab_id": str(lab.id),
            "name": lab.name,
            "slug": lab.slug,
            "state": lab.state,
            "status_detail": lab.status_detail,
            "agent_id": str(lab.agent_id) if lab.agent_id else None,
            "agent_name": a.name if a else None,
            "agent_status": a.status if a else None,
            "sensor_serial": lab.sensor_serial,
            "gen_if": lab.gen_if,
            "mon_if": lab.mon_if,
            "stage": None,
            "percent": None,
            "resources": None,
        }
        items.append(_merge_live_status(item, lab.slug))
    return items


async def get_lab(db, lab_id: str) -> dict | None:
    result = await db.execute(select(LocalLab).where(LocalLab.id == uuid.UUID(lab_id)))
    lab = result.scalar_one_or_none()
    if not lab:
        return None
    a = None
    if lab.agent_id:
        ar = await db.execute(select(TrafficAgent).where(TrafficAgent.id == lab.agent_id))
        a = ar.scalar_one_or_none()
    item = {
        "lab_id": str(lab.id),
        "name": lab.name,
        "slug": lab.slug,
        "state": lab.state,
        "status_detail": lab.status_detail,
        "agent_id": str(lab.agent_id) if lab.agent_id else None,
        "agent_name": a.name if a else None,
        "agent_status": a.status if a else None,
        "sensor_serial": lab.sensor_serial,
        "gen_if": lab.gen_if,
        "mon_if": lab.mon_if,
        "stage": None,
        "percent": None,
        "resources": None,
    }
    return _merge_live_status(item, lab.slug)


async def teardown_lab(db, lab_id: str) -> dict:
    """Full delete (UX ↔ backend in sync): queue host teardown, then delete the
    LocalLab row and its agent. The host-agent removes veth + containers + spec
    and drops the registry trust if unused."""
    result = await db.execute(select(LocalLab).where(LocalLab.id == uuid.UUID(lab_id)))
    lab = result.scalar_one_or_none()
    if not lab:
        raise ValidationError("Local lab not found.")

    slug = lab.slug
    if host_agent_client.is_available():
        try:
            host_agent_client.submit_teardown(slug)
        except Exception:  # noqa: BLE001 — proceed with DB delete regardless
            logger.exception("failed to queue host-agent teardown for %s", slug)

    # Delete the agent row (full delete) then the lab row.
    if lab.agent_id:
        ar = await db.execute(select(TrafficAgent).where(TrafficAgent.id == lab.agent_id))
        agent = ar.scalar_one_or_none()
        if agent:
            await db.delete(agent)
    await db.delete(lab)
    await db.commit()
    return {"success": True, "message": f"Local lab '{slug}' torn down and removed."}
