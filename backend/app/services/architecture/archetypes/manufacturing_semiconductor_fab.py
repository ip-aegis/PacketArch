# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Semiconductor fab archetype — 300mm wafer line.

Architecturally distinct from any existing manufacturing pattern:
process bays each host cluster tools (modeled as dcs_controller) plus
heavy analyzer / vision instrumentation. AMHS zone holds the OHT
fleet (modeled as agv + fleet_manager). Cleanroom-monitoring zone
holds environmental field instruments.

Recipe-driven, no people on the floor — flows are dense even at small
scale.
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
    description="L3.5 — fab IT integration + vendor support tunnels.",
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
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_Historian_Replica"),
        RoleSlot(role_id="opc_ua_aggregator",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_OPCUA_Aggregator"),
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
    name="Fab Operations",
    purdue_level=3.0,
    security_level="high",
    description=(
        "L3 fab control room — MES, SCADA, scheduler, historian, NMS."
    ),
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Fab_SCADA_Primary"),
        RoleSlot(role_id="scada_standby",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Fab_SCADA_Standby"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Fab_Process_Historian"),
        RoleSlot(role_id="mes_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Fab_MES_Server"),
        RoleSlot(role_id="batch_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Fab_Recipe_Manager"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 2, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 name_prefix="Fab_Eng_Workstation"),
        RoleSlot(role_id="alarm_event_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Fab_Alarm_Server"),
        RoleSlot(role_id="asset_management_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="Fab_Asset_Mgmt"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Fab_NMS"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Operations_Core_Switch"),
    ),
)


def _make_bay_zone(bid: int, bname: str) -> ZoneDef:
    """Process bay — cluster tool + analyzers + vision + servos.

    Each bay represents one process module group (litho, etch, dep, CMP,
    metrology, diffusion). The cluster tool is modeled as a DCS
    controller; each tool is heavy on analyzer + vision instrumentation.
    """
    return ZoneDef(
        id=f"bay{bid}",
        name=bname,
        purdue_level=1.0,
        security_level="high",
        description=f"Process bay {bid} — cluster tool + analyzers + vision.",
        role_slots=(
            # Cluster tool aggregator.
            RoleSlot(role_id="dcs_controller",
                     count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     name_prefix=f"Bay{bid}_Cluster_Tool"),
            # Wafer-handler robot per tool.
            RoleSlot(role_id="robot_controller",
                     count_by_scale={"demo": 1, "small": 1, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     name_prefix=f"Bay{bid}_Wafer_Handler"),
            # Heavy analyzer instrumentation: RGAs, mass-spec, gas chrom.
            RoleSlot(role_id="analyzer",
                     count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                     "large": 8, "multi_site": 8},
                     name_prefix=f"Bay{bid}_Analyzer"),
            # Vision systems (alignment / overlay / defect).
            RoleSlot(role_id="vision_system",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Bay{bid}_Vision"),
            # Servos for stage / chuck motion.
            RoleSlot(role_id="servo",
                     count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                     "large": 5, "multi_site": 5},
                     name_prefix=f"Bay{bid}_Stage_Servo"),
            # Mass-flow controllers + pressure / temperature transmitters.
            RoleSlot(role_id="field_instrument",
                     count_by_scale={"demo": 4, "small": 6, "medium": 8,
                                     "large": 10, "multi_site": 10},
                     name_prefix=f"Bay{bid}_MFC"),
            RoleSlot(role_id="valve_actuator",
                     count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                     "large": 6, "multi_site": 6},
                     name_prefix=f"Bay{bid}_Valve"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Bay{bid}_Switch"),
        ),
    )


_BAY_ZONES: tuple[ZoneDef, ...] = (
    _make_bay_zone(1, "Lithography"),
    _make_bay_zone(2, "Etch"),
    _make_bay_zone(3, "Deposition"),
    _make_bay_zone(4, "CMP"),
    _make_bay_zone(5, "Metrology"),
    _make_bay_zone(6, "Diffusion"),
)


_ZONE_AMHS = ZoneDef(
    id="amhs",
    name="AMHS (Overhead Transport)",
    purdue_level=1.5,
    security_level="standard",
    description=(
        "Automated material handling — OHTs ferry FOUPs between bays."
    ),
    role_slots=(
        # Fleet manager dispatches OHTs.
        RoleSlot(role_id="fleet_manager",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="AMHS_Dispatcher"),
        # Each OHT modeled as an AGV.
        RoleSlot(role_id="agv",
                 count_by_scale={"demo": 4, "small": 8, "medium": 12,
                                 "large": 16, "multi_site": 16},
                 name_prefix="OHT"),
        # Stockers + load-port aggregators (modeled as conveyor PLCs).
        RoleSlot(role_id="conveyor_controller",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="AMHS_Stocker"),
        # Barcode scanners at every bay handoff.
        RoleSlot(role_id="barcode_scanner",
                 count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                 "large": 8, "multi_site": 8},
                 name_prefix="AMHS_FOUP_Scanner"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="AMHS_Switch"),
    ),
)


_ZONE_CLEANROOM = ZoneDef(
    id="cleanroom_env",
    name="Cleanroom Environmental Monitoring",
    purdue_level=1.0,
    security_level="high",
    description=(
        "Particle counters + temperature / humidity / DP transmitters."
    ),
    role_slots=(
        RoleSlot(role_id="cell_controller",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Cleanroom_PLC"),
        # Particle counters / environmental sensors.
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 4, "small": 6, "medium": 8,
                                 "large": 12, "multi_site": 12},
                 name_prefix="Particle_Counter"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Cleanroom_Switch"),
    ),
)


# Conduits — IDMZ↔ops, ops↔each bay, ops↔AMHS, ops↔cleanroom.
_C_IDMZ_OPS = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ Operations",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("https", "snmp", "opc_ua", "rdp", "ssh"),
    description="Fab IT integration + vendor support tunnel.",
)


def _make_ops_to_bay_conduit(bid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_bay{bid}",
        name=f"Operations ↔ Bay {bid}",
        source_zone="operations",
        target_zone=f"bay{bid}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=("opc_ua", "modbus_tcp", "ethernet_ip", "snmp"),
        description=f"Fab control reach to bay {bid} cluster tools.",
    )


_BAY_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_ops_to_bay_conduit(i) for i in range(1, 7)
)


_C_OPS_TO_AMHS = ConduitTemplate(
    id="operations_to_amhs",
    name="Operations ↔ AMHS",
    source_zone="operations",
    target_zone="amhs",
    direction="bidirectional",
    security_level="standard",
    allowed_protocols=("https", "modbus_tcp", "ethernet_ip", "snmp"),
    description="Fab scheduler dispatches OHTs / tracks FOUP movement.",
)


_C_OPS_TO_CLEANROOM = ConduitTemplate(
    id="operations_to_cleanroom_env",
    name="Operations ↔ Cleanroom",
    source_zone="operations",
    target_zone="cleanroom_env",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("modbus_tcp", "snmp", "opc_ua"),
    description="Cleanroom environmental data + alarm flow (OPC UA replication).",
)


# AMHS conduits to each bay (OHTs deliver to bays).
def _make_amhs_to_bay_conduit(bid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"amhs_to_bay{bid}",
        name=f"AMHS ↔ Bay {bid}",
        source_zone="amhs",
        target_zone=f"bay{bid}",
        direction="bidirectional",
        security_level="standard",
        allowed_protocols=("https", "modbus_tcp", "ethernet_ip", "snmp"),
        description=f"OHT FOUP handoff to bay {bid} load ports.",
    )


_AMHS_BAY_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_amhs_to_bay_conduit(i) for i in range(1, 7)
)


ARCHETYPE = Archetype(
    id="manufacturing_semiconductor_fab",
    name="Manufacturing — Semiconductor Fab (300mm)",
    vertical=Vertical.MANUFACTURING_DISCRETE.value,
    pattern=ArchitecturePattern.DISCRETE_CELL,
    description=(
        "300mm wafer fabrication facility. Process bays (lithography, "
        "etch, deposition, CMP, metrology, diffusion) each host cluster "
        "tools with heavy analyzer + vision instrumentation. AMHS zone "
        "carries the OHT (Overhead Hoist Transport) fleet ferrying "
        "FOUPs between bays under fleet-manager dispatch. Cleanroom-"
        "environmental zone monitors particle / temperature / humidity. "
        "Recipe-driven (Batch / MES) with heavy historian + asset "
        "management."
    ),
    default_vendor_profile=VendorProfile.MULTI_VENDOR,
    supported_vendor_profiles=(
        VendorProfile.MULTI_VENDOR,
        VendorProfile.SIEMENS_SHOP,
        VendorProfile.ROCKWELL_SHOP,
    ),
    zones=(
        _ZONE_IDMZ, _ZONE_OPERATIONS,
    ) + _BAY_ZONES + (_ZONE_AMHS, _ZONE_CLEANROOM),
    conduits=(
        (_C_IDMZ_OPS,)
        + _BAY_CONDUITS
        + (_C_OPS_TO_AMHS, _C_OPS_TO_CLEANROOM)
        + _AMHS_BAY_CONDUITS
    ),
    min_scale=ScaleTier.SMALL,
    cell_isolation_default="conduit_gated",
    notes=(
        "All 6 process bays always present (litho / etch / dep / CMP / "
        "metrology / diffusion are the canonical fab process modules).",
        "OHT counts: SMALL=8, MEDIUM=12, LARGE=16. Each FOUP movement "
        "generates fleet-manager dispatch traffic + barcode reads at "
        "each handoff.",
        "Heavy analyzer presence (6-8 per bay) reflects RGA / mass-"
        "spec / gas chrom instrumentation typical of 300mm tooling.",
        "Cleanroom zone is monitor-only — particle counters + DP "
        "transmitters polled by a single PLC.",
    ),
)
