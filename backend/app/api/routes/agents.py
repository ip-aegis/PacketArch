"""REST API routes for managing traffic agents."""

import asyncio
import hashlib
import logging
import secrets
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import get_or_404, paginate as paginate_query
from app.core.database import get_db
from app.core.exceptions import ConflictError, ExternalServiceError, NotFoundError, ValidationError
from app.models.traffic_agent import AgentDeployment, TrafficAgent
from app.models.scenario import Scenario
from app.schemas.agent import (
    AgentConnectionInfo,
    AgentCreate,
    AgentInterfacesResponse,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    AgentUpdateStatus,
    AgentWithToken,
    DeploymentCreate,
    DeploymentResponse,
    InterfaceInfo,
)
from app.services.agent_manager import agent_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


def generate_agent_token() -> str:
    """Generate a secure random token for agent authentication."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# Agent image path (define early for use in routes)
AGENT_IMAGE_PATH = Path(__file__).parent.parent.parent / "static" / "agent" / "packetarch-agent.tar.gz"
AGENT_VERSION_PATH = Path(__file__).parent.parent.parent / "static" / "agent" / "version.txt"
AGENT_BUILD_STATUS_PATH = Path(__file__).parent.parent.parent / "static" / "agent" / "build_status.json"
AGENT_CHECKSUM_PATH = Path(__file__).parent.parent.parent / "static" / "agent" / "checksum.txt"
AGENT_SOURCE_PATH = Path(__file__).parent.parent.parent.parent.parent / "docker" / "packetarch-agent"
BACKEND_APP_PATH = Path(__file__).parent.parent.parent  # backend/app/


def get_standard_agent_version() -> str | None:
    """Get the current standard (built) agent version."""
    if AGENT_VERSION_PATH.exists():
        return AGENT_VERSION_PATH.read_text().strip()
    return None


def extract_agent_version_from_source() -> str | None:
    """Extract the version from the agent source code."""
    version_file = AGENT_SOURCE_PATH / "app" / "version.py"
    if version_file.exists():
        content = version_file.read_text()
        # Parse VERSION = "x.y.z" from the file
        import re
        match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    return None


# IMPORTANT: Place specific routes BEFORE parameterized /{agent_id} routes
# FastAPI matches routes in order, so /connected, /build-image, /image-status, /image
# must come before /{agent_id} to avoid being matched as UUIDs


@router.get("/connected", response_model=list[AgentConnectionInfo])
async def list_connected_agents() -> list[AgentConnectionInfo]:
    """List all currently connected agents with their real-time info."""
    connections = agent_manager.get_all_connections()

    return [
        AgentConnectionInfo(
            agent_id=conn.agent_id,
            connected_at=conn.connected_at,
            last_heartbeat=conn.last_heartbeat,
            hostname=conn.hostname,
            platform=conn.platform,
            version=conn.version,
            cpu_percent=conn.cpu_percent,
            memory_percent=conn.memory_percent,
            running_scenarios=list(conn.running_scenarios),
        )
        for conn in connections
    ]


def _write_build_status(status_dict: dict) -> None:
    """Write build status to JSON file."""
    import json
    AGENT_BUILD_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENT_BUILD_STATUS_PATH.write_text(json.dumps(status_dict))


def _read_build_status() -> dict | None:
    """Read build status from JSON file."""
    import json
    if AGENT_BUILD_STATUS_PATH.exists():
        try:
            return json.loads(AGENT_BUILD_STATUS_PATH.read_text())
        except Exception:
            return None
    return None


@router.get("/build-status")
async def get_build_status() -> dict:
    """Get the current agent image build status.

    Returns the status of any in-progress or recently completed build.
    """
    status_data = _read_build_status()
    if not status_data:
        return {
            "status": "idle",
            "message": "No build in progress",
        }
    return status_data


@router.post("/build-image")
async def build_agent_image(background_tasks: BackgroundTasks) -> dict:
    """Build the agent Docker image and save it for distribution.

    This builds the agent image from source and saves it as a tarball
    that agents can download for updates.
    """
    # Check if build already in progress
    current_status = _read_build_status()
    if current_status and current_status.get("status") == "building":
        return {
            "status": "building",
            "message": "Build already in progress",
            "started_at": current_status.get("started_at"),
        }

    # Verify source exists
    if not AGENT_SOURCE_PATH.exists():
        raise NotFoundError("Agent source", str(AGENT_SOURCE_PATH))

    # Ensure static directory exists
    AGENT_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Extract version from source
    version = extract_agent_version_from_source()
    started_at = datetime.utcnow().isoformat()

    # Write initial build status
    _write_build_status({
        "status": "building",
        "stage": "starting",
        "message": "Starting build...",
        "version": version,
        "started_at": started_at,
    })

    def build_image_sync():
        """Build image using Docker SDK (synchronous for background task)."""
        import gzip
        import shutil
        import tempfile
        import docker

        build_dir = None
        try:
            # Copy agent source to a writable temp directory
            # (the agent source mount may be read-only in production)
            _write_build_status({
                "status": "building",
                "stage": "staging",
                "message": "Staging shared protocol engines...",
                "version": version,
                "started_at": started_at,
            })

            build_dir = Path(tempfile.mkdtemp(prefix="packetarch-agent-build-"))
            shutil.copytree(AGENT_SOURCE_PATH, build_dir / "agent", dirs_exist_ok=True)
            build_context = build_dir / "agent"

            shared_dir = build_context / "_shared"
            if shared_dir.exists():
                shutil.rmtree(shared_dir)
            shared_dir.mkdir(parents=True)

            # Copy protocol_engines/ (canonical source of truth for all protocols)
            shutil.copytree(
                BACKEND_APP_PATH / "protocol_engines",
                shared_dir / "protocol_engines",
            )

            # Copy needed traffic_generator files (scheduler, flow_coordinator)
            tg_dir = shared_dir / "traffic_generator"
            tg_dir.mkdir()
            for fname in ("scheduler.py", "flow_coordinator.py", "pcap_writer.py"):
                src_file = BACKEND_APP_PATH / "traffic_generator" / fname
                if src_file.exists():
                    shutil.copy2(src_file, tg_dir / fname)
            # Write minimal __init__.py (backend's imports modules not available in agent)
            (tg_dir / "__init__.py").write_text(
                '"""Traffic generator utilities (agent subset)."""\n'
            )

            logger.info(f"Staged shared code into {shared_dir}")

            # Update status: building
            _write_build_status({
                "status": "building",
                "stage": "building",
                "message": "Building Docker image...",
                "version": version,
                "started_at": started_at,
            })

            client = docker.from_env()

            # Build the image from the writable temp directory
            logger.info(f"Building agent image from {build_context}...")
            image, build_logs = client.images.build(
                path=str(build_context),
                tag="packetarch-agent:latest",
                rm=True,
                nocache=True,
            )

            # Log build output
            for chunk in build_logs:
                if 'stream' in chunk:
                    logger.debug(chunk['stream'].strip())

            logger.info(f"Agent image built successfully: {image.id[:12]}")

            # Update status: saving
            _write_build_status({
                "status": "building",
                "stage": "saving",
                "message": "Saving image tarball...",
                "version": version,
                "started_at": started_at,
            })

            # Save as tarball (compressed)
            logger.info(f"Saving agent image to {AGENT_IMAGE_PATH}...")

            # Get raw image data
            image_data = image.save(named=True)

            # Compress and write
            with gzip.open(AGENT_IMAGE_PATH, 'wb') as f:
                for chunk in image_data:
                    f.write(chunk)

            # Calculate checksum of the saved tarball
            _write_build_status({
                "status": "building",
                "stage": "checksum",
                "message": "Calculating checksum...",
                "version": version,
                "started_at": started_at,
            })

            checksum = hashlib.sha256()
            with open(AGENT_IMAGE_PATH, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    checksum.update(chunk)
            checksum_hex = checksum.hexdigest()
            AGENT_CHECKSUM_PATH.write_text(checksum_hex)
            logger.info(f"Agent image checksum: {checksum_hex}")

            # Save version file
            if version:
                AGENT_VERSION_PATH.write_text(version)
                logger.info(f"Agent version {version} recorded")

            logger.info(f"Agent image saved to {AGENT_IMAGE_PATH}")

            # Update status: complete
            _write_build_status({
                "status": "complete",
                "stage": "complete",
                "message": f"Build completed successfully (v{version})" if version else "Build completed successfully",
                "version": version,
                "checksum": checksum_hex,
                "started_at": started_at,
                "completed_at": datetime.utcnow().isoformat(),
            })

        except docker.errors.BuildError as e:
            logger.error(f"Failed to build agent image: {e}")
            _write_build_status({
                "status": "failed",
                "stage": "building",
                "message": f"Build failed: {e}",
                "error": str(e),
                "version": version,
                "started_at": started_at,
                "completed_at": datetime.utcnow().isoformat(),
            })
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            _write_build_status({
                "status": "failed",
                "stage": "building",
                "message": f"Docker API error: {e}",
                "error": str(e),
                "version": version,
                "started_at": started_at,
                "completed_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.exception(f"Error building agent image: {e}")
            _write_build_status({
                "status": "failed",
                "stage": "unknown",
                "message": f"Build error: {e}",
                "error": str(e),
                "version": version,
                "started_at": started_at,
                "completed_at": datetime.utcnow().isoformat(),
            })
        finally:
            # Clean up temp build directory
            if build_dir and build_dir.exists():
                shutil.rmtree(build_dir, ignore_errors=True)
                logger.info("Cleaned up temp build directory")

    background_tasks.add_task(build_image_sync)

    return {
        "status": "building",
        "message": "Agent image build started in background",
        "version": version,
        "started_at": started_at,
    }


@router.get("/image-status")
async def get_agent_image_status() -> dict:
    """Check if the agent image is available and get its info."""
    if not AGENT_IMAGE_PATH.exists():
        return {
            "available": False,
            "message": "Agent image not built. Run POST /api/v1/agents/build-image first.",
            "standard_version": None,
        }

    stat = AGENT_IMAGE_PATH.stat()
    standard_version = get_standard_agent_version()

    # Read checksum if available
    checksum = None
    if AGENT_CHECKSUM_PATH.exists():
        checksum = AGENT_CHECKSUM_PATH.read_text().strip()

    return {
        "available": True,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "standard_version": standard_version,
        "checksum": checksum,
    }


@router.get("/image")
async def download_agent_image():
    """Download the agent Docker image tarball.

    This is used by agents to download the latest image during self-update.
    The X-Checksum-SHA256 header contains the expected checksum for verification.
    """
    if not AGENT_IMAGE_PATH.exists():
        raise NotFoundError("Agent image", "packetarch-agent.tar.gz")

    # Read checksum for header
    checksum = None
    if AGENT_CHECKSUM_PATH.exists():
        checksum = AGENT_CHECKSUM_PATH.read_text().strip()

    # Build headers with checksum
    headers = {}
    if checksum:
        headers["X-Checksum-SHA256"] = checksum

    return FileResponse(
        path=AGENT_IMAGE_PATH,
        media_type="application/gzip",
        filename="packetarch-agent.tar.gz",
        headers=headers,
    )


# Standard CRUD routes


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> AgentListResponse:
    """List all traffic agents with pagination."""
    query = select(TrafficAgent)

    if status_filter:
        query = query.where(TrafficAgent.status == status_filter)

    query = query.order_by(TrafficAgent.name)
    agents, total = await paginate_query(db, query, page, page_size)

    # Enrich with real-time connection info
    agent_responses = []
    for agent in agents:
        response = AgentResponse.model_validate(agent)
        # Update status from agent manager if connected
        if agent_manager.is_connected(agent.id):
            response.status = "online"
            conn = agent_manager.get_connection(agent.id)
            if conn:
                response.hostname = conn.hostname
                response.platform = conn.platform
                response.version = conn.version
        agent_responses.append(response)

    # Get standard version for comparison
    standard_version = get_standard_agent_version()

    return AgentListResponse(
        agents=agent_responses,
        total=total,
        page=page,
        page_size=page_size,
        standard_version=standard_version,
    )


@router.post("", response_model=AgentWithToken, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentWithToken:
    """Create a new traffic agent and return its authentication token.

    The token is only shown once. Store it securely for use in the agent
    installation.
    """
    # Check for duplicate name
    existing = await db.execute(
        select(TrafficAgent).where(TrafficAgent.name == agent_data.name)
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            f"Agent with name '{agent_data.name}' already exists",
            details={"name": agent_data.name},
        )

    # Generate token
    token = generate_agent_token()
    token_hash = hash_token(token)

    # Create agent
    agent = TrafficAgent(
        name=agent_data.name,
        description=agent_data.description,
        default_interface=agent_data.default_interface,
        token_hash=token_hash,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    logger.info(f"Created agent: {agent.name} ({agent.id})")

    # Return with token
    response = AgentWithToken(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        default_interface=agent.default_interface,
        status=agent.status,
        version=agent.version,
        hostname=agent.hostname,
        platform=agent.platform,
        is_active=agent.is_active,
        last_seen=agent.last_seen,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        token=token,
    )
    return response


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Get details for a specific agent."""
    agent = await get_or_404(db, TrafficAgent, agent_id, "Agent")

    response = AgentResponse.model_validate(agent)

    # Enrich with real-time info
    if agent_manager.is_connected(agent.id):
        response.status = "online"
        conn = agent_manager.get_connection(agent.id)
        if conn:
            response.hostname = conn.hostname
            response.platform = conn.platform
            response.version = conn.version

    return response


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Update a traffic agent."""
    agent = await get_or_404(db, TrafficAgent, agent_id, "Agent")

    # Check for duplicate name if changing
    if agent_data.name and agent_data.name != agent.name:
        existing = await db.execute(
            select(TrafficAgent).where(
                TrafficAgent.name == agent_data.name,
                TrafficAgent.id != agent_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                f"Agent with name '{agent_data.name}' already exists",
                details={"name": agent_data.name},
            )

    # Update fields
    update_data = agent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)

    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a traffic agent."""
    agent = await get_or_404(db, TrafficAgent, agent_id, "Agent")

    # Disconnect if connected
    if agent_manager.is_connected(agent_id):
        conn = agent_manager.get_connection(agent_id)
        if conn:
            try:
                await conn.websocket.close(code=1000, reason="Agent deleted")
            except Exception:
                pass

    await db.delete(agent)
    await db.commit()

    logger.info(f"Deleted agent: {agent.name} ({agent.id})")


@router.post("/{agent_id}/token", response_model=AgentWithToken)
async def regenerate_agent_token(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentWithToken:
    """Regenerate the authentication token for an agent.

    This will invalidate the current token and disconnect the agent.
    """
    agent = await get_or_404(db, TrafficAgent, agent_id, "Agent")

    # Generate new token
    token = generate_agent_token()
    agent.token_hash = hash_token(token)

    await db.commit()
    await db.refresh(agent)

    # Disconnect existing connection
    if agent_manager.is_connected(agent_id):
        conn = agent_manager.get_connection(agent_id)
        if conn:
            try:
                await conn.websocket.close(code=4001, reason="Token regenerated")
            except Exception:
                pass

    logger.info(f"Regenerated token for agent: {agent.name}")

    return AgentWithToken(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        default_interface=agent.default_interface,
        status="offline",  # Will be offline after token change
        version=agent.version,
        hostname=agent.hostname,
        platform=agent.platform,
        is_active=agent.is_active,
        last_seen=agent.last_seen,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        token=token,
    )


@router.get("/{agent_id}/connection", response_model=AgentConnectionInfo)
async def get_agent_connection(agent_id: UUID) -> AgentConnectionInfo:
    """Get real-time connection info for a connected agent."""
    conn = agent_manager.get_connection(agent_id)

    if not conn:
        raise NotFoundError("Agent connection")

    return AgentConnectionInfo(
        agent_id=conn.agent_id,
        connected_at=conn.connected_at,
        last_heartbeat=conn.last_heartbeat,
        hostname=conn.hostname,
        platform=conn.platform,
        version=conn.version,
        cpu_percent=conn.cpu_percent,
        memory_percent=conn.memory_percent,
        running_scenarios=list(conn.running_scenarios),
    )


@router.get("/{agent_id}/interfaces", response_model=AgentInterfacesResponse)
async def get_agent_interfaces(agent_id: UUID) -> AgentInterfacesResponse:
    """Get network interfaces from a connected agent."""
    if not agent_manager.is_connected(agent_id):
        raise NotFoundError("Agent connection")

    try:
        interfaces = await agent_manager.list_interfaces(agent_id)
        return AgentInterfacesResponse(
            agent_id=agent_id,
            interfaces=[InterfaceInfo(**iface) for iface in interfaces],
        )
    except TimeoutError:
        raise ExternalServiceError(
            service="agent",
            message="Agent did not respond in time",
        )
    except RuntimeError as e:
        raise ExternalServiceError(
            service="agent",
            message=str(e),
            original_error=str(e),
        )


@router.post("/{agent_id}/deploy", response_model=DeploymentResponse)
async def deploy_scenario_to_agent(
    agent_id: UUID,
    deployment: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
) -> DeploymentResponse:
    """Deploy a scenario to an agent for traffic generation."""
    # Check agent exists and is active
    agent = await get_or_404(db, TrafficAgent, agent_id, "Agent")

    if not agent.is_active:
        raise ValidationError("Agent is not active")

    if not agent_manager.is_connected(agent_id):
        raise ValidationError("Agent is not connected")

    # Get scenario
    scenario = await get_or_404(db, Scenario, deployment.scenario_id, "Scenario")

    # Check for existing active deployment - prevent duplicates
    existing_result = await db.execute(
        select(AgentDeployment).where(
            AgentDeployment.agent_id == agent_id,
            AgentDeployment.scenario_id == scenario.id,
            AgentDeployment.state.in_(["starting", "running"]),
        )
    )
    existing_deployment = existing_result.scalars().first()

    if existing_deployment:
        logger.info(
            f"Reusing existing deployment {existing_deployment.id} for scenario {scenario.id}"
        )
        return DeploymentResponse.model_validate(existing_deployment)

    # Create deployment record
    interface = deployment.interface or agent.default_interface
    agent_deployment = AgentDeployment(
        agent_id=agent_id,
        scenario_id=scenario.id,
        interface=interface,
    )
    db.add(agent_deployment)
    await db.commit()
    await db.refresh(agent_deployment)

    # Send deployment command — merge overrides into definition
    definition = scenario.definition
    if deployment.adaptive_config:
        definition = {**definition}
        existing_adaptive = definition.get("adaptive_config", {})
        definition["adaptive_config"] = {**existing_adaptive, **deployment.adaptive_config}
    if deployment.attack_playbook:
        definition = {**definition} if definition is scenario.definition else definition
        definition["attack_playbook"] = deployment.attack_playbook

    success = await agent_manager.deploy_scenario(
        agent_id=agent_id,
        scenario_id=str(scenario.id),
        definition=definition,
        interface=interface,
    )

    if not success:
        agent_deployment.state = "error"
        agent_deployment.error_message = "Failed to send deployment command"
        await db.commit()
        raise ExternalServiceError(
            service="agent",
            message="Failed to send deployment command to agent",
        )

    logger.info(
        f"Deployed scenario {scenario.id} to agent {agent.name} on interface {interface}"
    )

    return DeploymentResponse.model_validate(agent_deployment)


@router.delete("/{agent_id}/deploy/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_deployment(
    agent_id: UUID,
    scenario_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Stop a running deployment."""
    # Find all matching deployments (handle duplicates gracefully)
    result = await db.execute(
        select(AgentDeployment).where(
            AgentDeployment.agent_id == agent_id,
            AgentDeployment.scenario_id == scenario_id,
            AgentDeployment.state.in_(["starting", "running"]),
        )
    )
    deployments = result.scalars().all()

    if not deployments:
        raise NotFoundError(
            "Active deployment not found",
            details={"agent_id": str(agent_id), "scenario_id": str(scenario_id)},
        )

    # Send stop command (only once)
    await agent_manager.stop_scenario(str(scenario_id))

    # Update all matching deployments to stopping state
    for deployment in deployments:
        deployment.state = "stopping"
    await db.commit()

    if len(deployments) > 1:
        logger.warning(
            f"Stopped {len(deployments)} duplicate deployments for scenario {scenario_id}"
        )


@router.post("/{agent_id}/stop-scenario/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_orphan_scenario(
    agent_id: UUID,
    scenario_id: UUID,
) -> None:
    """Stop an orphan scenario running on an agent (no deployment record required).

    This is useful when a scenario is running on an agent but the deployment
    record was lost (e.g., after backend restart).
    """
    # Verify agent is connected
    if not agent_manager.is_connected(agent_id):
        raise ExternalServiceError(
            service="agent",
            message="Agent is not connected",
        )

    # Send stop command directly
    success = await agent_manager.stop_scenario(str(scenario_id))
    if not success:
        raise NotFoundError("Running scenario on agent", str(scenario_id))

    logger.info(f"Stopped orphan scenario {scenario_id} on agent {agent_id}")


@router.get("/{agent_id}/deployments", response_model=list[DeploymentResponse])
async def list_agent_deployments(
    agent_id: UUID,
    active_only: bool = Query(True, description="Only show active deployments"),
    db: AsyncSession = Depends(get_db),
) -> list[DeploymentResponse]:
    """List deployments for an agent."""
    query = select(AgentDeployment).where(AgentDeployment.agent_id == agent_id)

    if active_only:
        query = query.where(AgentDeployment.state.in_(["starting", "running"]))

    query = query.order_by(AgentDeployment.started_at.desc())

    result = await db.execute(query)
    deployments = result.scalars().all()

    return [DeploymentResponse.model_validate(d) for d in deployments]


@router.post("/{agent_id}/update")
async def trigger_agent_update(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger an update on a connected agent.

    Sends an UPDATE command to the agent, which will:
    1. Download the latest image from this server
    2. Load the new image
    3. Restart with the new version
    """
    # Check agent exists
    agent = await get_or_404(db, TrafficAgent, agent_id, "Agent")

    if not agent_manager.is_connected(agent_id):
        raise ValidationError("Agent is not connected")

    # Check image is available
    if not AGENT_IMAGE_PATH.exists():
        raise ValidationError("Agent image not available. Build it first with POST /api/v1/agents/build-image")

    # Get target version
    target_version = get_standard_agent_version()

    # Send update command with version tracking
    success = await agent_manager.send_update_command(agent_id, target_version)

    if not success:
        raise ExternalServiceError(
            service="agent",
            message="Failed to send update command to agent",
        )

    logger.info(f"Sent update command to agent {agent.name}")

    return {
        "status": "update_triggered",
        "message": f"Update command sent to agent {agent.name}. Agent will download and restart.",
        "target_version": target_version,
    }


@router.get("/{agent_id}/update-status", response_model=AgentUpdateStatus)
async def get_agent_update_status(agent_id: UUID) -> AgentUpdateStatus:
    """Get the current update status for an agent.

    This endpoint allows the UI to poll for update progress after triggering
    an update. Returns the current status including download progress,
    load status, and completion/failure information.
    """
    status_obj = agent_manager.get_update_status(agent_id)

    return AgentUpdateStatus(
        agent_id=status_obj.agent_id,
        status=status_obj.status,
        progress=status_obj.progress,
        message=status_obj.message,
        target_version=status_obj.target_version,
        initiated_at=status_obj.initiated_at,
        completed_at=status_obj.completed_at,
        error=status_obj.error,
    )


@router.delete("/{agent_id}/update-status", status_code=status.HTTP_204_NO_CONTENT)
async def clear_agent_update_status(agent_id: UUID) -> None:
    """Clear the update status for an agent.

    Call this after the user has acknowledged an update completion or failure.
    """
    agent_manager.clear_update_status(agent_id)


@router.get("/{agent_id}/logs")
async def get_agent_logs(
    agent_id: UUID,
    lines: int = Query(100, ge=1, le=1000, description="Number of log lines to retrieve"),
) -> dict:
    """Get recent logs from a connected agent.

    Retrieves the last N lines of agent container logs for troubleshooting.
    Requires the agent to be online and connected.
    """
    if not agent_manager.is_connected(agent_id):
        raise NotFoundError("Agent connection")

    try:
        logs = await agent_manager.request_logs(agent_id, lines=lines)
        return {
            "agent_id": str(agent_id),
            "logs": logs,
            "count": len(logs),
        }
    except TimeoutError:
        raise ExternalServiceError(
            service="agent",
            message="Agent did not respond in time",
        )
    except RuntimeError as e:
        raise ExternalServiceError(
            service="agent",
            message=str(e),
            original_error=str(e),
        )


@router.post("/{agent_id}/ping")
async def ping_agent_test(agent_id: UUID) -> dict:
    """Test connectivity to an agent and measure latency.

    Sends a timestamped ping to the agent and measures round-trip time.
    Useful for diagnosing connectivity issues.
    """
    if not agent_manager.is_connected(agent_id):
        raise NotFoundError("Agent connection")

    try:
        timing = await agent_manager.ping_with_timing(agent_id)
        return {
            "agent_id": str(agent_id),
            "status": "ok",
            "round_trip_ms": round(timing["round_trip_ms"], 2),
            "server_to_agent_ms": round(timing["server_to_agent_ms"], 2),
            "agent_to_server_ms": round(timing["agent_to_server_ms"], 2),
        }
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Agent did not respond to ping",
        )
    except RuntimeError as e:
        raise ExternalServiceError(
            service="agent",
            message=str(e),
            original_error=str(e),
        )
