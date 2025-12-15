"""Deployment control tools for MCP.

This module provides tools for:
- Starting traffic generation deployments
- Stopping running deployments
- Getting deployment status
- Listing deployments for scenarios
- Listing available Docker hosts
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.encryption import decrypt_value
from app.models.docker_host import DockerHost
from app.models.remote_deployment import DeploymentStatus, RemoteDeployment, RunMode
from app.models.scenario import Scenario
from app.services.docker_service import docker_service


async def list_docker_hosts(db: AsyncSession) -> str:
    """List available Docker hosts for deployment.

    Args:
        db: Database session

    Returns:
        JSON string with available hosts
    """
    result = await db.execute(
        select(DockerHost).where(DockerHost.is_active == True)
    )
    hosts = list(result.scalars().all())

    host_list = [
        {
            "id": str(host.id),
            "name": host.name,
            "hostname": host.hostname,
            "port": host.port,
            "is_active": host.is_active,
            "default_interface": host.default_interface,
        }
        for host in hosts
    ]

    return json.dumps({
        "hosts": host_list,
        "count": len(host_list),
    })


async def start_deployment(
    db: AsyncSession,
    scenario_id: str,
    docker_host_id: str,
    network_interface: str | None = None,
    run_mode: str = "timed",
    duration_ms: int | None = 60000,
) -> str:
    """Start a traffic generation deployment.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        docker_host_id: Docker host UUID
        network_interface: Network interface for packet injection (uses host default if not specified)
        run_mode: 'timed' (stops after duration) or 'perpetual' (runs until stopped)
        duration_ms: Duration in milliseconds for timed mode

    Returns:
        JSON string with deployment result
    """
    # Get the scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    # Get the Docker host
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == uuid.UUID(docker_host_id))
    )
    host = result.scalar_one_or_none()

    if not host:
        return json.dumps({"error": "Docker host not found"})

    if not host.is_active:
        return json.dumps({"error": "Docker host is not active"})

    # Use default interface if not specified
    interface = network_interface or host.default_interface
    if not interface:
        return json.dumps({"error": "Network interface not specified and host has no default"})

    # Validate run mode
    if run_mode not in ["timed", "perpetual"]:
        return json.dumps({"error": f"Invalid run_mode '{run_mode}'. Must be 'timed' or 'perpetual'"})

    # Create deployment record
    deployment = RemoteDeployment(
        scenario_id=uuid.UUID(scenario_id),
        docker_host_id=uuid.UUID(docker_host_id),
        network_interface=interface,
        run_mode=run_mode,
        duration_ms=duration_ms if run_mode == "timed" else None,
        status=DeploymentStatus.PENDING.value,
    )

    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)

    # Prepare scenario JSON for the container
    scenario_json = json.dumps({
        "id": str(scenario.id),
        "name": scenario.name,
        "run_mode": run_mode,
        "total_duration_ms": duration_ms if run_mode == "timed" else None,
        "definition": scenario.definition,
    })

    # Decrypt client key for connection
    host_key = None
    if host.client_key:
        host_key = decrypt_value(host.client_key)

    try:
        # Update status to starting
        deployment.status = DeploymentStatus.STARTING.value
        await db.commit()

        # Create a copy of host with decrypted key for docker service
        host_copy = DockerHost(
            id=host.id,
            name=host.name,
            hostname=host.hostname,
            port=host.port,
            tls_enabled=host.tls_enabled,
            client_cert=host.client_cert,
            client_key=host_key,
            ca_cert=host.ca_cert,
            default_interface=host.default_interface,
            is_active=host.is_active,
        )

        # Deploy the container
        container_id = docker_service.deploy_container(
            host=host_copy,
            scenario_json=scenario_json,
            interface=interface,
            duration_ms=duration_ms if run_mode == "timed" else None,
            run_mode=run_mode,
            deployment_id=deployment.id,
        )

        # Update deployment with container info
        deployment.container_id = container_id
        deployment.container_name = f"packetarch-generator-{str(deployment.id)[:8]}"
        deployment.status = DeploymentStatus.RUNNING.value
        deployment.started_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(deployment)

        return json.dumps({
            "success": True,
            "deployment_id": str(deployment.id),
            "container_id": container_id,
            "status": deployment.status,
            "scenario_name": scenario.name,
            "docker_host": host.name,
            "network_interface": interface,
            "run_mode": run_mode,
        })

    except Exception as e:
        # Update deployment status to failed
        deployment.status = DeploymentStatus.FAILED.value
        deployment.error_message = str(e)
        await db.commit()

        return json.dumps({
            "error": f"Failed to deploy: {str(e)}",
            "deployment_id": str(deployment.id),
        })


async def stop_deployment(
    db: AsyncSession,
    deployment_id: str,
) -> str:
    """Stop a running deployment.

    Args:
        db: Database session
        deployment_id: Deployment UUID

    Returns:
        JSON string with result
    """
    result = await db.execute(
        select(RemoteDeployment)
        .options(selectinload(RemoteDeployment.docker_host))
        .where(RemoteDeployment.id == uuid.UUID(deployment_id))
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        return json.dumps({"error": "Deployment not found"})

    if deployment.status not in [
        DeploymentStatus.RUNNING.value,
        DeploymentStatus.STARTING.value,
    ]:
        return json.dumps({
            "error": f"Cannot stop deployment in '{deployment.status}' status",
            "deployment_id": str(deployment.id),
            "current_status": deployment.status,
        })

    if not deployment.container_id:
        deployment.status = DeploymentStatus.STOPPED.value
        deployment.stopped_at = datetime.now(timezone.utc)
        await db.commit()
        return json.dumps({
            "success": True,
            "deployment_id": str(deployment.id),
            "status": deployment.status,
            "message": "Deployment stopped (no container was running)",
        })

    host = deployment.docker_host
    host_key = None
    if host.client_key:
        host_key = decrypt_value(host.client_key)

    try:
        deployment.status = DeploymentStatus.STOPPING.value
        await db.commit()

        # Create host copy with decrypted key
        host_copy = DockerHost(
            id=host.id,
            name=host.name,
            hostname=host.hostname,
            port=host.port,
            tls_enabled=host.tls_enabled,
            client_cert=host.client_cert,
            client_key=host_key,
            ca_cert=host.ca_cert,
            default_interface=host.default_interface,
            is_active=host.is_active,
        )

        docker_service.stop_container(host_copy, deployment.container_id)

        deployment.status = DeploymentStatus.STOPPED.value
        deployment.stopped_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(deployment)

        return json.dumps({
            "success": True,
            "deployment_id": str(deployment.id),
            "status": deployment.status,
            "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
        })

    except Exception as e:
        return json.dumps({
            "error": f"Failed to stop deployment: {str(e)}",
            "deployment_id": str(deployment.id),
        })


async def get_deployment_status(
    db: AsyncSession,
    deployment_id: str,
) -> str:
    """Get current deployment status and statistics.

    Args:
        db: Database session
        deployment_id: Deployment UUID

    Returns:
        JSON string with deployment status
    """
    result = await db.execute(
        select(RemoteDeployment)
        .options(
            selectinload(RemoteDeployment.scenario),
            selectinload(RemoteDeployment.docker_host),
        )
        .where(RemoteDeployment.id == uuid.UUID(deployment_id))
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        return json.dumps({"error": "Deployment not found"})

    # If deployment is running, check actual container status
    if deployment.status == DeploymentStatus.RUNNING.value and deployment.container_id:
        host = deployment.docker_host
        host_key = None
        if host.client_key:
            host_key = decrypt_value(host.client_key)

        try:
            host_copy = DockerHost(
                id=host.id,
                name=host.name,
                hostname=host.hostname,
                port=host.port,
                tls_enabled=host.tls_enabled,
                client_cert=host.client_cert,
                client_key=host_key,
                ca_cert=host.ca_cert,
                default_interface=host.default_interface,
                is_active=host.is_active,
            )

            container_status = docker_service.get_container_status(
                host_copy, deployment.container_id
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
        except Exception:
            pass  # Ignore status check errors

    # Calculate elapsed time
    elapsed_ms = None
    if deployment.started_at:
        end_time = deployment.stopped_at or datetime.now(timezone.utc)
        elapsed_ms = int((end_time - deployment.started_at).total_seconds() * 1000)

    return json.dumps({
        "deployment_id": str(deployment.id),
        "scenario_id": str(deployment.scenario_id),
        "scenario_name": deployment.scenario.name if deployment.scenario else None,
        "docker_host_name": deployment.docker_host.name if deployment.docker_host else None,
        "status": deployment.status,
        "run_mode": deployment.run_mode,
        "duration_ms": deployment.duration_ms,
        "elapsed_ms": elapsed_ms,
        "packets_injected": deployment.packets_injected,
        "network_interface": deployment.network_interface,
        "container_id": deployment.container_id,
        "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
        "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
        "error_message": deployment.error_message,
    })


async def list_deployments(
    db: AsyncSession,
    scenario_id: str | None = None,
    status_filter: str | None = None,
) -> str:
    """List deployments with optional filters.

    Args:
        db: Database session
        scenario_id: Optional scenario UUID to filter by
        status_filter: Optional status to filter by (pending, starting, running, stopping, stopped, failed)

    Returns:
        JSON string with deployments list
    """
    query = select(RemoteDeployment).options(
        selectinload(RemoteDeployment.scenario),
        selectinload(RemoteDeployment.docker_host),
    ).order_by(RemoteDeployment.created_at.desc())

    if scenario_id:
        query = query.where(RemoteDeployment.scenario_id == uuid.UUID(scenario_id))

    if status_filter:
        query = query.where(RemoteDeployment.status == status_filter)

    result = await db.execute(query)
    deployments = list(result.scalars().all())

    deployment_list = [
        {
            "id": str(d.id),
            "scenario_id": str(d.scenario_id),
            "scenario_name": d.scenario.name if d.scenario else None,
            "docker_host_name": d.docker_host.name if d.docker_host else None,
            "status": d.status,
            "run_mode": d.run_mode,
            "network_interface": d.network_interface,
            "started_at": d.started_at.isoformat() if d.started_at else None,
            "stopped_at": d.stopped_at.isoformat() if d.stopped_at else None,
            "error_message": d.error_message,
        }
        for d in deployments
    ]

    return json.dumps({
        "deployments": deployment_list,
        "count": len(deployment_list),
    })
