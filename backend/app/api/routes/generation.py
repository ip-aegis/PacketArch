"""API routes for traffic generation."""

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.core.exceptions import ExternalServiceError, NotFoundError, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.generation_job import GenerationJob as GenerationJobModel, GenerationJobStatus
from app.models.scenario import Scenario
from app.models.user import User
from app.protocol_engines import list_supported_protocols
from app.schemas.generation import (
    GenerationJobResponse,
    GenerationRequest,
    JobListResponse,
    SupportedProtocolsResponse,
)
from app.traffic_generator.tasks import create_job_in_db, generate_traffic, celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generation", tags=["generation"])


def _job_model_to_response(job: GenerationJobModel) -> GenerationJobResponse:
    """Convert database model to response schema."""
    return GenerationJobResponse(
        job_id=str(job.id),
        scenario_id=job.scenario_id,
        scenario_name=job.scenario.name if job.scenario else None,
        status=job.status,
        progress=job.progress,
        total_duration_ms=job.total_duration_ms,
        output_path=job.output_path,
        packets_generated=job.packets_generated,
        file_size_bytes=job.file_size_bytes,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status", description="Filter by job status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
) -> JobListResponse:
    """List generation jobs for the current user.

    Args:
        current_user: Current authenticated user
        db: Database session
        status_filter: Optional status filter
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip

    Returns:
        Paginated list of generation jobs
    """
    # Build query
    query = select(GenerationJobModel).options(selectinload(GenerationJobModel.scenario))

    # Filter by user (unless admin)
    if not current_user.is_admin:
        query = query.where(GenerationJobModel.user_id == current_user.id)

    # Filter by status
    if status_filter:
        query = query.where(GenerationJobModel.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Add pagination and ordering
    query = query.order_by(GenerationJobModel.created_at.desc()).offset(offset).limit(limit)

    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[_job_model_to_response(job) for job in jobs],
        total=total,
    )


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
        raise NotFoundError("Scenario", str(request.scenario_id))

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
        raise ValidationError(f"Duration exceeds maximum of {settings.max_simulation_duration_ms}ms")

    # Create job in database
    job = await create_job_in_db(
        scenario_id=scenario.id,
        user_id=current_user.id,
        total_duration_ms=duration_ms,
    )

    # Start Celery task
    try:
        task = generate_traffic.apply_async(
            kwargs={
                "job_id": str(job.id),
                "scenario_id": str(scenario.id),
                "duration_ms": duration_ms,
            }
        )
        logger.info(f"Started generation task {task.id} for job {job.id}")

        # Store the celery task ID in the job
        job.celery_task_id = task.id
        await db.flush()

    except Exception as e:
        logger.error(f"Failed to start generation task: {e}", exc_info=True)
        raise ExternalServiceError(service="celery", message="Failed to start generation task", original_error=e)

    return GenerationJobResponse(
        job_id=str(job.id),
        scenario_id=job.scenario_id,
        scenario_name=scenario.name,
        status=job.status,
        progress=job.progress,
        total_duration_ms=job.total_duration_ms,
        output_path=job.output_path,
        packets_generated=job.packets_generated,
        file_size_bytes=job.file_size_bytes,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/{job_id}", response_model=GenerationJobResponse)
async def get_generation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationJobResponse:
    """Get status of a generation job.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        db: Database session

    Returns:
        Job status and details

    Raises:
        HTTPException: If job not found
    """
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise ValidationError("Invalid job ID format")

    result = await db.execute(
        select(GenerationJobModel)
        .options(selectinload(GenerationJobModel.scenario))
        .where(GenerationJobModel.id == job_uuid)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError("Generation job", job_id)

    # Check user access (user must own job or be admin)
    if job.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job",
        )

    return _job_model_to_response(job)


@router.get("/{job_id}/download")
async def download_pcap(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Download the generated PCAP file.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        db: Database session

    Returns:
        PCAP file download

    Raises:
        HTTPException: If job not found, not completed, or file missing
    """
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise ValidationError("Invalid job ID format")

    result = await db.execute(
        select(GenerationJobModel).where(GenerationJobModel.id == job_uuid)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError("Generation job", job_id)

    # Check user access
    if job.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job",
        )

    # Check job is completed
    if job.status != GenerationJobStatus.COMPLETED.value:
        raise ValidationError(f"Job is not completed (status: {job.status})")

    # Check output file exists
    output_path = job.output_path
    if not output_path:
        raise NotFoundError("Output file path")

    output_path_obj = Path(output_path)
    if not output_path_obj.exists():
        raise NotFoundError("Output file")

    # Return file
    return FileResponse(
        path=str(output_path_obj),
        media_type="application/vnd.tcpdump.pcap",
        filename=output_path_obj.name,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_generation(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Cancel a running generation job.

    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If job not found or cannot be cancelled
    """
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise ValidationError("Invalid job ID format")

    result = await db.execute(
        select(GenerationJobModel).where(GenerationJobModel.id == job_uuid)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError("Generation job", job_id)

    # Check user access
    if job.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job",
        )

    # Check if job can be cancelled
    terminal_statuses = [
        GenerationJobStatus.COMPLETED.value,
        GenerationJobStatus.FAILED.value,
        GenerationJobStatus.CANCELLED.value,
    ]
    if job.status in terminal_statuses:
        raise ValidationError(f"Cannot cancel job in {job.status} state")

    # Try to revoke the Celery task if we have a task ID
    if job.celery_task_id:
        try:
            # Revoke the task - terminate=True will kill running tasks
            celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")
            logger.info(f"Revoked Celery task {job.celery_task_id} for job {job_id}")
        except Exception as e:
            logger.warning(f"Failed to revoke Celery task: {e}")

    # Mark job as cancelled
    job.status = GenerationJobStatus.CANCELLED.value
    await db.flush()

    logger.info(f"Cancelled job {job_id}")


@router.delete("/{job_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a generation job record (and optionally the PCAP file).

    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If job not found or still running
    """
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise ValidationError("Invalid job ID format")

    result = await db.execute(
        select(GenerationJobModel).where(GenerationJobModel.id == job_uuid)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError("Generation job", job_id)

    # Check user access
    if job.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job",
        )

    # Can only delete jobs that are not running
    if job.status in [GenerationJobStatus.PENDING.value, GenerationJobStatus.RUNNING.value]:
        raise ValidationError(f"Cannot delete job in {job.status} state. Cancel it first.")

    # Optionally delete the PCAP file
    if job.output_path:
        output_path = Path(job.output_path)
        if output_path.exists():
            try:
                output_path.unlink()
                logger.info(f"Deleted PCAP file: {output_path}")
            except Exception as e:
                logger.warning(f"Failed to delete PCAP file: {e}")

    # Delete the job record
    await db.delete(job)
    await db.flush()

    logger.info(f"Deleted job {job_id}")


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
