"""Scenario routes for managing traffic simulation scenarios."""

import math
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from sqlalchemy import delete as sql_delete

from app.api.deps import CurrentUser, DBSession
from app.models.scenario import Scenario
from app.models.generation_job import GenerationJob
from app.models.traffic_agent import AgentDeployment
from app.models.remote_deployment import RemoteDeployment
from app.services.ip_management import IPManagementService
from app.services.learned_pattern_service import LearnedPatternService
from app.services.protocol_validator import validate_scenario_protocols
from app.services.serial_number_generator import SerialNumberGenerator
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioExport,
    ScenarioImport,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioSummaryResponse,
    ScenarioUpdate,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


def get_scenario_counts(definition: dict) -> tuple[int, int]:
    """Extract device and flow counts from scenario definition."""
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})
    return len(devices), len(flows)


def get_learned_pattern_info(definition: dict) -> tuple[bool, list[str]]:
    """Extract learned pattern information from scenario definition."""
    learned_info = definition.get("learned_patterns_applied", {})
    if learned_info:
        return True, learned_info.get("protocols_enhanced", [])
    return False, []


def ensure_device_serial_numbers(definition: dict, scenario_id: str) -> dict:
    """Ensure all devices in definition have unique serial numbers.

    Serial numbers are critical for Cyber Vision to correctly identify
    distinct devices. This function adds serial numbers to devices that
    have proper identity data but are missing serial numbers.

    IMPORTANT: Only enriches identities that ALREADY EXIST in the fingerprint
    with proper vendor data. Does NOT create new identity blocks, as that would
    cause protocol misattribution (e.g., Siemens appearing as Rockwell).

    Args:
        definition: Scenario definition dict
        scenario_id: Scenario UUID for deterministic generation

    Returns:
        Updated definition with serial numbers added
    """
    devices = definition.get("devices", {})
    if not devices:
        return definition

    # Handle both dict and list formats
    if isinstance(devices, dict):
        device_items = devices.items()
    else:
        device_items = [(d.get("id", f"device_{i}"), d) for i, d in enumerate(devices)]

    def identity_has_vendor_data(identity: dict | None, required_key: str) -> bool:
        """Check if identity has real vendor data, not just a serial number placeholder."""
        if not identity or not isinstance(identity, dict):
            return False
        # For EtherNet/IP, vendor_id is required to avoid defaulting to Rockwell
        if required_key == "vendor_id":
            return identity.get("vendor_id") is not None
        # For other protocols, check for any key besides serial_number
        return any(k != "serial_number" for k in identity.keys())

    for device_id, device in device_items:
        if not device_id or not device:
            continue

        fingerprint = device.get("vendorFingerprint") or device.get("vendor_fingerprint") or {}
        protocols = device.get("protocols", []) or []
        modified = False

        # EtherNet/IP - ONLY enrich if protocol declared AND identity has vendor_id
        if "ethernet_ip" in protocols:
            existing_identity = fingerprint.get("ethernet_ip_identity")
            if identity_has_vendor_data(existing_identity, "vendor_id"):
                if not existing_identity.get("serial_number"):
                    existing_identity["serial_number"] = SerialNumberGenerator.generate_ethernet_ip(device_id, scenario_id)
                    modified = True

        # S7comm - enrich if protocol declared AND identity exists with data
        if "s7comm" in protocols or "s7comm_plus" in protocols:
            existing_identity = fingerprint.get("s7_identity")
            if identity_has_vendor_data(existing_identity, "order_code"):
                if not existing_identity.get("serial_number"):
                    existing_identity["serial_number"] = SerialNumberGenerator.generate_s7(device_id, scenario_id)
                    modified = True

        # PROFINET - enrich if protocol declared AND identity exists with data
        if "profinet" in protocols or "profisafe" in protocols:
            existing_identity = fingerprint.get("profinet_identity")
            if identity_has_vendor_data(existing_identity, "vendor_id"):
                if not existing_identity.get("serial_number"):
                    serial = SerialNumberGenerator.generate_profinet(device_id, scenario_id)
                    existing_identity["serial_number"] = serial
                    existing_identity["im0_serial_number"] = serial
                    modified = True

        # Modbus - enrich if protocol declared AND identity exists with data
        if "modbus_tcp" in protocols or "modbus" in protocols:
            existing_identity = fingerprint.get("modbus_identity")
            if identity_has_vendor_data(existing_identity, "vendor_name"):
                if not existing_identity.get("serial_number"):
                    existing_identity["serial_number"] = SerialNumberGenerator.generate_s7(device_id, scenario_id)
                    modified = True

        # BACnet - enrich if protocol declared AND identity exists with data
        if "bacnet" in protocols:
            existing_identity = fingerprint.get("bacnet_identity")
            if identity_has_vendor_data(existing_identity, "vendor_id"):
                if not existing_identity.get("serial_number"):
                    existing_identity["serial_number"] = SerialNumberGenerator.generate_s7(device_id, scenario_id)
                    modified = True

        # SNMP - enrich if protocol declared AND identity exists with data
        if "snmp" in protocols:
            existing_identity = fingerprint.get("snmp_identity")
            if identity_has_vendor_data(existing_identity, "sys_descr"):
                if not existing_identity.get("serial_number"):
                    existing_identity["serial_number"] = SerialNumberGenerator.generate_s7(device_id, scenario_id)
                    modified = True

        # OPC UA - enrich if protocol declared AND identity exists with data
        if "opc_ua" in protocols:
            existing_identity = fingerprint.get("opc_ua_identity")
            if identity_has_vendor_data(existing_identity, "manufacturer_name"):
                if not existing_identity.get("serial_number"):
                    existing_identity["serial_number"] = SerialNumberGenerator.generate_s7(device_id, scenario_id)
                    modified = True

        if modified:
            device["vendorFingerprint"] = fingerprint
            device["vendor_fingerprint"] = fingerprint

    return definition


@router.get("", response_model=ScenarioListResponse)
async def list_scenarios(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    vertical: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> ScenarioListResponse:
    """List scenarios with filtering and pagination."""
    query = select(Scenario).where(Scenario.user_id == current_user.id)

    # Apply filters
    if vertical:
        query = query.where(Scenario.vertical == vertical)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            Scenario.name.ilike(search_filter)
            | Scenario.description.ilike(search_filter)
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Scenario.updated_at.desc())

    result = await db.execute(query)
    scenarios = result.scalars().all()

    # Build summary responses with counts
    items = []
    for s in scenarios:
        definition = s.definition or {}
        device_count, flow_count = get_scenario_counts(definition)
        has_learned_patterns, protocols_enhanced = get_learned_pattern_info(definition)
        items.append(ScenarioSummaryResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            vertical=s.vertical,
            total_duration_ms=s.total_duration_ms,
            version=s.version,
            device_count=device_count,
            flow_count=flow_count,
            has_learned_patterns=has_learned_patterns,
            protocols_enhanced=protocols_enhanced,
            created_at=s.created_at,
            updated_at=s.updated_at,
        ))

    return ScenarioListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ScenarioResponse:
    """Get a scenario by ID."""
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    return ScenarioResponse.model_validate(scenario)


@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    scenario_data: ScenarioCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> ScenarioResponse:
    """Create a new scenario with auto-allocated IP range."""
    scenario = Scenario(
        user_id=current_user.id,
        name=scenario_data.name,
        description=scenario_data.description,
        vertical=scenario_data.vertical,
        total_duration_ms=scenario_data.total_duration_ms,
        definition=scenario_data.definition,
        addressing_config=scenario_data.addressing_config,
        version=1,
    )

    db.add(scenario)
    await db.flush()  # Get scenario ID before allocating IP range

    # Allocate IP range for this scenario
    try:
        allocation = await IPManagementService.allocate_range(db, scenario.id)
        # Store range info in addressing_config
        scenario.addressing_config = {
            **(scenario.addressing_config or {}),
            "ip_range": allocation.cidr_range,
            "range_index": allocation.range_index,
            "auto_assign_enabled": True,
        }
    except ValueError as e:
        # No IP ranges available - proceed without allocation
        pass

    # CRITICAL: Ensure all devices have unique serial numbers
    # This prevents Cyber Vision from merging devices with same fingerprint
    if scenario.definition:
        scenario.definition = ensure_device_serial_numbers(
            scenario.definition, str(scenario.id)
        )

    await db.commit()
    await db.refresh(scenario)

    return ScenarioResponse.model_validate(scenario)


@router.put("/{scenario_id}", response_model=ScenarioResponse)
@router.patch("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: UUID,
    scenario_data: ScenarioUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> ScenarioResponse:
    """Update a scenario (supports both PUT and PATCH)."""
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Update fields
    update_data = scenario_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scenario, field, value)

    # If definition was updated, ensure all devices have serial numbers
    if "definition" in update_data and scenario.definition:
        scenario.definition = ensure_device_serial_numbers(
            scenario.definition, str(scenario.id)
        )

    # Increment version
    scenario.version += 1
    scenario.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(scenario)

    return ScenarioResponse.model_validate(scenario)


@router.delete("/{scenario_id}", response_model=MessageResponse)
async def delete_scenario(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    force: bool = Query(False, description="Force delete, removing all dependencies"),
) -> MessageResponse:
    """Delete a scenario.

    If the scenario has active deployments or generation jobs, the delete will fail
    unless force=true is specified, which will stop deployments and remove all
    related records first.
    """
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Check for active agent deployments
    active_agent_deployments = await db.execute(
        select(func.count()).select_from(AgentDeployment).where(
            AgentDeployment.scenario_id == scenario_id,
            AgentDeployment.state.in_(["running", "starting", "stopping"]),
        )
    )
    active_agent_count = active_agent_deployments.scalar() or 0

    # Check for active docker deployments
    active_docker_deployments = await db.execute(
        select(func.count()).select_from(RemoteDeployment).where(
            RemoteDeployment.scenario_id == scenario_id,
            RemoteDeployment.status.in_(["running", "starting", "stopping"]),
        )
    )
    active_docker_count = active_docker_deployments.scalar() or 0

    # Check for generation jobs
    generation_jobs_result = await db.execute(
        select(func.count()).select_from(GenerationJob).where(
            GenerationJob.scenario_id == scenario_id,
        )
    )
    generation_job_count = generation_jobs_result.scalar() or 0

    # If there are active deployments and not forcing, return error with details
    if (active_agent_count > 0 or active_docker_count > 0) and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Cannot delete scenario with active deployments",
                "active_agent_deployments": active_agent_count,
                "active_docker_deployments": active_docker_count,
                "hint": "Stop deployments first or use force=true to force delete",
            },
        )

    # Clean up dependencies
    if force or generation_job_count > 0:
        # Delete generation jobs
        await db.execute(
            sql_delete(GenerationJob).where(GenerationJob.scenario_id == scenario_id)
        )

    if force:
        # Delete all agent deployments (including stopped ones)
        await db.execute(
            sql_delete(AgentDeployment).where(AgentDeployment.scenario_id == scenario_id)
        )
        # Delete all docker deployments (including stopped ones)
        await db.execute(
            sql_delete(RemoteDeployment).where(RemoteDeployment.scenario_id == scenario_id)
        )

    # Now delete the scenario
    await db.delete(scenario)
    await db.commit()

    cleanup_msg = ""
    if force and (active_agent_count > 0 or active_docker_count > 0 or generation_job_count > 0):
        cleanup_msg = f" (cleaned up {generation_job_count} generation jobs, {active_agent_count + active_docker_count} deployments)"

    return MessageResponse(message=f"Scenario deleted successfully{cleanup_msg}")


class BulkDeleteRequest(BaseModel):
    """Request for bulk delete."""
    scenario_ids: list[UUID]


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete."""
    deleted: int
    message: str


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_scenarios(
    request: BulkDeleteRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> BulkDeleteResponse:
    """Delete multiple scenarios at once.

    Only deletes scenarios owned by the current user.
    Returns the count of actually deleted scenarios.
    """
    if not request.scenario_ids:
        return BulkDeleteResponse(deleted=0, message="No scenarios specified")

    # Delete scenarios that belong to the current user
    result = await db.execute(
        sql_delete(Scenario).where(
            Scenario.id.in_(request.scenario_ids),
            Scenario.user_id == current_user.id,
        )
    )
    # Note: commit handled by get_db dependency

    deleted_count = result.rowcount
    return BulkDeleteResponse(
        deleted=deleted_count,
        message=f"Successfully deleted {deleted_count} scenario(s)",
    )


@router.post("/{scenario_id}/duplicate", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_scenario(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    new_name: str | None = Query(default=None, min_length=1, max_length=255),
) -> ScenarioResponse:
    """Duplicate a scenario with a new name and new IP allocation."""
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Use provided name or generate a copy name
    final_name = new_name if new_name else f"{scenario.name} (Copy)"

    # Deep copy the definition to avoid modifying the original
    import copy
    definition = copy.deepcopy(scenario.definition or {})

    # Create a new scenario with empty definition (will be populated after IP allocation)
    new_scenario = Scenario(
        user_id=current_user.id,
        name=final_name,
        description=scenario.description,
        vertical=scenario.vertical,
        total_duration_ms=scenario.total_duration_ms,
        definition={},  # Will be set after IP range allocation
        addressing_config=None,
        version=1,
    )

    db.add(new_scenario)
    await db.flush()  # Get scenario ID before allocating IP range

    # Allocate new IP range for duplicated scenario
    allocation = None
    try:
        allocation = await IPManagementService.allocate_range(db, new_scenario.id)
        new_scenario.addressing_config = {
            "ip_range": allocation.cidr_range,
            "range_index": allocation.range_index,
            "auto_assign_enabled": True,
        }
    except ValueError:
        pass

    # Reassign all device IPs based on new allocation
    definition = _reassign_device_ips(definition, allocation)
    new_scenario.definition = definition

    await db.commit()
    await db.refresh(new_scenario)

    return ScenarioResponse.model_validate(new_scenario)


@router.get("/{scenario_id}/export", response_model=ScenarioExport)
async def export_scenario(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ScenarioExport:
    """Export a scenario as JSON."""
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    return ScenarioExport(
        name=scenario.name,
        description=scenario.description,
        vertical=scenario.vertical,
        total_duration_ms=scenario.total_duration_ms,
        definition=scenario.definition,
        addressing_config=scenario.addressing_config,
        version=scenario.version,
        exported_at=datetime.now(timezone.utc),
    )


class ValidationWarning(BaseModel):
    """A single validation warning."""
    code: str
    severity: str  # "warning" or "error"
    message: str
    details: str | None = None


class ScenarioValidationResponse(BaseModel):
    """Response from scenario validation."""
    scenario_id: str
    is_valid: bool
    warnings: list[ValidationWarning]
    device_count: int
    flow_count: int
    protocols_used: list[str]


@router.get("/{scenario_id}/validate", response_model=ScenarioValidationResponse)
async def validate_scenario(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ScenarioValidationResponse:
    """Validate a scenario before deployment.

    Checks for common issues like:
    - Devices with no flows
    - Missing IP addresses
    - Protocol mismatches
    """
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    warnings: list[ValidationWarning] = []
    definition = scenario.definition or {}
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    # Track which devices have flows
    devices_with_flows = set()
    protocols_used = set()

    # Analyze flows
    for flow_id, flow in flows.items():
        # Support both camelCase (from templates) and snake_case (legacy)
        source_id = flow.get("sourceDeviceId") or flow.get("source_device_id")
        target_id = flow.get("targetDeviceId") or flow.get("target_device_id")
        protocol = flow.get("protocol")

        if source_id:
            devices_with_flows.add(source_id)
        if target_id:
            devices_with_flows.add(target_id)
        if protocol:
            protocols_used.add(protocol)

        # Check for missing endpoints
        # External flows (EWON Talk2M, etc.) have no target device - they target external IPs
        flow_config = flow.get("config", {})
        is_external_flow = flow_config.get("external", False)

        if not source_id:
            warnings.append(ValidationWarning(
                code="incomplete_flow",
                severity="error",
                message=f"Flow is missing source device",
                details=f"Flow ID: {flow_id}",
            ))
        elif not target_id and not is_external_flow:
            # Only error if target is missing AND it's not an external flow
            warnings.append(ValidationWarning(
                code="incomplete_flow",
                severity="error",
                message=f"Flow is missing target device",
                details=f"Flow ID: {flow_id}",
            ))

    # Check devices
    for device_id, device in devices.items():
        device_name = device.get("name", device_id)

        # Check for devices with no flows
        if device_id not in devices_with_flows:
            warnings.append(ValidationWarning(
                code="orphan_device",
                severity="warning",
                message=f"Device '{device_name}' has no flows",
                details="This device won't generate any traffic",
            ))

        # Check for missing IP addresses (support both formats)
        network = device.get("network", {})
        ip_address = network.get("ipAddress") or network.get("ip_address") or device.get("ip_address")
        if not ip_address:
            warnings.append(ValidationWarning(
                code="missing_ip",
                severity="warning",
                message=f"Device '{device_name}' has no IP address",
                details="Consider enabling auto-assign or setting manually",
            ))

    # Check protocol/fingerprint consistency
    # This prevents issues like Siemens devices appearing as Rockwell in Cyber Vision
    protocol_issues = validate_scenario_protocols(definition)
    for issue in protocol_issues:
        warnings.append(ValidationWarning(
            code="protocol_identity_mismatch",
            severity=issue.get("severity", "warning"),
            message=f"Device '{issue['device_name']}': {issue['issue']}",
            details=issue.get("recommendation"),
        ))

    # Check for duplicate device names (critical for SNMP sysName uniqueness)
    from collections import Counter
    device_names = [d.get("name", did) for did, d in devices.items()]
    name_counts = Counter(device_names)
    duplicates = {name: cnt for name, cnt in name_counts.items() if cnt > 1}
    for name, count in duplicates.items():
        warnings.append(ValidationWarning(
            code="duplicate_device_name",
            severity="error",
            message=f"Device name '{name}' is used {count} times",
            details="Each device must have a unique name for proper SNMP/protocol identification",
        ))

    # Check for duplicate MAC addresses
    mac_addresses = []
    for device_id, device in devices.items():
        network = device.get("network", {})
        mac = network.get("macAddress") or network.get("mac_address")
        if mac:
            mac_addresses.append((mac.upper(), device.get("name", device_id)))
    mac_counts = Counter(mac for mac, _ in mac_addresses)
    duplicate_macs = {mac: cnt for mac, cnt in mac_counts.items() if cnt > 1}
    for mac, count in duplicate_macs.items():
        device_names_with_mac = [name for m, name in mac_addresses if m.upper() == mac]
        warnings.append(ValidationWarning(
            code="duplicate_mac_address",
            severity="error",
            message=f"MAC address '{mac}' is used {count} times",
            details=f"Devices: {', '.join(device_names_with_mac)}",
        ))

    # Check for empty scenario
    if len(devices) == 0:
        warnings.append(ValidationWarning(
            code="no_devices",
            severity="error",
            message="Scenario has no devices",
            details="Add devices to generate traffic",
        ))

    if len(flows) == 0:
        warnings.append(ValidationWarning(
            code="no_flows",
            severity="error",
            message="Scenario has no flows",
            details="Add flows to define traffic patterns",
        ))

    # Determine if valid (no errors, warnings are ok)
    has_errors = any(w.severity == "error" for w in warnings)

    return ScenarioValidationResponse(
        scenario_id=str(scenario_id),
        is_valid=not has_errors,
        warnings=warnings,
        device_count=len(devices),
        flow_count=len(flows),
        protocols_used=list(protocols_used),
    )


class RepairProtocolsResponse(BaseModel):
    """Response from protocol repair operation."""
    scenario_id: str
    devices_fixed: int
    protocols_removed: list[dict]
    message: str


@router.post("/{scenario_id}/repair-protocols", response_model=RepairProtocolsResponse)
async def repair_scenario_protocols(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> RepairProtocolsResponse:
    """Repair protocol assignments by removing protocols without fingerprint support.

    This endpoint fixes existing scenarios that have protocol_identity_mismatch errors.
    It removes protocols from devices that don't have the corresponding identity data
    in their fingerprint.

    Args:
        scenario_id: The scenario to repair
        db: Database session
        current_user: Authenticated user

    Returns:
        Summary of repairs made
    """
    from app.services.vendor_fingerprints import get_fingerprint_by_vendor_model
    from app.services.protocol_validator import (
        get_protocol_identity_key,
        identity_has_vendor_data,
    )

    # Get scenario
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    definition = scenario.definition or {}
    devices = definition.get("devices", {})

    devices_fixed = 0
    protocols_removed: list[dict] = []

    for device_id, device in devices.items():
        device_name = device.get("name", device_id)
        vendor = (device.get("vendor") or "").lower()
        fingerprint_model = device.get("fingerprint_model")
        protocols = device.get("protocols", []) or []

        if not protocols:
            continue

        # Get fingerprint data
        fingerprint = (
            device.get("vendorFingerprint")
            or device.get("vendor_fingerprint")
            or device.get("fingerprint")
            or {}
        )

        # If no fingerprint in device, try to look it up
        if not fingerprint and vendor and fingerprint_model:
            fingerprint = get_fingerprint_by_vendor_model(vendor, fingerprint_model) or {}

        # Filter protocols
        validated_protocols = []
        removed_from_device = []

        for protocol in protocols:
            identity_key = get_protocol_identity_key(protocol)
            if identity_key:
                identity = fingerprint.get(identity_key)
                if identity_has_vendor_data(identity, identity_key):
                    validated_protocols.append(protocol)
                else:
                    removed_from_device.append(protocol)
            else:
                validated_protocols.append(protocol)

        if removed_from_device:
            devices_fixed += 1
            device["protocols"] = validated_protocols
            protocols_removed.append({
                "device_id": device_id,
                "device_name": device_name,
                "removed": removed_from_device,
                "remaining": validated_protocols,
            })

    # Save changes if any
    if devices_fixed > 0:
        scenario.definition = definition
        await db.commit()

    return RepairProtocolsResponse(
        scenario_id=str(scenario_id),
        devices_fixed=devices_fixed,
        protocols_removed=protocols_removed,
        message=f"Fixed {devices_fixed} devices, removed {sum(len(p['removed']) for p in protocols_removed)} protocol assignments",
    )


@router.post("/import", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def import_scenario(
    scenario_data: ScenarioImport,
    db: DBSession,
    current_user: CurrentUser,
) -> ScenarioResponse:
    """Import a scenario from JSON with new IP range allocation."""
    import copy

    # Deep copy the definition to allow modification
    definition = copy.deepcopy(scenario_data.definition or {})

    scenario = Scenario(
        user_id=current_user.id,
        name=scenario_data.name,
        description=scenario_data.description,
        vertical=scenario_data.vertical,
        total_duration_ms=scenario_data.total_duration_ms,
        definition={},  # Will be set after IP range allocation
        addressing_config=None,
        version=1,
    )

    db.add(scenario)
    await db.flush()  # Get scenario ID before allocating IP range

    # Allocate new IP range for imported scenario
    allocation = None
    try:
        allocation = await IPManagementService.allocate_range(db, scenario.id)
        scenario.addressing_config = {
            "ip_range": allocation.cidr_range,
            "range_index": allocation.range_index,
            "auto_assign_enabled": True,
        }
    except ValueError:
        pass

    # Reassign all device IPs based on new allocation
    definition = _reassign_device_ips(definition, allocation)
    scenario.definition = definition

    await db.commit()
    await db.refresh(scenario)

    return ScenarioResponse.model_validate(scenario)


# ========== Pattern Integration Endpoints ==========


class DevicePatternSuggestion(BaseModel):
    """Pattern suggestions for a single device."""
    device_id: str
    device_name: str
    device_type: str
    protocol: str
    suggestions: dict


class ScenarioPatternSuggestionsResponse(BaseModel):
    """Response for scenario pattern suggestions."""
    scenario_id: str
    scenario_name: str
    device_suggestions: list[DevicePatternSuggestion]
    total_patterns_available: int


class ApplyPatternsRequest(BaseModel):
    """Request to apply patterns to a scenario."""
    device_pattern_mappings: list[dict]  # [{device_id, fingerprint_id, pattern_id, sequence_ids}]
    apply_timing: bool = True
    apply_fingerprints: bool = True
    apply_sequences: bool = False


class ApplyPatternsResponse(BaseModel):
    """Response from applying patterns."""
    scenario_id: str
    devices_updated: int
    patterns_applied: int
    message: str


@router.get("/{scenario_id}/pattern-suggestions", response_model=ScenarioPatternSuggestionsResponse)
async def get_pattern_suggestions(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ScenarioPatternSuggestionsResponse:
    """Get pattern suggestions for all devices in a scenario.

    Analyzes each device's type and protocol to find matching learned patterns
    from the PCAP learning system.
    """
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    definition = scenario.definition or {}
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    # Build device -> protocol mapping from flows
    device_protocols: dict[str, set[str]] = {}
    for flow in flows.values():
        source_id = flow.get("sourceDeviceId") or flow.get("source_device_id")
        target_id = flow.get("targetDeviceId") or flow.get("target_device_id")
        protocol = flow.get("protocol", "").lower()

        if protocol:
            if source_id:
                device_protocols.setdefault(source_id, set()).add(protocol)
            if target_id:
                device_protocols.setdefault(target_id, set()).add(protocol)

    # Get suggestions for each device
    device_suggestions = []
    total_patterns = 0

    for device_id, device in devices.items():
        device_name = device.get("name", device_id)
        device_type = device.get("type", "plc").lower()
        protocols = device_protocols.get(device_id, set())

        # Get suggestions for each protocol this device uses
        for protocol in protocols:
            suggestions = await LearnedPatternService.suggest_patterns_for_device(
                db, device_type, protocol
            )

            # Count available patterns
            pattern_count = (
                len(suggestions["suggestions"].get("protocol_patterns", []))
                + len(suggestions["suggestions"].get("fingerprints", []))
                + len(suggestions["suggestions"].get("sequences", []))
            )
            total_patterns += pattern_count

            device_suggestions.append(DevicePatternSuggestion(
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                protocol=protocol,
                suggestions=suggestions["suggestions"],
            ))

    return ScenarioPatternSuggestionsResponse(
        scenario_id=str(scenario_id),
        scenario_name=scenario.name,
        device_suggestions=device_suggestions,
        total_patterns_available=total_patterns,
    )


@router.post("/{scenario_id}/apply-patterns", response_model=ApplyPatternsResponse)
async def apply_patterns(
    scenario_id: UUID,
    request: ApplyPatternsRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> ApplyPatternsResponse:
    """Apply learned patterns to devices in a scenario.

    Updates the scenario definition with realistic timing, fingerprints,
    and sequences from the PCAP learning system.
    """
    from app.models.device_template import DeviceTemplate, TemplateSource
    from app.models.learned_protocol_pattern import LearnedProtocolPattern
    from app.models.learned_sequence import LearnedSequence
    import uuid as uuid_module

    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    definition = scenario.definition or {}
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    devices_updated = 0
    patterns_applied = 0

    for mapping in request.device_pattern_mappings:
        device_id = mapping.get("device_id")
        if not device_id or device_id not in devices:
            continue

        device = devices[device_id]

        # Apply fingerprint to device
        if request.apply_fingerprints and mapping.get("fingerprint_id"):
            try:
                fp_result = await db.execute(
                    select(DeviceTemplate).where(
                        DeviceTemplate.id == uuid_module.UUID(mapping["fingerprint_id"]),
                        DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
                    )
                )
                fingerprint = fp_result.scalar_one_or_none()

                if fingerprint:
                    # Add learned fingerprint data to device
                    device["learned_fingerprint"] = {
                        "source_id": str(fingerprint.id),
                        "tcp_signature": fingerprint.tcp_signature,
                        "response_timings": fingerprint.response_timings,
                        "inferred_vendor": fingerprint.vendor,
                    }
                    patterns_applied += 1
            except Exception:
                pass

        # Apply protocol pattern timing to flows
        if request.apply_timing and mapping.get("pattern_id"):
            try:
                pattern_result = await db.execute(
                    select(LearnedProtocolPattern).where(
                        LearnedProtocolPattern.id == uuid_module.UUID(mapping["pattern_id"])
                    )
                )
                pattern = pattern_result.scalar_one_or_none()

                if pattern:
                    # Find flows involving this device and update them
                    for flow_id, flow in flows.items():
                        source_id = flow.get("sourceDeviceId") or flow.get("source_device_id")
                        target_id = flow.get("targetDeviceId") or flow.get("target_device_id")

                        if source_id == device_id or target_id == device_id:
                            # Add learned pattern data to flow
                            flow["learned_pattern"] = {
                                "source_id": str(pattern.id),
                                "function_codes": pattern.function_codes,
                                "address_patterns": pattern.address_patterns,
                                "timing_distributions": pattern.timing_distributions,
                            }
                            patterns_applied += 1
            except Exception:
                pass

        # Apply sequences
        if request.apply_sequences and mapping.get("sequence_ids"):
            sequence_data = []
            for seq_id in mapping.get("sequence_ids", []):
                try:
                    seq_result = await db.execute(
                        select(LearnedSequence).where(
                            LearnedSequence.id == uuid_module.UUID(seq_id)
                        )
                    )
                    sequence = seq_result.scalar_one_or_none()

                    if sequence:
                        sequence_data.append({
                            "source_id": str(sequence.id),
                            "name": sequence.name,
                            "sequence_type": str(sequence.sequence_type),
                            "steps": sequence.steps,
                            "step_count": sequence.step_count,
                        })
                        patterns_applied += 1
                except Exception:
                    pass

            if sequence_data:
                device["learned_sequences"] = sequence_data

        devices_updated += 1

    # Update scenario definition
    definition["devices"] = devices
    definition["flows"] = flows
    scenario.definition = definition
    scenario.version += 1
    scenario.updated_at = datetime.now(timezone.utc)
    # Note: commit handled by get_db dependency

    return ApplyPatternsResponse(
        scenario_id=str(scenario_id),
        devices_updated=devices_updated,
        patterns_applied=patterns_applied,
        message=f"Applied {patterns_applied} patterns to {devices_updated} devices",
    )


# ========== AI Device Naming ==========


class RegenerateNamesRequest(BaseModel):
    """Request to regenerate device names with AI."""

    process_context: str = Field(
        ...,
        description="Industrial process description for AI naming (e.g., 'candy factory', 'dairy processing')",
        min_length=3,
        max_length=200,
    )


class RegenerateNamesResponse(BaseModel):
    """Response after regenerating device names."""

    scenario_id: str
    devices_renamed: int
    message: str


@router.post("/{scenario_id}/regenerate-names", response_model=RegenerateNamesResponse)
async def regenerate_device_names(
    scenario_id: UUID,
    request: RegenerateNamesRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> RegenerateNamesResponse:
    """Regenerate device names using AI for an existing scenario.

    Uses the scenario's vertical and description, combined with user-provided
    process context, to generate meaningful, process-aware device names.
    This transforms generic names like "PLC-MAIN-01" into contextual names
    like "Chocolate_Tempering_PLC" (if process_context is "candy factory").

    Args:
        scenario_id: Scenario UUID
        request: Request body containing process_context (required)

    Returns:
        Summary of devices renamed
    """
    from app.ai_services.device_namer import AIDeviceNamer, DeviceNamingContext
    from app.mcp_server.ai_providers import AIProviderFactory

    # Get scenario
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    definition = scenario.definition or {}
    devices = definition.get("devices", {})
    zones = definition.get("zones", {})

    if not devices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scenario has no devices to rename",
        )

    # Get AI provider
    try:
        ai_provider = await AIProviderFactory.create(db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI provider not configured: {e}. Configure API key in Settings.",
        )

    # Build naming context from scenario metadata and user-provided process context
    context = DeviceNamingContext(
        vertical=scenario.vertical or "manufacturing",
        template_name=scenario.name,
        template_description=scenario.description or "",
        zones=zones,
        process_context=request.process_context,
    )

    # Convert devices dict to list
    device_list = list(devices.values())

    # Regenerate names with AI
    namer = AIDeviceNamer()
    try:
        enhanced_devices = await namer.enhance_device_names(
            devices=device_list,
            context=context,
            ai_provider=ai_provider,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI naming failed: {e}",
        )

    # Rebuild devices dict with enhanced names
    definition["devices"] = {d["id"]: d for d in enhanced_devices}

    # Update scenario
    scenario.definition = definition
    scenario.version += 1
    scenario.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(scenario)

    return RegenerateNamesResponse(
        scenario_id=str(scenario_id),
        devices_renamed=len(enhanced_devices),
        message=f"Successfully regenerated names for {len(enhanced_devices)} devices using AI",
    )


# ========== IP Reassignment Helper ==========


def _reassign_device_ips(definition: dict, allocation) -> dict:
    """Reassign all device IPs based on new IP range allocation.

    Updates zone subnets and device IPs to use the newly allocated range.
    This is used when duplicating or importing scenarios to ensure
    each scenario has unique IPs within its allocated range.

    Args:
        definition: Scenario definition dictionary
        allocation: IPRangeAllocation object (or None if no allocation)

    Returns:
        Modified definition dictionary with reassigned IPs
    """
    if not allocation:
        return definition

    range_idx = allocation.range_index
    zones = definition.get("zones", {})
    devices = definition.get("devices", {})

    # Update zone subnets based on allocation
    for zone_id, zone in zones.items():
        network = zone.get("network", {})
        subnet_offset = network.get("subnet_offset")

        if subnet_offset is not None:
            # Use subnet_offset to derive new subnet
            network["subnet"] = f"10.{range_idx}.{subnet_offset}.0/24"
        else:
            # Try to preserve zone order by using zone index
            zone_keys = list(zones.keys())
            zone_index = zone_keys.index(zone_id) if zone_id in zone_keys else 0
            network["subnet"] = f"10.{range_idx}.{zone_index}.0/24"
            network["subnet_offset"] = zone_index

        zone["network"] = network

    # Group devices by zone
    devices_by_zone: dict[str, list[str]] = {}
    for device_id, device in devices.items():
        zone_id = device.get("zoneId", "default")
        if zone_id not in devices_by_zone:
            devices_by_zone[zone_id] = []
        devices_by_zone[zone_id].append(device_id)

    # Reassign device IPs within each zone
    for zone_id, device_ids in devices_by_zone.items():
        zone = zones.get(zone_id, {})
        network = zone.get("network", {})
        subnet_offset = network.get("subnet_offset", 0)

        # Base IP for this zone: 10.{range_idx}.{subnet_offset}.x
        base = f"10.{range_idx}.{subnet_offset}"

        # Assign IPs starting at .10
        for i, device_id in enumerate(device_ids, start=10):
            device = devices[device_id]
            dev_network = device.get("network", {})
            dev_network["ipAddress"] = f"{base}.{i}"
            dev_network["subnetMask"] = "255.255.255.0"
            dev_network["gateway"] = f"{base}.1"
            dev_network["vlan"] = network.get("vlan")
            device["network"] = dev_network

    definition["zones"] = zones
    definition["devices"] = devices
    return definition
