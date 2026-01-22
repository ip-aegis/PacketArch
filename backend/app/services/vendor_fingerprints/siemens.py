"""Siemens device fingerprints.

Comprehensive fingerprint data for Siemens SIMATIC devices
including S7-1500, S7-1500F (safety), S7-1200, S7-300, S7-400,
SINAMICS drives, SIMATIC HMIs, ET 200 I/O, and SCALANCE switches.

Based on real device characteristics for realistic traffic simulation.

Protocol Support:
- Siemens PLCs use PROFINET and S7comm as primary protocols
- Some PLCs also support Modbus TCP
- HMIs and I/O modules typically only use PROFINET
- SCALANCE switches support PROFINET and SNMP
"""

from typing import Any

# Siemens MAC OUI Prefixes (IEEE registrations)
SIEMENS_OUI_PREFIXES = [
    "00:0E:8C",  # Siemens AG
    "00:1B:1B",  # Siemens AG
    "00:1C:06",  # Siemens AG
    "64:9D:D8",  # Siemens AG
    "B8:2C:A0",  # Siemens AG
]

# Siemens PROFINET Vendor ID
SIEMENS_PROFINET_VENDOR_ID = 0x002A  # 42


def get_siemens_fingerprints() -> list[dict[str, Any]]:
    """Get all Siemens device fingerprints."""
    return [
        # ============================================================
        # S7-1500 PLCs
        # ============================================================
        # S7-1500 CPU 1517-3 PN/DP (High-Performance)
        {
            "vendor": "Siemens",
            "vendor_family": "S7-1500",
            "model": "6ES7 517-3AP00-0AB0",
            "firmware_version": "V3.0.3",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "s7comm", "modbus"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 517-3AP00-0AB0",
                "major_minor_revision": "V3.0.3",
                "vendor_url": "http://www.siemens.com",
                "product_name": "CPU 1517-3 PN/DP",
                "model_name": "S7-1500",
            },
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0303,
                "device_type": "CPU 1517-3 PN/DP",
                "station_name": "plc-cpu1517",
                "device_role": 2,  # Controller
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 517-3AP00-0AB0",
                "im0_hw_revision": 2,
                "im0_sw_revision": "V3.0.3",
            },
            "s7_identity": {
                "order_code": "6ES7 517-3AP00-0AB0",
                "module_type": "CPU 1517-3 PN/DP",
                "firmware_version": "V3.0.3",
                "hardware_version": "2",
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
                "min_ms": 0.25,
                "max_ms": 8.0,
                "mean_ms": 1.8,
                "std_dev_ms": 1.2,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 5.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "protocol_quirks": {
                "profinet_cycle_time_us": 1000,
                "s7_max_pdu_size": 960,
                "s7_max_jobs": 32,
            },
            "is_builtin": True,
        },
        # S7-1500 CPU 1511-1 PN (Entry-Level)
        {
            "vendor": "Siemens",
            "vendor_family": "S7-1500",
            "model": "6ES7 511-1AK02-0AB0",
            "firmware_version": "V3.0.2",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "s7comm", "modbus"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 511-1AK02-0AB0",
                "major_minor_revision": "V3.0.2",
                "product_name": "CPU 1511-1 PN",
                "model_name": "S7-1500",
            },
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0301,
                "device_type": "CPU 1511-1 PN",
                "station_name": "plc-cpu1511",
                "device_role": 2,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 511-1AK02-0AB0",
                "im0_hw_revision": 2,
                "im0_sw_revision": "V3.0.2",
            },
            "s7_identity": {
                "order_code": "6ES7 511-1AK02-0AB0",
                "module_type": "CPU 1511-1 PN",
                "firmware_version": "V3.0.2",
                "hardware_version": "2",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
                "window_scaling": 7,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 12.0,
                "mean_ms": 3.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0003,
                "timeout_probability": 0.00015,
            },
            "protocol_quirks": {
                "profinet_cycle_time_us": 2000,
                "s7_max_pdu_size": 480,
            },
            "is_builtin": True,
        },
        # ============================================================
        # S7-1500F Safety PLCs
        # ============================================================
        # S7-1500F CPU 1516F-3 PN/DP (Safety)
        {
            "vendor": "Siemens",
            "vendor_family": "S7-1500F",
            "model": "6ES7 516-3FN02-0AB0",
            "firmware_version": "V3.0.3",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "profisafe", "s7comm", "modbus"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 516-3FN02-0AB0",
                "major_minor_revision": "V3.0.3",
                "vendor_url": "http://www.siemens.com",
                "product_name": "CPU 1516F-3 PN/DP",
                "model_name": "S7-1500F",
            },
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x030F,  # F-series
                "device_type": "CPU 1516F-3 PN/DP",
                "station_name": "plc-s71500f",
                "device_role": 2,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 516-3FN02-0AB0",
                "im0_hw_revision": 2,
                "im0_sw_revision": "V3.0.3",
            },
            "s7_identity": {
                "order_code": "6ES7 516-3FN02-0AB0",
                "module_type": "CPU 1516F-3 PN/DP",
                "firmware_version": "V3.0.3",
                "hardware_version": "2",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
                "window_scaling": 7,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 0.25,
                "max_ms": 8.0,
                "mean_ms": 1.8,
                "std_dev_ms": 1.2,
                "distribution": "gaussian",
                "outlier_probability": 0.001,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0002,
                "timeout_probability": 0.00005,
            },
            "protocol_quirks": {
                "profinet_cycle_time_us": 500,  # Faster for safety
                "s7_max_pdu_size": 960,
                "profisafe_enabled": True,
                "f_host_mode": "standard",
            },
            "safety_config": {
                "sil_level": "SIL3",
                "category": "Cat4",
                "profisafe_enabled": True,
                "safety_watchdog_ms": 50,
                "f_destination_address": 1,
            },
            "is_builtin": True,
        },
        # S7-1200F CPU 1214FC (Safety)
        {
            "vendor": "Siemens",
            "vendor_family": "S7-1200F",
            "model": "6ES7 214-1HF40-0XB0",
            "firmware_version": "V4.5.2",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "profisafe", "s7comm", "modbus"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 214-1HF40-0XB0",
                "major_minor_revision": "V4.5.2",
                "product_name": "CPU 1214FC DC/DC/DC",
                "model_name": "S7-1200F",
            },
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x010F,
                "device_type": "CPU 1214FC DC/DC/DC",
                "station_name": "plc-s71200f",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 214-1HF40-0XB0",
                "im0_hw_revision": 4,
                "im0_sw_revision": "V4.5.2",
            },
            "s7_identity": {
                "order_code": "6ES7 214-1HF40-0XB0",
                "module_type": "CPU 1214FC DC/DC/DC",
                "firmware_version": "V4.5.2",
                "hardware_version": "4",
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
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "protocol_quirks": {
                "profisafe_enabled": True,
            },
            "safety_config": {
                "sil_level": "SIL3",
                "category": "Cat4",
                "profisafe_enabled": True,
                "safety_watchdog_ms": 100,
            },
            "is_builtin": True,
        },
        # ============================================================
        # S7-1200 PLCs
        # ============================================================
        # S7-1200 CPU 1214C DC/DC/DC
        {
            "vendor": "Siemens",
            "vendor_family": "S7-1200",
            "model": "6ES7 214-1AG40-0XB0",
            "firmware_version": "V4.5.2",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "s7comm", "modbus"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 214-1AG40-0XB0",
                "major_minor_revision": "V4.5.2",
                "product_name": "CPU 1214C DC/DC/DC",
                "model_name": "S7-1200",
            },
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x010D,
                "device_type": "CPU 1214C DC/DC/DC",
                "station_name": "plc-s71200",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 214-1AG40-0XB0",
                "im0_hw_revision": 4,
                "im0_sw_revision": "V4.5.2",
            },
            "s7_identity": {
                "order_code": "6ES7 214-1AG40-0XB0",
                "module_type": "CPU 1214C DC/DC/DC",
                "firmware_version": "V4.5.2",
                "hardware_version": "4",
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
                "outlier_probability": 0.004,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
            "protocol_quirks": {
                "s7_max_pdu_size": 240,
            },
            "is_builtin": True,
        },
        # ============================================================
        # S7-300/400 Legacy PLCs
        # ============================================================
        # S7-300 CPU 315-2 PN/DP
        {
            "vendor": "Siemens",
            "vendor_family": "S7-300",
            "model": "6ES7 315-2EH14-0AB0",
            "firmware_version": "V3.2.17",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "s7comm", "modbus"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 315-2EH14-0AB0",
                "major_minor_revision": "V3.2.17",
                "product_name": "CPU 315-2 PN/DP",
                "model_name": "S7-300",
            },
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0202,
                "device_type": "CPU 315-2 PN/DP",
                "station_name": "plc-s7300",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 315-2EH14-0AB0",
                "im0_hw_revision": 14,
                "im0_sw_revision": "V3.2.17",
            },
            "s7_identity": {
                "order_code": "6ES7 315-2EH14-0AB0",
                "module_type": "CPU 315-2 PN/DP",
                "firmware_version": "V3.2.17",
                "hardware_version": "14",
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
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.008,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0008,
                "timeout_probability": 0.0004,
            },
            "protocol_quirks": {
                "s7_max_pdu_size": 240,
            },
            "is_builtin": True,
        },
        # S7-400 CPU 416-3 PN/DP
        {
            "vendor": "Siemens",
            "vendor_family": "S7-400",
            "model": "6ES7 416-3ES07-0AB0",
            "firmware_version": "V6.0.9",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "s7comm", "modbus"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 416-3ES07-0AB0",
                "major_minor_revision": "V6.0.9",
                "product_name": "CPU 416-3 PN/DP",
                "model_name": "S7-400",
            },
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0203,
                "device_type": "CPU 416-3 PN/DP",
                "station_name": "plc-s7400",
                "device_role": 2,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 416-3ES07-0AB0",
                "im0_hw_revision": 7,
                "im0_sw_revision": "V6.0.9",
            },
            "s7_identity": {
                "order_code": "6ES7 416-3ES07-0AB0",
                "module_type": "CPU 416-3 PN/DP",
                "firmware_version": "V6.0.9",
                "hardware_version": "7",
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
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0003,
                "timeout_probability": 0.00015,
            },
            "protocol_quirks": {
                "s7_max_pdu_size": 960,
            },
            "is_builtin": True,
        },
        # ============================================================
        # SINAMICS Drives
        # ============================================================
        # SINAMICS G120C
        {
            "vendor": "Siemens",
            "vendor_family": "SINAMICS",
            "model": "6SL3210-1KE21-7UF1",
            "firmware_version": "V4.8",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "modbus"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6SL3210-1KE21-7UF1",
                "major_minor_revision": "V4.8",
                "product_name": "SINAMICS G120C",
                "model_name": "Variable Speed Drive",
            },
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0500,
                "device_type": "SINAMICS G120C",
                "station_name": "drive-g120c",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6SL3210-1KE21-7UF1",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V4.8",
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
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0005,
                "timeout_probability": 0.0003,
            },
            "is_builtin": True,
        },
        # SINAMICS S120
        {
            "vendor": "Siemens",
            "vendor_family": "SINAMICS",
            "model": "6SL3130-7TE25-5AA3",
            "firmware_version": "V5.2",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "modbus"],
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6SL3130-7TE25-5AA3",
                "major_minor_revision": "V5.2",
                "product_name": "SINAMICS S120",
                "model_name": "Servo Drive",
            },
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0501,
                "device_type": "SINAMICS S120",
                "station_name": "drive-s120",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6SL3130-7TE25-5AA3",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V5.2",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
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
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # SINAMICS G115D (PROFINET-only drive)
        {
            "vendor": "Siemens",
            "vendor_family": "SINAMICS",
            "model": "6SL3544-0FB21-1FA0",
            "firmware_version": "V1.2",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet"],
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0502,
                "device_type": "SINAMICS G115D",
                "station_name": "drive-g115d",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6SL3544-0FB21-1FA0",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V1.2",
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
                "distribution": "gaussian",
                "outlier_probability": 0.006,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0006,
                "timeout_probability": 0.0003,
            },
            "is_builtin": True,
        },
        # ============================================================
        # SIMATIC HMIs (PROFINET-only)
        # ============================================================
        # KTP900 Basic
        {
            "vendor": "Siemens",
            "vendor_family": "SIMATIC HMI",
            "model": "6AV2 123-2JB03-0AX0",
            "firmware_version": "V17.0.0",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet"],
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0403,
                "device_type": "KTP900 Basic",
                "station_name": "hmi-ktp900",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6AV2 123-2JB03-0AX0",
                "im0_hw_revision": 3,
                "im0_sw_revision": "V17.0.0",
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
                "max_ms": 100.0,
                "mean_ms": 25.0,
                "std_dev_ms": 15.0,
                "distribution": "lognormal",
                "outlier_probability": 0.01,
                "outlier_multiplier": 2.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.001,
                "timeout_probability": 0.0005,
            },
            "is_builtin": True,
        },
        # TP1200 Comfort
        {
            "vendor": "Siemens",
            "vendor_family": "SIMATIC HMI",
            "model": "6AV2 124-0MC01-0AX0",
            "firmware_version": "V17.0.0",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet"],
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0404,
                "device_type": "TP1200 Comfort",
                "station_name": "hmi-tp1200",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6AV2 124-0MC01-0AX0",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V17.0.0",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 80.0,
                "mean_ms": 20.0,
                "std_dev_ms": 12.0,
                "distribution": "lognormal",
                "outlier_probability": 0.008,
                "outlier_multiplier": 2.5,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0008,
                "timeout_probability": 0.0004,
            },
            "is_builtin": True,
        },
        # ============================================================
        # ET 200 Distributed I/O (PROFINET-only)
        # ============================================================
        # ET 200SP IM155-6
        {
            "vendor": "Siemens",
            "vendor_family": "ET 200SP",
            "model": "6ES7 155-6AU01-0BN0",
            "firmware_version": "V4.2.5",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet"],
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0601,
                "device_type": "ET 200SP IM155-6 PN",
                "station_name": "et200sp-im155",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 155-6AU01-0BN0",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V4.2.5",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 0.3,
                "max_ms": 8.0,
                "mean_ms": 2.0,
                "std_dev_ms": 1.2,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "protocol_quirks": {
                "profinet_cycle_time_us": 250,
            },
            "is_builtin": True,
        },
        # ET 200MP IM155-5
        {
            "vendor": "Siemens",
            "vendor_family": "ET 200MP",
            "model": "6ES7 155-5AA01-0AB0",
            "firmware_version": "V4.1.3",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet"],
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0602,
                "device_type": "ET 200MP IM155-5 PN",
                "station_name": "et200mp-im155",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 155-5AA01-0AB0",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V4.1.3",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 10.0,
                "mean_ms": 2.5,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
            "is_builtin": True,
        },
        # ============================================================
        # SCALANCE Network Infrastructure (PROFINET + SNMP)
        # ============================================================
        # SCALANCE XB208
        {
            "vendor": "Siemens",
            "vendor_family": "SCALANCE",
            "model": "6GK5 208-0BA00-2AB2",
            "firmware_version": "V5.2.6",
            "oui_prefixes": SIEMENS_OUI_PREFIXES,
            "supported_protocols": ["profinet", "snmp"],
            "profinet_identity": {
                "vendor_id": SIEMENS_PROFINET_VENDOR_ID,
                "device_id": 0x0700,
                "device_type": "SCALANCE XB208",
                "station_name": "switch-xb208",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6GK5 208-0BA00-2AB2",
                "im0_hw_revision": 2,
                "im0_sw_revision": "V5.2.6",
            },
            "snmp_identity": {
                "sys_descr": "Siemens SCALANCE XB208 Industrial Ethernet Switch V5.2.6",
                "sys_object_id": "1.3.6.1.4.1.4329.6.1.5.1",
                "sys_name": "SCALANCE-XB208",
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
                "max_ms": 15.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.5,
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
    ]
