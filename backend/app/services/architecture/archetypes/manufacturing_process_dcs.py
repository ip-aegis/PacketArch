# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Process manufacturing archetype: DCS-driven continuous control.

Models pharma / specialty chemicals / food&beverage continuous lines.
Distinct from discrete cells: DCS controllers (DeltaV / Centum / Experion
/ 800xA) drive regulatory loops at high cadence; field instruments and
valve actuators dominate the field; safety system is in its own zone;
batch server orchestrates ISA-88 phases.
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


# ---------------------------------------------------------------------------
# IDMZ (L3.5)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Operations (L3)
# ---------------------------------------------------------------------------

_ZONE_OPERATIONS = ZoneDef(
    id="operations",
    name="Plant Operations",
    purdue_level=3.0,
    security_level="high",
    description="L3 plant operations — DCS HMI, historian, batch, NMS.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DCS_HMI_Server"),
        RoleSlot(role_id="scada_standby",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DCS_HMI_Standby"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Plant_Historian"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 2, "multi_site": 2},
                 name_prefix="Eng_Workstation"),
        RoleSlot(role_id="batch_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Batch_Server"),
        RoleSlot(role_id="alarm_event_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
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


# ---------------------------------------------------------------------------
# Process Unit N (L0 + L1 combined)
# ---------------------------------------------------------------------------

def _make_unit_zone(uid: int, uname: str) -> ZoneDef:
    """Process unit — DCS + per-unit HMI + batch + IO + instruments +
    analyzers + flow meters + valves + drives. Phase 9 audit fix added
    area_hmi, analyzer, flow_meter."""
    return ZoneDef(
        id=f"unit{uid}",
        name=uname,
        purdue_level=1.0,
        security_level="standard",
        description=f"Process unit {uid} — DCS controllers + field.",
        role_slots=(
            RoleSlot(role_id="dcs_controller",
                     count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     name_prefix=f"Unit{uid}_DCS_Controller"),
            RoleSlot(role_id="area_hmi",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     optional_at=("demo",),
                     name_prefix=f"Unit{uid}_Operator_HMI"),
            RoleSlot(role_id="batch_controller",
                     count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     optional_at=("demo", "small"),
                     name_prefix=f"Unit{uid}_Batch_PLC"),
            RoleSlot(role_id="distributed_io",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Unit{uid}_IO"),
            RoleSlot(role_id="field_instrument",
                     count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                     "large": 8, "multi_site": 8},
                     name_prefix=f"Unit{uid}_Instrument"),
            RoleSlot(role_id="analyzer",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     optional_at=("demo",),
                     name_prefix=f"Unit{uid}_Analyzer"),
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
                     count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     name_prefix=f"Unit{uid}_VFD"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Unit{uid}_Switch"),
        ),
    )


_UNIT_ZONES: tuple[ZoneDef, ...] = (
    _make_unit_zone(1, "Process Unit 1"),
    _make_unit_zone(2, "Process Unit 2"),
    _make_unit_zone(3, "Process Unit 3"),
    _make_unit_zone(4, "Process Unit 4"),
)


# ---------------------------------------------------------------------------
# Safety (L1, separate zone)
# ---------------------------------------------------------------------------

_ZONE_SAFETY = ZoneDef(
    id="safety",
    name="Safety Instrumented System",
    purdue_level=1.0,
    security_level="critical",
    description="SIL-rated safety controllers, isolated from process net.",
    role_slots=(
        RoleSlot(role_id="safety_controller",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 2, "multi_site": 2},
                 optional_at=("demo",),
                 name_prefix="SIS_Safety_Controller"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="SIS_Switch"),
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
    description="Jump-server pivot, replication, AV/patch sync.",
)


def _make_ops_to_unit_conduit(uid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_unit{uid}",
        name=f"Operations ↔ Unit {uid}",
        source_zone="operations",
        target_zone=f"unit{uid}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=("opc_ua", "modbus_tcp", "ethernet_ip", "snmp"),
        description=(
            f"DCS HMI / historian / engineering reach to unit {uid} "
            "controllers."
        ),
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
    description="Engineering workstation reach to safety system (configuration).",
)


def _make_unit_to_safety_conduit(uid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"unit{uid}_to_safety",
        name=f"Unit {uid} ↔ Safety",
        source_zone=f"unit{uid}",
        target_zone="safety",
        direction="bidirectional",
        security_level="critical",
        allowed_protocols=(
            "modbus_tcp", "profisafe", "cip_safety", "snmp",
        ),
        description=(
            f"Unit {uid} DCS handshake with SIS for safety state."
        ),
    )


_UNIT_SAFETY_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_unit_to_safety_conduit(i) for i in range(1, 5)
)


# ---------------------------------------------------------------------------
# Archetype
# ---------------------------------------------------------------------------

ARCHETYPE = Archetype(
    id="manufacturing_process_dcs",
    name="Process Manufacturing — DCS",
    vertical=Vertical.MANUFACTURING_PROCESS.value,
    pattern=ArchitecturePattern.CONTINUOUS_DCS,
    description=(
        "Continuous-process plant: DCS controllers (DeltaV / Centum / "
        "Experion / 800xA) per unit, dedicated safety zone for SIL "
        "controllers, batch server orchestrating ISA-88 phases. "
        "Standard for pharma, specialty chemicals, food&beverage."
    ),
    default_vendor_profile=VendorProfile.DCS_EMERSON,
    supported_vendor_profiles=(
        VendorProfile.DCS_EMERSON,
        VendorProfile.DCS_HONEYWELL,
        VendorProfile.DCS_YOKOGAWA,
        VendorProfile.DCS_ABB,
    ),
    zones=(_ZONE_IDMZ, _ZONE_OPERATIONS) + _UNIT_ZONES + (_ZONE_SAFETY,),
    conduits=(
        (_C_IDMZ_OPS,)
        + _UNIT_CONDUITS
        + (_C_OPS_TO_SAFETY,)
        + _UNIT_SAFETY_CONDUITS
    ),
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Unit counts: DEMO=1, SMALL/MEDIUM=2, LARGE/MULTI_SITE=3-4.",
        "Safety zone is isolated by IEC 62443 SIL-rated conduit; protocols "
        "limited to safety-rated channels (PROFIsafe / CIP Safety) plus "
        "engineering config over OPC UA.",
        "Batch controller appears at MEDIUM+ when batch processes are "
        "modeled. Smaller plants run continuous-only.",
    ),
)
