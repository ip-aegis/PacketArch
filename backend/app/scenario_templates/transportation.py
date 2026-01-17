"""Transportation ITS scenario templates.

Primary Vendors: Econolite, Siemens ITS, McCain, Wavetronix, Daktronics, Hikvision
Protocol Focus: SNMP/NTCIP (all transportation devices)

Scenarios:
- Highway Corridor: Interstate management with DMS, ramp meters, weather stations
- Urban Intersection: Coordinated traffic signals with detectors
- Tunnel System: Tunnel management with lighting, ventilation, sensors
- Toll Plaza: Electronic toll collection with RSUs, ANPR cameras
- Network Infrastructure: ITS network backbone with switches, RTUs, NTCIP devices

CVE Vulnerability mapping:
- Traffic controllers: CVE-2020-16205 (Econolite), CVE-2023-28489 (Siemens CP-8000), CVE-2020-25230 (Siemens M60)
- DMS controllers: CVE-2018-18472 (Daktronics)
- Toll systems: CVE-2022-29885 (Kapsch), CVE-2022-30456 (Q-Free RSU)
- Sensors: CVE-2021-38294 (Wavetronix), CVE-2021-27656 (FLIR)
- Cameras: CVE-2021-31986 (Axis), CVE-2019-18230 (Pelco), CVE-2021-36260 (Hikvision ANPR)
- RTUs: CVE-2020-7480 (Schneider SCADAPack), CVE-2021-22778 (Schneider TBox)
- Network: CVE-2019-6569 (Siemens SCALANCE), CVE-2020-11896 (Treck Ripple20)
"""

from typing import Any


TRANSPORTATION_TEMPLATES: dict[str, dict[str, Any]] = {
    "highway_corridor": {
        "name": "Highway Corridor Management",
        "description": "Interstate highway management system with dynamic message signs, "
                       "ramp meters, traffic detection radars, weather stations, and a "
                       "central traffic management center. Uses NTCIP/SNMP protocol for "
                       "device communication.",
        "vertical": "transportation",
        "devices": [
            # Traffic Management Center
            {"type": "master_station", "vendor": "siemens", "count": 1, "zone": "tmc",
             "name_pattern": "TMC-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "CP-8000",
             "role": "Traffic Management Center",
             "cve_ids": ["CVE-2023-28489"]},

            # Dynamic Message Signs (Daktronics)
            {"type": "dms", "vendor": "daktronics", "count": 8, "zone": "corridor",
             "name_pattern": "DMS-MM{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "Venus 1500",
             "role": "Dynamic Message Sign",
             "cve_ids": ["CVE-2018-18472"]},

            # Ramp Meter Controllers (Econolite)
            {"type": "traffic_controller", "vendor": "econolite", "count": 6, "zone": "field",
             "name_pattern": "RM-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "Cobalt ATC",
             "role": "Ramp Meter Controller",
             "cve_ids": ["CVE-2020-16205"]},

            # Traffic Detection Radars (Wavetronix)
            {"type": "radar_sensor", "vendor": "wavetronix", "count": 12, "zone": "field",
             "name_pattern": "RADAR-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "SmartSensor HD",
             "role": "Vehicle Detection Radar",
             "cve_ids": ["CVE-2021-38294"]},

            # Road Weather Information Systems
            {"type": "weather_station", "vendor": "vaisala", "count": 4, "zone": "field",
             "name_pattern": "RWIS-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "RWIS500",
             "role": "Road Weather Station"},

            # CCTV Cameras (Axis)
            {"type": "camera", "vendor": "axis", "count": 10, "zone": "field",
             "name_pattern": "CAM-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "P1455-LE",
             "role": "Traffic Camera",
             "cve_ids": ["CVE-2021-31986"]},

            # RTU for Remote Sites
            {"type": "rtu", "vendor": "schneider", "count": 4, "zone": "field",
             "name_pattern": "RTU-{n:03d}", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "SCADAPack 350",
             "role": "Remote Terminal Unit",
             "cve_ids": ["CVE-2020-7480"]},
        ],
        "flows": [
            # TMC polling DMS (10s interval)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["master_station"], "target_types": ["dms"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # TMC polling ramp meters (5s interval)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["master_station"], "target_types": ["traffic_controller"],
             "jitter_ms": 250, "jitter_type": "uniform"},
            # TMC polling radars (2s interval for detection data)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["radar_sensor"],
             "jitter_ms": 100, "jitter_type": "uniform"},
            # TMC polling weather stations (60s interval)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["master_station"], "target_types": ["weather_station"],
             "jitter_ms": 2000, "jitter_type": "uniform"},
            # TMC polling cameras (30s interval)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["master_station"], "target_types": ["camera"],
             "jitter_ms": 1000, "jitter_type": "uniform"},
            # RTU local polling of radars (500ms)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["rtu"], "target_types": ["radar_sensor"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "tmc", "name": "Traffic Management Center", "level": 4,
             "subnet_offset": 0, "vlan": 10},
            {"id": "corridor", "name": "Highway Corridor", "level": 2,
             "subnet_offset": 1, "vlan": 20},
            {"id": "field", "name": "Field Devices", "level": 1,
             "subnet_offset": 2, "vlan": 30},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "timeout"],
            "protocol": ["snmp_error"],
            "sequence": [],
            "payload": ["value_spike"],
            "network": ["packet_loss"],
            "security": ["community_string_probe"],
        },
        "pcap_learning_hints": [
            {"protocol": "snmp", "flow_type": "ntcip_polling", "priority": "high",
             "description": "Learn NTCIP 1202/1203 OID polling patterns"},
            {"protocol": "snmp", "flow_type": "trap_notifications", "priority": "medium",
             "description": "Capture trap events from field devices"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    "urban_intersection": {
        "name": "Urban Traffic Signal System",
        "description": "Coordinated urban traffic signal system with 8 intersections, "
                       "actuated controllers, vehicle detection, pedestrian signals, "
                       "and central coordination for adaptive timing.",
        "vertical": "transportation",
        "devices": [
            # Central Master Controller
            {"type": "master_station", "vendor": "siemens", "count": 1, "zone": "tmc",
             "name_pattern": "MASTER-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "M60",
             "role": "Central Controller",
             "cve_ids": ["CVE-2020-25230"]},

            # Intersection Controllers (Econolite Cobalt ATC)
            {"type": "traffic_controller", "vendor": "econolite", "count": 8, "zone": "intersection",
             "name_pattern": "INT-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "Cobalt ATC",
             "role": "Actuated Signal Controller",
             "cve_ids": ["CVE-2020-16205"]},

            # Thermal Detection Sensors (FLIR)
            {"type": "thermal_sensor", "vendor": "flir", "count": 16, "zone": "intersection",
             "name_pattern": "THERMAL-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "TrafiOne",
             "role": "Thermal Detection",
             "cve_ids": ["CVE-2021-27656"]},

            # Video Detection Cameras
            {"type": "video_detector", "vendor": "axis", "count": 16, "zone": "intersection",
             "name_pattern": "VDET-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "P1448-LE",
             "role": "Video Detection",
             "cve_ids": ["CVE-2021-31986"]},

            # Loop Detector Cards (legacy - connects via controller)
            {"type": "detector_rack", "vendor": "mccain", "count": 8, "zone": "intersection",
             "name_pattern": "DET-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "170E",
             "role": "Detector Rack"},
        ],
        "flows": [
            # Master polling controllers for phase status (1s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["master_station"], "target_types": ["traffic_controller"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            # Master polling thermal sensors (500ms)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["master_station"], "target_types": ["thermal_sensor"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            # Controller polling local detectors (250ms)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["traffic_controller"], "target_types": ["thermal_sensor", "video_detector", "detector_rack"],
             "jitter_ms": 10, "jitter_type": "gaussian"},
            # Master polling video detectors (2s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["video_detector"],
             "jitter_ms": 100, "jitter_type": "uniform"},
            # Coordination messages between controllers (100ms cycle)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["traffic_controller"], "target_types": ["traffic_controller"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "tmc", "name": "Traffic Operations", "level": 3,
             "subnet_offset": 0, "vlan": 10},
            {"id": "intersection", "name": "Intersection Devices", "level": 1,
             "subnet_offset": 1, "vlan": 20},
        ],
        "suggested_anomalies": {
            "timing": ["cycle_slip", "coordination_loss", "detector_stuck"],
            "protocol": ["snmp_timeout"],
            "sequence": [],
            "payload": ["phase_conflict", "detector_failure"],
            "network": [],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "snmp", "flow_type": "phase_polling", "priority": "high",
             "description": "Learn NTCIP 1202 phase status polling patterns"},
            {"protocol": "snmp", "flow_type": "coordination", "priority": "high",
             "description": "Capture coordination sync timing between controllers"},
        ],
        "total_duration_ms": 300000,
    },

    "tunnel_system": {
        "name": "Tunnel Control System",
        "description": "Highway tunnel management system with lighting control, "
                       "ventilation fans, CO/NO2 sensors, fire detection, CCTV, "
                       "and emergency systems. Critical safety infrastructure.",
        "vertical": "transportation",
        "devices": [
            # Tunnel Control Center
            {"type": "master_station", "vendor": "siemens", "count": 1, "zone": "control_center",
             "name_pattern": "TCC-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "CP-8000",
             "role": "Tunnel Control Center",
             "cve_ids": ["CVE-2023-28489"]},

            # Lighting Controllers (Siemens Climatix for lighting zones)
            {"type": "lighting_controller", "vendor": "siemens", "count": 6, "zone": "tunnel",
             "name_pattern": "LIGHT-{n:03d}", "protocols": ["snmp", "bacnet"],
             "fingerprint_model": "C600",
             "role": "Lighting Zone Controller"},

            # Ventilation Controllers (jet fans - Siemens DXR2 for HVAC/ventilation)
            {"type": "ventilation_controller", "vendor": "siemens", "count": 4, "zone": "tunnel",
             "name_pattern": "VENT-{n:03d}", "protocols": ["snmp", "bacnet"],
             "fingerprint_model": "DXR2.E12",
             "cve_ids": ["CVE-2022-31465"],
             "role": "Ventilation Controller"},

            # Chemical Sensors (CO/NO2/Visibility)
            {"type": "chem_sensor", "vendor": "vaisala", "count": 12, "zone": "tunnel",
             "name_pattern": "CHEM-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "RWIS500",
             "role": "Air Quality Sensor"},

            # Fire Detection Panels (SCADAPack 350 with auth bypass)
            {"type": "fire_panel", "vendor": "schneider", "count": 4, "zone": "tunnel",
             "name_pattern": "FIRE-{n:03d}", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "SCADAPack 350",
             "role": "Fire Detection Panel",
             "cve_ids": ["CVE-2020-7480"]},

            # Tunnel CCTV (Pelco PTZ)
            {"type": "camera", "vendor": "pelco", "count": 20, "zone": "tunnel",
             "name_pattern": "CAM-T{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "Spectra Enhanced",
             "role": "Tunnel Camera",
             "cve_ids": ["CVE-2019-18230"]},

            # Seismic/Stress Sensors (SCADAPack 350 with auth bypass)
            {"type": "seismic_sensor", "vendor": "schneider", "count": 8, "zone": "tunnel",
             "name_pattern": "SEISMIC-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SCADAPack 350",
             "cve_ids": ["CVE-2020-7480"],
             "role": "Structural Monitor"},

            # Drainage Pump Controllers (SCADAPack 350 with auth bypass)
            {"type": "pump_controller", "vendor": "schneider", "count": 4, "zone": "mechanical",
             "name_pattern": "PUMP-{n:03d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SCADAPack 350",
             "cve_ids": ["CVE-2020-7480"],
             "role": "Pump Controller"},

            # DMS at Portal
            {"type": "dms", "vendor": "daktronics", "count": 2, "zone": "portal",
             "name_pattern": "DMS-PORTAL-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "Venus 7000",
             "role": "Portal Message Sign",
             "cve_ids": ["CVE-2018-18472"]},
        ],
        "flows": [
            # TCC polling lighting (1s for dimming control)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["master_station"], "target_types": ["lighting_controller"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            # TCC polling ventilation (500ms for jet fan control)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["master_station"], "target_types": ["ventilation_controller"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            # TCC polling chemical sensors (2s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["chem_sensor"],
             "jitter_ms": 100, "jitter_type": "uniform"},
            # TCC polling fire panels (1s - safety critical)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["master_station"], "target_types": ["fire_panel"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            # TCC polling cameras (5s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["master_station"], "target_types": ["camera"],
             "jitter_ms": 250, "jitter_type": "uniform"},
            # TCC polling DMS (10s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["master_station"], "target_types": ["dms"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # Modbus polling for pumps and seismic (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["master_station"], "target_types": ["pump_controller", "seismic_sensor"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "control_center", "name": "Tunnel Control Center", "level": 4,
             "subnet_offset": 0, "vlan": 10},
            {"id": "tunnel", "name": "Tunnel Zone", "level": 1,
             "subnet_offset": 1, "vlan": 20},
            {"id": "mechanical", "name": "Mechanical Room", "level": 1,
             "subnet_offset": 2, "vlan": 30},
            {"id": "portal", "name": "Portal Zone", "level": 2,
             "subnet_offset": 3, "vlan": 40},
        ],
        "suggested_anomalies": {
            "timing": ["ventilation_delay", "sensor_timeout"],
            "protocol": ["snmp_error", "modbus_exception"],
            "sequence": [],
            "payload": ["co_spike", "visibility_drop"],
            "network": [],
            "security": ["fire_panel_tamper"],
        },
        "pcap_learning_hints": [
            {"protocol": "snmp", "flow_type": "tunnel_monitoring", "priority": "high",
             "description": "Learn tunnel sensor polling patterns"},
            {"protocol": "modbus_tcp", "flow_type": "pump_control", "priority": "medium",
             "description": "Capture pump and seismic sensor polling"},
        ],
        "total_duration_ms": 300000,
    },

    "toll_plaza": {
        "name": "Electronic Toll Collection Plaza",
        "description": "Multi-lane toll plaza with RFID readers (RSUs), ANPR cameras, "
                       "lane controllers, barrier gates, and central toll system. "
                       "High-throughput transaction processing.",
        "vertical": "transportation",
        "devices": [
            # Central Toll System
            {"type": "toll_host", "vendor": "kapsch", "count": 1, "zone": "toll_center",
             "name_pattern": "TOLL-HOST-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "TCS 2000",
             "role": "Toll Host System",
             "cve_ids": ["CVE-2022-29885"]},

            # Roadside Units (DSRC/RFID readers)
            {"type": "rsu", "vendor": "q-free", "count": 12, "zone": "lanes",
             "name_pattern": "RSU-L{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "RSU 5000",
             "role": "Roadside Unit",
             "cve_ids": ["CVE-2022-30456"]},

            # Lane Controllers (Kapsch)
            {"type": "lane_controller", "vendor": "kapsch", "count": 12, "zone": "lanes",
             "name_pattern": "LANE-{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "TCS 2000",
             "role": "Lane Controller",
             "cve_ids": ["CVE-2022-29885"]},

            # ANPR Cameras (Hikvision)
            {"type": "anpr_camera", "vendor": "hikvision", "count": 24, "zone": "lanes",
             "name_pattern": "ANPR-L{n:02d}-{dir}", "protocols": ["snmp"],
             "fingerprint_model": "DS-2CD7A26G0/P",
             "role": "ANPR Camera",
             "cve_ids": ["CVE-2021-36260"]},

            # Overview Cameras (Axis)
            {"type": "camera", "vendor": "axis", "count": 8, "zone": "plaza",
             "name_pattern": "CAM-OV-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "P1455-LE",
             "role": "Overview Camera",
             "cve_ids": ["CVE-2021-31986"]},

            # DMS Signs (tolling info)
            {"type": "dms", "vendor": "daktronics", "count": 4, "zone": "plaza",
             "name_pattern": "DMS-TOLL-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "Venus 1500",
             "role": "Toll Info Sign",
             "cve_ids": ["CVE-2018-18472"]},

            # Barrier Gate Controllers (SCADAPack 350 with auth bypass)
            {"type": "barrier_controller", "vendor": "schneider", "count": 12, "zone": "lanes",
             "name_pattern": "BARRIER-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "SCADAPack 350",
             "cve_ids": ["CVE-2020-7480"],
             "role": "Barrier Controller"},

            # Vehicle Classification Sensors
            {"type": "classification_sensor", "vendor": "wavetronix", "count": 12, "zone": "lanes",
             "name_pattern": "CLASS-{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "SmartSensor Advance",
             "role": "Vehicle Classification",
             "cve_ids": ["CVE-2021-38294"]},
        ],
        "flows": [
            # Toll host polling RSUs (100ms for real-time transactions)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["toll_host"], "target_types": ["rsu"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
            # Toll host polling lane controllers (200ms)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["toll_host"], "target_types": ["lane_controller"],
             "jitter_ms": 10, "jitter_type": "gaussian"},
            # Lane controllers polling classification (100ms)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 100,
             "source_types": ["lane_controller"], "target_types": ["classification_sensor"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
            # Toll host polling ANPR (500ms)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["toll_host"], "target_types": ["anpr_camera"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            # Toll host polling overview cameras (5s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["toll_host"], "target_types": ["camera"],
             "jitter_ms": 250, "jitter_type": "uniform"},
            # Toll host polling DMS (10s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["toll_host"], "target_types": ["dms"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # Lane controllers polling barriers (50ms - fast)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 50,
             "source_types": ["lane_controller"], "target_types": ["barrier_controller"],
             "jitter_ms": 2, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "toll_center", "name": "Toll Operations Center", "level": 4,
             "subnet_offset": 0, "vlan": 10},
            {"id": "plaza", "name": "Plaza Infrastructure", "level": 2,
             "subnet_offset": 1, "vlan": 20},
            {"id": "lanes", "name": "Toll Lanes", "level": 1,
             "subnet_offset": 2, "vlan": 30},
        ],
        "suggested_anomalies": {
            "timing": ["transaction_delay", "rsu_timeout"],
            "protocol": ["snmp_error"],
            "sequence": ["duplicate_transaction"],
            "payload": ["tag_read_error", "classification_mismatch"],
            "network": [],
            "security": ["unauthorized_gate_open"],
        },
        "pcap_learning_hints": [
            {"protocol": "snmp", "flow_type": "toll_transactions", "priority": "high",
             "description": "Learn RSU polling and transaction patterns"},
            {"protocol": "snmp", "flow_type": "anpr_polling", "priority": "high",
             "description": "Capture ANPR camera image trigger patterns"},
            {"protocol": "modbus_tcp", "flow_type": "barrier_control", "priority": "medium",
             "description": "Learn barrier gate control timing"},
        ],
        "total_duration_ms": 300000,
    },

    "traffic_network_infrastructure": {
        "name": "ITS Network Infrastructure",
        "description": "Traffic management network backbone with industrial switches, "
                       "RTUs, and NTCIP devices. Includes network equipment commonly "
                       "found in ITS cabinets connecting traffic controllers, sensors, "
                       "and management systems. Focus on network layer vulnerabilities.",
        "vertical": "transportation",
        "devices": [
            # Network Operations Center
            {"type": "master_station", "vendor": "siemens", "count": 1, "zone": "noc",
             "name_pattern": "NOC-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "CP-8000",
             "role": "Network Operations Center",
             "cve_ids": ["CVE-2023-28489"]},

            # Core Network Switches (SCALANCE XM-400)
            {"type": "network_switch", "vendor": "siemens", "count": 2, "zone": "core",
             "name_pattern": "CORE-SW-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "XM-400",
             "role": "Core Switch",
             "cve_ids": ["CVE-2019-6569"]},

            # Field Cabinet Switches (SCALANCE X-200)
            {"type": "network_switch", "vendor": "siemens", "count": 12, "zone": "field",
             "name_pattern": "CAB-SW-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "X-200",
             "role": "Cabinet Switch",
             "cve_ids": ["CVE-2019-6569"]},

            # Tunnel Monitoring RTUs (TBox with hardcoded creds)
            {"type": "rtu", "vendor": "schneider", "count": 4, "zone": "tunnel",
             "name_pattern": "TBOX-{n:03d}", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "MS-CPU32",
             "role": "Tunnel RTU",
             "cve_ids": ["CVE-2021-22778"]},

            # Field RTUs (TBox LT2)
            {"type": "rtu", "vendor": "schneider", "count": 8, "zone": "field",
             "name_pattern": "TBOX-LT-{n:03d}", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "LT2",
             "role": "Field RTU",
             "cve_ids": ["CVE-2021-22778"]},

            # Traffic Controllers with Treck Stack (Ripple20)
            {"type": "traffic_controller", "vendor": "econolite", "count": 6, "zone": "field",
             "name_pattern": "TC-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "Cobalt ATC",
             "role": "Traffic Controller",
             "cve_ids": ["CVE-2020-11896"]},

            # DMS with Treck Stack
            {"type": "dms", "vendor": "daktronics", "count": 4, "zone": "field",
             "name_pattern": "DMS-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "Venus 1500",
             "role": "Dynamic Message Sign",
             "cve_ids": ["CVE-2020-11896", "CVE-2018-18472"]},

            # Radar Sensors
            {"type": "radar_sensor", "vendor": "wavetronix", "count": 8, "zone": "field",
             "name_pattern": "RADAR-{n:03d}", "protocols": ["snmp"],
             "fingerprint_model": "SmartSensor HD",
             "role": "Vehicle Detection",
             "cve_ids": ["CVE-2021-38294"]},
        ],
        "flows": [
            # NOC polling core switches (5s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["master_station"], "target_types": ["network_switch"],
             "jitter_ms": 250, "jitter_type": "uniform"},
            # NOC polling RTUs (2s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["master_station"], "target_types": ["rtu"],
             "jitter_ms": 100, "jitter_type": "uniform"},
            # NOC polling traffic controllers (1s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["master_station"], "target_types": ["traffic_controller"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
            # NOC polling DMS (10s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["master_station"], "target_types": ["dms"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # RTU polling radars (500ms)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["rtu"], "target_types": ["radar_sensor"],
             "jitter_ms": 25, "jitter_type": "gaussian"},
            # Modbus polling RTUs (1s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["master_station"], "target_types": ["rtu"],
             "jitter_ms": 50, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "noc", "name": "Network Operations Center", "level": 4,
             "subnet_offset": 0, "vlan": 10},
            {"id": "core", "name": "Core Network", "level": 3,
             "subnet_offset": 1, "vlan": 20},
            {"id": "tunnel", "name": "Tunnel Infrastructure", "level": 2,
             "subnet_offset": 2, "vlan": 30},
            {"id": "field", "name": "Field Cabinets", "level": 1,
             "subnet_offset": 3, "vlan": 40},
        ],
        "suggested_anomalies": {
            "timing": ["switch_latency", "rtu_timeout"],
            "protocol": ["snmp_error", "modbus_exception"],
            "sequence": [],
            "payload": ["switch_port_flap", "spanning_tree_event"],
            "network": ["packet_loss", "duplicate_packets"],
            "security": ["unauthorized_snmp_access", "port_scan"],
        },
        "pcap_learning_hints": [
            {"protocol": "snmp", "flow_type": "network_monitoring", "priority": "high",
             "description": "Learn SNMP polling patterns for network equipment"},
            {"protocol": "modbus_tcp", "flow_type": "rtu_polling", "priority": "medium",
             "description": "Capture RTU Modbus communication patterns"},
        ],
        "total_duration_ms": 300000,
    },
}
