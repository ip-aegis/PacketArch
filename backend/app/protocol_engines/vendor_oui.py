# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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

# VENDOR_OUIS is AUTO-GENERATED from the bundled IEEE OUI registry — see
# scripts/generate_vendor_ouis.py. Pure data + in protocol_engines/, so it is
# safely staged into the agent image. Do NOT hand-edit OUI lists here.
from app.protocol_engines._vendor_ouis_generated import VENDOR_OUIS



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
    "switch": ["cisco"],
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

    # Rail / train-control Device Types (PTC = EMP; legacy signaling = ATCS)
    "back_office_server": ["wabtec", "ge transportation"],
    "wayside_interface_unit": ["wabtec", "ge transportation"],
    "locomotive_computer": ["wabtec", "ge transportation"],
    "wayside_mcp": ["alstom", "siemens mobility", "hitachi rail"],
    "atcs_base_station": ["siemens mobility", "alstom", "hitachi rail"],
    "wayside_signal_controller": ["hitachi rail", "alstom", "siemens mobility"],
    "atcs_office": ["alstom", "hitachi rail", "siemens mobility"],

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
DEFAULT_OUI = "02:00:00"

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
    "york": "York (Johnson Controls)",
    "notifier": "Notifier (Honeywell)",
    "lutron": "Lutron Electronics",
    "aveva": "AVEVA",
    "lansweeper": "Lansweeper",
    "paessler": "Paessler PRTG",
    "broadcom": "Broadcom",
    "f5_networks": "F5 Networks",
    "f5-networks": "F5 Networks",
    "belden": "Belden",
    "harting": "HARTING",
    "siemens_its": "Siemens ITS",
    "wabtec": "Wabtec",
    "ge transportation": "GE Transportation",
    "alstom": "Alstom",
    "siemens mobility": "Siemens Mobility",
    "hitachi rail": "Hitachi Rail",
    "bombardier": "Bombardier Transportation",
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
    "fanuc": "Fanuc",
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
    # Audit 2026-05-31: IDs verified against Wireshark packet-cip.c cip_vendor_vals.
    "rockwell": 1,  # Allen-Bradley (Rockwell Automation)
    "schneider": 243,  # Schneider Electric (was 67 — wrong)
    "siemens": 145,  # Siemens (was 285 — wrong)
    "cisco": 680,  # Cisco Systems (UNRESOLVED — left as-is)
    "abb": 46,  # ABB (was 75 — wrong)
    "honeywell": 3,  # Honeywell (was 50 — wrong)
    "emerson": 90,  # Emerson (UNRESOLVED — left as-is)
    "ge": 143,  # General Electric (was 82 — wrong)
    "omron": 47,  # Omron
    "mitsubishi": 161,  # Mitsubishi (was 121 — that ID is actually KUKA)
    "kuka": 121,  # KUKA Roboter GmbH (was 368 — wrong)
    "cognex": 112,  # Cognex Corporation (UNRESOLVED — left as-is)
}

# PROFINET Vendor IDs
PROFINET_VENDOR_IDS: dict[str, int] = {
    "siemens": 0x002A,  # 42
    "schneider": 0x0095,  # 149
    "rockwell": 0x0001,  # 1
    "cisco": 0x0145,  # 325
    "abb": 0x0037,  # 55
    "phoenix_contact": 0x00B8,  # 184
}

# BACnet Vendor IDs (ASHRAE-registered)
# Audit 2026-05-31: IDs verified against bacnet.org/assigned-vendor-ids.
BACNET_VENDOR_IDS: dict[int, str] = {
    5: "Johnson Controls",
    17: "Honeywell",
    7: "Siemens",  # was 24
    10: "Schneider Electric",  # was 67
    24: "Automated Logic",  # was 86
    11: "TAC (Schneider)",  # was 95
    2: "Trane",  # was 97
    8: "Delta Controls",  # was 122
    332: "Distech Controls",  # was 165
    28: "KMC Controls",  # was 200
    18: "Alerton",  # was 236
    252: "Continental Automated Buildings Association",
    77: "Carel Industries",  # was 260
    16: "Carrier",  # was 279
    301: "Carrier Corp.",
    35: "Reliable Controls",  # was 317
    255: "Lennox",  # was 353
    381: "McQuay",  # UNRESOLVED — not found in assigned-vendor-ids
    91: "Novar (Honeywell)",  # was 416
    225: "Computrols",  # was 438
    245: "Contemporary Controls",  # was 489
    115: "Lutron",  # Lutron Electronics
    188: "Notifier",  # Notifier (Honeywell fire) — template-sourced, verify vs assigned-vendor-ids
    316: "Janitza",  # Janitza electronics GmbH (EU energy metering)
    1473: "Elvaco",  # Elvaco AB (M-Bus metering gateways)
}

# Vendor division OUI aliases — keys not in VENDOR_OUIS that map to
# subdivision-specific OUI prefixes used by fingerprinting.
# Division/alias spellings are now emitted directly into VENDOR_OUIS by the
# generator, so this overlay is empty (kept for import back-compat).
_VENDOR_DIVISION_OUIS: dict[str, list[str]] = {}

# Aggregated OUI prefixes: canonical VENDOR_OUIS + vendor division aliases.
# Use this when you need ALL known OUI mappings for MAC-based vendor lookup.
VENDOR_OUI_PREFIXES: dict[str, list[str]] = {**VENDOR_OUIS, **_VENDOR_DIVISION_OUIS}


# Vendor name aliases: maps variations to canonical short form. Lives here (a
# stdlib-only module staged into the agent) so it is the single source of truth
# for vendor normalization on BOTH the backend and the agent. The backend's
# app.core.vendor_normalize re-exports normalize_vendor/VENDOR_NAME_ALIASES from
# here for backward compatibility.
VENDOR_NAME_ALIASES: dict[str, str] = {
    # Full names -> canonical short names
    "johnson controls": "johnson_controls",
    "schneider electric": "schneider",
    "delta controls": "delta_controls",
    "distech controls": "distech",
    "automated logic": "automated_logic",
    "endress+hauser": "endress_hauser",
    "endress hauser": "endress_hauser",
    "ge multilin": "ge_multilin",
    # Handle underscore variants in lookups
    "johnson_controls": "johnson_controls",
    "schneider_electric": "schneider",
    "delta_controls": "delta_controls",
    "distech_controls": "distech",
    "automated_logic": "automated_logic",
    "endress_hauser": "endress_hauser",
    "ge_multilin": "ge_multilin",
    # Handle Allen-Bradley variations
    "allen-bradley": "allen_bradley",
    "allen bradley": "allen_bradley",
    "allen_bradley": "allen_bradley",
}


def normalize_vendor(vendor: str) -> str:
    """Normalize a vendor name to its canonical short form for lookups.

    Examples: "Johnson Controls" -> "johnson_controls", "Schneider Electric" ->
    "schneider", "Allen-Bradley" -> "allen_bradley".
    """
    lower = vendor.lower().strip()
    return VENDOR_NAME_ALIASES.get(lower, lower)


def get_random_oui_for_vendor(vendor: str) -> str | None:
    """Get a random OUI prefix for a vendor from the full OUI database."""
    import random as _rand
    ouis = VENDOR_OUI_PREFIXES.get(vendor.lower(), [])
    return _rand.choice(ouis) if ouis else None


def get_oui_for_vendor(vendor: str) -> str:
    """Get a random OUI for a specific vendor.

    Normalises the vendor: lowercase, spaces/hyphens → underscores.
    Then tries the literal form (so `&` etc. land via their aliases)
    and the `&` → `_and_` expansion. Falls back to DEFAULT_OUI.

    Args:
        vendor: Vendor name (case-insensitive)

    Returns:
        OUI prefix (e.g., "00:0E:8C")
    """
    raw = vendor.lower()
    vendor_lower = raw.replace(" ", "_").replace("-", "_")
    candidates = [vendor_lower, vendor_lower.replace("&", "_and_")]

    for key in candidates:
        if key in VENDOR_OUIS:
            oui_list = VENDOR_OUIS[key]
            if oui_list:  # Only use vendor OUIs if list is non-empty
                return random.choice(oui_list)
            # Empty list means software vendor - use default OUI
            return DEFAULT_OUI

    return DEFAULT_OUI


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

    return DEFAULT_OUI


def generate_mac_address(
    vendor: Optional[str] = None,
    device_type: Optional[str] = None,
    oui_prefixes: list[str] | None = None,
) -> str:
    """Generate a complete MAC address with appropriate OUI.

    Args:
        vendor: Optional vendor name
        device_type: Optional device type
        oui_prefixes: Optional list of OUI prefixes to choose from.
                      When provided, takes priority over vendor/device_type lookup.

    Returns:
        Complete MAC address (e.g., "00:0E:8C:AB:12:34")
    """
    if oui_prefixes:
        oui = random.choice(oui_prefixes)
    elif vendor:
        oui = get_oui_for_vendor(vendor)
    elif device_type:
        oui = get_oui_for_device_type(device_type)
    else:
        oui = DEFAULT_OUI

    # Generate the last 3 bytes randomly
    last_bytes = [random.randint(0, 255) for _ in range(3)]
    last_part = ":".join(f"{b:02x}" for b in last_bytes)

    return f"{oui}:{last_part}"


_IEEE_REGISTRY: dict[str, str] | None = None


def _ieee_registry() -> dict[str, str]:
    """Lazily load the bundled IEEE OUI registry (prefix6 -> registrant name).

    Lazy so the agent (which never calls get_vendor_for_oui) never pays the cost.
    Returns {} if the data file is absent — callers fall back to local OUIS.
    """
    global _IEEE_REGISTRY
    if _IEEE_REGISTRY is None:
        import csv
        import os

        path = os.path.join(os.path.dirname(__file__), "data", "ieee_oui.csv")
        reg: dict[str, str] = {}
        try:
            with open(path, newline="") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 2 and len(row[0]) == 6:
                        reg[row[0].upper()] = row[1]
        except OSError:
            pass
        _IEEE_REGISTRY = reg
    return _IEEE_REGISTRY


def get_vendor_for_oui(oui: str, human_readable: bool = True) -> Optional[str]:
    """Look up the vendor that owns a given OUI.

    Authoritative source is the bundled IEEE OUI registry (the same data Cyber
    Vision uses), so labels match what CV reports. Falls back to the local
    VENDOR_OUIS map if the registry is unavailable.

    Args:
        oui: OUI prefix (e.g., "00:0E:8C" or "00-0E-8C")
        human_readable: If True, return the registrant/display name. If False,
                       return our internal vendor key when the OUI is one of ours.

    Returns:
        Vendor name or None if not found.
    """
    oui_normalized = oui.upper().replace("-", ":")

    # For display, the IEEE registrant is authoritative and matches what CV shows.
    # (It also avoids alias ambiguity: parent-mapped vendors like Pelco/York share
    # their parent's OUI list, so a VENDOR_OUIS scan could return the alias name.)
    if human_readable:
        company = _ieee_registry().get(oui_normalized.replace(":", ""))
        if company:
            return company

    # Internal-key lookups stay scoped to our vendors (used for keyed routing);
    # also the display fallback when the registry file is unavailable.
    for vendor_key, ouis in VENDOR_OUIS.items():
        for vendor_oui in ouis:
            if vendor_oui.upper() == oui_normalized:
                if human_readable:
                    return VENDOR_DISPLAY_NAMES.get(vendor_key, vendor_key.replace("_", " ").title())
                return vendor_key

    return None


def pick_vendor_oui(vendor: str, oui_prefixes: list[str]) -> Optional[str]:
    """Return the first OUI in ``oui_prefixes`` whose IEEE registrant (the label
    Cyber Vision shows) is consistent with ``vendor``.

    A device's MAC should read as its intended manufacturer. This matters most for
    client-only personas (an HMI polling a PLC): with no protocol identity to
    override it, the OUI is the ENTIRE fingerprint, so a MAC drawn from a
    sub-brand OUI (e.g. a Schneider template's Control-Microsystems prefix) mislabels
    the device. Preferring the earliest vendor-matching prefix keeps the MAC on the
    vendor's canonical OUI (templates list it first). Returns None when nothing
    matches, so callers can fall back to the raw list.
    """
    if not vendor or not oui_prefixes:
        return None
    key = vendor.strip().lower().split()[0]  # "Schneider Electric" -> "schneider"
    for oui in oui_prefixes:
        registrant = get_vendor_for_oui(oui)
        if registrant and key in registrant.lower():
            return oui
    return None


# ---------------------------------------------------------------------------
# SNMP Enterprise OIDs (IANA Private Enterprise Numbers)
# Used for sysObjectID synthesis when a device template lacks explicit
# snmp_identity.  Keyed by normalised vendor name (lowercase, underscores).
# ---------------------------------------------------------------------------
VENDOR_ENTERPRISE_OIDS: dict[str, str] = {
    "siemens": "1.3.6.1.4.1.4329",
    "rockwell": "1.3.6.1.4.1.95",      # PEN 95 (was 53148 — wrong)
    "schneider": "1.3.6.1.4.1.3833",
    "abb": "1.3.6.1.4.1.908",          # PEN 908 (was 26381 — wrong)
    "emerson": "1.3.6.1.4.1.476",      # PEN 476 (was 3530 — wrong)
    "honeywell": "1.3.6.1.4.1.2879",
    "ge": "1.3.6.1.4.1.3861",
    "yokogawa": "1.3.6.1.4.1.2745",
    "cisco": "1.3.6.1.4.1.9",
    "moxa": "1.3.6.1.4.1.8691",
    "hirschmann": "1.3.6.1.4.1.248",
    "hms": "1.3.6.1.4.1.8284",
    "phoenix_contact": "1.3.6.1.4.1.4346",
    "beckhoff": "1.3.6.1.4.1.25157",   # PEN 25157 (was 2510 — wrong)
    "wago": "1.3.6.1.4.1.13576",
    "omron": "1.3.6.1.4.1.16838",      # PEN 16838 (was 1103 — wrong)
    "mitsubishi": "1.3.6.1.4.1.409",   # PEN 409 (was 18296 — wrong)
    "sel": "1.3.6.1.4.1.1027",
    "beckwith": "1.3.6.1.4.1.2456",        # Beckwith Electric Co. (IANA PEN 2456)
    "basler": "1.3.6.1.4.1.16654",         # Basler Electric (IANA PEN 16654)
    "erlphase": "1.3.6.1.4.1.39298",       # ERLPhase Power Technologies (IANA PEN 39298)
    "doble": "1.3.6.1.4.1.7037",           # Doble Engineering Company (IANA PEN 7037)
    "sick": "1.3.6.1.4.1.1713",
    "advantech": "1.3.6.1.4.1.10297",
    "johnson_controls": "1.3.6.1.4.1.21239",
    "tridium": "1.3.6.1.4.1.18943",
    "trane": "1.3.6.1.4.1.11108",
    "delta_controls": "1.3.6.1.4.1.12412",
    "distech": "1.3.6.1.4.1.37567",
    "daktronics": "1.3.6.1.4.1.5765",
    "kapsch": "1.3.6.1.4.1.28846",
    "axis": "1.3.6.1.4.1.368",
    "vaisala": "1.3.6.1.4.1.39165",
    "kuka": "1.3.6.1.4.1.25882",
    "cognex": "1.3.6.1.4.1.10642",
    "fanuc": "1.3.6.1.4.1.5765",
    "endress+hauser": "1.3.6.1.4.1.8714",
    "econolite": "1.3.6.1.4.1.1206.4.2",
    "siemens_its": "1.3.6.1.4.1.1206.4.2",
    "mccain": "1.3.6.1.4.1.1206.4.2",
}

# Neutral fallback — net-snmp on Linux, signals "generic agent"
DEFAULT_ENTERPRISE_OID = "1.3.6.1.4.1.8072.3.2.10"


def get_enterprise_oid_for_vendor(vendor: str) -> str:
    """Return the SNMP enterprise OID for a vendor.

    Normalises the vendor string (lowercase, spaces/hyphens → underscores)
    and looks up ``VENDOR_ENTERPRISE_OIDS``.  Falls back to
    ``DEFAULT_ENTERPRISE_OID`` for unknown vendors.
    """
    key = vendor.lower().replace(" ", "_").replace("-", "_")
    if key in VENDOR_ENTERPRISE_OIDS:
        return VENDOR_ENTERPRISE_OIDS[key]
    # Try prefix match (e.g. "schneider electric" → "schneider")
    for vendor_key, oid in VENDOR_ENTERPRISE_OIDS.items():
        if key.startswith(vendor_key) or vendor_key.startswith(key):
            return oid
    return DEFAULT_ENTERPRISE_OID


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
