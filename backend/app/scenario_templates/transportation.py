# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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
        "description": "Highway corridor ATMS deployment with 10 roadside cabinets, each "
                       "carrying a McCain / Econolite traffic controller plus Axis CCTV, Pelco "
                       "PTZ, and Daktronics DMS sign. Reverse-proxy fronted public web for "
                       "traveler info; full IDMZ. 69 devices across 12 zones.",
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
             "fingerprint_model": "CP-8000", "firmware_version": "V11.0.0",
             "role": "Traffic Management Center Master Station"},

            # Core Switches - Cisco IE-9320-24T4X-E
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "tmc_core",
             "name_pattern": "TMC_Core_Network_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-9320-24T4X-E",
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
             "fingerprint_model": "P1455-LE", "firmware_version": "10.6.0",
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
        "conduits": [
            # L3 (tmc_core) <-> L2 (dms_corridor): TMC to DMS signs
            {"id": "tmc_to_dms", "name": "TMC Core \u2194 DMS Corridor",
             "source_zone": "tmc_core", "target_zone": "dms_corridor",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "high",
             "description": "TMC master stations SNMP polling dynamic message signs for status and message updates"},
            # L3 (tmc_core) <-> L2 (detection_zone): TMC to detection sensors
            {"id": "tmc_to_detection", "name": "TMC Core \u2194 Detection Zone",
             "source_zone": "tmc_core", "target_zone": "detection_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "high",
             "description": "TMC master stations polling radar and thermal detection sensors for vehicle data"},
            # L3 (tmc_core) <-> L2 (weather_zone): TMC to weather stations
            {"id": "tmc_to_weather", "name": "TMC Core \u2194 Weather Zone",
             "source_zone": "tmc_core", "target_zone": "weather_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "TMC master stations polling road weather information stations for ESS data"},
            # L3 (tmc_core) <-> L1 (camera_zone): TMC to CCTV cameras
            {"id": "tmc_to_cameras", "name": "TMC Core \u2194 Camera Zone",
             "source_zone": "tmc_core", "target_zone": "camera_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "TMC master stations polling fixed and PTZ CCTV cameras for status and control"},
            # L3 (tmc_core) <-> L4 (external): TMC to remote access and RSU
            {"id": "tmc_to_external", "name": "TMC Core \u2194 External",
             "source_zone": "tmc_core", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp", "https"],
             "security_level": "critical",
             "description": "SNMP monitoring of remote gateway and RSU; EWON Talk2M cloud heartbeat"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 2: URBAN INTERSECTION NETWORK (35 devices)
    # Multi-intersection urban traffic control with coordinated signals
    # ============================================================
    "urban_intersection_network": {
        "name": "Urban Intersection Network",
        "description": "Urban intersection ATMS with 10 signalized intersection cabinets "
                       "supervised by a Centracs-class master at the TMC. Each cabinet has "
                       "traffic controller + CCTV + PTZ + DMS + cabinet aux. NTCIP-over-SNMP "
                       "polling throughout. TMC core adds standby master + NMS. "
                       "37 devices across 6 zones.",
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
             "fingerprint_model": "CP-8000", "firmware_version": "V11.0.0",
             "role": "ATMS Coordination Master"},

            # Distribution Switches - Cisco IE-3500-8P3S-E
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "atms_core",
             "name_pattern": "ATMS_Distribution_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-3500-8P3S-E",
             "role": "ATMS Distribution Switch"},

            # Remote Access Gateway - HMS EWON Flexy
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "atms_core",
             "name": "ATMS_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "architectural_role": "remote_access_gateway",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # Standby Coordination Master - Siemens CP-8000 (hot standby;
            # scada_standby role, mirrors the primary and takes over on
            # failover). Catalog-known type distinct from the primary's
            # master_station so the primary->standby sync flow resolves
            # against it in the template builder (same-type same-zone pairs
            # are self-skipped by the zip-by-index flow expansion).
            {"type": "scada_server", "vendor": "siemens_its", "count": 1, "zone": "atms_core",
             "name": "ATMS_Standby_Coordination_Master", "protocols": ["snmp"],
             "fingerprint_model": "CP-8000", "firmware_version": "V11.0.0",
             "architectural_role": "scada_standby",
             "role": "ATMS Standby Coordination Master"},

            # Network Management Station - Paessler PRTG (SNMP monitoring of
            # switches and remote-access gateway; satisfies the infrastructure
            # role requirement)
            {"type": "server", "vendor": "Paessler", "count": 1, "zone": "atms_core",
             "name": "ATMS_Network_Management_Station", "protocols": ["snmp"],
             "fingerprint_model": "PRTG Network Monitor 24",
             "architectural_role": "nms_server",
             "role": "Network Management Station"},

            # ============================================================
            # MAIN INTERSECTION ZONE (Level 2) - 12 devices
            # Primary arterial traffic controllers
            # ============================================================
            # Econolite Cobalt ATC Controllers
            {"type": "traffic_controller", "vendor": "econolite", "count": 6, "zone": "intersection_main",
             "name_pattern": "Main_Arterial_Signal_Controller_Econolite_{n}", "protocols": ["snmp"],
             "fingerprint_model": "Cobalt ATC", "firmware_version": "V7.10",
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
             "fingerprint_model": "DS-2CD7A26G0/P", "firmware_version": "V5.5.0",
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
            # SNMP Infrastructure Monitoring (30s) - from the NMS, not the master
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["server"], "target_types": ["switch", "remote_gateway"],
             "source_zones": ["atms_core"], "target_zones": ["atms_core"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP Standby Sync - Coordination Master to Standby (2s)
            # Hot-standby state replication / health check
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["scada_server"],
             "source_zones": ["atms_core"], "target_zones": ["atms_core"],
             "jitter_ms": 200, "jitter_type": "gaussian", "auto_repair_skip": True},

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
        "conduits": [
            # L3 (atms_core) <-> L2 (intersection_main): ATMS to main signal controllers
            {"id": "atms_to_main", "name": "ATMS Core \u2194 Main Intersections",
             "source_zone": "atms_core", "target_zone": "intersection_main",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "high",
             "description": "ATMS coordination master high-frequency polling of main arterial signal controllers"},
            # L3 (atms_core) <-> L2 (intersection_minor): ATMS to minor controllers
            {"id": "atms_to_minor", "name": "ATMS Core \u2194 Minor Intersections",
             "source_zone": "atms_core", "target_zone": "intersection_minor",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "ATMS coordination master polling secondary street signal controllers"},
            # L2 (intersection_main) <-> L1 (detection_zone): Main controllers to detectors
            {"id": "main_to_detection", "name": "Main Intersections \u2194 Detection Zone",
             "source_zone": "intersection_main", "target_zone": "detection_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Main intersection controllers fast-polling radar and thermal sensors for signal actuation"},
            # L2 (intersection_minor) <-> L1 (detection_zone): Minor controllers to detectors
            {"id": "minor_to_detection", "name": "Minor Intersections \u2194 Detection Zone",
             "source_zone": "intersection_minor", "target_zone": "detection_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Minor street intersection controllers fast-polling radar and thermal sensors for signal actuation"},
            # L3 (atms_core) <-> L1 (camera_zone): ATMS to ANPR and PTZ cameras
            {"id": "atms_to_cameras", "name": "ATMS Core \u2194 Camera Zone",
             "source_zone": "atms_core", "target_zone": "camera_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "ATMS master polling ANPR enforcement and PTZ surveillance cameras"},
            # L3 (atms_core) <-> L4 (external): Remote access cloud connectivity
            {"id": "atms_to_external", "name": "ATMS Core \u2194 External",
             "source_zone": "atms_core", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https"],
             "security_level": "critical",
             "description": "EWON remote access gateway Talk2M cloud heartbeat for remote ATMS monitoring"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 3: TUNNEL CONTROL SYSTEM (45 devices)
    # Highway tunnel with ventilation, lighting, detection, safety
    # ============================================================
    "tunnel_control_system": {
        "name": "Tunnel Control System",
        "description": "Highway tunnel control system. Three tunnel sections each with "
                       "ventilation / lighting / fire-detection cabinets and fixed CCTV. Portal "
                       "zones host Daktronics DMS, Hikvision ANPR, Pelco PTZ surveillance, and "
                       "Vaisala RWIS road-weather stations. TMC has ATMS master + standby + "
                       "alarm server + historian + NMS. 43 devices across 8 zones.",
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
             "name": "Tunnel_Master_Control_Station", "protocols": ["snmp", "modbus_tcp", "bacnet"],
             "fingerprint_model": "CP-8000", "firmware_version": "V11.0.0",
             "role": "Tunnel Master Control Station"},

            # Core Switches - Cisco IE-9320-24T4X-E
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "tunnel_master",
             "name_pattern": "Tunnel_Core_Network_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-9320-24T4X-E",
             "role": "Tunnel Core Switch"},

            # Distribution Switches - Cisco IE-3500-8P3S-E
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "tunnel_master",
             "name_pattern": "Tunnel_Distribution_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-3500-8P3S-E",
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
             "name_pattern": "Tunnel_Adaptive_Lighting_Controller_{n}", "protocols": ["snmp", "bacnet"],
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
        "conduits": [
            # L3 (tunnel_master) <-> L2 (ventilation_zone): Master to ventilation
            {"id": "master_to_ventilation", "name": "Tunnel Master \u2194 Ventilation",
             "source_zone": "tunnel_master", "target_zone": "ventilation_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp", "modbus_tcp"],
             "security_level": "critical",
             "description": "Master station high-frequency polling of ventilation controllers and field RTUs for air quality"},
            # L3 (tunnel_master) <-> L2 (lighting_zone): Master to lighting
            {"id": "master_to_lighting", "name": "Tunnel Master \u2194 Lighting",
             "source_zone": "tunnel_master", "target_zone": "lighting_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["bacnet"],
             "security_level": "high",
             "description": "Master station BACnet polling of adaptive tunnel lighting controllers"},
            # L3 (tunnel_master) <-> L2 (detection_zone): Master to detection
            {"id": "master_to_detection", "name": "Tunnel Master \u2194 Detection",
             "source_zone": "tunnel_master", "target_zone": "detection_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp", "modbus_tcp"],
             "security_level": "high",
             "description": "Master station polling radar, thermal sensors, and loop detector RTUs for incident detection"},
            # L3 (tunnel_master) <-> L2 (safety_zone): Master to safety systems
            {"id": "master_to_safety", "name": "Tunnel Master \u2194 Safety Zone",
             "source_zone": "tunnel_master", "target_zone": "safety_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "Master station polling fire detection RTUs and evacuation signal controllers"},
            # L2 (safety_zone) <-> L1 (portal_zone): Safety to portal control
            {"id": "safety_to_portal", "name": "Safety Zone \u2194 Portal Zone",
             "source_zone": "safety_zone", "target_zone": "portal_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "high",
             "description": "Evacuation controllers coordinating with portal DMS and barrier controllers"},
            # L3 (tunnel_master) <-> L1 (portal_zone): Master to portal
            {"id": "master_to_portal", "name": "Tunnel Master \u2194 Portal Zone",
             "source_zone": "tunnel_master", "target_zone": "portal_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "high",
             "description": "Master station polling portal message signs and barrier controllers"},
            # L3 (tunnel_master) <-> L4 (external): Remote access
            {"id": "master_to_external", "name": "Tunnel Master \u2194 External",
             "source_zone": "tunnel_master", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp", "https"],
             "security_level": "critical",
             "description": "SNMP monitoring of remote gateway and RSU; EWON Talk2M cloud heartbeat"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
    },

    # ============================================================
    # TEMPLATE 4: TOLL PLAZA OPERATIONS (30 devices)
    # Multi-lane toll collection with ETC, ANPR, and manual lanes
    # ============================================================
    "toll_plaza_operations": {
        "name": "Toll Plaza Operations",
        "description": "Toll plaza with 4 lanes (2 ETC, 2 manual). Each lane carries a Kapsch "
                       "ETC controller, Q-Free DSRC RSU, and Hikvision ANPR enforcement camera. "
                       "Approach zone has Daktronics DMS signs and Pelco / Bosch surveillance "
                       "cameras. TMC at L3 with ATMS master + historian + NMS; full IDMZ for "
                       "back-office settlement. 32 devices across 7 zones.",
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
             "fingerprint_model": "CP-8000", "firmware_version": "V11.0.0",
             "role": "Toll Plaza Master Station"},

            # Distribution Switches - Cisco IE-3500-8P3S-E
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "toll_center",
             "name_pattern": "Toll_Center_Network_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-3500-8P3S-E",
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
             "fingerprint_model": "DS-2CD7A26G0/P", "firmware_version": "V5.5.0",
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
        "conduits": [
            # L3 (toll_center) <-> L2 (etc_lanes): Toll center to ETC lanes
            {"id": "toll_to_etc", "name": "Toll Center \u2194 ETC Lanes",
             "source_zone": "toll_center", "target_zone": "etc_lanes",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "high",
             "description": "Toll master station polling ETC lane controllers and roadside units for transaction processing"},
            # L3 (toll_center) <-> L2 (manual_lanes): Toll center to manual lanes
            {"id": "toll_to_manual", "name": "Toll Center \u2194 Manual Lanes",
             "source_zone": "toll_center", "target_zone": "manual_lanes",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Toll master station polling manual/cash lane controllers for status and revenue data"},
            # L3 (toll_center) <-> L1 (anpr_zone): Toll center to ANPR cameras
            {"id": "toll_to_anpr", "name": "Toll Center \u2194 ANPR Zone",
             "source_zone": "toll_center", "target_zone": "anpr_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "high",
             "description": "Toll master station high-frequency polling of ANPR cameras for real-time plate capture"},
            # L3 (toll_center) <-> L1 (signage_zone): Toll center to lane signs
            {"id": "toll_to_signage", "name": "Toll Center \u2194 Signage Zone",
             "source_zone": "toll_center", "target_zone": "signage_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["snmp"],
             "security_level": "standard",
             "description": "Toll master station polling lane status and pricing displays"},
            # L3 (toll_center) <-> L4 (external): Remote access cloud connectivity
            {"id": "toll_to_external", "name": "Toll Center \u2194 External",
             "source_zone": "toll_center", "target_zone": "external",
             "direction": "bidirectional",
             "allowed_protocols": ["https"],
             "security_level": "critical",
             "description": "EWON remote access gateway Talk2M cloud heartbeat for revenue sync and remote monitoring"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 5: PTC FREIGHT CORRIDOR (17 devices)
    # Positive Train Control: back office <-> wayside <-> locomotive
    # over EMP (the AAR Interoperable Train Control message envelope).
    # ============================================================
    "ptc_freight_corridor": {
        "name": "PTC Freight Corridor",
        "description": "Positive Train Control (I-ETMS) freight corridor: a back-office server "
                       "pair exchanging EMP messages with wayside interface units along the "
                       "subdivision and with locomotive train-management computers. Wayside units "
                       "report signal/switch status; the back office issues wayside device "
                       "controls. 17 devices across 4 zones.",
        "vertical": "transportation",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "network_recon", "relevance": "high",
             "rationale": "PTC back-office networks are reachable from railroad enterprise IT"},
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "devices": [
            # BACK OFFICE (Level 3)
            {"type": "back_office_server", "vendor": "wabtec", "count": 2, "zone": "back_office",
             "name_pattern": "PTC_Back_Office_Server_{n}", "protocols": ["emp", "snmp"],
             "fingerprint_model": "I-ETMS Back Office Server",
             "role": "I-ETMS Back Office Server"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "back_office",
             "name_pattern": "PTC_Back_Office_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-9320-24T4X-E",
             "role": "Back Office Network Switch"},

            # WAYSIDE CORRIDOR (Level 2)
            {"type": "wayside_interface_unit", "vendor": "wabtec", "count": 8, "zone": "wayside_corridor",
             "name_pattern": "Wayside_Interface_Unit_{n}", "protocols": ["emp"],
             "fingerprint_model": "I-ETMS Wayside Interface Unit",
             "role": "I-ETMS Wayside Interface Unit"},
            {"type": "wayside_interface_unit", "vendor": "ge transportation", "count": 2,
             "zone": "wayside_corridor",
             "name_pattern": "ITCS_Wayside_Controller_{n}", "protocols": ["emp"],
             "fingerprint_model": "ITCS Wayside Controller",
             "role": "ITCS Wayside Controller"},

            # LOCOMOTIVE FLEET (Level 2 - mobile assets)
            {"type": "locomotive_computer", "vendor": "wabtec", "count": 4, "zone": "locomotive_fleet",
             "name_pattern": "Locomotive_Train_Mgmt_Computer_{n}", "protocols": ["emp"],
             "fingerprint_model": "I-ETMS Train Management Computer",
             "role": "I-ETMS Locomotive Train Management Computer"},
        ],
        "flows": [
            # Wayside status reporting to the back office (EMP)
            {"protocol": "emp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["wayside_interface_unit"], "target_types": ["back_office_server"],
             "source_zones": ["wayside_corridor"], "target_zones": ["back_office"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Locomotive onboard reporting to the back office (EMP, slower - radio backhaul)
            {"protocol": "emp", "pattern": "poll", "interval_ms": 15000,
             "source_types": ["locomotive_computer"], "target_types": ["back_office_server"],
             "source_zones": ["locomotive_fleet"], "target_zones": ["back_office"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # Back-office switch management
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["back_office_server"], "target_types": ["switch"],
             "source_zones": ["back_office"], "target_zones": ["back_office"],
             "jitter_ms": 2000, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "back_office", "name": "PTC Back Office", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "wayside_corridor", "name": "Wayside Corridor", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "locomotive_fleet", "name": "Locomotive Fleet", "level": 2,
             "subnet_offset": 2, "vlan": 120, "security_level": "high"},
        ],
        "conduits": [
            {"id": "wayside_to_back_office", "name": "Wayside Corridor ↔ Back Office",
             "source_zone": "wayside_corridor", "target_zone": "back_office",
             "direction": "bidirectional",
             "allowed_protocols": ["emp"],
             "security_level": "critical",
             "description": "Wayside interface units reporting signal/switch status to the back office and receiving wayside device controls over EMP"},
            {"id": "locomotive_to_back_office", "name": "Locomotive Fleet ↔ Back Office",
             "source_zone": "locomotive_fleet", "target_zone": "back_office",
             "direction": "bidirectional",
             "allowed_protocols": ["emp"],
             "security_level": "critical",
             "description": "Locomotive train-management computers exchanging EMP messages with the back office for movement authorities"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap", "timeout"],
            "sequence": ["out_of_order", "duplicate"],
            "network": ["broadcast_storm"],
            "security": ["unauthorized_remote_access"],
        },
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 6: ATCS SIGNALING TERRITORY (8 devices)
    # Legacy ATCS codeline, observed via the ATCS Monitor relay feed.
    # NOTE: wayside MCPs ride a 900 MHz radio codeline and are NOT IP
    # endpoints — they appear as ATCS addresses INSIDE the codeline
    # frames, not as devices on this network. Only the office/dispatch
    # systems and the base-station relays are IP-visible.
    # ============================================================
    "atcs_signaling_territory": {
        "name": "ATCS Signaling Territory",
        "description": "Legacy ATCS (AAR MSRP Section K-II) codeline territory observed over the "
                       "ATCS Monitor relay feed: dispatch/CTC office systems subscribe to base-station "
                       "relays, which stream decoded codeline frames (wayside indications and "
                       "office controls) as binary records over UDP. Wayside MCPs are radio-only and "
                       "appear as ATCS addresses within the frames, not as IP hosts. 8 devices "
                       "across 3 zones.",
        "vertical": "transportation",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "network_recon", "relevance": "medium",
             "rationale": "Codeline relay feeds are often carried on flat railroad WAN segments"},
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "devices": [
            # DISPATCH OFFICE (Level 3)
            {"type": "atcs_office", "vendor": "alstom", "count": 2, "zone": "dispatch_office",
             "name_pattern": "ATCS_Dispatch_Office_System_{n}", "protocols": ["atcs", "snmp"],
             "fingerprint_model": "ATCS Office Dispatch System",
             "role": "ATCS Office Dispatch System"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "dispatch_office",
             "name_pattern": "Dispatch_Office_Switch_{n}", "protocols": ["snmp"],
             "fingerprint_model": "IE-9320-24T4X-E",
             "role": "Dispatch Office Network Switch"},

            # CODELINE RELAY (Level 2)
            {"type": "atcs_base_station", "vendor": "siemens mobility", "count": 4,
             "zone": "codeline_relay",
             "name_pattern": "ATCS_Base_Comms_Package_{n}", "protocols": ["atcs"],
             "fingerprint_model": "ATCS Base Communications Package",
             "role": "ATCS Base Communications Package (codeline relay)"},

            # WAYSIDE SIGNALING (Level 2) - IP-managed signal controller
            {"type": "wayside_signal_controller", "vendor": "hitachi rail", "count": 1,
             "zone": "wayside_signaling",
             "name_pattern": "Wayside_Signal_Controller_{n}", "protocols": ["atcs"],
             "fingerprint_model": "Wayside Signal Controller",
             "role": "Wayside Signal Controller"},
        ],
        "flows": [
            # Office subscribes to the base-station codeline relay feed (ATCS)
            {"protocol": "atcs", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["atcs_office"], "target_types": ["atcs_base_station"],
             "source_zones": ["dispatch_office"], "target_zones": ["codeline_relay"],
             "jitter_ms": 250, "jitter_type": "gaussian"},

            # Office also pulls the codeline feed covering the wayside controller
            {"protocol": "atcs", "pattern": "poll", "interval_ms": 4000,
             "source_types": ["atcs_office"], "target_types": ["wayside_signal_controller"],
             "source_zones": ["dispatch_office"], "target_zones": ["wayside_signaling"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Dispatch switch management
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["atcs_office"], "target_types": ["switch"],
             "source_zones": ["dispatch_office"], "target_zones": ["dispatch_office"],
             "jitter_ms": 2000, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "dispatch_office", "name": "Dispatch / CTC Office", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "codeline_relay", "name": "Codeline Relay Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "wayside_signaling", "name": "Wayside Signaling", "level": 2,
             "subnet_offset": 2, "vlan": 120, "security_level": "high"},
        ],
        "conduits": [
            {"id": "office_to_relay", "name": "Dispatch Office ↔ Codeline Relay",
             "source_zone": "dispatch_office", "target_zone": "codeline_relay",
             "direction": "bidirectional",
             "allowed_protocols": ["atcs"],
             "security_level": "high",
             "description": "Dispatch office systems subscribing to base-station relays streaming decoded ATCS codeline frames"},
            {"id": "office_to_wayside", "name": "Dispatch Office ↔ Wayside Signaling",
             "source_zone": "dispatch_office", "target_zone": "wayside_signaling",
             "direction": "bidirectional",
             "allowed_protocols": ["atcs"],
             "security_level": "high",
             "description": "Dispatch office pulling the codeline feed covering wayside signal controllers"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "polling_gap", "timeout"],
            "sequence": ["out_of_order", "duplicate"],
            "network": ["broadcast_storm"],
        },
        "total_duration_ms": 300000,  # 5 minutes
    },
}
