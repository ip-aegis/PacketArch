"""Docker host model for remote traffic generator deployment."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DockerHost(Base):
    """Docker host configuration for remote deployment."""

    __tablename__ = "docker_hosts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Docker API URL, e.g., "tcp://192.168.1.100:2376"
    docker_api_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    tls_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # TLS certificates (PEM-encoded, encrypted for client_key)
    ca_cert: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    client_cert: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Client key is encrypted before storage
    client_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Default network interface for traffic injection
    default_interface: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    deployments: Mapped[list["RemoteDeployment"]] = relationship(
        "RemoteDeployment",
        back_populates="docker_host",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DockerHost {self.name}>"


# Import here to avoid circular imports
from app.models.remote_deployment import RemoteDeployment  # noqa: E402, F401
