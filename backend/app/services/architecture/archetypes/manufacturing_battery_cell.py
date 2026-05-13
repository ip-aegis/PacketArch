# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""EV battery cell manufacturing archetype.

Multi-stage process: coating + drying (continuous web), calendaring +
slitting (discrete with high-precision servos), formation + aging
(racks of charge/discharge cyclers — heavy power telemetry), quality
(vision / X-ray / hi-pot), pack assembly (robotic). Each stage is a
distinct OT shape — this archetype shows off the breadth of patterns
in one plant.
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
    description="L3.5 — IT integration + vendor remote service.",
    role_slots=(
        RoleSlot(role_id="jump_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DMZ_Jump_Server"),
        RoleSlot(role_id="remote_access_gateway",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Remote_Service_GW"),
        RoleSlot(role_id="patch_staging_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Patch_Server"),
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
    description="L3 control room — SCADA, MES, historian, NMS.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Plant_SCADA_Primary"),
        RoleSlot(role_id="scada_standby",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Plant_SCADA_Standby"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Plant_Historian"),
        RoleSlot(role_id="mes_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Battery_MES"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Eng_Workstation"),
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


# Stage 1: Coating + drying (continuous web, DCS-flavored).
_ZONE_COATING = ZoneDef(
    id="cell1",
    name="Coating + Drying",
    purdue_level=1.0,
    security_level="standard",
    description=(
        "Continuous web coating — slot-die / gravure + drying ovens. "
        "DCS-flavored with web-tension control."
    ),
    role_slots=(
        RoleSlot(role_id="dcs_controller",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Coating_DCS"),
        RoleSlot(role_id="area_hmi",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Coating_HMI"),
        RoleSlot(role_id="vfd",
                 count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                 "large": 8, "multi_site": 8},
                 name_prefix="Coating_Web_Drive"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 3, "small": 5, "medium": 7,
                                 "large": 9, "multi_site": 9},
                 name_prefix="Coating_Sensor"),
        RoleSlot(role_id="analyzer",
                 count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 name_prefix="Coating_Thickness"),
        RoleSlot(role_id="vision_system",
                 count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 name_prefix="Coating_Defect_Vision"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Coating_Switch"),
    ),
)


# Stage 2: Calendaring + slitting (discrete + servo motion).
_ZONE_CALENDARING = ZoneDef(
    id="cell2",
    name="Calendaring + Slitting",
    purdue_level=1.0,
    security_level="standard",
    description=(
        "Roll-to-roll calendaring + slitting. Servo-precision motion."
    ),
    role_slots=(
        RoleSlot(role_id="cell_controller",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Calendar_PLC"),
        RoleSlot(role_id="area_hmi",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Calendar_HMI"),
        RoleSlot(role_id="servo",
                 count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                 "large": 8, "multi_site": 8},
                 name_prefix="Slitter_Servo"),
        RoleSlot(role_id="vfd",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Calendar_Drive"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                 "large": 5, "multi_site": 5},
                 name_prefix="Calendar_Sensor"),
        RoleSlot(role_id="vision_system",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Slitter_Edge_Vision"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Calendar_Switch"),
    ),
)


# Stage 3: Formation + aging (battery cyclers — heavy power telemetry).
_ZONE_FORMATION = ZoneDef(
    id="cell3",
    name="Formation + Aging",
    purdue_level=1.0,
    security_level="standard",
    description=(
        "Charge / discharge cycling racks — heavy power instrumentation."
    ),
    role_slots=(
        RoleSlot(role_id="cell_controller",
                 count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 name_prefix="Formation_PLC"),
        RoleSlot(role_id="area_hmi",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Formation_HMI"),
        # Cyclers modeled as VFDs (power-electronics class device).
        RoleSlot(role_id="vfd",
                 count_by_scale={"demo": 4, "small": 8, "medium": 16,
                                 "large": 24, "multi_site": 24},
                 name_prefix="Formation_Cycler"),
        # Revenue meters at every cycler bank for energy accounting.
        RoleSlot(role_id="power_meter",
                 count_by_scale={"demo": 1, "small": 2, "medium": 4,
                                 "large": 6, "multi_site": 6},
                 name_prefix="Formation_Power_Meter"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                 "large": 8, "multi_site": 8},
                 name_prefix="Formation_Cell_Sensor"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Formation_Switch"),
    ),
)


# Stage 4: Quality + final test (vision / X-ray / hi-pot).
_ZONE_QUALITY = ZoneDef(
    id="cell4",
    name="Quality Inspection",
    purdue_level=1.0,
    security_level="standard",
    description=(
        "Vision + X-ray + hi-pot final test. Heavy vision instrumentation."
    ),
    role_slots=(
        RoleSlot(role_id="cell_controller",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Quality_PLC"),
        RoleSlot(role_id="vision_system",
                 count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                 "large": 8, "multi_site": 8},
                 name_prefix="Quality_Vision"),
        # Hi-pot test measurement.
        RoleSlot(role_id="analyzer",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="HiPot_Tester"),
        RoleSlot(role_id="barcode_scanner",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Quality_Barcode"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Quality_Switch"),
    ),
)


# Stage 5: Pack assembly (robotic).
_ZONE_ASSEMBLY = ZoneDef(
    id="cell5",
    name="Pack Assembly",
    purdue_level=1.0,
    security_level="standard",
    description=(
        "Cell-to-pack robotic assembly + module welding."
    ),
    role_slots=(
        RoleSlot(role_id="cell_controller",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 name_prefix="Assembly_PLC"),
        RoleSlot(role_id="safety_controller",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Assembly_Safety_PLC"),
        RoleSlot(role_id="robot_controller",
                 count_by_scale={"demo": 1, "small": 2, "medium": 4,
                                 "large": 6, "multi_site": 6},
                 name_prefix="Assembly_Robot"),
        RoleSlot(role_id="area_hmi",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Assembly_HMI"),
        RoleSlot(role_id="vfd",
                 count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                 "large": 5, "multi_site": 5},
                 name_prefix="Assembly_VFD"),
        RoleSlot(role_id="distributed_io",
                 count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                 "large": 5, "multi_site": 5},
                 name_prefix="Assembly_IO"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Assembly_Switch"),
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
    description="Plant IT integration + vendor remote service.",
)


def _make_ops_to_cell_conduit(cid: int, label: str) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_cell{cid}",
        name=f"Operations ↔ {label}",
        source_zone="operations",
        target_zone=f"cell{cid}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=("opc_ua", "modbus_tcp", "ethernet_ip", "snmp"),
        description=f"Plant control reach to {label}.",
    )


_CELL_CONDUITS: tuple[ConduitTemplate, ...] = (
    _make_ops_to_cell_conduit(1, "Coating"),
    _make_ops_to_cell_conduit(2, "Calendaring"),
    _make_ops_to_cell_conduit(3, "Formation"),
    _make_ops_to_cell_conduit(4, "Quality"),
    _make_ops_to_cell_conduit(5, "Assembly"),
)


ARCHETYPE = Archetype(
    id="manufacturing_battery_cell",
    name="Manufacturing — EV Battery Cell Plant",
    vertical=Vertical.MANUFACTURING_DISCRETE.value,
    pattern=ArchitecturePattern.DISCRETE_CELL,
    description=(
        "EV battery cell manufacturing — five-stage line: coating + "
        "drying (continuous web with thickness analyzer + defect vision); "
        "calendaring + slitting (servo precision motion); formation + "
        "aging (racks of charge/discharge cyclers with revenue power "
        "metering); quality (vision + hi-pot test); pack assembly "
        "(robotic). Each stage exercises a different OT pattern."
    ),
    default_vendor_profile=VendorProfile.MULTI_VENDOR,
    supported_vendor_profiles=(
        VendorProfile.MULTI_VENDOR,
        VendorProfile.SIEMENS_SHOP,
        VendorProfile.ROCKWELL_SHOP,
    ),
    zones=(
        _ZONE_IDMZ, _ZONE_OPERATIONS,
        _ZONE_COATING, _ZONE_CALENDARING, _ZONE_FORMATION,
        _ZONE_QUALITY, _ZONE_ASSEMBLY,
    ),
    conduits=(_C_IDMZ_OPS,) + _CELL_CONDUITS,
    min_scale=ScaleTier.SMALL,
    cell_isolation_default="conduit_gated",
    notes=(
        "All 5 process stages always present — they're the canonical "
        "cell-manufacturing flow.",
        "Formation cyclers modeled as VFDs (power-electronics class). "
        "16-24 cyclers at MEDIUM-LARGE scale plus 4-6 revenue meters.",
        "Quality station heavy on vision_system (X-ray + DCM imaging) "
        "and analyzer (hi-pot tester).",
    ),
)
