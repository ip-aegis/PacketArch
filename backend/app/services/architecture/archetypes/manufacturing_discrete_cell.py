# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Discrete-cell manufacturing archetype.

Models a typical multi-cell discrete-manufacturing plant: an IDMZ at
L3.5, a plant operations zone at L3 with SCADA / historian / engineering,
and 2-4 production cells at L1-L2 each containing a cell PLC, an area
HMI, drives, distributed I/O, and a cell switch.

Vendor profiles supported: SIEMENS_SHOP, ROCKWELL_SHOP, MULTI_VENDOR.
The vendor profile is the dominant decision driver for protocol
selection inside cells (PROFINET vs EtherNet/IP vs mixed).
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
# Zone: IDMZ (L3.5)
# ---------------------------------------------------------------------------

_ZONE_IDMZ = ZoneDef(
    id="idmz",
    name="Industrial DMZ",
    purdue_level=3.5,
    security_level="critical",
    description="L3.5 IT/OT boundary — jump server, replicas, AV, patch.",
    role_slots=(
        # Jump server is required at every scale.
        RoleSlot(
            role_id="jump_server",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            name_prefix="DMZ_Jump_Server",
        ),
        # Remote-access gateway at small+ for vendor service access.
        RoleSlot(
            role_id="remote_access_gateway",
            count_by_scale={"demo": 0, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            optional_at=("demo",),
            name_prefix="DMZ_Remote_Access_GW",
        ),
        # Patch staging server at medium+.
        RoleSlot(
            role_id="patch_staging_server",
            count_by_scale={"demo": 0, "small": 0, "medium": 1,
                            "large": 1, "multi_site": 1},
            optional_at=("demo", "small"),
            name_prefix="DMZ_Patch_Server",
        ),
        # AV management at medium+.
        RoleSlot(
            role_id="av_management_server",
            count_by_scale={"demo": 0, "small": 0, "medium": 1,
                            "large": 1, "multi_site": 1},
            optional_at=("demo", "small"),
            name_prefix="DMZ_AV_Server",
        ),
        # Historian replica at large+ (read-only mirror for IT).
        RoleSlot(
            role_id="historian_replica",
            count_by_scale={"demo": 0, "small": 0, "medium": 0,
                            "large": 1, "multi_site": 1},
            optional_at=("demo", "small", "medium"),
            name_prefix="DMZ_Historian_Replica",
        ),
        # OPC UA aggregator at large+ for multi-vendor sites.
        RoleSlot(
            role_id="opc_ua_aggregator",
            count_by_scale={"demo": 0, "small": 0, "medium": 0,
                            "large": 1, "multi_site": 1},
            optional_at=("demo", "small", "medium"),
            name_prefix="DMZ_OPCUA_Aggregator",
        ),
        # WAN edge router (always except DEMO).
        RoleSlot(
            role_id="wan_edge_router",
            count_by_scale={"demo": 0, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            optional_at=("demo",),
            name_prefix="DMZ_WAN_Edge",
        ),
        # Core switch in IDMZ.
        RoleSlot(
            role_id="core_switch",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            name_prefix="DMZ_Core_Switch",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Zone: Operations / L3
# ---------------------------------------------------------------------------

_ZONE_OPERATIONS = ZoneDef(
    id="operations",
    name="Operations",
    purdue_level=3.0,
    security_level="high",
    description="L3 plant operations — SCADA, historian, engineering, NMS.",
    role_slots=(
        # SCADA primary (always).
        RoleSlot(
            role_id="scada_primary",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            name_prefix="Plant_SCADA_Server",
        ),
        # SCADA standby at medium+.
        RoleSlot(
            role_id="scada_standby",
            count_by_scale={"demo": 0, "small": 0, "medium": 1,
                            "large": 1, "multi_site": 1},
            optional_at=("demo", "small"),
            name_prefix="Plant_SCADA_Standby",
        ),
        # Process historian (always except DEMO).
        RoleSlot(
            role_id="process_historian",
            count_by_scale={"demo": 0, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            optional_at=("demo",),
            name_prefix="Plant_Historian",
        ),
        # Engineering workstation (always — vendor-specific instance).
        RoleSlot(
            role_id="engineering_workstation",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 2, "multi_site": 2},
            name_prefix="Eng_Workstation",
        ),
        # NMS at small+.
        RoleSlot(
            role_id="nms_server",
            count_by_scale={"demo": 0, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            optional_at=("demo",),
            name_prefix="Plant_NMS",
        ),
        # Asset management at large+.
        RoleSlot(
            role_id="asset_management_server",
            count_by_scale={"demo": 0, "small": 0, "medium": 0,
                            "large": 1, "multi_site": 1},
            optional_at=("demo", "small", "medium"),
            name_prefix="Plant_Asset_Mgmt",
        ),
        # MES at large+.
        RoleSlot(
            role_id="mes_server",
            count_by_scale={"demo": 0, "small": 0, "medium": 0,
                            "large": 1, "multi_site": 1},
            optional_at=("demo", "small", "medium"),
            name_prefix="Plant_MES",
        ),
        # Operations core switch.
        RoleSlot(
            role_id="core_switch",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            name_prefix="Operations_Core_Switch",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Zone: Cell N (L1-L2)
# ---------------------------------------------------------------------------

def _make_cell_zone(cell_id: int, cell_name: str) -> ZoneDef:
    """Generate a cell zone definition with the standard slot mix.

    Cell count itself is governed by archetype scale: DEMO=1, SMALL=2,
    MEDIUM=3, LARGE=4, MULTI_SITE=4. The generator instantiates this
    template once per cell.

    Phase 9 audit fix: added robot_controller, cnc_controller,
    vision_system, barcode_scanner — real device classes the legacy
    multi_vendor / strict_purdue templates carried that the original
    archetype refactor collapsed away.
    """
    return ZoneDef(
        id=f"cell{cell_id}",
        name=cell_name,
        purdue_level=1.5,
        security_level="standard",
        description=f"Production cell {cell_id} — controllers, robotics, IO.",
        role_slots=(
            RoleSlot(
                role_id="cell_controller",
                count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                "large": 2, "multi_site": 2},
                name_prefix=f"Cell{cell_id}_Main_PLC",
            ),
            RoleSlot(
                role_id="safety_controller",
                count_by_scale={"demo": 0, "small": 0, "medium": 0,
                                "large": 1, "multi_site": 1},
                optional_at=("demo", "small", "medium"),
                name_prefix=f"Cell{cell_id}_Safety_PLC",
            ),
            RoleSlot(
                role_id="area_hmi",
                count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                "large": 1, "multi_site": 1},
                name_prefix=f"Cell{cell_id}_HMI",
            ),
            # Phase 9 audit: robotic automation. Articulated robots show
            # up at MEDIUM+ scale (small cells are typically all-PLC).
            RoleSlot(
                role_id="robot_controller",
                count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                "large": 2, "multi_site": 2},
                optional_at=("demo", "small"),
                name_prefix=f"Cell{cell_id}_Robot",
            ),
            # CNC machining at LARGE+ for precision-machining cells.
            RoleSlot(
                role_id="cnc_controller",
                count_by_scale={"demo": 0, "small": 0, "medium": 0,
                                "large": 1, "multi_site": 1},
                optional_at=("demo", "small", "medium"),
                name_prefix=f"Cell{cell_id}_CNC",
            ),
            # Vision inspection at MEDIUM+ (quality stations).
            RoleSlot(
                role_id="vision_system",
                count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                "large": 2, "multi_site": 2},
                optional_at=("demo", "small"),
                name_prefix=f"Cell{cell_id}_Vision",
            ),
            # Barcode at MEDIUM+ (part / pallet tracking).
            RoleSlot(
                role_id="barcode_scanner",
                count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                "large": 2, "multi_site": 2},
                optional_at=("demo", "small"),
                name_prefix=f"Cell{cell_id}_Barcode",
            ),
            RoleSlot(
                role_id="vfd",
                count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                "large": 4, "multi_site": 4},
                name_prefix=f"Cell{cell_id}_VFD",
            ),
            RoleSlot(
                role_id="servo",
                count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                "large": 3, "multi_site": 3},
                optional_at=("demo",),
                name_prefix=f"Cell{cell_id}_Servo",
            ),
            RoleSlot(
                role_id="distributed_io",
                count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                "large": 4, "multi_site": 4},
                name_prefix=f"Cell{cell_id}_IO",
            ),
            RoleSlot(
                role_id="cell_switch",
                count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                "large": 1, "multi_site": 1},
                name_prefix=f"Cell{cell_id}_Switch",
            ),
        ),
    )


# Cell counts vary by scale. The generator picks the first N cell zones
# matching the scale tier (DEMO=1, SMALL=2, MEDIUM=3, LARGE/MULTI_SITE=4).
_CELL_ZONES: tuple[ZoneDef, ...] = (
    _make_cell_zone(1, "Production Cell 1"),
    _make_cell_zone(2, "Production Cell 2"),
    _make_cell_zone(3, "Production Cell 3"),
    _make_cell_zone(4, "Production Cell 4"),
)


# ---------------------------------------------------------------------------
# Conduits
# ---------------------------------------------------------------------------

# IDMZ ↔ Operations (always present).
_C_IDMZ_OPS = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ Operations",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("https", "snmp", "opc_ua", "rdp", "ssh", "smb"),
    description=(
        "Jump-server admin pivot, historian replication, AV/patch sync, "
        "OPC UA aggregator north-side."
    ),
)


def _make_ops_to_cell_conduit(cell_id: int) -> ConduitTemplate:
    """Operations ↔ Cell conduit. Standard north-south plant flow."""
    return ConduitTemplate(
        id=f"operations_to_cell{cell_id}",
        name=f"Operations ↔ Cell {cell_id}",
        source_zone="operations",
        target_zone=f"cell{cell_id}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=(
            "ethernet_ip", "modbus_tcp", "s7comm", "profinet",
            "opc_ua", "snmp",
        ),
        description=(
            f"SCADA polling, historian subscription, engineering workstation "
            f"download/online to cell {cell_id} controllers."
        ),
    )


_CELL_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_ops_to_cell_conduit(i) for i in range(1, 5)
)


# ---------------------------------------------------------------------------
# Archetype definition
# ---------------------------------------------------------------------------

ARCHETYPE = Archetype(
    id="manufacturing_discrete_cell",
    name="Discrete Manufacturing — Cell-Based",
    vertical=Vertical.MANUFACTURING_DISCRETE.value,
    pattern=ArchitecturePattern.DISCRETE_CELL,
    description=(
        "Multi-cell discrete-manufacturing plant. Each cell has a PLC + "
        "HMI + drives + I/O on a vendor-native fieldbus (PROFINET, "
        "EtherNet/IP, or mixed). L3 SCADA polls all cells; L3.5 IDMZ "
        "brokers to IT. Standard pattern for automotive assembly, "
        "discrete electronics, packaging, food&beverage discrete lines."
    ),
    default_vendor_profile=VendorProfile.SIEMENS_SHOP,
    supported_vendor_profiles=(
        VendorProfile.SIEMENS_SHOP,
        VendorProfile.ROCKWELL_SHOP,
        VendorProfile.MULTI_VENDOR,
    ),
    zones=(_ZONE_IDMZ, _ZONE_OPERATIONS) + _CELL_ZONES,
    conduits=(_C_IDMZ_OPS,) + _CELL_CONDUITS,
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Cell counts: DEMO=1, SMALL=2, MEDIUM=3, LARGE/MULTI_SITE=4.",
        "Safety PLC included only at LARGE+ (smaller plants typically "
        "embed safety functions in the cell PLC).",
        "MULTI_VENDOR vendor profile spreads cells across siemens/rockwell/"
        "schneider/abb. Comm matrix routes cross-vendor flows over OPC UA.",
    ),
)
