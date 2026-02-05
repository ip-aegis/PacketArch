"""Specialty OT vendor fingerprints.

Fingerprint data for specialty OT vendors that appear in industrial scenarios
but are not the primary automation vendors. Includes instrument vendors,
sensor manufacturers, and control valve suppliers.

Vendors covered:
- SICK AG (vision systems, barcode scanners)
- Yokogawa (process analyzers, transmitters)
- Endress+Hauser (flow meters, level transmitters)
- Honeywell (leak detection, process analytics)
- ABB (protection relays, motors, drives)
- Emerson (control valves, DeltaV systems)
"""

from typing import Any

# MAC OUI Prefixes for specialty vendors (IEEE registrations)
SICK_OUI_PREFIXES = [
    "00:06:6F",  # SICK AG
    "00:10:BE",  # SICK AG
]

YOKOGAWA_OUI_PREFIXES = [
    "00:00:C1",  # Yokogawa Electric
    "00:02:E0",  # Yokogawa Electric
]

ENDRESS_HAUSER_OUI_PREFIXES = [
    "00:0B:CD",  # Endress+Hauser
    "00:80:A3",  # Endress+Hauser
]

HONEYWELL_OUI_PREFIXES = [
    "00:40:84",  # Honeywell Inc (IEEE MA-L, 2000)
    "00:22:6A",  # Honeywell (IEEE MA-L, 2008)
    "C4:EF:DA",  # Honeywell (IEEE MA-L, 2022)
    "58:FC:C8",  # Honeywell (IEEE MA-L, 2023)
]

ABB_OUI_PREFIXES = [
    "00:20:99",  # ABB Industrial Systems
    "00:21:99",  # ABB STOTZ-KONTAKT
    "CC:DA:0C",  # ABB
]

EMERSON_OUI_PREFIXES = [
    # NOTE: Emerson/Fisher-Rosemount often uses embedded NICs from other vendors.
    # Protocol-based identification (Modbus FC43, EtherNet/IP identity) is more reliable.
    "00:0D:3A",  # Emerson Network Power (verified IEEE)
    # "00:A0:F8" REMOVED - Actually Zebra/Symbol per IEEE
    # "00:03:38" REMOVED - Actually Oak Technology per IEEE
    # "00:90:E8" REMOVED - Actually MOXA per IEEE
]

GE_OUI_PREFIXES = [
    "00:09:45",  # GE Fanuc Automation (verified IEEE)
    "00:30:C1",  # GE Healthcare (verified IEEE)
    "00:50:99",  # GE Industrial Systems (verified IEEE)
    "00:22:52",  # GE Digital Energy (verified IEEE)
    # "00:1C:C4" REMOVED - Actually Hewlett Packard per IEEE
]


def get_specialty_fingerprints() -> list[dict[str, Any]]:
    """Get all specialty vendor fingerprints."""
    return [
        # ============================================================
        # SICK AG - Vision Systems and Scanners
        # ============================================================
        # SICK Inspector Vision Sensor
        {
            "vendor": "SICK",
            "vendor_family": "Inspector",
            "model": "Inspector P631",
            "firmware_version": "2.4.3",
            "oui_prefixes": SICK_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "ethernet_ip_identity": {
                "vendor_id": 218,  # SICK AG ODVA vendor ID
                "device_type": 43,  # Machine Vision
                "product_code": 631,
                "revision_major": 2,
                "revision_minor": 4,
                "serial_number": 0x51C00001,
                "product_name": "Inspector P631 Vision Sensor",
                "state": 3,
            },
            "modbus_identity": {
                "vendor_name": "SICK AG",
                "product_code": "1085891",
                "major_minor_revision": "V2.4.3",
                "vendor_url": "http://www.sick.com",
                "product_name": "Inspector P631",
                "model_name": "Vision Sensor",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # SICK CLV6xx Barcode Scanner
        {
            "vendor": "SICK",
            "vendor_family": "CLV",
            "model": "CLV650-0120",
            "firmware_version": "5.60",
            "oui_prefixes": SICK_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "ethernet_ip_identity": {
                "vendor_id": 218,
                "device_type": 12,  # Communications Adapter
                "product_code": 650,
                "revision_major": 5,
                "revision_minor": 60,
                "serial_number": 0x51C00002,
                "product_name": "CLV650-0120 Barcode Scanner",
                "state": 3,
            },
            "modbus_identity": {
                "vendor_name": "SICK AG",
                "product_code": "1041807",
                "major_minor_revision": "V5.60",
                "product_name": "CLV650-0120",
                "model_name": "Barcode Scanner",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Yokogawa - Process Analyzers and Transmitters
        # ============================================================
        # Yokogawa TDLS8000 Gas Analyzer
        {
            "vendor": "Yokogawa",
            "vendor_family": "TDLS",
            "model": "TDLS8000",
            "firmware_version": "R1.04.01",
            "oui_prefixes": YOKOGAWA_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "TDLS8000",
                "major_minor_revision": "R1.04.01",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "TDLS8000 Tunable Diode Laser Spectrometer",
                "model_name": "Gas Analyzer",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 100.0,
                "mean_ms": 35.0,
                "std_dev_ms": 15.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Yokogawa EJA530A Pressure Transmitter
        {
            "vendor": "Yokogawa",
            "vendor_family": "EJA",
            "model": "EJA530A",
            "firmware_version": "3.01",
            "oui_prefixes": YOKOGAWA_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "EJA530A",
                "major_minor_revision": "V3.01",
                "product_name": "EJA530A In-Line Mount Gauge Pressure Transmitter",
                "model_name": "Pressure Transmitter",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Yokogawa GC8000 Gas Chromatograph
        {
            "vendor": "Yokogawa",
            "vendor_family": "GC8000",
            "model": "GC8000",
            "firmware_version": "1.10.00",
            "oui_prefixes": YOKOGAWA_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "GC8000",
                "major_minor_revision": "V1.10.00",
                "product_name": "GC8000 Process Gas Chromatograph",
                "model_name": "Gas Chromatograph",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 20.0,
                "max_ms": 200.0,
                "mean_ms": 60.0,
                "std_dev_ms": 30.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Yokogawa FLXA402 - 4-Wire Liquid Analyzer (pH/ORP/Conductivity/DO)
        {
            "vendor": "Yokogawa",
            "vendor_family": "FLXA",
            "model": "FLXA402",
            "firmware_version": "2.02",
            "oui_prefixes": YOKOGAWA_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "FLXA402",
                "major_minor_revision": "V2.02",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "FLXA402 4-Wire Liquid Analyzer",
                "model_name": "Water Quality Analyzer",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 80.0,
                "mean_ms": 28.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Yokogawa SC450G - Turbidity Analyzer
        {
            "vendor": "Yokogawa",
            "vendor_family": "SC450G",
            "model": "SC450G",
            "firmware_version": "1.04",
            "oui_prefixes": YOKOGAWA_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "SC450G",
                "major_minor_revision": "V1.04",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "SC450G Turbidity Analyzer",
                "model_name": "Turbidity Analyzer",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 60.0,
                "mean_ms": 20.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Yokogawa RC400G - Residual Chlorine Analyzer
        {
            "vendor": "Yokogawa",
            "vendor_family": "RC400G",
            "model": "RC400G",
            "firmware_version": "1.05",
            "oui_prefixes": YOKOGAWA_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "RC400G",
                "major_minor_revision": "V1.05",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "RC400G Residual Chlorine Analyzer",
                "model_name": "Chlorine Analyzer",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 65.0,
                "mean_ms": 22.0,
                "std_dev_ms": 11.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Yokogawa - DCS and Safety Systems (Oil & Gas)
        # ============================================================
        # Yokogawa CENTUM VP Field Control Station
        {
            "vendor": "Yokogawa",
            "vendor_family": "CENTUM VP",
            "model": "CENTUM VP",
            "firmware_version": "R6.08.00",
            "oui_prefixes": YOKOGAWA_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "CENTUM-VP",
                "major_minor_revision": "R6.08.00",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "CENTUM VP Field Control Station",
                "model_name": "CENTUM VP",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 35.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Yokogawa ProSafe-RS Safety Instrumented System
        {
            "vendor": "Yokogawa",
            "vendor_family": "ProSafe-RS",
            "model": "ProSafe-RS",
            "firmware_version": "R4.05.00",
            "oui_prefixes": YOKOGAWA_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "ProSafe-RS",
                "major_minor_revision": "R4.05.00",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "ProSafe-RS Safety Instrumented System",
                "model_name": "ProSafe-RS",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.0005,
                "outlier_multiplier": 2.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0001,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Endress+Hauser - Flow and Level Instrumentation
        # ============================================================
        # Endress+Hauser Promag 400 Flow Meter
        {
            "vendor": "Endress+Hauser",
            "vendor_family": "Promag",
            "model": "Promag 400",
            "firmware_version": "01.06.00",
            "oui_prefixes": ENDRESS_HAUSER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Endress+Hauser",
                "product_code": "50W40-UA0A1AA0AAAA",
                "major_minor_revision": "01.06.00",
                "vendor_url": "http://www.endress.com",
                "product_name": "Promag 400 Electromagnetic Flowmeter",
                "model_name": "Electromagnetic Flowmeter",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 40.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Endress+Hauser Proline Promag W 400 - Water/Wastewater Flowmeter
        {
            "vendor": "Endress+Hauser",
            "vendor_family": "Promag",
            "model": "Promag W 400",
            "firmware_version": "01.07.00",
            "oui_prefixes": ENDRESS_HAUSER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Endress+Hauser",
                "product_code": "50W4H-UA0A1AA0AAAA",
                "major_minor_revision": "01.07.00",
                "vendor_url": "http://www.endress.com",
                "product_name": "Proline Promag W 400 Water Flowmeter",
                "model_name": "Water Flowmeter",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 45.0,
                "mean_ms": 14.0,
                "std_dev_ms": 7.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Endress+Hauser Levelflex FMP50 Level Transmitter
        {
            "vendor": "Endress+Hauser",
            "vendor_family": "Levelflex",
            "model": "FMP50",
            "firmware_version": "01.05.00",
            "oui_prefixes": ENDRESS_HAUSER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Endress+Hauser",
                "product_code": "FMP50-ABC1A1AVDWJ",
                "major_minor_revision": "01.05.00",
                "product_name": "Levelflex FMP50 Guided Radar",
                "model_name": "Level Transmitter",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Endress+Hauser Prosonic S FMU90 - Ultrasonic Level (water/wastewater tanks)
        {
            "vendor": "Endress+Hauser",
            "vendor_family": "Prosonic",
            "model": "FMU90",
            "firmware_version": "01.04.00",
            "oui_prefixes": ENDRESS_HAUSER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Endress+Hauser",
                "product_code": "FMU90-R11CA111AA3A",
                "major_minor_revision": "01.04.00",
                "vendor_url": "http://www.endress.com",
                "product_name": "Prosonic S FMU90 Ultrasonic Level",
                "model_name": "Ultrasonic Level Transmitter",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 60.0,
                "mean_ms": 20.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
            "is_builtin": True,
        },
        # Endress+Hauser Liquiline CM442 Analyzer
        {
            "vendor": "Endress+Hauser",
            "vendor_family": "Liquiline",
            "model": "CM442",
            "firmware_version": "01.09.00",
            "oui_prefixes": ENDRESS_HAUSER_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Endress+Hauser",
                "product_code": "CM442-AAM1A1A001",
                "major_minor_revision": "01.09.00",
                "product_name": "Liquiline CM442 Multiparameter Controller",
                "model_name": "Water Quality Analyzer",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 80.0,
                "mean_ms": 25.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Honeywell - Analytics and Detection Systems
        # ============================================================
        # Honeywell Enraf Optiflex Level Gauge
        {
            "vendor": "Honeywell",
            "vendor_family": "Enraf",
            "model": "Optiflex 6000",
            "firmware_version": "4.0.1",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Honeywell International Inc.",
                "product_code": "6000",
                "major_minor_revision": "V4.0.1",
                "vendor_url": "http://www.honeywell.com",
                "product_name": "Enraf Optiflex 6000 Level Gauge",
                "model_name": "Tank Gauging",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 60.0,
                "mean_ms": 20.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Honeywell Pipeline Leak Detection System
        {
            "vendor": "Honeywell",
            "vendor_family": "LDS",
            "model": "Pipeline LDS",
            "firmware_version": "3.2.0",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Honeywell International Inc.",
                "product_code": "LDS-3200",
                "major_minor_revision": "V3.2.0",
                "product_name": "Pipeline Leak Detection System",
                "model_name": "LDS Server",
            },
            "tcp_stack": {
                "ttl": 128,  # Windows-based server
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 100.0,
                "mean_ms": 25.0,
                "std_dev_ms": 15.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Honeywell Experion PKS DCS (Water/Wastewater)
        # ============================================================
        # Honeywell Experion PKS C300 Controller
        {
            "vendor": "Honeywell",
            "vendor_family": "Experion PKS",
            "model": "C300",
            "firmware_version": "R520.2",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Honeywell",
                "product_code": "C300",
                "major_minor_revision": "R520.2",
                "vendor_url": "http://www.honeywell.com",
                "product_name": "Experion PKS C300 Controller",
                "model_name": "DCS Controller",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0x0039,  # Honeywell ODVA vendor ID
                "device_type": 14,
                "product_code": 0xC300,
                "revision_major": 520,
                "revision_minor": 2,
                "serial_number": 0xC3000001,
                "product_name": "Experion PKS C300 Controller",
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
                "min_ms": 1.0,
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.001,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Honeywell Experion PKS C200 Controller
        {
            "vendor": "Honeywell",
            "vendor_family": "Experion PKS",
            "model": "C200",
            "firmware_version": "R511.5",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Honeywell",
                "product_code": "C200",
                "major_minor_revision": "R511.5",
                "vendor_url": "http://www.honeywell.com",
                "product_name": "Experion PKS C200 Controller",
                "model_name": "DCS Controller",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0x0039,
                "device_type": 14,
                "product_code": 0xC200,
                "revision_major": 511,
                "revision_minor": 5,
                "serial_number": 0xC2000001,
                "product_name": "Experion PKS C200 Controller",
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
                "min_ms": 1.5,
                "max_ms": 25.0,
                "mean_ms": 6.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.001,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0003,
                "timeout_probability": 0.00015,
            },
            "is_builtin": True,
        },
        # Honeywell Experion Server
        {
            "vendor": "Honeywell",
            "vendor_family": "Experion PKS",
            "model": "Experion Server",
            "firmware_version": "520.2 HF7",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Honeywell",
                "product_code": "EXPERION-SVR",
                "major_minor_revision": "520.2",
                "vendor_url": "http://www.honeywell.com",
                "product_name": "Experion Server",
                "model_name": "SCADA Server",
            },
            "tcp_stack": {
                "ttl": 128,  # Windows-based server
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Honeywell Safety Manager
        {
            "vendor": "Honeywell",
            "vendor_family": "Safety Manager",
            "model": "Safety Manager",
            "firmware_version": "R520.1",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Honeywell",
                "product_code": "SM-SC",
                "major_minor_revision": "R520.1",
                "vendor_url": "http://www.honeywell.com",
                "product_name": "Safety Manager SC",
                "model_name": "Safety Controller",
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
                "mean_ms": 3.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.001,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0001,
                "timeout_probability": 0.00005,
            },
            "safety_config": {
                "sil_level": "SIL3",
                "category": "Cat4",
            },
            "is_builtin": True,
        },
        # Honeywell Series C I/O
        {
            "vendor": "Honeywell",
            "vendor_family": "Series C",
            "model": "Series C I/O",
            "firmware_version": "R520.1",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Honeywell",
                "product_code": "SC-IO",
                "major_minor_revision": "R520.1",
                "vendor_url": "http://www.honeywell.com",
                "product_name": "Series C I/O Module",
                "model_name": "I/O Module",
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
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Honeywell Experion Station (HMI/Workstation)
        {
            "vendor": "Honeywell",
            "vendor_family": "Experion PKS",
            "model": "Experion Station",
            "firmware_version": "520.2",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Honeywell",
                "product_code": "EXPERION-STN",
                "major_minor_revision": "520.2",
                "vendor_url": "http://www.honeywell.com",
                "product_name": "Experion Station",
                "model_name": "Operator Workstation",
            },
            "tcp_stack": {
                "ttl": 128,  # Windows-based
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 100.0,
                "mean_ms": 25.0,
                "std_dev_ms": 15.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 2.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0005,
                "timeout_probability": 0.0003,
            },
            "is_builtin": True,
        },
        # Honeywell UDA2182 Analyzer
        {
            "vendor": "Honeywell",
            "vendor_family": "UDA",
            "model": "UDA2182",
            "firmware_version": "2.50",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Honeywell International Inc.",
                "product_code": "UDA2182",
                "major_minor_revision": "V2.50",
                "product_name": "UDA2182 Universal Dual Analyzer",
                "model_name": "Process Analyzer",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 80.0,
                "mean_ms": 30.0,
                "std_dev_ms": 15.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # ABB - Protection Relays and Motors
        # ============================================================
        # ABB REF615 Protection Relay
        {
            "vendor": "ABB",
            "vendor_family": "Relion",
            "model": "REF615",
            "firmware_version": "5.1",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "REF615",
                "major_minor_revision": "V5.1",
                "vendor_url": "http://www.abb.com",
                "product_name": "REF615 Feeder Protection Relay",
                "model_name": "Protection Relay",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ABB REX640 Protection Relay
        {
            "vendor": "ABB",
            "vendor_family": "Relion",
            "model": "REX640",
            "firmware_version": "2.2",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "REX640",
                "major_minor_revision": "V2.2",
                "product_name": "REX640 IEC 61850 Protection Relay",
                "model_name": "Protection Relay",
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
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ABB ACS880 Drive
        {
            "vendor": "ABB",
            "vendor_family": "ACS880",
            "model": "ACS880-01",
            "firmware_version": "1.98",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "ACS880-01",
                "major_minor_revision": "V1.98",
                "product_name": "ACS880-01 Industrial Drive",
                "model_name": "Variable Speed Drive",
            },
            "ethernet_ip_identity": {
                "vendor_id": 285,  # ABB
                "device_type": 2,  # AC Drive
                "product_code": 880,
                "revision_major": 1,
                "revision_minor": 98,
                "serial_number": 0xABB00001,
                "product_name": "ACS880-01 Industrial Drive",
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
                "min_ms": 3.0,
                "max_ms": 40.0,
                "mean_ms": 12.0,
                "std_dev_ms": 7.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # ABB AC500 PLCs (Water/Wastewater)
        # ============================================================
        # ABB AC500 PM590-ETH PLC
        {
            "vendor": "ABB",
            "vendor_family": "AC500 V2",
            "model": "PM590-ETH",
            "firmware_version": "2.8.6",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "PM590-ETH",
                "major_minor_revision": "2.8.6",
                "vendor_url": "http://www.abb.com",
                "product_name": "ABB AC500 PM590-ETH PLC",
                "model_name": "AC500 V2 PLC",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0x0016,  # ABB ODVA vendor ID
                "device_type": 14,
                "product_code": 0x0590,
                "revision_major": 2,
                "revision_minor": 86,
                "serial_number": 0xABB00590,
                "product_name": "ABB AC500 PM590-ETH",
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
                "min_ms": 1.0,
                "max_ms": 25.0,
                "mean_ms": 6.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
            "is_builtin": True,
        },
        # ABB AC500 PM583-ETH PLC
        {
            "vendor": "ABB",
            "vendor_family": "AC500 V2",
            "model": "PM583-ETH",
            "firmware_version": "2.8.6",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "PM583-ETH",
                "major_minor_revision": "2.8.6",
                "vendor_url": "http://www.abb.com",
                "product_name": "ABB AC500 PM583-ETH PLC",
                "model_name": "AC500 V2 PLC",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0x0016,
                "device_type": 14,
                "product_code": 0x0583,
                "revision_major": 2,
                "revision_minor": 86,
                "serial_number": 0xABB00583,
                "product_name": "ABB AC500 PM583-ETH",
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
                "min_ms": 1.5,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0005,
                "timeout_probability": 0.00025,
            },
            "is_builtin": True,
        },
        # ABB AC500 PM554-TP-ETH PLC (Compact)
        {
            "vendor": "ABB",
            "vendor_family": "AC500",
            "model": "PM554-TP-ETH",
            "firmware_version": "2.6.0",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "PM554-TP-ETH",
                "major_minor_revision": "2.6.0",
                "vendor_url": "http://www.abb.com",
                "product_name": "ABB AC500 PM554-TP-ETH PLC",
                "model_name": "AC500 Compact PLC",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0x0016,
                "device_type": 14,
                "product_code": 0x0554,
                "revision_major": 2,
                "revision_minor": 60,
                "serial_number": 0xABB00554,
                "product_name": "ABB AC500 PM554-TP-ETH",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 40.0,
                "mean_ms": 10.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0008,
                "timeout_probability": 0.0004,
            },
            "is_builtin": True,
        },
        # ABB CP620 HMI Panel
        {
            "vendor": "ABB",
            "vendor_family": "CP600",
            "model": "CP620",
            "firmware_version": "2.1",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "CP620",
                "major_minor_revision": "V2.1",
                "vendor_url": "http://www.abb.com",
                "product_name": "ABB CP620 Control Panel",
                "model_name": "HMI Panel",
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
                "outlier_probability": 0.005,
                "outlier_multiplier": 2.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0006,
                "timeout_probability": 0.0003,
            },
            "is_builtin": True,
        },
        # ABB ACS580 Drive
        {
            "vendor": "ABB",
            "vendor_family": "ACS580",
            "model": "ACS580",
            "firmware_version": "2.76",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "ACS580-01",
                "major_minor_revision": "V2.76",
                "vendor_url": "http://www.abb.com",
                "product_name": "ACS580-01 General Purpose Drive",
                "model_name": "Variable Speed Drive",
            },
            "ethernet_ip_identity": {
                "vendor_id": 285,  # ABB
                "device_type": 2,  # AC Drive
                "product_code": 580,
                "revision_major": 2,
                "revision_minor": 76,
                "serial_number": 0xABB00580,
                "product_name": "ACS580-01 General Purpose Drive",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "exponential",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0005,
                "timeout_probability": 0.00025,
            },
            "is_builtin": True,
        },
        # ABB CI501 I/O Module
        {
            "vendor": "ABB",
            "vendor_family": "S500",
            "model": "CI501",
            "firmware_version": "3.2",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "CI501",
                "major_minor_revision": "V3.2",
                "vendor_url": "http://www.abb.com",
                "product_name": "ABB CI501 Communication Interface",
                "model_name": "I/O Interface",
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
                "max_ms": 15.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.5,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0003,
                "timeout_probability": 0.00015,
            },
            "is_builtin": True,
        },
        # ABB M2BAX Motor (with Modbus gateway)
        {
            "vendor": "ABB",
            "vendor_family": "M2BAX",
            "model": "M2BAX 180MLB",
            "firmware_version": "1.0",
            "oui_prefixes": ABB_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "M2BAX 180MLB",
                "major_minor_revision": "V1.0",
                "product_name": "M2BAX 180MLB Induction Motor",
                "model_name": "Electric Motor",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 4096,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 100.0,
                "mean_ms": 35.0,
                "std_dev_ms": 20.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
            "is_builtin": True,
        },
        # ============================================================
        # Emerson - Control Valves and DeltaV
        # ============================================================
        # Emerson Fisher FIELDVUE DVC6200 Valve Controller
        {
            "vendor": "Emerson",
            "vendor_family": "FIELDVUE",
            "model": "DVC6200",
            "firmware_version": "12.4",
            "oui_prefixes": EMERSON_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "Emerson Process Management",
                "product_code": "DVC6200",
                "major_minor_revision": "V12.4",
                "vendor_url": "http://www.emerson.com",
                "product_name": "FIELDVUE DVC6200 Digital Valve Controller",
                "model_name": "Valve Positioner",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Emerson Rosemount 3051 Pressure Transmitter
        {
            "vendor": "Emerson",
            "vendor_family": "Rosemount",
            "model": "3051S",
            "firmware_version": "9.7",
            "oui_prefixes": EMERSON_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Emerson Process Management",
                "product_code": "3051S",
                "major_minor_revision": "V9.7",
                "product_name": "Rosemount 3051S SuperModule Pressure Transmitter",
                "model_name": "Pressure Transmitter",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Emerson Micro Motion Flow Meter
        {
            "vendor": "Emerson",
            "vendor_family": "Micro Motion",
            "model": "5700",
            "firmware_version": "5.2",
            "oui_prefixes": EMERSON_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Emerson Process Management",
                "product_code": "5700",
                "major_minor_revision": "V5.2",
                "product_name": "Micro Motion 5700 Coriolis Transmitter",
                "model_name": "Flow Meter",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 40.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Emerson DeltaV M-Series Controller
        {
            "vendor": "Emerson",
            "vendor_family": "DeltaV",
            "model": "MD Plus",
            "firmware_version": "14.3",
            "oui_prefixes": EMERSON_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Emerson Process Management",
                "product_code": "MD Plus",
                "major_minor_revision": "V14.3",
                "product_name": "DeltaV MD Plus Controller",
                "model_name": "DCS Controller",
            },
            "ethernet_ip_identity": {
                "vendor_id": 90,  # Emerson
                "device_type": 14,  # Programmable Logic Controller
                "product_code": 143,
                "revision_major": 14,
                "revision_minor": 3,
                "serial_number": 0xE4520001,
                "product_name": "DeltaV MD Plus Controller",
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
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Emerson DeltaV S-Series Controller
        {
            "vendor": "Emerson",
            "vendor_family": "DeltaV",
            "model": "S-Series",
            "firmware_version": "13.3",
            "oui_prefixes": EMERSON_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Emerson Process Management",
                "product_code": "S-Series",
                "major_minor_revision": "V13.3",
                "product_name": "DeltaV S-Series Controller",
                "model_name": "DCS Controller",
            },
            "ethernet_ip_identity": {
                "vendor_id": 90,  # Emerson
                "device_type": 14,  # Programmable Logic Controller
                "product_code": 133,
                "revision_major": 13,
                "revision_minor": 3,
                "serial_number": 0xE4520002,
                "product_name": "DeltaV S-Series Controller",
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
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # Emerson ROC800 Remote Operations Controller
        {
            "vendor": "Emerson",
            "vendor_family": "ROC800",
            "model": "ROC800",
            "firmware_version": "3.75",
            "oui_prefixes": EMERSON_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "modbus_identity": {
                "vendor_name": "Emerson Process Management",
                "product_code": "ROC800",
                "major_minor_revision": "V3.75",
                "product_name": "ROC800 Remote Operations Controller",
                "model_name": "ROC RTU",
            },
            "snmp_identity": {
                "sys_descr": "Emerson ROC800 Remote Operations Controller v3.75",
                "sys_object_id": "1.3.6.1.4.1.216.2.800",
                "sys_name": "ROC800-RTU-001",
                "sys_location": "Pump Station",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 18.0,
                "std_dev_ms": 8.0,
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
        # Emerson ROC800L Remote Operations Controller (Low Power)
        {
            "vendor": "Emerson",
            "vendor_family": "ROC800",
            "model": "ROC800L",
            "firmware_version": "3.75",
            "oui_prefixes": EMERSON_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "modbus_identity": {
                "vendor_name": "Emerson Process Management",
                "product_code": "ROC800L",
                "major_minor_revision": "V3.75",
                "product_name": "ROC800L Remote Operations Controller",
                "model_name": "ROC RTU",
            },
            "snmp_identity": {
                "sys_descr": "Emerson ROC800L Remote Operations Controller v3.75",
                "sys_object_id": "1.3.6.1.4.1.216.2.800",
                "sys_name": "ROC800L-RTU-001",
                "sys_location": "Remote Station",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 80.0,
                "mean_ms": 25.0,
                "std_dev_ms": 12.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0005,
                "timeout_probability": 0.0003,
            },
            "is_builtin": True,
        },

        # ============================================================
        # GE - PROFICY HISTORIAN
        # ============================================================
        # Proficy Historian Server (SQL injection vuln CVE-2022-46660)
        # Major OPC UA server product - supports OPC UA, Modbus, SNMP, EtherNet/IP
        {
            "vendor": "GE",
            "vendor_family": "Proficy",
            "model": "Proficy Historian",
            "firmware_version": "8.0",
            "oui_prefixes": GE_OUI_PREFIXES,
            "supported_protocols": ["opc_ua", "modbus", "snmp", "ethernet_ip"],
            "ethernet_ip_identity": {
                "vendor_id": 82,  # GE
                "device_type": 12,  # Communications Adapter
                "product_code": 8000,
                "revision_major": 8,
                "revision_minor": 0,
                "product_name": "Proficy Historian",
                "state": 3,
            },
            "opc_ua_identity": {
                "application_name": "GE Proficy Historian",
                "application_uri": "urn:GE:Proficy:Historian",
                "product_uri": "http://www.ge.com/digital/proficy-historian",
                "manufacturer_name": "GE Digital",
                "product_name": "Proficy Historian",
                "software_version": "8.0.0",
                "build_number": "8.0",
                "build_date": "2022-09-01T12:00:00Z",
            },
            "modbus_identity": {
                "vendor_name": "GE Digital",
                "product_code": "HISTORIAN",
                "major_minor_revision": "8.0",
                "product_name": "Proficy Historian Server",
                "model_name": "Proficy Historian",
            },
            "snmp_identity": {
                "sys_descr": "GE Proficy Historian Server 8.0",
                "sys_name": "HISTORIAN-001",
                "sys_object_id": "1.3.6.1.4.1.23310.1.1",
                "sys_location": "Control Room",
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 50.0,
                "mean_ms": 10.0,
                "std_dev_ms": 8.0,
                "distribution": "lognormal",
                "outlier_probability": 0.01,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # KEPWARE / PTC - OPC UA GATEWAYS
        # ============================================================
        # KEPServerEX OPC UA Gateway
        {
            "vendor": "Kepware",
            "vendor_family": "KEPServerEX",
            "model": "KEPServerEX",
            "firmware_version": "6.14",
            "oui_prefixes": [],  # Software runs on standard PCs
            "supported_protocols": ["opc_ua", "modbus", "ethernet_ip", "s7comm"],
            "opc_ua_identity": {
                "application_name": "Kepware KEPServerEX",
                "application_uri": "urn:localhost:KEPServerEX",
                "product_uri": "http://www.kepware.com/kepserverex",
                "manufacturer_name": "Kepware Technologies",
                "product_name": "KEPServerEX",
                "software_version": "6.14.263.0",
                "build_number": "263",
                "build_date": "2023-09-15T12:00:00Z",
            },
            "modbus_identity": {
                "vendor_name": "Kepware Technologies",
                "product_code": "KEPServerEX",
                "major_minor_revision": "6.14",
                "vendor_url": "http://www.kepware.com",
                "product_name": "KEPServerEX OPC Server",
                "model_name": "OPC UA Gateway",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0x0001,  # Generic
                "device_type": 12,  # Communications Adapter
                "product_code": 614,
                "revision_major": 6,
                "revision_minor": 14,
                "serial_number": 0x4B455001,  # KEP00001 in hex
                "product_name": "KEPServerEX EtherNet/IP Driver",
                "state": 3,
            },
            "s7_identity": {
                "order_code": "KEPServerEX-S7",
                "module_type": "Siemens S7 Driver",
                "firmware_version": "6.14",
                "hardware_version": "N/A",
            },
            "tcp_stack": {
                "ttl": 128,  # Windows-based
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 50.0,
                "mean_ms": 10.0,
                "std_dev_ms": 8.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # HMS INDUSTRIAL NETWORKS - PROTOCOL GATEWAYS
        # ============================================================
        # HMS Anybus X-gateway
        {
            "vendor": "HMS",
            "vendor_family": "Anybus",
            "model": "Anybus X-gateway",
            "firmware_version": "2.30",
            "oui_prefixes": ["00:30:11"],  # HMS Industrial Networks OUI
            "supported_protocols": ["modbus", "ethernet_ip", "profinet"],
            "modbus_identity": {
                "vendor_name": "HMS Industrial Networks",
                "product_code": "AB7634",
                "major_minor_revision": "2.30",
                "vendor_url": "http://www.anybus.com",
                "product_name": "Anybus X-gateway Modbus TCP",
                "model_name": "Protocol Gateway",
            },
            "ethernet_ip_identity": {
                "vendor_id": 283,  # HMS Industrial Networks ODVA ID
                "device_type": 12,  # Communications Adapter
                "product_code": 7634,
                "revision_major": 2,
                "revision_minor": 30,
                "serial_number": 0x484D5301,  # HMS00001 in hex
                "product_name": "Anybus X-gateway EtherNet/IP",
                "state": 3,
            },
            "profinet_identity": {
                "vendor_id": 0x0128,  # HMS PROFINET vendor ID
                "device_id": 0x0100,
                "device_type": "Anybus X-gateway PROFINET",
                "station_name": "anybus-xgw",
                "device_role": 1,
                "im0_manufacturer": "HMS Industrial Networks",
                "im0_order_id": "AB7634",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V2.30",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
            "is_builtin": True,
        },
        # HMS Anybus Communicator
        {
            "vendor": "HMS",
            "vendor_family": "Anybus",
            "model": "Anybus Communicator",
            "firmware_version": "1.50",
            "oui_prefixes": ["00:30:11"],
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "HMS Industrial Networks",
                "product_code": "AB7072",
                "major_minor_revision": "1.50",
                "vendor_url": "http://www.anybus.com",
                "product_name": "Anybus Communicator EtherNet/IP",
                "model_name": "Serial-to-EtherNet Gateway",
            },
            "ethernet_ip_identity": {
                "vendor_id": 283,
                "device_type": 12,
                "product_code": 7072,
                "revision_major": 1,
                "revision_minor": 50,
                "serial_number": 0x484D5302,  # HMS00002 in hex
                "product_name": "Anybus Communicator",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 40.0,
                "mean_ms": 12.0,
                "std_dev_ms": 7.0,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0005,
                "timeout_probability": 0.00025,
            },
            "is_builtin": True,
        },
        # ============================================================
        # HMS EWON - INDUSTRIAL REMOTE ACCESS GATEWAYS
        # Talk2M cloud connectivity for remote PLC access
        # ============================================================
        # EWON Flexy 205 - Industrial IoT Gateway
        {
            "vendor": "HMS",
            "vendor_family": "EWON",
            "model": "Flexy 205",
            "firmware_version": "14.8s0",
            "oui_prefixes": ["00:30:11"],  # HMS Industrial Networks OUI
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "HMS Industrial Networks - EWON",
                "product_code": "EF205",
                "major_minor_revision": "14.8",
                "vendor_url": "https://www.ewon.biz",
                "product_name": "EWON Flexy 205 Industrial IoT Gateway",
                "model_name": "Remote Access Gateway",
            },
            "ethernet_ip_identity": {
                "vendor_id": 283,  # HMS Industrial Networks ODVA ID
                "device_type": 12,  # Communications Adapter
                "product_code": 205,
                "revision_major": 14,
                "revision_minor": 8,
                "serial_number": 0x45574E01,  # EWN00001 in hex
                "product_name": "EWON Flexy 205",
                "state": 3,
            },
            "snmp_identity": {
                "sys_descr": "EWON Flexy 205 Industrial IoT Gateway v14.8s0",
                "sys_object_id": "1.3.6.1.4.1.8284.2.1",
                "sys_name": "EWON-FLEXY-001",
                "sys_location": "Industrial DMZ",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 40.0,
                "mean_ms": 10.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "external_communications": {
                "cloud_service": "Talk2M",
                "cloud_domains": ["*.talk2m.com", "*.ewon.biz", "m2web.talk2m.com"],
                "protocols": ["https"],
                "ports": [443],
                "connection_type": "outbound_persistent",
                "heartbeat_interval_ms": 30000,
            },
            "is_builtin": True,
        },
        # EWON Cosy 131 - Simple Remote Access Router
        {
            "vendor": "HMS",
            "vendor_family": "EWON",
            "model": "Cosy 131",
            "firmware_version": "14.8s0",
            "oui_prefixes": ["00:30:11"],
            "supported_protocols": ["modbus", "ethernet_ip", "snmp"],
            "modbus_identity": {
                "vendor_name": "HMS Industrial Networks - EWON",
                "product_code": "EC131",
                "major_minor_revision": "14.8",
                "vendor_url": "https://www.ewon.biz",
                "product_name": "EWON Cosy 131 Remote Access Router",
                "model_name": "Remote Access Router",
            },
            "ethernet_ip_identity": {
                "vendor_id": 283,  # HMS Industrial Networks
                "device_type": 12,  # Communications Adapter
                "product_code": 131,
                "revision_major": 14,
                "revision_minor": 8,
                "serial_number": 0xEC131001,
                "product_name": "EWON Cosy 131 Remote Access Router",
                "state": 3,
            },
            "snmp_identity": {
                "sys_descr": "EWON Cosy 131 Remote Access Router v14.8s0",
                "sys_object_id": "1.3.6.1.4.1.8284.2.2",
                "sys_name": "EWON-COSY-001",
                "sys_location": "Control Room",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
            "external_communications": {
                "cloud_service": "Talk2M",
                "cloud_domains": ["*.talk2m.com", "*.ewon.biz", "m2web.talk2m.com"],
                "protocols": ["https"],
                "ports": [443],
                "connection_type": "outbound_persistent",
                "heartbeat_interval_ms": 30000,
            },
            "is_builtin": True,
        },
        # ============================================================
        # CISCO - INDUSTRIAL NETWORK INFRASTRUCTURE
        # ============================================================
        # Cisco IE-4000 Industrial Switch
        {
            "vendor": "Cisco",
            "vendor_family": "IE-4000",
            "model": "IE-4000-8GT4G-E",
            "firmware_version": "15.2(8)E",
            "oui_prefixes": ["00:1B:0D", "00:1D:A1", "00:22:90"],  # Cisco OUIs
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Cisco IOS Software, IE-4000 Industrial Ethernet Switch V15.2(8)E",
                "sys_object_id": "1.3.6.1.4.1.9.1.2613",
                "sys_name": "IE-4000-CORE",
                "sys_location": "Industrial DMZ",
            },
            "tcp_stack": {
                "ttl": 255,  # Cisco IOS
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0001,
                "timeout_probability": 0.00005,
            },
            "is_builtin": True,
        },
        # ============================================================
        # HIRSCHMANN - INDUSTRIAL SWITCHES
        # ============================================================
        # Hirschmann RS20 Managed Switch
        {
            "vendor": "Hirschmann",
            "vendor_family": "RS20",
            "model": "RS20-0800M2M2SDAE",
            "firmware_version": "09.1.00",
            "oui_prefixes": ["00:80:63"],  # Hirschmann OUI
            "supported_protocols": ["modbus", "snmp"],
            "modbus_identity": {
                "vendor_name": "Hirschmann Automation and Control",
                "product_code": "RS20-0800M2M2SDAE",
                "major_minor_revision": "09.1.00",
                "vendor_url": "http://www.hirschmann.com",
                "product_name": "RS20 Managed Industrial Switch",
                "model_name": "Industrial Ethernet Switch",
            },
            "snmp_identity": {
                "sys_descr": "Hirschmann Rail Switch RS20-0800M2M2SDAE HiOS-2A-09.1.00",
                "sys_object_id": "1.3.6.1.4.1.248.14.2.1",
                "sys_name": "RS20-SWITCH",
                "sys_location": "Production Floor",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 6.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
    ]
