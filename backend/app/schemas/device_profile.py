"""Device profile schemas for API validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TimingModel(BaseModel):
    """Timing model for device communication patterns."""

    polling_interval_ms: int = Field(default=1000, ge=10, le=3600000)
    jitter_min_ms: int = Field(default=0, ge=0)
    jitter_max_ms: int = Field(default=100, ge=0)
    jitter_type: str = Field(default="uniform")  # uniform, gaussian, exponential
    burst_enabled: bool = False
    burst_size: int | None = None
    burst_interval_ms: int | None = None


class VendorFingerprint(BaseModel):
    """Vendor fingerprint for realistic device emulation."""

    vendor_family: str
    oui_prefix: str  # MAC OUI, e.g., "00:1C:06"
    oui_variants: list[str] = []
    response_time_min_ms: int = 1
    response_time_max_ms: int = 50
    firmware_patterns: list[str] = []


class DeviceProfileBase(BaseModel):
    """Base schema for device profile."""

    name: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., min_length=1, max_length=50)
    role: str | None = Field(default=None, max_length=255)
    description: str | None = None
    supported_protocols: list[str] | None = Field(default=None)
    timing_model: dict[str, Any] | None = None
    # payload_templates can be either dict (keyed by protocol) or list (array of templates)
    payload_templates: dict[str, Any] | list[dict[str, Any]] | None = Field(default=None)
    behavior_model: dict[str, Any] | None = None
    vendor_fingerprint: dict[str, Any] | None = None
    vertical_hints: list[str] | None = Field(default=None)


class DeviceProfileCreate(DeviceProfileBase):
    """Schema for creating a device profile."""

    pass


class DeviceProfileUpdate(BaseModel):
    """Schema for updating a device profile."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    device_type: str | None = Field(default=None, min_length=1, max_length=50)
    role: str | None = None
    description: str | None = None
    supported_protocols: list[str] | None = None
    timing_model: dict[str, Any] | None = None
    payload_templates: dict[str, Any] | list[dict[str, Any]] | None = None
    behavior_model: dict[str, Any] | None = None
    vendor_fingerprint: dict[str, Any] | None = None
    vertical_hints: list[str] | None = None


class DeviceProfileResponse(DeviceProfileBase):
    """Schema for device profile response."""

    id: UUID
    is_builtin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceProfileListResponse(BaseModel):
    """Schema for listing device profiles."""

    items: list[DeviceProfileResponse]
    total: int
    page: int
    page_size: int
    pages: int
