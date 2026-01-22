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
            # Using BMEP582040 to match CVE affected_models for Cyber Vision detection
            {"type": "scada_server", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["modbus_tcp", "dnp3", "opc_ua"],
             "fingerprint_model": "BMEP582040",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "SCADA Master",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # Historian Server
            {"type": "historian", "vendor": "schneider", "count": 1, "zone": "enterprise",
             "name_pattern": "HIST-{n:03d}", "protocols": ["opc_ua", "modbus_tcp"],
             "role": "Historian"},

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
             "fingerprint_model": "ATV930D15N4",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "Pump Drive"},

            # Distributed I/O - Schneider Advantys STB
            {"type": "remote_io", "vendor": "schneider", "count": 8, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STBNIP2311",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Field I/O Module"},

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
             "name_pattern": "SW-{n:03d}", "protocols": ["snmp"],
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
            # Using BMEP582040 to match CVE affected_models for Cyber Vision detection
            {"type": "scada_server", "vendor": "schneider", "count": 1, "zone": "enterprise",
             "name_pattern": "MASTER-{n:03d}", "protocols": ["dnp3", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEP582040",
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
             "fingerprint_model": "ATV930D15N4",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "Main Pump Drive"},

            # HMI at Main Station - Schneider Magelis
            {"type": "hmi", "vendor": "schneider", "count": 2, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIST6700",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Station"},

            # Remote I/O - Schneider TM3
            {"type": "remote_io", "vendor": "schneider", "count": 4, "zone": "process",
             "name_pattern": "RIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Field I/O Module"},
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
            # Using BMEP582040 to match CVE affected_models for Cyber Vision detection
            {"type": "scada_server", "vendor": "schneider", "count": 1, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["dnp3", "modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEP582040",
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
             "fingerprint_model": "ATV320U22N4C",
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
             "fingerprint_model": "STBNIP2311",
             "role": "Pressure Transmitter"},

            # Control Center HMI - Schneider Magelis
            {"type": "hmi", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "OWS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "HMIST6700",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Workstation"},

            # Remote HMI (compact) at Booster Stations - Schneider Magelis HMISTM6
            {"type": "hmi", "vendor": "schneider", "count": 6, "zone": "remote",
             "name_pattern": "HMI-BOOST-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Local Operator Panel"},

            # Network Switches - Schneider ConneXium
            {"type": "switch", "vendor": "schneider", "count": 6, "zone": "remote",
             "name_pattern": "SW-{n:03d}", "protocols": ["snmp"],
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

    # ============================================================
    # HONEYWELL WATER/WASTEWATER TEMPLATES
    # ============================================================

    "honeywell_water_treatment": {
        "name": "Honeywell Experion Water Treatment Plant",
        "description": "Large municipal water treatment facility using Honeywell Experion PKS "
                       "DCS for process control. Common in large utilities and industrial water "
                       "systems. Contains critical vulnerabilities including CVSS 10.0 RCE.",
        "vertical": "water_wastewater",
        "devices": [
            # Experion PKS C300 Controllers (with critical CVE vulnerabilities)
            {"type": "dcs_controller", "vendor": "honeywell", "count": 4, "zone": "process",
             "name_pattern": "C300-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "C300",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "DCS Controller",
             "cve_ids": ["CVE-2020-10628", "CVE-2021-38397"]},

            # Experion PKS C200 Controllers (backup/smaller processes)
            {"type": "dcs_controller", "vendor": "honeywell", "count": 2, "zone": "process",
             "name_pattern": "C200-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "C200",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Secondary Controller",
             "cve_ids": ["CVE-2020-10628", "CVE-2020-6959"]},

            # Experion Server
            {"type": "scada_server", "vendor": "honeywell", "count": 2, "zone": "enterprise",
             "name_pattern": "EXPERION-SVR-{n:03d}", "protocols": ["opc_ua", "modbus_tcp"],
             "fingerprint_model": "Experion Server",
             "role": "SCADA Server",
             "cve_ids": ["CVE-2023-25078"]},

            # Honeywell Safety Manager
            {"type": "safety_plc", "vendor": "honeywell", "count": 1, "zone": "process",
             "name_pattern": "SAFETY-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Safety Manager",
             "role": "Safety Controller"},

            # Field I/O - Honeywell Series C I/O
            {"type": "remote_io", "vendor": "honeywell", "count": 12, "zone": "field",
             "name_pattern": "FIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Series C I/O",
             "role": "Field I/O Module"},

            # VFDs for Pumps - Generic Modbus drives
            {"type": "drive", "vendor": "schneider", "count": 8, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Pump Drive"},

            # Flow Meters - Endress+Hauser
            {"type": "sensor", "vendor": "endress_hauser", "count": 10, "zone": "field",
             "name_pattern": "FT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Flow Transmitter"},

            # Analyzers - Yokogawa
            {"type": "sensor", "vendor": "yokogawa", "count": 6, "zone": "field",
             "name_pattern": "AIT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Water Quality Analyzer"},

            # Operator Workstations - Experion Station
            {"type": "hmi", "vendor": "honeywell", "count": 4, "zone": "enterprise",
             "name_pattern": "OWS-{n:03d}", "protocols": ["opc_ua"],
             "fingerprint_model": "Experion Station",
             "role": "Operator Workstation"},
        ],
        "flows": [
            # DCS controller polling (250ms - fast DCS cycle)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["dcs_controller"], "target_types": ["remote_io", "sensor"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            # Server to controller (1 second)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["dcs_controller"]},
            # HMI to server (500ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["scada_server"]},
            # Drive control (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["drive"]},
            # Safety monitoring (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["safety_plc"], "target_types": ["dcs_controller"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Control Center", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "process", "name": "Treatment Process", "level": 2,
             "subnet_offset": 1, "vlan": 200, "security_level": "standard"},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 2, "vlan": 300, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "timeout"],
            "protocol": ["modbus_exception", "opc_ua_error"],
            "sequence": ["out_of_order"],
            "payload": ["out_of_range_value"],
            "network": [],
            "security": ["unauthorized_write", "file_upload_attempt"],  # CVE-2021-38397
        },
        "pcap_learning_hints": [
            {"protocol": "opc_ua", "flow_type": "dcs_communication", "priority": "high",
             "description": "Experion PKS OPC UA patterns"},
            {"protocol": "modbus_tcp", "flow_type": "field_io", "priority": "high",
             "description": "DCS to field I/O communication patterns"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "https",
            "c2_pattern": "jittered_5m",
            "enable_exfil": True,
            "exfil_protocol": "dns",
            "exfil_data_size": 1024,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "file_upload_exploit"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["dcs_controller", "scada_server", "hmi"],
        },
        "total_duration_ms": 600000,  # 10 minutes
    },

    # ============================================================
    # ABB WATER/WASTEWATER TEMPLATES
    # ============================================================

    "abb_water_treatment": {
        "name": "ABB AC500 Water Treatment Plant",
        "description": "Water treatment facility using ABB AC500 PLCs for process control. "
                       "Common in European water utilities and industrial applications. "
                       "Contains authentication bypass and buffer overflow vulnerabilities.",
        "vertical": "water_wastewater",
        "devices": [
            # ABB AC500 PM590 PLCs (main controllers with CVE vulnerabilities)
            {"type": "plc", "vendor": "abb", "count": 4, "zone": "process",
             "name_pattern": "PLC-{n:03d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "PM590-ETH",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Process Controller",
             "cve_ids": ["CVE-2021-22285"]},

            # ABB AC500 PM554 PLCs (compact/remote with buffer overflow CVE)
            {"type": "plc", "vendor": "abb", "count": 6, "zone": "remote",
             "name_pattern": "RTU-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM554-TP-ETH",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.002},
             "role": "Remote RTU",
             "cve_ids": ["CVE-2019-18253"]},

            # ABB AC500 PM583 PLCs (chemical dosing)
            {"type": "plc", "vendor": "abb", "count": 2, "zone": "process",
             "name_pattern": "CHEM-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM583-ETH",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Chemical Controller",
             "cve_ids": ["CVE-2021-22285"]},

            # ABB CP600 HMI Panels
            {"type": "hmi", "vendor": "abb", "count": 3, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Operator Panel"},

            # ABB ACS580 Drives for pumps
            {"type": "drive", "vendor": "abb", "count": 10, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS580",
             "role": "Pump Drive"},

            # ABB CI501 I/O Modules
            {"type": "remote_io", "vendor": "abb", "count": 8, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CI501",
             "role": "Remote I/O"},

            # Flow Meters - Endress+Hauser
            {"type": "sensor", "vendor": "endress_hauser", "count": 8, "zone": "field",
             "name_pattern": "FT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Flow Transmitter"},

            # Level Sensors
            {"type": "sensor", "vendor": "endress_hauser", "count": 6, "zone": "field",
             "name_pattern": "LT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Level Transmitter"},
        ],
        "flows": [
            # PLC to field devices (1 second)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["drive", "remote_io", "sensor"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            # HMI to PLC (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # Remote RTU polling (5 seconds)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["plc"], "target_types": ["plc"],
             "jitter_ms": 500, "jitter_type": "exponential"},
        ],
        "zones": [
            {"id": "process", "name": "Treatment Plant", "level": 2,
             "subnet_offset": 0, "vlan": 100, "security_level": "standard"},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 1, "vlan": 200, "security_level": "standard"},
            {"id": "remote", "name": "Remote Stations", "level": 1,
             "subnet_offset": 2, "vlan": 300, "security_level": "minimal"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "delayed_response"],
            "protocol": ["modbus_exception"],
            "sequence": ["out_of_order"],
            "payload": ["buffer_overflow_attempt"],  # CVE-2019-18253
            "network": ["packet_loss_wan"],
            "security": ["auth_bypass_attempt"],  # CVE-2021-22285
        },
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "plc_polling", "priority": "high",
             "description": "ABB AC500 Modbus communication patterns"},
            {"protocol": "ethernet_ip", "flow_type": "cip_messaging", "priority": "medium",
             "description": "ABB EtherNet/IP patterns"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "dns",
            "c2_pattern": "jittered_5m",
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "buffer_overflow"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["plc", "hmi"],
        },
        "total_duration_ms": 600000,  # 10 minutes
    },

    # ============================================================
    # SCHNEIDER LEGACY WATER/WASTEWATER TEMPLATES
    # ============================================================

    "schneider_legacy_water": {
        "name": "Schneider Legacy Water System",
        "description": "Older water/wastewater system using legacy Schneider Modicon Premium "
                       "and Quantum PLCs. Common in facilities not yet upgraded to M580/M340. "
                       "Contains hardcoded FTP credentials vulnerability (no patch available).",
        "vertical": "water_wastewater",
        "devices": [
            # Modicon Premium PLCs (legacy with hardcoded credentials - NO FIX)
            {"type": "plc", "vendor": "schneider", "count": 3, "zone": "process",
             "name_pattern": "PLC-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TSXP57204M",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.0005},
             "role": "Process Controller",
             "cve_ids": ["CVE-2018-7760"]},

            # Modicon Premium PLCs (remote pumping stations)
            {"type": "rtu", "vendor": "schneider", "count": 8, "zone": "remote",
             "name_pattern": "PS-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TSXP57154M",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.003},
             "role": "Pump Station RTU",
             "cve_ids": ["CVE-2018-7760"]},

            # Older Magelis HMIs
            {"type": "hmi", "vendor": "schneider", "count": 2, "zone": "process",
             "name_pattern": "HMI-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "Operator Panel"},

            # Older Altivar drives
            {"type": "drive", "vendor": "schneider", "count": 12, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320U22N4C",
             "role": "Pump Drive"},

            # Advantys STB I/O
            {"type": "remote_io", "vendor": "schneider", "count": 6, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STBNIP2311",
             "role": "Field I/O Module"},
        ],
        "flows": [
            # Modbus polling (2 seconds - slower legacy)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["drive", "remote_io"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            # HMI to PLC (1 second)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # Remote station polling (10 seconds)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["plc"], "target_types": ["rtu"],
             "jitter_ms": 1000, "jitter_type": "exponential"},
        ],
        "zones": [
            {"id": "process", "name": "Control Building", "level": 2,
             "subnet_offset": 0, "vlan": 50, "security_level": "standard"},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 1, "vlan": 60, "security_level": "standard"},
            {"id": "remote", "name": "Pump Stations", "level": 1,
             "subnet_offset": 2, "vlan": 70, "security_level": "minimal"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "delayed_response"],
            "protocol": ["modbus_exception"],
            "sequence": [],
            "payload": [],
            "network": ["packet_loss_wan"],
            "security": ["ftp_login_attempt", "hardcoded_cred_exploit"],  # CVE-2018-7760
        },
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "legacy_polling", "priority": "high",
             "description": "Legacy Modicon Premium communication patterns"},
        ],
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "ftp",  # FTP-based C2 exploiting hardcoded creds
            "c2_pattern": "jittered_10m",
            "enable_exfil": True,
            "exfil_protocol": "ftp",
            "exfil_data_size": 4096,
            "enable_exploits": True,
            "exploit_patterns": ["ftp_hardcoded_login", "modbus_write_scan"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["plc", "rtu"],
        },
        "total_duration_ms": 600000,  # 10 minutes
    },
}
