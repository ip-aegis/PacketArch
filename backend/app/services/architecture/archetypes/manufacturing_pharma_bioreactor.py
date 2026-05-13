# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Pharma bioreactor / vaccine plant archetype.

GMP-regulated process plant with dense bioreactor instrumentation, ISA-
88 batch control, dedicated SIS for over-pressure / over-temp safety,
purification suite (tangential flow filtration, chromatography),
fill-finish suite (vial filling, lyophilization), and clean utilities
(WFI water for injection, clean steam, compressed air). Heavy
historian + asset_management + audit_trail traffic for 21 CFR Part 11.
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
    description="L3.5 — IT integration + GMP audit-trail replication.",
    role_slots=(
        RoleSlot(role_id="jump_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DMZ_Jump_Server"),
        RoleSlot(role_id="remote_access_gateway",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Vendor_Service_GW"),
        RoleSlot(role_id="patch_staging_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Patch_Server"),
        RoleSlot(role_id="av_management_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_AV_Server"),
        RoleSlot(role_id="historian_replica",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_GMP_Audit_Replica"),
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
    description="L3 control room — DCS HMI, batch, historian, alarm, NMS.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DCS_HMI_Primary"),
        RoleSlot(role_id="scada_standby",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DCS_HMI_Standby"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="GMP_Historian"),
        RoleSlot(role_id="batch_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="ISA88_Batch_Server"),
        RoleSlot(role_id="alarm_event_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="GMP_Alarm_Server"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Eng_Workstation"),
        RoleSlot(role_id="asset_management_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="GMP_Asset_Mgmt"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Plant_NMS"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Operations_Core_Switch"),
    ),
)


def _make_bioreactor_unit(uid: int, uname: str) -> ZoneDef:
    """Bioreactor suite — DCS + heavy analyzer instrumentation
    (pH / DO / OD / glucose / lactate) + jacket-temperature control."""
    return ZoneDef(
        id=f"unit{uid}",
        name=uname,
        purdue_level=1.0,
        security_level="high",
        description=f"Bioreactor suite {uid} — DCS + dense instrumentation.",
        role_slots=(
            RoleSlot(role_id="dcs_controller",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     name_prefix=f"Unit{uid}_Bioreactor_DCS"),
            RoleSlot(role_id="batch_controller",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Unit{uid}_Batch_Controller"),
            RoleSlot(role_id="area_hmi",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     optional_at=("demo",),
                     name_prefix=f"Unit{uid}_Operator_HMI"),
            # Bioreactor analyzer instrumentation (pH, DO, OD, glucose,
            # lactate, viable cell density, off-gas analyzer).
            RoleSlot(role_id="analyzer",
                     count_by_scale={"demo": 4, "small": 6, "medium": 8,
                                     "large": 10, "multi_site": 10},
                     name_prefix=f"Unit{uid}_Analyzer"),
            # Mass-flow controllers + temperature transmitters + level.
            RoleSlot(role_id="field_instrument",
                     count_by_scale={"demo": 4, "small": 6, "medium": 8,
                                     "large": 10, "multi_site": 10},
                     name_prefix=f"Unit{uid}_Instrument"),
            # Steam / WFI flow custody-grade meters.
            RoleSlot(role_id="flow_meter",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Unit{uid}_Flow_Meter"),
            # Sterile + jacket valves.
            RoleSlot(role_id="valve_actuator",
                     count_by_scale={"demo": 3, "small": 5, "medium": 7,
                                     "large": 9, "multi_site": 9},
                     name_prefix=f"Unit{uid}_Sterile_Valve"),
            # Agitator + pump VFDs.
            RoleSlot(role_id="vfd",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Unit{uid}_Agitator_VFD"),
            RoleSlot(role_id="distributed_io",
                     count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     name_prefix=f"Unit{uid}_IO"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Unit{uid}_Switch"),
        ),
    )


_BIOREACTOR_ZONES: tuple[ZoneDef, ...] = (
    _make_bioreactor_unit(1, "Bioreactor Train 1"),
    _make_bioreactor_unit(2, "Bioreactor Train 2"),
    _make_bioreactor_unit(3, "Bioreactor Train 3"),
)


_ZONE_PURIFICATION = ZoneDef(
    id="purification",
    name="Purification Suite",
    purdue_level=1.0,
    security_level="high",
    description=(
        "Tangential flow filtration + chromatography columns. Heavy "
        "flow-meter and analyzer instrumentation."
    ),
    role_slots=(
        RoleSlot(role_id="dcs_controller",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Purification_DCS"),
        RoleSlot(role_id="area_hmi",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Purification_HMI"),
        RoleSlot(role_id="flow_meter",
                 count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                 "large": 8, "multi_site": 8},
                 name_prefix="Purif_Flow_Meter"),
        RoleSlot(role_id="analyzer",
                 count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                 "large": 5, "multi_site": 5},
                 name_prefix="Purif_UV_Analyzer"),
        RoleSlot(role_id="valve_actuator",
                 count_by_scale={"demo": 3, "small": 5, "medium": 7,
                                 "large": 9, "multi_site": 9},
                 name_prefix="Purif_Sterile_Valve"),
        RoleSlot(role_id="vfd",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Purif_Pump_VFD"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Purification_Switch"),
    ),
)


_ZONE_FILL_FINISH = ZoneDef(
    id="fill_finish",
    name="Fill / Finish Suite",
    purdue_level=1.0,
    security_level="high",
    description=(
        "Aseptic vial filling + lyophilization + visual inspection."
    ),
    role_slots=(
        RoleSlot(role_id="cell_controller",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="FillFinish_PLC"),
        RoleSlot(role_id="area_hmi",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="FillFinish_HMI"),
        RoleSlot(role_id="servo",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Filler_Servo"),
        # Vision inspection of every vial (fill-volume + cosmetic).
        RoleSlot(role_id="vision_system",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Vial_Inspection"),
        RoleSlot(role_id="barcode_scanner",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 3, "multi_site": 3},
                 name_prefix="Vial_Track_Barcode"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                 "large": 5, "multi_site": 5},
                 name_prefix="Lyophilizer_Sensor"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="FillFinish_Switch"),
    ),
)


_ZONE_UTILITIES = ZoneDef(
    id="utilities",
    name="Clean Utilities",
    purdue_level=1.0,
    security_level="standard",
    description=(
        "WFI (water for injection) + clean steam + compressed air."
    ),
    role_slots=(
        RoleSlot(role_id="cell_controller",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 2, "multi_site": 2},
                 optional_at=("demo",),
                 name_prefix="Utility_PLC"),
        RoleSlot(role_id="flow_meter",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="WFI_Flow_Meter"),
        RoleSlot(role_id="analyzer",
                 count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 name_prefix="WFI_TOC_Analyzer"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                 "large": 5, "multi_site": 5},
                 name_prefix="Utility_Sensor"),
        RoleSlot(role_id="vfd",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Utility_Pump_VFD"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Utility_Switch"),
    ),
)


_ZONE_SAFETY = ZoneDef(
    id="safety",
    name="Safety Instrumented System",
    purdue_level=1.0,
    security_level="critical",
    description=(
        "SIL-3 SIS — pressure relief + over-temp shutdown + emergency."
    ),
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


_C_IDMZ_OPS = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ Operations",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("https", "snmp", "opc_ua", "rdp", "ssh"),
    description="GMP audit trail + admin pivot + AV / patch.",
)


def _make_ops_to_unit_conduit(uid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_unit{uid}",
        name=f"Operations ↔ Bioreactor {uid}",
        source_zone="operations",
        target_zone=f"unit{uid}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=("opc_ua", "modbus_tcp", "snmp"),
        description=f"DCS HMI / batch / historian to bioreactor train {uid}.",
    )


_BIOREACTOR_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_ops_to_unit_conduit(i) for i in range(1, 4)
)


_C_OPS_TO_PURIFICATION = ConduitTemplate(
    id="operations_to_purification",
    name="Operations ↔ Purification",
    source_zone="operations",
    target_zone="purification",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("opc_ua", "modbus_tcp", "snmp"),
    description="DCS HMI to purification suite.",
)


_C_OPS_TO_FILL = ConduitTemplate(
    id="operations_to_fill_finish",
    name="Operations ↔ Fill / Finish",
    source_zone="operations",
    target_zone="fill_finish",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("opc_ua", "modbus_tcp", "ethernet_ip", "snmp"),
    description="DCS HMI to fill / finish suite.",
)


_C_OPS_TO_UTILITIES = ConduitTemplate(
    id="operations_to_utilities",
    name="Operations ↔ Clean Utilities",
    source_zone="operations",
    target_zone="utilities",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("modbus_tcp", "snmp"),
    description="WFI / clean steam / compressed air monitoring.",
)


_C_OPS_TO_SAFETY = ConduitTemplate(
    id="operations_to_safety",
    name="Operations ↔ Safety",
    source_zone="operations",
    target_zone="safety",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("opc_ua", "ssh", "snmp"),
    description="Engineering reach to SIS for config check; NMS SNMP polls.",
)


def _make_unit_to_safety_conduit(uid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"unit{uid}_to_safety",
        name=f"Bioreactor {uid} ↔ Safety",
        source_zone=f"unit{uid}",
        target_zone="safety",
        direction="bidirectional",
        security_level="critical",
        allowed_protocols=("modbus_tcp", "snmp"),
        description=(
            f"Bioreactor {uid} ↔ SIS handshake (over-pressure / temp)."
        ),
    )


_UNIT_SAFETY_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_unit_to_safety_conduit(i) for i in range(1, 4)
)


ARCHETYPE = Archetype(
    id="manufacturing_pharma_bioreactor",
    name="Manufacturing — Pharma / Vaccine Bioreactor Plant",
    vertical=Vertical.MANUFACTURING_PROCESS.value,
    pattern=ArchitecturePattern.CONTINUOUS_DCS,
    description=(
        "GMP-regulated pharma / vaccine plant. Three bioreactor trains "
        "with dense analyzer instrumentation (pH / DO / OD / glucose / "
        "off-gas), tangential flow filtration + chromatography in "
        "purification suite, vial filling + lyophilization in fill / "
        "finish, dedicated SIL-3 SIS for over-pressure / over-temp, "
        "clean utilities (WFI / clean steam / compressed air). Heavy "
        "historian + batch + asset management for 21 CFR Part 11."
    ),
    default_vendor_profile=VendorProfile.DCS_EMERSON,
    supported_vendor_profiles=(
        VendorProfile.DCS_EMERSON,
        VendorProfile.DCS_HONEYWELL,
        VendorProfile.DCS_YOKOGAWA,
        VendorProfile.DCS_ABB,
    ),
    zones=(
        _ZONE_IDMZ, _ZONE_OPERATIONS,
    ) + _BIOREACTOR_ZONES + (
        _ZONE_PURIFICATION, _ZONE_FILL_FINISH,
        _ZONE_UTILITIES, _ZONE_SAFETY,
    ),
    conduits=(
        (_C_IDMZ_OPS,)
        + _BIOREACTOR_CONDUITS
        + (_C_OPS_TO_PURIFICATION, _C_OPS_TO_FILL,
           _C_OPS_TO_UTILITIES, _C_OPS_TO_SAFETY)
        + _UNIT_SAFETY_CONDUITS
    ),
    min_scale=ScaleTier.SMALL,
    cell_isolation_default="conduit_gated",
    notes=(
        "All 3 bioreactor trains always present. Each train has 6-10 "
        "analyzers covering the standard upstream-process panel.",
        "Purification suite uses flow_meter heavily (UV-280 monitoring + "
        "TFF retentate / permeate flow + chromatography step gradient).",
        "SIS is SIL-3 — every bioreactor has a safety conduit to it for "
        "over-pressure / over-temperature / agitator-fault shutdown.",
        "21 CFR Part 11 audit trail flows go via historian + asset_mgmt "
        "+ alarm_event_server (always present).",
    ),
)
