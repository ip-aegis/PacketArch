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
        "description": "CNC machining and assembly cell with Siemens S7-1500 PLCs, SINAMICS drives, "
                       "and distributed I/O. Features S7-1500F safety PLCs with PROFIsafe for machine "
                       "guarding. Typical cell-level manufacturing with fast PROFINET cyclic I/O and "
                       "S7comm+ HMI connectivity. 35 devices across control, cell, and field zones.",
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
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Assembly_Line_Main_PLC", "protocols": ["profinet", "s7comm_plus", "snmp"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Line Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},

            # Auxiliary PLCs - S7-1511-1 PN
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Material_Handling_PLC", "protocols": ["profinet", "s7comm_plus", "snmp"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2019-13945"]},
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Quality_Inspection_PLC", "protocols": ["profinet", "s7comm_plus", "snmp"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2019-13945"]},

            # Safety PLC - S7-1516F-3 PN/DP with PROFIsafe
            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "Machine_Safety_Controller", "protocols": ["profinet", "profisafe", "s7comm_plus"],
             "fingerprint_model": "6ES7 516-3FN01-0AB0",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2019-13945"]},

            # HMI Panels - TP1200 Comfort
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "control",
             "name": "CNC_Cell_Operator_HMI", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
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
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "control",
             "name": "Control_Room_Switch", "protocols": ["profinet", "snmp"],
             "fingerprint_id": "cisco/ie3500/8t3s",
             "role": "Industrial Switch"},
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "control",
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

            # SNMP monitoring of switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["plc"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["control"], "target_zones": ["control"]},

            # EWON Modbus polling to drives (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["drive", "servo"],
             "source_zones": ["control"], "target_zones": ["cell"],
             "jitter_ms": 500, "jitter_type": "gaussian"},
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
        "description": "Body shop welding cells with ControlLogix L85E PLCs, GuardLogix L83ES safety "
                       "controllers with CIP Safety, Kinetix servo drives, and PowerFlex VFDs. Heavy use "
                       "of EtherNet/IP implicit messaging for deterministic motion control. 41 devices "
                       "across control, cell, and field zones with robust safety infrastructure.",
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
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161", "CVE-2023-3595"]},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Paint_Shop_Line_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Line Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161", "CVE-2023-3595"]},

            # Cell PLCs - ControlLogix L84E
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Weld_Cell_1_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L84E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             "cve_ids": ["CVE-2022-1159"]},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Weld_Cell_2_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L84E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             "cve_ids": ["CVE-2022-1159"]},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Material_Transfer_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L84E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             "cve_ids": ["CVE-2022-1159"]},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Quality_Inspection_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1756-L84E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             "cve_ids": ["CVE-2022-1159"]},

            # Safety PLCs - GuardLogix L83ES
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Weld_Cell_Safety_PLC", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-1159"]},
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "Paint_Booth_Safety_PLC", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-1159"]},

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
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "control",
             "name": "Body_Shop_Core_Switch", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_id": "cisco/ie9320/24p4x",
             "role": "Industrial Switch"},
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "control",
             "name": "Weld_Cell_Network_Switch", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_id": "cisco/ie9320/24p4x",
             "role": "Industrial Switch"},
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "control",
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

            # SNMP monitoring of switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["plc"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["control"], "target_zones": ["control"]},

            # EWON EtherNet/IP polling to PLCs (10s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},
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
        "description": "Large multi-zone manufacturing facility demonstrating complex OT network architecture "
                       "based on the Purdue model. Features 9 zones with Siemens, Rockwell, Schneider, and ABB "
                       "vendor ecosystems. Includes centralized DMZ with SCADA/Historian, Windows jump server "
                       "(vulnerable to BlueKeep CVE-2019-0708), 4 production zones (one per vendor), and "
                       "corresponding field zones. Cross-zone material handoff coordination via Modbus TCP. "
                       "119 devices with 20+ CVE-affected devices across all major vendors including IT/OT "
                       "boundary jump server. Ideal for Cisco Cyber Vision grouping and vulnerability detection demos.",
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
             "cve_ids": ["CVE-2022-46660"],
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
             "cve_ids": ["CVE-2019-0708"],
             "external_comms": True},

            # ============================================================
            # SIEMENS PRODUCTION ZONE (Level 2) - 25 devices
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Line_1_Main_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},

            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Line_2_Main_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},

            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Material_Handling_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2019-13945"]},

            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Packaging_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2019-13945"]},

            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Safety_Controller", "protocols": ["profinet", "profisafe", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 516-3FN01-0AB0",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2019-13945"]},

            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Line_1_HMI", "protocols": ["profinet"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
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

            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "siemens_zone",
             "name": "Siemens_Zone_Switch_1", "protocols": ["profinet", "snmp"],
             "fingerprint_id": "cisco/ie3500/8t3s",
             "role": "Industrial Switch"},

            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "siemens_zone",
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
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161"]},

            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Line_2_Main_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161"]},

            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Material_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L73",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2022-1159"]},

            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_QC_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L73",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2022-1159"]},

            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Safety_Controller", "protocols": ["ethernet_ip", "cip_safety", "opc_ua"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-1159"]},

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

            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "rockwell_zone",
             "name": "Rockwell_Zone_Switch_1", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_id": "cisco/ie9320/24p4x",
             "role": "Industrial Switch"},

            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "rockwell_zone",
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
             "cve_ids": ["CVE-2022-45789"]},

            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Process_2_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "BMEP586040",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2022-45789"]},

            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Utility_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2021-22779"]},

            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Batch_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2021-22779"]},

            {"type": "safety_plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Safety_Controller", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEP586040S",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-45789"]},

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

            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Zone_Switch_1", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_id": "cisco/ie4000/8gt4g",
             "role": "Industrial Switch"},

            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "schneider_zone",
             "name": "Schneider_Zone_Switch_2", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_id": "cisco/ie4000/8gt4g",
             "role": "Industrial Switch"},

            # ============================================================
            # ABB/MIXED PRODUCTION ZONE (Level 2) - 20 devices
            # ============================================================
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Process_1_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "PM590-ETH",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2021-22285"]},

            {"type": "plc", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Process_2_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "PM590-ETH",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2021-22285"]},

            {"type": "plc", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Utility_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "PM583-ETH",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.00025},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2021-22285"]},

            {"type": "plc", "vendor": "abb", "count": 1, "zone": "abb_zone",
             "name": "ABB_Warehouse_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "PM583-ETH",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.00025},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2021-22285"]},

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

            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "abb_zone",
             "name": "ABB_Zone_Switch_1", "protocols": ["snmp"],
             "fingerprint_id": "cisco/ie3300/8t2s",
             "role": "Industrial Switch"},

            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "abb_zone",
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

            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["rockwell_zone"]},

            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["schneider_zone", "abb_zone"]},

            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["dmz"], "target_zones": ["dmz", "siemens_zone", "rockwell_zone", "schneider_zone", "abb_zone"]},

            # CROSS-ZONE FLOWS (Material Handoff)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["siemens_zone"], "target_zones": ["rockwell_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["rockwell_zone"], "target_zones": ["schneider_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["schneider_zone"], "target_zones": ["abb_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

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
            # Cross-zone material handoff conduits (L2 -> L2)
            {"id": "siemens_rockwell_handoff", "name": "Siemens \u2194 Rockwell Handoff",
             "source_zone": "siemens_zone", "target_zone": "rockwell_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Cross-zone material handoff coordination between Siemens and Rockwell production lines via Modbus TCP"},
            {"id": "rockwell_schneider_handoff", "name": "Rockwell \u2194 Schneider Handoff",
             "source_zone": "rockwell_zone", "target_zone": "schneider_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Cross-zone material handoff coordination between Rockwell and Schneider production lines via Modbus TCP"},
            {"id": "schneider_abb_handoff", "name": "Schneider \u2194 ABB Handoff",
             "source_zone": "schneider_zone", "target_zone": "abb_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Cross-zone material handoff coordination between Schneider and ABB production lines via Modbus TCP"},
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
        "description": "Precision automotive parts manufacturing facility following strict Purdue Model "
                       "architecture with four isolated manufacturing cells and an Industrial DMZ (IDMZ). "
                       "Cell 1: CNC Machining (Siemens/PROFINET), Cell 2: Robotic Welding (Rockwell/EtherNet-IP), "
                       "Cell 3: E-Coat Surface Treatment (Schneider/Modbus TCP), Cell 4: Final Assembly & Test "
                       "(ABB/mixed). No east-west communication between cells - only intra-cell flows and "
                       "northbound IDMZ supervisory data collection. EWON and Jump Server in IDMZ for "
                       "remote access. 67 devices across 6 zones with strict zone isolation.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        "zones": [
            # IDMZ - Level 3.5 (critical security boundary between IT and OT)
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
            # Cell 4 - Final Assembly & Test (ABB ecosystem, self-contained L0-L2)
            {"id": "cell4_assembly", "name": "Cell 4 - Final Assembly", "level": 2,
             "subnet_offset": 4, "vlan": 240, "security_level": "high"},
            # External/Internet
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "conduits": [
            # IDMZ to cell conduits (L3.5 -> L2, strict northbound-only data collection)
            {"id": "idmz_cell1_cnc", "name": "IDMZ \u2194 Cell 1 CNC",
             "source_zone": "idmz", "target_zone": "cell1_cnc",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "s7comm_plus", "s7comm", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to Siemens PLCs, central HMI S7comm+ polling, EWON Modbus TCP polling, SNMP infrastructure monitoring"},
            {"id": "idmz_cell2_weld", "name": "IDMZ \u2194 Cell 2 Welding",
             "source_zone": "idmz", "target_zone": "cell2_weld",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "ethernet_ip", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to Rockwell PLCs, central HMI EtherNet/IP polling, EWON Modbus TCP polling, SNMP monitoring"},
            {"id": "idmz_cell3_ecoat", "name": "IDMZ \u2194 Cell 3 E-Coat",
             "source_zone": "idmz", "target_zone": "cell3_ecoat",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to Schneider PLCs, central HMI and EWON Modbus TCP polling, SNMP monitoring"},
            {"id": "idmz_cell4_assembly", "name": "IDMZ \u2194 Cell 4 Assembly",
             "source_zone": "idmz", "target_zone": "cell4_assembly",
             "direction": "bidirectional",
             "allowed_protocols": ["opc_ua", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA/Historian OPC UA subscriptions to ABB PLCs, central HMI and EWON Modbus TCP polling, SNMP monitoring"},
            # IDMZ to external (L3.5 -> L4)
            {"id": "idmz_external", "name": "IDMZ \u2194 External",
             "source_zone": "idmz", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https", "rdp"],
             "security_level": "critical",
             "description": "EWON remote gateway heartbeat to Talk2M cloud; Jump server RDP for remote IT/OT administration"},
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
            # IDMZ (Level 3.5) - 9 devices
            # Central SCADA, historian, OPC gateway, remote access, switches
            # ============================================================
            # WinCC Professional - central SCADA server aggregating all cell data
            {"type": "scada_server", "vendor": "siemens", "count": 1, "zone": "idmz",
             "name": "Plant_Central_SCADA", "protocols": ["opc_ua", "s7comm", "modbus_tcp", "snmp"],
             "fingerprint_model": "WinCC Professional",
             "role": "Central SCADA Server"},
            # GE Proficy Historian - process data archival
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "idmz",
             "name": "Plant_Process_Historian", "protocols": ["opc_ua", "modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "role": "Process Historian",
             "cve_ids": ["CVE-2022-46660"]},
            # Kepware OPC UA Gateway - multi-protocol translation
            {"type": "gateway", "vendor": "kepware", "count": 1, "zone": "idmz",
             "name": "Plant_OPC_Gateway", "protocols": ["opc_ua", "modbus_tcp", "ethernet_ip", "s7comm"],
             "fingerprint_model": "KEPServerEX",
             "role": "OPC UA Gateway"},
            # HMS EWON Flexy 205 - remote access gateway to Talk2M cloud
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "idmz",
             "name": "IDMZ_EWON_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},
            # Windows Server 2016 Jump Server - IT/OT boundary (BlueKeep vulnerable)
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "idmz",
             "name": "IDMZ_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "cve_ids": ["CVE-2019-0708"],
             "external_comms": True},
            # WinCC Unified - central overview HMI for plant-wide visibility
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "idmz",
             "name": "Plant_Overview_HMI", "protocols": ["s7comm", "opc_ua"],
             "fingerprint_model": "WinCC Unified",
             "role": "Central Overview HMI"},
            # Cisco IE-9320 - IDMZ core aggregation switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "idmz",
             "name": "IDMZ_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-9320-24P4X-E",
             "role": "Core Network Switch"},
            # Cisco IE-3500 - north-facing firewall switch (enterprise side)
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "idmz",
             "name": "IDMZ_North_Firewall_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3500-8P3S-E",
             "role": "Firewall DMZ Switch"},
            # Cisco IE-3500 - south-facing firewall switch (cell side)
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "idmz",
             "name": "IDMZ_South_Firewall_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3500-8P3S-E",
             "role": "Firewall DMZ Switch"},

            # ============================================================
            # CELL 1: CNC MACHINING CENTER - Siemens (16 devices)
            # S7-1500 PLCs, SINAMICS S120 servos, G120C VFDs, ET200SP I/O
            # Protocol: PROFINET RT cyclic I/O, PROFIsafe, S7comm+
            # ============================================================
            # S7-1517-3 PN/DP - main cell controller (high-performance CPU)
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Cell_Main_PLC", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},
            # S7-1511-1 PN - auxiliary PLC for tool management
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Tool_Mgmt_PLC", "protocols": ["profinet", "opc_ua"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2019-13945"]},
            # S7-1516F-3 PN/DP - safety PLC for machine guarding
            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Safety_Controller", "protocols": ["profinet", "profisafe", "s7comm_plus", "opc_ua"],
             "fingerprint_model": "6ES7 516-3FN01-0AB0",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2019-13945"]},
            # TP1200 Comfort Panel - main operator HMI
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Operator_HMI", "protocols": ["profinet"],
             "fingerprint_model": "6AV2 124-0MC01-0AX0",
             "role": "Operator Interface"},
            # KTP700 Basic - setup/diagnostic HMI
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Setup_HMI", "protocols": ["profinet"],
             "fingerprint_model": "6AV2 123-2GB03-0AX0",
             "role": "Setup Interface"},
            # SINAMICS S120 - X axis servo drive
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_X_Axis_Servo", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            # SINAMICS S120 - Y axis servo drive
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Y_Axis_Servo", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            # SINAMICS S120 - Z axis servo drive
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Z_Axis_Servo", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            # SINAMICS S120 - spindle servo drive
            {"type": "servo", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Spindle_Servo", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6SL3130-7TE25-5AA3",
             "role": "Servo Drive"},
            # SINAMICS G120C - coolant pump VFD
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Coolant_Pump_VFD", "protocols": ["profinet", "modbus_tcp", "snmp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            # SINAMICS G120C - chip conveyor VFD
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Chip_Conveyor_VFD", "protocols": ["profinet", "modbus_tcp", "snmp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Variable Frequency Drive"},
            # ET200SP - spindle tool monitoring I/O
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Spindle_IO", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            # ET200SP - automatic tool changer I/O
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Tool_Changer_IO", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            # ET200SP - pallet/workholding I/O
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Pallet_IO", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Distributed I/O"},
            # Cisco IE-3500 - cell-internal managed switch
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Cell_Switch", "protocols": ["profinet", "snmp"],
             "fingerprint_id": "cisco/ie3500/8t3s",
             "role": "Industrial Switch"},
            # Cisco IE-3300 - cell uplink to IDMZ
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "cell1_cnc",
             "name": "CNC_Uplink_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Cell Uplink Switch"},

            # ============================================================
            # CELL 2: ROBOTIC WELDING LINE - Rockwell (16 devices)
            # ControlLogix/GuardLogix PLCs, KUKA robots, PowerFlex VFDs
            # Protocol: EtherNet/IP implicit I/O, CIP Safety
            # ============================================================
            # ControlLogix L85E - welding line controller
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Line_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Line Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161", "CVE-2023-3595"]},
            # ControlLogix L84E - welding station controller
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Station_PLC", "protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "1756-L84E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Cell Controller",
             "cve_ids": ["CVE-2022-1159"]},
            # GuardLogix L83ES - safety controller for weld cell
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Safety_PLC", "protocols": ["ethernet_ip", "cip_safety", "opc_ua"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-1159"]},
            # PanelView Plus 7 15" - main weld cell operator HMI
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Main_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T15C22D9P",
             "role": "Operator Interface"},
            # PanelView Plus 7 10" - welding station HMI
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Station_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Station Interface"},
            # KUKA KR C4 Robot Controller #1 - MIG welding robot
            {"type": "robot_controller", "vendor": "kuka", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Robot_1_Controller", "protocols": ["ethernet_ip", "profinet"],
             "fingerprint_model": "KR C4",
             "role": "Robot Controller"},
            # KUKA KR C4 Robot Controller #2 - TIG welding robot
            {"type": "robot_controller", "vendor": "kuka", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Robot_2_Controller", "protocols": ["ethernet_ip", "profinet"],
             "fingerprint_model": "KR C4",
             "role": "Robot Controller"},
            # Kinetix 5500 - weld positioner servo
            {"type": "servo", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Positioner_Servo", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},
            # PowerFlex 525 - parts conveyor VFD
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Conveyor_VFD", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},
            # PowerFlex 525 - fume exhaust fan VFD
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Exhaust_Fan_VFD", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},
            # PowerFlex 753 - welding cooling pump (high-power)
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cooling_Pump_VFD", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "20F-D052N103",
             "role": "High-Power Drive"},
            # FLEX 5000 - welding station 1 remote I/O
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Station_1_IO", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},
            # FLEX 5000 - welding station 2 remote I/O
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Station_2_IO", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Remote I/O"},
            # POINT I/O - safety gate/light curtain I/O
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Safety_Gate_IO", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "1734-AENT",
             "role": "Point I/O"},
            # Cisco IE-9320 - cell-internal managed switch
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Cell_Switch", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_id": "cisco/ie9320/24p4x",
             "role": "Industrial Switch"},
            # Cisco IE-3300 - cell uplink to IDMZ
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "cell2_weld",
             "name": "Weld_Uplink_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Cell Uplink Switch"},

            # ============================================================
            # CELL 3: E-COAT SURFACE TREATMENT - Schneider (14 devices)
            # Modicon M580/M340 PLCs, Altivar VFDs, process analyzers
            # Protocol: Modbus TCP polling
            # ============================================================
            # Modicon M580 - e-coat process controller
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Process_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "BMEP586040",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0001},
             "role": "Process Controller",
             "cve_ids": ["CVE-2022-45789"]},
            # Modicon M340 - conveyor/material handling controller
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Conveyor_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0002},
             "role": "Conveyor Controller",
             "cve_ids": ["CVE-2021-22779"]},
            # TM5 Safety PLC - chemical hazard/e-stop safety
            {"type": "safety_plc", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Safety_Controller", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "TM5CSLC100FS",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-45789"]},
            # Magelis GTO 10.4" - coating line operator HMI
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Operator_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIGTO5310",
             "role": "Operator Interface"},
            # Altivar 930 - rectifier power VFD (electrocoat deposition)
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Rectifier_VFD", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Rectifier Drive"},
            # Altivar 930 - bath circulation pump VFD
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Circulation_Pump_VFD", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Variable Frequency Drive"},
            # Altivar 630 - ultrafiltration pump VFD
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_UF_Pump_VFD", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ATV630D15N4",
             "role": "Variable Frequency Drive"},
            # Altivar 630 - cure oven recirculation fan VFD
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Oven_Fan_VFD", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ATV630D15N4",
             "role": "Variable Frequency Drive"},
            # E+H Liquiline CM442 - bath pH/conductivity analyzer
            {"type": "sensor", "vendor": "endress+hauser", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_pH_Analyzer", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CM442",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.0005},
             "role": "Process Analyzer"},
            # Rosemount 3051S - paint supply pressure transmitter
            {"type": "sensor", "vendor": "emerson", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Pressure_Xmitter", "protocols": ["modbus_tcp"],
             "fingerprint_model": "3051S",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.0005},
             "role": "Pressure Transmitter"},
            # Advantys STB - pretreatment wash stage I/O
            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Pretreat_IO", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "STBNIP2311",
             "role": "Remote I/O"},
            # TM3 Compact - tank level/temperature discrete I/O
            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Tank_IO", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "TM3DI32K",
             "role": "Discrete I/O"},
            # Cisco IE-4000 - cell-internal managed switch
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Cell_Switch", "protocols": ["snmp"],
             "fingerprint_id": "cisco/ie4000/8gt4g",
             "role": "Industrial Switch"},
            # Cisco IE-3300 - cell uplink to IDMZ
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "cell3_ecoat",
             "name": "ECoat_Uplink_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Cell Uplink Switch"},

            # ============================================================
            # CELL 4: FINAL ASSEMBLY & TEST - ABB (12 devices)
            # AC500 PLCs, ACS880/ACS580 drives, Fanuc robot, mixed I/O
            # Protocol: EtherNet/IP + Modbus TCP
            # ============================================================
            # ABB AC500 PM590-ETH - assembly line controller
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Line_PLC", "protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
             "fingerprint_model": "PM590-ETH",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0001},
             "role": "Line Controller",
             "cve_ids": ["CVE-2021-22285"]},
            # ABB AC500 PM583-ETH - test stand controller
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Test_Stand_PLC", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "PM583-ETH",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Test Controller",
             "cve_ids": ["CVE-2021-22285"]},
            # ABB CP620 - assembly operator HMI
            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Operator_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Operator Interface"},
            # ABB ACS880 - main assembly conveyor VFD
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Conveyor_VFD", "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "ACS880-01",
             "role": "Variable Frequency Drive"},
            # ABB ACS880 - parts lift/transfer VFD
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Lift_VFD", "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "ACS880-01",
             "role": "Variable Frequency Drive"},
            # ABB ACS580 - press/crimp station VFD
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Press_VFD", "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "ACS580",
             "role": "Variable Frequency Drive"},
            # ABB ACS580 - test fixture motor VFD
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Test_Motor_VFD", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ACS580",
             "role": "Variable Frequency Drive"},
            # Fanuc R-30iB Plus - precision assembly robot
            {"type": "robot_controller", "vendor": "fanuc", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Robot_Controller", "protocols": ["ethernet_ip"],
             "fingerprint_model": "R-30iB Plus",
             "role": "Robot Controller"},
            # Moxa ioLogik E1210 - torque station remote I/O
            {"type": "io_module", "vendor": "moxa", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Torque_Station_IO", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ioLogik E1210",
             "role": "Remote I/O"},
            # Advantech ADAM-6052 - leak test discrete I/O
            {"type": "io_module", "vendor": "advantech", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Leak_Test_IO", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ADAM-6052",
             "role": "Discrete I/O"},
            # Cisco IE-3300 - cell-internal managed switch
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Cell_Switch", "protocols": ["snmp"],
             "fingerprint_id": "cisco/ie3300/8t2s",
             "role": "Industrial Switch"},
            # Cisco IE-3300 - cell uplink to IDMZ
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "cell4_assembly",
             "name": "Assembly_Uplink_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Cell Uplink Switch"},
        ],

        "flows": [
            # ============================================================
            # CELL 1 INTRA-CELL FLOWS - Siemens PROFINET/S7comm
            # Strict: source_zones and target_zones both = cell1_cnc
            # ============================================================
            # PROFINET cyclic I/O - Main PLC to servo drives (4ms, motion control)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["servo"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            # PROFINET cyclic I/O - Main PLC to VFDs (8ms, auxiliary drives)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            # PROFINET cyclic I/O - PLCs to distributed I/O (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            # PROFIsafe - Safety PLC to PLCs and I/O (4ms, fail-safe)
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"]},
            # S7comm+ - HMI polling to PLCs (500ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # PROFINET - PLC-to-PLC interlocking within cell (32ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 32,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["cell1_cnc"], "target_zones": ["cell1_cnc"],
             "jitter_ms": 4, "jitter_type": "gaussian"},

            # ============================================================
            # CELL 2 INTRA-CELL FLOWS - Rockwell EtherNet/IP
            # Strict: source_zones and target_zones both = cell2_weld
            # ============================================================
            # EtherNet/IP implicit - PLC to robot controllers (2ms RPI, motion-critical)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source_types": ["plc"], "target_types": ["robot_controller"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 0.2, "jitter_type": "gaussian"},
            # EtherNet/IP implicit - PLC to servo drive (2ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source_types": ["plc"], "target_types": ["servo"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 0.2, "jitter_type": "gaussian"},
            # EtherNet/IP implicit - PLC to VFDs (10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            # EtherNet/IP implicit - PLC to remote I/O modules (10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            # CIP Safety - Safety PLC to PLCs and I/O (4ms Safety RPI)
            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"]},
            # EtherNet/IP explicit - HMI polling to PLCs (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # EtherNet/IP - PLC-to-PLC interlocking within cell (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["cell2_weld"], "target_zones": ["cell2_weld"],
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # ============================================================
            # CELL 3 INTRA-CELL FLOWS - Schneider Modbus TCP
            # Strict: source_zones and target_zones both = cell3_ecoat
            # ============================================================
            # Modbus TCP - PLCs to VFDs (100ms polling, process control)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 15, "jitter_type": "gaussian"},
            # Modbus TCP - PLCs to I/O modules (200ms polling)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            # Modbus TCP - PLC to process sensors (500ms, pH/pressure readings)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            # Modbus TCP - HMI polling to PLCs (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # Modbus TCP - PLC-to-PLC interlocking within cell (250ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["cell3_ecoat"], "target_zones": ["cell3_ecoat"],
             "jitter_ms": 30, "jitter_type": "uniform"},

            # ============================================================
            # CELL 4 INTRA-CELL FLOWS - ABB EtherNet/IP + Modbus TCP
            # Strict: source_zones and target_zones both = cell4_assembly
            # ============================================================
            # Modbus TCP - PLCs to VFDs (100ms polling)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 15, "jitter_type": "gaussian"},
            # EtherNet/IP implicit - PLC to robot controller (10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["robot_controller"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            # Modbus TCP - PLCs to I/O modules (200ms polling)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            # Modbus TCP - HMI polling to PLCs (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # Modbus TCP - PLC-to-PLC interlocking within cell (200ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["cell4_assembly"], "target_zones": ["cell4_assembly"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # ============================================================
            # IDMZ → CELL SUPERVISORY FLOWS (northbound data collection)
            # All originate from IDMZ, no cell initiates northbound
            # ============================================================
            # OPC UA - SCADA server subscriptions to all cell PLCs (1s)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["idmz"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"]},
            # OPC UA - Historian data collection from all cell PLCs (5s)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["idmz"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"]},
            # S7comm+ - Central HMI polling Siemens cell PLCs (1s)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["idmz"], "target_zones": ["cell1_cnc"]},
            # EtherNet/IP - Central HMI polling Rockwell cell PLCs (1s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["idmz"], "target_zones": ["cell2_weld"]},
            # Modbus TCP - Central HMI polling Schneider/ABB cell PLCs (1s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["idmz"], "target_zones": ["cell3_ecoat", "cell4_assembly"]},
            # Modbus TCP - EWON remote gateway polling all cell PLCs (10s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["idmz"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # ============================================================
            # OPC GATEWAY DATA COLLECTION
            # ============================================================
            # OPC UA - OPC Gateway multi-protocol data collection from all cell PLCs (2s)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 2000,
             "source_types": ["gateway"], "target_types": ["plc"],
             "source_zones": ["idmz"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"]},

            # ============================================================
            # SNMP INFRASTRUCTURE MONITORING
            # ============================================================
            # SNMP - SCADA monitoring all switches + EWON (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["idmz"],
             "target_zones": ["idmz", "cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"]},
            # SNMP - Jump server network reconnaissance (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["switch"],
             "source_zones": ["idmz"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"],
             "jitter_ms": 10000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP FIELD DEVICE MONITORING
            # Ensures PROFINET-only field devices (servos, VFDs, I/O) have
            # IP-based traffic so CV can associate their MAC with an IP.
            # ============================================================
            # SNMP - Cell switches polling field devices (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["switch"],
             "target_types": ["servo", "drive", "io_module"],
             "source_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"],
             "target_zones": ["cell1_cnc", "cell2_weld", "cell3_ecoat", "cell4_assembly"],
             "jitter_ms": 5000, "jitter_type": "uniform"},

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
}
