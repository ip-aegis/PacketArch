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
        "description": "Full municipal water treatment plant from intake through distribution. "
                       "Features coagulation/flocculation, sedimentation, filtration, and chlorine "
                       "disinfection processes. Schneider M580 PLCs for main control with Rockwell "
                       "CompactLogix for field zones. Extensive water quality instrumentation from "
                       "Endress+Hauser and Yokogawa. EWON remote access for vendor support. "
                       "45 devices across SCADA, control, and field zones.",
        "vertical": "water_wastewater",
        "phase_preset": "with_maintenance",
        "devices": [
            # ============================================================
            # SCADA ZONE (Level 3) - 5 devices
            # Centralized supervision, historian, OPC gateway
            # ============================================================
            # SCADA Server - Schneider ClearSCADA
            {"type": "scada_server", "vendor": "schneider", "count": 1, "zone": "scada",
             "name_pattern": "SCADA-WTP-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "SCADA Server"},

            # Historian - GE Proficy (vulnerable)
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "scada",
             "name_pattern": "HIST-WTP-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "Process Historian"},

            # OPC UA Gateway - Kepware KEPServerEX
            {"type": "gateway", "vendor": "kepware", "count": 1, "zone": "scada",
             "name_pattern": "OPC-GW-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "KEPServerEX",
             "role": "OPC UA Gateway"},

            # Core Switch - Cisco IE-4000
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "scada",
             "name_pattern": "SW-CORE-{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # EWON Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "scada",
             "name_pattern": "EWON-FLEXY-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # CONTROL ZONE (Level 2) - 10 devices
            # Main PLCs, safety, HMI, switches
            # ============================================================
            # Main PLCs - Schneider M580 BMEP586040 (vulnerable)
            {"type": "plc", "vendor": "schneider", "count": 2, "zone": "control",
             "name_pattern": "PLC-MAIN-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "BMEP586040",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2022-45789"]},

            # Hot Standby PLC - Schneider M580 BMEH586040
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "control",
             "name_pattern": "PLC-STBY-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "BMEH586040",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Hot Standby Controller",
             "cve_ids": ["CVE-2022-45789"]},

            # Auxiliary PLCs - Schneider M340 (vulnerable)
            {"type": "plc", "vendor": "schneider", "count": 2, "zone": "control",
             "name_pattern": "PLC-AUX-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "BMXP3420302",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Auxiliary Controller",
             "cve_ids": ["CVE-2021-22779"]},

            # Safety PLC - Schneider M580 Safety
            {"type": "safety_plc", "vendor": "schneider", "count": 1, "zone": "control",
             "name_pattern": "PLC-SAFETY-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "BMEP586040S",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-45789"]},

            # HMI Panels - Schneider Magelis
            {"type": "hmi", "vendor": "schneider", "count": 2, "zone": "control",
             "name_pattern": "HMI-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "Operator Interface"},

            # Industrial Switches - Schneider ConneXium
            {"type": "switch", "vendor": "schneider", "count": 2, "zone": "control",
             "name_pattern": "SW-CTRL-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "TCSESM083F2CU0",
             "role": "Control Zone Switch"},

            # ============================================================
            # INTAKE ZONE (Level 1) - 8 devices
            # Raw water intake, screening, pumping
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "intake",
             "name_pattern": "PLC-INTAKE-{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Intake Controller"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "intake",
             "name_pattern": "FT-INTAKE-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Raw Water Flow Meter"},

            # Level Transmitters - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "intake",
             "name_pattern": "LT-INTAKE-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Level Transmitter"},

            # VFD Drives - ABB ACS580
            {"type": "drive", "vendor": "abb", "count": 3, "zone": "intake",
             "name_pattern": "VFD-INTAKE-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS580",
             "role": "Raw Water Pump VFD"},

            # ============================================================
            # TREATMENT ZONE (Level 1) - 12 devices
            # Coagulation, flocculation, sedimentation, filtration
            # ============================================================
            # Remote I/O - Schneider Advantys STB
            {"type": "io_module", "vendor": "schneider", "count": 4, "zone": "treatment",
             "name_pattern": "RIO-TREAT-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STBNIP2311",
             "role": "Treatment Remote I/O"},

            # Water Quality Analyzers - E+H Liquiline
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "treatment",
             "name_pattern": "AIT-TURB-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CM442",
             "role": "Turbidity Analyzer"},

            # pH/ORP Analyzers - Yokogawa FLXA402
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "treatment",
             "name_pattern": "AIT-PH-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "pH/ORP Analyzer"},

            # Turbidity Analyzers - Yokogawa SC450G
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "treatment",
             "name_pattern": "AIT-FLT-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SC450G",
             "role": "Filter Turbidity Analyzer"},

            # VFD Drives - Schneider Altivar ATV930
            {"type": "drive", "vendor": "schneider", "count": 2, "zone": "treatment",
             "name_pattern": "VFD-TREAT-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ATV930D15N4",
             "role": "Treatment Process VFD"},

            # ============================================================
            # DISTRIBUTION ZONE (Level 1) - 10 devices
            # Clearwell, high service pumps, chlorination
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "distribution",
             "name_pattern": "PLC-DIST-{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Distribution Controller"},

            # Chlorine Analyzers - Yokogawa RC400G
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "distribution",
             "name_pattern": "AIT-CL2-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "RC400G",
             "role": "Chlorine Analyzer"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "distribution",
             "name_pattern": "FT-DIST-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Distribution Flow Meter"},

            # Level Transmitters - E+H Prosonic
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "distribution",
             "name_pattern": "LT-TANK-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Clearwell Level"},

            # VFD Drives - ABB ACS880
            {"type": "drive", "vendor": "abb", "count": 3, "zone": "distribution",
             "name_pattern": "VFD-HS-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
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
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "polling", "priority": "high",
             "description": "Modbus TCP polling patterns from M580 PLCs"},
            {"protocol": "ethernet_ip", "flow_type": "polling", "priority": "medium",
             "description": "EtherNet/IP communication with CompactLogix field PLCs"},
            {"protocol": "modbus_tcp", "flow_type": "instrumentation", "priority": "high",
             "description": "Water quality analyzer communication patterns"},
            {"protocol": "https", "flow_type": "remote_access", "priority": "high",
             "description": "EWON Talk2M cloud communication patterns"},
        ],
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": False,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "historian_sqli"],
            "enable_recon": False,
            "target_device_types": ["hmi", "plc"],
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 2: REGIONAL PUMP STATION NETWORK (52 devices)
    # Central SCADA with 6 remote pump stations via WAN
    # ============================================================
    "regional_pump_station_network": {
        "name": "Regional Pump Station Network",
        "description": "Regional water distribution system with central SCADA and 6 remote pump stations "
                       "connected via WAN. Features Honeywell Experion C300/C200 DCS at central control with "
                       "Emerson ROC800 RTUs at remote stations. DNP3 for WAN SCADA polling with Modbus TCP "
                       "for local control. Includes high-capacity, medium, and booster pump stations plus "
                       "storage tank monitoring. 52 devices with realistic WAN-aware timing.",
        "vertical": "water_wastewater",
        "phase_preset": "with_maintenance",
        "devices": [
            # ============================================================
            # CENTRAL CONTROL (Level 3) - 8 devices
            # Honeywell Experion DCS, Historian, HMIs
            # ============================================================
            # DCS Controllers - Honeywell Experion C300
            {"type": "plc", "vendor": "honeywell", "count": 1, "zone": "central",
             "name_pattern": "C300-MAIN-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "C300",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Main DCS Controller"},

            # Redundant DCS - Honeywell Experion C200
            {"type": "plc", "vendor": "honeywell", "count": 1, "zone": "central",
             "name_pattern": "C200-STBY-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "C200",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Standby DCS Controller"},

            # Historian - GE Proficy (vulnerable)
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "central",
             "name_pattern": "HIST-CENT-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "Central Historian"},

            # HMI Workstations - Honeywell Experion Station
            {"type": "hmi", "vendor": "honeywell", "count": 2, "zone": "central",
             "name_pattern": "HMI-CENT-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Experion Station",
             "role": "Operator Workstation"},

            # Core Switch - Cisco IE-4000
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "central",
             "name_pattern": "SW-CORE-{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # EWON Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "central",
             "name_pattern": "EWON-CENT-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Central Remote Access",
             "external_comms": True},

            # Jump Server (vulnerable to BlueKeep)
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "central",
             "name_pattern": "JUMP-SVR-{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "cve_ids": ["CVE-2019-0708"],
             "external_comms": True},

            # ============================================================
            # PUMP STATION 1 - HIGH CAPACITY (Level 1) - 8 devices
            # Major lift station with ROC800 RTU
            # ============================================================
            # RTU - Emerson ROC800
            {"type": "rtu", "vendor": "emerson", "count": 1, "zone": "station1",
             "name_pattern": "RTU-PS1-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ROC800",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Pump Station 1 RTU"},

            # High-Power VFDs - ABB ACS880
            {"type": "drive", "vendor": "abb", "count": 4, "zone": "station1",
             "name_pattern": "VFD-PS1-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "High Capacity Pump VFD"},

            # Flow Meter - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "station1",
             "name_pattern": "FT-PS1-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Station Flow Meter"},

            # Level Transmitter - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "station1",
             "name_pattern": "LT-PS1-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Wet Well Level"},

            # ============================================================
            # PUMP STATIONS 2-4 - MEDIUM CAPACITY (Level 1) - 18 devices
            # Standard pump stations with ROC800L RTUs
            # ============================================================
            # RTUs - Emerson ROC800L (3 stations)
            {"type": "rtu", "vendor": "emerson", "count": 3, "zone": "station_medium",
             "name_pattern": "RTU-PS-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ROC800L",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Medium Station RTU"},

            # VFDs - Schneider ATV320 (2 per station)
            {"type": "drive", "vendor": "schneider", "count": 6, "zone": "station_medium",
             "name_pattern": "VFD-MED-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Medium Pump VFD"},

            # Flow Meters - E+H Promag 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 3, "zone": "station_medium",
             "name_pattern": "FT-MED-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Station Flow Meter"},

            # Level Transmitters - E+H Prosonic
            {"type": "sensor", "vendor": "endress_hauser", "count": 6, "zone": "station_medium",
             "name_pattern": "LT-MED-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Wet Well Level"},

            # ============================================================
            # PUMP STATIONS 5-6 - BOOSTER (Level 1) - 10 devices
            # Small booster stations with Schneider M241 PLCs
            # ============================================================
            # PLCs - Schneider M241
            {"type": "plc", "vendor": "schneider", "count": 2, "zone": "station_booster",
             "name_pattern": "PLC-BOOST-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM241CE40R",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Booster Station PLC"},

            # VFDs - Schneider ATV320
            {"type": "drive", "vendor": "schneider", "count": 4, "zone": "station_booster",
             "name_pattern": "VFD-BOOST-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Booster Pump VFD"},

            # Flow Meters - E+H Promag 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "station_booster",
             "name_pattern": "FT-BOOST-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Booster Flow Meter"},

            # Pressure Transmitters - E+H
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "station_booster",
             "name_pattern": "PT-BOOST-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Discharge Pressure"},

            # ============================================================
            # STORAGE TANKS (Level 1) - 8 devices
            # Elevated and ground storage tank monitoring
            # ============================================================
            # RTUs - Emerson ROC800L (2 tanks)
            {"type": "rtu", "vendor": "emerson", "count": 2, "zone": "storage",
             "name_pattern": "RTU-TANK-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "ROC800L",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0003},
             "role": "Storage Tank RTU"},

            # Level Transmitters - E+H Levelflex (primary)
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "storage",
             "name_pattern": "LT-TANK-PRI-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Primary Tank Level"},

            # Level Transmitters - E+H Prosonic (backup)
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "storage",
             "name_pattern": "LT-TANK-BAK-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Backup Tank Level"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "storage",
             "name_pattern": "FT-TANK-{n:02d}", "protocols": ["modbus_tcp"],
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

            # Local RTU polling sensors (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["rtu"], "target_types": ["sensor"],
             "source_zones": ["station1", "station_medium", "storage"],
             "target_zones": ["station1", "station_medium", "storage"],
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
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "wan_scada", "priority": "high",
             "description": "WAN SCADA polling patterns from Experion to RTUs"},
            {"protocol": "modbus_tcp", "flow_type": "local_control", "priority": "high",
             "description": "Local RTU to VFD control patterns"},
            {"protocol": "snmp", "flow_type": "monitoring", "priority": "medium",
             "description": "RTU health monitoring via SNMP"},
            {"protocol": "https", "flow_type": "remote_access", "priority": "high",
             "description": "EWON Talk2M and TeamViewer cloud patterns"},
        ],
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["54.95.198.117", "51.38.74.240", "185.188.32.1"],
            "enable_c2": False,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "rdp_bluekeep"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "rtu", "jump_server"],
        },
        "total_duration_ms": 600000,  # 10 minutes
    },

    # ============================================================
    # TEMPLATE 3: WASTEWATER TREATMENT FACILITY (58 devices)
    # Activated sludge process with full treatment train
    # ============================================================
    "wastewater_treatment_facility": {
        "name": "Wastewater Treatment Facility",
        "description": "Full wastewater treatment facility with headworks, primary clarification, "
                       "activated sludge secondary treatment, tertiary filtration, UV disinfection, "
                       "and sludge processing. Rockwell ControlLogix L85E main controllers with "
                       "GuardLogix safety PLCs. ABB drives for all major equipment. Extensive "
                       "water quality instrumentation from Yokogawa and Endress+Hauser. "
                       "58 devices across SCADA, control, and 5 process zones.",
        "vertical": "water_wastewater",
        "phase_preset": "full_lifecycle",
        "devices": [
            # ============================================================
            # SCADA/DMZ (Level 3.5) - 6 devices
            # ============================================================
            # Historian - GE Proficy (vulnerable)
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "dmz",
             "name_pattern": "HIST-WWTP-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "Process Historian"},

            # OPC UA Gateway - Kepware KEPServerEX
            {"type": "gateway", "vendor": "kepware", "count": 1, "zone": "dmz",
             "name_pattern": "OPC-GW-{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "KEPServerEX",
             "role": "OPC UA Gateway"},

            # Central HMI - Rockwell PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 1, "zone": "dmz",
             "name_pattern": "HMI-CENTRAL-{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Central HMI"},

            # Core Switch - Rockwell Stratix 5700
            {"type": "switch", "vendor": "rockwell", "count": 1, "zone": "dmz",
             "name_pattern": "SW-CORE-{n:02d}", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "1783-BMS10CGL",
             "role": "Core Network Switch"},

            # EWON Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "dmz",
             "name_pattern": "EWON-COSY-{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp", "snmp"],
             "fingerprint_model": "Cosy 131",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # Jump Server
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "dmz",
             "name_pattern": "JUMP-SVR-{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Vendor Remote Access",
             "cve_ids": ["CVE-2019-0708"],
             "external_comms": True},

            # ============================================================
            # CONTROL ZONE (Level 2) - 12 devices
            # Main PLCs, safety, HMI, switches, I/O
            # ============================================================
            # Main PLCs - Rockwell ControlLogix L85E (vulnerable)
            {"type": "plc", "vendor": "rockwell", "count": 2, "zone": "control",
             "name_pattern": "PLC-MAIN-{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Main Process Controller",
             "cve_ids": ["CVE-2022-1159", "CVE-2023-3595"]},

            # Area PLCs - Rockwell ControlLogix L73
            {"type": "plc", "vendor": "rockwell", "count": 2, "zone": "control",
             "name_pattern": "PLC-AREA-{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1756-L73",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Area Controller",
             "cve_ids": ["CVE-2022-1159"]},

            # Safety PLC - Rockwell GuardLogix L83ES
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "control",
             "name_pattern": "PLC-SAFETY-{n:02d}", "protocols": ["ethernet_ip", "cip_safety"],
             "fingerprint_model": "1756-L83ES",
             "error_config": {"exception_rate": 0.0001, "timeout_rate": 0.00005},
             "role": "Safety Controller",
             "cve_ids": ["CVE-2022-1159"]},

            # Local HMI Panels - Rockwell PanelView Plus 7
            {"type": "hmi", "vendor": "rockwell", "count": 3, "zone": "control",
             "name_pattern": "HMI-LOCAL-{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "2711P-T10C22D9P",
             "role": "Local Operator Interface"},

            # Industrial Switches - Rockwell Stratix 5700
            {"type": "switch", "vendor": "rockwell", "count": 2, "zone": "control",
             "name_pattern": "SW-CTRL-{n:02d}", "protocols": ["ethernet_ip", "snmp"],
             "fingerprint_model": "1783-BMS10CGL",
             "role": "Control Zone Switch"},

            # FLEX 5000 Remote I/O
            {"type": "io_module", "vendor": "rockwell", "count": 2, "zone": "control",
             "name_pattern": "RIO-CTRL-{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "5094-AEN2TR",
             "role": "Control Room I/O"},

            # ============================================================
            # HEADWORKS ZONE (Level 1) - 8 devices
            # Screening, grit removal, flow measurement
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "headworks",
             "name_pattern": "PLC-HEAD-{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Headworks Controller"},

            # VFDs - ABB ACS580
            {"type": "drive", "vendor": "abb", "count": 4, "zone": "headworks",
             "name_pattern": "VFD-HEAD-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS580",
             "role": "Screening/Grit VFD"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "headworks",
             "name_pattern": "FT-HEAD-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Influent Flow Meter"},

            # Level Transmitters - E+H Prosonic
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "headworks",
             "name_pattern": "LT-HEAD-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Wet Well Level"},

            # ============================================================
            # PRIMARY ZONE (Level 1) - 6 devices
            # Primary clarifiers
            # ============================================================
            # Point I/O - Rockwell 1734-AENT
            {"type": "io_module", "vendor": "rockwell", "count": 2, "zone": "primary",
             "name_pattern": "PIO-PRI-{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Primary Clarifier I/O"},

            # Clarifier Drives - ABB ACS880
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "primary",
             "name_pattern": "VFD-CLAR-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Clarifier Drive"},

            # Level/Sludge Blanket - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "primary",
             "name_pattern": "LT-PRI-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Sludge Blanket Level"},

            # ============================================================
            # SECONDARY ZONE (Level 1) - 12 devices
            # Aeration basins, secondary clarifiers
            # ============================================================
            # Point I/O - Rockwell 1734-AENT
            {"type": "io_module", "vendor": "rockwell", "count": 4, "zone": "secondary",
             "name_pattern": "PIO-SEC-{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Secondary Process I/O"},

            # Blower VFDs - ABB ACS880 (high power)
            {"type": "drive", "vendor": "abb", "count": 4, "zone": "secondary",
             "name_pattern": "VFD-BLOW-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Blower VFD"},

            # DO Analyzers - Yokogawa FLXA402
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "secondary",
             "name_pattern": "AIT-DO-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "Dissolved Oxygen Analyzer"},

            # pH Analyzers - Yokogawa FLXA402
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "secondary",
             "name_pattern": "AIT-PH-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FLXA402",
             "role": "pH Analyzer"},

            # ============================================================
            # TERTIARY/UV ZONE (Level 1) - 8 devices
            # Tertiary filters, UV disinfection
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "tertiary",
             "name_pattern": "PLC-TERT-{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Tertiary Controller"},

            # Filter VFDs - ABB ACS580
            {"type": "drive", "vendor": "abb", "count": 3, "zone": "tertiary",
             "name_pattern": "VFD-FILT-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS580",
             "role": "Filter Pump VFD"},

            # Turbidity Analyzers - Yokogawa SC450G
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "tertiary",
             "name_pattern": "AIT-TURB-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SC450G",
             "role": "Effluent Turbidity"},

            # UV System I/O
            {"type": "io_module", "vendor": "rockwell", "count": 2, "zone": "tertiary",
             "name_pattern": "PIO-UV-{n:02d}", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "UV System I/O"},

            # ============================================================
            # SLUDGE ZONE (Level 1) - 6 devices
            # Thickening, dewatering, digester
            # ============================================================
            # Field PLC - Rockwell CompactLogix
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "sludge",
             "name_pattern": "PLC-SLUDGE-{n:02d}", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "1769-L33ER",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Sludge Controller"},

            # Dewatering VFDs - ABB ACS880
            {"type": "drive", "vendor": "abb", "count": 3, "zone": "sludge",
             "name_pattern": "VFD-DEWAT-{n:02d}", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Dewatering Press VFD"},

            # Digester Level/Temp - E+H
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "sludge",
             "name_pattern": "TT-DIG-{n:02d}", "protocols": ["modbus_tcp"],
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

            # EtherNet/IP - PLCs to ABB Drives (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["control", "headworks", "tertiary", "sludge"],
             "target_zones": ["headworks", "primary", "secondary", "tertiary", "sludge"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # CIP Safety communication (4ms)
            {"protocol": "cip_safety", "pattern": "safety", "interval_ms": 4,
             "source_types": ["safety_plc"], "target_types": ["plc", "io_module"],
             "source_zones": ["control"], "target_zones": ["control", "headworks"]},

            # Modbus TCP - PLCs to analyzers (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["control", "headworks", "tertiary", "sludge"],
             "target_zones": ["headworks", "primary", "secondary", "tertiary", "sludge"],
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
        "pcap_learning_hints": [
            {"protocol": "ethernet_ip", "flow_type": "implicit_io", "priority": "high",
             "description": "EtherNet/IP implicit messaging from ControlLogix PLCs"},
            {"protocol": "cip_safety", "flow_type": "safety", "priority": "high",
             "description": "CIP Safety GuardLogix communication patterns"},
            {"protocol": "modbus_tcp", "flow_type": "instrumentation", "priority": "high",
             "description": "Water quality analyzer Modbus polling patterns"},
            {"protocol": "ethernet_ip", "flow_type": "drive_control", "priority": "medium",
             "description": "ABB ACS880/ACS580 EtherNet/IP control patterns"},
            {"protocol": "https", "flow_type": "remote_access", "priority": "high",
             "description": "EWON Talk2M cloud communication patterns"},
        ],
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117", "185.188.32.1"],
            "enable_c2": False,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["cip_stop_plc", "modbus_write_scan", "rdp_bluekeep"],
            "enable_recon": True,
            "scan_ot_ports": True,
            "target_device_types": ["hmi", "plc", "jump_server"],
        },
        "total_duration_ms": 900000,  # 15 minutes (full lifecycle)
    },

    # ============================================================
    # TEMPLATE 4: SMALL UTILITY SCADA (26 devices)
    # Budget-constrained municipality with legacy/modern mix
    # ============================================================
    "small_utility_scada": {
        "name": "Small Utility SCADA",
        "description": "Budget-constrained small municipality water system with 2 wells, elevated storage "
                       "tank, and distribution network. Features mix of legacy Schneider Modicon Premium "
                       "PLCs (CVE-vulnerable) and modern M241 controllers. Brownfield environment with "
                       "older infrastructure still in service. Minimal redundancy, basic remote access. "
                       "26 devices representing realistic small utility constraints.",
        "vertical": "water_wastewater",
        "phase_preset": "normal_operation",
        "devices": [
            # ============================================================
            # CONTROL ROOM (Level 2-3) - 5 devices
            # Combined SCADA/control room
            # ============================================================
            # Main PLC - Schneider Modicon Premium (legacy, vulnerable)
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "control_room",
             "name_pattern": "PLC-MAIN-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TSXP57204M",
             "error_config": {"exception_rate": 0.0008, "timeout_rate": 0.0004},
             "role": "Main System Controller",
             "cve_ids": ["CVE-2018-7760"]},

            # HMI - Schneider Magelis
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "control_room",
             "name_pattern": "HMI-MAIN-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "Operator Interface"},

            # Industrial Switch - Schneider ConneXium
            {"type": "switch", "vendor": "schneider", "count": 1, "zone": "control_room",
             "name_pattern": "SW-CTRL-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "TCSESM083F2CU0",
             "role": "Control Room Switch"},

            # SCADA PC (simple HMI/data collection)
            {"type": "scada_server", "vendor": "schneider", "count": 1, "zone": "control_room",
             "name_pattern": "SCADA-PC-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMISTM6",
             "role": "SCADA Workstation"},

            # EWON Remote Access - Cosy 131 (budget model)
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "control_room",
             "name_pattern": "EWON-COSY-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Cosy 131",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # WELL 1 - LEGACY (Level 1) - 5 devices
            # Older installation with Modicon Premium
            # ============================================================
            # Field PLC - Modicon Premium (legacy, vulnerable)
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "well1",
             "name_pattern": "PLC-WELL1-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TSXP57154M",
             "error_config": {"exception_rate": 0.001, "timeout_rate": 0.0005},
             "role": "Well 1 Controller",
             "cve_ids": ["CVE-2018-7760"]},

            # VFD - Schneider ATV320
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "well1",
             "name_pattern": "VFD-WELL1-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Well Pump VFD"},

            # Flow Meter - E+H Promag 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well1",
             "name_pattern": "FT-WELL1-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Well Flow Meter"},

            # Level Transmitter - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well1",
             "name_pattern": "LT-WELL1-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Well Water Level"},

            # Pressure Transmitter
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well1",
             "name_pattern": "PT-WELL1-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Discharge Pressure"},

            # ============================================================
            # WELL 2 - UPGRADED (Level 1) - 5 devices
            # Recently upgraded with M241
            # ============================================================
            # Field PLC - Schneider M241 (modern)
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "well2",
             "name_pattern": "PLC-WELL2-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM241CE40R",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Well 2 Controller"},

            # VFD - Schneider ATV320
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "well2",
             "name_pattern": "VFD-WELL2-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Well Pump VFD"},

            # Flow Meter - E+H Promag 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well2",
             "name_pattern": "FT-WELL2-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag 400",
             "role": "Well Flow Meter"},

            # Level Transmitter - E+H Levelflex
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well2",
             "name_pattern": "LT-WELL2-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Well Water Level"},

            # Pressure Transmitter
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "well2",
             "name_pattern": "PT-WELL2-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "Discharge Pressure"},

            # ============================================================
            # STORAGE TANK (Level 1) - 5 devices
            # Elevated storage with booster pumps
            # ============================================================
            # Field PLC - Schneider M241
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "storage",
             "name_pattern": "PLC-TANK-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM241CE40R",
             "error_config": {"exception_rate": 0.0004, "timeout_rate": 0.0002},
             "role": "Tank/Booster Controller"},

            # Level Transmitter - E+H Prosonic
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "storage",
             "name_pattern": "LT-TANK-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMU90",
             "role": "Tank Level"},

            # Booster Pump VFDs - Schneider ATV320
            {"type": "drive", "vendor": "schneider", "count": 2, "zone": "storage",
             "name_pattern": "VFD-BOOST-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV320",
             "role": "Booster Pump VFD"},

            # Pressure Transmitter
            {"type": "sensor", "vendor": "endress_hauser", "count": 1, "zone": "storage",
             "name_pattern": "PT-BOOST-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
             "role": "System Pressure"},

            # ============================================================
            # DISTRIBUTION (Level 1) - 6 devices
            # Distribution monitoring points
            # ============================================================
            # Chlorine Analyzers - Yokogawa RC400G
            {"type": "sensor", "vendor": "yokogawa", "count": 2, "zone": "distribution",
             "name_pattern": "AIT-CL2-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "RC400G",
             "role": "Distribution Chlorine"},

            # Flow Meters - E+H Promag W 400
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "distribution",
             "name_pattern": "FT-DIST-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Promag W 400",
             "role": "Distribution Flow"},

            # Pressure Transmitters
            {"type": "sensor", "vendor": "endress_hauser", "count": 2, "zone": "distribution",
             "name_pattern": "PT-DIST-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "FMP50",
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

            # Well PLCs polling local VFDs (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["well1", "well2"], "target_zones": ["well1", "well2"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Well PLCs polling local sensors (3000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 3000,
             "source_types": ["plc"], "target_types": ["sensor"],
             "source_zones": ["well1", "well2", "storage"],
             "target_zones": ["well1", "well2", "storage"],
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
        "pcap_learning_hints": [
            {"protocol": "modbus_tcp", "flow_type": "legacy_polling", "priority": "high",
             "description": "Legacy Modicon Premium slow polling patterns"},
            {"protocol": "modbus_tcp", "flow_type": "modern_polling", "priority": "high",
             "description": "M241 Modbus TCP polling patterns"},
            {"protocol": "modbus_tcp", "flow_type": "instrumentation", "priority": "medium",
             "description": "Field instrument communication patterns"},
            {"protocol": "https", "flow_type": "remote_access", "priority": "high",
             "description": "EWON Talk2M cloud communication patterns"},
        ],
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["54.95.198.117"],
            "enable_c2": False,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "legacy_device_exploit"],
            "enable_recon": False,
            "target_device_types": ["hmi", "plc"],
        },
        "total_duration_ms": 300000,  # 5 minutes
    },
}
