# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Building automation archetype — BAS supervisor + zone controllers.

BACnet/IP-centric: a BAS supervisor (Niagara / Distech / Honeywell EBI)
sits at L3 and aggregates per-zone field controllers. Each zone has
HVAC field instruments, valves, fan VFDs, and a BAS field controller
(JACE / JENE / Distech ECY).
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
    name="IT/BAS Boundary",
    purdue_level=3.5,
    security_level="critical",
    description="L3.5 boundary — IT integration of BAS.",
    role_slots=(
        RoleSlot(role_id="jump_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Jump_Server"),
        RoleSlot(role_id="remote_access_gateway",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Remote_Access_GW"),
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
    name="BAS Supervisor",
    purdue_level=3.0,
    security_level="high",
    description="L3 BAS supervisor — operator workstation, historian, NMS.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="BAS_Supervisor"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="BAS_Historian"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="BAS_Eng_Workstation"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="BAS_NMS"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="BAS_Core_Switch"),
    ),
)


def _make_bas_zone(zid: int, zname: str) -> ZoneDef:
    """Each BAS zone hosts a JACE supervisor + AHU + VAVs + room
    controllers + HVAC field. Phase 9 audit fix — restored vav, ahu,
    chiller, and room controllers as distinct roles."""
    return ZoneDef(
        id=f"zone{zid}",
        name=zname,
        purdue_level=1.0,
        security_level="standard",
        description=(
            f"BAS zone {zid} — JACE supervisor + AHU + VAVs + room "
            "controls + HVAC field."
        ),
        role_slots=(
            RoleSlot(role_id="bms_field_controller",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     name_prefix=f"Zone{zid}_BMS_Supervisor"),
            RoleSlot(role_id="ahu_controller",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     optional_at=("demo",),
                     name_prefix=f"Zone{zid}_AHU"),
            RoleSlot(role_id="vav_controller",
                     count_by_scale={"demo": 0, "small": 2, "medium": 4,
                                     "large": 6, "multi_site": 6},
                     optional_at=("demo",),
                     name_prefix=f"Zone{zid}_VAV"),
            RoleSlot(role_id="room_controller",
                     count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     optional_at=("demo",),
                     name_prefix=f"Zone{zid}_Room"),
            RoleSlot(role_id="vfd",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Zone{zid}_VFD"),
            RoleSlot(role_id="field_instrument",
                     count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                     "large": 6, "multi_site": 6},
                     name_prefix=f"Zone{zid}_Sensor"),
            RoleSlot(role_id="valve_actuator",
                     count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     optional_at=("demo",),
                     name_prefix=f"Zone{zid}_Valve"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Zone{zid}_Switch"),
        ),
    )


_ZONE_PLANT = ZoneDef(
    id="plant",
    name="Central Plant",
    purdue_level=1.0,
    security_level="standard",
    description="Central chilled-water + boiler plant.",
    role_slots=(
        RoleSlot(role_id="chiller_controller",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 2, "multi_site": 2},
                 optional_at=("demo", "small"),
                 name_prefix="Plant_Chiller_Controller"),
        RoleSlot(role_id="vfd",
                 count_by_scale={"demo": 0, "small": 0, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 optional_at=("demo", "small"),
                 name_prefix="Plant_Pump_VFD"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 0, "small": 0, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 optional_at=("demo", "small"),
                 name_prefix="Plant_Sensor"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="Plant_Switch"),
    ),
)


_ZONE_BAS_ZONES: tuple[ZoneDef, ...] = tuple(
    _make_bas_zone(i, f"BAS Zone {i}") for i in range(1, 5)
)


_C_IDMZ_OPS = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ BAS Supervisor",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("https", "snmp", "rdp", "ssh"),
    description="Tenant-side admin access to BAS supervisor.",
)


def _make_ops_to_zone_conduit(zid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_zone{zid}",
        name=f"BAS Supervisor ↔ Zone {zid}",
        source_zone="operations",
        target_zone=f"zone{zid}",
        direction="bidirectional",
        security_level="standard",
        allowed_protocols=("bacnet", "modbus_tcp", "snmp"),
        description=f"BAS supervisor reach to zone {zid} BMS controller.",
    )


_BAS_ZONE_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_ops_to_zone_conduit(i) for i in range(1, 5)
)


ARCHETYPE = Archetype(
    id="building_automation_bas_supervisor",
    name="Building Automation — BAS Supervisor",
    vertical=Vertical.BUILDING_AUTOMATION.value,
    pattern=ArchitecturePattern.BAS_SUPERVISOR,
    description=(
        "BACnet/IP building automation: a BAS supervisor (Niagara JACE / "
        "Distech / Honeywell EBI) at L3 supervises per-zone field "
        "controllers handling HVAC, lighting, and access control. "
        "Standard for commercial offices, university campuses, "
        "data-center facility-side BAS."
    ),
    default_vendor_profile=VendorProfile.BAS_TRIDIUM,
    supported_vendor_profiles=(
        VendorProfile.BAS_TRIDIUM,
    ),
    zones=(_ZONE_IDMZ, _ZONE_OPERATIONS) + _ZONE_BAS_ZONES + (_ZONE_PLANT,),
    conduits=(_C_IDMZ_OPS,) + _BAS_ZONE_CONDUITS + (
        ConduitTemplate(
            id="operations_to_plant",
            name="BAS Supervisor ↔ Central Plant",
            source_zone="operations",
            target_zone="plant",
            direction="bidirectional",
            security_level="standard",
            allowed_protocols=("bacnet", "modbus_tcp", "snmp"),
            description="BAS supervisor reach to chiller / boiler plant.",
        ),
    ),
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Zone counts: DEMO=1, SMALL=2, MEDIUM=3, LARGE/MULTI_SITE=4.",
        "BACnet/IP is the default; vendor profile drives whether MS/TP "
        "fallback or pure /IP is used.",
    ),
)
