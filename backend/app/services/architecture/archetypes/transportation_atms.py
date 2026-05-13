# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Transportation ATMS archetype.

Advanced Traffic Management System: central master + per-intersection
roadside cabinet controllers communicating over NTCIP (which rides on
SNMP). Distinct from manufacturing — geographically distributed,
read-mostly, master-poll pattern.
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
    name="IT/Traffic Boundary",
    purdue_level=3.5,
    security_level="critical",
    description="L3.5 boundary — public web exposure, vendor remote.",
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
    name="Traffic Management Center",
    purdue_level=3.0,
    security_level="high",
    description="L3 ATMS master + operator HMI + historian + NMS.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="ATMS_Master"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Traffic_Historian"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Traffic_Eng_Workstation"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="ATMS_NMS"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="TMC_Core_Switch"),
    ),
)


def _make_intersection_zone(iid: int, iname: str) -> ZoneDef:
    """Roadside cabinet: traffic controller + auxiliaries (CCTV, DMS,
    ANPR, RWIS) + switch. Now includes specific camera / DMS / RWIS
    roles instead of a single generic cabinet stand-in (Phase 9 fix
    for the depth lost in the original archetype refactor)."""
    return ZoneDef(
        id=f"intersection{iid}",
        name=iname,
        purdue_level=1.0,
        security_level="standard",
        description=f"Cabinet {iid} — traffic controller + ITS auxiliaries.",
        role_slots=(
            RoleSlot(role_id="traffic_controller",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Intersection{iid}_TrafficCtrl"),
            # CCTV at every cabinet from SMALL+; PTZ at MEDIUM+ for
            # active surveillance in urban / corridor deployments.
            RoleSlot(role_id="cctv_camera",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     optional_at=("demo",),
                     name_prefix=f"Intersection{iid}_CCTV"),
            RoleSlot(role_id="ptz_camera",
                     count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     optional_at=("demo", "small"),
                     name_prefix=f"Intersection{iid}_PTZ"),
            # DMS sign at the intersection (e.g. ramp-meter advisory).
            RoleSlot(role_id="dms_sign",
                     count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     optional_at=("demo", "small"),
                     name_prefix=f"Intersection{iid}_DMS"),
            # Cabinet aux (kept as a generic catch-all for non-specific
            # equipment like detector racks, beacons, etc.).
            RoleSlot(role_id="cabinet_controller",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     optional_at=("demo",),
                     name_prefix=f"Intersection{iid}_Aux"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Intersection{iid}_Switch"),
        ),
    )


_INTERSECTION_ZONES: tuple[ZoneDef, ...] = tuple(
    _make_intersection_zone(i, f"Intersection {i}") for i in range(1, 17)
)


_C_IDMZ_TMC = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ TMC",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("https", "snmp", "ssh"),
    description="Public-facing dashboards + vendor admin access.",
)


def _make_tmc_to_intersection_conduit(iid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_intersection{iid}",
        name=f"TMC ↔ Intersection {iid}",
        source_zone="operations",
        target_zone=f"intersection{iid}",
        direction="bidirectional",
        security_level="standard",
        allowed_protocols=("snmp", "https"),
        description=f"ATMS master polls intersection {iid} via NTCIP/SNMP.",
    )


_INTERSECTION_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_tmc_to_intersection_conduit(i) for i in range(1, 17)
)


ARCHETYPE = Archetype(
    id="transportation_atms_corridor",
    name="Transportation — ATMS Corridor",
    vertical=Vertical.TRANSPORTATION_ITS.value,
    pattern=ArchitecturePattern.ATMS_CORRIDOR,
    description=(
        "Advanced Traffic Management System for an urban corridor or "
        "highway: central TMC with ATMS master + operator HMI + NMS, "
        "and per-intersection roadside cabinets running ATC/2070-class "
        "controllers. Communication is NTCIP-over-SNMP; a single "
        "operator manages tens to hundreds of intersections."
    ),
    default_vendor_profile=VendorProfile.ATMS_NTCIP,
    supported_vendor_profiles=(VendorProfile.ATMS_NTCIP,),
    zones=(_ZONE_IDMZ, _ZONE_TMC) + _INTERSECTION_ZONES,
    conduits=(_C_IDMZ_TMC,) + _INTERSECTION_CONDUITS,
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="off",
    notes=(
        "Intersection counts: DEMO=1, SMALL=3, MEDIUM=6, LARGE=10, "
        "MULTI_SITE=16.",
        "NTCIP rides on SNMP — that's why SNMP from the ATMS master is "
        "operationally legitimate (not just admin-style).",
    ),
)
