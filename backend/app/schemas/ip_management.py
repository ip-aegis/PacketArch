"""IP Management schemas for API validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IPRangeAllocationBase(BaseModel):
    """Base schema for IP range allocation."""

    range_index: int = Field(..., ge=1, le=254, description="Index in 10.{n}.0.0/16")
    cidr_range: str = Field(..., description="CIDR notation e.g. 10.1.0.0/16")
    next_host_offset: int = Field(default=10, ge=1, description="Next host offset")


class IPRangeAllocationResponse(IPRangeAllocationBase):
    """Response schema with scenario info."""

    id: UUID
    scenario_id: UUID
    scenario_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class IPRangeListResponse(BaseModel):
    """List of all IP allocations."""

    items: list[IPRangeAllocationResponse]
    total: int
    available_ranges: list[int] = Field(
        description="Which range indices (1-254) are still free"
    )


class NextIPResponse(BaseModel):
    """Response for getting next available IP in a scenario's range."""

    ip_address: str = Field(..., description="Next available IP address")
    subnet_mask: str = Field(default="255.255.255.0", description="Subnet mask")
    gateway: str = Field(..., description="Gateway address for this subnet")
    cidr: str = Field(..., description="Scenario's CIDR range")


class ScenarioIPInfoResponse(BaseModel):
    """IP range info for a specific scenario."""

    scenario_id: UUID
    scenario_name: str
    cidr_range: str
    range_index: int
    devices_with_ips: int = Field(description="Count of devices that have IPs assigned")
    next_available_ip: str = Field(description="Next IP that will be assigned")
    gateway: str = Field(description="Default gateway for the range")
