# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Water and wastewater industry scenario templates.

Primary Vendors: Schneider Electric, Rockwell Automation, Honeywell, Emerson, ABB
Supporting Vendors: Endress+Hauser, Yokogawa, HMS Networks, GE
Protocol Focus: Modbus TCP (primary), EtherNet/IP (secondary), DNP3 (WAN SCADA)

Templates cover:
- Municipal water treatment plants (filtration, chlorination, distribution)
- Regional pump station networks (WAN SCADA with RTUs)
- Wastewater treatment facilities (activated sludge process)
- Small utility SCADA (budget-constrained brownfield)

Enhanced templates with:
- CVE vulnerable firmware on appropriate devices
- 25-60 devices per template with realistic zone architecture
- Realistic traffic flows based on water/wastewater process timing
- Proper fingerprinting with protocol identities
"""

from typing import Any


WATER_TEMPLATES: dict[str, dict[str, Any]] = {
    # ============================================================
    # TEMPLATE 1: MUNICIPAL WATER TREATMENT PLANT (45 devices)
    # Full treatment from intake through distribution
    # ============================================================
    "municipal_water_treatment": {
        "name": "Municipal Water Treatment Plant",
        "description": "Municipal water utility with central control room and 5 remote pump / "
                       "lift stations. Central RTAC aggregates field RTUs over WAN; SCADA + "
                       "historian + engineering workstation + NMS at L3; full IDMZ stack (jump "
                       "server, remote access, patch staging). 52 devices across 7 zones.",
        "vertical": "water_wastewater",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high", "rationale": "PIPEDREAM targets water/wastewater PLCs (Schneider M580)"},
            {"playbook_id": "industroyer_like", "relevance": "medium", "rationale": "Critical infrastructure disruption pattern applicable to water utilities"},
            {"playbook_id": "insider_threat", "relevance": "medium", "rationale": "Chemical dosing manipulation via insider access"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "water_wastewater",
            "description": "Water treatment train: intake flow, coagulation, filtration, chlorination, pH control",
            "key_variables": ["intake_flow", "pump_speed", "coag_dose_rate", "chlorine_residual", "ph_level"],
            "available_faults": ["pump_failure", "chemical_feed_loss", "filter_clog"],
        },
        "devices": [
            # ============================================================
            # SCADA ZONE (Level 3) - 5 devices
            # Centralized supervision, historian, OPC gateway
            # ============================================================
            # SCADA Server - Schneider ClearSCADA
            {"type": "scada_server", "vendor": "schneider", "count": 1, "zone": "scada",
             "name": "WTP_SCADA_Server", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "HMISTM6",
             "role": "SCADA Server"},

            # Historian - GE Proficy (vulnerable)
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "scada",
             "name": "WTP_Process_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian"},

            # OPC UA Gateway - Kepware KEPServerEX
            {"type": "gateway", "vendor": "kepware", "count": 1, "zone": "scada",
             "name": "WTP_OPC_Gateway", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "KEPServerEX",
             "role": "OPC UA Gateway"},

            # Core Switch - Cisco IE-4000
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "scada",
             "name": "SCADA_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "firmware_version": "15.2(7)E6",
             "role": "Core Network Switch"},

            # EWON Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "scada",
             "name": "WTP_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # CONTROL ZONE (Level 2) - 10 devices
            # Main PLCs, safety, HMI, switches
            # ============================================================
            # Main PLCs - Schneider M580 BMEP586040 (vulnerable)
            {"type": "plc", "vendor": "schneider", "count": 2, "zone": "control",
             "name_pattern": "WTP_Main_Process_Controller_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "BMEP586040",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             },

            # Hot Standby PLC - Schneider M580 BMEH586040
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "control",
             "name": "WTP_Hot_Standby_Controller", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Hot Standby Controller",
             },

            # Auxiliary PLCs - Schneider M340 (vulnerable)
            {"type": "plc", "vendor": "schneider", "count": 2, "zone": "control",
             "name_pattern": "WTP_Auxiliary_Controller_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMXP3420302",
             "firmware_version": "V3.10",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             },

            # Safety PLC - Schneider M580 Safety
            {"type": "safety_plc", "vendor": "schneider", "count": 1, "zone": "control",
             "name": "WTP_Safety_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMEP586040S",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },

            # HMI Panels - Schneider Magelis
            {"type": "hmi", "vendor": "schneider", "count": 2, "zone": "control",
             "name_pattern": "WTP_Operator_HMI_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "Operator Interface"},

            # Industrial Switches - Cisco IE-4000
            {"type": "switch", "vendor": "Cisco", "count": 2, "zone": "control",
             "name_pattern": "Control_Zone_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Control Zone Switch"},

            # ============================================================
            # INTAKE ZONE (Level 1) - 8 devices
            # Raw water intake, screening, pumping
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "intake",
             "name": "Intake_Field_Controller", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L33ER",
             "firmware_version": "V34.014",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Intake Controller"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "intake",
             "name_pattern": "Intake_Raw_Water_Flow_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Raw Water Flow Meter"},

            # Level Transmitters - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "intake",
             "name_pattern": "Intake_Level_Transmitter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Level Transmitter"},

            # VFD Drives - ABB ACS580
            {"type": "drive", "vendor": "abb", "count": 3, "zone": "intake",
             "name_pattern": "Intake_Raw_Water_Pump_VFD_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS580",
             "role": "Raw Water Pump VFD"},

            # ============================================================
            # TREATMENT ZONE (Level 1) - 12 devices
            # Coagulation, flocculation, sedimentation, filtration
            # ============================================================
            # Remote I/O - Schneider Advantys STB
            {"type": "io_module", "vendor": "schneider", "count": 4, "zone": "treatment",
             "name_pattern": "Treatment_Remote_IO_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STBNIP2311",
             "role": "Treatment Remote I/O"},

            # Water Quality Analyzers - E+H Liquiline
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "treatment",
             "name_pattern": "Treatment_Turbidity_Analyzer_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CM442",
             "role": "Turbidity Analyzer"},

            # pH/ORP Analyzers - Yokogawa FLXA402
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "treatment",
             "name_pattern": "Treatment_pH_ORP_Analyzer_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "pH/ORP Analyzer"},

            # Turbidity Analyzers - Yokogawa SC450G
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "treatment",
             "name_pattern": "Filter_Effluent_Turbidity_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SC450G",
             "role": "Filter Turbidity Analyzer"},

            # VFD Drives - Schneider Altivar ATV930
            {"type": "drive", "vendor": "schneider", "count": 2, "zone": "treatment",
             "name_pattern": "Treatment_Process_VFD_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Treatment Process VFD"},

            # ============================================================
            # DISTRIBUTION ZONE (Level 1) - 10 devices
            # Clearwell, high service pumps, chlorination
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "distribution",
             "name": "Distribution_Field_Controller", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Distribution Controller"},

            # Chlorine Analyzers - Yokogawa RC400G
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "distribution",
             "name_pattern": "Distribution_Chlorine_Analyzer_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "RC400G",
             "role": "Chlorine Analyzer"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "distribution",
             "name_pattern": "Distribution_Flow_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Distribution Flow Meter"},

            # Level Transmitters - E+H Prosonic
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "distribution",
             "name_pattern": "Clearwell_Level_Transmitter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Clearwell Level"},

            # VFD Drives - ABB ACS880
            {"type": "drive", "vendor": "abb", "count": 3, "zone": "distribution",
             "name_pattern": "High_Service_Pump_VFD_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "firmware_version": "V2.40",
             "role": "High Service Pump VFD"},
        ],
        "flows": [
            # Main M580 PLCs polling field I/O (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["control"], "target_zones": ["treatment"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Main M580 PLCs polling VFDs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["control"], "target_zones": ["intake", "treatment", "distribution"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Main PLCs polling water quality analyzers (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["control"], "target_zones": ["intake", "treatment", "distribution"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Main PLCs to Field CompactLogix (EtherNet/IP, 1000ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["intake", "distribution"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # HMI polling main PLCs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # OPC Gateway to all PLCs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["gateway"], "target_types": ["plc"],
             "source_zones": ["scada"], "target_zones": ["control"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # SCADA server polling main PLCs (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "source_zones": ["scada"], "target_zones": ["control"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Historian collection (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["scada"], "target_zones": ["control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # SNMP monitoring of switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["scada"], "target_zones": ["scada", "control"]},

            # EWON polling PLCs for remote monitoring (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["scada"], "target_zones": ["control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Safety PLC polling main PLCs (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["safety_plc"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "scada", "name": "SCADA Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "control", "name": "Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "intake", "name": "Intake Zone", "level": 1,
             "subnet_offset": 2, "vlan": 121, "security_level": "standard"},
            {"id": "treatment", "name": "Treatment Zone", "level": 1,
             "subnet_offset": 3, "vlan": 122, "security_level": "standard"},
            {"id": "distribution", "name": "Distribution Zone", "level": 1,
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
            "timing": ["delayed_response", "watchdog_timeout"],
            "protocol": ["modbus_exception", "timeout"],
            "sequence": ["duplicate", "out_of_order"],
            "payload": ["value_spike", "chlorine_upset"],
            "network": [],
            "security": ["unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "historian_sqli"],
            "enable_recon": True,
            "target_device_types": ["hmi", "plc"],
        },
        "conduits": [
            # L3 (scada) <-> L2 (control): SCADA/OPC/Historian to PLCs
            {"id": "scada_to_control", "name": "SCADA \u2194 Control",
             "source_zone": "scada", "target_zone": "control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "SCADA server, OPC gateway, historian, and remote access gateway polling main PLCs and safety controller"},
            # L2 (control) <-> L1 (intake): PLCs to intake field devices
            {"id": "control_to_intake", "name": "Control \u2194 Intake",
             "source_zone": "control", "target_zone": "intake",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "ethernet_ip"],
             "security_level": "high",
             "description": "Main PLCs polling intake field PLC, VFDs, flow meters, and level transmitters"},
            # L2 (control) <-> L1 (treatment): PLCs to treatment field devices
            {"id": "control_to_treatment", "name": "Control \u2194 Treatment",
             "source_zone": "control", "target_zone": "treatment",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "ethernet_ip"],
             "security_level": "high",
             "description": "Main PLCs polling treatment remote I/O, analyzers, VFDs, and turbidity sensors"},
            # L2 (control) <-> L1 (distribution): PLCs to distribution field devices
            {"id": "control_to_distribution", "name": "Control \u2194 Distribution",
             "source_zone": "control", "target_zone": "distribution",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "ethernet_ip"],
             "security_level": "high",
             "description": "Main PLCs polling distribution field PLC, chlorine analyzers, flow meters, and VFDs"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 2: REGIONAL PUMP STATION NETWORK (52 devices)
    # Central SCADA with 6 remote pump stations via WAN
    # ============================================================
    "regional_pump_station_network": {
        "name": "Regional Pump Station Network",
        "description": "Regional water utility distribution network: central control room "
                       "supervising 8 remote pump stations. Standby SCADA, primary historian, "
                       "full IDMZ. Each station has a field RTU + variable-speed pumps + level / "
                       "pressure / flow instruments + valve actuators. 84 devices across 10 "
                       "zones.",
        "vertical": "water_wastewater",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "industroyer_like", "relevance": "high", "rationale": "Distributed WAN architecture mirrors INDUSTROYER grid targeting"},
            {"playbook_id": "network_recon", "relevance": "medium", "rationale": "Multi-site WAN topology for reconnaissance mapping"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "water_wastewater",
            "description": "Distributed pump station operations with flow, level, and pressure monitoring",
            "key_variables": ["intake_flow", "pump_speed", "raw_water_level", "clearwell_level"],
            "available_faults": ["pump_failure", "chemical_feed_loss"],
        },
        "devices": [
            # ============================================================
            # CENTRAL CONTROL (Level 3) - 8 devices
            # Honeywell Experion DCS, Historian, HMIs
            # ============================================================
            # DCS Controllers - Honeywell Experion C300
            {"type": "plc", "vendor": "honeywell", "count": 1, "zone": "central",
             "name": "Central_Main_DCS_Controller", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "C300",
             "firmware_version": "R520.2",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Main DCS Controller"},

            # Redundant DCS - Honeywell Experion C200
            {"type": "plc", "vendor": "honeywell", "count": 1, "zone": "central",
             "name": "Central_Standby_DCS_Controller", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "C200",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Standby DCS Controller"},

            # Historian - GE Proficy (vulnerable)
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "central",
             "name": "Central_Process_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Central Historian"},

            # HMI Workstations - Honeywell Experion Station
            {"type": "hmi", "vendor": "honeywell", "count": 2, "zone": "central",
             "name_pattern": "Central_Operator_Workstation_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Experion Station",
             "role": "Operator Workstation"},

            # Core Switch - Cisco IE-4000
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "central",
             "name": "Central_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "firmware_version": "15.2(7)E6",
             "role": "Core Network Switch"},

            # EWON Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "central",
             "name": "Central_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Central Remote Access",
             "external_comms": True},

            # Jump Server (vulnerable to BlueKeep)
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "central",
             "name": "Central_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True},

            # ============================================================
            # PUMP STATION 1 - HIGH CAPACITY (Level 1) - 8 devices
            # Major lift station with ROC800 RTU
            # ============================================================
            # RTU - Emerson ROC800
            {"type": "rtu", "vendor": "emerson", "count": 1, "zone": "station1",
             "name": "Station_1_Lift_RTU", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ROC800",
             "firmware_version": "V3.91",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Pump Station 1 RTU"},

            # High-Power VFDs - ABB ACS880
            {"type": "drive", "vendor": "abb", "count": 4, "zone": "station1",
             "name_pattern": "Station_1_High_Cap_Pump_VFD_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "firmware_version": "V2.40",
             "role": "High Capacity Pump VFD"},

            # Flow Meter - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "station1",
             "name": "Station_1_Discharge_Flow_Meter", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Station Flow Meter"},

            # Level Transmitter - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "station1",
             "name_pattern": "Station_1_Wet_Well_Level_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Wet Well Level"},

            # ============================================================
            # PUMP STATIONS 2-4 - MEDIUM CAPACITY (Level 1) - 18 devices
            # Standard pump stations with ROC800L RTUs
            # ============================================================
            # RTUs - Emerson ROC800L (3 stations)
            {"type": "rtu", "vendor": "emerson", "count": 3, "zone": "station_medium",
             "name_pattern": "Medium_Station_RTU_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ROC800L",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Medium Station RTU"},

            # VFDs - Schneider ATV320 (2 per station)
            {"type": "drive", "vendor": "schneider", "count": 6, "zone": "station_medium",
             "name_pattern": "Medium_Station_Pump_VFD_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Medium Pump VFD"},

            # Flow Meters - E+H Promag 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 3, "zone": "station_medium",
             "name_pattern": "Medium_Station_Flow_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Station Flow Meter"},

            # Level Transmitters - E+H Prosonic
            {"type": "sensor", "vendor": "endress_hauser", "count": 6, "zone": "station_medium",
             "name_pattern": "Medium_Station_Wet_Well_Level_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Wet Well Level"},

            # ============================================================
            # PUMP STATIONS 5-6 - BOOSTER (Level 1) - 10 devices
            # Small booster stations with Schneider M241 PLCs
            # ============================================================
            # PLCs - Schneider M241
            {"type": "plc", "vendor": "schneider", "count": 2, "zone": "station_booster",
             "name_pattern": "Booster_Station_PLC_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM241CE40R",
             "firmware_version": "V5.1.0.6",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Booster Station PLC"},

            # VFDs - Schneider ATV320
            {"type": "drive", "vendor": "schneider", "count": 4, "zone": "station_booster",
             "name_pattern": "Booster_Station_Pump_VFD_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Booster Pump VFD"},

            # Flow Meters - E+H Promag 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "station_booster",
             "name_pattern": "Booster_Station_Flow_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Booster Flow Meter"},

            # Pressure Transmitters - E+H
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "station_booster",
             "name_pattern": "Booster_Station_Discharge_Pressure_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Discharge Pressure"},

            # ============================================================
            # STORAGE TANKS (Level 1) - 8 devices
            # Elevated and ground storage tank monitoring
            # ============================================================
            # RTUs - Emerson ROC800L (2 tanks)
            {"type": "rtu", "vendor": "emerson", "count": 2, "zone": "storage",
             "name_pattern": "Storage_Tank_RTU_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ROC800L",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Storage Tank RTU"},

            # Level Transmitters - E+H Levelflex (primary)
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "storage",
             "name_pattern": "Storage_Tank_Primary_Level_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Primary Tank Level"},

            # Level Transmitters - E+H Prosonic (backup)
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "storage",
             "name_pattern": "Storage_Tank_Backup_Level_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Backup Tank Level"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "storage",
             "name_pattern": "Storage_Tank_Flow_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Tank Inflow/Outflow"},
        ],
        "flows": [
            # Central DCS polling RTUs via WAN (5000ms - WAN timing)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["plc"], "target_types": ["rtu"],
             "source_zones": ["central"], "target_zones": ["station1", "station_medium", "storage"],
             "jitter_ms": 500, "jitter_type": "lognormal"},

            # Central DCS polling booster PLCs (3000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 3000,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["central"], "target_zones": ["station_booster"],
             "jitter_ms": 300, "jitter_type": "lognormal"},

            # Local RTU polling VFDs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["rtu"], "target_types": ["drive"],
             "source_zones": ["station1"], "target_zones": ["station1"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Local RTU polling sensors — each station's RTU only reaches its
            # OWN wet-well/flow instruments (per-zone, not cross-station).
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["rtu"], "target_types": ["sensor"],
             "source_zones": ["station1"], "target_zones": ["station1"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["rtu"], "target_types": ["sensor"],
             "source_zones": ["station_medium"], "target_zones": ["station_medium"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["rtu"], "target_types": ["sensor"],
             "source_zones": ["storage"], "target_zones": ["storage"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Medium station RTU polling VFDs (1500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1500,
             "source_types": ["rtu"], "target_types": ["drive"],
             "source_zones": ["station_medium"], "target_zones": ["station_medium"],
             "jitter_ms": 150, "jitter_type": "gaussian"},

            # Booster PLC polling VFDs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["station_booster"], "target_zones": ["station_booster"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Booster PLC polling sensors (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["station_booster"], "target_zones": ["station_booster"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # HMI polling DCS (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["central"], "target_zones": ["central"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # Historian collection (10000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["central"], "target_zones": ["central"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # SNMP monitoring of RTUs (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["plc"], "target_types": ["rtu"],
             "source_zones": ["central"], "target_zones": ["station1", "station_medium", "storage"]},

            # Jump server SNMP monitoring of central switch (60s) — replaces
            # the removed plc→switch flow with the topologically correct
            # NMS-class source.
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["switch"],
             "source_zones": ["central"], "target_zones": ["central"]},

            # EWON polling DCS for remote monitoring (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["central"], "target_zones": ["central"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Jump server polling DCS via SNMP (60s) — admin reachability
            # check, legitimate for a small-utility scenario where the jump
            # server doubles as a quick health-monitor.
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["plc"],
             "source_zones": ["central"], "target_zones": ["central"]},
        ],
        "zones": [
            {"id": "central", "name": "Central Control", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "station1", "name": "Pump Station 1 (High Cap)", "level": 1,
             "subnet_offset": 1, "vlan": 111, "security_level": "standard"},
            {"id": "station_medium", "name": "Medium Pump Stations", "level": 1,
             "subnet_offset": 2, "vlan": 112, "security_level": "standard"},
            {"id": "station_booster", "name": "Booster Stations", "level": 1,
             "subnet_offset": 3, "vlan": 113, "security_level": "standard"},
            {"id": "storage", "name": "Storage Tanks", "level": 1,
             "subnet_offset": 4, "vlan": 114, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "cloud_services": [
            {
                "provider": "talk2m",
                "region": "us-central",
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
            "timing": ["wan_latency_spike", "timeout", "watchdog_timeout"],
            "protocol": ["modbus_exception", "dnp3_restart"],
            "sequence": ["duplicate", "dropped_packet"],
            "payload": ["level_spike", "pump_failure"],
            "network": ["wan_outage"],
            "security": ["unauthorized_remote_access", "rdp_bruteforce"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["54.95.198.117", "51.38.74.240", "185.188.32.1"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "rdp_bluekeep"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "rtu", "jump_server"],
        },
        "conduits": [
            # L3 (central) <-> L1 (station1): Central DCS to high-capacity pump station
            {"id": "central_to_station1", "name": "Central \u2194 Pump Station 1",
             "source_zone": "central", "target_zone": "station1",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "security_level": "high",
             "description": "Central DCS polling high-capacity pump station RTU and sensors via WAN"},
            # L3 (central) <-> L1 (station_medium): Central DCS to medium pump stations
            {"id": "central_to_station_medium", "name": "Central \u2194 Medium Stations",
             "source_zone": "central", "target_zone": "station_medium",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "high",
             "description": "Central DCS polling medium pump station RTUs and sensors via WAN"},
            # L3 (central) <-> L1 (station_booster): Central DCS to booster stations
            {"id": "central_to_station_booster", "name": "Central \u2194 Booster Stations",
             "source_zone": "central", "target_zone": "station_booster",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Central DCS polling booster station PLCs and sensors"},
            # L3 (central) <-> L1 (storage): Central DCS to storage tanks
            {"id": "central_to_storage", "name": "Central \u2194 Storage Tanks",
             "source_zone": "central", "target_zone": "storage",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "high",
             "description": "Central DCS polling storage tank RTUs, level transmitters, and flow meters via WAN"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
    },

    # ============================================================
    # TEMPLATE 3: WASTEWATER TREATMENT FACILITY (58 devices)
    # Activated sludge process with full treatment train
    # ============================================================
    "wastewater_treatment_facility": {
        "name": "Wastewater Treatment Facility",
        "description": "Multi-stage wastewater treatment plant modeled as 8 process / lift "
                       "stations under central RTAC supervision. Same master-remote SCADA "
                       "pattern as a regional distribution utility — central operations + remote "
                       "field RTUs + IDMZ. 84 devices across 10 zones.",
        "vertical": "water_wastewater",
        "phase_preset": "full_lifecycle",
        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high", "rationale": "PIPEDREAM targets wastewater treatment PLC environments"},
            {"playbook_id": "insider_threat", "relevance": "medium", "rationale": "Effluent quality manipulation via process tampering"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "water_wastewater",
            "description": "Wastewater treatment process with aeration, settling, and effluent monitoring",
            "key_variables": ["intake_flow", "pump_speed", "coag_dose_rate", "ph_level"],
            "available_faults": ["pump_failure", "chemical_feed_loss"],
        },
        "devices": [
            # ============================================================
            # SCADA/DMZ (Level 3.5) - 6 devices
            # ============================================================
            # Historian - GE Proficy (vulnerable)
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "dmz",
             "name": "WWTP_Process_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "firmware_version": "8.0",
             "role": "Process Historian"},

            # OPC UA Gateway - Kepware KEPServerEX
            {"type": "gateway", "vendor": "kepware", "count": 1, "zone": "dmz",
             "name": "WWTP_OPC_Gateway", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "KEPServerEX",
             "role": "OPC UA Gateway"},

            # Central HMI - Rockwell PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "dmz",
             "name": "WWTP_Central_HMI", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Central HMI"},

            # Core Switch - Cisco IE-9320
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "dmz",
             "name": "WWTP_Core_Switch", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "IE-9320-24P4X-E",
             "firmware_version": "17.9.3",
             "role": "Core Network Switch"},

            # EWON Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "dmz",
             "name": "WWTP_Remote_Access_Gateway", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "Cosy 131",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # Jump Server
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "dmz",
             "name": "WWTP_Vendor_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Vendor Remote Access",
             "external_comms": True},

            # ============================================================
            # CONTROL ZONE (Level 2) - 12 devices
            # Main PLCs, safety, HMI, switches, I/O
            # ============================================================
            # Main PLCs - Rockwell ControlLogix L85E (vulnerable)
            {"type": "plc", "vendor": "rockwell", "count": 2, "zone": "control",
             "name_pattern": "WWTP_Main_Process_Controller_{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             },

            # Area PLCs - Rockwell ControlLogix L73
            {"type": "plc", "vendor": "rockwell", "count": 2, "zone": "control",
             "name_pattern": "WWTP_Area_Controller_{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L73",
             "firmware_version": "V33.011",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Area Controller",
             },

            # Safety PLC - Rockwell GuardLogix L83ES
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name": "WWTP_Safety_Controller", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             },

            # Local HMI Panels - Rockwell PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 3, "zone": "control",
             "name_pattern": "WWTP_Local_Operator_HMI_{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Local Operator Interface"},

            # Industrial Switches - Cisco IE-9320
            {"type": "switch", "vendor": "Cisco", "count": 2, "zone": "control",
             "name_pattern": "WWTP_Control_Zone_Switch_{n:02d}", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "IE-9320-24P4X-E",
             "role": "Control Zone Switch"},

            # FLEX 5000 Remote I/O
            {"type": "io_module", "vendor": "rockwell", "count": 2, "zone": "control",
             "name_pattern": "WWTP_Control_Room_IO_{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Control Room I/O"},

            # ============================================================
            # HEADWORKS ZONE (Level 1) - 8 devices
            # Screening, grit removal, flow measurement
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "headworks",
             "name": "Headworks_Screening_Controller", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Headworks Controller"},

            # VFDs - ABB ACS580
            {"type": "drive", "vendor": "abb", "count": 4, "zone": "headworks",
             "name_pattern": "Headworks_Screening_Grit_VFD_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS580",
             "role": "Screening/Grit VFD"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "headworks",
             "name_pattern": "Headworks_Influent_Flow_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Influent Flow Meter"},

            # Level Transmitters - E+H Prosonic
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "headworks",
             "name": "Headworks_Wet_Well_Level", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Wet Well Level"},

            # ============================================================
            # PRIMARY ZONE (Level 1) - 6 devices
            # Primary clarifiers
            # ============================================================
            # Point I/O - Rockwell 1734-AENT
            {"type": "io_module", "vendor": "rockwell", "count": 2, "zone": "primary",
             "name_pattern": "Primary_Clarifier_IO_{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Primary Clarifier I/O"},

            # Clarifier Drives - ABB ACS880
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "primary",
             "name_pattern": "Primary_Clarifier_Drive_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "firmware_version": "V2.40",
             "role": "Clarifier Drive"},

            # Level/Sludge Blanket - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "primary",
             "name_pattern": "Primary_Sludge_Blanket_Level_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Sludge Blanket Level"},

            # ============================================================
            # SECONDARY ZONE (Level 1) - 12 devices
            # Aeration basins, secondary clarifiers
            # ============================================================
            # Point I/O - Rockwell 1734-AENT
            {"type": "io_module", "vendor": "rockwell", "count": 4, "zone": "secondary",
             "name_pattern": "Secondary_Aeration_IO_{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Secondary Process I/O"},

            # Blower VFDs - ABB ACS880 (high power)
            {"type": "drive", "vendor": "abb", "count": 4, "zone": "secondary",
             "name_pattern": "Secondary_Aeration_Blower_VFD_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Blower VFD"},

            # DO Analyzers - Yokogawa FLXA402
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "secondary",
             "name_pattern": "Secondary_Dissolved_Oxygen_Analyzer_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "Dissolved Oxygen Analyzer"},

            # pH Analyzers - Yokogawa FLXA402
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "secondary",
             "name_pattern": "Secondary_pH_Analyzer_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "pH Analyzer"},

            # ============================================================
            # TERTIARY/UV ZONE (Level 1) - 8 devices
            # Tertiary filters, UV disinfection
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "tertiary",
             "name": "Tertiary_Filtration_Controller", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Tertiary Controller"},

            # Filter VFDs - ABB ACS580
            {"type": "drive", "vendor": "abb", "count": 3, "zone": "tertiary",
             "name_pattern": "Tertiary_Filter_Pump_VFD_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS580",
             "role": "Filter Pump VFD"},

            # Turbidity Analyzers - Yokogawa SC450G
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "tertiary",
             "name_pattern": "Tertiary_Effluent_Turbidity_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SC450G",
             "role": "Effluent Turbidity"},

            # UV System I/O
            {"type": "io_module", "vendor": "rockwell", "count": 2, "zone": "tertiary",
             "name_pattern": "UV_Disinfection_System_IO_{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "UV System I/O"},

            # ============================================================
            # SLUDGE ZONE (Level 1) - 6 devices
            # Thickening, dewatering, digester
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "sludge",
             "name": "Sludge_Processing_Controller", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Sludge Controller"},

            # Dewatering VFDs - ABB ACS880
            {"type": "drive", "vendor": "abb", "count": 3, "zone": "sludge",
             "name_pattern": "Sludge_Dewatering_Press_VFD_{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Dewatering Press VFD"},

            # Digester Level/Temp - E+H
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "sludge",
             "name_pattern": "Sludge_Digester_Monitor_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CM442",
             "role": "Digester Monitoring"},
        ],
        "flows": [
            # EtherNet/IP implicit - Main PLC to Field PLCs (500ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["control"], "target_zones": ["headworks", "tertiary", "sludge"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # EtherNet/IP implicit - Main PLC to Point I/O (100ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 100,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["control"], "target_zones": ["control", "primary", "secondary", "tertiary"],
             "jitter_ms": 10, "jitter_type": "gaussian"},

            # EtherNet/IP - Control main PLCs to field ABB drives (vertical,
            # 500ms). Main controllers reach down into every process zone.
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["control"],
             "target_zones": ["headworks", "primary", "secondary", "tertiary", "sludge"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # EtherNet/IP - field PLCs to drives in their OWN process zone only
            # (no peer headworks<->tertiary<->sludge cell-to-cell traffic).
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["headworks"], "target_zones": ["headworks"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["tertiary"], "target_zones": ["tertiary"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["sludge"], "target_zones": ["sludge"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # CIP Safety communication (4ms)
            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"],
             "source_zones": ["control"], "target_zones": ["control", "headworks"]},

            # Modbus TCP - Control main PLCs to field analyzers (vertical, 2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["control"],
             "target_zones": ["headworks", "primary", "secondary", "tertiary", "sludge"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Modbus TCP - field PLCs to analyzers in their OWN zone only
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["headworks"], "target_zones": ["headworks"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["tertiary"], "target_zones": ["tertiary"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["sludge"], "target_zones": ["sludge"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # HMI polling PLCs (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["dmz", "control"], "target_zones": ["control"],
             "jitter_ms": 50, "jitter_type": "uniform"},

            # OPC Gateway polling (1000ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["gateway"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["control"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Historian collection (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # SNMP monitoring (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["gateway"], "target_types": ["switch"],
             "source_zones": ["dmz"], "target_zones": ["dmz", "control"]},

            # EWON polling PLCs (10s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["control"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # Jump server polling PLCs via SNMP (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["jump_server"], "target_types": ["plc"],
             "source_zones": ["dmz"], "target_zones": ["control"]},
        ],
        "zones": [
            {"id": "dmz", "name": "Industrial DMZ", "level": 3.5,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "control", "name": "Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "headworks", "name": "Headworks Zone", "level": 1,
             "subnet_offset": 2, "vlan": 121, "security_level": "standard"},
            {"id": "primary", "name": "Primary Treatment", "level": 1,
             "subnet_offset": 3, "vlan": 122, "security_level": "standard"},
            {"id": "secondary", "name": "Secondary Treatment", "level": 1,
             "subnet_offset": 4, "vlan": 123, "security_level": "standard"},
            {"id": "tertiary", "name": "Tertiary/UV", "level": 1,
             "subnet_offset": 5, "vlan": 124, "security_level": "standard"},
            {"id": "sludge", "name": "Sludge Processing", "level": 1,
             "subnet_offset": 6, "vlan": 125, "security_level": "standard"},
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
            {
                "provider": "teamviewer",
                "region": "global",
                "device_types": ["jump_server"],
                "heartbeat_interval_ms": 30000,
            },
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "rpi_violation", "watchdog_timeout"],
            "protocol": ["cip_error", "cip_safety_fault", "modbus_exception"],
            "sequence": ["dropped_packet", "out_of_order"],
            "payload": ["do_upset", "ph_spike", "blower_failure"],
            "network": ["jitter_spike"],
            "security": ["unauthorized_remote_access", "cip_stop_plc"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117", "185.188.32.1"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["cip_stop_plc", "modbus_write_scan", "rdp_bluekeep"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "plc", "jump_server"],
        },
        "conduits": [
            # L3.5 (dmz) <-> L2 (control): DMZ historian/OPC/HMI to main PLCs
            {"id": "dmz_to_control", "name": "DMZ \u2194 Control",
             "source_zone": "dmz", "target_zone": "control",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "Historian, OPC gateway, central HMI, and remote access gateway polling main PLCs and safety PLC"},
            # L2 (control) <-> L1 (headworks): PLCs to headworks field devices
            {"id": "control_to_headworks", "name": "Control \u2194 Headworks",
             "source_zone": "control", "target_zone": "headworks",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "modbus_tcp", "cip_safety"],
             "security_level": "high",
             "description": "Main PLCs and safety PLC polling headworks field PLC, VFDs, flow meters, and I/O"},
            # L2 (control) <-> L1 (primary): PLCs to primary treatment
            {"id": "control_to_primary", "name": "Control \u2194 Primary Treatment",
             "source_zone": "control", "target_zone": "primary",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "modbus_tcp"],
             "security_level": "high",
             "description": "Main PLCs polling primary clarifier I/O modules, drives, and level sensors"},
            # L2 (control) <-> L1 (secondary): PLCs to secondary treatment
            {"id": "control_to_secondary", "name": "Control \u2194 Secondary Treatment",
             "source_zone": "control", "target_zone": "secondary",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "modbus_tcp"],
             "security_level": "high",
             "description": "Main PLCs polling secondary aeration I/O, blower VFDs, and DO/pH analyzers"},
            # L2 (control) <-> L1 (tertiary): PLCs to tertiary/UV
            {"id": "control_to_tertiary", "name": "Control \u2194 Tertiary/UV",
             "source_zone": "control", "target_zone": "tertiary",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "modbus_tcp"],
             "security_level": "high",
             "description": "Main PLCs polling tertiary field PLC, filter VFDs, turbidity analyzers, and UV I/O"},
            # L2 (control) <-> L1 (sludge): PLCs to sludge processing
            {"id": "control_to_sludge", "name": "Control \u2194 Sludge Processing",
             "source_zone": "control", "target_zone": "sludge",
             "direction": "bidirectional",
             "allowed_protocols": ["ethernet_ip", "modbus_tcp"],
             "security_level": "high",
             "description": "Main PLCs polling sludge field PLC, dewatering VFDs, and digester monitors"},
        ],
        "total_duration_ms": 900000,  # 15 minutes (full lifecycle)
    },

    # ============================================================
    # TEMPLATE 4: SMALL UTILITY SCADA (26 devices)
    # Budget-constrained municipality with legacy/modern mix
    # ============================================================
    "small_utility_scada": {
        "name": "Small Utility SCADA",
        "description": "Small water utility with central SCADA + 3 remote pump stations "
                       "communicating over WAN. Master-RTU pattern: aggregator RTAC at central, "
                       "Schneider M340 / SCADAPack at each station. Slim IDMZ (remote-access "
                       "gateway only) — full jump-server stack only kicks in at MEDIUM scale. 27 "
                       "devices across 5 zones.",
        "vertical": "water_wastewater",
        "phase_preset": "normal_operation",
        "recommended_attack_playbooks": [
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "Small utility with limited security posture, easy reconnaissance target"},
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "Small staff increases insider threat risk"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "water_wastewater",
            "description": "Small utility SCADA with basic water treatment monitoring",
            "key_variables": ["intake_flow", "pump_speed", "chlorine_residual"],
            "available_faults": ["pump_failure"],
        },
        "devices": [
            # ============================================================
            # CONTROL ROOM (Level 2-3) - 5 devices
            # Combined SCADA/control room
            # ============================================================
            # Main PLC - Schneider Modicon Premium (legacy, vulnerable)
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "control_room",
             "name": "Main_Legacy_System_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TSXP57204M",
             "firmware_version": "V5.0",
             "error_config": {"exception_rate": 0.0008, "timeout_rate": 0.0004},
             "role": "Main System Controller",
             },

            # HMI - Schneider Magelis
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "control_room",
             "name": "Control_Room_Operator_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "Operator Interface"},

            # Industrial Switch - Cisco IE-4000
            {"type": "switch", "vendor": "Cisco", "count": 1, "zone": "control_room",
             "name": "Control_Room_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "firmware_version": "15.2(7)E6",
             "role": "Control Room Switch"},

            # SCADA PC - Magelis GTO Advanced HMI (10.4" panel as SCADA workstation)
            {"type": "scada_server", "vendor": "schneider", "count": 1, "zone": "control_room",
             "name": "SCADA_Workstation", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "HMIGTO5310",
             "role": "SCADA Workstation"},

            # EWON Remote Access - Cosy 131 (budget model)
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "control_room",
             "name": "Utility_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Cosy 131",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # WELL 1 - LEGACY (Level 1) - 5 devices
            # Older installation with Modicon Premium
            # ============================================================
            # Field PLC - Modicon Premium (legacy, vulnerable)
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "well1",
             "name": "Well_1_Legacy_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TSXP57154M",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.0005},
             "role": "Well 1 Controller",
             },

            # VFD - Schneider ATV320
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "well1",
             "name": "Well_1_Pump_VFD", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Well Pump VFD"},

            # Flow Meter - E+H Promag 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well1",
             "name": "Well_1_Flow_Meter", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Well Flow Meter"},

            # Level Transmitter - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well1",
             "name": "Well_1_Water_Level", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Well Water Level"},

            # Pressure Transmitter - E+H Cerabar PMC71
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well1",
             "name": "Well_1_Discharge_Pressure", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PMC71",
             "role": "Discharge Pressure"},

            # ============================================================
            # WELL 2 - UPGRADED (Level 1) - 5 devices
            # Recently upgraded with M241
            # ============================================================
            # Field PLC - Schneider M241 (modern)
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "well2",
             "name": "Well_2_Modern_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM241CE40R",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Well 2 Controller"},

            # VFD - Schneider ATV320
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "well2",
             "name": "Well_2_Pump_VFD", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Well Pump VFD"},

            # Flow Meter - E+H Promag 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well2",
             "name": "Well_2_Flow_Meter", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Well Flow Meter"},

            # Level Transmitter - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well2",
             "name": "Well_2_Water_Level", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Well Water Level"},

            # Pressure Transmitter - E+H Cerabar PMC71
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well2",
             "name": "Well_2_Discharge_Pressure", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PMC71",
             "role": "Discharge Pressure"},

            # ============================================================
            # STORAGE TANK (Level 1) - 5 devices
            # Elevated storage with booster pumps
            # ============================================================
            # Field PLC - Schneider M241
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "storage",
             "name": "Elevated_Tank_Booster_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM241CE40R",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Tank/Booster Controller"},

            # Level Transmitter - E+H Prosonic
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "storage",
             "name": "Elevated_Tank_Level", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Tank Level"},

            # Booster Pump VFDs - Schneider ATV320
            {"type": "drive", "vendor": "schneider", "count": 2, "zone": "storage",
             "name_pattern": "Storage_Booster_Pump_VFD_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Booster Pump VFD"},

            # Pressure Transmitter - E+H Cerabar PMC71
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "storage",
             "name": "System_Discharge_Pressure", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PMC71",
             "role": "System Pressure"},

            # ============================================================
            # DISTRIBUTION (Level 1) - 6 devices
            # Distribution monitoring points
            # ============================================================
            # Chlorine Analyzers - Yokogawa RC400G
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "distribution",
             "name_pattern": "Distribution_Chlorine_Analyzer_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "RC400G",
             "role": "Distribution Chlorine"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "distribution",
             "name_pattern": "Distribution_Flow_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Distribution Flow"},

            # Pressure Transmitters - E+H Cerabar PMC71
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "distribution",
             "name_pattern": "Distribution_Pressure_Monitor_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PMC71",
             "role": "Distribution Pressure"},
        ],
        "flows": [
            # Main PLC polling remote PLCs (5000ms - slow WAN)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["control_room"], "target_zones": ["well1", "well2", "storage"],
             "jitter_ms": 500, "jitter_type": "lognormal"},

            # Main PLC polling distribution sensors (10000ms - very slow)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["control_room"], "target_zones": ["distribution"],
             "jitter_ms": 1000, "jitter_type": "lognormal"},

            # Well PLCs polling local VFDs — each well controller drives only
            # its own pump (no well1<->well2 cell-to-cell traffic).
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["well1"], "target_zones": ["well1"],
             "jitter_ms": 200, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["well2"], "target_zones": ["well2"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Well/storage PLCs polling local sensors — per-zone only.
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 3000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["well1"], "target_zones": ["well1"],
             "jitter_ms": 300, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 3000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["well2"], "target_zones": ["well2"],
             "jitter_ms": 300, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 3000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["storage"], "target_zones": ["storage"],
             "jitter_ms": 300, "jitter_type": "gaussian"},

            # Storage PLC polling booster VFDs (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["storage"], "target_zones": ["storage"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # HMI polling main PLC (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["control_room"], "target_zones": ["control_room"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # SCADA PC polling main PLC (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "source_zones": ["control_room"], "target_zones": ["control_room"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # EWON polling main PLC (10s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["control_room"], "target_zones": ["control_room"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # SNMP monitoring of control room switch (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["control_room"], "target_zones": ["control_room"]},
        ],
        "zones": [
            {"id": "control_room", "name": "Control Room", "level": 2.5,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "well1", "name": "Well Station 1 (Legacy)", "level": 1,
             "subnet_offset": 1, "vlan": 111, "security_level": "standard"},
            {"id": "well2", "name": "Well Station 2 (Upgraded)", "level": 1,
             "subnet_offset": 2, "vlan": 112, "security_level": "standard"},
            {"id": "storage", "name": "Storage Tank/Boosters", "level": 1,
             "subnet_offset": 3, "vlan": 113, "security_level": "standard"},
            {"id": "distribution", "name": "Distribution Network", "level": 1,
             "subnet_offset": 4, "vlan": 114, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "cloud_services": [
            {
                "provider": "talk2m",
                "region": "us-central",
                "device_types": ["remote_gateway"],
                "heartbeat_interval_ms": 60000,  # Slower for budget
            },
        ],
        "suggested_anomalies": {
            "timing": ["timeout", "slow_response", "watchdog_timeout"],
            "protocol": ["modbus_exception", "legacy_device_error"],
            "sequence": ["duplicate", "dropped_packet"],
            "payload": ["pressure_drop", "well_failure", "chlorine_low"],
            "network": ["wan_latency"],
            "security": ["unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "legacy_device_exploit"],
            "enable_recon": True,
            "target_device_types": ["hmi", "plc"],
        },
        "conduits": [
            # L2.5 (control_room) <-> L1 (well1): Control room to legacy well station
            {"id": "control_to_well1", "name": "Control Room \u2194 Well 1",
             "source_zone": "control_room", "target_zone": "well1",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Main PLC polling legacy well field PLC, VFD, and sensors via WAN link"},
            # L2.5 (control_room) <-> L1 (well2): Control room to upgraded well station
            {"id": "control_to_well2", "name": "Control Room \u2194 Well 2",
             "source_zone": "control_room", "target_zone": "well2",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Main PLC polling modern well field PLC, VFD, and sensors via WAN link"},
            # L2.5 (control_room) <-> L1 (storage): Control room to storage tank/boosters
            {"id": "control_to_storage", "name": "Control Room \u2194 Storage",
             "source_zone": "control_room", "target_zone": "storage",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "Main PLC polling storage tank PLC, booster VFDs, and level/pressure sensors"},
            # L2.5 (control_room) <-> L1 (distribution): Control room to distribution network
            {"id": "control_to_distribution", "name": "Control Room \u2194 Distribution",
             "source_zone": "control_room", "target_zone": "distribution",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "standard",
             "description": "Main PLC polling remote distribution chlorine analyzers, flow meters, and pressure monitors"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },
}
