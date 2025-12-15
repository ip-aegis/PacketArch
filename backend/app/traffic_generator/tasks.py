"""Celery tasks for traffic generation."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from celery import Celery, Task
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.scenario import Scenario
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

# In-memory job storage (in production, use Redis or database)
_job_store: dict[str, GenerationJob] = {}


def get_job(job_id: str) -> GenerationJob | None:
    """Get job by ID.

    Args:
        job_id: Job identifier

    Returns:
        GenerationJob or None if not found
    """
    return _job_store.get(job_id)


def update_job(job: GenerationJob) -> None:
    """Update job in store.

    Args:
        job: Job to update
    """
    _job_store[job.job_id] = job


def create_job(
    scenario_id: uuid.UUID,
    user_id: uuid.UUID | None,
    total_duration_ms: int,
) -> GenerationJob:
    """Create a new generation job.

    Args:
        scenario_id: Scenario UUID
        user_id: User UUID
        total_duration_ms: Total duration in milliseconds

    Returns:
        Created GenerationJob
    """
    job_id = str(uuid.uuid4())

    job = GenerationJob(
        job_id=job_id,
        scenario_id=scenario_id,
        user_id=user_id,
        status=JobStatus.PENDING,
        total_duration_ms=total_duration_ms,
    )

    _job_store[job_id] = job
    return job


class CallbackTask(Task):
    """Task with callbacks for job status updates."""

    def on_success(self, retval, task_id, args, kwargs):
        """Handle successful task completion."""
        job_id = kwargs.get("job_id")
        if job_id and job_id in _job_store:
            job = _job_store[job_id]
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()

            if isinstance(retval, dict):
                job.packets_generated = retval.get("packets_generated", 0)
                job.file_size_bytes = retval.get("file_size_bytes", 0)
                job.output_path = retval.get("pcap_path")

            logger.info(f"Job {job_id} completed successfully")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        job_id = kwargs.get("job_id")
        if job_id and job_id in _job_store:
            job = _job_store[job_id]
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = str(exc)

            logger.error(f"Job {job_id} failed: {exc}")


@celery_app.task(bind=True, base=CallbackTask, name="packetarch.generate_traffic")
def generate_traffic(self, job_id: str, scenario_id: str, duration_ms: int | None = None):
    """Generate traffic for a scenario.

    Args:
        self: Task instance
        job_id: Job identifier
        scenario_id: Scenario UUID string
        duration_ms: Optional duration override in milliseconds

    Returns:
        Dictionary with generation results
    """
    import asyncio

    logger.info(f"Starting traffic generation task for job {job_id}")

    # Update job status
    job = get_job(job_id)
    if job:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        update_job(job)

    # Run async generation
    result = asyncio.run(_generate_traffic_async(job_id, scenario_id, duration_ms))

    return result


async def _generate_traffic_async(
    job_id: str,
    scenario_id: str,
    duration_ms: int | None = None,
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
        # Load scenario from database
        async with async_session_maker() as session:
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
            )

            # Create orchestrator
            orchestrator = TrafficOrchestrator(config)

            # Build flow contexts from scenario definition
            flow_contexts = _build_flow_contexts(scenario.definition)

            # Add flows to orchestrator
            for flow_context in flow_contexts:
                orchestrator.add_flow(flow_context)

            # Generate traffic
            logger.info(f"Starting traffic generation for {len(flow_contexts)} flows")
            generation_result = orchestrator.generate()

            # Update job with results
            job = get_job(job_id)
            if job:
                job.output_path = generation_result.pcap_path
                job.packets_generated = generation_result.packets_generated
                job.file_size_bytes = generation_result.file_size_bytes
                job.progress = 100.0
                update_job(job)

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


def _build_flow_contexts(scenario_definition: dict) -> list[FlowContext]:
    """Build flow contexts from scenario definition.

    Args:
        scenario_definition: Scenario definition dictionary
            Supports both formats:
            - Array format: {"devices": [...], "flows": [...]}
            - Record/Object format: {"devices": {id: {...}, ...}, "flows": {id: {...}, ...}}

    Returns:
        List of FlowContext objects
    """
    flow_contexts = []

    devices_raw = scenario_definition.get("devices", {})
    flows_raw = scenario_definition.get("flows", {})

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
        destination_id = flow.get("destination_device_id") or flow.get("destinationDeviceId") or flow.get("target")

        if not source_id or not destination_id:
            logger.warning(f"Flow missing source or destination: {flow}")
            continue

        source_device = device_map.get(source_id)
        destination_device = device_map.get(destination_id)

        if not source_device or not destination_device:
            logger.warning(f"Device not found for flow: {flow}")
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

        # Build device contexts with CVE vulnerability overrides
        source_context = DeviceContext(
            device_id=source_device["id"],
            mac_address=get_network_field(source_device, "mac_address", "00:00:00:00:00:01"),
            ip_address=get_network_field(source_device, "ip_address", "192.168.1.1"),
            port=flow.get("source_port") or flow.get("sourcePort", 50000),
            unit_id=source_device.get("unit_id") or source_device.get("unitId"),
            vendor_fingerprint=source_device.get("vendor_fingerprint") or source_device.get("vendorFingerprint", {}),
            # Pass CVE identity overrides for vulnerable firmware emulation
            vulnerability_override=get_cve_overrides(source_device),
        )

        destination_context = DeviceContext(
            device_id=destination_device["id"],
            mac_address=get_network_field(destination_device, "mac_address", "00:00:00:00:00:02"),
            ip_address=get_network_field(destination_device, "ip_address", "192.168.1.2"),
            port=flow.get("destination_port") or flow.get("destinationPort", 502),
            unit_id=destination_device.get("unit_id") or destination_device.get("unitId", 1),
            vendor_fingerprint=destination_device.get("vendor_fingerprint") or destination_device.get("vendorFingerprint", {}),
            # Pass CVE identity overrides for vulnerable firmware emulation
            vulnerability_override=get_cve_overrides(destination_device),
        )

        # Get protocol
        protocol_str = flow.get("protocol", "modbus_tcp")
        try:
            protocol = ProtocolType(protocol_str)
        except ValueError:
            logger.warning(f"Unsupported protocol: {protocol_str}")
            continue

        # Build flow context
        flow_context = FlowContext(
            flow_id=flow.get("id", str(uuid.uuid4())),
            source=source_context,
            destination=destination_context,
            protocol=protocol,
            config=flow.get("config", {}),
            timing_model=flow.get("timing_model", {}),
            payload_template=flow.get("payload_template"),
        )

        flow_contexts.append(flow_context)

    return flow_contexts
