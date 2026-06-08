# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Distribution and Logistics industry scenario templates.

Primary Vendors: KUKA, MiR (AGVs), Rockwell, Siemens (conveyors), Cognex (vision), Impinj/Zebra (RFID)
Protocol Focus: EtherNet/IP (Rockwell conveyors, AGVs), PROFINET (KUKA/Siemens), Modbus TCP (sensors, MiR)

Enhanced templates with:
- AGV fleet management and mobile robot traffic
- Conveyor and sortation system automation
- RFID tracking and barcode scanning workflows
- Cold chain temperature monitoring (refrigerated variant)
- 30-50 devices per template following Purdue model
"""

from typing import Any


DISTRIBUTION_LOGISTICS_TEMPLATES: dict[str, dict[str, Any]] = {
    # ============================================================
    # TEMPLATE 1: FULFILLMENT CENTER (45 devices)
    # E-commerce fulfillment with AGVs, conveyors, pick-to-light
    # ============================================================
    "fulfillment_center": {
        "name": "Fulfillment Center",
        "description": "E-commerce fulfillment center with four zones (pick / pack / ship / "
                       "sortation), a WMS + standby + MES at L3, and a full IDMZ. ControlLogix "
                       "WCS PLCs and conveyor PLCs throughout. 89 devices across 6 zones.",
        "vertical": "distribution_logistics",
        "phase_preset": "standard",
        "recommended_attack_playbooks": [
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "Warehouse operational disruption via conveyor/AGV manipulation"},
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "Large flat network with many EtherNet/IP endpoints"},
            {"playbook_id": "pipedream_like", "relevance": "medium", "rationale": "Rockwell ControlLogix conveyor PLCs targeted by PIPEDREAM"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "distribution_logistics",
            "description": "Fulfillment conveyor line with package throughput, zone fill level, AGV utilization, cold storage temperature",
            "key_variables": ["conveyor_speed", "throughput", "zone_fill_level", "agv_utilization", "cold_storage_temp"],
            "available_faults": ["conveyor_jam", "agv_fleet_failure", "cold_chain_breach"],
        },
        "devices": [
            # ============================================================
            # WMS CORE ZONE (Level 3) - 4 devices
            # Warehouse Management System servers and core infrastructure
            # ============================================================
            {"type": "scada_server", "vendor": "rockwell", "count": 1, "zone": "wms_core",
             "name": "WCS_Primary_Server", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "1756-L85E",
             "role": "Warehouse Control System"},
            {"type": "scada_server", "vendor": "rockwell", "count": 1, "zone": "wms_core",
             "name": "WCS_Backup_Server", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "1756-L85E",
             "role": "Warehouse Control System"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "wms_core",
             "name": "WMS_Core_Switch_1", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Core Network Switch"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "wms_core",
             "name": "WMS_Core_Switch_2", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Core Network Switch"},

            # ============================================================
            # FLEET MANAGEMENT ZONE (Level 2) - 3 devices
            # AGV fleet controllers and coordination
            # ============================================================
            {"type": "fleet_manager", "vendor": "kuka", "count": 1, "zone": "fleet_mgmt",
             "name": "KUKA_Fleet_Manager", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KUKA.FleetManager",
             "role": "AGV Fleet Controller",
             },
            {"type": "fleet_manager", "vendor": "mir", "count": 1, "zone": "fleet_mgmt",
             "name": "MiR_Fleet_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "MiR Fleet",
             "role": "AMR Fleet Controller"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "fleet_mgmt",
             "name": "Fleet_Network_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Industrial Switch"},

            # ============================================================
            # CONVEYOR ZONE (Level 2) - 10 devices
            # Conveyor PLCs, VFDs, and sortation controllers
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Conveyor_Main_PLC", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Conveyor Master Controller",
             },
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Inbound_Conveyor_PLC", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L83E",
             "role": "Conveyor Zone Controller"},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Outbound_Conveyor_PLC", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L83E",
             "role": "Conveyor Zone Controller"},
            {"type": "sortation_controller", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Sortation_Master_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "role": "Sortation Controller"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Main_Takeaway_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Merge_Line_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Accumulation_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Divert_Gate_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Variable Frequency Drive"},
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Conveyor_Safety_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L73S",
             "role": "Safety Controller"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "conveyor_zone",
             "name": "Conveyor_Zone_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Industrial Switch"},

            # ============================================================
            # AGV ZONE (Level 1) - 14 devices
            # Individual AGV/AMR units
            # ============================================================
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_01", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 1500",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_02", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 1500",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_03", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 1500",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_04", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 1500",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_05", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 600",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_06", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 600",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_07", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 600",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_08", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 600",
             "role": "Automated Guided Vehicle"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_01", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_02", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_03", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_04", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_05", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_06", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},

            # ============================================================
            # PICK ZONE (Level 1) - 14 devices
            # Pick-to-light, barcode scanners, vision systems
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_Master_PLC", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L33ER",
             "role": "Pick Station Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_1_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_2_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_3_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_4_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_5_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_6_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "pick_zone",
             "name": "Inbound_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Fixed Barcode Scanner"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "pick_zone",
             "name": "Inbound_Scanner_2", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Fixed Barcode Scanner"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "pick_zone",
             "name": "Outbound_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Fixed Barcode Scanner"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "pick_zone",
             "name": "Outbound_Scanner_2", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Fixed Barcode Scanner"},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "pick_zone",
             "name": "QC_Vision_Station_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Quality Control Vision",
             },
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "pick_zone",
             "name": "QC_Vision_Station_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Quality Control Vision"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "pick_zone",
             "name": "Pick_Zone_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Industrial Switch"},

            # ============================================================
            # DMZ ZONE - Remote Access and Jump Server
            # ============================================================
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "wms_core",
             "name": "Warehouse_Remote_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True,
             },
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "wms_core",
             "name": "WMS_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True,
             },
        ],
        "flows": [
            # ============================================================
            # FLEET MANAGEMENT FLOWS
            # ============================================================
            # KUKA Fleet Manager to KUKA AGVs - PROFINET cyclic (8ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source_types": ["fleet_manager"], "target_types": ["agv"],
             "source_zones": ["fleet_mgmt"], "target_zones": ["agv_zone"],
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # MiR Fleet Controller to MiR AMRs - Modbus mission commands (250ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["fleet_manager"], "target_types": ["amr"],
             "source_zones": ["fleet_mgmt"], "target_zones": ["agv_zone"],
             "jitter_ms": 30, "jitter_type": "gaussian"},

            # ============================================================
            # CONVEYOR ZONE FLOWS
            # ============================================================
            # Conveyor PLCs and Sortation to VFDs - cyclic I/O (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc", "sortation_controller"], "target_types": ["drive"],
             "source_zones": ["conveyor_zone"], "target_zones": ["conveyor_zone"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Inter-PLC communication - zone coordination (50ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source_types": ["plc"], "target_types": ["plc", "sortation_controller"],
             "source_zones": ["conveyor_zone"], "target_zones": ["conveyor_zone"],
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Safety PLC to conveyor PLCs and VFDs - safety interlock (20ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source_types": ["safety_plc"], "target_types": ["plc", "sortation_controller", "drive"],
             "source_zones": ["conveyor_zone"], "target_zones": ["conveyor_zone"],
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # ============================================================
            # PICK ZONE FLOWS
            # ============================================================
            # Pick Station PLC to I/O modules - pick-to-light (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["pick_zone"], "target_zones": ["pick_zone"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Pick PLC to barcode scanners (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["barcode_scanner"],
             "source_zones": ["pick_zone"], "target_zones": ["pick_zone"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # Vision systems to Pick PLC - QC results (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["vision_system"], "target_types": ["plc"],
             "source_zones": ["pick_zone"], "target_zones": ["pick_zone"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # ============================================================
            # WCS/SCADA FLOWS (Level 3 to Level 2)
            # ============================================================
            # Primary WCS to conveyor PLCs and sortation (200ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source_types": ["scada_server"], "target_types": ["plc", "sortation_controller"],
             "source_zones": ["wms_core"], "target_zones": ["conveyor_zone"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # Primary WCS to Pick Station PLC (200ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "source_zones": ["wms_core"], "target_zones": ["pick_zone"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # WCS to Fleet Managers - EtherNet/IP (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["scada_server"], "target_types": ["fleet_manager"],
             "source_zones": ["wms_core"], "target_zones": ["fleet_mgmt"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # WCS to Safety PLC status (1000ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["safety_plc"],
             "source_zones": ["wms_core"], "target_zones": ["conveyor_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # WCS to Vision Systems (1000ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["vision_system"],
             "source_zones": ["wms_core"], "target_zones": ["pick_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Backup WCS heartbeat to primary (5000ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["scada_server"], "target_types": ["scada_server"],
             "source_zones": ["wms_core"], "target_zones": ["wms_core"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP NETWORK MONITORING
            # ============================================================
            # WCS monitoring all switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["wms_core"], "target_zones": ["wms_core", "fleet_mgmt", "conveyor_zone", "pick_zone"]},

            # Jump server SNMP monitoring of core switches (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["switch"],
             "source_zones": ["wms_core"], "target_zones": ["wms_core"]},


            # eWON Modbus polling to conveyor PLCs (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["wms_core"], "target_zones": ["conveyor_zone"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

                    ],
        "zones": [
            {"id": "wms_core", "name": "WMS Core", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "fleet_mgmt", "name": "Fleet Management", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "conveyor_zone", "name": "Conveyor Network", "level": 2,
             "subnet_offset": 2, "vlan": 120, "security_level": "standard"},
            {"id": "agv_zone", "name": "AGV Network", "level": 1,
             "subnet_offset": 3, "vlan": 130, "security_level": "standard"},
            {"id": "pick_zone", "name": "Pick Stations", "level": 1,
             "subnet_offset": 4, "vlan": 140, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "cloud_services": [
            {
                "provider": "talk2m",
                "region": "us-west",
                "device_types": ["remote_gateway"],
                "heartbeat_interval_ms": 30000,
            },
            {
                "provider": "teamviewer",
                "region": "global",
                "device_types": ["jump_server"],
                "heartbeat_interval_ms": 30000,
            },
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "jitter_spike", "agv_position_lag"],
            "protocol": ["ethernet_ip_error", "modbus_exception"],
            "sequence": ["duplicate", "out_of_order", "scan_retry"],
            "payload": ["barcode_read_error", "vision_inspection_fail"],
            "network": ["wireless_dropout"],
            "security": ["unauthorized_agv_command"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_jump_server": True,
            "jump_server_external_ip": "203.0.113.50",
        },
        "conduits": [
            # L3 (wms_core) <-> L2 (fleet_mgmt): WCS to fleet management
            {"id": "wms_to_fleet", "name": "WMS Core \u2194 Fleet Management",
             "source_zone": "wms_core", "target_zone": "fleet_mgmt",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip"],
             "security_level": "high",
             "description": "WCS servers polling KUKA and MiR fleet managers for AGV coordination and status"},
            # L3 (wms_core) <-> L2 (conveyor_zone): WCS to conveyor automation
            {"id": "wms_to_conveyor", "name": "WMS Core \u2194 Conveyor Zone",
             "source_zone": "wms_core", "target_zone": "conveyor_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "modbus_tcp"],
             "security_level": "high",
             "description": "WCS servers polling conveyor PLCs, sortation controllers, safety PLC, and VFDs"},
            # L2 (fleet_mgmt) <-> L1 (agv_zone): Fleet managers to AGV units
            {"id": "fleet_to_agv", "name": "Fleet Management \u2194 AGV Zone",
             "source_zone": "fleet_mgmt", "target_zone": "agv_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["profinet", "ethernet_ip", "modbus_tcp"],
             "security_level": "standard",
             "description": "KUKA fleet manager PROFINET cyclic I/O to AGVs; MiR fleet Modbus mission commands to AMRs"},
            # L3 (wms_core) <-> L1 (pick_zone): WCS to pick stations
            {"id": "wms_to_pick", "name": "WMS Core \u2194 Pick Zone",
             "source_zone": "wms_core", "target_zone": "pick_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip"],
             "security_level": "standard",
             "description": "WCS servers polling pick station PLC and vision systems for order fulfillment status"},
            # L3 (wms_core) <-> L4 (external): Remote access and jump server
            {"id": "wms_to_external", "name": "WMS Core \u2194 External",
             "source_zone": "wms_core", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https", "rdp"],
             "security_level": "critical",
             "description": "EWON Talk2M cloud heartbeat and jump server RDP for remote warehouse management"},
        ],
        "total_duration_ms": 300000,
    },

    # ============================================================
    # TEMPLATE 2: DISTRIBUTION CENTER (40 devices)
    # Traditional DC with cross-docking, RFID tracking
    # ============================================================
    "distribution_center": {
        "name": "Distribution Center",
        "description": "Regional distribution center on Rockwell EtherNet/IP — same "
                       "architectural shape as a fulfillment center. Four area zones, MES + WMS, "
                       "full IDMZ. 89 devices across 6 zones.",
        "vertical": "distribution_logistics",
        "phase_preset": "standard",
        "recommended_attack_playbooks": [
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "Distribution center operational sabotage"},
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "Multi-zone warehouse network mapping"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "distribution_logistics",
            "description": "Fulfillment conveyor line with package throughput, zone fill level, AGV utilization, cold storage temperature",
            "key_variables": ["conveyor_speed", "throughput", "zone_fill_level", "agv_utilization", "cold_storage_temp"],
            "available_faults": ["conveyor_jam", "agv_fleet_failure", "cold_chain_breach"],
        },
        "devices": [
            # ============================================================
            # DC CORE ZONE (Level 3) - 4 devices
            # ============================================================
            {"type": "scada_server", "vendor": "siemens", "count": 1, "zone": "dc_core",
             "name": "DC_Operations_Server", "protocols": ["s7comm_plus", "ethernet_ip", "snmp"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "role": "Distribution Operations"},
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "dc_core",
             "name": "DC_Historian", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "Proficy Historian",
             "role": "Data Historian"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "dc_core",
             "name": "DC_Core_Switch_1", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Core Switch",
             },
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "dc_core",
             "name": "DC_Core_Switch_2", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Core Switch"},

            # ============================================================
            # RECEIVING ZONE (Level 2) - 10 devices
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "receiving",
             "name": "Receiving_Main_PLC", "protocols": ["profinet", "s7comm_plus", "modbus_tcp"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Receiving Controller",
             },
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "receiving",
             "name": "Dock_Door_1_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader",
             },
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "receiving",
             "name": "Dock_Door_2_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "receiving",
             "name": "Dock_Door_3_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "receiving",
             "name": "Dock_Door_4_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_gateway", "vendor": "zebra", "count": 1, "zone": "receiving",
             "name": "Receiving_RFID_Gateway_1", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "FX9600",
             "role": "RFID Aggregation Gateway",
             },
            {"type": "rfid_gateway", "vendor": "zebra", "count": 1, "zone": "receiving",
             "name": "Receiving_RFID_Gateway_2", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "FX9600",
             "role": "RFID Aggregation Gateway"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "receiving",
             "name": "Receiving_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Pallet Barcode Scanner"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "receiving",
             "name": "Receiving_IO_Module", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Dock I/O"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "receiving",
             "name": "Receiving_Switch", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Zone Switch"},

            # ============================================================
            # SHIPPING ZONE (Level 2) - 10 devices
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Shipping_Main_PLC", "protocols": ["profinet", "s7comm_plus", "modbus_tcp"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Shipping Controller",
             },
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "shipping",
             "name": "Ship_Door_1_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "shipping",
             "name": "Ship_Door_2_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_gateway", "vendor": "zebra", "count": 1, "zone": "shipping",
             "name": "Shipping_RFID_Gateway_1", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "FX9600",
             "role": "RFID Aggregation Gateway"},
            {"type": "rfid_gateway", "vendor": "zebra", "count": 1, "zone": "shipping",
             "name": "Shipping_RFID_Gateway_2", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "FX9600",
             "role": "RFID Aggregation Gateway"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "shipping",
             "name": "Shipping_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Pallet Barcode Scanner"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Shipping_IO_Module", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Dock I/O"},
            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Dock_Safety_Controller", "protocols": ["profinet", "profisafe", "s7comm_plus"],
             "fingerprint_model": "6ES7 516-3FN02-0AB0",
             "role": "Dock Safety Controller"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Safety_Light_Curtain_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Safety I/O"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Shipping_Switch", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Zone Switch"},

            # ============================================================
            # CONVEYOR BACKBONE (Level 1) - 16 devices
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Zone_1_PLC", "protocols": ["profinet", "s7comm_plus", "modbus_tcp"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Conveyor Zone Controller"},
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Zone_2_PLC", "protocols": ["profinet", "s7comm_plus", "modbus_tcp"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Conveyor Zone Controller"},
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Zone_3_PLC", "protocols": ["profinet", "s7comm_plus", "modbus_tcp"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Conveyor Zone Controller"},
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Controller_PLC", "protocols": ["profinet", "s7comm_plus", "modbus_tcp"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "role": "Cross-Dock Sortation"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_VFD_1", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Conveyor Drive",
             },
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_VFD_2", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Conveyor Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_VFD_3", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Conveyor Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_VFD_4", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Conveyor Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Divert_VFD_1", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Divert Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Divert_VFD_2", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Divert Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Divert_VFD_3", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Divert Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Divert_VFD_4", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Divert Drive"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Sensors_IO_1", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Conveyor Sensors"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Sensors_IO_2", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Conveyor Sensors"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Switch_1", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Zone Switch"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Switch_2", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Zone Switch"},

            # ============================================================
            # DMZ ZONE - Remote Access and Jump Server
            # ============================================================
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "dc_core",
             "name": "DC_Remote_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True,
             },
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "dc_core",
             "name": "DC_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True,
             },
        ],
        "flows": [
            # ============================================================
            # RECEIVING ZONE FLOWS (Siemens)
            # ============================================================
            # Receiving PLC to I/O modules - PROFINET cyclic (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["receiving"], "target_zones": ["receiving"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # Receiving PLC to RFID readers and gateways - Modbus TCP (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["rfid_reader", "rfid_gateway"],
             "source_zones": ["receiving"], "target_zones": ["receiving"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Receiving PLC to barcode scanner (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["barcode_scanner"],
             "source_zones": ["receiving"], "target_zones": ["receiving"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # SHIPPING ZONE FLOWS (Siemens)
            # ============================================================
            # Shipping PLC to I/O modules - PROFINET cyclic (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["shipping"], "target_zones": ["shipping"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # Shipping PLC to RFID readers and gateways - Modbus TCP (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["rfid_reader", "rfid_gateway"],
             "source_zones": ["shipping"], "target_zones": ["shipping"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Shipping PLC to barcode scanner (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["barcode_scanner"],
             "source_zones": ["shipping"], "target_zones": ["shipping"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # Safety PLC to Safety I/O - PROFIsafe (4ms)
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["io_module"],
             "source_zones": ["shipping"], "target_zones": ["shipping"],
             "jitter_ms": 0.3, "jitter_type": "gaussian"},

            # Safety PLC to zone PLCs - safety interlock (4ms)
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc"],
             "source_zones": ["shipping"], "target_zones": ["receiving", "shipping"],
             "jitter_ms": 0.3, "jitter_type": "gaussian"},

            # ============================================================
            # CONVEYOR BACKBONE FLOWS (Siemens)
            # ============================================================
            # Conveyor PLCs to VFDs - PROFINET cyclic (8ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["conveyor_backbone"], "target_zones": ["conveyor_backbone"],
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # Conveyor PLCs to I/O modules - PROFINET cyclic (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["conveyor_backbone"], "target_zones": ["conveyor_backbone"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # Inter-PLC communication - zone handoff (50ms)
            {"protocol": "profinet", "pattern": "poll", "interval_ms": 50,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["conveyor_backbone"], "target_zones": ["conveyor_backbone"],
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Receiving to Conveyor handoff (100ms)
            {"protocol": "profinet", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["receiving"], "target_zones": ["conveyor_backbone"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # Conveyor to Shipping handoff (100ms)
            {"protocol": "profinet", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["conveyor_backbone"], "target_zones": ["shipping"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # SCADA/OPERATIONS (S7comm+ - Siemens native)
            # ============================================================
            # Operations Server to all PLCs and safety PLC - S7comm+ (500ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source_types": ["scada_server"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["dc_core"], "target_zones": ["receiving", "shipping", "conveyor_backbone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # Historian data collection from Operations Server (30s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["historian"], "target_types": ["scada_server"],
             "source_zones": ["dc_core"], "target_zones": ["dc_core"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP NETWORK MONITORING
            # ============================================================
            # Operations Server to all switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["dc_core"], "target_zones": ["dc_core", "receiving", "shipping", "conveyor_backbone"]},

            # Operations Server SNMP to RFID readers and gateways (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["rfid_reader", "rfid_gateway"],
             "source_zones": ["dc_core"], "target_zones": ["receiving", "shipping"]},

            # Jump server SNMP monitoring of core switches (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["switch"],
             "source_zones": ["dc_core"], "target_zones": ["dc_core"]},


            # eWON Modbus polling to conveyor PLCs (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["dc_core"], "target_zones": ["conveyor_backbone"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

                    ],
        "zones": [
            {"id": "dc_core", "name": "DC Operations Core", "level": 3,
             "subnet_offset": 0, "vlan": 200, "security_level": "high"},
            {"id": "receiving", "name": "Receiving Area", "level": 2,
             "subnet_offset": 1, "vlan": 210, "security_level": "standard"},
            {"id": "shipping", "name": "Shipping Area", "level": 2,
             "subnet_offset": 2, "vlan": 220, "security_level": "standard"},
            {"id": "conveyor_backbone", "name": "Conveyor Backbone", "level": 1,
             "subnet_offset": 3, "vlan": 230, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "cloud_services": [
            {
                "provider": "talk2m",
                "region": "us-west",
                "device_types": ["remote_gateway"],
                "heartbeat_interval_ms": 30000,
            },
            {
                "provider": "teamviewer",
                "region": "global",
                "device_types": ["jump_server"],
                "heartbeat_interval_ms": 30000,
            },
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "rfid_read_timeout"],
            "protocol": ["profinet_alarm", "modbus_exception", "snmp_timeout"],
            "sequence": ["duplicate_rfid_read", "out_of_order"],
            "payload": ["rfid_read_error", "barcode_no_read"],
            "network": ["network_congestion"],
            "security": ["rfid_spoofing"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["54.95.198.117", "51.38.74.240"],
            "enable_jump_server": True,
            "jump_server_external_ip": "203.0.113.51",
        },
        "conduits": [
            # L3 (dc_core) <-> L2 (receiving): Operations to receiving area
            {"id": "dc_to_receiving", "name": "DC Core \u2194 Receiving",
             "source_zone": "dc_core", "target_zone": "receiving",
             "direction": "bidirectional",
             "allowed_protocols": ["s7comm_plus", "snmp"],
             "security_level": "high",
             "description": "Operations server S7comm+ polling receiving PLC; SNMP monitoring of RFID readers, gateways, and switches"},
            # L3 (dc_core) <-> L2 (shipping): Operations to shipping area
            {"id": "dc_to_shipping", "name": "DC Core \u2194 Shipping",
             "source_zone": "dc_core", "target_zone": "shipping",
             "direction": "bidirectional",
             "allowed_protocols": ["s7comm_plus", "snmp"],
             "security_level": "high",
             "description": "Operations server S7comm+ polling shipping PLC and safety controller; SNMP monitoring of RFID and switches"},
            # L2 (receiving) <-> L1 (conveyor_backbone): Receiving to conveyor handoff
            {"id": "receiving_to_conveyor", "name": "Receiving \u2194 Conveyor Backbone",
             "source_zone": "receiving", "target_zone": "conveyor_backbone",
             "direction": "bidirectional",
             "allowed_protocols": ["profinet"],
             "security_level": "standard",
             "description": "Receiving PLC PROFINET handoff to conveyor zone PLCs for inbound pallet routing"},
            # L2 (shipping) <-> L1 (conveyor_backbone): Shipping to conveyor handoff
            {"id": "shipping_to_conveyor", "name": "Shipping \u2194 Conveyor Backbone",
             "source_zone": "shipping", "target_zone": "conveyor_backbone",
             "direction": "bidirectional",
             "allowed_protocols": ["profinet"],
             "security_level": "standard",
             "description": "Conveyor backbone PROFINET handoff to shipping zone PLCs for outbound routing"},
            # L3 (dc_core) <-> L1 (conveyor_backbone): Operations to conveyor
            {"id": "dc_to_conveyor", "name": "DC Core \u2194 Conveyor Backbone",
             "source_zone": "dc_core", "target_zone": "conveyor_backbone",
             "direction": "bidirectional",
             "allowed_protocols": ["s7comm_plus", "modbus_tcp", "snmp"],
             "security_level": "high",
             "description": "Operations server S7comm+ polling conveyor PLCs; EWON Modbus polling; SNMP switch monitoring"},
            # L3 (dc_core) <-> L4 (external): Remote access and jump server
            {"id": "dc_to_external", "name": "DC Core \u2194 External",
             "source_zone": "dc_core", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https", "rdp"],
             "security_level": "critical",
             "description": "EWON Talk2M cloud heartbeat and jump server RDP for remote distribution management"},
        ],
        "total_duration_ms": 300000,
    },

    # ============================================================
    # TEMPLATE 3: COLD CHAIN WAREHOUSE (35 devices)
    # Temperature-controlled with monitoring and compliance
    # ============================================================
    "cold_chain_warehouse": {
        "name": "Cold Chain Warehouse",
        "description": "Cold-chain warehouse with three conveyor / sortation zones supervised by "
                       "a Rockwell-based WMS. EtherNet/IP from WCS PLCs to PowerFlex drives + "
                       "Point I/O. Full L3.5 IDMZ for ERP integration. 58 devices across 5 "
                       "zones.",
        "vertical": "distribution_logistics",
        "phase_preset": "standard",
        "recommended_attack_playbooks": [
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "Temperature manipulation causing cold chain compromise"},
            {"playbook_id": "network_recon", "relevance": "medium", "rationale": "Cold storage monitoring network discovery"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "distribution_logistics",
            "description": "Fulfillment conveyor line with package throughput, zone fill level, AGV utilization, cold storage temperature",
            "key_variables": ["conveyor_speed", "throughput", "zone_fill_level", "agv_utilization", "cold_storage_temp"],
            "available_faults": ["conveyor_jam", "agv_fleet_failure", "cold_chain_breach"],
        },
        "devices": [
            # ============================================================
            # HVAC CONTROL ZONE (Level 3) - 6 devices
            # ============================================================
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "hvac_control",
             "name": "Refrigeration_Master_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "BMEH586040",
             "role": "Refrigeration Master Controller",
             },
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "hvac_control",
             "name": "Refrigeration_Backup_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "BMEH586040",
             "role": "Refrigeration Backup Controller"},
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "hvac_control",
             "name": "Temperature_Compliance_Historian", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "Proficy Historian",
             "role": "Compliance Data Historian"},
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "hvac_control",
             "name": "HVAC_Control_Room_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIGTO5310",
             "role": "HVAC Operator Interface"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "hvac_control",
             "name": "HVAC_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "HVAC Network Switch"},
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "hvac_control",
             "name": "Cold_Chain_Remote_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Monitoring Gateway",
             "external_comms": True,
             },
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "hvac_control",
             "name": "Cold_Chain_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True,
             },

            # ============================================================
            # FROZEN ZONE (Level 2) - 8 devices
            # ============================================================
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Zone_Controller_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Freezer Controller"},
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Zone_Controller_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Freezer Controller"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Temp_Sensor_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Temp_Sensor_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Temp_Sensor_3", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Temp_Sensor_4", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "frozen_zone",
             "name": "Freezer_Compressor_VFD_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "role": "Compressor Drive",
             },
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "frozen_zone",
             "name": "Freezer_Compressor_VFD_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "role": "Compressor Drive"},

            # ============================================================
            # CHILLED ZONE (Level 2) - 8 devices
            # ============================================================
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Zone_Controller_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Cooler Controller"},
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Zone_Controller_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Cooler Controller"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Temp_Sensor_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Temp_Sensor_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Temp_Sensor_3", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Temp_Sensor_4", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "chilled_zone",
             "name": "Chiller_Compressor_VFD_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "role": "Compressor Drive"},
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "chilled_zone",
             "name": "Chiller_Compressor_VFD_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "role": "Compressor Drive"},

            # ============================================================
            # AMBIENT/CONVEYOR ZONE (Level 1) - 9 devices
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "ambient_zone",
             "name": "Cold_Conveyor_PLC", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "1769-L33ER",
             "role": "Conveyor Controller"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "ambient_zone",
             "name": "Cold_Conveyor_VFD_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Conveyor Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "ambient_zone",
             "name": "Cold_Conveyor_VFD_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Conveyor Drive"},
            {"type": "fleet_manager", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_Fleet_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "MiR Fleet",
             "role": "Cold-Rated AMR Fleet"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_AMR_1", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR500",
             "role": "Cold-Rated Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_AMR_2", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR500",
             "role": "Cold-Rated Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_AMR_3", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR500",
             "role": "Cold-Rated Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_AMR_4", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR500",
             "role": "Cold-Rated Mobile Robot"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "ambient_zone",
             "name": "Ambient_Zone_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Zone Switch"},

            # ============================================================
            # MONITORING ZONE (Level 1) - 4 devices
            # ============================================================
            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "monitoring",
             "name": "Door_Interlock_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM5CSLC100FS",
             "role": "Door Interlocks"},
            {"type": "safety_plc", "vendor": "schneider", "count": 1, "zone": "monitoring",
             "name": "Cold_Storage_Safety_PLC", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM5CSLC100FS",
             "role": "Safety Controller"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "monitoring",
             "name": "Monitoring_Switch_1", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Monitoring Switch"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "monitoring",
             "name": "Monitoring_Switch_2", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Monitoring Switch"},
        ],
        "flows": [
            # ============================================================
            # TEMPERATURE ZONE CONTROL (Honeywell)
            # Controllers to sensors - Modbus (5s) - frozen and chilled zones
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["temperature_controller"], "target_types": ["sensor"],
             "source_zones": ["frozen_zone"], "target_zones": ["frozen_zone"],
             "jitter_ms": 500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["temperature_controller"], "target_types": ["sensor"],
             "source_zones": ["chilled_zone"], "target_zones": ["chilled_zone"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Controllers to compressor VFDs - Modbus (100ms) - frozen and chilled zones
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["temperature_controller"], "target_types": ["drive"],
             "source_zones": ["frozen_zone"], "target_zones": ["frozen_zone"],
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["temperature_controller"], "target_types": ["drive"],
             "source_zones": ["chilled_zone"], "target_zones": ["chilled_zone"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # MASTER REFRIGERATION PLC (Schneider M580)
            # ============================================================
            # Master PLC to zone controllers - Modbus (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["temperature_controller"],
             "source_zones": ["hvac_control"], "target_zones": ["frozen_zone", "chilled_zone"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # HMI to Master PLC - operator interface (200ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["hvac_control"], "target_zones": ["hvac_control"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # Backup PLC heartbeat to Master (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["hvac_control"], "target_zones": ["hvac_control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # AMBIENT/CONVEYOR ZONE (Rockwell)
            # ============================================================
            # Conveyor PLC to VFDs - EtherNet/IP cyclic (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["ambient_zone"], "target_zones": ["ambient_zone"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # MiR Fleet to cold-rated AMRs - Modbus (250ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["fleet_manager"], "target_types": ["amr"],
             "source_zones": ["ambient_zone"], "target_zones": ["ambient_zone"],
             "jitter_ms": 30, "jitter_type": "gaussian"},

            # ============================================================
            # SAFETY & MONITORING
            # ============================================================
            # Safety PLC to door interlocks (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["safety_plc"], "target_types": ["io_module"],
             "source_zones": ["monitoring"], "target_zones": ["monitoring"],
             "jitter_ms": 10, "jitter_type": "gaussian"},

            # Safety PLC to refrigeration PLCs (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["safety_plc"], "target_types": ["plc"],
             "source_zones": ["monitoring"], "target_zones": ["hvac_control"],
             "jitter_ms": 10, "jitter_type": "gaussian"},

            # ============================================================
            # HISTORIAN - COMPLIANCE DATA (30s logging)
            # ============================================================
            # Historian to all temperature sensors (frozen + chilled)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["historian"], "target_types": ["sensor"],
             "source_zones": ["hvac_control"], "target_zones": ["frozen_zone", "chilled_zone"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # Historian to zone controllers (frozen + chilled)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["historian"], "target_types": ["temperature_controller"],
             "source_zones": ["hvac_control"], "target_zones": ["frozen_zone", "chilled_zone"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # Historian to master PLC - EtherNet/IP (30s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["hvac_control"], "target_zones": ["hvac_control"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # REMOTE GATEWAY - External monitoring
            # ============================================================
            # Gateway to Master PLC (60s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["hvac_control"], "target_zones": ["hvac_control"],
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP NETWORK MONITORING — moved to scada_server / NMS source.
            # PLCs do not poll switches in real industrial networks; the
            # NMS does. SCADA servers and jump_servers in this template
            # already cover network-management polling.
            # ============================================================

            # Jump server SNMP monitoring of switches (60s) — covers all
            # zones so no switch is orphaned for Cyber Vision discovery.
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["switch"],
             "source_zones": ["hvac_control"],
             "target_zones": ["hvac_control", "frozen_zone", "chilled_zone",
                              "ambient_zone", "monitoring"]},


                    ],
        "zones": [
            {"id": "hvac_control", "name": "HVAC/Refrigeration Control", "level": 3,
             "subnet_offset": 0, "vlan": 300, "security_level": "high"},
            {"id": "frozen_zone", "name": "Frozen Storage (-20C)", "level": 2,
             "subnet_offset": 1, "vlan": 310, "security_level": "standard"},
            {"id": "chilled_zone", "name": "Chilled Storage (2-8C)", "level": 2,
             "subnet_offset": 2, "vlan": 320, "security_level": "standard"},
            {"id": "ambient_zone", "name": "Ambient/Loading", "level": 1,
             "subnet_offset": 3, "vlan": 330, "security_level": "standard"},
            {"id": "monitoring", "name": "Temperature Monitoring", "level": 1,
             "subnet_offset": 4, "vlan": 340, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "cloud_services": [
            {
                "provider": "talk2m",
                "region": "eu",
                "device_types": ["remote_gateway"],
                "heartbeat_interval_ms": 30000,
            },
            {
                "provider": "teamviewer",
                "region": "global",
                "device_types": ["jump_server"],
                "heartbeat_interval_ms": 30000,
            },
        ],
        "suggested_anomalies": {
            "timing": ["temperature_reading_delay", "compliance_gap"],
            "protocol": ["modbus_exception", "sensor_timeout"],
            "sequence": ["temperature_spike", "door_interlock_fault"],
            "payload": ["out_of_range_temperature", "sensor_drift"],
            "network": ["network_latency"],
            "security": ["unauthorized_setpoint_change"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["51.38.74.240", "87.98.169.126"],
            "enable_jump_server": True,
            "jump_server_external_ip": "203.0.113.52",
        },
        "conduits": [
            # L3 (hvac_control) <-> L2 (frozen_zone): Refrigeration to frozen storage
            {"id": "hvac_to_frozen", "name": "HVAC Control \u2194 Frozen Zone",
             "source_zone": "hvac_control", "target_zone": "frozen_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Refrigeration master PLC and historian polling frozen zone controllers, sensors, and compressor VFDs"},
            # L3 (hvac_control) <-> L2 (chilled_zone): Refrigeration to chilled storage
            {"id": "hvac_to_chilled", "name": "HVAC Control \u2194 Chilled Zone",
             "source_zone": "hvac_control", "target_zone": "chilled_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Refrigeration master PLC and historian polling chilled zone controllers, sensors, and compressor VFDs"},
            # L3 (hvac_control) <-> L1 (ambient_zone): Control to ambient/loading
            {"id": "hvac_to_ambient", "name": "HVAC Control \u2194 Ambient Zone",
             "source_zone": "hvac_control", "target_zone": "ambient_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Master PLC SNMP monitoring of ambient zone network switch"},
            # L3 (hvac_control) <-> L1 (monitoring): Control to temperature monitoring
            {"id": "hvac_to_monitoring", "name": "HVAC Control \u2194 Monitoring",
             "source_zone": "hvac_control", "target_zone": "monitoring",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Master PLC SNMP monitoring of monitoring zone switches"},
            # L1 (monitoring) <-> L3 (hvac_control): Safety to refrigeration
            {"id": "monitoring_to_hvac", "name": "Monitoring \u2194 HVAC Control",
             "source_zone": "monitoring", "target_zone": "hvac_control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Safety PLC Modbus polling refrigeration master PLCs for interlock and door interlock I/O"},
            # L3 (hvac_control) <-> L4 (external): Remote access and jump server
            {"id": "hvac_to_external", "name": "HVAC Control \u2194 External",
             "source_zone": "hvac_control", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https", "rdp"],
             "security_level": "critical",
             "description": "EWON Talk2M cloud heartbeat and jump server RDP for remote cold chain monitoring"},
        ],
        "total_duration_ms": 300000,
    },

    # ============================================================
    # TEMPLATE 4: PARCEL SORTING HUB (50 devices)
    # High-speed sortation with scanning tunnels
    # ============================================================
    "parcel_sorting_hub": {
        "name": "Parcel Sorting Hub",
        "description": "Parcel sortation hub with three multi-vendor sortation zones (Siemens / "
                       "Rockwell / Schneider) under a unified WMS. Cross-vendor cell layout with "
                       "vendor-consistent intra-cell PROFINET / EtherNet/IP / Modbus traffic. 58 "
                       "devices across 5 zones.",
        "vertical": "distribution_logistics",
        "phase_preset": "standard",
        "recommended_attack_playbooks": [
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "Sorting system disruption and package misdirection"},
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "High-speed sorting network with many barcode/RFID endpoints"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "distribution_logistics",
            "description": "Fulfillment conveyor line with package throughput, zone fill level, AGV utilization, cold storage temperature",
            "key_variables": ["conveyor_speed", "throughput", "zone_fill_level", "agv_utilization", "cold_storage_temp"],
            "available_faults": ["conveyor_jam", "agv_fleet_failure", "cold_chain_breach"],
        },
        "devices": [
            # ============================================================
            # SORT CONTROL ZONE (Level 3) - 5 devices
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "sort_control",
             "name": "Sort_Master_PLC_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Sortation Master Controller",
             },
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "sort_control",
             "name": "Sort_Master_PLC_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Sortation Master Controller",
             },
            {"type": "scada_server", "vendor": "rockwell", "count": 1, "zone": "sort_control",
             "name": "Sort_SCADA_Server", "protocols": ["ethernet_ip", "snmp", "modbus_tcp"],
             "fingerprint_model": "1756-L85E",
             "role": "Sortation SCADA"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "sort_control",
             "name": "Sort_Control_Switch_1", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Control Room Switch"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "sort_control",
             "name": "Sort_Control_Switch_2", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Control Room Switch"},

            # ============================================================
            # INDUCTION ZONE (Level 2) - 8 devices
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "induct_zone",
             "name": "Induction_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L83E",
             "role": "Induction Controller"},
            {"type": "barcode_scanner", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Induct_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "DataMan 370",
             "role": "Induction Barcode Reader",
             },
            {"type": "barcode_scanner", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Induct_Scanner_2", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "DataMan 370",
             "role": "Induction Barcode Reader"},
            {"type": "barcode_scanner", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Induct_Scanner_3", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "DataMan 370",
             "role": "Induction Barcode Reader"},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Dimension_Camera_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Dimensioning Camera"},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Dimension_Camera_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Dimensioning Camera"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "induct_zone",
             "name": "Induct_Singulator_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Singulator I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "induct_zone",
             "name": "Induct_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Induction Switch"},

            # ============================================================
            # SORT LOOP ZONE (Level 2) - 12 devices
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Tray_Master_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "role": "Tilt-Tray Master"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Sorter_Drive_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 755",
             "role": "Sorter Main Drive",
             },
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Sorter_Drive_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 755",
             "role": "Sorter Main Drive"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_3", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_4", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_5", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_6", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_7", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_8", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "sort_loop",
             "name": "Sort_Loop_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Sort Loop Switch"},

            # ============================================================
            # SCAN TUNNEL ZONE (Level 1) - 10 devices
            # ============================================================
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Top", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Top"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Bottom", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Bottom"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Left", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Left"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Right", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Right"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Front", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Front"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Back", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Back"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "scan_tunnel",
             "name": "Weigh_In_Motion_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Weigh-In-Motion Scale"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "scan_tunnel",
             "name": "Weigh_In_Motion_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Weigh-In-Motion Scale"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "scan_tunnel",
             "name": "Label_Applicator_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Print-and-Apply"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "scan_tunnel",
             "name": "Label_Applicator_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Print-and-Apply"},

            # ============================================================
            # CHUTE ZONE (Level 1) - 15 devices
            # ============================================================
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Safety_PLC_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L73S",
             "role": "Chute Safety Controller"},
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Safety_PLC_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L73S",
             "role": "Chute Safety Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Full_Sensor_Bank_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Chute Full Sensors"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Full_Sensor_Bank_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Chute Full Sensors"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Full_Sensor_Bank_3", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Chute Full Sensors"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Full_Sensor_Bank_4", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Chute Full Sensors"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_3", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_4", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_5", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_6", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_7", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_8", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "chute_zone",
             "name": "Chute_Zone_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Chute Zone Switch"},

            # ============================================================
            # DMZ ZONE - Remote Access and Jump Server
            # ============================================================
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "sort_control",
             "name": "Sorting_Remote_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True,
             },
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "sort_control",
             "name": "Sorting_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True,
             },
        ],
        "flows": [
            # ============================================================
            # SORT LOOP - HIGH SPEED FLOWS (2-4ms critical)
            # ============================================================
            # Tilt-Tray PLC to tilt controllers - EtherNet/IP cyclic I/O (2ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["sort_loop"], "target_zones": ["sort_loop"],
             "jitter_ms": 0.3, "jitter_type": "gaussian"},

            # Tilt-Tray PLC to sorter drives - cyclic (4ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["sort_loop"], "target_zones": ["sort_loop"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # ============================================================
            # SORT CONTROL - MASTER PLCs
            # ============================================================
            # Master PLCs coordination (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["sort_control"], "target_zones": ["sort_control"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Sort Master to Tilt-Tray PLC (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["sort_control"], "target_zones": ["sort_loop"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Sort Master to Induction PLC (20ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["sort_control"], "target_zones": ["induct_zone"],
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # ============================================================
            # INDUCTION ZONE - SCANNERS & VISION
            # ============================================================
            # Induction PLC to singulator I/O (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["induct_zone"], "target_zones": ["induct_zone"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Induction barcode scanners to PLC - Cognex (50ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source_types": ["barcode_scanner"], "target_types": ["plc"],
             "source_zones": ["induct_zone"], "target_zones": ["induct_zone"],
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Dimension cameras to PLC (100ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 100,
             "source_types": ["vision_system"], "target_types": ["plc"],
             "source_zones": ["induct_zone"], "target_zones": ["induct_zone"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # SCAN TUNNEL - 6-SIDED SCANNING (SICK)
            # ============================================================
            # Scan tunnel scanners to Sort Master - fast scan results (50ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source_types": ["barcode_scanner"], "target_types": ["plc"],
             "source_zones": ["scan_tunnel"], "target_zones": ["sort_control"],
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Sort Master to weigh stations (50ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["sort_control"], "target_zones": ["scan_tunnel"],
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Sort Master to label applicators (100ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["sort_control"], "target_zones": ["scan_tunnel"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # CHUTE ZONE - SENSORS & SAFETY
            # ============================================================
            # Sort Master to chute full sensors (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["sort_control"], "target_zones": ["chute_zone"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Safety PLCs to light curtains - CIP Safety (4ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["io_module"],
             "source_zones": ["chute_zone"], "target_zones": ["chute_zone"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # Safety PLCs to Sort Masters - E-stop interlock (20ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source_types": ["safety_plc"], "target_types": ["plc"],
             "source_zones": ["chute_zone"], "target_zones": ["sort_control"],
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # Safety PLCs to Tilt-Tray PLC - E-stop interlock (20ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source_types": ["safety_plc"], "target_types": ["plc"],
             "source_zones": ["chute_zone"], "target_zones": ["sort_loop"],
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # ============================================================
            # SCADA MONITORING
            # ============================================================
            # SCADA to all PLCs (200ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source_types": ["scada_server"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["sort_control"],
             "target_zones": ["sort_control", "induct_zone", "sort_loop", "chute_zone"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # SCADA to vision systems status (1s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["vision_system"],
             "source_zones": ["sort_control"], "target_zones": ["induct_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP NETWORK MONITORING
            # ============================================================
            # SCADA monitoring all switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["sort_control"],
             "target_zones": ["sort_control", "induct_zone", "sort_loop", "chute_zone"]},

            # Jump server SNMP monitoring of switches (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["switch"],
             "source_zones": ["sort_control"], "target_zones": ["sort_control"]},


            # eWON Modbus polling to SCADA (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["scada_server"],
             "source_zones": ["sort_control"], "target_zones": ["sort_control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

                    ],
        "zones": [
            {"id": "sort_control", "name": "Sort Control Room", "level": 3,
             "subnet_offset": 0, "vlan": 400, "security_level": "high"},
            {"id": "induct_zone", "name": "Induction Zone", "level": 2,
             "subnet_offset": 1, "vlan": 410, "security_level": "standard"},
            {"id": "sort_loop", "name": "Main Sort Loop", "level": 2,
             "subnet_offset": 2, "vlan": 420, "security_level": "standard"},
            {"id": "scan_tunnel", "name": "Scanning Tunnel", "level": 1,
             "subnet_offset": 3, "vlan": 430, "security_level": "standard"},
            {"id": "chute_zone", "name": "Destination Chutes", "level": 1,
             "subnet_offset": 4, "vlan": 440, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "cloud_services": [
            {
                "provider": "talk2m",
                "region": "eu",
                "device_types": ["remote_gateway"],
                "heartbeat_interval_ms": 30000,
            },
            {
                "provider": "teamviewer",
                "region": "global",
                "device_types": ["jump_server"],
                "heartbeat_interval_ms": 30000,
            },
        ],
        "suggested_anomalies": {
            "timing": ["high_speed_desync", "scanner_lag", "safety_response_delay"],
            "protocol": ["ethernet_ip_error", "cip_safety_fault"],
            "sequence": ["tilt_misfire", "double_induction"],
            "payload": ["no_read", "dimension_error", "weight_variance"],
            "network": ["scanner_network_congestion"],
            "security": ["unauthorized_sort_divert"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["87.98.169.126", "13.56.142.1"],
            "enable_jump_server": True,
            "jump_server_external_ip": "203.0.113.53",
        },
        "conduits": [
            # L3 (sort_control) <-> L2 (induct_zone): Sort control to induction
            {"id": "sort_to_induct", "name": "Sort Control \u2194 Induction Zone",
             "source_zone": "sort_control", "target_zone": "induct_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "snmp"],
             "security_level": "high",
             "description": "Sort master PLCs cyclic I/O to induction PLC; SCADA polling vision systems; SNMP switch monitoring"},
            # L3 (sort_control) <-> L2 (sort_loop): Sort control to sort loop
            {"id": "sort_to_loop", "name": "Sort Control \u2194 Sort Loop",
             "source_zone": "sort_control", "target_zone": "sort_loop",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "snmp"],
             "security_level": "high",
             "description": "Sort master PLCs cyclic I/O to tilt-tray PLC and sorter drives; SNMP switch monitoring"},
            # L3 (sort_control) <-> L1 (scan_tunnel): Sort control to scan tunnel
            {"id": "sort_to_scan", "name": "Sort Control \u2194 Scan Tunnel",
             "source_zone": "sort_control", "target_zone": "scan_tunnel",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip"],
             "security_level": "standard",
             "description": "Sort master PLCs polling 6-sided barcode scanners, weigh stations, and label applicators"},
            # L3 (sort_control) <-> L1 (chute_zone): Sort control to chutes
            {"id": "sort_to_chutes", "name": "Sort Control \u2194 Chute Zone",
             "source_zone": "sort_control", "target_zone": "chute_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "snmp"],
             "security_level": "standard",
             "description": "Sort master PLCs polling chute full sensors; safety PLCs E-stop interlock to sort masters"},
            # L1 (chute_zone) <-> L2 (sort_loop): Safety interlock
            {"id": "chutes_to_loop", "name": "Chute Zone \u2194 Sort Loop",
             "source_zone": "chute_zone", "target_zone": "sort_loop",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip"],
             "security_level": "high",
             "description": "Chute safety PLCs E-stop interlock to tilt-tray PLC for emergency stop propagation"},
            # L3 (sort_control) <-> L4 (external): Remote access and jump server
            {"id": "sort_to_external", "name": "Sort Control \u2194 External",
             "source_zone": "sort_control", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https", "rdp"],
             "security_level": "critical",
             "description": "EWON Talk2M cloud heartbeat and jump server RDP for remote sorting hub management"},
        ],
        "total_duration_ms": 300000,
    },
}
