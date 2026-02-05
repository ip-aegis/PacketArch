"""WebSocket hub for traffic agent connections."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update

from app.core.database import async_session_maker
from app.models.traffic_agent import AgentDeployment, TrafficAgent
from app.services.agent_manager import agent_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent-websocket"])


async def update_deployment_status(
    agent_id: UUID,
    scenario_id: str,
    state: str,
    packets_sent: int = 0,
    error_message: str | None = None,
) -> None:
    """Update deployment status in the database.

    The agent is the source of truth. If the agent says a scenario is running,
    we find or create a deployment record to reflect that.

    Args:
        agent_id: Agent UUID
        scenario_id: Scenario UUID string
        state: New state (running, stopped, error, etc.)
        packets_sent: Number of packets sent
        error_message: Error message if state is 'error'
    """
    try:
        async with async_session_maker() as db:
            # Find ALL deployments for this agent/scenario (including stopped ones if agent says running)
            # This allows re-activation of stopped deployments when agent reports running
            allowed_states = ["starting", "running", "stopping", "disconnected"]
            if state == "running":
                allowed_states.append("stopped")  # Allow re-activation

            result = await db.execute(
                select(AgentDeployment)
                .where(
                    AgentDeployment.agent_id == agent_id,
                    AgentDeployment.scenario_id == UUID(scenario_id),
                    AgentDeployment.state.in_(allowed_states),
                )
                .order_by(AgentDeployment.started_at.desc())
            )
            deployments = result.scalars().all()

            if deployments:
                # Update the most recent deployment (first in list since sorted desc)
                deployment = deployments[0]
                old_state = deployment.state
                deployment.state = state
                deployment.packets_sent = packets_sent
                if error_message:
                    deployment.error_message = error_message
                if state in ("stopped", "error"):
                    deployment.stopped_at = datetime.utcnow()
                elif state == "running" and old_state == "stopped":
                    # Re-activating a stopped deployment - clear stopped_at
                    deployment.stopped_at = None
                    logger.info(f"Re-activated deployment {deployment.id}: stopped -> running")

                # Mark any older duplicate deployments as stopped to prevent confusion
                for old_deployment in deployments[1:]:
                    if old_deployment.state in ("running", "starting", "disconnected"):
                        old_deployment.state = "stopped"
                        old_deployment.stopped_at = datetime.utcnow()
                        logger.info(f"Auto-closing duplicate deployment {old_deployment.id}")

                await db.commit()
                logger.debug(f"Updated deployment {deployment.id}: state={state}, packets={packets_sent}")
            else:
                logger.warning(
                    f"No deployment found for agent={agent_id}, scenario={scenario_id}. "
                    f"Status update ignored (state={state}, packets={packets_sent})"
                )
    except Exception as e:
        logger.error(f"Failed to update deployment status: {e}")


async def update_agent_heartbeat(
    agent_id: UUID,
    hostname: str | None = None,
    platform: str | None = None,
    version: str | None = None,
) -> None:
    """Update agent info from heartbeat in the database.

    This ensures the database always reflects the current agent state,
    not just what was reported on initial connection.

    Args:
        agent_id: Agent UUID
        hostname: Agent hostname
        platform: Agent platform (Linux, Windows, etc.)
        version: Agent version
    """
    try:
        async with async_session_maker() as db:
            update_values: dict = {
                "last_seen": datetime.utcnow(),
                "status": "online",  # Agent is online if sending heartbeats
            }
            if hostname is not None:
                update_values["hostname"] = hostname
            if platform is not None:
                update_values["platform"] = platform
            if version is not None:
                update_values["version"] = version

            await db.execute(
                update(TrafficAgent)
                .where(TrafficAgent.id == agent_id)
                .values(**update_values)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to update agent heartbeat: {e}")


async def sync_running_scenarios(agent_id: UUID, running_scenarios: list[str]) -> None:
    """Sync deployment states with what the agent reports as running.

    This is the source of truth reconciliation - if the agent says a scenario
    is running, it's running. This includes re-activating stopped deployments.

    Args:
        agent_id: Agent UUID
        running_scenarios: List of scenario IDs the agent reports as running
    """
    if not running_scenarios:
        # No scenarios reported - nothing to sync
        # Don't mark things as stopped just because the list is empty
        # (could be an early heartbeat before agent starts scenarios)
        return

    try:
        async with async_session_maker() as db:
            running_set = set(running_scenarios)
            synced_count = 0

            # For each running scenario, find or re-activate a deployment
            for scenario_id_str in running_set:
                try:
                    scenario_uuid = UUID(scenario_id_str)
                except ValueError:
                    continue

                # Find ALL deployments for this agent/scenario including stopped
                result = await db.execute(
                    select(AgentDeployment)
                    .where(
                        AgentDeployment.agent_id == agent_id,
                        AgentDeployment.scenario_id == scenario_uuid,
                    )
                    .order_by(AgentDeployment.started_at.desc())
                )
                deployments = result.scalars().all()

                if deployments:
                    # Update the most recent deployment
                    primary_deployment = deployments[0]
                    if primary_deployment.state != "running":
                        old_state = primary_deployment.state
                        primary_deployment.state = "running"
                        primary_deployment.stopped_at = None  # Clear stopped_at on re-activation
                        synced_count += 1
                        logger.info(
                            f"Synced deployment {primary_deployment.id}: {old_state} -> running "
                            f"(agent reports scenario {scenario_id_str[:8]} as running)"
                        )

                    # Mark any older duplicate deployments as stopped
                    for old_deployment in deployments[1:]:
                        if old_deployment.state in ("running", "starting", "disconnected"):
                            old_deployment.state = "stopped"
                            old_deployment.stopped_at = datetime.utcnow()
                            synced_count += 1
                            logger.info(f"Auto-closing duplicate deployment {old_deployment.id}")

            if synced_count > 0:
                await db.commit()
                logger.info(f"Synced {synced_count} deployment states for agent {agent_id}")

    except Exception as e:
        logger.error(f"Failed to sync running scenarios: {e}")


async def validate_agent_token(token: str) -> TrafficAgent | None:
    """Validate agent token and return the agent record.

    Args:
        token: Bearer token from Authorization header

    Returns:
        TrafficAgent if valid, None otherwise
    """
    import hashlib

    # Hash the token for comparison
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    async with async_session_maker() as db:
        result = await db.execute(
            select(TrafficAgent).where(
                TrafficAgent.token_hash == token_hash,
                TrafficAgent.is_active == True,
            )
        )
        agent = result.scalar_one_or_none()

        if agent:
            # Update last_seen and first_connected_at if not set
            update_values = {
                "last_seen": datetime.utcnow(),
                "status": "online",
            }
            # Set first_connected_at only if not already set
            if agent.first_connected_at is None:
                update_values["first_connected_at"] = datetime.utcnow()

            await db.execute(
                update(TrafficAgent)
                .where(TrafficAgent.id == agent.id)
                .values(**update_values)
            )
            await db.commit()

            # Refresh to get updated values
            await db.refresh(agent)

        return agent


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="Agent authentication token"),
):
    """WebSocket endpoint for traffic agents.

    Agents connect to this endpoint to receive commands and report status.
    Authentication is via bearer token in the query string.
    """
    # Validate token before accepting connection
    agent = await validate_agent_token(token)
    if not agent:
        logger.warning("Agent WebSocket connection rejected: invalid token")
        await websocket.close(code=4001, reason="Invalid or inactive agent token")
        return

    # Accept the connection
    await websocket.accept()
    logger.info(f"Agent {agent.name} ({agent.id}) connected")

    # Register with agent manager
    await agent_manager.register(agent.id, websocket)

    # Send connection confirmation
    await websocket.send_json({
        "type": "CONNECTED",
        "agent_id": str(agent.id),
        "agent_name": agent.name,
        "default_interface": agent.default_interface,
    })

    try:
        # Message loop
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            logger.debug(f"Agent {agent.id} sent message: {msg_type}")

            # Handle STATUS messages with database persistence
            if msg_type == "STATUS":
                logger.info(f"Agent {agent.id} STATUS: scenario={data.get('scenario_id')}, state={data.get('state')}, packets={data.get('packets_sent')}")
                scenario_id = data.get("scenario_id")
                if scenario_id:
                    await update_deployment_status(
                        agent_id=agent.id,
                        scenario_id=scenario_id,
                        state=data.get("state", "unknown"),
                        packets_sent=data.get("packets_sent", 0),
                        error_message=data.get("error"),
                    )

            # Handle HEARTBEAT - sync agent info and running scenarios with database
            # This is critical for state reconciliation after backend restart
            elif msg_type == "HEARTBEAT":
                # Update agent info in database
                await update_agent_heartbeat(
                    agent_id=agent.id,
                    hostname=data.get("hostname"),
                    platform=data.get("platform"),
                    version=data.get("version"),
                )
                # Sync running scenarios
                running_scenarios = data.get("running_scenarios", [])
                if running_scenarios is not None:
                    await sync_running_scenarios(agent.id, running_scenarios)

            # Also update in-memory state
            await agent_manager.handle_message(agent.id, data)

    except WebSocketDisconnect:
        logger.info(f"Agent {agent.name} ({agent.id}) disconnected")

    except Exception as e:
        logger.error(f"Agent {agent.id} WebSocket error: {e}")

    finally:
        # Unregister and update status
        await agent_manager.unregister(agent.id)

        # Update agent status to offline and mark active deployments as disconnected
        async with async_session_maker() as db:
            await db.execute(
                update(TrafficAgent)
                .where(TrafficAgent.id == agent.id)
                .values(status="offline")
            )

            # Mark any running/starting deployments as disconnected
            await db.execute(
                update(AgentDeployment)
                .where(
                    AgentDeployment.agent_id == agent.id,
                    AgentDeployment.state.in_(["running", "starting", "stopping"]),
                )
                .values(state="disconnected")
            )
            await db.commit()
            logger.info(f"Agent {agent.id} marked as offline, active deployments marked as disconnected")
