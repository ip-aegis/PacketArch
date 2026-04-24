# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cyber Vision schemas for API validation."""

from pydantic import BaseModel, Field


class CVDeviceResponse(BaseModel):
    """Schema for a device discovered by Cyber Vision."""

    id: str
    name: str
    ip: str | None = None
    mac: str | None = None
    vendor: str | None = None
    model: str | None = None
    firmware: str | None = None
    category: str | None = None
    risk_score: int | None = None
    first_seen: str | None = None
    last_seen: str | None = None
    group_name: str | None = None


class CVDeviceListResponse(BaseModel):
    """Schema for listing CV devices."""

    items: list[CVDeviceResponse]
    total: int


class CVVulnerabilityResponse(BaseModel):
    """Schema for a vulnerability from Cyber Vision."""

    id: str
    cve_id: str
    title: str
    severity: str
    cvss_score: float | None = None
    affected_device_count: int = 0
    description: str | None = None


class CVVulnerabilityListResponse(BaseModel):
    """Schema for listing CV vulnerabilities."""

    items: list[CVVulnerabilityResponse]
    total: int


class CVConnectionStatusResponse(BaseModel):
    """Schema for CV connection status."""

    connected: bool
    message: str
    version: str | None = None
    center_name: str | None = None


class CVTestConnectionRequest(BaseModel):
    """Schema for testing CV connection with provided credentials."""

    url: str = Field(..., description="Cyber Vision URL")
    api_token: str = Field(..., description="API token")
    verify_ssl: bool = Field(default=False, description="Verify SSL certificates")


class CVTestConnectionResponse(BaseModel):
    """Schema for CV connection test result."""

    success: bool
    message: str
    version: str | None = None


class MatchedDevice(BaseModel):
    """Schema for a matched device in comparison results."""

    scenario_device: dict
    cv_device: CVDeviceResponse
    confidence: float = Field(..., ge=0, le=1, description="Match confidence (0-1)")
    match_type: str = Field(..., description="How the match was made (ip, mac, vendor_model)")


class ComparisonInsight(BaseModel):
    """A single actionable insight from comparison analysis."""

    category: str = Field(..., description="Insight category: match_quality, protocol_visibility, enrichment_suggestion")
    severity: str = Field(..., description="info, warning, or suggestion")
    message: str
    affected_devices: list[str] = Field(default_factory=list, description="Names of affected devices")


class CVComparisonResult(BaseModel):
    """Schema for scenario vs CV device comparison results."""

    scenario_id: str
    scenario_name: str
    scenario_device_count: int
    cv_device_count: int
    matched_devices: list[MatchedDevice]
    scenario_only: list[dict] = Field(default_factory=list, description="Devices only in scenario")
    cv_only: list[CVDeviceResponse] = Field(default_factory=list, description="Devices only in CV")
    match_rate: float = Field(..., ge=0, le=1, description="Percentage of scenario devices matched")
    insights: list[ComparisonInsight] = Field(default_factory=list, description="Actionable comparison insights")


class CVSettingsUpdate(BaseModel):
    """Schema for updating CV settings."""

    cyber_vision_url: str | None = Field(default=None, description="Cyber Vision URL")
    cyber_vision_api_token: str | None = Field(default=None, description="API token")
    cyber_vision_verify_ssl: bool | None = Field(default=None, description="Verify SSL")


class CVSettingsResponse(BaseModel):
    """Schema for CV settings response (token masked)."""

    cyber_vision_url: str
    cyber_vision_api_token_set: bool = Field(description="Whether token is configured")
    cyber_vision_verify_ssl: bool


class CVPresetResponse(BaseModel):
    """Schema for a CV preset."""

    id: str
    label: str


class CVPresetListResponse(BaseModel):
    """Schema for listing CV presets."""

    items: list[CVPresetResponse]


# ==================== Enrichment Schemas ====================


class CVDevicePropertyMapping(BaseModel):
    """Mapping of a CV device to properties to enrich."""

    cv_device_id: str = Field(..., description="Cyber Vision device ID")
    cv_device_mac: str | None = Field(default=None, description="MAC address for ID resolution fallback")
    cv_device_ip: str | None = Field(default=None, description="IP address for ID resolution fallback")
    device_label: str | None = Field(default=None, description="Optional: Set device name/label in CV")
    properties: dict[str, str] = Field(
        ...,
        description="Properties to add (label -> value). Labels max 60 chars, values max 180 chars."
    )


class CVEnrichmentRequest(BaseModel):
    """Request to enrich CV devices with PacketArch data."""

    device_mappings: list[CVDevicePropertyMapping] = Field(
        ..., description="List of device-to-properties mappings"
    )
    skip_existing: bool = Field(
        default=True,
        description="Skip properties that already exist on the device"
    )


class CVEnrichmentDeviceResult(BaseModel):
    """Result of enrichment for a single device."""

    cv_device_id: str
    status: str = Field(..., description="'success' or 'failed'")
    properties_added: list[str] = Field(
        default_factory=list,
        description="Labels of properties successfully added"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class CVEnrichmentResult(BaseModel):
    """Result of enrichment operation."""

    success_count: int = Field(..., description="Number of devices successfully enriched")
    failed_count: int = Field(..., description="Number of devices that failed")
    total_properties_added: int = Field(..., description="Total properties added across all devices")
    results: list[CVEnrichmentDeviceResult] = Field(
        ..., description="Per-device results"
    )


# ==================== Duplicate MAC Analysis Schemas ====================


class DuplicateMacDeviceInfo(BaseModel):
    """Device info within a duplicate MAC group."""

    id: str
    name: str
    ip: str | None = None
    mac: str | None = None
    vendor: str | None = None
    model: str | None = None
    firmware: str | None = None
    category: str | None = None
    risk_score: int | None = None
    first_seen: str | None = None
    last_seen: str | None = None
    group_name: str | None = None


class NoMacDeviceInfo(BaseModel):
    """Minimal info for a device that has no MAC address."""

    id: str
    name: str
    ip: str | None = None
    vendor: str | None = None
    category: str | None = None
    group_name: str | None = None


class DuplicateMacGroup(BaseModel):
    """A group of devices sharing the same MAC address."""

    mac: str = Field(..., description="Normalized MAC address (xx:xx:xx:xx:xx:xx)")
    oui_vendor: str | None = Field(None, description="Vendor name from OUI lookup")
    severity: str = Field(..., description="critical, high, medium, or low")
    reason: str = Field(..., description="Human-readable explanation of the severity classification")
    device_count: int = Field(..., description="Number of devices sharing this MAC")
    devices: list[DuplicateMacDeviceInfo] = Field(..., description="Devices in this group")


class DuplicateMacSeverityCounts(BaseModel):
    """Count of duplicate groups by severity level."""

    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class DuplicateMacAnalysisResponse(BaseModel):
    """Complete duplicate MAC analysis result."""

    total_devices_analyzed: int = Field(..., description="Total devices fetched from CV")
    devices_with_mac: int = Field(..., description="Devices that have a MAC address")
    devices_without_mac: int = Field(..., description="Devices missing MAC address")
    unique_macs: int = Field(..., description="Count of unique MAC addresses")
    duplicate_groups_count: int = Field(..., description="Number of MAC addresses shared by 2+ devices")
    severity_counts: DuplicateMacSeverityCounts
    duplicate_groups: list[DuplicateMacGroup] = Field(
        ..., description="Duplicate groups sorted by severity (critical first)"
    )
    no_mac_devices: list[NoMacDeviceInfo] = Field(
        default_factory=list, description="Devices without any MAC address"
    )
