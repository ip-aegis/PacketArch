# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unified one-shot teardown for a scenario's deployment.

Whatever a scenario was deployed as — a single agent, a new Local Lab, or a
multi-sensor topology — this tears the whole thing down in one call: stops the
run, removes the AgentDeployment rows, tears down the sensor labs it owns, AND
deletes the Cyber Vision objects PacketArch created for it (preset, zone
groups, networks, org-hierarchy levels). One button, all deploy types.

Lab safety: only labs unambiguously attributed to the scenario are removed
(the topology member labs, named by ``group_prefix``). Un-attributed labs a
user set up by hand (e.g. a persistent Local Lab they deploy various scenarios
to) are NOT auto-removed — the model has no scenario link to prove ownership.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


async def teardown_scenario_deployment(db, scenario_id: str) -> dict[str, Any]:
    """Tear down everything a scenario was deployed as. Idempotent + best-effort:
    a failure in one step is logged and the rest proceed."""
    from sqlalchemy import select

    from app.models.scenario import Scenario
    from app.models.traffic_agent import AgentDeployment
    from app.services import local_sensor_service, topology_provisioning_service
    from app.services.agent_manager import agent_manager

    scenario = await db.get(Scenario, uuid.UUID(scenario_id))
    summary: dict[str, Any] = {
        "scenario_id": scenario_id,
        "type": "none",
        "deployments_removed": 0,
        "labs_torn_down": [],
        "cv": None,
        "protected_labs": [],
    }

    # 1) Cyber Vision cleanup FIRST — it reads the cyber_vision state (preset /
    #    group / network / OH-level ids) off the scenario, which later steps
    #    reset. Deletes those objects on the Center. Never raises.
    if scenario and (scenario.definition or {}).get("cyber_vision"):
        try:
            from app.services.cv_provisioning_service import teardown_cv_provisioning

            summary["cv"] = await teardown_cv_provisioning(db, scenario)
        except Exception:
            logger.exception("unified teardown: CV cleanup failed for %s", scenario_id)

    # 2) Topology deployment? Its member labs are named by group_prefix — the
    #    topology teardown stops the conductor, removes the AgentDeployment,
    #    tears down every member lab, and resets the CV state.
    prefix = topology_provisioning_service.group_prefix(scenario_id)
    labs = await local_sensor_service.list_labs(db)
    topo_members = [lab for lab in labs if (lab.get("name") or "").startswith(prefix)]

    if topo_members:
        summary["type"] = "topology"
        res = await topology_provisioning_service.teardown(db, scenario_id)
        summary["labs_torn_down"] = res.get("torn_down", [])
        return summary

    # 3) Standard deployment(s): stop the run + drop the AgentDeployment rows.
    summary["type"] = "standard"
    try:
        await agent_manager.stop_scenario(scenario_id)
    except Exception:
        logger.exception("unified teardown: stop_scenario failed for %s", scenario_id)

    deps = (
        await db.execute(
            select(AgentDeployment).where(AgentDeployment.scenario_id == uuid.UUID(scenario_id))
        )
    ).scalars().all()

    # A local-lab-backed agent flags a lab that COULD be torn down, but with no
    # scenario link on the lab we can't tell a dedicated deploy-lab from a
    # hand-built persistent one — so we report it as protected, not removed.
    from app.models.traffic_agent import TrafficAgent

    for dep in deps:
        agent = await db.get(TrafficAgent, dep.agent_id)
        if agent and agent.local_lab_id:
            summary["protected_labs"].append(
                {"lab_id": str(agent.local_lab_id), "agent_name": agent.name}
            )
        await db.delete(dep)
        summary["deployments_removed"] += 1
    await db.commit()

    # 4) Reset the scenario's CV provisioning state so a redeploy re-provisions
    #    cleanly (topology path already did this on its own teardown).
    if scenario and (scenario.definition or {}).get("cyber_vision"):
        try:
            from sqlalchemy.orm.attributes import flag_modified

            definition = dict(scenario.definition)
            definition.pop("cyber_vision", None)
            scenario.definition = definition
            flag_modified(scenario, "definition")
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("unified teardown: resetting CV state failed for %s", scenario_id)

    return summary
