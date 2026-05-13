# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comm matrix for data_center_infra (DCIM-centric)."""

from __future__ import annotations

from app.services.architecture.comm_matrix._base import CommEntry
from app.services.architecture.role_catalog import Vertical


_V = Vertical.DATA_CENTER_INFRA.value


DATA_CENTER_INFRA_ENTRIES: tuple[CommEntry, ...] = (
    # DCIM polls PDUs (modeled as vfd) over SNMP / Modbus.
    CommEntry(
        src_role="scada_primary",
        tgt_role="vfd",
        vertical=_V,
        pattern="poll",
        interval_ms=(30_000, 30_000),
        jitter_ms=(0, 3_000),
        protocol_options=("snmp", "modbus_tcp"),
        description="DCIM polls PDUs / UPSes for power telemetry.",
    ),
    # DCIM polls environmental sensors.
    CommEntry(
        src_role="scada_primary",
        tgt_role="field_instrument",
        vertical=_V,
        pattern="poll",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp", "modbus_tcp", "bacnet"),
        description="DCIM polls environmental / branch-circuit monitors.",
    ),
    # DCIM polls cooling / BMS controllers.
    CommEntry(
        src_role="scada_primary",
        tgt_role="bms_field_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(10_000, 10_000),
        jitter_ms=(0, 1_000),
        protocol_options=("bacnet", "modbus_tcp", "snmp"),
        description="DCIM polls CRAC / chiller controllers.",
    ),
    # DCIM polls power-zone PLC.
    CommEntry(
        src_role="scada_primary",
        tgt_role="cell_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("modbus_tcp", "snmp"),
        description="DCIM polls power-plant PLC (UPS / ATS / generator).",
    ),
    # Power PLC -> field.
    CommEntry(
        src_role="cell_controller",
        tgt_role="vfd",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("modbus_tcp",),
        description="Power-plant PLC polls UPS / ATS units.",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="field_instrument",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("modbus_tcp",),
        description="Power-plant PLC polls voltage / current sensors.",
    ),
    # BMS controller -> field (cooling-zone).
    CommEntry(
        src_role="bms_field_controller",
        tgt_role="vfd",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("bacnet", "modbus_tcp"),
        description="CRAC controller polls chiller VFDs.",
    ),
    CommEntry(
        src_role="bms_field_controller",
        tgt_role="field_instrument",
        vertical=_V,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("bacnet", "modbus_tcp"),
        description="CRAC controller polls cooling sensors.",
    ),

    # DCIM historian subscribes to facility data.
    CommEntry(
        src_role="process_historian",
        tgt_role="vfd",
        vertical=_V,
        pattern="subscription",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp", "modbus_tcp"),
        description="DCIM historian trends PDU power telemetry.",
    ),
    CommEntry(
        src_role="process_historian",
        tgt_role="bms_field_controller",
        vertical=_V,
        pattern="subscription",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("bacnet", "modbus_tcp"),
        description="DCIM historian trends cooling state.",
    ),

    # Engineering workstation pushes config to BMS / power-zone PLC.
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="bms_field_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(600_000, 600_000),
        jitter_ms=(0, 60_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("https", "ssh", "bacnet"),
        description="Eng workstation BMS controller config.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="cell_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(600_000, 600_000),
        jitter_ms=(0, 60_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("https", "ssh", "modbus_tcp"),
        description="Eng workstation power-zone PLC config.",
    ),
)
