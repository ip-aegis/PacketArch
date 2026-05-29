# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cyber Vision routes for device discovery and comparison."""

import logging
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.exceptions import ExternalServiceError, NotFoundError, ValidationError

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.core.encryption import decrypt_value, encrypt_value
from app.models.scenario import Scenario
from app.models.settings import SystemSetting
from app.schemas.cyber_vision import (
    ComparisonInsight,
    CVComparisonResult,
    CVConnectionStatusResponse,
    CVDeviceListResponse,
    CVDeviceResponse,
    CVEnrichmentDeviceResult,
    CVEnrichmentRequest,
    CVEnrichmentResult,
    CVPresetListResponse,
    CVPresetResponse,
    CVSettingsResponse,
    CVSettingsUpdate,
    CVTestConnectionRequest,
    CVTestConnectionResponse,
    CVVulnerabilityListResponse,
    CVVulnerabilityResponse,
    DuplicateMacAnalysisResponse,
    MatchedDevice,
)
from app.services.cyber_vision_service import (
    CyberVisionService,
    CVDevice,
    analyze_duplicate_macs,
    deduplicate_by_mac,
    normalize_mac,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cyber-vision", tags=["Cyber Vision"])


async def get_cv_settings(db) -> tuple[str | None, str | None, bool]:
    """Get CV settings from database."""
    settings = {}
    result = await db.execute(
        select(SystemSetting).where(
            SystemSetting.key.in_([
                "cyber_vision_url",
                "cyber_vision_api_token",
                "cyber_vision_verify_ssl",
            ])
        )
    )
    for setting in result.scalars().all():
        if setting.key == "cyber_vision_api_token" and setting.value:
            settings[setting.key] = decrypt_value(setting.value)
        else:
            settings[setting.key] = setting.value

    url = settings.get("cyber_vision_url")
    token = settings.get("cyber_vision_api_token")
    verify_ssl = settings.get("cyber_vision_verify_ssl", "false").lower() == "true"

    return url, token, verify_ssl


async def get_cv_service(db) -> CyberVisionService:
    """Get a configured CV service instance."""
    url, token, verify_ssl = await get_cv_settings(db)

    if not url or not token:
        raise ValidationError("Cyber Vision is not configured. Please set URL and API token in settings.")

    return CyberVisionService(url, token, verify_ssl)


@router.get("/settings", response_model=CVSettingsResponse)
async def get_settings(
    db: DBSession,
    _admin: AdminUser,
) -> CVSettingsResponse:
    """Get Cyber Vision settings (token masked)."""
    url, token, verify_ssl = await get_cv_settings(db)

    return CVSettingsResponse(
        cyber_vision_url=url or "",
        cyber_vision_api_token_set=bool(token),
        cyber_vision_verify_ssl=verify_ssl,
    )


@router.put("/settings", response_model=CVSettingsResponse)
async def update_settings(
    update: CVSettingsUpdate,
    db: DBSession,
    admin: AdminUser,
) -> CVSettingsResponse:
    """Update Cyber Vision settings."""
    updates = {}

    if update.cyber_vision_url is not None:
        updates["cyber_vision_url"] = update.cyber_vision_url

    if update.cyber_vision_api_token is not None:
        updates["cyber_vision_api_token"] = encrypt_value(update.cyber_vision_api_token)

    if update.cyber_vision_verify_ssl is not None:
        updates["cyber_vision_verify_ssl"] = str(update.cyber_vision_verify_ssl).lower()

    for key, value in updates.items():
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()

        if setting is None:
            # Create new setting
            setting = SystemSetting(
                key=key,
                value=value,
                is_secret=(key == "cyber_vision_api_token"),
                category="cyber_vision",
                description=f"Cyber Vision {key.replace('cyber_vision_', '').replace('_', ' ')}",
            )
            db.add(setting)
        else:
            setting.value = value
            setting.updated_by_id = admin.id

    await db.commit()

    # Return updated settings
    return await get_settings(db, admin)


@router.get("/status", response_model=CVConnectionStatusResponse)
async def get_status(
    db: DBSession,
    _user: CurrentUser,
) -> CVConnectionStatusResponse:
    """Check Cyber Vision connection status."""
    try:
        service = await get_cv_service(db)
        result = await service.test_connection()
        await service.close()

        return CVConnectionStatusResponse(
            connected=result.success,
            message=result.message,
            version=result.version,
            center_name=result.center_name,
        )

    except (ValidationError, NotFoundError):
        # Re-raise typed exceptions (not configured)
        raise
    except Exception as e:
        logger.exception("Error checking CV status")
        return CVConnectionStatusResponse(
            connected=False,
            message=f"Connection error: {str(e)}",
        )


@router.post("/test-connection", response_model=CVTestConnectionResponse)
async def test_connection(
    request: CVTestConnectionRequest,
    _admin: AdminUser,
) -> CVTestConnectionResponse:
    """Test connection to Cyber Vision with provided credentials."""
    try:
        service = CyberVisionService(
            request.url,
            request.api_token,
            request.verify_ssl,
        )
        result = await service.test_connection()
        await service.close()

        return CVTestConnectionResponse(
            success=result.success,
            message=result.message,
            version=result.version,
        )

    except Exception as e:
        logger.exception("Error testing CV connection")
        return CVTestConnectionResponse(
            success=False,
            message=f"Connection error: {str(e)}",
        )


@router.get("/presets", response_model=CVPresetListResponse)
async def get_presets(
    db: DBSession,
    _user: CurrentUser,
) -> CVPresetListResponse:
    """Fetch available presets from Cyber Vision."""
    try:
        service = await get_cv_service(db)
        presets = await service.get_presets()
        await service.close()

        return CVPresetListResponse(
            items=[
                CVPresetResponse(id=str(p.get("id", "")), label=p.get("label", "Unknown"))
                for p in presets
            ]
        )

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.exception("Error fetching CV presets")
        raise ExternalServiceError(service="cyber_vision", message=f"Failed to fetch presets: {str(e)}", original_error=e)


@router.get("/devices", response_model=CVDeviceListResponse)
async def get_devices(
    db: DBSession,
    _user: CurrentUser,
    size: int = Query(default=100, ge=1, le=500, description="Number of devices per page"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    search: str | None = Query(default=None),
) -> CVDeviceListResponse:
    """Fetch devices from Cyber Vision."""
    try:
        service = await get_cv_service(db)
        devices = await service.get_devices(size=size, page=page)
        await service.close()

        # Merge duplicate MAC components (L2-only + L3 entries for the
        # same physical device) so the frontend never sees phantom no-IP
        # duplicates created by PROFINET Layer 2 traffic.
        devices = deduplicate_by_mac(devices)

        return CVDeviceListResponse(
            items=[
                CVDeviceResponse(
                    id=d.id,
                    name=d.name,
                    ip=d.ip,
                    mac=d.mac,
                    vendor=d.vendor,
                    model=d.model,
                    firmware=d.firmware,
                    category=d.category,
                    risk_score=d.risk_score,
                    first_seen=d.first_seen,
                    last_seen=d.last_seen,
                    group_name=d.group_name,
                )
                for d in devices
            ],
            total=len(devices),
        )

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.exception("Error fetching CV devices")
        raise ExternalServiceError(service="cyber_vision", message=f"Failed to fetch devices: {str(e)}", original_error=e)


@router.get("/duplicate-macs", response_model=DuplicateMacAnalysisResponse)
async def analyze_duplicate_mac_addresses(
    db: DBSession,
    _user: CurrentUser,
    preset_id: str | None = Query(
        default=None,
        description="Optional CV preset ID to filter devices",
    ),
) -> DuplicateMacAnalysisResponse:
    """Analyze all CV devices for duplicate MAC addresses.

    Fetches all devices (auto-paginating), groups by normalized MAC,
    and classifies duplicate groups by severity:
    - critical: Same MAC across different vendors (spoofing/misconfiguration)
    - high: Same MAC with different IPs (cloned device)
    - medium: Same MAC/IP but different names/models (data quality)
    - low: Nearly identical devices (multi-segment visibility)
    """
    try:
        service = await get_cv_service(db)
        all_devices = await service.get_all_devices(preset_id=preset_id)
        await service.close()

        result = analyze_duplicate_macs(all_devices)
        return DuplicateMacAnalysisResponse(**result)

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.exception("Error analyzing duplicate MACs")
        raise ExternalServiceError(
            service="cyber_vision",
            message=f"Failed to analyze duplicate MACs: {str(e)}",
            original_error=e,
        )


@router.get("/devices/{device_id}", response_model=CVDeviceResponse)
async def get_device(
    device_id: str,
    db: DBSession,
    _user: CurrentUser,
) -> CVDeviceResponse:
    """Get details for a specific CV device."""
    try:
        service = await get_cv_service(db)
        device = await service.get_device_details(device_id)
        await service.close()

        if device is None:
            raise NotFoundError("CV device", device_id)

        return CVDeviceResponse(
            id=device.id,
            name=device.name,
            ip=device.ip,
            mac=device.mac,
            vendor=device.vendor,
            model=device.model,
            firmware=device.firmware,
            category=device.category,
            risk_score=device.risk_score,
            first_seen=device.first_seen,
            last_seen=device.last_seen,
            group_name=device.group_name,
        )

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.exception(f"Error fetching CV device {device_id}")
        raise ExternalServiceError(service="cyber_vision", message=f"Failed to fetch device: {str(e)}", original_error=e)


@router.get("/vulnerabilities", response_model=CVVulnerabilityListResponse)
async def get_vulnerabilities(
    db: DBSession,
    _user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    severity: str | None = Query(default=None),
) -> CVVulnerabilityListResponse:
    """Fetch vulnerabilities from Cyber Vision."""
    try:
        service = await get_cv_service(db)
        vulnerabilities = await service.get_vulnerabilities(
            limit=limit, offset=offset, severity=severity
        )
        await service.close()

        return CVVulnerabilityListResponse(
            items=[
                CVVulnerabilityResponse(
                    id=v.id,
                    cve_id=v.cve_id,
                    title=v.title,
                    severity=v.severity,
                    cvss_score=v.cvss_score,
                    affected_device_count=v.affected_device_count,
                    description=v.description,
                )
                for v in vulnerabilities
            ],
            total=len(vulnerabilities),
        )

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.exception("Error fetching CV vulnerabilities")
        raise ExternalServiceError(service="cyber_vision", message=f"Failed to fetch vulnerabilities: {str(e)}", original_error=e)


def find_best_match(
    scenario_device: dict, cv_devices: list[CVDevice]
) -> tuple[CVDevice | None, float, str]:
    """Find the best matching CV device for a scenario device.

    Returns:
        Tuple of (matched_device, confidence, match_type)
    """
    # Extract network info - scenario devices store IP/MAC under "network" key
    network = scenario_device.get("network", {})
    device_ip = network.get("ipAddress") or scenario_device.get("ip")
    device_mac = normalize_mac(network.get("macAddress") or scenario_device.get("mac"))

    # Vendor and model info
    device_vendor = scenario_device.get("vendor", "").lower()
    device_model = (
        scenario_device.get("fingerprintModel", "")
        or scenario_device.get("model", "")
    ).lower()

    best_match = None
    best_confidence = 0.0
    best_match_type = ""

    for cv_device in cv_devices:
        cv_mac = normalize_mac(cv_device.mac)

        # MAC address match - highest confidence (MAC is globally unique)
        if device_mac and cv_mac and device_mac == cv_mac:
            return cv_device, 1.0, "mac"

        # Exact IP match - high confidence
        if device_ip and cv_device.ip and device_ip == cv_device.ip:
            if best_confidence < 0.95:
                best_match = cv_device
                best_confidence = 0.95
                best_match_type = "ip"
                continue

        # Vendor + Model match - medium confidence
        cv_vendor = (cv_device.vendor or "").lower()
        cv_model = (cv_device.model or "").lower()

        if device_vendor and cv_vendor:
            # Check if vendor matches (partial match okay)
            vendor_match = device_vendor in cv_vendor or cv_vendor in device_vendor

            if vendor_match and device_model and cv_model:
                # Both vendor and model match
                model_match = device_model in cv_model or cv_model in device_model
                if model_match and best_confidence < 0.8:
                    best_match = cv_device
                    best_confidence = 0.8
                    best_match_type = "vendor_model"
            elif vendor_match and best_confidence < 0.5:
                # Just vendor match
                best_match = cv_device
                best_confidence = 0.5
                best_match_type = "vendor"

    return best_match, best_confidence, best_match_type


# Protocols that require Layer 2 adjacency for CV discovery
LAYER2_ONLY_PROTOCOLS = {"profinet"}
# Protocols discoverable via IP traffic
IP_PROTOCOLS = {"modbus_tcp", "ethernet_ip", "s7comm", "bacnet", "snmp", "opc_ua", "dnp3", "iec_104"}


def generate_comparison_insights(
    scenario_devices: list[dict],
    matched_devices: list[MatchedDevice],
    scenario_only: list[dict],
    cv_only: list[CVDeviceResponse],
) -> list[ComparisonInsight]:
    """Generate actionable insights from comparison results."""
    insights: list[ComparisonInsight] = []
    total = len(scenario_devices)
    matched_count = len(matched_devices)

    # 1. Match summary (always)
    if total > 0:
        pct = round(matched_count / total * 100)
        insights.append(ComparisonInsight(
            category="match_quality",
            severity="info",
            message=f"CV discovered {matched_count} of {total} scenario devices ({pct}% match rate).",
        ))

    # 2. Layer 2 protocol visibility
    l2_devices = []
    for dev in scenario_only:
        protocols = {p.lower() for p in (dev.get("protocols") or [])}
        if protocols and protocols.issubset(LAYER2_ONLY_PROTOCOLS):
            l2_devices.append(dev.get("name", "Unknown"))

    if l2_devices:
        insights.append(ComparisonInsight(
            category="protocol_visibility",
            severity="warning",
            message=(
                f"{len(l2_devices)} device(s) use only Layer 2 protocols (e.g. PROFINET). "
                "CV sensors must be on the same VLAN/broadcast domain to discover these devices."
            ),
            affected_devices=l2_devices,
        ))

    # 3. Enrichment suggestion
    enrichable = [
        m for m in matched_devices
        if any(m.scenario_device.get(f) for f in ("vendor", "fingerprintModel", "model", "type", "role"))
    ]
    if enrichable:
        insights.append(ComparisonInsight(
            category="enrichment_suggestion",
            severity="suggestion",
            message=(
                f"{len(enrichable)} matched device(s) can be enriched with vendor, model, "
                "or type information from PacketArch."
            ),
        ))

    # 4. CV-only note
    if cv_only:
        insights.append(ComparisonInsight(
            category="match_quality",
            severity="info",
            message=(
                f"CV discovered {len(cv_only)} additional device(s) not represented in your scenario. "
                "These may be real network infrastructure or devices outside the simulation scope."
            ),
        ))

    return insights


@router.post("/compare/{scenario_id}", response_model=CVComparisonResult)
async def compare_scenario(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    preset_id: str | None = Query(default=None, description="Optional CV preset ID to filter devices"),
) -> CVComparisonResult:
    """Compare a scenario's devices against Cyber Vision discovered devices.

    Fetches all CV devices and builds lookup tables for MAC and IP matching.
    This is more reliable than the CV search API which returns inconsistent results.

    Args:
        preset_id: Optional preset ID to filter CV devices by preset
    """
    # Fetch the scenario
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise NotFoundError("Scenario", str(scenario_id))

    # Get scenario devices from definition
    scenario_definition = scenario.definition or {}
    scenario_devices = list(scenario_definition.get("devices", {}).values())

    try:
        service = await get_cv_service(db)

        # Fetch ALL CV devices and build lookup tables (optionally filtered by preset)
        all_cv_devices = await service.get_all_devices(preset_id=preset_id)
        logger.info(f"Fetched {len(all_cv_devices)} CV devices for comparison (preset_id={preset_id})")

        # Build MAC and IP lookup tables (normalized keys)
        mac_lookup: dict[str, CVDevice] = {}
        ip_lookup: dict[str, CVDevice] = {}

        for cv_device in all_cv_devices:
            # Add to MAC lookup (normalize: lowercase, colons)
            if cv_device.mac:
                norm_mac = cv_device.mac.lower().replace("-", ":").replace(".", ":")
                mac_lookup[norm_mac] = cv_device

            # Add to IP lookup
            if cv_device.ip:
                ip_lookup[cv_device.ip] = cv_device

        logger.info(f"Built lookup tables: {len(mac_lookup)} MACs, {len(ip_lookup)} IPs")

        # Match scenario devices against CV
        matched_devices = []
        scenario_only = []

        for s_device in scenario_devices:
            network = s_device.get("network", {})
            device_mac = network.get("macAddress", "")
            device_ip = network.get("ipAddress", "")

            cv_match = None
            match_type = ""
            confidence = 0.0

            # Try MAC first (globally unique, most reliable)
            if device_mac:
                norm_mac = device_mac.lower().replace("-", ":").replace(".", ":")
                cv_match = mac_lookup.get(norm_mac)
                if cv_match:
                    match_type = "mac"
                    confidence = 1.0
                    logger.info(f"Matched by MAC {device_mac}: {s_device.get('name')} -> {cv_match.name}")

            # If no MAC match, try IP
            if not cv_match and device_ip:
                cv_match = ip_lookup.get(device_ip)
                if cv_match:
                    match_type = "ip"
                    confidence = 0.95
                    logger.info(f"Matched by IP {device_ip}: {s_device.get('name')} -> {cv_match.name}")

            if cv_match:
                matched_devices.append(
                    MatchedDevice(
                        scenario_device=s_device,
                        cv_device=CVDeviceResponse(
                            id=cv_match.id,
                            name=cv_match.name,
                            ip=cv_match.ip,
                            mac=cv_match.mac,
                            vendor=cv_match.vendor,
                            model=cv_match.model,
                            firmware=cv_match.firmware,
                            category=cv_match.category,
                            risk_score=cv_match.risk_score,
                            first_seen=cv_match.first_seen,
                            last_seen=cv_match.last_seen,
                            group_name=cv_match.group_name,
                        ),
                        confidence=confidence,
                        match_type=match_type,
                    )
                )
            else:
                logger.debug(f"No CV match for {s_device.get('name')} (MAC: {device_mac}, IP: {device_ip})")
                scenario_only.append(s_device)

        await service.close()

        # Calculate match rate
        match_rate = len(matched_devices) / len(scenario_devices) if scenario_devices else 0.0

        # Build cv_only: CV devices not matched to any scenario device
        matched_cv_ids = {m.cv_device.id for m in matched_devices}
        cv_only = [
            CVDeviceResponse(
                id=cv_dev.id,
                name=cv_dev.name,
                ip=cv_dev.ip,
                mac=cv_dev.mac,
                vendor=cv_dev.vendor,
                model=cv_dev.model,
                firmware=cv_dev.firmware,
                category=cv_dev.category,
                risk_score=cv_dev.risk_score,
                first_seen=cv_dev.first_seen,
                last_seen=cv_dev.last_seen,
                group_name=cv_dev.group_name,
            )
            for cv_dev in all_cv_devices
            if cv_dev.id not in matched_cv_ids
        ]

        # Generate actionable insights
        insights = generate_comparison_insights(
            scenario_devices, matched_devices, scenario_only, cv_only,
        )

        logger.info(
            f"Comparison complete: {len(matched_devices)}/{len(scenario_devices)} matched "
            f"({match_rate*100:.0f}%), {len(cv_only)} CV-only, {len(insights)} insights"
        )

        return CVComparisonResult(
            scenario_id=str(scenario_id),
            scenario_name=scenario.name,
            scenario_device_count=len(scenario_devices),
            cv_device_count=len(all_cv_devices),
            matched_devices=matched_devices,
            scenario_only=scenario_only,
            cv_only=cv_only,
            match_rate=match_rate,
            insights=insights,
        )

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.exception("Error during CV comparison")
        raise ExternalServiceError(service="cyber_vision", message=f"Failed to compare with CV: {str(e)}", original_error=e)


@router.post("/enrich", response_model=CVEnrichmentResult)
async def enrich_devices(
    request: CVEnrichmentRequest,
    db: DBSession,
    _admin: AdminUser,
) -> CVEnrichmentResult:
    """Push PacketArch device data to Cyber Vision.

    Adds user properties to CV devices with PacketArch-known information
    such as vendor, model, firmware version, device type, etc.

    IMPORTANT: This endpoint fetches ALL devices from the main CV /devices endpoint
    and builds a MAC lookup table. This is necessary because preset visualization
    node IDs don't work with the /devices/{id}/usersProperties API - we need the
    real device IDs from the main endpoint.

    Requires admin privileges to write to Cyber Vision.
    """
    try:
        service = await get_cv_service(db)
        results = []
        success_count = 0
        failed_count = 0
        total_props = 0

        logger.info(f"Enrich request: {len(request.device_mappings)} devices, skip_existing={request.skip_existing}")

        # CRITICAL: Fetch ALL devices from main endpoint (not preset) and build MAC lookup
        # Preset visualization node IDs don't work with the usersProperties API
        logger.info("Building MAC lookup table from main CV devices endpoint...")
        all_cv_devices = await service.get_all_devices(preset_id=None)  # Main endpoint only
        logger.info(f"Fetched {len(all_cv_devices)} devices from main CV endpoint")

        # Build MAC -> device ID lookup (normalized: lowercase, colons)
        mac_to_device: dict[str, CVDevice] = {}
        ip_to_device: dict[str, CVDevice] = {}
        for cv_device in all_cv_devices:
            if cv_device.mac:
                norm_mac = cv_device.mac.lower().replace("-", ":").replace(".", ":")
                mac_to_device[norm_mac] = cv_device
            if cv_device.ip:
                ip_to_device[cv_device.ip] = cv_device

        logger.info(f"Built lookup tables: {len(mac_to_device)} MACs, {len(ip_to_device)} IPs")

        for mapping in request.device_mappings:
            cv_id = mapping.cv_device_id
            properties = mapping.properties

            # Resolve the device ID using MAC/IP lookup
            resolved_device = None
            resolution_method = "direct"

            # Try MAC first (most reliable)
            if mapping.cv_device_mac:
                norm_mac = mapping.cv_device_mac.lower().replace("-", ":").replace(".", ":")
                resolved_device = mac_to_device.get(norm_mac)
                if resolved_device:
                    resolution_method = f"MAC:{mapping.cv_device_mac}"

            # Try IP if MAC didn't work
            if not resolved_device and mapping.cv_device_ip:
                resolved_device = ip_to_device.get(mapping.cv_device_ip)
                if resolved_device:
                    resolution_method = f"IP:{mapping.cv_device_ip}"

            if not resolved_device:
                logger.warning(f"Could not resolve device {cv_id} (MAC: {mapping.cv_device_mac}, IP: {mapping.cv_device_ip}) - not found in main devices")
                results.append(
                    CVEnrichmentDeviceResult(
                        cv_device_id=cv_id,
                        status="failed",
                        error="Device not found in main CV devices (MAC/IP not matched)",
                    )
                )
                failed_count += 1
                continue

            # Use the resolved device's real ID
            real_device_id = resolved_device.id
            if real_device_id != cv_id:
                logger.info(f"Resolved device via {resolution_method}: {cv_id} -> {real_device_id}")

            logger.info(f"Enriching device {real_device_id} ({resolved_device.name}): properties={list(properties.keys())}")

            try:
                # Set device label/name if provided
                label_set = False
                if mapping.device_label:
                    try:
                        await service.set_device_label(real_device_id, mapping.device_label)
                        logger.info(f"Set device {real_device_id} label to '{mapping.device_label}'")
                        label_set = True
                    except Exception as e:
                        logger.warning(f"Failed to set label for device {real_device_id}: {e}")

                # Use the REAL device ID for enrichment (not the preset node ID)
                added = await service.enrich_device_direct(real_device_id, properties)

                # Include label in properties_added if it was set
                props_added = list(added.keys())
                if label_set:
                    props_added.insert(0, "_label")

                results.append(
                    CVEnrichmentDeviceResult(
                        cv_device_id=cv_id,
                        status="success",
                        properties_added=props_added,
                    )
                )
                success_count += 1
                total_props += len(added) + (1 if label_set else 0)
                logger.info(f"Enriched CV device {real_device_id} with {len(added)} properties" + (" + label" if label_set else ""))

            except Exception as e:
                logger.warning(f"Failed to enrich CV device {real_device_id}: {e}")
                results.append(
                    CVEnrichmentDeviceResult(
                        cv_device_id=cv_id,
                        status="failed",
                        error=str(e),
                    )
                )
                failed_count += 1

        await service.close()

        return CVEnrichmentResult(
            success_count=success_count,
            failed_count=failed_count,
            total_properties_added=total_props,
            results=results,
        )

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.exception("Error during CV enrichment")
        raise ExternalServiceError(service="cyber_vision", message=f"Failed to enrich CV devices: {str(e)}", original_error=e)


@router.get("/flows")
async def get_flows(
    db: DBSession,
    _user: CurrentUser,
    device_id: str | None = Query(default=None, description="Filter by device id"),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Fetch raw network flows from Cyber Vision.

    Returns CV's flow records with whatever fields CV provides — typically
    src/dst MAC, src/dst IP, protocol/service tags, packet/byte counts, and
    first/last activity timestamps. Used to verify *when* phantom or normal
    flows last had traffic (e.g. confirm clean_demo_mode actually stopped
    PN-IO by checking last-activity timestamps on suspicious flows).
    """
    try:
        service = await get_cv_service(db)
        flows = await service.get_flows(
            device_id=device_id, limit=limit, offset=offset
        )
        await service.close()
        return {"items": flows, "count": len(flows)}
    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.exception("Error fetching CV flows")
        raise ExternalServiceError(
            service="cyber_vision",
            message=f"Failed to fetch flows: {str(e)}",
            original_error=e,
        )
