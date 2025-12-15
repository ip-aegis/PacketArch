"""Energy and power industry scenario templates.

Enhanced with Sprint 1-6 capabilities:
- Vendor fingerprint references for hyper-realistic device emulation
- Suggested anomalies per template for testing scenarios
- PCAP learning hints for pattern extraction

Primary Vendor: Rockwell Automation
- ControlLogix L85E/L73 for high-performance control
- CompactLogix L33ER/L24ER-QB1B for distributed/remote control
- GuardLogix L83ES/L73S for safety-integrated systems
- PowerFlex drives for motor control
- PanelView HMIs for operator interfaces
- EtherNet/IP as primary protocol
"""

from typing import Any


ENERGY_TEMPLATES: dict[str, dict[str, Any]] = {
    "transmission_substation": {
        "name": "Transmission Substation",
        "description": "High-voltage transmission substation with protective relays, RTUs, "
                       "and SCADA connectivity. Rockwell ControlLogix/CompactLogix for "
                       "automation with EtherNet/IP, IEC 61850, and DNP3.",
        "vertical": "energy_power",
        "devices": [
            # Substation RTU/Gateway - Rockwell ControlLogix L85E with CVE vulnerabilities
            {"type": "rtu", "vendor": "rockwell", "count": 2, "zone": "process",
             "name_pattern": "RTU-{n:03d}", "protocols": ["ethernet_ip", "dnp3", "iec104"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Substation Gateway",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161", "CVE-2023-3595"]},

            # Bay Controllers - Rockwell CompactLogix L33ER with CVE vulnerabilities
            {"type": "plc", "vendor": "rockwell", "count": 6, "zone": "process",
             "name_pattern": "BCU-{n:03d}", "protocols": ["ethernet_ip", "iec104"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
             "role": "Bay Controller",
             "cve_ids": ["CVE-2021-22681"]},

            # Protection Relays - SEL (industry standard for protection)
            {"type": "protection_relay", "vendor": "sel", "count": 8, "zone": "process",
             "name_pattern": "SEL-{n:03d}", "protocols": ["iec104", "dnp3"],
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.0001},
             "role": "Line Protection"},

            # Protection Relays - ABB (transformer protection)
            {"type": "protection_relay", "vendor": "abb", "count": 6, "zone": "process",
             "name_pattern": "REL-{n:03d}", "protocols": ["iec104"],
             "role": "Transformer Protection"},

            # Protection Relays - Siemens (bus protection)
            {"type": "protection_relay", "vendor": "siemens", "count": 4, "zone": "process",
             "name_pattern": "7SJ-{n:03d}", "protocols": ["iec104"],
             "role": "Bus Protection"},

            # Metering - Schneider ION (industry standard)
            {"type": "meter", "vendor": "schneider", "count": 12, "zone": "field",
             "name_pattern": "PM-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Power Meter"},

            # Transformer Monitoring
            {"type": "sensor", "vendor": "rockwell", "count": 4, "zone": "field",
             "name_pattern": "TM-{n:03d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1734-AENT",
             "role": "Transformer Monitor"},

            # Remote I/O - Rockwell Point I/O
            {"type": "remote_io", "vendor": "rockwell", "count": 8, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002}},

            # Local HMI - Rockwell PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 2, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["ethernet_ip", "opc_ua"],
             "fingerprint_model": "PanelView Plus 7",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Station"},

            # Engineering Station
            {"type": "engineering_station", "vendor": "rockwell", "count": 1, "zone": "process",
             "name_pattern": "ENG-{n:03d}", "protocols": ["ethernet_ip", "opc_ua"],
             "role": "Engineering Workstation"},

            # Network Switch - Rockwell Stratix
            {"type": "switch", "vendor": "rockwell", "count": 4, "zone": "process",
             "name_pattern": "SW-{n:03d}", "protocols": [],
             "fingerprint_model": "Stratix 5700",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # EtherNet/IP I/O (fast cyclic)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["rtu", "plc"], "target_types": ["remote_io"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            # IEC 104 spontaneous reporting (event-driven)
            {"protocol": "iec104", "pattern": "spontaneous", "interval_ms": 0,
             "source_types": ["protection_relay", "plc"], "target_types": ["rtu"]},
            # IEC 104 general interrogation (on connect)
            {"protocol": "iec104", "pattern": "gi", "interval_ms": 60000,
             "source_types": ["rtu"], "target_types": ["protection_relay", "plc"]},
            # DNP3 to control center (integrity poll)
            {"protocol": "dnp3", "pattern": "integrity", "interval_ms": 30000,
             "source_types": ["rtu"], "target_types": [],
             "jitter_ms": 500, "jitter_type": "gaussian"},
            # Metering poll
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["rtu"], "target_types": ["meter"]},
            # HMI to PLC
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["rtu", "plc"]},
            # Engineering station to PLCs (programming/config)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["engineering_station"], "target_types": ["rtu", "plc"]},
            # Transformer monitoring (sensor data to RTU)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["rtu"], "target_types": ["sensor"]},
            # SNMP monitoring of network switches
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["rtu"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "process", "name": "Substation LAN", "level": 2,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "field", "name": "Process Bus", "level": 1,
             "subnet_offset": 1, "vlan": 101, "security_level": "standard"},
            {"id": "wan", "name": "WAN to Control Center", "level": 3,
             "subnet_offset": 2, "vlan": 200, "security_level": "critical"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "delayed_response"],
            "protocol": ["iec104_internal_error", "dnp3_internal_error", "cip_error"],
            "sequence": ["spontaneous_storm", "out_of_order"],
            "payload": [],
            "network": [],
            "security": ["unauthorized_control", "reconnaissance_scan"],
        },
        "pcap_learning_hints": [
            {"protocol": "iec104", "flow_type": "spontaneous", "priority": "high",
             "description": "Learn event reporting patterns from protective relays"},
            {"protocol": "dnp3", "flow_type": "integrity_poll", "priority": "high",
             "description": "Capture DNP3 polling to control center"},
            {"protocol": "ethernet_ip", "flow_type": "cyclic_io", "priority": "high",
             "description": "Learn EtherNet/IP I/O timing patterns"},
            {"protocol": "modbus_tcp", "flow_type": "metering", "priority": "medium",
             "description": "Power meter communication patterns"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
        # External communications for IDS testing - recon only (critical infrastructure)
        "external_comms": {
            "enable_c2": False,  # Too risky for substations
            "c2_protocol": "https",
            "c2_pattern": "jittered_30m",
            "enable_exfil": False,  # Too risky
            "exfil_protocol": "https",
            "exfil_data_size": 1024,
            "enable_exploits": False,  # Too risky
            "exploit_patterns": [],
            "enable_recon": True,  # Recon-only profile for detection testing
            "scan_ot_ports": True,
            "target_device_types": ["rtu", "plc", "engineering_station"],
        },
    },

    "distribution_feeder": {
        "name": "Distribution Feeder Automation",
        "description": "Distribution automation with reclosers, capacitor banks, and voltage regulators. "
                       "Rockwell CompactLogix controllers with DNP3 over cellular/radio backhaul.",
        "vertical": "energy_power",
        "devices": [
            # Control Center - Rockwell ControlLogix L85E with CVE vulnerabilities
            {"type": "scada_server", "vendor": "rockwell", "count": 1, "zone": "enterprise",
             "name_pattern": "DMS-{n:03d}", "protocols": ["ethernet_ip", "dnp3", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Distribution Management",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161", "CVE-2023-3595"]},

            # Substation Gateway (aggregator) - Rockwell ControlLogix L73 with CVE vulnerabilities
            {"type": "gateway", "vendor": "rockwell", "count": 3, "zone": "process",
             "name_pattern": "GW-{n:03d}", "protocols": ["ethernet_ip", "dnp3"],
             "fingerprint_model": "1756-L73",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
             "role": "Substation Gateway",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161"]},

            # Recloser Controllers - Rockwell CompactLogix L24ER-QB1B with CVE vulnerabilities
            {"type": "rtu", "vendor": "rockwell", "count": 15, "zone": "remote",
             "name_pattern": "RCL-{n:03d}", "protocols": ["dnp3"],
             "fingerprint_model": "1769-L24ER-QB1B",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.005},
             "role": "Recloser Controller",
             "cve_ids": ["CVE-2021-22681"]},

            # Capacitor Bank Controllers - Rockwell CompactLogix L24ER-QB1B with CVE vulnerabilities
            {"type": "rtu", "vendor": "rockwell", "count": 8, "zone": "remote",
             "name_pattern": "CAP-{n:03d}", "protocols": ["dnp3"],
             "fingerprint_model": "1769-L24ER-QB1B",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.005},
             "role": "Capacitor Controller",
             "cve_ids": ["CVE-2021-22681"]},

            # Voltage Regulators - Rockwell CompactLogix L33ER with CVE vulnerabilities
            {"type": "rtu", "vendor": "rockwell", "count": 6, "zone": "remote",
             "name_pattern": "VR-{n:03d}", "protocols": ["dnp3"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.004},
             "role": "Voltage Regulator Controller",
             "cve_ids": ["CVE-2021-22681"]},

            # Fault Indicators - Rockwell Point I/O
            {"type": "sensor", "vendor": "rockwell", "count": 20, "zone": "remote",
             "name_pattern": "FCI-{n:03d}", "protocols": ["dnp3"],
             "fingerprint_model": "1734-AENT",
             "error_config": {"exception_rate": 0.003, "timeout_rate": 0.006},
             "role": "Fault Current Indicator"},

            # Control Center HMI - Rockwell PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 3, "zone": "enterprise",
             "name_pattern": "HMI-{n:03d}", "protocols": ["ethernet_ip", "opc_ua"],
             "fingerprint_model": "PanelView Plus 7",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Station"},

            # Network Switch - Rockwell Stratix
            {"type": "switch", "vendor": "rockwell", "count": 3, "zone": "process",
             "name_pattern": "SW-{n:03d}", "protocols": [],
             "fingerprint_model": "Stratix 5700",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # DNP3 polling (slow due to bandwidth constraints)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["gateway"],
             "jitter_ms": 1000, "jitter_type": "exponential"},
            # Gateway to field (aggregated)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["gateway"], "target_types": ["rtu", "sensor"],
             "jitter_ms": 3000, "jitter_type": "exponential"},
            # Unsolicited responses (events)
            {"protocol": "dnp3", "pattern": "unsolicited", "interval_ms": 0,
             "source_types": ["rtu"], "target_types": ["gateway"]},
            # EtherNet/IP at control center
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["gateway"]},
            # HMI to SCADA
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["scada_server"]},
            # SNMP monitoring of network switches
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Control Center", "level": 3,
             "subnet_offset": 0, "vlan": 200, "security_level": "high"},
            {"id": "process", "name": "Substation", "level": 2,
             "subnet_offset": 1, "vlan": 201, "security_level": "standard"},
            {"id": "remote", "name": "Field Devices", "level": 1,
             "subnet_offset": 2, "vlan": 202, "security_level": "minimal"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "delayed_response"],
            "protocol": ["dnp3_internal_error"],
            "sequence": ["unsolicited_storm"],
            "payload": [],
            "network": ["packet_loss_cellular", "jitter_spike_radio"],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "dnp3", "flow_type": "slow_polling", "priority": "high",
             "description": "Learn timing for cellular/radio constrained links"},
            {"protocol": "dnp3", "flow_type": "fault_events", "priority": "high",
             "description": "Capture fault indicator event patterns"},
            {"protocol": "ethernet_ip", "flow_type": "gateway_comms", "priority": "medium",
             "description": "EtherNet/IP gateway communication patterns"},
        ],
        "total_duration_ms": 900000,  # 15 minutes
        # External communications for IDS testing - recon-focused for distribution
        "external_comms": {
            "enable_c2": False,  # Too risky for grid automation
            "c2_protocol": "https",
            "c2_pattern": "jittered_30m",
            "enable_exfil": False,  # Too risky
            "exfil_protocol": "https",
            "exfil_data_size": 1024,
            "enable_exploits": False,  # Too risky for distribution
            "exploit_patterns": [],
            "enable_recon": True,  # Recon-only for detection testing
            "scan_ot_ports": True,
            "target_device_types": ["gateway", "rtu"],
        },
    },

    "generation_plant": {
        "name": "Power Generation Plant",
        "description": "Combined cycle power plant with turbine controls, generator protection, "
                       "and balance of plant systems. Rockwell ControlLogix/GuardLogix with "
                       "EtherNet/IP for high-speed control.",
        "vertical": "energy_power",
        "devices": [
            # Turbine Control System - Rockwell ControlLogix L85E with CVE vulnerabilities
            {"type": "plc", "vendor": "rockwell", "count": 4, "zone": "process",
             "name_pattern": "TCS-{n:03d}", "protocols": ["ethernet_ip", "opc_ua"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Turbine Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161", "CVE-2023-3595"]},

            # Generator Protection - Rockwell GuardLogix L83ES (safety-rated) with CVE vulnerabilities
            {"type": "safety_plc", "vendor": "rockwell", "count": 6, "zone": "process",
             "name_pattern": "GPR-{n:03d}", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.0001},
             "role": "Generator Protection",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161"]},

            # Excitation System - Rockwell CompactLogix L33ER with CVE vulnerabilities
            {"type": "plc", "vendor": "rockwell", "count": 2, "zone": "process",
             "name_pattern": "AVR-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
             "role": "Excitation Controller",
             "cve_ids": ["CVE-2021-22681"]},

            # Balance of Plant - Rockwell ControlLogix L73 with CVE vulnerabilities
            {"type": "plc", "vendor": "rockwell", "count": 6, "zone": "process",
             "name_pattern": "BOP-{n:03d}", "protocols": ["ethernet_ip", "opc_ua"],
             "fingerprint_model": "1756-L73",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
             "role": "Balance of Plant Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161"]},

            # DCS Controllers - Rockwell ControlLogix L73 with CVE vulnerabilities
            {"type": "plc", "vendor": "rockwell", "count": 8, "zone": "process",
             "name_pattern": "DCS-{n:03d}", "protocols": ["ethernet_ip", "opc_ua"],
             "fingerprint_model": "1756-L73",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
             "role": "DCS Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2022-1161"]},

            # High-Performance Drives - Rockwell PowerFlex 753
            {"type": "drive", "vendor": "rockwell", "count": 8, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 753",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "High-Perf Drive"},

            # Auxiliary Drives - Rockwell PowerFlex 525
            {"type": "drive", "vendor": "rockwell", "count": 12, "zone": "field",
             "name_pattern": "AUX-VFD-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "error_config": {"exception_rate": 0.0008, "timeout_rate": 0.0004},
             "role": "Auxiliary Drive"},

            # Remote I/O - Rockwell FLEX 5000
            {"type": "remote_io", "vendor": "rockwell", "count": 16, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002}},

            # Historian
            {"type": "historian", "vendor": "rockwell", "count": 2, "zone": "enterprise",
             "name_pattern": "HIST-{n:03d}", "protocols": ["opc_ua", "ethernet_ip"]},

            # Operator Stations - Rockwell PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 6, "zone": "enterprise",
             "name_pattern": "OWS-{n:03d}", "protocols": ["ethernet_ip", "opc_ua"],
             "fingerprint_model": "PanelView Plus 7",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Station"},

            # Local HMI - Rockwell PanelView 800 (compact)
            {"type": "hmi", "vendor": "rockwell", "count": 8, "zone": "process",
             "name_pattern": "HMI-LOCAL-{n:03d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PanelView 800",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Local Panel"},

            # Emission Monitoring - Yokogawa (industry standard)
            {"type": "sensor", "vendor": "yokogawa", "count": 4, "zone": "field",
             "name_pattern": "CEMS-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Emission Analyzer"},

            # Network Switches - Rockwell Stratix
            {"type": "switch", "vendor": "rockwell", "count": 8, "zone": "process",
             "name_pattern": "SW-{n:03d}", "protocols": [],
             "fingerprint_model": "Stratix 5700",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # EtherNet/IP cyclic I/O (very fast for turbine control)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source_types": ["plc"], "target_types": ["remote_io", "drive"],
             "jitter_ms": 1, "jitter_type": "gaussian"},
            # Turbine control (fast)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["plc"],
             "jitter_ms": 5, "jitter_type": "uniform"},
            # Safety communication (CIP Safety)
            {"protocol": "cip_safety", "pattern": "cyclic_io", "interval_ms": 20,
             "source_types": ["safety_plc"], "target_types": ["plc", "remote_io"],
             "jitter_ms": 2, "jitter_type": "gaussian"},
            # DCS to BOP (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"]},
            # Operator displays (1 second)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # Historical data (5 seconds)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc"]},
            # Emission monitoring
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["plc"], "target_types": ["sensor"]},
            # SNMP monitoring of network switches
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["plc"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Plant Network", "level": 3,
             "subnet_offset": 0, "vlan": 50, "security_level": "high"},
            {"id": "process", "name": "Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 51, "security_level": "standard"},
            {"id": "field", "name": "Field Network", "level": 1,
             "subnet_offset": 2, "vlan": 52, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "jitter_spike"],
            "protocol": ["cip_error", "cip_safety_fault"],
            "sequence": [],
            "payload": ["setpoint_deviation"],
            "network": [],
            "security": ["unauthorized_write"],  # Critical for turbine control
        },
        "pcap_learning_hints": [
            {"protocol": "ethernet_ip", "flow_type": "turbine_control", "priority": "high",
             "description": "Learn ControlLogix turbine control communication patterns"},
            {"protocol": "cip_safety", "flow_type": "safety_io", "priority": "high",
             "description": "Capture GuardLogix CIP Safety I/O patterns"},
            {"protocol": "opc_ua", "flow_type": "historian", "priority": "medium",
             "description": "Historian data collection patterns"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
        # External communications for IDS testing - recon-only for power plants
        "external_comms": {
            "enable_c2": False,  # Too risky for power generation
            "c2_protocol": "https",
            "c2_pattern": "jittered_30m",
            "enable_exfil": False,  # Too risky
            "exfil_protocol": "https",
            "exfil_data_size": 1024,
            "enable_exploits": False,  # Too risky for power plants
            "exploit_patterns": [],
            "enable_recon": True,  # Recon-only for detection testing
            "scan_ot_ports": True,
            "target_device_types": ["plc", "safety_plc", "hmi"],
        },
    },
}
