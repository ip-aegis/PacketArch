"""Schneider Electric device fingerprints.

Comprehensive fingerprint data for Schneider Electric devices
including Modicon M580, M580 Safety, M340, M241, M251, M262,
Altivar drives, Lexium servos, Magelis HMIs, and TM3 I/O modules.

Based on real device characteristics for realistic traffic simulation.
"""

from typing import Any

# Schneider Electric MAC OUI Prefixes (IEEE registrations)
SCHNEIDER_OUI_PREFIXES = [
    "00:00:54",  # Schneider Electric
    "00:80:F4",  # Schneider Electric (Telemecanique)
    "EC:FA:AA",  # Schneider Electric
]

# Schneider ODVA Vendor ID
SCHNEIDER_ODVA_VENDOR_ID = 67


def get_schneider_fingerprints() -> list[dict[str, Any]]:
    """Get all Schneider Electric device fingerprints."""
    return [
        # ============================================================
        # Modicon M580 PLCs
        # ============================================================
        # M580 BMEP586040 (Standard)
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon M580",
            "model": "BMEP586040",
            "firmware_version": "3.30",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "BMEP586040",
                "major_minor_revision": "3.30",
                "vendor_url": "http://www.schneider-electric.com",
                "product_name": "Modicon M580 ePAC",
                "model_name": "BMEP586040",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Modicon M580 BMEP586040 Firmware V3.30",
                "sys_name": "M580-BMEP586040",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.580",
                "sys_location": "Control Room",
            },
            "ethernet_ip_identity": {
                "vendor_id": SCHNEIDER_ODVA_VENDOR_ID,
                "device_type": 14,  # PLC
                "product_code": 586,
                "revision_major": 3,
                "revision_minor": 30,
                "serial_number": 0x12AB34CD,
                "product_name": "BMEP586040",
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
                "unity_pro_compatible": True,
            },
            "is_builtin": True,
        },
        # M580 BMEH586040 (Hot Standby)
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon M580",
            "model": "BMEH586040",
            "firmware_version": "3.30",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "BMEH586040",
                "major_minor_revision": "3.30",
                "vendor_url": "http://www.schneider-electric.com",
                "product_name": "Modicon M580 ePAC Hot Standby",
                "model_name": "BMEH586040",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Modicon M580 BMEH586040 Hot Standby Firmware V3.30",
                "sys_name": "M580-BMEH586040",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.580",
                "sys_location": "Control Room",
            },
            "ethernet_ip_identity": {
                "vendor_id": SCHNEIDER_ODVA_VENDOR_ID,
                "device_type": 14,
                "product_code": 587,
                "revision_major": 3,
                "revision_minor": 30,
                "serial_number": 0x23BC45DE,
                "product_name": "BMEH586040",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 18.0,
                "mean_ms": 3.5,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6, 10, 11],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0001,
            },
            "protocol_quirks": {
                "modbus_max_registers": 125,
                "hot_standby_enabled": True,
            },
            "is_builtin": True,
        },
        # M580 Safety BMEP586040S
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon M580 Safety",
            "model": "BMEP586040S",
            "firmware_version": "3.20",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "BMEP586040S",
                "major_minor_revision": "3.20",
                "vendor_url": "http://www.schneider-electric.com",
                "product_name": "Modicon M580 Safety ePAC",
                "model_name": "BMEP586040S",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Modicon M580 Safety BMEP586040S Firmware V3.20",
                "sys_name": "M580S-BMEP586040S",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.580",
                "sys_location": "Safety Zone",
            },
            "ethernet_ip_identity": {
                "vendor_id": SCHNEIDER_ODVA_VENDOR_ID,
                "device_type": 14,
                "product_code": 588,
                "revision_major": 3,
                "revision_minor": 20,
                "serial_number": 0x34CD56EF,
                "product_name": "BMEP586040S",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 0.4,
                "max_ms": 15.0,
                "mean_ms": 3.0,
                "std_dev_ms": 1.8,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0002,
                "timeout_probability": 0.00005,
            },
            "protocol_quirks": {
                "modbus_max_registers": 125,
                "cip_safety_enabled": True,
            },
            "safety_config": {
                "sil_level": "SIL3",
                "category": "Cat4",
                "cip_safety_enabled": True,
                "safety_watchdog_ms": 50,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Modicon M340 PLCs
        # ============================================================
        # M340 BMXP3420302
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon M340",
            "model": "BMXP3420302",
            "firmware_version": "3.51",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "BMXP3420302",
                "major_minor_revision": "3.51",
                "vendor_url": "http://www.schneider-electric.com",
                "product_name": "Modicon M340 CPU",
                "model_name": "BMXP3420302",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Modicon M340 BMXP3420302 Firmware V3.51",
                "sys_name": "M340-BMXP3420302",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.340",
                "sys_location": "Control Cabinet",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 30.0,
                "mean_ms": 7.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0008,
                "timeout_probability": 0.0004,
            },
            "protocol_quirks": {
                "modbus_max_registers": 120,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Modicon M241/M251/M262 Compact PLCs
        # ============================================================
        # M241 TM241CE40R
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon M241",
            "model": "TM241CE40R",
            "firmware_version": "5.1.62",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TM241CE40R",
                "major_minor_revision": "5.1.62",
                "product_name": "Modicon M241 Logic Controller",
                "model_name": "TM241CE40R",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Modicon M241 TM241CE40R Firmware V5.1.62",
                "sys_name": "M241-TM241CE40R",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.241",
                "sys_location": "Machine Cabinet",
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
                "outlier_probability": 0.006,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.001,
                "timeout_probability": 0.0005,
            },
            "is_builtin": True,
        },
        # M251 TM251MESE
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon M251",
            "model": "TM251MESE",
            "firmware_version": "5.1.62",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TM251MESE",
                "major_minor_revision": "5.1.62",
                "product_name": "Modicon M251 Logic Controller",
                "model_name": "TM251MESE",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Modicon M251 TM251MESE Firmware V5.1.62",
                "sys_name": "M251-TM251MESE",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.251",
                "sys_location": "Machine Cabinet",
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
                "max_ms": 40.0,
                "mean_ms": 10.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.008,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0012,
                "timeout_probability": 0.0006,
            },
            "is_builtin": True,
        },
        # M262 TM262L20MESE8T
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon M262",
            "model": "TM262L20MESE8T",
            "firmware_version": "2.0.11",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TM262L20MESE8T",
                "major_minor_revision": "2.0.11",
                "product_name": "Modicon M262 Logic/Motion Controller",
                "model_name": "TM262L20MESE8T",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Modicon M262 TM262L20MESE8T Firmware V2.0.11",
                "sys_name": "M262-TM262L20MESE8T",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.262",
                "sys_location": "Machine Cabinet",
            },
            "ethernet_ip_identity": {
                "vendor_id": SCHNEIDER_ODVA_VENDOR_ID,
                "device_type": 14,
                "product_code": 262,
                "revision_major": 2,
                "revision_minor": 11,
                "serial_number": 0x45DE67F0,
                "product_name": "TM262L20MESE8T",
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
                "min_ms": 0.8,
                "max_ms": 25.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0006,
                "timeout_probability": 0.0003,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Altivar Drives
        # ============================================================
        # Altivar ATV930
        {
            "vendor": "Schneider",
            "vendor_family": "Altivar Process",
            "model": "ATV930D15N4",
            "firmware_version": "V2.9",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "ATV930D15N4",
                "major_minor_revision": "V2.9",
                "product_name": "Altivar Process ATV930",
                "model_name": "Variable Speed Drive",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Altivar Process ATV930D15N4 Firmware V2.9",
                "sys_name": "ATV930-D15N4",
                "sys_object_id": "1.3.6.1.4.1.3833.1.200.930",
                "sys_location": "Drive Cabinet",
            },
            "ethernet_ip_identity": {
                "vendor_id": SCHNEIDER_ODVA_VENDOR_ID,
                "device_type": 2,  # AC Drive
                "product_code": 930,
                "revision_major": 2,
                "revision_minor": 9,
                "serial_number": 0x56EF7801,
                "product_name": "ATV930D15N4",
                "state": 3,
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
                "max_ms": 45.0,
                "mean_ms": 12.0,
                "std_dev_ms": 7.0,
                "distribution": "exponential",
                "outlier_probability": 0.006,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0008,
                "timeout_probability": 0.0004,
            },
            "is_builtin": True,
        },
        # Altivar ATV320
        {
            "vendor": "Schneider",
            "vendor_family": "Altivar Machine",
            "model": "ATV320U22N4C",
            "firmware_version": "V2.1",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "ATV320U22N4C",
                "major_minor_revision": "V2.1",
                "product_name": "Altivar Machine ATV320",
                "model_name": "Variable Speed Drive",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Altivar Machine ATV320U22N4C Firmware V2.1",
                "sys_name": "ATV320-U22N4C",
                "sys_object_id": "1.3.6.1.4.1.3833.1.200.320",
                "sys_location": "Drive Cabinet",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 60.0,
                "mean_ms": 15.0,
                "std_dev_ms": 10.0,
                "distribution": "exponential",
                "outlier_probability": 0.008,
                "outlier_multiplier": 2.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.001,
                "timeout_probability": 0.0005,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Lexium Servo Drives
        # ============================================================
        # Lexium LXM32
        {
            "vendor": "Schneider",
            "vendor_family": "Lexium 32",
            "model": "LXM32MD18M2",
            "firmware_version": "V2.62",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "LXM32MD18M2",
                "major_minor_revision": "V2.62",
                "product_name": "Lexium 32 Servo Drive",
                "model_name": "LXM32",
            },
            "ethernet_ip_identity": {
                "vendor_id": SCHNEIDER_ODVA_VENDOR_ID,
                "device_type": 3,  # Servo Drive
                "product_code": 32,
                "revision_major": 2,
                "revision_minor": 62,
                "serial_number": 0x67F08912,
                "product_name": "LXM32MD18M2",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 15.0,
                "mean_ms": 3.5,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Magelis HMIs
        # ============================================================
        # Magelis HMIST6700
        {
            "vendor": "Schneider",
            "vendor_family": "Magelis STU",
            "model": "HMIST6700",
            "firmware_version": "V6.0",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "HMIST6700",
                "major_minor_revision": "V6.0",
                "product_name": "Magelis STU 7\" Touchscreen",
                "model_name": "HMIST6700",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 80.0,
                "mean_ms": 20.0,
                "std_dev_ms": 12.0,
                "distribution": "lognormal",
                "outlier_probability": 0.01,
                "outlier_multiplier": 2.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0008,
                "timeout_probability": 0.0004,
            },
            "is_builtin": True,
        },
        # Magelis HMISTM6
        {
            "vendor": "Schneider",
            "vendor_family": "Magelis STM",
            "model": "HMISTM6",
            "firmware_version": "V5.0",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "HMISTM6",
                "major_minor_revision": "V5.0",
                "product_name": "Magelis STM Touchscreen",
                "model_name": "HMISTM6",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 120.0,
                "mean_ms": 30.0,
                "std_dev_ms": 18.0,
                "distribution": "lognormal",
                "outlier_probability": 0.012,
                "outlier_multiplier": 2.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.001,
                "timeout_probability": 0.0005,
            },
            "is_builtin": True,
        },
        # ============================================================
        # TM3 Distributed I/O
        # ============================================================
        # TM3 TM3DI32K
        {
            "vendor": "Schneider",
            "vendor_family": "TM3",
            "model": "TM3DI32K",
            "firmware_version": "V1.2",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TM3DI32K",
                "major_minor_revision": "V1.2",
                "product_name": "TM3 32 Input Module",
                "model_name": "TM3DI32K",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 10.0,
                "mean_ms": 2.5,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0003,
                "timeout_probability": 0.00015,
            },
            "is_builtin": True,
        },
        # Advantys STB
        {
            "vendor": "Schneider",
            "vendor_family": "Advantys STB",
            "model": "STBNIP2311",
            "firmware_version": "V5.0",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "STBNIP2311",
                "major_minor_revision": "V5.0",
                "product_name": "Advantys STB Ethernet Network Interface",
                "model_name": "STBNIP2311",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 15.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.5,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Legacy Modicon Premium PLCs (Water/Wastewater)
        # ============================================================
        # Modicon Premium TSXP57204M
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon Premium",
            "model": "TSXP57204M",
            "firmware_version": "3.60",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TSXP57204M",
                "major_minor_revision": "3.60",
                "vendor_url": "http://www.schneider-electric.com",
                "product_name": "Modicon Premium PLC",
                "model_name": "TSXP57204M",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Modicon Premium TSXP57204M Firmware V3.60",
                "sys_name": "PREMIUM-TSXP57204M",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.57",
                "sys_location": "Control Room",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 60.0,
                "mean_ms": 15.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
                "outlier_probability": 0.008,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.001,
                "timeout_probability": 0.0005,
            },
            "protocol_quirks": {
                "modbus_max_registers": 100,
                "unity_pro_compatible": False,  # Uses older software
                "ftp_enabled": True,  # CVE-2018-7760 - hardcoded FTP creds
            },
            "is_builtin": True,
        },
        # Modicon Premium TSXP57154M (Compact version)
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon Premium",
            "model": "TSXP57154M",
            "firmware_version": "3.60",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TSXP57154M",
                "major_minor_revision": "3.60",
                "vendor_url": "http://www.schneider-electric.com",
                "product_name": "Modicon Premium PLC",
                "model_name": "TSXP57154M",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Modicon Premium TSXP57154M Firmware V3.60",
                "sys_name": "PREMIUM-TSXP57154M",
                "sys_object_id": "1.3.6.1.4.1.3833.1.100.57",
                "sys_location": "Remote Station",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 4.0,
                "max_ms": 80.0,
                "mean_ms": 20.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 2.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0015,
                "timeout_probability": 0.0008,
            },
            "protocol_quirks": {
                "modbus_max_registers": 100,
                "unity_pro_compatible": False,
                "ftp_enabled": True,  # CVE-2018-7760 - hardcoded FTP creds
            },
            "is_builtin": True,
        },
        # ============================================================
        # Network Infrastructure
        # ============================================================
        # ConneXium Switch - Managed industrial Ethernet switch with SNMP support
        {
            "vendor": "Schneider",
            "vendor_family": "ConneXium",
            "model": "TCSESM083F2CU0",
            "firmware_version": "V6.2",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TCSESM083F2CU0",
                "major_minor_revision": "V6.2",
                "product_name": "ConneXium Managed Switch",
                "model_name": "TCSESM083F2CU0",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric ConneXium TCSESM083F2CU0 Managed Switch V6.2",
                "sys_object_id": "1.3.6.1.4.1.3833.1.7.255",
                "sys_name": "CONNEXIUM-SW",
                "sys_location": "Industrial Network",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 4096,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0003,
                "timeout_probability": 0.00015,
            },
            "is_builtin": True,
        },

        # ============================================================
        # ALTIVAR VARIABLE FREQUENCY DRIVES
        # ============================================================
        # ATV930 (High-performance process drive)
        {
            "vendor": "Schneider",
            "vendor_family": "Altivar",
            "model": "ATV930",
            "firmware_version": "V2.1IE26",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "ATV930",
                "major_minor_revision": "V2.1IE26",
                "product_name": "Altivar Process ATV930",
                "model_name": "ATV930",
            },
            "ethernet_ip_identity": {
                "vendor_id": 67,  # Schneider
                "device_type": 22,  # AC Drive
                "product_code": 930,
                "revision_major": 2,
                "revision_minor": 1,
                "product_name": "Altivar Process ATV930",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0005,
                "timeout_probability": 0.0002,
            },
            "is_builtin": True,
        },
        # ATV320 (Compact machinery drive)
        {
            "vendor": "Schneider",
            "vendor_family": "Altivar",
            "model": "ATV320",
            "firmware_version": "V1.7IE18",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "ATV320",
                "major_minor_revision": "V1.7IE18",
                "product_name": "Altivar Machine ATV320",
                "model_name": "ATV320",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 4096,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.008,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0008,
                "timeout_probability": 0.0003,
            },
            "is_builtin": True,
        },

        # ============================================================
        # MODICON TM5 SAFETY I/O
        # ============================================================
        # TM5CSLC100FS (Safety Logic Controller)
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon TM5",
            "model": "TM5CSLC100FS",
            "firmware_version": "V1.40",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TM5CSLC100FS",
                "major_minor_revision": "V1.40",
                "product_name": "TM5 Safety Logic Controller",
                "model_name": "TM5CSLC100FS",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 15.0,
                "mean_ms": 5.0,
                "std_dev_ms": 2.5,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 2.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "protocol_quirks": {
                "safety_certified": True,
                "sil_level": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # ADVANTYS STB DISTRIBUTED I/O
        # ============================================================
        # STB NIP 2311 (Network Interface Processor)
        {
            "vendor": "Schneider",
            "vendor_family": "Advantys STB",
            "model": "STB NIP 2311",
            "firmware_version": "V6.0",
            "oui_prefixes": SCHNEIDER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "STBNIP2311",
                "major_minor_revision": "V6.0",
                "product_name": "Advantys STB Network Interface",
                "model_name": "STB NIP 2311",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 4096,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 20.0,
                "mean_ms": 6.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0005,
                "timeout_probability": 0.0002,
            },
            "is_builtin": True,
        },
    ]
