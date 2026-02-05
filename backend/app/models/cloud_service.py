"""Cloud service endpoint model for external cloud connectivity."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class CloudServiceProvider(str, Enum):
    """Supported cloud service providers."""

    TALK2M = "talk2m"
    TEAMVIEWER = "teamviewer"
    AZURE_IOT = "azure_iot"
    AWS_IOT = "aws_iot"
    CUSTOM = "custom"


class CloudServiceEndpoint(Base):
    """Cloud service endpoint for remote access and monitoring.

    Represents external cloud services that OT devices connect to,
    such as EWON Talk2M or TeamViewer relay servers.

    Cloud service links (stored in scenario definitions) reference
    these endpoints by ID to configure cloud heartbeat traffic.
    """

    __tablename__ = "cloud_service_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    provider = Column(
        SQLEnum(CloudServiceProvider, name="cloud_service_provider"),
        nullable=False,
    )
    ip_addresses = Column(ARRAY(String(45)), nullable=False)  # Multiple IPs for load balancing
    primary_ip = Column(String(45), nullable=False)  # Main IP for traffic generation
    port = Column(Integer, default=443)
    hostname = Column(String(255), nullable=True)  # For TLS SNI
    tls_enabled = Column(Boolean, default=True)
    heartbeat_interval_ms = Column(Integer, default=30000)  # Default 30 seconds
    region = Column(String(50), nullable=True)  # Geographic region (us-west, eu, etc.)
    description = Column(Text, nullable=True)
    is_builtin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<CloudServiceEndpoint(name={self.name}, provider={self.provider}, primary_ip={self.primary_ip})>"
