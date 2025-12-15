"""Fingerprint API routes for vendor fingerprint management.

This module provides REST API endpoints for:
- Listing available vendor fingerprints
- Getting fingerprint details by vendor/model
- Suggesting fingerprints for device types
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.services.vendor_fingerprint_data import (
    VENDOR_OUI_PREFIXES,
    get_all_vendor_fingerprints,
    get_fingerprint_by_vendor_model,
    get_fingerprints_by_vendor,
)
from app.scenario_templates.base import (
    FINGERPRINT_MODEL_MAP,
    DEFAULT_ERROR_CONFIGS,
    get_fingerprint_models_for_vendor,
)
from app.protocol_engines.vendor_oui import (
    VENDOR_OUIS,
    DEVICE_TYPE_VENDORS,
    list_vendors,
    list_vendors_for_device_type,
)

router = APIRouter(prefix="/fingerprints", tags=["Fingerprints"])


# ========== Response Models ==========


class VendorSummaryResponse(BaseModel):
    """Summary of a vendor's fingerprints."""

    vendor: str
    display_name: str
    fingerprint_count: int
    models: list[str]
    oui_prefixes: list[str]


class FingerprintSummaryResponse(BaseModel):
    """Summary of a fingerprint."""

    vendor: str
    vendor_family: str
    model: str
    firmware_version: str | None
    protocols: list[str]


class FingerprintDetailResponse(BaseModel):
    """Full fingerprint details."""

    vendor: str
    vendor_family: str
    model: str
    firmware_version: str | None
    oui_prefixes: list[str]
    modbus_identity: dict[str, Any] | None
    ethernet_ip_identity: dict[str, Any] | None
    profinet_identity: dict[str, Any] | None
    tcp_stack: dict[str, Any] | None
    response_timing: dict[str, Any] | None
    error_behavior: dict[str, Any] | None
    protocol_quirks: dict[str, Any] | None
    is_builtin: bool


class FingerprintSuggestionResponse(BaseModel):
    """Suggested fingerprint for a device type."""

    device_type: str
    typical_vendors: list[str]
    suggested_fingerprints: list[FingerprintSummaryResponse]
    default_error_config: dict[str, float] | None


class ErrorConfigResponse(BaseModel):
    """Error configuration for a device type."""

    device_type: str
    exception_rate: float
    timeout_rate: float
    retry_behavior: bool
    max_retries: int


# ========== API Endpoints ==========


@router.get("/vendors", response_model=list[VendorSummaryResponse])
async def list_fingerprint_vendors(
    _current_user: CurrentUser,
) -> list[VendorSummaryResponse]:
    """List all vendors with available fingerprints.

    Returns:
        List of vendors with fingerprint counts
    """
    all_fingerprints = get_all_vendor_fingerprints()

    # Group by vendor
    vendors: dict[str, dict[str, Any]] = {}
    for fp in all_fingerprints:
        vendor = fp.get("vendor", "Unknown").lower()
        if vendor not in vendors:
            vendors[vendor] = {
                "display_name": fp.get("vendor", "Unknown"),
                "models": [],
                "oui_prefixes": fp.get("oui_prefixes", []),
            }
        if fp.get("model"):
            vendors[vendor]["models"].append(fp.get("model"))

    # Add OUI prefixes from vendor_oui module
    for vendor in vendors:
        if vendor in VENDOR_OUIS:
            vendors[vendor]["oui_prefixes"] = list(set(
                vendors[vendor]["oui_prefixes"] + VENDOR_OUIS[vendor]
            ))

    return [
        VendorSummaryResponse(
            vendor=vendor,
            display_name=data["display_name"],
            fingerprint_count=len(data["models"]),
            models=data["models"],
            oui_prefixes=data["oui_prefixes"][:5],  # Limit to 5
        )
        for vendor, data in sorted(vendors.items())
    ]


@router.get("/list", response_model=list[FingerprintSummaryResponse])
async def list_fingerprints(
    _current_user: CurrentUser,
    vendor: str | None = Query(None, description="Filter by vendor"),
) -> list[FingerprintSummaryResponse]:
    """List all available fingerprints.

    Args:
        vendor: Optional filter by vendor name

    Returns:
        List of fingerprint summaries
    """
    if vendor:
        fingerprints = get_fingerprints_by_vendor(vendor)
    else:
        fingerprints = get_all_vendor_fingerprints()

    return [
        FingerprintSummaryResponse(
            vendor=fp.get("vendor", "Unknown"),
            vendor_family=fp.get("vendor_family", ""),
            model=fp.get("model", ""),
            firmware_version=fp.get("firmware_version"),
            protocols=_get_protocols_from_fingerprint(fp),
        )
        for fp in fingerprints
    ]


@router.get("/detail/{vendor}/{model}", response_model=FingerprintDetailResponse)
async def get_fingerprint_detail(
    vendor: str,
    model: str,
    _current_user: CurrentUser,
) -> FingerprintDetailResponse:
    """Get detailed fingerprint information.

    Args:
        vendor: Vendor name
        model: Model identifier

    Returns:
        Full fingerprint details

    Raises:
        HTTPException: If fingerprint not found
    """
    fingerprint = get_fingerprint_by_vendor_model(vendor, model)

    if not fingerprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fingerprint not found for {vendor} / {model}",
        )

    return FingerprintDetailResponse(
        vendor=fingerprint.get("vendor", "Unknown"),
        vendor_family=fingerprint.get("vendor_family", ""),
        model=fingerprint.get("model", ""),
        firmware_version=fingerprint.get("firmware_version"),
        oui_prefixes=fingerprint.get("oui_prefixes", []),
        modbus_identity=fingerprint.get("modbus_identity"),
        ethernet_ip_identity=fingerprint.get("ethernet_ip_identity"),
        profinet_identity=fingerprint.get("profinet_identity"),
        tcp_stack=fingerprint.get("tcp_stack"),
        response_timing=fingerprint.get("response_timing"),
        error_behavior=fingerprint.get("error_behavior"),
        protocol_quirks=fingerprint.get("protocol_quirks"),
        is_builtin=fingerprint.get("is_builtin", False),
    )


@router.get("/suggest/{device_type}", response_model=FingerprintSuggestionResponse)
async def suggest_fingerprint_for_device(
    device_type: str,
    _current_user: CurrentUser,
    vendor: str | None = Query(None, description="Preferred vendor"),
) -> FingerprintSuggestionResponse:
    """Suggest appropriate fingerprints for a device type.

    Args:
        device_type: Device type (plc, hmi, rtu, drive, etc.)
        vendor: Optional preferred vendor

    Returns:
        Suggested fingerprints for the device type
    """
    # Get typical vendors for this device type
    typical_vendors = list_vendors_for_device_type(device_type)

    if not typical_vendors:
        # Fall back to common industrial vendors
        typical_vendors = ["siemens", "rockwell", "schneider", "abb"]

    # If vendor specified, prioritize it
    if vendor and vendor.lower() in typical_vendors:
        typical_vendors = [vendor.lower()] + [v for v in typical_vendors if v != vendor.lower()]

    # Get fingerprints for suggested vendors
    suggested = []
    for v in typical_vendors[:4]:  # Top 4 vendors
        fingerprints = get_fingerprints_by_vendor(v)
        for fp in fingerprints[:2]:  # Top 2 models per vendor
            suggested.append(FingerprintSummaryResponse(
                vendor=fp.get("vendor", "Unknown"),
                vendor_family=fp.get("vendor_family", ""),
                model=fp.get("model", ""),
                firmware_version=fp.get("firmware_version"),
                protocols=_get_protocols_from_fingerprint(fp),
            ))

    # Get default error config
    error_config = DEFAULT_ERROR_CONFIGS.get(device_type)
    default_error = None
    if error_config:
        default_error = {
            "exception_rate": error_config.exception_rate,
            "timeout_rate": error_config.timeout_rate,
        }

    return FingerprintSuggestionResponse(
        device_type=device_type,
        typical_vendors=typical_vendors[:6],
        suggested_fingerprints=suggested,
        default_error_config=default_error,
    )


@router.get("/models/{vendor}", response_model=list[str])
async def get_vendor_models(
    vendor: str,
    _current_user: CurrentUser,
) -> list[str]:
    """Get available fingerprint models for a vendor.

    Args:
        vendor: Vendor name

    Returns:
        List of model identifiers
    """
    # Try from template map first
    models = get_fingerprint_models_for_vendor(vendor)

    if not models:
        # Fall back to fingerprint data
        fingerprints = get_fingerprints_by_vendor(vendor)
        models = [fp.get("model") for fp in fingerprints if fp.get("model")]

    return models


@router.get("/oui/{vendor}", response_model=list[str])
async def get_vendor_oui_prefixes(
    vendor: str,
    _current_user: CurrentUser,
) -> list[str]:
    """Get OUI prefixes for a vendor.

    Args:
        vendor: Vendor name

    Returns:
        List of OUI prefixes (e.g., ["00:0E:8C", "00:1B:1B"])
    """
    vendor_lower = vendor.lower()

    # Check vendor_oui module
    if vendor_lower in VENDOR_OUIS:
        return VENDOR_OUIS[vendor_lower]

    # Check fingerprint data
    if vendor_lower in VENDOR_OUI_PREFIXES:
        return VENDOR_OUI_PREFIXES[vendor_lower]

    # Return empty list if not found
    return []


@router.get("/error-configs", response_model=list[ErrorConfigResponse])
async def get_default_error_configs(
    _current_user: CurrentUser,
) -> list[ErrorConfigResponse]:
    """Get default error configurations for all device types.

    Returns:
        List of error configurations by device type
    """
    return [
        ErrorConfigResponse(
            device_type=device_type,
            exception_rate=config.exception_rate,
            timeout_rate=config.timeout_rate,
            retry_behavior=config.retry_behavior,
            max_retries=config.max_retries,
        )
        for device_type, config in DEFAULT_ERROR_CONFIGS.items()
    ]


@router.get("/error-configs/{device_type}", response_model=ErrorConfigResponse)
async def get_device_error_config(
    device_type: str,
    _current_user: CurrentUser,
) -> ErrorConfigResponse:
    """Get default error configuration for a device type.

    Args:
        device_type: Device type

    Returns:
        Error configuration

    Raises:
        HTTPException: If device type not found
    """
    config = DEFAULT_ERROR_CONFIGS.get(device_type)

    if not config:
        # Return default config
        from app.scenario_templates.base import ErrorConfig
        config = ErrorConfig()

    return ErrorConfigResponse(
        device_type=device_type,
        exception_rate=config.exception_rate,
        timeout_rate=config.timeout_rate,
        retry_behavior=config.retry_behavior,
        max_retries=config.max_retries,
    )


def _get_protocols_from_fingerprint(fp: dict[str, Any]) -> list[str]:
    """Extract supported protocols from fingerprint data.

    Args:
        fp: Fingerprint dictionary

    Returns:
        List of protocol names
    """
    protocols = []

    if fp.get("modbus_identity"):
        protocols.append("modbus_tcp")
    if fp.get("ethernet_ip_identity"):
        protocols.append("ethernet_ip")
    if fp.get("profinet_identity"):
        protocols.append("profinet")

    # Infer from protocol quirks
    quirks = fp.get("protocol_quirks", {})
    if "s7_max_pdu_size" in quirks and "s7" not in protocols:
        protocols.append("s7")
    if "profinet_cycle_time_us" in quirks and "profinet" not in protocols:
        protocols.append("profinet")

    return protocols if protocols else ["modbus_tcp"]  # Default
