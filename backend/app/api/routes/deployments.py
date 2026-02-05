"""Remote deployment management routes."""

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.core.encryption import decrypt_value
from app.models.docker_host import DockerHost
from app.models.remote_deployment import DeploymentStatus, RemoteDeployment
from app.models.scenario import Scenario
from app.models.traffic_agent import AgentDeployment, TrafficAgent
from app.schemas.deployment import (
    DeploymentListResponse,
    DeploymentLogsResponse,
    DeploymentRequest,
    DeploymentResponse,
    UnifiedDeploymentListResponse,
    UnifiedDeploymentResponse,
)
from app.services.docker_service import docker_service
from app.services.scenario_enricher import ScenarioDefinitionEnricher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deployments", tags=["Deployments"])


@router.get("", response_model=UnifiedDeploymentListResponse)
async def list_deployments(
    db: DBSession,
    _user: CurrentUser,
    scenario_id: UUID | None = None,
    docker_host_id: UUID | None = None,
    agent_id: UUID | None = None,
    status_filter: str | None = Query(None, description="Filter by status"),
    deployment_type: str | None = Query(None, description="Filter by type: docker, agent"),
) -> UnifiedDeploymentListResponse:
    """List all deployments (Docker and Agent) with optional filters.

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
                    # Find the most recent deployment for this agent/scenario
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

    # Fetch Docker deployments (unless filtered to agent only)
    if deployment_type != "agent":
        docker_query = select(RemoteDeployment).options(
            selectinload(RemoteDeployment.scenario),
            selectinload(RemoteDeployment.docker_host),
        ).order_by(RemoteDeployment.created_at.desc())

        if scenario_id:
            docker_query = docker_query.where(RemoteDeployment.scenario_id == scenario_id)
        if docker_host_id:
            docker_query = docker_query.where(RemoteDeployment.docker_host_id == docker_host_id)
        if status_filter:
            docker_query = docker_query.where(RemoteDeployment.status == status_filter)

        result = await db.execute(docker_query)
        docker_deployments = result.scalars().all()

        for d in docker_deployments:
            all_deployments.append(UnifiedDeploymentResponse.from_docker_deployment(d))

    # Fetch Agent deployments (unless filtered to docker only)
    if deployment_type != "docker":
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
        from app.services.agent_manager import agent_manager
        needs_commit = False
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(minutes=2)

        for d in agent_deployments:
            conn = agent_manager._connections.get(d.agent_id)
            scenario_id_str = str(d.scenario_id)

            if d.state == "stopping":
                # Check if the scenario is still in the agent's running_scenarios
                if conn is None or scenario_id_str not in conn.running_scenarios:
                    # Agent disconnected or scenario not running - mark as stopped
                    logger.info(f"Auto-marking deployment {d.id} as stopped (agent disconnected or scenario not running)")
                    d.state = "stopped"
                    d.stopped_at = now
                    needs_commit = True

            elif d.state == "running":
                # If agent is disconnected, mark deployment as disconnected
                if conn is None:
                    logger.info(f"Auto-marking deployment {d.id} as disconnected (agent offline)")
                    d.state = "disconnected"
                    needs_commit = True
                # If agent is connected but scenario not in running_scenarios, mark as stopped
                elif scenario_id_str not in conn.running_scenarios:
                    logger.info(f"Auto-marking deployment {d.id} as stopped (scenario not in agent's running list)")
                    d.state = "stopped"
                    d.stopped_at = now
                    needs_commit = True

            elif d.state == "starting":
                # If starting for too long and agent disconnected, mark as error
                if d.started_at and d.started_at < stale_threshold:
                    if conn is None:
                        logger.info(f"Auto-marking deployment {d.id} as error (stale starting state, agent offline)")
                        d.state = "error"
                        d.error_message = "Agent disconnected during startup"
                        needs_commit = True

        if needs_commit:
            await db.commit()

        # Fetch related agents and scenarios for agent deployments
        for d in agent_deployments:
            # Get agent
            agent_result = await db.execute(
                select(TrafficAgent).where(TrafficAgent.id == d.agent_id)
            )
            agent = agent_result.scalar_one_or_none()

            # Get scenario
            scenario_result = await db.execute(
                select(Scenario).where(Scenario.id == d.scenario_id)
            )
            scenario = scenario_result.scalar_one_or_none()

            all_deployments.append(
                UnifiedDeploymentResponse.from_agent_deployment(d, agent, scenario)
            )

    # Sort all deployments by created_at descending
    all_deployments.sort(key=lambda x: x.created_at, reverse=True)

    return UnifiedDeploymentListResponse(
        items=all_deployments,
        total=len(all_deployments),
    )


@router.post("", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def start_deployment(
    data: DeploymentRequest,
    db: DBSession,
    user: CurrentUser,
) -> DeploymentResponse:
    """Start a new traffic generator deployment."""
    # Get the scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == data.scenario_id)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Get the Docker host
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == data.docker_host_id)
    )
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docker host not found",
        )

    if not host.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Docker host is not active",
        )

    # Create deployment record
    deployment = RemoteDeployment(
        scenario_id=data.scenario_id,
        docker_host_id=data.docker_host_id,
        network_interface=data.network_interface,
        run_mode=data.run_mode,
        duration_ms=data.duration_ms,
        status=DeploymentStatus.PENDING.value,
        created_by_id=user.id,
    )

    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)

    # Enrich scenario definition with unique identifiers
    # This is CRITICAL for remote deployments to ensure each device has
    # unique serial numbers and network identifiers (BACnet device_instance,
    # PROFINET station_name, SNMP sys_name, etc.)
    enriched_definition = ScenarioDefinitionEnricher.enrich_for_deployment(
        definition=scenario.definition,
        scenario_id=str(scenario.id),
    )

    # Prepare scenario JSON for the container
    scenario_json = json.dumps({
        "id": str(scenario.id),
        "name": scenario.name,
        "run_mode": data.run_mode,
        "total_duration_ms": data.duration_ms,  # None for perpetual mode
        "definition": enriched_definition,  # Use enriched definition with unique IDs
    })

    # Decrypt client key for connection
    if host.client_key:
        host.client_key = decrypt_value(host.client_key)

    try:
        # Update status to starting
        deployment.status = DeploymentStatus.STARTING.value
        await db.commit()

        # Deploy the container
        container_id = docker_service.deploy_container(
            host=host,
            scenario_json=scenario_json,
            interface=data.network_interface,
            duration_ms=data.duration_ms,
            run_mode=data.run_mode,
            deployment_id=deployment.id,
        )

        # Update deployment with container info
        deployment.container_id = container_id
        deployment.container_name = f"packetarch-generator-{str(deployment.id)[:8]}"
        deployment.status = DeploymentStatus.RUNNING.value
        deployment.started_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(deployment)

        # Reload with relationships
        result = await db.execute(
            select(RemoteDeployment)
            .options(
                selectinload(RemoteDeployment.scenario),
                selectinload(RemoteDeployment.docker_host),
            )
            .where(RemoteDeployment.id == deployment.id)
        )
        deployment = result.scalar_one()

        return DeploymentResponse.from_model(deployment)

    except Exception as e:
        logger.exception(f"Failed to deploy container: {e}")

        # Update deployment status to failed
        deployment.status = DeploymentStatus.FAILED.value
        deployment.error_message = str(e)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy container: {str(e)}",
        )


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    db: DBSession,
    _user: CurrentUser,
) -> DeploymentResponse:
    """Get deployment status."""
    result = await db.execute(
        select(RemoteDeployment)
        .options(
            selectinload(RemoteDeployment.scenario),
            selectinload(RemoteDeployment.docker_host),
        )
        .where(RemoteDeployment.id == deployment_id)
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    # If deployment is running, check container status
    if deployment.status == DeploymentStatus.RUNNING.value and deployment.container_id:
        host = deployment.docker_host
        if host.client_key:
            host.client_key = decrypt_value(host.client_key)

        try:
            container_status = docker_service.get_container_status(
                host, deployment.container_id
            )

            if container_status:
                if container_status.status == "exited":
                    deployment.status = DeploymentStatus.STOPPED.value
                    deployment.stopped_at = (
                        container_status.finished_at or datetime.now(timezone.utc)
                    )
                    if container_status.exit_code != 0:
                        deployment.status = DeploymentStatus.FAILED.value
                        deployment.error_message = (
                            f"Container exited with code {container_status.exit_code}"
                        )
                    await db.commit()
                    await db.refresh(deployment)
        except Exception as e:
            logger.warning(f"Failed to check container status: {e}")

    return DeploymentResponse.from_model(deployment)


@router.post("/{deployment_id}/stop", response_model=DeploymentResponse)
async def stop_deployment(
    deployment_id: UUID,
    db: DBSession,
    _user: CurrentUser,
) -> DeploymentResponse:
    """Stop a running deployment."""
    result = await db.execute(
        select(RemoteDeployment)
        .options(
            selectinload(RemoteDeployment.scenario),
            selectinload(RemoteDeployment.docker_host),
        )
        .where(RemoteDeployment.id == deployment_id)
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    if deployment.status not in [
        DeploymentStatus.RUNNING.value,
        DeploymentStatus.STARTING.value,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot stop deployment in '{deployment.status}' status",
        )

    if not deployment.container_id:
        deployment.status = DeploymentStatus.STOPPED.value
        deployment.stopped_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(deployment)
        return DeploymentResponse.from_model(deployment)

    host = deployment.docker_host
    if host.client_key:
        host.client_key = decrypt_value(host.client_key)

    try:
        deployment.status = DeploymentStatus.STOPPING.value
        await db.commit()

        docker_service.stop_container(host, deployment.container_id)

        deployment.status = DeploymentStatus.STOPPED.value
        deployment.stopped_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(deployment)

        return DeploymentResponse.from_model(deployment)

    except Exception as e:
        logger.exception(f"Failed to stop container: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop container: {str(e)}",
        )


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_deployment(
    deployment_id: UUID,
    db: DBSession,
    _user: CurrentUser,
) -> None:
    """Remove a deployment (Docker or Agent)."""
    # Try Docker deployment first
    result = await db.execute(
        select(RemoteDeployment)
        .options(selectinload(RemoteDeployment.docker_host))
        .where(RemoteDeployment.id == deployment_id)
    )
    docker_deployment = result.scalar_one_or_none()

    if docker_deployment:
        # Stop and remove container if it exists
        if docker_deployment.container_id:
            host = docker_deployment.docker_host
            if host.client_key:
                host.client_key = decrypt_value(host.client_key)

            try:
                docker_service.stop_container(host, docker_deployment.container_id)
                docker_service.remove_container(host, docker_deployment.container_id)
            except Exception as e:
                logger.warning(f"Failed to remove container: {e}")

        await db.delete(docker_deployment)
        await db.commit()
        return

    # Try Agent deployment
    result = await db.execute(
        select(AgentDeployment).where(AgentDeployment.id == deployment_id)
    )
    agent_deployment = result.scalar_one_or_none()

    if agent_deployment:
        await db.delete(agent_deployment)
        await db.commit()
        return

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Deployment not found",
    )


@router.get("/{deployment_id}/logs", response_model=DeploymentLogsResponse)
async def get_deployment_logs(
    deployment_id: UUID,
    db: DBSession,
    _user: CurrentUser,
    tail: int = 100,
) -> DeploymentLogsResponse:
    """Get logs from a deployment container."""
    result = await db.execute(
        select(RemoteDeployment)
        .options(selectinload(RemoteDeployment.docker_host))
        .where(RemoteDeployment.id == deployment_id)
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    if not deployment.container_id:
        return DeploymentLogsResponse(
            deployment_id=deployment.id,
            container_id=None,
            logs="No container associated with this deployment",
            timestamp=datetime.now(timezone.utc),
        )

    host = deployment.docker_host
    if host.client_key:
        host.client_key = decrypt_value(host.client_key)

    try:
        logs = docker_service.get_container_logs(host, deployment.container_id, tail)

        return DeploymentLogsResponse(
            deployment_id=deployment.id,
            container_id=deployment.container_id,
            logs=logs,
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.exception(f"Failed to get container logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get logs: {str(e)}",
        )


# Default PCAP output directory inside the container
PCAP_OUTPUT_DIR = "/output"


@router.get("/{deployment_id}/pcap")
async def list_pcap_files(
    deployment_id: UUID,
    db: DBSession,
    _user: CurrentUser,
) -> dict:
    """List available PCAP files from a deployment."""
    result = await db.execute(
        select(RemoteDeployment)
        .options(selectinload(RemoteDeployment.docker_host))
        .where(RemoteDeployment.id == deployment_id)
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    if not deployment.container_id:
        return {"deployment_id": str(deployment.id), "files": []}

    host = deployment.docker_host
    if host.client_key:
        host.client_key = decrypt_value(host.client_key)

    try:
        files = docker_service.list_files_in_container(
            host, deployment.container_id, PCAP_OUTPUT_DIR
        )
        pcap_files = [f for f in files if f.endswith(".pcap") or f.endswith(".pcapng")]

        return {
            "deployment_id": str(deployment.id),
            "files": pcap_files,
        }

    except Exception as e:
        logger.exception(f"Failed to list PCAP files: {e}")
        return {"deployment_id": str(deployment.id), "files": [], "error": str(e)}


@router.get("/{deployment_id}/pcap/{filename}")
async def download_pcap_file(
    deployment_id: UUID,
    filename: str,
    db: DBSession,
    _user: CurrentUser,
) -> Response:
    """Download a PCAP file from a deployment."""
    result = await db.execute(
        select(RemoteDeployment)
        .options(selectinload(RemoteDeployment.docker_host))
        .where(RemoteDeployment.id == deployment_id)
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    if not deployment.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this deployment",
        )

    # Validate filename to prevent directory traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    host = deployment.docker_host
    if host.client_key:
        host.client_key = decrypt_value(host.client_key)

    try:
        file_path = f"{PCAP_OUTPUT_DIR}/{filename}"
        content = docker_service.get_file_from_container(
            host, deployment.container_id, file_path
        )

        if content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PCAP file not found",
            )

        return Response(
            content=content,
            media_type="application/vnd.tcpdump.pcap",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to download PCAP file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download PCAP: {str(e)}",
        )
