# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Water utility — master/remote SCADA archetype.

Central control room with SCADA + RTAC; field RTUs at pump stations,
storage, lift stations communicating over WAN/cellular. Distinct from
manufacturing in that L2 area-supervision is mostly absent — operators
manage everything from the central HMI.
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
    description="L3.5 IT/OT boundary (collapses into central at small scale).",
    role_slots=(
        RoleSlot(role_id="jump_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_Jump_Server"),
        RoleSlot(role_id="remote_access_gateway",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DMZ_Remote_Access_GW"),
        RoleSlot(role_id="patch_staging_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_Patch_Server"),
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


_ZONE_CENTRAL = ZoneDef(
    id="central",
    name="Central Control",
    purdue_level=3.0,
    security_level="high",
    description="L3 central control room — SCADA, historian, RTAC, NMS.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Central_SCADA_Server"),
        RoleSlot(role_id="scada_standby",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="Central_SCADA_Standby"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Central_Historian"),
        RoleSlot(role_id="aggregator_rtu",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Central_RTAC",
                 role_hint="Master RTU"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Central_Eng_Workstation"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Central_NMS"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Central_Core_Switch"),
    ),
)


def _make_station_zone(sid: int, sname: str) -> ZoneDef:
    """Pump station / lift station zone — typically a single RTU + small
    field-instrument complement plus a pump VFD."""
    return ZoneDef(
        id=f"station{sid}",
        name=sname,
        purdue_level=1.0,
        security_level="standard",
        description=f"Remote site {sid} — RTU + pumps + instruments.",
        role_slots=(
            RoleSlot(role_id="field_rtu",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Station{sid}_RTU"),
            RoleSlot(role_id="vfd",
                     count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                     "large": 2, "multi_site": 2},
                     name_prefix=f"Station{sid}_Pump_VFD"),
            RoleSlot(role_id="field_instrument",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 3, "multi_site": 3},
                     name_prefix=f"Station{sid}_Instrument"),
            RoleSlot(role_id="valve_actuator",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     optional_at=("demo",),
                     name_prefix=f"Station{sid}_Valve"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Station{sid}_Switch"),
        ),
    )


_STATION_ZONES: tuple[ZoneDef, ...] = tuple(
    _make_station_zone(i, f"Pump Station {i}") for i in range(1, 13)
)


_C_IDMZ_CENTRAL = ConduitTemplate(
    id="idmz_to_central",
    name="IDMZ ↔ Central",
    source_zone="idmz",
    target_zone="central",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("https", "snmp", "rdp", "ssh"),
    description="Jump-server pivot, vendor remote access, AV/patch.",
)


def _make_central_to_station_conduit(sid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"central_to_station{sid}",
        name=f"Central ↔ Station {sid}",
        source_zone="central",
        target_zone=f"station{sid}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=("modbus_tcp", "dnp3", "iec104", "snmp", "opc_ua"),
        description=f"Central RTAC + SCADA reach to station {sid} field RTU.",
    )


_STATION_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_central_to_station_conduit(i) for i in range(1, 13)
)


ARCHETYPE = Archetype(
    id="water_utility_master_remote",
    name="Water Utility — Master/Remote SCADA",
    vertical=Vertical.WATER_UTILITY.value,
    pattern=ArchitecturePattern.MASTER_REMOTE_SCADA,
    description=(
        "Municipal / regional water utility with central control room and "
        "remote pump stations / lift stations. RTAC at central aggregates "
        "field RTUs over WAN; SCADA provides operator view; vendor remote "
        "access for service techs."
    ),
    default_vendor_profile=VendorProfile.MIXED_FIELD,
    supported_vendor_profiles=(
        VendorProfile.MIXED_FIELD,
        VendorProfile.SCADAPACK,
        VendorProfile.SCHNEIDER_SHOP,
    ),
    zones=(_ZONE_IDMZ, _ZONE_CENTRAL) + _STATION_ZONES,
    conduits=(_C_IDMZ_CENTRAL,) + _STATION_CONDUITS,
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Station counts: DEMO=1, SMALL=3, MEDIUM=5, LARGE=8, "
        "MULTI_SITE=12.",
        "IDMZ collapses into central at DEMO/SMALL (jump server is "
        "optional below MEDIUM).",
        "Field RTUs talk DNP3 / Modbus TCP to RTAC over WAN; vendor "
        "selection drives whether DNP3 or IEC 104 dominates.",
    ),
)
