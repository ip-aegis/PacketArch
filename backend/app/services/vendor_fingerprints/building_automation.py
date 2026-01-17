"""Building Automation / BMS vendor fingerprints.

Fingerprint data for Building Management System (BMS) and Building Automation
equipment vendors. These devices use BACnet/IP protocol (UDP 47808) and are found in:
- Commercial office buildings
- University campuses
- Data centers
- Hospitals
- Hotels and hospitality

Vendors covered:
- Johnson Controls (Metasys controllers)
- Honeywell (Tridium Niagara, Excel controllers)
- Trane (Tracer controllers)
- Carrier (i-Vu controllers)
- Schneider Electric (Andover Continuum)
- Siemens (Climatix, DXR controllers)
- Delta Controls (enteliBUS)
- Distech Controls (EC-BOS)
- Carel Industries (pCO controllers)
- Automated Logic (WebCTRL)

BACnet Vendor IDs (registered with ASHRAE):
- 5: Johnson Controls
- 17: Honeywell
- 24: Siemens
- 67: Schneider Electric
- 86: Automated Logic
- 97: Trane
- 122: Delta Controls
- 165: Distech Controls
- 260: Carel Industries
- 301: Carrier
"""

from typing import Any

# MAC OUI Prefixes for BMS vendors (IEEE registrations)
# NOTE: Authoritative source for MAC generation is:
#   backend/app/protocol_engines/vendor_oui.py (VENDOR_OUIS dict)
JOHNSON_CONTROLS_OUI_PREFIXES = [
    "00:1A:17",  # Johnson Controls
    "00:16:C7",  # Johnson Controls Inc
    "00:23:BE",  # Johnson Controls Systems
]

HONEYWELL_OUI_PREFIXES = [
    "00:00:8C",  # Honeywell (legacy)
    "00:D0:34",  # Honeywell Industrial
    "00:04:63",  # Honeywell Inc
    "00:1A:64",  # Honeywell Life Safety
]

TRIDIUM_OUI_PREFIXES = [
    "00:50:62",  # Tridium (Niagara Framework)
]

TRANE_OUI_PREFIXES = [
    "00:0D:AD",  # Trane Technologies
    "00:1C:C0",  # Trane
]

CARRIER_OUI_PREFIXES = [
    "00:0D:AD",  # Carrier Corporation
    "00:1E:8E",  # Carrier
]

DELTA_CONTROLS_OUI_PREFIXES = [
    "00:0B:AB",  # Delta Controls
    "00:0D:9F",  # Delta Controls Inc
]

DISTECH_OUI_PREFIXES = [
    "00:1E:C0",  # Distech Controls
    "D0:77:14",  # Distech Controls Inc
]

CAREL_OUI_PREFIXES = [
    "00:0D:5D",  # Carel Industries
    "00:15:F9",  # Carel SpA
]

AUTOMATED_LOGIC_OUI_PREFIXES = [
    "00:14:C1",  # Automated Logic Corporation
    "00:1C:12",  # Automated Logic
]

SIEMENS_BUILDING_OUI_PREFIXES = [
    "00:1B:1B",  # Siemens Building Technologies
    "00:0E:8C",  # Siemens AG
]

SCHNEIDER_BMS_OUI_PREFIXES = [
    "00:80:F4",  # Schneider Electric
    "00:04:A3",  # Schneider Electric
]


def get_building_automation_fingerprints() -> list[dict[str, Any]]:
    """Get all building automation vendor fingerprints."""
    return [
        # ============================================================
        # JOHNSON CONTROLS - Metasys Building Automation
        # ============================================================
        # Johnson Controls Metasys NAE55
        {
            "vendor": "Johnson Controls",
            "vendor_family": "Metasys",
            "model": "NAE55",
            "firmware_version": "12.0.3",
            "oui_prefixes": JOHNSON_CONTROLS_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 5,  # Johnson Controls BACnet vendor ID
                "vendor_name": "Johnson Controls",
                "model_name": "NAE55 Network Automation Engine",
                "firmware_revision": "12.0.3",
                "application_software_version": "12.0",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,  # Both
                "device_instance": 1001,
                "system_status": 0,  # Operational
                "object_name": "NAE55-MAIN-001",
                "description": "Metasys Network Automation Engine",
            },
            "snmp_identity": {
                "sys_descr": "Johnson Controls Metasys NAE55 v12.0.3",
                "sys_object_id": "1.3.6.1.4.1.4399.2.1.1",
                "sys_name": "NAE55-BLD-001",
                "sys_location": "Building 1 MDF",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 100.0,
                "mean_ms": 25.0,
                "std_dev_ms": 15.0,
                "distribution": "lognormal",
                "outlier_probability": 0.004,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Johnson Controls Metasys SNC
        {
            "vendor": "Johnson Controls",
            "vendor_family": "Metasys",
            "model": "SNC",
            "firmware_version": "11.0.2",
            "oui_prefixes": JOHNSON_CONTROLS_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 5,
                "vendor_name": "Johnson Controls",
                "model_name": "SNC Supervisory Network Controller",
                "firmware_revision": "11.0.2",
                "application_software_version": "11.0",
                "protocol_version": 1,
                "protocol_revision": 17,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 1002,
                "object_name": "SNC-001",
                "description": "Metasys Supervisory Controller",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 120.0,
                "mean_ms": 35.0,
                "std_dev_ms": 20.0,
                "distribution": "lognormal",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Johnson Controls FEC (Field Equipment Controller)
        {
            "vendor": "Johnson Controls",
            "vendor_family": "Metasys",
            "model": "FEC26",
            "firmware_version": "10.0.1",
            "oui_prefixes": JOHNSON_CONTROLS_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 5,
                "vendor_name": "Johnson Controls",
                "model_name": "FEC26 Field Equipment Controller",
                "firmware_revision": "10.0.1",
                "application_software_version": "10.0",
                "protocol_version": 1,
                "protocol_revision": 16,
                "max_apdu_length": 480,
                "segmentation_supported": 3,  # None
                "device_instance": 2001,
                "object_name": "FEC26-AHU-001",
                "description": "AHU Controller",
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 150.0,
                "mean_ms": 40.0,
                "std_dev_ms": 25.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # HONEYWELL - Tridium Niagara Framework
        # ============================================================
        # Honeywell Tridium Niagara 4 JACE 8000
        {
            "vendor": "Honeywell",
            "vendor_family": "Niagara",
            "model": "JACE 8000",
            "firmware_version": "4.10.1",
            "oui_prefixes": TRIDIUM_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 17,  # Honeywell BACnet vendor ID
                "vendor_name": "Honeywell",
                "model_name": "Niagara 4 JACE 8000",
                "firmware_revision": "4.10.1",
                "application_software_version": "4.10",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 3001,
                "object_name": "JACE8000-001",
                "description": "Niagara JACE Controller",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 80.0,
                "mean_ms": 20.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Honeywell Excel Web Controller
        {
            "vendor": "Honeywell",
            "vendor_family": "Excel",
            "model": "XL Web",
            "firmware_version": "5.0.2",
            "oui_prefixes": HONEYWELL_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 17,
                "vendor_name": "Honeywell",
                "model_name": "Excel Web Building Controller",
                "firmware_revision": "5.0.2",
                "application_software_version": "5.0",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 1024,
                "segmentation_supported": 3,
                "device_instance": 3002,
                "object_name": "XLWEB-001",
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 100.0,
                "mean_ms": 30.0,
                "std_dev_ms": 18.0,
                "distribution": "lognormal",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # TRANE - Building Automation
        # ============================================================
        # Trane Tracer SC+
        {
            "vendor": "Trane",
            "vendor_family": "Tracer",
            "model": "SC+",
            "firmware_version": "5.8.0",
            "oui_prefixes": TRANE_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 97,  # Trane BACnet vendor ID
                "vendor_name": "Trane",
                "model_name": "Tracer SC+ System Controller",
                "firmware_revision": "5.8.0",
                "application_software_version": "5.8",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 4001,
                "object_name": "TRACER-SC-001",
                "description": "Trane Tracer SC+ Controller",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 90.0,
                "mean_ms": 28.0,
                "std_dev_ms": 15.0,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Trane UC600 Unit Controller
        {
            "vendor": "Trane",
            "vendor_family": "Tracer",
            "model": "UC600",
            "firmware_version": "3.5.2",
            "oui_prefixes": TRANE_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 97,
                "vendor_name": "Trane",
                "model_name": "UC600 Unit Controller",
                "firmware_revision": "3.5.2",
                "application_software_version": "3.5",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 4002,
                "object_name": "UC600-AHU-001",
            },
            "response_timing": {
                "min_ms": 12.0,
                "max_ms": 120.0,
                "mean_ms": 35.0,
                "std_dev_ms": 20.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # CARRIER - i-Vu Controllers
        # ============================================================
        # Carrier i-Vu Pro Open
        {
            "vendor": "Carrier",
            "vendor_family": "i-Vu",
            "model": "Pro Open",
            "firmware_version": "7.0.2",
            "oui_prefixes": CARRIER_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 301,  # Carrier BACnet vendor ID
                "vendor_name": "Carrier",
                "model_name": "i-Vu Pro Open Server",
                "firmware_revision": "7.0.2",
                "application_software_version": "7.0",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 5001,
                "object_name": "IVU-SERVER-001",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 70.0,
                "mean_ms": 22.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # SCHNEIDER ELECTRIC - Andover Continuum
        # ============================================================
        # Schneider Andover Continuum CX9680
        {
            "vendor": "Schneider Electric",
            "vendor_family": "Andover Continuum",
            "model": "CX9680",
            "firmware_version": "1.87.0",
            "oui_prefixes": SCHNEIDER_BMS_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 67,  # Schneider Electric BACnet vendor ID
                "vendor_name": "Schneider Electric",
                "model_name": "Andover Continuum CX9680",
                "firmware_revision": "1.87.0",
                "application_software_version": "1.87",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 6001,
                "object_name": "CX9680-001",
                "description": "Continuum Building Controller",
            },
            "modbus_identity": {
                "vendor_id": 0x000B,
                "product_code": "CX9680",
                "major_minor_revision": "1.87",
                "vendor_name": "Schneider Electric",
                "product_name": "Andover Continuum CX9680",
                "model_name": "CX9680",
                "user_application_name": "Building Controller",
            },
            "response_timing": {
                "min_ms": 6.0,
                "max_ms": 85.0,
                "mean_ms": 25.0,
                "std_dev_ms": 14.0,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # SIEMENS - Building Technologies
        # ============================================================
        # Siemens Climatix C600
        {
            "vendor": "Siemens",
            "vendor_family": "Climatix",
            "model": "C600",
            "firmware_version": "2.0.0",
            "oui_prefixes": SIEMENS_BUILDING_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 24,  # Siemens BACnet vendor ID
                "vendor_name": "Siemens",
                "model_name": "Climatix C600",
                "firmware_revision": "2.0.0",
                "application_software_version": "2.0",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 7001,
                "object_name": "CLIMATIX-C600-001",
                "description": "Siemens Climatix Controller",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 75.0,
                "mean_ms": 20.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Siemens DXR2 Room Automation Station
        {
            "vendor": "Siemens",
            "vendor_family": "Desigo",
            "model": "DXR2.E12",
            "firmware_version": "5.30.0",
            "oui_prefixes": SIEMENS_BUILDING_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 24,
                "vendor_name": "Siemens",
                "model_name": "DXR2.E12 Room Automation Station",
                "firmware_revision": "5.30.0",
                "application_software_version": "5.30",
                "protocol_version": 1,
                "protocol_revision": 17,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 7002,
                "object_name": "DXR2-RM-001",
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 100.0,
                "mean_ms": 28.0,
                "std_dev_ms": 16.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # DELTA CONTROLS - enteliBUS
        # ============================================================
        # Delta Controls enteliBUS Manager
        {
            "vendor": "Delta Controls",
            "vendor_family": "enteliBUS",
            "model": "Manager",
            "firmware_version": "4.8.0",
            "oui_prefixes": DELTA_CONTROLS_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 122,  # Delta Controls BACnet vendor ID
                "vendor_name": "Delta Controls",
                "model_name": "enteliBUS Manager",
                "firmware_revision": "4.8.0",
                "application_software_version": "4.8",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 8001,
                "object_name": "ENTBUS-MGR-001",
                "description": "enteliBUS Building Controller",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 80.0,
                "mean_ms": 22.0,
                "std_dev_ms": 13.0,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Delta Controls eBCON
        {
            "vendor": "Delta Controls",
            "vendor_family": "enteliBUS",
            "model": "eBCON",
            "firmware_version": "3.5.0",
            "oui_prefixes": DELTA_CONTROLS_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 122,
                "vendor_name": "Delta Controls",
                "model_name": "eBCON Controller",
                "firmware_revision": "3.5.0",
                "application_software_version": "3.5",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 8002,
                "object_name": "EBCON-001",
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 120.0,
                "mean_ms": 35.0,
                "std_dev_ms": 20.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # DISTECH CONTROLS - EC-BOS
        # ============================================================
        # Distech EC-BOS-8
        {
            "vendor": "Distech Controls",
            "vendor_family": "EC-BOS",
            "model": "EC-BOS-8",
            "firmware_version": "4.1.2",
            "oui_prefixes": DISTECH_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 165,  # Distech Controls BACnet vendor ID
                "vendor_name": "Distech Controls",
                "model_name": "EC-BOS-8 Building Controller",
                "firmware_revision": "4.1.2",
                "application_software_version": "4.1",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 9001,
                "object_name": "ECBOS8-001",
                "description": "EC-BOS Building Controller",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 70.0,
                "mean_ms": 20.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Distech ECY-VAV
        {
            "vendor": "Distech Controls",
            "vendor_family": "ECY",
            "model": "ECY-VAV",
            "firmware_version": "2.5.0",
            "oui_prefixes": DISTECH_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 165,
                "vendor_name": "Distech Controls",
                "model_name": "ECY-VAV Variable Air Volume Controller",
                "firmware_revision": "2.5.0",
                "application_software_version": "2.5",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 9002,
                "object_name": "ECY-VAV-001",
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 100.0,
                "mean_ms": 28.0,
                "std_dev_ms": 15.0,
                "distribution": "lognormal",
                "outlier_probability": 0.004,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # CAREL INDUSTRIES - pCO Controllers
        # ============================================================
        # Carel pCO5+
        {
            "vendor": "Carel",
            "vendor_family": "pCO",
            "model": "pCO5+",
            "firmware_version": "3.2.1",
            "oui_prefixes": CAREL_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 260,  # Carel Industries BACnet vendor ID
                "vendor_name": "Carel Industries",
                "model_name": "pCO5+ Programmable Controller",
                "firmware_revision": "3.2.1",
                "application_software_version": "3.2",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 10001,
                "object_name": "PCO5-CHILLER-001",
                "description": "Chiller Controller",
            },
            "modbus_identity": {
                "vendor_id": 0x0104,
                "product_code": "pCO5+",
                "major_minor_revision": "3.21",
                "vendor_name": "Carel Industries",
                "product_name": "pCO5+",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 150.0,
                "mean_ms": 40.0,
                "std_dev_ms": 25.0,
                "distribution": "lognormal",
                "outlier_probability": 0.006,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # AUTOMATED LOGIC - WebCTRL
        # ============================================================
        # Automated Logic WebCTRL Server
        {
            "vendor": "Automated Logic",
            "vendor_family": "WebCTRL",
            "model": "Server",
            "firmware_version": "8.5.0",
            "oui_prefixes": AUTOMATED_LOGIC_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 86,  # Automated Logic BACnet vendor ID
                "vendor_name": "Automated Logic",
                "model_name": "WebCTRL Building Automation Server",
                "firmware_revision": "8.5.0",
                "application_software_version": "8.5",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 11001,
                "object_name": "WEBCTRL-SVR-001",
                "description": "WebCTRL Server",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.0005,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Automated Logic ME812U
        {
            "vendor": "Automated Logic",
            "vendor_family": "WebCTRL",
            "model": "ME812U",
            "firmware_version": "6.2.0",
            "oui_prefixes": AUTOMATED_LOGIC_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 86,
                "vendor_name": "Automated Logic",
                "model_name": "ME812U Field Controller",
                "firmware_revision": "6.2.0",
                "application_software_version": "6.2",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 11002,
                "object_name": "ME812U-001",
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 100.0,
                "mean_ms": 30.0,
                "std_dev_ms": 18.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # SCHNEIDER ELECTRIC - Data Center Equipment
        # ============================================================
        # Schneider InRow DX CRAC Unit
        {
            "vendor": "Schneider Electric",
            "vendor_family": "InRow",
            "model": "InRow DX",
            "firmware_version": "5.3.2",
            "oui_prefixes": SCHNEIDER_BMS_OUI_PREFIXES,
            "bacnet_identity": {
                "vendor_id": 67,
                "vendor_name": "Schneider Electric",
                "model_name": "InRow DX Precision Cooling",
                "firmware_revision": "5.3.2",
                "application_software_version": "5.3",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 12001,
                "object_name": "INROW-DX-001",
                "description": "In-Row Cooling Unit",
            },
            "modbus_identity": {
                "vendor_id": 0x000B,
                "product_code": "ACRD",
                "major_minor_revision": "5.32",
                "vendor_name": "Schneider Electric",
                "product_name": "InRow DX CRAC",
                "model_name": "InRow DX",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 100.0,
                "mean_ms": 30.0,
                "std_dev_ms": 15.0,
                "distribution": "lognormal",
                "outlier_probability": 0.004,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Schneider Galaxy VM UPS
        {
            "vendor": "Schneider Electric",
            "vendor_family": "Galaxy",
            "model": "Galaxy VM",
            "firmware_version": "2.1.0",
            "oui_prefixes": SCHNEIDER_BMS_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_id": 0x000B,
                "product_code": "GVMUPS",
                "major_minor_revision": "2.10",
                "vendor_name": "Schneider Electric",
                "product_name": "Galaxy VM UPS",
                "model_name": "Galaxy VM",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Galaxy VM UPS v2.1.0",
                "sys_object_id": "1.3.6.1.4.1.318.1.3.30",
                "sys_name": "GALAXY-VM-001",
                "sys_location": "Data Center Power Room",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Schneider Rack PDU
        {
            "vendor": "Schneider Electric",
            "vendor_family": "Rack PDU",
            "model": "Rack PDU",
            "firmware_version": "6.9.6",
            "oui_prefixes": SCHNEIDER_BMS_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_id": 0x000B,
                "product_code": "AP8953",
                "major_minor_revision": "6.96",
                "vendor_name": "Schneider Electric",
                "product_name": "Rack PDU Metered-by-Outlet",
                "model_name": "Rack PDU",
            },
            "snmp_identity": {
                "sys_descr": "Schneider Electric Rack PDU v6.9.6",
                "sys_object_id": "1.3.6.1.4.1.318.1.3.4.5",
                "sys_name": "RPDU-001",
                "sys_location": "Data Center Row A",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 80.0,
                "mean_ms": 25.0,
                "std_dev_ms": 12.0,
                "distribution": "lognormal",
                "outlier_probability": 0.004,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
    ]


def get_bms_fingerprint_by_vendor(vendor: str) -> list[dict[str, Any]]:
    """Get fingerprints for a specific vendor.

    Args:
        vendor: Vendor name (case-insensitive)

    Returns:
        List of fingerprints for the vendor
    """
    vendor_lower = vendor.lower()
    return [
        fp for fp in get_building_automation_fingerprints()
        if fp["vendor"].lower() == vendor_lower
    ]


def get_bms_fingerprint_by_model(model: str) -> dict[str, Any] | None:
    """Get fingerprint for a specific model.

    Args:
        model: Model name (case-insensitive)

    Returns:
        Fingerprint dictionary or None if not found
    """
    model_lower = model.lower()
    for fp in get_building_automation_fingerprints():
        if fp["model"].lower() == model_lower:
            return fp
    return None
