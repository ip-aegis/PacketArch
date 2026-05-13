# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comm matrix for building_automation (BACnet/IP-centric)."""

from __future__ import annotations

from app.services.architecture.comm_matrix._base import CommEntry
from app.services.architecture.role_catalog import Vertical


_V = Vertical.BUILDING_AUTOMATION.value


BUILDING_AUTOMATION_ENTRIES: tuple[CommEntry, ...] = (
    # BAS supervisor <-> field controllers (BACnet primary).
    CommEntry(
        src_role="scada_primary",
        tgt_role="bms_field_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("bacnet", "modbus_tcp"),
        description="BAS supervisor polls zone BMS controllers via BACnet.",
    ),
    CommEntry(
        src_role="process_historian",
        tgt_role="bms_field_controller",
        vertical=_V,
        pattern="subscription",
        interval_ms=(30_000, 30_000),
        jitter_ms=(0, 3_000),
        protocol_options=("bacnet",),
        description="BAS historian trends from field controllers.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="bms_field_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(300_000, 300_000),
        jitter_ms=(0, 60_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("https", "ssh", "bacnet"),
        description="BAS engineering workstation config / diagnostics.",
    ),

    # BMS field controller <-> field (HVAC).
    CommEntry(
        src_role="bms_field_controller",
        tgt_role="vfd",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("bacnet", "modbus_tcp"),
        description="BAS controller fan / pump VFD setpoints.",
    ),
    CommEntry(
        src_role="bms_field_controller",
        tgt_role="field_instrument",
        vertical=_V,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("bacnet", "modbus_tcp"),
        description="BAS controller polls zone HVAC sensors.",
    ),
    CommEntry(
        src_role="bms_field_controller",
        tgt_role="valve_actuator",
        vertical=_V,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("bacnet", "modbus_tcp"),
        description="BAS controller valve setpoints (chilled water, etc.).",
    ),
)
