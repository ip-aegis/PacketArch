"""Vendor fingerprint seed data for major OT vendors.

This module contains realistic fingerprint data for major OT vendors
including Rockwell Automation, Siemens, Schneider Electric, ABB,
Honeywell, Emerson, and GE. The data is based on real device
characteristics observed in industrial environments.

IMPORTANT: These values are approximations for training/testing purposes.
Actual production devices may have variations.
"""

from typing import Any

# ODVA Vendor IDs (official registrations)
ODVA_VENDOR_IDS = {
    "rockwell": 1,  # Allen-Bradley (Rockwell Automation)
    "schneider": 67,  # Schneider Electric
    "siemens": 285,  # Siemens
    "abb": 285,  # ABB also uses 285 in some products
    "honeywell": 50,  # Honeywell
    "emerson": 90,  # Emerson
    "ge": 82,  # General Electric
    "omron": 47,  # Omron
    "mitsubishi": 121,  # Mitsubishi
}

# PROFINET Vendor IDs
PROFINET_VENDOR_IDS = {
    "siemens": 0x002A,  # 42
    "schneider": 0x0095,  # 149
    "rockwell": 0x0001,  # 1
    "abb": 0x0037,  # 55
    "phoenix_contact": 0x00B8,  # 184
}

# MAC OUI Prefixes by vendor (IEEE registrations)
VENDOR_OUI_PREFIXES = {
    "rockwell": [
        "00:00:BC",  # Allen-Bradley
        "00:1D:9C",  # Rockwell Automation
        "5C:88:16",  # Rockwell Automation
    ],
    "siemens": [
        "00:0E:8C",  # Siemens AG
        "00:1B:1B",  # Siemens AG
        "00:1C:06",  # Siemens AG
        "64:9D:D8",  # Siemens AG
        "B8:2C:A0",  # Siemens AG
    ],
    "schneider": [
        "00:00:54",  # Schneider Electric
        "00:80:F4",  # Schneider Electric
        "EC:FA:AA",  # Schneider Electric
    ],
    "abb": [
        "00:20:99",  # ABB Industrial Systems
        "00:21:99",  # ABB STOTZ-KONTAKT
        "CC:DA:0C",  # ABB
    ],
    "honeywell": [
        "00:60:35",  # Honeywell
        "00:D0:36",  # Honeywell
        "64:31:7E",  # Honeywell
    ],
    "emerson": [
        "00:A0:F8",  # Emerson Network Power
        "00:03:38",  # Emerson
        "00:90:E8",  # Fisher-Rosemount (Emerson)
    ],
    "ge": [
        "00:14:49",  # GE Fanuc Automation
        "00:60:B0",  # GE Energy
        "1C:39:47",  # GE
    ],
}


def get_rockwell_fingerprints() -> list[dict[str, Any]]:
    """Get Rockwell Automation device fingerprints."""
    return [
        # ControlLogix L83E
        {
            "vendor": "Rockwell",
            "vendor_family": "ControlLogix",
            "model": "1756-L83E",
            "firmware_version": "32.011",
            "oui_prefixes": VENDOR_OUI_PREFIXES["rockwell"],
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L83E/B",
                "major_minor_revision": "32.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L83E Logix5583E Controller",
                "model_name": "ControlLogix 5583E",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,  # Programmable Logic Controller
                "product_code": 55,
                "revision_major": 32,
                "revision_minor": 11,
                "serial_number": 0x12345678,
                "product_name": "1756-L83E/B LOGIX5583E",
                "state": 3,
            },
            "profinet_identity": None,
            "tcp_stack": {
                "ttl": 128,  # Windows-based
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "nop_padding": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 15.0,
                "mean_ms": 3.5,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0005,
                "timeout_probability": 0.0002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "protocol_quirks": {
                "enip_encap_timeout_ms": 10000,
                "cip_connection_timeout_multiplier": 32,
            },
            "is_builtin": True,
        },
        # CompactLogix L33ER
        {
            "vendor": "Rockwell",
            "vendor_family": "CompactLogix",
            "model": "1769-L33ER",
            "firmware_version": "33.013",
            "oui_prefixes": VENDOR_OUI_PREFIXES["rockwell"],
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1769-L33ER",
                "major_minor_revision": "33.013",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1769-L33ER CompactLogix Controller",
                "model_name": "CompactLogix 5370",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 89,
                "revision_major": 33,
                "revision_minor": 13,
                "serial_number": 0x23456789,
                "product_name": "1769-L33ER/B LOGIX5370",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 0.8,
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0008,
            },
            "is_builtin": True,
        },
        # PanelView Plus 7
        {
            "vendor": "Rockwell",
            "vendor_family": "PanelView",
            "model": "2711P-T15C22D9P",
            "firmware_version": "12.0",
            "oui_prefixes": VENDOR_OUI_PREFIXES["rockwell"],
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 24,  # Human-Machine Interface
                "product_code": 773,
                "revision_major": 12,
                "revision_minor": 0,
                "serial_number": 0x34567890,
                "product_name": "2711P-T15C22D9P",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,  # VxWorks/Linux based
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "lognormal",
            },
            "is_builtin": True,
        },
    ]


def get_siemens_fingerprints() -> list[dict[str, Any]]:
    """Get Siemens device fingerprints."""
    return [
        # S7-1500 CPU 1516-3 PN/DP
        {
            "vendor": "Siemens",
            "vendor_family": "S7-1500",
            "model": "6ES7 516-3AN02-0AB0",
            "firmware_version": "V3.0.3",
            "oui_prefixes": VENDOR_OUI_PREFIXES["siemens"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 516-3AN02-0AB0",
                "major_minor_revision": "V3.0.3",
                "vendor_url": "http://www.siemens.com",
                "product_name": "CPU 1516-3 PN/DP",
                "model_name": "S7-1500",
            },
            "profinet_identity": {
                "vendor_id": 0x002A,
                "device_id": 0x0301,
                "station_name": "plc-s71500",
                "device_role": 2,  # Controller
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 516-3AN02-0AB0",
                "im0_hw_revision": 2,
                "im0_sw_revision": "V3.0.3",
            },
            "tcp_stack": {
                "ttl": 64,  # Linux-based
                "window_size": 29200,
                "mss": 1460,
                "window_scaling": 7,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
                "ecn_support": False,
            },
            "response_timing": {
                "min_ms": 0.3,
                "max_ms": 10.0,
                "mean_ms": 2.0,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 5.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "protocol_quirks": {
                "profinet_cycle_time_us": 1000,
                "s7_max_pdu_size": 960,
            },
            "is_builtin": True,
        },
        # S7-1200 CPU 1214C
        {
            "vendor": "Siemens",
            "vendor_family": "S7-1200",
            "model": "6ES7 214-1AG40-0XB0",
            "firmware_version": "V4.5.2",
            "oui_prefixes": VENDOR_OUI_PREFIXES["siemens"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 214-1AG40-0XB0",
                "major_minor_revision": "V4.5.2",
                "product_name": "CPU 1214C DC/DC/DC",
                "model_name": "S7-1200",
            },
            "profinet_identity": {
                "vendor_id": 0x002A,
                "device_id": 0x010D,
                "station_name": "plc-s71200",
                "device_role": 1,  # Device
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 214-1AG40-0XB0",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "window_scaling": 5,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 25.0,
                "mean_ms": 6.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # SIMATIC HMI KTP700
        {
            "vendor": "Siemens",
            "vendor_family": "SIMATIC HMI",
            "model": "6AV2 123-2GB03-0AX0",
            "firmware_version": "V17.0.0",
            "oui_prefixes": VENDOR_OUI_PREFIXES["siemens"],
            "profinet_identity": {
                "vendor_id": 0x002A,
                "device_id": 0x0403,
                "station_name": "hmi-ktp700",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6AV2 123-2GB03-0AX0",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 100.0,
                "mean_ms": 25.0,
                "std_dev_ms": 15.0,
                "distribution": "lognormal",
            },
            "is_builtin": True,
        },
    ]


def get_schneider_fingerprints() -> list[dict[str, Any]]:
    """Get Schneider Electric device fingerprints."""
    return [
        # Modicon M580
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon M580",
            "model": "BMEP584040",
            "firmware_version": "3.20",
            "oui_prefixes": VENDOR_OUI_PREFIXES["schneider"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "BMEP584040",
                "major_minor_revision": "3.20",
                "vendor_url": "http://www.schneider-electric.com",
                "product_name": "Modicon M580 ePAC",
                "model_name": "BMEP584040",
            },
            "ethernet_ip_identity": {
                "vendor_id": 67,
                "device_type": 14,
                "product_code": 584,
                "revision_major": 3,
                "revision_minor": 20,
                "serial_number": 0x45678901,
                "product_name": "BMEP584040",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,  # VxWorks
                "window_size": 32768,
                "mss": 1460,
                "window_scaling": None,
                "sack_permitted": True,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 20.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.5,
                "distribution": "gaussian",
                "outlier_probability": 0.008,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6, 10, 11],
                "exception_probability": 0.0006,
            },
            "protocol_quirks": {
                "modbus_max_registers": 125,
                "modbus_max_coils": 2000,
            },
            "is_builtin": True,
        },
        # Modicon M241
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon M241",
            "model": "TM241CE40R",
            "firmware_version": "5.1.0",
            "oui_prefixes": VENDOR_OUI_PREFIXES["schneider"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TM241CE40R",
                "major_minor_revision": "5.1.0",
                "product_name": "Modicon M241 Logic Controller",
                "model_name": "TM241CE40R",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 1.5,
                "max_ms": 35.0,
                "mean_ms": 8.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Altivar Process ATV630
        {
            "vendor": "Schneider",
            "vendor_family": "Altivar",
            "model": "ATV630D15N4",
            "firmware_version": "V2.7",
            "oui_prefixes": VENDOR_OUI_PREFIXES["schneider"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "ATV630D15N4",
                "major_minor_revision": "V2.7",
                "product_name": "Altivar Process ATV630",
                "model_name": "Variable Speed Drive",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "exponential",
            },
            "is_builtin": True,
        },
    ]


def get_abb_fingerprints() -> list[dict[str, Any]]:
    """Get ABB device fingerprints."""
    return [
        # AC500 PM5630
        {
            "vendor": "ABB",
            "vendor_family": "AC500",
            "model": "PM5630-2ETH",
            "firmware_version": "3.2.0",
            "oui_prefixes": VENDOR_OUI_PREFIXES["abb"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "PM5630-2ETH",
                "major_minor_revision": "3.2.0",
                "vendor_url": "http://www.abb.com",
                "product_name": "AC500-eCo PLC",
                "model_name": "PM5630",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 30.0,
                "mean_ms": 7.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
    ]


def get_honeywell_fingerprints() -> list[dict[str, Any]]:
    """Get Honeywell device fingerprints."""
    return [
        # ControlEdge PLC
        {
            "vendor": "Honeywell",
            "vendor_family": "ControlEdge",
            "model": "LCNP4M",
            "firmware_version": "R430.1",
            "oui_prefixes": VENDOR_OUI_PREFIXES["honeywell"],
            "modbus_identity": {
                "vendor_name": "Honeywell International Inc.",
                "product_code": "LCNP4M",
                "major_minor_revision": "R430.1",
                "product_name": "ControlEdge PLC",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 15.0,
                "mean_ms": 3.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
    ]


def get_emerson_fingerprints() -> list[dict[str, Any]]:
    """Get Emerson device fingerprints."""
    return [
        # DeltaV Controller
        {
            "vendor": "Emerson",
            "vendor_family": "DeltaV",
            "model": "S-series Controller",
            "firmware_version": "14.3",
            "oui_prefixes": VENDOR_OUI_PREFIXES["emerson"],
            "modbus_identity": {
                "vendor_name": "Emerson Process Management",
                "product_code": "DeltaV-S",
                "major_minor_revision": "14.3",
                "product_name": "DeltaV S-series Controller",
            },
            "tcp_stack": {
                "ttl": 128,  # Windows-based
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 0.8,
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # ROC800
        {
            "vendor": "Emerson",
            "vendor_family": "ROC",
            "model": "ROC800L",
            "firmware_version": "3.80",
            "oui_prefixes": VENDOR_OUI_PREFIXES["emerson"],
            "modbus_identity": {
                "vendor_name": "Emerson Process Management",
                "product_code": "ROC800L",
                "major_minor_revision": "3.80",
                "product_name": "ROC800L Remote Operations Controller",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 100.0,
                "mean_ms": 25.0,
                "std_dev_ms": 15.0,
                "distribution": "lognormal",
            },
            "is_builtin": True,
        },
    ]


def get_ge_fingerprints() -> list[dict[str, Any]]:
    """Get GE device fingerprints."""
    return [
        # PACSystems RX3i
        {
            "vendor": "GE",
            "vendor_family": "PACSystems",
            "model": "IC695CPE400",
            "firmware_version": "9.70",
            "oui_prefixes": VENDOR_OUI_PREFIXES["ge"],
            "modbus_identity": {
                "vendor_name": "GE Automation",
                "product_code": "IC695CPE400",
                "major_minor_revision": "9.70",
                "vendor_url": "http://www.geautomation.com",
                "product_name": "PACSystems RX3i CPE400",
            },
            "ethernet_ip_identity": {
                "vendor_id": 82,
                "device_type": 14,
                "product_code": 400,
                "revision_major": 9,
                "revision_minor": 70,
                "serial_number": 0x56789012,
                "product_name": "CPE400",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 15.0,
                "mean_ms": 3.5,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Mark VIe Controller
        {
            "vendor": "GE",
            "vendor_family": "Mark VIe",
            "model": "IS420UCSBH1A",
            "firmware_version": "6.03",
            "oui_prefixes": VENDOR_OUI_PREFIXES["ge"],
            "modbus_identity": {
                "vendor_name": "GE Energy",
                "product_code": "IS420UCSBH1A",
                "major_minor_revision": "6.03",
                "product_name": "Mark VIe Controller",
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 0.3,
                "max_ms": 10.0,
                "mean_ms": 2.0,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
    ]


def get_all_vendor_fingerprints() -> list[dict[str, Any]]:
    """Get all vendor fingerprints for seeding."""
    fingerprints = []
    fingerprints.extend(get_rockwell_fingerprints())
    fingerprints.extend(get_siemens_fingerprints())
    fingerprints.extend(get_schneider_fingerprints())
    fingerprints.extend(get_abb_fingerprints())
    fingerprints.extend(get_honeywell_fingerprints())
    fingerprints.extend(get_emerson_fingerprints())
    fingerprints.extend(get_ge_fingerprints())
    return fingerprints


def get_fingerprint_by_vendor_model(vendor: str, model: str) -> dict[str, Any] | None:
    """Find a fingerprint by vendor and model."""
    for fp in get_all_vendor_fingerprints():
        if fp["vendor"].lower() == vendor.lower() and fp.get("model") == model:
            return fp
    return None


def get_fingerprints_by_vendor(vendor: str) -> list[dict[str, Any]]:
    """Get all fingerprints for a vendor."""
    return [
        fp
        for fp in get_all_vendor_fingerprints()
        if fp["vendor"].lower() == vendor.lower()
    ]


def get_random_oui_for_vendor(vendor: str) -> str | None:
    """Get a random OUI prefix for a vendor."""
    import random

    ouis = VENDOR_OUI_PREFIXES.get(vendor.lower(), [])
    return random.choice(ouis) if ouis else None
