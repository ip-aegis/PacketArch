"""Building automation and BMS industry scenario templates.

Primary Vendors: Johnson Controls, Honeywell, Trane, Schneider Electric, Siemens
Protocol Focus: BACnet/IP (primary), Modbus TCP (power/HVAC), SNMP (infrastructure)

Enhanced templates with:
- 30-45+ devices per template
- Realistic traffic flows based on BACnet polling patterns
- Proper fingerprinting with protocol identities
- Multi-vendor architectures typical of real buildings
"""

from typing import Any


BUILDING_AUTOMATION_TEMPLATES: dict[str, dict[str, Any]] = {
    # ============================================================
    # TEMPLATE 1: COMMERCIAL OFFICE BUILDING BMS (35 devices)
    # Modern Class A office building with central BMS
    # ============================================================
    "commercial_office_bms": {
        "name": "Commercial Office Building BMS",
        "description": "Modern Class A office building with central BMS. Features WebCTRL server "
                       "with Johnson Controls NAE55 supervisory controllers, Trane HVAC, and "
                       "distributed Distech VAV and Siemens room controllers. Multi-vendor "
                       "architecture typical of modern commercial buildings. 35 devices across "
                       "BMS core, HVAC control, and floor zone networks.",
        "vertical": "building_automation",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "Building systems accessible from corporate network"},
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "BACnet device discovery via Who-Is scanning"}
        ],
        "recommended_traffic_schedule": "office_hours",
        "process_sim": {
            "template": "building_automation",
            "description": "HVAC zone control with setpoint tracking, supply/return air temps, damper position, humidity",
            "key_variables": ["setpoint", "zone_temp", "supply_air_temp", "damper_position", "humidity"],
            "available_faults": ["fan_failure", "sensor_drift"],
        },
        "devices": [
            # ============================================================
            # BMS CORE ZONE (Level 3) - 5 devices
            # Central BMS server, supervisory controllers, infrastructure
            # ============================================================
            # BMS Server - Automated Logic WebCTRL
            # Fingerprint has: bacnet_identity ONLY
            {"type": "bms_server", "vendor": "automated_logic", "count": 1, "zone": "bms_core",
             "name_pattern": "WEBCTRL-SVR-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "Server",
             "role": "Central BMS Server"},

            # Supervisory Controllers - Johnson Controls NAE55
            # Fingerprint has: bacnet_identity, snmp_identity
            {"type": "controller", "vendor": "johnson_controls", "count": 2, "zone": "bms_core",
             "name_pattern": "NAE55-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "NAE55",
             "role": "Supervisory Network Controller"},

            # Industrial Switches with SNMP monitoring
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "bms_core",
             "name_pattern": "SW-BMS-{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "BMS Network Switch"},

            # EWON Remote Access Gateway - Talk2M cloud connectivity
            # Fingerprint has: modbus_identity, snmp_identity, external_communications
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "bms_core",
             "name_pattern": "EWON-FLEXY-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # HVAC CONTROL ZONE (Level 2) - 10 devices
            # AHU controllers, chiller controllers, zone supervisors
            # ============================================================
            # HVAC Supervisory - Trane Tracer SC+
            # Fingerprint has: bacnet_identity ONLY
            {"type": "hvac_controller", "vendor": "trane", "count": 2, "zone": "hvac_control",
             "name_pattern": "TRACER-SC-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "SC+",
             "role": "HVAC Supervisory Controller"},

            # AHU Controllers - Johnson Controls FEC26
            # Fingerprint has: bacnet_identity ONLY
            {"type": "ahu_controller", "vendor": "johnson_controls", "count": 4, "zone": "hvac_control",
             "name_pattern": "FEC-AHU-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "FEC26",
             "role": "AHU Controller"},

            # Chiller Controllers - Carel pCO5+
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "chiller_controller", "vendor": "carel", "count": 2, "zone": "hvac_control",
             "name_pattern": "PCO5-CHILL-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "pCO5+",
             "role": "Chiller Controller"},

            # Building Controllers - Schneider CX9680
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "building_controller", "vendor": "schneider", "count": 2, "zone": "hvac_control",
             "name_pattern": "CX9680-{n:02d}", "protocols": ["bacnet", "modbus_tcp"],
             "fingerprint_model": "CX9680",
             "role": "Building Controller"},

            # ============================================================
            # FLOOR ZONE (Level 1) - 20 devices
            # VAV controllers, room controllers, field equipment
            # ============================================================
            # VAV Controllers - Distech ECY-VAV
            # Fingerprint has: bacnet_identity ONLY
            {"type": "vav_controller", "vendor": "distech", "count": 8, "zone": "floor_zone",
             "name_pattern": "ECY-VAV-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "ECY-VAV",
             "role": "VAV Controller"},

            # Room Controllers - Siemens DXR2.E12
            # Fingerprint has: bacnet_identity ONLY
            {"type": "room_controller", "vendor": "siemens", "count": 6, "zone": "floor_zone",
             "name_pattern": "DXR2-RM-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "DXR2.E12",
             "role": "Room Automation Station"},

            # Field Controllers - Delta Controls eBCON
            # Fingerprint has: bacnet_identity ONLY
            {"type": "field_controller", "vendor": "delta_controls", "count": 4, "zone": "floor_zone",
             "name_pattern": "EBCON-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "eBCON",
             "role": "Field Controller"},

            # Zone Controllers - Trane UC600
            # Fingerprint has: bacnet_identity ONLY
            {"type": "zone_controller", "vendor": "trane", "count": 2, "zone": "floor_zone",
             "name_pattern": "UC600-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "UC600",
             "role": "Unit Controller"},
        ],
        "flows": [
            # ============================================================
            # BACnet Subscription Flows - Server to Supervisory (5s)
            # ============================================================
            {"protocol": "bacnet", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["bms_server"], "target_types": ["controller"],
             "source_zones": ["bms_core"], "target_zones": ["bms_core"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # BACnet Polling - Supervisory to HVAC Controllers (1s)
            # ============================================================
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["controller"], "target_types": ["hvac_controller", "ahu_controller", "chiller_controller", "building_controller"],
             "source_zones": ["bms_core"], "target_zones": ["hvac_control"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # BACnet Polling - HVAC to Field Controllers (500ms)
            # ============================================================
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 500,
             "source_types": ["hvac_controller", "building_controller"], "target_types": ["vav_controller", "room_controller", "field_controller", "zone_controller"],
             "source_zones": ["hvac_control"], "target_zones": ["floor_zone"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # ============================================================
            # BACnet COV - Change of Value Notifications (async, ~2s avg)
            # ============================================================
            {"protocol": "bacnet", "pattern": "cov", "interval_ms": 2000,
             "source_types": ["vav_controller", "room_controller"], "target_types": ["controller"],
             "source_zones": ["floor_zone"], "target_zones": ["bms_core"],
             "jitter_ms": 1000, "jitter_type": "uniform"},

            # ============================================================
            # Modbus TCP - Chiller/Building Controller polling (1s)
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["controller"], "target_types": ["chiller_controller", "building_controller"],
             "source_zones": ["bms_core"], "target_zones": ["hvac_control"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP - Infrastructure Monitoring (30s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["bms_server"], "target_types": ["switch", "controller", "remote_gateway"],
             "source_zones": ["bms_core"], "target_zones": ["bms_core"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # EWON Remote Access - Talk2M Cloud Communication (30s heartbeat)
            # Uses actual Talk2M public IPs for Cyber Vision external detection
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source_types": ["remote_gateway"], "target_types": ["cloud"],
             "source_zones": ["bms_core"], "target_zones": ["external"],
             "external_ip": "13.56.142.1",  # Talk2M US-West VPN server
             "external_port": 443,
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # EWON Modbus polling to HVAC controllers (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["chiller_controller", "building_controller"],
             "source_zones": ["bms_core"], "target_zones": ["hvac_control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "bms_core", "name": "BMS Core Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "hvac_control", "name": "HVAC Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "standard"},
            {"id": "floor_zone", "name": "Floor Zone Network", "level": 1,
             "subnet_offset": 2, "vlan": 120, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap", "subscription_timeout"],
            "protocol": ["bacnet_reject", "bacnet_abort", "modbus_exception"],
            "sequence": ["out_of_order", "duplicate_invoke_id"],
            "payload": ["value_spike", "setpoint_change"],
            "network": ["broadcast_storm"],
            "security": ["unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],  # Talk2M VPN server IPs
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "enable_recon": True,
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 2: DATA CENTER INFRASTRUCTURE (28 devices)
    # Tier III data center with precision cooling and power monitoring
    # ============================================================
    "data_center_infrastructure": {
        "name": "Data Center Infrastructure",
        "description": "Tier III data center with precision cooling (CRAC units) and power "
                       "monitoring (UPS, PDU). Features Schneider Electric cooling and power "
                       "equipment with BACnet, Modbus TCP, and SNMP monitoring. Centralized "
                       "DCIM integration via Automated Logic server. 28 devices across DCIM "
                       "core, cooling zone, power zone, and rack-level monitoring.",
        "vertical": "building_automation",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "DCIM/BMS access can disrupt cooling and power to IT infrastructure"},
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "BACnet/Modbus/SNMP multi-protocol discovery surface"}
        ],
        "recommended_traffic_schedule": "data_center",
        "process_sim": {
            "template": "building_automation",
            "description": "Precision cooling with CRAC/chiller control and rack-level temperature monitoring",
            "key_variables": ["setpoint", "zone_temp", "supply_air_temp", "fan_speed", "humidity"],
            "available_faults": ["fan_failure", "sensor_drift"],
        },
        "devices": [
            # ============================================================
            # DCIM CORE ZONE (Level 3) - 4 devices
            # DCIM server, building controllers, infrastructure
            # ============================================================
            # DCIM Server - Automated Logic WebCTRL
            # Fingerprint has: bacnet_identity ONLY
            {"type": "dcim_server", "vendor": "automated_logic", "count": 1, "zone": "dcim_core",
             "name_pattern": "DCIM-SVR-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "Server",
             "role": "DCIM Server"},

            # Building Controllers - Schneider CX9680
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "building_controller", "vendor": "schneider", "count": 2, "zone": "dcim_core",
             "name_pattern": "CX9680-DC-{n:02d}", "protocols": ["bacnet", "modbus_tcp"],
             "fingerprint_model": "CX9680",
             "role": "Data Center Controller"},

            # Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "dcim_core",
             "name_pattern": "SW-DCIM-{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "DCIM Network Switch"},

            # EWON Remote Access Gateway - Talk2M cloud connectivity for remote DCIM
            # Fingerprint has: modbus_identity, snmp_identity, external_communications
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "dcim_core",
             "name_pattern": "EWON-COSY-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Cosy 131",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # COOLING ZONE (Level 2) - 8 devices
            # CRAC units and chiller controllers
            # ============================================================
            # CRAC Units - Schneider InRow DX
            # Fingerprint has: bacnet_identity, modbus_identity (no snmp_identity)
            {"type": "crac_unit", "vendor": "schneider", "count": 6, "zone": "cooling_zone",
             "name_pattern": "INROW-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "InRow DX",
             "role": "In-Row Cooling Unit"},

            # Chiller Controllers - Carel pCO5+
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "chiller_controller", "vendor": "carel", "count": 2, "zone": "cooling_zone",
             "name_pattern": "PCO5-CHILL-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "pCO5+",
             "role": "Chiller Controller"},

            # ============================================================
            # POWER ZONE (Level 2) - 6 devices
            # UPS systems and main PDUs
            # ============================================================
            # UPS Systems - Schneider Galaxy VM
            # Fingerprint has: modbus_identity, snmp_identity (NO bacnet_identity)
            {"type": "ups", "vendor": "schneider", "count": 4, "zone": "power_zone",
             "name_pattern": "GALAXY-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Galaxy VM",
             "role": "UPS System"},

            # AHU/Cooling for electrical room - Trane UC600
            # Fingerprint has: bacnet_identity ONLY
            {"type": "ahu_controller", "vendor": "trane", "count": 2, "zone": "power_zone",
             "name_pattern": "UC600-ELEC-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "UC600",
             "role": "Electrical Room Cooling"},

            # ============================================================
            # RACK ZONE (Level 1) - 10 devices
            # Rack PDUs and in-row monitoring
            # ============================================================
            # Rack PDUs - Schneider Rack PDU
            # Fingerprint has: modbus_identity, snmp_identity (NO bacnet_identity)
            {"type": "pdu", "vendor": "schneider", "count": 8, "zone": "rack_zone",
             "name_pattern": "RPDU-{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Rack PDU",
             "role": "Rack PDU"},

            # Switches for rack monitoring
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "rack_zone",
             "name_pattern": "SW-RACK-{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Rack Network Switch"},
        ],
        "flows": [
            # ============================================================
            # BACnet Polling - DCIM to Cooling Zone (1s)
            # ============================================================
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["dcim_server", "building_controller"],
             "target_types": ["crac_unit", "chiller_controller"],
             "source_zones": ["dcim_core"], "target_zones": ["cooling_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # BACnet Polling - Building Controller to AHU (1s)
            # ============================================================
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["building_controller"], "target_types": ["ahu_controller"],
             "source_zones": ["dcim_core"], "target_zones": ["power_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # Modbus TCP - Power Monitoring (1s)
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["building_controller"], "target_types": ["ups", "pdu"],
             "source_zones": ["dcim_core"], "target_zones": ["power_zone", "rack_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # Modbus TCP - Precision Cooling (500ms)
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["building_controller"], "target_types": ["crac_unit", "chiller_controller"],
             "source_zones": ["dcim_core"], "target_zones": ["cooling_zone"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP - UPS and PDU Monitoring (30s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["dcim_server"], "target_types": ["ups", "pdu", "switch", "remote_gateway"],
             "source_zones": ["dcim_core"], "target_zones": ["power_zone", "rack_zone", "dcim_core"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # EWON Remote Access - Talk2M Cloud Communication (30s heartbeat)
            # Uses actual Talk2M public IPs for Cyber Vision external detection
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source_types": ["remote_gateway"], "target_types": ["cloud"],
             "source_zones": ["dcim_core"], "target_zones": ["external"],
             "external_ip": "54.95.198.117",  # Talk2M Asia-Pacific VPN server
             "external_port": 443,
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # EWON Modbus polling to UPS systems (10s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["remote_gateway"], "target_types": ["ups"],
             "source_zones": ["dcim_core"], "target_zones": ["power_zone"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "dcim_core", "name": "DCIM Core Network", "level": 3,
             "subnet_offset": 0, "vlan": 200, "security_level": "critical"},
            {"id": "cooling_zone", "name": "Cooling Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 210, "security_level": "high"},
            {"id": "power_zone", "name": "Power Distribution Network", "level": 2,
             "subnet_offset": 2, "vlan": 220, "security_level": "high"},
            {"id": "rack_zone", "name": "Rack Monitoring Network", "level": 1,
             "subnet_offset": 3, "vlan": 230, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap", "timeout"],
            "protocol": ["bacnet_reject", "modbus_exception", "snmp_timeout"],
            "sequence": ["out_of_order", "duplicate"],
            "payload": ["temperature_spike", "power_alarm", "ups_transfer"],
            "network": [],
            "security": ["unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["54.95.198.117", "51.38.74.240"],  # Talk2M VPN server IPs
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "enable_recon": True,
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 3: UNIVERSITY CAMPUS BMS (45 devices)
    # Multi-building campus with distributed BMS architecture
    # ============================================================
    "university_campus_bms": {
        "name": "University Campus BMS",
        "description": "Multi-building university campus with distributed BMS architecture. "
                       "Features central Honeywell JACE 8000 servers with multi-vendor building "
                       "controllers including Johnson Controls, Trane, Schneider, and Siemens. "
                       "Represents typical campus environment with legacy and modern equipment. "
                       "45 devices across campus core, two academic buildings, central plant, "
                       "and distributed field devices.",
        "vertical": "building_automation",
        "phase_preset": "full_lifecycle",
        "recommended_attack_playbooks": [
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "Campus-wide BMS with minimal segmentation from academic network"},
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "Multi-building BACnet campus network discovery"}
        ],
        "recommended_traffic_schedule": "office_hours",
        "process_sim": {
            "template": "building_automation",
            "description": "Campus HVAC with multi-building zone control and central plant",
            "key_variables": ["setpoint", "zone_temp", "supply_air_temp", "damper_position", "humidity"],
            "available_faults": ["fan_failure", "sensor_drift"],
        },
        "devices": [
            # ============================================================
            # CAMPUS CORE (Level 3) - 5 devices
            # Central BMS servers and campus-wide infrastructure
            # ============================================================
            # Campus BMS Servers - Honeywell JACE 8000
            # Fingerprint has: bacnet_identity ONLY
            {"type": "bms_server", "vendor": "honeywell", "count": 2, "zone": "campus_core",
             "name_pattern": "Campus_BMS_Server_{n}", "protocols": ["bacnet"],
             "fingerprint_model": "JACE 8000",
             "role": "Campus BMS Server"},

            # Core Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "campus_core",
             "name_pattern": "Campus_Core_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Campus Network Switch"},

            # EWON Remote Access Gateway - Talk2M cloud connectivity
            # Fingerprint has: modbus_identity, ethernet_ip_identity, snmp_identity
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "campus_core",
             "name": "Campus_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Campus Remote Access Gateway",
             "external_comms": True},

            # Engineering Workstation - Honeywell XL Web
            # Fingerprint has: bacnet_identity ONLY
            {"type": "engineering_station", "vendor": "honeywell", "count": 1, "zone": "campus_core",
             "name": "Campus_Engineering_Workstation", "protocols": ["bacnet"],
             "fingerprint_model": "XL Web",
             "role": "Engineering Workstation"},

            # ============================================================
            # BUILDING A - Academic Building (Level 2) - 10 devices
            # Johnson Controls + Trane equipment
            # ============================================================
            # Building Supervisor - Johnson Controls NAE55
            # Fingerprint has: bacnet_identity, snmp_identity
            {"type": "controller", "vendor": "johnson_controls", "count": 2, "zone": "building_a",
             "name_pattern": "Building_A_Supervisor_{n}", "protocols": ["bacnet"],
             "fingerprint_model": "NAE55",
             "role": "Building Supervisor"},

            # AHU Controllers - Johnson Controls FEC26
            # Fingerprint has: bacnet_identity ONLY
            {"type": "ahu_controller", "vendor": "johnson_controls", "count": 3, "zone": "building_a",
             "name_pattern": "Building_A_AHU_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "FEC26",
             "role": "AHU Controller"},

            # Unit Controllers - Trane UC600
            # Fingerprint has: bacnet_identity ONLY
            {"type": "zone_controller", "vendor": "trane", "count": 3, "zone": "building_a",
             "name_pattern": "Building_A_Unit_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "UC600",
             "role": "Unit Controller"},

            # Building Controller - Distech EC-BOS-8
            # Fingerprint has: bacnet_identity ONLY (no modbus_identity)
            {"type": "building_controller", "vendor": "distech", "count": 2, "zone": "building_a",
             "name_pattern": "Building_A_Controller_{n}", "protocols": ["bacnet"],
             "fingerprint_model": "EC-BOS-8",
             "role": "Building Controller"},

            # ============================================================
            # BUILDING B - Research Building (Level 2) - 10 devices
            # Siemens + Schneider equipment (different vendor ecosystem)
            # ============================================================
            # Building Supervisor - Johnson Controls SNC
            # Fingerprint has: bacnet_identity ONLY
            {"type": "controller", "vendor": "johnson_controls", "count": 2, "zone": "building_b",
             "name_pattern": "Building_B_Supervisor_{n}", "protocols": ["bacnet"],
             "fingerprint_model": "SNC",
             "role": "Building Supervisor"},

            # Room Controllers - Siemens DXR2.E12
            # Fingerprint has: bacnet_identity ONLY
            {"type": "room_controller", "vendor": "siemens", "count": 4, "zone": "building_b",
             "name_pattern": "Building_B_Room_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "DXR2.E12",
             "role": "Room Automation Station"},

            # Building Controllers - Siemens Climatix C600
            # Fingerprint has: bacnet_identity ONLY
            {"type": "building_controller", "vendor": "siemens", "count": 2, "zone": "building_b",
             "name_pattern": "Building_B_Controller_{n}", "protocols": ["bacnet"],
             "fingerprint_model": "C600",
             "role": "Building Controller"},

            # Zone Controller - Schneider CX9680
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "zone_controller", "vendor": "schneider", "count": 2, "zone": "building_b",
             "name_pattern": "Building_B_Zone_{n}_Controller", "protocols": ["bacnet", "modbus_tcp"],
             "fingerprint_model": "CX9680",
             "role": "Zone Controller"},

            # ============================================================
            # CENTRAL PLANT (Level 2) - 8 devices
            # Chiller/boiler plant with multi-vendor controllers
            # ============================================================
            # Chiller Controllers - Carel pCO5+
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "chiller_controller", "vendor": "carel", "count": 3, "zone": "central_plant",
             "name_pattern": "Central_Plant_Chiller_{n}_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "pCO5+",
             "role": "Chiller Controller"},

            # Boiler Controller - Carrier Pro Open
            # Fingerprint has: bacnet_identity ONLY (no modbus_identity)
            {"type": "boiler_controller", "vendor": "carrier", "count": 2, "zone": "central_plant",
             "name_pattern": "Central_Plant_Boiler_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "Pro Open",
             "role": "Boiler Controller"},

            # Plant Supervisor - Delta Controls Manager
            # Fingerprint has: bacnet_identity ONLY
            {"type": "plant_controller", "vendor": "delta_controls", "count": 1, "zone": "central_plant",
             "name": "Central_Plant_Manager", "protocols": ["bacnet"],
             "fingerprint_model": "Manager",
             "role": "Central Plant Manager"},

            # AHU for Central Plant - Trane SC+
            # Fingerprint has: bacnet_identity ONLY
            {"type": "hvac_controller", "vendor": "trane", "count": 2, "zone": "central_plant",
             "name_pattern": "Central_Plant_HVAC_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "SC+",
             "role": "Plant HVAC Controller"},

            # ============================================================
            # FIELD DEVICES (Level 1) - 12 devices
            # Distributed VAV, room controllers, and field equipment
            # ============================================================
            # VAV Controllers - Distech ECY-VAV
            # Fingerprint has: bacnet_identity ONLY
            {"type": "vav_controller", "vendor": "distech", "count": 4, "zone": "field_devices",
             "name_pattern": "Field_VAV_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "ECY-VAV",
             "role": "VAV Controller"},

            # Room Controllers - Siemens DXR2.E12
            # Fingerprint has: bacnet_identity ONLY
            {"type": "room_controller", "vendor": "siemens", "count": 2, "zone": "field_devices",
             "name_pattern": "Field_Room_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "DXR2.E12",
             "role": "Room Controller"},

            # Field Controllers - Delta Controls eBCON
            # Fingerprint has: bacnet_identity ONLY
            {"type": "field_controller", "vendor": "delta_controls", "count": 3, "zone": "field_devices",
             "name_pattern": "Field_IO_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "eBCON",
             "role": "Field Controller"},

            # Distribution Switches
            {"type": "switch", "vendor": "cisco", "count": 3, "zone": "field_devices",
             "name_pattern": "Field_Distribution_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Field Network Switch"},
        ],
        "flows": [
            # ============================================================
            # Campus Core Flows - Server to Building Supervisors
            # ============================================================
            # BACnet Subscription - Campus servers to building supervisors (5s)
            {"protocol": "bacnet", "pattern": "subscription", "interval_ms": 5000,
             "source_types": ["bms_server"],
             "target_types": ["controller"],
             "source_zones": ["campus_core"],
             "target_zones": ["building_a", "building_b"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # BACnet Polling - Engineering workstation to BMS servers (10s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["engineering_station"],
             "target_types": ["bms_server"],
             "source_zones": ["campus_core"],
             "target_zones": ["campus_core"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # ============================================================
            # Building A Flows - Johnson Controls / Trane
            # ============================================================
            # BACnet Polling - NAE55 to FEC/UC600 (1s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["controller"],
             "target_types": ["ahu_controller", "zone_controller", "building_controller"],
             "source_zones": ["building_a"], "target_zones": ["building_a"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # Building B Flows - Siemens / Schneider
            # ============================================================
            # BACnet Polling - SNC to room/zone controllers (1s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["controller"],
             "target_types": ["room_controller", "building_controller", "zone_controller"],
             "source_zones": ["building_b"], "target_zones": ["building_b"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Modbus TCP - Schneider zone controllers (1s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["controller"],
             "target_types": ["zone_controller"],
             "source_zones": ["building_b"], "target_zones": ["building_b"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # Central Plant Flows
            # ============================================================
            # BACnet Polling - Plant manager to chillers/boilers (1s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plant_controller"],
             "target_types": ["chiller_controller", "boiler_controller", "hvac_controller"],
             "source_zones": ["central_plant"], "target_zones": ["central_plant"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Modbus TCP - Chiller controllers (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plant_controller"],
             "target_types": ["chiller_controller"],
             "source_zones": ["central_plant"], "target_zones": ["central_plant"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # ============================================================
            # Building to Field Device Flows
            # ============================================================
            # BACnet Polling - Building controllers to VAV/field (500ms)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 500,
             "source_types": ["building_controller", "zone_controller"],
             "target_types": ["vav_controller", "room_controller", "field_controller"],
             "source_zones": ["building_a", "building_b"],
             "target_zones": ["field_devices"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # ============================================================
            # BACnet COV Notifications (async)
            # ============================================================
            {"protocol": "bacnet", "pattern": "cov", "interval_ms": 2000,
             "source_types": ["vav_controller", "room_controller", "field_controller"],
             "target_types": ["controller"],
             "source_zones": ["field_devices"],
             "target_zones": ["building_a", "building_b"],
             "jitter_ms": 1000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP Infrastructure Monitoring (30s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["bms_server"],
             "target_types": ["switch", "controller", "remote_gateway"],
             "source_zones": ["campus_core"],
             "target_zones": ["campus_core", "building_a", "field_devices"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # EWON Remote Access - Talk2M Cloud Communication (30s heartbeat)
            # Uses actual Talk2M public IPs for Cyber Vision external detection
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source_types": ["remote_gateway"], "target_types": ["cloud"],
             "source_zones": ["campus_core"], "target_zones": ["external"],
             "external_ip": "51.38.74.240",  # Talk2M Europe VPN server
             "external_port": 443,
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # EWON Modbus polling to central plant (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["chiller_controller"],
             "source_zones": ["campus_core"], "target_zones": ["central_plant"],
             "jitter_ms": 500, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "campus_core", "name": "Campus Core Network", "level": 3,
             "subnet_offset": 0, "vlan": 300, "security_level": "critical"},
            {"id": "building_a", "name": "Building A - Academic", "level": 2,
             "subnet_offset": 1, "vlan": 310, "security_level": "high"},
            {"id": "building_b", "name": "Building B - Research", "level": 2,
             "subnet_offset": 2, "vlan": 320, "security_level": "high"},
            {"id": "central_plant", "name": "Central Plant", "level": 2,
             "subnet_offset": 3, "vlan": 330, "security_level": "high"},
            {"id": "field_devices", "name": "Field Device Network", "level": 1,
             "subnet_offset": 4, "vlan": 340, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap", "subscription_timeout", "cov_flood"],
            "protocol": ["bacnet_reject", "bacnet_abort", "modbus_exception"],
            "sequence": ["out_of_order", "duplicate_invoke_id"],
            "payload": ["value_spike", "setpoint_change", "alarm_storm"],
            "network": ["broadcast_storm", "multicast_flood"],
            "security": ["unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["51.38.74.240", "87.98.169.126"],  # Talk2M VPN server IPs
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "enable_recon": True,
        },
        "total_duration_ms": 600000,  # 10 minutes
    },
}
