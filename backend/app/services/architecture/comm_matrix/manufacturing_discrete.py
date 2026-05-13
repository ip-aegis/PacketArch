# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comm matrix for manufacturing_discrete vertical.

Covers the manufacturing_discrete_cell archetype: SCADA polls cells,
historian subscribes to cells, engineering programs cells, area HMI
polls its cell, cell PLC drives field I/O cyclically, safety PLC
exchanges safety frames with cell PLC + drives.

Vendor overrides exist where the protocol differs by vendor:

  - cell_controller → distributed_io: PROFINET (siemens), EtherNet/IP
    (rockwell), Modbus TCP (schneider/abb).
  - scada → cell_controller: vendor native first; OPC UA used as
    cross-vendor fallback (e.g. multi_vendor profile).
"""

from __future__ import annotations

from app.services.architecture.archetypes._base import VendorProfile
from app.services.architecture.comm_matrix._base import CommEntry
from app.services.architecture.role_catalog import Vertical


_V = Vertical.MANUFACTURING_DISCRETE.value


MANUFACTURING_DISCRETE_ENTRIES: tuple[CommEntry, ...] = (
    # ====================================================================
    # SCADA → cell controllers (operations → cell flow).
    # Protocol is vendor-driven; OPC UA is the cross-vendor fallback.
    # ====================================================================
    CommEntry(
        src_role="scada_primary",
        tgt_role="cell_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("opc_ua",),  # cross-vendor default
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("s7comm",),
            VendorProfile.ROCKWELL_SHOP.value: ("ethernet_ip",),
            VendorProfile.SCHNEIDER_SHOP.value: ("modbus_tcp",),
            VendorProfile.ABB_SHOP.value: ("modbus_tcp",),
        },
        description="SCADA polls each cell PLC for live values.",
    ),

    # ====================================================================
    # Process historian → cell controllers (subscription pattern).
    # ====================================================================
    CommEntry(
        src_role="process_historian",
        tgt_role="cell_controller",
        vertical=_V,
        pattern="subscription",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("opc_ua",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("opc_ua", "s7comm"),
            VendorProfile.ROCKWELL_SHOP.value: ("opc_ua", "ethernet_ip"),
        },
        description="Historian subscribes to cell PLC tags for trending.",
    ),

    # ====================================================================
    # Engineering workstation → cell PLCs (occasional configure / online).
    # Vendor-pinned: TIA Portal speaks S7, Studio 5000 speaks ENIP.
    # ====================================================================
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="cell_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 30_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("opc_ua",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("s7comm",),
            VendorProfile.ROCKWELL_SHOP.value: ("ethernet_ip",),
            VendorProfile.SCHNEIDER_SHOP.value: ("modbus_tcp",),
        },
        description="Engineering workstation periodic check / online edit.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="safety_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(120_000, 120_000),
        jitter_ms=(0, 30_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("opc_ua",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("s7comm",),
            VendorProfile.ROCKWELL_SHOP.value: ("ethernet_ip",),
        },
        description="Engineering workstation safety PLC config check.",
    ),

    # ====================================================================
    # Area HMI → cell controller (in-cell poll).
    # ====================================================================
    CommEntry(
        src_role="area_hmi",
        tgt_role="cell_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("opc_ua",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("s7comm",),
            VendorProfile.ROCKWELL_SHOP.value: ("ethernet_ip",),
            VendorProfile.SCHNEIDER_SHOP.value: ("modbus_tcp",),
            VendorProfile.ABB_SHOP.value: ("modbus_tcp",),
        },
        description="Area HMI polls its cell's main PLC.",
    ),

    # ====================================================================
    # Cell controller → field (cyclic I/O — vendor-pinned).
    # ====================================================================
    CommEntry(
        src_role="cell_controller",
        tgt_role="distributed_io",
        vertical=_V,
        pattern="cyclic_io",
        interval_ms=(4, 4),
        jitter_ms=(0, 1),
        protocol_options=("modbus_tcp",),  # safest universal default
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
            VendorProfile.ROCKWELL_SHOP.value: ("ethernet_ip",),
            VendorProfile.SCHNEIDER_SHOP.value: ("modbus_tcp", "ethernet_ip"),
            VendorProfile.ABB_SHOP.value: ("profinet", "modbus_tcp"),
        },
        description="Cell PLC cyclic IO to distributed IO blocks.",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="vfd",
        vertical=_V,
        pattern="cyclic_io",
        interval_ms=(8, 8),
        jitter_ms=(0, 1),
        protocol_options=("modbus_tcp",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
            VendorProfile.ROCKWELL_SHOP.value: ("ethernet_ip",),
            VendorProfile.SCHNEIDER_SHOP.value: ("modbus_tcp",),
            VendorProfile.ABB_SHOP.value: ("modbus_tcp", "profinet"),
        },
        description="Cell PLC drive control (speed/torque cmd, status).",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="servo",
        vertical=_V,
        pattern="cyclic_io",
        interval_ms=(2, 2),  # tight motion loop
        jitter_ms=(0, 0),
        protocol_options=("ethernet_ip",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
            VendorProfile.ROCKWELL_SHOP.value: ("ethernet_ip",),
        },
        description="Cell PLC tight motion control to servo drive.",
    ),

    # ====================================================================
    # Safety controller → cell PLC + drives + IO (safety-rated frames).
    # ====================================================================
    CommEntry(
        src_role="safety_controller",
        tgt_role="cell_controller",
        vertical=_V,
        pattern="safety",
        interval_ms=(4, 4),
        jitter_ms=(0, 0),
        protocol_options=("modbus_tcp",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profisafe",),
            VendorProfile.ROCKWELL_SHOP.value: ("cip_safety",),
        },
        description="Safety PLC ↔ regular PLC safety frame exchange.",
    ),
    CommEntry(
        src_role="safety_controller",
        tgt_role="vfd",
        vertical=_V,
        pattern="safety",
        interval_ms=(4, 4),
        jitter_ms=(0, 0),
        protocol_options=("modbus_tcp",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profisafe",),
            VendorProfile.ROCKWELL_SHOP.value: ("cip_safety",),
        },
        description="Safety PLC drive STO / safety speed enforcement.",
    ),
    CommEntry(
        src_role="safety_controller",
        tgt_role="distributed_io",
        vertical=_V,
        pattern="safety",
        interval_ms=(4, 4),
        jitter_ms=(0, 0),
        protocol_options=("modbus_tcp",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profisafe",),
            VendorProfile.ROCKWELL_SHOP.value: ("cip_safety",),
        },
        description="Safety PLC ↔ safety I/O block.",
    ),

    # ====================================================================
    # Robot / CNC integration (Phase 9 audit).
    # ====================================================================

    # Cell PLC orchestrates the robot — handshake + program control.
    CommEntry(
        src_role="cell_controller",
        tgt_role="robot_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(50, 50),
        jitter_ms=(0, 5),
        protocol_options=("ethernet_ip", "modbus_tcp"),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
            VendorProfile.ROCKWELL_SHOP.value: ("ethernet_ip",),
        },
        description="Cell PLC ↔ robot controller (handshake + program).",
    ),
    # Robot drives its servos directly (vendor-internal usually, but
    # modeled here as the robot polling field servos for cell-internal
    # motion-coordinated tasks).
    CommEntry(
        src_role="robot_controller",
        tgt_role="servo",
        vertical=_V,
        pattern="cyclic_io",
        interval_ms=(4, 4),
        jitter_ms=(0, 0),
        protocol_options=("ethernet_ip",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
        },
        description="Robot controller motion coordination.",
    ),
    # Safety PLC handshake with robot for E-stop / safety-rated speed.
    CommEntry(
        src_role="safety_controller",
        tgt_role="robot_controller",
        vertical=_V,
        pattern="safety",
        interval_ms=(8, 8),
        jitter_ms=(0, 0),
        protocol_options=("modbus_tcp",),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profisafe",),
            VendorProfile.ROCKWELL_SHOP.value: ("cip_safety",),
        },
        description="Safety PLC ↔ robot for E-stop / SLS handshake.",
    ),

    # Cell PLC orchestrates CNC.
    CommEntry(
        src_role="cell_controller",
        tgt_role="cnc_controller",
        vertical=_V,
        pattern="poll",
        interval_ms=(100, 100),
        jitter_ms=(0, 10),
        protocol_options=("ethernet_ip", "modbus_tcp"),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
            VendorProfile.ROCKWELL_SHOP.value: ("ethernet_ip",),
        },
        description="Cell PLC ↔ CNC machine (job-load handshake).",
    ),

    # Engineering workstation programs robots / CNCs.
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="robot_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(120_000, 120_000),
        jitter_ms=(0, 30_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("ethernet_ip", "ssh"),
        description="Engineering programs robot / loads new programs.",
    ),
    CommEntry(
        src_role="engineering_workstation",
        tgt_role="cnc_controller",
        vertical=_V,
        pattern="configuration",
        interval_ms=(180_000, 180_000),
        jitter_ms=(0, 30_000),
        phase_tags=("steady", "maintenance"),
        protocol_options=("ethernet_ip", "ssh"),
        description="Engineering loads CNC programs / verifies config.",
    ),

    # Vision / barcode polled by cell PLC for inspection results.
    CommEntry(
        src_role="cell_controller",
        tgt_role="vision_system",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("ethernet_ip", "modbus_tcp"),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
        },
        description="Cell PLC pulls vision-inspection result.",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="barcode_scanner",
        vertical=_V,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("ethernet_ip", "modbus_tcp"),
        vendor_overrides={
            VendorProfile.SIEMENS_SHOP.value: ("profinet",),
        },
        description="Cell PLC pulls barcode reads at part-tracking station.",
    ),
)
