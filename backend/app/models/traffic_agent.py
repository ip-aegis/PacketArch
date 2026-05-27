# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Traffic agent model for remote WebSocket-based traffic generation."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrafficAgent(Base):
    """Traffic agent configuration for WebSocket-based remote deployment.

    Agents connect to the server via WebSocket and receive commands to
    start/stop traffic generation. This replaces the Docker API approach
    with a simpler "phone home" model.
    """

    __tablename__ = "traffic_agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # SHA-256 hash of the authentication token
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    # Default network interface for traffic injection
    default_interface: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    # CML deployment linkage (set when this agent was auto-deployed into a
    # Cisco Modeling Labs lab; null for manually-installed agents)
    cml_lab_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    cml_node_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    cml_node_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    # Agent status: online, offline
    status: Mapped[str] = mapped_column(
        String(20),
        default="offline",
        nullable=False,
    )
    # Agent version (reported by agent on connect)
    version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    # Hostname (reported by agent on connect)
    hostname: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    # Platform (Linux, Windows, etc.)
    platform: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # First time the agent connected (never null after first connection)
    first_connected_at: Mapped[datetime | None] = mapped_column(
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
    deployments: Mapped[list["AgentDeployment"]] = relationship(
        "AgentDeployment",
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TrafficAgent {self.name} ({self.status})>"


class AgentDeployment(Base):
    """Tracks scenario deployments to traffic agents."""

    __tablename__ = "agent_deployments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traffic_agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Deployment state: starting, running, stopping, stopped, error
    state: Mapped[str] = mapped_column(
        String(20),
        default="starting",
        nullable=False,
    )
    # Network interface used for this deployment
    interface: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    # Number of packets sent
    packets_sent: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    # Error message if state is 'error'
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    agent: Mapped["TrafficAgent"] = relationship(
        "TrafficAgent",
        back_populates="deployments",
    )

    def __repr__(self) -> str:
        return f"<AgentDeployment {self.scenario_id} on {self.agent_id} ({self.state})>"
