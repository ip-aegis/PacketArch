"""Template API routes for scenario creation from templates."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DBSession
from app.models.scenario import Scenario
from app.protocol_engines.vendor_oui import generate_mac_address
from app.services.ip_management import IPManagementService
from app.services.template_pattern_service import TemplatePatternService
from app.services.cve_fingerprint_service import CVEFingerprintService
from app.scenario_templates import (
    VERTICAL_TEMPLATES,
    get_template,
    list_templates,
    list_verticals,
)
from app.scenario_templates.phases import (
    PHASE_TEMPLATES,
    get_default_phases,
    list_phase_presets,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])


class VerticalResponse(BaseModel):
    """Vertical summary response."""

    id: str
    name: str
    template_count: int
    templates: list[str]


class TemplateSummaryResponse(BaseModel):
    """Template summary response."""

    vertical: str
    name: str
    display_name: str
    description: str
    device_count: int
    protocols: list[str]


class TemplateDetailResponse(BaseModel):
    """Full template detail response."""

    name: str
    description: str
    vertical: str
    devices: list[dict[str, Any]]
    flows: list[dict[str, Any]]
    zones: list[dict[str, Any]]
    total_duration_ms: int


class PhaseTemplateResponse(BaseModel):
    """Phase template response."""

    id: str
    name: str
    description: str
    duration_pct: int
    traffic_multiplier: float
    color: str
    behaviors: list[str]


class PhasePresetResponse(BaseModel):
    """Phase preset response."""

    name: str
    display_name: str
    phase_count: int
    phases: list[str]


class LearnedPatternOptions(BaseModel):
    """Options for learned pattern application."""

    timing: bool = True
    fingerprints: bool = True
    sequences: bool = True
    function_codes: bool = True
    address_patterns: bool = True


class CreateFromTemplateRequest(BaseModel):
    """Request to create scenario from template."""

    vertical: str
    template_name: str = "default"
    scenario_name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    phase_preset: str = "standard"
    auto_assign_addresses: bool = True
    total_duration_ms: int | None = None
    # Learned pattern options
    apply_learned_patterns: bool = True
    learned_pattern_options: LearnedPatternOptions | None = None


class CreateFromTemplateResponse(BaseModel):
    """Response after creating scenario from template."""

    scenario_id: str
    name: str
    device_count: int
    flow_count: int
    zone_count: int
    phase_count: int
    learned_patterns_applied: bool = False
    protocols_enhanced: list[str] = []


@router.get("/verticals", response_model=list[VerticalResponse])
async def get_verticals(
    _current_user: CurrentUser,
) -> list[VerticalResponse]:
    """List available industry verticals.

    Returns:
        List of verticals with template counts
    """
    verticals = list_verticals()
    return [VerticalResponse(**v) for v in verticals]


@router.get("/list", response_model=list[TemplateSummaryResponse])
async def get_templates(
    _current_user: CurrentUser,
    vertical: str | None = None,
) -> list[TemplateSummaryResponse]:
    """List available scenario templates.

    Args:
        vertical: Optional filter by vertical

    Returns:
        List of template summaries
    """
    templates = list_templates()

    if vertical:
        templates = [t for t in templates if t["vertical"] == vertical]

    return [TemplateSummaryResponse(**t) for t in templates]


@router.get("/detail/{vertical}/{template_name}", response_model=TemplateDetailResponse)
async def get_template_detail(
    vertical: str,
    template_name: str,
    _current_user: CurrentUser,
) -> TemplateDetailResponse:
    """Get detailed template information.

    Args:
        vertical: Industry vertical
        template_name: Template name

    Returns:
        Full template details

    Raises:
        HTTPException: If template not found
    """
    template = get_template(vertical, template_name)

    if not template:
        # Try to find a default template for the vertical
        if vertical in VERTICAL_TEMPLATES:
            available = list(VERTICAL_TEMPLATES[vertical].keys())
            if available:
                template = VERTICAL_TEMPLATES[vertical][available[0]]
                template_name = available[0]

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found for vertical '{vertical}'",
        )

    return TemplateDetailResponse(
        name=template.get("name", template_name),
        description=template.get("description", ""),
        vertical=template.get("vertical", vertical),
        devices=template.get("devices", []),
        flows=template.get("flows", []),
        zones=template.get("zones", []),
        total_duration_ms=template.get("total_duration_ms", 300000),
    )


@router.get("/phases", response_model=list[PhaseTemplateResponse])
async def get_phase_templates(
    _current_user: CurrentUser,
) -> list[PhaseTemplateResponse]:
    """List available phase templates.

    Returns:
        List of phase templates
    """
    phases = []
    for phase_id, phase_data in PHASE_TEMPLATES.items():
        phases.append(PhaseTemplateResponse(
            id=phase_id,
            name=phase_data.get("name", phase_id),
            description=phase_data.get("description", ""),
            duration_pct=phase_data.get("duration_pct", 25),
            traffic_multiplier=phase_data.get("traffic_multiplier", 1.0),
            color=phase_data.get("color", "#1890ff"),
            behaviors=phase_data.get("behaviors", []),
        ))
    return phases


@router.get("/phases/presets", response_model=list[PhasePresetResponse])
async def get_phase_presets(
    _current_user: CurrentUser,
) -> list[PhasePresetResponse]:
    """List available phase presets.

    Returns:
        List of phase presets
    """
    presets = list_phase_presets()
    return [PhasePresetResponse(**p) for p in presets]


@router.post("/create", response_model=CreateFromTemplateResponse)
async def create_scenario_from_template(
    request: CreateFromTemplateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> CreateFromTemplateResponse:
    """Create a new scenario from a template.

    Args:
        request: Template creation request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created scenario summary

    Raises:
        HTTPException: If template not found
    """
    # Get template
    template = get_template(request.vertical, request.template_name)

    if not template:
        # Try first template in vertical
        if request.vertical in VERTICAL_TEMPLATES:
            available = list(VERTICAL_TEMPLATES[request.vertical].keys())
            if available:
                template = VERTICAL_TEMPLATES[request.vertical][available[0]]

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{request.template_name}' not found for vertical '{request.vertical}'",
        )

    # Determine total duration
    total_duration_ms = request.total_duration_ms or template.get("total_duration_ms", 300000)

    # STEP 1: Create scenario shell first to get ID for IP allocation
    scenario = Scenario(
        id=uuid.uuid4(),
        name=request.scenario_name,
        description=request.description or template.get("description", ""),
        vertical=request.vertical,
        total_duration_ms=total_duration_ms,
        definition={},  # Will be populated after IP allocation
        user_id=current_user.id,
        version=1,
    )

    db.add(scenario)
    await db.flush()  # Get scenario ID

    # STEP 2: Allocate IP range FIRST (before building zones/devices)
    allocation = None
    try:
        allocation = await IPManagementService.allocate_range(db, scenario.id)
        scenario.addressing_config = {
            "ip_range": allocation.cidr_range,
            "range_index": allocation.range_index,
            "auto_assign_enabled": True,
        }
    except ValueError:
        # No IP ranges available - proceed without allocation
        logger.warning("No IP ranges available for scenario")

    # STEP 3: Build zones with subnets derived from allocation
    zones = _build_zones_from_template(template, allocation)

    # STEP 4: Build devices from template
    devices = {}
    device_index = 0
    for device_spec in template.get("devices", []):
        count = device_spec.get("count", 1)
        for i in range(count):
            device_index += 1
            device_id = f"device_{device_index:03d}"

            # Generate name from pattern
            name_pattern = device_spec.get("name_pattern", "{type}-{n:03d}")
            try:
                name = name_pattern.format(n=device_index, **device_spec)
            except KeyError:
                name = f"{device_spec.get('type', 'device')}-{device_index:03d}"

            # Build device
            device = {
                "id": device_id,
                "name": name,
                "type": device_spec.get("type", "plc"),
                "protocols": device_spec.get("protocols", []),
                "zoneId": device_spec.get("zone"),
                "vendor": device_spec.get("vendor"),
                "fingerprintModel": device_spec.get("fingerprint_model"),
                "network": {},
            }

            # Add role if specified
            if device_spec.get("role"):
                device["role"] = device_spec.get("role")

            # Add error config if specified
            if device_spec.get("error_config"):
                device["errorConfig"] = device_spec.get("error_config")

            # Add CVE IDs if specified
            cve_ids = device_spec.get("cve_ids", [])
            if cve_ids:
                device["cveIds"] = cve_ids

                # Resolve CVE configuration (vulnerable variant lookup)
                try:
                    variant = await CVEFingerprintService.get_best_variant_for_device(
                        db,
                        vendor=device_spec.get("vendor", ""),
                        fingerprint_model=device_spec.get("fingerprint_model"),
                        cve_ids=cve_ids,
                    )
                    if variant:
                        device["vulnerableVariantId"] = str(variant.id)
                        device["vulnerableFirmware"] = variant.firmware_version
                        # Store identity overrides for traffic generation
                        device["cveIdentityOverrides"] = (
                            CVEFingerprintService.extract_identity_overrides(variant)
                        )
                        logger.info(
                            f"Resolved CVE for device {device_id}: {variant.display_name}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to resolve CVE for device {device_id}: {e}")

            # Auto-assign MAC if requested
            if request.auto_assign_addresses:
                device["network"]["macAddress"] = generate_mac_address(
                    vendor=device_spec.get("vendor"),
                    device_type=device_spec.get("type"),
                )

            devices[device_id] = device

    # STEP 5: Auto-assign IP addresses from allocated range
    if request.auto_assign_addresses and zones:
        _auto_assign_ips(devices, zones, allocation)

    # Build flows from template - ensure every device has at least one flow
    flows = {}
    flow_index = 0

    # Group devices by type for flow matching
    devices_by_type: dict[str, list[str]] = {}
    for device_id, device in devices.items():
        dtype = device.get("type", "unknown")
        if dtype not in devices_by_type:
            devices_by_type[dtype] = []
        devices_by_type[dtype].append(device_id)

    for flow_spec in template.get("flows", []):
        source_types = flow_spec.get("source_types", [])
        target_types = flow_spec.get("target_types", [])
        protocol = flow_spec.get("protocol")
        interval_ms = flow_spec.get("interval_ms", 1000)

        # Create flows between matching device types
        for source_type in source_types:
            for target_type in target_types:
                source_devices = devices_by_type.get(source_type, [])
                target_devices = devices_by_type.get(target_type, [])

                if not source_devices or not target_devices:
                    continue

                # Smart flow distribution: EVERY source AND target must have at least one flow
                # Generate max(sources, targets) flows to ensure full coverage on both sides
                n_flows = max(len(source_devices), len(target_devices))

                for i in range(n_flows):
                    source_id = source_devices[i % len(source_devices)]
                    target_id = target_devices[i % len(target_devices)]

                    if source_id != target_id:
                        flow_index += 1
                        flow_id = f"flow_{flow_index:03d}"
                        flows[flow_id] = {
                            "id": flow_id,
                            "sourceDeviceId": source_id,
                            "targetDeviceId": target_id,
                            "protocol": protocol,
                            "timing": {
                                "intervalMs": interval_ms,
                            },
                            "config": {},
                        }

    # Generate phases
    phases = get_default_phases(
        total_duration_ms=total_duration_ms,
        preset=request.phase_preset,
        vertical=request.vertical,
    )

    # Create scenario definition
    definition = {
        "devices": devices,
        "flows": flows,
        "zones": zones,
        "phases": phases,
    }

    # Add external communications config if present in template
    external_comms = template.get("external_comms")
    if external_comms:
        definition["external_comms"] = external_comms
        logger.info(f"Added external comms config to scenario: {external_comms}")

    # Apply learned patterns if requested
    learned_patterns_applied = False
    protocols_enhanced = []

    if request.apply_learned_patterns:
        options = request.learned_pattern_options or LearnedPatternOptions()
        try:
            definition = await TemplatePatternService.enhance_scenario_from_learned(
                db,
                definition,
                apply_timing=options.timing,
                apply_fingerprints=options.fingerprints,
                apply_sequences=options.sequences,
                apply_function_codes=options.function_codes,
                apply_address_patterns=options.address_patterns,
            )
            learned_patterns_applied = True
            protocols_enhanced = definition.get("learned_patterns_applied", {}).get(
                "protocols_enhanced", []
            )
            logger.info(
                f"Applied learned patterns to scenario. Protocols enhanced: {protocols_enhanced}"
            )
        except Exception as e:
            logger.warning(f"Failed to apply learned patterns: {e}")
            # Continue without learned patterns

    # Update scenario with final definition
    scenario.definition = definition

    await db.commit()
    await db.refresh(scenario)

    return CreateFromTemplateResponse(
        scenario_id=str(scenario.id),
        name=scenario.name,
        device_count=len(devices),
        flow_count=len(flows),
        zone_count=len(zones),
        phase_count=len(phases),
        learned_patterns_applied=learned_patterns_applied,
        protocols_enhanced=protocols_enhanced,
    )


def _build_zones_from_template(
    template: dict,
    allocation: Any | None,
) -> dict:
    """Build zones with subnets derived from allocated range.

    Args:
        template: Template dictionary
        allocation: IP range allocation (or None if not available)

    Returns:
        Dictionary of zone configurations
    """
    from app.models.ip_range_allocation import IPRangeAllocation

    zones = {}
    range_idx = allocation.range_index if allocation else 1

    for zone_spec in template.get("zones", []):
        zone_id = zone_spec.get("id", f"zone_{len(zones)}")
        subnet_offset = zone_spec.get("subnet_offset")

        # Derive subnet from allocation or use legacy fallback
        if subnet_offset is not None and allocation:
            subnet = f"10.{range_idx}.{subnet_offset}.0/24"
        else:
            # Legacy fallback for templates without subnet_offset
            subnet = zone_spec.get("subnet", f"10.{range_idx}.{len(zones)}.0/24")

        zones[zone_id] = {
            "id": zone_id,
            "name": zone_spec.get("name", zone_id),
            "level": zone_spec.get("level", 1),
            "network": {
                "subnet": subnet,
                "subnet_offset": subnet_offset,
                "vlan": zone_spec.get("vlan"),
            },
        }

        # Preserve security_level if specified
        if zone_spec.get("security_level"):
            zones[zone_id]["security_level"] = zone_spec.get("security_level")

    return zones


def _auto_assign_ips(
    devices: dict,
    zones: dict,
    allocation: Any | None = None,
) -> None:
    """Auto-assign IP addresses to devices from allocated range.

    Args:
        devices: Device dictionary (modified in place)
        zones: Zone dictionary
        allocation: IP range allocation (or None for fallback behavior)
    """
    # Get range index from allocation
    range_idx = allocation.range_index if allocation else 1

    # Group devices by zone
    devices_by_zone: dict[str, list[str]] = {}
    for device_id, device in devices.items():
        zone_id = device.get("zoneId", "default")
        if zone_id not in devices_by_zone:
            devices_by_zone[zone_id] = []
        devices_by_zone[zone_id].append(device_id)

    # Assign IPs within each zone using allocated range
    for zone_id, device_ids in devices_by_zone.items():
        zone = zones.get(zone_id, {})
        network = zone.get("network", {})

        # Get subnet_offset from zone (set by _build_zones_from_template)
        subnet_offset = network.get("subnet_offset")

        if subnet_offset is not None and allocation:
            # Use allocation-derived subnet: 10.{range_idx}.{subnet_offset}.x
            base = f"10.{range_idx}.{subnet_offset}"
        else:
            # Fallback: parse subnet from zone
            subnet = network.get("subnet", "192.168.100.0/24")
            if "/" in subnet:
                base_ip = subnet.split("/")[0]
            else:
                base_ip = subnet
            octets = base_ip.split(".")
            base = ".".join(octets[:3]) if len(octets) >= 3 else "192.168.100"

        # Assign IPs starting at .10
        for i, device_id in enumerate(device_ids, start=10):
            device = devices[device_id]
            dev_network = device.get("network", {})
            dev_network["ipAddress"] = f"{base}.{i}"
            dev_network["subnetMask"] = "255.255.255.0"
            dev_network["gateway"] = f"{base}.1"
            dev_network["vlan"] = network.get("vlan")
            device["network"] = dev_network
