# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Energy substation archetype (IEC 61850 station bus + GOOSE).

Distinct shape from manufacturing/process: per-bay protection relays,
station bus aggregating to an RTAC, no L2 area HMI. Operator interaction
happens through the RTAC + remote SCADA (utility EMS).
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
# Zone: Station Operations (L3) — local SCADA + engineering
# ---------------------------------------------------------------------------

_ZONE_STATION_OPS = ZoneDef(
    id="station_ops",
    name="Station Operations",
    purdue_level=3.0,
    security_level="high",
    description="L3 station ops — local HMI, engineering, NMS.",
    role_slots=(
        # Station HMI (modeled as scada_primary at the substation).
        # LARGE/MULTI_SITE substations run redundant HMI clusters for
        # NERC-CIP availability requirements — primary + hot standby.
        RoleSlot(
            role_id="scada_primary",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 2, "multi_site": 2},
            name_prefix="Station_HMI_Server",
        ),
        # Engineering workstation (NERC-CIP regulated; required).
        # Multi-vendor sites typically have one per protection discipline
        # (feeder/bus/transformer) so engineers can program in parallel.
        RoleSlot(
            role_id="engineering_workstation",
            count_by_scale={"demo": 1, "small": 1, "medium": 2,
                            "large": 3, "multi_site": 3},
            name_prefix="Station_Eng_Workstation",
        ),
        # NMS at small+.
        RoleSlot(
            role_id="nms_server",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            name_prefix="Station_NMS",
        ),
        # Asset management at medium+.
        RoleSlot(
            role_id="asset_management_server",
            count_by_scale={"demo": 0, "small": 0, "medium": 1,
                            "large": 1, "multi_site": 1},
            optional_at=("demo", "small"),
            name_prefix="Station_Asset_Mgmt",
        ),
        # Local historian at medium+ (for regulatory event capture).
        RoleSlot(
            role_id="local_historian",
            count_by_scale={"demo": 0, "small": 0, "medium": 1,
                            "large": 1, "multi_site": 1},
            optional_at=("demo", "small"),
            name_prefix="Station_Historian",
        ),
        # Operations core switch.
        RoleSlot(
            role_id="core_switch",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 1, "multi_site": 1},
            name_prefix="Station_Core_Switch",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Zone: Station Bus (L1.5) — RTAC aggregator + station-level switching
# ---------------------------------------------------------------------------

_ZONE_STATION_BUS = ZoneDef(
    id="station_bus",
    name="Station Bus",
    purdue_level=1.5,
    security_level="high",
    description="IEC 61850 station bus — RTAC aggregator + station switch.",
    role_slots=(
        # Aggregator RTU (RTAC). One per station; redundant pair at large+.
        RoleSlot(
            role_id="aggregator_rtu",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 2, "multi_site": 2},
            name_prefix="Station_RTAC",
            role_hint="Substation Gateway",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Zone: Bay N (L0-L1) — protection relays + bay switch
# ---------------------------------------------------------------------------

def _make_bay_zone(bay_id: int, bay_name: str) -> ZoneDef:
    """A substation bay: 2-4 protection relays + revenue meter +
    bay switch. Phase 9 audit added power_meter (revenue-grade
    metering is a real distinct device class in substations)."""
    return ZoneDef(
        id=f"bay{bay_id}",
        name=bay_name,
        purdue_level=1.0,
        security_level="critical",
        description=f"Bay {bay_id} — protection relays + meter + switch.",
        role_slots=(
            RoleSlot(
                role_id="protection_relay",
                count_by_scale={"demo": 2, "small": 2, "medium": 3,
                                "large": 4, "multi_site": 4},
                name_prefix=f"Bay{bay_id}_Relay",
            ),
            RoleSlot(
                role_id="power_meter",
                count_by_scale={"demo": 0, "small": 1, "medium": 1,
                                "large": 2, "multi_site": 2},
                optional_at=("demo",),
                name_prefix=f"Bay{bay_id}_Meter",
            ),
            RoleSlot(
                role_id="bay_switch",
                count_by_scale={"demo": 1, "small": 1, "medium": 1,
                                "large": 1, "multi_site": 1},
                name_prefix=f"Bay{bay_id}_Switch",
            ),
        ),
    )


_BAY_ZONES: tuple[ZoneDef, ...] = (
    _make_bay_zone(1, "Bay 1 — Feeder Protection"),
    _make_bay_zone(2, "Bay 2 — Bus Protection"),
    _make_bay_zone(3, "Bay 3 — Transformer Protection"),
    _make_bay_zone(4, "Bay 4 — Line Protection"),
    _make_bay_zone(5, "Bay 5 — Capacitor Bank"),
    _make_bay_zone(6, "Bay 6 — Reactor"),
)


# ---------------------------------------------------------------------------
# Zone: WAN (Utility EMS uplink)
# ---------------------------------------------------------------------------

_ZONE_WAN = ZoneDef(
    id="wan_uplink",
    name="Utility WAN Uplink",
    purdue_level=4.0,
    is_external=True,
    security_level="external",
    description="External WAN to utility EMS / control center.",
    role_slots=(
        # WAN edge router (always; the substation backbone).
        RoleSlot(
            role_id="wan_edge_router",
            count_by_scale={"demo": 1, "small": 1, "medium": 1,
                            "large": 2, "multi_site": 2},
            name_prefix="WAN_Edge_Router",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Conduits
# ---------------------------------------------------------------------------

_C_OPS_TO_BUS = ConduitTemplate(
    id="ops_to_station_bus",
    name="Station Ops ↔ Station Bus",
    source_zone="station_ops",
    target_zone="station_bus",
    direction="bidirectional",
    security_level="high",
    allowed_protocols=("modbus_tcp", "iec104", "iec61850", "snmp"),
    description="Station HMI / engineering workstation reach to RTAC.",
)


def _make_bus_to_bay_conduit(bay_id: int) -> ConduitTemplate:
    return ConduitTemplate(
        id=f"station_bus_to_bay{bay_id}",
        name=f"Station Bus ↔ Bay {bay_id}",
        source_zone="station_bus",
        target_zone=f"bay{bay_id}",
        direction="bidirectional",
        security_level="critical",
        allowed_protocols=("iec61850", "modbus_tcp", "snmp"),
        description=(
            f"RTAC ↔ bay {bay_id} protection relays over MMS / station bus."
        ),
    )


_BAY_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_bus_to_bay_conduit(i) for i in range(1, 7)
)


def _make_ops_to_bay_conduit(bay_id: int) -> ConduitTemplate:
    """Operations -> bay conduit for NMS-class reach + engineering /
    SCADA access. Permits SNMP/HTTPS/SSH for asset management; Modbus
    TCP and IEC 61850 MMS for SCADA polls and engineering workstation
    config reads. Distinct from station_bus -> bay which carries the
    bulk operational MMS/protection traffic between RTAC and relays."""
    return ConduitTemplate(
        id=f"station_ops_to_bay{bay_id}",
        name=f"Station Ops ↔ Bay {bay_id}",
        source_zone="station_ops",
        target_zone=f"bay{bay_id}",
        direction="bidirectional",
        security_level="high",
        allowed_protocols=("snmp", "https", "ssh", "modbus_tcp", "iec61850"),
        description=(
            f"NMS / asset-mgmt SNMP poll into bay {bay_id} for switch / "
            "relay fingerprinting; engineering workstations and SCADA "
            "HMIs reach bay relays over Modbus TCP / IEC 61850 MMS."
        ),
    )


_BAY_OPS_CONDUITS: tuple[ConduitTemplate, ...] = tuple(
    _make_ops_to_bay_conduit(i) for i in range(1, 7)
)


_C_OPS_TO_WAN = ConduitTemplate(
    id="ops_to_wan",
    name="Station Ops ↔ WAN",
    source_zone="station_ops",
    target_zone="wan_uplink",
    direction="bidirectional",
    security_level="critical",
    allowed_protocols=("iec104", "dnp3", "https", "snmp"),
    description="EMS uplink — DNP3/IEC 104 to utility control center.",
)


# ---------------------------------------------------------------------------
# Archetype definition
# ---------------------------------------------------------------------------

ARCHETYPE = Archetype(
    id="energy_substation",
    name="Energy — IEC 61850 Substation",
    vertical=Vertical.ENERGY_SUBSTATION.value,
    pattern=ArchitecturePattern.DISTRIBUTED_SUBSTATION,
    description=(
        "Electrical substation following IEC 61850. Per-bay protection "
        "relays exchange GOOSE multicast at the bay; MMS reports flow "
        "north to a station-level RTAC; the RTAC presents DNP3 / IEC 104 "
        "north to the utility EMS over WAN. Engineering and local HMI "
        "live in a station-ops zone alongside NMS and asset management."
    ),
    default_vendor_profile=VendorProfile.SEL_PROTECTION,
    supported_vendor_profiles=(
        VendorProfile.SEL_PROTECTION,
        VendorProfile.MIXED_FIELD,
        VendorProfile.ABB_SHOP,
    ),
    zones=(_ZONE_STATION_OPS, _ZONE_STATION_BUS) + _BAY_ZONES + (_ZONE_WAN,),
    conduits=(
        (_C_OPS_TO_BUS,)
        + _BAY_CONDUITS
        + _BAY_OPS_CONDUITS
        + (_C_OPS_TO_WAN,)
    ),
    min_scale=ScaleTier.DEMO,
    cell_isolation_default="conduit_gated",
    notes=(
        "Bay counts: DEMO=1, SMALL=2, MEDIUM=3, LARGE=4, MULTI_SITE=6.",
        "GOOSE multicast is intra-bay; the comm matrix synthesizes those "
        "as bay-internal flows from protection_relay→protection_relay.",
        "DNP3 / IEC 104 north-uplink is generated from the WAN conduit.",
        "Substations omit IDMZ (the station_ops zone fills that role for "
        "remote utility access).",
    ),
)
