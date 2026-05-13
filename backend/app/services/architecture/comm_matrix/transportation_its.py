# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comm matrix for transportation_its (NTCIP-over-SNMP)."""

from __future__ import annotations

from app.services.architecture.comm_matrix._base import CommEntry
from app.services.architecture.role_catalog import Vertical


_V = Vertical.TRANSPORTATION_ITS.value


TRANSPORTATION_ITS_ENTRIES: tuple[CommEntry, ...] = (
    # ATMS master polls each intersection's traffic controller via NTCIP
    # (which rides on SNMP — that's why SNMP is the operational protocol
    # here, not just admin-style).
    CommEntry(
        src_role="scada_primary",
        tgt_role="traffic_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("snmp",),
        description="ATMS master polls traffic controllers via NTCIP/SNMP.",
    ),
    CommEntry(
        src_role="scada_primary",
        tgt_role="cabinet_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("snmp", "https"),
        description="ATMS master polls cabinet auxiliaries.",
    ),
    CommEntry(
        src_role="process_historian",
        tgt_role="traffic_controller",
        vertical=_V,
        pattern="subscription",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp",),
        description="Traffic historian samples controller state for trend.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="traffic_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(600_000, 600_000),
        jitter_ms=(0, 60_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("ssh", "https", "snmp"),
        description="Engineer downloads timing plans / firmware to cabinet.",
    ),

    # ============================================================
    # ITS field equipment (Phase 9): cameras, DMS, RSU, RWIS, toll.
    # ============================================================

    # ATMS master polls cameras for SNMP health + RTSP stream.
    CommEntry(
        src_role="scada_primary",
        tgt_role="cctv_camera",
        vertical=_V,
        pattern="poll",
        interval_ms=(30_000, 30_000),
        jitter_ms=(0, 3_000),
        protocol_options=("snmp", "rtsp"),
        description="ATMS master health-polls fixed CCTV cameras.",
    ),
    CommEntry(
        src_role="scada_primary",
        tgt_role="ptz_camera",
        vertical=_V,
        pattern="poll",
        interval_ms=(10_000, 10_000),
        jitter_ms=(0, 1_000),
        protocol_options=("snmp", "rtsp", "https"),
        description="ATMS master polls PTZ cameras + sends control cmds.",
    ),
    CommEntry(
        src_role="scada_primary",
        tgt_role="anpr_camera",
        vertical=_V,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("snmp", "https"),
        description="ATMS master polls ANPR cameras for plate-read events.",
    ),

    # ATMS master pushes content to DMS signs via NTCIP / SNMP.
    CommEntry(
        src_role="scada_primary",
        tgt_role="dms_sign",
        vertical=_V,
        pattern="poll",
        interval_ms=(15_000, 15_000),
        jitter_ms=(0, 1_500),
        protocol_options=("snmp", "https"),
        description="ATMS master health-polls + pushes messages to DMS.",
    ),

    # ATMS master polls RWIS for road / weather data.
    CommEntry(
        src_role="scada_primary",
        tgt_role="rwis_station",
        vertical=_V,
        pattern="poll",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp",),
        description="ATMS master polls RWIS road-weather station.",
    ),

    # ============================================================
    # Toll plaza specifics — lane controller orchestrates RSU + ANPR.
    # ============================================================

    # Toll lane controller polls its DSRC RSU for transactions.
    CommEntry(
        src_role="toll_lane_controller",
        tgt_role="toll_rsu",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("snmp", "https"),
        description="ETC lane controller polls DSRC RSU for transponder reads.",
    ),
    # Toll lane controller polls its ANPR camera for enforcement images.
    CommEntry(
        src_role="toll_lane_controller",
        tgt_role="anpr_camera",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("https", "snmp"),
        description="Toll lane controller pulls plate reads from ANPR.",
    ),

    # ATMS master aggregates from toll lane controllers + RSU stats.
    CommEntry(
        src_role="scada_primary",
        tgt_role="toll_lane_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("snmp", "https"),
        description="ATMS master polls toll lane controllers for state.",
    ),
    CommEntry(
        src_role="scada_primary",
        tgt_role="toll_rsu",
        vertical=_V,
        pattern="poll",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp",),
        description="ATMS master health-polls DSRC RSUs.",
    ),

    # Engineering workstation pushes config to ITS field gear.
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="dms_sign",
        vertical=_V,
        pattern="configuration",
        interval_ms=(600_000, 600_000),
        jitter_ms=(0, 60_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("snmp", "https", "ssh"),
        description="Engineer pushes DMS firmware / fonts.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="cctv_camera",
        vertical=_V,
        pattern="configuration",
        interval_ms=(900_000, 900_000),
        jitter_ms=(0, 60_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("https", "ssh"),
        description="Engineer reaches CCTV for firmware / config check.",
    ),

    # Historian subscribes to DMS / camera / toll telemetry.
    CommEntry(
        src_role="process_historian",
        tgt_role="toll_lane_controller",
        vertical=_V,
        pattern="subscription",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("https", "snmp"),
        description="Historian streams toll-transaction events.",
    ),
)
