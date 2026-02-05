"""Manufacturing industry scenario templates.

Primary Vendors: Siemens, Rockwell Automation
Protocol Focus: PROFINET (Siemens), EtherNet/IP (Rockwell)

Enhanced with Sprint 1-6 capabilities:
- Vendor fingerprint references for hyper-realistic device emulation
- Suggested anomalies per template for testing scenarios
- PCAP learning hints for pattern extraction
- CVE vulnerability mapping for security testing
"""

from typing import Any


MANUFACTURING_TEMPLATES: dict[str, dict[str, Any]] = {
    "discrete_manufacturing": {
        "name": "Discrete Manufacturing Plant",
        "description": "Typical discrete manufacturing facility with Siemens S7-1500 PLCs, "
                       "SINAMICS drives, ET 200 I/O, and Comfort HMI panels. "
                       "Uses PROFINET for high-speed IO with Modbus for legacy devices.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        "devices": [
            # Control Layer - Siemens S7-1500 PLCs (with CVE vulnerabilities)
            # Using order codes to match CVE affected_models for Cyber Vision detection
            {"type": "plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "PLC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Process Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},
            {"type": "plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "PLC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 516-3AN01-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Process Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},
            {"type": "plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "PLC-AUX-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},

            # HMI Layer - Siemens Comfort and Basic Panels
            {"type": "hmi", "vendor": "siemens", "count": 3, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "TP1200 Comfort",
             "role": "Operator Interface"},
            {"type": "hmi", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "HMI-BASIC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "KTP900 Basic",
             "role": "Operator Interface"},

            # Drives - Siemens SINAMICS
            {"type": "drive", "vendor": "siemens", "count": 12, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "SINAMICS G120C",
             "role": "Variable Frequency Drive"},

            # Distributed I/O - Siemens ET 200SP
            {"type": "io_module", "vendor": "siemens", "count": 18, "zone": "field",
             "name_pattern": "ET200-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "ET 200SP IM155-6 PN",
             "role": "Distributed I/O"},

            # Network Infrastructure - Siemens SCALANCE
            {"type": "switch", "vendor": "siemens", "count": 3, "zone": "field",
             "name_pattern": "SW-{n:03d}", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "SCALANCE XB208",
             "role": "Industrial Switch"},

            # Enterprise Layer
            {"type": "engineering_station", "vendor": "siemens", "count": 2, "zone": "enterprise",
             "name_pattern": "ENG-{n:03d}", "protocols": ["profinet", "s7comm_plus", "opc_ua"],
             "role": "Engineering Workstation"},
            {"type": "scada_server", "vendor": "siemens", "count": 1, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["opc_ua", "s7comm_plus"],
             "role": "SCADA Server"},
            {"type": "historian", "vendor": "siemens", "count": 1, "zone": "enterprise",
             "name_pattern": "HIST-{n:03d}", "protocols": ["opc_ua"],
             "role": "Process Historian"},
        ],
        "flows": [
            # PROFINET cyclic IO (fast - 4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            # HMI polling via S7comm+ (500ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # SCADA polling via OPC UA (1000ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc"]},
            # Historian collection (5000ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["scada_server"]},
            # Engineering station connections (on-demand)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["engineering_station"], "target_types": ["plc"]},
            # SNMP monitoring of network infrastructure (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server", "engineering_station"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Enterprise Zone", "level": 4,
             "subnet_offset": 0, "vlan": 10, "security_level": "standard"},
            {"id": "dmz", "name": "Industrial DMZ", "level": 3.5,
             "subnet_offset": 1, "vlan": 20, "security_level": "high"},
            {"id": "process", "name": "Process Control Zone", "level": 2,
             "subnet_offset": 2, "vlan": 30, "security_level": "high"},
            {"id": "field", "name": "Field Device Zone", "level": 1,
             "subnet_offset": 3, "vlan": 40, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "jitter_spike", "watchdog_timeout"],
            "protocol": ["profinet_alarm", "s7comm_error"],
            "sequence": ["duplicate", "out_of_order"],
            "payload": ["value_spike"],
            "network": [],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "profinet", "flow_type": "cyclic_io", "priority": "high",
             "description": "Learn actual PROFINET RT cycle timing from S7-1500 PLCs"},
            {"protocol": "s7comm_plus", "flow_type": "hmi_polling", "priority": "high",
             "description": "Capture Siemens S7comm+ communication patterns"},
            {"protocol": "profinet", "flow_type": "drive_control", "priority": "medium",
             "description": "SINAMICS drive telegram timing patterns"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "http",
            "c2_pattern": "jittered_30s",
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["s7_stop_cpu", "s7_unauthorized_read"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "engineering_station"],
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    "automotive_assembly": {
        "name": "Automotive Assembly Line",
        "description": "High-speed automotive assembly with Siemens S7-1500 robot controllers, "
                       "S7-1500F safety PLCs with PROFIsafe, and SINAMICS S120 servo drives. "
                       "Heavy use of PROFINET IRT for deterministic motion control.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        "devices": [
            # Robot controllers - Siemens S7-1500 high-performance (with CVE vulnerabilities)
            # Using order codes to match CVE affected_models for Cyber Vision detection
            {"type": "plc", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "RC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Robot Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},
            {"type": "plc", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "RC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 516-3AN01-0AB0",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Robot Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},

            # Safety PLCs - Siemens S7-1500F with PROFIsafe (with CVE vulnerabilities)
            # Using order codes to match CVE affected_models for Cyber Vision detection
            {"type": "safety_plc", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "SAFETY-{n:03d}", "protocols": ["profinet", "profisafe", "s7comm_plus"],
             "fingerprint_model": "6ES7 516-3AN01-0AB0",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},

            # Vision systems - Keep SICK (specialty vendor)
            {"type": "sensor", "vendor": "SICK", "count": 6, "zone": "field",
             "name_pattern": "CAM-{n:03d}", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "Inspector P631",
             "role": "Vision System"},

            # Servo drives - Siemens SINAMICS S120 for motion control
            {"type": "servo", "vendor": "siemens", "count": 16, "zone": "field",
             "name_pattern": "SERVO-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "SINAMICS S120",
             "role": "Servo Drive"},

            # Conveyor drives - Siemens SINAMICS G115D distributed
            {"type": "drive", "vendor": "siemens", "count": 8, "zone": "field",
             "name_pattern": "CONV-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "SINAMICS G115D",
             "role": "Distributed Drive"},

            # Robot IO modules - Siemens ET 200SP
            {"type": "io_module", "vendor": "siemens", "count": 24, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "ET 200SP IM155-6 PN",
             "role": "Robot I/O"},

            # Central HMI - Siemens Comfort Panels
            {"type": "hmi", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "TP1200 Comfort",
             "role": "Operator Interface"},

            # Line controller - MES interface
            {"type": "scada_server", "vendor": "siemens", "count": 1, "zone": "enterprise",
             "name_pattern": "MES-{n:03d}", "protocols": ["opc_ua", "s7comm_plus"],
             "role": "MES Gateway"},
        ],
        "flows": [
            # High-speed cyclic (1ms) for motion control - PROFINET IRT
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 1,
             "source_types": ["plc"], "target_types": ["servo"],
             "jitter_ms": 0.1, "jitter_type": "gaussian"},
            # Conveyor control (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            # Safety communication via PROFIsafe (4ms)
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"]},
            # Vision data (100ms)
            {"protocol": "profinet", "pattern": "acyclic", "interval_ms": 100,
             "source_types": ["sensor"], "target_types": ["plc"]},
            # HMI updates (250ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 250,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # MES/SCADA data collection (1000ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "MES Zone", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "standard"},
            {"id": "process", "name": "Line Control", "level": 2,
             "subnet_offset": 1, "vlan": 200, "security_level": "high"},
            {"id": "field", "name": "Cell Level", "level": 1,
             "subnet_offset": 2, "vlan": 300, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "watchdog_timeout", "sync_loss"],
            "protocol": ["profinet_alarm", "profisafe_error"],
            "sequence": ["dropped_packet", "out_of_order"],
            "payload": [],
            "network": ["jitter_spike"],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "profinet", "flow_type": "cyclic_io", "priority": "high",
             "description": "Critical: Capture 1ms PROFINET IRT motion control timing"},
            {"protocol": "profisafe", "flow_type": "safety", "priority": "high",
             "description": "PROFIsafe safety PLC communication patterns"},
            {"protocol": "profinet", "flow_type": "servo_control", "priority": "high",
             "description": "SINAMICS S120 servo telegram timing"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "https",
            "c2_pattern": "jittered_1m",
            "enable_exfil": True,
            "exfil_protocol": "http",
            "enable_exploits": True,
            "exploit_patterns": ["s7_stop_cpu", "modbus_write_scan"],
            "enable_recon": False,
            "target_device_types": ["hmi", "scada_server"],
        },
        "total_duration_ms": 600000,  # 10 minutes
    },

    "packaging_line": {
        "name": "Packaging and Palletizing Line",
        "description": "High-speed packaging with Siemens S7-1500 motion controllers, "
                       "SINAMICS S120 servo drives for synchronized motion, "
                       "and integrated barcode scanning.",
        "vertical": "manufacturing",
        "phase_preset": "standard",
        "devices": [
            # Motion controllers - Siemens S7-1500 with Technology CPU (with CVE vulnerabilities)
            # Using order codes to match CVE affected_models for Cyber Vision detection
            {"type": "plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "MC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Motion Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},
            {"type": "plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "MC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 516-3AN01-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Motion Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},

            # Palletizing controllers - Siemens S7-1500 (with CVE vulnerabilities)
            # Using order codes to match CVE affected_models for Cyber Vision detection
            {"type": "plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "PALLET-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Palletizing Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},

            # Servo drives - Siemens SINAMICS S120 for motion
            {"type": "servo", "vendor": "siemens", "count": 12, "zone": "field",
             "name_pattern": "SERVO-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "SINAMICS S120",
             "role": "Servo Drive"},

            # Barcode scanners - Keep SICK (specialty vendor)
            {"type": "sensor", "vendor": "SICK", "count": 8, "zone": "field",
             "name_pattern": "SCAN-{n:03d}", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "CLV650-0120",
             "role": "Barcode Scanner"},

            # Label printers - Siemens I/O controlled
            {"type": "actuator", "vendor": "siemens", "count": 4, "zone": "field",
             "name_pattern": "PRINT-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "role": "Label Printer"},

            # Distributed I/O - Siemens ET 200SP
            {"type": "io_module", "vendor": "siemens", "count": 10, "zone": "field",
             "name_pattern": "ET200-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "ET 200SP IM155-6 PN",
             "role": "Distributed I/O"},

            # HMI panels - Siemens Basic Panels
            {"type": "hmi", "vendor": "siemens", "count": 3, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "KTP900 Basic",
             "role": "Operator Interface"},

            # Network switches - Siemens SCALANCE
            {"type": "switch", "vendor": "siemens", "count": 2, "zone": "field",
             "name_pattern": "SW-{n:03d}", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "SCALANCE XB208",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # Motion synchronization (2ms) - PROFINET IRT
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 2,
             "source_types": ["plc"], "target_types": ["servo"],
             "jitter_ms": 0.2, "jitter_type": "gaussian"},
            # I/O polling (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["io_module", "actuator"]},
            # Scanner data (50ms)
            {"protocol": "profinet", "pattern": "acyclic", "interval_ms": 50,
             "source_types": ["sensor"], "target_types": ["plc"]},
            # HMI update (250ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 250,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # SNMP monitoring of switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["plc"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "process", "name": "Line Control", "level": 2,
             "subnet_offset": 0, "vlan": 50, "security_level": "high"},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 1, "vlan": 51, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "motion_sync_error"],
            "protocol": ["profinet_alarm", "dcp_error"],
            "sequence": ["duplicate"],
            "payload": ["encoder_fault"],
            "network": [],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "profinet", "flow_type": "cyclic_io", "priority": "high",
             "description": "Capture SINAMICS S120 motion control timing patterns"},
            {"protocol": "profinet", "flow_type": "scanner_data", "priority": "medium",
             "description": "Scanner data transfer patterns via acyclic PROFINET"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "http",
            "c2_pattern": "jittered_1m",
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["s7_stop_cpu"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi"],
        },
        "total_duration_ms": 180000,  # 3 minutes
    },

    # ============================================================
    # ROCKWELL AUTOMATION TEMPLATES
    # ============================================================

    "rockwell_discrete_manufacturing": {
        "name": "Rockwell Discrete Manufacturing Plant",
        "description": "Discrete manufacturing facility with Rockwell ControlLogix L85E PLCs, "
                       "PowerFlex 525/753 drives, Point I/O distributed modules, and PanelView HMIs. "
                       "Uses EtherNet/IP for high-speed I/O with Modbus TCP for legacy integration.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        "devices": [
            # Control Layer - ControlLogix PLCs (with CVE vulnerabilities)
            {"type": "plc", "vendor": "rockwell", "count": 4, "zone": "process",
             "name_pattern": "PLC-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Process Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2023-3595"]},
            {"type": "plc", "vendor": "rockwell", "count": 2, "zone": "process",
             "name_pattern": "PLC-AUX-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L73",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2022-1159"]},

            # HMI Layer - Rockwell PanelView
            {"type": "hmi", "vendor": "rockwell", "count": 3, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},
            {"type": "hmi", "vendor": "rockwell", "count": 2, "zone": "process",
             "name_pattern": "HMI-BASIC-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711R-T7T",
             "role": "Operator Interface"},

            # Drives - Rockwell PowerFlex
            {"type": "drive", "vendor": "rockwell", "count": 8, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 4, "zone": "field",
             "name_pattern": "VFD-HP-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "20F-D052N103",
             "role": "High-Power Drive"},

            # Distributed I/O - Point I/O
            {"type": "io_module", "vendor": "rockwell", "count": 18, "zone": "field",
             "name_pattern": "PIO-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Distributed I/O"},

            # Network Infrastructure - Stratix Switches
            {"type": "switch", "vendor": "rockwell", "count": 3, "zone": "field",
             "name_pattern": "SW-{n:03d}", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "1783-BMS10CGL",
             "role": "Industrial Switch"},

            # Enterprise Layer
            {"type": "engineering_station", "vendor": "rockwell", "count": 2, "zone": "enterprise",
             "name_pattern": "ENG-{n:03d}", "protocols": ["ethernet_ip", "opc_ua"],
             "role": "Engineering Workstation"},
            {"type": "scada_server", "vendor": "rockwell", "count": 1, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["opc_ua", "ethernet_ip"],
             "role": "SCADA Server"},
            {"type": "historian", "vendor": "rockwell", "count": 1, "zone": "enterprise",
             "name_pattern": "HIST-{n:03d}", "protocols": ["opc_ua"],
             "role": "Process Historian"},
        ],
        "flows": [
            # EtherNet/IP implicit messaging (fast - 10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "jitter_ms": 2, "jitter_type": "gaussian"},
            # HMI polling via EtherNet/IP explicit messaging (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # Modbus polling for legacy drives (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["drive"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            # SCADA polling via OPC UA (1000ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc"]},
            # Historian collection (5000ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["scada_server"]},
            # Engineering station connections (on-demand)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["engineering_station"], "target_types": ["plc"]},
            # SNMP monitoring of network infrastructure (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server", "engineering_station"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Enterprise Zone", "level": 4,
             "subnet_offset": 0, "vlan": 10, "security_level": "standard"},
            {"id": "dmz", "name": "Industrial DMZ", "level": 3.5,
             "subnet_offset": 1, "vlan": 20, "security_level": "high"},
            {"id": "process", "name": "Process Control Zone", "level": 2,
             "subnet_offset": 2, "vlan": 30, "security_level": "high"},
            {"id": "field", "name": "Field Device Zone", "level": 1,
             "subnet_offset": 3, "vlan": 40, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "jitter_spike", "connection_timeout"],
            "protocol": ["cip_error", "modbus_exception"],
            "sequence": ["duplicate", "out_of_order"],
            "payload": ["value_spike"],
            "network": [],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "ethernet_ip", "flow_type": "implicit_io", "priority": "high",
             "description": "Learn actual EtherNet/IP RPI timing from ControlLogix PLCs"},
            {"protocol": "ethernet_ip", "flow_type": "explicit_messaging", "priority": "high",
             "description": "Capture CIP explicit messaging patterns for HMI polling"},
            {"protocol": "modbus_tcp", "flow_type": "polling", "priority": "medium",
             "description": "PowerFlex drive Modbus communication patterns"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "http",
            "c2_pattern": "jittered_30s",
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["cip_stop_plc", "modbus_write_scan"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "engineering_station"],
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    "rockwell_automotive_assembly": {
        "name": "Rockwell Automotive Assembly Line",
        "description": "High-speed automotive assembly with ControlLogix L85E robot controllers, "
                       "GuardLogix L83ES safety PLCs with CIP Safety, and Kinetix 5500 servo drives. "
                       "Heavy use of EtherNet/IP implicit messaging for deterministic motion control.",
        "vertical": "manufacturing",
        "phase_preset": "with_maintenance",
        "devices": [
            # Robot controllers - ControlLogix high-performance (with CVE vulnerabilities)
            {"type": "plc", "vendor": "rockwell", "count": 8, "zone": "process",
             "name_pattern": "RC-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Robot Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2023-3595", "CVE-2022-1161"]},

            # Safety PLCs - GuardLogix with CIP Safety (with CVE vulnerabilities)
            {"type": "safety_plc", "vendor": "rockwell", "count": 4, "zone": "process",
             "name_pattern": "SAFETY-{n:03d}", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-1159"]},

            # Compact GuardLogix for cell-level safety
            {"type": "safety_plc", "vendor": "rockwell", "count": 2, "zone": "process",
             "name_pattern": "CELL-SAFETY-{n:03d}", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1769-L33ERMS",
             "role": "Cell Safety Controller"},

            # Vision systems - Keep SICK/Cognex (specialty vendor)
            {"type": "sensor", "vendor": "SICK", "count": 6, "zone": "field",
             "name_pattern": "CAM-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "Inspector P631",
             "role": "Vision System"},

            # Servo drives - Kinetix 5500 for motion control
            {"type": "servo", "vendor": "rockwell", "count": 16, "zone": "field",
             "name_pattern": "SERVO-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},

            # Conveyor drives - PowerFlex 753
            {"type": "drive", "vendor": "rockwell", "count": 8, "zone": "field",
             "name_pattern": "CONV-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "20F-D052N103",
             "role": "Conveyor Drive"},

            # Robot IO modules - FLEX 5000
            {"type": "io_module", "vendor": "rockwell", "count": 24, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Robot I/O"},

            # Central HMI - PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 4, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},

            # Line controller - MES interface
            {"type": "scada_server", "vendor": "rockwell", "count": 1, "zone": "enterprise",
             "name_pattern": "MES-{n:03d}", "protocols": ["opc_ua", "ethernet_ip"],
             "role": "MES Gateway"},
        ],
        "flows": [
            # High-speed cyclic (2ms RPI) for motion control
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source_types": ["plc"], "target_types": ["servo"],
             "jitter_ms": 0.2, "jitter_type": "gaussian"},
            # Conveyor control (10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            # CIP Safety communication (4ms Safety RPI)
            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"]},
            # Vision data (100ms)
            {"protocol": "ethernet_ip", "pattern": "explicit", "interval_ms": 100,
             "source_types": ["sensor"], "target_types": ["plc"]},
            # HMI updates (250ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 250,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # MES/SCADA data collection (1000ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "MES Zone", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "standard"},
            {"id": "process", "name": "Line Control", "level": 2,
             "subnet_offset": 1, "vlan": 200, "security_level": "high"},
            {"id": "field", "name": "Cell Level", "level": 1,
             "subnet_offset": 2, "vlan": 300, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "connection_timeout", "rpi_violation"],
            "protocol": ["cip_error", "cip_safety_fault"],
            "sequence": ["dropped_packet", "out_of_order"],
            "payload": [],
            "network": ["jitter_spike"],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "ethernet_ip", "flow_type": "implicit_io", "priority": "high",
             "description": "Critical: Capture 2ms EtherNet/IP motion control timing"},
            {"protocol": "cip_safety", "flow_type": "safety", "priority": "high",
             "description": "CIP Safety GuardLogix communication patterns"},
            {"protocol": "ethernet_ip", "flow_type": "servo_control", "priority": "high",
             "description": "Kinetix 5500 servo drive CIP motion timing"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "https",
            "c2_pattern": "jittered_1m",
            "enable_exfil": True,
            "exfil_protocol": "http",
            "enable_exploits": True,
            "exploit_patterns": ["cip_stop_plc", "cip_unauthorized_write"],
            "enable_recon": False,
            "target_device_types": ["hmi", "scada_server"],
        },
        "total_duration_ms": 600000,  # 10 minutes
    },

    "rockwell_packaging_line": {
        "name": "Rockwell Packaging and Palletizing Line",
        "description": "High-speed packaging with CompactLogix L33ER motion controllers, "
                       "Kinetix 5500 servo drives for synchronized motion, "
                       "and integrated barcode scanning via Point I/O.",
        "vertical": "manufacturing",
        "phase_preset": "standard",
        "devices": [
            # Motion controllers - CompactLogix (with CVE vulnerabilities)
            {"type": "plc", "vendor": "rockwell", "count": 4, "zone": "process",
             "name_pattern": "MC-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Motion Controller",
             "cve_ids": ["CVE-2021-22681", "CVE-2022-1161"]},

            # Palletizing controllers - CompactLogix (with CVE vulnerabilities)
            {"type": "plc", "vendor": "rockwell", "count": 2, "zone": "process",
             "name_pattern": "PALLET-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1769-L24ER-QB1B",
             "role": "Palletizing Controller",
             "cve_ids": ["CVE-2021-22681", "CVE-2022-1161"]},

            # Servo drives - Kinetix 5500 for motion
            {"type": "servo", "vendor": "rockwell", "count": 12, "zone": "field",
             "name_pattern": "SERVO-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},

            # Barcode scanners - Keep SICK (specialty vendor)
            {"type": "sensor", "vendor": "SICK", "count": 8, "zone": "field",
             "name_pattern": "SCAN-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "CLV650-0120",
             "role": "Barcode Scanner"},

            # Conveyor drives - PowerFlex 525
            {"type": "drive", "vendor": "rockwell", "count": 6, "zone": "field",
             "name_pattern": "CONV-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "25B-D030N104",
             "role": "Conveyor Drive"},

            # Distributed I/O - Point I/O
            {"type": "io_module", "vendor": "rockwell", "count": 10, "zone": "field",
             "name_pattern": "PIO-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Distributed I/O"},

            # HMI panels - PanelView 800
            {"type": "hmi", "vendor": "rockwell", "count": 3, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711R-T7T",
             "role": "Operator Interface"},

            # Network switches - Stratix
            {"type": "switch", "vendor": "rockwell", "count": 2, "zone": "field",
             "name_pattern": "SW-{n:03d}", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "1783-BMS10CGL",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # Motion synchronization (4ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["servo"],
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            # I/O polling (10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["io_module", "drive"]},
            # Scanner data (50ms)
            {"protocol": "ethernet_ip", "pattern": "explicit", "interval_ms": 50,
             "source_types": ["sensor"], "target_types": ["plc"]},
            # HMI update (250ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 250,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # SNMP monitoring of switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["plc"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "process", "name": "Line Control", "level": 2,
             "subnet_offset": 0, "vlan": 50, "security_level": "high"},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 1, "vlan": 51, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "motion_sync_error"],
            "protocol": ["cip_error", "list_identity_timeout"],
            "sequence": ["duplicate"],
            "payload": ["encoder_fault"],
            "network": [],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "ethernet_ip", "flow_type": "implicit_io", "priority": "high",
             "description": "Capture Kinetix 5500 motion control timing patterns"},
            {"protocol": "ethernet_ip", "flow_type": "scanner_data", "priority": "medium",
             "description": "Scanner data transfer patterns via explicit messaging"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "http",
            "c2_pattern": "jittered_1m",
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["cip_stop_plc"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi"],
        },
        "total_duration_ms": 180000,  # 3 minutes
    },

    "rockwell_micrologix_legacy": {
        "name": "Rockwell MicroLogix Legacy System",
        "description": "Legacy manufacturing cell with MicroLogix 1400 PLCs for machine control. "
                       "Uses Modbus TCP for SCADA integration and EtherNet/IP for local HMI. "
                       "Contains devices with known unpatched vulnerabilities (CVE-2019-10954).",
        "vertical": "manufacturing",
        "phase_preset": "standard",
        "devices": [
            # MicroLogix PLCs (legacy, CVE vulnerabilities - no patch available)
            {"type": "plc", "vendor": "rockwell", "count": 6, "zone": "process",
             "name_pattern": "ML-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1766-L32BWA",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.0005},
             "role": "Machine Controller",
             "cve_ids": ["CVE-2019-10954"]},

            # Older CompactLogix for coordination
            {"type": "plc", "vendor": "rockwell", "count": 2, "zone": "process",
             "name_pattern": "CL-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L24ER-QB1B",
             "role": "Cell Coordinator"},

            # PowerFlex 525 drives
            {"type": "drive", "vendor": "rockwell", "count": 8, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},

            # Point I/O modules
            {"type": "io_module", "vendor": "rockwell", "count": 12, "zone": "field",
             "name_pattern": "PIO-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Distributed I/O"},

            # PanelView 800 HMIs
            {"type": "hmi", "vendor": "rockwell", "count": 4, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711R-T7T",
             "role": "Operator Interface"},

            # SCADA server for Modbus polling (GE Proficy Historian with SQL Injection vuln)
            {"type": "scada_server", "vendor": "ge", "count": 1, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "SCADA Server"},
        ],
        "flows": [
            # EtherNet/IP polling (100ms - slower legacy)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "jitter_ms": 10, "jitter_type": "gaussian"},
            # Modbus polling for MicroLogix (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # HMI updates (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # Drive status via Modbus (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["drive"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "SCADA Zone", "level": 3,
             "subnet_offset": 0, "vlan": 10, "security_level": "standard"},
            {"id": "process", "name": "Control Zone", "level": 2,
             "subnet_offset": 1, "vlan": 20, "security_level": "high"},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 2, "vlan": 30, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "timeout"],
            "protocol": ["modbus_exception", "cip_error"],
            "sequence": ["duplicate"],
            "payload": ["value_spike"],
            "network": [],
            "security": ["unauthorized_access"],  # CVE-2019-10954 exploitation
        },
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "polling", "priority": "high",
             "description": "MicroLogix Modbus polling patterns"},
            {"protocol": "ethernet_ip", "flow_type": "explicit_messaging", "priority": "medium",
             "description": "Legacy EtherNet/IP communication patterns"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "http",
            "c2_pattern": "jittered_30s",
            "enable_exfil": True,
            "exfil_protocol": "dns",  # DNS exfil for stealth
            "enable_exploits": True,
            "exploit_patterns": ["modbus_unauthorized_write", "cip_auth_bypass"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["plc", "hmi"],
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # SIEMENS LEGACY AND BUDGET TEMPLATES
    # ============================================================

    "siemens_legacy_manufacturing": {
        "name": "Siemens Legacy Manufacturing Cell",
        "description": "Brownfield manufacturing cell with legacy Siemens S7-300 and S7-400 PLCs. "
                       "Common in older facilities not yet upgraded to S7-1500. "
                       "Contains devices with known DoS vulnerability (CVE-2019-13103).",
        "vertical": "manufacturing",
        "phase_preset": "standard",
        "devices": [
            # Legacy S7-300 PLCs (with CVE vulnerability)
            {"type": "plc", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "PLC-{n:03d}", "protocols": ["profinet", "s7comm"],
             "fingerprint_model": "CPU 315-2 PN/DP",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.0005},
             "role": "Process Controller",
             "cve_ids": ["CVE-2019-13103"]},

            # Legacy S7-400 PLCs for coordination (with CVE vulnerability)
            {"type": "plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "PLC-MAIN-{n:03d}", "protocols": ["profinet", "s7comm"],
             "fingerprint_model": "CPU 416-3 PN/DP",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Main Controller",
             "cve_ids": ["CVE-2019-13103"]},

            # Older HMI panels - Siemens Basic Panels
            {"type": "hmi", "vendor": "siemens", "count": 3, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["profinet", "s7comm"],
             "fingerprint_model": "KTP900 Basic",
             "role": "Operator Interface"},

            # Older SINAMICS drives
            {"type": "drive", "vendor": "siemens", "count": 8, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "SINAMICS G120C",
             "role": "Variable Frequency Drive"},

            # Distributed I/O - ET 200MP (older than SP)
            {"type": "io_module", "vendor": "siemens", "count": 12, "zone": "field",
             "name_pattern": "ET200-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "ET 200MP IM155-5 PN",
             "role": "Distributed I/O"},

            # Network Infrastructure - Siemens SCALANCE
            {"type": "switch", "vendor": "siemens", "count": 2, "zone": "field",
             "name_pattern": "SW-{n:03d}", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "SCALANCE XB208",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # PROFINET cyclic IO (slower for legacy - 8ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "jitter_ms": 2, "jitter_type": "gaussian"},
            # HMI polling via S7comm (1000ms)
            {"protocol": "s7comm", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "jitter_ms": 100, "jitter_type": "uniform"},
            # SNMP monitoring (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["plc"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "process", "name": "Process Control Zone", "level": 2,
             "subnet_offset": 0, "vlan": 30, "security_level": "high"},
            {"id": "field", "name": "Field Device Zone", "level": 1,
             "subnet_offset": 1, "vlan": 40, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "timeout", "watchdog_timeout"],
            "protocol": ["profinet_alarm", "s7comm_error"],
            "sequence": ["duplicate", "out_of_order"],
            "payload": ["value_spike"],
            "network": [],
            "security": ["dos_attack"],  # CVE-2019-13103 exploitation
        },
        "pcap_learning_hints": [
            {"protocol": "profinet", "flow_type": "cyclic_io", "priority": "high",
             "description": "Learn PROFINET RT cycle timing from legacy S7-300/400"},
            {"protocol": "s7comm", "flow_type": "hmi_polling", "priority": "high",
             "description": "Capture S7comm communication patterns (legacy protocol)"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "http",
            "c2_pattern": "jittered_30s",
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["s7_stop_cpu", "s7_dos"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["plc", "hmi"],
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    "siemens_small_manufacturing": {
        "name": "Siemens Small Manufacturing Cell",
        "description": "Budget-friendly manufacturing cell with Siemens S7-1200 PLCs. "
                       "Common in smaller facilities or machine-level applications. "
                       "Contains devices with known web server vulnerability (CVE-2019-10929).",
        "vertical": "manufacturing",
        "phase_preset": "standard",
        "devices": [
            # S7-1200 PLCs (with CVE vulnerability)
            {"type": "plc", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "PLC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "CPU 1214C DC/DC/DC",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "Machine Controller",
             "cve_ids": ["CVE-2019-10929"]},

            # S7-1200F Safety PLCs
            {"type": "safety_plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "SAFETY-{n:03d}", "protocols": ["profinet", "profisafe", "s7comm_plus"],
             "fingerprint_model": "CPU 1214FC DC/DC/DC",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2019-10929"]},

            # Basic HMI panels
            {"type": "hmi", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "KTP900 Basic",
             "role": "Operator Interface"},

            # Small drives
            {"type": "drive", "vendor": "siemens", "count": 6, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "SINAMICS G120C",
             "role": "Variable Frequency Drive"},

            # Distributed I/O - Siemens ET 200SP
            {"type": "io_module", "vendor": "siemens", "count": 8, "zone": "field",
             "name_pattern": "ET200-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "ET 200SP IM155-6 PN",
             "role": "Distributed I/O"},

            # Network switch
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "field",
             "name_pattern": "SW-{n:03d}", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "SCALANCE XB208",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # PROFINET cyclic IO (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            # Safety communication via PROFIsafe (8ms)
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 8,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"]},
            # HMI polling via S7comm+ (500ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # SNMP monitoring (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["plc"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "process", "name": "Cell Control Zone", "level": 2,
             "subnet_offset": 0, "vlan": 50, "security_level": "high"},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 1, "vlan": 51, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "timeout"],
            "protocol": ["profinet_alarm", "s7comm_error", "profisafe_error"],
            "sequence": ["duplicate"],
            "payload": ["value_spike"],
            "network": [],
            "security": ["web_server_dos"],  # CVE-2019-10929 exploitation
        },
        "pcap_learning_hints": [
            {"protocol": "profinet", "flow_type": "cyclic_io", "priority": "high",
             "description": "Capture S7-1200 PROFINET communication patterns"},
            {"protocol": "s7comm_plus", "flow_type": "hmi_polling", "priority": "medium",
             "description": "S7-1200 HMI polling patterns"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "http",
            "c2_pattern": "jittered_1m",
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["s7_stop_cpu", "web_server_dos"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["plc", "hmi"],
        },
        "total_duration_ms": 180000,  # 3 minutes
    },

    # ============================================================
    # SUPER MANUFACTURING - MULTI-VENDOR MULTI-ZONE
    # ============================================================

    "super_manufacturing": {
        "name": "Super Manufacturing - Multi-Vendor Multi-Zone",
        "description": "Comprehensive multi-vendor, multi-zone manufacturing facility demonstrating "
                       "complex OT network architecture. Features 9 Purdue-level zones with Siemens, "
                       "Rockwell, Schneider, and ABB vendor ecosystems. Includes cross-zone material "
                       "handoff coordination, centralized SCADA/historian, and safety systems across "
                       "all production areas. Ideal for Cisco Cyber Vision grouping demonstrations "
                       "and inter-zone communication pattern analysis.",
        "vertical": "manufacturing",
        "phase_preset": "full_lifecycle",
        "devices": [
            # ============================================================
            # INDUSTRIAL DMZ (Level 3.5) - 8 devices
            # Centralized supervision, historians, and gateways
            # ============================================================
            # SCADA Server - Siemens WinCC
            {"type": "scada_server", "vendor": "siemens", "count": 1, "zone": "dmz",
             "name_pattern": "SCADA-S7-DMZ-{n:03d}", "protocols": ["opc_ua", "s7comm_plus", "modbus_tcp"],
             "fingerprint_model": "WinCC Professional",
             "role": "Central SCADA Server"},

            # Historian - GE Proficy (with CVE-2022-46660)
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "dmz",
             "name_pattern": "HIST-GE-DMZ-{n:03d}", "protocols": ["opc_ua", "modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "Process Historian"},

            # OPC UA Gateway - Kepware (multi-protocol translation)
            {"type": "gateway", "vendor": "kepware", "count": 1, "zone": "dmz",
             "name_pattern": "GW-OPC-DMZ-{n:03d}", "protocols": ["opc_ua", "modbus_tcp", "ethernet_ip", "s7comm_plus"],
             "role": "Protocol Gateway"},

            # Engineering Stations - Siemens TIA Portal
            {"type": "engineering_station", "vendor": "siemens", "count": 1, "zone": "dmz",
             "name_pattern": "ENG-S7-DMZ-{n:03d}", "protocols": ["s7comm_plus", "profinet", "opc_ua"],
             "role": "Siemens Engineering Workstation"},

            # Engineering Station - Rockwell Studio 5000
            {"type": "engineering_station", "vendor": "rockwell", "count": 1, "zone": "dmz",
             "name_pattern": "ENG-AB-DMZ-{n:03d}", "protocols": ["ethernet_ip", "opc_ua"],
             "role": "Rockwell Engineering Workstation"},

            # Protocol Gateway - Anybus (Modbus/EtherNet/IP translation)
            {"type": "gateway", "vendor": "hms", "count": 1, "zone": "dmz",
             "name_pattern": "GW-ANYBUS-DMZ-{n:03d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "role": "Anybus Protocol Gateway"},

            # Centralized HMI - Multi-protocol Siemens TP1200
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "dmz",
             "name_pattern": "HMI-CENTRAL-DMZ-{n:03d}", "protocols": ["s7comm_plus", "ethernet_ip", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "TP1200 Comfort",
             "role": "Central Multi-Protocol HMI"},

            # DMZ Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "dmz",
             "name_pattern": "SW-CISCO-DMZ-{n:03d}", "protocols": ["snmp"],
             "role": "DMZ Network Switch"},

            # ============================================================
            # SIEMENS PRODUCTION ZONE (Level 2) - 13 devices
            # S7-1500 PLCs, Safety, HMI for Siemens production area
            # ============================================================
            # Main PLCs - S7-1517-3 PN/DP (high performance)
            # Using order codes to match CVE affected_models for Cyber Vision detection
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name_pattern": "PLC-S7-SZ-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name_pattern": "PLC-S7-SZ-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 516-3AN01-0AB0",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},

            # Auxiliary PLC - S7-1511-1 PN
            # Using order codes to match CVE affected_models for Cyber Vision detection
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name_pattern": "PLC-S7-SZ-AUX-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},

            # Safety PLC - S7-1516F-3 PN/DP with PROFIsafe
            # Using order codes to match CVE affected_models for Cyber Vision detection
            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name_pattern": "SAFETY-S7-SZ-{n:03d}", "protocols": ["profinet", "profisafe", "s7comm_plus"],
             "fingerprint_model": "6ES7 516-3AN01-0AB0",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782", "CVE-2022-38465"]},

            # HMI - TP1200 Comfort Panel
            {"type": "hmi", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name_pattern": "HMI-S7-SZ-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "TP1200 Comfort",
             "role": "Operator Interface"},

            # VFD Drives - SINAMICS G120C
            {"type": "drive", "vendor": "siemens", "count": 6, "zone": "siemens_zone",
             "name_pattern": "VFD-S7-SZ-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "SINAMICS G120C",
             "role": "Variable Frequency Drive"},

            # Servo Drives - SINAMICS S120
            {"type": "servo", "vendor": "siemens", "count": 4, "zone": "siemens_zone",
             "name_pattern": "SERVO-S7-SZ-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "SINAMICS S120",
             "role": "Servo Drive"},

            # Distributed I/O - ET 200SP
            {"type": "io_module", "vendor": "siemens", "count": 6, "zone": "siemens_zone",
             "name_pattern": "IO-S7-SZ-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "ET 200SP IM155-6 PN",
             "role": "Distributed I/O"},

            # Switch - SCALANCE XB208
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "siemens_zone",
             "name_pattern": "SW-S7-SZ-{n:03d}", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "SCALANCE XB208",
             "role": "Industrial Switch"},

            # ============================================================
            # ROCKWELL PRODUCTION ZONE (Level 2) - 13 devices
            # ControlLogix/GuardLogix PLCs for Rockwell production area
            # ============================================================
            # Main PLCs - ControlLogix L85E
            {"type": "plc", "vendor": "rockwell", "count": 2, "zone": "rockwell_zone",
             "name_pattern": "PLC-AB-RZ-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2023-3595"]},

            # Auxiliary PLC - ControlLogix L73
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name_pattern": "PLC-AB-RZ-AUX-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L73",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2022-1159"]},

            # Safety PLC - GuardLogix L83ES with CIP Safety
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name_pattern": "SAFETY-AB-RZ-{n:03d}", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-1159"]},

            # HMI - PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name_pattern": "HMI-AB-RZ-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Operator Interface"},

            # VFD Drives - PowerFlex 525
            {"type": "drive", "vendor": "rockwell", "count": 4, "zone": "rockwell_zone",
             "name_pattern": "VFD-AB-RZ-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "25B-D030N104",
             "role": "Variable Frequency Drive"},

            # High-Power Drives - PowerFlex 753
            {"type": "drive", "vendor": "rockwell", "count": 2, "zone": "rockwell_zone",
             "name_pattern": "VFD-HP-AB-RZ-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "20F-D052N103",
             "role": "High-Power Drive"},

            # Servo Drives - Kinetix 5500
            {"type": "servo", "vendor": "rockwell", "count": 4, "zone": "rockwell_zone",
             "name_pattern": "SERVO-AB-RZ-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2198-D012-ERS3",
             "role": "Servo Drive"},

            # Distributed I/O - Point I/O 1734-AENT
            {"type": "io_module", "vendor": "rockwell", "count": 6, "zone": "rockwell_zone",
             "name_pattern": "IO-AB-RZ-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Distributed I/O"},

            # Switch - Stratix 5700
            {"type": "switch", "vendor": "rockwell", "count": 1, "zone": "rockwell_zone",
             "name_pattern": "SW-AB-RZ-{n:03d}", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "1783-BMS10CGL",
             "role": "Industrial Switch"},

            # ============================================================
            # SCHNEIDER PRODUCTION ZONE (Level 2) - 11 devices
            # M580/M340 PLCs for Schneider production area
            # ============================================================
            # Main PLCs - M580 BMEH586040 (Hot Standby capable)
            {"type": "plc", "vendor": "schneider", "count": 2, "zone": "schneider_zone",
             "name_pattern": "PLC-SE-SCZ-{n:03d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2021-22779", "CVE-2020-7540"]},

            # Auxiliary PLC - M340
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name_pattern": "PLC-SE-SCZ-AUX-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMXP342020",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2021-22779"]},

            # Safety PLC - M580 Safety BMEP586040S
            {"type": "safety_plc", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name_pattern": "SAFETY-SE-SCZ-{n:03d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "BMEP586040S",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller"},

            # HMI - Magelis HMIST6700
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name_pattern": "HMI-SE-SCZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIST6700",
             "role": "Operator Interface"},

            # VFD Drives - Altivar ATV930
            {"type": "drive", "vendor": "schneider", "count": 5, "zone": "schneider_zone",
             "name_pattern": "VFD-SE-SCZ-{n:03d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ATV930",
             "role": "Variable Frequency Drive"},

            # Servo Drives - Lexium LXM32
            {"type": "servo", "vendor": "schneider", "count": 3, "zone": "schneider_zone",
             "name_pattern": "SERVO-SE-SCZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "LXM32MD18N4",
             "role": "Servo Drive"},

            # Distributed I/O - TM3DI32K
            {"type": "io_module", "vendor": "schneider", "count": 4, "zone": "schneider_zone",
             "name_pattern": "IO-SE-SCZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "role": "Distributed I/O"},

            # Switch - ConneXium TCSESM
            {"type": "switch", "vendor": "schneider", "count": 1, "zone": "schneider_zone",
             "name_pattern": "SW-SE-SCZ-{n:03d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "TCSESM083F2CU0",
             "role": "Industrial Switch"},

            # ============================================================
            # MIXED/SPECIALTY ZONE (Level 2) - 12 devices
            # ABB PLCs, specialty sensors, instrumentation
            # ============================================================
            # ABB PLCs - PM590-ETH
            {"type": "plc", "vendor": "abb", "count": 2, "zone": "mixed_zone",
             "name_pattern": "PLC-ABB-MZ-{n:03d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "PM590-ETH",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Process Controller"},

            # ABB Compact PLC - PM583-ETH
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "mixed_zone",
             "name_pattern": "PLC-ABB-MZ-AUX-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM583-ETH",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.00025},
             "role": "Auxiliary Controller"},

            # ABB HMI - CP620
            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "mixed_zone",
             "name_pattern": "HMI-ABB-MZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Operator Interface"},

            # ABB Drives - ACS880 (Industrial)
            {"type": "drive", "vendor": "abb", "count": 4, "zone": "mixed_zone",
             "name_pattern": "VFD-ABB-MZ-{n:03d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Industrial Drive"},

            # ABB Drives - ACS580 (General Purpose)
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "mixed_zone",
             "name_pattern": "VFD-GP-ABB-MZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS580",
             "role": "General Purpose Drive"},

            # SICK Vision Systems - Inspector P631
            {"type": "sensor", "vendor": "sick", "count": 2, "zone": "mixed_zone",
             "name_pattern": "CAM-SICK-MZ-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "Inspector P631",
             "role": "Vision System"},

            # SICK Barcode Scanners - CLV650
            {"type": "sensor", "vendor": "sick", "count": 3, "zone": "mixed_zone",
             "name_pattern": "SCAN-SICK-MZ-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "CLV650-0120",
             "role": "Barcode Scanner"},

            # Endress+Hauser Flow Meters - Promag 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "mixed_zone",
             "name_pattern": "FLOW-EH-MZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Electromagnetic Flowmeter"},

            # Endress+Hauser Level Transmitters - FMP50
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "mixed_zone",
             "name_pattern": "LEVEL-EH-MZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Level Transmitter"},

            # ABB I/O - CI501
            {"type": "io_module", "vendor": "abb", "count": 2, "zone": "mixed_zone",
             "name_pattern": "IO-ABB-MZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CI501",
             "role": "Distributed I/O"},

            # ============================================================
            # SIEMENS FIELD ZONE (Level 1) - 4 devices
            # Field devices for Siemens production area
            # ============================================================
            # Additional VFDs for field level
            {"type": "drive", "vendor": "siemens", "count": 2, "zone": "field_siemens",
             "name_pattern": "VFD-S7-FSZ-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "SINAMICS G120C",
             "role": "Field VFD"},

            # Additional I/O modules
            {"type": "io_module", "vendor": "siemens", "count": 2, "zone": "field_siemens",
             "name_pattern": "IO-S7-FSZ-{n:03d}", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "ET 200SP IM155-6 PN",
             "role": "Field I/O"},

            # ============================================================
            # ROCKWELL FIELD ZONE (Level 1) - 4 devices
            # Field devices for Rockwell production area
            # ============================================================
            # Additional VFDs for field level
            {"type": "drive", "vendor": "rockwell", "count": 2, "zone": "field_rockwell",
             "name_pattern": "VFD-AB-FRZ-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "25B-D030N104",
             "role": "Field VFD"},

            # Additional I/O modules
            {"type": "io_module", "vendor": "rockwell", "count": 2, "zone": "field_rockwell",
             "name_pattern": "IO-AB-FRZ-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Field I/O"},

            # ============================================================
            # SCHNEIDER FIELD ZONE (Level 1) - 4 devices
            # Field devices for Schneider production area
            # ============================================================
            # Additional VFDs for field level
            {"type": "drive", "vendor": "schneider", "count": 2, "zone": "field_schneider",
             "name_pattern": "VFD-SE-FSCZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "role": "Field VFD"},

            # Additional I/O modules
            {"type": "io_module", "vendor": "schneider", "count": 2, "zone": "field_schneider",
             "name_pattern": "IO-SE-FSCZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "role": "Field I/O"},

            # ============================================================
            # MIXED FIELD ZONE (Level 1) - 4 devices
            # Field devices for mixed/specialty area
            # ============================================================
            # Additional ABB drives
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "field_mixed",
             "name_pattern": "VFD-ABB-FMZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS580",
             "role": "Field VFD"},

            # Additional ABB I/O modules
            {"type": "io_module", "vendor": "abb", "count": 2, "zone": "field_mixed",
             "name_pattern": "IO-ABB-FMZ-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CI501",
             "role": "Field I/O"},
        ],
        "flows": [
            # ============================================================
            # INTRA-ZONE FLOWS - Siemens Zone
            # ============================================================
            # PROFINET cyclic IO (2-4ms) - Siemens PLCs to drives/I/O
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "source_zones": ["siemens_zone"], "target_zones": ["siemens_zone", "field_siemens"],
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # PROFIsafe safety communication (4ms)
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"],
             "source_zones": ["siemens_zone"], "target_zones": ["siemens_zone", "field_siemens"]},

            # Siemens HMI polling via S7comm+ (250ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 250,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["siemens_zone"], "target_zones": ["siemens_zone"],
             "jitter_ms": 25, "jitter_type": "uniform"},

            # ============================================================
            # INTRA-ZONE FLOWS - Rockwell Zone
            # ============================================================
            # EtherNet/IP implicit messaging (4-10ms RPI)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["drive", "io_module", "servo"],
             "source_zones": ["rockwell_zone"], "target_zones": ["rockwell_zone", "field_rockwell"],
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # CIP Safety communication (4ms Safety RPI)
            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"],
             "source_zones": ["rockwell_zone"], "target_zones": ["rockwell_zone", "field_rockwell"]},

            # Rockwell HMI polling via EtherNet/IP (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["rockwell_zone"], "target_zones": ["rockwell_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # INTRA-ZONE FLOWS - Schneider Zone
            # ============================================================
            # Modbus TCP polling (50-100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive", "io_module", "servo"],
             "source_zones": ["schneider_zone"], "target_zones": ["schneider_zone", "field_schneider"],
             "jitter_ms": 20, "jitter_type": "gaussian"},

            # Schneider HMI polling (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["schneider_zone"], "target_zones": ["schneider_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # INTRA-ZONE FLOWS - Mixed Zone
            # ============================================================
            # ABB Modbus TCP polling (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["drive", "io_module"],
             "source_zones": ["mixed_zone"], "target_zones": ["mixed_zone", "field_mixed"],
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # Specialty sensor polling (200ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["mixed_zone"], "target_zones": ["mixed_zone"],
             "jitter_ms": 30, "jitter_type": "gaussian"},

            # Instrumentation polling via Modbus (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["mixed_zone"], "target_zones": ["mixed_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ABB HMI polling (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["mixed_zone"], "target_zones": ["mixed_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # ZONE-TO-DMZ FLOWS (Supervision/Data Collection)
            # ============================================================
            # OPC UA subscriptions - SCADA to all zone PLCs (1000ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc", "safety_plc"],
             "source_zones": ["dmz"], "target_zones": ["siemens_zone", "rockwell_zone", "schneider_zone", "mixed_zone"]},

            # Historian collection via OPC UA (5000ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["siemens_zone", "rockwell_zone", "schneider_zone", "mixed_zone"]},

            # Engineering access - Siemens (2000ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["engineering_station"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["siemens_zone"]},

            # Engineering access - Rockwell (2000ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["engineering_station"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["rockwell_zone"]},

            # Central HMI multi-protocol polling (1000ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["siemens_zone"]},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["rockwell_zone"]},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["schneider_zone", "mixed_zone"]},

            # Gateway protocol translation (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["gateway"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["schneider_zone", "mixed_zone"]},

            # ============================================================
            # CROSS-ZONE FLOWS (Material Handoff Coordination)
            # ============================================================
            # Siemens → Rockwell handoff via Modbus TCP (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["siemens_zone"], "target_zones": ["rockwell_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # Rockwell → Schneider handoff via Modbus TCP (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["rockwell_zone"], "target_zones": ["schneider_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # Schneider → Mixed zone handoff via Modbus TCP (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["schneider_zone"], "target_zones": ["mixed_zone"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # ============================================================
            # INFRASTRUCTURE MONITORING
            # ============================================================
            # SNMP polling of all switches (30000ms)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["dmz"], "target_zones": ["dmz", "siemens_zone", "rockwell_zone", "schneider_zone"]},
        ],
        "zones": [
            # DMZ - Level 3.5
            {"id": "dmz", "name": "Industrial DMZ", "level": 3.5,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},

            # Production Zones - Level 2
            {"id": "siemens_zone", "name": "Siemens Production", "level": 2,
             "subnet_offset": 1, "vlan": 210, "security_level": "high"},
            {"id": "rockwell_zone", "name": "Rockwell Production", "level": 2,
             "subnet_offset": 2, "vlan": 220, "security_level": "high"},
            {"id": "schneider_zone", "name": "Schneider Production", "level": 2,
             "subnet_offset": 3, "vlan": 230, "security_level": "high"},
            {"id": "mixed_zone", "name": "Mixed/Specialty Production", "level": 2,
             "subnet_offset": 4, "vlan": 240, "security_level": "high"},

            # Field Zones - Level 1
            {"id": "field_siemens", "name": "Siemens Field", "level": 1,
             "subnet_offset": 5, "vlan": 211, "security_level": "standard"},
            {"id": "field_rockwell", "name": "Rockwell Field", "level": 1,
             "subnet_offset": 6, "vlan": 221, "security_level": "standard"},
            {"id": "field_schneider", "name": "Schneider Field", "level": 1,
             "subnet_offset": 7, "vlan": 231, "security_level": "standard"},
            {"id": "field_mixed", "name": "Mixed Field", "level": 1,
             "subnet_offset": 8, "vlan": 241, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "jitter_spike", "watchdog_timeout", "rpi_violation"],
            "protocol": ["profinet_alarm", "cip_error", "modbus_exception", "profisafe_error"],
            "sequence": ["duplicate", "out_of_order", "dropped_packet"],
            "payload": ["value_spike", "encoder_fault"],
            "network": ["broadcast_storm"],
            "security": ["unauthorized_access", "scan_activity", "replay_attack"],
        },
        "pcap_learning_hints": [
            {"protocol": "profinet", "flow_type": "cyclic_io", "priority": "high",
             "description": "PROFINET RT cycle timing from S7-1500 PLCs"},
            {"protocol": "profisafe", "flow_type": "safety", "priority": "high",
             "description": "PROFIsafe safety PLC communication patterns"},
            {"protocol": "ethernet_ip", "flow_type": "implicit_io", "priority": "high",
             "description": "EtherNet/IP RPI timing from ControlLogix PLCs"},
            {"protocol": "cip_safety", "flow_type": "safety", "priority": "high",
             "description": "CIP Safety GuardLogix communication patterns"},
            {"protocol": "modbus_tcp", "flow_type": "polling", "priority": "high",
             "description": "Modbus TCP polling patterns from Schneider/ABB PLCs"},
            {"protocol": "opc_ua", "flow_type": "subscription", "priority": "medium",
             "description": "OPC UA subscription patterns for SCADA/Historian"},
            {"protocol": "s7comm_plus", "flow_type": "hmi_polling", "priority": "medium",
             "description": "S7comm+ HMI polling patterns"},
            {"protocol": "modbus_tcp", "flow_type": "cross_zone", "priority": "high",
             "description": "Cross-zone Modbus handoff coordination traffic"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "https",
            "c2_pattern": "jittered_1m",
            "enable_exfil": True,
            "exfil_protocol": "http",
            "enable_exploits": True,
            "exploit_patterns": ["s7_stop_cpu", "cip_stop_plc", "modbus_write_scan", "historian_sqli"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "engineering_station", "scada_server", "historian"],
        },
        "total_duration_ms": 900000,  # 15 minutes (full lifecycle)
    },
}
