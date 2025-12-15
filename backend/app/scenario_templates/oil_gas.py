"""Oil and gas industry scenario templates.

Enhanced with Sprint 1-6 capabilities:
- Vendor fingerprint references for hyper-realistic device emulation
- Suggested anomalies per template for testing scenarios
- PCAP learning hints for pattern extraction

Primary Vendor: Schneider Electric
- M580 ePAC for high-performance DCS/SCADA applications
- M580 Safety for SIS/ESD systems
- M340 PAC for process control
- M251/M262 Modicon for RTU/remote applications
- Altivar drives for motor control
- Magelis HMIs for operator stations
- Modbus TCP as primary protocol
"""

from typing import Any


OIL_GAS_TEMPLATES: dict[str, dict[str, Any]] = {
    "pipeline_scada": {
        "name": "Pipeline SCADA System",
        "description": "Long-distance pipeline with compressor/pump stations, valve sites, "
                       "and leak detection. Schneider M580/M340/M251 control systems with "
                       "Modbus TCP and DNP3 over satellite/microwave links.",
        "vertical": "oil_gas",
        "devices": [
            # Control Center - Schneider M580 (Hot Standby pair) with CVE vulnerabilities
            {"type": "scada_server", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["modbus_tcp", "dnp3", "opc_ua"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "SCADA Master",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # Historian
            {"type": "historian", "vendor": "schneider", "count": 1, "zone": "enterprise",
             "name_pattern": "HIST-{n:03d}", "protocols": ["opc_ua", "modbus_tcp"]},

            # Compressor/Pump Station PLCs - Schneider M340 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 6, "zone": "process",
             "name_pattern": "CS-{n:03d}", "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Compressor Station Controller",
             "cve_ids": ["CVE-2021-22779", "CVE-2019-6829"]},

            # Station RTUs - Schneider M262 Motion Controller
            {"type": "rtu", "vendor": "schneider", "count": 6, "zone": "process",
             "name_pattern": "PS-RTU-{n:03d}", "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "TM262L20MESE8T",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.002},
             "role": "Pump Station RTU"},

            # Block Valve Stations - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 15, "zone": "remote",
             "name_pattern": "BVS-{n:03d}", "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.01},
             "role": "Block Valve RTU",
             "cve_ids": ["CVE-2020-7540"]},

            # Metering Stations - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 8, "zone": "remote",
             "name_pattern": "MS-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.008},
             "role": "Metering Station RTU",
             "cve_ids": ["CVE-2020-7540"]},

            # Pig Launchers/Receivers - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 4, "zone": "remote",
             "name_pattern": "PIG-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.006},
             "role": "Pig Launcher/Receiver",
             "cve_ids": ["CVE-2020-7540"]},

            # Flow Computers - Schneider M262
            {"type": "rtu", "vendor": "schneider", "count": 10, "zone": "field",
             "name_pattern": "FC-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM262L20MESE8T",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.003},
             "role": "Flow Computer"},

            # Leak Detection System - Honeywell (specialty vendor)
            {"type": "sensor", "vendor": "honeywell", "count": 8, "zone": "process",
             "name_pattern": "LDS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "role": "Leak Detection"},

            # Gas Chromatographs - Yokogawa (specialty instrumentation)
            {"type": "sensor", "vendor": "yokogawa", "count": 4, "zone": "field",
             "name_pattern": "GC-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Gas Chromatograph"},

            # VFDs for Compressors - Schneider Altivar ATV930
            {"type": "drive", "vendor": "schneider", "count": 12, "zone": "process",
             "name_pattern": "VFD-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "Compressor Drive"},

            # Operator Workstations - Schneider Magelis with CVE vulnerabilities
            {"type": "hmi", "vendor": "schneider", "count": 4, "zone": "enterprise",
             "name_pattern": "OWS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "HMIST6700",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Station",
             "cve_ids": ["CVE-2018-7760"]},

            # Network Switches - Schneider ConneXium
            {"type": "switch", "vendor": "schneider", "count": 8, "zone": "process",
             "name_pattern": "SW-{n:03d}", "protocols": [],
             "fingerprint_model": "TCSESM083F2CU0",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # Slow polling over constrained links (30 seconds)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "jitter_ms": 3000, "jitter_type": "exponential"},
            # DNP3 polling to remote stations
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "jitter_ms": 5000, "jitter_type": "exponential"},
            # Station internal (1 second)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["rtu", "drive"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # Flow measurement (5 seconds)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["rtu"], "target_types": ["sensor"]},
            # Leak detection (500ms - critical)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["sensor"]},
            # HMI to SCADA
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["scada_server"]},
            # Historian collection (10 seconds)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 10000,
             "source_types": ["historian"], "target_types": ["scada_server"]},
            # SNMP monitoring of network switches
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Control Center", "level": 3,
             "subnet_offset": 0, "vlan": 10, "security_level": "high"},
            {"id": "process", "name": "Station Networks", "level": 2,
             "subnet_offset": 1, "vlan": 20, "security_level": "standard"},
            {"id": "field", "name": "Field Instruments", "level": 1,
             "subnet_offset": 2, "vlan": 30, "security_level": "standard"},
            {"id": "remote", "name": "Remote Sites", "level": 1,
             "subnet_offset": 3, "vlan": 40, "security_level": "minimal"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "delayed_response_satellite"],
            "protocol": ["modbus_exception", "dnp3_internal_error"],
            "sequence": [],
            "payload": ["out_of_range_value", "flow_measurement_error"],
            "network": ["packet_loss_satellite", "high_latency"],
            "security": ["unauthorized_write"],  # Valve/compressor control
        },
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "satellite_polling", "priority": "high",
             "description": "Learn timing patterns over satellite/microwave links"},
            {"protocol": "modbus_tcp", "flow_type": "flow_computer", "priority": "high",
             "description": "Capture M262 flow measurement patterns"},
            {"protocol": "modbus_tcp", "flow_type": "leak_detection", "priority": "high",
             "description": "Leak detection system communication patterns"},
        ],
        "total_duration_ms": 1200000,  # 20 minutes
        # External communications for IDS testing - satellite-resilient profile
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "dns",  # DNS for satellite resilience
            "c2_pattern": "jittered_10m",  # Slow for bandwidth constraints
            "enable_exfil": True,
            "exfil_protocol": "dns",  # DNS tunneling
            "exfil_data_size": 256,  # Small chunks for satellite
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "modbus_function_scan"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["historian", "rtu", "hmi"],
        },
    },

    "offshore_platform": {
        "name": "Offshore Production Platform",
        "description": "Offshore oil/gas platform with process control, safety systems, "
                       "and communication to shore. Schneider M580/M580 Safety for DCS "
                       "and SIS with high reliability requirements.",
        "vertical": "oil_gas",
        "devices": [
            # Process Control System (DCS) - Schneider M580 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 8, "zone": "process",
             "name_pattern": "DCS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
             "role": "DCS Controller",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # Safety Instrumented System (SIS) - Schneider M580 Safety with CVE vulnerabilities
            {"type": "safety_plc", "vendor": "schneider", "count": 4, "zone": "safety",
             "name_pattern": "SIS-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMEP586040S",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.0001},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-45789"]},

            # Emergency Shutdown System - Schneider TM5 Safety
            {"type": "safety_plc", "vendor": "schneider", "count": 2, "zone": "safety",
             "name_pattern": "ESD-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM5CSLC100FS",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.0001},
             "role": "ESD Controller"},

            # Fire & Gas System - Schneider M580 Safety with CVE vulnerabilities
            {"type": "safety_plc", "vendor": "schneider", "count": 2, "zone": "safety",
             "name_pattern": "F&G-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMEP586040S",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.0001},
             "role": "Fire & Gas Controller",
             "cve_ids": ["CVE-2022-45789"]},

            # Wellhead Controllers - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 12, "zone": "field",
             "name_pattern": "WH-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.0008, "timeout_rate": 0.0004},
             "role": "Wellhead Controller",
             "cve_ids": ["CVE-2020-7540"]},

            # Separator Controls - Schneider M340 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 4, "zone": "process",
             "name_pattern": "SEP-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Separator Controller",
             "cve_ids": ["CVE-2021-22779", "CVE-2019-6829"]},

            # Compressor Controls - Schneider M580 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 3, "zone": "process",
             "name_pattern": "COMP-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
             "role": "Compressor Controller",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # Compressor VFDs - Schneider Altivar ATV930
            {"type": "drive", "vendor": "schneider", "count": 6, "zone": "field",
             "name_pattern": "VFD-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "Compressor Drive"},

            # Remote I/O - Schneider TM3
            {"type": "remote_io", "vendor": "schneider", "count": 16, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003}},

            # Operator Stations - Schneider Magelis HMIST6700 with CVE vulnerabilities
            {"type": "hmi", "vendor": "schneider", "count": 6, "zone": "enterprise",
             "name_pattern": "OWS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "HMIST6700",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Station",
             "cve_ids": ["CVE-2018-7760"]},

            # Historian
            {"type": "historian", "vendor": "schneider", "count": 1, "zone": "enterprise",
             "name_pattern": "HIST-{n:03d}", "protocols": ["opc_ua", "modbus_tcp"]},

            # Shore Communication Gateway
            {"type": "gateway", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "SHORE-{n:03d}", "protocols": ["opc_ua", "modbus_tcp"],
             "role": "Shore Gateway"},

            # Analyzers - Yokogawa (industry standard)
            {"type": "sensor", "vendor": "yokogawa", "count": 8, "zone": "field",
             "name_pattern": "AIT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Process Analyzer"},

            # Flow Meters - Endress+Hauser (industry standard)
            {"type": "sensor", "vendor": "endress_hauser", "count": 16, "zone": "field",
             "name_pattern": "FT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Flow Transmitter"},

            # Network Switches - Schneider ConneXium
            {"type": "switch", "vendor": "schneider", "count": 8, "zone": "process",
             "name_pattern": "SW-{n:03d}", "protocols": [],
             "fingerprint_model": "TCSESM083F2CU0",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # Process control (250ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["plc"], "target_types": ["plc", "rtu", "remote_io"],
             "jitter_ms": 20, "jitter_type": "gaussian"},
            # Safety system (100ms - fast for safety)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["safety_plc"], "target_types": ["safety_plc", "remote_io"],
             "jitter_ms": 10, "jitter_type": "gaussian"},
            # Wellhead monitoring (1 second)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["rtu"]},
            # Drive control (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["drive"]},
            # Operator displays (500ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # Historian (2 seconds)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 2000,
             "source_types": ["historian"], "target_types": ["plc"]},
            # Shore reporting (30 seconds)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 30000,
             "source_types": ["gateway"], "target_types": ["historian"]},
            # Process analyzer/sensor data collection (10 seconds)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["plc"], "target_types": ["sensor"]},
            # Gateway receives data from PLCs for shore transmission
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["gateway"], "target_types": ["plc"]},
            # SNMP monitoring of network switches
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["plc"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Platform Network", "level": 3,
             "subnet_offset": 0, "vlan": 10, "security_level": "high"},
            {"id": "process", "name": "Process Control", "level": 2,
             "subnet_offset": 1, "vlan": 20, "security_level": "standard"},
            {"id": "field", "name": "Field Network", "level": 1,
             "subnet_offset": 2, "vlan": 30, "security_level": "standard"},
            {"id": "safety", "name": "Safety Network", "level": 2,
             "subnet_offset": 3, "vlan": 40, "security_level": "critical"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "watchdog_timeout"],
            "protocol": ["modbus_exception"],
            "sequence": [],
            "payload": ["esd_trigger_simulation"],
            "network": ["shore_link_loss"],
            "security": ["unauthorized_write"],  # Critical for ESD
        },
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "safety_system", "priority": "high",
             "description": "SIS/ESD communication patterns with high reliability"},
            {"protocol": "modbus_tcp", "flow_type": "m580_dcs", "priority": "high",
             "description": "Schneider M580 process control patterns"},
            {"protocol": "opc_ua", "flow_type": "shore_link", "priority": "medium",
             "description": "Shore communication over satellite"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
        # External communications for IDS testing - offshore satellite profile
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "dns",  # DNS for satellite resilience
            "c2_pattern": "jittered_10m",
            "enable_exfil": True,
            "exfil_protocol": "dns",  # DNS tunneling over satellite
            "exfil_data_size": 256,  # Small chunks for satellite bandwidth
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan"],
            "enable_recon": False,  # Avoid noisy recon on safety-critical platform
            "scan_ot_ports": False,
            "target_device_types": ["gateway", "hmi"],  # Shore-facing only
        },
    },

    "refinery_unit": {
        "name": "Refinery Process Unit",
        "description": "Petroleum refinery process unit (CDU, FCC, etc.) with Schneider M580 "
                       "DCS control, M580 Safety for SIS, advanced process control, and "
                       "comprehensive safety systems.",
        "vertical": "oil_gas",
        "devices": [
            # DCS Controllers - Schneider M580 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 12, "zone": "process",
             "name_pattern": "DCS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
             "role": "DCS Controller",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # SIS Controllers - Schneider M580 Safety with CVE vulnerabilities
            {"type": "safety_plc", "vendor": "schneider", "count": 4, "zone": "safety",
             "name_pattern": "SIS-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMEP586040S",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.0001},
             "role": "SIS Controller",
             "cve_ids": ["CVE-2022-45789"]},

            # Burner Management System - Schneider M580 Safety with CVE vulnerabilities
            {"type": "safety_plc", "vendor": "schneider", "count": 3, "zone": "safety",
             "name_pattern": "BMS-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMEP586040S",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.0001},
             "role": "Burner Management",
             "cve_ids": ["CVE-2022-45789"]},

            # Advanced Process Control Server with CVE vulnerabilities
            {"type": "scada_server", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "APC-{n:03d}", "protocols": ["opc_ua", "modbus_tcp"],
             "fingerprint_model": "BMEH586040",
             "role": "APC Server",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # Remote I/O - Schneider Advantys STB
            {"type": "remote_io", "vendor": "schneider", "count": 24, "zone": "field",
             "name_pattern": "RIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STB NIP 2311",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003}},

            # Safety I/O - Schneider TM5 Safety
            {"type": "safety_io", "vendor": "schneider", "count": 8, "zone": "safety",
             "name_pattern": "SIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM5CSLC100FS",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.0001}},

            # Analyzers (many) - Yokogawa (industry standard)
            {"type": "sensor", "vendor": "yokogawa", "count": 24, "zone": "field",
             "name_pattern": "AIT-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Process Analyzer"},

            # Transmitters - Endress+Hauser
            {"type": "sensor", "vendor": "endress_hauser", "count": 80, "zone": "field",
             "name_pattern": "XMTR-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Process Transmitter"},

            # Control Valves (via I/O) - Emerson Fisher (industry standard)
            {"type": "actuator", "vendor": "emerson", "count": 40, "zone": "field",
             "name_pattern": "CV-{n:03d}", "protocols": ["modbus_tcp"],
             "role": "Control Valve"},

            # Motor Control VFDs - Schneider Altivar ATV930
            {"type": "drive", "vendor": "schneider", "count": 15, "zone": "field",
             "name_pattern": "MCC-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "Motor Control"},

            # Auxiliary Drives - Schneider Altivar ATV320
            {"type": "drive", "vendor": "schneider", "count": 20, "zone": "field",
             "name_pattern": "AUX-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "error_config": {"exception_rate": 0.0008, "timeout_rate": 0.0004},
             "role": "Auxiliary Drive"},

            # Operator Stations - Schneider Magelis HMIST6700 with CVE vulnerabilities
            {"type": "hmi", "vendor": "schneider", "count": 8, "zone": "enterprise",
             "name_pattern": "OWS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "HMIST6700",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Station",
             "cve_ids": ["CVE-2018-7760"]},

            # Engineering Stations
            {"type": "engineering_station", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "EWS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "role": "Engineering Station"},

            # Historian
            {"type": "historian", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "HIST-{n:03d}", "protocols": ["opc_ua", "modbus_tcp"]},

            # Network Switches - Schneider ConneXium
            {"type": "switch", "vendor": "schneider", "count": 12, "zone": "process",
             "name_pattern": "SW-{n:03d}", "protocols": [],
             "fingerprint_model": "TCSESM083F2CU0",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # DCS control (100ms - fast loop control)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["remote_io", "actuator"],
             "jitter_ms": 10, "jitter_type": "gaussian"},
            # Inter-controller (250ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["plc"], "target_types": ["plc"],
             "jitter_ms": 20, "jitter_type": "gaussian"},
            # Safety system (50ms - critical timing)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 50,
             "source_types": ["safety_plc"], "target_types": ["safety_io"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
            # APC optimization (1 minute)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["plc"]},
            # Operator displays (500ms)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"]},
            # Historian (1 second)
            {"protocol": "opc_ua", "pattern": "subscription", "interval_ms": 1000,
             "source_types": ["historian"], "target_types": ["plc"]},
            # Motor control (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["drive"]},
            # Analyzer polling (10 seconds - slow changing)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["plc"], "target_types": ["sensor"]},
            # Engineering station to PLCs (programming/config)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["engineering_station"], "target_types": ["plc"]},
            # BMS safety_plc integration with DCS
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["safety_plc"]},
            # SNMP monitoring of network switches
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Plant Network", "level": 3,
             "subnet_offset": 0, "vlan": 20, "security_level": "high"},
            {"id": "process", "name": "Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 21, "security_level": "standard"},
            {"id": "field", "name": "Field Network", "level": 1,
             "subnet_offset": 2, "vlan": 22, "security_level": "standard"},
            {"id": "safety", "name": "Safety Network", "level": 2,
             "subnet_offset": 3, "vlan": 24, "security_level": "critical"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "jitter_spike"],
            "protocol": ["modbus_exception"],
            "sequence": [],
            "payload": ["setpoint_deviation", "out_of_range_value"],
            "network": [],
            "security": ["unauthorized_write"],  # Valve control
        },
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "dcs_control", "priority": "high",
             "description": "Schneider M580 DCS communication patterns"},
            {"protocol": "modbus_tcp", "flow_type": "analyzer_polling", "priority": "medium",
             "description": "Yokogawa analyzer communication patterns"},
            {"protocol": "opc_ua", "flow_type": "apc_optimization", "priority": "medium",
             "description": "Advanced process control setpoint updates"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
        # External communications for IDS testing - refinery internal network
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "https",  # HTTPS blends with enterprise traffic
            "c2_pattern": "jittered_5m",
            "enable_exfil": True,
            "exfil_protocol": "https",  # HTTPS for stealth
            "exfil_data_size": 1024,  # Larger chunks on fast internal network
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "modbus_function_scan"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "historian", "engineering_station"],
        },
    },

    "gas_gathering": {
        "name": "Gas Gathering System",
        "description": "Upstream gas gathering with wellsites, compressor stations, "
                       "and central processing facility. Schneider M580/M340/M251 control "
                       "systems with sparse SCADA over cellular.",
        "vertical": "oil_gas",
        "devices": [
            # Central Processing Facility - Schneider M580 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 4, "zone": "process",
             "name_pattern": "CPF-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0002},
             "role": "CPF Controller",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # SCADA Server - Schneider M580 with CVE vulnerabilities
            {"type": "scada_server", "vendor": "schneider", "count": 1, "zone": "enterprise",
             "name_pattern": "SCADA-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "SCADA Master",
             "cve_ids": ["CVE-2022-45789", "CVE-2022-37300"]},

            # Wellsite RTUs (many, sparse communication) - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 50, "zone": "remote",
             "name_pattern": "WELL-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.003, "timeout_rate": 0.01},
             "role": "Wellsite RTU",
             "cve_ids": ["CVE-2020-7540"]},

            # Compressor Stations - Schneider M340 with CVE vulnerabilities
            {"type": "plc", "vendor": "schneider", "count": 6, "zone": "process",
             "name_pattern": "COMP-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Compressor Station Controller",
             "cve_ids": ["CVE-2021-22779", "CVE-2019-6829"]},

            # Gathering System RTUs - Schneider M251 with CVE vulnerabilities
            {"type": "rtu", "vendor": "schneider", "count": 15, "zone": "remote",
             "name_pattern": "GS-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM251MESE",
             "error_config": {"exception_rate": 0.002, "timeout_rate": 0.008},
             "role": "Gathering RTU",
             "cve_ids": ["CVE-2020-7540"]},

            # Flow Computers - Schneider M262
            {"type": "rtu", "vendor": "schneider", "count": 20, "zone": "field",
             "name_pattern": "FC-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM262L20MESE8T",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.003},
             "role": "Flow Computer"},

            # Compressor VFDs - Schneider Altivar ATV930
            {"type": "drive", "vendor": "schneider", "count": 12, "zone": "process",
             "name_pattern": "VFD-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "error_config": {"exception_rate": 0.0006, "timeout_rate": 0.0003},
             "role": "Compressor Drive"},

            # Remote I/O - Schneider TM3
            {"type": "remote_io", "vendor": "schneider", "count": 12, "zone": "process",
             "name_pattern": "RIO-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM3DI32K",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003}},

            # Operator Stations - Schneider Magelis HMISTM6 (compact) with CVE vulnerabilities
            {"type": "hmi", "vendor": "schneider", "count": 2, "zone": "enterprise",
             "name_pattern": "OWS-{n:03d}", "protocols": ["modbus_tcp", "opc_ua"],
             "fingerprint_model": "HMISTM6",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Operator Station",
             "cve_ids": ["CVE-2018-7760"]},

            # Local HMI at CPF - Schneider Magelis HMIST6700 with CVE vulnerabilities
            {"type": "hmi", "vendor": "schneider", "count": 2, "zone": "process",
             "name_pattern": "HMI-CPF-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIST6700",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Local Panel",
             "cve_ids": ["CVE-2018-7760"]},

            # Network Switches - Schneider ConneXium
            {"type": "switch", "vendor": "schneider", "count": 6, "zone": "process",
             "name_pattern": "SW-{n:03d}", "protocols": [],
             "fingerprint_model": "TCSESM083F2CU0",
             "role": "Industrial Switch"},
        ],
        "flows": [
            # Wellsite polling (very slow - 60 seconds due to cellular)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "jitter_ms": 5000, "jitter_type": "exponential"},
            # Compressor polling (10 seconds)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "jitter_ms": 500, "jitter_type": "gaussian"},
            # CPF internal (1 second)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["rtu", "drive", "remote_io"],
             "jitter_ms": 50, "jitter_type": "uniform"},
            # Flow measurement (5 seconds)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["plc"], "target_types": ["rtu"]},
            # HMI to SCADA
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["scada_server", "plc"]},
            # SNMP monitoring of network switches
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["scada_server"], "target_types": ["switch"]},
        ],
        "zones": [
            {"id": "enterprise", "name": "Central Facility", "level": 3,
             "subnet_offset": 0, "vlan": 30, "security_level": "high"},
            {"id": "process", "name": "Process Control", "level": 2,
             "subnet_offset": 1, "vlan": 31, "security_level": "standard"},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 2, "vlan": 32, "security_level": "standard"},
            {"id": "remote", "name": "Wellsites", "level": 1,
             "subnet_offset": 3, "vlan": 33, "security_level": "minimal"},
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "delayed_response_cellular"],
            "protocol": ["modbus_exception"],
            "sequence": [],
            "payload": ["well_production_anomaly"],
            "network": ["packet_loss_cellular", "high_latency_cellular"],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "cellular_polling", "priority": "high",
             "description": "Learn timing for very slow cellular wellsite polling"},
            {"protocol": "modbus_tcp", "flow_type": "m262_flow", "priority": "high",
             "description": "Schneider M262 flow computer communication patterns"},
        ],
        "total_duration_ms": 1800000,  # 30 minutes
        # External communications for IDS testing - cellular/remote profile
        "external_comms": {
            "enable_c2": True,
            "c2_protocol": "dns",  # DNS for cellular resilience
            "c2_pattern": "jittered_10m",  # Slow for bandwidth constraints
            "enable_exfil": True,
            "exfil_protocol": "dns",  # DNS tunneling
            "exfil_data_size": 256,  # Small chunks for cellular
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan"],
            "enable_recon": False,  # Too noisy for remote sites
            "scan_ot_ports": False,
            "target_device_types": ["rtu", "hmi"],
        },
    },
}
