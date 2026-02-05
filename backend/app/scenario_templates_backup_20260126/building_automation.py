"""Building Automation / BMS scenario templates.

Primary Vendors: Johnson Controls, Honeywell/Tridium, Trane, Carrier, Schneider Electric
Protocol Focus: BACnet/IP (primary), SNMP (secondary), Modbus TCP (equipment)

Scenarios:
- Commercial Building: Multi-floor office with central HVAC, VAV boxes, lighting
- University Campus: Multiple buildings, central plant, energy management
- Data Center: Precision cooling, power monitoring, environmental sensors

CVE Vulnerability mapping:
- Building controllers: CVE-2023-4804 (Johnson Controls), CVE-2022-30312 (Tridium)
- HVAC controllers: CVE-2015-2867 (Trane), CVE-2021-42534 (Trane)
- BMS servers: CVE-2021-35963 (Automated Logic), CVE-2020-7002 (Carrier)
"""

from typing import Any


BUILDING_AUTOMATION_TEMPLATES: dict[str, dict[str, Any]] = {
    "commercial_building": {
        "name": "Commercial Office Building",
        "description": "Multi-floor commercial office building (10 floors) with central "
                       "HVAC system, VAV boxes for zone control, automated lighting, "
                       "access control, and building automation server. Uses BACnet/IP "
                       "for building automation communication.",
        "vertical": "building_automation",
        "devices": [
            # Building Automation Server (Metasys)
            {"type": "bac", "vendor": "johnson_controls", "count": 1, "zone": "control",
             "name_pattern": "BAC-{n:03d}", "protocols": ["bacnet", "snmp"],
             "fingerprint_model": "NAE55",
             "role": "Building Automation Controller",
             "cve_ids": ["CVE-2023-4804"]},

            # Air Handling Units (Trane)
            # Using Tracer SC+ to match CVE affected_models for Cyber Vision detection
            {"type": "ahu_controller", "vendor": "trane", "count": 4, "zone": "hvac",
             "name_pattern": "AHU-{n:03d}", "protocols": ["bacnet"],
             "fingerprint_model": "Tracer SC+",
             "role": "Air Handling Unit Controller",
             "cve_ids": ["CVE-2021-42534"]},

            # Variable Air Volume Controllers (Distech)
            # Using EC-BOS-8 to match CVE affected_models for Cyber Vision detection
            {"type": "vav_controller", "vendor": "Distech Controls", "count": 40, "zone": "field",
             "name_pattern": "VAV-{floor:02d}-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "EC-BOS-8",
             "role": "VAV Zone Controller",
             "cve_ids": ["CVE-2020-9049"]},

            # Chiller Plant (Trane - hardcoded credentials vuln)
            # Using XL950 to match CVE affected_models for Cyber Vision detection
            {"type": "chiller_controller", "vendor": "Trane", "count": 2, "zone": "mechanical",
             "name_pattern": "CHW-{n:03d}", "protocols": ["bacnet"],
             "fingerprint_model": "XL950",
             "cve_ids": ["CVE-2015-2867"],
             "role": "Chiller Controller"},

            # Boiler Plant (Honeywell)
            {"type": "boiler_controller", "vendor": "honeywell", "count": 2, "zone": "mechanical",
             "name_pattern": "HW-{n:03d}", "protocols": ["bacnet"],
             "fingerprint_model": "XL Web",
             "role": "Boiler Controller"},

            # Lighting Controllers (Johnson Controls)
            {"type": "lighting_controller", "vendor": "johnson_controls", "count": 10, "zone": "field",
             "name_pattern": "LTG-{floor:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "FEC26",
             "role": "Lighting Controller"},

            # Energy Meters (Schneider)
            {"type": "energy_meter", "vendor": "schneider", "count": 5, "zone": "field",
             "name_pattern": "PWR-{n:03d}", "protocols": ["modbus_tcp", "bacnet"],
             "fingerprint_model": "PM8000",
             "role": "Power Meter"},

            # Access Controllers (Honeywell)
            {"type": "access_controller", "vendor": "honeywell", "count": 12, "zone": "security",
             "name_pattern": "ACC-{floor:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "JACE 8000",
             "role": "Access Control Panel",
             "cve_ids": ["CVE-2022-30312"]},
        ],
        "flows": [
            # BAC polling AHU controllers (15s interval)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 15000,
             "source_types": ["bac"], "target_types": ["ahu_controller"],
             "jitter_ms": 1000, "jitter_type": "uniform"},
            # BAC polling VAV controllers (30s interval)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["bac"], "target_types": ["vav_controller"],
             "jitter_ms": 2000, "jitter_type": "uniform"},
            # BAC polling chillers (10s interval)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["bac"], "target_types": ["chiller_controller"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # BAC polling boilers (10s interval)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["bac"], "target_types": ["boiler_controller"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # BAC polling lighting (60s interval)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["bac"], "target_types": ["lighting_controller"],
             "jitter_ms": 3000, "jitter_type": "uniform"},
            # BAC polling energy meters via Modbus (5s interval)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["bac"], "target_types": ["energy_meter"],
             "jitter_ms": 250, "jitter_type": "gaussian"},
            # BAC polling access controllers (30s interval)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["bac"], "target_types": ["access_controller"],
             "jitter_ms": 2000, "jitter_type": "uniform"},
        ],
        "zones": [
            {"id": "control", "name": "BMS Control Room", "level": 4,
             "subnet_offset": 0, "vlan": 100},
            {"id": "hvac", "name": "HVAC Zone", "level": 3,
             "subnet_offset": 1, "vlan": 101},
            {"id": "mechanical", "name": "Mechanical Room", "level": 3,
             "subnet_offset": 2, "vlan": 102},
            {"id": "field", "name": "Field Devices", "level": 2,
             "subnet_offset": 3, "vlan": 103},
            {"id": "security", "name": "Security Zone", "level": 3,
             "subnet_offset": 4, "vlan": 104},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "timeout"],
            "protocol": ["bacnet_error"],
            "sequence": [],
            "payload": ["temperature_spike", "setpoint_change"],
            "network": ["packet_loss"],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "bacnet", "flow_type": "polling", "priority": "high",
             "description": "Learn BACnet ReadProperty polling patterns"},
            {"protocol": "bacnet", "flow_type": "discovery", "priority": "high",
             "description": "Capture BACnet Who-Is/I-Am discovery"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },

    "university_campus": {
        "name": "University Campus",
        "description": "Large university campus with 8 buildings, central chilled water "
                       "plant, hot water plant, campus-wide energy management, and "
                       "integrated access control. Uses BACnet/IP with distributed "
                       "building controllers.",
        "vertical": "building_automation",
        "devices": [
            # Campus BMS Server (Automated Logic WebCTRL)
            {"type": "bms_server", "vendor": "automated_logic", "count": 1, "zone": "noc",
             "name_pattern": "WEBCTRL-{n:03d}", "protocols": ["bacnet", "snmp"],
             "fingerprint_model": "Server",
             "role": "Campus BMS Server",
             "cve_ids": ["CVE-2021-35963"]},

            # Building Automation Controllers (Johnson Controls)
            {"type": "bac", "vendor": "johnson_controls", "count": 8, "zone": "buildings",
             "name_pattern": "NAE-BLD{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "NAE55",
             "role": "Building Controller",
             "cve_ids": ["CVE-2023-4804"]},

            # AHU Controllers per building (Delta Controls - RCE vuln)
            # Using enteliBUS Manager to match CVE affected_models for Cyber Vision detection
            {"type": "ahu_controller", "vendor": "delta_controls", "count": 24, "zone": "buildings",
             "name_pattern": "AHU-B{building:02d}-{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "enteliBUS Manager",
             "cve_ids": ["CVE-2019-9569"],
             "role": "Air Handling Unit"},

            # VAV Controllers distributed across campus
            # Using EC-BOS-8 to match CVE affected_models for Cyber Vision detection
            {"type": "vav_controller", "vendor": "Distech Controls", "count": 200, "zone": "field",
             "name_pattern": "VAV-B{building:02d}-{floor:02d}{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "EC-BOS-8",
             "role": "VAV Zone Controller",
             "cve_ids": ["CVE-2020-9049"]},

            # Central Plant Chillers (Carrier)
            # Using i-Vu Pro to match CVE affected_models for Cyber Vision detection
            {"type": "chiller_controller", "vendor": "carrier", "count": 4, "zone": "plant",
             "name_pattern": "CH-{n:03d}", "protocols": ["bacnet"],
             "fingerprint_model": "i-Vu Pro",
             "role": "Chiller Controller",
             "cve_ids": ["CVE-2020-7002"]},

            # Central Plant Boilers (Siemens - Desigo privilege escalation)
            # Using Desigo CC to match CVE affected_models for Cyber Vision detection
            {"type": "boiler_controller", "vendor": "siemens", "count": 4, "zone": "plant",
             "name_pattern": "BLR-{n:03d}", "protocols": ["bacnet"],
             "fingerprint_model": "Desigo CC",
             "cve_ids": ["CVE-2022-31465"],
             "role": "Boiler Controller"},

            # Energy Meters campus-wide
            {"type": "energy_meter", "vendor": "schneider", "count": 20, "zone": "field",
             "name_pattern": "PWR-B{building:02d}-{n:02d}", "protocols": ["modbus_tcp"],
             "fingerprint_model": "PM8000",
             "role": "Building Power Meter"},

            # Niagara JACE Controllers for legacy integration
            {"type": "niagara_jace", "vendor": "honeywell", "count": 8, "zone": "buildings",
             "name_pattern": "JACE-B{n:02d}", "protocols": ["bacnet"],
             "fingerprint_model": "JACE 8000",
             "role": "Integration Controller",
             "cve_ids": ["CVE-2022-30312"]},
        ],
        "flows": [
            # WebCTRL polling building controllers (30s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["bms_server"], "target_types": ["bac"],
             "jitter_ms": 2000, "jitter_type": "uniform"},
            # Building controllers polling AHUs (15s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 15000,
             "source_types": ["bac"], "target_types": ["ahu_controller"],
             "jitter_ms": 1000, "jitter_type": "uniform"},
            # Building controllers polling VAVs (45s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 45000,
             "source_types": ["bac"], "target_types": ["vav_controller"],
             "jitter_ms": 3000, "jitter_type": "uniform"},
            # WebCTRL polling central plant (10s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["bms_server"], "target_types": ["chiller_controller", "boiler_controller"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # Building controllers polling energy meters (60s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 60000,
             "source_types": ["bac"], "target_types": ["energy_meter"],
             "jitter_ms": 5000, "jitter_type": "uniform"},
            # WebCTRL polling JACEs (30s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["bms_server"], "target_types": ["niagara_jace"],
             "jitter_ms": 2000, "jitter_type": "uniform"},
        ],
        "zones": [
            {"id": "noc", "name": "Campus NOC", "level": 4,
             "subnet_offset": 0, "vlan": 200},
            {"id": "plant", "name": "Central Plant", "level": 3,
             "subnet_offset": 1, "vlan": 201},
            {"id": "buildings", "name": "Building Controllers", "level": 3,
             "subnet_offset": 2, "vlan": 202},
            {"id": "field", "name": "Field Devices", "level": 2,
             "subnet_offset": 3, "vlan": 203},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "burst_traffic"],
            "protocol": ["bacnet_error"],
            "sequence": [],
            "payload": ["temperature_spike"],
            "network": ["packet_loss", "congestion"],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "bacnet", "flow_type": "polling", "priority": "high",
             "description": "Learn BACnet ReadPropertyMultiple patterns"},
            {"protocol": "bacnet", "flow_type": "cov", "priority": "medium",
             "description": "Capture COV subscription notifications"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
    },

    "data_center": {
        "name": "Data Center Facility",
        "description": "Mission-critical data center with precision cooling (CRAC units), "
                       "hot/cold aisle containment, UPS monitoring, power distribution, "
                       "and environmental sensors. Uses BACnet/IP and Modbus for "
                       "equipment monitoring.",
        "vertical": "building_automation",
        "devices": [
            # Data Center BMS (Schneider Andover)
            {"type": "bac", "vendor": "schneider", "count": 2, "zone": "control",
             "name_pattern": "DCIM-{n:03d}", "protocols": ["bacnet", "snmp"],
             "fingerprint_model": "CX9680",
             "role": "Data Center Infrastructure Management",
             "cve_ids": ["CVE-2019-6853"]},

            # CRAC Units (Schneider)
            {"type": "crac_unit", "vendor": "schneider", "count": 12, "zone": "cooling",
             "name_pattern": "CRAC-{row:01d}{n:02d}", "protocols": ["bacnet", "modbus_tcp"],
             "fingerprint_model": "InRow DX",
             "role": "Precision Cooling Unit"},

            # Chiller Plant (Carrier)
            # Using i-Vu Pro to match CVE affected_models for Cyber Vision detection
            {"type": "chiller_controller", "vendor": "carrier", "count": 4, "zone": "plant",
             "name_pattern": "CH-{n:03d}", "protocols": ["bacnet"],
             "fingerprint_model": "i-Vu Pro",
             "role": "Chiller Controller",
             "cve_ids": ["CVE-2020-7002"]},

            # UPS Monitoring (via Modbus)
            {"type": "meter", "vendor": "schneider", "count": 8, "zone": "power",
             "name_pattern": "UPS-{n:03d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Galaxy VM",
             "role": "UPS System"},

            # PDU Monitoring
            {"type": "power_meter", "vendor": "schneider", "count": 48, "zone": "power",
             "name_pattern": "PDU-{row:01d}{rack:02d}", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Rack PDU",
             "role": "Power Distribution Unit"},

            # Environmental Sensors (Carel)
            {"type": "sensor", "vendor": "carel", "count": 60, "zone": "sensors",
             "name_pattern": "ENV-{row:01d}{rack:02d}{pos:01d}", "protocols": ["bacnet"],
             "fingerprint_model": "pCO5+",
             "role": "Temperature/Humidity Sensor"},

            # Building Controllers for support areas (Siemens Desigo vuln)
            # Using Desigo CC to match CVE affected_models for Cyber Vision detection
            {"type": "bac", "vendor": "siemens", "count": 2, "zone": "building",
             "name_pattern": "BMS-{n:03d}", "protocols": ["bacnet"],
             "fingerprint_model": "Desigo CC",
             "cve_ids": ["CVE-2022-31465"],
             "role": "Building Controller"},
        ],
        "flows": [
            # DCIM polling CRAC units (5s - critical)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 5000,
             "source_types": ["bac"], "target_types": ["crac_unit"],
             "jitter_ms": 250, "jitter_type": "gaussian"},
            # DCIM polling chillers (10s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["bac"], "target_types": ["chiller_controller"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # DCIM polling UPS via Modbus (2s - critical)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["bac"], "target_types": ["meter"],
             "jitter_ms": 100, "jitter_type": "gaussian"},
            # DCIM polling PDUs via Modbus (10s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 10000,
             "source_types": ["bac"], "target_types": ["power_meter"],
             "jitter_ms": 500, "jitter_type": "uniform"},
            # DCIM polling environmental sensors (15s)
            {"protocol": "bacnet", "pattern": "poll", "interval_ms": 15000,
             "source_types": ["bac"], "target_types": ["sensor"],
             "jitter_ms": 1000, "jitter_type": "uniform"},
        ],
        "zones": [
            {"id": "control", "name": "DCIM Control Room", "level": 4,
             "subnet_offset": 0, "vlan": 300},
            {"id": "cooling", "name": "Cooling Systems", "level": 3,
             "subnet_offset": 1, "vlan": 301},
            {"id": "plant", "name": "Chiller Plant", "level": 3,
             "subnet_offset": 2, "vlan": 302},
            {"id": "power", "name": "Power Systems", "level": 3,
             "subnet_offset": 3, "vlan": 303},
            {"id": "sensors", "name": "Environmental Sensors", "level": 2,
             "subnet_offset": 4, "vlan": 304},
            {"id": "building", "name": "Building Systems", "level": 2,
             "subnet_offset": 5, "vlan": 305},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "timeout"],
            "protocol": ["bacnet_error", "modbus_exception"],
            "sequence": [],
            "payload": ["temperature_alarm", "power_spike"],
            "network": ["packet_loss"],
            "security": [],
        },
        "pcap_learning_hints": [
            {"protocol": "bacnet", "flow_type": "high_frequency_polling", "priority": "high",
             "description": "Learn critical cooling system polling patterns"},
            {"protocol": "modbus_tcp", "flow_type": "power_monitoring", "priority": "high",
             "description": "Capture UPS and PDU monitoring traffic"},
        ],
        "total_duration_ms": 300000,  # 5 minutes
    },
}


def get_building_automation_template(name: str) -> dict[str, Any] | None:
    """Get a specific building automation template by name.

    Args:
        name: Template name (e.g., "commercial_building")

    Returns:
        Template dictionary or None if not found
    """
    return BUILDING_AUTOMATION_TEMPLATES.get(name)


def list_building_automation_templates() -> list[str]:
    """List all available building automation template names.

    Returns:
        List of template names
    """
    return list(BUILDING_AUTOMATION_TEMPLATES.keys())
