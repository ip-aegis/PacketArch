"""Vendor OUI (Organizationally Unique Identifier) database for realistic MAC generation."""

import random
from typing import Optional


# OUI database: Vendor name -> list of OUI prefixes (first 3 bytes of MAC)
# Based on IEEE OUI registry for major OT/industrial automation vendors
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
    ],
    "rockwell": [
        "00:00:BC",  # Allen-Bradley (legacy)
        "00:1D:9C",  # Rockwell Automation
        "00:1B:90",  # Rockwell Collins
        "B4:8C:9D",  # Rockwell Automation
    ],
    "schneider": [
        "00:00:54",  # Schneider Electric (legacy Modicon)
        "00:80:F4",  # Schneider Electric
        "00:04:A3",  # Schneider Electric
        "00:1C:C4",  # Schneider Electric
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
        "00:A0:F8",  # Emerson Process Management
        "00:50:43",  # Fisher-Rosemount (Emerson)
        "00:60:35",  # Emerson Electric
        "00:0D:3A",  # Emerson Network Power
    ],
    "honeywell": [
        "00:00:8C",  # Honeywell (legacy)
        "00:D0:34",  # Honeywell Industrial
        "00:04:63",  # Honeywell Inc
        "00:1A:64",  # Honeywell Life Safety
        "F4:4E:05",  # Honeywell Connected
    ],
    "ge": [
        "00:04:A5",  # GE Intelligent Platforms
        "00:09:45",  # GE Fanuc Automation
        "00:30:C1",  # GE Healthcare
        "00:50:99",  # GE Industrial Systems
        "00:22:52",  # GE Digital Energy
    ],
    "phoenix_contact": [
        "00:A0:45",  # Phoenix Contact
        "00:16:9D",  # Phoenix Contact
        "00:60:65",  # Phoenix Contact
    ],
    "beckhoff": [
        "00:01:05",  # Beckhoff Automation
        "00:04:A5",  # Beckhoff shared
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
    "cisco": [
        "00:00:0C",  # Cisco Systems
        "00:1A:A1",  # Cisco Systems
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

    # Building Automation
    "johnson_controls": [
        "00:1A:17",  # Johnson Controls
    ],
    "tridium": [
        "00:50:62",  # Tridium
    ],

    # Network Infrastructure for OT
    "belden": [
        "00:80:63",  # Hirschmann (Belden)
    ],
    "harting": [
        "00:0D:C5",  # HARTING
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
    "protection_relay": ["ge", "abb", "siemens", "schneider"],
}

# Default OUI for unknown vendors (locally administered)
DEFAULT_OUIS = [
    "02:00:00",  # Locally administered
    "00:50:56",  # VMware (common in virtual OT labs)
]


def get_oui_for_vendor(vendor: str) -> str:
    """Get a random OUI for a specific vendor.

    Args:
        vendor: Vendor name (case-insensitive)

    Returns:
        OUI prefix (e.g., "00:0E:8C")
    """
    vendor_lower = vendor.lower().replace(" ", "_").replace("-", "_")

    if vendor_lower in VENDOR_OUIS:
        return random.choice(VENDOR_OUIS[vendor_lower])

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


def get_vendor_for_oui(oui: str) -> Optional[str]:
    """Look up vendor for a given OUI.

    Args:
        oui: OUI prefix (e.g., "00:0E:8C" or "00-0E-8C")

    Returns:
        Vendor name or None if not found
    """
    oui_normalized = oui.upper().replace("-", ":")

    for vendor, ouis in VENDOR_OUIS.items():
        for vendor_oui in ouis:
            if vendor_oui.upper() == oui_normalized:
                return vendor

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
