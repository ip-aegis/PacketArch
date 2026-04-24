# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""MCP tool registration and handler functions for AI assistant.

This module contains all MCP tool registrations that were previously
inline in the ai.py routes file. Tools are registered with the MCP server
and bound to the current request's database session.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp_server.server import mcp_server
from app.mcp_server.tools import (
    addressing_tools,
    ai_generation_tools,
    attack_tools,
    device_tools,
    external_comm_tools,
    fingerprint_tools,
    flow_tools,
    layout_tools,
    protocol_tools,
    scenario_tools,
    validation_tools,
)
from app.services.ai_scenario_generation_service import (
    create_from_template,
    get_template_preview,
    list_templates_filtered,
)
from app.scenario_templates import list_verticals

logger = logging.getLogger(__name__)


def register_mcp_tools(db: AsyncSession, user_id: str | None = None) -> None:
    """Register all MCP tools with the server.

    This must be called at the start of each chat request to ensure the tools
    have access to the current request's database session. The lambda closures
    capture the db parameter, which must be valid for the duration of tool execution.

    Args:
        db: Database session for the current request
        user_id: Current user ID (needed for scenario generation tools)
    """
    # ==================== Device Tools ====================
    mcp_server.register_tool(
        name="list_devices",
        description="List all devices in a scenario",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id: device_tools.list_devices(db, scenario_id),
    )

    mcp_server.register_tool(
        name="add_device",
        description="Add a device to a scenario. IMPORTANT: Maximum 100 devices per scenario. Plan your device count carefully before adding devices.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_data": {"type": "object", "description": "Device configuration"},
            },
            "required": ["scenario_id", "device_data"],
        },
        handler=lambda scenario_id, device_data: device_tools.add_device(
            db, scenario_id, device_data
        ),
    )

    mcp_server.register_tool(
        name="update_device",
        description="Update a device in a scenario",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "updates": {"type": "object", "description": "Updates to apply"},
            },
            "required": ["scenario_id", "device_id", "updates"],
        },
        handler=lambda scenario_id, device_id, updates: device_tools.update_device(
            db, scenario_id, device_id, updates
        ),
    )

    mcp_server.register_tool(
        name="remove_device",
        description="Remove a device from a scenario",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id: device_tools.remove_device(
            db, scenario_id, device_id
        ),
    )

    # ==================== Flow Tools ====================
    mcp_server.register_tool(
        name="list_flows",
        description="List all flows in a scenario",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id: flow_tools.list_flows(db, scenario_id),
    )

    mcp_server.register_tool(
        name="add_flow",
        description="Add a flow to a scenario",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_data": {"type": "object", "description": "Flow configuration"},
            },
            "required": ["scenario_id", "flow_data"],
        },
        handler=lambda scenario_id, flow_data: flow_tools.add_flow(db, scenario_id, flow_data),
    )

    mcp_server.register_tool(
        name="suggest_flows",
        description="AI suggests flows for a device",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "source_device_id": {"type": "string", "description": "Source device ID"},
            },
            "required": ["scenario_id", "source_device_id"],
        },
        handler=lambda scenario_id, source_device_id: flow_tools.suggest_flows(
            db, scenario_id, source_device_id
        ),
    )

    # ==================== Scenario Tools ====================
    mcp_server.register_tool(
        name="get_scenario_summary",
        description="Get scenario summary with statistics",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id: scenario_tools.get_scenario_summary(db, scenario_id),
    )

    # ==================== Validation Tools ====================
    mcp_server.register_tool(
        name="validate_topology",
        description="Validate scenario topology for issues",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id: validation_tools.validate_topology(db, scenario_id),
    )

    mcp_server.register_tool(
        name="score_realism",
        description="Score the realism of a scenario (0-100)",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id: validation_tools.score_realism(db, scenario_id),
    )

    # ==================== Addressing Tools ====================
    mcp_server.register_tool(
        name="auto_assign_addresses",
        description="Automatically assign IP and MAC addresses",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "scheme": {
                    "type": "string",
                    "description": "Addressing scheme",
                    "enum": ["zone_based", "sequential", "vertical_based"],
                },
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id, scheme="zone_based": addressing_tools.auto_assign_addresses(
            db, scenario_id, scheme
        ),
    )

    mcp_server.register_tool(
        name="assign_vlans",
        description="Assign VLANs to devices based on network zones",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "zone_vlan_map": {
                    "type": "object",
                    "description": "Optional custom zone->VLAN mapping",
                },
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id, zone_vlan_map=None: addressing_tools.assign_vlans(
            db, scenario_id, zone_vlan_map
        ),
    )

    # ==================== Fingerprint Tools ====================
    mcp_server.register_tool(
        name="list_vendor_fingerprints",
        description="List available vendor fingerprints. Returns vendor, model, protocols, and firmware version for each fingerprint.",
        input_schema={
            "type": "object",
            "properties": {
                "vendor": {"type": "string", "description": "Optional vendor name to filter by (e.g., 'siemens', 'rockwell', 'schneider')"},
            },
        },
        handler=lambda vendor=None: fingerprint_tools.list_vendor_fingerprints(vendor),
    )

    mcp_server.register_tool(
        name="get_fingerprint_detail",
        description="Get full fingerprint details including TCP stack characteristics, response timing, protocol identities, and quirks.",
        input_schema={
            "type": "object",
            "properties": {
                "vendor": {"type": "string", "description": "Vendor name"},
                "model": {"type": "string", "description": "Model identifier"},
            },
            "required": ["vendor", "model"],
        },
        handler=lambda vendor, model: fingerprint_tools.get_fingerprint_detail(vendor, model),
    )

    mcp_server.register_tool(
        name="suggest_fingerprint_for_device",
        description="Suggest appropriate fingerprints for a device type based on typical vendors and models.",
        input_schema={
            "type": "object",
            "properties": {
                "device_type": {"type": "string", "description": "Device type (plc, hmi, rtu, drive, io_module, relay, sensor)"},
                "preferred_vendor": {"type": "string", "description": "Optional preferred vendor"},
            },
            "required": ["device_type"],
        },
        handler=lambda device_type, preferred_vendor=None: fingerprint_tools.suggest_fingerprint_for_device(
            device_type, preferred_vendor
        ),
    )

    mcp_server.register_tool(
        name="apply_fingerprint_to_device",
        description="Apply a vendor fingerprint to a device. Sets protocol identities, TCP stack characteristics, response timing, and error behavior.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "vendor": {"type": "string", "description": "Vendor name"},
                "model": {"type": "string", "description": "Model identifier"},
            },
            "required": ["scenario_id", "device_id", "vendor", "model"],
        },
        handler=lambda scenario_id, device_id, vendor, model: fingerprint_tools.apply_fingerprint_to_device(
            db, scenario_id, device_id, vendor, model
        ),
    )

    # ==================== Realism Configuration Tools ====================
    mcp_server.register_tool(
        name="configure_device_realism",
        description="Set realism parameters for a device including response timing, error rates, and protocol quirks.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "response_timing": {
                    "type": "object",
                    "properties": {
                        "mean_ms": {"type": "number", "description": "Mean response time in milliseconds"},
                        "std_dev_ms": {"type": "number", "description": "Standard deviation in milliseconds"},
                    },
                    "description": "Response timing configuration",
                },
                "error_config": {
                    "type": "object",
                    "properties": {
                        "exception_rate": {"type": "number", "description": "Rate of protocol exceptions (0.0-1.0)"},
                        "timeout_rate": {"type": "number", "description": "Rate of timeouts (0.0-1.0)"},
                    },
                    "description": "Error behavior configuration",
                },
                "protocol_quirks": {"type": "object", "description": "Protocol-specific quirks"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, response_timing=None, error_config=None, protocol_quirks=None: fingerprint_tools.configure_device_realism(
            db, scenario_id, device_id, response_timing, error_config, protocol_quirks
        ),
    )

    mcp_server.register_tool(
        name="configure_flow_realism",
        description="Set realism parameters for a flow including timing jitter, packet loss, and response delay variance.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "timing_jitter_ms": {"type": "number", "description": "Timing jitter in milliseconds"},
                "packet_loss_rate": {"type": "number", "description": "Packet loss rate (0.0-1.0)"},
                "response_delay_variance_ms": {"type": "number", "description": "Response delay variance in milliseconds"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, timing_jitter_ms=None, packet_loss_rate=None, response_delay_variance_ms=None: fingerprint_tools.configure_flow_realism(
            db, scenario_id, flow_id, timing_jitter_ms, packet_loss_rate, response_delay_variance_ms
        ),
    )

    mcp_server.register_tool(
        name="apply_realism_preset",
        description="Apply a realism preset to the entire scenario. Presets: 'minimal' (no jitter/errors), 'moderate' (realistic timing), 'high_fidelity' (full fingerprinting), 'vertical_specific' (industry norms).",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "preset": {
                    "type": "string",
                    "enum": ["minimal", "moderate", "high_fidelity", "vertical_specific"],
                    "description": "Preset name",
                },
            },
            "required": ["scenario_id", "preset"],
        },
        handler=lambda scenario_id, preset: fingerprint_tools.apply_realism_preset(
            db, scenario_id, preset
        ),
    )

    # ==================== CVE and Vulnerability Tools ====================
    mcp_server.register_tool(
        name="search_cves",
        description="Search the CVE database with filters. Returns CVE ID, title, severity, CVSS score, vendor, and product family.",
        input_schema={
            "type": "object",
            "properties": {
                "vendor": {"type": "string", "description": "Filter by vendor (Rockwell, Siemens, Schneider)"},
                "product_family": {"type": "string", "description": "Filter by product family"},
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Filter by severity",
                },
                "cyber_vision_detectable": {"type": "boolean", "description": "Filter by Cisco Cyber Vision detectability"},
            },
        },
        handler=lambda vendor=None, product_family=None, severity=None, cyber_vision_detectable=None: fingerprint_tools.search_cves(
            vendor, product_family, severity, cyber_vision_detectable
        ),
    )

    mcp_server.register_tool(
        name="get_cve_detail",
        description="Get full CVE details including description, MITRE techniques, exploit info, and variant count.",
        input_schema={
            "type": "object",
            "properties": {
                "cve_id": {"type": "string", "description": "CVE identifier (e.g., CVE-2022-1159)"},
            },
            "required": ["cve_id"],
        },
        handler=lambda cve_id: fingerprint_tools.get_cve_detail(cve_id),
    )

    mcp_server.register_tool(
        name="list_vulnerable_variants",
        description="List vulnerable fingerprint variants (pre-built vulnerable device configurations) that can be applied to devices.",
        input_schema={
            "type": "object",
            "properties": {
                "vendor": {"type": "string", "description": "Filter by vendor"},
                "cve_id": {"type": "string", "description": "Filter by CVE ID"},
            },
        },
        handler=lambda vendor=None, cve_id=None: fingerprint_tools.list_vulnerable_variants(vendor, cve_id),
    )

    mcp_server.register_tool(
        name="apply_cve_to_device",
        description="Apply a CVE vulnerability to a device by modifying its fingerprint. This changes protocol identities to reflect vulnerable firmware.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "cve_id": {"type": "string", "description": "CVE identifier"},
                "variant_id": {"type": "string", "description": "Optional specific variant ID"},
            },
            "required": ["scenario_id", "device_id", "cve_id"],
        },
        handler=lambda scenario_id, device_id, cve_id, variant_id=None: fingerprint_tools.apply_cve_to_device(
            db, scenario_id, device_id, cve_id, variant_id
        ),
    )

    mcp_server.register_tool(
        name="suggest_cves_for_device",
        description="Suggest relevant CVEs based on device vendor and model. Returns matching CVEs with relevance scores.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id: fingerprint_tools.suggest_cves_for_device(
            db, scenario_id, device_id
        ),
    )

    mcp_server.register_tool(
        name="get_scenario_vulnerability_profile",
        description="Get vulnerability profile for entire scenario. Shows vulnerable devices, coverage by severity, and suggests additional CVEs.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id: fingerprint_tools.get_scenario_vulnerability_profile(
            db, scenario_id
        ),
    )

    # ==================== Protocol-Specific Tools ====================

    # Modbus
    mcp_server.register_tool(
        name="configure_modbus_device",
        description="Configure Modbus-specific parameters for a device including unit ID, register map, and supported function codes.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "unit_id": {"type": "integer", "description": "Modbus unit/slave ID (1-247)"},
                "register_map": {
                    "type": "object",
                    "properties": {
                        "holding_registers": {"type": "object", "description": "Holding registers config"},
                        "input_registers": {"type": "object", "description": "Input registers config"},
                        "coils": {"type": "object", "description": "Coils config"},
                        "discrete_inputs": {"type": "object", "description": "Discrete inputs config"},
                    },
                    "description": "Register map configuration",
                },
                "function_codes": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Supported Modbus function codes",
                },
                "exception_responses": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Configured exception responses",
                },
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, unit_id=None, register_map=None, function_codes=None, exception_responses=None: protocol_tools.configure_modbus_device(
            db, scenario_id, device_id, unit_id, register_map, function_codes, exception_responses
        ),
    )

    mcp_server.register_tool(
        name="configure_modbus_flow",
        description="Configure Modbus flow polling patterns including read/write operations and exception rate.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "read_operations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "function_code": {"type": "integer"},
                            "start_address": {"type": "integer"},
                            "count": {"type": "integer"},
                            "interval_ms": {"type": "integer"},
                        },
                    },
                    "description": "Read operations",
                },
                "write_operations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "function_code": {"type": "integer"},
                            "start_address": {"type": "integer"},
                            "values": {"type": "array"},
                        },
                    },
                    "description": "Write operations",
                },
                "exception_rate": {"type": "number", "description": "Exception response rate (0.0-1.0)"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, read_operations=None, write_operations=None, exception_rate=None: protocol_tools.configure_modbus_flow(
            db, scenario_id, flow_id, read_operations, write_operations, exception_rate
        ),
    )

    # EtherNet/IP
    mcp_server.register_tool(
        name="configure_ethernet_ip_device",
        description="Configure EtherNet/IP device parameters including vendor ID, device type, and CIP classes.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "vendor_id": {"type": "integer", "description": "CIP vendor ID"},
                "device_type": {"type": "integer", "description": "CIP device type"},
                "product_code": {"type": "integer", "description": "Product code"},
                "serial_number": {"type": "string", "description": "Serial number"},
                "cip_classes": {"type": "object", "description": "CIP class configurations"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, vendor_id=None, device_type=None, product_code=None, serial_number=None, cip_classes=None: protocol_tools.configure_ethernet_ip_device(
            db, scenario_id, device_id, vendor_id, device_type, product_code, serial_number, cip_classes
        ),
    )

    mcp_server.register_tool(
        name="configure_ethernet_ip_connection",
        description="Configure EtherNet/IP I/O connection parameters including connection type, RPI, and data sizes.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "connection_type": {"type": "string", "enum": ["explicit", "class1", "class3"], "description": "Connection type"},
                "rpi_ms": {"type": "integer", "description": "Requested Packet Interval in ms"},
                "input_size": {"type": "integer", "description": "Input data size in bytes"},
                "output_size": {"type": "integer", "description": "Output data size in bytes"},
                "transport_class": {"type": "integer", "description": "Transport class (0-3)"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, connection_type=None, rpi_ms=None, input_size=None, output_size=None, transport_class=None: protocol_tools.configure_ethernet_ip_connection(
            db, scenario_id, flow_id, connection_type, rpi_ms, input_size, output_size, transport_class
        ),
    )

    # PROFINET
    mcp_server.register_tool(
        name="configure_profinet_device",
        description="Configure PROFINET device parameters including station name, vendor ID, and GSD info.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "station_name": {"type": "string", "description": "PROFINET station name (lowercase, alphanumeric with hyphens)"},
                "vendor_id": {"type": "integer", "description": "Vendor ID"},
                "device_id_value": {"type": "integer", "description": "Device ID value"},
                "gsd_info": {"type": "object", "description": "GSD file information"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, station_name=None, vendor_id=None, device_id_value=None, gsd_info=None: protocol_tools.configure_profinet_device(
            db, scenario_id, device_id, station_name, vendor_id, device_id_value, gsd_info
        ),
    )

    mcp_server.register_tool(
        name="configure_profinet_ar",
        description="Configure PROFINET Application Relationship including AR type, cycle time, and I/O data.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "ar_type": {"type": "string", "enum": ["io_controller", "io_device", "io_supervisor"], "description": "AR type"},
                "cycle_time_us": {"type": "integer", "description": "Cycle time in microseconds"},
                "io_data": {"type": "object", "description": "I/O data configuration"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, ar_type=None, cycle_time_us=None, io_data=None: protocol_tools.configure_profinet_ar(
            db, scenario_id, flow_id, ar_type, cycle_time_us, io_data
        ),
    )

    # S7
    mcp_server.register_tool(
        name="configure_s7_device",
        description="Configure Siemens S7 device parameters including rack, slot, PDU size, and data blocks.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "rack": {"type": "integer", "description": "Rack number (0-7)"},
                "slot": {"type": "integer", "description": "Slot number (1-31)"},
                "pdu_size": {"type": "integer", "description": "Maximum PDU size"},
                "cpu_type": {"type": "string", "enum": ["S7-300", "S7-400", "S7-1200", "S7-1500"], "description": "CPU type"},
                "data_blocks": {"type": "array", "items": {"type": "object"}, "description": "Data block configurations"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, rack=None, slot=None, pdu_size=None, cpu_type=None, data_blocks=None: protocol_tools.configure_s7_device(
            db, scenario_id, device_id, rack, slot, pdu_size, cpu_type, data_blocks
        ),
    )

    mcp_server.register_tool(
        name="configure_s7_communication",
        description="Configure S7 read/write operations for DB, M, I, Q, C, T memory areas.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "read_areas": {"type": "array", "items": {"type": "object", "properties": {"area": {"type": "string", "enum": ["DB", "M", "I", "Q", "C", "T"]}, "db_number": {"type": "integer"}, "start": {"type": "integer"}, "length": {"type": "integer"}, "interval_ms": {"type": "integer"}}}, "description": "Read operations"},
                "write_areas": {"type": "array", "items": {"type": "object", "properties": {"area": {"type": "string", "enum": ["DB", "M", "I", "Q", "C", "T"]}, "db_number": {"type": "integer"}, "start": {"type": "integer"}, "values": {"type": "array"}}}, "description": "Write operations"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, read_areas=None, write_areas=None: protocol_tools.configure_s7_communication(
            db, scenario_id, flow_id, read_areas, write_areas
        ),
    )

    # DNP3
    mcp_server.register_tool(
        name="configure_dnp3_device",
        description="Configure DNP3 device parameters including master/outstation addresses and data link layer settings.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "master_address": {"type": "integer", "description": "DNP3 master address (0-65519)"},
                "outstation_address": {"type": "integer", "description": "DNP3 outstation address (0-65519)"},
                "data_link_config": {"type": "object", "properties": {"confirm_timeout_ms": {"type": "integer"}, "max_retries": {"type": "integer"}}, "description": "Data link layer configuration"},
                "application_config": {"type": "object", "properties": {"response_timeout_ms": {"type": "integer"}, "event_buffer_size": {"type": "integer"}}, "description": "Application layer configuration"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, master_address=None, outstation_address=None, data_link_config=None, application_config=None: protocol_tools.configure_dnp3_device(
            db, scenario_id, device_id, master_address, outstation_address, data_link_config, application_config
        ),
    )

    mcp_server.register_tool(
        name="configure_dnp3_flow",
        description="Configure DNP3 flow polling patterns including class polling and unsolicited responses.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "polling_classes": {"type": "array", "items": {"type": "integer", "enum": [0, 1, 2, 3]}, "description": "Classes to poll (0=static, 1/2/3=events)"},
                "integrity_poll_interval_ms": {"type": "integer", "description": "Interval for integrity polls"},
                "unsolicited_responses": {"type": "boolean", "description": "Enable unsolicited response mode"},
                "event_config": {"type": "object", "description": "Event buffer configuration"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, polling_classes=None, integrity_poll_interval_ms=None, unsolicited_responses=None, event_config=None: protocol_tools.configure_dnp3_flow(
            db, scenario_id, flow_id, polling_classes, integrity_poll_interval_ms, unsolicited_responses, event_config
        ),
    )

    # IEC 104
    mcp_server.register_tool(
        name="configure_iec104_device",
        description="Configure IEC 60870-5-104 device parameters including addresses and timeout values.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "originator_address": {"type": "integer", "description": "Originator address (OA)"},
                "common_address": {"type": "integer", "description": "Common Address of ASDU (CA)"},
                "k_value": {"type": "integer", "description": "Max unconfirmed I-format APDUs (1-32767)"},
                "w_value": {"type": "integer", "description": "Latest ack threshold (1-32767)"},
                "t1_timeout_ms": {"type": "integer", "description": "Send/receive timeout"},
                "t2_timeout_ms": {"type": "integer", "description": "Ack timeout"},
                "t3_timeout_ms": {"type": "integer", "description": "Test frame timeout"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, originator_address=None, common_address=None, k_value=None, w_value=None, t1_timeout_ms=None, t2_timeout_ms=None, t3_timeout_ms=None: protocol_tools.configure_iec104_device(
            db, scenario_id, device_id, originator_address, common_address, k_value, w_value, t1_timeout_ms, t2_timeout_ms, t3_timeout_ms
        ),
    )

    mcp_server.register_tool(
        name="configure_iec104_flow",
        description="Configure IEC 104 flow polling patterns including general interrogation and spontaneous events.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "general_interrogation": {"type": "boolean", "description": "Enable general interrogation"},
                "interrogation_interval_ms": {"type": "integer", "description": "Interval between interrogation requests"},
                "spontaneous_events": {"type": "array", "items": {"type": "object"}, "description": "Spontaneous event configuration"},
                "time_sync": {"type": "boolean", "description": "Enable time synchronization"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, general_interrogation=None, interrogation_interval_ms=None, spontaneous_events=None, time_sync=None: protocol_tools.configure_iec104_flow(
            db, scenario_id, flow_id, general_interrogation, interrogation_interval_ms, spontaneous_events, time_sync
        ),
    )

    # BACnet
    mcp_server.register_tool(
        name="configure_bacnet_device",
        description="Configure BACnet device parameters including device instance, vendor ID, and object list.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "device_instance": {"type": "integer", "description": "BACnet device instance (0-4194302)"},
                "vendor_id": {"type": "integer", "description": "BACnet vendor ID"},
                "max_apdu_length": {"type": "integer", "description": "Maximum APDU length (50-1476)"},
                "segmentation_support": {"type": "string", "enum": ["both", "transmit", "receive", "none"], "description": "Segmentation support"},
                "object_list": {"type": "array", "items": {"type": "object"}, "description": "List of BACnet objects"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, device_instance=None, vendor_id=None, max_apdu_length=None, segmentation_support=None, object_list=None: protocol_tools.configure_bacnet_device(
            db, scenario_id, device_id, device_instance, vendor_id, max_apdu_length, segmentation_support, object_list
        ),
    )

    mcp_server.register_tool(
        name="configure_bacnet_polling",
        description="Configure BACnet flow polling patterns including ReadPropertyMultiple and COV subscriptions.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "read_property_multiple": {"type": "array", "items": {"type": "object"}, "description": "ReadPropertyMultiple configuration"},
                "cov_subscriptions": {"type": "array", "items": {"type": "object"}, "description": "COV subscription configuration"},
                "poll_interval_ms": {"type": "integer", "description": "Polling interval for ReadProperty operations"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, read_property_multiple=None, cov_subscriptions=None, poll_interval_ms=None: protocol_tools.configure_bacnet_polling(
            db, scenario_id, flow_id, read_property_multiple, cov_subscriptions, poll_interval_ms
        ),
    )

    # SNMP
    mcp_server.register_tool(
        name="configure_snmp_device",
        description="Configure SNMP device parameters including version, community strings, and system information.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "snmp_version": {"type": "string", "enum": ["v1", "v2c", "v3"], "description": "SNMP version"},
                "community_read": {"type": "string", "description": "Read community string"},
                "community_write": {"type": "string", "description": "Write community string"},
                "sys_descr": {"type": "string", "description": "System description"},
                "sys_object_id": {"type": "string", "description": "System OID"},
                "sys_name": {"type": "string", "description": "System name"},
                "sys_location": {"type": "string", "description": "System location"},
                "supported_mibs": {"type": "array", "items": {"type": "string"}, "description": "List of supported MIBs"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, snmp_version=None, community_read=None, community_write=None, sys_descr=None, sys_object_id=None, sys_name=None, sys_location=None, supported_mibs=None: protocol_tools.configure_snmp_device(
            db, scenario_id, device_id, snmp_version, community_read, community_write, sys_descr, sys_object_id, sys_name, sys_location, supported_mibs
        ),
    )

    mcp_server.register_tool(
        name="configure_snmp_polling",
        description="Configure SNMP flow polling patterns including OID list, GetBulk, and trap configuration.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "oid_list": {"type": "array", "items": {"type": "string"}, "description": "List of OIDs to poll"},
                "poll_interval_ms": {"type": "integer", "description": "Polling interval"},
                "use_get_bulk": {"type": "boolean", "description": "Use GetBulk requests (SNMPv2c/v3)"},
                "max_repetitions": {"type": "integer", "description": "Max repetitions for GetBulk"},
                "trap_config": {"type": "object", "description": "Trap configuration"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, oid_list=None, poll_interval_ms=None, use_get_bulk=None, max_repetitions=None, trap_config=None: protocol_tools.configure_snmp_polling(
            db, scenario_id, flow_id, oid_list, poll_interval_ms, use_get_bulk, max_repetitions, trap_config
        ),
    )

    # OPC UA
    mcp_server.register_tool(
        name="configure_opcua_device",
        description="Configure OPC UA device parameters including application URIs, security settings, and namespaces.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "application_uri": {"type": "string", "description": "Application URI"},
                "product_uri": {"type": "string", "description": "Product URI"},
                "application_name": {"type": "string", "description": "Application name"},
                "security_mode": {"type": "string", "enum": ["None", "Sign", "SignAndEncrypt"], "description": "Security mode"},
                "security_policy": {"type": "string", "enum": ["None", "Basic128Rsa15", "Basic256", "Basic256Sha256"], "description": "Security policy"},
                "namespace_uris": {"type": "array", "items": {"type": "string"}, "description": "List of namespace URIs"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, application_uri=None, product_uri=None, application_name=None, security_mode=None, security_policy=None, namespace_uris=None: protocol_tools.configure_opcua_device(
            db, scenario_id, device_id, application_uri, product_uri, application_name, security_mode, security_policy, namespace_uris
        ),
    )

    mcp_server.register_tool(
        name="configure_opcua_subscription",
        description="Configure OPC UA subscription parameters including node IDs and publishing intervals.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "node_ids": {"type": "array", "items": {"type": "string"}, "description": "List of node IDs to subscribe to"},
                "publishing_interval_ms": {"type": "integer", "description": "Publishing interval"},
                "lifetime_count": {"type": "integer", "description": "Subscription lifetime count"},
                "max_keepalive_count": {"type": "integer", "description": "Max keepalive count"},
                "sampling_interval_ms": {"type": "integer", "description": "Sampling interval for monitored items"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, node_ids=None, publishing_interval_ms=None, lifetime_count=None, max_keepalive_count=None, sampling_interval_ms=None: protocol_tools.configure_opcua_subscription(
            db, scenario_id, flow_id, node_ids, publishing_interval_ms, lifetime_count, max_keepalive_count, sampling_interval_ms
        ),
    )

    # IEC 61850
    mcp_server.register_tool(
        name="configure_iec61850_ied",
        description="Configure IEC 61850 IED parameters including IED name, logical devices, and GOOSE settings.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "ied_name": {"type": "string", "description": "IED name (used in SCL)"},
                "manufacturer": {"type": "string", "description": "Manufacturer name"},
                "model": {"type": "string", "description": "Model number"},
                "logical_devices": {"type": "array", "items": {"type": "object"}, "description": "List of logical devices"},
                "goose_config": {"type": "object", "description": "GOOSE configuration"},
            },
            "required": ["scenario_id", "device_id"],
        },
        handler=lambda scenario_id, device_id, ied_name=None, manufacturer=None, model=None, logical_devices=None, goose_config=None: protocol_tools.configure_iec61850_ied(
            db, scenario_id, device_id, ied_name, manufacturer, model, logical_devices, goose_config
        ),
    )

    mcp_server.register_tool(
        name="configure_goose_publisher",
        description="Configure GOOSE publishing parameters for IEC 61850 protection messaging.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "gocb_ref": {"type": "string", "description": "GOOSE control block reference"},
                "dataset": {"type": "string", "description": "Dataset reference"},
                "app_id": {"type": "integer", "description": "Application ID"},
                "conf_rev": {"type": "integer", "description": "Configuration revision"},
                "min_time_ms": {"type": "integer", "description": "Minimum time between GOOSE frames"},
                "max_time_ms": {"type": "integer", "description": "Maximum time between GOOSE frames"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, gocb_ref=None, dataset=None, app_id=None, conf_rev=None, min_time_ms=None, max_time_ms=None: protocol_tools.configure_goose_publisher(
            db, scenario_id, flow_id, gocb_ref, dataset, app_id, conf_rev, min_time_ms, max_time_ms
        ),
    )

    # ==================== Canvas Layout Tools ====================
    mcp_server.register_tool(
        name="set_device_position",
        description="Set exact X/Y coordinates for a device on the canvas.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "x": {"type": "number", "description": "X coordinate in pixels"},
                "y": {"type": "number", "description": "Y coordinate in pixels"},
            },
            "required": ["scenario_id", "device_id", "x", "y"],
        },
        handler=lambda scenario_id, device_id, x, y: layout_tools.set_device_position(db, scenario_id, device_id, x, y),
    )

    mcp_server.register_tool(
        name="set_zone_bounds",
        description="Set zone position and dimensions on the canvas.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "zone_id": {"type": "string", "description": "Zone ID"},
                "x": {"type": "number", "description": "X coordinate of top-left corner"},
                "y": {"type": "number", "description": "Y coordinate of top-left corner"},
                "width": {"type": "number", "description": "Zone width in pixels"},
                "height": {"type": "number", "description": "Zone height in pixels"},
            },
            "required": ["scenario_id", "zone_id", "x", "y", "width", "height"],
        },
        handler=lambda scenario_id, zone_id, x, y, width, height: layout_tools.set_zone_bounds(db, scenario_id, zone_id, x, y, width, height),
    )

    mcp_server.register_tool(
        name="auto_layout_scenario",
        description="Automatically arrange all devices using layout algorithms. Options: 'hierarchical' (based on flows), 'grid', 'circular', 'zone_grouped'.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "layout_type": {"type": "string", "enum": ["hierarchical", "grid", "circular", "zone_grouped"], "description": "Layout algorithm to use"},
                "spacing": {"type": "number", "description": "Spacing between devices in pixels (default 150)"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id, layout_type="hierarchical", spacing=150: layout_tools.auto_layout_scenario(db, scenario_id, layout_type, spacing),
    )

    mcp_server.register_tool(
        name="move_devices_to_zone",
        description="Move multiple devices into a zone with optional auto-positioning within the zone.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_ids": {"type": "array", "items": {"type": "string"}, "description": "List of device IDs to move"},
                "zone_id": {"type": "string", "description": "Target zone ID"},
                "auto_position": {"type": "boolean", "description": "Auto-position devices within zone (default true)"},
            },
            "required": ["scenario_id", "device_ids", "zone_id"],
        },
        handler=lambda scenario_id, device_ids, zone_id, auto_position=True: layout_tools.move_devices_to_zone(db, scenario_id, device_ids, zone_id, auto_position),
    )

    # ==================== External Communication Tools ====================
    mcp_server.register_tool(
        name="add_external_communication",
        description="Add external communication (C2 beacon, DNS tunnel, HTTP exfil, exploit, port scan) to a scenario. Used for security testing scenarios.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "comm_type": {"type": "string", "enum": ["c2_beacon", "dns_tunnel", "http_exfil", "exploit", "port_scan"], "description": "Type of external communication"},
                "source_device_id": {"type": "string", "description": "Device ID that initiates the communication"},
                "destination_ip": {"type": "string", "description": "External destination IP (auto-generated if not specified)"},
                "start_time_ms": {"type": "number", "description": "Start time in scenario timeline"},
                "duration_ms": {"type": "number", "description": "Duration of the communication (default 300000)"},
                "c2_pattern": {"type": "string", "enum": ["jittered_1m", "jittered_5m", "jittered_10m", "exponential_backoff", "regular_1m", "working_hours"], "description": "C2 beaconing pattern (for c2_beacon type)"},
                "c2_protocol": {"type": "string", "enum": ["http", "https", "dns"], "description": "Protocol for C2 communication"},
                "beacon_count": {"type": "integer", "description": "Number of beacons (for c2_beacon type)"},
                "exfil_data_size": {"type": "integer", "description": "Size of exfiltrated data in bytes"},
                "exploit_pattern": {"type": "string", "description": "Exploit pattern name (for exploit type)"},
                "scan_ot_ports": {"type": "boolean", "description": "Scan OT-specific ports (for port_scan type)"},
                "mitre_technique": {"type": "string", "description": "Override MITRE ATT&CK technique ID"},
            },
            "required": ["scenario_id", "comm_type", "source_device_id"],
        },
        handler=lambda scenario_id, comm_type, source_device_id, destination_ip=None, start_time_ms=0, duration_ms=300000, c2_pattern=None, c2_protocol="http", beacon_count=10, exfil_data_size=1024, exploit_pattern=None, scan_ot_ports=True, mitre_technique=None: external_comm_tools.add_external_communication(
            db, scenario_id, comm_type, source_device_id, destination_ip, start_time_ms, duration_ms, c2_pattern, c2_protocol, beacon_count, exfil_data_size, exploit_pattern, scan_ot_ports, mitre_technique
        ),
    )

    mcp_server.register_tool(
        name="list_external_communications",
        description="List external communications configured in a scenario.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "type_filter": {"type": "string", "enum": ["c2_beacon", "dns_tunnel", "http_exfil", "exploit", "port_scan"], "description": "Filter by communication type"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id, type_filter=None: external_comm_tools.list_external_communications(db, scenario_id, type_filter),
    )

    mcp_server.register_tool(
        name="remove_external_communication",
        description="Remove an external communication from a scenario.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "external_comm_id": {"type": "string", "description": "External communication ID"},
            },
            "required": ["scenario_id", "external_comm_id"],
        },
        handler=lambda scenario_id, external_comm_id: external_comm_tools.remove_external_communication(db, scenario_id, external_comm_id),
    )

    mcp_server.register_tool(
        name="get_external_comm_patterns",
        description="Get available external communication patterns including C2 patterns, exploit patterns, and MITRE ATT&CK mappings.",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: external_comm_tools.get_external_comm_patterns(),
    )

    # ==================== Phase Management Tools ====================
    mcp_server.register_tool(
        name="apply_phase_preset",
        description="Apply a predefined phase configuration preset. Options: startup_shutdown, maintenance_window, shift_change, incident_response.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "preset_name": {"type": "string", "enum": ["startup_shutdown", "maintenance_window", "shift_change", "incident_response"], "description": "Preset name"},
            },
            "required": ["scenario_id", "preset_name"],
        },
        handler=lambda scenario_id, preset_name: scenario_tools.apply_phase_preset(db, scenario_id, preset_name),
    )

    mcp_server.register_tool(
        name="update_phase_timing",
        description="Modify phase timing parameters including start time, duration, intensity, and ramp up/down.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "phase_id": {"type": "string", "description": "Phase ID"},
                "start_ms": {"type": "integer", "description": "New start time in milliseconds"},
                "duration_ms": {"type": "integer", "description": "New duration in milliseconds"},
                "intensity": {"type": "number", "description": "Traffic intensity multiplier (0.0-2.0)"},
                "ramp_up_ms": {"type": "integer", "description": "Ramp up duration in milliseconds"},
                "ramp_down_ms": {"type": "integer", "description": "Ramp down duration in milliseconds"},
            },
            "required": ["scenario_id", "phase_id"],
        },
        handler=lambda scenario_id, phase_id, start_ms=None, duration_ms=None, intensity=None, ramp_up_ms=None, ramp_down_ms=None: scenario_tools.update_phase_timing(
            db, scenario_id, phase_id, start_ms, duration_ms, intensity, ramp_up_ms, ramp_down_ms
        ),
    )

    mcp_server.register_tool(
        name="reorder_phases",
        description="Change phase execution order by providing phase IDs in desired order.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "phase_ids_in_order": {"type": "array", "items": {"type": "string"}, "description": "List of phase IDs in desired execution order"},
            },
            "required": ["scenario_id", "phase_ids_in_order"],
        },
        handler=lambda scenario_id, phase_ids_in_order: scenario_tools.reorder_phases(db, scenario_id, phase_ids_in_order),
    )

    mcp_server.register_tool(
        name="list_phase_presets",
        description="List available phase presets with their descriptions and phase configurations.",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: scenario_tools.list_phase_presets(),
    )

    # ==================== AI Generation Tools ====================
    mcp_server.register_tool(
        name="generate_scenario_from_nl",
        description="""Generate a complete OT scenario from a natural language description.
PREFERRED method for creating new scenarios - creates devices, flows, zones automatically.
IMPORTANT: Respects device counts specified in the description (e.g., "25 devices", "no more than 10 PLCs").
Example: "A manufacturing plant with 5 Rockwell PLCs, 2 HMIs, and 10 VFDs using EtherNet/IP"
Returns: New scenario ID, device count, flow count, and extracted entities.
Maximum 100 devices per scenario.""",
        input_schema={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Natural language description of the OT environment to generate"},
                "name": {"type": "string", "description": "Optional name for the scenario"},
                "duration_ms": {"type": "integer", "description": "Scenario duration in milliseconds (default: 300000 = 5 minutes)"},
            },
            "required": ["description"],
        },
        handler=lambda description, name=None, duration_ms=300000: ai_generation_tools.generate_scenario_from_nl(
            db, user_id, description, name, duration_ms
        ),
    )

    mcp_server.register_tool(
        name="suggest_vertical_template",
        description="""Suggest the most appropriate industry vertical based on a description.
Analyzes keywords and context to recommend: manufacturing, water, energy, or oil_gas.
Returns: Suggested vertical with confidence score and reasoning.""",
        input_schema={
            "type": "object",
            "properties": {"description": {"type": "string", "description": "Description to analyze for vertical suggestion"}},
            "required": ["description"],
        },
        handler=lambda description: ai_generation_tools.suggest_vertical_template(description),
    )

    # ==================== Anomaly Injection Tools ====================
    mcp_server.register_tool(
        name="inject_anomaly_campaign",
        description="""Configure an anomaly injection campaign for security testing.
Creates coordinated anomalies that will be injected during traffic generation.
Anomaly types: timeout, delayed, duplicate, drop, jitter_spike, modbus_exception, etc.""",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "campaign_name": {"type": "string", "description": "Name for the anomaly campaign"},
                "anomaly_types": {"type": "array", "items": {"type": "string"}, "description": "List of anomaly types to include (e.g., ['timeout', 'delayed', 'duplicate'])"},
                "start_time_ms": {"type": "number", "description": "Campaign start time in milliseconds from scenario start"},
                "duration_ms": {"type": "number", "description": "Campaign duration in milliseconds (optional, None for single injection)"},
                "target_flow_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific flow IDs to target (optional, None for all flows)"},
            },
            "required": ["scenario_id", "campaign_name", "anomaly_types", "start_time_ms"],
        },
        handler=lambda scenario_id, campaign_name, anomaly_types, start_time_ms, duration_ms=None, target_flow_ids=None: ai_generation_tools.inject_anomaly_campaign(
            db, scenario_id, campaign_name, anomaly_types, start_time_ms, duration_ms, target_flow_ids
        ),
    )

    mcp_server.register_tool(
        name="list_anomaly_templates",
        description="""List available anomaly templates for injection.
Anomalies are categorized by type (timing, protocol, sequence) and severity.
Use this to see what anomalies are available before creating a campaign.""",
        input_schema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filter by category: timing, protocol, sequence, security, external_communication"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Filter by severity level"},
            },
        },
        handler=lambda category=None, severity=None: ai_generation_tools.list_anomaly_templates(db, category, severity),
    )

    mcp_server.register_tool(
        name="analyze_scenario_for_anomalies",
        description="""Analyze a scenario and suggest appropriate anomalies for security testing.
Examines devices, protocols, and industry vertical to recommend relevant anomaly types.
Returns: Ranked list of anomaly suggestions with relevance scores and reasons.""",
        input_schema={
            "type": "object",
            "properties": {"scenario_id": {"type": "string", "description": "Scenario UUID to analyze"}},
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id: ai_generation_tools.analyze_scenario_for_anomalies(db, scenario_id),
    )

    # ==================== Template Management Tools ====================
    mcp_server.register_tool(
        name="list_industry_verticals",
        description="""List all available industry verticals for scenario templates.
Returns: List of verticals (manufacturing, water_wastewater, energy_power, oil_gas) with their available templates.""",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: list_verticals(),
    )

    mcp_server.register_tool(
        name="list_scenario_templates",
        description="""List all available scenario templates, optionally filtered by industry vertical.
Returns: Template summaries with device counts and supported protocols.""",
        input_schema={
            "type": "object",
            "properties": {
                "vertical": {"type": "string", "description": "Filter by vertical: manufacturing, water_wastewater, energy_power, oil_gas", "enum": ["manufacturing", "water_wastewater", "energy_power", "oil_gas"]},
            },
        },
        handler=lambda vertical=None: list_templates_filtered(vertical),
    )

    mcp_server.register_tool(
        name="get_template_preview",
        description="""Get detailed preview of a specific scenario template.
Shows all devices, flows, zones, and configuration details before creating a scenario.""",
        input_schema={
            "type": "object",
            "properties": {
                "vertical": {"type": "string", "description": "Industry vertical", "enum": ["manufacturing", "water_wastewater", "energy_power", "oil_gas"]},
                "template_name": {"type": "string", "description": "Template name within the vertical (e.g., 'default', 'assembly_line')"},
            },
            "required": ["vertical", "template_name"],
        },
        handler=lambda vertical, template_name: get_template_preview(vertical, template_name),
    )

    mcp_server.register_tool(
        name="create_scenario_from_template",
        description="""Create a new scenario from an industry template.
Generates devices, flows, zones, and phases automatically with proper IP addressing.
Use list_scenario_templates first to see available templates.""",
        input_schema={
            "type": "object",
            "properties": {
                "vertical": {"type": "string", "description": "Industry vertical", "enum": ["manufacturing", "water_wastewater", "energy_power", "oil_gas"]},
                "template_name": {"type": "string", "description": "Template name (default: 'default')"},
                "scenario_name": {"type": "string", "description": "Name for the new scenario"},
                "description": {"type": "string", "description": "Optional scenario description"},
                "total_duration_ms": {"type": "integer", "description": "Scenario duration in ms (default: 300000 = 5 minutes)"},
            },
            "required": ["vertical", "scenario_name"],
        },
        handler=lambda vertical, scenario_name, template_name="default", description="", total_duration_ms=300000: create_from_template(
            db, user_id, vertical, template_name, scenario_name, description, total_duration_ms
        ),
    )

    # ==================== Attack Simulation Tools ====================
    mcp_server.register_tool(
        name="list_attack_playbooks",
        description="List all available attack simulation playbooks with their kill chain stages and MITRE ATT&CK techniques",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=lambda: attack_tools.list_attack_playbooks(),
    )

    mcp_server.register_tool(
        name="get_playbook_details",
        description="Get full details of an attack playbook including kill chain stages, actions, and MITRE techniques",
        input_schema={
            "type": "object",
            "properties": {
                "playbook_id": {"type": "string", "description": "Playbook ID (e.g., 'triton_like', 'pipedream_like')"},
            },
            "required": ["playbook_id"],
        },
        handler=lambda playbook_id: attack_tools.get_playbook_details(playbook_id),
    )

    mcp_server.register_tool(
        name="suggest_attack_for_scenario",
        description="Recommend attack playbooks based on the scenario's protocols and industry vertical",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "protocols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Protocols used in the scenario (e.g., ['modbus_tcp', 's7comm'])",
                },
                "vertical": {"type": "string", "description": "Industry vertical (e.g., 'manufacturing', 'energy')"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id, protocols=None, vertical=None: attack_tools.suggest_attack_for_scenario(
            scenario_id, protocols, vertical
        ),
    )
