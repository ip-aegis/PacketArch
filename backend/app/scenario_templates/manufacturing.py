# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Manufacturing industry scenario templates.

Primary Vendors: Siemens, Rockwell Automation, Schneider, ABB
Protocol Focus: PROFINET (Siemens), EtherNet/IP (Rockwell), Modbus TCP (Schneider/ABB)

Enhanced templates with:
- CVE vulnerable firmware on all appropriate devices
- 25-30+ devices minimum per template (one with 100+ devices)
- Realistic traffic flows based on Purdue model timing
- Proper fingerprinting with protocol identities
- Unique, meaningful device names (not generic patterns)
"""

from typing import Any


MANUFACTURING_TEMPLATES: dict[str, dict[str, Any]] = {
    # ============================================================
    # TEMPLATE 1: SIEMENS DISCRETE MANUFACTURING (35 devices)
    # CNC machining and assembly cell with S7-1500 PLCs
    # ============================================================
    "siemens_discrete_manufacturing": {
        "name": "Siemens Discrete Manufacturing",
        "description": "Mid-sized Siemens-only discrete manufacturing plant. Three production "
                       "cells with S7-1500 PLCs running PROFINET cyclic IO to drives and "
                       "distributed I/O, supervised by a WinCC SCADA stack at L3 with TIA Portal "
                       "engineering workstations. Standard L3.5 IDMZ stack (jump server, "
                       "remote-access gateway, AV / patch staging). 45 devices across 5 zones.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high", "rationale": "PIPEDREAM toolkit targets Siemens S7/PROFINET environments"},
            {"playbook_id": "triton_like", "relevance": "medium", "rationale": "PROFIsafe safety controllers present TRITON-relevant target"},
            {"playbook_id": "havex_like", "relevance": "medium", "rationale": "Manufacturing IP theft via OPC/remote access vectors"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "manufacturing",
            "description": "CNC machining cell with spindle speed, feed rate, coolant temperature, vibration, and tool wear simulation",
            "key_variables": ["spindle_speed", "feed_rate", "coolant_temp", "vibration", "tool_wear"],
            "available_faults": ["tool_breakage", "coolant_failure", "drive_overload"],
        },
        "devices": [
            # ============================================================
            # CONTROL ZONE (Level 2) - 11 devices
            # Main controllers, safety, HMI, and infrastructure
            # ============================================================
            # Main PLCs - S7-1517-3 PN/DP (high performance)
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "CNC_Machining_Main_PLC", "protocols": ["profinet", "s7comm_plus", "snmp"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Line Controller",
             },
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Assembly_Line_Main_PLC", "protocols": ["profinet", "s7comm_plus", "snmp"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Line Controller",
             },

            # Auxiliary PLCs - S7-1511-1 PN
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Material_Handling_PLC", "protocols": ["profinet", "s7comm_plus", "snmp"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             },
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Quality_Inspection_PLC", "protocols": ["profinet", "s7comm_plus", "snmp"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             },

            # Safety PLC - S7-1516F-3 PN/DP with PROFIsafe
            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Machine_Safety_Controller", "protocols": ["profinet", "profisafe", "s7comm_plus"],
             "fingerprint_model": "6ES7 516-3FN01-0AB0",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },

            # HMI Panels - TP1200 Comfort
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "CNC_Cell_Operator_HMI", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "firmware_version": "V17.0.0.0",
             "role": "Operator Interface"},
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Assembly_Station_HMI", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "role": "Operator Interface"},
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Packaging_Area_HMI", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "role": "Operator Interface"},

            # Industrial Switches - Cisco IE-3500
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "control",
             "name": "Control_Room_Switch", "protocols": ["profinet", "snmp"],
             "fingerprint_id": "cisco/ie3500/8t3s",
             "role": "Industrial Switch"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "control",
             "name": "Cell_Network_Switch", "protocols": ["profinet", "snmp"],
             "fingerprint_id": "cisco/ie3500/8t3s",
             "role": "Industrial Switch"},

            # EWON Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "control",
             "name": "Plant_Remote_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # CELL ZONE (Level 1) - 22 devices
            # VFDs, servo drives, and I/O modules
            # ============================================================
            # VFD Drives - SINAMICS G120C (PE21 frame)
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Spindle_Motor_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Coolant_Pump_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Main_Conveyor_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Infeed_Conveyor_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Outfeed_Conveyor_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Hydraulic_Pump_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Exhaust_Fan_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Coolant_Fan_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},

            # Servo Drives - SINAMICS S120 for motion control
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "X_Axis_Servo_Drive", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Y_Axis_Servo_Drive", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Z_Axis_Servo_Drive", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Tool_Changer_Servo", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Rotary_Table_Servo", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Gripper_Actuator_Servo", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},

            # Distributed I/O - ET 200SP IM155-6 PN
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "CNC_Cell_1_IO_Module", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "CNC_Cell_2_IO_Module", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Assembly_Station_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Packaging_Zone_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Safety_Light_Curtain_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Conveyor_Sensors_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Robot_Interface_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell",
             "name": "Quality_Station_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},

            # ============================================================
            # FIELD ZONE (Level 0) - 3 devices
            # Remote field I/O
            # ============================================================
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "field",
             "name": "Raw_Material_Storage_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Field I/O"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "field",
             "name": "Finished_Goods_Area_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Field I/O"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "field",
             "name": "Shipping_Dock_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Field I/O"},
        ],
        "flows": [
            # PROFINET cyclic IO - Main PLC to Servo Drives (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["servo"],
             "source_zones": ["control"], "target_zones": ["cell"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # PROFINET cyclic IO - Main PLC to VFDs (8ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["control"], "target_zones": ["cell"],
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # PROFINET cyclic IO - Main PLC to I/O Modules (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["control"], "target_zones": ["cell"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # PROFIsafe safety communication (4ms)
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "drive", "io_module"],
             "source_zones": ["control"], "target_zones": ["control", "cell"]},

            # HMI polling via S7comm+ (500ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # Aux PLC to Main PLC coordination (32ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 32,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 4, "jitter_type": "gaussian"},

            # Main PLC to Field I/O (16ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 16,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["control"], "target_zones": ["field"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # EWON Modbus polling to drives (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["drive", "servo"],
             "source_zones": ["control"], "target_zones": ["cell"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Network management — remote gateway acts as NMS proxy and
            # SNMP-polls every switch in the plant for Cyber Vision
            # discovery (covers control room and cell-network switches).
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["remote_gateway"], "target_types": ["switch"],
             "source_zones": ["control"], "target_zones": ["control", "cell"]},
        ],
        "zones": [
            {"id": "control", "name": "Control Network", "level": 2,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "cell", "name": "Cell Network", "level": 1,
             "subnet_offset": 1, "vlan": 110, "security_level": "standard"},
            {"id": "field", "name": "Field Network", "level": 0,
             "subnet_offset": 2, "vlan": 120, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "conduits": [
            {"id": "ctrl_cell", "name": "Control \u2194 Cell",
             "source_zone": "control", "target_zone": "cell",
             "direction": "bidirectional",
             "allowed_protocols": ["profinet", "profisafe", "s7comm_plus", "modbus_tcp"],
             "security_level": "high",
             "description": "PLCs communicate with drives, servos, and I/O modules via PROFINET cyclic I/O; EWON gateway polls drives via Modbus TCP"},
            {"id": "ctrl_field", "name": "Control \u2194 Field",
             "source_zone": "control", "target_zone": "field",
             "direction": "bidirectional",
             "allowed_protocols": ["profinet"],
             "security_level": "high",
             "description": "Main PLCs poll remote field I/O modules via PROFINET cyclic I/O"},
            {"id": "ctrl_external", "name": "Control \u2194 External",
             "source_zone": "control", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https"],
             "security_level": "critical",
             "description": "EWON remote access gateway heartbeat to Talk2M cloud service"},
        ],
        "cloud_services": [
            {
                "provider": "talk2m",
                "region": "us-west",
                "device_types": ["remote_gateway"],
                "heartbeat_interval_ms": 30000,
            },
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "jitter_spike", "watchdog_timeout"],
            "protocol": ["profinet_alarm", "s7comm_error", "profisafe_error"],
            "sequence": ["duplicate", "out_of_order"],
            "payload": ["value_spike", "encoder_fault"],
            "network": [],
            "security": ["unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "c2_protocol": "http",
            "c2_pattern": "jittered_30s",
            "enable_exfil": True,
            "enable_exploits": True,
            "exploit_patterns": ["s7_stop_cpu", "s7_unauthorized_read"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "plc"],
        },
        "total_duration_ms": 300000,
    },

    # ============================================================
    # TEMPLATE 2: ROCKWELL AUTOMOTIVE ASSEMBLY (41 devices)
    # Body shop welding cells with ControlLogix PLCs
    # ============================================================
    "rockwell_automotive_assembly": {
        "name": "Rockwell Automotive Assembly",
        "description": "Mid-sized Rockwell-only automotive assembly plant. Three production "
                       "cells with ControlLogix 5580 PLCs and PowerFlex drives over EtherNet/IP, "
                       "supervised by a Studio 5000 / FactoryTalk View SE stack at L3. Standard "
                       "L3.5 IDMZ stack. 45 devices across 5 zones.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high", "rationale": "PIPEDREAM natively targets Rockwell ControlLogix via CIP"},
            {"playbook_id": "insider_threat", "relevance": "medium", "rationale": "Automotive IP and production sabotage risk"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "manufacturing",
            "description": "CNC machining simulation applied to automotive body shop welding and assembly",
            "key_variables": ["spindle_speed", "feed_rate", "coolant_temp", "vibration", "tool_wear"],
            "available_faults": ["tool_breakage", "coolant_failure", "drive_overload"],
        },
        "devices": [
            # ============================================================
            # CONTROL ZONE (Level 2) - 16 devices
            # ============================================================
            # Line PLCs - ControlLogix L85E
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Body_Shop_Line_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Line Controller",
             },
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Paint_Shop_Line_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Line Controller",
             },

            # Cell PLCs - ControlLogix L84E
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Weld_Cell_1_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L84E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             },
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Weld_Cell_2_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L84E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             },
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Material_Transfer_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L84E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             },
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Quality_Inspection_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L84E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             },

            # Safety PLCs - GuardLogix L83ES
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Weld_Cell_Safety_PLC", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Paint_Booth_Safety_PLC", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },

            # HMI Panels - PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Body_Shop_Main_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Weld_Cell_1_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Weld_Cell_2_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Paint_Shop_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},

            # Industrial Switches - Cisco IE-9320
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "control",
             "name": "Body_Shop_Core_Switch", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "IE-9320-24P4X-E",
             "firmware_version": "17.9.3",
             "role": "Industrial Switch"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "control",
             "name": "Weld_Cell_Network_Switch", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_id": "cisco/ie9320/24p4x",
             "role": "Industrial Switch"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "control",
             "name": "Paint_Shop_Switch", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_id": "cisco/ie9320/24p4x",
             "role": "Industrial Switch"},

            # EWON Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "control",
             "name": "Body_Shop_Remote_Gateway", "protocols": ["modbus_tcp", "snmp", "ethernet_ip"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # CELL ZONE (Level 1) - 25 devices
            # ============================================================
            # Servo Drives - Kinetix 5500
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Robot_1_X_Axis_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Robot_1_Y_Axis_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Robot_1_Z_Axis_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Robot_2_X_Axis_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Robot_2_Y_Axis_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Robot_2_Z_Axis_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Positioner_Turntable_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Weld_Gun_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},

            # VFD Drives - PowerFlex 525
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Transfer_Conveyor_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "firmware_version": "V5.001",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Infeed_Conveyor_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Outfeed_Conveyor_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Lift_Table_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Ventilation_Fan_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Cooling_Pump_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},

            # High-Power VFD Drives - PowerFlex 753
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Main_Air_Handler_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "20F-D052N103",
             "role": "High-Power Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Paint_Booth_Exhaust_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "20F-D052N103",
             "role": "High-Power Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Chiller_Compressor_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "20F-D052N103",
             "role": "High-Power Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Process_Water_Pump_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "20F-D052N103",
             "role": "High-Power Drive"},

            # Remote I/O - FLEX 5000
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Weld_Cell_1_Remote_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Weld_Cell_2_Remote_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Transfer_Station_Remote_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Paint_Prep_Remote_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},

            # Point I/O - 1734-AENT
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Safety_Gate_Point_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Point I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "E_Stop_Panel_Point_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Point I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell",
             "name": "Light_Curtain_Point_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Point I/O"},
        ],
        "flows": [
            # EtherNet/IP implicit - Line PLC to Servo Drives (2ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source_types": ["plc"], "target_types": ["servo"],
             "source_zones": ["control"], "target_zones": ["cell"],
             "jitter_ms": 0.2, "jitter_type": "gaussian"},

            # EtherNet/IP implicit - Line PLC to Cell PLCs (10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # EtherNet/IP implicit - Cell PLC to VFDs (10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["control"], "target_zones": ["cell"],
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # CIP Safety communication (4ms Safety RPI)
            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "drive", "io_module"],
             "source_zones": ["control"], "target_zones": ["control", "cell"]},

            # HMI polling via EtherNet/IP explicit (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # Cell PLC to Remote I/O (10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["control"], "target_zones": ["cell"],
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # Cell PLC to Point I/O (20ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["control"], "target_zones": ["cell"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # EWON EtherNet/IP polling to PLCs (10s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # Network management \u2014 remote gateway acts as NMS proxy and
            # SNMP-polls every switch in the plant for Cyber Vision
            # discovery (covers body-shop core, weld and paint cells).
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["remote_gateway"], "target_types": ["switch"],
             "source_zones": ["control"], "target_zones": ["control", "cell"]},
        ],
        "zones": [
            {"id": "control", "name": "Control Network", "level": 2,
             "subnet_offset": 0, "vlan": 200, "security_level": "high"},
            {"id": "cell", "name": "Cell Network", "level": 1,
             "subnet_offset": 1, "vlan": 210, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "conduits": [
            {"id": "ctrl_cell", "name": "Control \u2194 Cell",
             "source_zone": "control", "target_zone": "cell",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "cip_safety"],
             "security_level": "high",
             "description": "PLCs communicate with servo drives, VFDs, and remote I/O via EtherNet/IP implicit messaging; CIP Safety for safety PLCs"},
            {"id": "ctrl_external", "name": "Control \u2194 External",
             "source_zone": "control", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https"],
             "security_level": "critical",
             "description": "EWON remote access gateway heartbeat to Talk2M cloud service"},
        ],
        "cloud_services": [
            {
                "provider": "talk2m",
                "region": "us-east",
                "device_types": ["remote_gateway"],
                "heartbeat_interval_ms": 30000,
            },
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "connection_timeout", "rpi_violation"],
            "protocol": ["cip_error", "cip_safety_fault", "list_identity_timeout"],
            "sequence": ["dropped_packet", "out_of_order"],
            "payload": ["encoder_fault"],
            "network": ["jitter_spike"],
            "security": ["unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["54.95.198.117", "51.38.74.240"],
            "enable_c2": True,
            "c2_protocol": "https",
            "c2_pattern": "jittered_1m",
            "enable_exfil": True,
            "exfil_protocol": "http",
            "enable_exploits": True,
            "exploit_patterns": ["cip_stop_plc", "cip_unauthorized_write"],
            "enable_recon": True,
            "target_device_types": ["hmi", "plc"],
        },
        "total_duration_ms": 600000,
    },

    # ============================================================
    # TEMPLATE 3: MULTI-VENDOR ENTERPRISE MANUFACTURING (119 devices)
    # Large multi-zone facility with Siemens, Rockwell, Schneider, ABB
    # ============================================================
    "multi_vendor_enterprise_manufacturing": {
        "name": "Multi-Vendor Enterprise Manufacturing",
        "description": "Enterprise multi-vendor manufacturing facility. Four cells, each pinned "
                       "to a different dominant vendor (Siemens / Rockwell / Schneider / ABB) "
                       "for vendor-consistent intra-cell traffic; cross-vendor supervision via "
                       "OPC UA. Full IDMZ + Operations stack including standby SCADA, asset "
                       "management, MES, and OPC UA aggregator. 81 devices across 6 zones.",
        "vertical": "manufacturing",
        "phase_preset": "full_lifecycle",
        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high", "rationale": "Multi-vendor environment exercises PIPEDREAM cross-protocol capabilities"},
            {"playbook_id": "havex_like", "relevance": "high", "rationale": "Enterprise manufacturing with OPC UA is prime HAVEX target"},
            {"playbook_id": "insider_threat", "relevance": "medium", "rationale": "Large multi-vendor plant with many access points"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "manufacturing",
            "description": "CNC machining simulation for multi-vendor enterprise plant",
            "key_variables": ["spindle_speed", "feed_rate", "coolant_temp", "vibration", "tool_wear"],
            "available_faults": ["tool_breakage", "coolant_failure", "drive_overload"],
        },
        "devices": [
            # ============================================================
            # INDUSTRIAL DMZ (Level 3.5) - 11 devices
            # ============================================================
            {"type": "scada_server", "vendor": "siemens", "count": 1, "zone": "dmz",
             "name": "Central_SCADA_Server", "protocols": ["opc_ua", "s7comm", "modbus_tcp", "snmp"],
             "fingerprint_model": "WinCC Professional",
             "role": "Central SCADA Server"},

            {"type": "historian", "vendor": "ge", "count": 1, "zone": "dmz",
             "name": "Process_Historian", "protocols": ["opc_ua", "modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian"},

            {"type": "gateway", "vendor": "kepware", "count": 1, "zone": "dmz",
             "name": "OPC_UA_Gateway", "protocols": ["opc_ua", "modbus_tcp", "ethernet_ip", "s7comm"],
             "fingerprint_model": "KEPServerEX",
             "role": "OPC UA Gateway"},

            {"type": "engineering_station", "vendor": "siemens", "count": 1, "zone": "dmz",
             "name": "Siemens_Eng_Workstation", "protocols": ["s7comm", "profinet"],
             "fingerprint_model": "TIA Portal",
             "role": "Siemens Engineering Workstation"},

            {"type": "engineering_station", "vendor": "rockwell", "count": 1, "zone": "dmz",
             "name": "Rockwell_Eng_Workstation", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "role": "Rockwell Engineering Workstation"},

            {"type": "gateway", "vendor": "hms", "count": 1, "zone": "dmz",
             "name": "Protocol_Gateway", "protocols": ["modbus_tcp", "ethernet_ip", "profinet"],
             "fingerprint_model": "Anybus X-gateway",
             "role": "Protocol Gateway"},

            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "dmz",
             "name": "Central_Overview_HMI", "protocols": ["s7comm_plus", "opc_ua"],
             "fingerprint_model": "WinCC Unified",
             "role": "Central Multi-Protocol HMI"},

            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "dmz",
             "name": "DMZ_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "firmware_version": "15.2(7)E6",
             "role": "Core Network Switch"},

            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "dmz",
             "name": "Primary_Remote_Gateway", "protocols": ["modbus_tcp", "snmp", "ethernet_ip"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "dmz",
             "name": "Backup_Remote_Gateway", "protocols": ["modbus_tcp", "snmp", "ethernet_ip"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "dmz",
             "name": "IT_OT_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True},

            # ============================================================
            # SIEMENS PRODUCTION ZONE (Level 2) - 25 devices
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Line_1_Main_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             },

            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Line_2_Main_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             },

            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Material_Handling_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             },

            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Packaging_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             },

            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Safety_Controller", "protocols": ["profinet", "profisafe", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 516-3FN01-0AB0",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },

            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Line_1_HMI", "protocols": ["profinet"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "firmware_version": "V17.0.0.0",
             "role": "Operator Interface"},

            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Line_2_HMI", "protocols": ["profinet"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "role": "Operator Interface"},

            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Spindle_VFD_1", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Spindle_VFD_2", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Conveyor_VFD_1", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Conveyor_VFD_2", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Pump_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Fan_VFD", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},

            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_X_Axis_Servo", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},

            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Y_Axis_Servo", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},

            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Z_Axis_Servo", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},

            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Rotary_Servo", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},

            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Cell_1_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},

            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Cell_2_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},

            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Assembly_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},

            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Packaging_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},

            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Safety_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},

            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Utility_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},

            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Zone_Switch_1", "protocols": ["profinet", "snmp"],
             "fingerprint_id": "cisco/ie3500/8t3s",
             "role": "Industrial Switch"},

            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Zone_Switch_2", "protocols": ["profinet", "snmp"],
             "fingerprint_id": "cisco/ie3500/8t3s",
             "role": "Industrial Switch"},

            # ============================================================
            # ROCKWELL PRODUCTION ZONE (Level 2) - 25 devices
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Line_1_Main_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             },

            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Line_2_Main_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             },

            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Material_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L73",
             "firmware_version": "V33.011",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             },

            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_QC_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L73",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             },

            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Safety_Controller", "protocols": ["ethernet_ip", "cip_safety", "opc_ua"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },

            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Line_1_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},

            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Line_2_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},

            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Conveyor_VFD_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Conveyor_VFD_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Pump_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Lift_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Air_Handler_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "20F-D052N103",
             "role": "High-Power Drive"},

            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Exhaust_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "20F-D052N103",
             "role": "High-Power Drive"},

            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Robot_X_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},

            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Robot_Y_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},

            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Robot_Z_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},

            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Positioner_Servo", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},

            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Cell_1_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},

            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Cell_2_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},

            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Assembly_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},

            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Transfer_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},

            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Safety_Gate_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Point I/O"},

            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_E_Stop_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Point I/O"},

            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Zone_Switch_1", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_id": "cisco/ie9320/24p4x",
             "role": "Industrial Switch"},

            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Zone_Switch_2", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_id": "cisco/ie9320/24p4x",
             "role": "Industrial Switch"},

            # ============================================================
            # SCHNEIDER PRODUCTION ZONE (Level 2) - 22 devices
            # ============================================================
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Process_1_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "BMEP586040",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             },

            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Process_2_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "BMEP586040",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             },

            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Utility_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMXP3420302",
             "firmware_version": "V3.10",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             },

            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Batch_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             },

            {"type": "safety_plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Safety_Controller", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEP586040S",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },

            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Process_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "Operator Interface"},

            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Utility_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "Operator Interface"},

            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Mixer_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Pump_1_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Pump_2_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Variable Frequency Drive"},

            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Agitator_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Variable Frequency Drive"},

            {"type": "servo", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Fill_Servo", "protocols": ["modbus_tcp"],
             "fingerprint_model": "LXM32MD18M2",
             "role": "Servo Drive"},

            {"type": "servo", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Cap_Servo", "protocols": ["modbus_tcp"],
             "fingerprint_model": "LXM32MD18M2",
             "role": "Servo Drive"},

            {"type": "servo", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Label_Servo", "protocols": ["modbus_tcp"],
             "fingerprint_model": "LXM32MD18M2",
             "role": "Servo Drive"},

            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Tank_1_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STBNIP2311",
             "role": "Distributed I/O"},

            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Tank_2_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STBNIP2311",
             "role": "Distributed I/O"},

            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Fill_Station_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STBNIP2311",
             "role": "Distributed I/O"},

            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Pack_Station_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STBNIP2311",
             "role": "Distributed I/O"},

            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Valve_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "role": "I/O Module"},

            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Sensor_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "role": "I/O Module"},

            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Zone_Switch_1", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_id": "cisco/ie4000/8gt4g",
             "role": "Industrial Switch"},

            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Zone_Switch_2", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_id": "cisco/ie4000/8gt4g",
             "role": "Industrial Switch"},

            # ============================================================
            # ABB/MIXED PRODUCTION ZONE (Level 2) - 20 devices
            # ============================================================
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Process_1_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "PM590-ETH",
             "firmware_version": "V2.9.0",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Main Process Controller",
             },

            {"type": "plc", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Process_2_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "PM590-ETH",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Main Process Controller",
             },

            {"type": "plc", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Utility_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "PM583-ETH",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.00025},
             "role": "Auxiliary Controller",
             },

            {"type": "plc", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Warehouse_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "PM583-ETH",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.00025},
             "role": "Auxiliary Controller",
             },

            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Process_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Operator Interface"},

            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Warehouse_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Operator Interface"},

            {"type": "drive", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Motor_1_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Industrial Drive"},

            {"type": "drive", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Motor_2_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Industrial Drive"},

            {"type": "drive", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Crane_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Industrial Drive"},

            {"type": "drive", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Hoist_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Industrial Drive"},

            {"type": "drive", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Conveyor_1_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS580",
             "role": "General Purpose Drive"},

            {"type": "drive", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Conveyor_2_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS580",
             "role": "General Purpose Drive"},

            {"type": "sensor", "vendor": "sick", "count": 1, "zone": "abb_zone",
             "name": "Vision_Inspection_Camera", "protocols": ["ethernet_ip"],
             "fingerprint_model": "Inspector P631",
             "role": "Vision System"},

            {"type": "sensor", "vendor": "sick", "count": 1, "zone": "abb_zone",
             "name": "Quality_Check_Camera", "protocols": ["ethernet_ip"],
             "fingerprint_model": "Inspector P631",
             "role": "Vision System"},

            {"type": "sensor", "vendor": "sick", "count": 1, "zone": "abb_zone",
             "name": "Pallet_Barcode_Scanner", "protocols": ["ethernet_ip"],
             "fingerprint_model": "CLV650-0120",
             "role": "Barcode Scanner"},

            {"type": "sensor", "vendor": "sick", "count": 1, "zone": "abb_zone",
             "name": "Product_Barcode_Scanner", "protocols": ["ethernet_ip"],
             "fingerprint_model": "CLV650-0120",
             "role": "Barcode Scanner"},

            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "abb_zone",
             "name": "Process_Water_Flowmeter", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Electromagnetic Flowmeter"},

            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "abb_zone",
             "name": "Cooling_Loop_Flowmeter", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Electromagnetic Flowmeter"},

            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "abb_zone",
             "name": "ABB_Zone_Switch_1", "protocols": ["snmp"],
             "fingerprint_id": "cisco/ie3300/8t2s",
             "role": "Industrial Switch"},

            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "abb_zone",
             "name": "ABB_Zone_Switch_2", "protocols": ["snmp"],
             "fingerprint_id": "cisco/ie3300/8t2s",
             "role": "Industrial Switch"},

            # ============================================================
            # FIELD ZONES (Level 1) - 16 devices total
            # ============================================================
            # Siemens Field Zone
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "field_siemens",
             "name": "Siemens_Raw_Material_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "field_siemens",
             "name": "Siemens_Storage_Area_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "field_siemens",
             "name": "Siemens_Shipping_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "field_siemens",
             "name": "Siemens_Dock_Door_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Field I/O"},

            # Rockwell Field Zone
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "field_rockwell",
             "name": "Rockwell_Raw_Material_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "field_rockwell",
             "name": "Rockwell_Storage_Area_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "field_rockwell",
             "name": "Rockwell_Shipping_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "field_rockwell",
             "name": "Rockwell_Dock_Door_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Field I/O"},

            # Schneider Field Zone
            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "field_schneider",
             "name": "Schneider_Tank_Farm_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "field_schneider",
             "name": "Schneider_Loading_Dock_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "field_schneider",
             "name": "Schneider_CIP_System_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "field_schneider",
             "name": "Schneider_Waste_Treatment_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "role": "Field I/O"},

            # ABB Field Zone
            {"type": "io_module", "vendor": "abb", "count": 1, "zone": "field_abb",
             "name": "ABB_Warehouse_Aisle_1_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CI501",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "abb", "count": 1, "zone": "field_abb",
             "name": "ABB_Warehouse_Aisle_2_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CI501",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "abb", "count": 1, "zone": "field_abb",
             "name": "ABB_Outbound_Staging_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CI501",
             "role": "Field I/O"},

            {"type": "io_module", "vendor": "abb", "count": 1, "zone": "field_abb",
             "name": "ABB_Inbound_Receiving_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CI501",
             "role": "Field I/O"},
        ],
        "flows": [
            # INTRA-ZONE FLOWS - Siemens Zone
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["drive", "io_module", "servo"],
             "source_zones": ["siemens_zone"], "target_zones": ["siemens_zone", "field_siemens"],
             "jitter_ms": 1, "jitter_type": "gaussian"},

            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"],
             "source_zones": ["siemens_zone"], "target_zones": ["siemens_zone", "field_siemens"]},

            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["siemens_zone"], "target_zones": ["siemens_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # INTRA-ZONE FLOWS - Rockwell Zone
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["drive", "io_module", "servo"],
             "source_zones": ["rockwell_zone"], "target_zones": ["rockwell_zone", "field_rockwell"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"],
             "source_zones": ["rockwell_zone"], "target_zones": ["rockwell_zone", "field_rockwell"]},

            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["rockwell_zone"], "target_zones": ["rockwell_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # INTRA-ZONE FLOWS - Schneider Zone
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive", "io_module", "servo"],
             "source_zones": ["schneider_zone"], "target_zones": ["schneider_zone", "field_schneider"],
             "jitter_ms": 20, "jitter_type": "gaussian"},

            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["schneider_zone"], "target_zones": ["schneider_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # INTRA-ZONE FLOWS - ABB/Mixed Zone
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "source_zones": ["abb_zone"], "target_zones": ["abb_zone", "field_abb"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["abb_zone"], "target_zones": ["abb_zone"],
             "jitter_ms": 30, "jitter_type": "gaussian"},

            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["abb_zone"], "target_zones": ["abb_zone"],
             "jitter_ms": 25, "jitter_type": "uniform"},

            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["abb_zone"], "target_zones": ["abb_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # DMZ FLOWS (Supervisory)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["dmz"], "target_zones": ["siemens_zone", "rockwell_zone", "schneider_zone", "abb_zone"]},

            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["siemens_zone", "rockwell_zone", "schneider_zone", "abb_zone"]},

            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["siemens_zone"]},

            # Central HMI is Siemens WinCC Unified (declares s7comm_plus +
            # opc_ua). Cross-vendor PLCs all support OPC UA — that's the
            # right cross-vendor supervisor protocol; using each PLC's
            # vendor-native here would snap to snmp and look irrational.
            {"protocol": "opc_ua", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["rockwell_zone"]},

            {"protocol": "opc_ua", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["schneider_zone", "abb_zone"]},

            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["dmz"], "target_zones": ["dmz", "siemens_zone", "rockwell_zone", "schneider_zone", "abb_zone"]},

            # NOTE: Cross-vendor material-handoff coordination between peer
            # production cells is mediated by the L3.5 supervisory stack
            # (Central SCADA + OPC UA aggregator already subscribe to every
            # cell PLC above), NOT by direct horizontal PLC-to-PLC links.
            # Real multi-vendor plants do not wire a Siemens S7 PLC as a
            # Modbus client to a peer Rockwell PLC across vendor-isolated
            # cells; that east-west path was removed (along with its
            # handoff conduits) per strict IEC 62443 area-zone segmentation.

            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["switch"],
             "source_zones": ["dmz"], "target_zones": ["siemens_zone", "rockwell_zone", "schneider_zone", "abb_zone"],
             "jitter_ms": 10000, "jitter_type": "uniform"},

            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["rockwell_zone"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["schneider_zone", "abb_zone"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # DMZ INFRASTRUCTURE FLOWS (Engineering & Gateway)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["plc"], "target_types": ["gateway"],
             "source_zones": ["siemens_zone", "rockwell_zone", "schneider_zone", "abb_zone"], "target_zones": ["dmz"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            {"protocol": "s7comm", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["engineering_station"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["siemens_zone"],
             "jitter_ms": 500, "jitter_type": "uniform"},

            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["engineering_station"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["rockwell_zone"],
             "jitter_ms": 500, "jitter_type": "uniform"},

            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["gateway"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["schneider_zone", "abb_zone"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "dmz", "name": "Industrial DMZ", "level": 3.5,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "siemens_zone", "name": "Siemens Production", "level": 2,
             "subnet_offset": 1, "vlan": 210, "security_level": "high"},
            {"id": "rockwell_zone", "name": "Rockwell Production", "level": 2,
             "subnet_offset": 2, "vlan": 220, "security_level": "high"},
            {"id": "schneider_zone", "name": "Schneider Production", "level": 2,
             "subnet_offset": 3, "vlan": 230, "security_level": "high"},
            {"id": "abb_zone", "name": "ABB/Mixed Production", "level": 2,
             "subnet_offset": 4, "vlan": 240, "security_level": "high"},
            {"id": "field_siemens", "name": "Siemens Field", "level": 1,
             "subnet_offset": 5, "vlan": 211, "security_level": "standard"},
            {"id": "field_rockwell", "name": "Rockwell Field", "level": 1,
             "subnet_offset": 6, "vlan": 221, "security_level": "standard"},
            {"id": "field_schneider", "name": "Schneider Field", "level": 1,
             "subnet_offset": 7, "vlan": 231, "security_level": "standard"},
            {"id": "field_abb", "name": "ABB Field", "level": 1,
             "subnet_offset": 8, "vlan": 241, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "conduits": [
            # DMZ to production zone conduits (L3.5 -> L2)
            {"id": "dmz_siemens", "name": "DMZ \u2194 Siemens Production",
             "source_zone": "dmz", "target_zone": "siemens_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "s7comm_plus", "s7comm", "profinet", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions, engineering station S7comm programming, central HMI polling, SNMP infrastructure monitoring"},
            {"id": "dmz_rockwell", "name": "DMZ \u2194 Rockwell Production",
             "source_zone": "dmz", "target_zone": "rockwell_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "ethernet_ip", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions, engineering station and EWON EtherNet/IP polling, SNMP monitoring"},
            {"id": "dmz_schneider", "name": "DMZ \u2194 Schneider Production",
             "source_zone": "dmz", "target_zone": "schneider_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions, gateway and EWON Modbus TCP polling, SNMP monitoring"},
            {"id": "dmz_abb", "name": "DMZ \u2194 ABB Production",
             "source_zone": "dmz", "target_zone": "abb_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions, gateway and EWON Modbus TCP polling, SNMP monitoring"},
            # Production zone to field zone conduits (L2 -> L1)
            {"id": "siemens_field", "name": "Siemens Production \u2194 Siemens Field",
             "source_zone": "siemens_zone", "target_zone": "field_siemens",
             "direction": "bidirectional",
             "allowed_protocols": ["profinet", "profisafe"],
             "security_level": "high",
             "description": "Siemens PLCs poll field I/O modules via PROFINET cyclic I/O and PROFIsafe safety"},
            {"id": "rockwell_field", "name": "Rockwell Production \u2194 Rockwell Field",
             "source_zone": "rockwell_zone", "target_zone": "field_rockwell",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "cip_safety"],
             "security_level": "high",
             "description": "Rockwell PLCs poll field I/O modules via EtherNet/IP implicit messaging and CIP Safety"},
            {"id": "schneider_field", "name": "Schneider Production \u2194 Schneider Field",
             "source_zone": "schneider_zone", "target_zone": "field_schneider",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Schneider PLCs poll field I/O modules via Modbus TCP"},
            {"id": "abb_field", "name": "ABB Production \u2194 ABB Field",
             "source_zone": "abb_zone", "target_zone": "field_abb",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "ABB PLCs poll field I/O modules via Modbus TCP"},
            # NOTE: No horizontal L2 peer-cell conduits exist by design.
            # Cross-vendor cells are hermetic at the IEC 62443 area-zone
            # boundary; material-handoff coordination is mediated north
            # through the L3.5 supervisory OPC UA stack, never east-west.
            # DMZ to external conduit (L3.5 -> L4)
            {"id": "dmz_external", "name": "DMZ \u2194 External",
             "source_zone": "dmz", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https", "rdp"],
             "security_level": "critical",
             "description": "EWON remote gateway heartbeat to Talk2M cloud; Jump server RDP for IT/OT boundary access"},
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
            "timing": ["delayed_response", "jitter_spike", "watchdog_timeout", "rpi_violation"],
            "protocol": ["profinet_alarm", "cip_error", "modbus_exception", "profisafe_error", "cip_safety_fault"],
            "sequence": ["duplicate", "out_of_order", "dropped_packet"],
            "payload": ["value_spike", "encoder_fault"],
            "network": ["broadcast_storm"],
            "security": ["unauthorized_access", "scan_activity", "replay_attack", "unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["51.38.74.240", "87.98.169.126", "185.188.32.1"],
            "enable_c2": True,
            "c2_protocol": "https",
            "c2_pattern": "jittered_1m",
            "enable_exfil": True,
            "exfil_protocol": "http",
            "enable_exploits": True,
            "exploit_patterns": ["s7_stop_cpu", "cip_stop_plc", "modbus_write_scan", "historian_sqli", "rdp_bluekeep"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "engineering_station", "scada_server", "historian", "jump_server"],
        },
        "total_duration_ms": 900000,
    },

    # ============================================================
    # TEMPLATE 4: STRICT PURDUE SEGMENTED MANUFACTURING (67 devices)
    # Precision automotive parts with 4 isolated cells + IDMZ
    # NO east-west communication between cells
    # ============================================================
    "strict_purdue_segmented": {
        "name": "Strict Purdue Segmented Manufacturing",
        "description": "Compact precision-machining facility laid out per IEC 62443 with strict "
                       "Purdue segmentation: three multi-vendor production cells (one each for "
                       "Siemens / Rockwell / Schneider), an L3 Operations zone, and an L3.5 "
                       "IDMZ. Cell-isolation defaults to `conduit_gated` so cross-zone flows "
                       "must match a declared conduit. 45 devices across 5 zones.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        # Boot the scenario in strict_northbound mode so the runtime gate
        # actively enforces what the topology implies. The studio UI lets the
        # user dial it back to conduit_gated or off if they want to relax.
        "cell_isolation": {
            "mode": "strict_northbound",
            "applies_to_levels": [0, 1, 2],
        },
        "zones": [
            # Operations / Process Control - Level 3 (SCADA, historian, engineering)
            {"id": "operations", "name": "Process Control / Operations", "level": 3,
             "subnet_offset": 5, "vlan": 150, "security_level": "critical"},
            # IDMZ - Level 3.5 (bastion zone: jump server, EWON, firewall switches)
            {"id": "idmz", "name": "Industrial DMZ", "level": 3.5,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            # Cell 1 - CNC Machining (Siemens ecosystem, self-contained L0-L2)
            {"id": "cell1_cnc", "name": "Cell 1 - CNC Machining", "level": 2,
             "subnet_offset": 1, "vlan": 210, "security_level": "high"},
            # Cell 2 - Robotic Welding (Rockwell ecosystem, self-contained L0-L2)
            {"id": "cell2_weld", "name": "Cell 2 - Robotic Welding", "level": 2,
             "subnet_offset": 2, "vlan": 220, "security_level": "high"},
            # Cell 3 - E-Coat Treatment (Schneider ecosystem, self-contained L0-L2)
            {"id": "cell3_ecoat", "name": "Cell 3 - E-Coat Treatment", "level": 2,
             "subnet_offset": 3, "vlan": 230, "security_level": "high"},
            # Cell 4 - Final Assembly & Test (mixed ABB / Fanuc / Rockwell-safety, self-contained L0-L2)
            {"id": "cell4_assembly", "name": "Cell 4 - Final Assembly", "level": 2,
             "subnet_offset": 4, "vlan": 240, "security_level": "high"},
        ],
        "conduits": [
            # L3 Operations to cell conduits - supervisory data + engineering access
            # All SCADA/historian/OPC/HMI/EWS traffic flows through here (strict Purdue).
            {"id": "ops_cell1_cnc", "name": "Operations \u2194 Cell 1 CNC",
             "source_zone": "operations", "target_zone": "cell1_cnc",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "s7comm_plus", "s7comm", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to Siemens PLCs, central HMI and engineering workstation S7comm+ access, SNMP infrastructure monitoring"},
            {"id": "ops_cell2_weld", "name": "Operations \u2194 Cell 2 Welding",
             "source_zone": "operations", "target_zone": "cell2_weld",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "ethernet_ip", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to Rockwell PLCs, central HMI and engineering workstation EtherNet/IP access, SNMP monitoring"},
            {"id": "ops_cell3_ecoat", "name": "Operations \u2194 Cell 3 E-Coat",
             "source_zone": "operations", "target_zone": "cell3_ecoat",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to Schneider PLCs, central HMI and engineering workstation Modbus TCP access, SNMP monitoring"},
            {"id": "ops_cell4_assembly", "name": "Operations \u2194 Cell 4 Assembly",
             "source_zone": "operations", "target_zone": "cell4_assembly",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "ethernet_ip", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to ABB PLCs, central HMI Modbus TCP and engineering workstation EtherNet/IP access, SNMP monitoring"},
            # IDMZ to cell conduits - narrow EWON remote polling + jump server SNMP recon only
            {"id": "idmz_cell1_cnc", "name": "IDMZ \u2194 Cell 1 CNC",
             "source_zone": "idmz", "target_zone": "cell1_cnc",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "EWON remote gateway Modbus TCP polling for offsite monitoring; jump server SNMP reconnaissance"},
            {"id": "idmz_cell2_weld", "name": "IDMZ \u2194 Cell 2 Welding",
             "source_zone": "idmz", "target_zone": "cell2_weld",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "EWON remote gateway Modbus TCP polling for offsite monitoring; jump server SNMP reconnaissance"},
            {"id": "idmz_cell3_ecoat", "name": "IDMZ \u2194 Cell 3 E-Coat",
             "source_zone": "idmz", "target_zone": "cell3_ecoat",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "EWON remote gateway Modbus TCP polling for offsite monitoring; jump server SNMP reconnaissance"},
            {"id": "idmz_cell4_assembly", "name": "IDMZ \u2194 Cell 4 Assembly",
             "source_zone": "idmz", "target_zone": "cell4_assembly",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "EWON remote gateway Modbus TCP polling for offsite monitoring; jump server SNMP reconnaissance"},
            # L3 Operations <-> L3.5 IDMZ - historian forwarding, jump-to-EWS pivot, internal monitoring
            {"id": "ops_idmz", "name": "Operations \u2194 IDMZ",
             "source_zone": "operations", "target_zone": "idmz",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "snmp", "rdp", "https"],
             "security_level": "critical",
             "description": "Historian forwarding to IDMZ proxy, SCADA SNMP polling of IDMZ switch, jump server RDP pivot to engineering workstation"},
            # NOTE: No L0-L2 east/west conduits exist by design. Cells are
            # hermetic at the IEC 62443 area-zone boundary; cell_isolation.mode
            # is set to strict_northbound so the runtime drops any cell-to-cell
            # flow that someone tries to add later.
        ],
        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high", "rationale": "Tests PIPEDREAM lateral movement against Purdue segmentation"},
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "Strict Purdue model tests reconnaissance containment"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "manufacturing",
            "description": "CNC machining simulation for segmented Purdue architecture",
            "key_variables": ["spindle_speed", "feed_rate", "coolant_temp", "vibration", "tool_wear"],
            "available_faults": ["tool_breakage", "coolant_failure", "drive_overload"],
        },
        "devices": [
            # ============================================================
            # OPERATIONS / PROCESS CONTROL (Level 3) — 4 devices
            # All cross-cell supervisory and engineering traffic originates here.
            # ============================================================
            {"type": "scada_server", "vendor": "siemens", "count": 1, "zone": "operations",
             "name": "Ops_Central_SCADA",
             "protocols": ["opc_ua", "s7comm_plus", "s7comm", "modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "WinCC Professional",
             "role": "Central SCADA Server"},
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "operations",
             "name": "Ops_Process_Historian", "protocols": ["opc_ua", "modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian",
             },
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "operations",
             "name": "Ops_Overview_HMI",
             "protocols": ["s7comm_plus", "s7comm", "opc_ua", "modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "WinCC Unified",
             "role": "Central Overview HMI"},
            # OT Engineering Workstation — TIA Portal / Studio 5000 / Control Expert host.
            # Remote engineers pivot in through the IDMZ jump server and use this box
            # to push programs / browse tags on cell PLCs. Classic strict-Purdue access path.
            {"type": "engineering_workstation", "vendor": "microsoft", "count": 1, "zone": "operations",
             "name": "Ops_Engineering_Workstation",
             "protocols": ["s7comm_plus", "s7comm", "ethernet_ip", "modbus_tcp", "opc_ua", "snmp"],
             "fingerprint_model": "Jump Server 2019",
             "role": "OT Engineering Workstation"},

            # ============================================================
            # IDMZ (Level 3.5) — 3 devices
            # Bastion functions only: remote-access gateway, jump server, IDMZ switch.
            # ============================================================
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "idmz",
             "name": "IDMZ_EWON_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},
            # Windows Server 2016 Jump Server (BlueKeep). RDP is a semantic declaration only —
            # the attack-simulation layer drives any RDP pivot traffic.
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "idmz",
             "name": "IDMZ_Jump_Server", "protocols": ["rdp", "snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "idmz",
             "name": "IDMZ_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-9320-24P4X-E",
             "firmware_version": "17.9.3",
             "role": "Core Network Switch"},

            # ============================================================
            # CELL 1: CNC MACHINING CENTER — Siemens (7 devices)
            # PROFINET RT cyclic I/O + PROFIsafe + S7comm+
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Cell_Main_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             },
            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Safety_Controller",
             "protocols": ["profinet", "profisafe", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 516-3FN01-0AB0",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Operator_HMI", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "firmware_version": "V17.0.0.0",
             "role": "Operator Interface"},
            # Spindle servo represents the motion-axis class.
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Spindle_Servo", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            # Coolant-pump VFD represents auxiliary drives.
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Coolant_Pump_VFD", "protocols": ["profinet", "modbus_tcp", "snmp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            # Tool-changer / pallet I/O represents distributed I/O.
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Tool_Changer_IO", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Cell_Switch", "protocols": ["profinet", "snmp"],
             "fingerprint_id": "cisco/ie3500/8t3s",
             "role": "Industrial Switch"},

            # ============================================================
            # CELL 2: ROBOTIC WELDING LINE — Rockwell (7 devices)
            # EtherNet/IP implicit I/O + CIP Safety
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Line_PLC",
             "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Line Controller",
             },
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Safety_PLC",
             "protocols": ["ethernet_ip", "cip_safety", "opc_ua"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Main_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T15C22D9P",
             "role": "Operator Interface"},
            # Single KUKA welding robot represents the welding work-cell motion class.
            {"type": "robot_controller", "vendor": "kuka", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Robot_Controller",
             "protocols": ["ethernet_ip", "profinet"],
             "fingerprint_model": "KR C4",
             "firmware_version": "V8.3.5",
             "role": "Robot Controller"},
            # PowerFlex 525 conveyor VFD represents the auxiliary-drive class.
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Conveyor_VFD",
             "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "25B-D030N104",
             "firmware_version": "V5.001",
             "role": "Variable Frequency Drive"},
            # FLEX 5000 remote I/O — also the cip_safety target for the safety controller.
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Station_IO",
             "protocols": ["ethernet_ip", "cip_safety", "snmp"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Switch",
             "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_id": "cisco/ie9320/24p4x",
             "role": "Industrial Switch"},

            # ============================================================
            # CELL 3: E-COAT SURFACE TREATMENT — Schneider (7 devices)
            # Modbus TCP polling throughout
            # ============================================================
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Process_PLC",
             "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "BMEP586040",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0001},
             "role": "Process Controller",
             },
            {"type": "safety_plc", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Safety_Controller",
             "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "TM5CSLC100FS",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Operator_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIGTO5310",
             "role": "Operator Interface"},
            # Altivar 930 rectifier represents the e-coat power-train drive.
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Rectifier_VFD",
             "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ATV930D15N4",
             "firmware_version": "V3.6IE50",
             "role": "Rectifier Drive"},
            # E+H pH/conductivity analyzer — process measurement.
            {"type": "sensor", "vendor": "endress+hauser", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_pH_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "CM442",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.0005},
             "role": "Process Analyzer"},
            # Advantys STB pretreatment I/O.
            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Pretreat_IO",
             "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "STBNIP2311",
             "role": "Remote I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Cell_Switch",
             "protocols": ["snmp"],
             "fingerprint_id": "cisco/ie4000/8gt4g",
             "role": "Industrial Switch"},

            # ============================================================
            # CELL 4: FINAL ASSEMBLY & TEST — mixed-vendor (7 devices)
            # ABB process control, Fanuc robot, Rockwell safety + I/O.
            # Protocols: EtherNet/IP + Modbus TCP + CIP Safety.
            # ============================================================
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Line_PLC",
             "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "PM590-ETH",
             "firmware_version": "V2.9.0",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0001},
             "role": "Line Controller",
             },
            # Rockwell GuardLogix safety controller — realistic in a mixed-vendor cell;
            # CIP Safety pairs with the Rockwell FLEX I/O below.
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Safety_Controller",
             "protocols": ["ethernet_ip", "cip_safety", "opc_ua"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },
            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Operator_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Operator Interface"},
            # Fanuc R-30iB on EtherNet/IP — robot motion class.
            {"type": "robot_controller", "vendor": "fanuc", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Robot_Controller",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "R-30iB Plus",
             "firmware_version": "V9.30",
             "role": "Robot Controller"},
            # ABB ACS880 conveyor VFD — production drive class.
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Conveyor_VFD",
             "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "ACS880-01",
             "role": "Variable Frequency Drive"},
            # Rockwell FLEX 5000 remote I/O — paired CIP Safety target for the GuardLogix.
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Station_IO",
             "protocols": ["ethernet_ip", "cip_safety", "snmp"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Cell_Switch",
             "protocols": ["snmp"],
             "fingerprint_id": "cisco/ie3300/8t2s",
             "role": "Industrial Switch"},
        ],

        "flows": [
            # ============================================================
            # CELL 1 INTRA-CELL — Siemens PROFINET / S7comm+ / PROFIsafe
            # All flows source and target the same cell. The runtime gate
            # would also drop any cell-to-cell flow on top of these.
            # ============================================================
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["servo"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["io_module"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"]},
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # CELL 2 INTRA-CELL — Rockwell EtherNet/IP + CIP Safety
            # ============================================================
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source_types": ["plc"], "target_types": ["robot_controller"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 0.2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["io_module"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"]},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # CELL 3 INTRA-CELL — Schneider Modbus TCP
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # Schneider TM5 safety — Modbus heartbeat to the process PLC.
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["safety_plc"], "target_types": ["plc"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 30, "jitter_type": "uniform"},

            # ============================================================
            # CELL 4 INTRA-CELL — ABB Modbus TCP + EtherNet/IP + CIP Safety
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["robot_controller"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # Rockwell GuardLogix → Rockwell FLEX I/O over CIP Safety.
            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["io_module"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"]},

            # ============================================================
            # L3 OPERATIONS → CELL SUPERVISORY FLOWS (northbound data collection)
            # SCADA, historian, central HMI, OPC gateway, and engineering
            # workstation all live in the Operations zone. Strict Purdue:
            # no cell initiates northbound, no cell-to-cell lateral.
            # ============================================================
            # OPC UA - SCADA server subscriptions to all cell PLCs (1s)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["operations"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"]},
            # OPC UA - Historian data collection from all cell PLCs (5s)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["operations"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"]},
            # S7comm+ - Central HMI polling Siemens cell PLCs (1s)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["operations"], "target_zones": ["cell1_cnc"]},
            # OPC UA - Central HMI polling cross-vendor cell PLCs (1s).
            # The L3 HMI is Siemens; cross-vendor PLCs (Rockwell/Schneider/
            # ABB) all support OPC UA. Authoring as ethernet_ip/modbus_tcp
            # would snap to snmp at runtime (no shared vendor protocol).
            {"protocol": "opc_ua", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["operations"], "target_zones": ["cell2_weld"]},
            {"protocol": "opc_ua", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["operations"], "target_zones": ["cell3_ecoat", "cell4_assembly"]},

            # ============================================================
            # ENGINEERING WORKSTATION FLOWS (L3 Operations → Cells)
            # Occasional engineering access: program uploads, tag browsing,
            # firmware checks. Low-frequency (30s) to represent non-production
            # activity. This is the inner ring of the strict-Purdue remote
            # path: remote user → IDMZ jump server → L3 EWS → cell PLCs.
            # ============================================================
            # S7comm+ - EWS → Cell 1 Siemens PLCs (engineering access)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["engineering_workstation"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["operations"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 5000, "jitter_type": "uniform"},
            # EtherNet/IP - EWS → Cell 2 Rockwell PLCs (engineering access)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["engineering_workstation"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["operations"], "target_zones": ["cell2_weld"],
             "jitter_ms": 5000, "jitter_type": "uniform"},
            # Modbus TCP - EWS → Cell 3 Schneider PLCs (engineering access)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["engineering_workstation"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["operations"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 5000, "jitter_type": "uniform"},
            # EtherNet/IP - EWS → Cell 4 safety controller (engineering access)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["engineering_workstation"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["operations"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # ============================================================
            # L3.5 IDMZ → CELL FLOWS (bastion-only narrow polling)
            # Only EWON remote gateway and jump server SNMP recon originate
            # from the IDMZ — everything else moved to L3 Operations.
            # ============================================================
            # Modbus TCP - EWON remote gateway polling all cell PLCs (10s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["idmz"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},
            # SNMP - Jump server network reconnaissance (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["switch"],
             "source_zones": ["idmz"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"],
             "jitter_ms": 10000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP INFRASTRUCTURE MONITORING
            # ============================================================
            # SNMP - SCADA (L3) monitoring all switches + EWON remote gateway (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["operations"],
             "target_zones": ["operations", "idmz",
                              "cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"]},
            # SNMP - SCADA (L3) monitoring the IDMZ jump server (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["jump_server"],
             "source_zones": ["operations"], "target_zones": ["idmz"],
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP FIELD DEVICE MONITORING (per-cell, strictly intra-cell)
            # ============================================================
            # NOTE: Earlier authoring used switches as the SNMP polling
            # source for in-cell field devices. That's the wrong topology —
            # switches are POLLED by NMS, not the other way around. PLCs
            # already poll their cell's drives / IO / servos via PROFINET
            # I/O, which gives CV all the MAC↔IP correlation it needs once
            # the per-PLC SNMP discovery loop runs against those endpoints.
            # ============================================================
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

        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["51.38.74.240", "87.98.169.126", "185.188.32.1"],
            "enable_c2": True,
            "c2_protocol": "https",
            "c2_pattern": "jittered_1m",
            "enable_exfil": True,
            "exfil_protocol": "http",
            "enable_exploits": True,
            "exploit_patterns": ["s7_stop_cpu", "cip_stop_plc", "modbus_write_scan", "rdp_bluekeep"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "scada_server", "historian", "jump_server"],
        },
        "total_duration_ms": 600000,
    },

    # ============================================================
    # PHASE 10 SHOWCASE TEMPLATES
    # These are minimal stubs — devices / flows / zones come entirely
    # from the archetype generator (see legacy_template_archetypes.py).
    # ============================================================

    "semiconductor_fab_300mm": {
        "name": "Semiconductor Fab — 300mm Wafer Line",
        "description": "300mm wafer fabrication facility with 6 process bays "
                       "(lithography, etch, deposition, CMP, metrology, "
                       "diffusion), each cluster-tool driven and densely "
                       "instrumented with analyzers (RGA, mass-spec, gas "
                       "chromatograph) and vision (alignment, defect, "
                       "metrology). AMHS zone carries an OHT fleet ferrying "
                       "FOUPs between bays under fleet-manager dispatch. "
                       "Cleanroom-environmental zone monitors particle / "
                       "temperature / humidity. Showcases the full vision / "
                       "analyzer / AGV / fleet-manager stack at scale. "
                       "~140 devices across 10 zones.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        # Strict Purdue: bays are hermetic L0-L2; only L3 Operations crosses zones.
        "cell_isolation": {
            "mode": "strict_northbound",
            "applies_to_levels": [0, 1, 2],
        },
        "zones": [
            # Operations / Process Control - Level 3 (MES, historian, SCADA, EWS)
            {"id": "operations", "name": "Fab Operations / MES", "level": 3,
             "subnet_offset": 5, "vlan": 150, "security_level": "critical"},
            # Process bays - Level 2 (each cluster-tool driven, self-contained)
            {"id": "bay_litho", "name": "Bay 1 - Lithography", "level": 2,
             "subnet_offset": 1, "vlan": 210, "security_level": "high"},
            {"id": "bay_etch", "name": "Bay 2 - Etch", "level": 2,
             "subnet_offset": 2, "vlan": 220, "security_level": "high"},
            {"id": "bay_depo", "name": "Bay 3 - Deposition (CVD/PVD)", "level": 2,
             "subnet_offset": 3, "vlan": 230, "security_level": "high"},
            {"id": "bay_cmp", "name": "Bay 4 - CMP (Planarization)", "level": 2,
             "subnet_offset": 4, "vlan": 240, "security_level": "high"},
            {"id": "bay_metro", "name": "Bay 5 - Metrology / Inspection", "level": 2,
             "subnet_offset": 6, "vlan": 250, "security_level": "high"},
            {"id": "bay_diff", "name": "Bay 6 - Diffusion / Furnace", "level": 2,
             "subnet_offset": 7, "vlan": 260, "security_level": "high"},
            # AMHS - Level 2 (OHT/AGV material handling under a fleet manager)
            {"id": "amhs", "name": "AMHS - Material Handling", "level": 2,
             "subnet_offset": 8, "vlan": 270, "security_level": "high"},
            # Cleanroom environmental monitoring - Level 2
            {"id": "cleanroom", "name": "Cleanroom Environmental", "level": 2,
             "subnet_offset": 9, "vlan": 280, "security_level": "high"},
        ],
        "conduits": [
            # L3 Operations <-> each process bay / AMHS / cleanroom.
            # One conduit per cross-zone flow zone-pair (all vertical L3<->bay).
            {"id": "ops_bay_litho", "name": "Operations ↔ Bay 1 Lithography",
             "source_zone": "operations", "target_zone": "bay_litho",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "s7comm", "snmp"],
             "security_level": "critical",
             "description": "MES/historian OPC UA subscriptions to the lithography cluster-tool PLC, central HMI and engineering workstation S7comm access, SNMP infrastructure monitoring"},
            {"id": "ops_bay_etch", "name": "Operations ↔ Bay 2 Etch",
             "source_zone": "operations", "target_zone": "bay_etch",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "ethernet_ip", "snmp"],
             "security_level": "critical",
             "description": "MES/historian OPC UA subscriptions to the etch cluster-tool PLC, central HMI and engineering EtherNet/IP access, SNMP monitoring"},
            {"id": "ops_bay_depo", "name": "Operations ↔ Bay 3 Deposition",
             "source_zone": "operations", "target_zone": "bay_depo",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "s7comm", "snmp"],
             "security_level": "critical",
             "description": "MES/historian OPC UA subscriptions to the deposition cluster-tool PLC, central HMI and engineering S7comm access, SNMP monitoring"},
            {"id": "ops_bay_cmp", "name": "Operations ↔ Bay 4 CMP",
             "source_zone": "operations", "target_zone": "bay_cmp",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "MES/historian OPC UA subscriptions to the CMP cluster-tool PLC, central HMI and engineering Modbus TCP access, SNMP monitoring"},
            {"id": "ops_bay_metro", "name": "Operations ↔ Bay 5 Metrology",
             "source_zone": "operations", "target_zone": "bay_metro",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "ethernet_ip", "snmp"],
             "security_level": "critical",
             "description": "MES/historian OPC UA subscriptions to the metrology cluster-tool PLC, central HMI and engineering EtherNet/IP access, SNMP monitoring"},
            {"id": "ops_bay_diff", "name": "Operations ↔ Bay 6 Diffusion",
             "source_zone": "operations", "target_zone": "bay_diff",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "s7comm", "snmp"],
             "security_level": "critical",
             "description": "MES/historian OPC UA subscriptions to the diffusion furnace cluster-tool PLC, central HMI and engineering S7comm access, SNMP monitoring"},
            {"id": "ops_amhs", "name": "Operations ↔ AMHS",
             "source_zone": "operations", "target_zone": "amhs",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "ethernet_ip", "snmp"],
             "security_level": "critical",
             "description": "MES dispatch and historian OPC UA / Modbus collection from the AMHS fleet manager, SNMP monitoring of the AMHS switch"},
            {"id": "ops_cleanroom", "name": "Operations ↔ Cleanroom Environmental",
             "source_zone": "operations", "target_zone": "cleanroom",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "MES/historian OPC UA and Modbus collection of cleanroom particle/temperature/humidity monitoring, SNMP infrastructure monitoring"},
            # NOTE: No L0-L2 east/west conduits exist by design. Bays are hermetic
            # at the IEC 62443 area-zone boundary; cell_isolation is strict_northbound
            # so the runtime drops any bay-to-bay flow added later.
        ],
        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high",
             "rationale": "Tests PIPEDREAM lateral movement against strict bay segmentation"},
            {"playbook_id": "network_recon", "relevance": "high",
             "rationale": "Dense multi-vendor fab tests reconnaissance containment"},
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "manufacturing",
            "description": "Cluster-tool wafer processing simulation",
            "key_variables": ["chamber_pressure", "rf_power", "gas_flow", "wafer_temp", "throughput"],
            "available_faults": ["chamber_leak", "rf_arc", "gas_flow_fault"],
        },
        "devices": [
            # ============================================================
            # OPERATIONS / MES (Level 3) — 6 devices
            # All cross-bay supervisory and engineering traffic originates here.
            # ============================================================
            {"type": "scada_server", "vendor": "honeywell", "count": 1, "zone": "operations",
             "name": "Fab_MES_SCADA_Server",
             "protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "fingerprint_model": "Experion Server",
             "firmware_version": "R510.1",
             "role": "MES / SCADA Server"},
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "operations",
             "name": "Fab_Process_Historian",
             "protocols": ["opc_ua", "modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian"},
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "operations",
             "name": "Fab_Central_Overview_HMI",
             "protocols": ["s7comm", "opc_ua"],
             "fingerprint_model": "WinCC Unified",
             "role": "Central Overview HMI"},
            {"type": "engineering_station", "vendor": "siemens", "count": 1, "zone": "operations",
             "name": "Fab_Engineering_Workstation",
             "protocols": ["s7comm", "profinet"],
             "fingerprint_model": "TIA Portal",
             "role": "OT Engineering Workstation"},
            {"type": "engineering_station", "vendor": "yokogawa", "count": 1, "zone": "operations",
             "name": "Fab_Analyzer_EWS",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "EWS",
             "firmware_version": "R6.05",
             "role": "Analyzer Engineering Workstation"},
            {"type": "network_switch", "vendor": "cisco", "count": 1, "zone": "operations",
             "name": "Ops_Core_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-9320-24P4X-E",
             "firmware_version": "17.9.3",
             "role": "Core Network Switch"},

            # ============================================================
            # BAY 1: LITHOGRAPHY — Siemens cluster tool (7 devices)
            # PROFINET cyclic I/O + S7comm + alignment vision + RGA analyzer
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "bay_litho",
             "name": "Litho_Cluster_Tool_PLC",
             "protocols": ["profinet", "s7comm", "opc_ua"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "role": "Cluster Tool Controller"},
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "bay_litho",
             "name": "Litho_Operator_HMI",
             "protocols": ["profinet", "s7comm"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "firmware_version": "V17.0.0.0",
             "role": "Operator Interface"},
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "bay_litho",
             "name": "Litho_Stage_Servo",
             "protocols": ["profinet"],
             "fingerprint_model": "6SL3310-1TE32-6AA3",
             "role": "Wafer Stage Servo"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "bay_litho",
             "name": "Litho_Track_IO",
             "protocols": ["profinet"],
             "fingerprint_model": "6ES7155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "vision_sensor", "vendor": "sick", "count": 1, "zone": "bay_litho",
             "name": "Litho_Alignment_Vision",
             "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "Inspector P631",
             "role": "Wafer Alignment Vision"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "bay_litho",
             "name": "Litho_Resist_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "Resist Process Analyzer"},
            {"type": "network_switch", "vendor": "cisco", "count": 1, "zone": "bay_litho",
             "name": "Litho_Bay_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Industrial Switch"},

            # ============================================================
            # BAY 2: ETCH — Rockwell cluster tool (7 devices)
            # EtherNet/IP cyclic I/O + RGA mass-spec + defect vision
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "bay_etch",
             "name": "Etch_Cluster_Tool_PLC",
             "protocols": ["ethernet_ip", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "role": "Cluster Tool Controller"},
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "bay_etch",
             "name": "Etch_Operator_HMI",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T15C22D9P",
             "firmware_version": "V12.00",
             "role": "Operator Interface"},
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "bay_etch",
             "name": "Etch_Chamber_Servo",
             "protocols": ["ethernet_ip", "cip_motion"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Chamber Lift Servo"},
            {"type": "remote_io", "vendor": "rockwell", "count": 1, "zone": "bay_etch",
             "name": "Etch_Chamber_IO",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "firmware_version": "V5.019",
             "role": "Remote I/O"},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "bay_etch",
             "name": "Etch_Defect_Vision",
             "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Post-Etch Defect Vision"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "bay_etch",
             "name": "Etch_RGA_MassSpec",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "TDLS8000",
             "role": "RGA / Mass-Spec Analyzer"},
            {"type": "network_switch", "vendor": "cisco", "count": 1, "zone": "bay_etch",
             "name": "Etch_Bay_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Industrial Switch"},

            # ============================================================
            # BAY 3: DEPOSITION (CVD/PVD) — Siemens cluster tool (7 devices)
            # PROFINET cyclic I/O + gas chromatograph + gas-flow analyzers
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "bay_depo",
             "name": "Depo_Cluster_Tool_PLC",
             "protocols": ["profinet", "s7comm", "opc_ua"],
             "fingerprint_model": "6ES7 516-3AN02-0AB0",
             "firmware_version": "V2.8.1",
             "role": "Cluster Tool Controller"},
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "bay_depo",
             "name": "Depo_Operator_HMI",
             "protocols": ["profinet", "s7comm", "opc_ua"],
             "fingerprint_model": "6AV2 124-0QC02-0AX1",
             "role": "Operator Interface"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "bay_depo",
             "name": "Depo_Vacuum_Pump_VFD",
             "protocols": ["profinet"],
             "fingerprint_model": "6SL3310-1TE32-6AA3",
             "role": "Vacuum Pump Drive"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "bay_depo",
             "name": "Depo_Gas_Panel_IO",
             "protocols": ["profinet"],
             "fingerprint_model": "ET 200MP IM155-5 PN",
             "role": "Gas Panel I/O"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "bay_depo",
             "name": "Depo_Gas_Chromatograph",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "GC8000",
             "role": "Gas Chromatograph"},
            {"type": "network_switch", "vendor": "cisco", "count": 1, "zone": "bay_depo",
             "name": "Depo_Bay_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Industrial Switch"},

            # ============================================================
            # BAY 4: CMP (Planarization) — Schneider cluster tool (6 devices)
            # Modbus TCP polling + slurry flow / pressure instrumentation
            # ============================================================
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "bay_cmp",
             "name": "CMP_Cluster_Tool_PLC",
             "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "BMXP3420302",
             "firmware_version": "V2.90",
             "role": "Cluster Tool Controller"},
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "bay_cmp",
             "name": "CMP_Operator_HMI",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "firmware_version": "V3.3.0",
             "role": "Operator Interface"},
            {"type": "servo", "vendor": "schneider", "count": 1, "zone": "bay_cmp",
             "name": "CMP_Polish_Head_Servo",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "LXM32MD18N4",
             "role": "Polish Head Servo"},
            {"type": "flow_sensor", "vendor": "endress+hauser", "count": 1, "zone": "bay_cmp",
             "name": "CMP_Slurry_Flow_Meter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Slurry Flow Meter"},
            {"type": "pressure_sensor", "vendor": "endress+hauser", "count": 1, "zone": "bay_cmp",
             "name": "CMP_Downforce_Pressure",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PMC71",
             "role": "Downforce Pressure Transmitter"},
            {"type": "network_switch", "vendor": "cisco", "count": 1, "zone": "bay_cmp",
             "name": "CMP_Bay_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Industrial Switch"},

            # ============================================================
            # BAY 5: METROLOGY / INSPECTION — Rockwell + vision (6 devices)
            # EtherNet/IP + metrology vision + defect vision
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "bay_metro",
             "name": "Metro_Tool_PLC",
             "protocols": ["ethernet_ip", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "role": "Metrology Tool Controller"},
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "bay_metro",
             "name": "Metro_Operator_HMI",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "bay_metro",
             "name": "Metro_CD_Vision",
             "protocols": ["ethernet_ip", "profinet", "modbus_tcp"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Critical-Dimension Metrology Vision"},
            {"type": "remote_io", "vendor": "rockwell", "count": 1, "zone": "bay_metro",
             "name": "Metro_Stage_IO",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Stage Remote I/O"},
            {"type": "network_switch", "vendor": "cisco", "count": 1, "zone": "bay_metro",
             "name": "Metro_Bay_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Industrial Switch"},

            # ============================================================
            # BAY 6: DIFFUSION / FURNACE — Siemens + safety (7 devices)
            # PROFINET + PROFIsafe + furnace temp / gas instrumentation
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "bay_diff",
             "name": "Diff_Furnace_PLC",
             "protocols": ["profinet", "s7comm", "opc_ua"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "role": "Furnace Cluster Controller"},
            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "bay_diff",
             "name": "Diff_Furnace_Safety_PLC",
             "protocols": ["profinet", "profisafe", "s7comm", "opc_ua"],
             "fingerprint_model": "6ES7 516-3FN01-0AB0",
             "role": "Furnace Safety Controller"},
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "bay_diff",
             "name": "Diff_Operator_HMI",
             "protocols": ["profinet", "s7comm"],
             "fingerprint_model": "6AV2 123-2GB03-0AX0",
             "firmware_version": "V16.0.0.0",
             "role": "Operator Interface"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "bay_diff",
             "name": "Diff_Thermocouple_IO",
             "protocols": ["profinet"],
             "fingerprint_model": "6ES7155-6AU01-0BN0",
             "role": "Thermocouple I/O"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "bay_diff",
             "name": "Diff_Ambient_O2_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "TDLS8000",
             "role": "Furnace O2 Analyzer"},
            {"type": "network_switch", "vendor": "cisco", "count": 1, "zone": "bay_diff",
             "name": "Diff_Bay_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Industrial Switch"},

            # ============================================================
            # AMHS — Material Handling (7 devices)
            # OHT/AGV fleet under a fleet manager + zone PLC
            # ============================================================
            {"type": "fleet_manager", "vendor": "kuka", "count": 1, "zone": "amhs",
             "name": "AMHS_Fleet_Manager",
             "protocols": ["modbus_tcp", "ethernet_ip", "profinet"],
             "fingerprint_model": "KUKA.FleetManager",
             "role": "AMHS Fleet Manager"},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "amhs",
             "name": "AMHS_Zone_PLC",
             "protocols": ["ethernet_ip", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "role": "AMHS Zone Controller"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "amhs",
             "name": "AMHS_OHT_01",
             "protocols": ["ethernet_ip", "profinet"],
             "fingerprint_model": "KMP 1500",
             "role": "Overhead Hoist Transport"},
            {"type": "robot_controller", "vendor": "kuka", "count": 1, "zone": "amhs",
             "name": "AMHS_LoadPort_Robot_Controller",
             "protocols": ["ethernet_ip", "profinet"],
             "fingerprint_model": "KR C4",
             "firmware_version": "V8.3.5",
             "role": "Load-Port / Sorter Robot Controller"},
            {"type": "agv", "vendor": "mir", "count": 1, "zone": "amhs",
             "name": "AMHS_FOUP_AGV_01",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "MiR250",
             "role": "FOUP Floor AGV"},
            {"type": "network_switch", "vendor": "cisco", "count": 1, "zone": "amhs",
             "name": "AMHS_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Industrial Switch"},

            # ============================================================
            # CLEANROOM ENVIRONMENTAL MONITORING (7 devices)
            # Particle / temp / humidity instrumentation under a monitoring PLC
            # ============================================================
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "cleanroom",
             "name": "Cleanroom_Monitor_PLC",
             "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "BMXP3420302",
             "role": "Environmental Monitoring Controller"},
            {"type": "remote_io", "vendor": "moxa", "count": 1, "zone": "cleanroom",
             "name": "Cleanroom_Particle_IO",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ioLogik E1210",
             "firmware_version": "V2.5",
             "role": "Particle Counter I/O"},
            {"type": "remote_io", "vendor": "advantech", "count": 1, "zone": "cleanroom",
             "name": "Cleanroom_TempHumidity_IO",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ADAM-6052",
             "firmware_version": "V2.02",
             "role": "Temp/Humidity I/O"},
            {"type": "field_instrument", "vendor": "endress+hauser", "count": 1, "zone": "cleanroom",
             "name": "Cleanroom_Differential_Pressure",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Room Differential Pressure"},
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "cleanroom",
             "name": "Cleanroom_Monitor_HMI",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIGTO5310",
             "role": "Environmental HMI"},
            {"type": "network_switch", "vendor": "cisco", "count": 1, "zone": "cleanroom",
             "name": "Cleanroom_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # ============================================================
            # BAY 1 LITHOGRAPHY INTRA-BAY — Siemens PROFINET / S7comm
            # ============================================================
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["servo"],
             "source_zones": ["bay_litho"], "target_zones": ["bay_litho"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["bay_litho"], "target_zones": ["bay_litho"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 20,
             "source_types": ["plc"], "target_types": ["vision_sensor"],
             "source_zones": ["bay_litho"], "target_zones": ["bay_litho"],
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["analyzer"],
             "source_zones": ["bay_litho"], "target_zones": ["bay_litho"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            {"protocol": "s7comm", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["bay_litho"], "target_zones": ["bay_litho"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # BAY 2 ETCH INTRA-BAY — Rockwell EtherNet/IP
            # ============================================================
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source_types": ["plc"], "target_types": ["servo"],
             "source_zones": ["bay_etch"], "target_zones": ["bay_etch"],
             "jitter_ms": 0.2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["remote_io"],
             "source_zones": ["bay_etch"], "target_zones": ["bay_etch"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source_types": ["plc"], "target_types": ["vision_system"],
             "source_zones": ["bay_etch"], "target_zones": ["bay_etch"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["analyzer"],
             "source_zones": ["bay_etch"], "target_zones": ["bay_etch"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["bay_etch"], "target_zones": ["bay_etch"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # BAY 3 DEPOSITION INTRA-BAY — Siemens PROFINET / S7comm
            # ============================================================
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["bay_depo"], "target_zones": ["bay_depo"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["bay_depo"], "target_zones": ["bay_depo"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["analyzer"],
             "source_zones": ["bay_depo"], "target_zones": ["bay_depo"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            {"protocol": "s7comm", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["bay_depo"], "target_zones": ["bay_depo"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # BAY 4 CMP INTRA-BAY — Schneider Modbus TCP
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["servo"],
             "source_zones": ["bay_cmp"], "target_zones": ["bay_cmp"],
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["plc"], "target_types": ["flow_sensor", "pressure_sensor"],
             "source_zones": ["bay_cmp"], "target_zones": ["bay_cmp"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["bay_cmp"], "target_zones": ["bay_cmp"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # BAY 5 METROLOGY INTRA-BAY — Rockwell EtherNet/IP + vision
            # ============================================================
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["remote_io"],
             "source_zones": ["bay_metro"], "target_zones": ["bay_metro"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source_types": ["plc"], "target_types": ["vision_system"],
             "source_zones": ["bay_metro"], "target_zones": ["bay_metro"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["bay_metro"], "target_zones": ["bay_metro"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # BAY 6 DIFFUSION INTRA-BAY — Siemens PROFINET / PROFIsafe / S7comm
            # ============================================================
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["bay_diff"], "target_zones": ["bay_diff"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 8,
             "source_types": ["safety_plc"], "target_types": ["io_module"],
             "source_zones": ["bay_diff"], "target_zones": ["bay_diff"]},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["analyzer"],
             "source_zones": ["bay_diff"], "target_zones": ["bay_diff"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            {"protocol": "s7comm", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["bay_diff"], "target_zones": ["bay_diff"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # AMHS INTRA-ZONE — fleet manager dispatch + OHT/AGV cyclic
            # ============================================================
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 100,
             "source_types": ["fleet_manager"], "target_types": ["agv"],
             "source_zones": ["amhs"], "target_zones": ["amhs"],
             "jitter_ms": 10, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["fleet_manager"], "target_types": ["agv"],
             "source_zones": ["amhs"], "target_zones": ["amhs"],
             "jitter_ms": 20, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 250,
             "source_types": ["plc"], "target_types": ["fleet_manager"],
             "source_zones": ["amhs"], "target_zones": ["amhs"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source_types": ["fleet_manager"], "target_types": ["robot_controller"],
             "source_zones": ["amhs"], "target_zones": ["amhs"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # ============================================================
            # CLEANROOM INTRA-ZONE — Schneider Modbus TCP environmental polling
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["remote_io"],
             "source_zones": ["cleanroom"], "target_zones": ["cleanroom"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["field_instrument"],
             "source_zones": ["cleanroom"], "target_zones": ["cleanroom"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["cleanroom"], "target_zones": ["cleanroom"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # ============================================================
            # L3 OPERATIONS → BAY SUPERVISORY FLOWS (northbound only)
            # MES/SCADA, historian, central HMI and EWS all live in Operations.
            # Strict Purdue: no bay initiates northbound, no bay-to-bay lateral.
            # ============================================================
            # OPC UA - SCADA server subscriptions to all bay/zone PLCs (1s)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc", "safety_plc", "fleet_manager"],
             "source_zones": ["operations"],
             "target_zones": ["bay_litho", "bay_etch", "bay_depo", "bay_cmp",
                              "bay_metro", "bay_diff", "amhs", "cleanroom"]},
            # OPC UA - Historian data collection from all bay/zone PLCs (5s)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc", "fleet_manager"],
             "source_zones": ["operations"],
             "target_zones": ["bay_litho", "bay_etch", "bay_depo", "bay_cmp",
                              "bay_metro", "bay_diff", "amhs", "cleanroom"]},
            # OPC UA - Central HMI polling all bay/zone PLCs (1s). The L3 HMI is
            # Siemens; cross-vendor PLCs all support OPC UA, so the supervisory
            # poll is authored as opc_ua to avoid a runtime snap to snmp.
            {"protocol": "opc_ua", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["operations"],
             "target_zones": ["bay_litho", "bay_etch", "bay_depo", "bay_cmp",
                              "bay_metro", "bay_diff", "amhs", "cleanroom"]},

            # ============================================================
            # ENGINEERING WORKSTATION FLOWS (L3 Operations → Bays)
            # Occasional engineering access: program uploads, tag browsing.
            # Low-frequency (30s) to represent non-production activity.
            # ============================================================
            # S7comm - Siemens EWS → Siemens bays (litho/depo/diffusion)
            {"protocol": "s7comm", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["engineering_station"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["operations"],
             "target_zones": ["bay_litho", "bay_depo", "bay_diff"],
             "jitter_ms": 5000, "jitter_type": "uniform"},
            # Modbus TCP - Yokogawa analyzer EWS → analyzers across bays
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["engineering_station"], "target_types": ["analyzer"],
             "source_zones": ["operations"],
             "target_zones": ["bay_litho", "bay_etch", "bay_depo", "bay_diff"],
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP INFRASTRUCTURE MONITORING (L3 → all switches)
            # SCADA polls every bay/zone switch + the core/AMHS switches.
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["network_switch"],
             "source_zones": ["operations"],
             "target_zones": ["operations", "bay_litho", "bay_etch", "bay_depo",
                              "bay_cmp", "bay_metro", "bay_diff", "amhs", "cleanroom"],
             "jitter_ms": 3000, "jitter_type": "uniform"},
        ],
        "total_duration_ms": 600000,
    },
    "ev_battery_cell_plant": {
        "name": "EV Battery Cell Plant — 5-Stage Line",
        "description": "Lithium-ion cell manufacturing line. Five process "
                       "stages each exercising a different OT pattern: "
                       "coating + drying (DCS-flavored continuous web with "
                       "thickness analyzer + defect-vision); calendaring + "
                       "slitting (servo-precision motion); formation + "
                       "aging (16+ charge / discharge cyclers with revenue "
                       "power metering for energy accounting); quality "
                       "(vision + X-ray + hi-pot test); pack assembly "
                       "(robotic cell-to-pack welding + safety SIS). "
                       "Showcases process + cell + power-meter + vision + "
                       "robot patterns in one plant. ~50 devices across "
                       "6 zones.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        "total_duration_ms": 600000,

        # Cells are hermetic at the area-zone boundary; only the L3 Operations
        # zone may reach into a stage (northbound supervisory data + engineering).
        "cell_isolation": {
            "mode": "strict_northbound",
            "applies_to_levels": [0, 1, 2],
        },

        "zones": [
            # Operations / Process Control - Level 3 (SCADA, historian, EWS, central HMI)
            {"id": "operations", "name": "Process Control / Operations", "level": 3,
             "subnet_offset": 5, "vlan": 150, "security_level": "critical"},
            # Stage 1 - Electrode Coating & Drying (Yokogawa DCS continuous web, L0-L2)
            {"id": "stage1_coating", "name": "Stage 1 - Coating & Drying", "level": 2,
             "subnet_offset": 1, "vlan": 211, "security_level": "high"},
            # Stage 2 - Calendaring & Slitting (Rockwell servo-precision motion, L0-L2)
            {"id": "stage2_calender", "name": "Stage 2 - Calendaring & Slitting", "level": 2,
             "subnet_offset": 2, "vlan": 212, "security_level": "high"},
            # Stage 3 - Formation & Aging (Schneider cyclers + revenue power metering, L0-L2)
            {"id": "stage3_formation", "name": "Stage 3 - Formation & Aging", "level": 2,
             "subnet_offset": 3, "vlan": 213, "security_level": "high"},
            # Stage 4 - Quality (vision + X-ray + hi-pot, Siemens, L0-L2)
            {"id": "stage4_quality", "name": "Stage 4 - Quality Inspection", "level": 2,
             "subnet_offset": 4, "vlan": 214, "security_level": "high"},
            # Stage 5 - Pack Assembly (robotic cell-to-pack weld + safety SIS, L0-L2)
            {"id": "stage5_pack", "name": "Stage 5 - Pack Assembly", "level": 2,
             "subnet_offset": 6, "vlan": 215, "security_level": "critical"},
        ],

        "conduits": [
            # Operations <-> Stage 1 (Yokogawa DCS speaks Modbus TCP; OPC UA via SCADA)
            {"id": "ops_stage1_coating", "name": "Operations ↔ Stage 1 Coating",
             "source_zone": "operations", "target_zone": "stage1_coating",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA and Modbus TCP supervisory polling of the "
                            "Yokogawa coating DCS, web-thickness analyzer trends, SNMP infrastructure monitoring"},
            # Operations <-> Stage 2 (Rockwell EtherNet/IP; OPC UA + SNMP supervisory)
            {"id": "ops_stage2_calender", "name": "Operations ↔ Stage 2 Calendaring",
             "source_zone": "operations", "target_zone": "stage2_calender",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "ethernet_ip", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to the Rockwell motion controller, "
                            "engineering workstation EtherNet/IP access, SNMP monitoring"},
            # Operations <-> Stage 3 (Schneider Modbus TCP; OPC UA + SNMP supervisory)
            {"id": "ops_stage3_formation", "name": "Operations ↔ Stage 3 Formation",
             "source_zone": "operations", "target_zone": "stage3_formation",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA + Modbus TCP collection of cycler set-points and "
                            "revenue power-meter energy accounting, SNMP monitoring"},
            # Operations <-> Stage 4 (Siemens S7comm+ / OPC UA; SNMP supervisory)
            {"id": "ops_stage4_quality", "name": "Operations ↔ Stage 4 Quality",
             "source_zone": "operations", "target_zone": "stage4_quality",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "s7comm", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to the Siemens quality PLC, central HMI "
                            "S7comm access to pass/fail results, SNMP monitoring"},
            # Operations <-> Stage 5 (mixed ABB Modbus TCP / Rockwell EtherNet/IP; OPC UA supervisory)
            {"id": "ops_stage5_pack", "name": "Operations ↔ Stage 5 Pack Assembly",
             "source_zone": "operations", "target_zone": "stage5_pack",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "ethernet_ip", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to the ABB pack-line PLC and Rockwell "
                            "safety controller status, central HMI Modbus TCP access, SNMP monitoring"},
            # NOTE: No L0-L2 east/west conduits exist by design. Stages are hermetic at the
            # IEC 62443 area-zone boundary; cell_isolation.mode = strict_northbound drops any
            # stage-to-stage flow added later.
        ],

        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high",
             "rationale": "Tests PIPEDREAM lateral movement against the Purdue-segmented stage model"},
            {"playbook_id": "network_recon", "relevance": "high",
             "rationale": "Strict northbound model tests reconnaissance containment between stages"},
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "manufacturing",
            "description": "Electrode coating + calendaring + formation cycling simulation",
            "key_variables": ["web_speed", "coat_weight", "oven_temp", "calender_gap", "cell_voltage", "cell_temp"],
            "available_faults": ["coat_streak", "web_break", "thermal_runaway", "servo_overload"],
        },

        "devices": [
            # ============================================================
            # OPERATIONS / PROCESS CONTROL (Level 3) — 5 devices
            # All cross-stage supervisory and engineering traffic originates here.
            # ============================================================
            {"type": "scada_server", "vendor": "siemens", "count": 1, "zone": "operations",
             "name": "Ops_Central_SCADA",
             "protocols": ["opc_ua", "s7comm", "modbus_tcp"],
             "fingerprint_model": "WinCC Professional",
             "firmware_version": "V17.0",
             "role": "Central SCADA Server"},
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "operations",
             "name": "Ops_Process_Historian",
             "protocols": ["opc_ua", "modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian"},
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "operations",
             "name": "Ops_Overview_HMI",
             "protocols": ["s7comm", "opc_ua"],
             "fingerprint_model": "WinCC Unified",
             "role": "Central Overview HMI"},
            {"type": "engineering_workstation", "vendor": "microsoft", "count": 1, "zone": "operations",
             "name": "Ops_Engineering_Workstation",
             "protocols": ["rdp", "https", "snmp"],
             "fingerprint_model": "Jump Server 2019",
             "role": "OT Engineering Workstation"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "operations",
             "name": "Ops_Core_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-9320-24P4X-E",
             "firmware_version": "17.9.3",
             "role": "Core Network Switch"},

            # ============================================================
            # STAGE 1: ELECTRODE COATING & DRYING — Yokogawa DCS continuous web (9 devices)
            # Modbus TCP polling throughout (CENTUM VP / analyzers / sensors) +
            # Cognex defect-vision (ethernet_ip) for coating-defect detection.
            # ============================================================
            {"type": "dcs_controller", "vendor": "yokogawa", "count": 1, "zone": "stage1_coating",
             "name": "Coating_DCS_Controller",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "AFV10D",
             "firmware_version": "R6.06",
             "role": "DCS Field Control Unit"},
            {"type": "hmi", "vendor": "yokogawa", "count": 1, "zone": "stage1_coating",
             "name": "Coating_Operator_HMI",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "HIS",
             "role": "Operator Interface"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "stage1_coating",
             "name": "Coating_Thickness_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "Web Thickness Analyzer"},
            {"type": "vision_system", "vendor": "cognex", "count": 2, "zone": "stage1_coating",
             "name": "Coating_Defect_Vision",
             "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Coating Defect Vision"},
            {"type": "sensor", "vendor": "endress+hauser", "count": 1, "zone": "stage1_coating",
             "name": "Coating_Slurry_Pressure",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PMC71",
             "role": "Slurry Pressure Transmitter"},
            {"type": "sensor", "vendor": "endress+hauser", "count": 1, "zone": "stage1_coating",
             "name": "Coating_Solvent_Flow",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Solvent Flow Meter"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "stage1_coating",
             "name": "Coating_Web_Drive",
             "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1PE21-1UL0",
             "role": "Web Transport Drive"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "stage1_coating",
             "name": "Coating_Stage_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Industrial Switch"},

            # ============================================================
            # STAGE 2: CALENDARING & SLITTING — Rockwell servo-precision motion (8 devices)
            # EtherNet/IP implicit I/O + CIP Motion. Tight servo loops on the
            # calender rolls and slitter knives.
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "stage2_calender",
             "name": "Calender_Line_PLC",
             "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua", "snmp"],
             "fingerprint_model": "1756-L73",
             "firmware_version": "V33.011",
             "role": "Line Controller"},
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "stage2_calender",
             "name": "Calender_Operator_HMI",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},
            {"type": "servo", "vendor": "rockwell", "count": 3, "zone": "stage2_calender",
             "name": "Calender_Roll_Servo",
             "protocols": ["ethernet_ip", "cip_motion"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Calender Roll Servo"},
            {"type": "servo", "vendor": "rockwell", "count": 2, "zone": "stage2_calender",
             "name": "Slitter_Knife_Servo",
             "protocols": ["ethernet_ip", "cip_motion"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Slitter Knife Servo"},
            {"type": "vision_sensor", "vendor": "sick", "count": 1, "zone": "stage2_calender",
             "name": "Slitter_Edge_Vision",
             "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "Inspector P631",
             "role": "Slit Edge Inspection"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "stage2_calender",
             "name": "Calender_Station_IO",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "stage2_calender",
             "name": "Calender_Stage_Switch",
             "protocols": ["snmp", "ethernet_ip"],
             "fingerprint_model": "IE-9320-24T4X-E",
             "role": "Industrial Switch"},

            # ============================================================
            # STAGE 3: FORMATION & AGING — Schneider cyclers + revenue power metering (11 devices)
            # Modbus TCP polling. Banks of charge/discharge cyclers (modeled as
            # drives) with revenue-grade power metering for energy accounting.
            # ============================================================
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "stage3_formation",
             "name": "Formation_Process_PLC",
             "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "BMXP3420302",
             "firmware_version": "V3.10",
             "role": "Process Controller"},
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "stage3_formation",
             "name": "Formation_Operator_HMI",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIGTO5310",
             "role": "Operator Interface"},
            {"type": "drive", "vendor": "schneider", "count": 6, "zone": "stage3_formation",
             "name": "Formation_Cycler",
             "protocols": ["modbus_tcp", "ethernet_ip", "profinet"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Charge/Discharge Cycler"},
            {"type": "power_meter", "vendor": "schneider", "count": 2, "zone": "stage3_formation",
             "name": "Formation_Revenue_Meter",
             "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "ION9000",
             "role": "Revenue Power Meter"},
            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "stage3_formation",
             "name": "Formation_Bank_IO",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "role": "Remote I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "stage3_formation",
             "name": "Formation_Stage_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Industrial Switch"},

            # ============================================================
            # STAGE 4: QUALITY INSPECTION — Siemens + vision/X-ray/hi-pot (9 devices)
            # PROFINET RT + S7comm. Cognex vision + SICK barcode + hi-pot test
            # station feeding a Siemens quality PLC.
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "stage4_quality",
             "name": "Quality_Cell_PLC",
             "protocols": ["profinet", "s7comm", "opc_ua"],
             "fingerprint_model": "6ES7 516-3AN02-0AB0",
             "firmware_version": "V2.9.2",
             "role": "Cell Controller"},
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "stage4_quality",
             "name": "Quality_Operator_HMI",
             "protocols": ["profinet", "s7comm"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "role": "Operator Interface"},
            {"type": "vision_system", "vendor": "cognex", "count": 2, "zone": "stage4_quality",
             "name": "Quality_Cap_Vision",
             "protocols": ["ethernet_ip", "profinet", "modbus_tcp"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Cell Cap Inspection Vision"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "stage4_quality",
             "name": "Quality_Traceability_Scanner",
             "protocols": ["ethernet_ip", "profinet", "modbus_tcp"],
             "fingerprint_model": "CLV650-0120",
             "role": "Cell Traceability Scanner"},
            {"type": "sensor", "vendor": "endress+hauser", "count": 1, "zone": "stage4_quality",
             "name": "Quality_HiPot_Sense",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Hi-Pot Test Sensing"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "stage4_quality",
             "name": "Quality_Station_IO",
             "protocols": ["profinet"],
             "fingerprint_model": "6ES7155-6AU01-0BN0",
             "role": "Distributed I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "stage4_quality",
             "name": "Quality_Stage_Switch",
             "protocols": ["snmp", "profinet"],
             "fingerprint_model": "IE-3500-8T3S-E",
             "role": "Industrial Switch"},

            # ============================================================
            # STAGE 5: PACK ASSEMBLY — robotic cell-to-pack weld + safety SIS (10 devices)
            # ABB process control (Modbus TCP) + KUKA / Fanuc weld robots
            # (EtherNet/IP) + Rockwell GuardLogix safety SIS over CIP Safety.
            # ============================================================
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "stage5_pack",
             "name": "Pack_Line_PLC",
             "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "PM590-ETH",
             "firmware_version": "V2.9.0",
             "role": "Line Controller"},
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "stage5_pack",
             "name": "Pack_Safety_Controller",
             "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "role": "Safety Controller (SIS)"},
            {"type": "robot_controller", "vendor": "kuka", "count": 2, "zone": "stage5_pack",
             "name": "Pack_Weld_Robot",
             "protocols": ["ethernet_ip", "profinet"],
             "fingerprint_model": "KR C4",
             "firmware_version": "V8.3.5",
             "role": "Cell-to-Pack Weld Robot"},
            {"type": "robot_controller", "vendor": "fanuc", "count": 1, "zone": "stage5_pack",
             "name": "Pack_Handling_Robot",
             "protocols": ["fanuc", "ethernet_ip"],
             "fingerprint_model": "R-30iB Plus",
             "firmware_version": "V9.30",
             "role": "Pack Handling Robot"},
            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "stage5_pack",
             "name": "Pack_Operator_HMI",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Operator Interface"},
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "stage5_pack",
             "name": "Pack_Conveyor_VFD",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Variable Frequency Drive"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "stage5_pack",
             "name": "Pack_Safety_IO",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Safety Remote I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "stage5_pack",
             "name": "Pack_Stage_Switch",
             "protocols": ["snmp", "ethernet_ip"],
             "fingerprint_model": "IE-9320-24P4X-E",
             "role": "Industrial Switch"},
        ],

        "flows": [
            # ============================================================
            # STAGE 1 INTRA-CELL — Yokogawa DCS Modbus TCP + Cognex EtherNet/IP
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["dcs_controller"], "target_types": ["drive"],
             "source_zones": ["stage1_coating"], "target_zones": ["stage1_coating"],
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["dcs_controller"], "target_types": ["analyzer"],
             "source_zones": ["stage1_coating"], "target_zones": ["stage1_coating"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["sensor"],
             "source_zones": ["stage1_coating"], "target_zones": ["stage1_coating"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 50,
             "source_types": ["dcs_controller"], "target_types": ["vision_system"],
             "source_zones": ["stage1_coating"], "target_zones": ["stage1_coating"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["stage1_coating"], "target_zones": ["stage1_coating"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # STAGE 2 INTRA-CELL — Rockwell EtherNet/IP + CIP Motion
            # ============================================================
            {"protocol": "cip_motion", "pattern": "cyclic_io", "interval_ms": 2,
             "source_types": ["plc"], "target_types": ["servo"],
             "source_zones": ["stage2_calender"], "target_zones": ["stage2_calender"],
             "jitter_ms": 0.2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["stage2_calender"], "target_zones": ["stage2_calender"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 50,
             "source_types": ["plc"], "target_types": ["vision_sensor"],
             "source_zones": ["stage2_calender"], "target_zones": ["stage2_calender"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["stage2_calender"], "target_zones": ["stage2_calender"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # STAGE 3 INTRA-CELL — Schneider Modbus TCP cyclers + metering
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["stage3_formation"], "target_zones": ["stage3_formation"],
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["power_meter"],
             "source_zones": ["stage3_formation"], "target_zones": ["stage3_formation"],
             "jitter_ms": 75, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["stage3_formation"], "target_zones": ["stage3_formation"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["stage3_formation"], "target_zones": ["stage3_formation"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # STAGE 4 INTRA-CELL — Siemens PROFINET + S7comm + vision
            # ============================================================
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["stage4_quality"], "target_zones": ["stage4_quality"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 50,
             "source_types": ["plc"], "target_types": ["vision_system"],
             "source_zones": ["stage4_quality"], "target_zones": ["stage4_quality"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["barcode_scanner"],
             "source_zones": ["stage4_quality"], "target_zones": ["stage4_quality"],
             "jitter_ms": 20, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["stage4_quality"], "target_zones": ["stage4_quality"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "s7comm", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["stage4_quality"], "target_zones": ["stage4_quality"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # STAGE 5 INTRA-CELL — ABB Modbus TCP + robot EtherNet/IP + CIP Safety
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["stage5_pack"], "target_zones": ["stage5_pack"],
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["robot_controller"],
             "source_zones": ["stage5_pack"], "target_zones": ["stage5_pack"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["io_module"],
             "source_zones": ["stage5_pack"], "target_zones": ["stage5_pack"]},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["stage5_pack"], "target_zones": ["stage5_pack"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # L3 OPERATIONS → STAGE SUPERVISORY FLOWS (northbound only)
            # SCADA, historian, central HMI live in Operations. Strict Purdue:
            # no stage initiates northbound, no stage-to-stage lateral.
            # ============================================================
            # OPC UA - SCADA subscriptions to the OPC-UA stage controllers (1s).
            # Stage 1 is excluded here: the Yokogawa CENTUM VP DCS exposes data
            # northbound over Modbus TCP only (it speaks no OPC UA), so Stage 1 is
            # collected via the dedicated Modbus TCP flow below.
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"],
             "target_types": ["plc", "safety_plc"],
             "source_zones": ["operations"],
             "target_zones": ["stage2_calender", "stage3_formation",
                              "stage4_quality", "stage5_pack"]},
            # OPC UA - Historian collection from the OPC-UA stage controllers (5s).
            # Stage 1 excluded for the same reason (Yokogawa DCS is Modbus TCP only).
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"],
             "target_types": ["plc"],
             "source_zones": ["operations"],
             "target_zones": ["stage2_calender", "stage3_formation",
                              "stage4_quality", "stage5_pack"]},
            # Modbus TCP - SCADA + Historian northbound collection of the Yokogawa
            # coating DCS (Stage 1), which speaks Modbus TCP only (2s).
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["scada_server", "historian"],
             "target_types": ["dcs_controller"],
             "source_zones": ["operations"], "target_zones": ["stage1_coating"],
             "jitter_ms": 150, "jitter_type": "gaussian"},
            # Modbus TCP - SCADA energy accounting poll of revenue meters (Stage 3) (2s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["scada_server"], "target_types": ["power_meter"],
             "source_zones": ["operations"], "target_zones": ["stage3_formation"],
             "jitter_ms": 150, "jitter_type": "gaussian"},
            # S7comm - Central Siemens HMI polling the Siemens quality PLC (Stage 4) (1s)
            {"protocol": "s7comm", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["operations"], "target_zones": ["stage4_quality"]},
            # OPC UA - Central HMI polling cross-vendor stage controllers (1s).
            # The L3 HMI is Siemens; cross-vendor controllers (Rockwell/Schneider/
            # ABB/Yokogawa) share opc_ua only where present, else SCADA covers them.
            {"protocol": "opc_ua", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["operations"],
             "target_zones": ["stage2_calender", "stage3_formation", "stage5_pack"]},
        ],
    },
    "pharma_vaccine_bioreactor": {
        "name": "Pharma — Vaccine Bioreactor Plant",
        "description": "GMP-regulated vaccine / monoclonal-antibody plant. "
                       "Three bioreactor trains with dense analyzer "
                       "instrumentation (pH / DO / OD / glucose / lactate / "
                       "off-gas — 6-10 analyzers per train). Tangential "
                       "flow filtration + chromatography in purification, "
                       "aseptic vial filling + lyophilization + automated "
                       "vision inspection in fill / finish, dedicated "
                       "SIL-3 SIS for over-pressure / over-temp shutdown, "
                       "clean utilities (WFI / clean steam / compressed "
                       "air). Heavy historian + asset management + alarm "
                       "server traffic for 21 CFR Part 11 audit trail. "
                       "~115 devices across 9 zones.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        "total_duration_ms": 600000,

        # Strict Purdue: cells are hermetic at L0-L2; only declared vertical
        # conduits to L3 operations are permitted. The studio UI can relax this.
        "cell_isolation": {
            "mode": "strict_northbound",
            "applies_to_levels": [0, 1, 2],
        },

        "zones": [
            # ---- Level 3: Operations / Process Control --------------------
            {"id": "operations", "name": "Plant Operations / Process Control", "level": 3,
             "subnet_offset": 5, "vlan": 150, "security_level": "critical"},
            # ---- Level 2: Bioreactor Trains (each a self-contained DCS cell)
            {"id": "train_a", "name": "Bioreactor Train A", "level": 2,
             "subnet_offset": 1, "vlan": 211, "security_level": "high"},
            {"id": "train_b", "name": "Bioreactor Train B", "level": 2,
             "subnet_offset": 2, "vlan": 212, "security_level": "high"},
            {"id": "train_c", "name": "Bioreactor Train C", "level": 2,
             "subnet_offset": 3, "vlan": 213, "security_level": "high"},
            # ---- Level 2: Downstream Purification (TFF + chromatography) ---
            {"id": "purification", "name": "Purification (TFF + Chromatography)", "level": 2,
             "subnet_offset": 4, "vlan": 220, "security_level": "high"},
            # ---- Level 2: Fill / Finish (filling + lyo + vision) ----------
            {"id": "fill_finish", "name": "Aseptic Fill / Finish", "level": 2,
             "subnet_offset": 6, "vlan": 230, "security_level": "high"},
            # ---- Level 2: Safety Instrumented System (SIL-3) --------------
            {"id": "sis", "name": "Safety Instrumented System (SIL-3)", "level": 2,
             "subnet_offset": 7, "vlan": 240, "security_level": "critical"},
            # ---- Level 2: Clean Utilities (WFI / clean steam / air) -------
            {"id": "utilities", "name": "Clean Utilities (WFI / Steam / Air)", "level": 2,
             "subnet_offset": 8, "vlan": 250, "security_level": "high"},
        ],

        "conduits": [
            # Every cross-zone flow pair below is L3 operations <-> a cell.
            {"id": "ops_train_a", "name": "Operations ↔ Bioreactor Train A",
             "source_zone": "operations", "target_zone": "train_a",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/historian OPC UA + Modbus collection from Train A DCS, "
                            "PI asset-management polling, engineering access, SNMP monitoring"},
            {"id": "ops_train_b", "name": "Operations ↔ Bioreactor Train B",
             "source_zone": "operations", "target_zone": "train_b",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/historian OPC UA + Modbus collection from Train B DCS, "
                            "PI asset-management polling, engineering access, SNMP monitoring"},
            {"id": "ops_train_c", "name": "Operations ↔ Bioreactor Train C",
             "source_zone": "operations", "target_zone": "train_c",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/historian OPC UA + Modbus collection from Train C DCS, "
                            "PI asset-management polling, engineering access, SNMP monitoring"},
            {"id": "ops_purification", "name": "Operations ↔ Purification",
             "source_zone": "operations", "target_zone": "purification",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/historian OPC UA + Modbus collection from the TFF/"
                            "chromatography PLC, engineering access, SNMP monitoring"},
            {"id": "ops_fill_finish", "name": "Operations ↔ Aseptic Fill / Finish",
             "source_zone": "operations", "target_zone": "fill_finish",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "ethernet_ip", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/historian OPC UA subscriptions to the Rockwell fill/"
                            "finish line, Modbus engineering access, SNMP monitoring"},
            {"id": "ops_sis", "name": "Operations ↔ Safety Instrumented System",
             "source_zone": "operations", "target_zone": "sis",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "Read-only SIS state collection to the historian and alarm "
                            "server; SNMP health monitoring. No write path."},
            {"id": "ops_utilities", "name": "Operations ↔ Clean Utilities",
             "source_zone": "operations", "target_zone": "utilities",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/historian OPC UA + Modbus collection from the clean-"
                            "utilities controller, engineering access, SNMP monitoring"},
        ],

        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high",
             "rationale": "Tests PIPEDREAM lateral movement against strict Purdue segmentation in a regulated plant"},
            {"playbook_id": "triton_like", "relevance": "high",
             "rationale": "Dedicated SIL-3 SIS is a TRITON-style safety-system target"},
            {"playbook_id": "network_recon", "relevance": "medium",
             "rationale": "Validates reconnaissance containment across the L3<->cell conduits"},
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "manufacturing",
            "description": "Bioreactor batch process simulation (fed-batch growth + downstream purification)",
            "key_variables": ["ph", "dissolved_oxygen", "optical_density", "glucose", "lactate", "agitation_rpm"],
            "available_faults": ["foaming_event", "do_crash", "feed_pump_failure", "sis_overpressure_trip"],
        },

        "devices": [
            # =====================================================================
            # OPERATIONS / PROCESS CONTROL (Level 3) — 6 devices
            # All northbound collection, asset-management, alarm/audit, and
            # engineering access originate here.
            # =====================================================================
            {"type": "scada_server", "vendor": "honeywell", "count": 1, "zone": "operations",
             "name": "Plant_Central_SCADA",
             "protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "fingerprint_model": "Experion Server",
             "firmware_version": "R520.2",
             "role": "Central SCADA Server"},
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "operations",
             "name": "Process_Historian",
             "protocols": ["opc_ua", "modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian (21 CFR Part 11 audit trail)"},
            {"type": "server", "vendor": "aveva", "count": 1, "zone": "operations",
             "name": "PI_Asset_Management_Server",
             "protocols": ["opc_ua", "snmp", "https"],
             "fingerprint_model": "OSIsoft PI Server 2018",
             "role": "Asset Management / PI Data Archive"},
            {"type": "server", "vendor": "aveva", "count": 1, "zone": "operations",
             "name": "Alarm_Audit_Server",
             "protocols": ["opc_ua", "snmp", "https"],
             "fingerprint_model": "InTouch Alarm Server 2023",
             "role": "Alarm + 21 CFR Part 11 Audit Server"},
            {"type": "engineering_workstation", "vendor": "schneider", "count": 1, "zone": "operations",
             "name": "OT_Engineering_Workstation",
             "protocols": ["modbus_tcp", "opc_ua", "snmp"],
             "fingerprint_model": "EcoStruxure Control Expert 16",
             "role": "OT Engineering Workstation"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "operations",
             "name": "Ops_Core_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-9320-24P4X-E",
             "firmware_version": "17.9.3",
             "role": "Core Network Switch"},

            # =====================================================================
            # BIOREACTOR TRAIN A (Level 2) — Yokogawa CENTUM VP DCS + analyzer skid
            # 9 devices. Dense Modbus analyzer instrumentation.
            # =====================================================================
            {"type": "dcs_controller", "vendor": "yokogawa", "count": 1, "zone": "train_a",
             "name": "Train_A_DCS_Controller",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "AFV10D",
             "firmware_version": "R6.06",
             "role": "Bioreactor DCS Field Control Unit"},
            {"type": "hmi", "vendor": "yokogawa", "count": 1, "zone": "train_a",
             "name": "Train_A_Operator_HIS",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "HIS",
             "role": "Operator Human Interface Station"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "train_a",
             "name": "Train_A_pH_DO_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "pH / DO Multi-Parameter Analyzer"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "train_a",
             "name": "Train_A_OffGas_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "TDLS8000",
             "role": "Off-Gas Laser Analyzer (CO2/O2)"},
            {"type": "analyzer", "vendor": "endress+hauser", "count": 1, "zone": "train_a",
             "name": "Train_A_Glucose_Lactate_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "CM442",
             "role": "Glucose / Lactate Liquiline Analyzer"},
            {"type": "transmitter", "vendor": "emerson", "count": 1, "zone": "train_a",
             "name": "Train_A_Pressure_Transmitter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "3051S",
             "role": "Bioreactor Head-Pressure Transmitter"},
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "train_a",
             "name": "Train_A_Agitator_Drive",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS880-01",
             "firmware_version": "V2.40",
             "role": "Agitator Variable Frequency Drive"},
            {"type": "flow_meter", "vendor": "emerson", "count": 1, "zone": "train_a",
             "name": "Train_A_Feed_Flow_Meter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "5700",
             "role": "Coriolis Feed Flow Meter"},

            # =====================================================================
            # BIOREACTOR TRAIN B (Level 2) — Emerson DeltaV DCS + analyzer skid
            # 9 devices.
            # =====================================================================
            {"type": "dcs_controller", "vendor": "emerson", "count": 1, "zone": "train_b",
             "name": "Train_B_DCS_Controller",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "S-series",
             "firmware_version": "V14.3",
             "role": "Bioreactor DeltaV S-series Controller"},
            {"type": "hmi", "vendor": "emerson", "count": 1, "zone": "train_b",
             "name": "Train_B_Operator_Workstation",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "OWS",
             "role": "Operator Workstation"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "train_b",
             "name": "Train_B_pH_DO_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "pH / DO Multi-Parameter Analyzer"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "train_b",
             "name": "Train_B_OffGas_GC",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "GC8000",
             "role": "Off-Gas Gas Chromatograph"},
            {"type": "analyzer", "vendor": "endress+hauser", "count": 1, "zone": "train_b",
             "name": "Train_B_Glucose_Lactate_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "CM442",
             "role": "Glucose / Lactate Liquiline Analyzer"},
            {"type": "instrument", "vendor": "honeywell", "count": 1, "zone": "train_b",
             "name": "Train_B_OD_Probe_Controller",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "UDA2182",
             "role": "Optical Density Probe Controller"},
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "train_b",
             "name": "Train_B_Agitator_Drive",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS880-01",
             "role": "Agitator Variable Frequency Drive"},
            {"type": "pressure_sensor", "vendor": "endress+hauser", "count": 1, "zone": "train_b",
             "name": "Train_B_Head_Pressure_Sensor",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PMC71",
             "role": "Cerabar Head-Pressure Transmitter"},

            # =====================================================================
            # BIOREACTOR TRAIN C (Level 2) — Siemens PCS DCS surrogate + analyzers
            # 9 devices. Siemens S7/PROFINET train.
            # =====================================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "train_c",
             "name": "Train_C_Process_Controller",
             "protocols": ["profinet", "s7comm", "opc_ua"],
             "fingerprint_model": "6ES7 516-3AN02-0AB0",
             "firmware_version": "V2.8.1",
             "role": "Bioreactor Process Controller"},
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "train_c",
             "name": "Train_C_Operator_HMI",
             "protocols": ["profinet", "s7comm", "opc_ua"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "role": "Operator Interface (TP1200 Comfort)"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "train_c",
             "name": "Train_C_pH_DO_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "pH / DO Multi-Parameter Analyzer"},
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "train_c",
             "name": "Train_C_OffGas_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "TDLS8000",
             "role": "Off-Gas Laser Analyzer (CO2/O2)"},
            {"type": "analyzer", "vendor": "endress+hauser", "count": 1, "zone": "train_c",
             "name": "Train_C_Glucose_Lactate_Analyzer",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "CM442",
             "role": "Glucose / Lactate Liquiline Analyzer"},
            {"type": "instrument", "vendor": "honeywell", "count": 1, "zone": "train_c",
             "name": "Train_C_Temp_Controller",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "UDC3500",
             "role": "Jacket Temperature Controller"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "train_c",
             "name": "Train_C_Agitator_Drive",
             "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "G120",
             "firmware_version": "V4.7 SP5",
             "role": "Agitator Variable Frequency Drive"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "train_c",
             "name": "Train_C_Skid_IO",
             "protocols": ["profinet"],
             "fingerprint_model": "6ES7155-6AU01-0BN0",
             "role": "ET 200SP Distributed I/O"},

            # =====================================================================
            # PURIFICATION — TFF + CHROMATOGRAPHY (Level 2) — Schneider Modbus
            # 8 devices.
            # =====================================================================
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "purification",
             "name": "Purification_Skid_PLC",
             "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "BMXP3420302",
             "firmware_version": "V2.90",
             "role": "TFF / Chromatography Skid PLC"},
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "purification",
             "name": "Purification_Operator_HMI",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "Operator Interface (Magelis STM6)"},
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "purification",
             "name": "TFF_Feed_Pump_Drive",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ATV630D15N4",
             "firmware_version": "V1.6IE42",
             "role": "TFF Feed Pump Drive"},
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "purification",
             "name": "Chromatography_Pump_Drive",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ATV930",
             "role": "Chromatography Buffer Pump Drive"},
            {"type": "flow_meter", "vendor": "endress+hauser", "count": 1, "zone": "purification",
             "name": "TFF_Permeate_Flow_Meter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Permeate Flow Meter"},
            {"type": "pressure_sensor", "vendor": "endress+hauser", "count": 1, "zone": "purification",
             "name": "TFF_TMP_Pressure_Sensor",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PMC71",
             "role": "Trans-Membrane Pressure Transmitter"},
            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "purification",
             "name": "Purification_Valve_IO",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "STB NIP 2311",
             "role": "Advantys STB Valve I/O"},

            # =====================================================================
            # ASEPTIC FILL / FINISH (Level 2) — Rockwell EtherNet/IP line
            # 8 devices. Filling + lyophilization + vision inspection.
            # =====================================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "fill_finish",
             "name": "Fill_Line_PLC",
             "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L83E",
             "firmware_version": "V32.011",
             "role": "Aseptic Fill Line Controller"},
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "fill_finish",
             "name": "Fill_Line_HMI",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T15C22D9P",
             "firmware_version": "V10.00",
             "role": "Operator Interface (PanelView Plus 7)"},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "fill_finish",
             "name": "Lyophilizer_PLC",
             "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L33ER",
             "role": "Lyophilization Cycle Controller"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "fill_finish",
             "name": "Vial_Conveyor_Drive",
             "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "PowerFlex 753",
             "role": "Vial Conveyor Drive"},
            {"type": "robot_controller", "vendor": "fanuc", "count": 1, "zone": "fill_finish",
             "name": "Vial_Handling_Robot",
             "protocols": ["ethernet_ip", "fanuc"],
             "fingerprint_model": "R-30iB Plus",
             "firmware_version": "V9.30",
             "role": "Aseptic Vial Handling Robot"},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "fill_finish",
             "name": "Automated_Vision_Inspection",
             "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Automated Fill Vision Inspection"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "fill_finish",
             "name": "Fill_Finish_Remote_IO",
             "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "FLEX 5000 Remote I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "fill_finish",
             "name": "Fill_Finish_Cell_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "firmware_version": "15.2(7)E6",
             "role": "Industrial Switch"},

            # =====================================================================
            # SAFETY INSTRUMENTED SYSTEM — SIL-3 (Level 2) — Honeywell/Yokogawa
            # 4 devices. Over-pressure / over-temp shutdown. Read-only northbound.
            # =====================================================================
            {"type": "safety_plc", "vendor": "honeywell", "count": 1, "zone": "sis",
             "name": "SIS_Safety_Manager",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Safety Manager",
             "firmware_version": "V12.5",
             "role": "SIL-3 Safety Manager (over-pressure/temp trip)"},
            {"type": "safety_plc", "vendor": "yokogawa", "count": 1, "zone": "sis",
             "name": "SIS_ProSafe_Controller",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "SSC60D",
             "role": "ProSafe-RS Safety Controller"},
            {"type": "transmitter", "vendor": "yokogawa", "count": 1, "zone": "sis",
             "name": "SIS_Pressure_Transmitter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "EJA530A",
             "role": "SIL-rated Pressure Transmitter"},
            {"type": "instrument", "vendor": "honeywell", "count": 1, "zone": "sis",
             "name": "SIS_Temperature_Transmitter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "SIL-rated Temperature Transmitter"},

            # =====================================================================
            # CLEAN UTILITIES — WFI / CLEAN STEAM / COMPRESSED AIR (Level 2)
            # 7 devices. ABB AC500 controller + instruments.
            # =====================================================================
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "utilities",
             "name": "Clean_Utilities_PLC",
             "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "PM590-ETH",
             "firmware_version": "V2.9.0",
             "role": "Clean Utilities Controller"},
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "utilities",
             "name": "WFI_Distribution_Pump_Drive",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "WFI Distribution Pump Drive"},
            {"type": "flow_meter", "vendor": "endress+hauser", "count": 1, "zone": "utilities",
             "name": "WFI_Loop_Flow_Meter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "WFI Loop Flow Meter"},
            {"type": "instrument", "vendor": "honeywell", "count": 1, "zone": "utilities",
             "name": "Clean_Steam_Controller",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Clean Steam Loop Controller"},
            {"type": "transmitter", "vendor": "emerson", "count": 1, "zone": "utilities",
             "name": "Compressed_Air_Pressure_Transmitter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "3051S",
             "role": "Compressed Air Header Pressure Transmitter"},
            {"type": "io_module", "vendor": "abb", "count": 1, "zone": "utilities",
             "name": "Utilities_Remote_IO",
             "protocols": ["modbus_tcp", "ethernet_ip", "profinet"],
             "fingerprint_model": "CI501",
             "role": "CI501 Remote I/O"},
        ],

        "flows": [
            # =====================================================================
            # TRAIN A INTRA-CELL — Yokogawa Modbus DCS
            # =====================================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["analyzer"],
             "source_zones": ["train_a"], "target_zones": ["train_a"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["transmitter", "flow_meter"],
             "source_zones": ["train_a"], "target_zones": ["train_a"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["dcs_controller"], "target_types": ["drive"],
             "source_zones": ["train_a"], "target_zones": ["train_a"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["train_a"], "target_zones": ["train_a"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # =====================================================================
            # TRAIN B INTRA-CELL — Emerson DeltaV Modbus DCS
            # =====================================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["analyzer", "instrument"],
             "source_zones": ["train_b"], "target_zones": ["train_b"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["pressure_sensor"],
             "source_zones": ["train_b"], "target_zones": ["train_b"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["dcs_controller"], "target_types": ["drive"],
             "source_zones": ["train_b"], "target_zones": ["train_b"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["train_b"], "target_zones": ["train_b"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # =====================================================================
            # TRAIN C INTRA-CELL — Siemens PROFINET / S7comm + Modbus analyzers
            # =====================================================================
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "source_zones": ["train_c"], "target_zones": ["train_c"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["analyzer", "instrument", "flow_meter"],
             "source_zones": ["train_c"], "target_zones": ["train_c"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            {"protocol": "s7comm", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["train_c"], "target_zones": ["train_c"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # =====================================================================
            # PURIFICATION INTRA-CELL — Schneider Modbus TCP
            # =====================================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["purification"], "target_zones": ["purification"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["flow_meter", "pressure_sensor", "io_module"],
             "source_zones": ["purification"], "target_zones": ["purification"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["purification"], "target_zones": ["purification"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # =====================================================================
            # FILL / FINISH INTRA-CELL — Rockwell EtherNet/IP
            # =====================================================================
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "source_zones": ["fill_finish"], "target_zones": ["fill_finish"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["robot_controller", "vision_system"],
             "source_zones": ["fill_finish"], "target_zones": ["fill_finish"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["fill_finish"], "target_zones": ["fill_finish"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # =====================================================================
            # SIS INTRA-CELL — Honeywell/Yokogawa Modbus safety heartbeat
            # =====================================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["safety_plc"], "target_types": ["transmitter", "instrument"],
             "source_zones": ["sis"], "target_zones": ["sis"],
             "jitter_ms": 20, "jitter_type": "gaussian"},

            # =====================================================================
            # UTILITIES INTRA-CELL — ABB Modbus / EtherNet/IP
            # =====================================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["utilities"], "target_zones": ["utilities"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["flow_meter", "instrument", "transmitter", "io_module"],
             "source_zones": ["utilities"], "target_zones": ["utilities"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # =====================================================================
            # L3 OPERATIONS → CELL SUPERVISORY FLOWS (northbound, vertical only)
            # SCADA, historian, PI asset-mgmt, alarm/audit server, and engineering
            # workstation all live in operations. No cell-to-cell lateral flows.
            # =====================================================================
            # SCADA OPC UA subscriptions to OPC-UA-capable cell controllers (Siemens/
            # Schneider/ABB/Rockwell). Yokogawa/Emerson Modbus trains collected below.
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "source_zones": ["operations"],
             "target_zones": ["train_c", "purification", "fill_finish", "utilities"]},
            # SCADA Modbus collection from the Yokogawa/Emerson Modbus-only DCS trains.
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["scada_server"], "target_types": ["dcs_controller"],
             "source_zones": ["operations"],
             "target_zones": ["train_a", "train_b"],
             "jitter_ms": 200, "jitter_type": "uniform"},
            # Historian OPC UA collection from OPC-UA controllers (5s).
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["operations"],
             "target_zones": ["train_c", "purification", "fill_finish", "utilities"]},
            # Historian Modbus collection from the Modbus DCS trains (5s).
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["dcs_controller"],
             "source_zones": ["operations"],
             "target_zones": ["train_a", "train_b"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # PI asset-management OPC UA polling of OPC-UA controllers (10s).
            {"protocol": "opc_ua", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["server"], "target_types": ["plc"],
             "source_zones": ["operations"],
             "target_zones": ["train_c", "purification", "fill_finish", "utilities"],
             "jitter_ms": 1000, "jitter_type": "uniform"},
            # Historian read-only Modbus collection of SIS state (no write path).
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["safety_plc"],
             "source_zones": ["operations"], "target_zones": ["sis"],
             "jitter_ms": 500, "jitter_type": "uniform"},

            # ---------------------------------------------------------------------
            # ENGINEERING WORKSTATION FLOWS (L3 operations → cells)
            # Low-frequency engineering access: program checks / tag browsing.
            # ---------------------------------------------------------------------
            # Modbus engineering access (Control Expert station speaks modbus_tcp;
            # every cell controller — Yokogawa/Emerson DCS, Schneider/ABB/Siemens/
            # Rockwell PLCs — exposes a Modbus engineering server).
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["engineering_workstation"], "target_types": ["dcs_controller", "plc"],
             "source_zones": ["operations"],
             "target_zones": ["train_a", "train_b", "train_c", "purification", "fill_finish", "utilities"],
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # ---------------------------------------------------------------------
            # SNMP INFRASTRUCTURE MONITORING (L3 operations → cell switches)
            # ---------------------------------------------------------------------
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["operations"], "target_zones": ["fill_finish"],
             "jitter_ms": 3000, "jitter_type": "uniform"},
            # Intra-operations SNMP health poll of the core switch (so no L3 device
            # is left without a flow for CV fingerprinting).
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["operations"], "target_zones": ["operations"],
             "jitter_ms": 3000, "jitter_type": "uniform"},
        ],
    },
}
