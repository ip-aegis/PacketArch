# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Local sensor lab service.

Orchestrates app-managed on-box labs: auto-provision a CV docker sensor via
the Cyber Vision API (deployment token -> per-sensor JWT), synthesize the
compose CV's own GUI would have generated, mint an agent token, persist the
desired LocalLab + TrafficAgent rows, and hand a spec to the privileged
host-agent (via the shared-volume file-queue) which does the actual host work.

The host-agent's `hostops.rewrite_sensor_compose()` is tolerant of any
well-formed compose (it only cares "is there a macvlan network" / "what's the
service image") — it doesn't care whether the YAML was pasted by a human or
synthesized here, so this module owns 100% of the CV-provisioning change; the
host-agent needed zero modifications.

Reuses, verbatim: agents.generate_agent_token / hash_token.
The backend never touches the host — see services/host_agent_client.py.
"""

from __future__ import annotations

import logging
import uuid

import yaml
from sqlalchemy import select

from app.core.exceptions import ConflictError, ExternalServiceError, ValidationError
from app.models.local_lab import LocalLab
from app.models.settings import SystemSetting
from app.models.traffic_agent import TrafficAgent
from app.services import host_agent_client, local_lab_naming
from app.services.agent_tokens import generate_agent_token, hash_token
from app.services.cyber_vision_service import CyberVisionService, cv_service_from_settings

logger = logging.getLogger(__name__)

# Headroom left on a deployment token's maxUsageCount before rotating to a
# freshly-suffixed one, so a long-lived install cycling many labs doesn't hit
# the cap mid-mint.
_DEPLOYMENT_TOKEN_HEADROOM = 5


async def _resolve_server_url(db) -> str:
    """The URL the on-box local-sensor agent phones home to: loopback by default.

    The agent runs host-networked on the SAME host as the backend, so
    https://127.0.0.1:443 reaches nginx directly. We must NOT default to
    site.fqdn here: that is the operator/browser-facing name and is frequently
    unresolvable or unreachable from INSIDE the appliance (no internal DNS
    record for it, or a public name that NAT-hairpins). Using it silently breaks
    agent registration — the agent dials wss://<fqdn>/ws/agent, the name doesn't
    resolve, and it never connects. Loopback is DNS-free and always works; SSL
    verification is disabled for the on-box agent (insecure=True), so the cert
    CN mismatch on 127.0.0.1 is irrelevant.

    Escape hatch: an operator with an unusual topology can pin an explicit URL
    via the `local_sensor.server_url` setting; otherwise loopback is used.
    """
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "local_sensor.server_url")
    )
    row = result.scalar_one_or_none()
    override = (row.value if row else "") or ""
    if override:
        return override if override.startswith("http") else f"https://{override}"
    return "https://127.0.0.1"


async def _resolve_cv_deployment_name(db, cv: CyberVisionService) -> str:
    """Per-install CV deployment-token name: lazily generated once and
    persisted (mirrors the `local_sensor.server_url` setting pattern above),
    so two PacketArch instances pointed at the same CV Center never collide
    on a shared hardcoded name. Rotates to a numbered suffix if the current
    token is near its usage cap (deployment tokens aren't single-use — CV
    reports `maxUsageCount`/`usageCount` — but they're finite and nothing
    decrements them when a lab is torn down)."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "local_sensor.cv_deployment_name")
    )
    row = result.scalar_one_or_none()
    base_name = (row.value if row else "") or ""
    if not base_name:
        base_name = f"packetarch-{uuid.uuid4().hex[:8]}"
        if row:
            row.value = base_name
        else:
            db.add(SystemSetting(key="local_sensor.cv_deployment_name", value=base_name))
        await db.flush()

    name = base_name
    suffix = 1
    while True:
        deployment = await cv.create_deployment_token(name)
        usage = deployment.get("usageCount", 0)
        cap = deployment.get("maxUsageCount", 100)
        if usage < cap - _DEPLOYMENT_TOKEN_HEADROOM:
            return name
        suffix += 1
        name = f"{base_name}-{suffix}"


def _synthesize_sensor_compose(*, image: str, serial: str, jwt: str) -> str:
    """Build a CV docker-sensor compose matching CV's own GUI-generated shape
    (confirmed against a real, redacted sample — NOT the internal doc's
    `perf_bench` example, which is a different/simpler lab tool): a routable
    bridge "collection" network ordered BEFORE a gatewayless macvlan "capture"
    network. `hostops.rewrite_sensor_compose()` relies on that ordering (a
    previously-debugged bug: swap them and the macvlan wins the default-route
    slot, leaving the sensor unable to reach the Center) and forces
    `container_name`/`pull_policy`/the macvlan `driver_opts.parent` itself —
    those fields here are placeholders that get overwritten downstream.
    """
    doc = {
        "services": {
            "sensor": {
                "image": image,
                "container_name": "sensor",
                "restart": "always",
                "pull_policy": "always",
                "sysctls": [
                    "net.ipv4.ip_forward=0",
                    "net.ipv6.conf.all.forwarding=0",
                ],
                "environment": [
                    f"SERIAL_NUMBER={serial}",
                    f"PROVISIONING_TOKEN={jwt}",
                ],
                "cap_add": ["NET_ADMIN"],
                "networks": {
                    "ccv-network-0-collection": {},
                    "ccv-network-capture-1": {},
                },
                "volumes": ["ccv-volume-1:/data"],
            }
        },
        "networks": {
            "ccv-network-0-collection": {
                "name": "ccv-network-0-collection",
                "driver": "bridge",
            },
            "ccv-network-capture-1": {
                "name": "ccv-network-capture-1",
                "driver": "macvlan",
                "driver_opts": {
                    "macvlan_mode": "passthru",
                    "parent": "placeholder",
                },
            },
        },
        "volumes": {"ccv-volume-1": {}},
    }
    return yaml.safe_dump(doc, sort_keys=False)


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


async def build_lab(db, *, name: str,
                    agent_name: str | None, created_by_id: uuid.UUID | None,
                    sensor_label: str | None = None) -> dict:
    """Create a local sensor lab: auto-provision a CV sensor, persist desired
    state, and queue host provisioning.

    Returns a dict suitable for LocalLabBuildResponse. The agent token is shown
    only once (in the return value); only its hash is stored.
    """
    if not host_agent_client.is_available():
        raise ExternalServiceError(
            service="host_agent",
            message="The host-agent is not available (its shared state volume isn't "
                    "mounted on the backend). Local sensor labs require the host-agent service.",
        )

    cv = await cv_service_from_settings(db)
    if cv is None:
        raise ValidationError(
            "Cyber Vision isn't configured. Configure it under Settings > Cyber Vision "
            "before creating a local sensor lab — auto-provisioning needs it."
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

    # Mint the CV provisioning JWT as late as possible (right before persist +
    # queueing the host-agent build) to minimize the window between minting
    # and the host-agent actually running `compose up`.
    # The CV sensor serial is what shows in the Center; derive it from a
    # human-readable label when the caller supplies one (topology deploys pass
    # the zone name so the sensor reads e.g. "cell1-cnc-<slug>" instead of the
    # lab name truncated to "topo-<scn>-c-<slug>").
    serial = local_lab_naming.sensor_serial(sensor_label or name, slug)
    try:
        deployment_name = await _resolve_cv_deployment_name(db, cv)
        jwt = await cv.mint_sensor_jwt(deployment_name, serial)
        image = cv.sensor_image_ref()
    except Exception as e:  # noqa: BLE001
        raise ExternalServiceError(
            service="cyber_vision",
            message=f"Failed to provision a Cyber Vision sensor: {e}",
            original_error=e,
        )
    finally:
        await cv.close()

    registry = image.rsplit("/", 1)[0]
    sensor_compose = _synthesize_sensor_compose(image=image, serial=serial, jwt=jwt)

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
        sensor_serial=serial,
        registry=registry,
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
                          server_url=server_url, registry=registry)
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
        "sensor_serial": serial,
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

    # Best-effort: remove the sensor object from the CV Center too, so labs
    # don't leave orphaned sensor entries behind. Non-fatal — a stale/
    # reconfigured CV connection (or a lab built via the old paste-a-compose
    # flow against a different Center) just no-ops with a logged warning,
    # same as the host-agent teardown call above.
    if lab.sensor_serial:
        cv = await cv_service_from_settings(db)
        if cv is not None:
            try:
                sensor = await cv.find_sensor_by_serial(lab.sensor_serial)
                if sensor and sensor.get("id"):
                    await cv.delete_sensor(sensor["id"])
            except Exception:  # noqa: BLE001 — proceed with DB delete regardless
                logger.warning(
                    "failed to delete CV sensor for lab %s (serial %s)",
                    slug, lab.sensor_serial, exc_info=True,
                )
            finally:
                await cv.close()

    # Delete the agent row (full delete) then the lab row.
    if lab.agent_id:
        ar = await db.execute(select(TrafficAgent).where(TrafficAgent.id == lab.agent_id))
        agent = ar.scalar_one_or_none()
        if agent:
            await db.delete(agent)
    await db.delete(lab)
    await db.commit()
    return {"success": True, "message": f"Local lab '{slug}' torn down and removed."}
