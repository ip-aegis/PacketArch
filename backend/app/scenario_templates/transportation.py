"""Transportation and ITS (Intelligent Transportation Systems) industry scenario templates.

Primary Vendors: Siemens ITS, Econolite, McCain, Wavetronix, FLIR, Daktronics, Kapsch
Protocol Focus: SNMP/NTCIP (primary), Modbus TCP (legacy), BACnet (tunnels), HTTPS (external)

Enhanced templates with:
- 30-45+ devices per template
- Realistic traffic flows based on NTCIP polling patterns
- Proper fingerprinting with protocol identities
- Multi-vendor architectures typical of real ITS deployments
- Support for highway corridors, urban intersections, tunnels, and toll plazas
"""

from typing import Any


TRANSPORTATION_TEMPLATES: dict[str, dict[str, Any]] = {
    # ============================================================
    # TEMPLATE 1: HIGHWAY CORRIDOR ITS (40 devices)
    # Multi-segment highway with DMS, detection, weather, and CCTV
    # ============================================================
    "highway_corridor_its": {
        "name": "Highway Corridor ITS",
        "description": "Multi-segment highway corridor with dynamic message signs, radar detection, "
                       "weather monitoring, and CCTV surveillance. Features Siemens central TMC "
                       "with distributed field equipment from multiple ITS vendors including "
                       "Daktronics DMS, Wavetronix radar, FLIR thermal, Vaisala weather stations, "
                       "and Axis/Pelco cameras. 40 devices across TMC core, DMS corridor, "
                       "detection zone, weather zone, and camera networks.",
        "vertical": "transportation",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "SNMP-based ITS infrastructure is vulnerable to network scanning"},
            {"playbook_id": "insider_threat", "relevance": "medium", "rationale": "TMC operator with DMS control access"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "transportation",
            "description": "Intersection signal control with vehicle counts, queue lengths, average speed, detector occupancy",
            "key_variables": ["vehicle_count", "queue_length", "average_speed", "detector_occupancy", "ped_demand"],
            "available_faults": ["detector_failure", "signal_stuck_red", "coordination_loss"],
        },
        "devices": [
            # ============================================================
            # TMC CORE ZONE (Level 3) - 4 devices
            # Traffic Management Center servers, switches
            # ============================================================
            # Master Station - Siemens CP-8000
            {"type": "master_station", "vendor": "siemens_its", "count": 2, "zone": "tmc_core",
             "name_pattern": "TMC_Master_Station_{n}", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "CP-8000",
             "role": "Traffic Management Center Master Station"},

            # Core Switches - Siemens SCALANCE XM-400
            {"type": "switch", "vendor": "siemens", "count": 2, "zone": "tmc_core",
             "name_pattern": "TMC_Core_Network_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "SCALANCE XM-400",
             "role": "TMC Core Network Switch"},

            # ============================================================
            # DMS CORRIDOR ZONE (Level 2) - 8 devices
            # Dynamic Message Signs for traffic information
            # ============================================================
            # Large DMS - Daktronics Venus 7000
            {"type": "dms_sign", "vendor": "daktronics", "count": 4, "zone": "dms_corridor",
             "name_pattern": "Highway_Full_Matrix_DMS_{n}", "protocols": ["snmp"],
             "fingerprint_model": "Venus 7000",
             "role": "Dynamic Message Sign (Full Matrix)"},

            # Smaller DMS - Daktronics Venus 1500
            {"type": "dms_sign", "vendor": "daktronics", "count": 4, "zone": "dms_corridor",
             "name_pattern": "Highway_Compact_DMS_{n}", "protocols": ["snmp"],
             "fingerprint_model": "Venus 1500",
             "role": "Dynamic Message Sign (Compact)"},

            # ============================================================
            # DETECTION ZONE (Level 2) - 12 devices
            # Radar and thermal sensors for vehicle detection
            # ============================================================
            # Radar Sensors - Wavetronix SmartSensor HD
            {"type": "radar_sensor", "vendor": "wavetronix", "count": 8, "zone": "detection_zone",
             "name_pattern": "Highway_Radar_Vehicle_Detector_{n}", "protocols": ["snmp"],
             "fingerprint_model": "SmartSensor HD",
             "role": "Radar Vehicle Detector (HD)"},

            # Thermal Sensors - FLIR TrafiOne
            {"type": "thermal_sensor", "vendor": "flir", "count": 4, "zone": "detection_zone",
             "name_pattern": "Highway_Thermal_Incident_Detector_{n}", "protocols": ["snmp"],
             "fingerprint_model": "TrafiOne",
             "role": "Thermal Incident Detector"},

            # ============================================================
            # WEATHER ZONE (Level 2) - 4 devices
            # Environmental Sensor Stations (ESS)
            # ============================================================
            # Weather Stations - Vaisala RWIS500
            {"type": "weather_station", "vendor": "vaisala", "count": 4, "zone": "weather_zone",
             "name_pattern": "Highway_Road_Weather_Station_{n}", "protocols": ["snmp"],
             "fingerprint_model": "RWIS500",
             "role": "Road Weather Information Station"},

            # ============================================================
            # CAMERA ZONE (Level 1) - 10 devices
            # CCTV for traffic monitoring
            # ============================================================
            # Fixed Cameras - Axis P1455-LE
            {"type": "camera_fixed", "vendor": "axis", "count": 6, "zone": "camera_zone",
             "name_pattern": "Highway_Fixed_CCTV_Camera_{n}", "protocols": ["snmp"],
             "fingerprint_model": "P1455-LE",
             "role": "Fixed ITS Camera"},

            # PTZ Cameras - Pelco Spectra Enhanced
            {"type": "camera_ptz", "vendor": "pelco", "count": 4, "zone": "camera_zone",
             "name_pattern": "Highway_PTZ_Surveillance_Camera_{n}", "protocols": ["snmp"],
             "fingerprint_model": "Spectra Enhanced",
             "role": "PTZ Surveillance Camera"},

            # ============================================================
            # EXTERNAL ZONE (Level 4) - 2 devices
            # Remote access and connectivity
            # ============================================================
            # Remote Access Gateway - HMS EWON Flexy
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "external",
             "name": "Highway_Corridor_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # Roadside Unit - Q-Free RSU 5000
            {"type": "rsu", "vendor": "q_free", "count": 1, "zone": "external",
             "name": "Highway_V2X_Roadside_Unit", "protocols": ["snmp"],
             "fingerprint_model": "RSU 5000",
             "role": "V2X Roadside Unit"},
        ],
        "flows": [
            # ============================================================
            # SNMP Polling - TMC to DMS (5s interval)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["master_station"], "target_types": ["dms_sign"],
             "source_zones": ["tmc_core"], "target_zones": ["dms_corridor"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - TMC to Detection Sensors (2s interval)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["radar_sensor", "thermal_sensor"],
             "source_zones": ["tmc_core"], "target_zones": ["detection_zone"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - TMC to Weather Stations (30s interval)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["master_station"], "target_types": ["weather_station"],
             "source_zones": ["tmc_core"], "target_zones": ["weather_zone"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP Polling - TMC to Cameras (10s keepalive)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["master_station"], "target_types": ["camera_fixed", "camera_ptz"],
             "source_zones": ["tmc_core"], "target_zones": ["camera_zone"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Infrastructure Monitoring (30s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["master_station"], "target_types": ["switch", "remote_gateway", "rsu"],
             "source_zones": ["tmc_core"], "target_zones": ["tmc_core", "external"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # EWON Remote Access - Talk2M Cloud (60s heartbeat)
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 60000,
             "source_types": ["remote_gateway"], "target_types": ["cloud"],
             "source_zones": ["external"], "target_zones": ["external"],
             "external_ip": "13.56.142.1",
             "external_port": 443,
             "jitter_ms": 5000, "jitter_type": "uniform"},
        ],
        "zones": [
            {"id": "tmc_core", "name": "TMC Core Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "dms_corridor", "name": "DMS Corridor Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "detection_zone", "name": "Detection Sensor Network", "level": 2,
             "subnet_offset": 2, "vlan": 120, "security_level": "high"},
            {"id": "weather_zone", "name": "Weather Station Network", "level": 2,
             "subnet_offset": 3, "vlan": 130, "security_level": "standard"},
            {"id": "camera_zone", "name": "CCTV Network", "level": 1,
             "subnet_offset": 4, "vlan": 140, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap", "timeout"],
            "protocol": ["snmp_timeout", "snmp_error"],
            "sequence": ["out_of_order", "duplicate"],
            "payload": ["dms_message_change", "weather_alert", "speed_spike"],
            "network": ["broadcast_storm"],
            "security": ["unauthorized_remote_access", "snmp_community_scan"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "enable_recon": True,
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 2: URBAN INTERSECTION NETWORK (35 devices)
    # Multi-intersection urban traffic control with coordinated signals
    # ============================================================
    "urban_intersection_network": {
        "name": "Urban Intersection Network",
        "description": "Multi-intersection urban traffic control network with coordinated signal "
                       "timing. Features Econolite and McCain controllers with Siemens coordination "
                       "master, plus Wavetronix detection and Hikvision ANPR cameras. Multi-vendor "
                       "architecture typical of modern urban ATMS deployments. 35 devices across "
                       "ATMS core, main intersections, minor intersections, detection, and camera zones.",
        "vertical": "transportation",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "Urban signal controller enumeration via SNMP"},
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "Traffic signal phase manipulation risk"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "transportation",
            "description": "Intersection signal control with vehicle counts, queue lengths, average speed, detector occupancy",
            "key_variables": ["vehicle_count", "queue_length", "average_speed", "detector_occupancy", "ped_demand"],
            "available_faults": ["detector_failure", "signal_stuck_red", "coordination_loss"],
        },
        "devices": [
            # ============================================================
            # ATMS CORE ZONE (Level 3) - 4 devices
            # Advanced Traffic Management System core
            # ============================================================
            # Coordination Master - Siemens CP-8000
            {"type": "master_station", "vendor": "siemens_its", "count": 1, "zone": "atms_core",
             "name": "ATMS_Coordination_Master_Station", "protocols": ["snmp"],
             "fingerprint_model": "CP-8000",
             "role": "ATMS Coordination Master"},

            # Distribution Switches - Siemens SCALANCE X-200
            {"type": "switch", "vendor": "siemens", "count": 2, "zone": "atms_core",
             "name_pattern": "ATMS_Distribution_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "SCALANCE X-200",
             "role": "ATMS Distribution Switch"},

            # Remote Access Gateway - HMS EWON Flexy
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "atms_core",
             "name": "ATMS_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # MAIN INTERSECTION ZONE (Level 2) - 12 devices
            # Primary arterial traffic controllers
            # ============================================================
            # Econolite Cobalt ATC Controllers
            {"type": "traffic_controller", "vendor": "econolite", "count": 6, "zone": "intersection_main",
             "name_pattern": "Main_Arterial_Signal_Controller_Econolite_{n}", "protocols": ["snmp"],
             "fingerprint_model": "Cobalt ATC",
             "role": "Traffic Signal Controller (Main)"},

            # McCain 2070 ATC Controllers
            {"type": "traffic_controller", "vendor": "mccain", "count": 3, "zone": "intersection_main",
             "name_pattern": "Main_Arterial_Signal_Controller_McCain_{n}", "protocols": ["snmp"],
             "fingerprint_model": "2070 ATC",
             "role": "Traffic Signal Controller (Main)"},

            # Siemens M60 Controllers
            {"type": "traffic_controller", "vendor": "siemens_its", "count": 3, "zone": "intersection_main",
             "name_pattern": "Main_Arterial_Signal_Controller_Siemens_{n}", "protocols": ["snmp"],
             "fingerprint_model": "M60",
             "role": "Traffic Signal Controller (Main)"},

            # ============================================================
            # MINOR INTERSECTION ZONE (Level 2) - 8 devices
            # Secondary/local street controllers
            # ============================================================
            # McCain 170E Controllers
            {"type": "traffic_controller", "vendor": "mccain", "count": 8, "zone": "intersection_minor",
             "name_pattern": "Minor_Street_Signal_Controller_{n}", "protocols": ["snmp"],
             "fingerprint_model": "170E",
             "role": "Traffic Signal Controller (Minor)"},

            # ============================================================
            # DETECTION ZONE (Level 1) - 8 devices
            # Vehicle and pedestrian detection
            # ============================================================
            # Wavetronix SmartSensor Advance
            {"type": "radar_sensor", "vendor": "wavetronix", "count": 4, "zone": "detection_zone",
             "name_pattern": "Intersection_Radar_Vehicle_Detector_{n}", "protocols": ["snmp"],
             "fingerprint_model": "SmartSensor Advance",
             "role": "Radar Vehicle Detector"},

            # FLIR TrafiSense Thermal
            {"type": "thermal_sensor", "vendor": "flir", "count": 4, "zone": "detection_zone",
             "name_pattern": "Intersection_Thermal_Pedestrian_Detector_{n}", "protocols": ["snmp"],
             "fingerprint_model": "TrafiSense",
             "role": "Thermal Detection Sensor"},

            # ============================================================
            # CAMERA ZONE (Level 1) - 3 devices
            # ANPR and PTZ surveillance
            # ============================================================
            # Hikvision ANPR Cameras
            {"type": "camera_anpr", "vendor": "hikvision", "count": 2, "zone": "camera_zone",
             "name_pattern": "Intersection_ANPR_Enforcement_Camera_{n}", "protocols": ["snmp"],
             "fingerprint_model": "DS-2CD7A26G0/P",
             "role": "ANPR Camera"},

            # Bosch PTZ Camera
            {"type": "camera_ptz", "vendor": "bosch", "count": 1, "zone": "camera_zone",
             "name": "Urban_Corridor_PTZ_Surveillance_Camera", "protocols": ["snmp"],
             "fingerprint_model": "MIC IP 7100i",
             "role": "PTZ Surveillance Camera"},
        ],
        "flows": [
            # ============================================================
            # SNMP Polling - ATMS to Main Controllers (1s interval)
            # High-frequency coordination polling
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["master_station"], "target_types": ["traffic_controller"],
             "source_zones": ["atms_core"], "target_zones": ["intersection_main"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - ATMS to Minor Controllers (2s interval)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["traffic_controller"],
             "source_zones": ["atms_core"], "target_zones": ["intersection_minor"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - Controllers to Detectors (500ms interval)
            # Fast detection polling for signal actuation
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["traffic_controller"], "target_types": ["radar_sensor", "thermal_sensor"],
             "source_zones": ["intersection_main", "intersection_minor"], "target_zones": ["detection_zone"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - ATMS to Cameras (5s interval)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["master_station"], "target_types": ["camera_anpr", "camera_ptz"],
             "source_zones": ["atms_core"], "target_zones": ["camera_zone"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Infrastructure Monitoring (30s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["master_station"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["atms_core"], "target_zones": ["atms_core"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # EWON Remote Access - Talk2M Cloud (30s heartbeat)
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source_types": ["remote_gateway"], "target_types": ["cloud"],
             "source_zones": ["atms_core"], "target_zones": ["external"],
             "external_ip": "54.95.198.117",
             "external_port": 443,
             "jitter_ms": 5000, "jitter_type": "uniform"},
        ],
        "zones": [
            {"id": "atms_core", "name": "ATMS Core Network", "level": 3,
             "subnet_offset": 0, "vlan": 200, "security_level": "critical"},
            {"id": "intersection_main", "name": "Main Intersection Network", "level": 2,
             "subnet_offset": 1, "vlan": 210, "security_level": "high"},
            {"id": "intersection_minor", "name": "Minor Intersection Network", "level": 2,
             "subnet_offset": 2, "vlan": 220, "security_level": "standard"},
            {"id": "detection_zone", "name": "Detection Sensor Network", "level": 1,
             "subnet_offset": 3, "vlan": 230, "security_level": "standard"},
            {"id": "camera_zone", "name": "Camera Network", "level": 1,
             "subnet_offset": 4, "vlan": 240, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap", "coordination_drift"],
            "protocol": ["snmp_timeout", "snmp_error", "ntcip_reject"],
            "sequence": ["phase_conflict", "detector_stuck"],
            "payload": ["phase_timing_change", "detector_malfunction"],
            "network": ["broadcast_storm", "controller_offline"],
            "security": ["unauthorized_remote_access", "phase_manipulation"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["54.95.198.117", "51.38.74.240"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "enable_recon": True,
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 3: TUNNEL CONTROL SYSTEM (45 devices)
    # Highway tunnel with ventilation, lighting, detection, safety
    # ============================================================
    "tunnel_control_system": {
        "name": "Tunnel Control System",
        "description": "Highway tunnel with integrated ventilation, lighting, incident detection, "
                       "and emergency systems. Features Siemens tunnel control system with "
                       "TCS-VENT ventilation controllers, Climatix C600 lighting controllers, "
                       "and distributed Schneider SCADAPack RTUs. Includes fire detection, "
                       "evacuation systems, and portal DMS/barriers. 45 devices across tunnel "
                       "master, ventilation, lighting, detection, safety, and portal zones.",
        "vertical": "transportation",
        "phase_preset": "full_lifecycle",
        "recommended_attack_playbooks": [
            {"playbook_id": "insider_threat", "relevance": "high", "rationale": "Tunnel ventilation and safety systems are life-safety critical"},
            {"playbook_id": "network_recon", "relevance": "medium", "rationale": "Tunnel SCADA network mapping"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "transportation",
            "description": "Intersection signal control with vehicle counts, queue lengths, average speed, detector occupancy",
            "key_variables": ["vehicle_count", "queue_length", "average_speed", "detector_occupancy", "ped_demand"],
            "available_faults": ["detector_failure", "signal_stuck_red", "coordination_loss"],
        },
        "devices": [
            # ============================================================
            # TUNNEL MASTER ZONE (Level 3) - 5 devices
            # Central control room and master station
            # ============================================================
            # Master Station - Siemens CP-8000
            {"type": "master_station", "vendor": "siemens_its", "count": 1, "zone": "tunnel_master",
             "name": "Tunnel_Master_Control_Station", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "CP-8000",
             "role": "Tunnel Master Control Station"},

            # Core Switches - Siemens SCALANCE XM-400
            {"type": "switch", "vendor": "siemens", "count": 2, "zone": "tunnel_master",
             "name_pattern": "Tunnel_Core_Network_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "SCALANCE XM-400",
             "role": "Tunnel Core Switch"},

            # Distribution Switches - Siemens SCALANCE X-200
            {"type": "switch", "vendor": "siemens", "count": 2, "zone": "tunnel_master",
             "name_pattern": "Tunnel_Distribution_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "SCALANCE X-200",
             "role": "Tunnel Distribution Switch"},

            # ============================================================
            # VENTILATION ZONE (Level 2) - 8 devices
            # Jet fans and air quality monitoring
            # ============================================================
            # Ventilation Controllers - Siemens TCS-VENT
            {"type": "ventilation_controller", "vendor": "siemens_its", "count": 4, "zone": "ventilation_zone",
             "name_pattern": "Tunnel_Jet_Fan_Ventilation_Controller_{n}", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "TCS-VENT",
             "role": "Tunnel Ventilation Controller"},

            # Ventilation RTUs - Schneider SCADAPack 350
            {"type": "rtu", "vendor": "schneider", "count": 4, "zone": "ventilation_zone",
             "name_pattern": "Tunnel_Ventilation_Field_RTU_{n}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SCADAPack 350",
             "role": "Ventilation Field RTU"},

            # ============================================================
            # LIGHTING ZONE (Level 2) - 6 devices
            # Adaptive tunnel lighting
            # ============================================================
            # Lighting Controllers - Siemens Climatix C600
            {"type": "lighting_controller", "vendor": "siemens", "count": 6, "zone": "lighting_zone",
             "name_pattern": "Tunnel_Adaptive_Lighting_Controller_{n}", "protocols": ["snmp"],
             "fingerprint_model": "C600",
             "role": "Tunnel Lighting Controller"},

            # ============================================================
            # DETECTION ZONE (Level 2) - 10 devices
            # Incident and vehicle detection
            # ============================================================
            # Radar Sensors - Wavetronix SmartSensor HD
            {"type": "radar_sensor", "vendor": "wavetronix", "count": 4, "zone": "detection_zone",
             "name_pattern": "Tunnel_Radar_Vehicle_Detector_{n}", "protocols": ["snmp"],
             "fingerprint_model": "SmartSensor HD",
             "role": "Radar Vehicle Detector"},

            # Thermal Sensors - FLIR TrafiOne
            {"type": "thermal_sensor", "vendor": "flir", "count": 4, "zone": "detection_zone",
             "name_pattern": "Tunnel_Thermal_Incident_Detector_{n}", "protocols": ["snmp"],
             "fingerprint_model": "TrafiOne",
             "role": "Thermal Incident Detector"},

            # Loop Detector RTUs - Schneider SCADAPack 350
            {"type": "rtu", "vendor": "schneider", "count": 2, "zone": "detection_zone",
             "name_pattern": "Tunnel_Loop_Detector_RTU_{n}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SCADAPack 350",
             "role": "Loop Detector RTU"},

            # ============================================================
            # SAFETY ZONE (Level 2) - 8 devices
            # Fire detection and evacuation
            # ============================================================
            # Fire Detection RTUs - Schneider SCADAPack 350
            {"type": "rtu", "vendor": "schneider", "count": 4, "zone": "safety_zone",
             "name_pattern": "Tunnel_Fire_Detection_RTU_{n}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SCADAPack 350",
             "role": "Fire Detection RTU"},

            # Evacuation Controllers - McCain 170E
            {"type": "traffic_controller", "vendor": "mccain", "count": 4, "zone": "safety_zone",
             "name_pattern": "Tunnel_Evacuation_Signal_Controller_{n}", "protocols": ["snmp"],
             "fingerprint_model": "170E",
             "role": "Evacuation Signal Controller"},

            # ============================================================
            # PORTAL ZONE (Level 1) - 6 devices
            # Entry/exit DMS and barriers
            # ============================================================
            # Portal DMS - Daktronics Venus 1500
            {"type": "dms_sign", "vendor": "daktronics", "count": 4, "zone": "portal_zone",
             "name_pattern": "Tunnel_Portal_Message_Sign_{n}", "protocols": ["snmp"],
             "fingerprint_model": "Venus 1500",
             "role": "Portal Message Sign"},

            # Portal Controllers - McCain 170E
            {"type": "traffic_controller", "vendor": "mccain", "count": 2, "zone": "portal_zone",
             "name_pattern": "Tunnel_Portal_Barrier_Controller_{n}", "protocols": ["snmp"],
             "fingerprint_model": "170E",
             "role": "Portal Barrier Controller"},

            # ============================================================
            # EXTERNAL ZONE (Level 4) - 2 devices
            # Remote monitoring
            # ============================================================
            # Remote Access Gateway - HMS EWON Cosy
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "external",
             "name": "Tunnel_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Cosy 131",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # Roadside Unit - Q-Free RSU 5000
            {"type": "rsu", "vendor": "q_free", "count": 1, "zone": "external",
             "name": "Tunnel_Entry_V2X_Roadside_Unit", "protocols": ["snmp"],
             "fingerprint_model": "RSU 5000",
             "role": "Tunnel Entry RSU"},
        ],
        "flows": [
            # ============================================================
            # SNMP Polling - Master to Ventilation (500ms - critical)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["master_station"], "target_types": ["ventilation_controller"],
             "source_zones": ["tunnel_master"], "target_zones": ["ventilation_zone"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # ============================================================
            # Modbus Polling - Ventilation Controllers to RTUs (1s)
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["ventilation_controller"], "target_types": ["rtu"],
             "source_zones": ["ventilation_zone"], "target_zones": ["ventilation_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # BACnet Polling - Master to Lighting (1s)
            # ============================================================
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["master_station"], "target_types": ["lighting_controller"],
             "source_zones": ["tunnel_master"], "target_zones": ["lighting_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - Master to Detection (2s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["radar_sensor", "thermal_sensor"],
             "source_zones": ["tunnel_master"], "target_zones": ["detection_zone"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # ============================================================
            # Modbus Polling - Master to Safety RTUs (1s - critical)
            # ============================================================
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["master_station"], "target_types": ["rtu"],
             "source_zones": ["tunnel_master"], "target_zones": ["safety_zone", "detection_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - Master to Safety Controllers (2s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["traffic_controller"],
             "source_zones": ["tunnel_master"], "target_zones": ["safety_zone"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - Master to Portal (5s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["master_station"], "target_types": ["dms_sign", "traffic_controller"],
             "source_zones": ["tunnel_master"], "target_zones": ["portal_zone"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Infrastructure Monitoring (30s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["master_station"], "target_types": ["switch", "remote_gateway", "rsu"],
             "source_zones": ["tunnel_master"], "target_zones": ["tunnel_master", "external"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # EWON Remote Access - Talk2M Cloud (30s heartbeat)
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source_types": ["remote_gateway"], "target_types": ["cloud"],
             "source_zones": ["external"], "target_zones": ["external"],
             "external_ip": "51.38.74.240",
             "external_port": 443,
             "jitter_ms": 5000, "jitter_type": "uniform"},
        ],
        "zones": [
            {"id": "tunnel_master", "name": "Tunnel Master Control", "level": 3,
             "subnet_offset": 0, "vlan": 300, "security_level": "critical"},
            {"id": "ventilation_zone", "name": "Ventilation Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 310, "security_level": "critical"},
            {"id": "lighting_zone", "name": "Lighting Control Network", "level": 2,
             "subnet_offset": 2, "vlan": 320, "security_level": "high"},
            {"id": "detection_zone", "name": "Detection Sensor Network", "level": 2,
             "subnet_offset": 3, "vlan": 330, "security_level": "high"},
            {"id": "safety_zone", "name": "Safety Systems Network", "level": 2,
             "subnet_offset": 4, "vlan": 340, "security_level": "critical"},
            {"id": "portal_zone", "name": "Portal Control Network", "level": 1,
             "subnet_offset": 5, "vlan": 350, "security_level": "high"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap", "timeout"],
            "protocol": ["snmp_timeout", "modbus_exception", "bacnet_reject"],
            "sequence": ["ventilation_fault", "lighting_fault"],
            "payload": ["co_level_spike", "temperature_spike", "fire_alarm"],
            "network": ["controller_offline", "communication_loss"],
            "security": ["unauthorized_remote_access", "safety_system_bypass"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["51.38.74.240", "87.98.169.126"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "enable_recon": True,
        },
        "total_duration_ms": 600000,  # 10 minutes
    },

    # ============================================================
    # TEMPLATE 4: TOLL PLAZA OPERATIONS (30 devices)
    # Multi-lane toll collection with ETC, ANPR, and manual lanes
    # ============================================================
    "toll_plaza_operations": {
        "name": "Toll Plaza Operations",
        "description": "Multi-lane toll collection facility with electronic toll collection (ETC), "
                       "ANPR cameras, and manual/cash lanes. Features Kapsch toll systems with "
                       "Q-Free RSUs, Hikvision ANPR cameras, and Daktronics lane status displays. "
                       "Includes central toll processing, revenue audit, and barrier control. "
                       "30 devices across toll center, ETC lanes, manual lanes, ANPR, and signage zones.",
        "vertical": "transportation",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "Toll system financial data and lane controller discovery"},
            {"playbook_id": "insider_threat", "relevance": "medium", "rationale": "Toll revenue manipulation via controller access"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "transportation",
            "description": "Intersection signal control with vehicle counts, queue lengths, average speed, detector occupancy",
            "key_variables": ["vehicle_count", "queue_length", "average_speed", "detector_occupancy", "ped_demand"],
            "available_faults": ["detector_failure", "signal_stuck_red", "coordination_loss"],
        },
        "devices": [
            # ============================================================
            # TOLL CENTER ZONE (Level 3) - 4 devices
            # Central toll processing and audit
            # ============================================================
            # Toll Master Station - Siemens CP-8000
            {"type": "master_station", "vendor": "siemens_its", "count": 1, "zone": "toll_center",
             "name": "Toll_Plaza_Master_Station", "protocols": ["snmp"],
             "fingerprint_model": "CP-8000",
             "role": "Toll Plaza Master Station"},

            # Distribution Switches - Siemens SCALANCE X-200
            {"type": "switch", "vendor": "siemens", "count": 2, "zone": "toll_center",
             "name_pattern": "Toll_Center_Network_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "SCALANCE X-200",
             "role": "Toll Center Switch"},

            # Remote Access Gateway - HMS EWON Flexy
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "toll_center",
             "name": "Toll_Plaza_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # ETC LANES ZONE (Level 2) - 10 devices
            # Electronic Toll Collection lanes
            # ============================================================
            # Toll Controllers - Kapsch TCS 2000
            {"type": "toll_controller", "vendor": "kapsch", "count": 6, "zone": "etc_lanes",
             "name_pattern": "ETC_Lane_Toll_Controller_{n}", "protocols": ["snmp"],
             "fingerprint_model": "TCS 2000",
             "role": "ETC Lane Controller"},

            # Roadside Units - Q-Free RSU 5000
            {"type": "rsu", "vendor": "q_free", "count": 4, "zone": "etc_lanes",
             "name_pattern": "ETC_Lane_Roadside_Unit_{n}", "protocols": ["snmp"],
             "fingerprint_model": "RSU 5000",
             "role": "ETC Roadside Unit"},

            # ============================================================
            # MANUAL LANES ZONE (Level 2) - 6 devices
            # Staffed and cash payment lanes
            # ============================================================
            # Manual Lane Controllers - McCain 170E
            {"type": "traffic_controller", "vendor": "mccain", "count": 6, "zone": "manual_lanes",
             "name_pattern": "Manual_Cash_Lane_Controller_{n}", "protocols": ["snmp"],
             "fingerprint_model": "170E",
             "role": "Manual Lane Controller"},

            # ============================================================
            # ANPR ZONE (Level 1) - 6 devices
            # License plate recognition cameras
            # ============================================================
            # ANPR Cameras - Hikvision
            {"type": "camera_anpr", "vendor": "hikvision", "count": 6, "zone": "anpr_zone",
             "name_pattern": "Toll_Plaza_ANPR_Camera_{n}", "protocols": ["snmp"],
             "fingerprint_model": "DS-2CD7A26G0/P",
             "role": "ANPR Camera"},

            # ============================================================
            # SIGNAGE ZONE (Level 1) - 4 devices
            # Lane status and pricing displays
            # ============================================================
            # Lane Status Signs - Daktronics Venus 1500
            {"type": "dms_sign", "vendor": "daktronics", "count": 4, "zone": "signage_zone",
             "name_pattern": "Toll_Lane_Status_Display_{n}", "protocols": ["snmp"],
             "fingerprint_model": "Venus 1500",
             "role": "Lane Status Display"},
        ],
        "flows": [
            # ============================================================
            # SNMP Polling - Toll Center to ETC Controllers (1s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["master_station"], "target_types": ["toll_controller", "rsu"],
             "source_zones": ["toll_center"], "target_zones": ["etc_lanes"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - Toll Center to Manual Lanes (2s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["traffic_controller"],
             "source_zones": ["toll_center"], "target_zones": ["manual_lanes"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - Toll Center to ANPR (500ms - fast)
            # High-frequency for real-time plate capture
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["master_station"], "target_types": ["camera_anpr"],
             "source_zones": ["toll_center"], "target_zones": ["anpr_zone"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Polling - Toll Center to Signs (5s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["master_station"], "target_types": ["dms_sign"],
             "source_zones": ["toll_center"], "target_zones": ["signage_zone"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP Infrastructure Monitoring (30s)
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["master_station"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["toll_center"], "target_zones": ["toll_center"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # EWON Remote Access - Talk2M Cloud (30s - revenue sync)
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source_types": ["remote_gateway"], "target_types": ["cloud"],
             "source_zones": ["toll_center"], "target_zones": ["external"],
             "external_ip": "13.56.142.1",
             "external_port": 443,
             "jitter_ms": 5000, "jitter_type": "uniform"},
        ],
        "zones": [
            {"id": "toll_center", "name": "Toll Center Network", "level": 3,
             "subnet_offset": 0, "vlan": 400, "security_level": "critical"},
            {"id": "etc_lanes", "name": "ETC Lanes Network", "level": 2,
             "subnet_offset": 1, "vlan": 410, "security_level": "high"},
            {"id": "manual_lanes", "name": "Manual Lanes Network", "level": 2,
             "subnet_offset": 2, "vlan": 420, "security_level": "standard"},
            {"id": "anpr_zone", "name": "ANPR Camera Network", "level": 1,
             "subnet_offset": 3, "vlan": 430, "security_level": "high"},
            {"id": "signage_zone", "name": "Signage Network", "level": 1,
             "subnet_offset": 4, "vlan": 440, "security_level": "standard"},
            {"id": "external", "name": "External/Internet", "level": 4,
             "subnet_offset": 99, "vlan": 999, "security_level": "external",
             "is_external": True},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap", "transaction_timeout"],
            "protocol": ["snmp_timeout", "snmp_error"],
            "sequence": ["lane_fault", "barrier_stuck"],
            "payload": ["revenue_discrepancy", "plate_mismatch"],
            "network": ["controller_offline", "camera_offline"],
            "security": ["unauthorized_remote_access", "transaction_manipulation"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "enable_recon": True,
        },
        "total_duration_ms": 300000,  # 5 minutes
    },
}
