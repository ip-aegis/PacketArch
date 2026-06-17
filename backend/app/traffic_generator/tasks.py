# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Celery tasks for traffic generation."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from celery import Celery, Task
from sqlalchemy import select, update

from app.core.config import settings
from app.models.scenario import Scenario
from app.models.generation_job import GenerationJob as GenerationJobModel, GenerationJobStatus
from app.protocol_engines.cell_isolation import parse_config as parse_isolation_config, should_drop_flow as should_drop_for_isolation
from app.protocol_engines.protocols import get_default_port, resolve_protocol
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType
from app.traffic_generator.models import GenerationJob, JobStatus
from app.traffic_generator.orchestrator import GenerationConfig, TrafficOrchestrator

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "packetarch",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
)


def _get_celery_session_maker():
    """Get a session maker for use in Celery tasks.

    Creates a new engine and session maker to avoid event loop conflicts.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(
        settings.async_database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_job_from_db(job_id: str) -> GenerationJobModel | None:
    """Get job from database by ID.

    Args:
        job_id: Job identifier (UUID string)

    Returns:
        GenerationJobModel or None if not found
    """
    session_maker = _get_celery_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(GenerationJobModel).where(GenerationJobModel.id == uuid.UUID(job_id))
        )
        return result.scalar_one_or_none()


async def update_job_in_db(
    job_id: str,
    **kwargs,
) -> None:
    """Update job in database.

    Args:
        job_id: Job identifier (UUID string)
        **kwargs: Fields to update
    """
    session_maker = _get_celery_session_maker()
    async with session_maker() as session:
        await session.execute(
            update(GenerationJobModel)
            .where(GenerationJobModel.id == uuid.UUID(job_id))
            .values(**kwargs)
        )
        await session.commit()


async def create_job_in_db(
    scenario_id: uuid.UUID,
    user_id: uuid.UUID | None,
    total_duration_ms: int,
) -> GenerationJobModel:
    """Create a new generation job in database.

    Args:
        scenario_id: Scenario UUID
        user_id: User UUID
        total_duration_ms: Total duration in milliseconds

    Returns:
        Created GenerationJobModel
    """
    session_maker = _get_celery_session_maker()
    async with session_maker() as session:
        job = GenerationJobModel(
            scenario_id=scenario_id,
            user_id=user_id,
            status=GenerationJobStatus.PENDING.value,
            total_duration_ms=total_duration_ms,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


# Keep synchronous wrappers for backward compatibility with existing code
def get_job(job_id: str) -> GenerationJob | None:
    """Get job by ID (synchronous wrapper).

    Args:
        job_id: Job identifier

    Returns:
        GenerationJob dataclass or None if not found
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    db_job = loop.run_until_complete(get_job_from_db(job_id))
    if not db_job:
        return None

    return GenerationJob(
        job_id=str(db_job.id),
        scenario_id=db_job.scenario_id,
        user_id=db_job.user_id,
        status=JobStatus(db_job.status),
        progress=db_job.progress,
        total_duration_ms=db_job.total_duration_ms,
        output_path=db_job.output_path,
        packets_generated=db_job.packets_generated,
        file_size_bytes=db_job.file_size_bytes,
        error_message=db_job.error_message,
        started_at=db_job.started_at,
        completed_at=db_job.completed_at,
    )


def update_job(job: GenerationJob) -> None:
    """Update job in store (synchronous wrapper).

    Args:
        job: Job to update
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Extract filename from output_path
    output_filename = None
    if job.output_path:
        output_filename = Path(job.output_path).name

    loop.run_until_complete(update_job_in_db(
        job.job_id,
        status=job.status.value,
        progress=job.progress,
        packets_generated=job.packets_generated,
        file_size_bytes=job.file_size_bytes,
        output_filename=output_filename,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
    ))


def create_job(
    scenario_id: uuid.UUID,
    user_id: uuid.UUID | None,
    total_duration_ms: int,
) -> GenerationJob:
    """Create a new generation job (synchronous wrapper).

    Args:
        scenario_id: Scenario UUID
        user_id: User UUID
        total_duration_ms: Total duration in milliseconds

    Returns:
        Created GenerationJob dataclass
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    db_job = loop.run_until_complete(create_job_in_db(
        scenario_id=scenario_id,
        user_id=user_id,
        total_duration_ms=total_duration_ms,
    ))

    return GenerationJob(
        job_id=str(db_job.id),
        scenario_id=db_job.scenario_id,
        user_id=db_job.user_id,
        status=JobStatus(db_job.status),
        total_duration_ms=db_job.total_duration_ms,
    )


class CallbackTask(Task):
    """Task with callbacks for job status updates."""

    def on_success(self, retval, task_id, args, kwargs):
        """Handle successful task completion."""
        import asyncio

        job_id = kwargs.get("job_id")
        if job_id:
            # Always create a new event loop for callbacks
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                update_data = {
                    "status": GenerationJobStatus.COMPLETED.value,
                    "completed_at": datetime.utcnow(),
                    "progress": 100.0,
                }

                if isinstance(retval, dict):
                    update_data["packets_generated"] = retval.get("packets_generated", 0)
                    update_data["file_size_bytes"] = retval.get("file_size_bytes", 0)
                    if retval.get("pcap_path"):
                        update_data["output_filename"] = Path(retval["pcap_path"]).name

                loop.run_until_complete(update_job_in_db(job_id, **update_data))
                logger.info(f"Job {job_id} completed successfully")
            finally:
                loop.close()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        import asyncio

        job_id = kwargs.get("job_id")
        if job_id:
            # Always create a new event loop for callbacks
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(update_job_in_db(
                    job_id,
                    status=GenerationJobStatus.FAILED.value,
                    completed_at=datetime.utcnow(),
                    error_message=str(exc),
                ))
                logger.error(f"Job {job_id} failed: {exc}")
            finally:
                loop.close()


@celery_app.task(bind=True, base=CallbackTask, name="packetarch.generate_traffic")
def generate_traffic(
    self,
    job_id: str,
    scenario_id: str,
    duration_ms: int | None = None,
    attack_playbook_id: str | None = None,
    attack_config: dict[str, Any] | None = None,
    adaptive_config: dict[str, Any] | None = None,
    cell_isolation_override: dict[str, Any] | None = None,
):
    """Generate traffic for a scenario.

    Args:
        self: Task instance
        job_id: Job identifier
        scenario_id: Scenario UUID string
        duration_ms: Optional duration override in milliseconds
        attack_playbook_id: Optional playbook id for in-PCAP attack simulation
        attack_config: Optional attack config overrides
        adaptive_config: Optional adaptive-traffic config dict

    Returns:
        Dictionary with generation results
    """
    import asyncio

    logger.info(f"Starting traffic generation task for job {job_id}")

    # Create new event loop for this task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Update job status to running
        loop.run_until_complete(update_job_in_db(
            job_id,
            status=GenerationJobStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        ))

        # Run async generation
        result = loop.run_until_complete(
            _generate_traffic_async(
                job_id,
                scenario_id,
                duration_ms,
                attack_playbook_id=attack_playbook_id,
                attack_config=attack_config,
                adaptive_config=adaptive_config,
                cell_isolation_override=cell_isolation_override,
            )
        )
        return result
    finally:
        loop.close()


async def _generate_traffic_async(
    job_id: str,
    scenario_id: str,
    duration_ms: int | None = None,
    attack_playbook_id: str | None = None,
    attack_config: dict[str, Any] | None = None,
    adaptive_config: dict[str, Any] | None = None,
    cell_isolation_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Async function to generate traffic.

    Args:
        job_id: Job identifier
        scenario_id: Scenario UUID string
        duration_ms: Optional duration override

    Returns:
        Dictionary with generation results
    """
    try:
        # Load scenario from database using Celery-safe session maker
        session_maker = _get_celery_session_maker()
        async with session_maker() as session:
            result = await session.execute(
                select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
            )
            scenario = result.scalar_one_or_none()

            if not scenario:
                raise ValueError(f"Scenario {scenario_id} not found")

            # Use scenario duration or override
            total_duration_ms = duration_ms or scenario.total_duration_ms

            # Build output path
            output_dir = Path(settings.pcap_output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_filename = f"scenario_{scenario.id}_{job_id[:8]}.pcap"
            output_path = output_dir / output_filename

            # Create generation config
            config = GenerationConfig(
                job_id=job_id,
                scenario_id=scenario.id,
                total_duration_ms=total_duration_ms,
                output_path=output_path,
                attack_playbook_id=attack_playbook_id,
                attack_config=attack_config,
                adaptive_config=adaptive_config,
                broadcast_traffic_enabled=bool(
                    scenario.definition.get("broadcast_traffic_enabled", True)
                ),
                clean_demo_mode=bool(
                    scenario.definition.get("clean_demo_mode", False)
                ),
            )

            # Create orchestrator
            orchestrator = TrafficOrchestrator(config)

            # Build flow contexts from scenario definition. Per-run
            # cell-isolation override (if any) is merged into a copy of the
            # definition so the saved scenario isn't mutated.
            effective_definition = scenario.definition
            if cell_isolation_override:
                effective_definition = {**scenario.definition}
                existing = effective_definition.get("cell_isolation", {})
                effective_definition["cell_isolation"] = {
                    **existing,
                    **cell_isolation_override,
                }

            # Mirror the agent's deploy-time enrichment chain. Live + PCAP
            # parity: any change to the live deploy path's enrichment
            # sequence here must be mirrored in routes/agents.py.
            from app.services.scenario_enrichment import (
                auto_repair_protocols,
                ensure_device_flow_coverage,
                ensure_remote_access_cloud_links,
                repair_flow_protocols,
            )
            # Defense-in-depth: legacy scenarios may have protocol/fingerprint
            # mismatches and flow-protocol mismatches; repair before
            # generating traffic.
            effective_definition = auto_repair_protocols(effective_definition)
            effective_definition = repair_flow_protocols(effective_definition)
            # Auto-attach cloud links for EWON / jump server / remote
            # gateway / cloud connector devices.
            effective_definition = await ensure_remote_access_cloud_links(
                session, effective_definition
            )
            # And guarantee every device has at least one flow so CV /
            # downstream tools can fingerprint it. Same pass that runs on
            # the live deploy path; live + PCAP parity.
            effective_definition = await ensure_device_flow_coverage(
                effective_definition
            )

            flow_contexts = _build_flow_contexts(
                effective_definition, str(scenario.id), vertical=scenario.vertical
            )

            # Append cloud-service-link flows so PCAP captures heartbeat
            # traffic from EWON / jump server / cloud-connector devices.
            cloud_links = effective_definition.get("cloud_service_links", []) or []
            cloud_devices_raw = effective_definition.get("devices", {})
            if isinstance(cloud_devices_raw, list):
                cloud_devices = {
                    d.get("id", str(i)): d for i, d in enumerate(cloud_devices_raw)
                }
            else:
                cloud_devices = cloud_devices_raw
            for link in cloud_links:
                if not link.get("enabled", True):
                    continue
                cloud_ctx = _build_cloud_flow_context(link, cloud_devices)
                if cloud_ctx is not None:
                    flow_contexts.append(cloud_ctx)

            # Add flows to orchestrator
            for flow_context in flow_contexts:
                orchestrator.add_flow(flow_context)

            # Generate traffic
            logger.info(f"Starting traffic generation for {len(flow_contexts)} flows")
            generation_result = orchestrator.generate()

            # Update job with results in database
            await update_job_in_db(
                job_id,
                output_filename=Path(generation_result.pcap_path).name if generation_result.pcap_path else None,
                packets_generated=generation_result.packets_generated,
                file_size_bytes=generation_result.file_size_bytes,
                progress=100.0,
            )

            return {
                "job_id": job_id,
                "scenario_id": scenario_id,
                "status": generation_result.status.value,
                "pcap_path": generation_result.pcap_path,
                "packets_generated": generation_result.packets_generated,
                "file_size_bytes": generation_result.file_size_bytes,
            }

    except Exception as e:
        logger.error(f"Error in traffic generation: {e}", exc_info=True)
        raise


def _build_flow_contexts(
    scenario_definition: dict,
    scenario_id: str | None = None,
    vertical: str | None = None,
) -> list[FlowContext]:
    """Build flow contexts from scenario definition.

    Args:
        scenario_definition: Scenario definition dictionary
            Supports both formats:
            - Array format: {"devices": [...], "flows": [...]}
            - Record/Object format: {"devices": {id: {...}, ...}, "flows": {id: {...}, ...}}
        scenario_id: Scenario identifier for unique serial number generation.
                    When provided, each device gets a deterministic unique serial.

    Returns:
        List of FlowContext objects
    """
    flow_contexts = []

    devices_raw = scenario_definition.get("devices", {})
    flows_raw = scenario_definition.get("flows", {})
    zones_raw = scenario_definition.get("zones", {})
    conduits_raw = scenario_definition.get("conduits", {})
    clean_demo_mode = bool(scenario_definition.get("clean_demo_mode", False))
    isolation = parse_isolation_config(scenario_definition)

    # Normalize to list format - support both Record<id, obj> and array formats
    if isinstance(devices_raw, dict):
        # Record format: {id: {device data}}
        devices = list(devices_raw.values())
    else:
        # Array format: [{device data}, ...]
        devices = devices_raw

    if isinstance(flows_raw, dict):
        # Record format: {id: {flow data}}
        flows = list(flows_raw.values())
    else:
        # Array format: [{flow data}, ...]
        flows = flows_raw

    # Create device lookup
    device_map = {}
    for device in devices:
        device_id = device.get("id") or device.get("deviceId")
        if device_id:
            device_map[device_id] = device

    # Build flow contexts
    for flow in flows:
        # Support both naming conventions
        source_id = flow.get("source_device_id") or flow.get("sourceDeviceId") or flow.get("source")
        destination_id = flow.get("destination_device_id") or flow.get("destinationDeviceId") or flow.get("targetDeviceId") or flow.get("target")

        if not source_id or not destination_id:
            logger.warning(f"Flow missing source or destination: {flow}")
            continue

        source_device = device_map.get(source_id)
        destination_device = device_map.get(destination_id)

        if not source_device or not destination_device:
            logger.warning(f"Device not found for flow: {flow}")
            continue

        # Purdue cell-isolation gate. When the scenario is in conduit_gated
        # or strict_northbound mode, drop east/west cell traffic before it
        # ever produces packets — Cyber Vision then sees no such connection.
        drop, reason = should_drop_for_isolation(
            flow, devices_raw, zones_raw, conduits_raw, isolation,
        )
        if drop:
            logger.info(
                f"[cell-isolation] flow {flow.get('id')} dropped: {reason}"
            )
            continue

        # Extract network info (support both nested and flat formats)
        def get_network_field(device: dict, field: str, default: str) -> str:
            """Get network field from device, supporting nested and flat formats."""
            # Try nested format first (from frontend): network.ipAddress
            network = device.get("network", {})
            camel_field = "".join(
                word.capitalize() if i > 0 else word
                for i, word in enumerate(field.split("_"))
            )
            if network.get(camel_field):
                return network[camel_field]
            # Try flat format: ip_address or ipAddress
            if device.get(field):
                return device[field]
            if device.get(camel_field):
                return device[camel_field]
            return default

        # Get CVE identity overrides (support both camelCase and snake_case)
        def get_cve_overrides(device: dict) -> dict | None:
            """Get CVE identity overrides from device."""
            return (
                device.get("cveIdentityOverrides")
                or device.get("cve_identity_overrides")
            )

        # Helper to get device name with fallback
        def get_device_name(device: dict) -> str | None:
            """Get device name from device dict."""
            return device.get("name") or device.get("label")

        def get_fingerprint_with_warning(device: dict, device_role: str) -> dict:
            """Get vendor fingerprint from device, warn if empty."""
            fp = device.get("vendor_fingerprint") or device.get("vendorFingerprint", {})
            if not fp:
                device_name = get_device_name(device) or device.get("id", "unknown")
                logger.warning(
                    f"Device '{device_name}' ({device_role}) has no vendor_fingerprint - "
                    f"protocol identity responses will use generic defaults. "
                    f"Ensure fingerprint_model is set and fingerprint data is passed from frontend."
                )
            return fp

        # Resolve protocol FIRST so we can compute the protocol-correct
        # default destination port. Without this, every non-Modbus flow
        # ends up framed in TCP/502 packets and CV/Wireshark dissect the
        # payloads as malformed Modbus.
        raw_protocol = flow.get("protocol", "modbus_tcp")
        protocol_str = resolve_protocol(raw_protocol)
        try:
            protocol = ProtocolType(protocol_str)
        except ValueError:
            logger.warning(
                f"Unsupported protocol: {raw_protocol!r} "
                f"(resolved to {protocol_str!r}) — flow {flow.get('id')} dropped"
            )
            continue

        # Per-protocol destination port (4840 for OPC UA, 102 for S7comm,
        # 44818 for EtherNet/IP, etc.). Explicit `destination_port` on the
        # flow spec always wins; the protocol default is the fallback.
        default_dst_port = get_default_port(protocol_str)
        explicit_dst_port = (
            flow.get("destination_port") or flow.get("destinationPort")
        )
        dst_port = explicit_dst_port if explicit_dst_port else default_dst_port

        # Build device contexts with CVE vulnerability overrides and scenario_id
        # for unique serial number and identifier generation
        source_context = DeviceContext(
            device_id=source_device["id"],
            mac_address=get_network_field(source_device, "mac_address", "02:00:00:00:00:01"),
            ip_address=get_network_field(source_device, "ip_address", "192.168.1.1"),
            port=flow.get("source_port") or flow.get("sourcePort", 50000),
            unit_id=source_device.get("unit_id") or source_device.get("unitId"),
            vendor_fingerprint=get_fingerprint_with_warning(source_device, "source"),
            # Pass CVE identity overrides for vulnerable firmware emulation
            vulnerability_override=get_cve_overrides(source_device),
            # Pass scenario_id for unique serial number generation
            scenario_id=scenario_id,
            # Pass device_name for unique identifier generation
            device_name=get_device_name(source_device),
        )

        destination_context = DeviceContext(
            device_id=destination_device["id"],
            mac_address=get_network_field(destination_device, "mac_address", "02:00:00:00:00:02"),
            ip_address=get_network_field(destination_device, "ip_address", "192.168.1.2"),
            port=dst_port,
            unit_id=destination_device.get("unit_id") or destination_device.get("unitId", 1),
            vendor_fingerprint=get_fingerprint_with_warning(destination_device, "destination"),
            # Pass CVE identity overrides for vulnerable firmware emulation
            vulnerability_override=get_cve_overrides(destination_device),
            # Pass scenario_id for unique serial number generation
            scenario_id=scenario_id,
            # Pass device_name for unique identifier generation
            device_name=get_device_name(destination_device),
        )

        # Build flow context (inject vertical for PayloadGenerator auto-selection)
        flow_config = flow.get("config", {})
        if vertical:
            flow_config = {**flow_config, "_vertical": vertical}
        if clean_demo_mode:
            flow_config = {**flow_config, "clean_demo_mode": True}

        flow_context = FlowContext(
            flow_id=flow.get("id", str(uuid.uuid4())),
            source=source_context,
            destination=destination_context,
            protocol=protocol,
            config=flow_config,
            timing_model=flow.get("timing_model", {}),
            payload_template=flow.get("payload_template"),
        )

        flow_contexts.append(flow_context)

    return flow_contexts


def _build_cloud_flow_context(
    link: dict[str, Any],
    devices: dict[str, dict[str, Any]],
) -> FlowContext | None:
    """Build a FlowContext for a cloud_service_link.

    Mirrors the agent's `OrchestratorPool._create_cloud_flow` so PCAP
    output captures the same heartbeat traffic the live deployment emits
    (EWON Talk2M, TeamViewer, Azure IoT, etc.).
    """
    device_id = link.get("device_id")
    device = devices.get(device_id) if device_id else None
    if not device:
        logger.warning(
            f"Device {device_id!r} not found for cloud link {link.get('id')}"
        )
        return None

    network = device.get("network", {})
    src_mac = (
        network.get("macAddress")
        or network.get("mac_address")
        or device.get("mac_address")
        or "00:00:00:00:00:01"
    )
    src_ip = (
        network.get("ipAddress")
        or network.get("ip_address")
        or device.get("ip_address")
        or "10.0.0.1"
    )

    cloud_svc = link.get("cloud_service") or {}
    dst_ip = cloud_svc.get("primary_ip") or link.get("cloud_ip") or "0.0.0.0"
    dst_port = cloud_svc.get("port") or link.get("port") or 443

    source = DeviceContext(
        device_id=str(device_id),
        mac_address=src_mac,
        ip_address=src_ip,
        port=0,
    )
    # Cloud endpoint has no scenario MAC; use broadcast MAC as a marker —
    # the engine routes by IP, MAC is informational here.
    destination = DeviceContext(
        device_id=f"cloud-{link.get('id', 'unknown')}",
        mac_address="ff:ff:ff:ff:ff:ff",
        ip_address=dst_ip,
        port=dst_port,
    )

    interval_ms = link.get("heartbeat_interval_ms") or link.get("interval_ms") or 30000

    return FlowContext(
        flow_id=f"cloud-{link.get('id', device_id)}",
        source=source,
        destination=destination,
        protocol=ProtocolType.CLOUD_SERVICE,
        config={
            "hostname": cloud_svc.get("hostname") or link.get("hostname", ""),
            "tls_enabled": cloud_svc.get("tls_enabled", link.get("tls_enabled", True)),
        },
        timing_model={"poll_interval_ms": interval_ms},
    )


@celery_app.task(bind=True, name="packetarch.provision_cyber_vision")
def provision_cyber_vision(
    self,
    scenario_id: str,
    poll: bool = True,
    max_polls: int = 15,
    interval_seconds: int = 60,
    attempt: int = 1,
    max_attempts: int = 8,
    retry_countdown: int = 300,
):
    """Poll Cyber Vision and create one group per scenario zone.

    Enqueued (typically with a countdown) after a CV preset has been created
    for the scenario. Polls the preset until the discovered-device count
    stabilises, then creates/assigns CV groups from the scenario's zones.

    Because Cyber Vision's device aggregation can lag a fresh deployment by
    well over the active poll window, the task RE-ARMS itself (up to
    ``max_attempts``) whenever CV hasn't surfaced any of the scenario's devices
    yet — so groups eventually populate without an operator re-click.

    Args:
        scenario_id: Scenario UUID string.
        poll: Whether to poll-until-stable before creating groups.
        max_polls: Max poll iterations per attempt.
        interval_seconds: Seconds between polls.
        attempt: 1-based attempt counter (for self re-arm).
        max_attempts: Max total attempts before giving up.
        retry_countdown: Seconds to wait before re-arming when CV is still empty.
    """
    import asyncio

    from app.services.cv_provisioning_service import provision_groups

    async def _run() -> dict:
        session_maker = _get_celery_session_maker()
        async with session_maker() as session:
            return await provision_groups(
                session,
                uuid.UUID(scenario_id),
                poll=poll,
                max_polls=max_polls,
                interval_seconds=interval_seconds,
            )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_run())
        # Re-arm if CV hasn't discovered any devices yet (status stayed "polling").
        if (
            isinstance(result, dict)
            and result.get("status") == "polling"
            and int(result.get("device_count") or 0) == 0
            and attempt < max_attempts
        ):
            logger.info(
                f"CV provisioning scenario {scenario_id}: no devices yet "
                f"(attempt {attempt}/{max_attempts}) — re-arming in {retry_countdown}s"
            )
            provision_cyber_vision.apply_async(
                kwargs={
                    "scenario_id": scenario_id,
                    "poll": poll,
                    "max_polls": max_polls,
                    "interval_seconds": interval_seconds,
                    "attempt": attempt + 1,
                    "max_attempts": max_attempts,
                    "retry_countdown": retry_countdown,
                },
                countdown=retry_countdown,
            )
        else:
            logger.info(f"CV provisioning task complete for scenario {scenario_id}")
        return result
    except Exception:
        logger.exception(f"CV provisioning task failed for scenario {scenario_id}")
        raise
    finally:
        loop.close()
