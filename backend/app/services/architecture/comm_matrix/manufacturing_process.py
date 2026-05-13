# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comm matrix for manufacturing_process (DCS-driven plants).

DCS pattern: regulatory loops at high cadence between dcs_controller
and field_instrument / valve_actuator; modest-cadence subscription to
SCADA / historian; safety zone exchanges over SIL-rated channels;
batch server orchestrates ISA-88 phases.
"""

from __future__ import annotations

from app.services.architecture.archetypes._base import VendorProfile
from app.services.architecture.comm_matrix._base import CommEntry
from app.services.architecture.role_catalog import Vertical


_V = Vertical.MANUFACTURING_PROCESS.value


MANUFACTURING_PROCESS_ENTRIES: tuple[CommEntry, ...] = (
    # ====================================================================
    # SCADA HMI ↔ DCS controllers (1s poll over OPC UA / vendor proto).
    # ====================================================================
    CommEntry(
        src_role="scada_primary",
        tgt_role="dcs_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("opc_ua", "modbus_tcp"),
        description="DCS HMI polls each unit's DCS controllers.",
    ),

    # Historian → DCS controller (subscription).
    CommEntry(
        src_role="process_historian",
        tgt_role="dcs_controller",
        vertical=_V,
        pattern="subscription",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("opc_ua", "modbus_tcp"),
        description="Historian subscribes to DCS controller tags.",
    ),

    # Engineering workstation → DCS controller (configuration / online).
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="dcs_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(120_000, 120_000),
        jitter_ms=(0, 30_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("opc_ua", "ssh"),
        description="Engineering workstation periodic DCS health / config.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="safety_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(300_000, 300_000),
        jitter_ms=(0, 60_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("opc_ua", "ssh"),
        description="Engineering workstation reach to SIS for config check.",
    ),

    # Alarm server ← scada_primary (events flow to alarm server, but the
    # alarm server poll-pulls events from SCADA periodically).
    CommEntry(
        src_role="alarm_event_server",
        tgt_role="scada_primary",
        vertical=_V,
        pattern="event",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("opc_ua", "https"),
        description="Alarm server pulls events from SCADA.",
    ),

    # ====================================================================
    # Batch server → batch controllers (ISA-88 phase orchestration).
    # ====================================================================
    CommEntry(
        src_role="batch_server",
        tgt_role="batch_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("opc_ua", "modbus_tcp"),
        description="Batch server controls batch PLC phase execution.",
    ),

    # ====================================================================
    # DCS controller → field (regulatory loops).
    # ====================================================================
    CommEntry(
        src_role="dcs_controller",
        tgt_role="distributed_io",
        vertical=_V,
        pattern="cyclic_io",
        interval_ms=(50, 50),
        jitter_ms=(0, 5),
        protocol_options=("modbus_tcp", "ethernet_ip"),
        description="DCS controller cyclic IO to field IO blocks.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="field_instrument",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("modbus_tcp", "hart_ip"),
        description="DCS controller polls smart field instruments.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="valve_actuator",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("modbus_tcp", "hart_ip"),
        description="DCS controller modulating-valve setpoints + feedback.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="vfd",
        vertical=_V,
        pattern="poll",
        interval_ms=(100, 100),
        jitter_ms=(0, 10),
        protocol_options=("modbus_tcp",),
        description="DCS controller drive speed / status.",
    ),

    # ====================================================================
    # Safety controller exchanges
    # ====================================================================
    CommEntry(
        src_role="safety_controller",
        tgt_role="dcs_controller",
        vertical=_V,
        pattern="safety",
        interval_ms=(50, 50),
        jitter_ms=(0, 0),
        protocol_options=("modbus_tcp",),
        description="SIS handshake with DCS for safety state.",
    ),
    CommEntry(
        src_role="safety_controller",
        tgt_role="valve_actuator",
        vertical=_V,
        pattern="safety",
        interval_ms=(50, 50),
        jitter_ms=(0, 0),
        protocol_options=("modbus_tcp",),
        description="SIS direct-trip emergency shutdown valves.",
    ),

    # ====================================================================
    # Utility-zone (boilers, cooling) cell_controller polling.
    # ====================================================================
    CommEntry(
        src_role="scada_primary",
        tgt_role="cell_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("modbus_tcp", "opc_ua"),
        description="DCS HMI polls utility-zone PLCs (boilers, etc.).",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="vfd",
        vertical=_V,
        pattern="poll",
        interval_ms=(200, 200),
        jitter_ms=(0, 20),
        protocol_options=("modbus_tcp",),
        description="Utility PLC drive control.",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="field_instrument",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("modbus_tcp",),
        description="Utility PLC instrument polling.",
    ),
)


# Oil & gas reuses the manufacturing_process pattern but is registered
# under its own vertical so vendor profiles + protocol preferences can
# diverge later (e.g. HART-IP heavier in oil&gas, MQTT pickups for
# offshore).
OIL_GAS_REFINERY_ENTRIES: tuple[CommEntry, ...] = tuple(
    CommEntry(
        src_role=e.src_role,
        tgt_role=e.tgt_role,
        vertical=Vertical.OIL_GAS.value,
        pattern=e.pattern,
        interval_ms=e.interval_ms,
        jitter_ms=e.jitter_ms,
        protocol_options=e.protocol_options,
        vendor_overrides=e.vendor_overrides,
        phase_tags=e.phase_tags,
        conduit_required=e.conduit_required,
        description=e.description,
        fan_out=e.fan_out,
    )
    for e in MANUFACTURING_PROCESS_ENTRIES
)
