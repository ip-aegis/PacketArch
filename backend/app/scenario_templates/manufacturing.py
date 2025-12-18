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
        "devices": [
            # Control Layer - Siemens S7-1500 PLCs (with CVE vulnerabilities)
            {"type": "plc", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "PLC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "CPU 1517-3 PN/DP",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Process Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},
            {"type": "plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "PLC-AUX-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "CPU 1511-1 PN",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2019-13945"]},

            # HMI Layer - Siemens Comfort and Basic Panels
            {"type": "hmi", "vendor": "siemens", "count": 3, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "TP1200 Comfort",
             "role": "Operator Interface"},
            {"type": "hmi", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "HMI-BASIC-{n:03d}", "protocols": ["profinet"],
             "fingerprint_model": "KTP900 Basic",
             "role": "Operator Interface"},

            # Drives - Siemens SINAMICS
            {"type": "drive", "vendor": "siemens", "count": 12, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["profinet"],
             "fingerprint_model": "SINAMICS G120C",
             "role": "Variable Frequency Drive"},

            # Distributed I/O - Siemens ET 200SP
            {"type": "io_module", "vendor": "siemens", "count": 18, "zone": "field",
             "name_pattern": "ET200-{n:03d}", "protocols": ["profinet"],
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
             "subnet_offset": 0, "vlan": 10},
            {"id": "dmz", "name": "Industrial DMZ", "level": 3.5,
             "subnet_offset": 1, "vlan": 20},
            {"id": "process", "name": "Process Control Zone", "level": 2,
             "subnet_offset": 2, "vlan": 30},
            {"id": "field", "name": "Field Device Zone", "level": 1,
             "subnet_offset": 3, "vlan": 40},
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
        "devices": [
            # Robot controllers - Siemens S7-1500 high-performance (with CVE vulnerabilities)
            {"type": "plc", "vendor": "siemens", "count": 8, "zone": "process",
             "name_pattern": "RC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "CPU 1517-3 PN/DP",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Robot Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},

            # Safety PLCs - Siemens S7-1500F with PROFIsafe (with CVE vulnerabilities)
            {"type": "safety_plc", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "SAFETY-{n:03d}", "protocols": ["profinet", "profisafe"],
             "fingerprint_model": "CPU 1516F-3 PN/DP",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2019-13945"]},

            # Vision systems - Keep SICK (specialty vendor)
            {"type": "sensor", "vendor": "sick", "count": 6, "zone": "field",
             "name_pattern": "CAM-{n:03d}", "protocols": ["profinet"],
             "role": "Vision System"},

            # Servo drives - Siemens SINAMICS S120 for motion control
            {"type": "servo", "vendor": "siemens", "count": 16, "zone": "field",
             "name_pattern": "SERVO-{n:03d}", "protocols": ["profinet"],
             "fingerprint_model": "SINAMICS S120",
             "role": "Servo Drive"},

            # Conveyor drives - Siemens SINAMICS G115D distributed
            {"type": "drive", "vendor": "siemens", "count": 8, "zone": "field",
             "name_pattern": "CONV-{n:03d}", "protocols": ["profinet"],
             "fingerprint_model": "SINAMICS G115D",
             "role": "Distributed Drive"},

            # Robot IO modules - Siemens ET 200SP
            {"type": "io_module", "vendor": "siemens", "count": 24, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["profinet"],
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
             "subnet_offset": 0, "vlan": 100},
            {"id": "process", "name": "Line Control", "level": 2,
             "subnet_offset": 1, "vlan": 200},
            {"id": "field", "name": "Cell Level", "level": 1,
             "subnet_offset": 2, "vlan": 300},
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
        "devices": [
            # Motion controllers - Siemens S7-1500 with Technology CPU (with CVE vulnerabilities)
            {"type": "plc", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "MC-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "CPU 1517-3 PN/DP",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Motion Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2020-15782"]},

            # Palletizing controllers - Siemens S7-1500 (with CVE vulnerabilities)
            {"type": "plc", "vendor": "siemens", "count": 2, "zone": "process",
             "name_pattern": "PALLET-{n:03d}", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "CPU 1511-1 PN",
             "role": "Palletizing Controller",
             "cve_ids": ["CVE-2019-13945"]},

            # Servo drives - Siemens SINAMICS S120 for motion
            {"type": "servo", "vendor": "siemens", "count": 12, "zone": "field",
             "name_pattern": "SERVO-{n:03d}", "protocols": ["profinet"],
             "fingerprint_model": "SINAMICS S120",
             "role": "Servo Drive"},

            # Barcode scanners - Keep SICK (specialty vendor)
            {"type": "sensor", "vendor": "sick", "count": 8, "zone": "field",
             "name_pattern": "SCAN-{n:03d}", "protocols": ["profinet"],
             "role": "Barcode Scanner"},

            # Label printers - Siemens I/O controlled
            {"type": "actuator", "vendor": "siemens", "count": 4, "zone": "field",
             "name_pattern": "PRINT-{n:03d}", "protocols": ["profinet"],
             "role": "Label Printer"},

            # Distributed I/O - Siemens ET 200SP
            {"type": "io_module", "vendor": "siemens", "count": 10, "zone": "field",
             "name_pattern": "ET200-{n:03d}", "protocols": ["profinet"],
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
             "subnet_offset": 0, "vlan": 50},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 1, "vlan": 51},
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
             "subnet_offset": 0, "vlan": 10},
            {"id": "dmz", "name": "Industrial DMZ", "level": 3.5,
             "subnet_offset": 1, "vlan": 20},
            {"id": "process", "name": "Process Control Zone", "level": 2,
             "subnet_offset": 2, "vlan": 30},
            {"id": "field", "name": "Field Device Zone", "level": 1,
             "subnet_offset": 3, "vlan": 40},
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
            {"type": "sensor", "vendor": "sick", "count": 6, "zone": "field",
             "name_pattern": "CAM-{n:03d}", "protocols": ["ethernet_ip"],
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
             "subnet_offset": 0, "vlan": 100},
            {"id": "process", "name": "Line Control", "level": 2,
             "subnet_offset": 1, "vlan": 200},
            {"id": "field", "name": "Cell Level", "level": 1,
             "subnet_offset": 2, "vlan": 300},
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
            {"type": "sensor", "vendor": "sick", "count": 8, "zone": "field",
             "name_pattern": "SCAN-{n:03d}", "protocols": ["ethernet_ip"],
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
             "subnet_offset": 0, "vlan": 50},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 1, "vlan": 51},
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

            # SCADA server for Modbus polling
            {"type": "scada_server", "vendor": "generic", "count": 1, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
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
             "subnet_offset": 0, "vlan": 10},
            {"id": "process", "name": "Control Zone", "level": 2,
             "subnet_offset": 1, "vlan": 20},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 2, "vlan": 30},
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
}
