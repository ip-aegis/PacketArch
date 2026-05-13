# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comm matrix for energy_substation vertical.

IEC 61850 substation flows: GOOSE multicast intra-bay, MMS reports
north to RTAC, station HMI / engineering reach to RTAC, DNP3/IEC 104
out the WAN to utility EMS.
"""

from __future__ import annotations

from app.services.architecture.archetypes._base import VendorProfile
from app.services.architecture.comm_matrix._base import CommEntry
from app.services.architecture.role_catalog import Vertical


_V = Vertical.ENERGY_SUBSTATION.value


ENERGY_SUBSTATION_ENTRIES: tuple[CommEntry, ...] = (
    # ====================================================================
    # GOOSE multicast: protection relays exchange trip / interlock data
    # at the bay over IEC 61850-8-1.
    # ====================================================================
    CommEntry(
        src_role="protection_relay",
        tgt_role="protection_relay",
        vertical=_V,
        pattern="event",
        interval_ms=(1_000, 1_000),  # heartbeat; events are spontaneous
        jitter_ms=(0, 0),
        protocol_options=("iec61850",),
        fan_out="pair",
        description=(
            "GOOSE multicast intra-bay for protection coordination. "
            "Heartbeat at 1s; events are spontaneous on state change."
        ),
    ),

    # ====================================================================
    # MMS reports: protection relays → RTAC (north-bound MMS).
    # ====================================================================
    CommEntry(
        src_role="aggregator_rtu",
        tgt_role="protection_relay",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("iec61850", "modbus_tcp"),
        description="RTAC polls each protection relay for measurements / status.",
    ),

    # ====================================================================
    # Station HMI → RTAC + protection relays.
    # ====================================================================
    CommEntry(
        src_role="scada_primary",
        tgt_role="aggregator_rtu",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("iec104", "modbus_tcp"),
        description="Station HMI polls RTAC for substation-wide status.",
    ),
    CommEntry(
        src_role="scada_primary",
        tgt_role="protection_relay",
        vertical=_V,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("iec61850",),
        description="Station HMI direct relay measurements (fallback path).",
    ),

    # ====================================================================
    # Engineering workstation → RTAC + relays (configuration).
    # ====================================================================
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="aggregator_rtu",
        vertical=_V,
        pattern="configuration",
        interval_ms=(120_000, 120_000),
        jitter_ms=(0, 30_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("iec61850", "ssh", "https"),
        description="Engineering workstation periodic RTAC config check.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="protection_relay",
        vertical=_V,
        pattern="configuration",
        interval_ms=(300_000, 300_000),
        jitter_ms=(0, 60_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("iec61850", "ssh"),
        description="Engineering workstation relay setting download / verify.",
    ),

    # ====================================================================
    # Local historian → RTAC.
    # ====================================================================
    CommEntry(
        src_role="local_historian",
        tgt_role="aggregator_rtu",
        vertical=_V,
        pattern="subscription",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("iec61850", "modbus_tcp"),
        description="Local historian subscribes to RTAC measurement stream.",
    ),

    # ====================================================================
    # WAN uplink: RTAC → utility EMS (modeled as wan_edge_router target).
    # In production this targets a utility-side EMS host; here the WAN
    # edge is the canonical northbound target.
    # ====================================================================
    CommEntry(
        src_role="aggregator_rtu",
        tgt_role="wan_edge_router",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("iec104", "dnp3"),
        description=(
            "RTAC northbound to utility EMS over WAN. Modeled as flow to "
            "WAN edge (real EMS host is upstream)."
        ),
    ),
)
