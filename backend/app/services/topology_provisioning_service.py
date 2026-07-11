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


async def status(db, scenario_id: str) -> dict[str, Any]:
    """List the member labs of this scenario's topology deployment (live state)."""
    prefix = group_prefix(scenario_id)
    labs = await local_sensor_service.list_labs(db)
    members = [lab for lab in labs if (lab.get("name") or "").startswith(prefix)]
    return {
        "scenario_id": scenario_id,
        "sensor_count": len(members),
        "members": members,
    }


async def teardown(db, scenario_id: str) -> dict[str, Any]:
    """Tear down every member lab of this scenario's topology deployment."""
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
