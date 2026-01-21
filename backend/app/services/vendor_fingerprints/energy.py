"""Energy/Power vertical vendor fingerprints.

Fingerprint data for protection relays, power meters, and substation equipment
used in electric utility SCADA systems. These fingerprints enable realistic
traffic generation and Cyber Vision device detection.

Vendors covered:
- SEL (Schweitzer Engineering Laboratories) - Protection relays
- Siemens SIPROTEC - Protection relays
- GE Multilin - Protection relays
- ABB Relion - Protection relays
- Basler Electric - Excitation systems
- Beckwith Electric - Transformer protection
"""

from typing import Any

# MAC OUI Prefixes for energy/protection vendors (IEEE registrations)
SEL_OUI_PREFIXES = [
    "00:30:A7",  # Schweitzer Engineering Laboratories
    "00:1C:73",  # SEL Inc
]

SIEMENS_PROTECTION_OUI_PREFIXES = [
    "00:0E:8C",  # Siemens AG
    "00:1C:06",  # Siemens AG A&D
    "74:DA:EA",  # Siemens Industrial
]

GE_MULTILIN_OUI_PREFIXES = [
    "00:22:52",  # GE Digital Energy
    "00:04:A5",  # GE Intelligent Platforms
]

BASLER_OUI_PREFIXES = [
    "00:1E:C9",  # Basler Electric
]


def get_energy_fingerprints() -> list[dict[str, Any]]:
    """Get all energy/power vertical fingerprints."""
    return [
        # ==================== SEL Protection Relays ====================

        # SEL-751 Feeder Protection Relay
        {
            "vendor": "SEL",
            "vendor_family": "Protection Relay",
            "model": "SEL-751",
            "firmware_version": "R144-V0",
            "device_type": "protection_relay",
            "oui_prefixes": SEL_OUI_PREFIXES,
            "supported_protocols": ["modbus", "dnp3", "iec104"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Schweitzer Engineering Laboratories",
                "product_code": "0751",
                "major_minor_revision": "R144-V0",
                "vendor_url": "https://selinc.com",
                "product_name": "SEL-751 Feeder Protection Relay",
                "model_name": "SEL-751",
            },
            "dnp3_identity": {
                "vendor_name": "SEL",
                "device_serial": "751-001",
                "hardware_version": "751A",
                "software_version": "R144-V0",
            },
            "iec104_identity": {
                "station_name": "SEL-751",
                "common_address": 1,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "options": ["timestamps", "sack"],
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 35.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        },

        # SEL-451 Bay Controller
        {
            "vendor": "SEL",
            "vendor_family": "Protection Relay",
            "model": "SEL-451",
            "firmware_version": "R320-V0",
            "device_type": "protection_relay",
            "oui_prefixes": SEL_OUI_PREFIXES,
            "supported_protocols": ["modbus", "dnp3", "iec104"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Schweitzer Engineering Laboratories",
                "product_code": "0451",
                "major_minor_revision": "R320-V0",
                "vendor_url": "https://selinc.com",
                "product_name": "SEL-451 Bay Controller",
                "model_name": "SEL-451",
            },
            "dnp3_identity": {
                "vendor_name": "SEL",
                "device_serial": "451-001",
                "hardware_version": "451-5",
                "software_version": "R320-V0",
            },
            "iec104_identity": {
                "station_name": "SEL-451",
                "common_address": 1,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "options": ["timestamps", "sack"],
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0001,
                "timeout_probability": 0.0001,
            },
        },

        # SEL-311C Line Protection
        {
            "vendor": "SEL",
            "vendor_family": "Protection Relay",
            "model": "SEL-311C",
            "firmware_version": "R501-V0",
            "device_type": "protection_relay",
            "oui_prefixes": SEL_OUI_PREFIXES,
            "supported_protocols": ["modbus", "dnp3"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Schweitzer Engineering Laboratories",
                "product_code": "311C",
                "major_minor_revision": "R501-V0",
                "vendor_url": "https://selinc.com",
                "product_name": "SEL-311C Line Protection",
                "model_name": "SEL-311C",
            },
            "dnp3_identity": {
                "vendor_name": "SEL",
                "device_serial": "311C-001",
                "hardware_version": "311C",
                "software_version": "R501-V0",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.5,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0001,
                "timeout_probability": 0.0001,
            },
        },

        # SEL-487E Transformer Protection
        {
            "vendor": "SEL",
            "vendor_family": "Protection Relay",
            "model": "SEL-487E",
            "firmware_version": "R103-V0",
            "device_type": "protection_relay",
            "oui_prefixes": SEL_OUI_PREFIXES,
            "supported_protocols": ["modbus", "dnp3"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Schweitzer Engineering Laboratories",
                "product_code": "487E",
                "major_minor_revision": "R103-V0",
                "vendor_url": "https://selinc.com",
                "product_name": "SEL-487E Transformer Protection",
                "model_name": "SEL-487E",
            },
            "dnp3_identity": {
                "vendor_name": "SEL",
                "device_serial": "487E-001",
                "hardware_version": "487E",
                "software_version": "R103-V0",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0001,
                "timeout_probability": 0.0001,
            },
        },

        # SEL-2411 Programmable Automation Controller
        {
            "vendor": "SEL",
            "vendor_family": "Automation Controller",
            "model": "SEL-2411",
            "firmware_version": "R117-V0",
            "device_type": "rtu",
            "oui_prefixes": SEL_OUI_PREFIXES,
            "supported_protocols": ["modbus", "dnp3", "iec104"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Schweitzer Engineering Laboratories",
                "product_code": "2411",
                "major_minor_revision": "R117-V0",
                "vendor_url": "https://selinc.com",
                "product_name": "SEL-2411 Programmable Automation Controller",
                "model_name": "SEL-2411",
            },
            "dnp3_identity": {
                "vendor_name": "SEL",
                "device_serial": "2411-001",
                "hardware_version": "2411",
                "software_version": "R117-V0",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 7.0,
                "std_dev_ms": 4.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0001,
                "timeout_probability": 0.0001,
            },
        },

        # ==================== Siemens SIPROTEC Protection Relays ====================

        # SIPROTEC 7SJ85 Overcurrent Protection
        {
            "vendor": "Siemens",
            "vendor_family": "SIPROTEC 5",
            "model": "7SJ85",
            "firmware_version": "V08.30",
            "device_type": "protection_relay",
            "oui_prefixes": SIEMENS_PROTECTION_OUI_PREFIXES,
            "supported_protocols": ["modbus", "iec104"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "7SJ85",
                "major_minor_revision": "V08.30",
                "vendor_url": "https://siemens.com",
                "product_name": "SIPROTEC 7SJ85 Overcurrent Protection",
                "model_name": "SIPROTEC 5",
            },
            "iec104_identity": {
                "station_name": "7SJ85",
                "common_address": 1,
                "vendor_id": 24,  # Siemens BACnet vendor ID
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "options": ["timestamps"],
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 40.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        },

        # SIPROTEC 7SL87 Line Differential Protection
        {
            "vendor": "Siemens",
            "vendor_family": "SIPROTEC 5",
            "model": "7SL87",
            "firmware_version": "V08.30",
            "device_type": "protection_relay",
            "oui_prefixes": SIEMENS_PROTECTION_OUI_PREFIXES,
            "supported_protocols": ["modbus", "iec104"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "7SL87",
                "major_minor_revision": "V08.30",
                "vendor_url": "https://siemens.com",
                "product_name": "SIPROTEC 7SL87 Line Differential",
                "model_name": "SIPROTEC 5",
            },
            "iec104_identity": {
                "station_name": "7SL87",
                "common_address": 1,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 45.0,
                "mean_ms": 16.0,
                "std_dev_ms": 9.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        },

        # SIPROTEC 7UT87 Transformer Differential
        {
            "vendor": "Siemens",
            "vendor_family": "SIPROTEC 5",
            "model": "7UT87",
            "firmware_version": "V08.30",
            "device_type": "protection_relay",
            "oui_prefixes": SIEMENS_PROTECTION_OUI_PREFIXES,
            "supported_protocols": ["modbus", "dnp3", "iec104"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "7UT87",
                "major_minor_revision": "V08.30",
                "vendor_url": "https://siemens.com",
                "product_name": "SIPROTEC 7UT87 Transformer Differential",
                "model_name": "SIPROTEC 5",
            },
            "iec104_identity": {
                "station_name": "7UT87",
                "common_address": 1,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 18.0,
                "std_dev_ms": 10.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        },

        # SIPROTEC 7SD87 Distance Protection
        {
            "vendor": "Siemens",
            "vendor_family": "SIPROTEC 5",
            "model": "7SD87",
            "firmware_version": "V08.30",
            "device_type": "protection_relay",
            "oui_prefixes": SIEMENS_PROTECTION_OUI_PREFIXES,
            "supported_protocols": ["modbus", "dnp3", "iec104"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "7SD87",
                "major_minor_revision": "V08.30",
                "vendor_url": "https://siemens.com",
                "product_name": "SIPROTEC 7SD87 Distance Protection",
                "model_name": "SIPROTEC 5",
            },
            "iec104_identity": {
                "station_name": "7SD87",
                "common_address": 1,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 45.0,
                "mean_ms": 16.0,
                "std_dev_ms": 8.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        },

        # ==================== GE Multilin Protection Relays ====================

        # GE Multilin 850 Feeder Protection
        {
            "vendor": "GE",
            "vendor_family": "Multilin",
            "model": "850",
            "firmware_version": "7.30",
            "device_type": "protection_relay",
            "oui_prefixes": GE_MULTILIN_OUI_PREFIXES,
            "supported_protocols": ["modbus", "dnp3"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "GE Digital Energy",
                "product_code": "850",
                "major_minor_revision": "7.30",
                "vendor_url": "https://gegridsolutions.com",
                "product_name": "Multilin 850 Feeder Protection System",
                "model_name": "Multilin 850",
            },
            "dnp3_identity": {
                "vendor_name": "GE",
                "device_serial": "850-001",
                "hardware_version": "850",
                "software_version": "7.30",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 4.0,
                "max_ms": 35.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        },

        # GE Multilin F650 Digital Bay Controller
        {
            "vendor": "GE",
            "vendor_family": "Multilin",
            "model": "F650",
            "firmware_version": "5.90",
            "device_type": "protection_relay",
            "oui_prefixes": GE_MULTILIN_OUI_PREFIXES,
            "supported_protocols": ["modbus", "dnp3"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "GE Digital Energy",
                "product_code": "F650",
                "major_minor_revision": "5.90",
                "vendor_url": "https://gegridsolutions.com",
                "product_name": "Multilin F650 Digital Bay Controller",
                "model_name": "Multilin F650",
            },
            "dnp3_identity": {
                "vendor_name": "GE",
                "device_serial": "F650-001",
                "hardware_version": "F650",
                "software_version": "5.90",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0001,
                "timeout_probability": 0.0001,
            },
        },

        # GE Multilin T60 Transformer Protection
        {
            "vendor": "GE",
            "vendor_family": "Multilin",
            "model": "T60",
            "firmware_version": "7.5",
            "device_type": "protection_relay",
            "oui_prefixes": GE_MULTILIN_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp", "dnp3"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "GE Digital Energy",
                "product_code": "T60",
                "major_minor_revision": "7.5",
                "vendor_url": "https://gegridsolutions.com",
                "product_name": "Multilin T60 Transformer Protection",
                "model_name": "Multilin T60",
            },
            "dnp3_identity": {
                "vendor_name": "GE",
                "device_serial": "T60-001",
                "hardware_version": "T60",
                "software_version": "7.5",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 4.0,
                "max_ms": 40.0,
                "mean_ms": 14.0,
                "std_dev_ms": 7.0,
                "distribution": "lognormal",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        },

        # ==================== Power Meters ====================

        # Schneider ION8650 Power Quality Meter
        {
            "vendor": "Schneider",
            "vendor_family": "ION",
            "model": "ION8650",
            "firmware_version": "4.03.10",
            "device_type": "meter",
            "oui_prefixes": ["00:80:F4", "00:04:A3"],  # Schneider Electric
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "ION8650",
                "major_minor_revision": "4.03.10",
                "vendor_url": "https://se.com",
                "product_name": "ION8650 Power Quality Meter",
                "model_name": "ION8650",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric ION8650 Power Quality Meter Firmware 4.03.10",
                "sys_name": "ION8650",
                "sys_object_id": "1.3.6.1.4.1.3833.1.7.8650",
                "sys_location": "Electrical Room",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 20.0,
                "std_dev_ms": 10.0,
                "distribution": "lognormal",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0002,
            },
        },

        # Schneider PM8000 Power Meter
        {
            "vendor": "Schneider",
            "vendor_family": "PowerLogic",
            "model": "PM8000",
            "firmware_version": "3.0.0",
            "device_type": "meter",
            "oui_prefixes": ["00:80:F4", "00:04:A3"],
            "is_builtin": True,
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "PM8000",
                "major_minor_revision": "3.0.0",
                "vendor_url": "https://se.com",
                "product_name": "PowerLogic PM8000 Power Meter",
                "model_name": "PM8000",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric PowerLogic PM8000 Power Meter Firmware 3.0.0",
                "sys_name": "PM8000",
                "sys_object_id": "1.3.6.1.4.1.3833.1.7.8000",
                "sys_location": "Electrical Room",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 45.0,
                "mean_ms": 18.0,
                "std_dev_ms": 9.0,
                "distribution": "lognormal",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0002,
            },
        },
    ]


__all__ = [
    "SEL_OUI_PREFIXES",
    "SIEMENS_PROTECTION_OUI_PREFIXES",
    "GE_MULTILIN_OUI_PREFIXES",
    "BASLER_OUI_PREFIXES",
    "get_energy_fingerprints",
]
