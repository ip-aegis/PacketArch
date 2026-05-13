# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comm matrix for distribution_logistics (warehouse / sortation)."""

from __future__ import annotations

from app.services.architecture.archetypes._base import VendorProfile
from app.services.architecture.comm_matrix._base import CommEntry
from app.services.architecture.role_catalog import Vertical


_V = Vertical.DISTRIBUTION_LOGISTICS.value


DISTRIBUTION_LOGISTICS_ENTRIES: tuple[CommEntry, ...] = (
    # WMS <-> WCS (zone-supervisor PLC).
    CommEntry(
        src_role="scada_primary",
        tgt_role="wcs_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("ethernet_ip", "modbus_tcp", "opc_ua"),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("s7comm", "profinet"),
        },
        description="WMS sends pick/wave/putaway tasks to zone WCS PLC.",
    ),
    CommEntry(
        src_role="process_historian",
        tgt_role="wcs_controller",
        vertical=_V,
        pattern="subscription",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("opc_ua", "ethernet_ip"),
        description="Throughput historian subscribes to WCS counters.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="wcs_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(120_000, 120_000),
        jitter_ms=(0, 30_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("ethernet_ip", "modbus_tcp", "opc_ua"),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("s7comm",),
        },
        description="Engineering workstation programs WCS PLCs.",
    ),

    # WCS -> conveyor controllers (zone PLC peer comms).
    CommEntry(
        src_role="wcs_controller",
        tgt_role="conveyor_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(100, 100),
        jitter_ms=(0, 10),
        protocol_options=("ethernet_ip", "modbus_tcp"),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet", "s7comm"),
        },
        description="Zone WCS coordinates with conveyor PLCs.",
    ),

    # Conveyor controller -> field (motion).
    CommEntry(
        src_role="conveyor_controller",
        tgt_role="vfd",
        vertical=_V,
        pattern="cyclic_io",
        interval_ms=(8, 8),
        jitter_ms=(0, 1),
        protocol_options=("ethernet_ip",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
        },
        description="Conveyor PLC tight motion control to drives.",
    ),
    CommEntry(
        src_role="conveyor_controller",
        tgt_role="distributed_io",
        vertical=_V,
        pattern="cyclic_io",
        interval_ms=(4, 4),
        jitter_ms=(0, 1),
        protocol_options=("ethernet_ip",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
        },
        description="Conveyor PLC cyclic IO to sortation IO blocks.",
    ),

    # Area HMI -> WCS controller.
    CommEntry(
        src_role="area_hmi",
        tgt_role="wcs_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("ethernet_ip", "modbus_tcp"),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("s7comm",),
        },
        description="Zone HMI polls WCS PLC for pick status.",
    ),

    # MES -> historian / WMS integration.
    CommEntry(
        src_role="mes_server",
        tgt_role="process_historian",
        vertical=_V,
        pattern="subscription",
        interval_ms=(10_000, 10_000),
        jitter_ms=(0, 1_000),
        protocol_options=("opc_ua", "https"),
        description="MES pulls throughput / KPIs from historian.",
    ),
)
