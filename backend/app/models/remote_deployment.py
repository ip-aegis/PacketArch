"""Remote deployment model for tracking traffic generator deployments."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeploymentStatus(str, Enum):
    """Deployment status enumeration."""

    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class RunMode(str, Enum):
    """Run mode for traffic generation."""

    TIMED = "timed"  # Run for specified duration then stop
    PERPETUAL = "perpetual"  # Run until manually stopped


class RemoteDeployment(Base):
    """Remote deployment tracking for traffic generator containers."""

    __tablename__ = "remote_deployments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id"),
        nullable=False,
        index=True,
    )
    docker_host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("docker_hosts.id"),
        nullable=False,
        index=True,
    )
    # Docker container ID once created
    container_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    container_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    # Network interface used for packet injection
    network_interface: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DeploymentStatus.PENDING.value,
        index=True,
    )
    # Run mode: timed (stops after duration) or perpetual (runs until stopped)
    run_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RunMode.TIMED.value,
    )
    # Duration for traffic generation in milliseconds (optional for perpetual mode)
    duration_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=60000,
    )
    # Statistics
    packets_injected: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    docker_host: Mapped["DockerHost"] = relationship(
        "DockerHost",
        back_populates="deployments",
    )
    scenario: Mapped["Scenario"] = relationship(
        "Scenario",
    )

    def __repr__(self) -> str:
        return f"<RemoteDeployment {self.id} status={self.status}>"


# Import here to avoid circular imports
from app.models.docker_host import DockerHost  # noqa: E402, F401
from app.models.scenario import Scenario  # noqa: E402, F401
