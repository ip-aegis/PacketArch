"""Docker host schemas for API validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DockerHostBase(BaseModel):
    """Base schema for Docker host."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    docker_api_url: str = Field(
        ...,
        min_length=1,
        max_length=500,
        pattern=r"^(tcp|unix|ssh)://",
        description="Docker API URL (e.g., tcp://192.168.1.100:2376)",
    )
    tls_enabled: bool = True
    default_interface: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class DockerHostCreate(DockerHostBase):
    """Schema for creating a Docker host."""

    ca_cert: str | None = Field(default=None, description="PEM-encoded CA certificate")
    client_cert: str | None = Field(
        default=None, description="PEM-encoded client certificate"
    )
    client_key: str | None = Field(
        default=None, description="PEM-encoded client private key"
    )

    @field_validator("ca_cert", "client_cert", "client_key")
    @classmethod
    def validate_pem_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if v and not (v.startswith("-----BEGIN") and v.endswith("-----")):
            raise ValueError("Certificate must be in PEM format")
        return v


class DockerHostUpdate(BaseModel):
    """Schema for updating a Docker host."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    docker_api_url: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        pattern=r"^(tcp|unix|ssh)://",
    )
    tls_enabled: bool | None = None
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None
    default_interface: str | None = None
    is_active: bool | None = None


class DockerHostResponse(BaseModel):
    """Schema for Docker host response."""

    id: UUID
    name: str
    description: str | None
    docker_api_url: str
    tls_enabled: bool
    default_interface: str | None
    is_active: bool
    # Don't expose certificates in response
    has_ca_cert: bool = False
    has_client_cert: bool = False
    has_client_key: bool = False
    last_connected_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, host) -> "DockerHostResponse":
        """Create response from model, computing has_* fields."""
        return cls(
            id=host.id,
            name=host.name,
            description=host.description,
            docker_api_url=host.docker_api_url,
            tls_enabled=host.tls_enabled,
            default_interface=host.default_interface,
            is_active=host.is_active,
            has_ca_cert=bool(host.ca_cert),
            has_client_cert=bool(host.client_cert),
            has_client_key=bool(host.client_key),
            last_connected_at=host.last_connected_at,
            created_at=host.created_at,
            updated_at=host.updated_at,
        )


class DockerHostListResponse(BaseModel):
    """Schema for listing Docker hosts."""

    items: list[DockerHostResponse]
    total: int


class DockerHostTestRequest(BaseModel):
    """Schema for testing Docker host connection."""

    timeout_seconds: int = Field(default=10, ge=1, le=60)


class DockerHostTestResult(BaseModel):
    """Schema for Docker host connection test result."""

    success: bool
    message: str
    docker_version: str | None = None
    api_version: str | None = None
    latency_ms: float | None = None


class DockerHostInterface(BaseModel):
    """Schema for a network interface on a Docker host."""

    name: str
    mac_address: str | None = None
    ip_addresses: list[str] = []
    is_up: bool = True


class DockerHostInterfaceList(BaseModel):
    """Schema for listing network interfaces on a Docker host."""

    host_id: UUID
    host_name: str
    interfaces: list[DockerHostInterface]
