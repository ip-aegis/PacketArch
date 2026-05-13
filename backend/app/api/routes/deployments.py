# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Agent deployment management routes."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.models.scenario import Scenario
from app.models.traffic_agent import AgentDeployment, TrafficAgent
from app.schemas.deployment import (
    UnifiedDeploymentListResponse,
    UnifiedDeploymentResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deployments", tags=["Deployments"])


@router.get("", response_model=UnifiedDeploymentListResponse)
async def list_deployments(
    db: DBSession,
    _user: CurrentUser,
    scenario_id: UUID | None = None,
    agent_id: UUID | None = None,
    status_filter: str | None = Query(None, description="Filter by status"),
) -> UnifiedDeploymentListResponse:
    """List agent deployments with optional filters.

    This endpoint syncs deployment states with what agents report as running
    to ensure the UI always reflects reality.
    """
    from app.services.agent_manager import agent_manager

    # RESILIENCE: Sync deployment states from all connected agents before listing
    # The agent is the source of truth - if it says a scenario is running, it is.
    # If a row exists, flip it to running. If no row exists at all (the deploy
    # record was deleted but the agent never got STOP, or the table was wiped),
    # synthesise one so the UI can see and manage the orphan run.
    for conn in agent_manager.get_all_connections():
        if not conn.running_scenarios:
            continue
        for scenario_id_str in conn.running_scenarios:
            try:
                scenario_uuid = UUID(scenario_id_str)
            except ValueError:
                logger.debug(f"Invalid scenario id from agent: {scenario_id_str!r}")
                continue
            try:
                # Skip orphan-recovery for scenarios that don't exist anymore.
                scenario_exists = await db.execute(
                    select(Scenario.id).where(Scenario.id == scenario_uuid)
                )
                if scenario_exists.scalar_one_or_none() is None:
                    continue

                result = await db.execute(
                    select(AgentDeployment)
                    .where(
                        AgentDeployment.agent_id == conn.agent_id,
                        AgentDeployment.scenario_id == scenario_uuid,
                    )
                    .order_by(AgentDeployment.started_at.desc())
                    .limit(1)
                )
                deployment = result.scalar_one_or_none()
                if deployment is None:
                    interface = getattr(conn, "interface", None)
                    if not interface:
                        agent_iface_q = await db.execute(
                            select(TrafficAgent.default_interface)
                            .where(TrafficAgent.id == conn.agent_id)
                        )
                        interface = agent_iface_q.scalar_one_or_none()
                    deployment = AgentDeployment(
                        agent_id=conn.agent_id,
                        scenario_id=scenario_uuid,
                        interface=interface,
                        state="running",
                    )
                    db.add(deployment)
                    logger.info(
                        f"Reconciled orphan running scenario "
                        f"{scenario_id_str} on agent {conn.agent_id} — "
                        f"created deployment record"
                    )
                elif deployment.state == "disconnected":
                    # Agent reconnect — auto-restore to running.
                    deployment.state = "running"
                    deployment.stopped_at = None
                    logger.info(
                        f"Synced deployment {deployment.id} on page load: "
                        f"disconnected -> running (agent reconnected)"
                    )
                elif deployment.state in ("stopping", "stopped"):
                    # User asked to stop. The agent still reports the
                    # scenario as running — it hasn't completed shutdown
                    # yet (or the STOP_SCENARIO command was lost). Do
                    # NOT silently re-activate; re-send the stop directly
                    # to THIS agent. Pre-fix this branch flipped state
                    # back to running, which made the UI Stop button
                    # appear broken: every subsequent deployments-page
                    # poll undid the stop.
                    try:
                        await agent_manager.send_command(conn.agent_id, {
                            "type": "STOP_SCENARIO",
                            "scenario_id": scenario_id_str,
                        })
                        logger.info(
                            "Resent STOP_SCENARIO to agent %s for "
                            "deployment %s — page-load reconciliation "
                            "saw agent still running scenario after "
                            "user-initiated stop",
                            str(conn.agent_id)[:8], deployment.id,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to resend STOP_SCENARIO to agent "
                            "%s for deployment %s: %s",
                            conn.agent_id, deployment.id, e,
                        )
                elif deployment.state != "running":
                    old_state = deployment.state
                    deployment.state = "running"
                    deployment.stopped_at = None
                    logger.info(
                        f"Synced deployment {deployment.id} on page load: "
                        f"{old_state} -> running"
                    )
            except Exception as e:
                logger.debug(f"Could not sync scenario {scenario_id_str}: {e}")

    await db.commit()

    all_deployments: list[UnifiedDeploymentResponse] = []

    # Fetch agent deployments
    agent_query = select(AgentDeployment).order_by(AgentDeployment.started_at.desc())

    if scenario_id:
        agent_query = agent_query.where(AgentDeployment.scenario_id == scenario_id)
    if agent_id:
        agent_query = agent_query.where(AgentDeployment.agent_id == agent_id)
    if status_filter:
        agent_query = agent_query.where(AgentDeployment.state == status_filter)

    result = await db.execute(agent_query)
    agent_deployments = result.scalars().all()

    # Auto-fix stuck deployments by checking agent connection status
    needs_commit = False
    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(minutes=2)

    for d in agent_deployments:
        conn = agent_manager._connections.get(d.agent_id)
        scenario_id_str = str(d.scenario_id)

        if d.state == "stopping":
            if conn is None or scenario_id_str not in conn.running_scenarios:
                logger.info(f"Auto-marking deployment {d.id} as stopped (agent disconnected or scenario not running)")
                d.state = "stopped"
                d.stopped_at = now
                needs_commit = True

        elif d.state == "running":
            if conn is None:
                logger.info(f"Auto-marking deployment {d.id} as disconnected (agent offline)")
                d.state = "disconnected"
                needs_commit = True
            elif scenario_id_str not in conn.running_scenarios:
                logger.info(f"Auto-marking deployment {d.id} as stopped (scenario not in agent's running list)")
                d.state = "stopped"
                d.stopped_at = now
                needs_commit = True

        elif d.state == "starting":
            if d.started_at and d.started_at < stale_threshold:
                if conn is None:
                    logger.info(f"Auto-marking deployment {d.id} as error (stale starting state, agent offline)")
                    d.state = "error"
                    d.error_message = "Agent disconnected during startup"
                    needs_commit = True

    if needs_commit:
        await db.commit()

    # Fetch related agents and scenarios for agent deployments
    # Also get real-time attack state from traffic_dashboard
    from app.services.traffic_dashboard import traffic_dashboard

    for d in agent_deployments:
        agent_result = await db.execute(
            select(TrafficAgent).where(TrafficAgent.id == d.agent_id)
        )
        agent = agent_result.scalar_one_or_none()

        scenario_result = await db.execute(
            select(Scenario).where(Scenario.id == d.scenario_id)
        )
        scenario = scenario_result.scalar_one_or_none()

        # Get real-time attack state from traffic_dashboard (if running)
        attack_state = None
        if d.state == "running":
            deployment_status = traffic_dashboard.get_deployment(str(d.scenario_id))
            if deployment_status and "attack" in deployment_status:
                attack_state = deployment_status["attack"]

        all_deployments.append(
            UnifiedDeploymentResponse.from_agent_deployment(d, agent, scenario, attack_state)
        )

    # Sort all deployments by created_at descending
    all_deployments.sort(key=lambda x: x.created_at, reverse=True)

    return UnifiedDeploymentListResponse(
        items=all_deployments,
        total=len(all_deployments),
    )


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_deployment(
    deployment_id: UUID,
    db: DBSession,
    _user: CurrentUser,
) -> None:
    """Remove a deployment record.

    If the deployment is still in an active state (running/starting/stopping)
    we send STOP_SCENARIO to the agent before deleting the row. Otherwise the
    agent would keep generating traffic for a deployment the backend has
    forgotten — the exact orphan state list_deployments has to reconcile on
    every page load.
    """
    from app.services.agent_manager import agent_manager

    result = await db.execute(
        select(AgentDeployment).where(AgentDeployment.id == deployment_id)
    )
    agent_deployment = result.scalar_one_or_none()

    if not agent_deployment:
        raise NotFoundError("Deployment", str(deployment_id))

    if agent_deployment.state in ("running", "starting", "stopping"):
        try:
            stopped = await agent_manager.stop_scenario(str(agent_deployment.scenario_id))
            if stopped:
                logger.info(
                    f"Sent STOP_SCENARIO to agent {agent_deployment.agent_id} "
                    f"before deleting deployment {deployment_id}"
                )
            else:
                logger.warning(
                    f"Could not stop scenario {agent_deployment.scenario_id} "
                    f"on agent {agent_deployment.agent_id} before deletion — "
                    f"the agent may continue running it"
                )
        except Exception as e:
            logger.warning(
                f"Error sending STOP_SCENARIO during deployment delete: {e}"
            )

    await db.delete(agent_deployment)
    await db.commit()
