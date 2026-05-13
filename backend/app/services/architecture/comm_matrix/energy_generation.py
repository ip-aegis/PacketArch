# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comm matrix for energy_generation (combined-cycle gas turbine plants).

Reuses the manufacturing_process DCS shape but with vertical-specific
generator-protection traffic (IEC 61850 GOOSE on the electrical side)
and turbine-control specifics.
"""

from __future__ import annotations

from app.services.architecture.comm_matrix._base import CommEntry
from app.services.architecture.role_catalog import Vertical


_V = Vertical.ENERGY_GENERATION.value


ENERGY_GENERATION_ENTRIES: tuple[CommEntry, ...] = (
    # SCADA <-> DCS controllers (turbine controls).
    CommEntry(
        src_role="scada_primary",
        tgt_role="dcs_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("opc_ua", "modbus_tcp"),
        description="DCS HMI polls turbine controls.",
    ),
    CommEntry(
        src_role="process_historian",
        tgt_role="dcs_controller",
        vertical=_V,
        pattern="subscription",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("opc_ua",),
        description="Historian subscribes to turbine measurements.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="dcs_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(180_000, 180_000),
        jitter_ms=(0, 30_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("opc_ua", "ssh"),
        description="Eng workstation periodic turbine config check.",
    ),
    CommEntry(
        src_role="alarm_event_server",
        tgt_role="scada_primary",
        vertical=_V,
        pattern="event",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("opc_ua",),
        description="Alarm server pulls events from SCADA.",
    ),

    # DCS controller -> field.
    CommEntry(
        src_role="dcs_controller",
        tgt_role="distributed_io",
        vertical=_V,
        pattern="cyclic_io",
        interval_ms=(50, 50),
        jitter_ms=(0, 5),
        protocol_options=("modbus_tcp", "ethernet_ip"),
        description="Turbine controller cyclic IO.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="field_instrument",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("modbus_tcp",),
        description="Turbine controller instrument polling.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="valve_actuator",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("modbus_tcp",),
        description="Fuel / steam valve setpoints + feedback.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="vfd",
        vertical=_V,
        pattern="poll",
        interval_ms=(100, 100),
        jitter_ms=(0, 10),
        protocol_options=("modbus_tcp",),
        description="Auxiliary motor / pump VFDs (lube oil, fuel pumps).",
    ),

    # Safety zone (BMS / E-stop).
    CommEntry(
        src_role="safety_controller",
        tgt_role="dcs_controller",
        vertical=_V,
        pattern="safety",
        interval_ms=(50, 50),
        jitter_ms=(0, 0),
        protocol_options=("modbus_tcp",),
        description="SIS handshake with turbine controls.",
    ),
    CommEntry(
        src_role="safety_controller",
        tgt_role="valve_actuator",
        vertical=_V,
        pattern="safety",
        interval_ms=(50, 50),
        jitter_ms=(0, 0),
        protocol_options=("modbus_tcp",),
        description="SIS direct trip of fuel valves.",
    ),

    # Electrical zone (generator protection).
    CommEntry(
        src_role="protection_relay",
        tgt_role="protection_relay",
        vertical=_V,
        pattern="event",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 0),
        protocol_options=("iec61850",),
        fan_out="pair",
        description="GOOSE multicast among generator-protection IEDs.",
    ),
    CommEntry(
        src_role="scada_primary",
        tgt_role="protection_relay",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("iec61850", "modbus_tcp"),
        description="DCS HMI polls generator protection.",
    ),
    CommEntry(
        src_role="scada_primary",
        tgt_role="field_instrument",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("modbus_tcp",),
        description="DCS HMI polls electrical-zone instruments.",
    ),
)
