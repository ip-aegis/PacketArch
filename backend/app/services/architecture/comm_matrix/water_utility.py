# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comm matrix for water_utility (master/remote SCADA).

Master-remote pattern: central RTAC aggregates field RTUs over WAN.
Field-side flows happen at the station; RTAC north-side polls the
fleet; SCADA sits above RTAC.
"""

from __future__ import annotations

from app.services.architecture.comm_matrix._base import CommEntry
from app.services.architecture.role_catalog import Vertical


_V = Vertical.WATER_UTILITY.value


WATER_UTILITY_ENTRIES: tuple[CommEntry, ...] = (
    # ====================================================================
    # SCADA <-> aggregator RTU (central pivot)
    # ====================================================================
    CommEntry(
        src_role="scada_primary",
        tgt_role="aggregator_rtu",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("modbus_tcp", "dnp3"),
        description="SCADA polls central RTAC for fleet status.",
    ),
    CommEntry(
        src_role="process_historian",
        tgt_role="aggregator_rtu",
        vertical=_V,
        pattern="subscription",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("modbus_tcp", "dnp3"),
        description="Historian subscribes to RTAC fleet measurements.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="aggregator_rtu",
        vertical=_V,
        pattern="configuration",
        interval_ms=(120_000, 120_000),
        jitter_ms=(0, 30_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("ssh", "https"),
        description="Engineering workstation RTAC configuration.",
    ),

    # ====================================================================
    # Aggregator RTU <-> field RTUs (WAN backhaul)
    # ====================================================================
    CommEntry(
        src_role="aggregator_rtu",
        tgt_role="field_rtu",
        vertical=_V,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 1_000),
        protocol_options=("modbus_tcp", "dnp3"),
        description="RTAC polls each station's field RTU.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="field_rtu",
        vertical=_V,
        pattern="configuration",
        interval_ms=(600_000, 600_000),
        jitter_ms=(0, 60_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("ssh", "https"),
        description="Engineering workstation reach to remote RTU for config.",
    ),

    # ====================================================================
    # Field RTU <-> field devices (intra-station)
    # ====================================================================
    CommEntry(
        src_role="field_rtu",
        tgt_role="vfd",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("modbus_tcp",),
        description="Field RTU drive control (pump speed/status).",
    ),
    CommEntry(
        src_role="field_rtu",
        tgt_role="field_instrument",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("modbus_tcp",),
        description="Field RTU instrument polling (pressure / flow / level).",
    ),
    CommEntry(
        src_role="field_rtu",
        tgt_role="valve_actuator",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("modbus_tcp",),
        description="Field RTU valve setpoints + feedback.",
    ),
)
