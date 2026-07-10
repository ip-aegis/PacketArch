# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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
        "description": "Mid-sized commercial office BAS with a Niagara JACE supervisor and three "
                       "zone field controllers (one per HVAC zone) over BACnet/IP. Engineering "
                       "workstation + historian + NMS at L3; light IDMZ for vendor remote "
                       "access. 42 devices across 5 zones.",
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
             "name_pattern": "Office_BMS_Server_{n:02d}", "protocols": ["bacnet", "snmp"],
             "fingerprint_model": "Server", "firmware_version": "7.0",
             "role": "Central BMS Server"},

            # Supervisory Controllers - Johnson Controls NAE55
            # Fingerprint has: bacnet_identity, snmp_identity
            {"type": "controller", "vendor": "johnson_controls", "count": 2, "zone": "bms_core",
             "name_pattern": "BMS_Supervisor_Controller_{n:02d}", "protocols": ["bacnet", "snmp"],
             "fingerprint_model": "NAE55",
             "role": "Supervisory Network Controller"},

            # Industrial Switches with SNMP monitoring
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "bms_core",
             "name_pattern": "BMS_Core_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E", "firmware_version": "15.2(7)E6",
             "role": "BMS Network Switch"},

            # Network Management Station - Paessler PRTG (SNMP monitoring of
            # BMS core switches and the remote-access gateway)
            {"type": "nms", "vendor": "Paessler", "count": 1, "zone": "bms_core",
             "name": "Office_Network_Management_Station", "protocols": ["snmp"],
             "fingerprint_model": "PRTG Network Monitor 24",
             "architectural_role": "nms_server",
             "role": "Network Management Station"},

            # EWON Remote Access Gateway - Talk2M cloud connectivity
            # Fingerprint has: modbus_identity, snmp_identity, external_communications
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "bms_core",
             "name_pattern": "BMS_Remote_Access_Gateway_{n:02d}", "protocols": ["modbus_tcp", "snmp"],
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
             "name_pattern": "HVAC_Supervisor_{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "SC+", "firmware_version": "V6.10",
             "role": "HVAC Supervisory Controller"},

            # AHU Controllers - Johnson Controls FEC26
            # Fingerprint has: bacnet_identity ONLY
            {"type": "ahu_controller", "vendor": "johnson_controls", "count": 4, "zone": "hvac_control",
             "name_pattern": "AHU_Controller_{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "FEC26",
             "role": "AHU Controller"},

            # Chiller Controllers - Carel pCO5+
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "chiller_controller", "vendor": "carel", "count": 2, "zone": "hvac_control",
             "name_pattern": "Chiller_Controller_{n:02d}", "protocols": ["modbus_tcp", "bacnet"],
             "fingerprint_model": "pCO5+", "firmware_version": "V3.2.0",
             "role": "Chiller Controller"},

            # Building Controllers - Schneider CX9680
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "building_controller", "vendor": "schneider", "count": 2, "zone": "hvac_control",
             "name_pattern": "Building_Controller_{n:02d}", "protocols": ["bacnet", "modbus_tcp"],
             "fingerprint_model": "CX9680", "firmware_version": "V2.6.0",
             "role": "Building Controller"},

            # ============================================================
            # FLOOR ZONE (Level 1) - 20 devices
            # VAV controllers, room controllers, field equipment
            # ============================================================
            # VAV Controllers - Distech ECY-VAV
            # Fingerprint has: bacnet_identity ONLY
            {"type": "vav_controller", "vendor": "distech", "count": 8, "zone": "floor_zone",
             "name_pattern": "Floor_VAV_Controller_{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "ECY-VAV",
             "role": "VAV Controller"},

            # Room Controllers - Siemens DXR2.E12
            # Fingerprint has: bacnet_identity ONLY
            {"type": "room_controller", "vendor": "siemens", "count": 6, "zone": "floor_zone",
             "name_pattern": "Room_Controller_{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "DXR2.E12", "firmware_version": "V4.0",
             "role": "Room Automation Station"},

            # Field Controllers - Delta Controls eBCON
            # Fingerprint has: bacnet_identity ONLY
            {"type": "field_controller", "vendor": "delta_controls", "count": 4, "zone": "floor_zone",
             "name_pattern": "Floor_Field_Controller_{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "eBCON",
             "role": "Field Controller"},

            # Zone Controllers - Trane UC600
            # Fingerprint has: bacnet_identity ONLY
            {"type": "zone_controller", "vendor": "trane", "count": 2, "zone": "floor_zone",
             "name_pattern": "Floor_Zone_Controller_{n:02d}", "protocols": ["bacnet"],
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
            # SNMP - NMS Infrastructure Monitoring (30s)
            # NMS polls core switches + remote-access gateway
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["nms"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["bms_core"], "target_zones": ["bms_core"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # SNMP - BMS server health poll of supervisory controllers (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["bms_server"], "target_types": ["controller"],
             "source_zones": ["bms_core"], "target_zones": ["bms_core"],
             "jitter_ms": 3000, "jitter_type": "uniform"},


            # EWON Modbus polling to building controllers (5s). The building
            # controllers, not the EWON, poll the subordinate chillers.
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["building_controller"],
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
        "conduits": [
            # L3 (bms_core) <-> L2 (hvac_control): Supervisory to HVAC controllers
            {"id": "bms_core_to_hvac", "name": "BMS Core \u2194 HVAC Control",
             "source_zone": "bms_core", "target_zone": "hvac_control",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet", "modbus_tcp"],
             "security_level": "high",
             "description": "Supervisory controllers and EWON gateway polling HVAC, AHU, chiller, and building controllers"},
            # L2 (hvac_control) <-> L1 (floor_zone): HVAC to field controllers
            {"id": "hvac_to_floor", "name": "HVAC Control \u2194 Floor Zone",
             "source_zone": "hvac_control", "target_zone": "floor_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet"],
             "security_level": "standard",
             "description": "HVAC and building controllers polling VAV, room, field, and zone controllers"},
            # L1 (floor_zone) <-> L3 (bms_core): COV notifications from field to supervisory
            {"id": "floor_to_bms_core", "name": "Floor Zone \u2194 BMS Core",
             "source_zone": "floor_zone", "target_zone": "bms_core",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet"],
             "security_level": "high",
             "description": "VAV and room controllers sending BACnet COV notifications to supervisory controllers"},
            # L3 (bms_core) <-> L4 (external): Remote access cloud connectivity
            {"id": "bms_core_to_external", "name": "BMS Core \u2194 External",
             "source_zone": "bms_core", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https"],
             "security_level": "critical",
             "description": "EWON remote access gateway Talk2M cloud heartbeat and VPN tunnel"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 2: DATA CENTER INFRASTRUCTURE (28 devices)
    # Tier III data center with precision cooling and power monitoring
    # ============================================================
    "data_center_infrastructure": {
        "name": "Data Center Infrastructure",
        "description": "Mid-sized colocation data center DCIM facility-side OT. Four rack rows "
                       "polled over SNMP / Modbus, mechanical / cooling zone with chiller "
                       "controls and CRAH units, dedicated power-plant zone for UPS / ATS / "
                       "generator. NMS-heavy traffic — every device polled by DCNM. 59 devices "
                       "across 8 zones.",
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
             "name_pattern": "DataCenter_DCIM_Server_{n:02d}", "protocols": ["bacnet", "snmp"],
             "fingerprint_model": "Server", "firmware_version": "7.0",
             "role": "DCIM Server"},

            # Building Controllers - Schneider CX9680
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "building_controller", "vendor": "schneider", "count": 2, "zone": "dcim_core",
             "name_pattern": "DataCenter_Controller_{n:02d}", "protocols": ["bacnet", "modbus_tcp"],
             "fingerprint_model": "CX9680", "firmware_version": "V2.6.0",
             "role": "Data Center Controller"},

            # Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "dcim_core",
             "name_pattern": "DCIM_Core_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E", "firmware_version": "15.2(7)E6",
             "role": "DCIM Network Switch"},

            # EWON Remote Access Gateway - Talk2M cloud connectivity for remote DCIM
            # Fingerprint has: modbus_identity, snmp_identity, external_communications
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "dcim_core",
             "name_pattern": "DCIM_Remote_Access_Gateway_{n:02d}", "protocols": ["modbus_tcp", "snmp"],
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
             "name_pattern": "InRow_Cooling_Unit_{n:02d}", "protocols": ["modbus_tcp", "bacnet"],
             "fingerprint_model": "InRow DX",
             "role": "In-Row Cooling Unit"},

            # Chiller Controllers - Carel pCO5+
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "chiller_controller", "vendor": "carel", "count": 2, "zone": "cooling_zone",
             "name_pattern": "Cooling_Chiller_Controller_{n:02d}", "protocols": ["modbus_tcp", "bacnet"],
             "fingerprint_model": "pCO5+", "firmware_version": "V3.2.0",
             "role": "Chiller Controller"},

            # ============================================================
            # POWER ZONE (Level 2) - 6 devices
            # UPS systems and main PDUs
            # ============================================================
            # UPS Systems - Schneider Galaxy VM
            # Fingerprint has: modbus_identity, snmp_identity (NO bacnet_identity)
            {"type": "ups", "vendor": "schneider", "count": 4, "zone": "power_zone",
             "name_pattern": "DataCenter_UPS_{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Galaxy VM",
             "role": "UPS System"},

            # AHU/Cooling for electrical room - Trane UC600
            # Fingerprint has: bacnet_identity ONLY
            {"type": "ahu_controller", "vendor": "trane", "count": 2, "zone": "power_zone",
             "name_pattern": "Electrical_Room_Cooling_{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "UC600",
             "role": "Electrical Room Cooling"},

            # ============================================================
            # RACK ZONE (Level 1) - 10 devices
            # Rack PDUs and in-row monitoring
            # ============================================================
            # Rack PDUs - Schneider Rack PDU
            # Fingerprint has: modbus_identity, snmp_identity (NO bacnet_identity)
            {"type": "pdu", "vendor": "schneider", "count": 8, "zone": "rack_zone",
             "name_pattern": "Rack_PDU_{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Rack PDU",
             "role": "Rack PDU"},

            # Switches for rack monitoring
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "rack_zone",
             "name_pattern": "Rack_Network_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E", "firmware_version": "15.2(7)E6",
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
        "conduits": [
            # L3 (dcim_core) <-> L2 (cooling_zone): DCIM to precision cooling
            {"id": "dcim_to_cooling", "name": "DCIM Core \u2194 Cooling Zone",
             "source_zone": "dcim_core", "target_zone": "cooling_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet", "modbus_tcp"],
             "security_level": "critical",
             "description": "DCIM server and building controllers polling CRAC units and chiller controllers"},
            # L3 (dcim_core) <-> L2 (power_zone): DCIM to power distribution
            {"id": "dcim_to_power", "name": "DCIM Core \u2194 Power Zone",
             "source_zone": "dcim_core", "target_zone": "power_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet", "modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "Building controllers polling UPS systems and electrical room cooling; SNMP monitoring of UPS"},
            # L2 (power_zone) <-> L1 (rack_zone): Power to rack-level PDUs
            {"id": "power_to_rack", "name": "Power Zone \u2194 Rack Zone",
             "source_zone": "power_zone", "target_zone": "rack_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "high",
             "description": "Power distribution monitoring of rack PDUs via Modbus TCP and SNMP"},
            # L3 (dcim_core) <-> L1 (rack_zone): DCIM direct to rack monitoring
            {"id": "dcim_to_rack", "name": "DCIM Core \u2194 Rack Zone",
             "source_zone": "dcim_core", "target_zone": "rack_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "high",
             "description": "DCIM server SNMP monitoring of rack PDUs and switches"},
            # L3 (dcim_core) <-> L4 (external): Remote access cloud connectivity
            {"id": "dcim_to_external", "name": "DCIM Core \u2194 External",
             "source_zone": "dcim_core", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https"],
             "security_level": "critical",
             "description": "EWON remote access gateway Talk2M cloud heartbeat for remote DCIM monitoring"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 3: UNIVERSITY CAMPUS BMS (45 devices)
    # Multi-building campus with distributed BMS architecture
    # ============================================================
    "university_campus_bms": {
        "name": "University Campus BMS",
        "description": "University campus BAS spanning four building zones, each with redundant "
                       "Niagara field controllers. Larger HVAC field complement (fans, valves, "
                       "sensors) per zone; full IDMZ stack for IT integration. 73 devices across "
                       "6 zones.",
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
             "name_pattern": "Campus_BMS_Server_{n}", "protocols": ["bacnet", "snmp"],
             "fingerprint_model": "JACE 8000", "firmware_version": "N4.8",
             "role": "Campus BMS Server"},

            # Core Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "campus_core",
             "name_pattern": "Campus_Core_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E", "firmware_version": "15.2(7)E6",
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
             "fingerprint_model": "XL Web", "firmware_version": "XLWebExe-2-01-00",
             "role": "Engineering Workstation"},

            # ============================================================
            # BUILDING A - Academic Building (Level 2) - 10 devices
            # Johnson Controls + Trane equipment
            # ============================================================
            # Building Supervisor - Johnson Controls NAE55
            # Fingerprint has: bacnet_identity, snmp_identity
            {"type": "controller", "vendor": "johnson_controls", "count": 2, "zone": "building_a",
             "name_pattern": "Building_A_Supervisor_{n}", "protocols": ["bacnet", "snmp"],
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
             "fingerprint_model": "EC-BOS-8", "firmware_version": "V1.4.5",
             "role": "Building Controller"},

            # ============================================================
            # BUILDING B - Research Building (Level 2) - 10 devices
            # Siemens + Schneider equipment (different vendor ecosystem)
            # ============================================================
            # Building Supervisor - Johnson Controls SNC
            # Fingerprint has: bacnet_identity ONLY
            {"type": "controller", "vendor": "johnson_controls", "count": 2, "zone": "building_b",
             "name_pattern": "Building_B_Supervisor_{n}", "protocols": ["bacnet", "snmp"],
             "fingerprint_model": "SNC",
             "role": "Building Supervisor"},

            # Room Controllers - Siemens DXR2.E12
            # Fingerprint has: bacnet_identity ONLY
            {"type": "room_controller", "vendor": "siemens", "count": 4, "zone": "building_b",
             "name_pattern": "Building_B_Room_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "DXR2.E12", "firmware_version": "V4.0",
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
             "fingerprint_model": "CX9680", "firmware_version": "V2.6.0",
             "role": "Zone Controller"},

            # ============================================================
            # CENTRAL PLANT (Level 2) - 8 devices
            # Chiller/boiler plant with multi-vendor controllers
            # ============================================================
            # Chiller Controllers - Carel pCO5+
            # Fingerprint has: bacnet_identity, modbus_identity
            {"type": "chiller_controller", "vendor": "carel", "count": 3, "zone": "central_plant",
             "name_pattern": "Central_Plant_Chiller_{n}_Controller", "protocols": ["modbus_tcp", "bacnet"],
             "fingerprint_model": "pCO5+", "firmware_version": "V3.2.0",
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
             "name": "Central_Plant_Manager", "protocols": ["bacnet", "modbus_tcp"],
             "fingerprint_model": "Manager",
             "role": "Central Plant Manager"},

            # AHU for Central Plant - Trane SC+
            # Fingerprint has: bacnet_identity ONLY
            {"type": "hvac_controller", "vendor": "trane", "count": 2, "zone": "central_plant",
             "name_pattern": "Central_Plant_HVAC_{n}_Controller", "protocols": ["bacnet"],
             "fingerprint_model": "SC+", "firmware_version": "V6.10",
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
             "fingerprint_model": "DXR2.E12", "firmware_version": "V4.0",
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
             "fingerprint_model": "IE-4000-8GT4G-E", "firmware_version": "15.2(7)E6",
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
        "conduits": [
            # L3 (campus_core) <-> L2 (building_a): Campus to Building A
            {"id": "campus_to_building_a", "name": "Campus Core \u2194 Building A",
             "source_zone": "campus_core", "target_zone": "building_a",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet", "snmp"],
             "security_level": "high",
             "description": "Campus BMS servers and engineering workstation polling Building A supervisors and controllers"},
            # L3 (campus_core) <-> L2 (building_b): Campus to Building B
            {"id": "campus_to_building_b", "name": "Campus Core \u2194 Building B",
             "source_zone": "campus_core", "target_zone": "building_b",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet", "snmp"],
             "security_level": "high",
             "description": "Campus BMS servers polling Building B supervisors, room, and zone controllers"},
            # L3 (campus_core) <-> L2 (central_plant): Campus to Central Plant
            {"id": "campus_to_central_plant", "name": "Campus Core \u2194 Central Plant",
             "source_zone": "campus_core", "target_zone": "central_plant",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "EWON gateway Modbus polling to central plant chiller controllers"},
            # L2 (building_a) <-> L1 (field_devices): Building A to field devices
            {"id": "building_a_to_field", "name": "Building A \u2194 Field Devices",
             "source_zone": "building_a", "target_zone": "field_devices",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet"],
             "security_level": "standard",
             "description": "Building A controllers polling field VAV, room, and I/O controllers"},
            # L2 (building_b) <-> L1 (field_devices): Building B to field devices
            {"id": "building_b_to_field", "name": "Building B \u2194 Field Devices",
             "source_zone": "building_b", "target_zone": "field_devices",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet"],
             "security_level": "standard",
             "description": "Building B controllers polling field VAV, room, and I/O controllers"},
            # L1 (field_devices) <-> L2 (building_a, building_b): COV notifications
            {"id": "field_to_buildings", "name": "Field Devices \u2194 Buildings",
             "source_zone": "field_devices", "target_zone": "building_a",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet"],
             "security_level": "standard",
             "description": "Field VAV and room controllers sending BACnet COV notifications to building supervisors"},
            # L3 (campus_core) <-> L1 (field_devices): SNMP infrastructure monitoring
            {"id": "campus_to_field", "name": "Campus Core \u2194 Field Devices",
             "source_zone": "campus_core", "target_zone": "field_devices",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "high",
             "description": "Campus BMS server SNMP monitoring of field distribution switches (vertical NMS hierarchy)"},
            # L3 (campus_core) <-> L4 (external): Remote access cloud connectivity
            {"id": "campus_to_external", "name": "Campus Core \u2194 External",
             "source_zone": "campus_core", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https"],
             "security_level": "critical",
             "description": "EWON remote access gateway Talk2M cloud heartbeat for campus remote monitoring"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
    },

    # ============================================================
    # TEMPLATE 4: TENANT ELECTRICAL SUB-METERING (31 devices)
    # Multi-tenant office tower billing tenants on actual metered
    # consumption per EED recast (EU) 2023/1791 Art. 29 (landlord
    # sub-metering/billing obligation).
    # ============================================================
    "tenant_submetering_office": {
        "name": "Tenant Electrical Sub-Metering & Energy Billing",
        "description": "Multi-tenant office tower retrofitted for EU EED (2023/1791 "
                       "Art. 29) tenant billing on actual metered consumption. A "
                       "Niagara JACE 8000 energy-management head-end polls a "
                       "main-incomer power quality meter and five tenant-riser "
                       "sub-metering concentrators, each aggregating four per-tenant "
                       "electric meters. Each riser is its own isolated subnet — no "
                       "riser-to-riser traffic — to keep one tenant's billing data "
                       "from leaking to another. 31 devices across 7 zones.",
        "vertical": "building_automation",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "bas_compromise", "relevance": "high", "rationale": "BACnet Who-Is discovery and manipulation against the JACE energy-management head-end"},
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "A compromised tenant network segment pivoting into another tenant's VMU-C EM concentrator (CVE-2017-5144 unauthenticated access) to read or tamper with billing data"},
            {"playbook_id": "network_recon", "relevance": "medium", "rationale": "Modbus/BACnet service enumeration across tenant riser subnets"}
        ],
        "recommended_traffic_schedule": "office_hours",
        "devices": [
            # ============================================================
            # ENERGY CORE ZONE (Level 3) - 6 devices
            # Landlord energy-management head-end, main-incomer meter,
            # infrastructure, billing-platform remote-access gateway
            # ============================================================
            # Landlord Energy Management Head-End - Honeywell/Tridium JACE 8000
            # Fingerprint has: modbus_identity, bacnet_identity, snmp_identity
            {"type": "bms_controller", "vendor": "honeywell", "count": 1, "zone": "energy_core",
             "name_pattern": "Landlord_Energy_Manager_{n:02d}", "protocols": ["modbus_tcp", "bacnet"],
             "fingerprint_model": "JACE 8000",
             "role": "Landlord Energy Management Head-End"},

            # Main Incomer Power Quality Meter - Janitza UMG 604-PRO
            # Fingerprint has: modbus_identity, bacnet_identity, snmp_identity
            {"type": "power_meter", "vendor": "janitza", "count": 1, "zone": "energy_core",
             "name_pattern": "Main_Incomer_Power_Meter_{n:02d}", "protocols": ["modbus_tcp", "bacnet", "snmp"],
             "fingerprint_model": "UMG 604-PRO",
             "role": "Main Incomer Power Quality Meter"},

            # Industrial Switches with SNMP monitoring
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "energy_core",
             "name_pattern": "Energy_Core_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E", "firmware_version": "15.2(7)E6",
             "role": "Energy Core Network Switch"},

            # Network Management Station - Paessler PRTG (SNMP monitoring of
            # the energy-core switches, ESCO gateway, and the main-incomer
            # power-quality meter, which exposes an SNMP identity)
            {"type": "nms", "vendor": "Paessler", "count": 1, "zone": "energy_core",
             "name": "Tenant_Energy_Network_Management_Station", "protocols": ["snmp"],
             "fingerprint_model": "PRTG Network Monitor 24",
             "architectural_role": "nms_server",
             "role": "Network Management Station"},

            # ESCO Billing Platform Remote Access Gateway - EWON Flexy 205
            # Fingerprint has: modbus_identity, snmp_identity, external_communications
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "energy_core",
             "name_pattern": "Tenant_Billing_Cloud_Gateway_{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "ESCO Billing Platform Remote Access Gateway",
             "external_comms": True},

            # Engineering Workstation - Honeywell XL Web
            # Fingerprint has: bacnet_identity ONLY
            {"type": "engineering_station", "vendor": "honeywell", "count": 1, "zone": "energy_core",
             "name": "Energy_Engineering_Workstation_01", "protocols": ["bacnet"],
             "fingerprint_model": "XL Web", "firmware_version": "XLWebExe-2-01-00",
             "role": "Engineering Workstation"},

            # ============================================================
            # TENANT RISER ZONES (Level 1) - 5 devices each, 5 risers = 25 devices
            # Each riser is an isolated tenant-billing subnet (no riser-to-riser
            # conduit) with one Carlo Gavazzi VMU-C EM concentrator aggregating
            # four Carlo Gavazzi EM24-Ethernet per-tenant meters.
            # ============================================================
            # Riser A - Floors 2-5
            {"type": "meter_data_concentrator", "vendor": "carlo_gavazzi", "count": 1, "zone": "riser_a",
             "name": "Riser_A_Submetering_Concentrator_01", "protocols": ["modbus_tcp"],
             "fingerprint_model": "VMU-C EM",
             "role": "Riser Sub-Metering Concentrator"},
            {"type": "power_meter", "vendor": "carlo_gavazzi", "count": 4, "zone": "riser_a",
             "name_pattern": "Riser_A_Tenant_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "EM24DINAV23XE1X",
             "role": "Tenant Electrical Sub-Meter"},

            # Riser B - Floors 6-9
            {"type": "meter_data_concentrator", "vendor": "carlo_gavazzi", "count": 1, "zone": "riser_b",
             "name": "Riser_B_Submetering_Concentrator_01", "protocols": ["modbus_tcp"],
             "fingerprint_model": "VMU-C EM",
             "role": "Riser Sub-Metering Concentrator"},
            {"type": "power_meter", "vendor": "carlo_gavazzi", "count": 4, "zone": "riser_b",
             "name_pattern": "Riser_B_Tenant_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "EM24DINAV23XE1X",
             "role": "Tenant Electrical Sub-Meter"},

            # Riser C - Floors 10-13
            {"type": "meter_data_concentrator", "vendor": "carlo_gavazzi", "count": 1, "zone": "riser_c",
             "name": "Riser_C_Submetering_Concentrator_01", "protocols": ["modbus_tcp"],
             "fingerprint_model": "VMU-C EM",
             "role": "Riser Sub-Metering Concentrator"},
            {"type": "power_meter", "vendor": "carlo_gavazzi", "count": 4, "zone": "riser_c",
             "name_pattern": "Riser_C_Tenant_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "EM24DINAV23XE1X",
             "role": "Tenant Electrical Sub-Meter"},

            # Riser D - Floors 14-17
            {"type": "meter_data_concentrator", "vendor": "carlo_gavazzi", "count": 1, "zone": "riser_d",
             "name": "Riser_D_Submetering_Concentrator_01", "protocols": ["modbus_tcp"],
             "fingerprint_model": "VMU-C EM",
             "role": "Riser Sub-Metering Concentrator"},
            {"type": "power_meter", "vendor": "carlo_gavazzi", "count": 4, "zone": "riser_d",
             "name_pattern": "Riser_D_Tenant_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "EM24DINAV23XE1X",
             "role": "Tenant Electrical Sub-Meter"},

            # Riser E - Floors 18-21
            {"type": "meter_data_concentrator", "vendor": "carlo_gavazzi", "count": 1, "zone": "riser_e",
             "name": "Riser_E_Submetering_Concentrator_01", "protocols": ["modbus_tcp"],
             "fingerprint_model": "VMU-C EM",
             "role": "Riser Sub-Metering Concentrator"},
            {"type": "power_meter", "vendor": "carlo_gavazzi", "count": 4, "zone": "riser_e",
             "name_pattern": "Riser_E_Tenant_Meter_{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "EM24DINAV23XE1X",
             "role": "Tenant Electrical Sub-Meter"},
        ],
        "flows": [
            # ============================================================
            # SNMP - NMS poll of the Main Incomer Power Quality Meter (10s).
            # The Janitza UMG 604-PRO exposes an SNMP identity; the NMS
            # collects its operational telemetry here (the tenant-billing
            # traffic proper is the JACE->riser-concentrator Modbus below).
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["nms"], "target_types": ["power_meter"],
             "source_zones": ["energy_core"], "target_zones": ["energy_core"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # ============================================================
            # Modbus TCP - JACE to Riser Concentrators (60s billing cadence,
            # deliberately much slower than HVAC control traffic elsewhere
            # in this vertical)
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["bms_controller"], "target_types": ["meter_data_concentrator"],
             "source_zones": ["energy_core"],
             "target_zones": ["riser_a", "riser_b", "riser_c", "riser_d", "riser_e"],
             "jitter_ms": 5000, "jitter_type": "gaussian"},

            # ============================================================
            # Modbus TCP - Riser Concentrators to Tenant Meters (15s,
            # riser-internal RS-485-over-Modbus polling). One flow spec per
            # riser so each concentrator polls ONLY its own riser's meters —
            # no cross-riser tenant-billing leakage.
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 15000,
             "source_types": ["meter_data_concentrator"], "target_types": ["power_meter"],
             "source_zones": ["riser_a"], "target_zones": ["riser_a"],
             "jitter_ms": 1500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 15000,
             "source_types": ["meter_data_concentrator"], "target_types": ["power_meter"],
             "source_zones": ["riser_b"], "target_zones": ["riser_b"],
             "jitter_ms": 1500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 15000,
             "source_types": ["meter_data_concentrator"], "target_types": ["power_meter"],
             "source_zones": ["riser_c"], "target_zones": ["riser_c"],
             "jitter_ms": 1500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 15000,
             "source_types": ["meter_data_concentrator"], "target_types": ["power_meter"],
             "source_zones": ["riser_d"], "target_zones": ["riser_d"],
             "jitter_ms": 1500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 15000,
             "source_types": ["meter_data_concentrator"], "target_types": ["power_meter"],
             "source_zones": ["riser_e"], "target_zones": ["riser_e"],
             "jitter_ms": 1500, "jitter_type": "gaussian"},

            # ============================================================
            # BACnet - Engineering Workstation Oversight Poll (5s)
            # ============================================================
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["engineering_station"], "target_types": ["bms_controller"],
             "source_zones": ["energy_core"], "target_zones": ["energy_core"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP - NMS Infrastructure Monitoring (30s)
            # NMS polls the energy-core switches + ESCO remote gateway
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["nms"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["energy_core"], "target_zones": ["energy_core"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # EWON batch export poll of the JACE head-end (5 min)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 300000,
             "source_types": ["remote_gateway"], "target_types": ["bms_controller"],
             "source_zones": ["energy_core"], "target_zones": ["energy_core"],
             "jitter_ms": 15000, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "energy_core", "name": "Energy Core Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "riser_a", "name": "Tenant Riser A Network", "level": 1,
             "subnet_offset": 1, "vlan": 121, "security_level": "high"},
            {"id": "riser_b", "name": "Tenant Riser B Network", "level": 1,
             "subnet_offset": 2, "vlan": 122, "security_level": "high"},
            {"id": "riser_c", "name": "Tenant Riser C Network", "level": 1,
             "subnet_offset": 3, "vlan": 123, "security_level": "high"},
            {"id": "riser_d", "name": "Tenant Riser D Network", "level": 1,
             "subnet_offset": 4, "vlan": 124, "security_level": "high"},
            {"id": "riser_e", "name": "Tenant Riser E Network", "level": 1,
             "subnet_offset": 5, "vlan": 125, "security_level": "high"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap"],
            "protocol": ["modbus_exception", "bacnet_reject"],
            "sequence": ["out_of_order", "duplicate_invoke_id"],
            "payload": ["value_spike", "setpoint_change"],
            "network": ["broadcast_storm"],
            "security": ["unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "custom",
            "cloud_ips": ["203.0.113.40", "203.0.113.41"],  # ESCO billing platform
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "enable_recon": True,
        },
        "conduits": [
            # L3 (energy_core) <-> L1 (riser_a..e): JACE/EWON polling each
            # tenant riser concentrator. Deliberately no riser-to-riser
            # conduit — tenant billing data must stay isolated per riser.
            {"id": "energy_core_to_riser_a", "name": "Energy Core ↔ Tenant Riser A",
             "source_zone": "energy_core", "target_zone": "riser_a",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "JACE energy manager polling the Riser A sub-metering concentrator"},
            {"id": "energy_core_to_riser_b", "name": "Energy Core ↔ Tenant Riser B",
             "source_zone": "energy_core", "target_zone": "riser_b",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "JACE energy manager polling the Riser B sub-metering concentrator"},
            {"id": "energy_core_to_riser_c", "name": "Energy Core ↔ Tenant Riser C",
             "source_zone": "energy_core", "target_zone": "riser_c",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "JACE energy manager polling the Riser C sub-metering concentrator"},
            {"id": "energy_core_to_riser_d", "name": "Energy Core ↔ Tenant Riser D",
             "source_zone": "energy_core", "target_zone": "riser_d",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "JACE energy manager polling the Riser D sub-metering concentrator"},
            {"id": "energy_core_to_riser_e", "name": "Energy Core ↔ Tenant Riser E",
             "source_zone": "energy_core", "target_zone": "riser_e",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "JACE energy manager polling the Riser E sub-metering concentrator"},
            # L3 (energy_core) <-> L4 (external): ESCO billing cloud connectivity
            {"id": "energy_core_to_external", "name": "Energy Core ↔ External",
             "source_zone": "energy_core", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https"],
             "security_level": "critical",
             "description": "EWON remote access gateway cloud heartbeat to the ESCO tenant-billing platform"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 5: HEAT & HOT-WATER COST ALLOCATION RETROFIT (29 devices)
    # Multi-family/mixed-use residential building retrofitted with
    # remote-readable heat/water metering per EED recast (EU)
    # 2023/1791 Art. 29 (non-remotely-readable devices must be
    # replaced by 1 Jan 2027).
    # ============================================================
    "heat_metering_retrofit": {
        "name": "Heat & Hot-Water Cost Allocation Retrofit",
        "description": "Multi-family residential building retrofitted ahead of the "
                       "EU EED (2023/1791 Art. 29) 1 Jan 2027 deadline to replace "
                       "non-remotely-readable heat/water meters. A Niagara JACE 8000 "
                       "building energy-manager polls eight wing-level Elvaco CMe3100 "
                       "M-Bus metering gateways (aggregating each wing's heat-cost "
                       "allocators and water meters, which stay on M-Bus and are not "
                       "individually IP-addressable) over BACnet/IP, and eight wings' "
                       "worth of Danfoss ECL Comfort 310 district-heating substation "
                       "controllers over Modbus TCP. 29 devices across 10 zones.",
        "vertical": "building_automation",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "bas_compromise", "relevance": "high", "rationale": "BACnet Who-Is discovery and manipulation against the JACE building energy-manager and Elvaco metering gateways"},
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "The Elvaco CMe3100's unrestricted file upload flaw (CVE-2024-49398, RCE) makes a vendor-remote-access-exposed metering gateway a credible foothold for tampering with billed heat/water consumption"},
            {"playbook_id": "network_recon", "relevance": "medium", "rationale": "Modbus/BACnet service enumeration across energy-center wing subnets"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "devices": [
            # ============================================================
            # BMS CORE ZONE (Level 3) - 5 devices
            # Building energy-manager head-end, infrastructure, ESCO
            # remote-meter-reading gateway
            # ============================================================
            # Building Energy Manager Head-End - Honeywell/Tridium JACE 8000
            # Fingerprint has: modbus_identity, bacnet_identity, snmp_identity
            {"type": "bms_controller", "vendor": "honeywell", "count": 1, "zone": "bms_core",
             "name_pattern": "Building_Energy_Manager_{n:02d}", "protocols": ["modbus_tcp", "bacnet"],
             "fingerprint_model": "JACE 8000",
             "role": "Building Energy Manager Head-End"},

            # Industrial Switches with SNMP monitoring
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "bms_core",
             "name_pattern": "BMS_Core_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E", "firmware_version": "15.2(7)E6",
             "role": "BMS Network Switch"},

            # Network Management Station - Paessler PRTG (SNMP monitoring of
            # the BMS core switches and the ESCO remote-reading gateway)
            {"type": "nms", "vendor": "Paessler", "count": 1, "zone": "bms_core",
             "name": "Building_Energy_Network_Management_Station", "protocols": ["snmp"],
             "fingerprint_model": "PRTG Network Monitor 24",
             "architectural_role": "nms_server",
             "role": "Network Management Station"},

            # ESCO Remote Meter-Reading Gateway - EWON Flexy 205
            # Fingerprint has: modbus_identity, snmp_identity, external_communications
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "bms_core",
             "name_pattern": "ESCO_Remote_Reading_Gateway_{n:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "ESCO Remote Meter-Reading Gateway",
             "external_comms": True},

            # Engineering Workstation - Honeywell XL Web
            # Fingerprint has: bacnet_identity ONLY
            {"type": "engineering_station", "vendor": "honeywell", "count": 1, "zone": "bms_core",
             "name": "Heat_Engineering_Workstation_01", "protocols": ["bacnet"],
             "fingerprint_model": "XL Web", "firmware_version": "XLWebExe-2-01-00",
             "role": "Engineering Workstation"},

            # ============================================================
            # ENERGY-CENTER WING ZONES (Level 2) - 3 devices each,
            # 8 wings = 24 devices. Each wing has two Danfoss ECL Comfort
            # 310 substation controllers (space heating + domestic hot
            # water circuits) and one Elvaco CMe3100 metering gateway
            # (the wing's heat-cost-allocators and water meters live
            # behind it on M-Bus, not modeled as separate IP devices).
            # ============================================================
        ] + [
            device
            for wing in "ABCDEFGH"
            for device in [
                {"type": "heat_substation_controller", "vendor": "danfoss", "count": 1,
                 "zone": f"energy_center_wing_{wing.lower()}",
                 "name": f"Wing_{wing}_Heating_Substation_Controller_01", "protocols": ["modbus_tcp"],
                 "fingerprint_model": "ECL Comfort 310",
                 "role": "Space-Heating Substation Controller"},
                {"type": "heat_substation_controller", "vendor": "danfoss", "count": 1,
                 "zone": f"energy_center_wing_{wing.lower()}",
                 "name": f"Wing_{wing}_DHW_Substation_Controller_01", "protocols": ["modbus_tcp"],
                 "fingerprint_model": "ECL Comfort 310",
                 "role": "Domestic Hot Water Substation Controller"},
                {"type": "meter_data_concentrator", "vendor": "elvaco", "count": 1,
                 "zone": f"energy_center_wing_{wing.lower()}",
                 "name": f"Wing_{wing}_Heat_Water_Meter_Gateway_01", "protocols": ["modbus_tcp", "bacnet"],
                 "fingerprint_model": "CMe3100",
                 "role": "Heat & Water Meter Data Concentrator"},
            ]
        ],
        "flows": [
            # ============================================================
            # BACnet - JACE to Elvaco Metering Gateways (60s billing cadence)
            # ============================================================
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["bms_controller"], "target_types": ["meter_data_concentrator"],
             "source_zones": ["bms_core"],
             "target_zones": ["energy_center_wing_a", "energy_center_wing_b", "energy_center_wing_c",
                               "energy_center_wing_d", "energy_center_wing_e", "energy_center_wing_f",
                               "energy_center_wing_g", "energy_center_wing_h"],
             "jitter_ms": 5000, "jitter_type": "gaussian"},

            # ============================================================
            # Modbus TCP - JACE to Danfoss ECL Substation Controllers (10s,
            # live weather-compensation control loop, faster than the
            # metering poll above)
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["bms_controller"], "target_types": ["heat_substation_controller"],
             "source_zones": ["bms_core"],
             "target_zones": ["energy_center_wing_a", "energy_center_wing_b", "energy_center_wing_c",
                               "energy_center_wing_d", "energy_center_wing_e", "energy_center_wing_f",
                               "energy_center_wing_g", "energy_center_wing_h"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # ============================================================
            # BACnet - Engineering Workstation Oversight Poll (5s)
            # ============================================================
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["engineering_station"], "target_types": ["bms_controller"],
             "source_zones": ["bms_core"], "target_zones": ["bms_core"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP - NMS Infrastructure Monitoring (30s)
            # NMS polls the BMS core switches + ESCO remote-reading gateway
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["nms"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["bms_core"], "target_zones": ["bms_core"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # EWON batch export poll of the JACE head-end (5 min)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 300000,
             "source_types": ["remote_gateway"], "target_types": ["bms_controller"],
             "source_zones": ["bms_core"], "target_zones": ["bms_core"],
             "jitter_ms": 15000, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "bms_core", "name": "BMS Core Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "energy_center_wing_a", "name": "Energy Center Wing A", "level": 2,
             "subnet_offset": 1, "vlan": 211, "security_level": "high"},
            {"id": "energy_center_wing_b", "name": "Energy Center Wing B", "level": 2,
             "subnet_offset": 2, "vlan": 212, "security_level": "high"},
            {"id": "energy_center_wing_c", "name": "Energy Center Wing C", "level": 2,
             "subnet_offset": 3, "vlan": 213, "security_level": "high"},
            {"id": "energy_center_wing_d", "name": "Energy Center Wing D", "level": 2,
             "subnet_offset": 4, "vlan": 214, "security_level": "high"},
            {"id": "energy_center_wing_e", "name": "Energy Center Wing E", "level": 2,
             "subnet_offset": 5, "vlan": 215, "security_level": "high"},
            {"id": "energy_center_wing_f", "name": "Energy Center Wing F", "level": 2,
             "subnet_offset": 6, "vlan": 216, "security_level": "high"},
            {"id": "energy_center_wing_g", "name": "Energy Center Wing G", "level": 2,
             "subnet_offset": 7, "vlan": 217, "security_level": "high"},
            {"id": "energy_center_wing_h", "name": "Energy Center Wing H", "level": 2,
             "subnet_offset": 8, "vlan": 218, "security_level": "high"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap"],
            "protocol": ["modbus_exception", "bacnet_reject"],
            "sequence": ["out_of_order", "duplicate_invoke_id"],
            "payload": ["value_spike", "setpoint_change"],
            "network": ["broadcast_storm"],
            "security": ["unauthorized_remote_access"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "custom",
            "cloud_ips": ["203.0.113.60", "203.0.113.61"],  # ESCO remote-meter-reading platform
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "enable_recon": True,
        },
        "conduits": [
            {"id": "bms_core_to_wing_a", "name": "BMS Core ↔ Energy Center Wing A",
             "source_zone": "bms_core", "target_zone": "energy_center_wing_a",
             "direction": "bidirectional", "allowed_protocols": ["modbus_tcp", "bacnet"],
             "security_level": "high",
             "description": "JACE energy manager polling Wing A's Danfoss substation controllers and Elvaco metering gateway"},
            {"id": "bms_core_to_wing_b", "name": "BMS Core ↔ Energy Center Wing B",
             "source_zone": "bms_core", "target_zone": "energy_center_wing_b",
             "direction": "bidirectional", "allowed_protocols": ["modbus_tcp", "bacnet"],
             "security_level": "high",
             "description": "JACE energy manager polling Wing B's Danfoss substation controllers and Elvaco metering gateway"},
            {"id": "bms_core_to_wing_c", "name": "BMS Core ↔ Energy Center Wing C",
             "source_zone": "bms_core", "target_zone": "energy_center_wing_c",
             "direction": "bidirectional", "allowed_protocols": ["modbus_tcp", "bacnet"],
             "security_level": "high",
             "description": "JACE energy manager polling Wing C's Danfoss substation controllers and Elvaco metering gateway"},
            {"id": "bms_core_to_wing_d", "name": "BMS Core ↔ Energy Center Wing D",
             "source_zone": "bms_core", "target_zone": "energy_center_wing_d",
             "direction": "bidirectional", "allowed_protocols": ["modbus_tcp", "bacnet"],
             "security_level": "high",
             "description": "JACE energy manager polling Wing D's Danfoss substation controllers and Elvaco metering gateway"},
            {"id": "bms_core_to_wing_e", "name": "BMS Core ↔ Energy Center Wing E",
             "source_zone": "bms_core", "target_zone": "energy_center_wing_e",
             "direction": "bidirectional", "allowed_protocols": ["modbus_tcp", "bacnet"],
             "security_level": "high",
             "description": "JACE energy manager polling Wing E's Danfoss substation controllers and Elvaco metering gateway"},
            {"id": "bms_core_to_wing_f", "name": "BMS Core ↔ Energy Center Wing F",
             "source_zone": "bms_core", "target_zone": "energy_center_wing_f",
             "direction": "bidirectional", "allowed_protocols": ["modbus_tcp", "bacnet"],
             "security_level": "high",
             "description": "JACE energy manager polling Wing F's Danfoss substation controllers and Elvaco metering gateway"},
            {"id": "bms_core_to_wing_g", "name": "BMS Core ↔ Energy Center Wing G",
             "source_zone": "bms_core", "target_zone": "energy_center_wing_g",
             "direction": "bidirectional", "allowed_protocols": ["modbus_tcp", "bacnet"],
             "security_level": "high",
             "description": "JACE energy manager polling Wing G's Danfoss substation controllers and Elvaco metering gateway"},
            {"id": "bms_core_to_wing_h", "name": "BMS Core ↔ Energy Center Wing H",
             "source_zone": "bms_core", "target_zone": "energy_center_wing_h",
             "direction": "bidirectional", "allowed_protocols": ["modbus_tcp", "bacnet"],
             "security_level": "high",
             "description": "JACE energy manager polling Wing H's Danfoss substation controllers and Elvaco metering gateway"},
            # L3 (bms_core) <-> L4 (external): ESCO remote-meter-reading cloud connectivity
            {"id": "bms_core_to_external", "name": "BMS Core ↔ External",
             "source_zone": "bms_core", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https"],
             "security_level": "critical",
             "description": "EWON remote access gateway cloud heartbeat to the ESCO remote-meter-reading platform"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },
}
