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
    "00:60:35",  # Honeywell
    "00:D0:36",  # Honeywell
    "64:31:7E",  # Honeywell
]

ABB_OUI_PREFIXES = [
    "00:20:99",  # ABB Industrial Systems
    "00:21:99",  # ABB STOTZ-KONTAKT
    "CC:DA:0C",  # ABB
]

EMERSON_OUI_PREFIXES = [
    "00:A0:F8",  # Emerson Network Power
    "00:03:38",  # Emerson
    "00:90:E8",  # Fisher-Rosemount (Emerson)
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
            },
            "is_builtin": True,
        },
    ]
