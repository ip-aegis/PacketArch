"""Vendor OUI (Organizationally Unique Identifier) database for realistic MAC generation.

IMPORTANT: OUI-based vendor detection is a FALLBACK method.
Many OT and building automation devices use embedded NICs from other manufacturers
(e.g., Cisco, Intel, Microchip). A Johnson Controls NAE55 might have a Cisco NIC.

For reliable vendor identification, use protocol-based detection:
- SNMP: sysDescr, sysObjectID (enterprise OID)
- BACnet: vendor_id
- Modbus: FC43 device identification
- EtherNet/IP: vendor_id in CIP identity

OUIs in this file are verified against the IEEE OUI registry where possible.
To verify an OUI: https://maclookup.app/ or https://macaddress.io/
"""

import random
from typing import Optional


# OUI database: Vendor name -> list of OUI prefixes (first 3 bytes of MAC)
# Based on IEEE OUI registry for major OT/industrial automation vendors
#
# NOTE: Empty lists indicate vendors that typically use generic NICs.
# These are kept for device_type mapping but generate default OUIs.
VENDOR_OUIS: dict[str, list[str]] = {
    # Major PLC/Industrial Automation Vendors
    "siemens": [
        "00:0E:8C",  # Siemens AG
        "00:1B:1B",  # Siemens Building Technologies
        "00:1C:06",  # Siemens AG A&D
        "00:0D:6B",  # Siemens AG Industrial Comm
        "00:1F:F8",  # Siemens AG Automation
        "74:DA:EA",  # Siemens Industrial
        "64:6E:97",  # Siemens AG
        "AC:64:17",  # Siemens AG (Amberg, IEEE 2017)
    ],
    "rockwell": [
        "00:00:BC",  # Allen-Bradley (legacy)
        "00:1D:9C",  # Rockwell Automation
        "08:61:95",  # Rockwell Automation
        "5C:88:16",  # Rockwell Automation
        "E4:90:69",  # Rockwell Automation
        "F4:54:33",  # Rockwell Automation
    ],
    "schneider": [
        "00:00:54",  # Schneider Electric (legacy Modicon)
        "00:80:F4",  # Schneider Electric
        # "00:04:A3" REMOVED - Actually Microchip Technology per IEEE registry
        # "00:1C:C4" REMOVED - Actually Hewlett Packard per IEEE registry
        "00:04:74",  # Schneider Electric
        "64:3A:EA",  # Schneider Electric
    ],
    "abb": [
        "00:21:99",  # ABB Stotz Kontakt
        "00:24:2B",  # ABB Inc
        "00:1F:ED",  # ABB AS
        "00:C0:53",  # ABB Power Automation
        "C4:93:00",  # ABB
    ],
    "emerson": [
        # NOTE: Emerson/Fisher-Rosemount often uses embedded NICs from other vendors.
        # Protocol-based identification (Modbus FC43, EtherNet/IP identity) is more reliable.
        "00:0D:3A",  # Emerson Network Power (verified IEEE)
        # "00:A0:F8" REMOVED - Actually Zebra/Symbol Technologies per IEEE
        # "00:50:43" REMOVED - Actually Marvell Semiconductor per IEEE
        # "00:60:35" REMOVED - Actually Dallas Semiconductor per IEEE
    ],
    "honeywell": [
        "00:40:84",  # Honeywell Inc (IEEE MA-L, 2000)
        "00:22:6A",  # Honeywell (IEEE MA-L, 2008)
        "C4:EF:DA",  # Honeywell (IEEE MA-L, 2022)
        "58:FC:C8",  # Honeywell (IEEE MA-L, 2023)
    ],
    "ge": [
        "00:09:45",  # GE Fanuc Automation
        "00:30:C1",  # GE Healthcare
        "00:50:99",  # GE Industrial Systems
        "00:22:52",  # GE Digital Energy
    ],
    # Protection Relay / Power Grid Vendors
    "sel": [
        "00:30:A7",  # Schweitzer Engineering Laboratories
        "00:1C:73",  # SEL Inc
    ],
    "basler": [
        "00:1E:C9",  # Basler Electric
    ],
    "beckwith": [
        "00:1A:F0",  # Beckwith Electric
    ],
    "phoenix_contact": [
        "00:A0:45",  # Phoenix Contact
        "00:16:9D",  # Phoenix Contact
        "A8:74:1D",  # Phoenix Contact
    ],
    "beckhoff": [
        "00:01:05",  # Beckhoff Automation
    ],
    "wago": [
        "00:30:DE",  # WAGO Kontakttechnik
        "00:03:C6",  # WAGO I/O-SYSTEM
    ],
    "omron": [
        "00:00:74",  # Omron Tateisi Electronics
        "00:04:C7",  # Omron Corporation
        "00:0C:DB",  # Omron Advanced Systems
    ],
    "mitsubishi": [
        "00:00:7E",  # Mitsubishi Electric
        "00:04:0F",  # Mitsubishi Electric
        "00:50:13",  # Meidensha Corporation (Mitsubishi group)
    ],
    "b_and_r": [
        "00:60:65",  # B&R Industrial Automation
        "00:0A:49",  # B&R Industrie-Elektronik
    ],
    "pilz": [
        "00:05:7C",  # Pilz GmbH & Co
    ],
    "sick": [
        "00:0B:2D",  # SICK AG
        "00:06:8C",  # SICK AG
    ],
    "turck": [
        "00:12:4D",  # Turck Inc
    ],
    "ifm": [
        "00:50:18",  # IFM Electronic
    ],
    "endress_hauser": [
        "00:06:69",  # Endress+Hauser
    ],
    "yokogawa": [
        "00:02:48",  # Yokogawa Electric
        "00:A0:78",  # Yokogawa Electric
    ],
    "moxa": [
        "00:90:E8",  # MOXA Technologies
        "00:10:35",  # MOXA Inc
    ],
    "advantech": [
        "00:D0:C9",  # Advantech Co
        "00:20:18",  # Advantech
    ],
    "hms": [
        "00:03:27",  # HMS Industrial Networks
        "00:05:94",  # HMS Industrial Networks
        "00:30:11",  # HMS Industrial Networks
        "00:30:56",  # HMS Industrial Networks
        "9C:B2:06",  # HMS Industrial Networks (newer)
    ],
    "cisco": [
        "00:00:0C",  # Cisco Systems
        "00:1A:A1",  # Cisco Systems
        "00:1B:90",  # Cisco Systems
        "00:24:51",  # Cisco
        "00:25:84",  # Cisco
    ],
    "hirschmann": [
        "00:80:63",  # Hirschmann Automation
        "00:0A:DB",  # Hirschmann
    ],

    # SCADA/HMI Vendors
    "wonderware": [
        "00:0F:34",  # Wonderware (Schneider)
    ],
    "copadata": [
        "00:0C:46",  # Copa-Data
    ],
    # NOTE: Kepware KEPServerEX is software running on host machine, uses host NIC
    "kepware": [],

    # Building Automation / BMS Vendors
    # NOTE: Many building automation devices use embedded NICs from other vendors
    # (Cisco, Intel, Microchip). Protocol-based detection (SNMP, BACnet) is more reliable.
    "johnson_controls": [
        "00:1A:17",  # Johnson Controls
        # "00:16:C7" REMOVED - Actually Cisco Systems per IEEE registry
        "00:23:BE",  # Johnson Controls Systems
    ],
    "tridium": [
        "00:50:62",  # Tridium (Niagara Framework)
    ],
    "trane": [
        "00:0D:AD",  # Trane Technologies
        "00:1C:C0",  # Trane
    ],
    "carrier": [
        "00:0D:AD",  # Carrier Corporation (shared with Trane parent)
        "00:1E:8E",  # Carrier
    ],
    "delta_controls": [
        "00:0B:AB",  # Delta Controls
        "00:0D:9F",  # Delta Controls Inc
    ],
    "distech": [
        "00:1E:C0",  # Distech Controls
        "D0:77:14",  # Distech Controls Inc
    ],
    "carel": [
        "00:0D:5D",  # Carel Industries
        "00:15:F9",  # Carel SpA
    ],
    "automated_logic": [
        "00:14:C1",  # Automated Logic Corporation
        "00:1C:12",  # Automated Logic
    ],
    "kmc_controls": [
        "00:10:E3",  # KMC Controls
    ],
    "alerton": [
        "00:0B:39",  # Alerton Technologies
    ],
    "reliable_controls": [
        "00:19:F5",  # Reliable Controls Corporation
    ],
    "lennox": [
        "00:11:2F",  # Lennox Industries
    ],

    # Network Infrastructure for OT
    "belden": [
        "00:80:63",  # Hirschmann (Belden)
    ],
    "harting": [
        "00:0D:C5",  # HARTING
    ],

    # Transportation/ITS Vendors
    "siemens_its": [
        "00:1F:F8",  # Siemens AG (ITS division)
        "00:0E:8C",  # Siemens AG
        "64:00:6A",  # Siemens AG
    ],
    "econolite": [
        # "00:19:FA" REMOVED - Actually Cable Vision Electronics per IEEE registry
        # NOTE: Econolite may use embedded NICs from other vendors.
        # Traffic controllers are better identified via SNMP sysDescr/sysObjectID.
    ],
    "mccain": [
        "00:0D:56",  # McCain Traffic Supply
    ],
    "wavetronix": [
        "00:18:3E",  # Wavetronix LLC
    ],
    "flir": [
        "00:40:7F",  # FLIR Systems (Sweden)
        "00:1B:D8",  # FLIR Systems Inc
    ],
    "daktronics": [
        "00:06:D3",  # Daktronics Inc
    ],
    "kapsch": [
        "00:0B:6B",  # Kapsch TrafficCom
    ],
    "qfree": [
        "00:17:B0",  # Q-Free ASA
    ],
    "q_free": [
        "00:17:B0",  # Q-Free ASA (alias with underscore)
    ],
    "q-free": [
        "00:17:B0",  # Q-Free ASA (alias with hyphen)
    ],
    "axis": [
        "00:40:8C",  # Axis Communications
        "AC:CC:8E",  # Axis Communications
        "B8:A4:4F",  # Axis Communications
    ],
    "pelco": [
        "00:80:F4",  # Schneider Electric (Pelco parent company)
        "64:3A:EA",  # Schneider Electric
    ],
    "bosch": [
        "00:04:13",  # Bosch Security Systems
        "00:07:5F",  # Bosch
    ],
    "hikvision": [
        "C0:56:E3",  # Hikvision
        "44:19:B6",  # Hikvision
        "BC:AD:28",  # Hikvision
    ],
    "vaisala": [
        "00:0C:D6",  # Vaisala
    ],

    # Logistics / AGV / Warehouse Automation Vendors
    "kuka": [
        "00:1A:28",  # KUKA Roboter GmbH
        "00:1F:29",  # KUKA Roboter GmbH
        "00:10:DC",  # KUKA Roboter GmbH (verified IEEE)
    ],
    "mir": [
        "00:1E:06",  # Mobile Industrial Robots A/S
    ],
    "cognex": [
        "00:04:3E",  # Cognex Corporation
        "00:0D:88",  # Cognex Corporation
    ],
    "impinj": [
        "00:16:25",  # Impinj Inc
    ],
    "zebra": [
        "00:A0:F8",  # Zebra Technologies (Symbol legacy)
        "00:23:68",  # Zebra Technologies
        "AC:3F:A4",  # Zebra Technologies
    ],
    "dematic": [
        "00:1C:34",  # Dematic (Kion Group)
    ],
    "swisslog": [
        # Uses embedded NICs (Siemens, Intel) - identified via protocol
    ],
    "daifuku": [
        "00:0E:C4",  # Daifuku Co Ltd
    ],
}

# Device type to typical vendor mapping
DEVICE_TYPE_VENDORS: dict[str, list[str]] = {
    "plc": ["siemens", "rockwell", "schneider", "abb", "omron", "mitsubishi", "beckhoff", "b_and_r"],
    "hmi": ["siemens", "rockwell", "schneider", "abb", "omron", "advantech"],
    "scada_server": ["wonderware", "ge", "honeywell", "yokogawa", "emerson"],
    "rtu": ["schneider", "abb", "ge", "emerson", "honeywell"],
    "drive": ["siemens", "abb", "rockwell", "schneider", "emerson"],
    "io_module": ["siemens", "rockwell", "phoenix_contact", "wago", "beckhoff", "turck"],
    "sensor": ["sick", "ifm", "omron", "turck", "endress_hauser"],
    "actuator": ["siemens", "abb", "emerson", "honeywell"],
    "engineering_station": ["siemens", "rockwell", "schneider", "abb", "ge", "emerson"],
    "historian": ["ge", "wonderware", "honeywell", "yokogawa"],
    "gateway": ["moxa", "advantech", "phoenix_contact", "cisco", "hirschmann"],
    "switch": ["cisco", "hirschmann", "moxa", "phoenix_contact", "belden"],
    "firewall": ["cisco", "hirschmann", "phoenix_contact"],
    "relay": ["ge", "abb", "siemens", "schneider"],
    "meter": ["schneider", "ge", "siemens", "abb"],
    "protection_relay": ["sel", "ge", "abb", "siemens", "schneider", "basler", "beckwith"],

    # Transportation/ITS Device Types
    "traffic_controller": ["econolite", "siemens", "mccain"],
    "dms": ["daktronics"],
    "dynamic_message_sign": ["daktronics"],
    "radar_sensor": ["wavetronix"],
    "thermal_sensor": ["flir"],
    "weather_station": ["vaisala"],
    "toll_system": ["kapsch"],
    "toll_controller": ["kapsch"],
    "rsu": ["qfree"],
    "roadside_unit": ["qfree"],
    "its_camera": ["axis", "pelco", "bosch", "hikvision"],
    "ptz_camera": ["pelco", "bosch"],
    "anpr_camera": ["hikvision", "bosch"],

    # Additional Transportation/ITS Device Types (tunnel, toll, infrastructure)
    "master_station": ["siemens", "siemens_its"],
    "toll_host": ["kapsch"],
    "lane_controller": ["kapsch"],
    "video_detector": ["axis", "bosch", "hikvision"],
    "detector_rack": ["mccain"],
    "lighting_controller": ["siemens", "siemens_its"],
    "ventilation_controller": ["siemens", "siemens_its"],
    "chem_sensor": ["vaisala"],
    "fire_panel": ["schneider"],
    "seismic_sensor": ["schneider"],
    "pump_controller": ["schneider"],
    "barrier_controller": ["schneider"],
    "classification_sensor": ["wavetronix"],
    "camera": ["axis", "pelco", "bosch", "hikvision"],

    # Building Automation / BMS Device Types
    "bac": ["johnson_controls", "honeywell", "siemens", "schneider"],  # Building Automation Controller
    "building_controller": ["johnson_controls", "honeywell", "siemens", "schneider"],
    "bms_server": ["johnson_controls", "honeywell", "schneider"],
    "ahu_controller": ["trane", "carrier", "johnson_controls", "honeywell"],  # Air Handling Unit
    "vav_controller": ["trane", "johnson_controls", "distech", "carrier"],  # Variable Air Volume
    "chiller_controller": ["trane", "carrier", "johnson_controls", "york"],
    "boiler_controller": ["honeywell", "siemens", "johnson_controls"],
    "rooftop_unit": ["trane", "carrier", "lennox"],
    "crac_unit": ["schneider", "emerson", "carel"],  # Computer Room AC
    "energy_meter": ["schneider", "siemens", "honeywell", "johnson_controls"],
    "power_meter": ["schneider", "siemens", "ge"],
    "thermostat": ["honeywell", "johnson_controls", "trane", "carrier"],
    "room_controller": ["distech", "delta_controls", "johnson_controls"],
    "zone_controller": ["distech", "delta_controls", "johnson_controls", "trane"],
    "access_panel": ["honeywell", "johnson_controls", "siemens"],
    "access_controller": ["honeywell", "johnson_controls", "siemens"],
    "niagara_jace": ["tridium", "honeywell"],  # Tridium JACE controllers
    "webctrl": ["automated_logic"],  # Automated Logic WebCTRL
    "metasys": ["johnson_controls"],  # Johnson Controls Metasys
    "tracer": ["trane"],  # Trane Tracer controllers

    # Oil & Gas / Process Industry Device Types
    "safety_plc": ["schneider", "honeywell", "siemens", "yokogawa", "abb"],  # SIS/ESD controllers
    "safety_io": ["schneider", "honeywell", "siemens", "yokogawa"],  # Safety I/O modules
    "flow_computer": ["schneider", "emerson", "abb", "honeywell"],  # Custody transfer
    "gas_chromatograph": ["yokogawa", "emerson", "siemens"],  # Process analyzers
    "compressor_controller": ["schneider", "emerson", "ge", "siemens"],  # Compressor control
    "leak_detection": ["honeywell", "emerson", "siemens"],  # Pipeline LDS
    "wellhead_controller": ["schneider", "emerson", "honeywell"],  # Wellsite RTUs
    "custody_meter": ["emerson", "endress_hauser", "schneider"],  # Fiscal metering
    "process_analyzer": ["yokogawa", "emerson", "honeywell", "siemens"],  # Online analyzers
    "valve_positioner": ["emerson", "siemens", "abb", "honeywell"],  # Fisher DVC, etc.
    "pressure_transmitter": ["emerson", "endress_hauser", "yokogawa", "honeywell"],
    "flow_transmitter": ["emerson", "endress_hauser", "yokogawa", "siemens"],
    "level_transmitter": ["emerson", "endress_hauser", "yokogawa", "siemens"],
    "temperature_transmitter": ["emerson", "endress_hauser", "yokogawa", "honeywell"],
    "dcs_controller": ["emerson", "honeywell", "yokogawa", "abb", "siemens"],  # DeltaV, Experion, CENTUM

    # Distribution / Logistics / Warehouse Automation Device Types
    "agv": ["kuka", "mir", "dematic", "daifuku"],  # Automated Guided Vehicles
    "amr": ["mir", "kuka"],  # Autonomous Mobile Robots
    "agv_controller": ["kuka", "mir", "dematic"],  # AGV onboard controllers
    "fleet_manager": ["kuka", "mir", "dematic", "swisslog"],  # AGV fleet management
    "conveyor_controller": ["siemens", "rockwell", "schneider"],  # Conveyor PLCs
    "sortation_controller": ["siemens", "rockwell", "dematic"],  # Sortation system PLCs
    "barcode_scanner": ["sick", "cognex", "honeywell", "zebra"],  # Fixed barcode readers
    "vision_system": ["cognex", "sick"],  # Machine vision cameras
    "rfid_reader": ["impinj", "zebra", "honeywell"],  # RFID readers
    "rfid_gateway": ["impinj", "zebra"],  # RFID aggregation gateways
    "pick_to_light": ["siemens", "rockwell", "honeywell"],  # Pick-to-light systems
    "label_applicator": ["zebra", "honeywell"],  # Print-and-apply systems
    "weigh_scale": ["honeywell", "emerson"],  # Weigh-in-motion / checkweighers
    "temperature_controller": ["honeywell", "schneider", "emerson"],  # Cold chain controllers
    "cold_storage_controller": ["honeywell", "schneider", "emerson"],  # Refrigeration systems
}

# Default OUI for unknown vendors (locally administered)
DEFAULT_OUIS = [
    "02:00:00",  # Locally administered
    "00:50:56",  # VMware (common in virtual OT labs)
]

# Human-readable vendor names for display
# Maps internal key -> display name
VENDOR_DISPLAY_NAMES: dict[str, str] = {
    "siemens": "Siemens",
    "rockwell": "Rockwell Automation",
    "schneider": "Schneider Electric",
    "abb": "ABB",
    "emerson": "Emerson",
    "honeywell": "Honeywell",
    "ge": "GE",
    "sel": "Schweitzer Engineering (SEL)",
    "basler": "Basler Electric",
    "beckwith": "Beckwith Electric",
    "phoenix_contact": "Phoenix Contact",
    "beckhoff": "Beckhoff",
    "wago": "WAGO",
    "omron": "Omron",
    "mitsubishi": "Mitsubishi Electric",
    "b_and_r": "B&R Automation",
    "pilz": "Pilz",
    "sick": "SICK",
    "turck": "Turck",
    "ifm": "IFM Electronic",
    "endress_hauser": "Endress+Hauser",
    "yokogawa": "Yokogawa",
    "moxa": "Moxa",
    "advantech": "Advantech",
    "hms": "HMS Industrial Networks",
    "cisco": "Cisco",
    "hirschmann": "Hirschmann",
    "wonderware": "Wonderware",
    "copadata": "Copa-Data",
    "kepware": "Kepware",
    "johnson_controls": "Johnson Controls",
    "tridium": "Tridium",
    "trane": "Trane",
    "carrier": "Carrier",
    "delta_controls": "Delta Controls",
    "distech": "Distech Controls",
    "carel": "Carel",
    "automated_logic": "Automated Logic",
    "kmc_controls": "KMC Controls",
    "alerton": "Alerton",
    "reliable_controls": "Reliable Controls",
    "lennox": "Lennox",
    "belden": "Belden",
    "harting": "HARTING",
    "siemens_its": "Siemens ITS",
    "econolite": "Econolite",
    "mccain": "McCain",
    "wavetronix": "Wavetronix",
    "flir": "FLIR Systems",
    "daktronics": "Daktronics",
    "kapsch": "Kapsch TrafficCom",
    "qfree": "Q-Free",
    "q_free": "Q-Free",
    "q-free": "Q-Free",
    "axis": "Axis Communications",
    "pelco": "Pelco",
    "bosch": "Bosch",
    "hikvision": "Hikvision",
    "vaisala": "Vaisala",
    # Logistics / AGV / Warehouse Automation
    "kuka": "KUKA",
    "mir": "MiR (Mobile Industrial Robots)",
    "cognex": "Cognex",
    "impinj": "Impinj",
    "zebra": "Zebra Technologies",
    "dematic": "Dematic",
    "swisslog": "Swisslog",
    "daifuku": "Daifuku",
}


# ODVA (CIP/EtherNet/IP) Vendor IDs - official ODVA registrations
ODVA_VENDOR_IDS: dict[str, int] = {
    "rockwell": 1,  # Allen-Bradley (Rockwell Automation)
    "schneider": 67,  # Schneider Electric
    "siemens": 285,  # Siemens
    "abb": 75,  # ABB (ODVA Licensed Vendor)
    "honeywell": 50,  # Honeywell
    "emerson": 90,  # Emerson
    "ge": 82,  # General Electric
    "omron": 47,  # Omron
    "mitsubishi": 121,  # Mitsubishi
    "kuka": 368,  # KUKA Roboter GmbH
    "cognex": 112,  # Cognex Corporation
}

# PROFINET Vendor IDs
PROFINET_VENDOR_IDS: dict[str, int] = {
    "siemens": 0x002A,  # 42
    "schneider": 0x0095,  # 149
    "rockwell": 0x0001,  # 1
    "abb": 0x0037,  # 55
    "phoenix_contact": 0x00B8,  # 184
}

# BACnet Vendor IDs (ASHRAE-registered)
BACNET_VENDOR_IDS: dict[int, str] = {
    5: "Johnson Controls",
    17: "Honeywell",
    24: "Siemens",
    67: "Schneider Electric",
    86: "Automated Logic",
    95: "TAC (Schneider)",
    97: "Trane",
    122: "Delta Controls",
    165: "Distech Controls",
    200: "KMC Controls",
    236: "Alerton",
    252: "Continental Automated Buildings Association",
    260: "Carel Industries",
    279: "Carrier",
    301: "Carrier Corp.",
    317: "Reliable Controls",
    353: "Lennox",
    381: "McQuay",
    416: "Novar (Honeywell)",
    438: "Computrols",
    489: "Contemporary Controls",
}

# Vendor division OUI aliases — keys not in VENDOR_OUIS that map to
# subdivision-specific OUI prefixes used by fingerprinting.
_VENDOR_DIVISION_OUIS: dict[str, list[str]] = {
    "endress+hauser": ["00:0B:CD", "00:80:A3"],  # Endress+Hauser (alt spelling)
    "ge_multilin": ["00:22:52", "00:04:A5"],  # GE Digital Energy / Multilin
    "siemens_building": ["00:1B:1B", "00:0E:8C"],  # Siemens Building Technologies
    "schneider_bms": ["00:80:F4", "00:04:A3"],  # Schneider Electric BMS
    "siemens_protection": ["00:0E:8C", "00:1C:06", "74:DA:EA"],  # Siemens SIPROTEC
    "microsoft": ["00:15:5D", "00:1D:D8", "00:50:F2"],  # Microsoft Corporation
}

# Aggregated OUI prefixes: canonical VENDOR_OUIS + vendor division aliases.
# Use this when you need ALL known OUI mappings for MAC-based vendor lookup.
VENDOR_OUI_PREFIXES: dict[str, list[str]] = {**VENDOR_OUIS, **_VENDOR_DIVISION_OUIS}


def get_random_oui_for_vendor(vendor: str) -> str | None:
    """Get a random OUI prefix for a vendor from the full OUI database."""
    import random as _rand
    ouis = VENDOR_OUI_PREFIXES.get(vendor.lower(), [])
    return _rand.choice(ouis) if ouis else None


def get_oui_for_vendor(vendor: str) -> str:
    """Get a random OUI for a specific vendor.

    Args:
        vendor: Vendor name (case-insensitive)

    Returns:
        OUI prefix (e.g., "00:0E:8C")
    """
    vendor_lower = vendor.lower().replace(" ", "_").replace("-", "_")

    if vendor_lower in VENDOR_OUIS:
        oui_list = VENDOR_OUIS[vendor_lower]
        if oui_list:  # Only use vendor OUIs if list is non-empty
            return random.choice(oui_list)
        # Empty list means software vendor - use default OUI

    return random.choice(DEFAULT_OUIS)


def get_oui_for_device_type(device_type: str, vendor: Optional[str] = None) -> str:
    """Get a random OUI appropriate for a device type.

    Args:
        device_type: Type of device (e.g., "plc", "hmi")
        vendor: Optional specific vendor

    Returns:
        OUI prefix (e.g., "00:0E:8C")
    """
    if vendor:
        return get_oui_for_vendor(vendor)

    device_type_lower = device_type.lower()

    if device_type_lower in DEVICE_TYPE_VENDORS:
        typical_vendor = random.choice(DEVICE_TYPE_VENDORS[device_type_lower])
        return get_oui_for_vendor(typical_vendor)

    return random.choice(DEFAULT_OUIS)


def generate_mac_address(vendor: Optional[str] = None, device_type: Optional[str] = None) -> str:
    """Generate a complete MAC address with appropriate OUI.

    Args:
        vendor: Optional vendor name
        device_type: Optional device type

    Returns:
        Complete MAC address (e.g., "00:0E:8C:AB:12:34")
    """
    if vendor:
        oui = get_oui_for_vendor(vendor)
    elif device_type:
        oui = get_oui_for_device_type(device_type)
    else:
        oui = random.choice(DEFAULT_OUIS)

    # Generate the last 3 bytes randomly
    last_bytes = [random.randint(0, 255) for _ in range(3)]
    last_part = ":".join(f"{b:02x}" for b in last_bytes)

    return f"{oui}:{last_part}"


def get_vendor_for_oui(oui: str, human_readable: bool = True) -> Optional[str]:
    """Look up vendor for a given OUI.

    Args:
        oui: OUI prefix (e.g., "00:0E:8C" or "00-0E-8C")
        human_readable: If True, return display name (e.g., "Johnson Controls").
                       If False, return internal key (e.g., "johnson_controls").

    Returns:
        Vendor name or None if not found
    """
    oui_normalized = oui.upper().replace("-", ":")

    for vendor_key, ouis in VENDOR_OUIS.items():
        for vendor_oui in ouis:
            if vendor_oui.upper() == oui_normalized:
                if human_readable:
                    return VENDOR_DISPLAY_NAMES.get(vendor_key, vendor_key.replace("_", " ").title())
                return vendor_key

    return None


def list_vendors() -> list[str]:
    """List all known vendors.

    Returns:
        List of vendor names
    """
    return sorted(VENDOR_OUIS.keys())


def list_vendors_for_device_type(device_type: str) -> list[str]:
    """List typical vendors for a device type.

    Args:
        device_type: Type of device

    Returns:
        List of vendor names
    """
    device_type_lower = device_type.lower()
    return DEVICE_TYPE_VENDORS.get(device_type_lower, [])
