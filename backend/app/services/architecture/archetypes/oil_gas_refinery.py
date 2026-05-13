# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Oil & gas refinery archetype: process units + dedicated SIS.

Same architectural pattern as process manufacturing (DCS-driven), but
vendor-pinned to oil&gas dominant DCS vendors (Honeywell Experion,
Yokogawa Centum, Emerson DeltaV) and slightly different zone shape:
multiple process units with cross-unit material flow, separate utilities
zone for boilers / cooling / instrument air.
"""

from __future__ import annotations

from app.services.architecture.archetypes._base import (
    Archetype,
    ArchitecturePattern,
    ConduitTemplate,
    RoleSlot,
    ScaleTier,
    VendorProfile,
    ZoneDef,
)
from app.services.architecture.role_catalog import Vertical


# IDMZ / Ops slots are the same shape as manufacturing_process; we
# define new instances here so each archetype owns its zone tree (no
# accidental coupling via shared zone constants).

_ZONE_IDMZ = ZoneDef(
    id="idmz",
    name="Industrial DMZ",
    purdue_level=3.5,
    security_level="critical",
    description="L3.5 IT/OT boundary.",
    role_slots=(
        RoleSlot(role_id="jump_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DMZ_Jump_Server"),
        RoleSlot(role_id="remote_access_gateway",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Remote_Access_GW"),
        RoleSlot(role_id="patch_staging_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_Patch_Server"),
        RoleSlot(role_id="av_management_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_AV_Server"),
        RoleSlot(role_id="historian_replica",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_Historian_Replica"),
        RoleSlot(role_id="wan_edge_router",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_WAN_Edge"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DMZ_Core_Switch"),
    ),
)


_ZONE_OPERATIONS = ZoneDef(
    id="operations",
    name="Refinery Operations",
    purdue_level=3.0,
    security_level="high",
    description="L3 control room — DCS HMI, historian, alarm, engineering.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Refinery_DCS_HMI"),
        RoleSlot(role_id="scada_standby",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Refinery_DCS_HMI_Standby"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Refinery_Historian"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Eng_Workstation"),
        RoleSlot(role_id="alarm_event_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Alarm_Server"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Refinery_NMS"),
        RoleSlot(role_id="asset_management_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="Refinery_Asset_Mgmt"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Operations_Core_Switch"),
    ),
)


def _make_unit_zone(uid: int, uname: str) -> ZoneDef:
    """Refinery unit — DCS controller + per-unit operator HMI + IO +
    instruments + analyzers + flow meters + valves + drives. Phase 9
    audit fix: added analyzer, flow_meter, area_hmi, power_meter."""
    return ZoneDef(
        id=f"unit{uid}",
        name=uname,
        purdue_level=1.0,
        security_level="standard",
        description=f"Process unit {uid} (refinery train).",
        role_slots=(
            RoleSlot(role_id="dcs_controller",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Unit{uid}_DCS"),
            RoleSlot(role_id="area_hmi",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     optional_at=("demo",),
                     name_prefix=f"Unit{uid}_Operator_HMI"),
            RoleSlot(role_id="distributed_io",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Unit{uid}_IO"),
            RoleSlot(role_id="field_instrument",
                     count_by_scale={"demo": 3, "small": 6, "medium": 8,
                                     "large": 10, "multi_site": 10},
                     name_prefix=f"Unit{uid}_Instrument"),
            RoleSlot(role_id="analyzer",
                     count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     optional_at=("demo",),
                     name_prefix=f"Unit{uid}_Analyzer"),
            RoleSlot(role_id="flow_meter",
                     count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     optional_at=("demo",),
                     name_prefix=f"Unit{uid}_Flow_Meter"),
            RoleSlot(role_id="valve_actuator",
                     count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                     "large": 8, "multi_site": 8},
                     name_prefix=f"Unit{uid}_Valve"),
            RoleSlot(role_id="vfd",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Unit{uid}_VFD"),
            RoleSlot(role_id="power_meter",
                     count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     optional_at=("demo", "small"),
                     name_prefix=f"Unit{uid}_Power_Meter"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Unit{uid}_Switch"),
        ),
    )


_UNIT_ZONES: tuple[ZoneDef, ...] = (
    _make_unit_zone(1, "Crude Distillation Unit"),
    _make_unit_zone(2, "Hydrocracker"),
    _make_unit_zone(3, "Reformer"),
    _make_unit_zone(4, "Alkylation Unit"),
)


_ZONE_SAFETY = ZoneDef(
    id="safety",
    name="Safety Instrumented System",
    purdue_level=1.0,
    security_level="critical",
    description="SIL-3 burner management / emergency shutdown.",
    role_slots=(
        RoleSlot(role_id="safety_controller",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 name_prefix="SIS_Controller"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="SIS_Switch"),
    ),
)


_ZONE_UTILITIES = ZoneDef(
    id="utilities",
    name="Plant Utilities",
    purdue_level=1.0,
    security_level="standard",
    description="Boilers, cooling water, instrument air, flares.",
    role_slots=(
        RoleSlot(role_id="cell_controller",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 2, "multi_site": 2},
                 optional_at=("demo",),
                 name_prefix="Utility_PLC"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 0, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 optional_at=("demo",),
                 name_prefix="Utility_Instrument"),
        RoleSlot(role_id="vfd",
                 count_by_scale={"demo": 0, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 optional_at=("demo",),
                 name_prefix="Utility_VFD"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Utility_Switch"),
    ),
)


# ---------------------------------------------------------------------------
# Conduits
# ---------------------------------------------------------------------------

_C_IDMZ_OPS = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ Operations",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("https", "snmp", "opc_ua", "rdp", "ssh"),
    description="Jump-server pivot, replication, AV/patch.",
)


def _make_ops_to_unit_conduit(uid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_unit{uid}",
        name=f"Operations ↔ Unit {uid}",
        source_zone="operations",
        target_zone=f"unit{uid}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=("opc_ua", "modbus_tcp", "snmp"),
        description=f"DCS HMI / historian to unit {uid}.",
    )


_UNIT_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_ops_to_unit_conduit(i) for i in range(1, 5)
)


_C_OPS_TO_SAFETY = ConduitTemplate(
    id="operations_to_safety",
    name="Operations ↔ Safety",
    source_zone="operations",
    target_zone="safety",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("opc_ua", "snmp", "ssh"),
    description="Engineering workstation reach to SIS (configuration).",
)


def _make_unit_to_safety_conduit(uid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"unit{uid}_to_safety",
        name=f"Unit {uid} ↔ Safety",
        source_zone=f"unit{uid}",
        target_zone="safety",
        direction="bidirectional",
        security_level="critical",
        allowed_protocols=("modbus_tcp", "snmp"),
        description=f"Unit {uid} ↔ SIS shutdown/handshake.",
    )


_UNIT_SAFETY_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_unit_to_safety_conduit(i) for i in range(1, 5)
)


_C_OPS_TO_UTILITIES = ConduitTemplate(
    id="operations_to_utilities",
    name="Operations ↔ Utilities",
    source_zone="operations",
    target_zone="utilities",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("opc_ua", "modbus_tcp", "snmp"),
    description="DCS HMI / historian to plant utilities.",
)


# ---------------------------------------------------------------------------
# Archetype
# ---------------------------------------------------------------------------

ARCHETYPE = Archetype(
    id="oil_gas_refinery",
    name="Oil & Gas — Refinery (DCS)",
    vertical=Vertical.OIL_GAS.value,
    pattern=ArchitecturePattern.CONTINUOUS_DCS,
    description=(
        "Refinery / petrochem plant. Multi-unit DCS architecture "
        "(crude unit, hydrocracker, reformer, alkylation), separate SIS "
        "zone for SIL-3 emergency shutdown / burner management, and a "
        "utilities zone for boilers / cooling / instrument air. Standard "
        "vendor profile is Honeywell Experion or Yokogawa Centum."
    ),
    default_vendor_profile=VendorProfile.DCS_HONEYWELL,
    supported_vendor_profiles=(
        VendorProfile.DCS_HONEYWELL,
        VendorProfile.DCS_YOKOGAWA,
        VendorProfile.DCS_EMERSON,
    ),
    zones=(_ZONE_IDMZ, _ZONE_OPERATIONS) + _UNIT_ZONES + (
        _ZONE_SAFETY, _ZONE_UTILITIES,
    ),
    conduits=(
        (_C_IDMZ_OPS,)
        + _UNIT_CONDUITS
        + (_C_OPS_TO_SAFETY,)
        + _UNIT_SAFETY_CONDUITS
        + (_C_OPS_TO_UTILITIES,)
    ),
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Unit counts: DEMO=1, SMALL=2, MEDIUM=3, LARGE/MULTI_SITE=4.",
        "Utilities zone appears at SMALL+; smaller scenarios fold "
        "utility-side instruments into the dominant unit.",
        "Conduits to SIS use SIL-3 protocols only — config over OPC UA "
        "from the engineering workstation, status handshake over "
        "modbus_tcp from process units.",
    ),
)
