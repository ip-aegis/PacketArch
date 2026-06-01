# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Energy and power industry scenario templates.

Primary Vendors: SEL, GE Grid Solutions, ABB Relion, Siemens SIPROTEC, Schneider Electric
Supporting Vendors: Honeywell (Experion), HMS Networks, Cisco Industrial
Protocol Focus: Modbus TCP (relay polling), DNP3 (WAN/SCADA), SNMP (infrastructure monitoring)

Templates cover:
- Electrical substations (transmission/distribution protection IEDs)
- Gas turbine combined-cycle power plants (GE Mark VIe DCS)
- Regional grid control centers (EMS/SCADA with remote substations)
- Solar farms with battery energy storage (microgrid/DER)

Enhanced templates with:
- CVE vulnerable firmware on protection relays and controllers
- 35-45 devices per template with realistic zone architecture
- Realistic traffic flows based on substation/generation timing
- Proper fingerprinting with protocol identities
"""

from typing import Any


ENERGY_TEMPLATES: dict[str, dict[str, Any]] = {
    # ============================================================
    # TEMPLATE 1: ELECTRICAL SUBSTATION IED NETWORK (38 devices)
    # 138kV/13.8kV substation with bay-level protection
    # ============================================================
    "electrical_substation": {
        "name": "Electrical Substation IED Network",
        "description": "IEC 61850 transmission substation. Three protection bays, each with SEL "
                       "protection relays exchanging GOOSE multicast and reporting MMS to a "
                       "station RTAC; station-ops zone with HMI / engineering / NMS / asset "
                       "management; DNP3 northbound to utility EMS over WAN. 20 devices across 6 "
                       "zones.",
        "vertical": "energy_power",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "industroyer_like", "relevance": "high", "rationale": "INDUSTROYER specifically targets electrical substation IEDs and breakers"},
            {"playbook_id": "industroyer2_like", "relevance": "high", "rationale": "INDUSTROYER2 specifically targets IEC-104 and IEC-61850 in transmission substations"},
            {"playbook_id": "havex_like", "relevance": "high", "rationale": "Energy sector reconnaissance matches HAVEX targeting profile"},
            {"playbook_id": "volt_typhoon_like", "relevance": "medium", "rationale": "LotL recon against utility OT for pre-positioning"},
            {"playbook_id": "network_recon", "relevance": "medium", "rationale": "Substation network mapping for relay enumeration"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "energy_power",
            "description": "Synchronous generator unit with power output, grid frequency, transformer loading, exhaust temperature",
            "key_variables": ["active_power", "grid_frequency", "generator_voltage", "transformer_loading", "exhaust_temp"],
            "available_faults": ["governor_failure", "transformer_overload", "grid_frequency_deviation"],
        },
        "devices": [
            # ============================================================
            # SUBSTATION LAN (Level 3) - 6 devices
            # RTAC gateway, historian, HMI, core switch, remote access
            # ============================================================
            # SEL-3530 RTAC - Substation Gateway
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "substation_lan",
             # SEL-3530 RTAC also acts as the PDC, concentrating C37.118
             # synchrophasor streams from the protection-relay PMUs.
             "name": "Substation_Gateway_RTAC", "protocols": ["modbus_tcp", "dnp3", "snmp", "c37118"],
             "fingerprint_model": "SEL-3530",
             "role": "Substation Gateway"},

            # GE Proficy Historian
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "substation_lan",
             "name": "Substation_Process_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "Process Historian"},

            # ABB CP620 HMI - Local Operator Panel
            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "substation_lan",
             "name": "Substation_Local_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Local Operator Panel"},

            # Cisco IE-4000 - Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "substation_lan",
             "name": "Substation_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # HMS Flexy 205 - Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "substation_lan",
             "name": "Substation_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # SEL-2411 PAC - Automation Controller
            {"type": "plc", "vendor": "sel", "count": 1, "zone": "substation_lan",
             "name": "Substation_Automation_Controller", "protocols": ["modbus_tcp", "dnp3", "iec61850"],
             "fingerprint_model": "SEL-2411",
             "role": "Automation Controller"},

            # ============================================================
            # BAY CONTROL (Level 2) - 6 devices
            # Bay controllers, bus protection, overcurrent, switches
            # ============================================================
            # SEL-451 Bay Controllers
            {"type": "protection_relay", "vendor": "sel", "count": 2, "zone": "bay_control",
             "name_pattern": "Bus_Section_{n:02d}_Bay_Controller",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SEL-451",
             "cve_ids": [],
             "role": "Bay Controller"},

            # ABB REX640 - Bus Tie Protection (IEC 61850 + Modbus)
            {"type": "protection_relay", "vendor": "abb", "count": 1, "zone": "bay_control",
             "name": "Bus_Tie_Protection_IED", "protocols": ["modbus_tcp", "iec61850", "snmp"],
             "fingerprint_model": "REX640",
             "role": "Bus Protection"},

            # Siemens 7SJ85 - Bus Overcurrent (IEC 61850 + Modbus)
            {"type": "protection_relay", "vendor": "siemens", "count": 1, "zone": "bay_control",
             "name": "Bus_Overcurrent_Protection", "protocols": ["modbus_tcp", "iec61850", "snmp"],
             "fingerprint_model": "7SJ85",
             "cve_ids": [],
             "role": "Overcurrent Protection"},

            # Cisco IE-3300 - Bay Network Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "bay_control",
             "name_pattern": "Bay_Network_Switch_{n:02d}", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Bay Network Switch"},

            # ============================================================
            # FEEDER PROTECTION (Level 1) - 10 devices
            # Feeder relays and backup relays
            # ============================================================
            # SEL-751 Feeder Protection Relays
            {"type": "protection_relay", "vendor": "sel", "count": 6, "zone": "feeder_zone",
             "name_pattern": "Feeder_{n:02d}_Protection_Relay",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SEL-751",
             "cve_ids": [],
             "role": "Feeder Protection"},

            # GE Multilin 850 - Feeder Backup Relays
            {"type": "protection_relay", "vendor": "ge", "count": 4, "zone": "feeder_zone",
             "name_pattern": "Feeder_{n:02d}_Backup_Relay",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "850",
             "cve_ids": [],
             "role": "Feeder Backup Protection"},

            # ============================================================
            # TRANSFORMER PROTECTION (Level 1) - 8 devices
            # Transformer differential, line distance, line differential
            # ============================================================
            # SEL-487E Transformer Differential Relays
            {"type": "protection_relay", "vendor": "sel", "count": 2, "zone": "transformer_zone",
             "name_pattern": "Transformer_{n:02d}_Differential_Relay",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SEL-487E",
             "cve_ids": [],
             "role": "Transformer Differential"},

            # Siemens 7UT87 Transformer Backup Differential (IEC 61850 + Modbus)
            {"type": "protection_relay", "vendor": "siemens", "count": 2, "zone": "transformer_zone",
             "name_pattern": "Transformer_{n:02d}_Backup_Differential",
             "protocols": ["modbus_tcp", "iec61850"],
             "fingerprint_model": "7UT87",
             "cve_ids": [],
             "role": "Transformer Backup"},

            # SEL-311C Line Distance Relays
            {"type": "protection_relay", "vendor": "sel", "count": 2, "zone": "transformer_zone",
             "name_pattern": "Transmission_Line_{n:02d}_Distance_Relay",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SEL-311C",
             "role": "Line Distance Protection"},

            # Siemens 7SD87 Line Differential (IEC 61850 + Modbus)
            {"type": "protection_relay", "vendor": "siemens", "count": 2, "zone": "transformer_zone",
             "name_pattern": "Transmission_Line_{n:02d}_Differential",
             "protocols": ["modbus_tcp", "iec61850"],
             "fingerprint_model": "7SD87",
             "role": "Line Differential"},

            # ============================================================
            # METERING (Level 1) - 6 devices
            # Revenue meters and power quality meters
            # ============================================================
            # Schneider ION8650 Revenue Meters
            {"type": "power_meter", "vendor": "schneider", "count": 4, "zone": "metering_zone",
             "name_pattern": "Feeder_{n:02d}_Revenue_Meter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ION8650",
             "role": "Revenue Meter"},

            # Schneider PM8000 Power Quality Meters
            {"type": "power_meter", "vendor": "schneider", "count": 2, "zone": "metering_zone",
             "name_pattern": "Transformer_{n:02d}_Power_Quality_Meter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM8000",
             "role": "Power Quality Meter"},

            # ============================================================
            # WAN ZONE (Level 4) - 2 devices
            # WAN communication RTU and edge switch
            # ============================================================
            # Schneider SCADAPack 350 - WAN Gateway RTU
            {"type": "rtu", "vendor": "schneider", "count": 1, "zone": "wan_zone",
             "name": "WAN_Communication_RTU", "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SCADAPack 350",
             "role": "WAN Gateway RTU"},

            # Cisco IE-3300 - WAN Edge Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "wan_zone",
             "name": "WAN_Edge_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "WAN Edge Switch"},

            # --- WAMS / EXTENDED PROTECTION (added) - 9 devices: SEL PMUs, RTAC PDC, Siemens busbar, ABB line distance, Schneider C264, Beckwith OLTC ---
            # SEL-411L Line Differential Relays + PMU (bay control)
            {"type": "protection_relay", "vendor": "sel", "count": 1, "zone": "bay_control",
             "name": "Line_Diff_PMU_North",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-411L",
             "cve_ids": [],
             "role": "Line Differential Protection + PMU"},
            {"type": "protection_relay", "vendor": "sel", "count": 1, "zone": "bay_control",
             "name": "Line_Diff_PMU_South",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-411L",
             "cve_ids": [],
             "role": "Line Differential Protection + PMU"},

            # SEL-787 Transformer Protection + PMU (transformer zone)
            {"type": "protection_relay", "vendor": "sel", "count": 1, "zone": "transformer_zone",
             "name": "Xfmr_Diff_PMU_T1",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-787",
             "cve_ids": [],
             "role": "Transformer Differential Protection + PMU"},

            # SEL-3555 RTAC - Substation PDC / Station RTAC
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "substation_lan",
             "name": "Substation_PDC_RTAC",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp"],
             "fingerprint_model": "SEL-3555",
             "role": "Phasor Data Concentrator + Station RTAC"},

            # Siemens SIPROTEC 7SS85 Busbar Differential
            {"type": "protection_relay", "vendor": "siemens", "count": 1, "zone": "bay_control",
             "name": "Busbar_Differential_7SS85",
             "protocols": ["s7comm", "iec61850", "modbus_tcp", "snmp"],
             "fingerprint_model": "7SS85",
             "cve_ids": ["CVE-2015-5374"],
             "role": "Busbar Differential Protection"},

            # ABB REL630 Line Distance Protection (feeder_zone)
            {"type": "protection_relay", "vendor": "abb", "count": 2, "zone": "feeder_zone",
             "name_pattern": "Feeder_{n:02d}_Line_Distance_REL630",
             "protocols": ["modbus_tcp", "dnp3", "iec61850"],
             "fingerprint_model": "REL630",
             "cve_ids": ["CVE-2021-22276"],
             "role": "Line Distance Protection"},

            # Schneider MiCOM C264 Bay Controller
            {"type": "protection_relay", "vendor": "schneider", "count": 1, "zone": "bay_control",
             "name": "Bay_Computer_C264",
             "protocols": ["modbus_tcp", "iec61850", "iec104", "snmp"],
             "fingerprint_model": "C264",
             "cve_ids": ["CVE-2021-22772"],
             "role": "Bay Computer / Bay Controller"},

            # Beckwith M-2001D OLTC Digital Tap-Changer Control
            {"type": "protection_relay", "vendor": "beckwith", "count": 1, "zone": "transformer_zone",
             "name": "Xfmr_T1_OLTC_Control",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "M-2001D",
             "role": "OLTC Digital Tap-Changer Control"},
        ],
        "flows": [
            # RTAC polling feeder relays (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["rtu"], "target_types": ["protection_relay"],
             "source_zones": ["substation_lan"], "target_zones": ["feeder_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # RTAC polling transformer relays (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["rtu"], "target_types": ["protection_relay"],
             "source_zones": ["substation_lan"], "target_zones": ["transformer_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # RTAC polling bay controllers (500ms - faster for bus protection)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["rtu"], "target_types": ["protection_relay"],
             "source_zones": ["substation_lan"], "target_zones": ["bay_control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # RTAC polling revenue meters (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["rtu"], "target_types": ["power_meter"],
             "source_zones": ["substation_lan"], "target_zones": ["metering_zone"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Historian collecting from RTAC (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["rtu"],
             "source_zones": ["substation_lan"], "target_zones": ["substation_lan"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # HMI polling RTAC (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["hmi"], "target_types": ["rtu"],
             "source_zones": ["substation_lan"], "target_zones": ["substation_lan"],
             "jitter_ms": 200, "jitter_type": "uniform"},

            # WAN DNP3 integrity polls from remote SCADA (2500ms with exponential jitter)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 2500,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["wan_zone"], "target_zones": ["substation_lan"],
             "jitter_ms": 500, "jitter_type": "exponential"},

            # DNP3 unsolicited responses - event-driven (Class 1/2/3 events)
            {"protocol": "dnp3", "pattern": "unsolicited", "interval_ms": 5000,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["substation_lan"], "target_zones": ["wan_zone"],
             "jitter_ms": 2000, "jitter_type": "exponential"},

            # Substation switch monitoring is performed by the remote-
            # access gateway acting as NMS proxy (covers core, bay, and
            # WAN-edge switches across all zones).
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["remote_gateway"], "target_types": ["switch"],
             "source_zones": ["substation_lan"],
             "target_zones": ["substation_lan", "bay_control",
                              "feeder_zone", "transformer_zone", "wan_zone"]},

            # Automation controller polling bay relays (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["protection_relay"],
             "source_zones": ["substation_lan"], "target_zones": ["bay_control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # SNMP monitoring relays (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["rtu"], "target_types": ["protection_relay"],
             "source_zones": ["substation_lan"],
             "target_zones": ["bay_control", "feeder_zone", "transformer_zone"]},

            # Feeder backup relay cross-polling (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["feeder_zone"], "target_zones": ["feeder_zone"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Remote gateway polling RTAC (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["rtu"],
             "source_zones": ["substation_lan"], "target_zones": ["substation_lan"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # IEC 61850 MMS reporting - bay controller to automation controller (2000ms)
            {"protocol": "iec61850", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["plc"], "target_types": ["protection_relay"],
             "source_zones": ["substation_lan"], "target_zones": ["bay_control"],
             "jitter_ms": 50, "jitter_type": "gaussian",
             "config": {"mode": "mms"}},

            # IEC 61850 MMS reporting - transformer IED data (5000ms)
            {"protocol": "iec61850", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["plc"], "target_types": ["protection_relay"],
             "source_zones": ["substation_lan"], "target_zones": ["transformer_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian",
             "config": {"mode": "mms"}},

            # IEC 61850 GOOSE - protection relay trip signals (4ms multicast)
            {"protocol": "iec61850", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["bay_control"], "target_zones": ["bay_control", "transformer_zone"],
             "jitter_ms": 1, "jitter_type": "gaussian",
             "config": {"mode": "goose"}},

            # IEEE C37.118 synchrophasor streaming - PMUs to Substation PDC (33 ms / 30 fps)
            {"protocol": "c37118", "pattern": "cyclic_data", "interval_ms": 33,
             "source_types": ["protection_relay"], "target_types": ["rtu"],
             "source_zones": ["bay_control", "transformer_zone"],
             "target_zones": ["substation_lan"],
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # IEC 61850 GOOSE bay-to-bay between SEL-411L PMUs (4 ms multicast)
            {"protocol": "iec61850", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["bay_control"], "target_zones": ["bay_control"],
             "jitter_ms": 1, "jitter_type": "gaussian",
             "config": {"mode": "goose"}},

            # IEC-104 northbound from Substation PDC RTAC to WAN/SCADA RTU (1000ms)
            {"protocol": "iec104", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["substation_lan"], "target_zones": ["wan_zone"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "substation_lan", "name": "Substation LAN", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "bay_control", "name": "Bay Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "feeder_zone", "name": "Feeder Protection Network", "level": 1,
             "subnet_offset": 2, "vlan": 121, "security_level": "high"},
            {"id": "transformer_zone", "name": "Transformer Protection Network", "level": 1,
             "subnet_offset": 3, "vlan": 122, "security_level": "high"},
            {"id": "metering_zone", "name": "Revenue Metering Network", "level": 1,
             "subnet_offset": 4, "vlan": 130, "security_level": "standard"},
            {"id": "wan_zone", "name": "WAN/SCADA Backhaul", "level": 4,
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
            "timing": ["delayed_response", "protection_trip_delay", "polling_gap"],
            "protocol": ["modbus_exception", "dnp3_timeout", "snmp_error"],
            "sequence": ["out_of_order", "duplicate", "unsolicited_event"],
            "payload": ["voltage_spike", "frequency_deviation", "power_factor_upset"],
            "network": ["wan_latency_spike", "link_failover"],
            "security": ["unauthorized_relay_setting_change", "snmp_community_scan"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "relay_setting_change"],
            "enable_recon": True,
            "target_device_types": ["protection_relay", "rtu"],
        },
        "conduits": [
            # L3 (substation_lan) <-> L2 (bay_control): RTAC/PAC to bay controllers
            {"id": "substation_to_bay", "name": "Substation LAN \u2194 Bay Control",
             "source_zone": "substation_lan", "target_zone": "bay_control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "iec61850", "iec104", "c37118", "s7comm", "snmp"],
             "security_level": "critical",
             "description": "RTAC and automation controller polling bay controllers, bus protection IEDs, PMU C37.118 streams, and network switches"},
            # L2 (bay_control) <-> L1 (feeder_zone): Bay controllers to feeder relays
            {"id": "bay_to_feeder", "name": "Bay Control \u2194 Feeder Protection",
             "source_zone": "bay_control", "target_zone": "feeder_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["iec61850"],
             "security_level": "high",
             "description": "Bay controller GOOSE trip signals to feeder protection relays"},
            # L2 (bay_control) <-> L1 (transformer_zone): Bay controllers to transformer relays
            {"id": "bay_to_transformer", "name": "Bay Control \u2194 Transformer Protection",
             "source_zone": "bay_control", "target_zone": "transformer_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["iec61850"],
             "security_level": "high",
             "description": "Bay controller GOOSE trip signals to transformer protection IEDs"},
            # L3 (substation_lan) <-> L1 (feeder_zone): RTAC to feeder relays
            {"id": "substation_to_feeder", "name": "Substation LAN \u2194 Feeder Protection",
             "source_zone": "substation_lan", "target_zone": "feeder_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "high",
             "description": "RTAC polling feeder protection relays and backup relays for status and event data"},
            # L3 (substation_lan) <-> L1 (transformer_zone): RTAC to transformer relays
            {"id": "substation_to_transformer", "name": "Substation LAN \u2194 Transformer Protection",
             "source_zone": "substation_lan", "target_zone": "transformer_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "iec61850", "c37118", "snmp"],
             "security_level": "high",
             "description": "RTAC polling transformer differential, line distance, line differential relays, and SEL-787 PMU C37.118 stream"},
            # L3 (substation_lan) <-> L1 (metering_zone): RTAC to revenue meters
            {"id": "substation_to_metering", "name": "Substation LAN \u2194 Metering",
             "source_zone": "substation_lan", "target_zone": "metering_zone",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "standard",
             "description": "RTAC polling revenue meters and power quality meters for energy accounting"},
            # L4 (wan_zone) <-> L3 (substation_lan): WAN SCADA backhaul to substation
            {"id": "wan_to_substation", "name": "WAN \u2194 Substation LAN",
             "source_zone": "wan_zone", "target_zone": "substation_lan",
             "direction": "bidirectional",
             "allowed_protocols": ["dnp3", "iec104"],
             "security_level": "critical",
             "description": "Remote SCADA WAN RTU DNP3/IEC-104 polling and unsolicited responses to/from substation RTAC and PDC"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 2: GAS TURBINE POWER GENERATION PLANT (42 devices)
    # Combined-cycle with GE Mark VIe turbine control
    # ============================================================
    "gas_turbine_generation": {
        "name": "Gas Turbine Power Generation Plant",
        "description": "Combined-cycle gas turbine plant with three generation units (GT1, GT2, "
                       "steam turbine). Emerson DeltaV / Ovation DCS controllers per unit, "
                       "Honeywell Safety Manager SIS, generator protection in a separate "
                       "electrical zone. NERC CIP regulated topology with full L3.5 IDMZ. 84 "
                       "devices across 7 zones.",
        "vertical": "energy_power",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "triton_like", "relevance": "high", "rationale": "Turbine safety systems are prime TRITON-style targets"},
            {"playbook_id": "industroyer2_like", "relevance": "medium", "rationale": "Energy generation susceptible to IEC-104 command injection at plant SCADA boundary"},
            {"playbook_id": "havex_like", "relevance": "medium", "rationale": "Power generation IP theft via remote access"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "energy_power",
            "description": "Synchronous generator unit with power output, grid frequency, transformer loading, exhaust temperature",
            "key_variables": ["active_power", "grid_frequency", "generator_voltage", "transformer_loading", "exhaust_temp"],
            "available_faults": ["governor_failure", "transformer_overload", "grid_frequency_deviation"],
        },
        "devices": [
            # ============================================================
            # PLANT SCADA (Level 3) - 7 devices
            # DCS server, historian, HMI, switches, remote access, WAN RTU
            # ============================================================
            # Honeywell Experion Server - Plant DCS Server
            {"type": "scada_server", "vendor": "honeywell", "count": 1, "zone": "plant_scada",
             "name": "Plant_DCS_Server", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Experion Server",
             "role": "Plant DCS Server"},

            # GE Proficy Historian
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "plant_scada",
             "name": "Plant_Process_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "Process Historian"},

            # Honeywell Experion Station - Operator Workstations
            {"type": "hmi", "vendor": "honeywell", "count": 2, "zone": "plant_scada",
             "name_pattern": "Plant_Operator_Workstation_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Experion Station",
             "role": "Operator Workstation"},

            # Cisco IE-4000 - Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "plant_scada",
             "name": "Plant_SCADA_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # HMS Flexy 205 - Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "plant_scada",
             "name": "Plant_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # Schneider SCADAPack 350 - WAN RTU
            {"type": "rtu", "vendor": "schneider", "count": 1, "zone": "plant_scada",
             "name": "Plant_WAN_RTU", "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SCADAPack 350",
             "role": "WAN SCADA Gateway"},

            # ============================================================
            # TURBINE CONTROL (Level 2) - 10 devices
            # Mark VIe controllers (GT, ST), HRSG PLCs, HMIs, switches
            # ============================================================
            # GE Mark VIe - Gas Turbine Controllers (Primary + Redundant)
            {"type": "dcs_controller", "vendor": "ge", "count": 2, "zone": "turbine_control",
             "name_pattern": "Gas_Turbine_Mark_VIe_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "IS420UCSBH1A",
             "cve_ids": [],
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Gas Turbine Controller"},

            # GE Mark VIe - Steam Turbine Controllers (Primary + Redundant)
            {"type": "dcs_controller", "vendor": "ge", "count": 2, "zone": "turbine_control",
             "name_pattern": "Steam_Turbine_Mark_VIe_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "IS420UCSBH1A",
             "cve_ids": [],
             "role": "Steam Turbine Controller"},

            # ABB CP620 HMI - Turbine Floor Panels
            {"type": "hmi", "vendor": "abb", "count": 2, "zone": "turbine_control",
             "name_pattern": "Turbine_Floor_HMI_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Turbine Floor Panel"},

            # GE PACSystems RX3i - HRSG Control PLCs
            {"type": "plc", "vendor": "ge", "count": 2, "zone": "turbine_control",
             "name_pattern": "HRSG_Control_PLC_{n:02d}",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "IC695CPE400",
             "cve_ids": [],
             "role": "Heat Recovery Steam Generator"},

            # Cisco IE-3300 - Turbine Network Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "turbine_control",
             "name_pattern": "Turbine_Network_Switch_{n:02d}",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Turbine Network Switch"},

            # ============================================================
            # BALANCE-OF-PLANT CONTROL (Level 2) - 8 devices
            # BOP PLCs, drives for pumps and fans
            # ============================================================
            # ABB AC500 PM590 - Cooling Tower PLC
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "bop_control",
             "name": "Cooling_Tower_PLC", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "PM590-ETH",
             "role": "Cooling Tower Controller"},

            # ABB AC500 PM590 - Fuel Gas System PLC
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "bop_control",
             "name": "Fuel_Gas_System_PLC", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "PM590-ETH",
             "role": "Fuel Gas Controller"},

            # ABB AC500 PM5630 - Water Treatment PLC
            {"type": "plc", "vendor": "abb", "count": 1, "zone": "bop_control",
             "name": "Water_Treatment_PLC", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM5630-2ETH",
             "role": "Water Treatment Controller"},

            # ABB ACS880 - Cooling Water Pump VFDs
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "bop_control",
             "name_pattern": "Cooling_Water_Pump_VFD_{n:02d}",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Cooling Water Pump"},

            # ABB ACS880 - ID Fan VFD
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "bop_control",
             "name": "ID_Fan_VFD", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Induced Draft Fan"},

            # ABB ACS580 - Boiler Feed Pump VFDs
            {"type": "drive", "vendor": "abb", "count": 2, "zone": "bop_control",
             "name_pattern": "Boiler_Feed_Pump_VFD_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ACS580",
             "role": "Boiler Feed Pump"},

            # ============================================================
            # GENERATOR PROTECTION (Level 1) - 10 devices
            # Generator differential, excitation, GSU transformer, tie line
            # ============================================================
            # SEL-487E Generator Differential Relays
            {"type": "protection_relay", "vendor": "sel", "count": 2,
             "zone": "generator_protection",
             "name_pattern": "Generator_{n:02d}_Differential_Relay",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SEL-487E",
             "cve_ids": [],
             "role": "Generator Differential"},

            # ABB REX640 Generator Excitation Protection
            {"type": "protection_relay", "vendor": "abb", "count": 2,
             "zone": "generator_protection",
             "name_pattern": "Generator_{n:02d}_Excitation_Protection",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "REX640",
             "role": "Excitation Protection"},

            # GE Multilin T60 - GSU Transformer Protection
            {"type": "protection_relay", "vendor": "ge", "count": 2,
             "zone": "generator_protection",
             "name_pattern": "GSU_Transformer_{n:02d}_Protection",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "T60",
             "cve_ids": [],
             "role": "GSU Transformer Protection"},

            # SEL-311C - Generator Tie Line Protection
            {"type": "protection_relay", "vendor": "sel", "count": 2,
             "zone": "generator_protection",
             "name_pattern": "Generator_Tie_Line_{n:02d}_Protection",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SEL-311C",
             "role": "Tie Line Protection"},

            # Siemens 7SJ85 - Generator Overcurrent Relays
            {"type": "protection_relay", "vendor": "siemens", "count": 2,
             "zone": "generator_protection",
             "name_pattern": "Generator_{n:02d}_Overcurrent_Relay",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "7SJ85",
             "cve_ids": [],
             "role": "Generator Overcurrent"},

            # ============================================================
            # AUXILIARY (Level 1) - 5 devices
            # Revenue meters, power quality, distributed I/O
            # ============================================================
            # Schneider ION8650 Revenue Meters
            {"type": "power_meter", "vendor": "schneider", "count": 2, "zone": "auxiliary",
             "name_pattern": "Generator_{n:02d}_Revenue_Meter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ION8650",
             "role": "Revenue Meter"},

            # Schneider PM8000 Power Quality Meters
            {"type": "power_meter", "vendor": "schneider", "count": 2, "zone": "auxiliary",
             "name_pattern": "Plant_Aux_Power_Meter_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM8000",
             "role": "Power Quality Meter"},

            # ABB CI501 Distributed I/O
            {"type": "io_module", "vendor": "abb", "count": 1, "zone": "auxiliary",
             "name": "Aux_Distributed_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CI501",
             "role": "Auxiliary I/O"},

            # --- EXTENDED GENERATOR PROTECTION + PLANT DCS (added) - 5 devices: 7UM85/7VK87, HPG800, Beckwith M-3425A ---
            # Siemens SIPROTEC 7UM85 - Generator Differential / Field-Failure
            {"type": "protection_relay", "vendor": "siemens", "count": 1,
             "zone": "generator_protection",
             "name": "Gen_Unit_1_Protection",
             "protocols": ["s7comm", "iec61850", "modbus_tcp", "snmp"],
             "fingerprint_model": "7UM85",
             "cve_ids": [],
             "role": "Generator Differential / Field-Failure Protection"},
            {"type": "protection_relay", "vendor": "siemens", "count": 1,
             "zone": "generator_protection",
             "name": "Gen_Unit_2_Protection",
             "protocols": ["s7comm", "iec61850", "modbus_tcp", "snmp"],
             "fingerprint_model": "7UM85",
             "cve_ids": [],
             "role": "Generator Differential / Field-Failure Protection"},

            # Siemens SIPROTEC 7VK87 - Autoreclose + Synchrocheck
            {"type": "protection_relay", "vendor": "siemens", "count": 1,
             "zone": "generator_protection",
             "name": "Gen_Autoreclose_Synchrocheck_7VK87",
             "protocols": ["s7comm", "iec61850", "modbus_tcp", "snmp"],
             "fingerprint_model": "7VK87",
             "cve_ids": ["CVE-2015-5374"],
             "role": "Autoreclose / Synchrocheck"},

            # ABB Symphony Plus HPG800 - Plant Controller (placed in plant_scada)
            {"type": "dcs_controller", "vendor": "abb", "count": 1, "zone": "plant_scada",
             "name": "Plant_Symphony_Plus_HPG800",
             "protocols": ["modbus_tcp", "opc_ua", "snmp"],
             "fingerprint_model": "HPG800",
             "cve_ids": [],
             "role": "Symphony Plus Plant Controller"},

            # Beckwith M-3425A - Generator Backup Protection
            {"type": "protection_relay", "vendor": "beckwith", "count": 1,
             "zone": "generator_protection",
             "name": "Generator_Backup_Protection_M3425A",
             "protocols": ["modbus_tcp", "dnp3", "iec61850"],
             "fingerprint_model": "M-3425A",
             "role": "Generator Backup Protection"},
        ],
        "flows": [
            # DCS server polling Mark VIe controllers (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["scada_server"], "target_types": ["dcs_controller"],
             "source_zones": ["plant_scada"], "target_zones": ["turbine_control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # DCS server polling BOP PLCs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "source_zones": ["plant_scada"], "target_zones": ["bop_control"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Mark VIe polling HRSG PLCs (200ms - fast turbine-HRSG coordination)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source_types": ["dcs_controller"], "target_types": ["plc"],
             "source_zones": ["turbine_control"], "target_zones": ["turbine_control"],
             "jitter_ms": 20, "jitter_type": "gaussian"},

            # BOP PLCs polling drives (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["bop_control"], "target_zones": ["bop_control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Turbine HMI polling Mark VIe controllers (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["dcs_controller"],
             "source_zones": ["turbine_control"], "target_zones": ["turbine_control"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # Plant HMI polling DCS server (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["scada_server"],
             "source_zones": ["plant_scada"], "target_zones": ["plant_scada"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # Historian collecting from all controllers (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["dcs_controller", "plc"],
             "source_zones": ["plant_scada"],
             "target_zones": ["turbine_control", "bop_control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # DCS server polling generator protection relays (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["protection_relay"],
             "source_zones": ["plant_scada"], "target_zones": ["generator_protection"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # DCS server polling revenue meters (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["scada_server"], "target_types": ["power_meter"],
             "source_zones": ["plant_scada"], "target_zones": ["auxiliary"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # SNMP infrastructure monitoring (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["plant_scada"],
             "target_zones": ["plant_scada", "turbine_control"]},

            # WAN RTU polling DCS server (2500ms with WAN jitter)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2500,
             "source_types": ["rtu"], "target_types": ["scada_server"],
             "source_zones": ["plant_scada"], "target_zones": ["plant_scada"],
             "jitter_ms": 500, "jitter_type": "exponential"},

            # Generator relay coordination (250ms - fast protection)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["generator_protection"],
             "target_zones": ["generator_protection"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # BOP PLCs polling I/O modules (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["bop_control"], "target_zones": ["auxiliary"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Remote gateway polling DCS server (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["scada_server"],
             "source_zones": ["plant_scada"], "target_zones": ["plant_scada"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # IEC 61850 GOOSE between Siemens 7UM85 generator protection and 7VK87 synchrocheck (intra-zone, 4 ms)
            {"protocol": "iec61850", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["generator_protection"], "target_zones": ["generator_protection"],
             "jitter_ms": 1, "jitter_type": "gaussian", "config": {"mode": "goose"}},

            # DCS server polling ABB Symphony Plus HPG800 plant controller (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["dcs_controller"],
             "source_zones": ["plant_scada"], "target_zones": ["plant_scada"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "plant_scada", "name": "Plant SCADA Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "turbine_control", "name": "Turbine Control Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "critical"},
            {"id": "bop_control", "name": "Balance-of-Plant Control", "level": 2,
             "subnet_offset": 2, "vlan": 120, "security_level": "high"},
            {"id": "generator_protection", "name": "Generator Protection Network", "level": 1,
             "subnet_offset": 3, "vlan": 131, "security_level": "high"},
            {"id": "auxiliary", "name": "Auxiliary Systems Network", "level": 1,
             "subnet_offset": 4, "vlan": 140, "security_level": "standard"},
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
            "timing": ["delayed_response", "turbine_trip_delay", "polling_gap"],
            "protocol": ["modbus_exception", "timeout"],
            "sequence": ["out_of_order", "duplicate"],
            "payload": ["frequency_deviation", "voltage_excursion", "bearing_vibration_spike"],
            "network": ["link_failover"],
            "security": ["unauthorized_setpoint_change", "turbine_control_injection"],
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
            "target_device_types": ["dcs_controller", "plc"],
        },
        "conduits": [
            # L3 (plant_scada) <-> L2 (turbine_control): Plant SCADA to turbine controllers
            {"id": "scada_to_turbine", "name": "Plant SCADA \u2194 Turbine Control",
             "source_zone": "plant_scada", "target_zone": "turbine_control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "DCS server and historian polling Mark VIe controllers, HRSG PLCs, and turbine HMIs"},
            # L3 (plant_scada) <-> L2 (bop_control): Plant SCADA to balance-of-plant
            {"id": "scada_to_bop", "name": "Plant SCADA \u2194 Balance-of-Plant",
             "source_zone": "plant_scada", "target_zone": "bop_control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "high",
             "description": "DCS server and historian polling cooling, fuel gas, and water treatment PLCs"},
            # L3 (plant_scada) <-> L1 (generator_protection): Plant SCADA to generator relays
            {"id": "scada_to_gen_prot", "name": "Plant SCADA \u2194 Generator Protection",
             "source_zone": "plant_scada", "target_zone": "generator_protection",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "s7comm", "iec61850", "dnp3", "snmp"],
             "security_level": "high",
             "description": "DCS server polling generator differential, excitation, overcurrent, synchrocheck, and backup protection relays (Siemens SIPROTEC + Beckwith)"},
            # L3 (plant_scada) <-> L1 (auxiliary): Plant SCADA to auxiliary systems
            {"id": "scada_to_auxiliary", "name": "Plant SCADA \u2194 Auxiliary",
             "source_zone": "plant_scada", "target_zone": "auxiliary",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "standard",
             "description": "DCS server polling revenue meters and power quality meters"},
            # L2 (bop_control) <-> L1 (auxiliary): BOP PLCs to auxiliary I/O
            {"id": "bop_to_auxiliary", "name": "Balance-of-Plant \u2194 Auxiliary",
             "source_zone": "bop_control", "target_zone": "auxiliary",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "standard",
             "description": "BOP PLCs polling distributed I/O modules in auxiliary systems"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # ============================================================
    # TEMPLATE 3: REGIONAL GRID CONTROL CENTER (45 devices)
    # EMS/SCADA monitoring 8 remote substations
    # ============================================================
    "grid_control_center": {
        "name": "Regional Grid Control Center",
        "description": "Multi-substation grid control center modeled as a multi-site IEC 61850 "
                       "deployment. Six protection bays, station bus, and central operations "
                       "zone with primary + standby RTACs. Heavy GOOSE intra-bay traffic and "
                       "DNP3 / IEC 104 north-uplink. 40 devices across 9 zones.",
        "vertical": "energy_power",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "industroyer_like", "relevance": "high", "rationale": "Grid control center is the primary INDUSTROYER target architecture"},
            {"playbook_id": "industroyer2_like", "relevance": "critical", "rationale": "Direct match for INDUSTROYER2: IEC-104 command injection against transmission control center"},
            {"playbook_id": "volt_typhoon_like", "relevance": "high", "rationale": "Pre-positioning in regional EMS is a documented Volt Typhoon target"},
            {"playbook_id": "havex_like", "relevance": "high", "rationale": "HAVEX energy sector espionage pattern"},
            {"playbook_id": "insider_threat", "relevance": "medium", "rationale": "EMS/SCADA operator access to grid-wide controls"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "energy_power",
            "description": "Synchronous generator unit with power output, grid frequency, transformer loading, exhaust temperature",
            "key_variables": ["active_power", "grid_frequency", "generator_voltage", "transformer_loading", "exhaust_temp"],
            "available_faults": ["governor_failure", "transformer_overload", "grid_frequency_deviation"],
        },
        "devices": [
            # ============================================================
            # EMS CORE (Level 3) - 8 devices
            # Dual SCADA servers, historian, operator consoles, core switch
            # ============================================================
            # Honeywell Experion Server - Primary SCADA
            {"type": "scada_server", "vendor": "honeywell", "count": 1, "zone": "ems_core",
             "name": "EMS_Primary_SCADA_Server", "protocols": ["modbus_tcp", "opc_ua", "snmp", "ethernet_ip", "iec104"],
             "fingerprint_model": "Experion Server",
             "role": "Primary SCADA Server"},

            # Honeywell Experion Server - Backup SCADA
            {"type": "scada_server", "vendor": "honeywell", "count": 1, "zone": "ems_core",
             "name": "EMS_Backup_SCADA_Server", "protocols": ["modbus_tcp", "opc_ua", "snmp", "ethernet_ip", "iec104"],
             "fingerprint_model": "Experion Server",
             "role": "Backup SCADA Server"},

            # GE Proficy Historian
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "ems_core",
             "name": "EMS_Grid_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "Grid Historian"},

            # Honeywell Experion Station - Operator Consoles
            {"type": "hmi", "vendor": "honeywell", "count": 3, "zone": "ems_core",
             "name_pattern": "EMS_Operator_Console_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Experion Station",
             "role": "Operator Console"},

            # Cisco IE-4000 - Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "ems_core",
             "name": "EMS_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # HMS Flexy 205 - Remote Access Gateway
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "ems_core",
             "name": "EMS_Remote_Access_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # ============================================================
            # ENGINEERING (Level 3) - 3 devices
            # Application server, engineering workstation, switch
            # ============================================================
            # GE PACSystems RX3i - EMS Application Server
            {"type": "plc", "vendor": "ge", "count": 1, "zone": "engineering",
             "name": "EMS_Application_Server",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "IC695CPE400",
             "role": "EMS Application Engine"},

            # ABB CP620 - Engineering Workstation
            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "engineering",
             "name": "Engineering_Workstation", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Engineering Workstation"},

            # Cisco IE-3300 - Engineering Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "engineering",
             "name": "Engineering_Network_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Engineering Network Switch"},

            # ============================================================
            # COMMUNICATIONS HUB (Level 2) - 4 devices
            # Front-end processors (dual RTAC) and WAN switches
            # ============================================================
            # SEL-3530 RTAC - Primary Comm Front-End
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "comm_hub",
             "name": "Comm_Hub_RTAC_Primary",
             "protocols": ["modbus_tcp", "dnp3", "snmp"],
             "fingerprint_model": "SEL-3530",
             "role": "Primary Communications Front-End"},

            # SEL-3530 RTAC - Redundant Comm Front-End
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "comm_hub",
             "name": "Comm_Hub_RTAC_Redundant",
             "protocols": ["modbus_tcp", "dnp3", "snmp"],
             "fingerprint_model": "SEL-3530",
             "role": "Redundant Communications Front-End"},

            # Cisco IE-4000 - WAN Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "comm_hub",
             "name_pattern": "Comm_Hub_WAN_Switch_{n:02d}",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Communications WAN Switch"},

            # ============================================================
            # REMOTE SUBSTATIONS A - Group 1-4 (Level 1) - 14 devices
            # SEL RTACs, protection relays, revenue meters
            # ============================================================
            # SEL-3530 RTAC - Substation Gateways (4 substations)
            {"type": "rtu", "vendor": "sel", "count": 4, "zone": "remote_sub_a",
             "name_pattern": "Substation_{n:02d}_RTAC",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SEL-3530",
             "role": "Remote Substation Gateway"},

            # SEL-751 Feeder Relays (1 per substation)
            {"type": "protection_relay", "vendor": "sel", "count": 4, "zone": "remote_sub_a",
             "name_pattern": "Substation_{n:02d}_Feeder_Relay",
             "protocols": ["modbus_tcp", "dnp3", "snmp"],
             "fingerprint_model": "SEL-751",
             "cve_ids": [],
             "role": "Feeder Protection"},

            # SEL-487E Transformer Relays (substations 1-2)
            {"type": "protection_relay", "vendor": "sel", "count": 2, "zone": "remote_sub_a",
             "name_pattern": "Substation_{n:02d}_Transformer_Relay",
             "protocols": ["modbus_tcp", "dnp3", "snmp"],
             "fingerprint_model": "SEL-487E",
             "role": "Transformer Protection"},

            # Schneider ION8650 Revenue Meters
            {"type": "power_meter", "vendor": "schneider", "count": 4, "zone": "remote_sub_a",
             "name_pattern": "Substation_{n:02d}_Revenue_Meter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ION8650",
             "role": "Revenue Meter"},

            # ============================================================
            # REMOTE SUBSTATIONS B - Group 5-8 (Level 1) - 14 devices
            # ABB RTU560s, protection relays, power meters
            # ============================================================
            # ABB RTU560 - Substation RTUs (4 substations)
            {"type": "rtu", "vendor": "abb", "count": 4, "zone": "remote_sub_b",
             "name_pattern": "Substation_{n:02d}_RTU",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "RTU560",
             "role": "Remote Substation RTU"},

            # ABB REF615 Feeder Relays
            {"type": "protection_relay", "vendor": "abb", "count": 4, "zone": "remote_sub_b",
             "name_pattern": "Substation_{n:02d}_Feeder_Relay",
             "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "REF615",
             "cve_ids": [],
             "role": "Feeder Protection"},

            # GE Multilin T60 Transformer Relays (substations 5-6)
            {"type": "protection_relay", "vendor": "ge", "count": 2, "zone": "remote_sub_b",
             "name_pattern": "Substation_{n:02d}_Transformer_Relay",
             "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "T60",
             "cve_ids": [],
             "role": "Transformer Protection"},

            # Schneider PM8000 Power Meters
            {"type": "power_meter", "vendor": "schneider", "count": 4, "zone": "remote_sub_b",
             "name_pattern": "Substation_{n:02d}_Power_Meter",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM8000",
             "role": "Power Meter"},

            # ============================================================
            # WAN (Level 4) - 2 devices
            # Backup communication RTUs
            # ============================================================
            # Schneider SCADAPack 350 - WAN Backup RTUs
            {"type": "rtu", "vendor": "schneider", "count": 2, "zone": "wan",
             "name_pattern": "WAN_Backup_RTU_{n:02d}",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SCADAPack 350",
             "role": "WAN Backup Path"},

            # --- WAMS / PDC AGGREGATION (added) - 9 devices: regional PDCs at EMS, 3 substation PMUs, C264, Beckwith M-7679 ---
            # SEL-3555 RTAC - Regional Phasor Data Concentrators (EMS core, 2x)
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "ems_core",
             "name": "Regional_PDC_North",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],
             "fingerprint_model": "SEL-3555",
             "role": "Regional Phasor Data Concentrator"},
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "ems_core",
             "name": "Regional_PDC_South",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],
             "fingerprint_model": "SEL-3555",
             "role": "Regional Phasor Data Concentrator"},

            # SEL-411L PMUs at remote substations (3 total, split across A/B)
            {"type": "protection_relay", "vendor": "sel", "count": 2, "zone": "remote_sub_a",
             "name_pattern": "Substation_A{n:02d}_PMU_SEL411L",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-411L",
             "cve_ids": [],
             "role": "Substation PMU"},
            {"type": "protection_relay", "vendor": "sel", "count": 1, "zone": "remote_sub_b",
             "name": "Substation_B01_PMU_SEL411L",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-411L",
             "cve_ids": [],
             "role": "Substation PMU"},

            # Schneider MiCOM C264 Bay Controller (placed at remote_sub_a)
            {"type": "protection_relay", "vendor": "schneider", "count": 1, "zone": "remote_sub_a",
             "name": "Substation_A_Bay_Computer_C264",
             "protocols": ["modbus_tcp", "iec61850", "iec104", "snmp"],
             "fingerprint_model": "C264",
             "cve_ids": ["CVE-2021-22772"],
             "role": "Bay Computer / Bay Controller"},

            # Substation PMU concentrators (SEL-3555 at substations)
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "remote_sub_a",
             "name": "Substation_A_Local_PDC_SEL3555",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],
             "fingerprint_model": "SEL-3555",
             "role": "Substation Phasor Data Concentrator"},
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "remote_sub_b",
             "name": "Substation_B_Local_PDC_SEL3555",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],
             "fingerprint_model": "SEL-3555",
             "role": "Substation Phasor Data Concentrator"},

            # Beckwith M-7679 Transformer Monitor (asset monitoring at EMS)
            {"type": "rtu", "vendor": "beckwith", "count": 1, "zone": "ems_core",
             "name": "EMS_Transformer_Asset_Monitor_M7679",
             "protocols": ["modbus_tcp", "dnp3", "snmp"],
             "fingerprint_model": "M-7679",
             "role": "Asset Monitoring"},
        ],
        "flows": [
            # Comm Hub RTAC DNP3 integrity polls to remote substations A (2500ms - WAN)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 2500,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["comm_hub"], "target_zones": ["remote_sub_a"],
             "jitter_ms": 500, "jitter_type": "exponential"},

            # Comm Hub RTAC DNP3 integrity polls to remote substations B (2500ms - WAN)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 2500,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["comm_hub"], "target_zones": ["remote_sub_b"],
             "jitter_ms": 500, "jitter_type": "exponential"},

            # DNP3 unsolicited responses from remote substations (event-driven)
            {"protocol": "dnp3", "pattern": "unsolicited", "interval_ms": 5000,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["remote_sub_a", "remote_sub_b"],
             "target_zones": ["comm_hub"],
             "jitter_ms": 2000, "jitter_type": "exponential"},

            # EMS SCADA polling Comm Hub RTACs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "source_zones": ["ems_core"], "target_zones": ["comm_hub"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Historian collecting from Comm Hub (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["rtu"],
             "source_zones": ["ems_core"], "target_zones": ["comm_hub"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # HMI polling SCADA servers (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["scada_server"],
             "source_zones": ["ems_core"], "target_zones": ["ems_core"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # Engineering polling application server (2000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["engineering"], "target_zones": ["engineering"],
             "jitter_ms": 200, "jitter_type": "uniform"},

            # SCADA server polling application server (1000ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["plc"],
             "source_zones": ["ems_core"], "target_zones": ["engineering"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # SNMP monitoring all switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["scada_server"], "target_types": ["switch"],
             "source_zones": ["ems_core"],
             "target_zones": ["ems_core", "engineering", "comm_hub"]},

            # Remote relay polling revenue meters (10s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["rtu"], "target_types": ["power_meter"],
             "source_zones": ["remote_sub_a", "remote_sub_b"],
             "target_zones": ["remote_sub_a", "remote_sub_b"],
             "jitter_ms": 1000, "jitter_type": "gaussian"},

            # WAN backup DNP3 polling (5000ms)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["wan"], "target_zones": ["comm_hub"],
             "jitter_ms": 1000, "jitter_type": "exponential"},

            # SNMP monitoring remote relays (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["rtu"], "target_types": ["protection_relay"],
             "source_zones": ["comm_hub"],
             "target_zones": ["remote_sub_a", "remote_sub_b"]},

            # Remote gateway polling SCADA (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["scada_server"],
             "source_zones": ["ems_core"], "target_zones": ["ems_core"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # C37.118 synchrophasor streaming - substation PMUs → substation PDCs (33 ms / 30 fps)
            {"protocol": "c37118", "pattern": "cyclic_data", "interval_ms": 33,
             "source_types": ["protection_relay"], "target_types": ["rtu"],
             "source_zones": ["remote_sub_a", "remote_sub_b"],
             "target_zones": ["remote_sub_a", "remote_sub_b"],
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # C37.118 aggregated PDC streams - substation PDCs → regional EMS PDCs (33 ms)
            {"protocol": "c37118", "pattern": "cyclic_data", "interval_ms": 33,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["remote_sub_a", "remote_sub_b"],
             "target_zones": ["ems_core"],
             "jitter_ms": 5, "jitter_type": "gaussian"},

            # IEC-104 from regional EMS PDCs to primary SCADA master (1000ms)
            {"protocol": "iec104", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["scada_server"], "target_types": ["rtu"],
             "source_zones": ["ems_core"], "target_zones": ["ems_core"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # IEC 61850 GOOSE intra-substation bay-to-bay (cyclic_io 4 ms)
            {"protocol": "iec61850", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["remote_sub_a", "remote_sub_b"],
             "target_zones": ["remote_sub_a", "remote_sub_b"],
             "jitter_ms": 1, "jitter_type": "gaussian",
             "config": {"mode": "goose"}},
        ],
        "zones": [
            {"id": "ems_core", "name": "EMS Core Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "engineering", "name": "Engineering Network", "level": 3,
             "subnet_offset": 1, "vlan": 105, "security_level": "critical"},
            {"id": "comm_hub", "name": "Communications Hub", "level": 2,
             "subnet_offset": 2, "vlan": 110, "security_level": "high"},
            {"id": "remote_sub_a", "name": "Remote Substations A (1-4)", "level": 1,
             "subnet_offset": 3, "vlan": 121, "security_level": "high"},
            {"id": "remote_sub_b", "name": "Remote Substations B (5-8)", "level": 1,
             "subnet_offset": 4, "vlan": 122, "security_level": "high"},
            {"id": "wan", "name": "WAN/Telecom", "level": 4,
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
            "protocol": ["modbus_exception", "dnp3_timeout"],
            "sequence": ["out_of_order", "unsolicited_event"],
            "payload": ["frequency_deviation", "voltage_excursion", "load_imbalance"],
            "network": ["wan_latency_spike", "communication_failover"],
            "security": ["unauthorized_scada_access", "relay_setting_change"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "scada_auth_bypass"],
            "enable_recon": True,
            "target_device_types": ["scada_server", "rtu"],
        },
        "conduits": [
            # L3 (ems_core) <-> L2 (comm_hub): EMS SCADA to communications front-end
            {"id": "ems_to_comm", "name": "EMS Core \u2194 Communications Hub",
             "source_zone": "ems_core", "target_zone": "comm_hub",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "critical",
             "description": "EMS SCADA servers and historian polling communications hub RTACs and WAN switches"},
            # L3 (ems_core) <-> L3 (engineering): EMS core to engineering
            {"id": "ems_to_engineering", "name": "EMS Core \u2194 Engineering",
             "source_zone": "ems_core", "target_zone": "engineering",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "security_level": "critical",
             "description": "SCADA servers polling application server and SNMP monitoring of engineering switch"},
            # L2 (comm_hub) <-> L1 (remote_sub_a): Comm hub to remote substations group A
            {"id": "comm_to_sub_a", "name": "Communications Hub \u2194 Remote Substations A",
             "source_zone": "comm_hub", "target_zone": "remote_sub_a",
             "direction": "bidirectional",
             "allowed_protocols": ["dnp3", "snmp", "modbus_tcp", "iec61850", "iec104", "c37118"],
             "security_level": "high",
             "description": "Comm hub RTACs polling remote substations A (1-4) via WAN DNP3/Modbus and IEC-61850/104 + C37.118 PMU streams for relay health and synchrophasor data"},
            # L2 (comm_hub) <-> L1 (remote_sub_b): Comm hub to remote substations group B
            {"id": "comm_to_sub_b", "name": "Communications Hub \u2194 Remote Substations B",
             "source_zone": "comm_hub", "target_zone": "remote_sub_b",
             "direction": "bidirectional",
             "allowed_protocols": ["dnp3", "snmp", "modbus_tcp", "iec61850", "iec104", "c37118"],
             "security_level": "high",
             "description": "Comm hub RTACs polling remote substations B (5-8) via WAN DNP3/Modbus and IEC-61850/104 + C37.118 PMU streams for relay health and synchrophasor data"},
            # L4 (wan) <-> L2 (comm_hub): WAN backup to comm hub
            {"id": "wan_to_comm", "name": "WAN \u2194 Communications Hub",
             "source_zone": "wan", "target_zone": "comm_hub",
             "direction": "bidirectional",
             "allowed_protocols": ["dnp3"],
             "security_level": "high",
             "description": "WAN backup RTUs providing redundant DNP3 communication path to comm hub RTACs"},
            # L3 (ems_core) <-> L1 (remote_sub_a): EMS regional PDCs receive PMU streams
            {"id": "ems_to_sub_a", "name": "EMS Core \u2194 Remote Substations A (WAMS)",
             "source_zone": "ems_core", "target_zone": "remote_sub_a",
             "direction": "bidirectional",
             "allowed_protocols": ["c37118", "iec104", "modbus_tcp"],
             "security_level": "critical",
             "description": "Regional PDCs at EMS aggregating C37.118 synchrophasor streams and IEC-104 from substation A PDC"},
            # L3 (ems_core) <-> L1 (remote_sub_b): EMS regional PDCs receive PMU streams
            {"id": "ems_to_sub_b", "name": "EMS Core \u2194 Remote Substations B (WAMS)",
             "source_zone": "ems_core", "target_zone": "remote_sub_b",
             "direction": "bidirectional",
             "allowed_protocols": ["c37118", "iec104", "modbus_tcp"],
             "security_level": "critical",
             "description": "Regional PDCs at EMS aggregating C37.118 synchrophasor streams and IEC-104 from substation B PDC"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
    },

    # ============================================================
    # TEMPLATE 4: SOLAR FARM WITH BESS MICROGRID (35 devices)
    # Utility-scale solar + battery energy storage
    # ============================================================
    "solar_bess_microgrid": {
        "name": "Solar Farm with Battery Energy Storage",
        "description": "Solar + battery-energy-storage microgrid modeled as a small-substation "
                       "shape: three protection-class bays (inverter strings / BESS racks / "
                       "point-of-interconnection) plus station-ops zone with HMI + RTAC. "
                       "Mixed-field vendor profile (Schneider RTUs, Emerson instruments). 20 "
                       "devices across 6 zones.",
        "vertical": "energy_power",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "network_recon", "relevance": "high", "rationale": "DER/microgrid discovery and capability mapping"},
            {"playbook_id": "volt_typhoon_like", "relevance": "high", "rationale": "DER aggregation and microgrid controllers are increasingly targeted for grid disruption pre-positioning"},
            {"playbook_id": "industroyer_like", "relevance": "medium", "rationale": "Grid-connected DER can be leveraged for grid destabilization"}
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "energy_power",
            "description": "Synchronous generator unit with power output, grid frequency, transformer loading, exhaust temperature",
            "key_variables": ["active_power", "grid_frequency", "generator_voltage", "transformer_loading", "exhaust_temp"],
            "available_faults": ["governor_failure", "transformer_overload", "grid_frequency_deviation"],
        },
        "devices": [
            # ============================================================
            # MICROGRID CONTROL (Level 3) - 7 devices
            # Master controller, historian, HMI, RTAC, core switch
            # ============================================================
            # SEL-2411 PAC - Microgrid Master Controller
            {"type": "plc", "vendor": "sel", "count": 1, "zone": "microgrid_control",
             "name": "Microgrid_Master_Controller",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SEL-2411",
             "role": "Microgrid Controller"},

            # GE Proficy Historian
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "microgrid_control",
             "name": "Plant_Process_Historian", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "Process Historian"},

            # ABB CP620 HMI - Plant Control Room
            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "microgrid_control",
             "name": "Plant_Control_Room_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "Control Room HMI"},

            # Honeywell Experion Station - Operator Workstation
            {"type": "hmi", "vendor": "honeywell", "count": 1, "zone": "microgrid_control",
             "name": "Plant_Operator_Workstation", "protocols": ["modbus_tcp"],
             "fingerprint_model": "Experion Station",
             "role": "Operator Workstation"},

            # Cisco IE-4000 - Core Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "microgrid_control",
             "name": "Microgrid_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "Core Network Switch"},

            # HMS Flexy 205 - Remote Access
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "microgrid_control",
             "name": "Solar_Farm_Remote_Access", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True},

            # SEL-3530 RTAC - SCADA Gateway
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "microgrid_control",
             "name": "Plant_SCADA_Gateway_RTAC",
             "protocols": ["modbus_tcp", "dnp3", "snmp"],
             "fingerprint_model": "SEL-3530",
             "role": "SCADA Gateway"},

            # ============================================================
            # INVERTER FIELD (Level 2) - 8 devices
            # String controllers, central inverter PLCs, switches
            # ============================================================
            # ABB AC500 PM583 - Inverter String Controllers
            {"type": "plc", "vendor": "abb", "count": 4, "zone": "inverter_field",
             "name_pattern": "Inverter_String_{n:02d}_Controller",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM583-ETH",
             "error_config": {"exception_rate": 0.0005, "timeout_rate": 0.0002},
             "role": "Inverter String Controller"},

            # ABB AC500 PM590 - Central Inverter PLCs
            {"type": "plc", "vendor": "abb", "count": 2, "zone": "inverter_field",
             "name_pattern": "Central_Inverter_PLC_{n:02d}",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "PM590-ETH",
             "role": "Central Inverter Controller"},

            # Cisco IE-3300 - Inverter Field Switches
            {"type": "switch", "vendor": "cisco", "count": 2, "zone": "inverter_field",
             "name_pattern": "Inverter_Field_Switch_{n:02d}",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Inverter Field Switch"},

            # ============================================================
            # BESS CONTROL (Level 2) - 6 devices
            # Battery rack controllers, master, power converter, HMI
            # ============================================================
            # GE PACSystems RX3i - BESS Rack Controllers
            {"type": "plc", "vendor": "ge", "count": 2, "zone": "bess_control",
             "name_pattern": "BESS_Rack_{n:02d}_Controller",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "IC695CPE400",
             "cve_ids": [],
             "role": "Battery Rack Controller"},

            # GE PACSystems RX3i - BESS Master Controller
            {"type": "plc", "vendor": "ge", "count": 1, "zone": "bess_control",
             "name": "BESS_Master_Controller",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "IC695CPE310",
             "role": "BESS Master Controller"},

            # ABB ACS880 - Power Converter VFD
            {"type": "drive", "vendor": "abb", "count": 1, "zone": "bess_control",
             "name": "BESS_Power_Converter_VFD",
             "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "ACS880-01",
             "role": "Power Converter"},

            # ABB CP620 HMI - BESS Local Panel
            {"type": "hmi", "vendor": "abb", "count": 1, "zone": "bess_control",
             "name": "BESS_Local_Panel", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CP620",
             "role": "BESS Local Panel"},

            # Cisco IE-3300 - BESS Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "bess_control",
             "name": "BESS_Network_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "BESS Network Switch"},

            # ============================================================
            # POI PROTECTION (Level 1) - 6 devices
            # Interconnection relays and net meters
            # ============================================================
            # ABB REX640 - POI Main Protection
            {"type": "protection_relay", "vendor": "abb", "count": 1,
             "zone": "poi_protection",
             "name": "POI_Main_Protection_IED", "protocols": ["modbus_tcp"],
             "fingerprint_model": "REX640",
             "role": "POI Main Protection"},

            # ABB REF615 - POI Feeder Protection
            {"type": "protection_relay", "vendor": "abb", "count": 1,
             "zone": "poi_protection",
             "name": "POI_Feeder_Protection", "protocols": ["modbus_tcp"],
             "fingerprint_model": "REF615",
             "cve_ids": [],
             "role": "POI Feeder Protection"},

            # SEL-751 - Anti-Islanding Relay
            {"type": "protection_relay", "vendor": "sel", "count": 1,
             "zone": "poi_protection",
             "name": "POI_Anti_Islanding_Relay",
             "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SEL-751",
             "role": "Anti-Islanding Protection"},

            # Siemens 7UT87 - POI Transformer Protection
            {"type": "protection_relay", "vendor": "siemens", "count": 1,
             "zone": "poi_protection",
             "name": "POI_Transformer_Protection", "protocols": ["modbus_tcp"],
             "fingerprint_model": "7UT87",
             "cve_ids": [],
             "role": "POI Transformer Protection"},

            # Schneider ION8650 - Net Revenue Meters
            {"type": "power_meter", "vendor": "schneider", "count": 2,
             "zone": "poi_protection",
             "name_pattern": "POI_Net_Meter_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "ION8650",
             "role": "Net Revenue Meter"},

            # ============================================================
            # ENVIRONMENTAL MONITORING (Level 1) - 6 devices
            # Weather RTUs, AC power meters, sensor I/O
            # ============================================================
            # Schneider TBox LT2 - Weather Station RTUs
            {"type": "rtu", "vendor": "schneider", "count": 3, "zone": "environmental",
             "name_pattern": "Weather_Station_RTU_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "LT2",
             "role": "Weather/Irradiance Station"},

            # Schneider PM8000 - Inverter AC Power Meters
            {"type": "power_meter", "vendor": "schneider", "count": 2, "zone": "environmental",
             "name_pattern": "Inverter_AC_Power_Meter_{n:02d}",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM8000",
             "role": "Inverter AC Power Meter"},

            # ABB CI501 - Environmental Sensor I/O
            {"type": "io_module", "vendor": "abb", "count": 1, "zone": "environmental",
             "name": "Environmental_Sensor_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "CI501",
             "role": "Environment Sensor I/O"},

            # ============================================================
            # WAN (Level 4) - 2 devices
            # Utility WAN RTU and edge switch
            # ============================================================
            # Schneider SCADAPack 350 - Utility WAN RTU
            {"type": "rtu", "vendor": "schneider", "count": 1, "zone": "wan",
             "name": "Utility_WAN_RTU", "protocols": ["modbus_tcp", "dnp3"],
             "fingerprint_model": "SCADAPack 350",
             "role": "Utility SCADA Gateway"},

            # Cisco IE-3300 - WAN Edge Switch
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "wan",
             "name": "WAN_Edge_Switch", "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "WAN Edge Switch"},

            # --- DER PROTECTION + POI METERING (added) - 6 devices: Easergy P3/T300/P1, ABB RED615, ION9000 ---
            # Schneider Easergy P3 - Inverter Array Feeder Protection (2x)
            {"type": "protection_relay", "vendor": "schneider", "count": 2, "zone": "inverter_field",
             "name_pattern": "Inverter_Array_{n:02d}_Feeder_Protection_P3",
             "protocols": ["modbus_tcp", "dnp3", "iec61850"],
             "fingerprint_model": "P3U30",
             "cve_ids": ["CVE-2022-37300", "CVE-2022-37301"],
             "role": "Feeder Protection Relay"},

            # Schneider Easergy T300 - POI RTU
            {"type": "rtu", "vendor": "schneider", "count": 1, "zone": "poi_protection",
             "name": "POI_RTU_T300",
             "protocols": ["modbus_tcp", "dnp3", "iec104", "snmp"],
             "fingerprint_model": "T300",
             "cve_ids": ["CVE-2022-37300"],
             "role": "POI RTU"},

            # Schneider Easergy P1 - BESS String Protection
            {"type": "protection_relay", "vendor": "schneider", "count": 1, "zone": "bess_control",
             "name": "BESS_String_Protection_P1",
             "protocols": ["modbus_tcp", "iec61850"],
             "fingerprint_model": "P1F30",
             "cve_ids": ["CVE-2022-37300", "CVE-2022-37301"],
             "role": "BESS String Protection"},

            # ABB RED615 - Microgrid Tie-Line Differential
            {"type": "protection_relay", "vendor": "abb", "count": 1, "zone": "poi_protection",
             "name": "Microgrid_TieLine_Differential_RED615",
             "protocols": ["modbus_tcp", "dnp3", "iec61850"],
             "fingerprint_model": "RED615",
             "cve_ids": ["CVE-2021-22276"],
             "role": "Microgrid Tie-Line Differential"},

            # Schneider PowerLogic ION9000 - Revenue Meter at POI
            {"type": "power_meter", "vendor": "schneider", "count": 1, "zone": "poi_protection",
             "name": "POI_Revenue_Meter_ION9000",
             "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "ION9000",
             "role": "Revenue Meter at POI"},
        ],
        "flows": [
            # Microgrid controller polling inverter PLCs (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["microgrid_control"], "target_zones": ["inverter_field"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Microgrid controller polling BESS controllers (250ms - fast)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["microgrid_control"], "target_zones": ["bess_control"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # Microgrid controller polling POI relays (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["protection_relay"],
             "source_zones": ["microgrid_control"], "target_zones": ["poi_protection"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Central inverter PLC polling string PLCs (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["inverter_field"], "target_zones": ["inverter_field"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # BESS master polling rack controllers (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source_types": ["plc"], "target_types": ["plc"],
             "source_zones": ["bess_control"], "target_zones": ["bess_control"],
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # BESS master polling power converter (250ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source_types": ["plc"], "target_types": ["drive"],
             "source_zones": ["bess_control"], "target_zones": ["bess_control"],
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # RTAC polling microgrid controller (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["rtu"], "target_types": ["plc"],
             "source_zones": ["microgrid_control"], "target_zones": ["microgrid_control"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Historian collecting from all controllers (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["plc"],
             "source_zones": ["microgrid_control"],
             "target_zones": ["inverter_field", "bess_control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # HMI polling microgrid controller (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["microgrid_control"], "target_zones": ["microgrid_control"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # Microgrid controller polling revenue meters (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["plc"], "target_types": ["power_meter"],
             "source_zones": ["microgrid_control"],
             "target_zones": ["poi_protection", "environmental"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Microgrid controller polling weather RTUs (30s - slow)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["plc"], "target_types": ["rtu"],
             "source_zones": ["microgrid_control"], "target_zones": ["environmental"],
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # Microgrid network management — remote gateway acts as NMS
            # proxy and SNMP-polls every switch in the site for Cyber
            # Vision discovery (covers core, inverter-field, BESS, WAN).
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["remote_gateway"], "target_types": ["switch"],
             "source_zones": ["microgrid_control"],
             "target_zones": ["microgrid_control", "inverter_field",
                              "bess_control", "poi_protection",
                              "environmental", "wan"]},

            # WAN RTU polling RTAC (2500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2500,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["wan"], "target_zones": ["microgrid_control"],
             "jitter_ms": 500, "jitter_type": "exponential"},

            # Remote gateway polling controller (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["remote_gateway"], "target_types": ["plc"],
             "source_zones": ["microgrid_control"], "target_zones": ["microgrid_control"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Microgrid controller polling environmental I/O (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["plc"], "target_types": ["io_module"],
             "source_zones": ["microgrid_control"], "target_zones": ["environmental"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # BESS local panel polling rack controllers (1000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["hmi"], "target_types": ["plc"],
             "source_zones": ["bess_control"], "target_zones": ["bess_control"],
             "jitter_ms": 100, "jitter_type": "uniform"},

            # WAN switch monitoring is bundled into the
            # remote_gateway → switch SNMP coverage flow above.

            # IEC 61850 GOOSE/MMS between Easergy P1 (BESS) and ABB RED615
            # (POI tie-line) — cross-bay coordination for islanding events
            {"protocol": "iec61850", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["bess_control"], "target_zones": ["poi_protection"],
             "jitter_ms": 1, "jitter_type": "gaussian",
             "config": {"mode": "goose"}},

            # IEC-104 northbound from POI T300 RTU to utility WAN RTU (1000ms)
            {"protocol": "iec104", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["poi_protection"], "target_zones": ["wan"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
        ],
        "zones": [
            {"id": "microgrid_control", "name": "Microgrid Control Network", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "inverter_field", "name": "Inverter String Network", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "bess_control", "name": "Battery Storage Control", "level": 2,
             "subnet_offset": 2, "vlan": 120, "security_level": "high"},
            {"id": "poi_protection", "name": "Point of Interconnection", "level": 1,
             "subnet_offset": 3, "vlan": 131, "security_level": "high"},
            {"id": "environmental", "name": "Environmental Monitoring", "level": 1,
             "subnet_offset": 4, "vlan": 140, "security_level": "standard"},
            {"id": "wan", "name": "WAN/Utility Backhaul", "level": 4,
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
            "timing": ["delayed_response", "inverter_dropout", "polling_gap"],
            "protocol": ["modbus_exception", "timeout"],
            "sequence": ["out_of_order", "duplicate"],
            "payload": ["irradiance_spike", "battery_soc_upset", "frequency_deviation"],
            "network": ["wan_latency_spike"],
            "security": ["unauthorized_islanding_command", "bess_setpoint_injection"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["modbus_write_scan", "bess_setpoint_attack"],
            "enable_recon": True,
            "target_device_types": ["plc", "protection_relay"],
        },
        "conduits": [
            # L3 (microgrid_control) <-> L2 (inverter_field): Microgrid to inverter PLCs
            {"id": "microgrid_to_inverter", "name": "Microgrid Control \u2194 Inverter Field",
             "source_zone": "microgrid_control", "target_zone": "inverter_field",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "dnp3", "iec61850", "snmp"],
             "security_level": "high",
             "description": "Microgrid controller and historian polling inverter string and central PLCs plus Easergy P3 feeder protection"},
            # L3 (microgrid_control) <-> L2 (bess_control): Microgrid to BESS
            {"id": "microgrid_to_bess", "name": "Microgrid Control \u2194 BESS",
             "source_zone": "microgrid_control", "target_zone": "bess_control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "snmp"],
             "security_level": "high",
             "description": "Microgrid controller and historian polling BESS rack controllers and master controller"},
            # L3 (microgrid_control) <-> L1 (poi_protection): Microgrid to POI
            {"id": "microgrid_to_poi", "name": "Microgrid Control \u2194 POI Protection",
             "source_zone": "microgrid_control", "target_zone": "poi_protection",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp", "dnp3", "iec61850", "ethernet_ip", "snmp"],
             "security_level": "high",
             "description": "Microgrid controller polling POI protection relays, T300 POI RTU, RED615 tie-line differential, and ION9000 revenue meter"},
            # L3 (microgrid_control) <-> L1 (environmental): Microgrid to environmental monitoring
            {"id": "microgrid_to_environmental", "name": "Microgrid Control \u2194 Environmental",
             "source_zone": "microgrid_control", "target_zone": "environmental",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "standard",
             "description": "Microgrid controller polling weather station RTUs, power meters, and environmental I/O"},
            # L4 (wan) <-> L3 (microgrid_control): WAN to microgrid control
            {"id": "wan_to_microgrid", "name": "WAN \u2194 Microgrid Control",
             "source_zone": "wan", "target_zone": "microgrid_control",
             "direction": "bidirectional",
             "allowed_protocols": ["modbus_tcp"],
             "security_level": "critical",
             "description": "Utility WAN RTU polling plant SCADA gateway RTAC for grid coordination"},
            # L2 (bess_control) <-> L1 (poi_protection): BESS protection to POI
            {"id": "bess_to_poi", "name": "BESS Control \u2194 POI Protection",
             "source_zone": "bess_control", "target_zone": "poi_protection",
             "direction": "bidirectional",
             "allowed_protocols": ["iec61850", "modbus_tcp"],
             "security_level": "high",
             "description": "Easergy P1 BESS string protection coordinating GOOSE/MMS with ABB RED615 tie-line differential for islanding events"},
            # L4 (wan) <-> L1 (poi_protection): WAN backhaul from POI RTU
            {"id": "wan_to_poi", "name": "WAN \u2194 POI Protection",
             "source_zone": "wan", "target_zone": "poi_protection",
             "direction": "bidirectional",
             "allowed_protocols": ["iec104", "dnp3", "modbus_tcp"],
             "security_level": "critical",
             "description": "Utility WAN RTU receiving IEC-104 northbound from Easergy T300 POI RTU"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    # TEMPLATE 5: WAMS / PDC PHASOR NETWORK (NEW) \u2014 4 substations \u00d7 {2x SEL-411L PMU, 1x SEL-787, 1x SEL-3555 PDC, 1x ABB REL670, 1x Cisco IE-3300} + EMS Super-PDC + Corp IT
    "wams_pdc_architecture": {
        "name": "WAMS / PDC Phasor Network",
        "description": "Wide-Area Measurement System: PMUs across 4 substations stream IEEE "
                       "C37.118 synchrophasor data at 60 fps to two redundant regional Phasor "
                       "Data Concentrators, which aggregate and forward to a Super-PDC at the "
                       "EMS. Demonstrates real-time WAMS topology used for state estimation, "
                       "oscillation detection, and remedial action schemes (RAS).",
        "vertical": "energy_power",
        "phase_preset": "with_maintenance",
        "recommended_attack_playbooks": [
            {"playbook_id": "industroyer2_like", "relevance": "critical", "rationale": "Direct match for INDUSTROYER2: IEC-104 + IEC-61850 command injection across WAMS topology"},
            {"playbook_id": "volt_typhoon_like", "relevance": "high", "rationale": "WAMS is a documented Volt Typhoon pre-positioning target per 2024 CISA advisory"},
            {"playbook_id": "havex_like", "relevance": "medium", "rationale": "Utility-sector ICS reconnaissance and credential harvesting"},
        ],
        "recommended_traffic_schedule": "industrial_24h",
        "process_sim": {
            "template": "energy_power",
            "description": "WAMS-monitored grid with synchrophasor angles, voltages, frequencies across 4 substations",
            "key_variables": ["active_power", "grid_frequency", "generator_voltage", "transformer_loading", "exhaust_temp"],
            "available_faults": ["governor_failure", "transformer_overload", "grid_frequency_deviation"],
        },
        "devices": [
            # --- SUBSTATION A (Level 2) - 6 devices ---
            {"type": "protection_relay", "vendor": "sel", "count": 2, "zone": "substation_a",
             "name_pattern": "SubA_PMU_SEL411L_{n:02d}",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-411L",
             "cve_ids": [],
             "role": "Line Differential PMU"},
            {"type": "protection_relay", "vendor": "sel", "count": 1, "zone": "substation_a",
             "name": "SubA_Xfmr_PMU_SEL787",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-787",
             "cve_ids": [],
             "role": "Transformer Differential + PMU"},
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "substation_a",
             "name": "SubA_PDC_SEL3555",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],
             "fingerprint_model": "SEL-3555",
             "role": "Substation Phasor Data Concentrator"},
            {"type": "protection_relay", "vendor": "abb", "count": 1, "zone": "substation_a",
             "name": "SubA_LineDistance_Backup_REL670",
             "protocols": ["modbus_tcp", "dnp3", "iec61850"],
             "fingerprint_model": "REL670",
             "role": "Line Distance Backup Protection"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "substation_a",
             "name": "SubA_Network_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Substation Network Switch"},

            # --- SUBSTATION B (Level 2) - 6 devices ---
            {"type": "protection_relay", "vendor": "sel", "count": 2, "zone": "substation_b",
             "name_pattern": "SubB_PMU_SEL411L_{n:02d}",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-411L",
             "cve_ids": [],
             "role": "Line Differential PMU"},
            {"type": "protection_relay", "vendor": "sel", "count": 1, "zone": "substation_b",
             "name": "SubB_Xfmr_PMU_SEL787",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-787",
             "cve_ids": [],
             "role": "Transformer Differential + PMU"},
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "substation_b",
             "name": "SubB_PDC_SEL3555",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],
             "fingerprint_model": "SEL-3555",
             "role": "Substation Phasor Data Concentrator"},
            {"type": "protection_relay", "vendor": "abb", "count": 1, "zone": "substation_b",
             "name": "SubB_LineDistance_Backup_REL670",
             "protocols": ["modbus_tcp", "dnp3", "iec61850"],
             "fingerprint_model": "REL670",
             "role": "Line Distance Backup Protection"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "substation_b",
             "name": "SubB_Network_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Substation Network Switch"},

            # --- SUBSTATION C (Level 2) - 6 devices ---
            {"type": "protection_relay", "vendor": "sel", "count": 2, "zone": "substation_c",
             "name_pattern": "SubC_PMU_SEL411L_{n:02d}",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-411L",
             "cve_ids": [],
             "role": "Line Differential PMU"},
            {"type": "protection_relay", "vendor": "sel", "count": 1, "zone": "substation_c",
             "name": "SubC_Xfmr_PMU_SEL787",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-787",
             "cve_ids": [],
             "role": "Transformer Differential + PMU"},
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "substation_c",
             "name": "SubC_PDC_SEL3555",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],
             "fingerprint_model": "SEL-3555",
             "role": "Substation Phasor Data Concentrator"},
            {"type": "protection_relay", "vendor": "abb", "count": 1, "zone": "substation_c",
             "name": "SubC_LineDistance_Backup_REL670",
             "protocols": ["modbus_tcp", "dnp3", "iec61850"],
             "fingerprint_model": "REL670",
             "role": "Line Distance Backup Protection"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "substation_c",
             "name": "SubC_Network_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Substation Network Switch"},

            # --- SUBSTATION D (Level 2) - 6 devices ---
            {"type": "protection_relay", "vendor": "sel", "count": 2, "zone": "substation_d",
             "name_pattern": "SubD_PMU_SEL411L_{n:02d}",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-411L",
             "cve_ids": [],
             "role": "Line Differential PMU"},
            {"type": "protection_relay", "vendor": "sel", "count": 1, "zone": "substation_d",
             "name": "SubD_Xfmr_PMU_SEL787",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "c37118"],
             "fingerprint_model": "SEL-787",
             "cve_ids": [],
             "role": "Transformer Differential + PMU"},
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "substation_d",
             "name": "SubD_PDC_SEL3555",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],
             "fingerprint_model": "SEL-3555",
             "role": "Substation Phasor Data Concentrator"},
            {"type": "protection_relay", "vendor": "abb", "count": 1, "zone": "substation_d",
             "name": "SubD_LineDistance_Backup_REL670",
             "protocols": ["modbus_tcp", "dnp3", "iec61850"],
             "fingerprint_model": "REL670",
             "role": "Line Distance Backup Protection"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "substation_d",
             "name": "SubD_Network_Switch",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-3300-8T2S",
             "role": "Substation Network Switch"},

            # --- EMS CONTROL CENTER (Level 4) - 4 devices: Super-PDC, state estimator, historian, core switch ---
            {"type": "rtu", "vendor": "sel", "count": 1, "zone": "ems_control_center",
             "name": "EMS_Super_PDC_SEL3555",
             "protocols": ["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],
             "fingerprint_model": "SEL-3555",
             "role": "Super Phasor Data Concentrator"},
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "ems_control_center",
             "name": "EMS_State_Estimator_Workstation",
             "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2019",
             "role": "State Estimator Workstation"},
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "ems_control_center",
             "name": "EMS_WAMS_Historian",
             "protocols": ["modbus_tcp"],
             "fingerprint_model": "Proficy Historian",
             "cve_ids": ["CVE-2022-46660"],
             "role": "WAMS Historian"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "ems_control_center",
             "name": "EMS_Core_Switch_IE4000",
             "protocols": ["snmp"],
             "fingerprint_model": "IE-4000-8GT4G-E",
             "role": "EMS Core Switch"},

            # --- CORPORATE IT (Level 5) - 3 devices: Jump + WSUS + AD (AD modeled as Jump Server 2019) ---
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "corporate_it",
             "name": "Corp_Jump_Server",
             "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2019",
             "role": "Corporate Jump Server",
             "external_comms": True},
            {"type": "server", "vendor": "microsoft", "count": 1, "zone": "corporate_it",
             "name": "Corp_WSUS_Server",
             "protocols": ["snmp"],
             "fingerprint_model": "WSUS Server 2022",
             "role": "WSUS Patch Server"},
            {"type": "server", "vendor": "microsoft", "count": 1, "zone": "corporate_it",
             "name": "Corp_AD_Domain_Controller",
             "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2019",
             "role": "Active Directory Domain Controller"},
        ],
        "flows": [
            # Per-substation: PMUs \u2192 local SEL-3555 PDC via C37.118 (16 ms = 60 fps)
            {"protocol": "c37118", "pattern": "cyclic_data", "interval_ms": 16,
             "source_types": ["protection_relay"], "target_types": ["rtu"],
             "source_zones": ["substation_a"], "target_zones": ["substation_a"],
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "c37118", "pattern": "cyclic_data", "interval_ms": 16,
             "source_types": ["protection_relay"], "target_types": ["rtu"],
             "source_zones": ["substation_b"], "target_zones": ["substation_b"],
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "c37118", "pattern": "cyclic_data", "interval_ms": 16,
             "source_types": ["protection_relay"], "target_types": ["rtu"],
             "source_zones": ["substation_c"], "target_zones": ["substation_c"],
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "c37118", "pattern": "cyclic_data", "interval_ms": 16,
             "source_types": ["protection_relay"], "target_types": ["rtu"],
             "source_zones": ["substation_d"], "target_zones": ["substation_d"],
             "jitter_ms": 2, "jitter_type": "gaussian"},
            # Each substation SEL-3555 \u2192 EMS Super-PDC C37.118 aggregated stream (33 ms)
            {"protocol": "c37118", "pattern": "cyclic_data", "interval_ms": 33,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["substation_a", "substation_b", "substation_c", "substation_d"],
             "target_zones": ["ems_control_center"],
             "jitter_ms": 5, "jitter_type": "gaussian"},
            # IEC-61850 GOOSE bay-to-bay within each substation (4 ms multicast)
            {"protocol": "iec61850", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["substation_a"], "target_zones": ["substation_a"],
             "jitter_ms": 1, "jitter_type": "gaussian", "config": {"mode": "goose"}},
            {"protocol": "iec61850", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["substation_b"], "target_zones": ["substation_b"],
             "jitter_ms": 1, "jitter_type": "gaussian", "config": {"mode": "goose"}},
            {"protocol": "iec61850", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["substation_c"], "target_zones": ["substation_c"],
             "jitter_ms": 1, "jitter_type": "gaussian", "config": {"mode": "goose"}},
            {"protocol": "iec61850", "pattern": "cyclic_io", "interval_ms": 4,
             "source_types": ["protection_relay"], "target_types": ["protection_relay"],
             "source_zones": ["substation_d"], "target_zones": ["substation_d"],
             "jitter_ms": 1, "jitter_type": "gaussian", "config": {"mode": "goose"}},

            # IEC-104 from substation SEL-3555 \u2192 EMS Super-PDC for command/control (1000ms)
            {"protocol": "iec104", "pattern": "poll", "interval_ms": 1000,
             "source_types": ["rtu"], "target_types": ["rtu"],
             "source_zones": ["substation_a", "substation_b", "substation_c", "substation_d"],
             "target_zones": ["ems_control_center"],
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # DNP3 from REL670 \u2192 SEL-3555 within each substation (status, 2000ms)
            {"protocol": "dnp3", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["rtu"], "target_types": ["protection_relay"],
             "source_zones": ["substation_a", "substation_b", "substation_c", "substation_d"],
             "target_zones": ["substation_a", "substation_b", "substation_c", "substation_d"],
             "jitter_ms": 200, "jitter_type": "gaussian"},

            # Historian collecting from Super-PDC (5000ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["historian"], "target_types": ["rtu"],
             "source_zones": ["ems_control_center"], "target_zones": ["ems_control_center"],
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # EMS SNMP monitoring of all switches across substations (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["rtu"], "target_types": ["switch"],
             "source_zones": ["ems_control_center"],
             "target_zones": ["substation_a", "substation_b", "substation_c",
                              "substation_d", "ems_control_center"]},
        ],
        "zones": [
            {"id": "substation_a", "name": "Substation A", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "substation_b", "name": "Substation B", "level": 2,
             "subnet_offset": 2, "vlan": 120, "security_level": "high"},
            {"id": "substation_c", "name": "Substation C", "level": 2,
             "subnet_offset": 3, "vlan": 130, "security_level": "high"},
            {"id": "substation_d", "name": "Substation D", "level": 2,
             "subnet_offset": 4, "vlan": 140, "security_level": "high"},
            {"id": "ems_control_center", "name": "EMS Control Center", "level": 4,
             "subnet_offset": 0, "vlan": 100, "security_level": "critical"},
            {"id": "corporate_it", "name": "Corporate IT", "level": 5,
             "subnet_offset": 50, "vlan": 200, "security_level": "external",
             "is_external": True},
        ],
        "cloud_services": [
            {
                "provider": "talk2m",
                "region": "us-east",
                "device_types": ["jump_server"],
                "heartbeat_interval_ms": 30000,
            },
        ],
        "suggested_anomalies": {
            "timing": ["pmu_stream_jitter", "pdc_aggregation_delay", "polling_gap"],
            "protocol": ["c37118_cfg_mismatch", "iec104_timeout"],
            "sequence": ["pmu_frame_loss", "out_of_order_phasor"],
            "payload": ["frequency_deviation", "voltage_angle_excursion", "oscillation_event"],
            "network": ["wan_latency_spike", "pdc_failover"],
            "security": ["unauthorized_relay_setting_change", "c37118_cfg_injection"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_c2": True,
            "enable_exfil": False,
            "enable_exploits": True,
            "exploit_patterns": ["iec104_command_injection", "relay_setting_change"],
            "enable_recon": True,
            "target_device_types": ["protection_relay", "rtu"],
        },
        "conduits": [
            # Each substation \u2192 EMS Super-PDC (L2 \u2194 L4): C37.118 + IEC-104
            {"id": "ems_to_sub_a_wams", "name": "EMS Control Center \u2194 Substation A (WAMS)",
             "source_zone": "ems_control_center", "target_zone": "substation_a", "direction": "bidirectional",
             "allowed_protocols": ["c37118", "iec104", "snmp", "modbus_tcp"], "security_level": "critical",
             "description": "Super-PDC aggregating C37.118 + IEC-104 to/from Substation A"},
            {"id": "ems_to_sub_b_wams", "name": "EMS Control Center \u2194 Substation B (WAMS)",
             "source_zone": "ems_control_center", "target_zone": "substation_b", "direction": "bidirectional",
             "allowed_protocols": ["c37118", "iec104", "snmp", "modbus_tcp"], "security_level": "critical",
             "description": "Super-PDC aggregating C37.118 + IEC-104 to/from Substation B"},
            {"id": "ems_to_sub_c_wams", "name": "EMS Control Center \u2194 Substation C (WAMS)",
             "source_zone": "ems_control_center", "target_zone": "substation_c", "direction": "bidirectional",
             "allowed_protocols": ["c37118", "iec104", "snmp", "modbus_tcp"], "security_level": "critical",
             "description": "Super-PDC aggregating C37.118 + IEC-104 to/from Substation C"},
            {"id": "ems_to_sub_d_wams", "name": "EMS Control Center \u2194 Substation D (WAMS)",
             "source_zone": "ems_control_center", "target_zone": "substation_d", "direction": "bidirectional",
             "allowed_protocols": ["c37118", "iec104", "snmp", "modbus_tcp"], "security_level": "critical",
             "description": "Super-PDC aggregating C37.118 + IEC-104 to/from Substation D"},
            # Corporate IT \u2194 EMS (L5 \u2194 L4): jump-server based admin access
            {"id": "corp_to_ems", "name": "Corporate IT \u2194 EMS Control Center",
             "source_zone": "corporate_it", "target_zone": "ems_control_center", "direction": "bidirectional",
             "allowed_protocols": ["snmp"], "security_level": "critical",
             "description": "Corporate jump server providing administrative access to EMS Super-PDC and state estimator"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
    },
}
