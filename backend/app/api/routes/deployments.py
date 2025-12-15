"""Remote deployment management routes."""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.core.encryption import decrypt_value
from app.models.docker_host import DockerHost
from app.models.remote_deployment import DeploymentStatus, RemoteDeployment
from app.models.scenario import Scenario
from app.schemas.deployment import (
    DeploymentListResponse,
    DeploymentLogsResponse,
    DeploymentRequest,
    DeploymentResponse,
)
from app.services.docker_service import docker_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deployments", tags=["Deployments"])


@router.get("", response_model=DeploymentListResponse)
async def list_deployments(
    db: DBSession,
    _user: CurrentUser,
    scenario_id: UUID | None = None,
    docker_host_id: UUID | None = None,
    status_filter: DeploymentStatus | None = None,
) -> DeploymentListResponse:
    """List all deployments with optional filters."""
    query = select(RemoteDeployment).options(
        selectinload(RemoteDeployment.scenario),
        selectinload(RemoteDeployment.docker_host),
    ).order_by(RemoteDeployment.created_at.desc())

    if scenario_id:
        query = query.where(RemoteDeployment.scenario_id == scenario_id)
    if docker_host_id:
        query = query.where(RemoteDeployment.docker_host_id == docker_host_id)
    if status_filter:
        query = query.where(RemoteDeployment.status == status_filter.value)

    result = await db.execute(query)
    deployments = result.scalars().all()

    return DeploymentListResponse(
        items=[DeploymentResponse.from_model(d) for d in deployments],
        total=len(deployments),
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

    # Prepare scenario JSON for the container
    scenario_json = json.dumps({
        "id": str(scenario.id),
        "name": scenario.name,
        "run_mode": data.run_mode,
        "total_duration_ms": data.duration_ms,  # None for perpetual mode
        "definition": scenario.definition,
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
    """Remove a deployment and its container."""
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

    # Stop and remove container if it exists
    if deployment.container_id:
        host = deployment.docker_host
        if host.client_key:
            host.client_key = decrypt_value(host.client_key)

        try:
            docker_service.stop_container(host, deployment.container_id)
            docker_service.remove_container(host, deployment.container_id)
        except Exception as e:
            logger.warning(f"Failed to remove container: {e}")

    await db.delete(deployment)
    await db.commit()


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
