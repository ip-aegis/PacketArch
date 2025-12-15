"""Water and wastewater industry scenario templates.

Enhanced with Sprint 1-6 capabilities:
- Vendor fingerprint references for hyper-realistic device emulation
- Suggested anomalies per template for testing scenarios
- PCAP learning hints for pattern extraction

Primary Vendor: Schneider Electric
- M580 ePAC for SCADA/high-performance applications
- M340 PAC for process control
- M251 Modicon for compact/RTU applications
- Altivar drives for pumps/motors
- Magelis HMIs for operator stations
- Modbus TCP as primary protocol
"""

from typing import Any


WATER_TEMPLATES: dict[str, dict[str, Any]] = {
    "water_treatment": {
        "name": "Water Treatment Plant",
        "description": "Municipal water treatment facility with remote pumping stations, "
                       "chemical dosing, and filtration. Schneider M580/M340/M251 control "
                       "systems with Modbus TCP and DNP3 for SCADA.",
        "vertical": "water_wastewater",
        "devices": [
            # Central SCADA - Schneider M580 (Hot Standby pair) with CVE vulnerabilities
            {"type": "scada_server", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["modbus_tcp", "dnp3", "opc_ua"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "SCADA Master",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # Historian Server
            {"type": "historian", "vendor": "schneider", "count": 1, "zone": "enterprise",
             "name_pattern": "HIST-{n:03d}", "protocols": ["opc_ua", "modbus_tcp"]},

            # Treatment Process PLCs - Schneider M340 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 4, "zone": "process",
             "name_pattern": "PLC-TREAT-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Treatment Controller",
             "cve_ids": ["CVE-2021-22779", "CVE-2019-6829"]},

            # Chemical Dosing - Schneider M251 (compact) with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 2, "zone": "process",
             "name_pattern": "PLC-CHEM-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Chemical Dosing Controller",
             "cve_ids": ["CVE-2020-7540"]},

            # Remote Pumping Station RTUs - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 6, "zone": "remote",
             "name_pattern": "RTU-PS-{n:03d}", "protocols": ["dnp3", "modbus_tcp"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.002},
             "role": "Remote Pump Station",
             "cve_ids": ["CVE-2020-7540"]},

            # VFDs for Pumps - Schneider Altivar ATV930
            {"type": "drive", "vendor": "schneider", "count": 10, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "Pump Drive"},

            # Distributed I/O - Schneider Advantys STB
            {"type": "remote_io", "vendor": "schneider", "count": 8, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STB NIP 2311",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003}},

            # Flow Meters - Endress+Hauser (industry-standard instrumentation)
            {"type": "sensor", "vendor": "endress_hauser", "count": 12, "zone": "field",
             "name_pattern": "FT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Flow Transmitter"},

            # Level Sensors - Endress+Hauser
            {"type": "sensor", "vendor": "endress_hauser", "count": 8, "zone": "field",
             "name_pattern": "LT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Level Transmitter"},

            # Water Quality Analyzers - Yokogawa (industry-standard)
            {"type": "sensor", "vendor": "yokogawa", "count": 6, "zone": "field",
             "name_pattern": "AIT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Water Quality Analyzer"},

            # Operator Workstations - Schneider Magelis HMIST6700
            {"type": "hmi", "vendor": "schneider", "count": 3, "zone": "process",
             "name_pattern": "OWS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "HMIST6700",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Workstation"},

            # Network Switch - Schneider ConneXium
            {"type": "switch", "vendor": "schneider", "count": 4, "zone": "process",
             "name_pattern": "SW-{n:03d}", "protocols": [],
             "fingerprint_model": "TCSESM083F2CU0",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # DNP3 polling from SCADA to remote RTUs (5 second scan)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            # Modbus polling for treatment process (1 second)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["sensor", "drive", "remote_io"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # SCADA to local PLCs (2 second)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            # HMI to PLC communication (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # OPC UA subscriptions (1 second)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["scada_server"]},
            # Historian collection (10 seconds)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 10000,
             "source_types": ["historian"], "target_types": ["scada_server"]},
            # SNMP monitoring of switches (60 seconds)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Control Center", "level": 3,
             "subnet_offset": 0, "vlan": 10, "security_level": "high"},
            {"id": "process", "name": "Treatment Plant", "level": 2,
             "subnet_offset": 1, "vlan": 20, "security_level": "standard"},
            {"id": "field", "name": "Field Instruments", "level": 1,
             "subnet_offset": 2, "vlan": 30, "security_level": "standard"},
            {"id": "remote", "name": "Remote Stations", "level": 1,
             "subnet_offset": 3, "vlan": 40, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "timeout"],
            "protocol": ["modbus_exception", "dnp3_internal_error"],
            "sequence": ["unsolicited_event_storm"],
            "payload": ["out_of_range_value"],
            "network": ["packet_loss_wan"],
            "security": ["unauthorized_write"],  # Critical for chemical dosing
        },
        "pcap_learning_hints": [
            {"protocol": "dnp3", "flow_type": "scada_polling", "priority": "high",
             "description": "Learn DNP3 polling patterns over WAN links"},
            {"protocol": "modbus_tcp", "flow_type": "sensor_polling", "priority": "high",
             "description": "Flow meter and analyzer communication patterns"},
            {"protocol": "modbus_tcp", "flow_type": "vfd_control", "priority": "medium",
             "description": "Pump VFD speed control patterns"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
        # External communications for IDS testing - stealthy water utility profile
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "dns",  # DNS tunneling for stealth
            "c2_pattern": "jittered_5m",  # Slow beaconing to avoid detection
            "enable_exfil": True,
            "exfil_protocol": "dns",  # DNS exfil common in water utility attacks
            "exfil_data_size": 512,  # Small chunks via DNS
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "modbus_function_scan"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["historian", "rtu", "hmi"],
        },
    },

    "wastewater_collection": {
        "name": "Wastewater Collection System",
        "description": "Distributed wastewater collection with lift stations, force mains, "
                       "and central treatment. Schneider M580 master with M251 remote RTUs. "
                       "Heavy DNP3 for remote monitoring over cellular/radio links.",
        "vertical": "water_wastewater",
        "devices": [
            # Master Station - Schneider M580 with CVE vulnerabilities
            {"type": "scada_server", "vendor": "schneider", "count": 1, "zone": "enterprise",
             "name_pattern": "MASTER-{n:03d}", "protocols": ["dnp3", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "SCADA Master",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # Remote Lift Stations (many spread across service area) - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 25, "zone": "remote",
             "name_pattern": "LS-{n:03d}", "protocols": ["dnp3"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.005},
             "role": "Lift Station RTU",
             "cve_ids": ["CVE-2020-7540"]},

            # Main Pump Station PLCs - Schneider M340 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 2, "zone": "process",
             "name_pattern": "MPS-{n:03d}", "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Main Pump Station Controller",
             "cve_ids": ["CVE-2021-22779", "CVE-2019-6829"]},

            # Flow Monitoring Points - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 10, "zone": "remote",
             "name_pattern": "FM-{n:03d}", "protocols": ["dnp3"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.004},
             "role": "Flow Monitor RTU",
             "cve_ids": ["CVE-2020-7540"]},

            # Treatment Headworks - Schneider M340 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "process",
             "name_pattern": "HW-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Headworks Controller",
             "cve_ids": ["CVE-2021-22779", "CVE-2019-6829"]},

            # Pump VFDs at Main Station - Schneider Altivar ATV930
            {"type": "drive", "vendor": "schneider", "count": 6, "zone": "process",
             "name_pattern": "VFD-MPS-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "Main Pump Drive"},

            # HMI at Main Station - Schneider Magelis with CVE vulnerabilities
            {"type": "hmi", "vendor": "schneider", "count": 2, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIST6700",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Station",
             "cve_ids": ["CVE-2018-7760"]},

            # Remote I/O - Schneider TM3
            {"type": "remote_io", "vendor": "schneider", "count": 4, "zone": "process",
             "name_pattern": "RIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003}},
        ],
        "flows": [
            # Slow poll for remote stations (30 seconds, typical for large service area)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "jitter_ms": 2000, "jitter_type": "exponential"},
            # Faster poll for main stations (5 seconds)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            # Unsolicited events (on alarm)
            {"protocol": "dnp3", "pattern": "unsolicited", "interval_ms": 0,
             "source_types": ["rtu"], "target_types": ["scada_server"]},
            # Local Modbus at main pump station (1 second)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["drive", "remote_io"]},
            # HMI polling (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Operations Center", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "process", "name": "Main Facility", "level": 2,
             "subnet_offset": 1, "vlan": 200, "security_level": "standard"},
            {"id": "remote", "name": "Remote Sites", "level": 1,
             "subnet_offset": 2, "vlan": 300, "security_level": "minimal"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "delayed_response"],
            "protocol": ["dnp3_internal_error"],
            "sequence": ["unsolicited_event_storm", "out_of_order"],
            "payload": [],
            "network": ["packet_loss_cellular", "jitter_spike"],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "dnp3", "flow_type": "slow_polling", "priority": "high",
             "description": "Learn timing for slow cellular/radio polling"},
            {"protocol": "dnp3", "flow_type": "unsolicited", "priority": "high",
             "description": "Capture unsolicited event patterns"},
        ],
        "total_duration_ms": 900000,  # 15 minutes
        # External communications for IDS testing - distributed collection profile
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "dns",  # DNS for cellular/radio resilience
            "c2_pattern": "jittered_5m",
            "enable_exfil": True,
            "exfil_protocol": "dns",
            "exfil_data_size": 256,  # Smaller chunks for remote sites
            "enable_exploits": True,
            "exploit_patterns": ["dnp3_control_relay", "modbus_write_scan"],
            "enable_recon": False,  # Skip recon - too noisy for distributed
            "scan_ot_ports": False,
            "target_device_types": ["rtu", "hmi"],
        },
    },

    "distribution_network": {
        "name": "Water Distribution Network",
        "description": "Drinking water distribution system with storage tanks, booster stations, "
                       "and pressure monitoring. Schneider M580 SCADA with M340/M251 field controllers. "
                       "Mix of DNP3 for remote and Modbus TCP for local.",
        "vertical": "water_wastewater",
        "devices": [
            # SCADA Master - Schneider M580 with CVE vulnerabilities
            {"type": "scada_server", "vendor": "schneider", "count": 1, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["dnp3", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "SCADA Master",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # Storage Tank RTUs - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 8, "zone": "remote",
             "name_pattern": "TANK-{n:03d}", "protocols": ["dnp3"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.002},
             "role": "Tank Level RTU",
             "cve_ids": ["CVE-2020-7540"]},

            # Booster Stations - Schneider M340 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 6, "zone": "remote",
             "name_pattern": "BOOST-{n:03d}", "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Booster Station Controller",
             "cve_ids": ["CVE-2021-22779", "CVE-2019-6829"]},

            # Pressure Monitoring Points - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 15, "zone": "remote",
             "name_pattern": "PRV-{n:03d}", "protocols": ["dnp3"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.002},
             "role": "Pressure Monitor RTU",
             "cve_ids": ["CVE-2020-7540"]},

            # Booster Pump VFDs - Schneider Altivar ATV320 (compact)
            {"type": "drive", "vendor": "schneider", "count": 12, "zone": "remote",
             "name_pattern": "VFD-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "error_config": {"exception_rate": 0.0008, "timeout_rate": 0.0004},
             "role": "Booster Pump Drive"},

            # Water Quality Monitors - Yokogawa (industry-standard)
            {"type": "sensor", "vendor": "yokogawa", "count": 10, "zone": "remote",
             "name_pattern": "WQ-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Water Quality Analyzer"},

            # Flow Meters at District Boundaries - Endress+Hauser
            {"type": "sensor", "vendor": "endress_hauser", "count": 12, "zone": "remote",
             "name_pattern": "DMA-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "District Meter"},

            # Pressure Sensors - Schneider OsiSense
            {"type": "sensor", "vendor": "schneider", "count": 20, "zone": "remote",
             "name_pattern": "PT-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "OsiSense XU",
             "role": "Pressure Transmitter"},

            # Control Center HMI - Schneider Magelis with CVE vulnerabilities
            {"type": "hmi", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "OWS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "HMIST6700",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Workstation",
             "cve_ids": ["CVE-2018-7760"]},

            # Remote HMI (compact) at Booster Stations - Schneider Magelis HMISTM6 with CVE vulnerabilities
            {"type": "hmi", "vendor": "schneider", "count": 6, "zone": "remote",
             "name_pattern": "HMI-BOOST-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Local Operator Panel",
             "cve_ids": ["CVE-2018-7760"]},

            # Network Switches - Schneider ConneXium
            {"type": "switch", "vendor": "schneider", "count": 6, "zone": "remote",
             "name_pattern": "SW-{n:03d}", "protocols": [],
             "fingerprint_model": "TCSESM083F2CU0",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # Tank level polling (10 seconds)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "jitter_ms": 500, "jitter_type": "gaussian"},
            # Booster station polling (5 seconds)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            # Local Modbus at booster stations (1 second)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["drive", "sensor"]},
            # Water quality polling (60 seconds - slow changing)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["sensor"],
             "jitter_ms": 2000, "jitter_type": "uniform"},
            # Event reporting
            {"protocol": "dnp3", "pattern": "unsolicited", "interval_ms": 0,
             "source_types": ["rtu", "plc"], "target_types": ["scada_server"]},
            # HMI to SCADA
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["scada_server"]},
            # Local HMI to PLC
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # SNMP monitoring of network switches (60 seconds)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Control Center", "level": 3,
             "subnet_offset": 0, "vlan": 50, "security_level": "high"},
            {"id": "remote", "name": "Distribution Sites", "level": 1,
             "subnet_offset": 1, "vlan": 60, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "delayed_response"],
            "protocol": ["dnp3_internal_error", "modbus_exception"],
            "sequence": [],
            "payload": ["out_of_range_value", "sensor_drift"],
            "network": ["packet_loss_wan"],
            "security": ["unauthorized_read"],  # Reconnaissance detection
        },
        "pcap_learning_hints": [
            {"protocol": "dnp3", "flow_type": "distributed_polling", "priority": "high",
             "description": "Learn polling timing for geographically distributed sites"},
            {"protocol": "modbus_tcp", "flow_type": "water_quality", "priority": "medium",
             "description": "Water quality analyzer communication patterns"},
        ],
        "total_duration_ms": 1200000,  # 20 minutes
        # External communications for IDS testing - distributed network profile
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "dns",  # DNS for geographically distributed sites
            "c2_pattern": "jittered_10m",  # Very slow for large footprint
            "enable_exfil": True,
            "exfil_protocol": "dns",
            "exfil_data_size": 512,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "dnp3_control_relay"],
            "enable_recon": True,  # Recon useful for distribution mapping
            "scan_ot_ports": True,
            "target_device_types": ["rtu", "plc", "hmi"],
        },
    },
}
