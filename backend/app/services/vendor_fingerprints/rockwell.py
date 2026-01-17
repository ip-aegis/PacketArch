"""Rockwell Automation device fingerprints.

Comprehensive fingerprint data for Rockwell Automation / Allen-Bradley devices
including ControlLogix, CompactLogix, GuardLogix (safety), PowerFlex drives,
Kinetix servos, PanelView HMIs, and I/O modules.

Based on real device characteristics for realistic traffic simulation.
"""

from typing import Any

# Rockwell Automation MAC OUI Prefixes (IEEE registrations)
ROCKWELL_OUI_PREFIXES = [
    "00:00:BC",  # Allen-Bradley
    "00:1D:9C",  # Rockwell Automation
    "5C:88:16",  # Rockwell Automation
]


def get_rockwell_fingerprints() -> list[dict[str, Any]]:
    """Get all Rockwell Automation device fingerprints."""
    return [
        # ============================================================
        # ControlLogix PLCs
        # ============================================================
        # ControlLogix L85E (High-Performance)
        {
            "vendor": "Rockwell",
            "vendor_family": "ControlLogix",
            "model": "1756-L85E",
            "firmware_version": "33.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L85E/B",
                "major_minor_revision": "33.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L85E Logix5585E Controller",
                "model_name": "ControlLogix 5585E",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,  # Programmable Logic Controller
                "product_code": 85,
                "revision_major": 33,
                "revision_minor": 11,
                "serial_number": 0x1A2B3C4D,
                "product_name": "1756-L85E/B LOGIX5585E",
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
                "min_ms": 0.3,
                "max_ms": 12.0,
                "mean_ms": 2.5,
                "std_dev_ms": 1.8,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "protocol_quirks": {
                "enip_encap_timeout_ms": 10000,
                "cip_connection_timeout_multiplier": 32,
                "forward_open_max_connections": 64,
            },
            # Extended CIP Identity Object attributes (Class 0x01) for deep fingerprinting
            "cip_identity_object": {
                "status": 0x0030,  # Attr 5: owned + configured
                "configuration_consistency_value": 0xA5B6C7D8,  # Attr 9
                "heartbeat_interval": 250,  # Attr 10 (ms)
                "active_language": "English",  # Attr 11
                "supported_languages": ["English"],  # Attr 12
                "protection_mode": 0,  # Attr 19: 0=no protection
                "maximum_cip_connections": 64,  # Attr 20
            },
            # Connection Manager Object (Class 0x06)
            "connection_manager_object": {
                "max_connections": 64,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,  # Class 1, Production trigger
                "supported_connection_types": ["implicit", "explicit", "unconnected_send"],
            },
            # Assembly Objects (Class 0x04)
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 500},
                "output": {"instance": 101, "size_bytes": 500},
                "config": {"instance": 102, "size_bytes": 64},
            },
            # ListServices response
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,  # TCP + UDP encapsulation
                },
            },
            "is_builtin": True,
        },
        # ControlLogix L73 (Mid-Range)
        {
            "vendor": "Rockwell",
            "vendor_family": "ControlLogix",
            "model": "1756-L73",
            "firmware_version": "32.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L73/B",
                "major_minor_revision": "32.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L73 Logix5573 Controller",
                "model_name": "ControlLogix 5573",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 73,
                "revision_major": 32,
                "revision_minor": 11,
                "serial_number": 0x2B3C4D5E,
                "product_name": "1756-L73/B LOGIX5573",
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
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xB6C7D8E9,
                "heartbeat_interval": 250,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 48,
            },
            "connection_manager_object": {
                "max_connections": 48,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 496},
                "output": {"instance": 101, "size_bytes": 496},
                "config": {"instance": 102, "size_bytes": 64},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # CompactLogix PLCs
        # ============================================================
        # CompactLogix L33ER
        {
            "vendor": "Rockwell",
            "vendor_family": "CompactLogix",
            "model": "1769-L33ER",
            "firmware_version": "33.013",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
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
                "serial_number": 0x3C4D5E6F,
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
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xC7D8E9FA,
                "heartbeat_interval": 250,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 32,
            },
            "connection_manager_object": {
                "max_connections": 32,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 248},
                "output": {"instance": 101, "size_bytes": 248},
                "config": {"instance": 102, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # CompactLogix L24ER-QB1B
        {
            "vendor": "Rockwell",
            "vendor_family": "CompactLogix",
            "model": "1769-L24ER-QB1B",
            "firmware_version": "33.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1769-L24ER-QB1B",
                "major_minor_revision": "33.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1769-L24ER-QB1B CompactLogix Controller",
                "model_name": "CompactLogix 5370",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 90,
                "revision_major": 33,
                "revision_minor": 11,
                "serial_number": 0x4D5E6F7A,
                "product_name": "1769-L24ER-QB1B LOGIX5370",
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
                "min_ms": 1.0,
                "max_ms": 25.0,
                "mean_ms": 6.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.001,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xD8E9FA0B,
                "heartbeat_interval": 250,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 24,
            },
            "connection_manager_object": {
                "max_connections": 24,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 248},
                "output": {"instance": 101, "size_bytes": 248},
                "config": {"instance": 102, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # GuardLogix Safety PLCs
        # ============================================================
        # GuardLogix L83ES (High-Performance Safety)
        {
            "vendor": "Rockwell",
            "vendor_family": "GuardLogix",
            "model": "1756-L83ES",
            "firmware_version": "32.014",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L83ES/B",
                "major_minor_revision": "32.014",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L83ES GuardLogix5583ES Safety Controller",
                "model_name": "GuardLogix 5583ES",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 166,  # GuardLogix product code
                "revision_major": 32,
                "revision_minor": 14,
                "serial_number": 0x5E6F7A8B,
                "product_name": "1756-L83ES/B GUARDLOGIX5583ES",
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
                "min_ms": 0.4,
                "max_ms": 12.0,
                "mean_ms": 2.8,
                "std_dev_ms": 1.8,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0003,  # Lower for safety
                "timeout_probability": 0.0001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "protocol_quirks": {
                "enip_encap_timeout_ms": 10000,
                "cip_connection_timeout_multiplier": 32,
                "safety_network_number": 1,
                "cip_safety_enabled": True,
            },
            "safety_config": {
                "sil_level": "SIL3",
                "category": "Cat4",
                "safety_watchdog_ms": 50,
                "safe_state_behavior": "de-energize",
            },
            "cip_identity_object": {
                "status": 0x0070,  # owned + configured + safety
                "configuration_consistency_value": 0xE9FA0B1C,
                "heartbeat_interval": 100,  # Faster for safety
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 64,
            },
            "connection_manager_object": {
                "max_connections": 64,
                "connection_timeout_multiplier": 16,  # Shorter for safety
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send", "safety"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 500},
                "output": {"instance": 101, "size_bytes": 500},
                "config": {"instance": 102, "size_bytes": 64},
                "safety_input": {"instance": 700, "size_bytes": 128},
                "safety_output": {"instance": 701, "size_bytes": 128},
            },
            # CIP Safety attributes for GuardLogix
            "cip_safety": {
                "safety_network_number": 1,
                "safety_signature": 0x1A2B3C4D5E6F,
                "configuration_signature": 0x6F5E4D3C2B1A,
                "time_correction_network_timestamp": 0,
                "tunid": (1, 1, 0, 0),  # Target Unique Network Identifier
                "snn_format": "time_based",
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # GuardLogix L73S (Mid-Range Safety)
        {
            "vendor": "Rockwell",
            "vendor_family": "GuardLogix",
            "model": "1756-L73S",
            "firmware_version": "32.012",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L73S/B",
                "major_minor_revision": "32.012",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L73S GuardLogix5573S Safety Controller",
                "model_name": "GuardLogix 5573S",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 167,
                "revision_major": 32,
                "revision_minor": 12,
                "serial_number": 0x6F7A8B9C,
                "product_name": "1756-L73S/B GUARDLOGIX5573S",
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
                "min_ms": 0.5,
                "max_ms": 15.0,
                "mean_ms": 3.5,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
            "protocol_quirks": {
                "enip_encap_timeout_ms": 10000,
                "cip_safety_enabled": True,
            },
            "safety_config": {
                "sil_level": "SIL3",
                "category": "Cat4",
                "safety_watchdog_ms": 50,
            },
            "cip_identity_object": {
                "status": 0x0070,
                "configuration_consistency_value": 0xFA0B1C2D,
                "heartbeat_interval": 100,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 48,
            },
            "connection_manager_object": {
                "max_connections": 48,
                "connection_timeout_multiplier": 16,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send", "safety"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 496},
                "output": {"instance": 101, "size_bytes": 496},
                "config": {"instance": 102, "size_bytes": 64},
                "safety_input": {"instance": 700, "size_bytes": 100},
                "safety_output": {"instance": 701, "size_bytes": 100},
            },
            "cip_safety": {
                "safety_network_number": 1,
                "safety_signature": 0x2B3C4D5E6F70,
                "configuration_signature": 0x706F5E4D3C2B,
                "time_correction_network_timestamp": 0,
                "tunid": (1, 1, 0, 0),
                "snn_format": "time_based",
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # Compact GuardLogix L33ERMS
        {
            "vendor": "Rockwell",
            "vendor_family": "Compact GuardLogix",
            "model": "1769-L33ERMS",
            "firmware_version": "33.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1769-L33ERMS",
                "major_minor_revision": "33.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1769-L33ERMS Compact GuardLogix Safety Controller",
                "model_name": "Compact GuardLogix 5370S",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 168,
                "revision_major": 33,
                "revision_minor": 11,
                "serial_number": 0x7A8B9CAD,
                "product_name": "1769-L33ERMS COMPACTGUARDLOGIX",
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
                "exception_probability": 0.0004,
            },
            "protocol_quirks": {
                "cip_safety_enabled": True,
            },
            "safety_config": {
                "sil_level": "SIL2",
                "category": "Cat3",
                "safety_watchdog_ms": 100,
            },
            "cip_identity_object": {
                "status": 0x0070,
                "configuration_consistency_value": 0x0B1C2D3E,
                "heartbeat_interval": 100,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 32,
            },
            "connection_manager_object": {
                "max_connections": 32,
                "connection_timeout_multiplier": 16,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send", "safety"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 248},
                "output": {"instance": 101, "size_bytes": 248},
                "config": {"instance": 102, "size_bytes": 32},
                "safety_input": {"instance": 700, "size_bytes": 64},
                "safety_output": {"instance": 701, "size_bytes": 64},
            },
            "cip_safety": {
                "safety_network_number": 1,
                "safety_signature": 0x3C4D5E6F7081,
                "configuration_signature": 0x81706F5E4D3C,
                "time_correction_network_timestamp": 0,
                "tunid": (1, 1, 0, 0),
                "snn_format": "time_based",
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # PowerFlex Drives
        # ============================================================
        # PowerFlex 525
        {
            "vendor": "Rockwell",
            "vendor_family": "PowerFlex",
            "model": "25B-D030N104",
            "firmware_version": "7.001",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "25B-D030N104",
                "major_minor_revision": "7.001",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "PowerFlex 525 AC Drive",
                "model_name": "PowerFlex 525",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 2,  # AC Drive
                "product_code": 525,
                "revision_major": 7,
                "revision_minor": 1,
                "serial_number": 0x8B9CADBE,
                "product_name": "POWERFLEX 525",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,  # VxWorks
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 40.0,
                "mean_ms": 10.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.001,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0x1C2D3E4F,
                "heartbeat_interval": 500,  # Drives have longer heartbeat
                "active_language": "English",
                "supported_languages": ["English", "Spanish", "German", "French"],
                "protection_mode": 0,
                "maximum_cip_connections": 16,
            },
            "connection_manager_object": {
                "max_connections": 16,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 32},
                "output": {"instance": 101, "size_bytes": 32},
                "config": {"instance": 102, "size_bytes": 16},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # PowerFlex 753
        {
            "vendor": "Rockwell",
            "vendor_family": "PowerFlex",
            "model": "20F-D052N103",
            "firmware_version": "19.003",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "20F-D052N103",
                "major_minor_revision": "19.003",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "PowerFlex 753 AC Drive",
                "model_name": "PowerFlex 753",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 2,
                "product_code": 753,
                "revision_major": 19,
                "revision_minor": 3,
                "serial_number": 0x9CADBECF,
                "product_name": "POWERFLEX 753",
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
                "max_ms": 35.0,
                "mean_ms": 8.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0008,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0x2D3E4F50,
                "heartbeat_interval": 500,
                "active_language": "English",
                "supported_languages": ["English", "Spanish", "German", "French", "Chinese"],
                "protection_mode": 0,
                "maximum_cip_connections": 32,
            },
            "connection_manager_object": {
                "max_connections": 32,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 64},
                "output": {"instance": 101, "size_bytes": 64},
                "config": {"instance": 102, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # Kinetix Servo Drives
        # ============================================================
        # Kinetix 5500
        {
            "vendor": "Rockwell",
            "vendor_family": "Kinetix",
            "model": "2198-D012-ERS3",
            "firmware_version": "6.003",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "2198-D012-ERS3",
                "major_minor_revision": "6.003",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "Kinetix 5500 Servo Drive",
                "model_name": "Kinetix 5500",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 3,  # Servo Drive
                "product_code": 5500,
                "revision_major": 6,
                "revision_minor": 3,
                "serial_number": 0xADBECFD0,
                "product_name": "KINETIX 5500",
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
                "mean_ms": 3.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0005,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0x3E4F5061,
                "heartbeat_interval": 250,  # Servo has fast heartbeat
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 8,
            },
            "connection_manager_object": {
                "max_connections": 8,
                "connection_timeout_multiplier": 16,  # Fast timeout for motion
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 32},
                "output": {"instance": 101, "size_bytes": 32},
                "config": {"instance": 102, "size_bytes": 16},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # PanelView HMIs
        # ============================================================
        # PanelView Plus 7 Standard (10")
        {
            "vendor": "Rockwell",
            "vendor_family": "PanelView Plus 7",
            "model": "2711P-T10C22D9P",
            "firmware_version": "12.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 24,  # Human-Machine Interface
                "product_code": 773,
                "revision_major": 12,
                "revision_minor": 11,
                "serial_number": 0xBECFD0E1,
                "product_name": "2711P-T10C22D9P",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,  # VxWorks/Linux
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
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0x4F506172,
                "heartbeat_interval": 1000,  # HMIs have longer heartbeat
                "active_language": "English",
                "supported_languages": ["English", "Spanish", "German", "French", "Chinese", "Japanese"],
                "protection_mode": 0,
                "maximum_cip_connections": 32,
            },
            "connection_manager_object": {
                "max_connections": 32,
                "connection_timeout_multiplier": 64,  # HMIs have longer timeout
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["explicit"],  # HMIs typically explicit only
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 128},
                "output": {"instance": 101, "size_bytes": 128},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0100,  # TCP only for HMI
                },
            },
            "is_builtin": True,
        },
        # PanelView 800
        {
            "vendor": "Rockwell",
            "vendor_family": "PanelView 800",
            "model": "2711R-T7T",
            "firmware_version": "6.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 24,
                "product_code": 800,
                "revision_major": 6,
                "revision_minor": 11,
                "serial_number": 0xCFD0E1F2,
                "product_name": "2711R-T7T",
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
                "min_ms": 5.0,
                "max_ms": 80.0,
                "mean_ms": 25.0,
                "std_dev_ms": 12.0,
                "distribution": "lognormal",
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0x50617283,
                "heartbeat_interval": 1000,
                "active_language": "English",
                "supported_languages": ["English", "Spanish", "German", "French"],
                "protection_mode": 0,
                "maximum_cip_connections": 16,
            },
            "connection_manager_object": {
                "max_connections": 16,
                "connection_timeout_multiplier": 64,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 64},
                "output": {"instance": 101, "size_bytes": 64},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0100,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # Remote I/O
        # ============================================================
        # Point I/O 1734-AENT
        {
            "vendor": "Rockwell",
            "vendor_family": "Point I/O",
            "model": "1734-AENT",
            "firmware_version": "6.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 12,  # Communications Adapter
                "product_code": 1734,
                "revision_major": 6,
                "revision_minor": 11,
                "serial_number": 0xD0E1F203,
                "product_name": "1734-AENT POINT IO",
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
                "min_ms": 0.5,
                "max_ms": 10.0,
                "mean_ms": 2.5,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2],
                "exception_probability": 0.0002,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0x61728394,
                "heartbeat_interval": 250,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 16,
            },
            "connection_manager_object": {
                "max_connections": 16,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 32},
                "output": {"instance": 101, "size_bytes": 32},
                "config": {"instance": 102, "size_bytes": 16},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # FLEX 5000 5094-AEN2TR
        {
            "vendor": "Rockwell",
            "vendor_family": "FLEX 5000",
            "model": "5094-AEN2TR",
            "firmware_version": "3.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 12,
                "product_code": 5094,
                "revision_major": 3,
                "revision_minor": 11,
                "serial_number": 0xE1F20314,
                "product_name": "5094-AEN2TR FLEX5000",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 0.3,
                "max_ms": 8.0,
                "mean_ms": 2.0,
                "std_dev_ms": 1.2,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2],
                "exception_probability": 0.0002,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0x728394A5,
                "heartbeat_interval": 250,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 32,
            },
            "connection_manager_object": {
                "max_connections": 32,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 64},
                "output": {"instance": 101, "size_bytes": 64},
                "config": {"instance": 102, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # Network Infrastructure
        # ============================================================
        # Stratix 5700 Switch
        {
            "vendor": "Rockwell",
            "vendor_family": "Stratix",
            "model": "1783-BMS10CGL",
            "firmware_version": "16.03.07",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 12,
                "product_code": 5700,
                "revision_major": 16,
                "revision_minor": 3,
                "serial_number": 0xF2031425,
                "product_name": "STRATIX 5700",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,  # Cisco IOS-based
                "window_size": 4128,
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
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0x8394A5B6,
                "heartbeat_interval": 500,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 64,
            },
            "connection_manager_object": {
                "max_connections": 64,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0x01,  # Switches are different
                "supported_connection_types": ["explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 8},
                "output": {"instance": 101, "size_bytes": 8},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0100,  # TCP only
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # MicroLogix PLCs (Legacy)
        # ============================================================
        # MicroLogix 1400 (Legacy - CVE-2019-10954 affects all versions)
        {
            "vendor": "Rockwell",
            "vendor_family": "MicroLogix",
            "model": "1766-L32BWA",
            "firmware_version": "21.007",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1766-L32BWA",
                "major_minor_revision": "21.007",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1766-L32BWA MicroLogix 1400",
                "model_name": "MicroLogix 1400",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 25,  # MicroLogix 1400
                "revision_major": 21,
                "revision_minor": 7,
                "serial_number": 0xA1B2C3D4,
                "product_name": "1766-L32BWA MICROLOGIX1400",
                "state": 3,
                "status": 0x0000,
            },
            "tcp_stack": {
                "ttl": 64,  # Embedded OS
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
                "timeout_probability": 0.001,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0x94A5B6C7,
                "heartbeat_interval": 500,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 8,  # Limited for legacy
            },
            "connection_manager_object": {
                "max_connections": 8,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 32},
                "output": {"instance": 101, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0100,  # TCP only for legacy
                },
            },
            "is_builtin": True,
        },
        # MicroLogix 1400 Series B with Analog (CVE-2019-10954)
        {
            "vendor": "Rockwell",
            "vendor_family": "MicroLogix",
            "model": "1766-L32BWAA",
            "firmware_version": "21.007",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1766-L32BWAA",
                "major_minor_revision": "21.007",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1766-L32BWAA MicroLogix 1400",
                "model_name": "MicroLogix 1400",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 25,
                "revision_major": 21,
                "revision_minor": 7,
                "serial_number": 0xA2B3C4D5,
                "product_name": "1766-L32BWAA MICROLOGIX1400",
                "state": 3,
                "status": 0x0000,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
                "timeout_probability": 0.001,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xA4B5C6D7,
                "heartbeat_interval": 500,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 8,
            },
            "connection_manager_object": {
                "max_connections": 8,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 32},
                "output": {"instance": 101, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0100,
                },
            },
            "is_builtin": True,
        },
        # MicroLogix 1400 Series B Extended (CVE-2019-10954)
        {
            "vendor": "Rockwell",
            "vendor_family": "MicroLogix",
            "model": "1766-L32BXB",
            "firmware_version": "21.007",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1766-L32BXB",
                "major_minor_revision": "21.007",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1766-L32BXB MicroLogix 1400",
                "model_name": "MicroLogix 1400",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 25,
                "revision_major": 21,
                "revision_minor": 7,
                "serial_number": 0xB3C4D5E6,
                "product_name": "1766-L32BXB MICROLOGIX1400",
                "state": 3,
                "status": 0x0000,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
                "timeout_probability": 0.001,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xB5C6D7E8,
                "heartbeat_interval": 500,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 8,
            },
            "connection_manager_object": {
                "max_connections": 8,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 32},
                "output": {"instance": 101, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0100,
                },
            },
            "is_builtin": True,
        },
        # MicroLogix 1400 Series A with Analog (CVE-2019-10954)
        {
            "vendor": "Rockwell",
            "vendor_family": "MicroLogix",
            "model": "1766-L32AWAA",
            "firmware_version": "21.007",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1766-L32AWAA",
                "major_minor_revision": "21.007",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1766-L32AWAA MicroLogix 1400",
                "model_name": "MicroLogix 1400",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 25,
                "revision_major": 21,
                "revision_minor": 7,
                "serial_number": 0xC4D5E6F7,
                "product_name": "1766-L32AWAA MICROLOGIX1400",
                "state": 3,
                "status": 0x0000,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
                "timeout_probability": 0.001,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xC6D7E8F9,
                "heartbeat_interval": 500,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 8,
            },
            "connection_manager_object": {
                "max_connections": 8,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 32},
                "output": {"instance": 101, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0100,
                },
            },
            "is_builtin": True,
        },
        # MicroLogix 1400 Series B Extended with Analog (CVE-2019-10954)
        {
            "vendor": "Rockwell",
            "vendor_family": "MicroLogix",
            "model": "1766-L32BXBA",
            "firmware_version": "21.007",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1766-L32BXBA",
                "major_minor_revision": "21.007",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1766-L32BXBA MicroLogix 1400",
                "model_name": "MicroLogix 1400",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 25,
                "revision_major": 21,
                "revision_minor": 7,
                "serial_number": 0xD5E6F708,
                "product_name": "1766-L32BXBA MICROLOGIX1400",
                "state": 3,
                "status": 0x0000,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
                "timeout_probability": 0.001,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xD7E8F90A,
                "heartbeat_interval": 500,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 8,
            },
            "connection_manager_object": {
                "max_connections": 8,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 32},
                "output": {"instance": 101, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0100,
                },
            },
            "is_builtin": True,
        },
        # MicroLogix 1100 (Older Legacy)
        {
            "vendor": "Rockwell",
            "vendor_family": "MicroLogix",
            "model": "1763-L16BWA",
            "firmware_version": "14.000",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1763-L16BWA",
                "major_minor_revision": "14.000",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1763-L16BWA MicroLogix 1100",
                "model_name": "MicroLogix 1100",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 22,  # MicroLogix 1100
                "revision_major": 14,
                "revision_minor": 0,
                "serial_number": 0xB2C3D4E5,
                "product_name": "1763-L16BWA MICROLOGIX1100",
                "state": 3,
                "status": 0x0000,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 60.0,
                "mean_ms": 15.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.003,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xA5B6C7D8,
                "heartbeat_interval": 500,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 4,  # Very limited for legacy
            },
            "connection_manager_object": {
                "max_connections": 4,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 16},
                "output": {"instance": 101, "size_bytes": 16},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0100,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # Additional ControlLogix PLCs
        # ============================================================
        # ControlLogix L81E (Entry-Level)
        {
            "vendor": "Rockwell",
            "vendor_family": "ControlLogix",
            "model": "1756-L81E",
            "firmware_version": "32.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L81E/B",
                "major_minor_revision": "32.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L81E Logix5581E Controller",
                "model_name": "ControlLogix 5581E",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 81,
                "revision_major": 32,
                "revision_minor": 11,
                "serial_number": 0xC3D4E5F6,
                "product_name": "1756-L81E/B LOGIX5581E",
                "state": 3,
                "status": 0x0000,
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
                "min_ms": 0.6,
                "max_ms": 18.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.5,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0006,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xB6C7D8E9,
                "heartbeat_interval": 250,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 40,
            },
            "connection_manager_object": {
                "max_connections": 40,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 496},
                "output": {"instance": 101, "size_bytes": 496},
                "config": {"instance": 102, "size_bytes": 64},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ControlLogix L82E (Mid-Range)
        {
            "vendor": "Rockwell",
            "vendor_family": "ControlLogix",
            "model": "1756-L82E",
            "firmware_version": "32.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L82E/B",
                "major_minor_revision": "32.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L82E Logix5582E Controller",
                "model_name": "ControlLogix 5582E",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 82,
                "revision_major": 32,
                "revision_minor": 11,
                "serial_number": 0xD4E5F607,
                "product_name": "1756-L82E/B LOGIX5582E",
                "state": 3,
                "status": 0x0000,
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
                "min_ms": 0.5,
                "max_ms": 15.0,
                "mean_ms": 3.2,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0005,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xC7D8E9FA,
                "heartbeat_interval": 250,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 48,
            },
            "connection_manager_object": {
                "max_connections": 48,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 500},
                "output": {"instance": 101, "size_bytes": 500},
                "config": {"instance": 102, "size_bytes": 64},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ControlLogix L84E (High-Range)
        {
            "vendor": "Rockwell",
            "vendor_family": "ControlLogix",
            "model": "1756-L84E",
            "firmware_version": "32.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L84E/B",
                "major_minor_revision": "32.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L84E Logix5584E Controller",
                "model_name": "ControlLogix 5584E",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 84,
                "revision_major": 32,
                "revision_minor": 11,
                "serial_number": 0xE5F60718,
                "product_name": "1756-L84E/B LOGIX5584E",
                "state": 3,
                "status": 0x0000,
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
                "min_ms": 0.35,
                "max_ms": 12.0,
                "mean_ms": 2.6,
                "std_dev_ms": 1.7,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0004,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xD8E9FA0B,
                "heartbeat_interval": 250,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 56,
            },
            "connection_manager_object": {
                "max_connections": 56,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 500},
                "output": {"instance": 101, "size_bytes": 500},
                "config": {"instance": 102, "size_bytes": 64},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # Additional CompactLogix PLCs
        # ============================================================
        # CompactLogix L30ERM (Motion)
        {
            "vendor": "Rockwell",
            "vendor_family": "CompactLogix",
            "model": "1769-L30ERM",
            "firmware_version": "33.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1769-L30ERM",
                "major_minor_revision": "33.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1769-L30ERM CompactLogix Controller",
                "model_name": "CompactLogix 5370",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 88,
                "revision_major": 33,
                "revision_minor": 11,
                "serial_number": 0xF6071829,
                "product_name": "1769-L30ERM/B LOGIX5370",
                "state": 3,
                "status": 0x0000,
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
                "min_ms": 0.9,
                "max_ms": 22.0,
                "mean_ms": 5.5,
                "std_dev_ms": 3.5,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0009,
            },
            "cip_identity_object": {
                "status": 0x0030,
                "configuration_consistency_value": 0xE9FA0B1C,
                "heartbeat_interval": 250,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 28,
            },
            "connection_manager_object": {
                "max_connections": 28,
                "connection_timeout_multiplier": 32,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 248},
                "output": {"instance": 101, "size_bytes": 248},
                "config": {"instance": 102, "size_bytes": 32},
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # ============================================================
        # Additional Compact GuardLogix (Safety)
        # ============================================================
        # Compact GuardLogix L31ES
        {
            "vendor": "Rockwell",
            "vendor_family": "Compact GuardLogix",
            "model": "1769-L31ES",
            "firmware_version": "33.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1769-L31ES",
                "major_minor_revision": "33.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1769-L31ES Compact GuardLogix Safety Controller",
                "model_name": "Compact GuardLogix 5370S",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 169,
                "revision_major": 33,
                "revision_minor": 11,
                "serial_number": 0x0718293A,
                "product_name": "1769-L31ES COMPACTGUARDLOGIX",
                "state": 3,
                "status": 0x0000,
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
                "exception_probability": 0.0004,
            },
            "protocol_quirks": {
                "cip_safety_enabled": True,
            },
            "safety_config": {
                "sil_level": "SIL2",
                "category": "Cat3",
                "safety_watchdog_ms": 100,
            },
            "cip_identity_object": {
                "status": 0x0070,  # Safety status
                "configuration_consistency_value": 0xFA0B1C2D,
                "heartbeat_interval": 100,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 24,
            },
            "connection_manager_object": {
                "max_connections": 24,
                "connection_timeout_multiplier": 16,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send", "safety"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 248},
                "output": {"instance": 101, "size_bytes": 248},
                "config": {"instance": 102, "size_bytes": 32},
                "safety_input": {"instance": 700, "size_bytes": 48},
                "safety_output": {"instance": 701, "size_bytes": 48},
            },
            "cip_safety": {
                "safety_network_number": 1,
                "safety_signature": 0x4D5E6F708192,
                "configuration_signature": 0x9281706F5E4D,
                "time_correction_network_timestamp": 0,
                "tunid": (1, 1, 0, 0),
                "snn_format": "time_based",
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
        # Compact GuardLogix L32ES
        {
            "vendor": "Rockwell",
            "vendor_family": "Compact GuardLogix",
            "model": "1769-L32ES",
            "firmware_version": "33.011",
            "oui_prefixes": ROCKWELL_OUI_PREFIXES,
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1769-L32ES",
                "major_minor_revision": "33.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1769-L32ES Compact GuardLogix Safety Controller",
                "model_name": "Compact GuardLogix 5370S",
            },
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 170,
                "revision_major": 33,
                "revision_minor": 11,
                "serial_number": 0x18293A4B,
                "product_name": "1769-L32ES COMPACTGUARDLOGIX",
                "state": 3,
                "status": 0x0000,
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
                "min_ms": 0.7,
                "max_ms": 18.0,
                "mean_ms": 4.5,
                "std_dev_ms": 2.8,
                "distribution": "gaussian",
            },
            "error_behavior": {
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
            },
            "protocol_quirks": {
                "cip_safety_enabled": True,
            },
            "safety_config": {
                "sil_level": "SIL2",
                "category": "Cat3",
                "safety_watchdog_ms": 100,
            },
            "cip_identity_object": {
                "status": 0x0070,
                "configuration_consistency_value": 0x0B1C2D3E,
                "heartbeat_interval": 100,
                "active_language": "English",
                "supported_languages": ["English"],
                "protection_mode": 0,
                "maximum_cip_connections": 28,
            },
            "connection_manager_object": {
                "max_connections": 28,
                "connection_timeout_multiplier": 16,
                "transport_class_trigger": 0xA3,
                "supported_connection_types": ["implicit", "explicit", "unconnected_send", "safety"],
            },
            "assembly_objects": {
                "input": {"instance": 100, "size_bytes": 248},
                "output": {"instance": 101, "size_bytes": 248},
                "config": {"instance": 102, "size_bytes": 32},
                "safety_input": {"instance": 700, "size_bytes": 56},
                "safety_output": {"instance": 701, "size_bytes": 56},
            },
            "cip_safety": {
                "safety_network_number": 1,
                "safety_signature": 0x5E6F708192A3,
                "configuration_signature": 0xA39281706F5E,
                "time_correction_network_timestamp": 0,
                "tunid": (1, 1, 0, 0),
                "snn_format": "time_based",
            },
            "list_services_response": {
                "communications": {
                    "type_code": 0x0100,
                    "name": "Communications",
                    "capability_flags": 0x0120,
                },
            },
            "is_builtin": True,
        },
    ]
