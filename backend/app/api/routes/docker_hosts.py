"""Docker hosts management routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AdminUser, DBSession
from app.core.encryption import decrypt_value, encrypt_value
from app.models.docker_host import DockerHost
from app.schemas.docker_host import (
    DockerHostCreate,
    DockerHostInterfaceList,
    DockerHostListResponse,
    DockerHostResponse,
    DockerHostTestResult,
    DockerHostUpdate,
)
from app.services.docker_service import docker_service

router = APIRouter(prefix="/docker-hosts", tags=["Docker Hosts"])


@router.get("", response_model=DockerHostListResponse)
async def list_docker_hosts(
    db: DBSession,
    _admin: AdminUser,
) -> DockerHostListResponse:
    """List all Docker hosts."""
    result = await db.execute(
        select(DockerHost).order_by(DockerHost.name)
    )
    hosts = result.scalars().all()

    return DockerHostListResponse(
        items=[DockerHostResponse.from_model(host) for host in hosts],
        total=len(hosts),
    )


@router.post("", response_model=DockerHostResponse, status_code=status.HTTP_201_CREATED)
async def create_docker_host(
    data: DockerHostCreate,
    db: DBSession,
    admin: AdminUser,
) -> DockerHostResponse:
    """Create a new Docker host."""
    # Check for duplicate name
    result = await db.execute(
        select(DockerHost).where(DockerHost.name == data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Docker host with name '{data.name}' already exists",
        )

    # Encrypt client key if provided
    client_key = data.client_key
    if client_key:
        client_key = encrypt_value(client_key)

    host = DockerHost(
        name=data.name,
        description=data.description,
        docker_api_url=data.docker_api_url,
        tls_enabled=data.tls_enabled,
        ca_cert=data.ca_cert,
        client_cert=data.client_cert,
        client_key=client_key,
        default_interface=data.default_interface,
        is_active=data.is_active,
        created_by_id=admin.id,
    )

    db.add(host)
    await db.commit()
    await db.refresh(host)

    return DockerHostResponse.from_model(host)


@router.get("/{host_id}", response_model=DockerHostResponse)
async def get_docker_host(
    host_id: UUID,
    db: DBSession,
    _admin: AdminUser,
) -> DockerHostResponse:
    """Get a Docker host by ID."""
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == host_id)
    )
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docker host not found",
        )

    return DockerHostResponse.from_model(host)


@router.put("/{host_id}", response_model=DockerHostResponse)
async def update_docker_host(
    host_id: UUID,
    data: DockerHostUpdate,
    db: DBSession,
    _admin: AdminUser,
) -> DockerHostResponse:
    """Update a Docker host."""
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == host_id)
    )
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docker host not found",
        )

    # Check for duplicate name if changing
    if data.name and data.name != host.name:
        result = await db.execute(
            select(DockerHost).where(DockerHost.name == data.name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Docker host with name '{data.name}' already exists",
            )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # Encrypt client key if provided
    if "client_key" in update_data and update_data["client_key"]:
        update_data["client_key"] = encrypt_value(update_data["client_key"])

    for key, value in update_data.items():
        setattr(host, key, value)

    await db.commit()
    await db.refresh(host)

    return DockerHostResponse.from_model(host)


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_docker_host(
    host_id: UUID,
    db: DBSession,
    _admin: AdminUser,
) -> None:
    """Delete a Docker host."""
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == host_id)
    )
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docker host not found",
        )

    await db.delete(host)
    await db.commit()


@router.post("/{host_id}/test", response_model=DockerHostTestResult)
async def test_docker_host_connection(
    host_id: UUID,
    db: DBSession,
    _admin: AdminUser,
) -> DockerHostTestResult:
    """Test connection to a Docker host."""
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == host_id)
    )
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docker host not found",
        )

    # Decrypt client key for connection - store in temp var to avoid modifying model
    decrypted_key = decrypt_value(host.client_key) if host.client_key else None

    # Expunge from session so we can safely modify for docker_service without affecting DB
    await db.refresh(host)
    db.expunge(host)

    # Now safe to modify for connection
    host.client_key = decrypted_key

    test_result = docker_service.test_connection(host)

    # Update last_connected_at on success using a fresh update
    if test_result.success:
        from datetime import datetime, timezone
        from sqlalchemy import update
        await db.execute(
            update(DockerHost)
            .where(DockerHost.id == host_id)
            .values(last_connected_at=datetime.now(timezone.utc))
        )
        await db.commit()

    return DockerHostTestResult(
        success=test_result.success,
        message=test_result.message,
        docker_version=test_result.docker_version,
        api_version=test_result.api_version,
        latency_ms=test_result.latency_ms,
    )


@router.get("/{host_id}/interfaces", response_model=DockerHostInterfaceList)
async def list_docker_host_interfaces(
    host_id: UUID,
    db: DBSession,
    _admin: AdminUser,
) -> DockerHostInterfaceList:
    """List network interfaces on a Docker host."""
    result = await db.execute(
        select(DockerHost).where(DockerHost.id == host_id)
    )
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docker host not found",
        )

    # Decrypt client key for connection - store in temp var to avoid modifying model
    decrypted_key = decrypt_value(host.client_key) if host.client_key else None

    # Expunge from session so we can safely modify for docker_service without affecting DB
    await db.refresh(host)
    db.expunge(host)

    # Now safe to modify for connection
    host.client_key = decrypted_key

    try:
        interfaces = docker_service.list_interfaces(host)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list interfaces: {str(e)}",
        )

    return DockerHostInterfaceList(
        host_id=host.id,
        host_name=host.name,
        interfaces=[
            {
                "name": iface.name,
                "mac_address": iface.mac_address,
                "ip_addresses": iface.ip_addresses,
                "is_up": iface.is_up,
            }
            for iface in interfaces
        ],
    )
