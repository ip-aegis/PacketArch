"""Learning API endpoints for PCAP upload and pattern management."""

import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_services.pcap_analyzer import PcapAnalyzer
from app.core.config import settings
from app.core.database import get_db
from app.learning.tasks import (
    create_pcap_job,
    get_pcap_processing_status,
    process_pcap_task,
)
from app.models.learned_pattern import DistributionType, LearnedPattern, PatternType
from app.models.learned_protocol_pattern import LearnedProtocolPattern
from app.models.device_template import DeviceTemplate, TemplateSource
from app.models.learned_device_fingerprint import LearnedDeviceFingerprint  # for retry delete
from app.models.learned_sequence import LearnedSequence, SequenceType
from app.models.pcap_capture import PcapCapture, ProcessingStatus
from app.services.learned_pattern_service import LearnedPatternService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["learning"])

# PCAP storage directory
PCAP_STORAGE_DIR = Path(settings.data_dir if hasattr(settings, "data_dir") else "./data") / "pcap_uploads"
PCAP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# ========== Pydantic Schemas ==========


class PcapUploadResponse(BaseModel):
    """Response for PCAP upload."""

    id: str
    filename: str
    status: str
    message: str
    job_id: str | None = None  # For tracking Celery job progress


class PcapJobStatusResponse(BaseModel):
    """Response for PCAP processing job status."""

    job_id: str
    capture_id: str
    status: str
    progress: float
    stage: str
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    packets_analyzed: int = 0
    patterns_extracted: int = 0
    fingerprints_extracted: int = 0
    sequences_extracted: int = 0


class PcapCaptureResponse(BaseModel):
    """Response for PCAP capture details."""

    id: str
    filename: str
    original_filename: str
    file_size: int
    status: str
    error_message: str | None
    packet_count: int | None
    flow_count: int | None
    capture_duration_ms: float | None
    protocol_stats: dict | None
    devices_detected: dict | None
    description: str | None
    tags: list | None
    source_environment: str | None
    industry_vertical: str | None
    created_at: datetime
    processed_at: datetime | None

    class Config:
        from_attributes = True


class LearnedPatternResponse(BaseModel):
    """Response for learned pattern."""

    id: str
    name: str
    pattern_type: str
    protocol: str
    source_ip: str | None
    destination_ip: str | None
    distribution_type: str | None
    sample_count: int
    min_value: float | None
    max_value: float | None
    mean_value: float | None
    std_dev: float | None
    fit_score: float | None
    confidence: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PatternListResponse(BaseModel):
    """Response for pattern list."""

    patterns: list[LearnedPatternResponse]
    total: int
    page: int
    page_size: int


class PcapListResponse(BaseModel):
    """Response for PCAP list."""

    captures: list[PcapCaptureResponse]
    total: int
    page: int
    page_size: int


class LearningStatsResponse(BaseModel):
    """Response for learning statistics."""

    uploaded_pcaps: int
    learned_patterns: int
    active_patterns: int
    protocols_covered: int
    protocol_patterns: int
    device_fingerprints: int
    learned_sequences: int


class PatternStatsResponse(BaseModel):
    """Response for pattern statistics."""
    protocol_patterns: dict
    device_fingerprints: dict
    sequences: dict


class ProtocolPatternResponse(BaseModel):
    """Response for learned protocol pattern."""

    id: str
    pcap_capture_id: str | None
    protocol: str
    function_codes: dict | None
    address_patterns: dict | None
    payload_structures: dict | None
    request_response_pairs: list | None
    unit_id_distribution: dict | None
    exception_patterns: dict | None
    device_identities: list | None
    protocol_metadata: dict | None
    sample_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProtocolPatternListResponse(BaseModel):
    """Response for protocol pattern list."""

    patterns: list[ProtocolPatternResponse]
    total: int
    page: int
    page_size: int


class DeviceFingerprintResponse(BaseModel):
    """Response for learned device fingerprint template.

    Fingerprints are GENERIC TEMPLATES capturing vendor characteristics,
    NOT specific device instances with IP addresses.
    """

    id: str
    pcap_capture_id: str | None
    # Vendor identification
    inferred_vendor: str | None
    device_type: str | None
    oui_patterns: list | None  # OUI prefixes associated with this fingerprint
    # TCP stack signature
    tcp_signature: dict | None
    # Response timing distributions
    response_timings: dict | None
    # Protocol-specific identity info (vendor, model, firmware)
    protocol_identities: dict | None
    # Behavioral patterns
    role: str
    active_protocols: list | None
    typical_ports: dict | None
    # Aggregation metadata
    observation_count: int
    total_packets_analyzed: int
    # Quality metrics
    confidence: float
    consistency_score: float
    # User metadata
    name: str | None
    tags: list | None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceFingerprintListResponse(BaseModel):
    """Response for device fingerprint list."""

    fingerprints: list[DeviceFingerprintResponse]
    total: int
    page: int
    page_size: int


class SequenceResponse(BaseModel):
    """Response for learned sequence."""

    id: str
    pcap_capture_id: str | None
    name: str
    sequence_type: str
    protocol: str
    initiator_ip: str | None
    responder_ip: str | None
    steps: dict | None
    step_count: int
    average_duration_ms: float | None
    timing_variance: float | None
    inter_step_timings: dict | None
    repetition_interval_ms: float | None
    repetition_jitter_ms: float | None
    occurrence_count: int
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


class SequenceListResponse(BaseModel):
    """Response for sequence list."""

    sequences: list[SequenceResponse]
    total: int
    page: int
    page_size: int


# ========== Helpers ==========


def _template_to_fingerprint_response(fp: DeviceTemplate) -> DeviceFingerprintResponse:
    """Convert DeviceTemplate to DeviceFingerprintResponse for API backward compat."""
    return DeviceFingerprintResponse(
        id=str(fp.id),
        pcap_capture_id=str(fp.source_pcap_id) if fp.source_pcap_id else None,
        inferred_vendor=fp.vendor,
        device_type=fp.device_type,
        oui_patterns=fp.oui_patterns,
        tcp_signature=fp.tcp_signature,
        response_timings=fp.response_timings,
        protocol_identities=fp.protocol_identities,
        role=fp.role or "unknown",
        active_protocols=fp.active_protocols,
        typical_ports=fp.typical_ports,
        observation_count=fp.sample_count or 0,
        total_packets_analyzed=0,
        confidence=fp.confidence or 0.0,
        consistency_score=fp.consistency_score or 1.0,
        name=fp.name,
        tags=fp.tags,
        created_at=fp.created_at,
    )


# ========== Stats Endpoint ==========


@router.get("/stats", response_model=LearningStatsResponse)
async def get_learning_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get learning statistics for the dashboard."""
    import asyncio
    from sqlalchemy import distinct

    # Run all 7 count queries concurrently
    (
        pcap_result,
        patterns_result,
        active_result,
        protocols_result,
        proto_patterns_result,
        fingerprints_result,
        sequences_result,
    ) = await asyncio.gather(
        db.execute(select(func.count(PcapCapture.id))),
        db.execute(select(func.count(LearnedPattern.id))),
        db.execute(
            select(func.count(LearnedPattern.id)).where(LearnedPattern.is_active == True)
        ),
        db.execute(select(func.count(distinct(LearnedPattern.protocol)))),
        db.execute(select(func.count(LearnedProtocolPattern.id))),
        db.execute(select(func.count(DeviceTemplate.id)).where(
            DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value
        )),
        db.execute(select(func.count(LearnedSequence.id))),
    )

    return LearningStatsResponse(
        uploaded_pcaps=pcap_result.scalar() or 0,
        learned_patterns=patterns_result.scalar() or 0,
        active_patterns=active_result.scalar() or 0,
        protocols_covered=protocols_result.scalar() or 0,
        protocol_patterns=proto_patterns_result.scalar() or 0,
        device_fingerprints=fingerprints_result.scalar() or 0,
        learned_sequences=sequences_result.scalar() or 0,
    )


# ========== PCAP Upload Endpoints ==========


@router.post("/pcap/upload", response_model=PcapUploadResponse)
async def upload_pcap(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    description: str | None = Query(None),
    source_environment: str | None = Query(None),
    industry_vertical: str | None = Query(None),
    use_celery: bool = Query(True, description="Use Celery for background processing (recommended for large files)"),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PCAP file for analysis.

    The file will be processed in the background to extract traffic patterns.
    For large files (>100MB), Celery processing is recommended as it provides:
    - Progress tracking
    - Automatic retry on failure
    - Better fault tolerance
    """
    # Validate file type
    if not file.filename.endswith((".pcap", ".pcapng", ".cap")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .pcap, .pcapng, and .cap files are allowed.",
        )

    # Generate unique filename
    capture_id = uuid.uuid4()
    file_ext = Path(file.filename).suffix
    stored_filename = f"{capture_id}{file_ext}"
    file_path = PCAP_STORAGE_DIR / stored_filename

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save PCAP file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    # Get file size and hash
    file_size = os.path.getsize(file_path)
    file_hash = PcapAnalyzer._calculate_file_hash(file_path)

    # Check for duplicate
    existing = await db.execute(
        select(PcapCapture).where(PcapCapture.file_hash == file_hash)
    )
    if existing.scalar_one_or_none():
        # Remove duplicate file
        os.remove(file_path)
        raise HTTPException(
            status_code=409,
            detail="This PCAP file has already been uploaded.",
        )

    # Create database record
    capture = PcapCapture(
        id=capture_id,
        filename=stored_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        file_hash=file_hash,
        status=ProcessingStatus.PENDING,
        description=description,
        source_environment=source_environment,
        industry_vertical=industry_vertical,
    )

    db.add(capture)
    await db.commit()

    job_id = None

    # Schedule background processing
    if use_celery:
        # Use Celery for robust processing with progress tracking
        job = create_pcap_job(str(capture_id))
        job_id = job.job_id
        process_pcap_task.delay(
            job_id=job.job_id,
            capture_id=str(capture_id),
            enhanced=True,
        )
        message = "PCAP file uploaded. Processing started with progress tracking."
    else:
        # Use FastAPI BackgroundTasks for simple processing
        background_tasks.add_task(process_pcap, str(capture_id))
        message = "PCAP file uploaded successfully. Processing will begin shortly."

    return PcapUploadResponse(
        id=str(capture_id),
        filename=file.filename,
        status="pending",
        message=message,
        job_id=job_id,
    )


@router.get("/pcap/job/{job_id}", response_model=PcapJobStatusResponse)
async def get_pcap_job_status(job_id: str):
    """Get the status of a PCAP processing job.

    Use this endpoint to track progress of Celery-based PCAP processing.
    """
    status = get_pcap_processing_status(job_id)

    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Processing job {job_id} not found",
        )

    return PcapJobStatusResponse(**status)


@router.get("/pcap", response_model=PcapListResponse)
async def list_pcap_captures(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded PCAP captures."""
    query = select(PcapCapture).order_by(PcapCapture.created_at.desc())

    if status:
        query = query.where(PcapCapture.status == ProcessingStatus(status))

    # Get total count
    count_query = select(func.count(PcapCapture.id))
    if status:
        count_query = count_query.where(PcapCapture.status == ProcessingStatus(status))
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    captures = result.scalars().all()

    return PcapListResponse(
        captures=[
            PcapCaptureResponse(
                id=str(c.id),
                filename=c.filename,
                original_filename=c.original_filename,
                file_size=c.file_size,
                status=c.status.value,
                error_message=c.error_message,
                packet_count=c.packet_count,
                flow_count=c.flow_count,
                capture_duration_ms=c.capture_duration_ms,
                protocol_stats=c.protocol_stats,
                devices_detected=c.devices_detected,
                description=c.description,
                tags=c.tags,
                source_environment=c.source_environment,
                industry_vertical=c.industry_vertical,
                created_at=c.created_at,
                processed_at=c.processed_at,
            )
            for c in captures
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/pcap/{capture_id}", response_model=PcapCaptureResponse)
async def get_pcap_capture(
    capture_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific PCAP capture."""
    result = await db.execute(
        select(PcapCapture).where(PcapCapture.id == uuid.UUID(capture_id))
    )
    capture = result.scalar_one_or_none()

    if not capture:
        raise HTTPException(status_code=404, detail="PCAP capture not found")

    return PcapCaptureResponse(
        id=str(capture.id),
        filename=capture.filename,
        original_filename=capture.original_filename,
        file_size=capture.file_size,
        status=capture.status.value,
        error_message=capture.error_message,
        packet_count=capture.packet_count,
        flow_count=capture.flow_count,
        capture_duration_ms=capture.capture_duration_ms,
        protocol_stats=capture.protocol_stats,
        devices_detected=capture.devices_detected,
        description=capture.description,
        tags=capture.tags,
        source_environment=capture.source_environment,
        industry_vertical=capture.industry_vertical,
        created_at=capture.created_at,
        processed_at=capture.processed_at,
    )


@router.delete("/pcap/{capture_id}")
async def delete_pcap_capture(
    capture_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a PCAP capture and its learned patterns."""
    result = await db.execute(
        select(PcapCapture).where(PcapCapture.id == uuid.UUID(capture_id))
    )
    capture = result.scalar_one_or_none()

    if not capture:
        raise HTTPException(status_code=404, detail="PCAP capture not found")

    # Delete file
    try:
        if os.path.exists(capture.file_path):
            os.remove(capture.file_path)
    except Exception as e:
        logger.warning(f"Failed to delete file: {e}")

    # Delete from database (patterns will cascade)
    await db.delete(capture)
    await db.commit()

    return {"message": "PCAP capture deleted successfully"}


@router.post("/pcap/{capture_id}/retry", response_model=PcapUploadResponse)
async def retry_pcap_processing(
    capture_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Retry processing a stuck or failed PCAP capture.

    This resets the capture status and restarts background processing.
    Useful for:
    - Processing jobs that were abandoned due to server restart
    - Failed processing that may succeed on retry
    """
    result = await db.execute(
        select(PcapCapture).where(PcapCapture.id == uuid.UUID(capture_id))
    )
    capture = result.scalar_one_or_none()

    if not capture:
        raise HTTPException(status_code=404, detail="PCAP capture not found")

    # Only allow retry for stuck/failed captures
    if capture.status == ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Cannot retry a completed capture. Delete and re-upload if needed.",
        )

    # Delete any existing patterns from previous failed/partial processing
    await db.execute(
        LearnedPattern.__table__.delete().where(
            LearnedPattern.pcap_capture_id == capture.id
        )
    )
    await db.execute(
        LearnedProtocolPattern.__table__.delete().where(
            LearnedProtocolPattern.pcap_capture_id == capture.id
        )
    )
    await db.execute(
        DeviceTemplate.__table__.delete().where(
            DeviceTemplate.source_pcap_id == capture.id,
            DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
        )
    )
    # Also clean legacy table for records created before migration
    await db.execute(
        LearnedDeviceFingerprint.__table__.delete().where(
            LearnedDeviceFingerprint.pcap_capture_id == capture.id
        )
    )
    await db.execute(
        LearnedSequence.__table__.delete().where(
            LearnedSequence.pcap_capture_id == capture.id
        )
    )

    # Reset status
    capture.status = ProcessingStatus.PENDING
    capture.error_message = None
    capture.processed_at = None
    capture.packet_count = None
    capture.flow_count = None
    capture.capture_duration_ms = None
    capture.protocol_stats = None
    capture.devices_detected = None
    await db.commit()

    # Invalidate fingerprint cache since old learned data was cleared
    from app.services.fingerprint_cache import invalidate_fingerprint_cache
    invalidate_fingerprint_cache()

    # Schedule background processing
    background_tasks.add_task(process_pcap, str(capture_id))

    return PcapUploadResponse(
        id=str(capture.id),
        filename=capture.original_filename,
        status="pending",
        message="Processing restarted. The capture will be analyzed shortly.",
    )


# ========== Pattern Endpoints ==========


@router.get("/patterns", response_model=PatternListResponse)
async def list_patterns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    protocol: str | None = Query(None),
    pattern_type: str | None = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """List learned traffic patterns."""
    query = select(LearnedPattern).order_by(LearnedPattern.confidence.desc())

    if protocol:
        query = query.where(LearnedPattern.protocol == protocol)
    if pattern_type:
        query = query.where(LearnedPattern.pattern_type == PatternType(pattern_type))
    if active_only:
        query = query.where(LearnedPattern.is_active == True)

    # Get total count
    count_query = select(LearnedPattern)
    if protocol:
        count_query = count_query.where(LearnedPattern.protocol == protocol)
    if pattern_type:
        count_query = count_query.where(LearnedPattern.pattern_type == PatternType(pattern_type))
    if active_only:
        count_query = count_query.where(LearnedPattern.is_active == True)
    result = await db.execute(count_query)
    total = len(result.scalars().all())

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    patterns = result.scalars().all()

    return PatternListResponse(
        patterns=[
            LearnedPatternResponse(
                id=str(p.id),
                name=p.name,
                pattern_type=p.pattern_type.value,
                protocol=p.protocol,
                source_ip=p.source_ip,
                destination_ip=p.destination_ip,
                distribution_type=p.distribution_type.value if p.distribution_type else None,
                sample_count=p.sample_count,
                min_value=p.min_value,
                max_value=p.max_value,
                mean_value=p.mean_value,
                std_dev=p.std_dev,
                fit_score=p.fit_score,
                confidence=p.confidence,
                is_active=p.is_active,
                created_at=p.created_at,
            )
            for p in patterns
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/patterns/stats", response_model=PatternStatsResponse)
async def get_pattern_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get statistics about available learned patterns.

    Returns counts and confidence scores by protocol for all pattern types.
    """
    stats = await LearnedPatternService.get_pattern_stats(db)

    return PatternStatsResponse(
        protocol_patterns=stats.get("protocol_patterns", {}),
        device_fingerprints=stats.get("device_fingerprints", {}),
        sequences=stats.get("sequences", {}),
    )


@router.get("/patterns/{pattern_id}")
async def get_pattern(
    pattern_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific pattern including full data."""
    result = await db.execute(
        select(LearnedPattern).where(LearnedPattern.id == uuid.UUID(pattern_id))
    )
    pattern = result.scalar_one_or_none()

    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return {
        "id": str(pattern.id),
        "name": pattern.name,
        "pattern_type": pattern.pattern_type.value,
        "protocol": pattern.protocol,
        "source_ip": pattern.source_ip,
        "destination_ip": pattern.destination_ip,
        "source_port": pattern.source_port,
        "destination_port": pattern.destination_port,
        "distribution_type": pattern.distribution_type.value if pattern.distribution_type else None,
        "timing_params": pattern.timing_params,
        "sample_count": pattern.sample_count,
        "min_value": pattern.min_value,
        "max_value": pattern.max_value,
        "mean_value": pattern.mean_value,
        "std_dev": pattern.std_dev,
        "fit_score": pattern.fit_score,
        "payload_patterns": pattern.payload_patterns,
        "sequence_patterns": pattern.sequence_patterns,
        "error_patterns": pattern.error_patterns,
        "pattern_data": pattern.pattern_data,
        "confidence": pattern.confidence,
        "is_active": pattern.is_active,
        "created_at": pattern.created_at,
        "updated_at": pattern.updated_at,
    }


@router.patch("/patterns/{pattern_id}/toggle")
async def toggle_pattern(
    pattern_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Toggle a pattern's active status."""
    result = await db.execute(
        select(LearnedPattern).where(LearnedPattern.id == uuid.UUID(pattern_id))
    )
    pattern = result.scalar_one_or_none()

    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    pattern.is_active = not pattern.is_active
    await db.commit()

    return {"id": str(pattern.id), "is_active": pattern.is_active}


# ========== Enhanced Pattern Endpoints ==========


@router.get("/protocol-patterns", response_model=ProtocolPatternListResponse)
async def list_protocol_patterns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    protocol: str | None = Query(None),
    pcap_capture_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List learned protocol patterns with deep payload analysis."""
    query = select(LearnedProtocolPattern).order_by(LearnedProtocolPattern.created_at.desc())

    if protocol:
        query = query.where(LearnedProtocolPattern.protocol == protocol)
    if pcap_capture_id:
        query = query.where(LearnedProtocolPattern.pcap_capture_id == uuid.UUID(pcap_capture_id))

    # Get total count
    count_query = select(LearnedProtocolPattern)
    if protocol:
        count_query = count_query.where(LearnedProtocolPattern.protocol == protocol)
    if pcap_capture_id:
        count_query = count_query.where(LearnedProtocolPattern.pcap_capture_id == uuid.UUID(pcap_capture_id))
    result = await db.execute(count_query)
    total = len(result.scalars().all())

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    patterns = result.scalars().all()

    return ProtocolPatternListResponse(
        patterns=[
            ProtocolPatternResponse(
                id=str(p.id),
                pcap_capture_id=str(p.pcap_capture_id) if p.pcap_capture_id else None,
                protocol=p.protocol,
                function_codes=p.function_codes,
                address_patterns=p.address_patterns,
                payload_structures=p.payload_structures,
                request_response_pairs=p.request_response_pairs,
                unit_id_distribution=p.unit_id_distribution,
                exception_patterns=p.exception_patterns,
                device_identities=p.device_identities,
                protocol_metadata=p.protocol_metadata,
                sample_count=p.sample_count,
                created_at=p.created_at,
            )
            for p in patterns
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/protocol-patterns/{pattern_id}")
async def get_protocol_pattern(
    pattern_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific protocol pattern."""
    result = await db.execute(
        select(LearnedProtocolPattern).where(LearnedProtocolPattern.id == uuid.UUID(pattern_id))
    )
    pattern = result.scalar_one_or_none()

    if not pattern:
        raise HTTPException(status_code=404, detail="Protocol pattern not found")

    return ProtocolPatternResponse(
        id=str(pattern.id),
        pcap_capture_id=str(pattern.pcap_capture_id) if pattern.pcap_capture_id else None,
        protocol=pattern.protocol,
        function_codes=pattern.function_codes,
        address_patterns=pattern.address_patterns,
        payload_structures=pattern.payload_structures,
        request_response_pairs=pattern.request_response_pairs,
        unit_id_distribution=pattern.unit_id_distribution,
        exception_patterns=pattern.exception_patterns,
        device_identities=pattern.device_identities,
        protocol_metadata=pattern.protocol_metadata,
        sample_count=pattern.sample_count,
        created_at=pattern.created_at,
    )


@router.get("/device-fingerprints", response_model=DeviceFingerprintListResponse)
async def list_device_fingerprints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vendor: str | None = Query(None, description="Filter by vendor name"),
    device_type: str | None = Query(None, description="Filter by device type (PLC, HMI, etc.)"),
    role: str | None = Query(None, description="Filter by role (master, slave, both)"),
    protocol: str | None = Query(None, description="Filter by protocol"),
    pcap_capture_id: str | None = Query(None, description="Filter by source PCAP"),
    db: AsyncSession = Depends(get_db),
):
    """List learned device fingerprint templates.

    Returns aggregated fingerprint templates that capture vendor characteristics,
    TCP signatures, and behavioral patterns - NOT specific device instances.
    """
    # Base filter: only PCAP-learned templates
    base_filter = DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value
    query = select(DeviceTemplate).where(base_filter).order_by(DeviceTemplate.created_at.desc())

    if vendor:
        query = query.where(DeviceTemplate.vendor.ilike(f"%{vendor}%"))
    if device_type:
        query = query.where(DeviceTemplate.device_type.ilike(f"%{device_type}%"))
    if role:
        query = query.where(DeviceTemplate.role == role)
    if protocol:
        query = query.where(DeviceTemplate.active_protocols.contains([protocol]))
    if pcap_capture_id:
        query = query.where(DeviceTemplate.source_pcap_id == uuid.UUID(pcap_capture_id))

    # Get total count
    count_query = select(func.count(DeviceTemplate.id)).where(base_filter)
    if vendor:
        count_query = count_query.where(DeviceTemplate.vendor.ilike(f"%{vendor}%"))
    if device_type:
        count_query = count_query.where(DeviceTemplate.device_type.ilike(f"%{device_type}%"))
    if role:
        count_query = count_query.where(DeviceTemplate.role == role)
    if protocol:
        count_query = count_query.where(DeviceTemplate.active_protocols.contains([protocol]))
    if pcap_capture_id:
        count_query = count_query.where(DeviceTemplate.source_pcap_id == uuid.UUID(pcap_capture_id))
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    fingerprints = result.scalars().all()

    return DeviceFingerprintListResponse(
        fingerprints=[
            _template_to_fingerprint_response(fp)
            for fp in fingerprints
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/device-fingerprints/{fingerprint_id}")
async def get_device_fingerprint(
    fingerprint_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific device fingerprint."""
    result = await db.execute(
        select(DeviceTemplate).where(
            DeviceTemplate.id == uuid.UUID(fingerprint_id),
            DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
        )
    )
    fingerprint = result.scalar_one_or_none()

    if not fingerprint:
        raise HTTPException(status_code=404, detail="Device fingerprint not found")

    return _template_to_fingerprint_response(fingerprint)


@router.get("/sequences", response_model=SequenceListResponse)
async def list_sequences(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sequence_type: str | None = Query(None),
    protocol: str | None = Query(None),
    pcap_capture_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List learned operation sequences."""
    query = select(LearnedSequence).order_by(LearnedSequence.confidence.desc())

    if sequence_type:
        query = query.where(LearnedSequence.sequence_type == SequenceType(sequence_type))
    if protocol:
        query = query.where(LearnedSequence.protocol == protocol)
    if pcap_capture_id:
        query = query.where(LearnedSequence.pcap_capture_id == uuid.UUID(pcap_capture_id))

    # Get total count
    count_query = select(LearnedSequence)
    if sequence_type:
        count_query = count_query.where(LearnedSequence.sequence_type == SequenceType(sequence_type))
    if protocol:
        count_query = count_query.where(LearnedSequence.protocol == protocol)
    if pcap_capture_id:
        count_query = count_query.where(LearnedSequence.pcap_capture_id == uuid.UUID(pcap_capture_id))
    result = await db.execute(count_query)
    total = len(result.scalars().all())

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    sequences = result.scalars().all()

    return SequenceListResponse(
        sequences=[
            SequenceResponse(
                id=str(s.id),
                pcap_capture_id=str(s.pcap_capture_id) if s.pcap_capture_id else None,
                name=s.name,
                sequence_type=str(s.sequence_type),
                protocol=s.protocol,
                initiator_ip=s.initiator_ip,
                responder_ip=s.responder_ip,
                steps=s.steps,
                step_count=s.step_count,
                average_duration_ms=s.average_duration_ms,
                timing_variance=s.timing_variance,
                inter_step_timings=s.inter_step_timings,
                repetition_interval_ms=s.repetition_interval_ms,
                repetition_jitter_ms=s.repetition_jitter_ms,
                occurrence_count=s.occurrence_count,
                confidence=s.confidence,
                created_at=s.created_at,
            )
            for s in sequences
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/sequences/{sequence_id}")
async def get_sequence(
    sequence_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific learned sequence."""
    result = await db.execute(
        select(LearnedSequence).where(LearnedSequence.id == uuid.UUID(sequence_id))
    )
    sequence = result.scalar_one_or_none()

    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")

    return SequenceResponse(
        id=str(sequence.id),
        pcap_capture_id=str(sequence.pcap_capture_id) if sequence.pcap_capture_id else None,
        name=sequence.name,
        sequence_type=str(sequence.sequence_type),
        protocol=sequence.protocol,
        initiator_ip=sequence.initiator_ip,
        responder_ip=sequence.responder_ip,
        steps=sequence.steps,
        step_count=sequence.step_count,
        average_duration_ms=sequence.average_duration_ms,
        timing_variance=sequence.timing_variance,
        inter_step_timings=sequence.inter_step_timings,
        repetition_interval_ms=sequence.repetition_interval_ms,
        repetition_jitter_ms=sequence.repetition_jitter_ms,
        occurrence_count=sequence.occurrence_count,
        confidence=sequence.confidence,
        created_at=sequence.created_at,
    )


# ========== Pattern Service Endpoints ==========


class TimingModelResponse(BaseModel):
    """Response for timing model."""
    protocol: str
    source_pattern_id: str | None
    timing: dict | None
    confidence: float


class FunctionCodeDistributionResponse(BaseModel):
    """Response for function code distribution."""
    protocol: str
    source_pattern_id: str | None
    function_codes: dict | None
    sample_count: int
    confidence: float


class AddressPatternsResponse(BaseModel):
    """Response for address patterns."""
    protocol: str
    source_pattern_id: str | None
    address_patterns: dict | None
    sample_count: int
    confidence: float


class TcpSignatureModelResponse(BaseModel):
    """Response for TCP signature model."""
    protocol: str | None
    role: str | None
    signatures: list[dict]
    count: int


class ResponseTimingModelResponse(BaseModel):
    """Response for device response timing model."""
    protocol: str
    role: str
    aggregate: dict
    individual_timings: list[dict]
    device_count: int


class StartupSequenceResponse(BaseModel):
    """Response for startup sequence."""
    protocol: str
    sequence_id: str
    name: str
    steps: dict | None
    step_count: int
    average_duration_ms: float | None
    confidence: float


class PollCyclePatternResponse(BaseModel):
    """Response for poll cycle pattern."""
    protocol: str
    sequence_id: str
    name: str
    steps: dict | None
    step_count: int
    repetition_interval_ms: float | None
    repetition_jitter_ms: float | None
    confidence: float


class PatternSuggestionResponse(BaseModel):
    """Response for pattern suggestions."""
    device_type: str
    protocol: str
    expected_role: str
    suggestions: dict


@router.get("/patterns/timing-model/{protocol}")
async def get_timing_model(
    protocol: str,
    db: AsyncSession = Depends(get_db),
):
    """Get timing model from learned patterns for a protocol.

    Returns aggregated timing statistics for realistic traffic generation.
    """
    model = await LearnedPatternService.get_timing_model(db, protocol)

    if not model:
        raise HTTPException(
            status_code=404,
            detail=f"No timing data found for protocol: {protocol}",
        )

    return TimingModelResponse(
        protocol=model["protocol"],
        source_pattern_id=model.get("source_pattern_id"),
        timing=model.get("timing"),
        confidence=model.get("confidence", 0.0),
    )


@router.get("/patterns/function-codes/{protocol}")
async def get_function_codes(
    protocol: str,
    db: AsyncSession = Depends(get_db),
):
    """Get function code distribution for a protocol.

    Returns observed function code frequencies for traffic generation.
    """
    distribution = await LearnedPatternService.get_function_code_distribution(db, protocol)

    if not distribution:
        raise HTTPException(
            status_code=404,
            detail=f"No function code data found for protocol: {protocol}",
        )

    return FunctionCodeDistributionResponse(
        protocol=distribution["protocol"],
        source_pattern_id=distribution.get("source_pattern_id"),
        function_codes=distribution.get("function_codes"),
        sample_count=distribution.get("sample_count", 0),
        confidence=distribution.get("confidence", 0.0),
    )


@router.get("/patterns/address-patterns/{protocol}")
async def get_address_patterns(
    protocol: str,
    db: AsyncSession = Depends(get_db),
):
    """Get address/register patterns for a protocol.

    Returns observed address ranges and access patterns.
    """
    patterns = await LearnedPatternService.get_address_patterns(db, protocol)

    if not patterns:
        raise HTTPException(
            status_code=404,
            detail=f"No address pattern data found for protocol: {protocol}",
        )

    return AddressPatternsResponse(
        protocol=patterns["protocol"],
        source_pattern_id=patterns.get("source_pattern_id"),
        address_patterns=patterns.get("address_patterns"),
        sample_count=patterns.get("sample_count", 0),
        confidence=patterns.get("confidence", 0.0),
    )


@router.get("/patterns/tcp-signatures")
async def get_tcp_signatures(
    protocol: str | None = Query(None),
    role: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get TCP signature model for realistic packet crafting.

    Returns collected TCP stack signatures from learned device fingerprints.
    """
    model = await LearnedPatternService.get_tcp_signature_model(db, protocol, role)

    if not model:
        raise HTTPException(
            status_code=404,
            detail="No TCP signature data found",
        )

    return TcpSignatureModelResponse(
        protocol=model.get("protocol"),
        role=model.get("role"),
        signatures=model.get("signatures", []),
        count=model.get("count", 0),
    )


@router.get("/patterns/response-timing/{protocol}")
async def get_response_timing(
    protocol: str,
    role: str = Query("slave", description="Device role (typically 'slave' for responders)"),
    db: AsyncSession = Depends(get_db),
):
    """Get response timing model for simulating realistic device responses.

    Returns timing statistics for how devices respond to requests.
    """
    model = await LearnedPatternService.get_response_timing_model(db, protocol, role)

    if not model:
        raise HTTPException(
            status_code=404,
            detail=f"No response timing data found for protocol: {protocol}",
        )

    return ResponseTimingModelResponse(
        protocol=model["protocol"],
        role=model["role"],
        aggregate=model.get("aggregate", {}),
        individual_timings=model.get("individual_timings", []),
        device_count=model.get("device_count", 0),
    )


@router.get("/patterns/startup-sequence/{protocol}")
async def get_startup_sequence(
    protocol: str,
    db: AsyncSession = Depends(get_db),
):
    """Get startup sequence for a protocol.

    Returns the learned startup/initialization sequence.
    """
    sequence = await LearnedPatternService.get_startup_sequence(db, protocol)

    if not sequence:
        raise HTTPException(
            status_code=404,
            detail=f"No startup sequence found for protocol: {protocol}",
        )

    return StartupSequenceResponse(
        protocol=sequence["protocol"],
        sequence_id=sequence["sequence_id"],
        name=sequence["name"],
        steps=sequence.get("steps"),
        step_count=sequence.get("step_count", 0),
        average_duration_ms=sequence.get("average_duration_ms"),
        confidence=sequence.get("confidence", 0.0),
    )


@router.get("/patterns/poll-cycle/{protocol}")
async def get_poll_cycle(
    protocol: str,
    db: AsyncSession = Depends(get_db),
):
    """Get poll cycle pattern for a protocol.

    Returns the learned polling pattern for steady-state operation.
    """
    pattern = await LearnedPatternService.get_poll_cycle_pattern(db, protocol)

    if not pattern:
        raise HTTPException(
            status_code=404,
            detail=f"No poll cycle pattern found for protocol: {protocol}",
        )

    return PollCyclePatternResponse(
        protocol=pattern["protocol"],
        sequence_id=pattern["sequence_id"],
        name=pattern["name"],
        steps=pattern.get("steps"),
        step_count=pattern.get("step_count", 0),
        repetition_interval_ms=pattern.get("repetition_interval_ms"),
        repetition_jitter_ms=pattern.get("repetition_jitter_ms"),
        confidence=pattern.get("confidence", 0.0),
    )


@router.get("/patterns/suggest")
async def suggest_patterns(
    device_type: str = Query(..., description="Device type (plc, hmi, rtu, etc.)"),
    protocol: str = Query(..., description="Protocol name"),
    db: AsyncSession = Depends(get_db),
):
    """Suggest learned patterns that match a device configuration.

    Returns recommendations for protocol patterns, fingerprints, and sequences
    that best match the specified device type and protocol.
    """
    suggestions = await LearnedPatternService.suggest_patterns_for_device(
        db, device_type, protocol
    )

    return PatternSuggestionResponse(
        device_type=suggestions["device_type"],
        protocol=suggestions["protocol"],
        expected_role=suggestions["expected_role"],
        suggestions=suggestions["suggestions"],
    )


# ========== Background Processing ==========


async def process_pcap(capture_id: str) -> None:
    """Process a PCAP file in the background."""
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        try:
            # Get capture record
            result = await db.execute(
                select(PcapCapture).where(PcapCapture.id == uuid.UUID(capture_id))
            )
            capture = result.scalar_one_or_none()

            if not capture:
                logger.error(f"Capture {capture_id} not found")
                return

            # Update status
            capture.status = ProcessingStatus.PROCESSING
            await db.commit()

            # Analyze PCAP
            analyzer = PcapAnalyzer()
            results = analyzer.analyze_file(capture.file_path)

            if "error" in results:
                capture.status = ProcessingStatus.FAILED
                capture.error_message = results["error"]
                await db.commit()
                return

            # Update capture with results
            capture.packet_count = results["packet_count"]
            capture.flow_count = results["flow_count"]
            capture.capture_duration_ms = results["capture_duration_ms"]
            capture.protocol_stats = results["protocol_stats"]
            capture.devices_detected = results["devices_detected"]
            capture.status = ProcessingStatus.COMPLETED
            capture.processed_at = datetime.utcnow()

            # Collect all objects for batch insert
            new_objects: list = []

            # Create learned patterns (timing)
            for pattern_data in results.get("timing_patterns", []):
                new_objects.append(LearnedPattern(
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
                ))

            # Create learned patterns (payload)
            for pattern_data in results.get("payload_patterns", []):
                new_objects.append(LearnedPattern(
                    pcap_capture_id=capture.id,
                    name=pattern_data["name"],
                    pattern_type=PatternType(pattern_data["pattern_type"]),
                    protocol=pattern_data["protocol"],
                    source_ip=pattern_data.get("source_ip"),
                    destination_ip=pattern_data.get("destination_ip"),
                    payload_patterns=pattern_data.get("payload_patterns"),
                    sample_count=pattern_data["sample_count"],
                    confidence=pattern_data.get("confidence", 0),
                ))

            # Store enhanced protocol patterns
            for proto_data in results.get("protocol_patterns", []):
                # S7-specific fields go in protocol_metadata
                s7_metadata = {}
                if proto_data.get("pdu_sizes"):
                    s7_metadata["pdu_sizes"] = proto_data["pdu_sizes"]
                if proto_data.get("rack_slot_configs"):
                    s7_metadata["rack_slot_configs"] = proto_data["rack_slot_configs"]
                if proto_data.get("memory_areas"):
                    s7_metadata["memory_areas"] = proto_data["memory_areas"]

                new_objects.append(LearnedProtocolPattern(
                    pcap_capture_id=capture.id,
                    protocol=proto_data["protocol"],
                    function_codes=proto_data.get("function_codes"),
                    address_patterns=proto_data.get("address_patterns"),
                    payload_structures=proto_data.get("payload_structures"),
                    request_response_pairs=proto_data.get("request_response_pairs"),
                    unit_id_distribution=proto_data.get("unit_id_distribution"),
                    exception_patterns=proto_data.get("exception_patterns"),
                    device_identities=proto_data.get("device_identities"),
                    protocol_metadata=s7_metadata if s7_metadata else None,
                    sample_count=proto_data.get("packet_count", proto_data.get("sample_count", 0)),
                ))

            # Store device fingerprint templates (aggregated, not per-device)
            for fp_data in results.get("device_fingerprints", []):
                # Get role value - ensure lowercase for PostgreSQL enum
                role_str = fp_data.get("role", "unknown").lower()
                if role_str not in ("master", "slave", "both", "unknown"):
                    role_str = "unknown"

                new_objects.append(DeviceTemplate(
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
                ))

            # Store learned sequences
            valid_sequence_types = {
                "startup", "shutdown", "poll_cycle", "write_sequence",
                "error_recovery", "state_transition", "heartbeat", "alarm"
            }
            for seq_data in results.get("learned_sequences", []):
                seq_type = seq_data.get("sequence_type", "").lower()
                if seq_type not in valid_sequence_types:
                    continue  # Skip invalid sequence types

                new_objects.append(LearnedSequence(
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
                ))

            # Batch insert all objects
            if new_objects:
                db.add_all(new_objects)
            await db.commit()

            # Invalidate fingerprint cache so new learned data is visible
            from app.services.fingerprint_cache import invalidate_fingerprint_cache
            invalidate_fingerprint_cache()

            logger.info(f"Successfully processed PCAP {capture_id}")

        except Exception as e:
            logger.exception(f"Failed to process PCAP {capture_id}: {e}")
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


# ========== Learning Session Endpoints ==========


class LearningSessionCreate(BaseModel):
    """Request to create a learning session."""

    name: str
    description: str | None = None
    source_environment: str | None = None
    industry_vertical: str | None = None
    network_description: str | None = None
    tags: list[str] | None = None


class LearningSessionUpdate(BaseModel):
    """Request to update a learning session."""

    name: str | None = None
    description: str | None = None
    source_environment: str | None = None
    industry_vertical: str | None = None
    network_description: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class LearningSessionResponse(BaseModel):
    """Response for a learning session."""

    id: str
    name: str
    description: str | None
    status: str
    source_environment: str | None
    industry_vertical: str | None
    network_description: str | None
    tags: list | None
    capture_count: int
    total_packets: int
    total_flows: int
    total_duration_ms: float | None
    protocols_detected: list | None
    protocol_stats: dict | None
    aggregate_confidence: float | None
    pattern_count: int
    fingerprint_count: int
    sequence_count: int
    created_at: datetime
    updated_at: datetime
    analyzed_at: datetime | None

    class Config:
        from_attributes = True


class LearningSessionListResponse(BaseModel):
    """Response for learning session list."""

    sessions: list[LearningSessionResponse]
    total: int
    page: int
    page_size: int


class ApplySessionPatternsRequest(BaseModel):
    """Request to apply session patterns to a scenario."""

    scenario_id: str
    apply_fingerprints: bool = True
    apply_timing: bool = True
    apply_sequences: bool = False
    min_confidence: float = 0.5


class ApplySessionPatternsResponse(BaseModel):
    """Response from applying session patterns."""

    session_id: str
    scenario_id: str
    devices_updated: int
    patterns_applied: int
    fingerprints_applied: int
    sequences_applied: int
    message: str


@router.get("/sessions", response_model=LearningSessionListResponse)
async def list_learning_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    industry_vertical: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List learning sessions with pagination and filtering."""
    from app.models.learning_session import LearningSession, SessionStatus

    query = select(LearningSession).order_by(LearningSession.created_at.desc())

    if status:
        query = query.where(LearningSession.status == SessionStatus(status))
    if industry_vertical:
        query = query.where(LearningSession.industry_vertical == industry_vertical)

    # Get total count
    count_query = select(LearningSession)
    if status:
        count_query = count_query.where(LearningSession.status == SessionStatus(status))
    if industry_vertical:
        count_query = count_query.where(LearningSession.industry_vertical == industry_vertical)
    result = await db.execute(count_query)
    total = len(result.scalars().all())

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    sessions = result.scalars().all()

    return LearningSessionListResponse(
        sessions=[
            LearningSessionResponse(
                id=str(s.id),
                name=s.name,
                description=s.description,
                status=s.status.value,
                source_environment=s.source_environment,
                industry_vertical=s.industry_vertical,
                network_description=s.network_description,
                tags=s.tags,
                capture_count=s.capture_count,
                total_packets=s.total_packets,
                total_flows=s.total_flows,
                total_duration_ms=s.total_duration_ms,
                protocols_detected=s.protocols_detected,
                protocol_stats=s.protocol_stats,
                aggregate_confidence=s.aggregate_confidence,
                pattern_count=s.pattern_count,
                fingerprint_count=s.fingerprint_count,
                sequence_count=s.sequence_count,
                created_at=s.created_at,
                updated_at=s.updated_at,
                analyzed_at=s.analyzed_at,
            )
            for s in sessions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/sessions", response_model=LearningSessionResponse, status_code=201)
async def create_learning_session(
    request: LearningSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new learning session for grouping related PCAP uploads."""
    from app.models.learning_session import LearningSession, SessionStatus

    session = LearningSession(
        name=request.name,
        description=request.description,
        status=SessionStatus.ACTIVE,
        source_environment=request.source_environment,
        industry_vertical=request.industry_vertical,
        network_description=request.network_description,
        tags=request.tags,
    )

    db.add(session)
    await db.flush()
    await db.refresh(session)

    return LearningSessionResponse(
        id=str(session.id),
        name=session.name,
        description=session.description,
        status=session.status.value,
        source_environment=session.source_environment,
        industry_vertical=session.industry_vertical,
        network_description=session.network_description,
        tags=session.tags,
        capture_count=session.capture_count,
        total_packets=session.total_packets,
        total_flows=session.total_flows,
        total_duration_ms=session.total_duration_ms,
        protocols_detected=session.protocols_detected,
        protocol_stats=session.protocol_stats,
        aggregate_confidence=session.aggregate_confidence,
        pattern_count=session.pattern_count,
        fingerprint_count=session.fingerprint_count,
        sequence_count=session.sequence_count,
        created_at=session.created_at,
        updated_at=session.updated_at,
        analyzed_at=session.analyzed_at,
    )


@router.get("/sessions/{session_id}", response_model=LearningSessionResponse)
async def get_learning_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific learning session."""
    from app.models.learning_session import LearningSession

    result = await db.execute(
        select(LearningSession).where(LearningSession.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Learning session not found")

    return LearningSessionResponse(
        id=str(session.id),
        name=session.name,
        description=session.description,
        status=session.status.value,
        source_environment=session.source_environment,
        industry_vertical=session.industry_vertical,
        network_description=session.network_description,
        tags=session.tags,
        capture_count=session.capture_count,
        total_packets=session.total_packets,
        total_flows=session.total_flows,
        total_duration_ms=session.total_duration_ms,
        protocols_detected=session.protocols_detected,
        protocol_stats=session.protocol_stats,
        aggregate_confidence=session.aggregate_confidence,
        pattern_count=session.pattern_count,
        fingerprint_count=session.fingerprint_count,
        sequence_count=session.sequence_count,
        created_at=session.created_at,
        updated_at=session.updated_at,
        analyzed_at=session.analyzed_at,
    )


@router.put("/sessions/{session_id}", response_model=LearningSessionResponse)
async def update_learning_session(
    session_id: str,
    request: LearningSessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a learning session."""
    from app.models.learning_session import LearningSession, SessionStatus

    result = await db.execute(
        select(LearningSession).where(LearningSession.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Learning session not found")

    # Update fields
    if request.name is not None:
        session.name = request.name
    if request.description is not None:
        session.description = request.description
    if request.source_environment is not None:
        session.source_environment = request.source_environment
    if request.industry_vertical is not None:
        session.industry_vertical = request.industry_vertical
    if request.network_description is not None:
        session.network_description = request.network_description
    if request.tags is not None:
        session.tags = request.tags
    if request.status is not None:
        session.status = SessionStatus(request.status)

    await db.flush()
    await db.refresh(session)

    return LearningSessionResponse(
        id=str(session.id),
        name=session.name,
        description=session.description,
        status=session.status.value,
        source_environment=session.source_environment,
        industry_vertical=session.industry_vertical,
        network_description=session.network_description,
        tags=session.tags,
        capture_count=session.capture_count,
        total_packets=session.total_packets,
        total_flows=session.total_flows,
        total_duration_ms=session.total_duration_ms,
        protocols_detected=session.protocols_detected,
        protocol_stats=session.protocol_stats,
        aggregate_confidence=session.aggregate_confidence,
        pattern_count=session.pattern_count,
        fingerprint_count=session.fingerprint_count,
        sequence_count=session.sequence_count,
        created_at=session.created_at,
        updated_at=session.updated_at,
        analyzed_at=session.analyzed_at,
    )


@router.delete("/sessions/{session_id}")
async def delete_learning_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a learning session and all associated captures."""
    from app.models.learning_session import LearningSession

    result = await db.execute(
        select(LearningSession).where(LearningSession.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Learning session not found")

    await db.delete(session)
    # Note: commit handled by get_db dependency

    return {"message": "Learning session deleted successfully"}


@router.post("/sessions/{session_id}/apply", response_model=ApplySessionPatternsResponse)
async def apply_session_patterns(
    session_id: str,
    request: ApplySessionPatternsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Apply learned patterns from a session to a scenario.

    This aggregates patterns from all PCAP captures in the session and applies
    them to the specified scenario's devices based on protocol matching.
    """
    from app.models.learning_session import LearningSession
    from app.models.scenario import Scenario

    # Get session
    result = await db.execute(
        select(LearningSession).where(LearningSession.id == uuid.UUID(session_id))
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Learning session not found")

    # Get scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(request.scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Get all fingerprints from captures in this session (single query)
    capture_ids = [c.id for c in session.pcap_captures]
    if capture_ids:
        fps_result = await db.execute(
            select(DeviceTemplate).where(
                DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
                DeviceTemplate.source_pcap_id.in_(capture_ids),
                DeviceTemplate.confidence >= request.min_confidence,
            )
        )
        fingerprints = list(fps_result.scalars().all())
    else:
        fingerprints = []

    # Get all sequences from captures in this session (single query)
    sequences = []
    if request.apply_sequences and capture_ids:
        seqs_result = await db.execute(
            select(LearnedSequence).where(
                LearnedSequence.pcap_capture_id.in_(capture_ids),
                LearnedSequence.confidence >= request.min_confidence,
            )
        )
        sequences = list(seqs_result.scalars().all())

    # Apply patterns to scenario devices
    definition = scenario.definition or {}
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    devices_updated = 0
    patterns_applied = 0
    fingerprints_applied = 0
    sequences_applied = 0

    # Build device -> protocol mapping from flows
    device_protocols: dict[str, set[str]] = {}
    for flow in flows.values():
        source_id = flow.get("sourceDeviceId") or flow.get("source_device_id")
        target_id = flow.get("targetDeviceId") or flow.get("target_device_id")
        protocol = flow.get("protocol", "").lower()

        if protocol:
            if source_id:
                device_protocols.setdefault(source_id, set()).add(protocol)
            if target_id:
                device_protocols.setdefault(target_id, set()).add(protocol)

    # Apply fingerprints to matching devices
    for device_id, device in devices.items():
        device_type = device.get("deviceType", "").lower()
        protocols = device_protocols.get(device_id, set())

        if not protocols:
            continue

        device_updated = False

        # Find best matching fingerprint
        for fp in fingerprints:
            fp_protocols = set(fp.active_protocols or [])
            if not protocols.intersection(fp_protocols):
                continue

            # Apply fingerprint data
            if request.apply_fingerprints:
                if fp.tcp_signature:
                    device.setdefault("learned_fingerprint", {})["tcp_signature"] = fp.tcp_signature
                if fp.response_timings and request.apply_timing:
                    device.setdefault("learned_fingerprint", {})["response_timings"] = fp.response_timings
                if fp.protocol_identities:
                    device.setdefault("learned_fingerprint", {})["protocol_identities"] = fp.protocol_identities
                fingerprints_applied += 1
                device_updated = True
                break  # Use first matching fingerprint

        # Apply sequences
        if request.apply_sequences:
            device_sequences = []
            for seq in sequences:
                if seq.protocol.lower() in protocols:
                    device_sequences.append({
                        "id": str(seq.id),
                        "name": seq.name,
                        "type": str(seq.sequence_type),
                        "protocol": seq.protocol,
                        "steps": seq.steps,
                    })
                    sequences_applied += 1

            if device_sequences:
                device["learned_sequences"] = device_sequences
                device_updated = True

        if device_updated:
            devices_updated += 1
            patterns_applied += 1

    # Update scenario
    definition["devices"] = devices
    scenario.definition = definition
    scenario.version += 1

    await db.flush()

    return ApplySessionPatternsResponse(
        session_id=session_id,
        scenario_id=request.scenario_id,
        devices_updated=devices_updated,
        patterns_applied=patterns_applied,
        fingerprints_applied=fingerprints_applied,
        sequences_applied=sequences_applied,
        message=f"Applied patterns from {session.capture_count} captures to {devices_updated} devices",
    )
