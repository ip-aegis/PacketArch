# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Fingerprint API routes for vendor fingerprint management.

This module provides REST API endpoints for:
- Listing available vendor fingerprints
- Getting fingerprint details by vendor/model
- Suggesting fingerprints for device types
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.exceptions import NotFoundError

from app.api.deps import CurrentUser, DBSession
from app.models.device_template import DeviceTemplate as DeviceTemplateModel, TemplateSource
from app.protocol_engines.vendor_oui import VENDOR_OUI_PREFIXES
from app.services.fingerprint_cache import get_fingerprint_cache
from app.scenario_templates.base import (
    DEFAULT_ERROR_CONFIGS,
    get_fingerprint_models_for_vendor,
)
from app.protocol_engines.vendor_oui import (
    VENDOR_OUIS,
    DEVICE_TYPE_VENDORS,
    list_vendors_for_device_type,
)
from app.services.device_templates import (
    get_all_templates,
    get_template_by_id,
    get_templates_by_vendor,
    get_templates_by_device_type,
    get_templates_with_cves,
    get_template_count,
    get_total_firmware_variants,
    get_total_cves,
    generate_device_instance,
    DeviceTemplate,
    FirmwareVariant,
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
    s7_identity: dict[str, Any] | None
    snmp_identity: dict[str, Any] | None
    bacnet_identity: dict[str, Any] | None
    opc_ua_identity: dict[str, Any] | None
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


# ========== Palette Response Models ==========


class PaletteDeviceResponse(BaseModel):
    """Device template formatted for the Scenario Studio palette."""

    id: str
    name: str
    device_type: str
    role: str | None = None
    description: str | None = None
    supported_protocols: list[str] | None = None
    timing_model: dict[str, Any] | None = None
    vendor_fingerprint: dict[str, Any] | None = None
    vertical_hints: list[str] | None = None
    is_builtin: bool = True
    template_id: str | None = None
    created_at: str | None = None


class PaletteDeviceListResponse(BaseModel):
    """Paginated palette device list."""

    items: list[PaletteDeviceResponse]
    total: int


class DeviceTemplateCreateRequest(BaseModel):
    """Request to create a user-defined device template."""

    name: str
    device_type: str
    role: str | None = None
    description: str | None = None
    vendor: str | None = None
    model: str | None = None
    supported_protocols: list[str] | None = None
    vertical_hints: list[str] | None = None
    timing_model: dict[str, Any] | None = None
    payload_templates: list[dict[str, Any]] | None = None
    behavior_model: dict[str, Any] | None = None


class DeviceTemplateUpdateRequest(BaseModel):
    """Request to update a user-defined device template."""

    name: str | None = None
    device_type: str | None = None
    role: str | None = None
    description: str | None = None
    vendor: str | None = None
    model: str | None = None
    supported_protocols: list[str] | None = None
    vertical_hints: list[str] | None = None
    timing_model: dict[str, Any] | None = None
    payload_templates: list[dict[str, Any]] | None = None
    behavior_model: dict[str, Any] | None = None


# ========== API Endpoints ==========


@router.get("/vendors", response_model=list[VendorSummaryResponse])
async def list_fingerprint_vendors(
    _current_user: CurrentUser,
) -> list[VendorSummaryResponse]:
    """List all vendors with available fingerprints.

    Returns:
        List of vendors with fingerprint counts
    """
    cache = get_fingerprint_cache()
    vendors: dict[str, dict[str, Any]] = {}

    for vendor_key in cache.get_vendors():
        fps = cache.get_by_vendor(vendor_key)
        if not fps:
            continue
        display_name = fps[0].get("vendor", vendor_key)
        models = [fp.get("model") for fp in fps if fp.get("model")]
        oui_prefixes = VENDOR_OUI_PREFIXES.get(vendor_key, [])
        vendors[vendor_key] = {
            "display_name": display_name,
            "models": models,
            "oui_prefixes": oui_prefixes,
        }

    return [
        VendorSummaryResponse(
            vendor=vendor,
            display_name=data["display_name"],
            fingerprint_count=len(data["models"]),
            models=data["models"],
            oui_prefixes=data["oui_prefixes"][:5],
        )
        for vendor, data in sorted(vendors.items())
    ]


class PortableRegistryEntry(BaseModel):
    """One entry in the portable scenario fingerprint registry.

    These are the valid `(vendor, model, type, protocols)` tuples that
    portable scenario authors can use as `fingerprint_model` values.
    """

    vendor: str
    model: str
    device_type: str
    protocols: list[str]
    description: str | None = None


class PortableRegistryResponse(BaseModel):
    """Response for GET /api/v1/fingerprints/registry."""

    format_version: str
    entries: list[PortableRegistryEntry]
    vendors: list[str]
    device_types: list[str]


@router.get(
    "/registry",
    response_model=PortableRegistryResponse,
    summary="Discovery endpoint for portable-scenario authors",
)
async def get_portable_fingerprint_registry(
    _current_user: CurrentUser,
    vendor: str | None = Query(None, description="Filter to one vendor"),
    device_type: str | None = Query(
        None, description="Filter to one device type (plc, hmi, drive, ...)",
    ),
) -> PortableRegistryResponse:
    """Return the valid `fingerprint_model` registry for portable scenarios.

    External authoring tools (AI generators, custom scripts) should fetch
    this before producing a `.pascenario.json` so they only emit
    `fingerprint_model` values the importer can resolve.

    Pair with GET /scenarios/schema/portable.json (the JSON Schema).
    """
    from app.services.device_templates import get_all_templates

    templates = get_all_templates()

    if vendor:
        templates = [t for t in templates if t.vendor.lower() == vendor.lower()]
    if device_type:
        templates = [t for t in templates if t.device_type == device_type]

    entries = [
        PortableRegistryEntry(
            vendor=t.vendor.lower(),
            model=t.model,
            device_type=t.device_type,
            protocols=list(t.supported_protocols),
            description=t.description or None,
        )
        for t in templates
    ]
    entries.sort(key=lambda e: (e.vendor, e.device_type, e.model))

    vendors = sorted({e.vendor for e in entries})
    device_types = sorted({e.device_type for e in entries})

    return PortableRegistryResponse(
        format_version="1.0",
        entries=entries,
        vendors=vendors,
        device_types=device_types,
    )


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
    cache = get_fingerprint_cache()
    if vendor:
        fingerprints = cache.get_by_vendor(vendor)
    else:
        fingerprints = cache.get_all()

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
    fingerprint = get_fingerprint_cache().get_by_vendor_model(vendor, model)

    if not fingerprint:
        raise NotFoundError("Fingerprint", f"{vendor}/{model}")

    return FingerprintDetailResponse(
        vendor=fingerprint.get("vendor", "Unknown"),
        vendor_family=fingerprint.get("vendor_family", ""),
        model=fingerprint.get("model", ""),
        firmware_version=fingerprint.get("firmware_version"),
        oui_prefixes=fingerprint.get("oui_prefixes", []),
        modbus_identity=fingerprint.get("modbus_identity"),
        ethernet_ip_identity=fingerprint.get("ethernet_ip_identity"),
        profinet_identity=fingerprint.get("profinet_identity"),
        s7_identity=fingerprint.get("s7_identity"),
        snmp_identity=fingerprint.get("snmp_identity"),
        bacnet_identity=fingerprint.get("bacnet_identity"),
        opc_ua_identity=fingerprint.get("opc_ua_identity"),
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
    cache = get_fingerprint_cache()
    suggested = []
    for v in typical_vendors[:4]:  # Top 4 vendors
        fingerprints = cache.get_by_vendor(v)
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
        # Fall back to cache
        fingerprints = get_fingerprint_cache().get_by_vendor(vendor)
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

    # VENDOR_OUI_PREFIXES includes all entries from VENDOR_OUIS (canonical)
    # plus vendor division aliases from fingerprint sub-modules
    if vendor_lower in VENDOR_OUI_PREFIXES:
        return VENDOR_OUI_PREFIXES[vendor_lower]

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


# ========== Protocol Library Models ==========


class ProtocolInfoResponse(BaseModel):
    """Information about a supported protocol."""

    id: str
    name: str
    category: str
    port: int | None
    layer: str
    has_identity_builder: bool
    description: str


class ProtocolDetailResponse(ProtocolInfoResponse):
    """Detailed protocol information."""

    identity_fields: list[str] | None
    typical_devices: list[str]
    typical_vendors: list[str]


class VendorCompleteResponse(BaseModel):
    """Complete vendor information with OUI data."""

    id: str
    display_name: str
    oui_prefixes: list[str]
    device_types: list[str]
    protocols: list[str]
    fingerprint_count: int


class FingerprintStatsResponse(BaseModel):
    """Fingerprinting library statistics."""

    total_protocols: int
    total_vendors: int
    total_oui_prefixes: int
    total_fingerprints: int
    total_device_types: int
    identity_builders: int
    protocols_by_category: dict[str, int]
    # New template-based stats
    total_device_templates: int
    total_firmware_variants: int
    total_cves: int


# ========== Device Template Models ==========


class FirmwareVariantResponse(BaseModel):
    """Firmware variant information."""

    version: str
    release_date: str
    is_latest: bool
    is_default: bool
    cves: list[str]
    notes: str | None


class DeviceTemplateSummaryResponse(BaseModel):
    """Summary of a device template."""

    id: str
    vendor: str
    vendor_family: str
    model: str
    model_name: str
    device_type: str
    description: str
    supported_protocols: list[str]
    firmware_count: int
    vulnerable_firmware_count: int
    has_cves: bool


class DeviceTemplateDetailResponse(BaseModel):
    """Full device template details."""

    id: str
    vendor: str
    vendor_family: str
    model: str
    model_name: str
    device_type: str
    description: str
    oui_prefixes: list[str]
    tcp_stack: dict[str, Any]
    response_timing: dict[str, Any]
    error_behavior: dict[str, Any]
    supported_protocols: list[str]
    firmware_variants: list[FirmwareVariantResponse]
    instance_rules: dict[str, str] | None
    modbus_identity: dict[str, Any] | None
    ethernet_ip_identity: dict[str, Any] | None
    profinet_identity: dict[str, Any] | None
    s7_identity: dict[str, Any] | None
    bacnet_identity: dict[str, Any] | None
    snmp_identity: dict[str, Any] | None
    protocol_quirks: dict[str, Any]
    is_builtin: bool


class GenerateInstanceRequest(BaseModel):
    """Request to generate a device instance."""

    template_id: str
    firmware_version: str | None = None
    station_name: str | None = None
    serial_number: str | None = None
    mac_address: str | None = None
    ip_address: str | None = None
    location: str | None = None
    sequence: int = 1


class DeviceInstanceResponse(BaseModel):
    """Generated device instance."""

    template_id: str
    firmware_version: str
    serial_number: str
    station_name: str
    mac_address: str
    ip_address: str
    cves: list[str]
    merged_identities: dict[str, dict[str, Any]]


# Protocol metadata - comprehensive list of all 21 supported protocols
PROTOCOL_DATA: dict[str, dict[str, Any]] = {
    "modbus_tcp": {
        "name": "Modbus TCP",
        "category": "Core Industrial",
        "port": 502,
        "layer": "TCP",
        "has_identity_builder": True,
        "description": "Industrial protocol for PLCs, RTUs, and SCADA systems. Widely used in manufacturing and process industries.",
        "identity_fields": ["vendor_name", "product_code", "revision", "vendor_url", "product_name", "model_name", "user_application_name"],
        "typical_devices": ["plc", "rtu", "hmi", "scada_server", "gateway"],
        "typical_vendors": ["siemens", "schneider", "rockwell", "abb", "emerson"],
    },
    "ethernet_ip": {
        "name": "EtherNet/IP",
        "category": "Core Industrial",
        "port": 44818,
        "layer": "TCP/UDP",
        "has_identity_builder": True,
        "description": "ODVA standard protocol for Rockwell/Allen-Bradley PLCs and CIP-based devices.",
        "identity_fields": ["vendor_id", "device_type", "product_code", "revision", "serial_number", "product_name"],
        "typical_devices": ["plc", "hmi", "drive", "io_module"],
        "typical_vendors": ["rockwell", "omron", "schneider", "abb"],
    },
    "profinet": {
        "name": "PROFINET",
        "category": "Core Industrial",
        "port": None,
        "layer": "Layer2",
        "has_identity_builder": True,
        "description": "Siemens-originated real-time Ethernet protocol for factory automation.",
        "identity_fields": ["device_vendor", "device_name", "device_id", "station_name", "ip_address"],
        "typical_devices": ["plc", "io_module", "drive", "hmi"],
        "typical_vendors": ["siemens", "phoenix_contact", "wago", "beckhoff"],
    },
    "s7comm": {
        "name": "S7comm",
        "category": "Core Industrial",
        "port": 102,
        "layer": "TCP",
        "has_identity_builder": True,
        "description": "Siemens proprietary protocol for S7 PLC communication.",
        "identity_fields": ["module_type", "serial_number", "plant_id", "copyright", "module_name"],
        "typical_devices": ["plc", "hmi", "engineering_station"],
        "typical_vendors": ["siemens"],
    },
    "bacnet": {
        "name": "BACnet/IP",
        "category": "Building Automation",
        "port": 47808,
        "layer": "UDP",
        "has_identity_builder": True,
        "description": "Building automation and control protocol for HVAC, lighting, and access control.",
        "identity_fields": ["device_instance", "vendor_id", "model_name", "firmware_revision", "application_software_version"],
        "typical_devices": ["bac", "ahu_controller", "vav_controller", "chiller_controller", "thermostat"],
        "typical_vendors": ["johnson_controls", "honeywell", "siemens", "trane", "carrier"],
    },
    "snmp": {
        "name": "SNMP/NTCIP",
        "category": "Network Management",
        "port": 161,
        "layer": "UDP",
        "has_identity_builder": True,
        "description": "Network management protocol used in ITS/transportation and network devices.",
        "identity_fields": ["sys_descr", "sys_object_id", "sys_name", "sys_location", "sys_contact"],
        "typical_devices": ["traffic_controller", "dms", "switch", "gateway", "router"],
        "typical_vendors": ["cisco", "econolite", "mccain", "siemens_its", "daktronics"],
    },
    "opc_ua": {
        "name": "OPC UA",
        "category": "SCADA/Utility",
        "port": 4840,
        "layer": "TCP",
        "has_identity_builder": True,
        "description": "Platform-independent industrial communication standard for secure data exchange.",
        "identity_fields": ["application_uri", "product_uri", "application_name", "application_type"],
        "typical_devices": ["plc", "scada_server", "historian", "gateway"],
        "typical_vendors": ["siemens", "rockwell", "schneider", "honeywell", "ge"],
    },
    "dnp3": {
        "name": "DNP3",
        "category": "SCADA/Utility",
        "port": 20000,
        "layer": "TCP",
        "has_identity_builder": False,
        "description": "Distributed Network Protocol for SCADA communications in utilities and water.",
        "identity_fields": None,
        "typical_devices": ["rtu", "ied", "scada_server"],
        "typical_vendors": ["schneider", "ge", "abb", "sel"],
    },
    "iec104": {
        "name": "IEC 104",
        "category": "SCADA/Utility",
        "port": 2404,
        "layer": "TCP",
        "has_identity_builder": False,
        "description": "Telecontrol protocol for power system SCADA (IEC 60870-5-104).",
        "identity_fields": None,
        "typical_devices": ["rtu", "ied", "scada_server"],
        "typical_vendors": ["abb", "siemens", "ge", "schneider"],
    },
    "iec61850": {
        "name": "IEC 61850",
        "category": "Power/Energy",
        "port": None,
        "layer": "TCP/Layer2",
        "has_identity_builder": False,
        "description": "Substation automation standard with MMS, GOOSE, and Sampled Values.",
        "identity_fields": None,
        "typical_devices": ["protection_relay", "ied", "merging_unit"],
        "typical_vendors": ["sel", "ge", "abb", "siemens", "schneider"],
    },
    "pccc": {
        "name": "PCCC",
        "category": "Vendor-Specific",
        "port": 44818,
        "layer": "TCP",
        "has_identity_builder": False,
        "description": "Allen-Bradley legacy protocol for PLC-5, SLC-500, and MicroLogix.",
        "identity_fields": None,
        "typical_devices": ["plc", "hmi"],
        "typical_vendors": ["rockwell"],
    },
    "codesys": {
        "name": "Codesys",
        "category": "Vendor-Specific",
        "port": 11740,
        "layer": "TCP",
        "has_identity_builder": False,
        "description": "IEC 61131-3 runtime protocol used by 500+ PLC vendors.",
        "identity_fields": None,
        "typical_devices": ["plc", "hmi", "motion_controller"],
        "typical_vendors": ["wago", "beckhoff", "schneider", "b_and_r"],
    },
    "fins": {
        "name": "FINS",
        "category": "Vendor-Specific",
        "port": 9600,
        "layer": "TCP/UDP",
        "has_identity_builder": False,
        "description": "Omron Factory Interface Network Service for CJ/NJ series PLCs.",
        "identity_fields": None,
        "typical_devices": ["plc", "hmi"],
        "typical_vendors": ["omron"],
    },
    "slmp": {
        "name": "SLMP",
        "category": "Vendor-Specific",
        "port": 5007,
        "layer": "TCP",
        "has_identity_builder": False,
        "description": "Seamless Message Protocol for Mitsubishi MELSEC PLCs.",
        "identity_fields": None,
        "typical_devices": ["plc", "hmi"],
        "typical_vendors": ["mitsubishi"],
    },
    "ethercat": {
        "name": "EtherCAT",
        "category": "Vendor-Specific",
        "port": None,
        "layer": "Layer2",
        "has_identity_builder": False,
        "description": "High-speed real-time Ethernet for motion control and servo drives.",
        "identity_fields": None,
        "typical_devices": ["plc", "drive", "servo", "io_module"],
        "typical_vendors": ["beckhoff", "omron", "b_and_r"],
    },
    "lldp": {
        "name": "LLDP",
        "category": "Network Management",
        "port": None,
        "layer": "Layer2",
        "has_identity_builder": False,
        "description": "Link Layer Discovery Protocol for network topology discovery.",
        "identity_fields": None,
        "typical_devices": ["switch", "gateway", "plc"],
        "typical_vendors": ["cisco"],
    },
    "cdp": {
        "name": "CDP",
        "category": "Network Management",
        "port": None,
        "layer": "Layer2",
        "has_identity_builder": False,
        "description": "Cisco Discovery Protocol for network device discovery.",
        "identity_fields": None,
        "typical_devices": ["switch", "router", "gateway"],
        "typical_vendors": ["cisco"],
    },
    "dcs": {
        "name": "DCS",
        "category": "DCS Systems",
        "port": None,
        "layer": "TCP",
        "has_identity_builder": False,
        "description": "Distributed Control System protocols (DeltaV, Experion, Vnet/IP, Triconex).",
        "identity_fields": None,
        "typical_devices": ["dcs_controller", "io_module", "engineering_station"],
        "typical_vendors": ["emerson", "honeywell", "yokogawa", "schneider"],
    },
    "wmi": {
        "name": "WMI",
        "category": "Specialized",
        "port": 135,
        "layer": "TCP",
        "has_identity_builder": False,
        "description": "Windows Management Instrumentation for Windows-based HMI/SCADA servers.",
        "identity_fields": None,
        "typical_devices": ["hmi", "scada_server", "engineering_station"],
        "typical_vendors": ["wonderware", "ge", "honeywell"],
    },
    "fanuc": {
        "name": "FANUC FOCAS",
        "category": "Specialized",
        "port": 8193,
        "layer": "TCP",
        "has_identity_builder": False,
        "description": "FANUC CNC machine protocol for machining centers and robots.",
        "identity_fields": None,
        "typical_devices": ["cnc_machine", "robot_controller"],
        "typical_vendors": ["ge"],  # GE Fanuc
    },
    "external": {
        "name": "External/Docker",
        "category": "Specialized",
        "port": None,
        "layer": "Variable",
        "has_identity_builder": False,
        "description": "External protocol simulation via Docker containers.",
        "identity_fields": None,
        "typical_devices": [],
        "typical_vendors": [],
    },
}


@router.get("/protocols", response_model=list[ProtocolInfoResponse])
async def list_protocols(
    _current_user: CurrentUser,
    category: str | None = Query(None, description="Filter by category"),
) -> list[ProtocolInfoResponse]:
    """List all supported protocols.

    Args:
        category: Optional filter by protocol category

    Returns:
        List of protocol information
    """
    from app.protocol_engines.identity import has_builder

    protocols = []
    for protocol_id, data in PROTOCOL_DATA.items():
        if category and data["category"] != category:
            continue

        protocols.append(
            ProtocolInfoResponse(
                id=protocol_id,
                name=data["name"],
                category=data["category"],
                port=data["port"],
                layer=data["layer"],
                has_identity_builder=has_builder(protocol_id.replace("_tcp", "").replace("comm", "")),
                description=data["description"],
            )
        )

    return sorted(protocols, key=lambda p: (p.category, p.name))


@router.get("/protocols/{protocol_id}", response_model=ProtocolDetailResponse)
async def get_protocol_detail(
    protocol_id: str,
    _current_user: CurrentUser,
) -> ProtocolDetailResponse:
    """Get detailed protocol information.

    Args:
        protocol_id: Protocol identifier (e.g., modbus_tcp, ethernet_ip)

    Returns:
        Detailed protocol information

    Raises:
        HTTPException: If protocol not found
    """
    from app.protocol_engines.identity import has_builder

    if protocol_id not in PROTOCOL_DATA:
        raise NotFoundError("Protocol", protocol_id)

    data = PROTOCOL_DATA[protocol_id]

    return ProtocolDetailResponse(
        id=protocol_id,
        name=data["name"],
        category=data["category"],
        port=data["port"],
        layer=data["layer"],
        has_identity_builder=has_builder(protocol_id.replace("_tcp", "").replace("comm", "")),
        description=data["description"],
        identity_fields=data.get("identity_fields"),
        typical_devices=data.get("typical_devices", []),
        typical_vendors=data.get("typical_vendors", []),
    )


@router.get("/vendors/complete", response_model=list[VendorCompleteResponse])
async def list_vendors_complete(
    _current_user: CurrentUser,
    device_type: str | None = Query(None, description="Filter by device type support"),
) -> list[VendorCompleteResponse]:
    """List all vendors with complete OUI and capability data.

    Args:
        device_type: Optional filter by device type support

    Returns:
        List of complete vendor information
    """
    cache = get_fingerprint_cache()

    # Build vendor data
    vendor_data: dict[str, dict[str, Any]] = {}

    # First, add all vendors from OUI database
    for vendor_id, oui_list in VENDOR_OUIS.items():
        vendor_data[vendor_id] = {
            "display_name": vendor_id.replace("_", " ").title(),
            "oui_prefixes": oui_list,
            "device_types": [],
            "protocols": [],
            "fingerprint_count": 0,
        }

    # Add device types from DEVICE_TYPE_VENDORS
    for dev_type, vendors in DEVICE_TYPE_VENDORS.items():
        for vendor in vendors:
            if vendor in vendor_data:
                if dev_type not in vendor_data[vendor]["device_types"]:
                    vendor_data[vendor]["device_types"].append(dev_type)

    # Add fingerprint data from cache (indexed by vendor for O(1) grouping)
    for vendor_key in cache.get_vendors():
        fps = cache.get_by_vendor(vendor_key)
        if vendor_key in vendor_data:
            vendor_data[vendor_key]["fingerprint_count"] = len(fps)
            if fps:
                vendor_data[vendor_key]["display_name"] = fps[0].get("vendor", vendor_key)
            for fp in fps:
                fp_protocols = _get_protocols_from_fingerprint(fp)
                for proto in fp_protocols:
                    if proto not in vendor_data[vendor_key]["protocols"]:
                        vendor_data[vendor_key]["protocols"].append(proto)

    # Infer protocols from typical vendors in PROTOCOL_DATA
    for protocol_id, proto_data in PROTOCOL_DATA.items():
        for vendor in proto_data.get("typical_vendors", []):
            if vendor in vendor_data:
                if protocol_id not in vendor_data[vendor]["protocols"]:
                    vendor_data[vendor]["protocols"].append(protocol_id)

    # Filter by device type if requested
    if device_type:
        vendor_data = {
            k: v for k, v in vendor_data.items()
            if device_type in v["device_types"]
        }

    return [
        VendorCompleteResponse(
            id=vendor_id,
            display_name=data["display_name"],
            oui_prefixes=data["oui_prefixes"][:10],  # Limit to 10
            device_types=sorted(data["device_types"])[:15],  # Limit to 15
            protocols=sorted(data["protocols"]),
            fingerprint_count=data["fingerprint_count"],
        )
        for vendor_id, data in sorted(vendor_data.items())
    ]


@router.get("/stats", response_model=FingerprintStatsResponse)
async def get_fingerprint_stats(
    _current_user: CurrentUser,
) -> FingerprintStatsResponse:
    """Get fingerprinting library statistics.

    Returns:
        Library statistics including protocol, vendor, and OUI counts
    """
    from app.protocol_engines.identity import get_registered_protocols

    cache = get_fingerprint_cache()

    # Count OUI prefixes
    total_ouis = sum(len(ouis) for ouis in VENDOR_OUIS.values())

    # Count unique device types
    all_device_types = set()
    for device_types in DEVICE_TYPE_VENDORS.values():
        all_device_types.update(device_types)

    # Count protocols by category
    protocols_by_category: dict[str, int] = {}
    for data in PROTOCOL_DATA.values():
        category = data["category"]
        protocols_by_category[category] = protocols_by_category.get(category, 0) + 1

    return FingerprintStatsResponse(
        total_protocols=len(PROTOCOL_DATA),
        total_vendors=len(VENDOR_OUIS),
        total_oui_prefixes=total_ouis,
        total_fingerprints=cache.get_count(),
        total_device_types=len(all_device_types),
        identity_builders=len(get_registered_protocols()),
        protocols_by_category=protocols_by_category,
        total_device_templates=get_template_count(),
        total_firmware_variants=get_total_firmware_variants(),
        total_cves=get_total_cves(),
    )


# ========== Device Template Endpoints ==========


def _template_to_summary(template: DeviceTemplate) -> DeviceTemplateSummaryResponse:
    """Convert a DeviceTemplate to a summary response."""
    vulnerable_count = len(template.get_vulnerable_firmwares())
    return DeviceTemplateSummaryResponse(
        id=template.id,
        vendor=template.vendor,
        vendor_family=template.vendor_family,
        model=template.model,
        model_name=template.model_name,
        device_type=template.device_type,
        description=template.description,
        supported_protocols=template.supported_protocols,
        firmware_count=len(template.firmware_variants),
        vulnerable_firmware_count=vulnerable_count,
        has_cves=vulnerable_count > 0,
    )


def _firmware_to_response(fw: FirmwareVariant) -> FirmwareVariantResponse:
    """Convert a FirmwareVariant to a response."""
    return FirmwareVariantResponse(
        version=fw.version,
        release_date=fw.release_date.isoformat(),
        is_latest=fw.is_latest,
        is_default=fw.is_default,
        cves=fw.cves,
        notes=fw.notes,
    )


def _template_to_detail(template: DeviceTemplate) -> DeviceTemplateDetailResponse:
    """Convert a DeviceTemplate to a detail response."""
    instance_rules = None
    if template.instance_rules:
        instance_rules = {
            "serial_format": template.instance_rules.serial_format,
            "station_name_pattern": template.instance_rules.station_name_pattern,
            "vendor_short": template.instance_rules.vendor_short,
            "model_short": template.instance_rules.model_short,
        }

    return DeviceTemplateDetailResponse(
        id=template.id,
        vendor=template.vendor,
        vendor_family=template.vendor_family,
        model=template.model,
        model_name=template.model_name,
        device_type=template.device_type,
        description=template.description,
        oui_prefixes=template.oui_prefixes,
        tcp_stack=template.tcp_stack,
        response_timing=template.response_timing,
        error_behavior=template.error_behavior,
        supported_protocols=template.supported_protocols,
        firmware_variants=[_firmware_to_response(fw) for fw in template.firmware_variants],
        instance_rules=instance_rules,
        modbus_identity=template.modbus_identity,
        ethernet_ip_identity=template.ethernet_ip_identity,
        profinet_identity=template.profinet_identity,
        s7_identity=template.s7_identity,
        bacnet_identity=template.bacnet_identity,
        snmp_identity=template.snmp_identity,
        protocol_quirks=template.protocol_quirks,
        is_builtin=template.is_builtin,
    )


@router.get("/device-templates", response_model=list[DeviceTemplateSummaryResponse])
async def list_device_templates(
    _current_user: CurrentUser,
    vendor: str | None = Query(None, description="Filter by vendor"),
    device_type: str | None = Query(None, description="Filter by device type"),
    has_cves: bool | None = Query(None, description="Filter by CVE presence"),
) -> list[DeviceTemplateSummaryResponse]:
    """List all device templates with firmware variants.

    Args:
        vendor: Optional filter by vendor
        device_type: Optional filter by device type
        has_cves: Optional filter for templates with vulnerable firmwares

    Returns:
        List of device template summaries
    """
    if vendor:
        templates = get_templates_by_vendor(vendor)
    elif device_type:
        templates = get_templates_by_device_type(device_type)
    elif has_cves:
        templates = get_templates_with_cves()
    else:
        templates = get_all_templates()

    # Additional filtering
    if has_cves is not None and vendor:
        if has_cves:
            templates = [t for t in templates if t.get_vulnerable_firmwares()]
        else:
            templates = [t for t in templates if not t.get_vulnerable_firmwares()]

    return [_template_to_summary(t) for t in templates]


@router.get("/device-templates/{template_id:path}", response_model=DeviceTemplateDetailResponse)
async def get_device_template_detail(
    template_id: str,
    _current_user: CurrentUser,
) -> DeviceTemplateDetailResponse:
    """Get detailed device template information.

    Args:
        template_id: Template identifier (e.g., siemens/s7-1500/cpu-1516-3)

    Returns:
        Full template details including firmware variants

    Raises:
        HTTPException: If template not found
    """
    template = get_template_by_id(template_id)

    if not template:
        raise NotFoundError("Device template", template_id)

    return _template_to_detail(template)


@router.post("/device-templates/instance", response_model=DeviceInstanceResponse)
async def generate_device_instance_endpoint(
    request: GenerateInstanceRequest,
    _current_user: CurrentUser,
) -> DeviceInstanceResponse:
    """Generate a device instance from a template.

    This generates unique serial numbers, station names, and merges
    protocol identities based on the selected firmware version.

    Args:
        request: Instance generation parameters

    Returns:
        Generated device instance with unique values

    Raises:
        HTTPException: If template or firmware not found
    """
    instance = generate_device_instance(
        template_id=request.template_id,
        firmware_version=request.firmware_version,
        station_name=request.station_name,
        serial_number=request.serial_number,
        mac_address=request.mac_address,
        ip_address=request.ip_address,
        location=request.location,
        sequence=request.sequence,
    )

    if not instance:
        raise NotFoundError("Device template", request.template_id)

    return DeviceInstanceResponse(
        template_id=instance.template_id,
        firmware_version=instance.firmware_version,
        serial_number=instance.serial_number,
        station_name=instance.station_name,
        mac_address=instance.mac_address,
        ip_address=instance.ip_address,
        cves=instance.cves,
        merged_identities=instance.merged_identities,
    )


@router.get("/device-templates/{template_id:path}/firmwares", response_model=list[FirmwareVariantResponse])
async def list_template_firmwares(
    template_id: str,
    _current_user: CurrentUser,
    vulnerable_only: bool = Query(False, description="Only show vulnerable firmwares"),
) -> list[FirmwareVariantResponse]:
    """List firmware variants for a device template.

    Args:
        template_id: Template identifier
        vulnerable_only: Only return firmwares with CVEs

    Returns:
        List of firmware variants

    Raises:
        HTTPException: If template not found
    """
    template = get_template_by_id(template_id)

    if not template:
        raise NotFoundError("Device template", template_id)

    if vulnerable_only:
        firmwares = template.get_vulnerable_firmwares()
    else:
        firmwares = template.firmware_variants

    return [_firmware_to_response(fw) for fw in firmwares]


# ========== Palette Endpoints ==========


def _db_template_to_palette(row: DeviceTemplateModel) -> PaletteDeviceResponse:
    """Convert a DB DeviceTemplate row to a palette response."""
    timing_model = None
    if row.palette_config and isinstance(row.palette_config, dict):
        timing_model = row.palette_config.get("timing_model")

    vendor_fingerprint = None
    if row.vendor and row.model:
        vendor_fingerprint = {
            "fingerprint_vendor": row.vendor,
            "fingerprint_model": row.model,
        }
    elif row.vendor:
        vendor_fingerprint = {"fingerprint_vendor": row.vendor}

    # Use name, falling back to model or vendor_family
    name = row.name or row.model or row.vendor_family or f"{row.vendor or 'Unknown'} {row.device_type or 'Device'}"

    return PaletteDeviceResponse(
        id=str(row.id),
        name=name,
        device_type=row.device_type or "other",
        role=row.role,
        description=row.description,
        supported_protocols=row.active_protocols,
        timing_model=timing_model,
        vendor_fingerprint=vendor_fingerprint,
        vertical_hints=row.vertical_hints,
        is_builtin=row.source == TemplateSource.VENDOR_BUILTIN.value,
        template_id=row.name,  # The string template ID for fingerprint lookup
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/palette", response_model=PaletteDeviceListResponse)
async def list_palette_devices(
    db: DBSession,
    _current_user: CurrentUser,
    device_type: str | None = Query(None, description="Filter by device type"),
    protocol: str | None = Query(None, description="Filter by protocol"),
    vertical: str | None = Query(None, description="Filter by industry vertical"),
    search: str | None = Query(None, description="Search name/description"),
    page_size: int = Query(200, ge=1, le=500, description="Max items to return"),
) -> PaletteDeviceListResponse:
    """List device templates for the Scenario Studio palette.

    Returns device templates in a shape compatible with the drag-and-drop palette,
    replacing the old /api/v1/devices endpoint.
    """
    query = select(DeviceTemplateModel).where(DeviceTemplateModel.is_active.is_(True))

    if device_type:
        query = query.where(DeviceTemplateModel.device_type == device_type)

    if protocol:
        query = query.where(DeviceTemplateModel.active_protocols.contains([protocol]))

    if vertical:
        query = query.where(DeviceTemplateModel.vertical_hints.contains([vertical]))

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            DeviceTemplateModel.name.ilike(search_filter)
            | DeviceTemplateModel.description.ilike(search_filter)
        )

    query = query.order_by(DeviceTemplateModel.name).limit(page_size)

    # Count total
    count_query = select(func.count(DeviceTemplateModel.id)).where(DeviceTemplateModel.is_active.is_(True))
    if device_type:
        count_query = count_query.where(DeviceTemplateModel.device_type == device_type)
    if protocol:
        count_query = count_query.where(DeviceTemplateModel.active_protocols.contains([protocol]))
    if vertical:
        count_query = count_query.where(DeviceTemplateModel.vertical_hints.contains([vertical]))
    if search:
        count_query = count_query.where(
            DeviceTemplateModel.name.ilike(f"%{search}%")
            | DeviceTemplateModel.description.ilike(f"%{search}%")
        )

    result = await db.execute(query)
    rows = result.scalars().all()
    total = await db.scalar(count_query) or 0

    return PaletteDeviceListResponse(
        items=[_db_template_to_palette(row) for row in rows],
        total=total,
    )


# ========== User-Created Device Template CRUD ==========


@router.post(
    "/device-templates",
    response_model=PaletteDeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_device_template(
    request: DeviceTemplateCreateRequest,
    db: DBSession,
    _current_user: CurrentUser,
) -> PaletteDeviceResponse:
    """Create a new user-defined device template."""
    palette_config: dict[str, Any] = {}
    if request.timing_model:
        palette_config["timing_model"] = request.timing_model
    if request.payload_templates:
        palette_config["payload_templates"] = request.payload_templates
    if request.behavior_model:
        palette_config["behavior_model"] = request.behavior_model

    template = DeviceTemplateModel(
        source=TemplateSource.USER_CREATED.value,
        name=request.name,
        device_type=request.device_type,
        role=request.role,
        description=request.description,
        vendor=request.vendor,
        model=request.model,
        active_protocols=request.supported_protocols,
        vertical_hints=request.vertical_hints,
        palette_config=palette_config if palette_config else None,
        is_active=True,
        confidence=1.0,
        sample_count=1,
        consistency_score=1.0,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return _db_template_to_palette(template)


@router.put("/device-templates/{template_id}", response_model=PaletteDeviceResponse)
async def update_device_template(
    template_id: UUID,
    request: DeviceTemplateUpdateRequest,
    db: DBSession,
    _current_user: CurrentUser,
) -> PaletteDeviceResponse:
    """Update a user-created device template."""
    result = await db.execute(
        select(DeviceTemplateModel).where(DeviceTemplateModel.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise NotFoundError("Device template", str(template_id))

    if template.source != TemplateSource.USER_CREATED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify built-in device templates",
        )

    # Update basic fields
    update_fields = request.model_dump(exclude_unset=True, exclude={"timing_model", "payload_templates", "behavior_model"})
    for field_name, value in update_fields.items():
        if field_name == "supported_protocols":
            setattr(template, "active_protocols", value)
        else:
            setattr(template, field_name, value)

    # Update palette_config sub-fields
    palette_config = dict(template.palette_config or {})
    if request.timing_model is not None:
        palette_config["timing_model"] = request.timing_model
    if request.payload_templates is not None:
        palette_config["payload_templates"] = request.payload_templates
    if request.behavior_model is not None:
        palette_config["behavior_model"] = request.behavior_model
    template.palette_config = palette_config if palette_config else None

    await db.commit()
    await db.refresh(template)

    return _db_template_to_palette(template)


@router.delete("/device-templates/{template_id}")
async def delete_device_template(
    template_id: UUID,
    db: DBSession,
    _current_user: CurrentUser,
) -> dict[str, str]:
    """Delete a user-created device template."""
    result = await db.execute(
        select(DeviceTemplateModel).where(DeviceTemplateModel.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise NotFoundError("Device template", str(template_id))

    if template.source != TemplateSource.USER_CREATED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete built-in device templates",
        )

    await db.delete(template)
    await db.commit()

    return {"message": "Device template deleted successfully"}


@router.post(
    "/device-templates/{template_id}/duplicate",
    response_model=PaletteDeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_device_template(
    template_id: UUID,
    db: DBSession,
    _current_user: CurrentUser,
    new_name: str = Query(..., min_length=1, max_length=255),
) -> PaletteDeviceResponse:
    """Duplicate a device template with a new name."""
    result = await db.execute(
        select(DeviceTemplateModel).where(DeviceTemplateModel.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise NotFoundError("Device template", str(template_id))

    new_template = DeviceTemplateModel(
        source=TemplateSource.USER_CREATED.value,
        name=new_name,
        device_type=template.device_type,
        role=template.role,
        description=template.description,
        vendor=template.vendor,
        vendor_family=template.vendor_family,
        model=template.model,
        active_protocols=template.active_protocols,
        vertical_hints=template.vertical_hints,
        palette_config=template.palette_config,
        oui_patterns=template.oui_patterns,
        tcp_signature=template.tcp_signature,
        protocol_identities=template.protocol_identities,
        modbus_identity=template.modbus_identity,
        ethernet_ip_identity=template.ethernet_ip_identity,
        profinet_identity=template.profinet_identity,
        s7_identity=template.s7_identity,
        snmp_identity=template.snmp_identity,
        bacnet_identity=template.bacnet_identity,
        opc_ua_identity=template.opc_ua_identity,
        response_timings=template.response_timings,
        typical_ports=template.typical_ports,
        protocol_quirks=template.protocol_quirks,
        error_behavior=template.error_behavior,
        is_active=True,
        confidence=1.0,
        sample_count=1,
        consistency_score=1.0,
    )

    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)

    return _db_template_to_palette(new_template)
