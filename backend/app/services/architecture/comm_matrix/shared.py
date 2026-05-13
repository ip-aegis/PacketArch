# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cross-vertical comm-matrix entries.

These entries apply in every vertical: NMS-style switch polling, jump-
server admin reachability, AV/patch IDMZ flows, replication. A
vertical-specific entry can override a shared one by declaring the
same (src_role, tgt_role) with the vertical set.
"""

from __future__ import annotations

from app.services.architecture.comm_matrix._base import (
    SHARED_VERTICAL,
    CommEntry,
)


SHARED_ENTRIES: tuple[CommEntry, ...] = (
    # ====================================================================
    # NMS — every switch in every zone gets polled.
    # ====================================================================
    CommEntry(
        src_role="nms_server",
        tgt_role="core_switch",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp",),
        description="NMS SNMP poll of plant-core / operations switch.",
    ),
    CommEntry(
        src_role="nms_server",
        tgt_role="cell_switch",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp",),
        description="NMS SNMP poll of cell / area switch.",
    ),
    CommEntry(
        src_role="nms_server",
        tgt_role="bay_switch",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp",),
        description="NMS SNMP poll of bay / skid switch.",
    ),
    CommEntry(
        src_role="nms_server",
        tgt_role="wan_edge_router",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp",),
        description="NMS SNMP poll of WAN edge router.",
    ),

    # ====================================================================
    # Jump server — admin reachability monitoring of OT assets.
    # Legitimate generic-only-protocol pattern (audit carve-out applies).
    # ====================================================================
    CommEntry(
        src_role="jump_server",
        tgt_role="scada_primary",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(120_000, 120_000),
        jitter_ms=(0, 12_000),
        protocol_options=("snmp",),
        description="Jump-server SNMP reachability check on SCADA host.",
    ),
    CommEntry(
        src_role="jump_server",
        tgt_role="cell_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(300_000, 300_000),
        jitter_ms=(0, 30_000),
        protocol_options=("snmp",),
        description="Jump-server SNMP reachability check on cell PLC.",
    ),
    CommEntry(
        src_role="jump_server",
        tgt_role="aggregator_rtu",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(300_000, 300_000),
        jitter_ms=(0, 30_000),
        protocol_options=("snmp",),
        description="Jump-server SNMP reachability check on aggregator RTU.",
    ),
    CommEntry(
        src_role="jump_server",
        tgt_role="core_switch",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(300_000, 300_000),
        jitter_ms=(0, 30_000),
        protocol_options=("snmp",),
        description="Jump-server SNMP reachability check on core switch.",
    ),

    # ====================================================================
    # IDMZ replication / IT-side aggregation
    # ====================================================================
    CommEntry(
        src_role="historian_replica",
        tgt_role="process_historian",
        vertical=SHARED_VERTICAL,
        pattern="replication",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("opc_ua",),
        description="Historian replica subscribes to primary historian.",
    ),
    CommEntry(
        src_role="opc_ua_aggregator",
        tgt_role="cell_controller",
        vertical=SHARED_VERTICAL,
        pattern="subscription",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("opc_ua",),
        description="OPC UA aggregator subscribes to cell PLC tags.",
    ),
    CommEntry(
        src_role="opc_ua_aggregator",
        tgt_role="dcs_controller",
        vertical=SHARED_VERTICAL,
        pattern="subscription",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("opc_ua",),
        description="OPC UA aggregator subscribes to DCS controller tags.",
    ),

    # ====================================================================
    # AV / patch — IDMZ servers push to OT endpoints.
    # ====================================================================
    CommEntry(
        src_role="av_management_server",
        tgt_role="engineering_workstation",
        vertical=SHARED_VERTICAL,
        pattern="heartbeat",
        interval_ms=(900_000, 900_000),  # 15 min
        jitter_ms=(0, 60_000),
        protocol_options=("https",),
        description="AV agent heartbeat / definition push.",
    ),
    CommEntry(
        src_role="av_management_server",
        tgt_role="scada_primary",
        vertical=SHARED_VERTICAL,
        pattern="heartbeat",
        interval_ms=(900_000, 900_000),
        jitter_ms=(0, 60_000),
        protocol_options=("https",),
        description="AV agent heartbeat / definition push to SCADA host.",
    ),
    CommEntry(
        src_role="patch_staging_server",
        tgt_role="engineering_workstation",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(3_600_000, 3_600_000),  # 1 hr
        jitter_ms=(0, 300_000),
        protocol_options=("https",),
        description="WSUS-style patch poll from engineering workstation.",
    ),

    # ====================================================================
    # Remote access gateway — vendor cloud heartbeat
    # ====================================================================
    CommEntry(
        src_role="remote_access_gateway",
        tgt_role="cell_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(10_000, 10_000),
        jitter_ms=(0, 1_000),
        protocol_options=("modbus_tcp", "ethernet_ip", "snmp"),
        description="Remote-access gateway pulls limited tags for cloud UI.",
    ),

    # ====================================================================
    # NTP — coarse time sync
    # ====================================================================
    CommEntry(
        src_role="dns_ntp_relay",
        tgt_role="scada_primary",
        vertical=SHARED_VERTICAL,
        pattern="event",
        interval_ms=(64_000, 64_000),
        jitter_ms=(0, 8_000),
        protocol_options=("ntp",),
        description="NTP time sync to SCADA primary.",
    ),

    # ====================================================================
    # Phase 9 vertical-audit roles — make sure cameras / DMS / pdu /
    # ups / crac / vav / ahu / chiller / room / agv / barcode / rfid /
    # vision / analyzer / flow_meter / power_meter all get inbound
    # flow coverage so they're not orphaned regardless of vertical.
    # ====================================================================

    # NMS polls each new field-class role over SNMP (the universal
    # discovery / health-check pattern).
    *(CommEntry(
        src_role="nms_server",
        tgt_role=role,
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("snmp",),
        description=f"NMS SNMP health-poll of {role}.",
    ) for role in (
        "vav_controller", "ahu_controller", "chiller_controller",
        "room_controller", "pdu", "ups_unit", "crac_unit",
        "agv", "barcode_scanner", "rfid_reader", "vision_system",
        "analyzer", "flow_meter", "power_meter",
    )),

    # AGV fleet manager <-> AGV (mobile-robot orchestration).
    CommEntry(
        src_role="fleet_manager",
        tgt_role="agv",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("https", "mqtt"),
        description="Fleet manager dispatches tasks + tracks AGV state.",
    ),

    # Conveyor controller pulls barcode reads.
    CommEntry(
        src_role="conveyor_controller",
        tgt_role="barcode_scanner",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("https", "modbus_tcp", "ethernet_ip"),
        description="Conveyor PLC pulls barcode reads.",
    ),
    CommEntry(
        src_role="conveyor_controller",
        tgt_role="vision_system",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("ethernet_ip", "modbus_tcp", "https"),
        description="Conveyor PLC pulls vision-inspection results.",
    ),

    # WCS pulls RFID tags.
    CommEntry(
        src_role="wcs_controller",
        tgt_role="rfid_reader",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("https", "ethernet_ip"),
        description="WCS pulls RFID-reader transactions.",
    ),

    # BAS supervisor polls VAV / AHU / room controllers + chiller.
    CommEntry(
        src_role="bms_field_controller",
        tgt_role="vav_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("bacnet", "modbus_tcp"),
        description="JACE supervisor polls zone VAV terminal units.",
    ),
    CommEntry(
        src_role="bms_field_controller",
        tgt_role="ahu_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("bacnet", "modbus_tcp"),
        description="JACE supervisor polls AHU controller.",
    ),
    CommEntry(
        src_role="bms_field_controller",
        tgt_role="room_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(10_000, 10_000),
        jitter_ms=(0, 1_000),
        protocol_options=("bacnet", "modbus_tcp"),
        description="JACE supervisor polls room / zone controllers.",
    ),
    CommEntry(
        src_role="scada_primary",
        tgt_role="chiller_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(10_000, 10_000),
        jitter_ms=(0, 1_000),
        protocol_options=("bacnet", "modbus_tcp", "snmp"),
        description="BAS / DCIM SCADA polls chiller plant controller.",
    ),
    CommEntry(
        src_role="chiller_controller",
        tgt_role="vfd",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("bacnet", "modbus_tcp"),
        description="Chiller controller drives chilled-water + tower VFDs.",
    ),
    CommEntry(
        src_role="chiller_controller",
        tgt_role="field_instrument",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("bacnet", "modbus_tcp"),
        description="Chiller controller polls plant temperature / flow sensors.",
    ),
    CommEntry(
        src_role="bms_field_controller",
        tgt_role="chiller_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(10_000, 10_000),
        jitter_ms=(0, 1_000),
        protocol_options=("bacnet", "modbus_tcp"),
        description="BAS supervisor polls chiller plant.",
    ),
    CommEntry(
        src_role="ahu_controller",
        tgt_role="vfd",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("bacnet", "modbus_tcp"),
        description="AHU controller drives supply-fan VFD.",
    ),
    CommEntry(
        src_role="vav_controller",
        tgt_role="field_instrument",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(10_000, 10_000),
        jitter_ms=(0, 1_000),
        protocol_options=("bacnet",),
        description="VAV controller reads zone temperature sensor.",
    ),

    # SCADA polls power meter (revenue-grade telemetry).
    CommEntry(
        src_role="scada_primary",
        tgt_role="power_meter",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("modbus_tcp", "iec61850", "snmp"),
        description="SCADA polls revenue-grade power meter.",
    ),
    CommEntry(
        src_role="aggregator_rtu",
        tgt_role="power_meter",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("modbus_tcp", "iec61850"),
        description="RTAC polls bay power meter.",
    ),

    # DCS / SCADA polls process analyzers + flow meters.
    CommEntry(
        src_role="dcs_controller",
        tgt_role="analyzer",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("modbus_tcp", "hart_ip"),
        description="DCS polls continuous gas / liquid analyzer.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="flow_meter",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("modbus_tcp", "hart_ip"),
        description="DCS polls custody-transfer flow meter.",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="flow_meter",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("modbus_tcp", "ethernet_ip"),
        description="Process PLC reads flow meter.",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="analyzer",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("modbus_tcp",),
        description="Process PLC reads analyzer.",
    ),

    # Per-unit area HMI polls DCS controller (oil&gas, process mfg, energy).
    CommEntry(
        src_role="area_hmi",
        tgt_role="dcs_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("opc_ua", "modbus_tcp"),
        description="Per-unit operator HMI polls its DCS controller.",
    ),

    # ====================================================================
    # Phase 10: cross-vertical DCS / cell-controller field flows that
    # weren't in vertical-specific matrices but need to apply to the
    # new showcase templates (semiconductor fab, battery, pharma).
    # ====================================================================

    # DCS controller polls field equipment (universal pattern across
    # discrete + process + energy verticals).
    CommEntry(
        src_role="dcs_controller",
        tgt_role="field_instrument",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("modbus_tcp", "hart_ip"),
        description="DCS controller polls field instrument.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="valve_actuator",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("modbus_tcp", "hart_ip"),
        description="DCS controller modulates valve setpoint + reads feedback.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="vfd",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(100, 100),
        jitter_ms=(0, 10),
        protocol_options=("modbus_tcp",),
        description="DCS controller drives auxiliary VFDs.",
    ),
    CommEntry(
        src_role="dcs_controller",
        tgt_role="distributed_io",
        vertical=SHARED_VERTICAL,
        pattern="cyclic_io",
        interval_ms=(50, 50),
        jitter_ms=(0, 5),
        protocol_options=("modbus_tcp", "ethernet_ip"),
        description="DCS cyclic IO to field IO blocks.",
    ),

    # Cell controller polls field equipment (covers utility / cleanroom
    # / fill-finish PLCs in showcase templates).
    CommEntry(
        src_role="cell_controller",
        tgt_role="field_instrument",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("modbus_tcp", "ethernet_ip"),
        description="Cell PLC polls field instrument.",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="valve_actuator",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("modbus_tcp", "ethernet_ip"),
        description="Cell PLC valve setpoint + feedback.",
    ),
    CommEntry(
        src_role="cell_controller",
        tgt_role="servo",
        vertical=SHARED_VERTICAL,
        pattern="cyclic_io",
        interval_ms=(4, 4),
        jitter_ms=(0, 0),
        protocol_options=("ethernet_ip", "modbus_tcp"),
        description="Cell PLC tight motion control to servo.",
    ),

    # Area HMI polls cell controller (peer to area_hmi → dcs_controller).
    CommEntry(
        src_role="area_hmi",
        tgt_role="cell_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(500, 500),
        jitter_ms=(0, 50),
        protocol_options=("opc_ua", "modbus_tcp", "ethernet_ip"),
        description="Per-unit operator HMI polls cell PLC.",
    ),

    # Recipe / batch server pushes recipes to DCS (semi fab + pharma).
    CommEntry(
        src_role="batch_server",
        tgt_role="dcs_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(1_000, 1_000),
        jitter_ms=(0, 100),
        protocol_options=("opc_ua", "modbus_tcp"),
        description="Recipe / batch server downloads recipes to DCS.",
    ),

    # Robot polls field IO + valve (battery cell pack assembly,
    # semi fab wafer-handler robots, etc.).
    CommEntry(
        src_role="robot_controller",
        tgt_role="distributed_io",
        vertical=SHARED_VERTICAL,
        pattern="cyclic_io",
        interval_ms=(8, 8),
        jitter_ms=(0, 1),
        protocol_options=("ethernet_ip", "profinet"),
        description="Robot cyclic IO to its end-of-arm tooling.",
    ),

    # ====================================================================
    # SCADA primary <-> standby — replication / failover sync.
    # ====================================================================
    CommEntry(
        src_role="scada_primary",
        tgt_role="scada_standby",
        vertical=SHARED_VERTICAL,
        pattern="replication",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("https", "snmp"),
        description="SCADA primary -> standby state replication.",
    ),

    # ====================================================================
    # Remote access gateway -> SCADA (the typical L3 pivot point for
    # remote service techs reaching the plant). Cell-direct paths are
    # added per-vertical when the conduit allows it.
    # ====================================================================
    CommEntry(
        src_role="remote_access_gateway",
        tgt_role="scada_primary",
        vertical=SHARED_VERTICAL,
        pattern="heartbeat",
        interval_ms=(30_000, 30_000),
        jitter_ms=(0, 3_000),
        protocol_options=("https", "snmp"),
        description=(
            "Remote-access gateway pivots through SCADA (admin reachability "
            "monitoring). Direct cell access requires explicit conduit."
        ),
    ),

    # ====================================================================
    # Asset-management — polls controllers for firmware / config audit.
    # ====================================================================
    CommEntry(
        src_role="asset_management_server",
        tgt_role="cell_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(3_600_000, 3_600_000),  # 1 hr
        jitter_ms=(0, 300_000),
        protocol_options=("https", "snmp"),
        description="Asset-mgmt audit poll of cell PLC firmware / config.",
    ),
    CommEntry(
        src_role="asset_management_server",
        tgt_role="dcs_controller",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(3_600_000, 3_600_000),
        jitter_ms=(0, 300_000),
        protocol_options=("https", "snmp"),
        description="Asset-mgmt audit poll of DCS controller firmware / config.",
    ),
    CommEntry(
        src_role="asset_management_server",
        tgt_role="aggregator_rtu",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(3_600_000, 3_600_000),
        jitter_ms=(0, 300_000),
        protocol_options=("https", "snmp"),
        description="Asset-mgmt audit poll of RTAC firmware.",
    ),
    CommEntry(
        src_role="asset_management_server",
        tgt_role="protection_relay",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(3_600_000, 3_600_000),
        jitter_ms=(0, 300_000),
        protocol_options=("https", "snmp"),
        description="Asset-mgmt audit poll of protection relay settings.",
    ),

    # ====================================================================
    # Alarm server — pulls events from SCADA. (Vertical-specific entries
    # exist for manufacturing_process and energy_generation; this shared
    # one keeps the alarm server tied in for any vertical that uses it.)
    # ====================================================================
    CommEntry(
        src_role="alarm_event_server",
        tgt_role="scada_primary",
        vertical=SHARED_VERTICAL,
        pattern="event",
        interval_ms=(5_000, 5_000),
        jitter_ms=(0, 500),
        protocol_options=("https", "opc_ua"),
        description="Alarm server pulls events from SCADA.",
    ),

    # ====================================================================
    # MES — pulls KPIs from historian, pushes work orders to SCADA.
    # ====================================================================
    CommEntry(
        src_role="mes_server",
        tgt_role="process_historian",
        vertical=SHARED_VERTICAL,
        pattern="subscription",
        interval_ms=(10_000, 10_000),
        jitter_ms=(0, 1_000),
        protocol_options=("opc_ua", "https"),
        description="MES pulls KPIs / production data from historian.",
    ),
    CommEntry(
        src_role="mes_server",
        tgt_role="scada_primary",
        vertical=SHARED_VERTICAL,
        pattern="poll",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("https", "opc_ua"),
        description="MES pushes / pulls production state to SCADA.",
    ),

    # ====================================================================
    # OPC UA aggregator — also subscribes to L3 historian as a fallback
    # path (avoids needing an explicit IDMZ→cell conduit).
    # ====================================================================
    CommEntry(
        src_role="opc_ua_aggregator",
        tgt_role="process_historian",
        vertical=SHARED_VERTICAL,
        pattern="subscription",
        interval_ms=(2_000, 2_000),
        jitter_ms=(0, 200),
        protocol_options=("opc_ua",),
        description="OPC UA aggregator pulls aggregated tags from L3 historian.",
    ),

    # ====================================================================
    # Reverse proxy — fronts SCADA / historian web UIs for IT consumers.
    # ====================================================================
    CommEntry(
        src_role="reverse_proxy",
        tgt_role="scada_primary",
        vertical=SHARED_VERTICAL,
        pattern="heartbeat",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("https",),
        description="Reverse proxy backend health probe to SCADA.",
    ),
    CommEntry(
        src_role="reverse_proxy",
        tgt_role="process_historian",
        vertical=SHARED_VERTICAL,
        pattern="heartbeat",
        interval_ms=(60_000, 60_000),
        jitter_ms=(0, 6_000),
        protocol_options=("https",),
        description="Reverse proxy backend health probe to historian.",
    ),
)
