"""Template API routes for scenario creation from templates."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.models.cloud_service import CloudServiceEndpoint, CloudServiceProvider
from app.models.scenario import Scenario
from app.protocol_engines.vendor_oui import generate_mac_address
from app.services.ip_management import IPManagementService
from app.services.cve_fingerprint_service import CVEFingerprintService
from app.services.device_templates import get_fingerprint_by_vendor_model
from app.traffic_generator.flow_generator import (
    DeviceSpec,
    FlowPattern,
    generate_flows_for_scenario,
)
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
from app.services.device_identity_enricher import (
    enrich_device_serial_numbers,
    enrich_device_unique_identifiers,
)
from app.ai_services.device_namer import AIDeviceNamer, DeviceNamingContext
from app.mcp_server.ai_providers import AIProviderFactory

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


class CreateFromTemplateRequest(BaseModel):
    """Request to create scenario from template."""

    vertical: str
    template_name: str = "default"
    scenario_name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    phase_preset: str = "standard"
    auto_assign_addresses: bool = True
    total_duration_ms: int | None = None
    # Flow generation pattern (realistic, hierarchical, mesh, star, tree)
    flow_pattern: str = "realistic"
    use_smart_flow_generation: bool = True  # Use new SmartFlowGenerator
    # AI-enhanced device naming (enabled by default)
    use_ai_naming: bool = False  # Templates have meaningful built-in names by default
    process_context: str | None = Field(
        None,
        description="Optional additional context about the industrial process for AI naming",
        max_length=500,
    )


class CreateFromTemplateResponse(BaseModel):
    """Response after creating scenario from template."""

    scenario_id: str
    name: str
    device_count: int
    flow_count: int
    zone_count: int
    phase_count: int
    ai_naming_applied: bool = False


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
        raise NotFoundError("Template", f"{vertical}/{template_name}")

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
        raise NotFoundError("Template", f"{request.vertical}/{request.template_name}")

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

            # Generate name: prefer explicit name, fall back to pattern
            if device_spec.get("name"):
                # Template has explicit device name (new style)
                name = device_spec.get("name")
            else:
                # Fall back to name_pattern for backward compatibility
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

            # Populate full vendor_fingerprint for traffic generation
            # This provides deep CIP fingerprinting data (ethernet_ip_identity, cip_identity_object, etc.)
            vendor = device_spec.get("vendor")
            fingerprint_model = device_spec.get("fingerprint_model")
            if vendor and fingerprint_model:
                full_fingerprint = get_fingerprint_by_vendor_model(vendor, fingerprint_model)
                if full_fingerprint:
                    device["vendorFingerprint"] = full_fingerprint
                    logger.debug(f"Added vendorFingerprint for device {device_id}: {fingerprint_model}")

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

                # Resolve CVE configuration using unified resolver
                try:
                    resolved_cve = await CVEFingerprintService.resolve_cves_for_device(
                        db,
                        vendor=device_spec.get("vendor", ""),
                        model=device_spec.get("fingerprint_model"),
                        cve_ids=cve_ids,
                        base_fingerprint=device.get("vendorFingerprint"),
                    )
                    if resolved_cve:
                        device["vulnerableVariantId"] = resolved_cve.variant_id
                        device["vulnerableFirmware"] = resolved_cve.firmware_version
                        # Store fully resolved identity overrides for traffic generation
                        device["cveIdentityOverrides"] = resolved_cve.to_vulnerability_override()
                        device["resolvedCveSeverity"] = resolved_cve.severity
                        logger.info(
                            f"Resolved CVE for device {device_id}: {resolved_cve.display_name} "
                            f"(severity={resolved_cve.severity})"
                        )
                except Exception as e:
                    logger.warning(f"Failed to resolve CVE for device {device_id}: {e}")

            # Auto-assign MAC if requested
            if request.auto_assign_addresses:
                fp_ouis = device.get("vendorFingerprint", {}).get("oui_prefixes")
                device["network"]["macAddress"] = generate_mac_address(
                    vendor=device_spec.get("vendor"),
                    device_type=device_spec.get("type"),
                    oui_prefixes=fp_ouis if fp_ouis else None,
                )

            # CRITICAL: Generate unique serial numbers for each device
            # This prevents Cyber Vision from merging devices with same fingerprint
            enrich_device_serial_numbers(device, device_id, str(scenario.id))

            devices[device_id] = device

    # STEP 4.5: AI-Enhanced Device Naming
    # Generate meaningful, process-aware device names using AI
    ai_naming_applied = False
    if request.use_ai_naming:
        try:
            ai_provider = await AIProviderFactory.create(db)
            namer = AIDeviceNamer()

            context = DeviceNamingContext(
                vertical=request.vertical,
                template_name=request.template_name,
                template_description=template.get("description", ""),
                zones=zones,
                process_context=request.process_context,
            )

            # Convert devices dict to list for AI processing
            device_list = list(devices.values())

            # Enhance names with AI
            enhanced_devices = await namer.enhance_device_names(
                devices=device_list,
                context=context,
                ai_provider=ai_provider,
            )

            # Rebuild devices dict with enhanced names
            devices = {d["id"]: d for d in enhanced_devices}
            ai_naming_applied = True

            logger.info(
                f"AI-enhanced naming applied to {len(devices)} devices"
            )

        except Exception as e:
            logger.warning(
                f"AI naming failed, using generic names: {e}. "
                "Check that AI provider is configured in Settings."
            )
            # Continue with generic names - don't fail scenario creation

    # STEP 4.6: Enrich protocol identities with device names
    # This ensures Cyber Vision displays the contextual device names (AI-generated or generic)
    # in protocol responses (EtherNet/IP product_name, PROFINET station_name, etc.)
    for device_id, device in devices.items():
        enrich_device_unique_identifiers(device, device_id, str(scenario.id))

    logger.info(f"Enriched {len(devices)} devices with unique protocol identifiers")

    # STEP 5: Auto-assign IP addresses from allocated range
    if request.auto_assign_addresses and zones:
        _auto_assign_ips(devices, zones, allocation)

    # Build flows
    # If the template defines flows, use them (they have protocol-correct timing
    # and zone isolation). Fall back to SmartFlowGenerator for templates without
    # flows or when explicitly requested.
    flows = {}
    cloud_service_links = []  # Will be populated from cloud_services template config
    template_has_flows = bool(template.get("flows"))
    use_smart = request.use_smart_flow_generation and not template_has_flows

    if use_smart:
        # Use SmartFlowGenerator for role-based, realistic flow generation
        # Convert devices dict to list of dicts for the generator
        device_list = []
        for device_id, device in devices.items():
            device_dict = {
                "device_id": device_id,
                "device_type": device.get("type", "unknown"),
                "role": device.get("role"),  # May be None - DeviceSpec.from_dict will infer
                "ip_address": device.get("network", {}).get("ipAddress", "0.0.0.0"),
                "mac_address": device.get("network", {}).get("macAddress"),
                "vendor": device.get("vendor"),
                "protocols": device.get("protocols", []),
                "zone": device.get("zoneId"),
            }
            device_list.append(device_dict)

        # Get default protocol from template flows (first protocol found)
        default_protocol = "modbus_tcp"
        template_flows = template.get("flows", [])
        if template_flows:
            default_protocol = template_flows[0].get("protocol", "modbus_tcp")

        # Get available protocols from template
        protocols = list({f.get("protocol") for f in template_flows if f.get("protocol")})

        # Generate flows using SmartFlowGenerator
        generated_flows = generate_flows_for_scenario(
            devices=device_list,
            pattern=request.flow_pattern or "realistic",
            protocols=protocols if protocols else None,
        )

        # Convert generated flows to scenario format
        for flow_dict in generated_flows:
            flow_id = flow_dict["flow_id"]
            flows[flow_id] = {
                "id": flow_id,
                "sourceDeviceId": flow_dict["source_id"],
                "targetDeviceId": flow_dict["destination_id"],
                "protocol": flow_dict["protocol"],
                "timing": {
                    "intervalMs": int(flow_dict.get("poll_rate", 1000)),
                },
                "priority": flow_dict.get("priority", 5),
                "config": {},
            }

        logger.info(
            f"SmartFlowGenerator created {len(flows)} flows using '{request.flow_pattern}' pattern"
        )

        # Create cloud service links from template (replaces legacy external flows)
        cloud_service_links = await _create_cloud_service_links_from_template(
            db, template, devices
        )
        if cloud_service_links:
            logger.info(f"Added {len(cloud_service_links)} cloud service links")

    else:
        # Template-driven flow generation (respects zone constraints)
        flow_index = 0

        # Group devices by (type, zone) for zone-aware flow matching
        devices_by_type: dict[str, list[str]] = {}
        devices_by_type_zone: dict[tuple[str, str], list[str]] = {}
        for device_id, device in devices.items():
            dtype = device.get("type", "unknown")
            dzone = device.get("zoneId", "")
            if dtype not in devices_by_type:
                devices_by_type[dtype] = []
            devices_by_type[dtype].append(device_id)
            key = (dtype, dzone)
            if key not in devices_by_type_zone:
                devices_by_type_zone[key] = []
            devices_by_type_zone[key].append(device_id)

        for flow_spec in template.get("flows", []):
            source_types = flow_spec.get("source_types", [])
            target_types = flow_spec.get("target_types", [])
            source_zones = flow_spec.get("source_zones", [])
            target_zones = flow_spec.get("target_zones", [])
            protocol = flow_spec.get("protocol")
            interval_ms = flow_spec.get("interval_ms", 1000)

            # Build jitter config if present
            timing: dict[str, Any] = {"intervalMs": interval_ms}
            if flow_spec.get("jitter_ms"):
                timing["jitterMs"] = flow_spec["jitter_ms"]
            if flow_spec.get("jitter_type"):
                timing["jitterType"] = flow_spec["jitter_type"]

            # Create flows between matching device types, respecting zone constraints
            for source_type in source_types:
                for target_type in target_types:
                    # Filter by zones when specified
                    if source_zones:
                        source_devices = []
                        for sz in source_zones:
                            source_devices.extend(
                                devices_by_type_zone.get((source_type, sz), [])
                            )
                    else:
                        source_devices = devices_by_type.get(source_type, [])

                    if target_zones:
                        target_devices = []
                        for tz in target_zones:
                            target_devices.extend(
                                devices_by_type_zone.get((target_type, tz), [])
                            )
                    else:
                        target_devices = devices_by_type.get(target_type, [])

                    if not source_devices or not target_devices:
                        continue

                    # Round-robin flow distribution
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
                                "timing": timing,
                                "config": {},
                            }

        # Also create cloud service links for legacy path
        cloud_service_links = await _create_cloud_service_links_from_template(
            db, template, devices
        )
        if cloud_service_links:
            logger.info(f"Added {len(cloud_service_links)} cloud service links (legacy path)")

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

    # Add cloud service links if any were created
    if cloud_service_links:
        definition["cloud_service_links"] = cloud_service_links

    # Add external communications config if present in template
    external_comms = template.get("external_comms")
    if external_comms:
        definition["external_comms"] = external_comms
        logger.info(f"Added external comms config to scenario: {external_comms}")

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
        ai_naming_applied=ai_naming_applied,
    )


async def _create_cloud_service_links_from_template(
    db: Any,
    template: dict,
    devices: dict,
) -> list[dict]:
    """Create cloud service links from template cloud_services configuration.

    Cloud service links connect devices to cloud service endpoints
    (Talk2M, TeamViewer, etc.) for heartbeat traffic generation.
    This replaces the legacy external flows approach.

    Args:
        db: Database session
        template: Template dictionary
        devices: Device dictionary

    Returns:
        List of cloud service link configurations
    """
    cloud_links = []
    link_index = 0

    # Get cloud_services configuration from template
    cloud_services_config = template.get("cloud_services", [])

    if not cloud_services_config:
        # Check for legacy external flows and migrate them
        cloud_links = await _migrate_external_flows_to_cloud_links(db, template, devices)
        return cloud_links

    for cloud_config in cloud_services_config:
        provider = cloud_config.get("provider")
        region = cloud_config.get("region")
        device_types = cloud_config.get("device_types", [])
        heartbeat_interval_ms = cloud_config.get("heartbeat_interval_ms", 30000)

        if not provider:
            continue

        # Look up cloud service endpoint from database
        query = select(CloudServiceEndpoint).where(
            CloudServiceEndpoint.provider == CloudServiceProvider(provider),
            CloudServiceEndpoint.is_active == True,
        )
        if region:
            query = query.where(CloudServiceEndpoint.region == region)

        result = await db.execute(query.limit(1))
        cloud_service = result.scalar_one_or_none()

        if not cloud_service:
            logger.warning(
                f"Cloud service not found for provider={provider}, region={region}"
            )
            continue

        # Find devices matching the specified types
        for device_id, device in devices.items():
            device_type = device.get("type", "")
            if device_type not in device_types:
                continue

            link_index += 1
            link_id = f"csl_{link_index:03d}"

            cloud_links.append({
                "id": link_id,
                "device_id": device_id,
                "cloud_service_id": str(cloud_service.id),
                "heartbeat_interval_ms": heartbeat_interval_ms,
                "enabled": True,
                # Include resolved cloud service data for agent consumption
                "cloud_service": {
                    "name": cloud_service.name,
                    "provider": cloud_service.provider.value,
                    "primary_ip": cloud_service.primary_ip,
                    "port": cloud_service.port,
                    "hostname": cloud_service.hostname,
                    "tls_enabled": cloud_service.tls_enabled,
                },
            })

            logger.debug(
                f"Created cloud link {link_id}: {device_id} -> "
                f"{cloud_service.name} ({cloud_service.primary_ip})"
            )

    return cloud_links


async def _migrate_external_flows_to_cloud_links(
    db: Any,
    template: dict,
    devices: dict,
) -> list[dict]:
    """Migrate legacy external flows to cloud service links.

    This handles backward compatibility for templates that still use
    the old external flow pattern (pattern="external", external_ip="...").

    Args:
        db: Database session
        template: Template dictionary
        devices: Device dictionary

    Returns:
        List of cloud service link configurations
    """
    # Known external IPs and their corresponding providers
    KNOWN_EXTERNAL_IPS = {
        "13.56.142.1": ("talk2m", "us-west"),
        "54.95.198.117": ("talk2m", "us-east"),
        "51.38.74.240": ("talk2m", "eu"),
        "87.98.169.126": ("talk2m", "ap"),
        "185.188.32.1": ("teamviewer", "global"),
        "185.188.32.2": ("teamviewer", "eu"),
    }

    cloud_links = []
    link_index = 0

    # Find legacy external flow definitions in template
    for flow_spec in template.get("flows", []):
        if flow_spec.get("pattern") != "external":
            continue

        external_ip = flow_spec.get("external_ip")
        external_port = flow_spec.get("external_port", 443)
        interval_ms = flow_spec.get("interval_ms", 30000)

        if not external_ip:
            continue

        # Look up provider from known IPs
        provider_info = KNOWN_EXTERNAL_IPS.get(external_ip)

        cloud_service = None
        if provider_info:
            provider, region = provider_info
            query = select(CloudServiceEndpoint).where(
                CloudServiceEndpoint.provider == CloudServiceProvider(provider),
                CloudServiceEndpoint.region == region,
                CloudServiceEndpoint.is_active == True,
            )
            result = await db.execute(query.limit(1))
            cloud_service = result.scalar_one_or_none()

        # Find source devices matching the type
        source_types = flow_spec.get("source_types", [])
        for device_id, device in devices.items():
            device_type = device.get("type", "")
            if device_type not in source_types:
                continue

            link_index += 1
            link_id = f"migrated_csl_{link_index:03d}"

            if cloud_service:
                # Use matched cloud service endpoint
                cloud_links.append({
                    "id": link_id,
                    "device_id": device_id,
                    "cloud_service_id": str(cloud_service.id),
                    "heartbeat_interval_ms": interval_ms,
                    "enabled": True,
                    "cloud_service": {
                        "name": cloud_service.name,
                        "provider": cloud_service.provider.value,
                        "primary_ip": cloud_service.primary_ip,
                        "port": cloud_service.port,
                        "hostname": cloud_service.hostname,
                        "tls_enabled": cloud_service.tls_enabled,
                    },
                })
            else:
                # Custom/unknown external IP - create inline config
                cloud_links.append({
                    "id": link_id,
                    "device_id": device_id,
                    "cloud_service_id": None,  # No matching endpoint
                    "heartbeat_interval_ms": interval_ms,
                    "enabled": True,
                    "cloud_service": {
                        "name": f"External ({external_ip})",
                        "provider": "custom",
                        "primary_ip": external_ip,
                        "port": external_port,
                        "hostname": None,
                        "tls_enabled": True,
                    },
                })

            logger.debug(
                f"Migrated external flow to cloud link {link_id}: "
                f"{device_id} -> {external_ip}:{external_port}"
            )

    return cloud_links


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
