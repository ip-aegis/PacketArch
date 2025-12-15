"""Schneider Electric device profiles for OT traffic simulation.

Contains 15 comprehensive device profiles for Schneider PLCs, safety controllers,
drives, HMIs, and I/O systems with realistic timing models and payload templates.
"""

from typing import Any

SCHNEIDER_PROFILES: list[dict[str, Any]] = [
    # =========================================================================
    # Modicon M580 Series PLCs
    # =========================================================================
    {
        "name": "Schneider M580 BMEH586040",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "High-performance M580 Hot Standby CPU with EtherNet/IP and Modbus",
        "supported_protocols": ["ethernet_ip", "modbus_tcp", "opc_ua"],
        "timing_model": {
            "polling_interval_ms": 20,
            "cycle_time_ms": 2,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 2,
            "response_time_ms": {"min": 0.5, "max": 15},
        },
        "payload_templates": {
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 14,
                "encapsulation_timeout_ms": 10000,
                "connection_type": "class3",
            },
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 125},
                "input_registers": {"start": 0, "count": 125},
                "coils": {"start": 0, "count": 2000},
                "discrete_inputs": {"start": 0, "count": 2000},
                "max_registers_per_request": 125,
            },
            "opc_ua": {
                "endpoint_url": "opc.tcp://plc:4840",
                "security_mode": "SignAndEncrypt",
                "security_policy": "Basic256Sha256",
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "enip_register", "delay_ms": 200},
                {"action": "modbus_init", "delay_ms": 100},
                {"action": "plc_run", "delay_ms": 500},
                {"action": "hot_standby_sync", "delay_ms": 1000},
            ],
            "shutdown_sequence": [
                {"action": "plc_stop", "delay_ms": 300},
                {"action": "enip_unregister", "delay_ms": 100},
            ],
            "fault_behavior": "failover_to_standby",
            "watchdog_ms": 100,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "BMEH586040",
        },
        "vertical_hints": ["process", "oil_gas", "water", "power"],
        "is_builtin": True,
    },
    {
        "name": "Schneider M580 Safety BMEP586040S",
        "device_type": "safety_plc",
        "role": "Safety Controller",
        "description": "M580 Safety CPU with CIP Safety for SIL3 applications",
        "supported_protocols": ["ethernet_ip", "cip_safety", "modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 10,
            "cycle_time_ms": 2,
            "safety_cycle_ms": 8,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 1,
            "response_time_ms": {"min": 0.3, "max": 10},
        },
        "payload_templates": {
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 14,
                "encapsulation_timeout_ms": 10000,
            },
            "cip_safety": {
                "safety_validator_id": 1,
                "configuration_signature": True,
                "time_coordination": True,
                "sil_level": "SIL3",
            },
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 125},
                "input_registers": {"start": 0, "count": 125},
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "enip_register", "delay_ms": 200},
                {"action": "safety_config_download", "delay_ms": 500},
                {"action": "safety_validation", "delay_ms": 300},
                {"action": "safety_run", "delay_ms": 200},
            ],
            "shutdown_sequence": [
                {"action": "safety_stop", "delay_ms": 100},
                {"action": "plc_stop", "delay_ms": 200},
                {"action": "enip_unregister", "delay_ms": 100},
            ],
            "fault_behavior": "fail_safe_state",
            "safety_watchdog_ms": 50,
            "watchdog_ms": 100,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "BMEP586040S",
        },
        "vertical_hints": ["process", "oil_gas", "chemical", "power"],
        "is_builtin": True,
    },
    # =========================================================================
    # Modicon M340 Series
    # =========================================================================
    {
        "name": "Schneider M340 BMXP3420302",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "M340 CPU with Modbus TCP and CANopen support",
        "supported_protocols": ["modbus_tcp", "ethernet_ip"],
        "timing_model": {
            "polling_interval_ms": 50,
            "cycle_time_ms": 5,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 1, "max": 25},
        },
        "payload_templates": {
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 100},
                "input_registers": {"start": 0, "count": 100},
                "coils": {"start": 0, "count": 1000},
                "max_registers_per_request": 100,
            },
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 14,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "modbus_init", "delay_ms": 200},
                {"action": "enip_register", "delay_ms": 300},
                {"action": "plc_run", "delay_ms": 500},
            ],
            "shutdown_sequence": [
                {"action": "plc_stop", "delay_ms": 300},
                {"action": "enip_unregister", "delay_ms": 100},
            ],
            "fault_behavior": "stop",
            "watchdog_ms": 200,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "BMXP3420302",
        },
        "vertical_hints": ["manufacturing", "water", "building"],
        "is_builtin": True,
    },
    # =========================================================================
    # Modicon M241/M251/M262 Compact PLCs
    # =========================================================================
    {
        "name": "Schneider M251 TM251MESE",
        "device_type": "plc",
        "role": "Compact Controller",
        "description": "M251 Logic Controller with Ethernet and serial ports",
        "supported_protocols": ["modbus_tcp", "ethernet_ip"],
        "timing_model": {
            "polling_interval_ms": 100,
            "cycle_time_ms": 10,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 10,
            "response_time_ms": {"min": 2, "max": 40},
        },
        "payload_templates": {
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 64},
                "input_registers": {"start": 0, "count": 64},
                "coils": {"start": 0, "count": 500},
                "max_registers_per_request": 64,
            },
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 14,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "modbus_init", "delay_ms": 300},
                {"action": "plc_run", "delay_ms": 800},
            ],
            "shutdown_sequence": [
                {"action": "plc_stop", "delay_ms": 300},
            ],
            "fault_behavior": "stop",
            "watchdog_ms": 500,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "TM251MESE",
        },
        "vertical_hints": ["packaging", "machinery", "building"],
        "is_builtin": True,
    },
    {
        "name": "Schneider M262 TM262L20MESE8T",
        "device_type": "plc",
        "role": "Motion Controller",
        "description": "M262 Motion Controller with dual Ethernet for motion and logic",
        "supported_protocols": ["modbus_tcp", "ethernet_ip", "sercos3"],
        "timing_model": {
            "polling_interval_ms": 20,
            "cycle_time_ms": 2,
            "motion_cycle_ms": 1,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 1,
            "response_time_ms": {"min": 0.5, "max": 10},
        },
        "payload_templates": {
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 125},
                "input_registers": {"start": 0, "count": 125},
                "max_registers_per_request": 125,
            },
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 14,
            },
            "sercos3": {
                "axis_count": 8,
                "cycle_time_us": 1000,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "modbus_init", "delay_ms": 100},
                {"action": "enip_register", "delay_ms": 200},
                {"action": "sercos_init", "delay_ms": 500},
                {"action": "motion_enable", "delay_ms": 200},
            ],
            "shutdown_sequence": [
                {"action": "motion_disable", "delay_ms": 100},
                {"action": "plc_stop", "delay_ms": 200},
            ],
            "fault_behavior": "controlled_stop",
            "watchdog_ms": 50,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "TM262L20MESE8T",
        },
        "vertical_hints": ["packaging", "machinery", "manufacturing"],
        "is_builtin": True,
    },
    # =========================================================================
    # Safety I/O
    # =========================================================================
    {
        "name": "Schneider TM5 Safety TM5CSLC100FS",
        "device_type": "safety_io",
        "role": "Safety I/O Module",
        "description": "TM5 Safety Logic Controller for distributed safety",
        "supported_protocols": ["ethernet_ip", "cip_safety"],
        "timing_model": {
            "polling_interval_ms": 20,
            "safety_cycle_ms": 10,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 2,
            "response_time_ms": {"min": 0.5, "max": 12},
        },
        "payload_templates": {
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 35,  # Safety device
            },
            "cip_safety": {
                "safety_validator_id": 1,
                "configuration_signature": True,
                "sil_level": "SIL3",
                "safety_inputs": 8,
                "safety_outputs": 4,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "enip_register", "delay_ms": 200},
                {"action": "safety_config_download", "delay_ms": 400},
                {"action": "safety_run", "delay_ms": 200},
            ],
            "shutdown_sequence": [
                {"action": "safety_stop", "delay_ms": 100},
                {"action": "enip_unregister", "delay_ms": 100},
            ],
            "fault_behavior": "fail_safe_state",
            "safety_watchdog_ms": 50,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "TM5CSLC100FS",
        },
        "vertical_hints": ["packaging", "machinery", "manufacturing"],
        "is_builtin": True,
    },
    # =========================================================================
    # Altivar Drives
    # =========================================================================
    {
        "name": "Schneider Altivar ATV930",
        "device_type": "drive",
        "role": "Variable Frequency Drive",
        "description": "High-performance process drive with multi-protocol support",
        "supported_protocols": ["modbus_tcp", "ethernet_ip"],
        "timing_model": {
            "polling_interval_ms": 50,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 1, "max": 30},
        },
        "payload_templates": {
            "modbus_tcp": {
                "holding_registers": {"start": 8501, "count": 50},
                "control_word_register": 8501,
                "status_word_register": 8601,
                "speed_reference_register": 8502,
                "actual_speed_register": 8602,
            },
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 2,  # AC Drive
                "assembly_input": 100,
                "assembly_output": 150,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "modbus_init", "delay_ms": 300},
                {"action": "enip_register", "delay_ms": 400},
                {"action": "drive_ready", "delay_ms": 500},
            ],
            "shutdown_sequence": [
                {"action": "drive_disable", "delay_ms": 200},
                {"action": "enip_unregister", "delay_ms": 200},
            ],
            "fault_behavior": "ramp_stop",
            "watchdog_ms": 500,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "ATV930",
        },
        "vertical_hints": ["hvac", "water", "process", "manufacturing"],
        "is_builtin": True,
    },
    {
        "name": "Schneider Altivar ATV320",
        "device_type": "drive",
        "role": "Compact Variable Frequency Drive",
        "description": "Compact drive for simple pump and fan applications",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 100,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 10,
            "response_time_ms": {"min": 2, "max": 50},
        },
        "payload_templates": {
            "modbus_tcp": {
                "holding_registers": {"start": 8501, "count": 30},
                "control_word_register": 8501,
                "status_word_register": 8601,
                "speed_reference_register": 8502,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "modbus_init", "delay_ms": 500},
                {"action": "drive_ready", "delay_ms": 800},
            ],
            "shutdown_sequence": [
                {"action": "drive_disable", "delay_ms": 300},
            ],
            "fault_behavior": "coast_stop",
            "watchdog_ms": 1000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "ATV320",
        },
        "vertical_hints": ["hvac", "water", "building"],
        "is_builtin": True,
    },
    # =========================================================================
    # Lexium Servo Drives
    # =========================================================================
    {
        "name": "Schneider Lexium LXM32",
        "device_type": "servo",
        "role": "Servo Drive",
        "description": "Lexium 32 integrated servo drive for motion applications",
        "supported_protocols": ["ethernet_ip", "modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 10,
            "cycle_time_ms": 1,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 1,
            "response_time_ms": {"min": 0.3, "max": 8},
        },
        "payload_templates": {
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 2,
                "assembly_input": 101,
                "assembly_output": 151,
            },
            "modbus_tcp": {
                "holding_registers": {"start": 6000, "count": 40},
                "control_word_register": 6040,
                "status_word_register": 6041,
                "position_command_register": 6042,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "enip_register", "delay_ms": 200},
                {"action": "servo_config", "delay_ms": 300},
                {"action": "servo_enable", "delay_ms": 200},
            ],
            "shutdown_sequence": [
                {"action": "servo_disable", "delay_ms": 100},
                {"action": "enip_unregister", "delay_ms": 100},
            ],
            "fault_behavior": "controlled_stop",
            "watchdog_ms": 100,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "LXM32",
        },
        "vertical_hints": ["packaging", "machinery", "manufacturing"],
        "is_builtin": True,
    },
    # =========================================================================
    # Magelis HMIs
    # =========================================================================
    {
        "name": "Schneider Magelis HMIST6700",
        "device_type": "hmi",
        "role": "Operator Panel",
        "description": "15-inch Magelis touchscreen panel for process visualization",
        "supported_protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
        "timing_model": {
            "polling_interval_ms": 500,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 50,
            "response_time_ms": {"min": 5, "max": 100},
        },
        "payload_templates": {
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 100},
                "read_rate_ms": 500,
            },
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 24,  # HMI
            },
            "opc_ua": {
                "endpoint_url": "opc.tcp://hmi:4840",
                "security_mode": "None",
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "modbus_init", "delay_ms": 500},
                {"action": "enip_register", "delay_ms": 800},
                {"action": "opc_ua_connect", "delay_ms": 600},
                {"action": "screen_load", "delay_ms": 2000},
            ],
            "shutdown_sequence": [
                {"action": "opc_ua_disconnect", "delay_ms": 300},
                {"action": "enip_unregister", "delay_ms": 300},
            ],
            "fault_behavior": "display_error",
            "watchdog_ms": 5000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "HMIST6700",
        },
        "vertical_hints": ["manufacturing", "process", "water"],
        "is_builtin": True,
    },
    {
        "name": "Schneider Magelis HMISTM6",
        "device_type": "hmi",
        "role": "Compact Operator Panel",
        "description": "7-inch Magelis basic touchscreen for machine applications",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 100,
            "response_time_ms": {"min": 10, "max": 150},
        },
        "payload_templates": {
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 50},
                "read_rate_ms": 1000,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "modbus_init", "delay_ms": 800},
                {"action": "screen_load", "delay_ms": 3000},
            ],
            "shutdown_sequence": [],
            "fault_behavior": "display_error",
            "watchdog_ms": 10000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "HMISTM6",
        },
        "vertical_hints": ["packaging", "machinery", "building"],
        "is_builtin": True,
    },
    # =========================================================================
    # TM3 Distributed I/O
    # =========================================================================
    {
        "name": "Schneider TM3 DI32K",
        "device_type": "remote_io",
        "role": "Digital Input Module",
        "description": "32-channel digital input module for M2xx PLCs",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 50,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 1, "max": 20},
        },
        "payload_templates": {
            "modbus_tcp": {
                "discrete_inputs": {"start": 0, "count": 32},
                "input_word_registers": {"start": 0, "count": 2},
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "modbus_init", "delay_ms": 200},
                {"action": "io_config", "delay_ms": 100},
            ],
            "shutdown_sequence": [],
            "fault_behavior": "inputs_false",
            "watchdog_ms": 200,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "TM3DI32K",
        },
        "vertical_hints": ["packaging", "machinery", "manufacturing"],
        "is_builtin": True,
    },
    {
        "name": "Schneider Advantys STB NIP2311",
        "device_type": "remote_io",
        "role": "Distributed I/O Station",
        "description": "Advantys STB network interface with EtherNet/IP",
        "supported_protocols": ["ethernet_ip", "modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 20,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 3,
            "response_time_ms": {"min": 0.5, "max": 15},
        },
        "payload_templates": {
            "ethernet_ip": {
                "vendor_id": 67,
                "device_type": 7,  # General Purpose I/O
                "assembly_input": 100,
                "assembly_output": 150,
                "io_size": 64,
            },
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 32},
                "input_registers": {"start": 0, "count": 32},
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "enip_register", "delay_ms": 300},
                {"action": "io_config", "delay_ms": 200},
                {"action": "io_start", "delay_ms": 100},
            ],
            "shutdown_sequence": [
                {"action": "io_stop", "delay_ms": 50},
                {"action": "enip_unregister", "delay_ms": 200},
            ],
            "fault_behavior": "outputs_off",
            "watchdog_ms": 100,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "STB NIP 2311",
        },
        "vertical_hints": ["manufacturing", "automotive", "packaging"],
        "is_builtin": True,
    },
    # =========================================================================
    # Network Infrastructure
    # =========================================================================
    {
        "name": "Schneider ConneXium TCSESM083F2CU0",
        "device_type": "switch",
        "role": "Industrial Ethernet Switch",
        "description": "8-port managed industrial Ethernet switch",
        "supported_protocols": ["modbus_tcp", "snmp"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 100,
            "response_time_ms": {"min": 1, "max": 50},
        },
        "payload_templates": {
            "modbus_tcp": {
                "holding_registers": {"start": 0, "count": 20},
                "port_status_register": 100,
            },
            "snmp": {
                "version": "v2c",
                "community": "public",
                "oids": [
                    "1.3.6.1.2.1.1.1.0",  # sysDescr
                    "1.3.6.1.2.1.2.2",  # ifTable
                    "1.3.6.1.2.1.17.4.3",  # dot1dTpFdbTable
                ],
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "link_up", "delay_ms": 5000},
                {"action": "spanning_tree_converge", "delay_ms": 30000},
            ],
            "shutdown_sequence": [
                {"action": "link_down", "delay_ms": 100},
            ],
            "fault_behavior": "port_bypass",
            "watchdog_ms": 10000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "TCSESM083F2CU0",
        },
        "vertical_hints": ["manufacturing", "infrastructure"],
        "is_builtin": True,
    },
    # =========================================================================
    # Field Devices
    # =========================================================================
    {
        "name": "Schneider OsiSense XU Sensor",
        "device_type": "sensor",
        "role": "Photoelectric Sensor",
        "description": "IO-Link capable photoelectric sensor with discrete output",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 100,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 20,
            "response_time_ms": {"min": 5, "max": 50},
        },
        "payload_templates": {
            "modbus_tcp": {
                "discrete_inputs": {"start": 0, "count": 1},
                "input_registers": {"start": 0, "count": 2},
                "distance_register": 0,
                "status_register": 1,
            },
        },
        "behavior_model": {
            "startup_sequence": [
                {"action": "sensor_init", "delay_ms": 500},
                {"action": "calibration", "delay_ms": 200},
            ],
            "shutdown_sequence": [],
            "fault_behavior": "output_off",
            "watchdog_ms": 1000,
        },
        "vendor_fingerprint": {
            "fingerprint_vendor": "Schneider",
            "fingerprint_model": "OsiSense XU",
        },
        "vertical_hints": ["packaging", "logistics", "manufacturing"],
        "is_builtin": True,
    },
]
