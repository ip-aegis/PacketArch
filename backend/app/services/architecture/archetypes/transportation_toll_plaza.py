# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Transportation — toll plaza archetype.

Distinct from the ATMS corridor pattern: a toll plaza clusters many
device classes (toll lanes, ANPR cameras, DMS, surveillance) at one
site, not distributed across many cabinets. Modeled as TMC + N "lane"
zones (each lane has a toll controller + DSRC RSU + ANPR camera + lane
gate), plus an approach zone with DMS signs and PTZ surveillance.
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
    name="IT/Toll Boundary",
    purdue_level=3.5,
    security_level="critical",
    description="L3.5 boundary — back-office settlement integration.",
    role_slots=(
        RoleSlot(role_id="jump_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Jump_Server"),
        RoleSlot(role_id="reverse_proxy",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Public_Web"),
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


_ZONE_TMC = ZoneDef(
    id="operations",
    name="Toll Plaza Control Center",
    purdue_level=3.0,
    security_level="high",
    description="L3 plaza ops — ATMS master, NMS, engineering, historian.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Plaza_ATMS_Master"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Plaza_Historian"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Plaza_Eng_Workstation"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Plaza_NMS"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="TMC_Core_Switch"),
    ),
)


_ZONE_APPROACH = ZoneDef(
    id="approach",
    name="Plaza Approach",
    purdue_level=1.0,
    security_level="standard",
    description="Approach signage + surveillance.",
    role_slots=(
        RoleSlot(role_id="dms_sign",
                 count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 name_prefix="Approach_DMS"),
        RoleSlot(role_id="ptz_camera",
                 count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 optional_at=("demo",),
                 name_prefix="Approach_PTZ"),
        RoleSlot(role_id="cctv_camera",
                 count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 optional_at=("demo",),
                 name_prefix="Approach_CCTV"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Approach_Switch"),
    ),
)


def _make_lane_zone(lane_id: int, lane_name: str) -> ZoneDef:
    """Each toll lane: one toll-lane controller + DSRC RSU + ANPR + switch."""
    return ZoneDef(
        id=f"lane{lane_id}",
        name=lane_name,
        purdue_level=1.0,
        security_level="standard",
        description=f"Toll lane {lane_id} — ETC controller + RSU + ANPR.",
        role_slots=(
            RoleSlot(role_id="toll_lane_controller",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Lane{lane_id}_ETC"),
            RoleSlot(role_id="toll_rsu",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Lane{lane_id}_RSU"),
            RoleSlot(role_id="anpr_camera",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     name_prefix=f"Lane{lane_id}_ANPR"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Lane{lane_id}_Switch"),
        ),
    )


_LANE_ZONES: tuple[ZoneDef, ...] = tuple(
    _make_lane_zone(i, f"Lane {i}") for i in range(1, 9)
)


_C_IDMZ_TMC = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ TMC",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("https", "snmp", "ssh"),
    description="Back-office settlement integration + admin pivot.",
)


_C_TMC_TO_APPROACH = ConduitTemplate(
    id="operations_to_approach",
    name="TMC ↔ Approach",
    source_zone="operations",
    target_zone="approach",
    direction="bidirectional",
    security_level="standard",
    allowed_protocols=("snmp", "rtsp", "https", "ntcip"),
    description="ATMS master polls approach DMS + cameras.",
)


def _make_tmc_to_lane_conduit(lane_id: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_lane{lane_id}",
        name=f"TMC ↔ Lane {lane_id}",
        source_zone="operations",
        target_zone=f"lane{lane_id}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=("snmp", "rtsp", "https"),
        description=(
            f"ATMS master ↔ lane {lane_id} ETC + RSU + ANPR; "
            "transactions + camera streams."
        ),
    )


_LANE_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_tmc_to_lane_conduit(i) for i in range(1, 9)
)


# Lane counts: small=2 (toll booth pair), medium=4, large=6, multi_site=8.
ARCHETYPE = Archetype(
    id="transportation_toll_plaza",
    name="Transportation — Toll Plaza",
    vertical=Vertical.TRANSPORTATION_ITS.value,
    pattern=ArchitecturePattern.ATMS_CORRIDOR,  # closest existing pattern
    description=(
        "Toll plaza with electronic toll collection (ETC) and ANPR "
        "enforcement. Each lane has a Kapsch toll-lane controller, "
        "Q-Free DSRC RSU, Hikvision ANPR camera, and lane switch. "
        "Approach zone has Daktronics DMS signs and Pelco / Bosch "
        "surveillance cameras. TMC at L3 with ATMS master + historian "
        "+ NMS."
    ),
    default_vendor_profile=VendorProfile.ATMS_NTCIP,
    supported_vendor_profiles=(VendorProfile.ATMS_NTCIP,),
    zones=(_ZONE_IDMZ, _ZONE_TMC, _ZONE_APPROACH) + _LANE_ZONES,
    conduits=(_C_IDMZ_TMC, _C_TMC_TO_APPROACH) + _LANE_CONDUITS,
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="off",
    notes=(
        "Lane counts: DEMO=1, SMALL=2 (toll booth pair), MEDIUM=4, "
        "LARGE=6, MULTI_SITE=8.",
        "Each lane is one ETC system: Kapsch lane controller aggregates "
        "RSU transactions + ANPR enforcement.",
    ),
)
