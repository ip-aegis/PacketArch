"""Siemens device profiles for OT traffic simulation.

Contains 15 comprehensive device profiles for Siemens PLCs, safety controllers,
drives, HMIs, and I/O systems with realistic timing models and payload templates.
"""

from typing import Any

SIEMENS_PROFILES: list[dict[str, Any]] = [
    # =========================================================================
    # S7-1500 Series PLCs
    # =========================================================================
    {
        "name": "Siemens S7-1517-3 PN/DP",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "High-performance S7-1500 CPU with PROFINET and PROFIBUS interfaces",
        "supported_protocols": ["profinet", "s7comm_plus", "modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 10,
            "cycle_time_ms": 1,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 1.5,
            "response_time_ms": {"min": 0.2, "max": 8},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 512,
                "ar_type": "io_controller",
                "alarm_handling": True,
            },
            "s7comm_plus": {
                "pdu_size": 960,
                "max_amq_caller": 32,
                "max_amq_callee": 32,
            },
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 125},
                "input_registers": {"start": 0, "count": 125},
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 100},
                {"action": "ar_establish", "delay_ms": 500},
                {"action": "param_download", "delay_ms": 200},
                {"action": "io_start", "delay_ms": 50},
            ],
            "shutdown_sequence": [
                {"action": "io_stop", "delay_ms": 50},
                {"action": "ar_release", "delay_ms": 200},
            ],
            "fault_behavior": "fail_safe",
            "watchdog_ms": 100,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "CPU 1517-3 PN/DP",
        },
        "vertical_hints": ["manufacturing", "automotive", "packaging"],
        "is_builtin": True,
    },
    {
        "name": "Siemens S7-1511-1 PN",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "Standard S7-1500 CPU for medium complexity applications",
        "supported_protocols": ["profinet", "s7comm_plus"],
        "timing_model": {
            "polling_interval_ms": 20,
            "cycle_time_ms": 2,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 2,
            "response_time_ms": {"min": 0.3, "max": 10},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 256,
                "ar_type": "io_controller",
                "alarm_handling": True,
            },
            "s7comm_plus": {
                "pdu_size": 480,
                "max_amq_caller": 16,
                "max_amq_callee": 16,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 100},
                {"action": "ar_establish", "delay_ms": 500},
                {"action": "io_start", "delay_ms": 50},
            ],
            "shutdown_sequence": [
                {"action": "io_stop", "delay_ms": 50},
                {"action": "ar_release", "delay_ms": 200},
            ],
            "fault_behavior": "stop",
            "watchdog_ms": 150,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "CPU 1511-1 PN",
        },
        "vertical_hints": ["manufacturing", "food_beverage", "packaging"],
        "is_builtin": True,
    },
    # =========================================================================
    # S7-1500F Safety PLCs
    # =========================================================================
    {
        "name": "Siemens S7-1516F-3 PN/DP",
        "device_type": "safety_plc",
        "role": "Safety Controller",
        "description": "Fail-safe S7-1500F CPU with PROFIsafe for SIL3/PLe safety applications",
        "supported_protocols": ["profinet", "profisafe", "s7comm_plus"],
        "timing_model": {
            "polling_interval_ms": 10,
            "cycle_time_ms": 1,
            "safety_cycle_ms": 10,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 1,
            "response_time_ms": {"min": 0.2, "max": 6},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 512,
                "ar_type": "io_controller",
                "alarm_handling": True,
            },
            "profisafe": {
                "f_dest_add": 1,
                "f_source_add": 100,
                "f_wd_time_ms": 50,
                "f_par_crc": True,
                "sil_level": "SIL3",
            },
            "s7comm_plus": {
                "pdu_size": 960,
                "max_amq_caller": 32,
                "max_amq_callee": 32,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 100},
                {"action": "ar_establish", "delay_ms": 500},
                {"action": "f_param_download", "delay_ms": 300},
                {"action": "safety_handshake", "delay_ms": 200},
                {"action": "io_start", "delay_ms": 50},
            ],
            "shutdown_sequence": [
                {"action": "safety_stop", "delay_ms": 100},
                {"action": "io_stop", "delay_ms": 50},
                {"action": "ar_release", "delay_ms": 200},
            ],
            "fault_behavior": "fail_safe_state",
            "safety_watchdog_ms": 50,
            "watchdog_ms": 100,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "CPU 1516F-3 PN/DP",
        },
        "vertical_hints": ["manufacturing", "automotive", "machinery"],
        "is_builtin": True,
    },
    {
        "name": "Siemens S7-1214FC",
        "device_type": "safety_plc",
        "role": "Compact Safety Controller",
        "description": "Compact fail-safe S7-1200F CPU for small safety applications",
        "supported_protocols": ["profinet", "profisafe", "s7comm"],
        "timing_model": {
            "polling_interval_ms": 50,
            "cycle_time_ms": 4,
            "safety_cycle_ms": 20,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 3,
            "response_time_ms": {"min": 0.5, "max": 15},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 128,
                "ar_type": "io_controller",
            },
            "profisafe": {
                "f_dest_add": 1,
                "f_source_add": 100,
                "f_wd_time_ms": 100,
                "f_par_crc": True,
                "sil_level": "SIL3",
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 150},
                {"action": "ar_establish", "delay_ms": 600},
                {"action": "f_param_download", "delay_ms": 400},
                {"action": "io_start", "delay_ms": 100},
            ],
            "shutdown_sequence": [
                {"action": "safety_stop", "delay_ms": 100},
                {"action": "ar_release", "delay_ms": 200},
            ],
            "fault_behavior": "fail_safe_state",
            "safety_watchdog_ms": 100,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "CPU 1214FC",
        },
        "vertical_hints": ["packaging", "machinery", "food_beverage"],
        "is_builtin": True,
    },
    # =========================================================================
    # Legacy S7-300/400 PLCs
    # =========================================================================
    {
        "name": "Siemens S7-315-2 PN/DP",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "S7-300 series CPU with PROFINET and PROFIBUS interfaces",
        "supported_protocols": ["profinet", "s7comm", "mpi"],
        "timing_model": {
            "polling_interval_ms": 50,
            "cycle_time_ms": 5,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 0.5, "max": 20},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 244,
                "ar_type": "io_controller",
            },
            "s7comm": {
                "pdu_size": 240,
                "max_amq_caller": 8,
                "max_amq_callee": 8,
                "rack": 0,
                "slot": 2,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 200},
                {"action": "s7_connect", "delay_ms": 300},
                {"action": "plc_cold_restart", "delay_ms": 2000},
            ],
            "shutdown_sequence": [
                {"action": "plc_stop", "delay_ms": 500},
                {"action": "s7_disconnect", "delay_ms": 100},
            ],
            "fault_behavior": "stop",
            "watchdog_ms": 200,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "CPU 315-2 PN/DP",
        },
        "vertical_hints": ["manufacturing", "water", "legacy"],
        "is_builtin": True,
    },
    {
        "name": "Siemens S7-416-3 PN/DP",
        "device_type": "plc",
        "role": "High-Performance Controller",
        "description": "High-end S7-400 CPU for complex process control",
        "supported_protocols": ["profinet", "s7comm", "profibus"],
        "timing_model": {
            "polling_interval_ms": 20,
            "cycle_time_ms": 2,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 3,
            "response_time_ms": {"min": 0.3, "max": 12},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 512,
                "ar_type": "io_controller",
            },
            "s7comm": {
                "pdu_size": 480,
                "max_amq_caller": 32,
                "max_amq_callee": 32,
                "rack": 0,
                "slot": 3,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 150},
                {"action": "s7_connect", "delay_ms": 200},
                {"action": "plc_warm_restart", "delay_ms": 1000},
            ],
            "shutdown_sequence": [
                {"action": "plc_stop", "delay_ms": 300},
                {"action": "s7_disconnect", "delay_ms": 100},
            ],
            "fault_behavior": "stop",
            "watchdog_ms": 150,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "CPU 416-3 PN/DP",
        },
        "vertical_hints": ["process", "oil_gas", "chemical"],
        "is_builtin": True,
    },
    # =========================================================================
    # SINAMICS Drives
    # =========================================================================
    {
        "name": "Siemens SINAMICS G120C",
        "device_type": "drive",
        "role": "Variable Frequency Drive",
        "description": "Compact inverter for pump, fan, and conveyor applications",
        "supported_protocols": ["profinet", "modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 50,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 1, "max": 25},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 32,
                "ar_type": "io_device",
                "telegram_type": "standard_telegram_1",
            },
            "modbus_tcp": {
                "holding_registers": {"start": 40001, "count": 50},
                "control_word_register": 40100,
                "status_word_register": 40101,
                "speed_reference_register": 40102,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 200},
                {"action": "ar_establish", "delay_ms": 800},
                {"action": "drive_ready", "delay_ms": 500},
            ],
            "shutdown_sequence": [
                {"action": "drive_disable", "delay_ms": 200},
                {"action": "ar_release", "delay_ms": 300},
            ],
            "fault_behavior": "coast_stop",
            "watchdog_ms": 500,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "SINAMICS G120C",
        },
        "vertical_hints": ["manufacturing", "hvac", "water"],
        "is_builtin": True,
    },
    {
        "name": "Siemens SINAMICS S120",
        "device_type": "servo",
        "role": "Servo Drive System",
        "description": "Modular drive system for motion control applications",
        "supported_protocols": ["profinet", "profidrive"],
        "timing_model": {
            "polling_interval_ms": 4,
            "cycle_time_ms": 1,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 0.5,
            "response_time_ms": {"min": 0.2, "max": 4},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 64,
                "ar_type": "io_device",
                "isochronous_mode": True,
            },
            "profidrive": {
                "telegram_type": "telegram_111",
                "axis_count": 6,
                "position_control": True,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 100},
                {"action": "ar_establish", "delay_ms": 500},
                {"action": "axis_enable", "delay_ms": 200},
                {"action": "servo_on", "delay_ms": 100},
            ],
            "shutdown_sequence": [
                {"action": "servo_off", "delay_ms": 50},
                {"action": "axis_disable", "delay_ms": 200},
                {"action": "ar_release", "delay_ms": 200},
            ],
            "fault_behavior": "controlled_stop",
            "watchdog_ms": 50,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "SINAMICS S120",
        },
        "vertical_hints": ["manufacturing", "automotive", "machinery"],
        "is_builtin": True,
    },
    {
        "name": "Siemens SINAMICS G115D",
        "device_type": "drive",
        "role": "Distributed Drive",
        "description": "Distributed converter for conveyor systems with PROFINET",
        "supported_protocols": ["profinet"],
        "timing_model": {
            "polling_interval_ms": 100,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 10,
            "response_time_ms": {"min": 2, "max": 40},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 16,
                "ar_type": "io_device",
                "telegram_type": "standard_telegram_1",
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 300},
                {"action": "ar_establish", "delay_ms": 1000},
                {"action": "drive_ready", "delay_ms": 800},
            ],
            "shutdown_sequence": [
                {"action": "drive_disable", "delay_ms": 300},
                {"action": "ar_release", "delay_ms": 400},
            ],
            "fault_behavior": "coast_stop",
            "watchdog_ms": 1000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "SINAMICS G115D",
        },
        "vertical_hints": ["logistics", "packaging", "manufacturing"],
        "is_builtin": True,
    },
    # =========================================================================
    # HMI Panels
    # =========================================================================
    {
        "name": "Siemens KTP900 Basic",
        "device_type": "hmi",
        "role": "Operator Panel",
        "description": "9-inch Basic Panel for simple visualization tasks",
        "supported_protocols": ["profinet", "s7comm"],
        "timing_model": {
            "polling_interval_ms": 500,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 50,
            "response_time_ms": {"min": 5, "max": 100},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 0,
                "ar_type": "io_supervisor",
            },
            "s7comm": {
                "pdu_size": 240,
                "read_vars_per_request": 20,
                "update_areas": [
                    {"db": 1, "start": 0, "length": 100},
                    {"db": 2, "start": 0, "length": 50},
                ],
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 500},
                {"action": "s7_connect", "delay_ms": 1000},
                {"action": "screen_load", "delay_ms": 2000},
            ],
            "shutdown_sequence": [
                {"action": "s7_disconnect", "delay_ms": 500},
            ],
            "fault_behavior": "display_error",
            "watchdog_ms": 5000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "KTP900 Basic",
        },
        "vertical_hints": ["manufacturing", "packaging", "machinery"],
        "is_builtin": True,
    },
    {
        "name": "Siemens TP1200 Comfort",
        "device_type": "hmi",
        "role": "Advanced Operator Panel",
        "description": "12-inch Comfort Panel with advanced visualization",
        "supported_protocols": ["profinet", "s7comm_plus", "opc_ua"],
        "timing_model": {
            "polling_interval_ms": 250,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 30,
            "response_time_ms": {"min": 3, "max": 60},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 0,
                "ar_type": "io_supervisor",
            },
            "s7comm_plus": {
                "pdu_size": 960,
                "read_vars_per_request": 50,
            },
            "opc_ua": {
                "endpoint_url": "opc.tcp://hmi:4840",
                "security_mode": "None",
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 300},
                {"action": "s7_connect", "delay_ms": 800},
                {"action": "opc_ua_connect", "delay_ms": 500},
                {"action": "screen_load", "delay_ms": 1500},
            ],
            "shutdown_sequence": [
                {"action": "opc_ua_disconnect", "delay_ms": 200},
                {"action": "s7_disconnect", "delay_ms": 300},
            ],
            "fault_behavior": "display_error",
            "watchdog_ms": 3000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "TP1200 Comfort",
        },
        "vertical_hints": ["manufacturing", "automotive", "process"],
        "is_builtin": True,
    },
    # =========================================================================
    # ET 200 Distributed I/O
    # =========================================================================
    {
        "name": "Siemens ET 200SP IM155-6",
        "device_type": "remote_io",
        "role": "Distributed I/O",
        "description": "Compact distributed I/O system for PROFINET",
        "supported_protocols": ["profinet"],
        "timing_model": {
            "polling_interval_ms": 4,
            "cycle_time_ms": 1,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 0.5,
            "response_time_ms": {"min": 0.1, "max": 3},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 128,
                "ar_type": "io_device",
                "modules": [
                    {"type": "DI", "channels": 16},
                    {"type": "DO", "channels": 16},
                    {"type": "AI", "channels": 4},
                    {"type": "AO", "channels": 2},
                ],
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 100},
                {"action": "ar_establish", "delay_ms": 400},
                {"action": "module_param", "delay_ms": 200},
                {"action": "io_start", "delay_ms": 50},
            ],
            "shutdown_sequence": [
                {"action": "io_stop", "delay_ms": 50},
                {"action": "ar_release", "delay_ms": 200},
            ],
            "fault_behavior": "substitute_values",
            "watchdog_ms": 50,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "ET 200SP IM155-6 PN",
        },
        "vertical_hints": ["manufacturing", "automotive", "packaging"],
        "is_builtin": True,
    },
    {
        "name": "Siemens ET 200MP IM155-5",
        "device_type": "remote_io",
        "role": "Distributed I/O",
        "description": "High-density distributed I/O with S7-1500 module form factor",
        "supported_protocols": ["profinet"],
        "timing_model": {
            "polling_interval_ms": 8,
            "cycle_time_ms": 2,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 1,
            "response_time_ms": {"min": 0.2, "max": 5},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 256,
                "ar_type": "io_device",
                "modules": [
                    {"type": "DI", "channels": 32},
                    {"type": "DO", "channels": 32},
                    {"type": "AI", "channels": 8},
                    {"type": "AO", "channels": 4},
                ],
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 100},
                {"action": "ar_establish", "delay_ms": 500},
                {"action": "module_param", "delay_ms": 300},
                {"action": "io_start", "delay_ms": 100},
            ],
            "shutdown_sequence": [
                {"action": "io_stop", "delay_ms": 100},
                {"action": "ar_release", "delay_ms": 300},
            ],
            "fault_behavior": "substitute_values",
            "watchdog_ms": 100,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "ET 200MP IM155-5 PN",
        },
        "vertical_hints": ["manufacturing", "process", "automotive"],
        "is_builtin": True,
    },
    # =========================================================================
    # Network Infrastructure
    # =========================================================================
    {
        "name": "Siemens SCALANCE XB208",
        "device_type": "switch",
        "role": "Industrial Switch",
        "description": "8-port unmanaged Industrial Ethernet switch",
        "supported_protocols": ["profinet", "snmp"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 100,
            "response_time_ms": {"min": 1, "max": 50},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 0,
                "ar_type": "none",
            },
            "snmp": {
                "version": "v2c",
                "community": "public",
                "oids": [
                    "1.3.6.1.2.1.1.1.0",  # sysDescr
                    "1.3.6.1.2.1.2.2",  # ifTable
                ],
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "link_up", "delay_ms": 3000},
                {"action": "profinet_dcp_identify", "delay_ms": 500},
            ],
            "shutdown_sequence": [
                {"action": "link_down", "delay_ms": 100},
            ],
            "fault_behavior": "port_isolation",
            "watchdog_ms": 10000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "SCALANCE XB208",
        },
        "vertical_hints": ["manufacturing", "infrastructure"],
        "is_builtin": True,
    },
    # =========================================================================
    # Field Devices
    # =========================================================================
    {
        "name": "Siemens SIMATIC RF200 Reader",
        "device_type": "sensor",
        "role": "RFID Reader",
        "description": "Compact RFID reader for identification and tracking",
        "supported_protocols": ["profinet"],
        "timing_model": {
            "polling_interval_ms": 100,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 20,
            "response_time_ms": {"min": 5, "max": 80},
        },
        "payload_templates": {
            "profinet": {
                "dcp_identify": True,
                "io_data_size": 64,
                "ar_type": "io_device",
                "tag_data_format": "iso_15693",
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "profinet_dcp_identify", "delay_ms": 200},
                {"action": "ar_establish", "delay_ms": 600},
                {"action": "antenna_enable", "delay_ms": 300},
            ],
            "shutdown_sequence": [
                {"action": "antenna_disable", "delay_ms": 100},
                {"action": "ar_release", "delay_ms": 300},
            ],
            "fault_behavior": "no_tag_response",
            "watchdog_ms": 1000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Siemens",
            "fingerprint_model": "RF200",
        },
        "vertical_hints": ["logistics", "manufacturing", "automotive"],
        "is_builtin": True,
    },
]
