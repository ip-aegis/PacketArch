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
    for conn in agent_manager.get_all_connections():
        if conn.running_scenarios:
            for scenario_id_str in conn.running_scenarios:
                try:
                    scenario_uuid = UUID(scenario_id_str)
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
                    if deployment and deployment.state != "running":
                        old_state = deployment.state
                        deployment.state = "running"
                        deployment.stopped_at = None
                        logger.info(
                            f"Synced deployment {deployment.id} on page load: "
                            f"{old_state} -> running"
                        )
                except (ValueError, Exception) as e:
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
    """Remove a deployment record."""
    result = await db.execute(
        select(AgentDeployment).where(AgentDeployment.id == deployment_id)
    )
    agent_deployment = result.scalar_one_or_none()

    if agent_deployment:
        await db.delete(agent_deployment)
        await db.commit()
        return

    raise NotFoundError("Deployment", str(deployment_id))
