# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Scenario routes for managing traffic simulation scenarios."""

import logging
import math
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from sqlalchemy import delete as sql_delete

from app.api.deps import CurrentUser, DBSession
from app.api.helpers import get_or_404_where, paginate
from app.core.exceptions import ConflictError, ExternalServiceError, ValidationError
from app.models.scenario import Scenario
from app.models.generation_job import GenerationJob
from app.models.traffic_agent import AgentDeployment
from app.services.device_identity_enricher import enrich_definition_serial_numbers
from app.services.ip_management import IPManagementService
from app.protocol_engines.protocols import validate_protocol_vendor_affinity
from app.services.protocol_validator import validate_scenario_protocols
from app.schemas.scenario import (
    ReadinessCheck,
    ReadinessSummary,
    ScenarioCreate,
    ScenarioExport,
    ScenarioImport,
    ScenarioListResponse,
    ScenarioModes,
    ScenarioResponse,
    ScenarioSummaryResponse,
    ScenarioUpdate,
)
from app.schemas.common import MessageResponse
from app.schemas.conduit import ConduitComplianceResponse

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


def get_scenario_counts(definition: dict) -> tuple[int, int]:
    """Extract device and flow counts from scenario definition."""
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})
    return len(devices), len(flows)


def compute_scenario_readiness(definition: dict) -> ReadinessSummary:
    """Compute readiness summary from a scenario definition.

    Pure function (no DB needed) that evaluates whether a scenario is
    deployment-ready based on its definition.
    """
    from collections import Counter

    checks: list[ReadinessCheck] = []
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    # --- Check: Has devices ---
    has_devices = len(devices) > 0
    checks.append(ReadinessCheck(
        name="Has devices",
        passed=has_devices,
        severity="error",
        message=None if has_devices else "Scenario has no devices",
    ))

    # --- Check: Has flows ---
    has_flows = len(flows) > 0
    checks.append(ReadinessCheck(
        name="Has flows",
        passed=has_flows,
        severity="error",
        message=None if has_flows else "Scenario has no flows",
    ))

    # --- Check: All flows have endpoints ---
    incomplete_flows = []
    devices_with_flows: set[str] = set()
    for flow_id, flow in flows.items():
        source_id = flow.get("sourceDeviceId") or flow.get("source_device_id")
        target_id = flow.get("targetDeviceId") or flow.get("target_device_id")
        flow_config = flow.get("config", {})
        is_external = flow_config.get("external", False)

        if source_id:
            devices_with_flows.add(source_id)
        if target_id:
            devices_with_flows.add(target_id)

        if not source_id:
            incomplete_flows.append(flow_id)
        elif not target_id and not is_external:
            incomplete_flows.append(flow_id)

    flows_complete = len(incomplete_flows) == 0
    checks.append(ReadinessCheck(
        name="All flows have endpoints",
        passed=flows_complete,
        severity="error",
        message=None if flows_complete else f"{len(incomplete_flows)} flow(s) missing endpoints",
    ))

    # --- Check: Unique device names ---
    device_names = [d.get("name", did) for did, d in devices.items()]
    name_counts = Counter(device_names)
    duplicate_names = {n: c for n, c in name_counts.items() if c > 1}
    names_unique = len(duplicate_names) == 0
    checks.append(ReadinessCheck(
        name="Unique device names",
        passed=names_unique,
        severity="error",
        message=None if names_unique else f"{len(duplicate_names)} duplicate name(s)",
    ))

    # --- Check: Unique MAC addresses ---
    mac_list = []
    for did, device in devices.items():
        network = device.get("network", {})
        mac = network.get("macAddress") or network.get("mac_address")
        if mac:
            mac_list.append(mac.upper())
    mac_counts = Counter(mac_list)
    duplicate_macs = {m: c for m, c in mac_counts.items() if c > 1}
    macs_unique = len(duplicate_macs) == 0
    checks.append(ReadinessCheck(
        name="Unique MAC addresses",
        passed=macs_unique,
        severity="error",
        message=None if macs_unique else f"{len(duplicate_macs)} duplicate MAC(s)",
    ))

    # --- Check: All devices have IPs ---
    devices_missing_ip = 0
    for did, device in devices.items():
        network = device.get("network", {})
        ip = network.get("ipAddress") or network.get("ip_address") or device.get("ip_address")
        if not ip:
            devices_missing_ip += 1
    all_have_ips = devices_missing_ip == 0
    checks.append(ReadinessCheck(
        name="All devices have IPs",
        passed=all_have_ips,
        severity="warning",
        message=None if all_have_ips else f"{devices_missing_ip} device(s) missing IP",
    ))

    # --- Check: IP-zone subnet consistency ---
    zones = definition.get("zones", {})
    ip_zone_mismatches = 0
    # Build zone → expected third octet mapping from subnet info
    _zone_offsets: dict[str, int | None] = {}
    for zid, zone in zones.items():
        net = zone.get("network", {})
        offset = net.get("subnet_offset")
        if offset is not None:
            _zone_offsets[zid] = int(offset)
        else:
            # Parse from subnet string e.g. "10.1.2.0/24" → 2
            subnet = net.get("subnet", "")
            parts = subnet.split("/")[0].split(".") if subnet else []
            try:
                _zone_offsets[zid] = int(parts[2]) if len(parts) >= 3 else None
            except (ValueError, IndexError):
                _zone_offsets[zid] = None

    for did, device in devices.items():
        zone_id = device.get("zoneId") or device.get("zone_id") or ""
        expected_offset = _zone_offsets.get(zone_id)
        if expected_offset is None:
            continue  # No zone or no subnet info — can't validate
        network = device.get("network", {})
        ip = network.get("ipAddress") or network.get("ip_address") or ""
        if not ip:
            continue
        parts = ip.split(".")
        if len(parts) >= 3:
            try:
                if int(parts[2]) != expected_offset:
                    ip_zone_mismatches += 1
            except ValueError:
                pass

    ip_zone_ok = ip_zone_mismatches == 0
    checks.append(ReadinessCheck(
        name="IP-zone subnet consistency",
        passed=ip_zone_ok,
        severity="warning",
        message=None if ip_zone_ok else (
            f"{ip_zone_mismatches} device(s) with IP not in their zone's subnet"
        ),
    ))

    # --- Check: No orphan devices (ERROR — CV cannot fingerprint devices without traffic) ---
    orphan_count = sum(1 for did in devices if did not in devices_with_flows)
    no_orphans = orphan_count == 0
    checks.append(ReadinessCheck(
        name="No orphan devices",
        passed=no_orphans,
        severity="error",
        message=None if no_orphans else (
            f"{orphan_count} device(s) with no flows — "
            f"Cyber Vision cannot fingerprint devices without traffic"
        ),
    ))

    # --- Check: Protocol/fingerprint consistency ---
    protocol_issues = validate_scenario_protocols(definition)
    protocols_ok = len(protocol_issues) == 0
    checks.append(ReadinessCheck(
        name="Protocol/fingerprint consistency",
        passed=protocols_ok,
        severity="warning",
        message=None if protocols_ok else f"{len(protocol_issues)} protocol mismatch(es)",
    ))

    # --- Check: Protocol-vendor affinity ---
    affinity_warnings: list[str] = []
    for did, device in devices.items():
        vendor = device.get("vendor") or ""
        protocols = device.get("protocols") or device.get("supported_protocols") or []
        if vendor and protocols:
            affinity_warnings.extend(validate_protocol_vendor_affinity(vendor, protocols))
    affinity_ok = len(affinity_warnings) == 0
    checks.append(ReadinessCheck(
        name="Protocol-vendor affinity",
        passed=affinity_ok,
        severity="warning",
        message=None if affinity_ok else f"{len(affinity_warnings)} vendor-protocol affinity warning(s)",
    ))

    # --- Check: Fingerprint coverage (per-protocol identity) ---
    # A device covered "by SNMP only" is shallow: CV probes each protocol
    # the device speaks and expects a protocol-specific identity block.
    # snmp_identity is universal via the carve-out, so SNMP-only is not
    # enough to pass — the device's declared protocols must each map to a
    # populated identity block.
    _PROTOCOL_IDENTITY = {
        "modbus": "modbus_identity",
        "modbus_tcp": "modbus_identity",
        "ethernet_ip": "ethernet_ip_identity",
        "enip": "ethernet_ip_identity",
        "cip_safety": "ethernet_ip_identity",
        "profinet": "profinet_identity",
        "profisafe": "profinet_identity",
        "s7comm": "s7_identity",
        "s7comm_plus": "s7_identity",
        "bacnet": "bacnet_identity",
        "bacnet_ip": "bacnet_identity",
        "opc_ua": "opc_ua_identity",
        "dnp3": "dnp3_identity",
        "iec104": "iec104_identity",
    }

    devices_without_fp = 0
    devices_thin_fp: list[str] = []
    for did, device in devices.items():
        fp = device.get("vendorFingerprint") or device.get("vendor_fingerprint") or {}
        if not fp:
            devices_without_fp += 1
            continue
        # Use the FINGERPRINT's own supported_protocols (the authoritative
        # statement of what this device template natively serves) rather
        # than the scenario device's protocols list — scenarios may
        # declare protocols beyond what the fingerprint backs, and
        # auto_repair_protocols handles those at create-time. We only
        # care that the fingerprint itself is internally consistent:
        # every protocol it claims to serve has a populated identity.
        fp_protocols = [
            p.lower()
            for p in (fp.get("supported_protocols") or [])
        ]
        expected = {_PROTOCOL_IDENTITY[p] for p in fp_protocols if p in _PROTOCOL_IDENTITY}
        if not expected:
            # Fingerprint only speaks SNMP-class protocols → snmp_identity covers it.
            if not fp.get("snmp_identity"):
                devices_without_fp += 1
            continue
        missing = [k for k in expected if not fp.get(k)]
        if missing:
            devices_thin_fp.append(
                f"{device.get('name', did)} ({', '.join(missing)})"
            )

    fp_coverage_ok = devices_without_fp == 0 and not devices_thin_fp
    if devices_without_fp and devices_thin_fp:
        fp_msg = (
            f"{devices_without_fp} device(s) missing fingerprint, "
            f"{len(devices_thin_fp)} thin (protocol-specific identity empty)"
        )
    elif devices_without_fp:
        fp_msg = (
            f"{devices_without_fp} device(s) missing vendor fingerprint — "
            f"Cyber Vision will see unknown vendor identity"
        )
    elif devices_thin_fp:
        fp_msg = (
            f"{len(devices_thin_fp)} device(s) advertise protocols but lack "
            f"matching identity blocks (e.g. speaks S7 with no s7_identity)"
        )
    else:
        fp_msg = None
    checks.append(ReadinessCheck(
        name="Fingerprint coverage",
        passed=fp_coverage_ok,
        severity="warning",
        message=fp_msg,
    ))

    # --- Check: MAC-vendor OUI alignment ---
    # A device's MAC must match SOME authoritative OUI list for its vendor.
    # Two sources are valid (in order of specificity):
    #   1. The device fingerprint's own `oui_prefixes` — model-level truth.
    #      A specific Cisco IE3500 template may declare OUI "F8:C2:88" that
    #      the vendor-level VENDOR_OUI_PREFIXES dict doesn't enumerate.
    #   2. VENDOR_OUI_PREFIXES — vendor-level fallback for devices without
    #      a fingerprint or whose fingerprint doesn't declare OUIs.
    from app.protocol_engines.vendor_oui import VENDOR_OUI_PREFIXES

    mac_vendor_mismatches = 0
    for did, device in devices.items():
        vendor = (device.get("vendor") or "").lower().strip()
        network = device.get("network", {})
        mac = (network.get("macAddress") or network.get("mac_address") or "").upper()
        if not vendor or not mac or len(mac) < 8:
            continue
        mac_prefix = mac[:8]  # e.g. "00:0E:8C"

        # Source 1: fingerprint-level OUIs (model-specific)
        fp = device.get("vendorFingerprint") or device.get("vendor_fingerprint") or {}
        fp_ouis = [o.upper() for o in (fp.get("oui_prefixes") or [])]
        if fp_ouis and mac_prefix in fp_ouis:
            continue

        # Source 2: vendor-level fallback
        vendor_ouis = [o.upper() for o in VENDOR_OUI_PREFIXES.get(vendor, [])]
        if vendor_ouis and mac_prefix not in vendor_ouis:
            # If the fingerprint declared OUIs and the MAC matched none of
            # them OR the vendor's, it's a real mismatch. If no fingerprint
            # OUIs were declared, we only had vendor-level to check.
            mac_vendor_mismatches += 1
    mac_vendor_ok = mac_vendor_mismatches == 0
    checks.append(ReadinessCheck(
        name="MAC-vendor OUI alignment",
        passed=mac_vendor_ok,
        severity="warning",
        message=None if mac_vendor_ok else (
            f"{mac_vendor_mismatches} device(s) with MAC OUI not matching "
            f"declared vendor — regenerate MACs to fix"
        ),
    ))

    # --- Check: Device naming quality ---
    import re as _re

    _GENERIC_NAME_PATTERNS = [
        _re.compile(r"^device[-_]?\d+$", _re.IGNORECASE),
        _re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-", _re.IGNORECASE),  # UUID prefix
        _re.compile(r"^(plc|hmi|rtu|sensor|switch|drive|io_module)[-_]?\d+$", _re.IGNORECASE),
        _re.compile(r"^new[-_]?device", _re.IGNORECASE),
    ]
    generic_names = 0
    for did, device in devices.items():
        name = device.get("name", did)
        if any(p.match(name) for p in _GENERIC_NAME_PATTERNS):
            generic_names += 1
    naming_ok = generic_names == 0
    checks.append(ReadinessCheck(
        name="Device naming quality",
        passed=naming_ok,
        severity="warning",
        message=None if naming_ok else (
            f"{generic_names} device(s) with generic names — "
            f"use descriptive names for realistic Cyber Vision classification"
        ),
    ))

    # --- Check: Flow protocol consistency ---
    flow_protocol_mismatches = 0
    for fid, flow in flows.items():
        proto = flow.get("protocol", "")
        if not proto:
            continue
        src_id = flow.get("sourceDeviceId") or flow.get("source_device_id")
        tgt_id = flow.get("targetDeviceId") or flow.get("target_device_id")
        src_protos = (devices.get(src_id, {}).get("protocols") or []) if src_id else []
        tgt_protos = (devices.get(tgt_id, {}).get("protocols") or []) if tgt_id else []
        if proto not in src_protos and proto not in tgt_protos:
            flow_protocol_mismatches += 1
    flow_protos_ok = flow_protocol_mismatches == 0
    checks.append(ReadinessCheck(
        name="Flow protocol consistency",
        passed=flow_protos_ok,
        severity="warning",
        message=None if flow_protos_ok else (
            f"{flow_protocol_mismatches} flow(s) use protocols not listed on "
            f"either endpoint device"
        ),
    ))

    # --- Check: Conduit compliance ---
    from app.services.conduit_compliance import validate_conduit_compliance

    conduit_result = validate_conduit_compliance(definition)
    conduit_ok = conduit_result.non_compliant_flows == 0
    checks.append(ReadinessCheck(
        name="Conduit compliance",
        passed=conduit_ok,
        severity="warning",
        message=None if conduit_ok else (
            f"{conduit_result.non_compliant_flows} flow(s) crossing zones "
            f"without matching conduit"
        ),
    ))

    # --- Check: Flow rationality (semantic correctness) ---
    from app.services.template_audit import audit_irrational_flows
    irrational = audit_irrational_flows(definition)
    # Only warning-severity findings gate the readiness; info-level
    # findings (role-pair soft warnings) ride along in the audit detail.
    warning_irrational = [f for f in irrational if f.severity == "warning"]
    rational_ok = len(warning_irrational) == 0
    checks.append(ReadinessCheck(
        name="Flow rationality",
        passed=rational_ok,
        severity="warning",
        message=None if rational_ok else (
            f"{len(warning_irrational)} flow(s) have irrational source/target "
            f"pairing (e.g. jump server polling a PLC, drive polling a PLC)"
        ),
    ))

    # --- Check: Role inventory health ---
    # A bag of 14 PLCs with no engineering workstation, SCADA, or
    # supervisory device is unrealistic; flag at SMALL+ scale. Honors
    # the device's `architectural_role` when present and falls back to
    # a device_type → category bucket for legacy scenario templates.
    # The fallback is deliberately strict on device_type (not the role
    # catalog) — `device_type=plc` is treated as control even though
    # the role catalog allows `plc` to also fulfill `area_supervisor_plc`.
    _SUPERVISORY_ROLES = {
        "scada_primary", "scada_standby", "engineering_workstation",
        "area_hmi", "area_supervisor_plc", "alarm_event_server",
    }
    _INFRA_ROLES = {
        "nms_server", "asset_management_server", "ot_domain_controller",
        "jump_server", "av_management_server", "patch_staging_server",
        "process_historian", "local_historian", "historian_replica",
        "reverse_proxy", "patch_server",
    }
    _CONTROL_ROLES = {
        "cell_controller", "batch_controller", "safety_controller",
        "dcs_controller", "field_rtu", "aggregator_rtu",
        "robot_controller", "cnc_controller", "wcs_controller",
        "conveyor_controller", "traffic_controller", "cabinet_controller",
        "bms_field_controller", "protection_relay",
    }
    # device_type → category bucket (used only when architectural_role
    # is absent). These are unambiguous; PLC always counts as control,
    # never supervisory, regardless of role catalog flexibility.
    _SUPERVISORY_TYPES = {
        "scada", "scada_server", "engineering_station",
        "engineering_workstation", "operator_station", "workstation",
        "hmi", "master_station",
    }
    _INFRA_TYPES = {
        "jump_server", "nms", "domain_controller", "patch_server",
        "asset_management", "av_server", "edr_server", "historian",
        "bms_server",
    }
    _CONTROL_TYPES = {
        "plc", "safety_plc", "rtu", "dcs_controller",
        "robot_controller", "cnc_controller", "batch_controller",
        "agv_controller", "fleet_manager", "wellhead_controller",
        "compressor_controller", "pump_controller",
        "traffic_controller", "tunnel_controller", "ahu_controller",
        "vav_controller", "chiller_controller", "bms_controller",
        "building_controller", "room_controller",
    }

    def _device_category(device: dict) -> str | None:
        """Return 'supervisory', 'infra', 'control', or None for a device.

        Uses architectural_role when present (authoritative), otherwise
        falls back to device_type bucketing. Returns None for devices
        that don't fit any category (field instruments, switches, etc.).
        """
        ar = device.get("architectural_role") or device.get("architecturalRole")
        if ar:
            if ar in _SUPERVISORY_ROLES:
                return "supervisory"
            if ar in _INFRA_ROLES:
                return "infra"
            if ar in _CONTROL_ROLES:
                return "control"
            return None
        dt = (
            device.get("device_type")
            or device.get("deviceType")
            or device.get("type")
            or ""
        ).lower()
        if dt in _SUPERVISORY_TYPES:
            return "supervisory"
        if dt in _INFRA_TYPES:
            return "infra"
        if dt in _CONTROL_TYPES:
            return "control"
        return None

    sup_count = 0
    infra_count = 0
    ctrl_count = 0
    for did, device in devices.items():
        cat = _device_category(device)
        if cat == "supervisory":
            sup_count += 1
        elif cat == "infra":
            infra_count += 1
        elif cat == "control":
            ctrl_count += 1

    inventory_issues: list[str] = []
    scale = len(devices)
    # SMALL+ scale gate — single-device demos and 3-device sketches are
    # allowed to skip supervisory/infra requirements.
    if scale >= 10:
        if sup_count == 0:
            inventory_issues.append(
                "no supervisory device (engineering workstation, SCADA, area HMI)"
            )
        if infra_count == 0:
            inventory_issues.append(
                "no infrastructure role (NMS, asset mgmt, jump server, domain controller, historian)"
            )
        if sup_count > 0 and ctrl_count > 0:
            ratio = ctrl_count / sup_count
            if ratio > 10.0:
                inventory_issues.append(
                    f"controller:supervisory ratio {ctrl_count}:{sup_count} exceeds 10:1"
                )
        elif ctrl_count >= 10 and sup_count == 0:
            inventory_issues.append(
                f"{ctrl_count} controllers but zero supervisory devices "
                f"— no human-in-the-loop is unrealistic"
            )

    inventory_ok = not inventory_issues
    checks.append(ReadinessCheck(
        name="Role inventory health",
        passed=inventory_ok,
        severity="warning",
        message=None if inventory_ok else (
            "Scenario lacks expected role variety: " + "; ".join(inventory_issues)
        ),
    ))

    # Compute score and status
    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    error_count = sum(1 for c in checks if not c.passed and c.severity == "error")
    warning_count = sum(1 for c in checks if not c.passed and c.severity == "warning")
    score = round((passed / total) * 100) if total > 0 else 0

    if error_count > 0:
        status = "not_ready"
    elif warning_count > 0:
        status = "warnings"
    else:
        status = "ready"

    return ReadinessSummary(
        score=score,
        status=status,
        error_count=error_count,
        warning_count=warning_count,
        checks=checks,
    )


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

    query = query.order_by(Scenario.updated_at.desc())
    scenarios, total = await paginate(db, query, page, page_size)

    # Build summary responses with counts and readiness
    items = []
    for s in scenarios:
        definition = s.definition or {}
        device_count, flow_count = get_scenario_counts(definition)
        readiness = compute_scenario_readiness(definition)
        modes = ScenarioModes(
            clean_demo_mode=bool(definition.get("clean_demo_mode", False)),
            broadcast_traffic_enabled=bool(
                definition.get("broadcast_traffic_enabled", True)
            ),
            cell_isolation_mode=str(
                (definition.get("cell_isolation") or {}).get("mode", "off")
            ),
        )
        items.append(ScenarioSummaryResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            vertical=s.vertical,
            total_duration_ms=s.total_duration_ms,
            version=s.version,
            device_count=device_count,
            flow_count=flow_count,
            readiness=readiness,
            modes=modes,
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
    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
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
        scenario.definition = enrich_definition_serial_numbers(
            scenario.definition, str(scenario.id)
        )

    # Auto-repair protocol/fingerprint mismatches at create time so the
    # scenario lands clean — users never see protocol_identity_mismatch
    # readiness warnings on freshly created scenarios.
    if scenario.definition:
        from app.services.scenario_enrichment import (
            auto_repair_protocols,
            repair_flow_protocols,
        )
        scenario.definition = auto_repair_protocols(scenario.definition)
        # Then snap any flow protocols to one both endpoints actually
        # support, using the just-repaired protocols list.
        scenario.definition = repair_flow_protocols(scenario.definition)

    await db.commit()
    await db.refresh(scenario)

    return ScenarioResponse.model_validate(scenario)


_AUTO_VERSION_INTERVAL_SECONDS = 300  # 5 minutes
_logger = logging.getLogger(__name__)


async def _maybe_auto_version(
    db: DBSession,
    scenario: Scenario,
    user_id: UUID,
) -> None:
    """Auto-create a version if enough time has passed since the last one.

    Coalesces rapid auto-saves into a single version by only creating
    a snapshot when >= 5 minutes have elapsed since the last version.
    """
    from app.models.scenario_version import ScenarioVersion
    from app.api.routes.scenario_versions import create_version_snapshot

    result = await db.execute(
        select(ScenarioVersion)
        .where(ScenarioVersion.scenario_id == scenario.id)
        .order_by(ScenarioVersion.version_number.desc())
        .limit(1)
    )
    latest_version = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    should_create = False

    if latest_version is None:
        should_create = True
    else:
        elapsed = (now - latest_version.created_at).total_seconds()
        if elapsed >= _AUTO_VERSION_INTERVAL_SECONDS:
            should_create = True

    if should_create:
        try:
            await create_version_snapshot(
                db, scenario, source="auto", user_id=user_id
            )
        except Exception:
            _logger.warning(
                "Failed to auto-create version for scenario %s",
                scenario.id,
                exc_info=True,
            )


@router.put("/{scenario_id}", response_model=ScenarioResponse)
@router.patch("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: UUID,
    scenario_data: ScenarioUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> ScenarioResponse:
    """Update a scenario (supports both PUT and PATCH)."""
    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
    )

    # Update fields
    update_data = scenario_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scenario, field, value)

    # If definition was updated, ensure all devices have serial numbers
    if "definition" in update_data and scenario.definition:
        scenario.definition = enrich_definition_serial_numbers(
            scenario.definition, str(scenario.id)
        )
        # Same protocol-mismatch guardrail as the create path — keep the
        # saved scenario clean so readiness warnings never appear in the
        # studio after a save.
        from app.services.scenario_enrichment import (
            auto_repair_protocols,
            repair_flow_protocols,
        )
        scenario.definition = auto_repair_protocols(scenario.definition)
        scenario.definition = repair_flow_protocols(scenario.definition)

    # Increment version
    scenario.version += 1
    scenario.updated_at = datetime.now(timezone.utc)

    # Auto-version coalescing: create a version if enough time has passed
    await _maybe_auto_version(db, scenario, current_user.id)

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
    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
    )

    # Check for active agent deployments
    active_agent_deployments = await db.execute(
        select(func.count()).select_from(AgentDeployment).where(
            AgentDeployment.scenario_id == scenario_id,
            AgentDeployment.state.in_(["running", "starting", "stopping"]),
        )
    )
    active_agent_count = active_agent_deployments.scalar() or 0

    # Check for generation jobs
    generation_jobs_result = await db.execute(
        select(func.count()).select_from(GenerationJob).where(
            GenerationJob.scenario_id == scenario_id,
        )
    )
    generation_job_count = generation_jobs_result.scalar() or 0

    # If there are active deployments and not forcing, return error with details
    if active_agent_count > 0 and not force:
        raise ConflictError(
            "Cannot delete scenario with active deployments",
            resource="Scenario",
            details={
                "active_agent_deployments": active_agent_count,
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

    # Now delete the scenario
    await db.delete(scenario)
    await db.commit()

    cleanup_msg = ""
    if force and (active_agent_count > 0 or generation_job_count > 0):
        cleanup_msg = f" (cleaned up {generation_job_count} generation jobs, {active_agent_count} deployments)"

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
    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
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
    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
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
    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
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


@router.get("/{scenario_id}/conduit-compliance", response_model=ConduitComplianceResponse)
async def get_conduit_compliance(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ConduitComplianceResponse:
    """Check all flows against conduit rules.

    Returns compliance findings for flows that cross zone boundaries
    without a matching conduit, or use protocols not allowed by the conduit.
    """
    from app.services.conduit_compliance import validate_conduit_compliance

    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
    )

    return validate_conduit_compliance(scenario.definition or {})


# ---------------------------------------------------------------------------
# Cell isolation (Purdue-aware east/west enforcement)
# ---------------------------------------------------------------------------


class CellIsolationItem(BaseModel):
    """One conduit or flow that strict_northbound mode would remove."""
    id: str
    name: str
    source_zone: str | None = None
    target_zone: str | None = None
    protocol: str | None = None
    allowed_protocols: list[str] | None = None


class CellIsolationPreview(BaseModel):
    """Preview returned before the destructive prune is applied."""
    flows: list[CellIsolationItem]
    conduits: list[CellIsolationItem]


class ApplyStrictResponse(BaseModel):
    """Result of applying strict_northbound mode to a scenario."""
    scenario_id: str
    version_snapshot_id: str | None = None
    removed_flow_ids: list[str]
    removed_conduit_ids: list[str]
    new_flow_count: int
    new_conduit_count: int


@router.get(
    "/{scenario_id}/cell-isolation/preview-strict",
    response_model=CellIsolationPreview,
)
async def preview_cell_isolation_strict(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> CellIsolationPreview:
    """Show exactly which cell-to-cell flows and conduits the strict
    northbound prune would remove. Read-only — does not mutate state."""
    from app.protocol_engines.cell_isolation import preview_strict_northbound

    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
    )

    preview = preview_strict_northbound(scenario.definition or {})
    return CellIsolationPreview(
        flows=[CellIsolationItem(**item) for item in preview["flows"]],
        conduits=[CellIsolationItem(**item) for item in preview["conduits"]],
    )


@router.post(
    "/{scenario_id}/cell-isolation/apply-strict",
    response_model=ApplyStrictResponse,
)
async def apply_cell_isolation_strict(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ApplyStrictResponse:
    """Switch the scenario to strict_northbound mode.

    Snapshots the current scenario via the version system (so the user
    can roll back), then prunes all cell-to-cell flows and conduits and
    sets ``definition.cell_isolation.mode = strict_northbound``.
    """
    from app.api.routes.scenario_versions import create_version_snapshot
    from app.protocol_engines.cell_isolation import prune_for_strict_northbound

    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
    )

    snapshot = await create_version_snapshot(
        db,
        scenario,
        source="manual",
        user_id=current_user.id,
        label="Pre cell-isolation lockdown",
    )

    new_definition, removed = prune_for_strict_northbound(scenario.definition or {})
    scenario.definition = new_definition
    scenario.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()

    new_flows = new_definition.get("flows", {})
    new_conduits = new_definition.get("conduits", {})

    return ApplyStrictResponse(
        scenario_id=str(scenario.id),
        version_snapshot_id=str(snapshot.id),
        removed_flow_ids=removed["flows"],
        removed_conduit_ids=removed["conduits"],
        new_flow_count=len(new_flows) if isinstance(new_flows, (dict, list)) else 0,
        new_conduit_count=(
            len(new_conduits) if isinstance(new_conduits, (dict, list)) else 0
        ),
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
    from app.services.fingerprint_cache import get_fingerprint_cache
    from app.services.protocol_validator import (
        get_protocol_identity_key,
        identity_has_vendor_data,
    )

    # Get scenario
    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
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
            cache = get_fingerprint_cache()
            fingerprint = cache.get_by_vendor_model(vendor, fingerprint_model) or {}

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
        from sqlalchemy.orm.attributes import flag_modified
        scenario.definition = definition
        flag_modified(scenario, "definition")
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
    # Auto-repair protocol mismatches in imported scenarios — old exports
    # may pre-date a fingerprint update or carry mismatches the source
    # install never repaired. Flow-protocol snap follows.
    from app.services.scenario_enrichment import (
        auto_repair_protocols,
        repair_flow_protocols,
    )
    definition = auto_repair_protocols(definition)
    definition = repair_flow_protocols(definition)
    scenario.definition = definition

    await db.commit()
    await db.refresh(scenario)

    return ScenarioResponse.model_validate(scenario)


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
    scenario = await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == current_user.id,
        resource_name="Scenario",
        identifier=str(scenario_id),
    )

    definition = scenario.definition or {}
    devices = definition.get("devices", {})
    zones = definition.get("zones", {})

    if not devices:
        raise ValidationError("Scenario has no devices to rename")

    # Get AI provider
    try:
        ai_provider = await AIProviderFactory.create(db)
    except ValueError as e:
        raise ValidationError(f"AI provider not configured: {e}. Configure API key in Settings.")

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
        raise ExternalServiceError(
            service="ai",
            message=f"AI naming failed: {e}",
            original_error=str(e),
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
