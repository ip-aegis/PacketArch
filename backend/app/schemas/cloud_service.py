# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Pydantic schemas for cloud service endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.cloud_service import CloudServiceProvider


class CloudServiceEndpointBase(BaseModel):
    """Base schema for cloud service endpoints."""

    name: str = Field(..., min_length=1, max_length=100)
    provider: CloudServiceProvider
    ip_addresses: list[str] = Field(..., min_length=1)
    primary_ip: str = Field(..., pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    port: int = Field(default=443, ge=1, le=65535)
    hostname: str | None = Field(default=None, max_length=255)
    tls_enabled: bool = True
    heartbeat_interval_ms: int = Field(default=30000, ge=1000, le=3600000)
    region: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)


class CloudServiceEndpointCreate(CloudServiceEndpointBase):
    """Schema for creating a cloud service endpoint."""

    pass


class CloudServiceEndpointUpdate(BaseModel):
    """Schema for updating a cloud service endpoint."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    provider: CloudServiceProvider | None = None
    ip_addresses: list[str] | None = None
    primary_ip: str | None = Field(default=None, pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    port: int | None = Field(default=None, ge=1, le=65535)
    hostname: str | None = Field(default=None, max_length=255)
    tls_enabled: bool | None = None
    heartbeat_interval_ms: int | None = Field(default=None, ge=1000, le=3600000)
    region: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class CloudServiceEndpointResponse(CloudServiceEndpointBase):
    """Schema for cloud service endpoint response."""

    id: UUID
    is_builtin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CloudServiceEndpointListResponse(BaseModel):
    """Schema for listing cloud service endpoints."""

    items: list[CloudServiceEndpointResponse]
    total: int


class CloudServiceLinkBase(BaseModel):
    """Base schema for cloud service links in scenario definitions.

    Cloud service links connect devices to cloud service endpoints
    for heartbeat traffic generation.
    """

    device_id: str
    cloud_service_id: UUID
    heartbeat_interval_ms: int = Field(default=30000, ge=1000, le=3600000)
    enabled: bool = True


class CloudServiceLinkCreate(CloudServiceLinkBase):
    """Schema for creating a cloud service link."""

    pass


class CloudServiceLinkResponse(CloudServiceLinkBase):
    """Schema for cloud service link response with resolved service info."""

    id: str
    cloud_service: CloudServiceEndpointResponse | None = None
