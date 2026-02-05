"""Celery tasks for PCAP learning and analysis."""

import logging
import uuid
from datetime import datetime
from typing import Any

from celery import Task

from app.ai_services.pcap_analyzer import PcapAnalyzer
from app.core.database import async_session_maker
from app.models.device_template import DeviceTemplate, TemplateSource
from app.models.learned_pattern import DistributionType, LearnedPattern, PatternType
from app.models.learned_protocol_pattern import LearnedProtocolPattern
from app.models.learned_sequence import LearnedSequence
from app.models.pcap_capture import PcapCapture, ProcessingStatus
from app.traffic_generator.tasks import celery_app
from sqlalchemy import select

logger = logging.getLogger(__name__)


class PcapProcessingJob:
    """Tracks PCAP processing job state."""

    def __init__(
        self,
        job_id: str,
        capture_id: str,
        status: str = "pending",
    ):
        self.job_id = job_id
        self.capture_id = capture_id
        self.status = status
        self.progress: float = 0.0
        self.stage: str = ""
        self.error_message: str | None = None
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.packets_analyzed: int = 0
        self.patterns_extracted: int = 0
        self.fingerprints_extracted: int = 0
        self.sequences_extracted: int = 0


# In-memory job storage (for progress tracking)
_pcap_job_store: dict[str, PcapProcessingJob] = {}


def get_pcap_job(job_id: str) -> PcapProcessingJob | None:
    """Get PCAP processing job by ID."""
    return _pcap_job_store.get(job_id)


def update_pcap_job(job: PcapProcessingJob) -> None:
    """Update PCAP job in store."""
    _pcap_job_store[job.job_id] = job


def create_pcap_job(capture_id: str) -> PcapProcessingJob:
    """Create a new PCAP processing job."""
    job_id = str(uuid.uuid4())
    job = PcapProcessingJob(
        job_id=job_id,
        capture_id=capture_id,
    )
    _pcap_job_store[job_id] = job
    return job


class PcapProcessingTask(Task):
    """Task with callbacks for PCAP processing status updates."""

    def on_success(self, retval, task_id, args, kwargs):
        """Handle successful task completion."""
        job_id = kwargs.get("job_id")
        if job_id and job_id in _pcap_job_store:
            job = _pcap_job_store[job_id]
            job.status = "completed"
            job.progress = 100.0
            job.completed_at = datetime.utcnow()
            if isinstance(retval, dict):
                job.patterns_extracted = retval.get("patterns_count", 0)
                job.fingerprints_extracted = retval.get("fingerprints_count", 0)
                job.sequences_extracted = retval.get("sequences_count", 0)
            logger.info(f"PCAP processing job {job_id} completed successfully")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        job_id = kwargs.get("job_id")
        if job_id and job_id in _pcap_job_store:
            job = _pcap_job_store[job_id]
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(exc)
            logger.error(f"PCAP processing job {job_id} failed: {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        job_id = kwargs.get("job_id")
        if job_id and job_id in _pcap_job_store:
            job = _pcap_job_store[job_id]
            job.status = "retrying"
            logger.warning(f"PCAP processing job {job_id} retrying: {exc}")


@celery_app.task(
    bind=True,
    base=PcapProcessingTask,
    name="packetarch.process_pcap",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=7200,  # 2 hour max for large files
    soft_time_limit=7000,
)
def process_pcap_task(
    self,
    job_id: str,
    capture_id: str,
    enhanced: bool = True,
) -> dict[str, Any]:
    """Process a PCAP file as a Celery task with progress tracking.

    Args:
        self: Task instance
        job_id: Job identifier for progress tracking
        capture_id: PcapCapture UUID string
        enhanced: Whether to run enhanced analysis with deep extractors

    Returns:
        Dictionary with processing results
    """
    import asyncio

    logger.info(f"Starting PCAP processing task for capture {capture_id}")

    # Update job status
    job = get_pcap_job(job_id)
    if job:
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.stage = "initializing"
        update_pcap_job(job)

    # Run async processing
    result = asyncio.run(
        _process_pcap_async(self, job_id, capture_id, enhanced)
    )

    return result


async def _process_pcap_async(
    task: Task,
    job_id: str,
    capture_id: str,
    enhanced: bool = True,
) -> dict[str, Any]:
    """Async function to process PCAP file with progress updates.

    Args:
        task: Celery task instance for state updates
        job_id: Job identifier
        capture_id: PcapCapture UUID string
        enhanced: Whether to run enhanced analysis

    Returns:
        Dictionary with processing results
    """
    job = get_pcap_job(job_id)

    async with async_session_maker() as db:
        try:
            # Get capture record
            result = await db.execute(
                select(PcapCapture).where(PcapCapture.id == uuid.UUID(capture_id))
            )
            capture = result.scalar_one_or_none()

            if not capture:
                raise ValueError(f"Capture {capture_id} not found")

            # Update status to processing
            capture.status = ProcessingStatus.PROCESSING
            await db.commit()

            # Update job progress
            if job:
                job.stage = "reading_pcap"
                job.progress = 5.0
                update_pcap_job(job)

            # Update Celery task state
            task.update_state(
                state="PROGRESS",
                meta={"stage": "reading_pcap", "progress": 5},
            )

            # Analyze PCAP
            analyzer = PcapAnalyzer()

            if job:
                job.stage = "analyzing_packets"
                job.progress = 10.0
                update_pcap_job(job)

            task.update_state(
                state="PROGRESS",
                meta={"stage": "analyzing_packets", "progress": 10},
            )

            results = analyzer.analyze_file(capture.file_path, enhanced=enhanced)

            if "error" in results:
                capture.status = ProcessingStatus.FAILED
                capture.error_message = results["error"]
                await db.commit()
                if job:
                    job.status = "failed"
                    job.error_message = results["error"]
                    update_pcap_job(job)
                return {"status": "failed", "error": results["error"]}

            # Update job with packet count
            if job:
                job.packets_analyzed = results.get("packet_count", 0)
                job.stage = "extracting_patterns"
                job.progress = 40.0
                update_pcap_job(job)

            task.update_state(
                state="PROGRESS",
                meta={"stage": "extracting_patterns", "progress": 40},
            )

            # Update capture with analysis results
            capture.packet_count = results["packet_count"]
            capture.flow_count = results["flow_count"]
            capture.capture_duration_ms = results["capture_duration_ms"]
            capture.protocol_stats = results["protocol_stats"]
            capture.devices_detected = results["devices_detected"]

            # Store timing patterns
            if job:
                job.stage = "storing_timing_patterns"
                job.progress = 50.0
                update_pcap_job(job)

            patterns_count = 0
            for pattern_data in results.get("timing_patterns", []):
                pattern = LearnedPattern(
                    pcap_capture_id=capture.id,
                    name=pattern_data["name"],
                    pattern_type=PatternType(pattern_data["pattern_type"]),
                    protocol=pattern_data["protocol"],
                    source_ip=pattern_data.get("source_ip"),
                    destination_ip=pattern_data.get("destination_ip"),
                    source_port=pattern_data.get("source_port"),
                    destination_port=pattern_data.get("destination_port"),
                    distribution_type=DistributionType(pattern_data["distribution_type"]),
                    timing_params=pattern_data.get("timing_params"),
                    sample_count=pattern_data["sample_count"],
                    min_value=pattern_data.get("min_value"),
                    max_value=pattern_data.get("max_value"),
                    mean_value=pattern_data.get("mean_value"),
                    std_dev=pattern_data.get("std_dev"),
                    fit_score=pattern_data.get("fit_score"),
                    confidence=pattern_data.get("confidence", 0),
                )
                db.add(pattern)
                patterns_count += 1

            # Store payload patterns
            for pattern_data in results.get("payload_patterns", []):
                pattern = LearnedPattern(
                    pcap_capture_id=capture.id,
                    name=pattern_data["name"],
                    pattern_type=PatternType(pattern_data["pattern_type"]),
                    protocol=pattern_data["protocol"],
                    source_ip=pattern_data.get("source_ip"),
                    destination_ip=pattern_data.get("destination_ip"),
                    payload_patterns=pattern_data.get("payload_patterns"),
                    sample_count=pattern_data["sample_count"],
                    confidence=pattern_data.get("confidence", 0),
                )
                db.add(pattern)
                patterns_count += 1

            # Store protocol patterns
            if job:
                job.stage = "storing_protocol_patterns"
                job.progress = 60.0
                update_pcap_job(job)

            task.update_state(
                state="PROGRESS",
                meta={"stage": "storing_protocol_patterns", "progress": 60},
            )

            for proto_data in results.get("protocol_patterns", []):
                # S7-specific fields go in protocol_metadata
                s7_metadata = {}
                if proto_data.get("pdu_sizes"):
                    s7_metadata["pdu_sizes"] = proto_data["pdu_sizes"]
                if proto_data.get("rack_slot_configs"):
                    s7_metadata["rack_slot_configs"] = proto_data["rack_slot_configs"]
                if proto_data.get("memory_areas"):
                    s7_metadata["memory_areas"] = proto_data["memory_areas"]

                proto_pattern = LearnedProtocolPattern(
                    pcap_capture_id=capture.id,
                    protocol=proto_data["protocol"],
                    function_codes=proto_data.get("function_codes"),
                    address_patterns=proto_data.get("address_patterns"),
                    payload_structures=proto_data.get("payload_structures"),
                    request_response_pairs=proto_data.get("request_response_pairs"),
                    unit_id_distribution=proto_data.get("unit_id_distribution"),
                    exception_patterns=proto_data.get("exception_patterns"),
                    device_identities=proto_data.get("device_identities"),
                    protocol_metadata=s7_metadata if s7_metadata else proto_data.get("protocol_metadata"),
                    sample_count=proto_data.get("packet_count", proto_data.get("sample_count", 0)),
                )
                db.add(proto_pattern)
                patterns_count += 1

            # Store device fingerprints
            if job:
                job.stage = "storing_device_fingerprints"
                job.progress = 70.0
                job.patterns_extracted = patterns_count
                update_pcap_job(job)

            task.update_state(
                state="PROGRESS",
                meta={"stage": "storing_device_fingerprints", "progress": 70},
            )

            fingerprints_count = 0
            for fp_data in results.get("device_fingerprints", []):
                role_str = fp_data.get("role", "unknown").lower()
                if role_str not in ("master", "slave", "both", "unknown"):
                    role_str = "unknown"

                # Store fingerprint template (aggregated, not per-device)
                fingerprint = DeviceTemplate(
                    source=TemplateSource.PCAP_LEARNED.value,
                    source_pcap_id=capture.id,
                    vendor=fp_data.get("inferred_vendor"),
                    device_type=fp_data.get("device_type"),
                    oui_patterns=fp_data.get("oui_patterns"),
                    tcp_signature=fp_data.get("tcp_signature"),
                    response_timings=fp_data.get("response_timings"),
                    protocol_identities=fp_data.get("protocol_identities"),
                    role=role_str,
                    active_protocols=fp_data.get("active_protocols", []),
                    typical_ports=fp_data.get("typical_ports"),
                    sample_count=fp_data.get("observation_count", 1),
                    confidence=fp_data.get("confidence", 0.0),
                    consistency_score=fp_data.get("consistency_score", 1.0),
                    name=fp_data.get("name"),
                    is_active=True,
                )
                db.add(fingerprint)
                fingerprints_count += 1

            # Store learned sequences
            if job:
                job.stage = "storing_sequences"
                job.progress = 85.0
                job.fingerprints_extracted = fingerprints_count
                update_pcap_job(job)

            task.update_state(
                state="PROGRESS",
                meta={"stage": "storing_sequences", "progress": 85},
            )

            valid_sequence_types = {
                "startup", "shutdown", "poll_cycle", "write_sequence",
                "error_recovery", "state_transition", "heartbeat", "alarm"
            }
            sequences_count = 0
            for seq_data in results.get("learned_sequences", []):
                seq_type = seq_data.get("sequence_type", "").lower()
                if seq_type not in valid_sequence_types:
                    continue

                sequence = LearnedSequence(
                    pcap_capture_id=capture.id,
                    name=seq_data["name"],
                    sequence_type=seq_type,
                    protocol=seq_data["protocol"],
                    initiator_ip=seq_data.get("initiator_ip"),
                    responder_ip=seq_data.get("responder_ip"),
                    steps=seq_data.get("steps"),
                    step_count=seq_data.get("step_count", 0),
                    average_duration_ms=seq_data.get("average_duration_ms"),
                    timing_variance=seq_data.get("timing_variance"),
                    inter_step_timings=seq_data.get("inter_step_timings"),
                    repetition_interval_ms=seq_data.get("repetition_interval_ms"),
                    repetition_jitter_ms=seq_data.get("repetition_jitter_ms"),
                    occurrence_count=seq_data.get("occurrence_count", 0),
                    confidence=seq_data.get("confidence", 0.0),
                )
                db.add(sequence)
                sequences_count += 1

            # Finalize
            if job:
                job.stage = "finalizing"
                job.progress = 95.0
                job.sequences_extracted = sequences_count
                update_pcap_job(job)

            task.update_state(
                state="PROGRESS",
                meta={"stage": "finalizing", "progress": 95},
            )

            capture.status = ProcessingStatus.COMPLETED
            capture.processed_at = datetime.utcnow()
            await db.commit()

            # Invalidate fingerprint cache so new learned data is visible
            from app.services.fingerprint_cache import invalidate_fingerprint_cache
            invalidate_fingerprint_cache()

            logger.info(
                f"Successfully processed PCAP {capture_id}: "
                f"{patterns_count} patterns, {fingerprints_count} fingerprints, "
                f"{sequences_count} sequences"
            )

            return {
                "status": "completed",
                "capture_id": capture_id,
                "packets_analyzed": results.get("packet_count", 0),
                "flows_analyzed": results.get("flow_count", 0),
                "patterns_count": patterns_count,
                "fingerprints_count": fingerprints_count,
                "sequences_count": sequences_count,
            }

        except Exception as e:
            logger.exception(f"Failed to process PCAP {capture_id}: {e}")

            # Update capture status
            try:
                result = await db.execute(
                    select(PcapCapture).where(PcapCapture.id == uuid.UUID(capture_id))
                )
                capture = result.scalar_one_or_none()
                if capture:
                    capture.status = ProcessingStatus.FAILED
                    capture.error_message = str(e)
                    await db.commit()
            except Exception:
                pass

            # Update job status
            if job:
                job.status = "failed"
                job.error_message = str(e)
                update_pcap_job(job)

            raise


def get_pcap_processing_status(job_id: str) -> dict[str, Any] | None:
    """Get the current status of a PCAP processing job.

    Args:
        job_id: Job identifier

    Returns:
        Dictionary with job status, or None if not found
    """
    job = get_pcap_job(job_id)
    if not job:
        return None

    return {
        "job_id": job.job_id,
        "capture_id": job.capture_id,
        "status": job.status,
        "progress": job.progress,
        "stage": job.stage,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "packets_analyzed": job.packets_analyzed,
        "patterns_extracted": job.patterns_extracted,
        "fingerprints_extracted": job.fingerprints_extracted,
        "sequences_extracted": job.sequences_extracted,
    }
