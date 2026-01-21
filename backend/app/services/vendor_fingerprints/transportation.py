"""Transportation ITS vendor fingerprints.

Fingerprint data for transportation and ITS (Intelligent Transportation Systems)
equipment vendors. These devices use SNMP/NTCIP protocols and are found in:
- Traffic signal systems
- Highway management systems
- Tunnel/bridge control systems
- Toll collection systems

Vendors covered:
- Econolite (traffic controllers)
- Siemens ITS (traffic controllers, DMS)
- McCain (traffic controllers)
- Wavetronix (radar/lidar sensors)
- FLIR (thermal detection)
- Daktronics (dynamic message signs)
- Kapsch (toll collection)
- Q-Free (RSUs, toll systems)
- Axis (ITS cameras)
- Pelco (PTZ cameras)
- Bosch (ITS cameras)
"""

from typing import Any

# MAC OUI Prefixes for transportation vendors (IEEE registrations)
# NOTE: These are kept for documentation/reference only.
# The authoritative source for MAC generation is:
#   backend/app/protocol_engines/vendor_oui.py (VENDOR_OUIS dict)
# When adding new vendors, ensure they are added to vendor_oui.py
# for proper MAC address generation during scenario creation.
ECONOLITE_OUI_PREFIXES = [
    "00:19:FA",  # Econolite Control Products
]

SIEMENS_ITS_OUI_PREFIXES = [
    "00:1F:F8",  # Siemens AG
    "00:0E:8C",  # Siemens AG
    "64:00:6A",  # Siemens AG
]

MCCAIN_OUI_PREFIXES = [
    "00:0D:56",  # McCain Traffic Supply
]

WAVETRONIX_OUI_PREFIXES = [
    "00:18:3E",  # Wavetronix LLC
]

FLIR_OUI_PREFIXES = [
    "00:40:7F",  # FLIR Systems
    "00:80:F4",  # FLIR Systems
]

DAKTRONICS_OUI_PREFIXES = [
    "00:06:D3",  # Daktronics Inc
]

KAPSCH_OUI_PREFIXES = [
    "00:0B:6B",  # Kapsch TrafficCom
]

QFREE_OUI_PREFIXES = [
    "00:17:B0",  # Q-Free ASA
]

AXIS_OUI_PREFIXES = [
    "00:40:8C",  # Axis Communications
    "AC:CC:8E",  # Axis Communications
    "B8:A4:4F",  # Axis Communications
]

PELCO_OUI_PREFIXES = [
    "00:0C:CE",  # Pelco (Schneider)
    "00:0F:FE",  # Pelco
]

BOSCH_OUI_PREFIXES = [
    "00:04:13",  # Bosch Security Systems
    "00:07:5F",  # Bosch
]

HIKVISION_OUI_PREFIXES = [
    "C0:56:E3",  # Hikvision
    "44:19:B6",  # Hikvision
    "BC:AD:28",  # Hikvision
]


def get_transportation_fingerprints() -> list[dict[str, Any]]:
    """Get all transportation vendor fingerprints."""
    return [
        # ============================================================
        # ECONOLITE - Traffic Controllers
        # ============================================================
        # Econolite Cobalt ATC Controller
        {
            "vendor": "Econolite",
            "vendor_family": "Traffic Controller",
            "model": "Cobalt ATC",
            "firmware_version": "V2.1.5",
            "oui_prefixes": ECONOLITE_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Econolite Cobalt ATC Traffic Controller V2.1.5",
                "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.1",
                "sys_name": "COBALT-ATC-001",
                "sys_location": "Intersection",
                "sys_contact": "traffic@city.gov",
                "sys_services": 72,
                "ntcip_device_type": "asc",
                "max_phases": 16,
                "max_detectors": 64,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.02,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Econolite ASC/3-2100 Controller
        {
            "vendor": "Econolite",
            "vendor_family": "Traffic Controller",
            "model": "ASC/3-2100",
            "firmware_version": "V2.0.8",
            "oui_prefixes": ECONOLITE_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Econolite ASC/3-2100 Signal Controller V2.0.8",
                "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.2",
                "sys_name": "ASC3-2100-001",
                "ntcip_device_type": "asc",
                "max_phases": 8,
                "max_detectors": 32,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 80.0,
                "mean_ms": 25.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.02,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # SIEMENS ITS - Traffic Controllers and Master Stations
        # ============================================================
        # Siemens M60 Traffic Controller
        {
            "vendor": "Siemens",
            "vendor_family": "Traffic Controller",
            "model": "M60",
            "firmware_version": "V6.2.1",
            "oui_prefixes": SIEMENS_ITS_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Siemens M60 Traffic Controller V6.2.1",
                "sys_object_id": "1.3.6.1.4.1.4329.6.1.1",
                "sys_name": "M60-TC-001",
                "sys_location": "Cabinet",
                "ntcip_device_type": "asc",
                "max_phases": 16,
                "max_detectors": 128,
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 40.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "timeout_probability": 0.0005,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Siemens CP-8000 Master Station
        {
            "vendor": "Siemens",
            "vendor_family": "Traffic Management",
            "model": "CP-8000",
            "firmware_version": "V5.30",
            "oui_prefixes": SIEMENS_ITS_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Siemens SICAM CP-8000 Master Station V5.30",
                "sys_object_id": "1.3.6.1.4.1.4329.6.1.2",
                "sys_name": "CP8000-TMC-001",
                "sys_location": "Traffic Management Center",
                "ntcip_device_type": "master",
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.0003,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # MCCAIN - Traffic Controllers
        # ============================================================
        # McCain 2070 ATC Controller
        {
            "vendor": "McCain",
            "vendor_family": "Traffic Controller",
            "model": "2070 ATC",
            "firmware_version": "V3.6.2",
            "oui_prefixes": MCCAIN_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "McCain 2070 ATC Controller V3.6.2",
                "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.3",
                "sys_name": "2070-ATC-001",
                "ntcip_device_type": "asc",
                "max_phases": 16,
                "max_detectors": 64,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 60.0,
                "mean_ms": 18.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
                "outlier_probability": 0.02,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # McCain 170E Controller
        {
            "vendor": "McCain",
            "vendor_family": "Traffic Controller",
            "model": "170E",
            "firmware_version": "V2.4.0",
            "oui_prefixes": MCCAIN_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "McCain 170E Controller V2.4.0",
                "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.4",
                "sys_name": "170E-001",
                "ntcip_device_type": "asc",
                "max_phases": 8,
                "max_detectors": 16,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 100.0,
                "mean_ms": 30.0,
                "std_dev_ms": 15.0,
                "distribution": "gaussian",
                "outlier_probability": 0.025,
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
        # WAVETRONIX - Radar/Lidar Sensors
        # ============================================================
        # Wavetronix SmartSensor HD
        {
            "vendor": "Wavetronix",
            "vendor_family": "Radar Sensor",
            "model": "SmartSensor HD",
            "firmware_version": "V8.5",
            "oui_prefixes": WAVETRONIX_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Wavetronix SmartSensor HD Radar V8.5",
                "sys_object_id": "1.3.6.1.4.1.34362.1.1.1",
                "sys_name": "RADAR-HD-001",
                "sys_location": "Detection Zone",
                "ntcip_device_type": "sensor",
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
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Wavetronix SmartSensor Advance
        {
            "vendor": "Wavetronix",
            "vendor_family": "Radar Sensor",
            "model": "SmartSensor Advance",
            "firmware_version": "V8.5",
            "oui_prefixes": WAVETRONIX_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Wavetronix SmartSensor Advance V8.5",
                "sys_object_id": "1.3.6.1.4.1.34362.1.2.1",
                "sys_name": "RADAR-ADV-001",
                "ntcip_device_type": "sensor",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 20.0,
                "mean_ms": 6.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # FLIR - Thermal Detection
        # ============================================================
        # FLIR TrafiOne
        {
            "vendor": "FLIR",
            "vendor_family": "Thermal Sensor",
            "model": "TrafiOne",
            "firmware_version": "V3.5.0",
            "oui_prefixes": FLIR_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "FLIR TrafiOne Thermal Detector V3.5.0",
                "sys_object_id": "1.3.6.1.4.1.28846.1.1.1",
                "sys_name": "THERMAL-001",
                "ntcip_device_type": "sensor",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # FLIR TrafiSense
        {
            "vendor": "FLIR",
            "vendor_family": "Thermal Sensor",
            "model": "TrafiSense",
            "firmware_version": "V3.5.0",
            "oui_prefixes": FLIR_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "FLIR TrafiSense Multi-Lane Detector V3.5.0",
                "sys_object_id": "1.3.6.1.4.1.28846.1.2.1",
                "sys_name": "THERMAL-ML-001",
                "ntcip_device_type": "sensor",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 35.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # DAKTRONICS - Dynamic Message Signs
        # ============================================================
        # Daktronics Venus 1500
        {
            "vendor": "Daktronics",
            "vendor_family": "DMS Controller",
            "model": "Venus 1500",
            "firmware_version": "V4.2",
            "oui_prefixes": DAKTRONICS_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Daktronics Venus 1500 DMS Controller V4.2",
                "sys_object_id": "1.3.6.1.4.1.2407.1.1.1",
                "sys_name": "DMS-VENUS-001",
                "sys_location": "Highway Sign",
                "ntcip_device_type": "dms",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.02,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Daktronics Venus 7000
        {
            "vendor": "Daktronics",
            "vendor_family": "DMS Controller",
            "model": "Venus 7000",
            "firmware_version": "V4.2",
            "oui_prefixes": DAKTRONICS_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Daktronics Venus 7000 DMS Controller V4.2 Build 4021",
                "sys_object_id": "1.3.6.1.4.1.2407.1.2.1",
                "sys_name": "DMS-V7000-001",
                "ntcip_device_type": "dms",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 60.0,
                "mean_ms": 18.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
                "outlier_probability": 0.02,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # KAPSCH - Toll Collection
        # ============================================================
        # Kapsch TCS 2000
        {
            "vendor": "Kapsch",
            "vendor_family": "Toll Collection",
            "model": "TCS 2000",
            "firmware_version": "V3.6.0",
            "oui_prefixes": KAPSCH_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Kapsch TrafficCom TCS 2000 Toll Controller V3.6.0",
                "sys_object_id": "1.3.6.1.4.1.22706.1.1.2",
                "sys_name": "TOLL-TCS-001",
                "sys_location": "Toll Plaza",
                "ntcip_device_type": "toll",
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.0005,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # Q-FREE - Roadside Units
        # ============================================================
        # Q-Free RSU 5000
        {
            "vendor": "Q-Free",
            "vendor_family": "RSU",
            "model": "RSU 5000",
            "firmware_version": "V2.9.0",
            "oui_prefixes": QFREE_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Q-Free RSU 5000 Roadside Unit V2.9.0",
                "sys_object_id": "1.3.6.1.4.1.32055.1.1.5",
                "sys_name": "RSU-5000-001",
                "sys_location": "Gantry",
                "ntcip_device_type": "rsu",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 15.0,
                "mean_ms": 5.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.0005,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # AXIS - ITS Cameras
        # ============================================================
        # Axis P1455-LE
        {
            "vendor": "Axis",
            "vendor_family": "ITS Camera",
            "model": "P1455-LE",
            "firmware_version": "10.12",
            "oui_prefixes": AXIS_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "AXIS P1455-LE Network Camera; 10.12; Linux 4.14 armv7l",
                "sys_object_id": "1.3.6.1.4.1.368.1.1.1",
                "sys_name": "CAM-AXIS-001",
                "sys_location": "Intersection",
                "ntcip_device_type": "camera",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
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
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.0005,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Axis P1448-LE
        {
            "vendor": "Axis",
            "vendor_family": "ITS Camera",
            "model": "P1448-LE",
            "firmware_version": "10.12",
            "oui_prefixes": AXIS_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "AXIS P1448-LE Network Camera; 10.12; Linux 4.14 armv7l",
                "sys_object_id": "1.3.6.1.4.1.368.1.1.2",
                "sys_name": "CAM-AXIS-4K-001",
                "ntcip_device_type": "camera",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 25.0,
                "mean_ms": 6.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.0005,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # PELCO - PTZ Cameras
        # ============================================================
        # Pelco Spectra Enhanced
        {
            "vendor": "Pelco",
            "vendor_family": "PTZ Camera",
            "model": "Spectra Enhanced",
            "firmware_version": "V1.32",
            "oui_prefixes": PELCO_OUI_PREFIXES,
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Pelco Spectra Enhanced PTZ Camera V1.32",
                "sys_object_id": "1.3.6.1.4.1.17685.1.1.1",
                "sys_name": "PTZ-PELCO-001",
                "sys_location": "Tunnel Portal",
                "ntcip_device_type": "camera",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # BOSCH - ITS Cameras
        # ============================================================
        # Bosch MIC IP 7100i
        {
            "vendor": "Bosch",
            "vendor_family": "PTZ Camera",
            "model": "MIC IP 7100i",
            "firmware_version": "7.82.0127",
            "oui_prefixes": BOSCH_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "snmp_identity": {
                "sys_descr": "Bosch MIC IP 7100i PTZ Camera 7.82.0127",
                "sys_object_id": "1.3.6.1.4.1.3246.1.1.7100",
                "sys_name": "CAM-BOSCH-001",
                "ntcip_device_type": "camera",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # HIKVISION - ANPR Cameras
        # ============================================================
        # Hikvision DS-2CD7A26G0/P ANPR
        {
            "vendor": "Hikvision",
            "vendor_family": "ANPR Camera",
            "model": "DS-2CD7A26G0/P",
            "firmware_version": "V5.7.2",
            "oui_prefixes": HIKVISION_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "snmp_identity": {
                "sys_descr": "Hikvision DS-2CD7A26G0/P ANPR Camera V5.7.2",
                "sys_object_id": "1.3.6.1.4.1.39165.1.1.1",
                "sys_name": "ANPR-HIK-001",
                "sys_location": "Toll Lane",
                "ntcip_device_type": "camera",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 15.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.0005,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # SCHNEIDER - Traffic RTUs
        # ============================================================
        # Schneider SCADAPack 350 (Traffic variant)
        {
            "vendor": "Schneider",
            "vendor_family": "Traffic RTU",
            "model": "SCADAPack 350",
            "firmware_version": "V2.2.0",
            "oui_prefixes": [
                "00:00:54",  # Schneider Electric
                "00:80:F4",  # Schneider Electric
            ],
            "snmp_identity": {
                "sys_descr": "Schneider Electric SCADAPack 350 RTU Firmware V2.2.0",
                "sys_object_id": "1.3.6.1.4.1.3833.1.1.350",
                "sys_name": "RTU-SP350-001",
                "sys_location": "Highway Corridor",
                "ntcip_device_type": "rtu",
            },
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "SCADAPack 350",
                "major_minor_revision": "V2.2.0",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.02,
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
        # WEATHER STATIONS
        # ============================================================
        # Generic RWIS Weather Station
        {
            "vendor": "Vaisala",
            "vendor_family": "Weather Station",
            "model": "RWIS500",
            "firmware_version": "V4.2.1",
            "oui_prefixes": [
                "00:0C:D6",  # Vaisala
            ],
            "snmp_identity": {
                "sys_descr": "Vaisala RWIS500 Road Weather Station V4.2.1",
                "sys_object_id": "1.3.6.1.4.1.1206.4.2.4.1",
                "sys_name": "RWIS-001",
                "sys_location": "Mile Marker 47",
                "ntcip_device_type": "ess",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 100.0,
                "mean_ms": 30.0,
                "std_dev_ms": 15.0,
                "distribution": "gaussian",
                "outlier_probability": 0.03,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.005,
                "retry_behavior": True,
                "max_retries": 5,
            },
            "is_builtin": True,
        },

        # ============================================================
        # TUNNEL SYSTEMS
        # ============================================================
        # Generic Tunnel Ventilation Controller
        {
            "vendor": "Siemens",
            "vendor_family": "Tunnel System",
            "model": "TCS-VENT",
            "firmware_version": "V2.1.0",
            "oui_prefixes": SIEMENS_ITS_OUI_PREFIXES,
            "supported_protocols": ["bacnet", "snmp"],
            "snmp_identity": {
                "sys_descr": "Siemens TCS Tunnel Ventilation Controller V2.1.0",
                "sys_object_id": "1.3.6.1.4.1.4329.6.2.1",
                "sys_name": "VENT-001",
                "sys_location": "Tunnel Section A",
                "ntcip_device_type": "tunnel",
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Tunnel Lighting Controller
        {
            "vendor": "Siemens",
            "vendor_family": "Tunnel System",
            "model": "TCS-LIGHT",
            "firmware_version": "V2.0.5",
            "oui_prefixes": SIEMENS_ITS_OUI_PREFIXES,
            "supported_protocols": ["bacnet", "snmp"],
            "snmp_identity": {
                "sys_descr": "Siemens TCS Tunnel Lighting Controller V2.0.5",
                "sys_object_id": "1.3.6.1.4.1.4329.6.2.2",
                "sys_name": "LIGHT-001",
                "sys_location": "Tunnel Zone 1",
                "ntcip_device_type": "tunnel",
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # SIEMENS - LIGHTING CONTROLLERS (CLIMATIX)
        # ============================================================
        # Siemens Climatix C600 Lighting Controller
        {
            "vendor": "Siemens",
            "vendor_family": "Climatix",
            "model": "C600",
            "firmware_version": "V10.71",
            "oui_prefixes": SIEMENS_ITS_OUI_PREFIXES,
            "supported_protocols": ["bacnet", "snmp"],
            "snmp_identity": {
                "sys_descr": "Siemens Climatix C600 Controller V10.71",
                "sys_object_id": "1.3.6.1.4.1.4329.7.1.1",
                "sys_name": "CLIMATIX-001",
                "sys_location": "Tunnel Lighting Zone",
                "ntcip_device_type": "controller",
            },
            "bacnet_identity": {
                "vendor_id": 7,  # Siemens
                "model_name": "Climatix C600",
                "firmware_revision": "10.71",
                "application_software_version": "10.71",
                "object_name": "C600-Light-Ctrl",
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 32768,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 35.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # SIEMENS - NETWORK SWITCHES (SCALANCE)
        # ============================================================
        # Siemens SCALANCE X-200 Industrial Switch
        {
            "vendor": "Siemens",
            "vendor_family": "SCALANCE",
            "model": "X-200",
            "firmware_version": "V5.2.4",
            "oui_prefixes": SIEMENS_ITS_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "snmp_identity": {
                "sys_descr": "Siemens SCALANCE X-200 Industrial Ethernet Switch V5.2.4",
                "sys_object_id": "1.3.6.1.4.1.4329.3.1.1",
                "sys_name": "ITS-SW-001",
                "sys_location": "Field Cabinet",
                "sys_services": 78,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 15.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.0003,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Siemens SCALANCE XM-400 Managed Switch
        {
            "vendor": "Siemens",
            "vendor_family": "SCALANCE",
            "model": "XM-400",
            "firmware_version": "V6.3.0",
            "oui_prefixes": SIEMENS_ITS_OUI_PREFIXES,
            "supported_protocols": ["modbus", "snmp"],
            "snmp_identity": {
                "sys_descr": "Siemens SCALANCE XM-400 Industrial Ethernet Switch V6.3.0",
                "sys_object_id": "1.3.6.1.4.1.4329.3.2.1",
                "sys_name": "CORE-SW-001",
                "sys_location": "ITS Equipment Room",
                "sys_services": 78,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 10.0,
                "mean_ms": 3.0,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "timeout_probability": 0.0002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },

        # ============================================================
        # SCHNEIDER - TUNNEL RTU (TBOX)
        # ============================================================
        # Schneider TBox MS-CPU32 RTU
        {
            "vendor": "Schneider",
            "vendor_family": "TBox",
            "model": "MS-CPU32",
            "firmware_version": "V1.50.598",
            "oui_prefixes": [
                "00:00:54",  # Schneider Electric
                "00:80:F4",  # Schneider Electric
            ],
            "snmp_identity": {
                "sys_descr": "Schneider Electric TBox MS-CPU32 RTU V1.50.598",
                "sys_object_id": "1.3.6.1.4.1.3833.2.1.1",
                "sys_name": "TBOX-001",
                "sys_location": "Tunnel Monitoring",
                "ntcip_device_type": "rtu",
            },
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TBox MS-CPU32",
                "major_minor_revision": "V1.50.598",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 80.0,
                "mean_ms": 25.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.02,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # Schneider TBox LT2 RTU
        {
            "vendor": "Schneider",
            "vendor_family": "TBox",
            "model": "LT2",
            "firmware_version": "V1.48.520",
            "oui_prefixes": [
                "00:00:54",  # Schneider Electric
                "00:80:F4",  # Schneider Electric
            ],
            "snmp_identity": {
                "sys_descr": "Schneider Electric TBox LT2 RTU V1.48.520",
                "sys_object_id": "1.3.6.1.4.1.3833.2.1.2",
                "sys_name": "TBOX-LT2-001",
                "sys_location": "Field Cabinet",
            },
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TBox LT2",
                "major_minor_revision": "V1.48.520",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 100.0,
                "mean_ms": 30.0,
                "std_dev_ms": 15.0,
                "distribution": "gaussian",
                "outlier_probability": 0.025,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "timeout_probability": 0.003,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
    ]
