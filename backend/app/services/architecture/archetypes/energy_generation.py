# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Energy generation archetype — gas turbine / combined cycle plant.

DCS-driven power plant with turbine controls, balance of plant
controllers, fuel-handling, electrical (generator + step-up), and SIS
for emergency stop / fire suppression.
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


_ZONE_IDMZ = ZoneDef(
    id="idmz",
    name="Industrial DMZ",
    purdue_level=3.5,
    security_level="critical",
    description="L3.5 IT/OT boundary — NERC CIP regulated.",
    role_slots=(
        RoleSlot(role_id="jump_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DMZ_Jump_Server"),
        RoleSlot(role_id="patch_staging_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Patch_Server"),
        RoleSlot(role_id="av_management_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_AV_Server"),
        RoleSlot(role_id="historian_replica",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_Historian_Replica"),
        RoleSlot(role_id="wan_edge_router",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DMZ_WAN_Edge"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DMZ_Core_Switch"),
    ),
)


_ZONE_OPERATIONS = ZoneDef(
    id="operations",
    name="Plant Operations",
    purdue_level=3.0,
    security_level="high",
    description="L3 control room — DCS HMI, historian, alarm, NMS.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Plant_DCS_HMI"),
        RoleSlot(role_id="scada_standby",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Plant_DCS_HMI_Standby"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Plant_Historian"),
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
                 name_prefix="Plant_NMS"),
        RoleSlot(role_id="asset_management_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="Plant_Asset_Mgmt"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Operations_Core_Switch"),
    ),
)


def _make_unit_zone(uid: int, uname: str) -> ZoneDef:
    """Generation unit — turbine DCS + operator HMI + IO + instruments +
    flow meters + valves + drives. Phase 9 audit added area_hmi +
    flow_meter."""
    return ZoneDef(
        id=f"unit{uid}",
        name=uname,
        purdue_level=1.0,
        security_level="standard",
        description=f"Generation unit {uid} — turbine controls + BoP.",
        role_slots=(
            RoleSlot(role_id="dcs_controller",
                     count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     name_prefix=f"Unit{uid}_Turbine_Controller"),
            RoleSlot(role_id="area_hmi",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     optional_at=("demo",),
                     name_prefix=f"Unit{uid}_Operator_HMI"),
            RoleSlot(role_id="distributed_io",
                     count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                     "large": 5, "multi_site": 5},
                     name_prefix=f"Unit{uid}_IO"),
            RoleSlot(role_id="field_instrument",
                     count_by_scale={"demo": 3, "small": 5, "medium": 7,
                                     "large": 9, "multi_site": 9},
                     name_prefix=f"Unit{uid}_Instrument"),
            RoleSlot(role_id="flow_meter",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     optional_at=("demo",),
                     name_prefix=f"Unit{uid}_Flow_Meter"),
            RoleSlot(role_id="valve_actuator",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Unit{uid}_Valve"),
            RoleSlot(role_id="vfd",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Unit{uid}_VFD"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Unit{uid}_Switch"),
        ),
    )


_UNIT_ZONES: tuple[ZoneDef, ...] = (
    _make_unit_zone(1, "Generation Unit 1 — GT1"),
    _make_unit_zone(2, "Generation Unit 2 — GT2"),
    _make_unit_zone(3, "Generation Unit 3 — Steam Turbine"),
)


_ZONE_SAFETY = ZoneDef(
    id="safety",
    name="Safety Instrumented System",
    purdue_level=1.0,
    security_level="critical",
    description="Burner management + emergency-stop SIS.",
    role_slots=(
        RoleSlot(role_id="safety_controller",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="SIS_Controller"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="SIS_Switch"),
    ),
)


_ZONE_ELECTRICAL = ZoneDef(
    id="electrical",
    name="Electrical / Generator",
    purdue_level=1.0,
    security_level="high",
    description="Generator excitation, step-up transformer protection.",
    role_slots=(
        RoleSlot(role_id="protection_relay",
                 count_by_scale={"demo": 0, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 optional_at=("demo",),
                 name_prefix="Generator_Protection"),
        RoleSlot(role_id="power_meter",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Revenue_Power_Meter"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Electrical_Instrument"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Electrical_Switch"),
    ),
)


_C_IDMZ_OPS = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ Operations",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("https", "snmp", "opc_ua", "rdp", "ssh"),
    description="NERC-CIP-controlled IT/OT boundary.",
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
        description=f"DCS HMI / historian to generation unit {uid}.",
    )


_UNIT_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_ops_to_unit_conduit(i) for i in range(1, 4)
)


def _make_unit_to_safety_conduit(uid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"unit{uid}_to_safety",
        name=f"Unit {uid} ↔ Safety",
        source_zone=f"unit{uid}",
        target_zone="safety",
        direction="bidirectional",
        security_level="critical",
        allowed_protocols=("modbus_tcp",),
        description=f"Unit {uid} ↔ SIS for emergency stop / BMS.",
    )


_UNIT_SAFETY_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_unit_to_safety_conduit(i) for i in range(1, 4)
)


_C_OPS_TO_SAFETY = ConduitTemplate(
    id="operations_to_safety",
    name="Operations ↔ Safety",
    source_zone="operations",
    target_zone="safety",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("opc_ua", "ssh", "snmp"),
    description="Engineering workstation reach to SIS; NMS SNMP polls.",
)


_C_OPS_TO_ELECTRICAL = ConduitTemplate(
    id="operations_to_electrical",
    name="Operations ↔ Electrical",
    source_zone="operations",
    target_zone="electrical",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("iec61850", "modbus_tcp", "snmp"),
    description="Generator protection and excitation supervision.",
)


ARCHETYPE = Archetype(
    id="energy_generation_combined_cycle",
    name="Energy Generation — Combined Cycle Gas Turbine",
    vertical=Vertical.ENERGY_GENERATION.value,
    pattern=ArchitecturePattern.CONTINUOUS_DCS,
    description=(
        "Combined-cycle gas turbine plant: turbine controls per unit "
        "(GE Mark VIe / Siemens TXP / ABB Symphony / Emerson Ovation), "
        "central DCS HMI, BMS-grade SIS, dedicated electrical zone for "
        "generator protection. NERC CIP regulated."
    ),
    default_vendor_profile=VendorProfile.DCS_EMERSON,
    supported_vendor_profiles=(
        VendorProfile.DCS_EMERSON,
        VendorProfile.DCS_HONEYWELL,
        VendorProfile.DCS_ABB,
    ),
    zones=(
        _ZONE_IDMZ, _ZONE_OPERATIONS,
    ) + _UNIT_ZONES + (
        _ZONE_SAFETY, _ZONE_ELECTRICAL,
    ),
    conduits=(
        (_C_IDMZ_OPS,)
        + _UNIT_CONDUITS
        + _UNIT_SAFETY_CONDUITS
        + (_C_OPS_TO_SAFETY, _C_OPS_TO_ELECTRICAL)
    ),
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Unit counts: DEMO=1, SMALL=2, MEDIUM/LARGE=3.",
        "Electrical zone hosts protection relays at SMALL+; smaller "
        "scenarios fold electrical into unit1.",
        "NERC CIP medium-impact assets land at MEDIUM+ scale.",
    ),
)
