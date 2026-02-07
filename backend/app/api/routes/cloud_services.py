"""Cloud service endpoints API routes."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError

from app.api.deps import CurrentUser, DBSession
from app.models.cloud_service import CloudServiceEndpoint, CloudServiceProvider
from app.schemas.cloud_service import (
    CloudServiceEndpointCreate,
    CloudServiceEndpointListResponse,
    CloudServiceEndpointResponse,
    CloudServiceEndpointUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cloud-services", tags=["Cloud Services"])


@router.get("", response_model=CloudServiceEndpointListResponse)
async def list_cloud_services(
    db: DBSession,
    _current_user: CurrentUser,
    provider: CloudServiceProvider | None = None,
    include_inactive: bool = False,
) -> CloudServiceEndpointListResponse:
    """List all cloud service endpoints.

    Args:
        provider: Optional filter by provider
        include_inactive: Include inactive services

    Returns:
        List of cloud service endpoints
    """
    query = select(CloudServiceEndpoint)

    if provider:
        query = query.where(CloudServiceEndpoint.provider == provider)

    if not include_inactive:
        query = query.where(CloudServiceEndpoint.is_active == True)

    query = query.order_by(CloudServiceEndpoint.provider, CloudServiceEndpoint.name)

    result = await db.execute(query)
    services = result.scalars().all()

    return CloudServiceEndpointListResponse(
        items=[CloudServiceEndpointResponse.model_validate(s) for s in services],
        total=len(services),
    )


@router.get("/{service_id}", response_model=CloudServiceEndpointResponse)
async def get_cloud_service(
    service_id: UUID,
    db: DBSession,
    _current_user: CurrentUser,
) -> CloudServiceEndpointResponse:
    """Get a cloud service endpoint by ID.

    Args:
        service_id: Cloud service endpoint ID

    Returns:
        Cloud service endpoint details
    """
    result = await db.execute(
        select(CloudServiceEndpoint).where(CloudServiceEndpoint.id == service_id)
    )
    service = result.scalar_one_or_none()

    if not service:
        raise NotFoundError("Cloud service endpoint", str(service_id))

    return CloudServiceEndpointResponse.model_validate(service)


@router.post("", response_model=CloudServiceEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_cloud_service(
    request: CloudServiceEndpointCreate,
    db: DBSession,
    _current_user: CurrentUser,
) -> CloudServiceEndpointResponse:
    """Create a new cloud service endpoint.

    Args:
        request: Cloud service endpoint data

    Returns:
        Created cloud service endpoint
    """
    # Check for duplicate name
    result = await db.execute(
        select(CloudServiceEndpoint).where(CloudServiceEndpoint.name == request.name)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise ConflictError(f"Cloud service endpoint with name '{request.name}' already exists", resource="Cloud service endpoint")

    service = CloudServiceEndpoint(
        name=request.name,
        provider=request.provider,
        ip_addresses=request.ip_addresses,
        primary_ip=request.primary_ip,
        port=request.port,
        hostname=request.hostname,
        tls_enabled=request.tls_enabled,
        heartbeat_interval_ms=request.heartbeat_interval_ms,
        region=request.region,
        description=request.description,
        is_builtin=False,
        is_active=True,
    )

    db.add(service)
    await db.flush()
    await db.refresh(service)

    logger.info(f"Created cloud service endpoint: {service.name} ({service.provider})")
    return CloudServiceEndpointResponse.model_validate(service)


@router.put("/{service_id}", response_model=CloudServiceEndpointResponse)
async def update_cloud_service(
    service_id: UUID,
    request: CloudServiceEndpointUpdate,
    db: DBSession,
    _current_user: CurrentUser,
) -> CloudServiceEndpointResponse:
    """Update a cloud service endpoint.

    Args:
        service_id: Cloud service endpoint ID
        request: Updated cloud service endpoint data

    Returns:
        Updated cloud service endpoint
    """
    result = await db.execute(
        select(CloudServiceEndpoint).where(CloudServiceEndpoint.id == service_id)
    )
    service = result.scalar_one_or_none()

    if not service:
        raise NotFoundError("Cloud service endpoint", str(service_id))

    # Prevent modification of builtin services (except is_active)
    if service.is_builtin:
        update_data = request.model_dump(exclude_unset=True)
        allowed_builtin_updates = {"is_active"}
        non_allowed_fields = set(update_data.keys()) - allowed_builtin_updates

        if non_allowed_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot modify builtin cloud service endpoint fields: {non_allowed_fields}",
            )

    # Check for duplicate name if updating name
    if request.name and request.name != service.name:
        result = await db.execute(
            select(CloudServiceEndpoint).where(CloudServiceEndpoint.name == request.name)
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise ConflictError(f"Cloud service endpoint with name '{request.name}' already exists", resource="Cloud service endpoint")

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)

    await db.flush()
    await db.refresh(service)

    logger.info(f"Updated cloud service endpoint: {service.name}")
    return CloudServiceEndpointResponse.model_validate(service)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cloud_service(
    service_id: UUID,
    db: DBSession,
    _current_user: CurrentUser,
) -> None:
    """Delete a cloud service endpoint.

    Args:
        service_id: Cloud service endpoint ID

    Raises:
        HTTPException: If service not found or is builtin
    """
    result = await db.execute(
        select(CloudServiceEndpoint).where(CloudServiceEndpoint.id == service_id)
    )
    service = result.scalar_one_or_none()

    if not service:
        raise NotFoundError("Cloud service endpoint", str(service_id))

    if service.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete builtin cloud service endpoint",
        )

    await db.delete(service)
    logger.info(f"Deleted cloud service endpoint: {service.name}")


@router.get("/providers/list", response_model=list[str])
async def list_providers(
    _current_user: CurrentUser,
) -> list[str]:
    """List available cloud service providers.

    Returns:
        List of provider names
    """
    return [p.value for p in CloudServiceProvider]
