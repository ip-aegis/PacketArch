# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Oil and gas industry scenario templates.

Primary Vendors: Emerson (DeltaV DCS), Yokogawa (CENTUM VP), Honeywell (Experion PKS)
Supporting Vendors: ABB, Schneider, GE, HMS Networks, Cisco, Endress+Hauser
Protocol Focus: Modbus TCP (DCS-to-field, universal in O&G)

Templates cover:
- Offshore production platform (Emerson DeltaV upstream)
- Pipeline SCADA compressor station (Honeywell Experion midstream)
- Refinery crude distillation unit (Yokogawa CENTUM VP downstream)
- LNG receiving terminal (Honeywell Experion gas distribution)

Enhanced templates with:
- Safety Instrumented Systems (SIS) per IEC 61511 in dedicated zones
- CVE vulnerable firmware on DCS controllers and safety PLCs
- 38-48 devices per template with realistic zone architecture
- Custody transfer metering with Emerson ROC800/Micro Motion
"""

from typing import Any


OIL_GAS_TEMPLATES: dict[str, dict[str, Any]] = {
    # ============================================================
    # TEMPLATE 1: EMERSON DELTAV OFFSHORE PLATFORM (42 devices)
    # Upstream production with DeltaV DCS and ProSafe-RS SIS
    # ============================================================
    "emerson_offshore_platform": {
        "name": "Emerson DeltaV Offshore Production Platform",
        "description": "Offshore oil platform with four process units (e.g. wellhead control, "
                       "separation, gas compression, water injection) running on Emerson DeltaV "
                       "DCS. Dedicated SIS for emergency shutdown and burner management; "
                       "utilities zone for power generation, heating, and instrument air; full "
                       "IDMZ for vendor remote service. 98 devices across 7 zones.",
        "vertical": "oil_gas",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "triton_like", "relevance": "high", "rationale": "Safety instrumented systems (ProSafe-RS) match TRITON targeting"},
            {"playbook_id": "pipedream_like", "relevance": "medium", "rationale": "DeltaV DCS with Modbus interfaces targeted by PIPEDREAM"},
            {"playbook_id": "havex_like", "relevance": "medium", "rationale": "Offshore platform IP and production data theft"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "oil_gas",
            "description": "Wellhead production with choke control, pressure, temperature, separator level, pipeline flow",
            "key_variables": ["choke_position", "wellhead_pressure", "wellhead_temp", "flow_rate_oil", "separator_level"],
            "available_faults": ["choke_stuck", "pipeline_leak", "overpressure"],
        },
        "devices": [
            # ============================================================
            # OPERATIONS (Level 3) - 5 devices
            # Operator workstations, historian, core switch, remote access
            # ============================================================
            # Emerson DeltaV OWS - Operator Workstations
            {"type": "hmi", "vendor": "emerson", "count": 2, "zone": "operations",
             "name_pattern": "Platform_Operator_Workstation_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "OWS",
             "role": "Operator Workstation"},

            # Emerson Continuous Historian
            {"type": "historian", "vendor": "emerson", "count": 1, "zone": "operations",
             "name": "Platform_Continuous_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Continuous Historian",
             "role": "Process Historian"},

            # Cisco IE-4000 - Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "operations",
             "name": "Platform_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # HMS Flexy 205 - Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "operations",
             "name": "Platform_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # CONTROL (Level 2) - 7 devices
            # DeltaV S-series and MD Plus controllers, operator station
            # ============================================================
            # Emerson DeltaV S-series Controllers
            {"type": "dcs_controller", "vendor": "emerson", "count": 2, "zone": "control",
             "name_pattern": "DeltaV_S_Series_Controller_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "S-series",
             "firmware_version": "V14.3",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Primary DCS Controller"},

            # Emerson DeltaV MD Plus Controllers
            {"type": "dcs_controller", "vendor": "emerson", "count": 2, "zone": "control",
             "name_pattern": "DeltaV_MD_Plus_Controller_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "MD Plus",
             "role": "Secondary DCS Controller"},

            # Honeywell Experion Station - ESD Override Panel
            {"type": "hmi", "vendor": "honeywell", "count": 1, "zone": "control",
             "name": "ESD_Override_Panel", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Experion Station",
             "role": "ESD Override Panel"},

            # Cisco IE-3300 - Control Zone Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "control",
             "name_pattern": "Control_Zone_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "firmware_version": "17.9.04",
             "role": "Control Network Switch"},

            # ============================================================
            # PROCESS (Level 1) - 16 devices
            # Transmitters, flow meters, valves, analyzers, drives
            # ============================================================
            # Emerson Rosemount 3051S Pressure Transmitters
            {"type": "transmitter", "vendor": "emerson", "count": 3, "zone": "process",
             "name_pattern": "Rosemount_Pressure_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "3051S",
             "role": "Pressure Transmitter"},

            # Emerson Micro Motion 5700 Flow Meters (custody transfer)
            {"type": "flow_meter", "vendor": "emerson", "count": 2, "zone": "process",
             "name_pattern": "Custody_Transfer_Meter_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "5700",
             "role": "Custody Transfer Flow Meter"},

            # Emerson DVC6200 Valve Controllers
            {"type": "valve_positioner", "vendor": "emerson", "count": 3, "zone": "process",
             "name_pattern": "Control_Valve_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "DVC6200",
             "role": "Control Valve Positioner"},

            # Yokogawa GC8000 Gas Chromatograph
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "process",
             "name": "Gas_Chromatograph_GC8000", "protocols": ["modbus_tcp"],
             "fingerprint_model": "GC8000",
             "role": "Gas Chromatograph"},

            # Yokogawa TDLS8000 Laser Analyzer (H2S detection)
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "process",
             "name": "H2S_Laser_Analyzer", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TDLS8000",
             "role": "H2S Laser Analyzer"},

            # Yokogawa EJA530A Pressure Transmitters
            {"type": "transmitter", "vendor": "yokogawa", "count": 2, "zone": "process",
             "name_pattern": "Yokogawa_Pressure_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "EJA530A",
             "role": "Pressure Transmitter"},

            # Honeywell STT850 Temperature Transmitters
            {"type": "instrument", "vendor": "honeywell", "count": 2, "zone": "process",
             "name_pattern": "Temperature_Transmitter_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},

            # ABB ACS880 VFDs - Export Pumps
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "process",
             "name_pattern": "Export_Pump_VFD_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS880-01",
             "firmware_version": "V2.40",
             "role": "Export Pump Drive"},

            # ============================================================
            # SAFETY (Level 1) - 5 devices
            # ProSafe-RS SIS, Safety Manager F&G, safety transmitters
            # ============================================================
            # Yokogawa ProSafe-RS Safety Controllers
            {"type": "safety_plc", "vendor": "yokogawa", "count": 2, "zone": "safety",
             "name_pattern": "ProSafe_RS_Controller_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "SSC60D",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "SIL 3 Safety Controller"},

            # Honeywell Safety Manager - Fire & Gas
            {"type": "safety_plc", "vendor": "honeywell", "count": 1, "zone": "safety",
             "name": "Fire_Gas_Safety_Manager", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Safety Manager",
             "firmware_version": "V12.5",
             "role": "Fire & Gas Detection"},

            # Honeywell STT850 - Safety Temperature Transmitters
            {"type": "instrument", "vendor": "honeywell", "count": 2, "zone": "safety",
             "name_pattern": "Safety_Temperature_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Safety Temperature Transmitter"},

            # ============================================================
            # FIELD (Level 0) - 7 devices
            # ROC flow computers, tank gauges, level sensors, remote RTUs
            # ============================================================
            # Emerson ROC800L Flow Computers
            {"type": "rtu", "vendor": "emerson", "count": 2, "zone": "field",
             "name_pattern": "ROC800L_Flow_Computer_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ROC800L",
             "role": "Fiscal Flow Computer"},

            # Endress+Hauser FMP50 Level Sensors (separator levels)
            {"type": "level_sensor", "vendor": "endress_hauser", "count": 2, "zone": "field",
             "name_pattern": "Separator_Level_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Separator Level Sensor"},

            # ABB AC500-eCo RTUs (remote wellheads)
            {"type": "rtu", "vendor": "abb", "count": 3, "zone": "field",
             "name_pattern": "Wellhead_RTU_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM554-TP-ETH",
             "role": "Remote Wellhead RTU"},
        ],
        "flows": [
            # DCS controllers polling field instruments (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["transmitter"],
             "source_zones": ["control"], "target_zones": ["process"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # DCS controllers polling valve positioners (500ms - tight loop)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["valve_positioner"],
             "source_zones": ["control"], "target_zones": ["process"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # DCS controllers polling VFDs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["drive"],
             "source_zones": ["control"], "target_zones": ["process"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Safety PLCs polling safety transmitters (250ms - SIL 3)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["safety_plc"], "target_types": ["instrument"],
             "source_zones": ["safety"], "target_zones": ["safety"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # Safety PLCs polling DCS controllers (500ms - SIS/DCS interlock)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["safety_plc"], "target_types": ["dcs_controller"],
             "source_zones": ["safety"], "target_zones": ["control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # OWS polling DCS controllers (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["operations"], "target_zones": ["control"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # Historian collecting from DCS controllers (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["dcs_controller"],
             "source_zones": ["operations"], "target_zones": ["control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ROC800L flow computers polling custody transfer meters (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["rtu"], "target_types": ["flow_meter"],
             "source_zones": ["field"], "target_zones": ["process"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # DCS controllers polling gas chromatographs (5000ms - slow GC cycle)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["dcs_controller"], "target_types": ["analyzer"],
             "source_zones": ["control"], "target_zones": ["process"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # DCS controllers polling remote wellhead RTUs (3000ms - field bus)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 3000,
             "source_types": ["dcs_controller"], "target_types": ["rtu"],
             "source_zones": ["control"], "target_zones": ["field"],
             "jitter_ms": 300, "jitter_type": "gaussian"},

            # Network management — remote gateway acts as NMS proxy
            # for switch discovery on the platform (covers operations
            # core, control, and process zones).
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["remote_gateway"], "target_types": ["switch"],
             "source_zones": ["operations"],
             "target_zones": ["operations", "control", "process",
                              "safety", "field"]},

            # Remote gateway polling controllers (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["dcs_controller"],
             "source_zones": ["operations"], "target_zones": ["control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ROC800L polling separator level sensors (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["rtu"], "target_types": ["level_sensor"],
             "source_zones": ["field"], "target_zones": ["field"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ESD override panel polling DCS controllers (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # DCS controllers polling process temperature instruments (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["instrument"],
             "source_zones": ["control"], "target_zones": ["process"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "operations", "name": "Operations Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "control", "name": "DCS Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "process", "name": "Process Field Network", "level": 1,
             "subnet_offset": 2, "vlan": 121, "security_level": "standard"},
            {"id": "safety", "name": "Safety Instrumented System", "level": 1,
             "subnet_offset": 3, "vlan": 122, "security_level": "critical"},
            {"id": "field", "name": "Field Instrument Network", "level": 0,
             "subnet_offset": 4, "vlan": 130, "security_level": "standard"},
            {"id": "external", "name": "External/WAN", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
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
            "timing": ["delayed_response", "safety_trip_delay", "polling_gap"],
            "protocol": ["modbus_exception", "timeout"],
            "sequence": ["out_of_order", "duplicate"],
            "payload": ["pressure_spike", "h2s_alarm", "flow_upset", "level_deviation"],
            "network": ["wan_latency_spike"],
            "security": ["unauthorized_valve_command", "safety_bypass_attempt"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": True,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "dcs_setpoint_injection"],
            "enable_recon": True,
            "target_device_types": ["dcs_controller", "safety_plc"],
        },
        "conduits": [
            # L3 (operations) <-> L2 (control): OWS/Historian to DCS controllers
            {"id": "operations_to_control", "name": "Operations \u2194 DCS Control",
             "source_zone": "operations", "target_zone": "control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "Operator workstations, historian, and remote access gateway polling DeltaV S-series and MD Plus controllers"},
            # L2 (control) <-> L1 (process): DCS controllers to field instruments
            {"id": "control_to_process", "name": "DCS Control \u2194 Process Field",
             "source_zone": "control", "target_zone": "process",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "DCS controllers polling pressure transmitters, flow meters, valve positioners, analyzers, and VFDs"},
            # L2 (control) <-> L1 (safety): DCS controllers to safety system (SIS/DCS interlock)
            {"id": "control_to_safety", "name": "DCS Control \u2194 Safety System",
             "source_zone": "control", "target_zone": "safety",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "critical",
             "description": "Safety PLCs polling DCS controllers for SIS/DCS interlock; dedicated safety communication path"},
            # L2 (control) <-> L0 (field): DCS controllers to remote wellhead RTUs
            {"id": "control_to_field", "name": "DCS Control \u2194 Field Instruments",
             "source_zone": "control", "target_zone": "field",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "standard",
             "description": "DCS controllers polling remote wellhead RTUs and ROC800L flow computers"},
            # L1 (process) <-> L0 (field): Field RTUs to custody transfer meters
            {"id": "process_to_field", "name": "Process Field \u2194 Field Instruments",
             "source_zone": "field", "target_zone": "process",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "standard",
             "description": "ROC800L flow computers polling custody transfer Micro Motion meters"},
            # L3 (operations) -> L1 (process): SNMP network management proxy
            {"id": "operations_to_process_nms", "name": "Operations \u2194 Process (NMS)",
             "source_zone": "operations", "target_zone": "process",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Remote access gateway acting as NMS proxy for SNMP switch discovery in the process field network"},
            # L3 (operations) -> L1 (safety): SNMP network management proxy
            {"id": "operations_to_safety_nms", "name": "Operations \u2194 Safety (NMS)",
             "source_zone": "operations", "target_zone": "safety",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "critical",
             "description": "Remote access gateway acting as NMS proxy for SNMP switch discovery in the safety instrumented system network"},
            # L3 (operations) -> L0 (field): SNMP network management proxy
            {"id": "operations_to_field_nms", "name": "Operations \u2194 Field (NMS)",
             "source_zone": "operations", "target_zone": "field",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Remote access gateway acting as NMS proxy for SNMP switch discovery in the field instrument network"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 2: PIPELINE SCADA COMPRESSOR STATION (38 devices)
    # Midstream with Honeywell Experion and remote block valve RTUs
    # ============================================================
    "pipeline_scada_network": {
        "name": "Pipeline SCADA Compressor Station Network",
        "description": "Long-haul pipeline modeled as a master-remote SCADA topology: central "
                       "control room + 8 remote pump / metering stations communicating over WAN. "
                       "Same architectural pattern as a regional water utility. 84 devices "
                       "across 10 zones.",
        "vertical": "oil_gas",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high", "rationale": "Pipeline SCADA with Honeywell Experion matches PIPEDREAM capabilities"},
            {"playbook_id": "havex_like", "relevance": "medium", "rationale": "Pipeline operations data exfiltration via remote access"},
            {"playbook_id": "insider_threat", "relevance": "medium", "rationale": "Compressor station operational manipulation"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "oil_gas",
            "description": "Pipeline compressor station with wellhead, flow metering, and leak detection",
            "key_variables": ["pipeline_pressure", "flow_rate_oil", "flow_rate_gas", "separator_level"],
            "available_faults": ["pipeline_leak", "choke_stuck"],
        },
        "devices": [
            # ============================================================
            # SCADA (Level 3) - 5 devices
            # Experion server, historian, OPC gateway, switch, remote access
            # ============================================================
            # Honeywell Experion Server
            {"type": "scada_server", "vendor": "honeywell", "count": 1, "zone": "scada",
             "name": "Pipeline_SCADA_Server", "protocols": ["modbus_tcp", "dnp3", "snmp"],
             "fingerprint_model": "Experion Server",
             "role": "SCADA Server"},

            # GE Proficy Historian
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "scada",
             "name": "Pipeline_Process_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian"},

            # Kepware KEPServerEX OPC Gateway
            {"type": "gateway", "vendor": "kepware", "count": 1, "zone": "scada",
             "name": "Pipeline_OPC_Gateway", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "KEPServerEX",
             "role": "OPC UA Gateway"},

            # Cisco IE-4000 - Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "scada",
             "name": "SCADA_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # HMS Flexy 205 - Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "scada",
             "name": "Pipeline_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # COMPRESSOR CONTROL (Level 2) - 11 devices
            # Experion C300 controllers, safety, operator stations, I/O, VFDs
            # ============================================================
            # Honeywell Experion C300 Controllers
            {"type": "dcs_controller", "vendor": "honeywell", "count": 2, "zone": "compressor",
             "name_pattern": "Compressor_C300_Controller_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "C300",
             "firmware_version": "R520.2",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Compressor Controller"},

            # Honeywell Safety Manager
            {"type": "safety_plc", "vendor": "honeywell", "count": 1, "zone": "compressor",
             "name": "Compressor_Safety_Manager", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Safety Manager",
             "role": "Compressor Safety System"},

            # Honeywell Experion Station - Operator Stations
            {"type": "hmi", "vendor": "honeywell", "count": 2, "zone": "compressor",
             "name_pattern": "Compressor_Operator_Station_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Experion Station",
             "role": "Operator Station"},

            # Honeywell Series C I/O Modules
            {"type": "remote_io", "vendor": "honeywell", "count": 4, "zone": "compressor",
             "name_pattern": "Compressor_IO_Rack_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Series C I/O",
             "role": "Distributed I/O"},

            # Cisco IE-3300 - Control Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "compressor",
             "name_pattern": "Compressor_Network_Switch_{n:02d}",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "firmware_version": "17.9.04",
             "role": "Control Network Switch"},

            # ============================================================
            # METERING (Level 1) - 7 devices
            # ROC800 flow computers, Coriolis meters, GC, transmitters
            # ============================================================
            # Emerson ROC800 Flow Computers
            {"type": "rtu", "vendor": "emerson", "count": 2, "zone": "metering",
             "name_pattern": "ROC800_Flow_Computer_{n:02d}",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "ROC800",
             "firmware_version": "V3.91",
             "role": "Fiscal Flow Computer"},

            # Emerson Micro Motion 5700 Coriolis Meters
            {"type": "flow_meter", "vendor": "emerson", "count": 2, "zone": "metering",
             "name_pattern": "Coriolis_Meter_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "5700",
             "role": "Custody Transfer Meter"},

            # Yokogawa GC8000 Gas Chromatograph
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "metering",
             "name": "Metering_Gas_Chromatograph", "protocols": ["modbus_tcp"],
             "fingerprint_model": "GC8000",
             "role": "Gas Quality Analyzer"},

            # Emerson Rosemount 3051S Pressure Transmitters
            {"type": "transmitter", "vendor": "emerson", "count": 2, "zone": "metering",
             "name_pattern": "Metering_Pressure_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "3051S",
             "role": "Metering Pressure"},

            # ============================================================
            # LEAK DETECTION (Level 2) - 5 devices
            # Pipeline LDS server, pressure and temperature transmitters
            # ============================================================
            # Honeywell Pipeline LDS Server
            {"type": "plc", "vendor": "honeywell", "count": 1, "zone": "leak_detection",
             "name": "Pipeline_Leak_Detection_Server", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Pipeline LDS",
             "role": "Pipeline Leak Detection"},

            # Emerson Rosemount 3051S - Pipeline Pressure
            {"type": "transmitter", "vendor": "emerson", "count": 2, "zone": "leak_detection",
             "name_pattern": "Pipeline_Pressure_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "3051S",
             "role": "Pipeline Pressure"},

            # Honeywell STT850 - Pipeline Temperature
            {"type": "instrument", "vendor": "honeywell", "count": 2, "zone": "leak_detection",
             "name_pattern": "Pipeline_Temperature_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Pipeline Temperature"},

            # ============================================================
            # REMOTE STATIONS (Level 0) - 4 devices
            # Block valve RTUs at remote pipeline locations
            # ============================================================
            # ABB AC500-eCo RTUs at block valve stations
            {"type": "rtu", "vendor": "abb", "count": 4, "zone": "remote_stations",
             "name_pattern": "Block_Valve_Station_{n:02d}_RTU",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "PM554-TP-ETH",
             "role": "Remote Block Valve RTU"},
        ],
        "flows": [
            # C300 controllers polling Series C I/O (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["remote_io"],
             "source_zones": ["compressor"], "target_zones": ["compressor"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Safety Manager polling C300 controllers (250ms - safety interlock)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["safety_plc"], "target_types": ["dcs_controller"],
             "source_zones": ["compressor"], "target_zones": ["compressor"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # Operator stations polling C300 (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["compressor"], "target_zones": ["compressor"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # SCADA server polling C300 controllers (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["scada_server"], "target_types": ["dcs_controller"],
             "source_zones": ["scada"], "target_zones": ["compressor"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # SCADA server DNP3 polling remote block valve RTUs (5000ms - WAN)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "source_zones": ["scada"], "target_zones": ["remote_stations"],
             "jitter_ms": 1000, "jitter_type": "exponential"},

            # DNP3 unsolicited responses from remote block valve RTUs (event-driven)
            {"protocol": "dnp3", "pattern": "unsolicited", "interval_ms": 10000,
             "source_types": ["rtu"], "target_types": ["scada_server"],
             "source_zones": ["remote_stations"], "target_zones": ["scada"],
             "jitter_ms": 3000, "jitter_type": "exponential"},

            # Pipeline LDS polling pressure transmitters (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["transmitter", "instrument"],
             "source_zones": ["leak_detection"], "target_zones": ["leak_detection"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ROC800 polling custody transfer meters (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["rtu"], "target_types": ["flow_meter"],
             "source_zones": ["metering"], "target_zones": ["metering"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Historian collecting from C300 controllers (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["dcs_controller"],
             "source_zones": ["scada"], "target_zones": ["compressor"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # OPC Gateway to C300 controllers (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["gateway"], "target_types": ["dcs_controller"],
             "source_zones": ["scada"], "target_zones": ["compressor"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # SNMP monitoring switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["scada"],
             "target_zones": ["scada", "compressor"]},

            # Remote gateway polling SCADA (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["scada_server"],
             "source_zones": ["scada"], "target_zones": ["scada"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # RTU polling gas chromatograph analyzer (10s - slow GC cycle)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["rtu"], "target_types": ["analyzer"],
             "source_zones": ["metering"], "target_zones": ["metering"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # RTU polling metering pressure transmitters (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["rtu"], "target_types": ["transmitter"],
             "source_zones": ["metering"], "target_zones": ["metering"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "scada", "name": "SCADA Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "compressor", "name": "Compressor Control", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "metering", "name": "Fiscal Metering", "level": 1,
             "subnet_offset": 2, "vlan": 121, "security_level": "high"},
            {"id": "leak_detection", "name": "Leak Detection System", "level": 2,
             "subnet_offset": 3, "vlan": 115, "security_level": "critical"},
            {"id": "remote_stations", "name": "Remote Block Valve Stations", "level": 0,
             "subnet_offset": 4, "vlan": 130, "security_level": "standard"},
            {"id": "external", "name": "External/WAN", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
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
            "timing": ["delayed_response", "wan_timeout", "polling_gap"],
            "protocol": ["modbus_exception", "timeout"],
            "sequence": ["out_of_order", "duplicate"],
            "payload": ["pressure_spike", "flow_upset", "leak_false_alarm"],
            "network": ["wan_latency_spike", "communication_failover"],
            "security": ["unauthorized_valve_command", "scada_auth_bypass"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": True,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "roc_setpoint_injection"],
            "enable_recon": True,
            "target_device_types": ["dcs_controller", "rtu"],
        },
        "conduits": [
            # L3 (scada) <-> L2 (compressor): SCADA to compressor control
            {"id": "scada_to_compressor", "name": "SCADA \u2194 Compressor Control",
             "source_zone": "scada", "target_zone": "compressor",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA server, historian, and OPC gateway polling C300 controllers and SNMP monitoring switches"},
            # L3 (scada) <-> L0 (remote_stations): SCADA to remote block valve RTUs
            {"id": "scada_to_remote", "name": "SCADA \u2194 Remote Block Valves",
             "source_zone": "scada", "target_zone": "remote_stations",
             "direction": "bidirectional",
             "allowed_protocols": ["dnp3"],
             "security_level": "high",
             "description": "SCADA server DNP3 polling and receiving unsolicited responses from remote block valve station RTUs"},
            # L2 (compressor) <-> L1 (metering): Compressor control to fiscal metering
            {"id": "compressor_to_metering", "name": "Compressor Control \u2194 Metering",
             "source_zone": "compressor", "target_zone": "metering",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "C300 controllers coordinating with ROC800 flow computers and custody transfer meters"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
    },

    # ============================================================
    # TEMPLATE 3: YOKOGAWA CENTUM VP REFINERY UNIT (48 devices)
    # Downstream crude distillation with dense instrumentation
    # ============================================================
    "yokogawa_refinery_unit": {
        "name": "Yokogawa CENTUM VP Refinery Process Unit",
        "description": "Refinery process unit (CDU + downstream trains) on Yokogawa Centum CN1 "
                       "DCS with Centum HIS operator stations and EWS engineering. Dedicated "
                       "SIS, utilities zone, full IDMZ. 98 devices across 7 zones.",
        "vertical": "oil_gas",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "triton_like", "relevance": "high", "rationale": "Yokogawa ProSafe-RS SIS in refinery is classic TRITON target"},
            {"playbook_id": "pipedream_like", "relevance": "medium", "rationale": "Refinery DCS environment with multi-protocol exposure"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "oil_gas",
            "description": "Refinery unit with reactor control, separator, and compressor operations",
            "key_variables": ["choke_position", "wellhead_pressure", "flow_rate_oil", "separator_level", "pipeline_pressure"],
            "available_faults": ["choke_stuck", "overpressure", "pipeline_leak"],
        },
        "devices": [
            # ============================================================
            # ENGINEERING (Level 3) - 5 devices
            # EWS, Exaopc, Proficy Historian, switch, remote access
            # ============================================================
            # Yokogawa EWS - Engineering Workstation
            {"type": "hmi", "vendor": "yokogawa", "count": 1, "zone": "engineering",
             "name": "CDU_Engineering_Workstation", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "EWS",
             "role": "Engineering Workstation"},

            # Yokogawa Exaopc - OPC Server
            {"type": "historian", "vendor": "yokogawa", "count": 1, "zone": "engineering",
             "name": "CDU_Exaopc_Server", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Exaopc",
             "role": "OPC/Historian Server"},

            # GE Proficy Historian
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "engineering",
             "name": "Refinery_Process_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian"},

            # Cisco IE-4000 - Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "engineering",
             "name": "Engineering_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # HMS Flexy 205 - Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "engineering",
             "name": "Refinery_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # CONTROL (Level 2) - 9 devices
            # CENTUM VP FCUs, HIS operator stations, switches
            # ============================================================
            # Yokogawa CENTUM VP FCU - Atmospheric Column
            {"type": "dcs_controller", "vendor": "yokogawa", "count": 2, "zone": "control",
             "name_pattern": "Atmospheric_Column_FCU_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "AFV10D",
             "firmware_version": "R6.06",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Atmospheric Column Controller"},

            # Yokogawa CENTUM VP FCU - Vacuum Column
            {"type": "dcs_controller", "vendor": "yokogawa", "count": 2, "zone": "control",
             "name_pattern": "Vacuum_Column_FCU_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "AFV10D",
             "role": "Vacuum Column Controller"},

            # Yokogawa HIS - Operator Stations
            {"type": "hmi", "vendor": "yokogawa", "count": 3, "zone": "control",
             "name_pattern": "CDU_Operator_Station_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "HIS",
             "role": "Operator Station"},

            # Cisco IE-3300 - Control Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "control",
             "name_pattern": "Control_Zone_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "firmware_version": "17.9.04",
             "role": "Control Network Switch"},

            # ============================================================
            # PROCESS FIELD (Level 1) - 21 devices
            # Dense instrumentation: transmitters, valves, analyzers, drives
            # ============================================================
            # Emerson Rosemount 3051S Pressure Transmitters
            {"type": "transmitter", "vendor": "emerson", "count": 4, "zone": "process_field",
             "name_pattern": "CDU_Pressure_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "3051S",
             "role": "Column Pressure"},

            # Yokogawa EJA530A Pressure Transmitters
            {"type": "transmitter", "vendor": "yokogawa", "count": 3, "zone": "process_field",
             "name_pattern": "CDU_Yokogawa_Pressure_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "EJA530A",
             "role": "Process Pressure"},

            # Honeywell STT850 Temperature Transmitters
            {"type": "instrument", "vendor": "honeywell", "count": 4, "zone": "process_field",
             "name_pattern": "CDU_Temperature_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Column Temperature"},

            # Endress+Hauser FMP50 Level Sensors (column levels)
            {"type": "level_sensor", "vendor": "endress_hauser", "count": 3,
             "zone": "process_field",
             "name_pattern": "CDU_Column_Level_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Column Level"},

            # Emerson DVC6200 Valve Controllers
            {"type": "valve_positioner", "vendor": "emerson", "count": 4,
             "zone": "process_field",
             "name_pattern": "CDU_Control_Valve_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "DVC6200",
             "role": "Control Valve Positioner"},

            # Yokogawa GC8000 Gas Chromatograph (product quality)
            {"type": "analyzer", "vendor": "yokogawa", "count": 2, "zone": "process_field",
             "name_pattern": "CDU_Product_GC_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "GC8000",
             "role": "Product Quality Analyzer"},

            # Yokogawa FLXA402 pH Analyzer
            {"type": "analyzer", "vendor": "yokogawa", "count": 1, "zone": "process_field",
             "name": "CDU_pH_Analyzer", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "pH Analyzer"},

            # Emerson Micro Motion 5700 (feed flow)
            {"type": "flow_meter", "vendor": "emerson", "count": 2, "zone": "process_field",
             "name_pattern": "CDU_Feed_Flow_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "5700",
             "role": "Feed Flow Measurement"},

            # ABB ACS880 VFDs - Charge Pumps
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "process_field",
             "name_pattern": "CDU_Charge_Pump_VFD_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS880-01",
             "role": "Charge Pump Drive"},

            # ABB ACS580 VFDs - Reflux Pumps
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "process_field",
             "name_pattern": "CDU_Reflux_Pump_VFD_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS580",
             "role": "Reflux Pump Drive"},

            # ============================================================
            # SAFETY (Level 1) - 5 devices
            # ProSafe-RS SIS, Safety Manager F&G, H2S detectors
            # ============================================================
            # Yokogawa ProSafe-RS Safety Controllers
            {"type": "safety_plc", "vendor": "yokogawa", "count": 2, "zone": "safety",
             "name_pattern": "CDU_ProSafe_RS_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "SSC60D",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "SIL 3 Safety Controller"},

            # Honeywell Safety Manager - Fire & Gas
            {"type": "safety_plc", "vendor": "honeywell", "count": 1, "zone": "safety",
             "name": "CDU_Fire_Gas_Safety_Manager", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Safety Manager",
             "firmware_version": "V12.5",
             "role": "Fire & Gas Detection"},

            # Yokogawa TDLS8000 H2S Detectors
            {"type": "analyzer", "vendor": "yokogawa", "count": 2, "zone": "safety",
             "name_pattern": "CDU_H2S_Detector_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "TDLS8000",
             "role": "H2S Gas Detector"},

            # ============================================================
            # UTILITY (Level 1) - 2 devices
            # Utility PLC and analyzer
            # ============================================================
            # ABB AC500 PM590 - Utility PLC
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "utility",
             "name": "CDU_Utility_PLC", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM590-ETH",
             "firmware_version": "V2.9.0",
             "role": "Utility Controller"},

            # Honeywell UDA2182 Analyzer
            {"type": "instrument", "vendor": "honeywell", "count": 1, "zone": "utility",
             "name": "CDU_Utility_Analyzer", "protocols": ["modbus_tcp"],
             "fingerprint_model": "UDA2182",
             "role": "Utility Water Analyzer"},
        ],
        "flows": [
            # CENTUM VP FCUs polling pressure transmitters (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["transmitter"],
             "source_zones": ["control"], "target_zones": ["process_field"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # FCUs polling temperature transmitters (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["instrument"],
             "source_zones": ["control"], "target_zones": ["process_field"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # FCUs polling level sensors (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["level_sensor"],
             "source_zones": ["control"], "target_zones": ["process_field"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # FCUs polling valve controllers (250ms - tight loop control)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["dcs_controller"], "target_types": ["valve_positioner"],
             "source_zones": ["control"], "target_zones": ["process_field"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # FCUs polling VFDs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["drive"],
             "source_zones": ["control"], "target_zones": ["process_field"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # FCUs polling analyzers (10s - slow analysis cycle)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["dcs_controller"], "target_types": ["analyzer"],
             "source_zones": ["control"], "target_zones": ["process_field"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # ProSafe-RS polling safety H2S detectors (250ms - SIL 3)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["safety_plc"], "target_types": ["analyzer"],
             "source_zones": ["safety"], "target_zones": ["safety"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # ProSafe-RS interlock to CENTUM VP FCUs (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["safety_plc"], "target_types": ["dcs_controller"],
             "source_zones": ["safety"], "target_zones": ["control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # HIS operator stations polling FCUs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # EWS polling FCUs (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["engineering"], "target_zones": ["control"],
             "jitter_ms": 200, "jitter_type": "uniform"},

            # Exaopc collecting from all FCUs (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["dcs_controller"],
             "source_zones": ["engineering"], "target_zones": ["control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Utility PLC polling utility instruments (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["instrument"],
             "source_zones": ["utility"], "target_zones": ["utility"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Network management — remote gateway acts as NMS proxy
            # for switch discovery across the refinery unit.
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["remote_gateway"], "target_types": ["switch"],
             "source_zones": ["engineering"],
             "target_zones": ["engineering", "control", "process_field",
                              "safety", "utility"]},

            # Remote gateway polling Exaopc (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["historian"],
             "source_zones": ["engineering"], "target_zones": ["engineering"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # FCUs polling feed flow meters (1000ms - precise flow measurement)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["flow_meter"],
             "source_zones": ["control"], "target_zones": ["process_field"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "engineering", "name": "Engineering Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "control", "name": "DCS Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "process_field", "name": "Process Field Network", "level": 1,
             "subnet_offset": 2, "vlan": 121, "security_level": "standard"},
            {"id": "safety", "name": "Safety Instrumented System", "level": 1,
             "subnet_offset": 3, "vlan": 122, "security_level": "critical"},
            {"id": "utility", "name": "Utility Systems", "level": 1,
             "subnet_offset": 4, "vlan": 123, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
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
            "timing": ["delayed_response", "safety_trip_delay", "polling_gap"],
            "protocol": ["modbus_exception", "timeout"],
            "sequence": ["out_of_order", "duplicate"],
            "payload": ["temperature_excursion", "pressure_spike", "column_flood",
                        "product_quality_upset"],
            "network": [],
            "security": ["unauthorized_setpoint_change", "safety_bypass_attempt"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": True,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "dcs_setpoint_injection"],
            "enable_recon": True,
            "target_device_types": ["dcs_controller", "safety_plc"],
        },
        "conduits": [
            # L3 (engineering) <-> L2 (control): Engineering to DCS control
            {"id": "engineering_to_control", "name": "Engineering \u2194 DCS Control",
             "source_zone": "engineering", "target_zone": "control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "Engineering workstation, Exaopc historian, and Proficy historian polling CENTUM VP FCUs and switches"},
            # L2 (control) <-> L1 (process_field): DCS controllers to process field instruments
            {"id": "control_to_process", "name": "DCS Control \u2194 Process Field",
             "source_zone": "control", "target_zone": "process_field",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "CENTUM VP FCUs polling transmitters, valves, analyzers, level sensors, flow meters, and VFDs"},
            # L2 (control) <-> L1 (safety): DCS controllers to safety system (SIS/DCS interlock)
            {"id": "control_to_safety", "name": "DCS Control \u2194 Safety System",
             "source_zone": "control", "target_zone": "safety",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "critical",
             "description": "ProSafe-RS safety PLCs polling DCS FCUs for safety interlock; dedicated SIS communication path"},
            # L3 (engineering) -> L1 (process_field): SNMP network management proxy
            {"id": "engineering_to_process_nms", "name": "Engineering ↔ Process Field (NMS)",
             "source_zone": "engineering", "target_zone": "process_field",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Remote access gateway acting as NMS proxy for SNMP switch discovery in the process field network"},
            # L3 (engineering) -> L1 (safety): SNMP network management proxy
            {"id": "engineering_to_safety_nms", "name": "Engineering ↔ Safety (NMS)",
             "source_zone": "engineering", "target_zone": "safety",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "critical",
             "description": "Remote access gateway acting as NMS proxy for SNMP switch discovery in the safety instrumented system network"},
            # L3 (engineering) -> L1 (utility): SNMP network management proxy
            {"id": "engineering_to_utility_nms", "name": "Engineering ↔ Utility (NMS)",
             "source_zone": "engineering", "target_zone": "utility",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Remote access gateway acting as NMS proxy for SNMP switch discovery in the utility systems network"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 4: HONEYWELL EXPERION LNG TERMINAL (45 devices)
    # Gas distribution with cryogenic storage and regasification
    # ============================================================
    "honeywell_lng_terminal": {
        "name": "Honeywell Experion LNG Receiving Terminal",
        "description": "Large LNG import / export terminal with four process units on Honeywell "
                       "Experion DCS. SIL-3 Honeywell Safety Manager system, utilities zone for "
                       "cryogenic plant + boil-off + power, plus historian replication and asset "
                       "management at scale. 155 devices across 8 zones.",
        "vertical": "oil_gas",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "triton_like", "relevance": "high", "rationale": "LNG safety systems (Honeywell Safety Manager) are TRITON targets"},
            {"playbook_id": "havex_like", "relevance": "medium", "rationale": "LNG terminal operations espionage"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "oil_gas",
            "description": "LNG terminal with cryogenic storage, vaporization, and custody transfer",
            "key_variables": ["wellhead_pressure", "wellhead_temp", "flow_rate_gas", "pipeline_pressure"],
            "available_faults": ["overpressure", "pipeline_leak"],
        },
        "devices": [
            # ============================================================
            # OPERATIONS (Level 3) - 6 devices
            # Experion server, historian, OPC gateway, switch, remote access, NMS
            # ============================================================
            # Honeywell Experion Server
            {"type": "scada_server", "vendor": "honeywell", "count": 1, "zone": "operations",
             "name": "LNG_Experion_Server", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Experion Server",
             "role": "SCADA/DCS Server"},

            # Network Management Station - Paessler PRTG (SNMP monitoring)
            {"type": "nms", "vendor": "Paessler", "count": 1, "zone": "operations",
             "name": "LNG_Terminal_Network_Management_Station", "protocols": ["snmp"],
             "fingerprint_model": "PRTG Network Monitor 24",
             "architectural_role": "nms_server",
             "role": "Network Management Station"},

            # GE Proficy Historian
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "operations",
             "name": "LNG_Process_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian"},

            # Kepware KEPServerEX OPC Gateway
            # snmp: the NMS health-polls this appliance (see the pinned
            # nms->gateway snmp flow below) — the host answers as a managed node.
            {"type": "gateway", "vendor": "kepware", "count": 1, "zone": "operations",
             "name": "LNG_OPC_Gateway", "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "KEPServerEX",
             "role": "OPC UA Gateway"},

            # Cisco IE-4000 - Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "operations",
             "name": "LNG_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # HMS Flexy 205 - Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "operations",
             "name": "LNG_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # CONTROL (Level 2) - 11 devices
            # Experion C300/C200 controllers, operator stations, switches
            # ============================================================
            # Honeywell Experion C300 Controllers
            {"type": "dcs_controller", "vendor": "honeywell", "count": 3, "zone": "control",
             "name_pattern": "LNG_C300_Controller_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "C300",
             "firmware_version": "R520.2",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "DCS Controller"},

            # Honeywell Experion C200 Controller (legacy tank farm)
            {"type": "dcs_controller", "vendor": "honeywell", "count": 1, "zone": "control",
             "name": "LNG_C200_Tank_Controller",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "C200",
             "role": "Tank Farm Controller"},

            # Honeywell Experion Station - Operator Stations
            {"type": "hmi", "vendor": "honeywell", "count": 3, "zone": "control",
             "name_pattern": "LNG_Operator_Station_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Experion Station",
             "role": "Operator Station"},

            # Honeywell Series C I/O Modules
            {"type": "remote_io", "vendor": "honeywell", "count": 2, "zone": "control",
             "name_pattern": "LNG_IO_Rack_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Series C I/O",
             "role": "Distributed I/O"},

            # Cisco IE-3300 - Control Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "control",
             "name_pattern": "LNG_Control_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "firmware_version": "17.9.04",
             "role": "Control Network Switch"},

            # ============================================================
            # TANK FARM (Level 1) - 11 devices
            # Tank gauges, pressure transmitters, temperature, I/O
            # ============================================================
            # Honeywell Optiflex 6000 Tank Gauges
            {"type": "instrument", "vendor": "honeywell", "count": 4, "zone": "tank_farm",
             "name_pattern": "LNG_Tank_{n:02d}_Gauge",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Optiflex 6000",
             "role": "Servo Tank Gauge"},

            # Emerson Rosemount 3051S Pressure Transmitters
            {"type": "transmitter", "vendor": "emerson", "count": 3, "zone": "tank_farm",
             "name_pattern": "Tank_Farm_Pressure_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "3051S",
             "role": "Tank Farm Pressure"},

            # Honeywell STT850 Temperature (cryogenic)
            {"type": "instrument", "vendor": "honeywell", "count": 4, "zone": "tank_farm",
             "name_pattern": "LNG_Cryogenic_Temperature_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Cryogenic Temperature"},

            # ============================================================
            # REGASIFICATION (Level 1) - 7 devices
            # Valve controllers, VFDs, flow meters, transmitters
            # ============================================================
            # Emerson DVC6200 Valve Controllers
            {"type": "valve_positioner", "vendor": "emerson", "count": 3,
             "zone": "regasification",
             "name_pattern": "Regas_Control_Valve_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "DVC6200",
             "role": "Regasification Control Valve"},

            # ABB ACS880 VFDs - Boil-Off Gas Compressors
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "regasification",
             "name_pattern": "BOG_Compressor_VFD_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS880-01",
             "firmware_version": "V2.40",
             "role": "Boil-Off Gas Compressor"},

            # Emerson Micro Motion 5700 - Send-Out Metering
            {"type": "flow_meter", "vendor": "emerson", "count": 2, "zone": "regasification",
             "name_pattern": "Sendout_Fiscal_Meter_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "5700",
             "role": "Fiscal Send-Out Meter"},

            # ============================================================
            # SAFETY (Level 1) - 6 devices
            # Dual Safety Managers, methane detectors, combustible gas
            # ============================================================
            # Honeywell Safety Manager - Dual SIS
            {"type": "safety_plc", "vendor": "honeywell", "count": 2, "zone": "safety",
             "name_pattern": "LNG_Safety_Manager_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Safety Manager",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Cryogenic Safety System"},

            # Yokogawa TDLS8000 Methane Detectors
            {"type": "analyzer", "vendor": "yokogawa", "count": 2, "zone": "safety",
             "name_pattern": "LNG_Methane_Detector_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "TDLS8000",
             "role": "Methane Gas Detector"},

            # Honeywell UDA2182 Combustible Gas Analyzers
            {"type": "instrument", "vendor": "honeywell", "count": 2, "zone": "safety",
             "name_pattern": "LNG_Combustible_Gas_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "UDA2182",
             "role": "Combustible Gas Analyzer"},

            # ============================================================
            # MARINE TERMINAL (Level 0) - 2 devices
            # Remote RTUs at marine berths
            # ============================================================
            # Schneider SCADAPack 350 RTUs - Marine Berths
            {"type": "rtu", "vendor": "schneider", "count": 2, "zone": "marine_terminal",
             "name_pattern": "Marine_Berth_{n:02d}_RTU",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SCADAPack 350",
             "role": "Marine Terminal RTU"},
        ],
        "flows": [
            # C300 controllers polling tank gauges (2000ms - precision level)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["dcs_controller"], "target_types": ["instrument"],
             "source_zones": ["control"], "target_zones": ["tank_farm"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # C300 polling cryogenic temperature (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["instrument"],
             "source_zones": ["control"], "target_zones": ["tank_farm"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # C300 polling pressure transmitters (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["transmitter"],
             "source_zones": ["control"], "target_zones": ["tank_farm"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # C300 polling valve controllers (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["valve_positioner"],
             "source_zones": ["control"], "target_zones": ["regasification"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # C300 polling VFDs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcs_controller"], "target_types": ["drive"],
             "source_zones": ["control"], "target_zones": ["regasification"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # C300 polling custody transfer meters (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["dcs_controller"], "target_types": ["flow_meter"],
             "source_zones": ["control"], "target_zones": ["regasification"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Safety Managers polling safety instruments (100ms - SIL safety timing)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["safety_plc"],
             "target_types": ["analyzer", "instrument"],
             "source_zones": ["safety"], "target_zones": ["safety"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # Safety Manager interlock to C300 (100ms - safety timing)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["safety_plc"], "target_types": ["dcs_controller"],
             "source_zones": ["safety"], "target_zones": ["control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Operator stations polling C300 (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # SCADA server polling C300 controllers (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["scada_server"], "target_types": ["dcs_controller"],
             "source_zones": ["operations"], "target_zones": ["control"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # SCADA polling marine terminal RTUs (5000ms - WAN)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "source_zones": ["operations"], "target_zones": ["marine_terminal"],
             "jitter_ms": 1000, "jitter_type": "exponential"},

            # Historian collecting from C300 (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["dcs_controller"],
             "source_zones": ["operations"], "target_zones": ["control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # SNMP monitoring of switches (30s) — from the NMS, not SCADA
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["nms"], "target_types": ["switch"],
             "source_zones": ["operations"],
             "target_zones": ["operations", "control"]},

            # C300 controllers polling distributed I/O (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["dcs_controller"], "target_types": ["remote_io"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # NMS SNMP health-poll of the OPC gateway appliance (5000ms) —
            # the gateway defaults to wan_edge_router role; SNMP management
            # of it belongs to the NMS, not the SCADA server. Pinned to snmp
            # (auto_repair_skip) since the gateway shares no non-generic
            # protocol with the NMS — this is a legitimate appliance health poll.
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["nms"], "target_types": ["gateway"],
             "source_zones": ["operations"], "target_zones": ["operations"],
             "jitter_ms": 500, "jitter_type": "gaussian",
             "auto_repair_skip": True},

            # Remote gateway polling DCS controllers (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["dcs_controller"],
             "source_zones": ["operations"], "target_zones": ["control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "operations", "name": "Operations Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "control", "name": "Experion Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "tank_farm", "name": "Tank Farm Instruments", "level": 1,
             "subnet_offset": 2, "vlan": 121, "security_level": "standard"},
            {"id": "regasification", "name": "Regasification Unit", "level": 1,
             "subnet_offset": 3, "vlan": 122, "security_level": "standard"},
            {"id": "safety", "name": "Safety Instrumented System", "level": 1,
             "subnet_offset": 4, "vlan": 125, "security_level": "critical"},
            {"id": "marine_terminal", "name": "Marine Terminal", "level": 0,
             "subnet_offset": 5, "vlan": 130, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
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
            "timing": ["delayed_response", "safety_trip_delay", "polling_gap"],
            "protocol": ["modbus_exception", "timeout"],
            "sequence": ["out_of_order", "duplicate"],
            "payload": ["cryogenic_temperature_alarm", "methane_leak_alarm",
                        "boiloff_gas_upset", "tank_overfill"],
            "network": ["wan_latency_spike", "marine_link_failover"],
            "security": ["unauthorized_valve_command", "tank_gauge_manipulation"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": True,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "tank_gauge_attack"],
            "enable_recon": True,
            "target_device_types": ["dcs_controller", "safety_plc"],
        },
        "conduits": [
            # L3 (operations) <-> L2 (control): Operations to Experion control
            {"id": "operations_to_control", "name": "Operations \u2194 Experion Control",
             "source_zone": "operations", "target_zone": "control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp", "https"],
             "security_level": "critical",
             "description": "Experion server, historian, and OPC gateway polling C300/C200 controllers; NMS SNMP/web management of control-zone switches"},
            # L2 (control) <-> L1 (tank_farm): Experion controllers to tank farm instruments
            {"id": "control_to_tank_farm", "name": "Experion Control \u2194 Tank Farm",
             "source_zone": "control", "target_zone": "tank_farm",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "C300/C200 controllers polling tank gauges, pressure transmitters, and cryogenic temperature sensors"},
            # L2 (control) <-> L1 (regasification): Experion controllers to regasification
            {"id": "control_to_regas", "name": "Experion Control \u2194 Regasification",
             "source_zone": "control", "target_zone": "regasification",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "C300 controllers polling valve positioners, BOG compressor VFDs, and fiscal send-out meters"},
            # L2 (control) <-> L1 (safety): Experion controllers to safety system (SIS interlock)
            {"id": "control_to_safety", "name": "Experion Control \u2194 Safety System",
             "source_zone": "control", "target_zone": "safety",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "critical",
             "description": "Safety Manager PLCs polling DCS controllers for cryogenic safety interlock and gas detection"},
            # L3 (operations) <-> L0 (marine_terminal): Operations to marine terminal RTUs
            {"id": "operations_to_marine", "name": "Operations \u2194 Marine Terminal",
             "source_zone": "operations", "target_zone": "marine_terminal",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "SCADA server polling marine berth RTUs for loading/unloading operations via WAN link"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },
}
