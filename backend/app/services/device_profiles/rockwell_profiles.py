"""Rockwell Automation device profiles.

Device profiles for Rockwell/Allen-Bradley devices including
ControlLogix, CompactLogix, GuardLogix, PowerFlex, Kinetix,
PanelView, Point I/O, and FLEX 5000.
"""

from typing import Any

ROCKWELL_PROFILES: list[dict[str, Any]] = [
    # ============================================================
    # ControlLogix PLCs
    # ============================================================
    {
        "name": "Rockwell ControlLogix L85E",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "High-performance ControlLogix 5585E controller with EtherNet/IP",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 20,
            "rpi_ms": 10,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 2,
            "response_time_ms": {"min": 0.3, "max": 12},
        },
        "payload_templates": [
            {
                "name": "Assembly Input",
                "assembly_instance": 100,
                "data_size": 128,
                "connection_type": "implicit",
            },
            {
                "name": "Assembly Output",
                "assembly_instance": 101,
                "data_size": 128,
                "connection_type": "implicit",
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 3000,
            "forward_open_required": True,
            "supports_unconnected_send": True,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "1756-L85E",
        },
        "vertical_hints": ["manufacturing", "automotive", "oil_gas"],
        "is_builtin": True,
    },
    {
        "name": "Rockwell ControlLogix L73",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "Mid-range ControlLogix 5573 controller with EtherNet/IP",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 50,
            "rpi_ms": 20,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 0.5, "max": 15},
        },
        "payload_templates": [
            {
                "name": "Assembly Input",
                "assembly_instance": 100,
                "data_size": 64,
                "connection_type": "implicit",
            },
            {
                "name": "Assembly Output",
                "assembly_instance": 101,
                "data_size": 64,
                "connection_type": "implicit",
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 3000,
            "forward_open_required": True,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "1756-L73",
        },
        "vertical_hints": ["manufacturing", "water"],
        "is_builtin": True,
    },
    # ============================================================
    # CompactLogix PLCs
    # ============================================================
    {
        "name": "Rockwell CompactLogix L33ER",
        "device_type": "plc",
        "role": "Machine Controller",
        "description": "CompactLogix 5370 controller for mid-size applications",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 50,
            "rpi_ms": 20,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 0.8, "max": 20},
        },
        "payload_templates": [
            {
                "name": "Assembly Input",
                "assembly_instance": 100,
                "data_size": 32,
                "connection_type": "implicit",
            },
            {
                "name": "Assembly Output",
                "assembly_instance": 101,
                "data_size": 32,
                "connection_type": "implicit",
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 2500,
            "forward_open_required": True,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "1769-L33ER",
        },
        "vertical_hints": ["manufacturing", "packaging"],
        "is_builtin": True,
    },
    {
        "name": "Rockwell CompactLogix L24ER-QB1B",
        "device_type": "plc",
        "role": "Machine Controller",
        "description": "Compact entry-level controller with onboard I/O",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 100,
            "rpi_ms": 50,
            "jitter_type": "gaussian",
            "jitter_min_ms": 1,
            "jitter_max_ms": 10,
            "response_time_ms": {"min": 1, "max": 25},
        },
        "payload_templates": [
            {
                "name": "Assembly Input",
                "assembly_instance": 100,
                "data_size": 16,
                "connection_type": "implicit",
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 2000,
            "forward_open_required": True,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "1769-L24ER-QB1B",
        },
        "vertical_hints": ["manufacturing"],
        "is_builtin": True,
    },
    # ============================================================
    # GuardLogix Safety PLCs
    # ============================================================
    {
        "name": "Rockwell GuardLogix L83ES",
        "device_type": "safety_plc",
        "role": "Safety Controller",
        "description": "High-performance safety controller with CIP Safety",
        "supported_protocols": ["ethernet_ip", "cip", "cip_safety"],
        "timing_model": {
            "polling_interval_ms": 10,
            "rpi_ms": 8,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 1,
            "response_time_ms": {"min": 0.4, "max": 12},
        },
        "payload_templates": [
            {
                "name": "Safety Input Assembly",
                "assembly_instance": 700,
                "data_size": 64,
                "connection_type": "safety",
            },
            {
                "name": "Safety Output Assembly",
                "assembly_instance": 701,
                "data_size": 64,
                "connection_type": "safety",
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 5000,
            "safety_signature_required": True,
            "forward_open_required": True,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "1756-L83ES",
        },
        "vertical_hints": ["manufacturing", "automotive", "oil_gas"],
        "is_builtin": True,
    },
    {
        "name": "Rockwell GuardLogix L73S",
        "device_type": "safety_plc",
        "role": "Safety Controller",
        "description": "Mid-range safety controller with CIP Safety",
        "supported_protocols": ["ethernet_ip", "cip", "cip_safety"],
        "timing_model": {
            "polling_interval_ms": 20,
            "rpi_ms": 10,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 2,
            "response_time_ms": {"min": 0.5, "max": 15},
        },
        "payload_templates": [
            {
                "name": "Safety Input Assembly",
                "assembly_instance": 700,
                "data_size": 32,
                "connection_type": "safety",
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 5000,
            "safety_signature_required": True,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "1756-L73S",
        },
        "vertical_hints": ["manufacturing", "oil_gas"],
        "is_builtin": True,
    },
    {
        "name": "Rockwell Compact GuardLogix L33ERMS",
        "device_type": "safety_plc",
        "role": "Safety Controller",
        "description": "Compact safety controller for machine safety",
        "supported_protocols": ["ethernet_ip", "cip", "cip_safety"],
        "timing_model": {
            "polling_interval_ms": 50,
            "rpi_ms": 20,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 0.8, "max": 20},
        },
        "payload_templates": [
            {
                "name": "Safety Input Assembly",
                "assembly_instance": 700,
                "data_size": 16,
                "connection_type": "safety",
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 4000,
            "safety_signature_required": True,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "1769-L33ERMS",
        },
        "vertical_hints": ["manufacturing", "packaging"],
        "is_builtin": True,
    },
    # ============================================================
    # PowerFlex Drives
    # ============================================================
    {
        "name": "Rockwell PowerFlex 525",
        "device_type": "drive",
        "role": "AC Drive",
        "description": "Compact AC drive with EtherNet/IP",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 100,
            "rpi_ms": 50,
            "jitter_type": "gaussian",
            "jitter_min_ms": 2,
            "jitter_max_ms": 20,
            "response_time_ms": {"min": 2, "max": 40},
        },
        "payload_templates": [
            {
                "name": "Drive Status",
                "assembly_instance": 21,
                "data_size": 8,
            },
            {
                "name": "Drive Command",
                "assembly_instance": 20,
                "data_size": 8,
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 8000,
            "ramp_time_ms": 5000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "25B-D030N104",
        },
        "vertical_hints": ["manufacturing", "water", "hvac"],
        "is_builtin": True,
    },
    {
        "name": "Rockwell PowerFlex 753",
        "device_type": "drive",
        "role": "AC Drive",
        "description": "High-power AC drive for demanding applications",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 50,
            "rpi_ms": 20,
            "jitter_type": "gaussian",
            "jitter_min_ms": 1,
            "jitter_max_ms": 10,
            "response_time_ms": {"min": 1.5, "max": 35},
        },
        "payload_templates": [
            {
                "name": "Drive Status",
                "assembly_instance": 21,
                "data_size": 16,
            },
            {
                "name": "Drive Command",
                "assembly_instance": 20,
                "data_size": 16,
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 10000,
            "ramp_time_ms": 8000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "20F-D052N103",
        },
        "vertical_hints": ["manufacturing", "oil_gas", "water"],
        "is_builtin": True,
    },
    # ============================================================
    # Kinetix Servo Drives
    # ============================================================
    {
        "name": "Rockwell Kinetix 5500",
        "device_type": "servo",
        "role": "Servo Drive",
        "description": "Integrated servo drive for motion control",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 4,
            "rpi_ms": 2,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 0.5,
            "response_time_ms": {"min": 0.5, "max": 15},
        },
        "payload_templates": [
            {
                "name": "Axis Status",
                "assembly_instance": 100,
                "data_size": 32,
            },
            {
                "name": "Axis Command",
                "assembly_instance": 101,
                "data_size": 32,
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 3000,
            "motion_profile": "trapezoidal",
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "2198-D012-ERS3",
        },
        "vertical_hints": ["manufacturing", "packaging", "automotive"],
        "is_builtin": True,
    },
    # ============================================================
    # PanelView HMIs
    # ============================================================
    {
        "name": "Rockwell PanelView Plus 7 (10\")",
        "device_type": "hmi",
        "role": "Operator Interface",
        "description": "10-inch color touchscreen HMI",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 500,
            "jitter_type": "uniform",
            "jitter_min_ms": 10,
            "jitter_max_ms": 100,
            "response_time_ms": {"min": 2, "max": 50},
        },
        "payload_templates": [],
        "behavior_model": {
            "startup_duration_ms": 30000,
            "screen_refresh_ms": 500,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "2711P-T10C22D9P",
        },
        "vertical_hints": ["manufacturing", "water", "oil_gas"],
        "is_builtin": True,
    },
    {
        "name": "Rockwell PanelView 800 (7\")",
        "device_type": "hmi",
        "role": "Operator Interface",
        "description": "7-inch compact HMI panel",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "uniform",
            "jitter_min_ms": 20,
            "jitter_max_ms": 150,
            "response_time_ms": {"min": 5, "max": 80},
        },
        "payload_templates": [],
        "behavior_model": {
            "startup_duration_ms": 20000,
            "screen_refresh_ms": 1000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "2711R-T7T",
        },
        "vertical_hints": ["manufacturing"],
        "is_builtin": True,
    },
    # ============================================================
    # Remote I/O
    # ============================================================
    {
        "name": "Rockwell Point I/O 1734-AENT",
        "device_type": "remote_io",
        "role": "I/O Adapter",
        "description": "Point I/O Ethernet adapter for distributed I/O",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 10,
            "rpi_ms": 5,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 1,
            "response_time_ms": {"min": 0.5, "max": 10},
        },
        "payload_templates": [
            {
                "name": "Input Data",
                "assembly_instance": 100,
                "data_size": 16,
            },
            {
                "name": "Output Data",
                "assembly_instance": 101,
                "data_size": 16,
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 2000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "1734-AENT",
        },
        "vertical_hints": ["manufacturing", "packaging"],
        "is_builtin": True,
    },
    {
        "name": "Rockwell FLEX 5000 5094-AEN2TR",
        "device_type": "remote_io",
        "role": "I/O Adapter",
        "description": "FLEX 5000 dual-port Ethernet adapter",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 5,
            "rpi_ms": 2,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 0.5,
            "response_time_ms": {"min": 0.3, "max": 8},
        },
        "payload_templates": [
            {
                "name": "Input Data",
                "assembly_instance": 100,
                "data_size": 64,
            },
            {
                "name": "Output Data",
                "assembly_instance": 101,
                "data_size": 64,
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 1500,
            "device_level_ring": True,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "5094-AEN2TR",
        },
        "vertical_hints": ["manufacturing", "automotive"],
        "is_builtin": True,
    },
    # ============================================================
    # Network Infrastructure
    # ============================================================
    {
        "name": "Rockwell Stratix 5700 Switch",
        "device_type": "switch",
        "role": "Industrial Switch",
        "description": "Managed industrial Ethernet switch",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "uniform",
            "jitter_min_ms": 5,
            "jitter_max_ms": 50,
            "response_time_ms": {"min": 0.5, "max": 20},
        },
        "payload_templates": [],
        "behavior_model": {
            "startup_duration_ms": 60000,
            "spanning_tree_enabled": True,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Rockwell",
            "fingerprint_model": "1783-BMS10CGL",
        },
        "vertical_hints": ["manufacturing", "oil_gas", "water"],
        "is_builtin": True,
    },
]
