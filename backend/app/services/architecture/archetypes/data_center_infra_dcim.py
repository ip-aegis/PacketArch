# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Data center infrastructure (DCIM) archetype.

Facility-side OT for a data center: DCIM server polls PDUs, UPSes,
CRACs, and branch-circuit monitors over SNMP / Modbus TCP / BACnet.
Distinct from manufacturing or process plants — no DCS, no PLC cells;
it's network gear and power/cooling field equipment.
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
    name="IT/Facility Boundary",
    purdue_level=3.5,
    security_level="critical",
    description="L3.5 boundary — DCIM exposed to IT operations.",
    role_slots=(
        RoleSlot(role_id="jump_server",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DMZ_Jump_Server"),
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
    name="DCIM Operations",
    purdue_level=3.0,
    security_level="high",
    description="L3 DCIM — facility monitoring server, NMS, eng workstation.",
    role_slots=(
        RoleSlot(role_id="scada_primary",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DCIM_Server"),
        RoleSlot(role_id="process_historian",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="DCIM_Historian"),
        RoleSlot(role_id="nms_server",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DC_NMS"),
        RoleSlot(role_id="engineering_workstation",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DC_Eng_Workstation"),
        RoleSlot(role_id="core_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="DCIM_Core_Switch"),
    ),
)


def _make_rack_zone(rid: int, rname: str) -> ZoneDef:
    """Per-rack-row zone — Schneider Rack PDUs + environmental sensors +
    rack switch. Phase 9 audit fix: replaced vfd stand-ins with the
    proper `pdu` role."""
    return ZoneDef(
        id=f"rack{rid}",
        name=rname,
        purdue_level=1.0,
        security_level="standard",
        description=f"Rack row {rid} — PDUs, environmental sensors.",
        role_slots=(
            RoleSlot(role_id="pdu",
                     count_by_scale={"demo": 1, "small": 2, "medium": 4,
                                     "large": 8, "multi_site": 8},
                     name_prefix=f"Row{rid}_PDU"),
            RoleSlot(role_id="field_instrument",
                     count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                     "large": 4, "multi_site": 4},
                     name_prefix=f"Row{rid}_Env_Sensor"),
            RoleSlot(role_id="cell_switch",
                     count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                     "large": 1, "multi_site": 1},
                     name_prefix=f"Row{rid}_Switch"),
        ),
    )


_RACK_ZONES: tuple[ZoneDef, ...] = tuple(
    _make_rack_zone(i, f"Rack Row {i}") for i in range(1, 17)
)


_ZONE_COOLING = ZoneDef(
    id="cooling",
    name="Mechanical / Cooling",
    purdue_level=1.0,
    security_level="standard",
    description="CRAC / CRAH units + chiller plant.",
    role_slots=(
        # Phase 9: dedicated CRAC role + chiller controller, replacing
        # the bms_field_controller stand-in.
        RoleSlot(role_id="crac_unit",
                 count_by_scale={"demo": 1, "small": 2, "medium": 4,
                                 "large": 6, "multi_site": 6},
                 name_prefix="CRAC_Unit"),
        RoleSlot(role_id="chiller_controller",
                 count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                 "large": 2, "multi_site": 2},
                 optional_at=("demo",),
                 name_prefix="Chiller_Controller"),
        RoleSlot(role_id="vfd",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="Chiller_Pump_VFD"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 2, "small": 3, "medium": 4,
                                 "large": 5, "multi_site": 5},
                 name_prefix="Cooling_Sensor"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Cooling_Switch"),
    ),
)


_ZONE_POWER = ZoneDef(
    id="power",
    name="Power Plant (UPS / Generators)",
    purdue_level=1.0,
    security_level="high",
    description="UPS, ATS, standby generator controls.",
    role_slots=(
        # Phase 9: dedicated ups_unit role replacing the vfd stand-in.
        RoleSlot(role_id="ups_unit",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 4, "multi_site": 4},
                 name_prefix="UPS"),
        RoleSlot(role_id="cell_controller",
                 count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 optional_at=("demo",),
                 name_prefix="Power_PLC"),
        RoleSlot(role_id="power_meter",
                 count_by_scale={"demo": 0, "small": 1, "medium": 2,
                                 "large": 3, "multi_site": 3},
                 optional_at=("demo",),
                 name_prefix="Power_Meter"),
        RoleSlot(role_id="field_instrument",
                 count_by_scale={"demo": 1, "small": 2, "medium": 3,
                                 "large": 3, "multi_site": 3},
                 name_prefix="Power_Sensor"),
        RoleSlot(role_id="cell_switch",
                 count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                 "large": 1, "multi_site": 1},
                 name_prefix="Power_Switch"),
    ),
)


_C_IDMZ_OPS = ConduitTemplate(
    id="idmz_to_operations",
    name="IDMZ ↔ DCIM Operations",
    source_zone="idmz",
    target_zone="operations",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("https", "snmp", "rdp", "ssh"),
    description="Tenant admin / vendor access to DCIM.",
)


def _make_ops_to_rack_conduit(rid: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"operations_to_rack{rid}",
        name=f"DCIM ↔ Rack Row {rid}",
        source_zone="operations",
        target_zone=f"rack{rid}",
        direction="bidirectional",
        security_level="standard",
        allowed_protocols=("snmp", "modbus_tcp", "https"),
        description=f"DCIM polls rack-row {rid} PDUs and sensors.",
    )


_RACK_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_ops_to_rack_conduit(i) for i in range(1, 17)
)


_C_OPS_TO_COOLING = ConduitTemplate(
    id="operations_to_cooling",
    name="DCIM ↔ Cooling",
    source_zone="operations",
    target_zone="cooling",
    direction="bidirectional",
    security_level="standard",
    allowed_protocols=("bacnet", "modbus_tcp", "snmp"),
    description="DCIM polls cooling controls and chillers.",
)


_C_OPS_TO_POWER = ConduitTemplate(
    id="operations_to_power",
    name="DCIM ↔ Power",
    source_zone="operations",
    target_zone="power",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("modbus_tcp", "snmp", "https"),
    description="DCIM polls UPS / ATS / generator controls.",
)


ARCHETYPE = Archetype(
    id="data_center_infra_dcim",
    name="Data Center — DCIM Facility",
    vertical=Vertical.DATA_CENTER_INFRA.value,
    pattern=ArchitecturePattern.DCIM_FACILITY,
    description=(
        "Facility-side OT for a colocation / hyperscale data center: "
        "DCIM server polls PDUs, UPSes, CRAC units, branch-circuit "
        "monitors, and chiller plant. No DCS, no PLC cells — it's "
        "network gear and power/cooling field equipment."
    ),
    default_vendor_profile=VendorProfile.DCIM_CISCO,
    supported_vendor_profiles=(
        VendorProfile.DCIM_CISCO,
        VendorProfile.BAS_TRIDIUM,  # BAS-side DCIM
    ),
    zones=(
        _ZONE_IDMZ, _ZONE_OPERATIONS,
    ) + _RACK_ZONES + (
        _ZONE_COOLING, _ZONE_POWER,
    ),
    conduits=(
        (_C_IDMZ_OPS,)
        + _RACK_CONDUITS
        + (_C_OPS_TO_COOLING, _C_OPS_TO_POWER)
    ),
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Rack-row counts: DEMO=1, SMALL=2, MEDIUM=4, LARGE=8, "
        "MULTI_SITE=16.",
        "PDUs are modeled under the `vfd` role (catalog stand-in for "
        "smart power devices). Future: dedicated `power_distribution_unit` "
        "role with its own SNMP-only catalog entries.",
    ),
)
