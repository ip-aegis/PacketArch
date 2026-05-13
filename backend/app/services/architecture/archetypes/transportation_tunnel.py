# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Transportation — highway/road tunnel archetype.

Tunnel control combines life-safety (ventilation, fire detection),
traveler info (DMS portals, ramp meters), and operations monitoring
(CCTV, RWIS at portals). Modeled as TMC + a portal zone for entry /
exit DMS + tunnel-section zones for ventilation, lighting, fire.
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
    name="IT/Tunnel Boundary",
    purdue_level=3.5,
    security_level="critical",
    description="L3.5 boundary — DOT operations integration.",
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
    name="Tunnel Control Center",
    purdue_level=3.0,
    security_level="high",
    description="L3 ops — ATMS master, historian, NMS, engineering.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Tunnel_ATMS_Master"),
        RoleSlot(role_id="scada_standby",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="Tunnel_ATMS_Standby"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Tunnel_Historian"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Tunnel_Eng_Workstation"),
        RoleSlot(role_id="alarm_event_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="Tunnel_Alarm_Server"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Tunnel_NMS"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="TMC_Core_Switch"),
    ),
)


_ZONE_PORTAL = ZoneDef(
    id="portal",
    name="Tunnel Portals (Entry / Exit)",
    purdue_level=1.0,
    security_level="standard",
    description="Entry / exit portals — DMS, ANPR, RWIS, surveillance.",
    role_slots=(
        RoleSlot(role_id="dms_sign",
                 count_by_scale={"demo": 1, "small": 2, "medium": 4,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Portal_DMS"),
        RoleSlot(role_id="anpr_camera",
                 count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 optional_at=("demo",),
                 name_prefix="Portal_ANPR"),
        RoleSlot(role_id="ptz_camera",
                 count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 optional_at=("demo",),
                 name_prefix="Portal_PTZ"),
        RoleSlot(role_id="rwis_station",
                 count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Portal_RWIS"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Portal_Switch"),
    ),
)


def _make_section_zone(sid: int, sname: str) -> ZoneDef:
    """Tunnel section: ventilation + lighting + fire-detection +
    surveillance. Modeled with cabinet_controller (mech / fire) plus
    fixed-CCTV cameras plus a section switch."""
    return ZoneDef(
        id=f"tunnel_section{sid}",
        name=sname,
        purdue_level=1.0,
        security_level="high",
        description=f"Tunnel section {sid} — ventilation / lighting / CCTV.",
        role_slots=(
            RoleSlot(role_id="cabinet_controller",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 3, "multi_site": 3},
                     name_prefix=f"Tunnel_Section{sid}_Cabinet"),
            RoleSlot(role_id="cctv_camera",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Tunnel_Section{sid}_CCTV"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Tunnel_Section{sid}_Switch"),
        ),
    )


_SECTION_ZONES: tuple[ZoneDef, ...] = tuple(
    _make_section_zone(i, f"Tunnel Section {i}") for i in range(1, 5)
)


_C_IDMZ_TMC = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ TMC",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("https", "snmp", "ssh"),
    description="DOT operations + admin pivot.",
)


_C_TMC_TO_PORTAL = ConduitTemplate(
    id="operations_to_portal",
    name="TMC ↔ Portal",
    source_zone="operations",
    target_zone="portal",
    direction="bidirectional",
    security_level="standard",
    allowed_protocols=("snmp", "rtsp", "https", "ntcip"),
    description="ATMS master polls portal DMS / cameras / RWIS.",
)


def _make_tmc_to_section_conduit(sid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_tunnel_section{sid}",
        name=f"TMC ↔ Section {sid}",
        source_zone="operations",
        target_zone=f"tunnel_section{sid}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=("snmp", "rtsp", "https"),
        description=(
            f"ATMS master ↔ tunnel section {sid} cabinets + CCTV."
        ),
    )


_SECTION_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_tmc_to_section_conduit(i) for i in range(1, 5)
)


ARCHETYPE = Archetype(
    id="transportation_tunnel",
    name="Transportation — Highway Tunnel",
    vertical=Vertical.TRANSPORTATION_ITS.value,
    pattern=ArchitecturePattern.ATMS_CORRIDOR,
    description=(
        "Highway / road tunnel control system. Tunnel sections each "
        "host ventilation / lighting / fire-detection cabinets and "
        "fixed CCTV. Portal zones (entry / exit) carry DMS signs, "
        "ANPR cameras, PTZ surveillance, and RWIS road-weather "
        "stations. TMC at L3 with ATMS master + standby + alarm "
        "server + historian + NMS."
    ),
    default_vendor_profile=VendorProfile.ATMS_NTCIP,
    supported_vendor_profiles=(VendorProfile.ATMS_NTCIP,),
    zones=(_ZONE_IDMZ, _ZONE_TMC, _ZONE_PORTAL) + _SECTION_ZONES,
    conduits=(_C_IDMZ_TMC, _C_TMC_TO_PORTAL) + _SECTION_CONDUITS,
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Tunnel section counts: DEMO=1, SMALL=2, MEDIUM=3, LARGE=4.",
        "Cabinets are stand-ins for ventilation / lighting / fire — all "
        "use cabinet_controller role at L1.",
        "Standby ATMS master at MEDIUM+ for life-safety reliability.",
    ),
)
