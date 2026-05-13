# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Distribution / warehouse archetype.

Warehouse Control System (WCS) at L3 supervises per-area conveyor and
sortation PLCs. Standard for fulfillment centers, parcel sorting hubs,
cold-chain warehouses.
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
    description="L3.5 — WMS/ERP IT integration boundary.",
    role_slots=(
        RoleSlot(role_id="jump_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DMZ_Jump_Server"),
        RoleSlot(role_id="reverse_proxy",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_Reverse_Proxy"),
        RoleSlot(role_id="patch_staging_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="DMZ_Patch_Server"),
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


_ZONE_OPERATIONS = ZoneDef(
    id="operations",
    name="WMS / WCS Operations",
    purdue_level=3.0,
    security_level="high",
    description="L3 WMS / WCS supervisors + historian.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="WMS_Server"),
        RoleSlot(role_id="scada_standby",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="WMS_Standby"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="WCS_Historian"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="WCS_Eng_Workstation"),
        RoleSlot(role_id="mes_server",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="MES_Server"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DC_NMS"),
        RoleSlot(role_id="fleet_manager",
                 count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo", "small"),
                 name_prefix="Fleet_Manager"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="WMS_Core_Switch"),
    ),
)


def _make_zone_zone(zid: int, zname: str) -> ZoneDef:
    """Per-area zone — WCS + conveyor PLCs + drives + identification +
    AGV fleet. Phase 9 audit fix: added barcode_scanner, rfid_reader,
    vision_system, and agv slots that the legacy templates carried."""
    return ZoneDef(
        id=f"zone{zid}",
        name=zname,
        purdue_level=1.0,
        security_level="standard",
        description=(
            f"Warehouse area {zid} — sortation / conveyor / identification "
            "+ optional AGV fleet."
        ),
        role_slots=(
            RoleSlot(role_id="wcs_controller",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Zone{zid}_WCS_PLC"),
            RoleSlot(role_id="conveyor_controller",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Zone{zid}_Conveyor_PLC"),
            RoleSlot(role_id="vfd",
                     count_by_scale={"demo": 2, "small": 4, "medium": 6,
                                     "large": 8, "multi_site": 8},
                     name_prefix=f"Zone{zid}_VFD"),
            RoleSlot(role_id="distributed_io",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Zone{zid}_IO"),
            RoleSlot(role_id="barcode_scanner",
                     count_by_scale={"demo": 0, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     optional_at=("demo",),
                     name_prefix=f"Zone{zid}_Barcode"),
            RoleSlot(role_id="rfid_reader",
                     count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                     "large": 3, "multi_site": 3},
                     optional_at=("demo",),
                     name_prefix=f"Zone{zid}_RFID"),
            RoleSlot(role_id="vision_system",
                     count_by_scale={"demo": 0, "small": 0, "medium": 1,
                                     "large": 2, "multi_site": 2},
                     optional_at=("demo", "small"),
                     name_prefix=f"Zone{zid}_Vision"),
            RoleSlot(role_id="agv",
                     count_by_scale={"demo": 0, "small": 0, "medium": 2,
                                     "large": 4, "multi_site": 4},
                     optional_at=("demo", "small"),
                     name_prefix=f"Zone{zid}_AGV"),
            RoleSlot(role_id="area_hmi",
                     count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     optional_at=("demo",),
                     name_prefix=f"Zone{zid}_HMI"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Zone{zid}_Switch"),
        ),
    )


_ZONE_AREAS: tuple[ZoneDef, ...] = tuple(
    _make_zone_zone(i, f"Warehouse Zone {i}") for i in range(1, 5)
)


_C_IDMZ_OPS = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ WMS",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("https", "snmp", "rdp", "ssh", "opc_ua"),
    description="ERP/WMS integration north-side.",
)


def _make_ops_to_zone_conduit(zid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_zone{zid}",
        name=f"WMS ↔ Zone {zid}",
        source_zone="operations",
        target_zone=f"zone{zid}",
        direction="bidirectional",
        security_level="standard",
        allowed_protocols=("ethernet_ip", "modbus_tcp", "snmp", "opc_ua"),
        description=f"WMS reach to zone {zid} WCS / conveyor PLCs.",
    )


_ZONE_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_ops_to_zone_conduit(i) for i in range(1, 5)
)


ARCHETYPE = Archetype(
    id="distribution_warehouse",
    name="Distribution / Logistics — Warehouse",
    vertical=Vertical.DISTRIBUTION_LOGISTICS.value,
    pattern=ArchitecturePattern.WAREHOUSE_PICK,
    description=(
        "Fulfillment center / sortation hub / cold-chain warehouse. "
        "WMS at L3 issues pick / wave / putaway tasks; per-zone WCS "
        "PLCs drive conveyor and sortation lanes; conveyor PLCs run "
        "tight motion to drives + sensors. Default vendor is Rockwell "
        "(EtherNet/IP-dominant) but Siemens / Schneider / multi-vendor "
        "supported."
    ),
    default_vendor_profile=VendorProfile.ROCKWELL_SHOP,
    supported_vendor_profiles=(
        VendorProfile.ROCKWELL_SHOP,
        VendorProfile.SIEMENS_SHOP,
        VendorProfile.SCHNEIDER_SHOP,
        VendorProfile.MULTI_VENDOR,
    ),
    zones=(_ZONE_IDMZ, _ZONE_OPERATIONS) + _ZONE_AREAS,
    conduits=(_C_IDMZ_OPS,) + _ZONE_CONDUITS,
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Zone counts: DEMO=1, SMALL=2, MEDIUM=3, LARGE/MULTI_SITE=4.",
        "MES server appears at MEDIUM+ when ERP integration is in scope.",
    ),
)
