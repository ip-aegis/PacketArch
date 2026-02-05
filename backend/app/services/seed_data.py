"""Seed data for device profiles, protocol templates, and vendor fingerprints."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_profile import DeviceProfile
from app.models.device_template import DeviceTemplate, TemplateSource
from app.models.protocol_template import ProtocolTemplate
from app.services.device_templates import DEVICE_TEMPLATES
from app.services.device_profiles import get_all_vendor_profiles

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


async def seed_device_profiles(db: AsyncSession) -> int:
    """Seed built-in device profiles including vendor-specific profiles."""
    created = 0

    # Combine generic profiles with vendor-specific profiles
    all_profiles = DEVICE_PROFILES + get_all_vendor_profiles()

    for profile_data in all_profiles:
        # Check if profile already exists by name
        result = await db.execute(
            select(DeviceProfile).where(
                DeviceProfile.name == profile_data["name"],
                DeviceProfile.is_builtin == True,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            profile = DeviceProfile(**profile_data)
            db.add(profile)
            created += 1

    if created > 0:
        await db.commit()

    return created


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


async def seed_device_templates_db(db: AsyncSession) -> int:
    """Seed built-in device templates to the DeviceTemplate DB table.

    This is the NEW authoritative source for vendor fingerprints.
    Seeds from the Python dataclass library (device_templates.py) into the
    DeviceTemplate DB table with source=VENDOR_BUILTIN.

    The DeviceTemplate table consolidates:
    - VendorFingerprint (legacy, built-in fingerprints)
    - LearnedDeviceFingerprint (PCAP-learned fingerprints)
    - User-created fingerprints

    Returns:
        Number of templates created
    """
    from app.services.device_templates import get_fingerprint_from_template

    # Pre-load all existing builtin (vendor, model) combos in a single query
    result = await db.execute(
        select(DeviceTemplate.vendor, DeviceTemplate.model).where(
            DeviceTemplate.source == TemplateSource.VENDOR_BUILTIN.value,
        )
    )
    existing_combos = {
        (row[0].lower(), row[1]) for row in result.all()
    }

    # Track combos from the Python library to avoid duplicates
    # (some templates share vendor/model with different IDs)
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

        new_templates.append(DeviceTemplate(
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
            active_protocols=template.supported_protocols,
            protocol_quirks=template.protocol_quirks if template.protocol_quirks else None,
            error_behavior=template.error_behavior if template.error_behavior else None,
            # Quality metrics (builtin = high confidence)
            confidence=1.0,
            sample_count=1,
            consistency_score=1.0,
            # Metadata
            name=f"{template.vendor} {template.model_name}",
            description=template.description,
            is_active=True,
        ))

    if new_templates:
        db.add_all(new_templates)
        await db.commit()

    return len(new_templates)


async def seed_cve_vulnerabilities(db: AsyncSession) -> int:
    """Seed CVE vulnerabilities from Python data files.

    These CVEs are used to generate protocol identity responses with
    vulnerable firmware versions that security tools will detect.
    """
    from app.models.cve_vulnerability import CVESeverity, CVEVulnerability
    from app.services.cve_data import ALL_CVES

    # Pre-load all existing CVE IDs in a single query
    result = await db.execute(select(CVEVulnerability.cve_id))
    existing_cve_ids = {row[0] for row in result.all()}

    new_cves = []
    seen_cve_ids: set[str] = set()

    for cve_data in ALL_CVES:
        cve_id = cve_data["cve_id"]

        # Skip duplicates within the batch and already-seeded entries
        if cve_id in seen_cve_ids or cve_id in existing_cve_ids:
            continue
        seen_cve_ids.add(cve_id)

        severity_str = cve_data.get("severity", "medium").lower()
        severity = CVESeverity(severity_str)

        new_cves.append(CVEVulnerability(
            cve_id=cve_data["cve_id"],
            title=cve_data["title"],
            description=cve_data.get("description"),
            severity=severity,
            cvss_score=cve_data.get("cvss_score"),
            cvss_vector=cve_data.get("cvss_vector"),
            vendor=cve_data["vendor"],
            product_family=cve_data["product_family"],
            affected_models=cve_data.get("affected_models"),
            affected_firmware_min=cve_data.get("affected_firmware_min"),
            affected_firmware_max=cve_data.get("affected_firmware_max", "unknown"),
            fixed_firmware_version=cve_data.get("fixed_firmware_version"),
            cyber_vision_detectable=cve_data.get("cyber_vision_detectable", True),
            detection_method=cve_data.get("detection_method"),
            advisory_url=cve_data.get("advisory_url"),
            references=cve_data.get("references"),
            mitre_techniques=cve_data.get("mitre_techniques"),
            exploit_available=cve_data.get("exploit_available", False),
            exploit_complexity=cve_data.get("exploit_complexity"),
            published_date=cve_data.get("published_date"),
            is_builtin=True,
        ))

    if new_cves:
        db.add_all(new_cves)
        await db.commit()

    return len(new_cves)


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

    # Pre-load all existing variant keys (cve_id, display_name) in a single query
    result = await db.execute(
        select(
            VulnerableFingerprintVariant.cve_vulnerability_id,
            VulnerableFingerprintVariant.display_name,
        )
    )
    existing_variants = {(row[0], row[1]) for row in result.all()}

    new_variants = []

    for cve_data in ALL_CVES:
        cve_db_id = cve_id_to_db_id.get(cve_data["cve_id"])
        if not cve_db_id:
            continue

        for variant_data in cve_data.get("vulnerable_variants", []):
            variant_key = (cve_db_id, variant_data["display_name"])
            if variant_key in existing_variants:
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
                snmp_sys_descr_template=variant_data.get("snmp_sys_descr_template"),
                target_vendor=cve_data["vendor"],
                target_product_family=cve_data.get("product_family"),
                target_models=cve_data.get("affected_models"),
                is_builtin=True,
                is_active=True,
            ))

    if new_variants:
        db.add_all(new_variants)
        await db.commit()

    return len(new_variants)


async def run_seed_data(db: AsyncSession) -> dict:
    """Run all seed data operations."""
    results = {}

    profiles_created = await seed_device_profiles(db)
    results["device_profiles"] = f"Seeded {profiles_created} device profiles"

    templates_created = await seed_protocol_templates(db)
    results["protocol_templates"] = f"Seeded {templates_created} protocol templates"

    # Seed DeviceTemplate DB table (NEW authoritative source)
    device_templates_created = await seed_device_templates_db(db)
    results["device_templates"] = f"Seeded {device_templates_created} device templates (new)"

    # Seed CVE vulnerabilities and vulnerable variants
    cve_count = await seed_cve_vulnerabilities(db)
    results["cve_vulnerabilities"] = f"Seeded {cve_count} CVE vulnerabilities"

    variant_count = await seed_vulnerable_variants(db)
    results["vulnerable_variants"] = f"Seeded {variant_count} vulnerable variants"

    return results
