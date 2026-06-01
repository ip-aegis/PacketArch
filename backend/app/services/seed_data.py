# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Seed data for device profiles, protocol templates, and vendor fingerprints."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.models.device_template import DeviceTemplate as DeviceTemplateDB, TemplateSource
from app.models.protocol_template import ProtocolTemplate
from app.services.device_templates import DEVICE_TEMPLATES

# Built-in device profiles for OT/ICS environments
DEVICE_PROFILES = [
    # PLCs
    {
        "name": "Generic Modbus PLC",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "Generic programmable logic controller with Modbus TCP/IP interface",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 100,
            "jitter_type": "gaussian",
            "jitter_min_ms": 1,
            "jitter_max_ms": 10,
            "jitter_mean_ms": 5,
            "response_time_ms": {"min": 2, "max": 15},
        },
        "payload_templates": [
            {
                "name": "Holding Registers",
                "function_code": 3,
                "start_address": 0,
                "quantity": 100,
                "data_type": "holding_registers",
            },
            {
                "name": "Input Registers",
                "function_code": 4,
                "start_address": 0,
                "quantity": 50,
                "data_type": "input_registers",
            },
            {
                "name": "Coils",
                "function_code": 1,
                "start_address": 0,
                "quantity": 64,
                "data_type": "coils",
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 5000,
            "steady_state_variation_percent": 5,
            "supports_exception_responses": True,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:1C:06",
            "vendor_family": "Industrial Controller A",
        },
        "vertical_hints": ["manufacturing", "water", "oil_gas"],
        "is_builtin": True,
    },
    {
        "name": "EtherNet/IP PLC",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "Industrial PLC with EtherNet/IP and CIP protocol support",
        "supported_protocols": ["ethernet_ip", "cip"],
        "timing_model": {
            "polling_interval_ms": 50,
            "rpi_ms": 20,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 1, "max": 8},
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
            "supports_unconnected_send": True,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:00:BC",
            "vendor_family": "Industrial Controller B",
        },
        "vertical_hints": ["manufacturing", "automotive"],
        "is_builtin": True,
    },
    {
        "name": "PROFINET PLC",
        "device_type": "plc",
        "role": "Process Controller",
        "description": "Industrial PLC with PROFINET RT/IRT support",
        "supported_protocols": ["profinet"],
        "timing_model": {
            "cycle_time_ms": 4,
            "reduction_ratio": 1,
            "jitter_type": "uniform",
            "jitter_min_us": 0,
            "jitter_max_us": 100,
            "response_time_ms": {"min": 0.5, "max": 2},
        },
        "payload_templates": [
            {
                "name": "IO Data",
                "frame_id": 0x8000,
                "input_size": 32,
                "output_size": 32,
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 8000,
            "dcp_required": True,
            "supports_rt": True,
            "supports_irt": False,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:0E:8C",
            "vendor_family": "Industrial Controller C",
        },
        "vertical_hints": ["manufacturing", "automotive", "packaging"],
        "is_builtin": True,
    },
    {
        "name": "Safety PLC",
        "device_type": "plc",
        "role": "Safety Controller",
        "description": "SIL-rated safety PLC for emergency shutdown systems",
        "supported_protocols": ["modbus_tcp", "ethernet_ip"],
        "timing_model": {
            "polling_interval_ms": 20,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 2,
            "response_time_ms": {"min": 1, "max": 5},
        },
        "behavior_model": {
            "startup_duration_ms": 10000,
            "safety_cycle_ms": 10,
            "watchdog_timeout_ms": 50,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:1A:2B",
            "vendor_family": "Safety Controller A",
        },
        "vertical_hints": ["oil_gas", "chemical", "power"],
        "is_builtin": True,
    },
    # HMIs
    {
        "name": "Industrial HMI Panel",
        "device_type": "hmi",
        "role": "Operator Interface",
        "description": "Touch panel HMI for operator visualization and control",
        "supported_protocols": ["modbus_tcp", "ethernet_ip"],
        "timing_model": {
            "polling_interval_ms": 500,
            "jitter_type": "gaussian",
            "jitter_min_ms": 10,
            "jitter_max_ms": 100,
            "jitter_mean_ms": 50,
            "response_time_ms": {"min": 5, "max": 50},
        },
        "behavior_model": {
            "startup_duration_ms": 15000,
            "polling_targets": 5,
            "burst_on_screen_change": True,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:1C:7A",
            "vendor_family": "HMI Panel A",
        },
        "vertical_hints": ["manufacturing", "water", "oil_gas", "power"],
        "is_builtin": True,
    },
    {
        "name": "SCADA Workstation",
        "device_type": "hmi",
        "role": "SCADA Client",
        "description": "Windows-based SCADA workstation for supervisory control",
        "supported_protocols": ["modbus_tcp", "ethernet_ip", "opc_ua"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "gaussian",
            "jitter_min_ms": 50,
            "jitter_max_ms": 200,
            "jitter_mean_ms": 100,
        },
        "behavior_model": {
            "startup_duration_ms": 30000,
            "polling_targets": 20,
            "concurrent_connections": 10,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:1A:A0",
            "vendor_family": "Workstation",
        },
        "vertical_hints": ["water", "oil_gas", "power", "manufacturing"],
        "is_builtin": True,
    },
    # RTUs
    {
        "name": "Remote Terminal Unit",
        "device_type": "rtu",
        "role": "Remote I/O",
        "description": "Remote terminal unit for distributed I/O and telemetry",
        "supported_protocols": ["modbus_tcp", "dnp3"],
        "timing_model": {
            "polling_interval_ms": 5000,
            "jitter_type": "exponential",
            "jitter_min_ms": 100,
            "jitter_max_ms": 2000,
            "response_time_ms": {"min": 10, "max": 100},
        },
        "payload_templates": [
            {
                "name": "Analog Inputs",
                "function_code": 4,
                "start_address": 0,
                "quantity": 16,
                "data_type": "input_registers",
            },
            {
                "name": "Digital Inputs",
                "function_code": 2,
                "start_address": 0,
                "quantity": 32,
                "data_type": "discrete_inputs",
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 20000,
            "event_generation": True,
            "unsolicited_responses": True,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:40:84",  # Honeywell (verified IEEE)
            "vendor_family": "RTU Controller A",
        },
        "vertical_hints": ["water", "oil_gas", "power"],
        "is_builtin": True,
    },
    {
        "name": "Pipeline RTU",
        "device_type": "rtu",
        "role": "Pipeline Monitoring",
        "description": "RTU for pipeline monitoring with flow and pressure sensors",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 10000,
            "jitter_type": "uniform",
            "jitter_min_ms": 500,
            "jitter_max_ms": 3000,
        },
        "payload_templates": [
            {
                "name": "Flow Meters",
                "function_code": 4,
                "start_address": 100,
                "quantity": 8,
            },
            {
                "name": "Pressure Sensors",
                "function_code": 4,
                "start_address": 200,
                "quantity": 8,
            },
        ],
        "vendor_fingerprint": {
            "oui_prefix": "00:40:AD",
            "vendor_family": "Pipeline Controller",
        },
        "vertical_hints": ["oil_gas", "water"],
        "is_builtin": True,
    },
    # Drives
    {
        "name": "Variable Frequency Drive",
        "device_type": "drive",
        "role": "Motor Control",
        "description": "VFD for AC motor speed and torque control",
        "supported_protocols": ["modbus_tcp", "ethernet_ip", "profinet"],
        "timing_model": {
            "polling_interval_ms": 100,
            "jitter_type": "gaussian",
            "jitter_min_ms": 1,
            "jitter_max_ms": 10,
            "response_time_ms": {"min": 2, "max": 15},
        },
        "payload_templates": [
            {
                "name": "Speed Reference",
                "function_code": 6,
                "start_address": 0,
                "quantity": 1,
            },
            {
                "name": "Status Registers",
                "function_code": 3,
                "start_address": 100,
                "quantity": 10,
            },
        ],
        "behavior_model": {
            "startup_duration_ms": 5000,
            "ramp_time_ms": 3000,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:01:05",
            "vendor_family": "Drive Controller A",
        },
        "vertical_hints": ["manufacturing", "water", "oil_gas"],
        "is_builtin": True,
    },
    {
        "name": "Servo Drive",
        "device_type": "drive",
        "role": "Motion Control",
        "description": "Servo drive for precise position and velocity control",
        "supported_protocols": ["ethernet_ip", "profinet"],
        "timing_model": {
            "polling_interval_ms": 4,
            "jitter_type": "uniform",
            "jitter_min_us": 0,
            "jitter_max_us": 50,
            "response_time_ms": {"min": 0.5, "max": 2},
        },
        "behavior_model": {
            "startup_duration_ms": 2000,
            "motion_profile": "s_curve",
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:01:09",
            "vendor_family": "Motion Controller A",
        },
        "vertical_hints": ["manufacturing", "packaging", "automotive"],
        "is_builtin": True,
    },
    # Sensors/Transmitters
    {
        "name": "Pressure Transmitter",
        "device_type": "sensor",
        "role": "Process Measurement",
        "description": "Industrial pressure transmitter with Modbus interface",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "uniform",
            "jitter_min_ms": 10,
            "jitter_max_ms": 100,
            "response_time_ms": {"min": 5, "max": 20},
        },
        "payload_templates": [
            {
                "name": "Process Value",
                "function_code": 4,
                "start_address": 0,
                "quantity": 2,
                "scaling": {"raw_min": 0, "raw_max": 32767, "eng_min": 0, "eng_max": 100, "unit": "psi"},
            },
        ],
        "vendor_fingerprint": {
            "oui_prefix": "00:80:A3",
            "vendor_family": "Instrument A",
        },
        "vertical_hints": ["oil_gas", "chemical", "water", "manufacturing"],
        "is_builtin": True,
    },
    {
        "name": "Flow Meter",
        "device_type": "sensor",
        "role": "Flow Measurement",
        "description": "Electromagnetic flow meter with Modbus TCP",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 2000,
            "jitter_type": "gaussian",
            "jitter_min_ms": 20,
            "jitter_max_ms": 200,
        },
        "payload_templates": [
            {
                "name": "Flow Rate",
                "function_code": 4,
                "start_address": 0,
                "quantity": 2,
                "scaling": {"unit": "gpm"},
            },
            {
                "name": "Totalizer",
                "function_code": 4,
                "start_address": 10,
                "quantity": 4,
                "scaling": {"unit": "gallons"},
            },
        ],
        "vendor_fingerprint": {
            "oui_prefix": "00:80:A3",
            "vendor_family": "Instrument B",
        },
        "vertical_hints": ["water", "chemical", "oil_gas"],
        "is_builtin": True,
    },
    {
        "name": "Temperature Transmitter",
        "device_type": "sensor",
        "role": "Temperature Measurement",
        "description": "RTD/Thermocouple transmitter with Modbus",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 5000,
            "jitter_type": "uniform",
            "jitter_min_ms": 50,
            "jitter_max_ms": 500,
        },
        "payload_templates": [
            {
                "name": "Temperature",
                "function_code": 4,
                "start_address": 0,
                "quantity": 2,
                "scaling": {"unit": "degF"},
            },
        ],
        "vendor_fingerprint": {
            "oui_prefix": "00:80:A3",
            "vendor_family": "Instrument C",
        },
        "vertical_hints": ["manufacturing", "chemical", "oil_gas", "power"],
        "is_builtin": True,
    },
    {
        "name": "Level Transmitter",
        "device_type": "sensor",
        "role": "Level Measurement",
        "description": "Radar level transmitter for tank level measurement",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 3000,
            "jitter_type": "gaussian",
            "jitter_min_ms": 30,
            "jitter_max_ms": 300,
        },
        "payload_templates": [
            {
                "name": "Level",
                "function_code": 4,
                "start_address": 0,
                "quantity": 2,
                "scaling": {"unit": "feet"},
            },
        ],
        "vendor_fingerprint": {
            "oui_prefix": "00:80:A3",
            "vendor_family": "Instrument D",
        },
        "vertical_hints": ["oil_gas", "water", "chemical"],
        "is_builtin": True,
    },
    # Relays
    {
        "name": "Protective Relay",
        "device_type": "relay",
        "role": "Electrical Protection",
        "description": "Multifunction protective relay for electrical protection",
        "supported_protocols": ["modbus_tcp", "dnp3"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "uniform",
            "jitter_min_ms": 10,
            "jitter_max_ms": 50,
            "response_time_ms": {"min": 2, "max": 10},
        },
        "payload_templates": [
            {
                "name": "Metering",
                "function_code": 4,
                "start_address": 0,
                "quantity": 20,
            },
            {
                "name": "Status",
                "function_code": 1,
                "start_address": 0,
                "quantity": 16,
            },
        ],
        "behavior_model": {
            "event_generation": True,
            "soe_buffer_size": 100,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:30:A7",
            "vendor_family": "Protection Relay A",
        },
        "vertical_hints": ["power", "oil_gas", "manufacturing"],
        "is_builtin": True,
    },
    {
        "name": "Motor Protection Relay",
        "device_type": "relay",
        "role": "Motor Protection",
        "description": "Motor protection relay with overload and fault detection",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 500,
            "jitter_type": "uniform",
            "jitter_min_ms": 5,
            "jitter_max_ms": 25,
        },
        "payload_templates": [
            {
                "name": "Motor Current",
                "function_code": 4,
                "start_address": 0,
                "quantity": 6,
            },
            {
                "name": "Thermal State",
                "function_code": 4,
                "start_address": 100,
                "quantity": 4,
            },
        ],
        "vendor_fingerprint": {
            "oui_prefix": "00:30:A7",
            "vendor_family": "Motor Relay A",
        },
        "vertical_hints": ["manufacturing", "water", "oil_gas"],
        "is_builtin": True,
    },
    # Engineering Workstations
    {
        "name": "Engineering Workstation",
        "device_type": "ews",
        "role": "Programming/Configuration",
        "description": "Engineering workstation for PLC programming and configuration",
        "supported_protocols": ["modbus_tcp", "ethernet_ip", "profinet", "opc_ua"],
        "timing_model": {
            "polling_interval_ms": 2000,
            "jitter_type": "exponential",
            "jitter_min_ms": 100,
            "jitter_max_ms": 1000,
        },
        "behavior_model": {
            "startup_duration_ms": 60000,
            "intermittent_connection": True,
            "programming_sessions": True,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:1A:A0",
            "vendor_family": "Workstation",
        },
        "vertical_hints": ["manufacturing", "water", "oil_gas", "power"],
        "is_builtin": True,
    },
    # Historians
    {
        "name": "Process Historian",
        "device_type": "historian",
        "role": "Data Collection",
        "description": "Process historian for long-term data archiving",
        "supported_protocols": ["modbus_tcp", "opc_ua"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "uniform",
            "jitter_min_ms": 10,
            "jitter_max_ms": 100,
        },
        "behavior_model": {
            "concurrent_connections": 50,
            "polling_targets": 100,
            "data_compression": True,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:1A:A0",
            "vendor_family": "Server",
        },
        "vertical_hints": ["manufacturing", "water", "oil_gas", "power", "chemical"],
        "is_builtin": True,
    },
    # Network Infrastructure
    {
        "name": "Industrial Managed Switch",
        "device_type": "switch",
        "role": "Network Infrastructure",
        "description": "Managed Ethernet switch with SNMP and web interface",
        "supported_protocols": ["snmp"],
        "timing_model": {
            "polling_interval_ms": 30000,
            "jitter_type": "uniform",
            "jitter_min_ms": 100,
            "jitter_max_ms": 1000,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:1B:0D",
            "vendor_family": "Network Switch A",
        },
        "vertical_hints": ["manufacturing", "water", "oil_gas", "power"],
        "is_builtin": True,
    },
    {
        "name": "Industrial Router",
        "device_type": "router",
        "role": "Network Gateway",
        "description": "Industrial router for WAN connectivity and VPN",
        "supported_protocols": ["snmp"],
        "timing_model": {
            "polling_interval_ms": 60000,
            "jitter_type": "uniform",
            "jitter_min_ms": 500,
            "jitter_max_ms": 5000,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:1E:BD",
            "vendor_family": "Industrial Router A",
        },
        "vertical_hints": ["water", "oil_gas", "power"],
        "is_builtin": True,
    },
    # I/O Modules
    {
        "name": "Remote I/O Module",
        "device_type": "io_module",
        "role": "Distributed I/O",
        "description": "Remote I/O module for distributed field signals",
        "supported_protocols": ["modbus_tcp", "ethernet_ip", "profinet"],
        "timing_model": {
            "polling_interval_ms": 50,
            "jitter_type": "uniform",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
            "response_time_ms": {"min": 1, "max": 5},
        },
        "payload_templates": [
            {
                "name": "Digital I/O",
                "function_code": 1,
                "start_address": 0,
                "quantity": 16,
            },
            {
                "name": "Analog I/O",
                "function_code": 4,
                "start_address": 0,
                "quantity": 8,
            },
        ],
        "vendor_fingerprint": {
            "oui_prefix": "00:01:05",
            "vendor_family": "I/O Module A",
        },
        "vertical_hints": ["manufacturing", "automotive", "packaging"],
        "is_builtin": True,
    },
    # OPC UA Server
    {
        "name": "OPC UA Server",
        "device_type": "server",
        "role": "Data Aggregation",
        "description": "OPC UA server for data aggregation and connectivity",
        "supported_protocols": ["opc_ua"],
        "timing_model": {
            "polling_interval_ms": 1000,
            "jitter_type": "gaussian",
            "jitter_min_ms": 10,
            "jitter_max_ms": 100,
        },
        "behavior_model": {
            "max_subscriptions": 100,
            "publishing_interval_ms": 500,
            "supports_browse": True,
            "supports_history": True,
        },
        "vendor_fingerprint": {
            "oui_prefix": "00:1A:A0",
            "vendor_family": "Server",
        },
        "vertical_hints": ["manufacturing", "oil_gas", "power"],
        "is_builtin": True,
    },
    # Valve Controllers
    {
        "name": "Valve Positioner",
        "device_type": "valve",
        "role": "Final Control Element",
        "description": "Smart valve positioner with diagnostics",
        "supported_protocols": ["modbus_tcp"],
        "timing_model": {
            "polling_interval_ms": 2000,
            "jitter_type": "uniform",
            "jitter_min_ms": 20,
            "jitter_max_ms": 200,
        },
        "payload_templates": [
            {
                "name": "Position",
                "function_code": 4,
                "start_address": 0,
                "quantity": 2,
                "scaling": {"unit": "percent"},
            },
            {
                "name": "Setpoint",
                "function_code": 3,
                "start_address": 10,
                "quantity": 2,
            },
        ],
        "vendor_fingerprint": {
            "oui_prefix": "00:80:A3",
            "vendor_family": "Valve Controller A",
        },
        "vertical_hints": ["oil_gas", "chemical", "water"],
        "is_builtin": True,
    },
]

# Protocol templates with default configurations
PROTOCOL_TEMPLATES = [
    # Modbus TCP Templates
    {
        "protocol": "modbus_tcp",
        "name": "Read Holding Registers",
        "description": "Standard Modbus TCP read holding registers (FC03)",
        "vertical": None,
        "config_schema": {
            "type": "object",
            "properties": {
                "function_code": {"type": "integer", "const": 3},
                "unit_id": {"type": "integer", "minimum": 0, "maximum": 255},
                "start_address": {"type": "integer", "minimum": 0, "maximum": 65535},
                "quantity": {"type": "integer", "minimum": 1, "maximum": 125},
                "response_delay_ms": {"type": "integer", "minimum": 0},
            },
            "required": ["unit_id", "start_address", "quantity"],
        },
        "default_config": {
            "function_code": 3,
            "unit_id": 1,
            "start_address": 0,
            "quantity": 10,
            "response_delay_ms": 5,
        },
    },
    {
        "protocol": "modbus_tcp",
        "name": "Read Input Registers",
        "description": "Standard Modbus TCP read input registers (FC04)",
        "vertical": None,
        "config_schema": {
            "type": "object",
            "properties": {
                "function_code": {"type": "integer", "const": 4},
                "unit_id": {"type": "integer", "minimum": 0, "maximum": 255},
                "start_address": {"type": "integer", "minimum": 0, "maximum": 65535},
                "quantity": {"type": "integer", "minimum": 1, "maximum": 125},
            },
            "required": ["unit_id", "start_address", "quantity"],
        },
        "default_config": {
            "function_code": 4,
            "unit_id": 1,
            "start_address": 0,
            "quantity": 10,
        },
    },
    {
        "protocol": "modbus_tcp",
        "name": "Read Coils",
        "description": "Standard Modbus TCP read coils (FC01)",
        "vertical": None,
        "config_schema": {
            "type": "object",
            "properties": {
                "function_code": {"type": "integer", "const": 1},
                "unit_id": {"type": "integer", "minimum": 0, "maximum": 255},
                "start_address": {"type": "integer", "minimum": 0, "maximum": 65535},
                "quantity": {"type": "integer", "minimum": 1, "maximum": 2000},
            },
            "required": ["unit_id", "start_address", "quantity"],
        },
        "default_config": {
            "function_code": 1,
            "unit_id": 1,
            "start_address": 0,
            "quantity": 16,
        },
    },
    {
        "protocol": "modbus_tcp",
        "name": "Write Single Register",
        "description": "Standard Modbus TCP write single register (FC06)",
        "vertical": None,
        "config_schema": {
            "type": "object",
            "properties": {
                "function_code": {"type": "integer", "const": 6},
                "unit_id": {"type": "integer", "minimum": 0, "maximum": 255},
                "start_address": {"type": "integer", "minimum": 0, "maximum": 65535},
                "value": {"type": "integer", "minimum": 0, "maximum": 65535},
            },
            "required": ["unit_id", "start_address", "value"],
        },
        "default_config": {
            "function_code": 6,
            "unit_id": 1,
            "start_address": 0,
            "value": 0,
        },
    },
    {
        "protocol": "modbus_tcp",
        "name": "Write Multiple Registers",
        "description": "Standard Modbus TCP write multiple registers (FC16)",
        "vertical": None,
        "config_schema": {
            "type": "object",
            "properties": {
                "function_code": {"type": "integer", "const": 16},
                "unit_id": {"type": "integer", "minimum": 0, "maximum": 255},
                "start_address": {"type": "integer", "minimum": 0, "maximum": 65535},
                "quantity": {"type": "integer", "minimum": 1, "maximum": 123},
            },
            "required": ["unit_id", "start_address", "quantity"],
        },
        "default_config": {
            "function_code": 16,
            "unit_id": 1,
            "start_address": 0,
            "quantity": 10,
        },
    },
    # EtherNet/IP Templates
    {
        "protocol": "ethernet_ip",
        "name": "Forward Open - Class 3",
        "description": "EtherNet/IP Forward Open for Class 3 explicit messaging",
        "vertical": "manufacturing",
        "config_schema": {
            "type": "object",
            "properties": {
                "connection_type": {"type": "string", "const": "forward_open"},
                "rpi_ms": {"type": "integer", "minimum": 2, "maximum": 30000},
                "timeout_multiplier": {"type": "integer", "minimum": 0, "maximum": 7},
                "assembly_instance_t2o": {"type": "integer"},
                "assembly_instance_o2t": {"type": "integer"},
            },
        },
        "default_config": {
            "connection_type": "forward_open",
            "rpi_ms": 20,
            "timeout_multiplier": 4,
            "assembly_instance_t2o": 100,
            "assembly_instance_o2t": 101,
        },
    },
    {
        "protocol": "ethernet_ip",
        "name": "Unconnected Send",
        "description": "EtherNet/IP unconnected explicit message",
        "vertical": None,
        "config_schema": {
            "type": "object",
            "properties": {
                "connection_type": {"type": "string", "const": "unconnected_send"},
                "service_code": {"type": "integer"},
                "class_id": {"type": "integer"},
                "instance_id": {"type": "integer"},
            },
        },
        "default_config": {
            "connection_type": "unconnected_send",
            "service_code": 14,
            "class_id": 1,
            "instance_id": 1,
        },
    },
    # PROFINET Templates
    {
        "protocol": "profinet",
        "name": "Cyclic IO - 4ms",
        "description": "PROFINET RT cyclic I/O with 4ms cycle time",
        "vertical": "manufacturing",
        "config_schema": {
            "type": "object",
            "properties": {
                "cycle_time_ms": {"type": "integer", "minimum": 1, "maximum": 512},
                "reduction_ratio": {"type": "integer", "minimum": 1, "maximum": 512},
                "frame_id": {"type": "integer"},
                "input_size": {"type": "integer"},
                "output_size": {"type": "integer"},
            },
        },
        "default_config": {
            "cycle_time_ms": 4,
            "reduction_ratio": 1,
            "frame_id": 32768,
            "input_size": 32,
            "output_size": 32,
        },
    },
    {
        "protocol": "profinet",
        "name": "DCP Identify",
        "description": "PROFINET DCP device identification",
        "vertical": None,
        "config_schema": {
            "type": "object",
            "properties": {
                "service_type": {"type": "string", "const": "identify"},
            },
        },
        "default_config": {
            "service_type": "identify",
        },
    },
    # OPC UA Templates
    {
        "protocol": "opc_ua",
        "name": "Subscription - 1s Publishing",
        "description": "OPC UA subscription with 1 second publishing interval",
        "vertical": None,
        "config_schema": {
            "type": "object",
            "properties": {
                "publishing_interval_ms": {"type": "integer", "minimum": 100},
                "lifetime_count": {"type": "integer", "minimum": 1},
                "max_keep_alive_count": {"type": "integer", "minimum": 1},
                "max_notifications_per_publish": {"type": "integer", "minimum": 0},
            },
        },
        "default_config": {
            "publishing_interval_ms": 1000,
            "lifetime_count": 10,
            "max_keep_alive_count": 3,
            "max_notifications_per_publish": 0,
        },
    },
    {
        "protocol": "opc_ua",
        "name": "Read Nodes",
        "description": "OPC UA read multiple nodes",
        "vertical": None,
        "config_schema": {
            "type": "object",
            "properties": {
                "node_ids": {"type": "array", "items": {"type": "string"}},
                "max_age": {"type": "integer", "minimum": 0},
            },
        },
        "default_config": {
            "node_ids": [],
            "max_age": 0,
        },
    },
]



async def seed_protocol_templates(db: AsyncSession) -> int:
    """Seed built-in protocol templates."""
    created = 0

    for template_data in PROTOCOL_TEMPLATES:
        # Check if template already exists by protocol and name
        result = await db.execute(
            select(ProtocolTemplate).where(
                ProtocolTemplate.protocol == template_data["protocol"],
                ProtocolTemplate.name == template_data["name"],
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            template = ProtocolTemplate(**template_data)
            db.add(template)
            created += 1

    if created > 0:
        await db.commit()

    return created


def _infer_vertical_hints(device_type: str, vendor: str, protocols: list[str]) -> list[str]:
    """Infer industry verticals from device type, vendor, and protocols."""
    hints: set[str] = set()

    # Protocol-based hints
    proto_set = set(protocols)
    if proto_set & {"modbus_tcp", "modbus"}:
        hints.update(["manufacturing", "water", "oil_gas"])
    if proto_set & {"ethernet_ip", "cip", "cip_safety"}:
        hints.update(["manufacturing"])
    if proto_set & {"profinet", "profisafe"}:
        hints.update(["manufacturing"])
    if proto_set & {"s7comm", "s7comm_plus"}:
        hints.update(["manufacturing", "water"])
    if proto_set & {"bacnet", "bacnet_ip"}:
        hints.update(["building_automation"])
    if proto_set & {"snmp", "ntcip"}:
        hints.update(["transportation"])

    # Device-type hints
    type_lower = device_type.lower()
    if type_lower in ("plc", "hmi", "drive", "vfd", "servo", "robot"):
        hints.add("manufacturing")
    elif type_lower in ("rtu", "scada_server", "flow_computer"):
        hints.update(["water", "oil_gas", "energy"])
    elif type_lower in ("relay", "ied", "protection_relay", "power_meter"):
        hints.add("energy")
    elif type_lower in ("building_controller", "hvac", "vav"):
        hints.add("building_automation")
    elif type_lower in ("traffic_controller", "its_device", "dms"):
        hints.add("transportation")
    elif type_lower in ("gateway", "switch", "router", "firewall"):
        hints.update(["manufacturing", "water", "energy"])

    return sorted(hints) if hints else ["manufacturing"]


def _infer_timing_model(device_type: str, protocols: list[str]) -> dict:
    """Infer default timing model from device type and protocols."""
    type_lower = device_type.lower()

    if type_lower in ("plc", "safety_plc"):
        return {
            "polling_interval_ms": 100,
            "jitter_type": "gaussian",
            "jitter_min_ms": 1,
            "jitter_max_ms": 10,
        }
    elif type_lower in ("hmi", "scada_server"):
        return {
            "polling_interval_ms": 1000,
            "jitter_type": "gaussian",
            "jitter_min_ms": 5,
            "jitter_max_ms": 50,
        }
    elif type_lower in ("drive", "vfd", "servo"):
        return {
            "polling_interval_ms": 50,
            "jitter_type": "gaussian",
            "jitter_min_ms": 0,
            "jitter_max_ms": 5,
        }
    elif type_lower in ("rtu", "flow_computer"):
        return {
            "polling_interval_ms": 5000,
            "jitter_type": "gaussian",
            "jitter_min_ms": 10,
            "jitter_max_ms": 100,
        }
    elif type_lower in ("relay", "ied", "protection_relay"):
        return {
            "polling_interval_ms": 2000,
            "jitter_type": "gaussian",
            "jitter_min_ms": 5,
            "jitter_max_ms": 30,
        }
    elif type_lower in ("building_controller", "hvac", "vav"):
        return {
            "polling_interval_ms": 10000,
            "jitter_type": "gaussian",
            "jitter_min_ms": 50,
            "jitter_max_ms": 500,
        }
    elif type_lower in ("sensor", "io_module", "io"):
        return {
            "polling_interval_ms": 200,
            "jitter_type": "gaussian",
            "jitter_min_ms": 1,
            "jitter_max_ms": 15,
        }
    else:
        return {
            "polling_interval_ms": 1000,
            "jitter_type": "gaussian",
            "jitter_min_ms": 5,
            "jitter_max_ms": 30,
        }


def _infer_role(device_type: str) -> str:
    """Infer a human-readable role from device type."""
    role_map = {
        "plc": "Process Controller",
        "safety_plc": "Safety Controller",
        "hmi": "Operator Interface",
        "scada_server": "SCADA Server",
        "drive": "Variable Frequency Drive",
        "vfd": "Variable Frequency Drive",
        "servo": "Servo Drive",
        "rtu": "Remote Terminal Unit",
        "gateway": "Protocol Gateway",
        "switch": "Network Switch",
        "router": "Network Router",
        "firewall": "Industrial Firewall",
        "sensor": "Field Sensor",
        "io_module": "I/O Module",
        "io": "I/O Module",
        "relay": "Protection Relay",
        "ied": "Intelligent Electronic Device",
        "protection_relay": "Protection Relay",
        "power_meter": "Power Meter",
        "building_controller": "Building Controller",
        "hvac": "HVAC Controller",
        "vav": "VAV Controller",
        "flow_computer": "Flow Computer",
        "robot": "Industrial Robot",
        "camera": "IP Camera",
        "traffic_controller": "Traffic Controller",
        "dms": "Dynamic Message Sign",
    }
    return role_map.get(device_type.lower(), "Industrial Device")


async def seed_device_templates_db(db: AsyncSession) -> int:
    """Seed built-in device templates to the DeviceTemplate DB table.

    Seeds from the Python dataclass library into the DeviceTemplate DB table
    with source=VENDOR_BUILTIN. Also populates palette_config and
    vertical_hints so all templates are available in the Scenario Studio palette.

    Returns:
        Number of templates created
    """
    from app.services.device_templates import get_fingerprint_from_template

    # Build cross-reference from generic DEVICE_PROFILES for palette enrichment
    profile_lookup: dict[tuple[str, str], dict] = {}
    for p in DEVICE_PROFILES:
        vfp = p.get("vendor_fingerprint", {})
        key_vendor = vfp.get("fingerprint_vendor", "").lower()
        key_model = vfp.get("fingerprint_model", "")
        if key_vendor and key_model:
            profile_lookup[(key_vendor, key_model.lower())] = p

    # Pre-load all existing builtin (vendor, model) combos in a single query
    result = await db.execute(
        select(DeviceTemplateDB.vendor, DeviceTemplateDB.model).where(
            DeviceTemplateDB.source == TemplateSource.VENDOR_BUILTIN.value,
        )
    )
    existing_combos = {
        (row[0].lower(), row[1]) for row in result.all() if row[0] is not None
    }

    # Track combos from the Python library to avoid duplicates
    seen_combos = set()
    new_templates = []

    for template_id, template in DEVICE_TEMPLATES.items():
        combo_key = (template.vendor.lower(), template.model)

        # Skip duplicates within the library and already-seeded entries
        if combo_key in seen_combos or combo_key in existing_combos:
            continue
        seen_combos.add(combo_key)

        fp_dict = get_fingerprint_from_template(template_id)
        if not fp_dict:
            continue

        # Determine vertical hints: from dataclass, then cross-ref, then infer
        vertical_hints = template.vertical_hints if template.vertical_hints else None
        profile_match = profile_lookup.get((template.vendor.lower(), template.model.lower()))
        if not vertical_hints and profile_match:
            vertical_hints = profile_match.get("vertical_hints")
        if not vertical_hints:
            vertical_hints = _infer_vertical_hints(
                template.device_type, template.vendor, template.supported_protocols
            )

        # Determine palette_config: from cross-ref or infer defaults
        palette_config = dict(template.palette_config) if template.palette_config else {}
        if profile_match:
            if not palette_config.get("timing_model") and profile_match.get("timing_model"):
                palette_config["timing_model"] = profile_match["timing_model"]
            if not palette_config.get("payload_templates") and profile_match.get("payload_templates"):
                palette_config["payload_templates"] = profile_match["payload_templates"]
            if not palette_config.get("behavior_model") and profile_match.get("behavior_model"):
                palette_config["behavior_model"] = profile_match["behavior_model"]
        if not palette_config.get("timing_model"):
            palette_config["timing_model"] = _infer_timing_model(
                template.device_type, template.supported_protocols
            )

        # Determine role
        role = None
        if profile_match:
            role = profile_match.get("role")
        if not role:
            role = _infer_role(template.device_type)

        new_templates.append(DeviceTemplateDB(
            source=TemplateSource.VENDOR_BUILTIN.value,
            vendor=template.vendor,
            vendor_family=template.vendor_family,
            model=template.model,
            firmware_version=fp_dict.get("firmware_version"),
            device_type=template.device_type,
            oui_patterns=template.oui_prefixes,
            tcp_signature=template.tcp_stack,
            # Legacy per-protocol identity columns (for backward compatibility)
            modbus_identity=fp_dict.get("modbus_identity"),
            ethernet_ip_identity=fp_dict.get("ethernet_ip_identity"),
            profinet_identity=fp_dict.get("profinet_identity"),
            s7_identity=fp_dict.get("s7_identity"),
            snmp_identity=fp_dict.get("snmp_identity"),
            bacnet_identity=fp_dict.get("bacnet_identity"),
            opc_ua_identity=fp_dict.get("opc_ua_identity"),
            # Response timing
            response_timings={"default": template.response_timing} if template.response_timing else None,
            # Behavioral patterns
            role=role,
            active_protocols=template.supported_protocols,
            protocol_quirks=template.protocol_quirks if template.protocol_quirks else None,
            error_behavior=template.error_behavior if template.error_behavior else None,
            # Palette data
            vertical_hints=vertical_hints,
            palette_config=palette_config if palette_config else None,
            # Quality metrics (builtin = high confidence)
            confidence=1.0,
            sample_count=1,
            consistency_score=1.0,
            # Metadata
            name=f"{template.vendor} {template.model_name}",
            description=template.description,
            is_active=True,
        ))

    # Also seed generic device profiles that don't map to specific templates
    existing_names_result = await db.execute(
        select(DeviceTemplateDB.name).where(
            DeviceTemplateDB.source == TemplateSource.VENDOR_BUILTIN.value,
        )
    )
    existing_names = {row[0] for row in existing_names_result.all() if row[0]}

    for profile in DEVICE_PROFILES:
        name = profile["name"]
        if name in existing_names:
            continue
        # Skip profiles that were cross-referenced to a real template
        vfp = profile.get("vendor_fingerprint", {})
        if vfp.get("fingerprint_vendor") and vfp.get("fingerprint_model"):
            continue  # Already covered via template match

        palette_cfg = {}
        if profile.get("timing_model"):
            palette_cfg["timing_model"] = profile["timing_model"]
        if profile.get("payload_templates"):
            palette_cfg["payload_templates"] = profile["payload_templates"]
        if profile.get("behavior_model"):
            palette_cfg["behavior_model"] = profile["behavior_model"]

        new_templates.append(DeviceTemplateDB(
            source=TemplateSource.VENDOR_BUILTIN.value,
            name=name,
            device_type=profile.get("device_type", "other"),
            role=profile.get("role"),
            description=profile.get("description"),
            active_protocols=profile.get("supported_protocols"),
            vertical_hints=profile.get("vertical_hints"),
            palette_config=palette_cfg if palette_cfg else None,
            is_active=True,
            confidence=1.0,
            sample_count=1,
            consistency_score=1.0,
        ))

    if new_templates:
        db.add_all(new_templates)
        await db.commit()

    return len(new_templates)


async def seed_cve_vulnerabilities(db: AsyncSession) -> int:
    """Reconcile built-in CVE vulnerabilities to the curated Python source.

    The ``cve_data/`` Python files are the single source of truth. On every
    boot this reconciles the DB to them:
      * inserts CVEs that are new to the DB,
      * updates built-in rows whose data changed (CVSS, product, firmware,
        advisory, etc.),
      * prunes built-in rows no longer present in the source (their
        vulnerable_fingerprint_variants are removed via FK ``ON DELETE
        CASCADE``).
    User-created rows (``is_builtin=False``) are never touched. This makes
    deletes/edits in the curated files actually propagate to a persistent
    DB instead of accumulating stale rows (insert-only seeding never did).

    Returns the number of newly inserted rows (kept for caller compatibility).
    """
    from app.models.cve_vulnerability import CVESeverity, CVEVulnerability
    from app.services.cve_data import ALL_CVES

    # Source of truth, keyed by cve_id (source is already de-duplicated;
    # first occurrence wins if not).
    source: dict[str, dict] = {}
    for cve_data in ALL_CVES:
        source.setdefault(cve_data["cve_id"], cve_data)

    result = await db.execute(select(CVEVulnerability))
    existing = {row.cve_id: row for row in result.scalars().all()}

    # Mutable scalar/JSON columns kept in sync from the source dict.
    MUTABLE = (
        "title", "description", "cvss_score", "cvss_vector", "vendor",
        "product_family", "affected_models", "affected_firmware_min",
        "fixed_firmware_version", "detection_method", "advisory_url",
        "references", "mitre_techniques", "exploit_complexity",
        "published_date",
    )

    def field_values(cve_data: dict) -> dict:
        vals = {k: cve_data.get(k) for k in MUTABLE}
        # NOT NULL column — never store None.
        vals["affected_firmware_max"] = cve_data.get("affected_firmware_max") or "unknown"
        vals["cyber_vision_detectable"] = cve_data.get("cyber_vision_detectable", True)
        vals["exploit_available"] = cve_data.get("exploit_available", False)
        vals["severity"] = CVESeverity(cve_data.get("severity", "medium").lower())
        return vals

    inserted = updated = pruned = 0
    new_rows = []
    for cve_id, cve_data in source.items():
        vals = field_values(cve_data)
        row = existing.get(cve_id)
        if row is None:
            new_rows.append(CVEVulnerability(cve_id=cve_id, is_builtin=True, **vals))
            inserted += 1
        elif row.is_builtin:
            changed = False
            for key, val in vals.items():
                if getattr(row, key) != val:
                    setattr(row, key, val)
                    changed = True
            if changed:
                updated += 1
        # else: user-created row with a clashing id — leave it alone.

    for cve_id, row in existing.items():
        if cve_id not in source and row.is_builtin:
            await db.delete(row)  # variants cascade
            pruned += 1

    if new_rows:
        db.add_all(new_rows)
    if inserted or updated or pruned:
        await db.commit()

    logger.info(
        "CVE reconcile: +%d inserted, %d updated, %d pruned (DB now matches source)",
        inserted, updated, pruned,
    )
    return inserted


async def seed_vulnerable_variants(db: AsyncSession) -> int:
    """Seed vulnerable fingerprint variants from CVE data.

    These variants contain protocol identity overrides that cause
    devices to report vulnerable firmware versions in their responses.
    """
    from app.models.cve_vulnerability import CVEVulnerability
    from app.models.vulnerable_fingerprint import VulnerableFingerprintVariant
    from app.services.cve_data import ALL_CVES

    # Pre-load all CVE records (cve_id -> DB id) in a single query
    result = await db.execute(
        select(CVEVulnerability.cve_id, CVEVulnerability.id)
    )
    cve_id_to_db_id = {row[0]: row[1] for row in result.all()}

    # Pre-load existing variants (full rows, keyed by (cve_id, display_name))
    # so we can both skip-create and patch newly-added override columns onto
    # rows that pre-date this column.
    result = await db.execute(select(VulnerableFingerprintVariant))
    existing_by_key: dict[tuple, VulnerableFingerprintVariant] = {
        (v.cve_vulnerability_id, v.display_name): v for v in result.scalars().all()
    }

    # Columns that may have been added to the schema after a variant was
    # first seeded — backfill them on existing rows from the source CVE dict
    # without recreating the variant (preserving its UUID and any FK refs).
    BACKFILL_COLUMNS = (
        "cip_identity_override",
        "snmp_identity_override",
        "bacnet_identity_override",
        "dnp3_identity_override",
        "iec104_identity_override",
        "iec61850_identity_override",
        "c37118_identity_override",
        "snmp_sys_descr_template",
    )

    new_variants = []
    patched = 0

    for cve_data in ALL_CVES:
        cve_db_id = cve_id_to_db_id.get(cve_data["cve_id"])
        if not cve_db_id:
            continue

        for variant_data in cve_data.get("vulnerable_variants", []):
            variant_key = (cve_db_id, variant_data["display_name"])
            existing = existing_by_key.get(variant_key)
            if existing is not None:
                changed = False
                for col in BACKFILL_COLUMNS:
                    src = variant_data.get(col)
                    if src and getattr(existing, col, None) in (None, {}):
                        setattr(existing, col, src)
                        changed = True
                if changed:
                    patched += 1
                continue

            new_variants.append(VulnerableFingerprintVariant(
                cve_vulnerability_id=cve_db_id,
                display_name=variant_data["display_name"],
                firmware_version=variant_data["firmware_version"],
                modbus_identity_override=variant_data.get("modbus_identity_override"),
                ethernet_ip_identity_override=variant_data.get(
                    "ethernet_ip_identity_override"
                ),
                profinet_identity_override=variant_data.get(
                    "profinet_identity_override"
                ),
                s7_identity_override=variant_data.get("s7_identity_override"),
                cip_identity_override=variant_data.get("cip_identity_override"),
                snmp_identity_override=variant_data.get("snmp_identity_override"),
                bacnet_identity_override=variant_data.get("bacnet_identity_override"),
                dnp3_identity_override=variant_data.get("dnp3_identity_override"),
                iec104_identity_override=variant_data.get("iec104_identity_override"),
                iec61850_identity_override=variant_data.get("iec61850_identity_override"),
                c37118_identity_override=variant_data.get("c37118_identity_override"),
                snmp_sys_descr_template=variant_data.get("snmp_sys_descr_template"),
                target_vendor=cve_data["vendor"],
                target_product_family=cve_data.get("product_family"),
                target_models=cve_data.get("affected_models"),
                is_builtin=True,
                is_active=True,
            ))

    if new_variants:
        db.add_all(new_variants)
    if new_variants or patched:
        await db.commit()
        if patched:
            logger.info(f"Backfilled override columns on {patched} existing variants")

    return len(new_variants)


async def run_seed_data(db: AsyncSession) -> dict:
    """Run all seed data operations."""
    results = {}

    templates_created = await seed_protocol_templates(db)
    results["protocol_templates"] = f"Seeded {templates_created} protocol templates"

    # Seed DeviceTemplate DB table (unified source for palette + fingerprints)
    device_templates_created = await seed_device_templates_db(db)
    results["device_templates"] = f"Seeded {device_templates_created} device templates"

    # Seed CVE vulnerabilities and vulnerable variants
    cve_count = await seed_cve_vulnerabilities(db)
    results["cve_vulnerabilities"] = f"Seeded {cve_count} CVE vulnerabilities"

    variant_count = await seed_vulnerable_variants(db)
    results["vulnerable_variants"] = f"Seeded {variant_count} vulnerable variants"

    return results
