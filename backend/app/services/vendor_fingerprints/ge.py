"""GE (General Electric) device fingerprints.

Comprehensive fingerprint data for GE industrial devices including
Proficy Historian, GE Fanuc PLCs, and related industrial systems.

Based on real device characteristics for realistic traffic simulation.
"""

from typing import Any

# GE MAC OUI Prefixes (IEEE registrations)
GE_OUI_PREFIXES = [
    "00:14:49",  # GE Fanuc Automation
    "00:60:B0",  # GE Energy
    "1C:39:47",  # GE
]


def get_ge_fingerprints() -> list[dict[str, Any]]:
    """Get all GE device fingerprints."""
    return [
        # ============================================================
        # Proficy Historian
        # ============================================================
        # Proficy Historian Server (CVE-2022-46660 - SQL Injection)
        {
            "vendor": "GE",
            "vendor_family": "Proficy",
            "model": "Proficy Historian",
            "firmware_version": "8.0",
            "oui_prefixes": GE_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "GE Digital",
                "product_code": "Proficy Historian",
                "major_minor_revision": "8.0",
                "vendor_url": "http://www.ge.com/digital",
                "product_name": "Proficy Historian Server",
                "model_name": "Proficy Historian 8.0",
            },
            "opc_ua_identity": {
                "application_name": "GE Proficy Historian",
                "application_uri": "urn:GE:Proficy:Historian",
                "product_uri": "http://www.ge.com/digital/proficy-historian",
                "manufacturer_name": "GE Digital",
                "product_name": "Proficy Historian",
                "software_version": "8.0.1",
                "build_number": "1234",
                "build_date": "2022-03-15T12:00:00Z",
            },
            "tcp_stack": {
                "ttl": 128,  # Windows-based server
                "window_size": 65535,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "nop_padding": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 200.0,
                "mean_ms": 50.0,
                "std_dev_ms": 30.0,
                "distribution": "lognormal",
                "outlier_probability": 0.008,
                "outlier_multiplier": 5.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.001,
                "timeout_probability": 0.0005,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "protocol_quirks": {
                "max_concurrent_connections": 500,
                "query_timeout_ms": 30000,
                "data_compression_enabled": True,
                "historian_api_version": "8.0",
            },
            "server_info": {
                "os_type": "Windows Server",
                "database_type": "Proprietary",
                "max_tags": 500000,
                "max_collection_rate_ms": 10,
                "supported_protocols": ["opc_ua", "opc_da", "modbus_tcp", "proficy_api"],
            },
            "is_builtin": True,
        },
        # Proficy Historian 7.x (Legacy version - also vulnerable)
        {
            "vendor": "GE",
            "vendor_family": "Proficy",
            "model": "Proficy Historian 7.2",
            "firmware_version": "7.2",
            "oui_prefixes": GE_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "GE Digital",
                "product_code": "Proficy Historian",
                "major_minor_revision": "7.2",
                "vendor_url": "http://www.ge.com/digital",
                "product_name": "Proficy Historian Server",
                "model_name": "Proficy Historian 7.2",
            },
            "opc_ua_identity": {
                "application_name": "GE Proficy Historian",
                "application_uri": "urn:GE:Proficy:Historian",
                "product_uri": "http://www.ge.com/digital/proficy-historian",
                "manufacturer_name": "GE Digital",
                "product_name": "Proficy Historian",
                "software_version": "7.2.0",
                "build_number": "5678",
                "build_date": "2020-06-10T12:00:00Z",
            },
            "tcp_stack": {
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
                "window_scaling": 7,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 8.0,
                "max_ms": 250.0,
                "mean_ms": 65.0,
                "std_dev_ms": 40.0,
                "distribution": "lognormal",
                "outlier_probability": 0.01,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0015,
                "timeout_probability": 0.0008,
            },
            "protocol_quirks": {
                "max_concurrent_connections": 300,
                "query_timeout_ms": 30000,
                "data_compression_enabled": True,
                "historian_api_version": "7.2",
            },
            "server_info": {
                "os_type": "Windows Server",
                "database_type": "Proprietary",
                "max_tags": 200000,
                "max_collection_rate_ms": 50,
                "supported_protocols": ["opc_ua", "opc_da", "modbus_tcp"],
            },
            "is_builtin": True,
        },
        # ============================================================
        # GE Fanuc / Emerson (PACSystems)
        # ============================================================
        # PACSystems RX3i CPE400 (Current high-end PLC)
        {
            "vendor": "GE",
            "vendor_family": "PACSystems",
            "model": "IC695CPE400",
            "firmware_version": "10.95",
            "oui_prefixes": GE_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "GE Automation",
                "product_code": "IC695CPE400",
                "major_minor_revision": "10.95",
                "vendor_url": "http://www.geautomation.com",
                "product_name": "PACSystems RX3i CPE400",
                "model_name": "PACSystems RX3i",
            },
            "ethernet_ip_identity": {
                "vendor_id": 82,  # GE Vendor ID
                "device_type": 14,  # Programmable Logic Controller
                "product_code": 400,
                "revision_major": 10,
                "revision_minor": 95,
                "serial_number": 0xAB12CD34,
                "product_name": "PACSystems RX3i CPE400",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,  # VxWorks-based
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0006,
                "timeout_probability": 0.0002,
            },
            "protocol_quirks": {
                "modbus_unit_id_behavior": "broadcast_supported",
                "max_modbus_registers_per_request": 125,
            },
            "is_builtin": True,
        },
        # PACSystems RX3i CPE310 (Mid-range)
        {
            "vendor": "GE",
            "vendor_family": "PACSystems",
            "model": "IC695CPE310",
            "firmware_version": "10.80",
            "oui_prefixes": GE_OUI_PREFIXES,
            "supported_protocols": ["modbus", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "GE Automation",
                "product_code": "IC695CPE310",
                "major_minor_revision": "10.80",
                "vendor_url": "http://www.geautomation.com",
                "product_name": "PACSystems RX3i CPE310",
                "model_name": "PACSystems RX3i",
            },
            "ethernet_ip_identity": {
                "vendor_id": 82,
                "device_type": 14,
                "product_code": 310,
                "revision_major": 10,
                "revision_minor": 80,
                "serial_number": 0xBC23DE45,
                "product_name": "PACSystems RX3i CPE310",
                "state": 3,
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
                "min_ms": 1.5,
                "max_ms": 40.0,
                "mean_ms": 10.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0008,
            },
            "is_builtin": True,
        },
        # VersaMax Micro (Small PLC)
        {
            "vendor": "GE",
            "vendor_family": "VersaMax",
            "model": "IC200UDD104",
            "firmware_version": "4.21",
            "oui_prefixes": GE_OUI_PREFIXES,
            "supported_protocols": ["modbus"],
            "modbus_identity": {
                "vendor_name": "GE Fanuc",
                "product_code": "IC200UDD104",
                "major_minor_revision": "4.21",
                "vendor_url": "http://www.gefanuc.com",
                "product_name": "VersaMax Micro PLC",
                "model_name": "VersaMax Micro",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 80.0,
                "mean_ms": 20.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
            },
            "is_builtin": True,
        },
    ]
