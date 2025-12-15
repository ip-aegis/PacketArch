"""API routes for traffic generation."""

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.scenario import Scenario
from app.models.user import User
from app.protocol_engines import list_supported_protocols
from app.schemas.generation import (
    GenerationJobResponse,
    GenerationRequest,
    JobListResponse,
    SupportedProtocolsResponse,
)
from app.traffic_generator.tasks import create_job, generate_traffic, get_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generation", tags=["generation"])


@router.post("", response_model=GenerationJobResponse, status_code=status.HTTP_201_CREATED)
async def start_generation(
    request: GenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationJobResponse:
    """Start a new traffic generation job.

    Args:
        request: Generation request parameters
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created generation job details

    Raises:
        HTTPException: If scenario not found or validation fails
    """
    # Verify scenario exists and user has access
    result = await db.execute(
        select(Scenario).where(Scenario.id == request.scenario_id)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {request.scenario_id} not found",
        )

    # Check user access (if scenario has user_id, must match current user or be admin)
    if scenario.user_id and scenario.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this scenario",
        )

    # Determine duration
    duration_ms = request.duration_override_ms or scenario.total_duration_ms

    # Validate duration
    if duration_ms > settings.max_simulation_duration_ms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duration exceeds maximum of {settings.max_simulation_duration_ms}ms",
        )

    # Create job
    job = create_job(
        scenario_id=scenario.id,
        user_id=current_user.id,
        total_duration_ms=duration_ms,
    )

    # Start Celery task
    try:
        task = generate_traffic.apply_async(
            kwargs={
                "job_id": job.job_id,
                "scenario_id": str(scenario.id),
                "duration_ms": duration_ms,
            }
        )
        logger.info(f"Started generation task {task.id} for job {job.job_id}")

    except Exception as e:
        logger.error(f"Failed to start generation task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start generation task",
        )

    return GenerationJobResponse(
        job_id=job.job_id,
        scenario_id=job.scenario_id,
        status=job.status.value,
        progress=job.progress,
        total_duration_ms=job.total_duration_ms,
        output_path=job.output_path,
        packets_generated=job.packets_generated,
        file_size_bytes=job.file_size_bytes,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/{job_id}", response_model=GenerationJobResponse)
async def get_generation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> GenerationJobResponse:
    """Get status of a generation job.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user

    Returns:
        Job status and details

    Raises:
        HTTPException: If job not found
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Check user access (user must own job or be admin)
    if job.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job",
        )

    return GenerationJobResponse(
        job_id=job.job_id,
        scenario_id=job.scenario_id,
        status=job.status.value,
        progress=job.progress,
        total_duration_ms=job.total_duration_ms,
        output_path=job.output_path,
        packets_generated=job.packets_generated,
        file_size_bytes=job.file_size_bytes,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/{job_id}/download")
async def download_pcap(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Download the generated PCAP file.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user

    Returns:
        PCAP file download

    Raises:
        HTTPException: If job not found, not completed, or file missing
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Check user access
    if job.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job",
        )

    # Check job is completed
    if job.status.value != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed (status: {job.status.value})",
        )

    # Check output file exists
    if not job.output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output file path not available",
        )

    output_path = Path(job.output_path)
    if not output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output file not found",
        )

    # Return file
    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.tcpdump.pcap",
        filename=output_path.name,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_generation(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    """Cancel a running generation job.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user

    Raises:
        HTTPException: If job not found or cannot be cancelled
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Check user access
    if job.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job",
        )

    # Check if job can be cancelled
    if job.status.value in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status.value} state",
        )

    # Implement Celery task cancellation
    from celery.result import AsyncResult
    from app.traffic_generator.models import JobStatus
    from app.traffic_generator.tasks import update_job, celery_app

    # Try to revoke the Celery task if we have a task ID
    task_id = job.custom_data.get("celery_task_id") if hasattr(job, "custom_data") else None
    if task_id:
        try:
            # Revoke the task - terminate=True will kill running tasks
            celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
            logger.info(f"Revoked Celery task {task_id} for job {job_id}")
        except Exception as e:
            logger.warning(f"Failed to revoke Celery task: {e}")

    # Mark job as cancelled
    job.status = JobStatus.CANCELLED
    update_job(job)

    logger.info(f"Cancelled job {job_id}")


@router.get("/protocols/supported", response_model=SupportedProtocolsResponse)
async def get_supported_protocols(
    current_user: User = Depends(get_current_user),
) -> SupportedProtocolsResponse:
    """Get list of supported protocol types.

    Args:
        current_user: Current authenticated user

    Returns:
        List of supported protocols
    """
    protocols = list_supported_protocols()
    protocol_names = [p.value for p in protocols]

    return SupportedProtocolsResponse(protocols=protocol_names)
