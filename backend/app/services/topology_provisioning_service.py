# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Multi-sensor topology deployment provisioning ("Advanced Deployment").

Stands up one Local Sensor Lab (agent + CV docker sensor + veth SPAN) per
topology SPAN — one per zone plus the core — by reusing
``local_sensor_service.build_lab`` N+1 times. Member labs are grouped by a
deterministic name prefix (``topo-<scenario8>-``) so no schema migration is
needed; ``status``/``teardown`` operate on that group.

The derived topology (per-zone IE3500 + IE9320 core, gateway-rewritten
per-segment framing) comes from ``topology_planner``; the injection plan +
``span → gen-interface`` map produced here is what a conductor replays onto
each lab's ``pa-gen`` veth so every sensor sees its correctly-framed segment.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.services import local_sensor_service, topology_planner
from app.services.local_lab_naming import make_slug

logger = logging.getLogger(__name__)

# Per-lab CV capture ring buffer (see local_sensor_lab_memory_sizing memory).
LAB_RAM_GB = 1.26


def group_prefix(scenario_id: str) -> str:
    return f"topo-{str(scenario_id)[:8]}-"


def _span_label(span_id: str) -> str:
    """'zone:cell1_cnc' -> 'cell1_cnc', 'core' -> 'core' (name-safe)."""
    label = span_id.split(":", 1)[1] if ":" in span_id else span_id
    return "".join(c if c.isalnum() else "-" for c in label).strip("-")[:40] or "span"


async def _load_scenario(db, scenario_id: str):
    from sqlalchemy import select

    from app.models.scenario import Scenario

    r = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scn = r.scalar_one_or_none()
    if not scn:
        raise NotFoundError("Scenario", scenario_id)
    return scn


async def plan_for(db, scenario_id: str) -> dict[str, Any]:
    """Derive + validate the topology plan for a scenario (raises on invalid)."""
    scn = await _load_scenario(db, scenario_id)
    plan = topology_planner.preview(scn.definition or {}, seed=str(scn.id))
    if not plan.get("valid"):
        errs = "; ".join(e["message"] for e in plan.get("errors", []))
        raise ValidationError(f"Topology plan is invalid: {errs}")
    return plan


def sensor_count(plan: dict[str, Any]) -> int:
    """N zones + 1 core (0 if the plan is single-zone/degenerate)."""
    return len(plan.get("spans", []))


def ram_estimate_gb(plan: dict[str, Any]) -> float:
    return round(sensor_count(plan) * LAB_RAM_GB, 2)


async def preflight(db, scenario_id: str) -> dict[str, Any]:
    """Non-destructive pre-deploy summary: sensor count, RAM, span list."""
    plan = await plan_for(db, scenario_id)
    spans = [s["id"] for s in plan.get("spans", [])]
    return {
        "scenario_id": scenario_id,
        "sensor_count": sensor_count(plan),
        "ram_estimate_gb": ram_estimate_gb(plan),
        "spans": spans,
        "switches": len(plan.get("switches", {})),
        "has_core": plan.get("core") is not None,
        "flow_plans": len(plan.get("flow_plans", {})),
    }


async def provision(db, scenario_id: str, created_by_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Provision one Local Sensor Lab per SPAN (zones + core).

    Returns the deployment summary including the per-span member list with each
    lab's ``gen_if`` (the injection interface for that SPAN). Agent tokens are
    returned once, per lab. Idempotency: refuses if a group already exists for
    this scenario.
    """
    plan = await plan_for(db, scenario_id)
    spans = [s["id"] for s in plan.get("spans", [])]
    if not spans:
        raise ValidationError("Topology has no SPANs to provision (single-zone/degenerate).")

    existing = await status(db, scenario_id)
    if existing["members"]:
        raise ValidationError(
            f"A topology deployment already exists for this scenario "
            f"({len(existing['members'])} labs). Tear it down first."
        )

    prefix = group_prefix(scenario_id)
    members: list[dict[str, Any]] = []
    for span_id in spans:
        role = "core" if span_id == topology_planner.CORE_SPAN else "zone"
        lab_name = f"{prefix}{_span_label(span_id)}"
        built = await local_sensor_service.build_lab(
            db, name=lab_name, agent_name=None, created_by_id=created_by_id
        )
        members.append(
            {
                "span_id": span_id,
                "role": role,
                "lab_id": built["lab_id"],
                "slug": built["slug"],
                "agent_id": built["agent_id"],
                "agent_token": built["agent_token"],
                "gen_if": local_sensor_service.local_lab_naming.gen_if(built["slug"]),
                "sensor_serial": built["sensor_serial"],
            }
        )
        logger.info("topology deploy %s: provisioned lab for span %s", scenario_id, span_id)

    return {
        "scenario_id": scenario_id,
        "sensor_count": len(members),
        "ram_estimate_gb": ram_estimate_gb(plan),
        "members": members,
        "span_interface_map": {m["span_id"]: m["gen_if"] for m in members},
    }


async def build_runtime(db, scenario_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """(augmented_definition, plan) for a topology run — switches injected,
    SNMP coverage wired, isolation off, fully enriched.

    Mirrors both the PCAP path (so live == PCAP) and the normal deploy
    enrichment chain in agent_manager.execute_deployment (so the conductor's
    definition is exactly what a normal deploy would send, plus the injected
    switches). ``execute_deployment`` uses this as its ``definition_override``.
    """
    from app.services import topology_definition_builder
    from app.services.scenario_enrichment import (
        auto_repair_protocols,
        ensure_device_flow_coverage,
        ensure_remote_access_cloud_links,
        repair_flow_protocols,
    )

    scn = await _load_scenario(db, scenario_id)
    definition = {**(scn.definition or {}), "cell_isolation": {"mode": "off"}}
    seed = str(scn.id)

    # Full normal-deploy enrichment first, on the real devices.
    definition = auto_repair_protocols(definition)
    definition = repair_flow_protocols(definition)
    definition = await ensure_remote_access_cloud_links(db, definition)
    definition = await ensure_device_flow_coverage(definition)

    # Derive the topology + inject the IE3500/IE9320 switches, then re-run
    # coverage so the injected switches get their SNMP monitoring flows.
    plan0 = topology_planner.derive_topology(definition, seed=seed).as_dict()
    if not plan0.get("valid"):
        errs = "; ".join(e["message"] for e in plan0.get("errors", []))
        raise ValidationError(f"Topology plan is invalid: {errs}")
    augmented = topology_definition_builder.build_topology_definition(definition, plan0)
    augmented = await ensure_device_flow_coverage(augmented)
    plan = topology_planner.preview(augmented, seed=seed)
    return augmented, plan


# Background deploy-when-ready tasks, held so the event loop doesn't GC them.
_bg_deploys: set = set()


def _core_member(members: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((m for m in members if str(m.get("name", "")).endswith("-core")), None)


def _build_span_map(scenario_id: str, members: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, str]:
    """span_id -> member lab veth, matching each SPAN to its lab by sanitizing
    the span id FORWARD (never reversing the lossy sanitizer)."""
    prefix = group_prefix(scenario_id)
    by_name = {m["name"]: m for m in members}
    out: dict[str, str] = {}
    for span in plan.get("spans", []):
        lab = by_name.get(f"{prefix}{_span_label(span['id'])}")
        if lab and lab.get("gen_if"):
            out[span["id"]] = lab["gen_if"]
    return out


async def deploy(
    db, scenario_id: str, *, provision_cyber_vision: bool = True,
    created_by_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Provision N+1 sensor labs, then (when all are ready) deploy the scenario
    to the core lab's agent as the single conductor THROUGH the normal
    ``execute_deployment`` path — so it gets an AgentDeployment (→ active
    status + live traffic) and full CV provisioning (preset + zone groups + org
    hierarchy), exactly like a normal deploy, plus the multi-sensor injection.
    """
    result = await provision(db, scenario_id, created_by_id=created_by_id)
    # The conductor deploy must run in THIS (backend) process — execute_deployment
    # sends agent WebSocket commands, and those connections live here, not in
    # celery. Fire a background task on the backend loop and hold a ref.
    import asyncio

    task = asyncio.create_task(_deploy_when_ready(scenario_id, provision_cyber_vision))
    _bg_deploys.add(task)
    task.add_done_callback(_bg_deploys.discard)
    result["deploy_pending"] = True
    return result


async def _deploy_when_ready(
    scenario_id: str, provision_cyber_vision: bool,
    *, timeout_s: float = 420.0, poll_s: float = 8.0,
) -> None:
    """Wait for all member labs running + the core agent online, then deploy the
    conductor. Own DB session; never raises (background task)."""
    import asyncio
    import time

    from app.core.database import async_session_maker

    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        try:
            async with async_session_maker() as db:
                members = (await status(db, scenario_id))["members"]
                core = _core_member(members)
                ready = (
                    members
                    and all(m.get("state") == "running" for m in members)
                    and core is not None
                    and core.get("agent_status") == "online"
                )
                if ready:
                    await _conductor_deploy(db, scenario_id, members, provision_cyber_vision)
                    logger.info("topology deploy %s: conductor deployed live", scenario_id)
                    return
        except Exception:
            logger.exception("topology deploy %s: deploy-when-ready iteration failed", scenario_id)
        await asyncio.sleep(poll_s)
    logger.error(
        "topology deploy %s: timed out after %ss waiting for labs to be ready",
        scenario_id, timeout_s,
    )


async def _conductor_deploy(
    db, scenario_id: str, members: list[dict[str, Any]], provision_cyber_vision: bool,
) -> None:
    """Route the single-conductor deploy through the normal execute_deployment."""
    from app.models.traffic_agent import TrafficAgent
    from app.services.agent_manager import agent_manager

    core = _core_member(members)
    if not core or not core.get("agent_id"):
        raise ValidationError("Core conductor lab not found in this deployment.")

    augmented, plan = await build_runtime(db, scenario_id)
    span_map = _build_span_map(scenario_id, members, plan)
    missing = [s["id"] for s in plan.get("spans", []) if s["id"] not in span_map]
    if missing:
        raise ValidationError(f"No provisioned lab for SPANs: {missing}.")

    core_agent = await db.get(TrafficAgent, uuid.UUID(core["agent_id"]))
    scenario = await _load_scenario(db, scenario_id)
    await agent_manager.execute_deployment(
        db,
        agent=core_agent,
        scenario=scenario,
        interface=core.get("gen_if"),
        adaptive_config=None,
        attack_playbook=None,
        cell_isolation_override=None,
        provision_cyber_vision=provision_cyber_vision,
        topology_plan=plan,
        span_interface_map=span_map,
        definition_override=augmented,
    )


async def _deployment_state(db, scenario_id: str) -> str | None:
    """State of the conductor's AgentDeployment for this scenario, if any."""
    from sqlalchemy import select

    from app.models.traffic_agent import AgentDeployment

    r = await db.execute(
        select(AgentDeployment.state)
        .where(AgentDeployment.scenario_id == uuid.UUID(scenario_id))
        .order_by(AgentDeployment.started_at.desc())
        .limit(1)
    )
    return r.scalar_one_or_none()


async def status(db, scenario_id: str) -> dict[str, Any]:
    """List the member labs of this scenario's topology deployment (live state),
    plus the conductor deployment state so the UI can show deploying/active."""
    prefix = group_prefix(scenario_id)
    labs = await local_sensor_service.list_labs(db)
    members = [lab for lab in labs if (lab.get("name") or "").startswith(prefix)]
    all_running = bool(members) and all(m.get("state") == "running" for m in members)
    deployment_state = await _deployment_state(db, scenario_id)
    if deployment_state in ("running", "starting"):
        phase = "active"
    elif members and not all_running:
        phase = "provisioning"
    elif all_running:
        phase = "deploying"  # labs up, conductor deploy pending/settling
    else:
        phase = "none"
    return {
        "scenario_id": scenario_id,
        "sensor_count": len(members),
        "members": members,
        "deployment_state": deployment_state,
        "phase": phase,
    }


async def teardown(db, scenario_id: str) -> dict[str, Any]:
    """Full teardown: stop the conductor, drop its deployment row, remove every
    member lab (containers + veths + sensors + agent rows)."""
    from sqlalchemy import delete

    from app.models.traffic_agent import AgentDeployment
    from app.services.agent_manager import agent_manager

    # 1) Stop the conductor's live injection (best-effort — agent may be gone).
    try:
        await agent_manager.stop_scenario(scenario_id)
    except Exception:
        logger.exception("topology teardown: stop_scenario failed for %s", scenario_id)

    # 1b) Reset the scenario's CV provisioning state so a REDEPLOY re-provisions
    #     from scratch. Otherwise the stale `cyber_vision` block (preset/group
    #     ids from the torn-down run, marked groups_created) makes the next
    #     deploy look already-provisioned and never re-assigns freshly-
    #     discovered devices to groups.
    try:
        from sqlalchemy.orm.attributes import flag_modified

        from app.models.scenario import Scenario

        scn = await db.get(Scenario, uuid.UUID(scenario_id))
        if scn and (scn.definition or {}).get("cyber_vision"):
            definition = dict(scn.definition)
            definition.pop("cyber_vision", None)
            scn.definition = definition
            flag_modified(scn, "definition")
            await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("topology teardown: resetting CV state failed for %s", scenario_id)

    # 2) Drop the AgentDeployment row(s) BEFORE deleting the agents (FK), so the
    #    scenario stops showing as active.
    try:
        await db.execute(
            delete(AgentDeployment).where(AgentDeployment.scenario_id == uuid.UUID(scenario_id))
        )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("topology teardown: removing AgentDeployment failed for %s", scenario_id)

    # 3) Tear down every member lab.
    prefix = group_prefix(scenario_id)
    labs = await local_sensor_service.list_labs(db)
    members = [lab for lab in labs if (lab.get("name") or "").startswith(prefix)]
    results = []
    for lab in members:
        try:
            await local_sensor_service.teardown_lab(db, lab["lab_id"])
            results.append({"lab_id": lab["lab_id"], "name": lab["name"], "ok": True})
        except Exception as e:  # noqa: BLE001 — best-effort; report per-lab
            logger.exception("topology teardown: lab %s failed", lab["lab_id"])
            results.append({"lab_id": lab["lab_id"], "name": lab["name"], "ok": False, "error": str(e)})
    return {"scenario_id": scenario_id, "torn_down": results}
