"""AI assistant routes for scenario composition."""

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.mcp_server.ai_providers import AIProvider, AIProviderFactory
from app.mcp_server.sanitization.sanitizer import DataSanitizer
from app.mcp_server.server import mcp_server
from app.mcp_server.tools import (
    addressing_tools,
    ai_generation_tools,
    deployment_tools,
    device_tools,
    external_comm_tools,
    fingerprint_tools,
    flow_tools,
    layout_tools,
    learning_tools,
    protocol_tools,
    scenario_tools,
    validation_tools,
)
from app.models.scenario import Scenario
from app.models.settings import SystemSetting
from app.scenario_templates import get_template, list_templates, list_verticals
from app.services.ai_session_service import AISessionService
from app.services.ai_scenario_preview_service import AIScenarioPreviewService
from app.services.ip_management import IPManagementService
from app.services.vendor_fingerprints import (
    get_fingerprint_by_vendor_model,
    get_fingerprints_by_vendor,
    VENDOR_OUI_PREFIXES,
)
from app.ai_services.nl_parser import extract_device_counts, format_device_counts_for_prompt, get_device_limit_warning
import random

logger = logging.getLogger(__name__)

# Maximum devices allowed per scenario
MAX_DEVICES_PER_SCENARIO = 100


def _generate_vendor_mac(vendor: str, device_type: str) -> str:
    """Generate a MAC address using vendor-specific OUI prefix.

    Args:
        vendor: Vendor name (e.g., 'rockwell', 'siemens')
        device_type: Device type for fallback vendor selection

    Returns:
        MAC address string in format XX:XX:XX:XX:XX:XX
    """
    # Get vendor OUI prefixes
    vendor_lower = vendor.lower() if vendor else ""
    oui_prefixes = VENDOR_OUI_PREFIXES.get(vendor_lower)

    if not oui_prefixes:
        # Fallback: try to find OUI by device type typical vendors
        device_type_vendors = {
            "plc": ["siemens", "rockwell", "schneider"],
            "hmi": ["siemens", "rockwell"],
            "rtu": ["schneider", "abb"],
            "drive": ["siemens", "abb", "schneider"],
            "sensor": ["sick", "endress+hauser"],
        }
        fallback_vendors = device_type_vendors.get(device_type.lower(), ["siemens"])
        for fb_vendor in fallback_vendors:
            oui_prefixes = VENDOR_OUI_PREFIXES.get(fb_vendor)
            if oui_prefixes:
                break

    if not oui_prefixes:
        # Ultimate fallback - generic OUI
        oui_prefixes = ["00:00:00"]

    # Select random OUI from vendor's prefixes
    oui = random.choice(oui_prefixes)

    # Generate random NIC portion (last 3 octets)
    nic = [random.randint(0, 255) for _ in range(3)]

    return f"{oui}:{nic[0]:02X}:{nic[1]:02X}:{nic[2]:02X}"


def _generate_serial_number(vendor: str, fingerprint_data: dict) -> str:
    """Generate a realistic serial number based on vendor patterns.

    Args:
        vendor: Vendor name
        fingerprint_data: Fingerprint data that may contain serial format hints

    Returns:
        Serial number string
    """
    vendor_lower = vendor.lower() if vendor else ""

    # Vendor-specific serial number formats
    if vendor_lower == "rockwell":
        # Rockwell format: XXXYYYYY (plant code + sequence)
        return f"{random.choice(['ACD', 'MKE', 'TEC'])}{random.randint(10000, 99999)}"
    elif vendor_lower == "siemens":
        # Siemens format: S XXXX-XXXX-XXXX
        return f"S {random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}"
    elif vendor_lower == "schneider":
        # Schneider format: XXYYMMDDNNNN
        return f"{random.randint(10,99)}{random.randint(1,12):02d}{random.randint(1,28):02d}{random.randint(1000,9999)}"
    elif vendor_lower == "abb":
        # ABB format: 3HADXXXXXX
        return f"3HAD{random.randint(100000, 999999)}"
    elif vendor_lower == "honeywell":
        # Honeywell format: XXXXXXXX
        return f"{random.randint(10000000, 99999999)}"
    elif vendor_lower == "emerson":
        # Emerson format: DXXXXXXXX
        return f"D{random.randint(10000000, 99999999)}"
    else:
        # Generic format
        return f"SN{random.randint(100000000, 999999999)}"


def detect_convergence(tool_calls_history: list[dict]) -> tuple[bool, str]:
    """Detect if AI is done or stuck in a loop.

    Returns (should_stop, reason) tuple.

    Detection rules:
    1. Same tool called 5+ times consecutively = stuck loop
    2. add_device called after device limit warning = should stop
    3. No tool calls for 2+ iterations = natural completion
    """
    if len(tool_calls_history) < 3:
        return False, ""

    # Check for add_device loop (same tool called 5+ times consecutively)
    last_5_names = [tc.get("name") for tc in tool_calls_history[-5:]]
    if len(last_5_names) == 5 and len(set(last_5_names)) == 1:
        if last_5_names[0] == "add_device":
            return True, "Detected add_device loop - stopping to prevent device explosion"
        elif last_5_names[0] == "add_flow":
            return True, "Detected add_flow loop - stopping"

    # Check for oscillating patterns (A, B, A, B, A, B)
    if len(tool_calls_history) >= 6:
        last_6_names = [tc.get("name") for tc in tool_calls_history[-6:]]
        if (
            last_6_names[0] == last_6_names[2] == last_6_names[4]
            and last_6_names[1] == last_6_names[3] == last_6_names[5]
            and last_6_names[0] != last_6_names[1]
        ):
            return True, f"Detected oscillating pattern between {last_6_names[0]} and {last_6_names[1]}"

    return False, ""


router = APIRouter(prefix="/ai", tags=["AI Assistant"])


class AISessionCreateRequest(BaseModel):
    """Request to create or resume an AI session for a scenario."""

    scenario_id: str = Field(..., description="Scenario UUID to associate with the session")


class AISessionResponse(BaseModel):
    """AI session response."""

    session_id: str
    created_at: str
    scenario_id: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)


class AIChatRequest(BaseModel):
    """AI chat request."""

    session_id: str
    scenario_id: str
    message: str


class AIChatResponse(BaseModel):
    """AI chat response."""

    response: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    pending_actions: list[str] = Field(default_factory=list)


class AIToolDefinition(BaseModel):
    """AI tool definition."""

    name: str
    description: str
    category: str


async def _get_ai_provider(db: DBSession) -> AIProvider:
    """Get configured AI provider (Anthropic or OpenAI).

    Uses AIProviderFactory to create the appropriate provider based on
    system settings. Supports both Anthropic Claude and OpenAI GPT models.

    Args:
        db: Database session

    Returns:
        Configured AI provider

    Raises:
        HTTPException: If API key not configured or provider unknown
    """
    try:
        return await AIProviderFactory.create(db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


# Backwards compatibility alias
_get_anthropic_provider = _get_ai_provider


def _register_mcp_tools(db: DBSession, user_id: str | None = None) -> None:
    """Register all MCP tools with the server.

    This must be called at the start of each chat request to ensure the tools
    have access to the current request's database session. The lambda closures
    capture the db parameter, which must be valid for the duration of tool execution.

    Args:
        db: Database session for the current request
        user_id: Current user ID (needed for scenario generation tools)
    """
    # Device tools
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

    # Flow tools
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

    # Scenario tools
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

    # Validation tools
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

    # Addressing tools
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

    # Fingerprint tools
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

    # Realism configuration tools
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

    # CVE and vulnerability tools
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

    # Protocol-specific tools - Modbus
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

    # Protocol-specific tools - EtherNet/IP
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
                "connection_type": {
                    "type": "string",
                    "enum": ["explicit", "class1", "class3"],
                    "description": "Connection type",
                },
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

    # Protocol-specific tools - PROFINET
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
                "ar_type": {
                    "type": "string",
                    "enum": ["io_controller", "io_device", "io_supervisor"],
                    "description": "AR type",
                },
                "cycle_time_us": {"type": "integer", "description": "Cycle time in microseconds"},
                "io_data": {"type": "object", "description": "I/O data configuration"},
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, ar_type=None, cycle_time_us=None, io_data=None: protocol_tools.configure_profinet_ar(
            db, scenario_id, flow_id, ar_type, cycle_time_us, io_data
        ),
    )

    # Protocol-specific tools - S7
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
                "cpu_type": {
                    "type": "string",
                    "enum": ["S7-300", "S7-400", "S7-1200", "S7-1500"],
                    "description": "CPU type",
                },
                "data_blocks": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Data block configurations",
                },
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
                "read_areas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "area": {"type": "string", "enum": ["DB", "M", "I", "Q", "C", "T"]},
                            "db_number": {"type": "integer"},
                            "start": {"type": "integer"},
                            "length": {"type": "integer"},
                            "interval_ms": {"type": "integer"},
                        },
                    },
                    "description": "Read operations",
                },
                "write_areas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "area": {"type": "string", "enum": ["DB", "M", "I", "Q", "C", "T"]},
                            "db_number": {"type": "integer"},
                            "start": {"type": "integer"},
                            "values": {"type": "array"},
                        },
                    },
                    "description": "Write operations",
                },
            },
            "required": ["scenario_id", "flow_id"],
        },
        handler=lambda scenario_id, flow_id, read_areas=None, write_areas=None: protocol_tools.configure_s7_communication(
            db, scenario_id, flow_id, read_areas, write_areas
        ),
    )

    # Learned pattern tools
    mcp_server.register_tool(
        name="list_learned_fingerprints",
        description="List device fingerprints learned from PCAP analysis. Returns fingerprints with vendor, protocols, confidence, and timing information.",
        input_schema={
            "type": "object",
            "properties": {
                "protocol_filter": {"type": "string", "description": "Filter by protocol (modbus, ethernet_ip, profinet, s7)"},
                "vendor_filter": {"type": "string", "description": "Filter by inferred vendor name"},
            },
        },
        handler=lambda protocol_filter=None, vendor_filter=None: learning_tools.list_learned_fingerprints(
            db, protocol_filter, vendor_filter
        ),
    )

    mcp_server.register_tool(
        name="apply_learned_fingerprint_to_device",
        description="Apply a learned fingerprint (from PCAP analysis) to a device. Sets TCP signature, response timing, and MAC address from the learned data.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_id": {"type": "string", "description": "Device ID"},
                "learned_fingerprint_id": {"type": "string", "description": "Learned fingerprint UUID from PCAP analysis"},
            },
            "required": ["scenario_id", "device_id", "learned_fingerprint_id"],
        },
        handler=lambda scenario_id, device_id, learned_fingerprint_id: learning_tools.apply_learned_fingerprint_to_device(
            db, scenario_id, device_id, learned_fingerprint_id
        ),
    )

    mcp_server.register_tool(
        name="list_learned_sequences",
        description="List communication sequences learned from PCAPs. Returns sequences with type (startup, poll_cycle, shutdown), timing, and step count.",
        input_schema={
            "type": "object",
            "properties": {
                "protocol_filter": {"type": "string", "description": "Filter by protocol (modbus, ethernet_ip, profinet, s7)"},
                "sequence_type_filter": {"type": "string", "description": "Filter by sequence type (startup, poll_cycle, shutdown)"},
            },
        },
        handler=lambda protocol_filter=None, sequence_type_filter=None: learning_tools.list_learned_sequences(
            db, protocol_filter, sequence_type_filter
        ),
    )

    mcp_server.register_tool(
        name="apply_sequence_to_flow",
        description="Apply a learned sequence pattern to a flow. Sets timing intervals, jitter, and learned operation steps.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "flow_id": {"type": "string", "description": "Flow ID"},
                "sequence_id": {"type": "string", "description": "Learned sequence UUID"},
            },
            "required": ["scenario_id", "flow_id", "sequence_id"],
        },
        handler=lambda scenario_id, flow_id, sequence_id: learning_tools.apply_sequence_to_flow(
            db, scenario_id, flow_id, sequence_id
        ),
    )

    mcp_server.register_tool(
        name="auto_apply_learned_patterns",
        description="Intelligently apply all relevant learned patterns to a scenario. Matches fingerprints to devices by protocol and sequences to flows.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "match_threshold": {
                    "type": "number",
                    "description": "Minimum confidence threshold for pattern matching (0.0-1.0, default 0.5)",
                },
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id, match_threshold=0.5: learning_tools.auto_apply_learned_patterns(
            db, scenario_id, match_threshold
        ),
    )

    # Deployment control tools
    mcp_server.register_tool(
        name="list_docker_hosts",
        description="List available Docker hosts for traffic generation deployment. Returns host name, hostname, port, and default network interface.",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=lambda: deployment_tools.list_docker_hosts(db),
    )

    mcp_server.register_tool(
        name="start_deployment",
        description="Start a traffic generation deployment on a Docker host. Deploys a container that generates traffic according to the scenario.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "docker_host_id": {"type": "string", "description": "Docker host UUID (use list_docker_hosts to find available hosts)"},
                "network_interface": {"type": "string", "description": "Network interface for packet injection (uses host default if not specified)"},
                "run_mode": {
                    "type": "string",
                    "enum": ["timed", "perpetual"],
                    "description": "Run mode: 'timed' stops after duration, 'perpetual' runs until stopped",
                },
                "duration_ms": {"type": "integer", "description": "Duration in milliseconds for timed mode (default 60000)"},
            },
            "required": ["scenario_id", "docker_host_id"],
        },
        handler=lambda scenario_id, docker_host_id, network_interface=None, run_mode="timed", duration_ms=60000: deployment_tools.start_deployment(
            db, scenario_id, docker_host_id, network_interface, run_mode, duration_ms
        ),
    )

    mcp_server.register_tool(
        name="stop_deployment",
        description="Stop a running deployment. Stops the traffic generation container.",
        input_schema={
            "type": "object",
            "properties": {
                "deployment_id": {"type": "string", "description": "Deployment UUID"},
            },
            "required": ["deployment_id"],
        },
        handler=lambda deployment_id: deployment_tools.stop_deployment(db, deployment_id),
    )

    mcp_server.register_tool(
        name="get_deployment_status",
        description="Get current deployment status including run statistics, elapsed time, and packet count.",
        input_schema={
            "type": "object",
            "properties": {
                "deployment_id": {"type": "string", "description": "Deployment UUID"},
            },
            "required": ["deployment_id"],
        },
        handler=lambda deployment_id: deployment_tools.get_deployment_status(db, deployment_id),
    )

    mcp_server.register_tool(
        name="list_deployments",
        description="List deployments with optional filters. Shows recent deployments with their status.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Filter by scenario UUID"},
                "status_filter": {
                    "type": "string",
                    "enum": ["pending", "starting", "running", "stopping", "stopped", "failed"],
                    "description": "Filter by deployment status",
                },
            },
        },
        handler=lambda scenario_id=None, status_filter=None: deployment_tools.list_deployments(
            db, scenario_id, status_filter
        ),
    )

    # Canvas layout tools
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
        handler=lambda scenario_id, device_id, x, y: layout_tools.set_device_position(
            db, scenario_id, device_id, x, y
        ),
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
        handler=lambda scenario_id, zone_id, x, y, width, height: layout_tools.set_zone_bounds(
            db, scenario_id, zone_id, x, y, width, height
        ),
    )

    mcp_server.register_tool(
        name="auto_layout_scenario",
        description="Automatically arrange all devices using layout algorithms. Options: 'hierarchical' (based on flows), 'grid', 'circular', 'zone_grouped'.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "layout_type": {
                    "type": "string",
                    "enum": ["hierarchical", "grid", "circular", "zone_grouped"],
                    "description": "Layout algorithm to use",
                },
                "spacing": {"type": "number", "description": "Spacing between devices in pixels (default 150)"},
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id, layout_type="hierarchical", spacing=150: layout_tools.auto_layout_scenario(
            db, scenario_id, layout_type, spacing
        ),
    )

    mcp_server.register_tool(
        name="move_devices_to_zone",
        description="Move multiple devices into a zone with optional auto-positioning within the zone.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "device_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of device IDs to move",
                },
                "zone_id": {"type": "string", "description": "Target zone ID"},
                "auto_position": {"type": "boolean", "description": "Auto-position devices within zone (default true)"},
            },
            "required": ["scenario_id", "device_ids", "zone_id"],
        },
        handler=lambda scenario_id, device_ids, zone_id, auto_position=True: layout_tools.move_devices_to_zone(
            db, scenario_id, device_ids, zone_id, auto_position
        ),
    )

    # External communication tools
    mcp_server.register_tool(
        name="add_external_communication",
        description="Add external communication (C2 beacon, DNS tunnel, HTTP exfil, exploit, port scan) to a scenario. Used for security testing scenarios.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "comm_type": {
                    "type": "string",
                    "enum": ["c2_beacon", "dns_tunnel", "http_exfil", "exploit", "port_scan"],
                    "description": "Type of external communication",
                },
                "source_device_id": {"type": "string", "description": "Device ID that initiates the communication"},
                "destination_ip": {"type": "string", "description": "External destination IP (auto-generated if not specified)"},
                "start_time_ms": {"type": "number", "description": "Start time in scenario timeline"},
                "duration_ms": {"type": "number", "description": "Duration of the communication (default 300000)"},
                "c2_pattern": {
                    "type": "string",
                    "enum": ["jittered_1m", "jittered_5m", "jittered_10m", "exponential_backoff", "regular_1m", "working_hours"],
                    "description": "C2 beaconing pattern (for c2_beacon type)",
                },
                "c2_protocol": {
                    "type": "string",
                    "enum": ["http", "https", "dns"],
                    "description": "Protocol for C2 communication",
                },
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
                "type_filter": {
                    "type": "string",
                    "enum": ["c2_beacon", "dns_tunnel", "http_exfil", "exploit", "port_scan"],
                    "description": "Filter by communication type",
                },
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id, type_filter=None: external_comm_tools.list_external_communications(
            db, scenario_id, type_filter
        ),
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
        handler=lambda scenario_id, external_comm_id: external_comm_tools.remove_external_communication(
            db, scenario_id, external_comm_id
        ),
    )

    mcp_server.register_tool(
        name="get_external_comm_patterns",
        description="Get available external communication patterns including C2 patterns, exploit patterns, and MITRE ATT&CK mappings.",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=lambda: external_comm_tools.get_external_comm_patterns(),
    )

    # Phase management tools
    mcp_server.register_tool(
        name="apply_phase_preset",
        description="Apply a predefined phase configuration preset. Options: startup_shutdown, maintenance_window, shift_change, incident_response.",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario UUID"},
                "preset_name": {
                    "type": "string",
                    "enum": ["startup_shutdown", "maintenance_window", "shift_change", "incident_response"],
                    "description": "Preset name",
                },
            },
            "required": ["scenario_id", "preset_name"],
        },
        handler=lambda scenario_id, preset_name: scenario_tools.apply_phase_preset(
            db, scenario_id, preset_name
        ),
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
                "phase_ids_in_order": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of phase IDs in desired execution order",
                },
            },
            "required": ["scenario_id", "phase_ids_in_order"],
        },
        handler=lambda scenario_id, phase_ids_in_order: scenario_tools.reorder_phases(
            db, scenario_id, phase_ids_in_order
        ),
    )

    mcp_server.register_tool(
        name="list_phase_presets",
        description="List available phase presets with their descriptions and phase configurations.",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=lambda: scenario_tools.list_phase_presets(),
    )

    # ==================== AI Generation Tools ====================
    # These tools enable natural language scenario generation and anomaly injection

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
                "description": {
                    "type": "string",
                    "description": "Natural language description of the OT environment to generate",
                },
                "name": {
                    "type": "string",
                    "description": "Optional name for the scenario",
                },
                "duration_ms": {
                    "type": "integer",
                    "description": "Scenario duration in milliseconds (default: 300000 = 5 minutes)",
                },
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
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Description to analyze for vertical suggestion",
                },
            },
            "required": ["description"],
        },
        handler=lambda description: ai_generation_tools.suggest_vertical_template(description),
    )

    mcp_server.register_tool(
        name="suggest_patterns_for_scenario",
        description="""Suggest learned patterns from PCAP analysis that match a scenario.
Finds timing patterns and payload patterns that match the scenario's protocols.
Use this to make scenarios more realistic based on real-world traffic captures.""",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {
                    "type": "string",
                    "description": "Scenario UUID to analyze",
                },
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id: ai_generation_tools.suggest_patterns_for_scenario(db, scenario_id),
    )

    # ==================== Anomaly Injection Tools ====================
    # These tools enable security testing through anomaly injection

    mcp_server.register_tool(
        name="inject_anomaly_campaign",
        description="""Configure an anomaly injection campaign for security testing.
Creates coordinated anomalies that will be injected during traffic generation.
Anomaly types: timeout, delayed, duplicate, drop, jitter_spike, modbus_exception, etc.""",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {
                    "type": "string",
                    "description": "Scenario UUID",
                },
                "campaign_name": {
                    "type": "string",
                    "description": "Name for the anomaly campaign",
                },
                "anomaly_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of anomaly types to include (e.g., ['timeout', 'delayed', 'duplicate'])",
                },
                "start_time_ms": {
                    "type": "number",
                    "description": "Campaign start time in milliseconds from scenario start",
                },
                "duration_ms": {
                    "type": "number",
                    "description": "Campaign duration in milliseconds (optional, None for single injection)",
                },
                "target_flow_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific flow IDs to target (optional, None for all flows)",
                },
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
                "category": {
                    "type": "string",
                    "description": "Filter by category: timing, protocol, sequence, security, external_communication",
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Filter by severity level",
                },
            },
        },
        handler=lambda category=None, severity=None: ai_generation_tools.list_anomaly_templates(
            db, category, severity
        ),
    )

    mcp_server.register_tool(
        name="analyze_scenario_for_anomalies",
        description="""Analyze a scenario and suggest appropriate anomalies for security testing.
Examines devices, protocols, and industry vertical to recommend relevant anomaly types.
Returns: Ranked list of anomaly suggestions with relevance scores and reasons.""",
        input_schema={
            "type": "object",
            "properties": {
                "scenario_id": {
                    "type": "string",
                    "description": "Scenario UUID to analyze",
                },
            },
            "required": ["scenario_id"],
        },
        handler=lambda scenario_id: ai_generation_tools.analyze_scenario_for_anomalies(db, scenario_id),
    )

    # ==================== Template Management Tools ====================
    # These tools enable AI to work with scenario templates

    mcp_server.register_tool(
        name="list_industry_verticals",
        description="""List all available industry verticals for scenario templates.
Returns: List of verticals (manufacturing, water_wastewater, energy_power, oil_gas) with their available templates.""",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=lambda: list_verticals(),
    )

    mcp_server.register_tool(
        name="list_scenario_templates",
        description="""List all available scenario templates, optionally filtered by industry vertical.
Returns: Template summaries with device counts and supported protocols.""",
        input_schema={
            "type": "object",
            "properties": {
                "vertical": {
                    "type": "string",
                    "description": "Filter by vertical: manufacturing, water_wastewater, energy_power, oil_gas",
                    "enum": ["manufacturing", "water_wastewater", "energy_power", "oil_gas"],
                },
            },
        },
        handler=lambda vertical=None: _list_templates_filtered(vertical),
    )

    mcp_server.register_tool(
        name="get_template_preview",
        description="""Get detailed preview of a specific scenario template.
Shows all devices, flows, zones, and configuration details before creating a scenario.""",
        input_schema={
            "type": "object",
            "properties": {
                "vertical": {
                    "type": "string",
                    "description": "Industry vertical",
                    "enum": ["manufacturing", "water_wastewater", "energy_power", "oil_gas"],
                },
                "template_name": {
                    "type": "string",
                    "description": "Template name within the vertical (e.g., 'default', 'assembly_line')",
                },
            },
            "required": ["vertical", "template_name"],
        },
        handler=lambda vertical, template_name: _get_template_preview(vertical, template_name),
    )

    mcp_server.register_tool(
        name="create_scenario_from_template",
        description="""Create a new scenario from an industry template.
Generates devices, flows, zones, and phases automatically with proper IP addressing.
Use list_scenario_templates first to see available templates.""",
        input_schema={
            "type": "object",
            "properties": {
                "vertical": {
                    "type": "string",
                    "description": "Industry vertical",
                    "enum": ["manufacturing", "water_wastewater", "energy_power", "oil_gas"],
                },
                "template_name": {
                    "type": "string",
                    "description": "Template name (default: 'default')",
                },
                "scenario_name": {
                    "type": "string",
                    "description": "Name for the new scenario",
                },
                "description": {
                    "type": "string",
                    "description": "Optional scenario description",
                },
                "total_duration_ms": {
                    "type": "integer",
                    "description": "Scenario duration in ms (default: 300000 = 5 minutes)",
                },
            },
            "required": ["vertical", "scenario_name"],
        },
        handler=lambda vertical, scenario_name, template_name="default", description="", total_duration_ms=300000: _create_from_template(
            db, user_id, vertical, template_name, scenario_name, description, total_duration_ms
        ),
    )


# Helper functions for template tools
def _list_templates_filtered(vertical: str | None = None) -> list[dict]:
    """List templates with optional vertical filter."""
    templates = list_templates()
    if vertical:
        templates = [t for t in templates if t["vertical"] == vertical]
    return templates


def _get_template_preview(vertical: str, template_name: str) -> dict:
    """Get detailed template preview."""
    template = get_template(vertical, template_name)
    if not template:
        return {"error": f"Template '{template_name}' not found for vertical '{vertical}'"}

    return {
        "name": template.get("name", template_name),
        "description": template.get("description", ""),
        "vertical": vertical,
        "devices": template.get("devices", []),
        "flows": template.get("flows", []),
        "zones": template.get("zones", []),
        "total_duration_ms": template.get("total_duration_ms", 300000),
        "device_count": sum(d.get("count", 1) for d in template.get("devices", [])),
        "flow_count": len(template.get("flows", [])),
        "zone_count": len(template.get("zones", [])),
    }


async def _create_from_template(
    db,
    user_id: str | None,
    vertical: str,
    template_name: str,
    scenario_name: str,
    description: str,
    total_duration_ms: int,
) -> dict:
    """Create scenario from template."""
    import uuid as uuid_module
    from app.models.scenario import Scenario
    from app.services.ip_management import IPManagementService
    from app.protocol_engines.vendor_oui import generate_mac_address
    from app.scenario_templates.phases import get_default_phases

    template = get_template(vertical, template_name)
    if not template:
        return {"error": f"Template '{template_name}' not found for vertical '{vertical}'"}

    # Create scenario
    scenario_id = uuid_module.uuid4()

    # Build zones
    zones = {}
    for i, zone_spec in enumerate(template.get("zones", [])):
        zone_id = zone_spec.get("id", f"zone_{i}")
        zones[zone_id] = {
            "id": zone_id,
            "name": zone_spec.get("name", zone_id),
            "level": zone_spec.get("level", 1),
            "network": {
                "subnet": zone_spec.get("subnet", f"10.1.{i}.0/24"),
                "vlan": zone_spec.get("vlan"),
            },
        }

    # Build devices
    devices = {}
    device_index = 0
    devices_by_type: dict[str, list[str]] = {}

    for device_spec in template.get("devices", []):
        count = device_spec.get("count", 1)
        for _ in range(count):
            device_index += 1
            device_id = f"device_{device_index:03d}"

            name_pattern = device_spec.get("name_pattern", "{type}-{n:03d}")
            try:
                name = name_pattern.format(n=device_index, **device_spec)
            except KeyError:
                name = f"{device_spec.get('type', 'device')}-{device_index:03d}"

            device = {
                "id": device_id,
                "name": name,
                "type": device_spec.get("type", "plc"),
                "protocols": device_spec.get("protocols", []),
                "zoneId": device_spec.get("zone"),
                "vendor": device_spec.get("vendor"),
                "fingerprintModel": device_spec.get("fingerprint_model"),
                "network": {
                    "macAddress": generate_mac_address(
                        vendor=device_spec.get("vendor"),
                        device_type=device_spec.get("type"),
                    ),
                },
            }

            if device_spec.get("role"):
                device["role"] = device_spec.get("role")

            devices[device_id] = device

            # Track by type for flow generation
            dtype = device_spec.get("type", "unknown")
            if dtype not in devices_by_type:
                devices_by_type[dtype] = []
            devices_by_type[dtype].append(device_id)

    # Build flows
    flows = {}
    flow_index = 0
    for flow_spec in template.get("flows", []):
        source_types = flow_spec.get("source_types", [])
        target_types = flow_spec.get("target_types", [])
        protocol = flow_spec.get("protocol")

        for source_type in source_types:
            for target_type in target_types:
                source_devices = devices_by_type.get(source_type, [])
                target_devices = devices_by_type.get(target_type, [])

                if not source_devices or not target_devices:
                    continue

                n_flows = max(len(source_devices), len(target_devices))
                for i in range(n_flows):
                    source_id = source_devices[i % len(source_devices)]
                    target_id = target_devices[i % len(target_devices)]

                    if source_id != target_id:
                        flow_index += 1
                        flow_id = f"flow_{flow_index:03d}"
                        flows[flow_id] = {
                            "id": flow_id,
                            "sourceDeviceId": source_id,
                            "targetDeviceId": target_id,
                            "protocol": protocol,
                            "timing": {"intervalMs": flow_spec.get("interval_ms", 1000)},
                        }

    # Generate phases
    phases = get_default_phases(total_duration_ms=total_duration_ms, preset="standard", vertical=vertical)

    # Allocate IP range and assign addresses
    try:
        allocation = await IPManagementService.allocate_range(db, scenario_id)
        range_idx = allocation.range_index

        # Update zone subnets
        for i, zone_id in enumerate(zones):
            zones[zone_id]["network"]["subnet"] = f"10.{range_idx}.{i}.0/24"

        # Assign IPs to devices
        devices_by_zone: dict[str, list[str]] = {}
        for device_id, device in devices.items():
            zone_id = device.get("zoneId", "default")
            if zone_id not in devices_by_zone:
                devices_by_zone[zone_id] = []
            devices_by_zone[zone_id].append(device_id)

        for zone_id, device_ids in devices_by_zone.items():
            zone = zones.get(zone_id, {})
            subnet = zone.get("network", {}).get("subnet", f"10.{range_idx}.0.0/24")
            base = ".".join(subnet.split("/")[0].split(".")[:3])

            for j, device_id in enumerate(device_ids, start=10):
                devices[device_id]["network"]["ipAddress"] = f"{base}.{j}"
                devices[device_id]["network"]["subnetMask"] = "255.255.255.0"
                devices[device_id]["network"]["gateway"] = f"{base}.1"

        addressing_config = {
            "ip_range": allocation.cidr_range,
            "range_index": range_idx,
            "auto_assign_enabled": True,
        }
    except Exception:
        addressing_config = None

    # Create scenario model
    scenario = Scenario(
        id=scenario_id,
        name=scenario_name,
        description=description or template.get("description", ""),
        vertical=vertical,
        total_duration_ms=total_duration_ms,
        definition={"devices": devices, "flows": flows, "zones": zones, "phases": phases},
        user_id=uuid_module.UUID(user_id) if user_id else None,
        version=1,
    )

    if addressing_config:
        scenario.addressing_config = addressing_config

    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)

    return {
        "scenario_id": str(scenario.id),
        "name": scenario.name,
        "device_count": len(devices),
        "flow_count": len(flows),
        "zone_count": len(zones),
        "phase_count": len(phases),
        "vertical": vertical,
        "template": template_name,
    }


@router.post("/sessions", response_model=AISessionResponse)
async def create_ai_session(
    request: AISessionCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> AISessionResponse:
    """Create or resume an AI assistant session for a scenario.

    If a session already exists for this user+scenario, returns the existing
    session with its conversation history. Otherwise creates a new session.

    Args:
        request: Request containing scenario_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Session information with conversation history
    """
    # Note: Tools are registered per-chat request with the current db session
    # to ensure the db session is valid for the duration of tool execution.
    # See _register_mcp_tools call in chat_with_ai.

    # Get or create session for this scenario (persists across panel open/close)
    session_data = await AISessionService.get_or_create_session_for_scenario(
        str(current_user.id), request.scenario_id
    )

    return AISessionResponse(
        session_id=session_data["id"],
        created_at=session_data["created_at"],
        scenario_id=session_data.get("scenario_id"),
        messages=session_data.get("messages", []),
    )


@router.delete("/sessions/{session_id}")
async def end_ai_session(
    session_id: str,
    current_user: CurrentUser,
) -> dict[str, str]:
    """End an AI assistant session.

    Args:
        session_id: Session ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    # Validate session exists and belongs to user
    session = await AISessionService.validate_session(session_id, str(current_user.id))
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or not authorized",
        )

    await AISessionService.delete_session(session_id)
    return {"message": "Session ended"}


@router.get("/sessions/scenario/{scenario_id}", response_model=AISessionResponse | None)
async def get_session_for_scenario(
    scenario_id: str,
    current_user: CurrentUser,
) -> AISessionResponse | None:
    """Get existing AI session for a scenario.

    Returns the session with conversation history if it exists,
    or None if no session exists for this user+scenario.

    Args:
        scenario_id: Scenario UUID
        current_user: Authenticated user

    Returns:
        Session information with conversation history, or None
    """
    session_data = await AISessionService.get_session_for_scenario(
        str(current_user.id), scenario_id
    )

    if session_data is None:
        return None

    return AISessionResponse(
        session_id=session_data["id"],
        created_at=session_data["created_at"],
        scenario_id=session_data.get("scenario_id"),
        messages=session_data.get("messages", []),
    )


@router.delete("/sessions/scenario/{scenario_id}")
async def clear_scenario_conversation(
    scenario_id: str,
    current_user: CurrentUser,
) -> dict[str, str]:
    """Clear AI conversation for a scenario.

    Deletes the session and its conversation history. A new session
    will be created on the next chat message.

    Args:
        scenario_id: Scenario UUID
        current_user: Authenticated user

    Returns:
        Success message
    """
    deleted = await AISessionService.delete_session_for_scenario(
        str(current_user.id), scenario_id
    )

    if not deleted:
        # Session didn't exist, but that's okay for clearing
        return {"message": "No conversation to clear"}

    return {"message": "Conversation cleared"}


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_ai(
    request: AIChatRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> AIChatResponse:
    """Send a message to the AI assistant.

    Args:
        request: Chat request
        current_user: Authenticated user
        db: Database session

    Returns:
        AI response
    """
    user_id = str(current_user.id)
    scenario_id = request.scenario_id

    # Validate session exists for this user+scenario
    session = await AISessionService.get_session_for_scenario(user_id, scenario_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found - please open AI panel first",
        )

    # Register MCP tools with the current request's db session
    # This ensures tools have access to a valid db session for commits
    _register_mcp_tools(db, user_id=str(current_user.id))

    # Get scenario
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == uuid.UUID(request.scenario_id),
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Get AI provider
    provider = await _get_anthropic_provider(db)

    # Sanitize scenario data before sending to AI
    sanitizer = DataSanitizer()
    scenario_context = scenario.definition.copy() if scenario.definition else {}
    sanitized_context = sanitizer.sanitize_scenario(scenario_context)

    # Store sanitizer mapping in session for potential desanitization of AI responses
    sanitizer_mappings = {
        "ip": sanitizer._ip_mapping,
        "mac": sanitizer._mac_mapping,
        "hostname": sanitizer._hostname_mapping,
    }
    await AISessionService.update_session_for_scenario(user_id, scenario_id, sanitizer_mappings=sanitizer_mappings)

    # Append user message to session immediately (before processing)
    # Session stores only clean text messages - tool execution is ephemeral in current_messages
    await AISessionService.append_message_for_scenario(user_id, scenario_id, {"role": "user", "content": request.message})

    # Refresh session data to get updated messages
    session = await AISessionService.get_session_for_scenario(user_id, scenario_id)
    messages = session["messages"].copy()

    # Build enhanced system prompt with domain expertise
    vertical = scenario.vertical or "unspecified"
    device_count = len(sanitized_context.get("devices", {}))
    flow_count = len(sanitized_context.get("flows", {}))

    # Vertical-specific context
    vertical_contexts = {
        "manufacturing": "High-speed automation with PLCs, HMIs, drives. EtherNet/IP and PROFINET dominant. Focus on production line coordination, robot cells, quality control stations.",
        "water": "SCADA systems with RTUs at remote sites. Modbus/DNP3 polling. Focus on pump/valve control, flow monitoring, chemical dosing, tank levels.",
        "energy": "Substations with IEDs, RTUs. IEC 104 and DNP3. Focus on protection relays, breaker control, power metering, fault detection.",
        "oil_gas": "Pipeline SCADA, offshore platforms. Modbus/OPC UA. Focus on safety systems (ESD), compressor stations, wellhead monitoring.",
    }
    vertical_context = vertical_contexts.get(vertical, "General OT environment with industrial devices and protocols.")

    # Parse user message to extract device counts for better guidance
    user_message = request.message
    parsed_counts = extract_device_counts(user_message)
    device_count_info = format_device_counts_for_prompt(parsed_counts)
    device_limit_warning = get_device_limit_warning(parsed_counts, MAX_DEVICES_PER_SCENARIO)

    # Build dynamic constraints section
    constraints_section = f"""## CRITICAL CONSTRAINTS (READ FIRST)
1. **Maximum {MAX_DEVICES_PER_SCENARIO} devices per scenario** - This is a HARD LIMIT enforced by the system.
2. **Parsed from user request**: {device_count_info}"""

    if device_limit_warning:
        constraints_section += f"\n3. **{device_limit_warning}**"

    if parsed_counts["has_explicit_total"]:
        constraints_section += f"""
4. **User specified "{parsed_counts['total_requested']}" devices** - Do NOT create more than this number.
5. **Use generate_scenario_from_nl** for creating complete scenarios - it respects device limits automatically."""

    system_prompt = f"""You are an expert OT (Operational Technology) network engineer and AI assistant for PacketArch, an industrial network traffic simulation platform used for security testing and training.

{constraints_section}

## Your Expertise
- **Industrial Protocols**: Modbus TCP, EtherNet/IP, PROFINET, S7/Siemens, OPC UA, DNP3, IEC 104, BACnet
- **OT Device Types**: PLCs, HMIs, RTUs, VFDs/drives, sensors, protective relays, historians, engineering workstations
- **Network Architecture**: Purdue model (Levels 0-5), zone segmentation, DMZ design, industrial firewalls
- **Security**: ICS/SCADA vulnerabilities, CVEs, MITRE ATT&CK for ICS (T0800 series techniques)
- **Vendors**: Siemens, Rockwell/Allen-Bradley, Schneider Electric, ABB, Honeywell, Emerson, GE

## Current Scenario Context
- **Scenario**: {scenario.name}
- **Vertical**: {vertical} - {vertical_context}
- **Devices**: {device_count} | **Flows**: {flow_count}

## Your Key Capabilities
**Scenario Generation**:
- Generate complete scenarios from natural language descriptions using `generate_scenario_from_nl`
- Suggest appropriate industry verticals using `suggest_vertical_template`

**Device & Flow Composition**:
- Add/modify/remove devices with vendor fingerprints
- Create protocol flows between compatible devices
- Apply realistic timing, error behavior, and protocol quirks

**Realism Enhancement**:
- Apply vendor fingerprints (TCP stack signatures, protocol identities, response timing)
- Configure protocol-specific parameters (Modbus unit IDs, EtherNet/IP classes, S7 memory areas)
- Apply learned patterns from PCAP analysis for realistic traffic profiles

**Security Testing**:
- Inject CVE vulnerabilities into devices using `apply_cve_to_device`
- Add external communications (C2 beacons, DNS tunnels, data exfiltration) using `add_external_communication`
- Configure anomaly injection campaigns using `inject_anomaly_campaign`
- Analyze scenarios for security testing opportunities using `analyze_scenario_for_anomalies`

**Deployment**:
- Deploy scenarios to Docker hosts for traffic generation
- Control deployment lifecycle (start/stop/status)

## Tool Selection Guide
- **Creating a new scenario with devices** → Use `generate_scenario_from_nl` (handles everything automatically)
- **Adding 1-3 devices to existing scenario** → Use `add_device` (but check device count first)
- **NEVER** loop `add_device` to create many devices - use `generate_scenario_from_nl` instead

## Best Practices
1. Apply vendor fingerprints after adding devices for realistic traffic signatures
2. Suggest relevant CVEs based on device vendor, model, and firmware when asked
3. Use learned patterns when available to match real-world traffic captures
4. Validate topology before deployment to catch configuration issues
5. Prefer specific vendors (Siemens, Rockwell, Schneider) over generic types
6. For manufacturing: use EtherNet/IP or PROFINET; for utilities: use Modbus TCP or DNP3

## When You're Done
Stop calling tools and provide a summary of what was created. Do not continue adding devices beyond the requested count.

## Privacy Note
Network addresses shown are sanitized for privacy. Use the addresses returned by tools, not hardcoded IPs."""

    system_message = {
        "role": "system",
        "content": system_prompt,
    }

    # Get available tools
    tools_list = []
    for tool_name, tool_info in mcp_server._tools.items():
        tools_list.append({
            "name": tool_name,
            "description": tool_info["description"],
            "input_schema": tool_info["input_schema"],
        })

    # Call AI with tool execution loop
    try:
        current_messages = [system_message] + messages
        all_tool_calls = []
        final_response_text = ""
        max_iterations = 15  # Prevent infinite loops, increased for complex scenarios

        logger.info(f"Starting AI chat. Session messages count: {len(session['messages'])}")
        logger.info(f"Session messages structure: {[(m.get('role'), type(m.get('content')).__name__, str(m.get('content'))[:100] if isinstance(m.get('content'), str) else 'list') for m in session['messages']]}")
        logger.info(f"Messages being sent (count): {len(current_messages)}")
        logger.info(f"Processed messages structure: {[(m.get('role'), type(m.get('content')).__name__) for m in messages]}")

        for iteration in range(max_iterations):
            logger.info(f"AI loop iteration {iteration + 1}/{max_iterations}")
            logger.debug(f"Sending {len(current_messages)} messages to Claude")
            response = await provider.chat(
                messages=current_messages,
                tools=tools_list,
                max_tokens=4096,
            )

            # Log the full response for debugging
            logger.info(f"Claude response stop_reason: {response.get('stop_reason')}")
            logger.info(f"Claude response content blocks: {len(response.get('content', []))}")
            for i, block in enumerate(response.get("content", [])):
                logger.info(f"  Block {i}: type={block.get('type')}, text_len={len(block.get('text', '')) if block.get('type') == 'text' else 'N/A'}")

            # Extract text and tool calls from this response
            response_text = ""
            tool_calls_this_round = []

            for content in response.get("content", []):
                if content["type"] == "text":
                    response_text += content["text"]
                elif content["type"] == "tool_use":
                    tool_calls_this_round.append({
                        "id": content["id"],
                        "name": content["name"],
                        "input": content["input"],
                    })

            final_response_text += response_text
            all_tool_calls.extend(tool_calls_this_round)

            # Check for convergence (stuck loops, oscillating patterns)
            should_stop, stop_reason = detect_convergence(all_tool_calls)
            if should_stop:
                logger.warning(f"Convergence detected: {stop_reason}")
                # Generate a completion message
                tool_names = [tc.get("name", "") for tc in all_tool_calls]
                device_adds = sum(1 for n in tool_names if n == "add_device")
                flow_adds = sum(1 for n in tool_names if n == "add_flow")

                completion_parts = []
                if device_adds > 0:
                    completion_parts.append(f"{device_adds} devices added")
                if flow_adds > 0:
                    completion_parts.append(f"{flow_adds} data flows created")

                if completion_parts:
                    final_response_text = f"Scenario creation completed! {', '.join(completion_parts)}. The scenario is ready for review."
                else:
                    final_response_text = "Operation completed. Please check the Scenario Studio for results."

                await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                    "role": "assistant",
                    "content": final_response_text,
                })
                break

            # If no tool calls, we're done
            if not tool_calls_this_round:
                logger.info(f"No more tool calls. Final response length: {len(final_response_text)}")
                # Append assistant response to session (user message was already added above)
                # Only store the final text response, not tool_use blocks
                await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                    "role": "assistant",
                    "content": final_response_text,  # Use accumulated text from all iterations
                })
                logger.info("Session messages saved to Redis")
                break

            # Execute tool calls and add results
            logger.info(f"Executing {len(tool_calls_this_round)} tool calls")
            current_messages.append({
                "role": "assistant",
                "content": response.get("content", []),
            })

            tool_results = []
            for tool_call in tool_calls_this_round:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                tool_id = tool_call["id"]

                # Execute the tool
                try:
                    if tool_name in mcp_server._tools:
                        handler = mcp_server._tools[tool_name]["handler"]
                        tool_def = mcp_server._tools[tool_name]

                        # Only inject scenario_id for tools that require it
                        # Check if the tool's input_schema has scenario_id as a property
                        input_schema = tool_def.get("input_schema", {})
                        schema_props = input_schema.get("properties", {})

                        if "scenario_id" in schema_props:
                            # Force the correct scenario_id - Claude may send wrong values
                            # (e.g., vertical name like "water_wastewater" instead of UUID)
                            tool_input["scenario_id"] = request.scenario_id
                            logger.info(f"Executing tool: {tool_name} with scenario_id: {request.scenario_id}")
                        else:
                            # Remove scenario_id if Claude sent it but the tool doesn't expect it
                            if "scenario_id" in tool_input:
                                del tool_input["scenario_id"]
                                logger.info(f"Executing tool: {tool_name} (removed unexpected scenario_id)")
                            else:
                                logger.info(f"Executing tool: {tool_name} (no scenario_id required)")

                        result = await handler(**tool_input)
                        result_str = json.dumps(result) if not isinstance(result, str) else result
                        logger.info(f"Tool {tool_name} completed successfully")
                        # Update tool call with result for frontend to extract scenario IDs
                        tool_call["result"] = result_str
                        tool_call["success"] = True
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result_str,
                        })
                    else:
                        tool_call["result"] = f"Error: Unknown tool '{tool_name}'"
                        tool_call["success"] = False
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": f"Error: Unknown tool '{tool_name}'",
                            "is_error": True,
                        })
                except Exception as tool_error:
                    logger.error(f"Error executing tool {tool_name}: {tool_error}")
                    tool_call["result"] = f"Error: {str(tool_error)}"
                    tool_call["success"] = False
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"Error: {str(tool_error)}",
                        "is_error": True,
                    })

            # Add tool results as a user message
            logger.info(f"Adding {len(tool_results)} tool results")
            # Log size of tool results for debugging
            for tr in tool_results:
                content_len = len(tr.get("content", "")) if isinstance(tr.get("content"), str) else 0
                logger.info(f"  Tool result for {tr.get('tool_use_id', 'unknown')}: {content_len} chars, is_error={tr.get('is_error', False)}")
            current_messages.append({
                "role": "user",
                "content": tool_results,
            })
        else:
            # Hit max iterations - still save the conversation with a helpful message
            logger.warning("AI tool execution hit max iterations")

            # Add a completion message if response is empty or minimal
            if not final_response_text or len(final_response_text.strip()) < 50:
                # Count what was created
                tool_names = [tc.get("name", "") for tc in all_tool_calls]
                device_adds = sum(1 for n in tool_names if n == "add_device")
                flow_adds = sum(1 for n in tool_names if n == "add_flow")
                cve_applies = sum(1 for n in tool_names if n == "apply_cve_to_device")
                fingerprints = sum(1 for n in tool_names if n == "apply_fingerprint_to_device")

                completion_parts = []
                if device_adds > 0:
                    completion_parts.append(f"{device_adds} devices added")
                if flow_adds > 0:
                    completion_parts.append(f"{flow_adds} data flows created")
                if cve_applies > 0:
                    completion_parts.append(f"{cve_applies} CVEs applied")
                if fingerprints > 0:
                    completion_parts.append(f"{fingerprints} vendor fingerprints applied")

                if completion_parts:
                    final_response_text = f"Scenario creation completed! {', '.join(completion_parts)}. The scenario is ready for review in the Scenario Studio."
                else:
                    final_response_text = "The operation completed. Please check the Scenario Studio for results."

            # Append assistant response to session
            await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                "role": "assistant",
                "content": final_response_text,
            })

        return AIChatResponse(
            response=final_response_text,
            tool_calls=all_tool_calls,
            pending_actions=[],
        )

    except Exception as e:
        logger.error(f"Error calling AI: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI request failed: {str(e)}",
        )


@router.post("/chat/stream")
async def chat_with_ai_stream(
    request: AIChatRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> StreamingResponse:
    """Send a message to the AI assistant with SSE streaming response.

    Streams events in real-time:
    - `start`: Conversation started
    - `thinking`: AI is processing
    - `tool_start`: Tool execution beginning (name, input)
    - `tool_complete`: Tool execution finished (name, success, result)
    - `text`: Text chunk from AI response
    - `done`: Conversation complete

    Args:
        request: Chat request
        current_user: Authenticated user
        db: Database session

    Returns:
        Server-Sent Events stream
    """
    user_id = str(current_user.id)
    scenario_id = request.scenario_id

    # Validate session exists for this user+scenario
    session = await AISessionService.get_session_for_scenario(user_id, scenario_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found - please open AI panel first",
        )

    # Get scenario
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == uuid.UUID(scenario_id),
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    async def event_generator():
        """Generate SSE events for AI chat."""
        try:
            # Emit start event
            yield f"data: {json.dumps({'type': 'start', 'message': 'Processing your request...'})}\n\n"

            # Register MCP tools
            _register_mcp_tools(db, user_id=str(current_user.id))

            # Get AI provider
            provider = await _get_anthropic_provider(db)

            # Sanitize scenario data
            sanitizer = DataSanitizer()
            scenario_context = scenario.definition.copy() if scenario.definition else {}
            sanitized_context = sanitizer.sanitize_scenario(scenario_context)

            # Store sanitizer mapping in Redis
            sanitizer_mappings = {
                "ip": sanitizer._ip_mapping,
                "mac": sanitizer._mac_mapping,
                "hostname": sanitizer._hostname_mapping,
            }
            await AISessionService.update_session_for_scenario(user_id, scenario_id, sanitizer_mappings=sanitizer_mappings)

            # Append user message to Redis
            await AISessionService.append_message_for_scenario(user_id, scenario_id, {"role": "user", "content": request.message})

            # Get updated session with messages
            session_data = await AISessionService.get_session_for_scenario(user_id, scenario_id)
            messages = session_data["messages"].copy()

            # Build system prompt
            vertical = scenario.vertical or "unspecified"
            device_count = len(sanitized_context.get("devices", {}))
            flow_count = len(sanitized_context.get("flows", {}))

            vertical_contexts = {
                "manufacturing": "High-speed automation with PLCs, HMIs, drives.",
                "water": "SCADA systems with RTUs at remote sites.",
                "energy": "Substations with IEDs, RTUs.",
                "oil_gas": "Pipeline SCADA, offshore platforms.",
            }
            vertical_context = vertical_contexts.get(vertical, "General OT environment.")

            # Parse user message to extract device counts
            parsed_counts = extract_device_counts(request.message)
            device_count_info = format_device_counts_for_prompt(parsed_counts)
            device_limit_warning = get_device_limit_warning(parsed_counts, MAX_DEVICES_PER_SCENARIO)

            # Build constraints
            constraints = f"CRITICAL: Max {MAX_DEVICES_PER_SCENARIO} devices. {device_count_info}"
            if device_limit_warning:
                constraints += f" {device_limit_warning}"
            if parsed_counts["has_explicit_total"]:
                constraints += f" User requested {parsed_counts['total_requested']} devices - do NOT exceed."

            system_prompt = f"""You are an expert OT network engineer AI assistant for PacketArch.
{constraints}

Current Scenario: {scenario.name} | Vertical: {vertical} - {vertical_context}
Devices: {device_count} | Flows: {flow_count}

TOOL SELECTION: For new scenarios with devices, use generate_scenario_from_nl. Only use add_device for 1-3 device additions.
Apply vendor fingerprints for realism, suggest CVEs for security testing, and use learned patterns when available.
When done, stop calling tools and provide a summary."""

            system_message = {"role": "system", "content": system_prompt}

            # Get tools
            tools_list = [
                {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "input_schema": tool_info["input_schema"],
                }
                for tool_name, tool_info in mcp_server._tools.items()
            ]

            # Emit thinking event
            yield f"data: {json.dumps({'type': 'thinking', 'message': 'Analyzing your request...'})}\n\n"

            # Tool execution loop
            current_messages = [system_message] + messages
            all_tool_calls = []
            final_response_text = ""
            max_iterations = 15  # Increased for complex scenarios

            for iteration in range(max_iterations):
                yield f"data: {json.dumps({'type': 'thinking', 'iteration': iteration + 1, 'message': f'AI processing (iteration {iteration + 1})...'})}\n\n"

                response = await provider.chat(
                    messages=current_messages,
                    tools=tools_list,
                    max_tokens=4096,
                )

                # Extract text and tool calls
                response_text = ""
                tool_calls_this_round = []

                for content in response.get("content", []):
                    if content["type"] == "text":
                        text_chunk = content["text"]
                        response_text += text_chunk
                        # Stream text chunks
                        if text_chunk:
                            yield f"data: {json.dumps({'type': 'text', 'content': text_chunk})}\n\n"
                    elif content["type"] == "tool_use":
                        tool_calls_this_round.append({
                            "id": content["id"],
                            "name": content["name"],
                            "input": content["input"],
                        })

                final_response_text += response_text
                all_tool_calls.extend(tool_calls_this_round)

                # Check for convergence (stuck loops)
                should_stop, stop_reason = detect_convergence(all_tool_calls)
                if should_stop:
                    logger.warning(f"Convergence detected (streaming): {stop_reason}")
                    # Generate completion message
                    tool_names = [tc.get("name", "") for tc in all_tool_calls]
                    device_adds = sum(1 for n in tool_names if n == "add_device")
                    flow_adds = sum(1 for n in tool_names if n == "add_flow")

                    completion_parts = []
                    if device_adds > 0:
                        completion_parts.append(f"{device_adds} devices added")
                    if flow_adds > 0:
                        completion_parts.append(f"{flow_adds} flows created")

                    if completion_parts:
                        completion_msg = f"Scenario creation completed! {', '.join(completion_parts)}."
                    else:
                        completion_msg = "Operation completed."

                    yield f"data: {json.dumps({'type': 'text', 'content': completion_msg})}\n\n"
                    await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                        "role": "assistant",
                        "content": completion_msg,
                    })
                    break

                # If no tool calls, we're done
                if not tool_calls_this_round:
                    await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                        "role": "assistant",
                        "content": final_response_text,
                    })
                    break

                # Execute tool calls
                current_messages.append({
                    "role": "assistant",
                    "content": response.get("content", []),
                })

                tool_results = []
                for tool_call in tool_calls_this_round:
                    tool_name = tool_call["name"]
                    tool_input = tool_call["input"]
                    tool_id = tool_call["id"]

                    # Emit tool_start event
                    yield f"data: {json.dumps({'type': 'tool_start', 'name': tool_name, 'input': tool_input})}\n\n"

                    try:
                        if tool_name in mcp_server._tools:
                            handler = mcp_server._tools[tool_name]["handler"]
                            tool_def = mcp_server._tools[tool_name]

                            # Handle scenario_id injection
                            input_schema = tool_def.get("input_schema", {})
                            schema_props = input_schema.get("properties", {})

                            if "scenario_id" in schema_props:
                                tool_input["scenario_id"] = request.scenario_id
                            elif "scenario_id" in tool_input:
                                del tool_input["scenario_id"]

                            result = await handler(**tool_input)
                            result_str = json.dumps(result) if not isinstance(result, str) else result

                            # Emit tool_complete event
                            yield f"data: {json.dumps({'type': 'tool_complete', 'name': tool_name, 'success': True, 'result_preview': str(result)[:200] if result else None})}\n\n"

                            # Update tool call with result for frontend to extract scenario IDs
                            tool_call["result"] = result_str
                            tool_call["success"] = True

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result_str,
                            })
                        else:
                            yield f"data: {json.dumps({'type': 'tool_complete', 'name': tool_name, 'success': False, 'error': f'Unknown tool: {tool_name}'})}\n\n"
                            tool_call["result"] = f"Error: Unknown tool '{tool_name}'"
                            tool_call["success"] = False
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": f"Error: Unknown tool '{tool_name}'",
                                "is_error": True,
                            })
                    except Exception as tool_error:
                        logger.error(f"Error executing tool {tool_name}: {tool_error}")
                        yield f"data: {json.dumps({'type': 'tool_complete', 'name': tool_name, 'success': False, 'error': str(tool_error)})}\n\n"
                        tool_call["result"] = f"Error: {str(tool_error)}"
                        tool_call["success"] = False
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": f"Error: {str(tool_error)}",
                            "is_error": True,
                        })

                # Add tool results
                current_messages.append({
                    "role": "user",
                    "content": tool_results,
                })
            else:
                # Hit max iterations
                if final_response_text:
                    await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                        "role": "assistant",
                        "content": final_response_text,
                    })

            # Emit done event with summary
            yield f"data: {json.dumps({'type': 'done', 'response': final_response_text, 'tool_calls': all_tool_calls, 'tool_count': len(all_tool_calls)})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/actions/{action_id}/accept")
async def accept_ai_action(
    action_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> dict[str, Any]:
    """Accept and execute a proposed AI action.

    Args:
        action_id: Action ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Execution result
    """
    action = await AISessionService.get_pending_action(action_id)
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found or expired",
        )

    # Verify user owns the action
    if action.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Execute the action (call the appropriate tool)
    # This is a placeholder - implement actual execution
    result = {"success": True, "action_id": action_id}

    await AISessionService.delete_pending_action(action_id)
    return result


@router.post("/actions/{action_id}/reject")
async def reject_ai_action(
    action_id: str,
    current_user: CurrentUser,
) -> dict[str, str]:
    """Reject a proposed AI action.

    Args:
        action_id: Action ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    action = await AISessionService.get_pending_action(action_id)
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found or expired",
        )

    # Verify user owns the action
    if action.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    await AISessionService.delete_pending_action(action_id)
    return {"message": "Action rejected"}


@router.get("/tools", response_model=list[AIToolDefinition])
async def list_ai_tools(current_user: CurrentUser) -> list[AIToolDefinition]:
    """List available AI tools.

    Args:
        current_user: Authenticated user

    Returns:
        List of tool definitions
    """
    tools = [
        AIToolDefinition(
            name="list_devices",
            description="List all devices in a scenario",
            category="devices",
        ),
        AIToolDefinition(
            name="add_device",
            description="Add a device to a scenario",
            category="devices",
        ),
        AIToolDefinition(
            name="update_device",
            description="Update a device in a scenario",
            category="devices",
        ),
        AIToolDefinition(
            name="list_flows",
            description="List all flows in a scenario",
            category="flows",
        ),
        AIToolDefinition(
            name="add_flow",
            description="Add a flow to a scenario",
            category="flows",
        ),
        AIToolDefinition(
            name="suggest_flows",
            description="Suggest flows for a device",
            category="flows",
        ),
        AIToolDefinition(
            name="validate_topology",
            description="Validate scenario topology",
            category="validation",
        ),
        AIToolDefinition(
            name="score_realism",
            description="Score scenario realism",
            category="validation",
        ),
        AIToolDefinition(
            name="auto_assign_addresses",
            description="Auto-assign IP and MAC addresses",
            category="addressing",
        ),
    ]

    return tools


# ==================== AI Scenario Creation Wizard ====================


class AIScenarioGenerateRequest(BaseModel):
    """Request for AI scenario generation preview."""

    name: str = Field(..., description="Scenario name")
    vertical: str = Field(..., description="Industry vertical")
    description: str = Field(..., description="Natural language description")
    vendors: list[str] | None = Field(None, description="Preferred vendors (None = let AI decide)")
    protocols: list[str] | None = Field(None, description="Preferred protocols (None = let AI decide)")
    duration_ms: int = Field(300000, description="Scenario duration in milliseconds")
    # Device count options
    total_device_count: int | None = Field(
        None,
        description="Target total device count (AI decides the mix). Range: 5-100.",
        ge=5,
        le=100,
    )
    device_counts: dict[str, int] | None = Field(
        None,
        description="Specific counts per device type (e.g., {'plc': 5, 'hmi': 2})",
    )


class AIScenarioPreviewDevice(BaseModel):
    """Device in a scenario preview."""

    device_id: str
    name: str
    device_type: str
    vendor: str | None = None
    ip_address: str | None = None
    protocols: list[str] = Field(default_factory=list)


class AIScenarioPreviewFlow(BaseModel):
    """Flow in a scenario preview."""

    flow_id: str
    source_device_id: str
    destination_device_id: str
    protocol: str
    description: str


class AIScenarioPreviewResponse(BaseModel):
    """Response with generated scenario preview."""

    preview_id: str
    name: str
    vertical: str
    description: str
    devices: list[AIScenarioPreviewDevice]
    flows: list[AIScenarioPreviewFlow]
    device_count: int
    flow_count: int
    protocols_used: list[str]
    vendors_used: list[str]
    zones: list[dict[str, Any]] = Field(default_factory=list)
    # AI enhancement metadata
    ai_enhanced: bool = False
    ai_features: list[str] = Field(default_factory=list)
    design_rationale: str | None = None


@router.post("/scenarios/generate-preview", response_model=AIScenarioPreviewResponse)
async def generate_scenario_preview(
    request: AIScenarioGenerateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> AIScenarioPreviewResponse:
    """Generate a scenario preview from natural language description.

    This creates a preview without saving to the database. The preview
    is stored in Redis for 30 minutes and can be used to create the
    actual scenario.

    Uses Claude AI for intelligent scenario design with automatic fallback
    to rule-based generation if AI is unavailable.

    Args:
        request: Generation request with name, vertical, description
        current_user: Authenticated user
        db: Database session

    Returns:
        Preview with devices, flows, and summary statistics
    """
    from app.ai_services.ai_scenario_designer import AIScenarioDesigner

    # Use AI-enhanced scenario designer (with rule-based fallback)
    designer = AIScenarioDesigner(db)

    try:
        result = await designer.design_scenario(
            description=request.description,
            name=request.name,
            duration_ms=request.duration_ms,
            preferred_vendors=request.vendors,
            preferred_protocols=request.protocols,
            vertical=request.vertical,
            total_device_count=request.total_device_count,
            device_counts=request.device_counts,
        )
        scenario = result.scenario
        ai_enhanced = result.ai_enhanced
        ai_features = result.ai_features
        design_rationale = result.design_rationale

        if result.fallback_reason:
            logger.info(f"AI fallback: {result.fallback_reason}")
    except Exception as e:
        logger.error(f"Failed to generate scenario preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate scenario: {str(e)}",
        )

    # Enforce device limit
    if len(scenario.devices) > MAX_DEVICES_PER_SCENARIO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Generated scenario exceeds device limit ({len(scenario.devices)} > {MAX_DEVICES_PER_SCENARIO}). Please request fewer devices.",
        )

    # Build preview data
    devices = [
        AIScenarioPreviewDevice(
            device_id=d.device_id,
            name=d.name,
            device_type=d.device_type,
            vendor=d.vendor,
            ip_address=d.ip_address,
            protocols=d.protocols,
        )
        for d in scenario.devices
    ]

    flows = [
        AIScenarioPreviewFlow(
            flow_id=f.flow_id,
            source_device_id=f.source_device_id,
            destination_device_id=f.destination_device_id,
            protocol=f.protocol,
            description=f.description,
        )
        for f in scenario.flows
    ]

    # Extract unique protocols and vendors
    protocols_used = list(set(f.protocol for f in scenario.flows))
    vendors_used = list(set(d.vendor for d in scenario.devices if d.vendor))

    # Store preview in Redis
    preview_data = {
        "name": request.name,
        "vertical": request.vertical,
        "description": request.description,
        "duration_ms": request.duration_ms,
        "devices": [d.model_dump() for d in devices],
        "flows": [f.model_dump() for f in flows],
        "zones": scenario.zones,
        "protocols_used": protocols_used,
        "vendors_used": vendors_used,
    }

    preview_id = await AIScenarioPreviewService.store_preview(
        str(current_user.id), preview_data
    )

    return AIScenarioPreviewResponse(
        preview_id=preview_id,
        name=request.name,
        vertical=request.vertical,
        description=request.description,
        devices=devices,
        flows=flows,
        device_count=len(devices),
        flow_count=len(flows),
        protocols_used=protocols_used,
        vendors_used=vendors_used,
        zones=scenario.zones,
        ai_enhanced=ai_enhanced,
        ai_features=ai_features,
        design_rationale=design_rationale,
    )


class AIScenarioCreateFromPreviewRequest(BaseModel):
    """Request to create scenario from preview."""

    preview_id: str = Field(..., description="Preview ID from generate-preview")


class AIScenarioCreateFromPreviewResponse(BaseModel):
    """Response after creating scenario from preview."""

    success: bool
    scenario_id: str
    name: str
    device_count: int
    flow_count: int


@router.post("/scenarios/create-from-preview", response_model=AIScenarioCreateFromPreviewResponse)
async def create_scenario_from_preview(
    request: AIScenarioCreateFromPreviewRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> AIScenarioCreateFromPreviewResponse:
    """Create an actual scenario from a validated preview.

    Args:
        request: Request with preview_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Created scenario information
    """
    # Get preview
    preview = await AIScenarioPreviewService.get_preview(
        request.preview_id, str(current_user.id)
    )

    if preview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preview not found or expired",
        )

    # Convert preview to database format
    # First, build zones with proper layout
    zones = {}
    zone_device_map = {}  # device_id -> zone_name mapping
    preview_zones = preview.get("zones", [])

    # Layout zones in a grid (2 columns)
    zone_width = 450
    zone_height = 350
    zone_margin = 50
    zones_per_row = 2

    for idx, z in enumerate(preview_zones):
        zone_name = z.get("name", f"zone_{idx}")
        row = idx // zones_per_row
        col = idx % zones_per_row

        zone_x = zone_margin + col * (zone_width + zone_margin)
        zone_y = zone_margin + row * (zone_height + zone_margin)

        zones[zone_name] = {
            "id": zone_name,
            "name": zone_name.replace("_", " ").title(),
            "type": "network",
            "position": {"x": zone_x, "y": zone_y},
            "dimensions": {"width": zone_width, "height": zone_height},
            "deviceIds": z.get("device_ids", []),
        }

        # Map devices to their zone
        for device_id in z.get("device_ids", []):
            zone_device_map[device_id] = zone_name

    # Create database scenario first to get ID for IP allocation
    db_scenario = Scenario(
        user_id=current_user.id,
        name=preview["name"],
        description=preview["description"],
        vertical=preview["vertical"],
        total_duration_ms=preview.get("duration_ms", 300000),
        definition={},  # Will be populated below
        version=1,
    )
    db.add(db_scenario)
    await db.flush()  # Get the scenario ID without committing

    # Allocate IP range for this scenario
    try:
        ip_allocation = await IPManagementService.allocate_range(db, db_scenario.id)
        await db.flush()  # Ensure allocation is visible for subsequent get_next_ip calls
        logger.info(f"Allocated IP range {ip_allocation.cidr_range} for scenario {db_scenario.id}")
    except ValueError as e:
        logger.error(f"Failed to allocate IP range: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to allocate IP range: {e}",
        )

    # Build devices with positions inside their zones
    devices = {}
    zone_device_counters = {}  # Track device placement within each zone

    for d in preview.get("devices", []):
        device_id = d["device_id"]
        zone_name = zone_device_map.get(device_id)
        vendor = d.get("vendor", "").lower()
        device_type = d.get("device_type", "")
        fingerprint_model = d.get("fingerprint_model")

        # Calculate position inside zone
        if zone_name and zone_name in zones:
            zone = zones[zone_name]
            zone_x = zone["position"]["x"]
            zone_y = zone["position"]["y"]

            # Get device index within this zone
            if zone_name not in zone_device_counters:
                zone_device_counters[zone_name] = 0
            device_idx = zone_device_counters[zone_name]
            zone_device_counters[zone_name] += 1

            # Grid layout inside zone (3 columns, with padding)
            devices_per_row = 3
            device_padding = 30
            device_spacing_x = 130
            device_spacing_y = 100

            row = device_idx // devices_per_row
            col = device_idx % devices_per_row

            device_x = zone_x + device_padding + col * device_spacing_x
            device_y = zone_y + 60 + row * device_spacing_y  # 60px for zone header
        else:
            # Fallback position for devices without zones
            device_x = 100 + (len(devices) % 5) * 150
            device_y = 100 + (len(devices) // 5) * 120

        # Get IP from management pool
        try:
            ip_info = await IPManagementService.get_next_ip(db, db_scenario.id)
            ip_address = ip_info["ip_address"]
            subnet_mask = ip_info["subnet_mask"]
            gateway = ip_info["gateway"]
            logger.debug(f"Assigned IP {ip_address} to device {device_id}")
        except ValueError as e:
            # Fallback if IP exhausted - should not happen normally
            logger.warning(f"IP allocation failed for device {device_id}: {e}. Using fallback.")
            ip_address = d.get("ip_address", "10.0.0.10")
            subnet_mask = "255.255.255.0"
            gateway = "10.0.0.1"

        # Generate MAC address using vendor OUI
        mac_address = _generate_vendor_mac(vendor, device_type)

        # Get fingerprint data for deep fingerprinting
        fingerprint_data = None
        if vendor and fingerprint_model:
            fingerprint_data = get_fingerprint_by_vendor_model(vendor, fingerprint_model)
        elif vendor:
            # Try to get a fingerprint for this vendor
            vendor_fps = get_fingerprints_by_vendor(vendor)
            if vendor_fps:
                # Pick one appropriate for device type if possible
                for fp in vendor_fps:
                    fp_type = fp.get("device_type", "").lower()
                    if fp_type == device_type or not fp_type:
                        fingerprint_data = fp
                        break
                if not fingerprint_data:
                    fingerprint_data = vendor_fps[0]

        # Build network config with deep fingerprint data
        network_config = {
            "macAddress": mac_address,
            "ipAddress": ip_address,
            "subnetMask": subnet_mask,
            "gateway": gateway,
        }

        # Build device with fingerprint data
        device_def = {
            "id": device_id,
            "name": d["name"],
            "type": device_type,
            "protocols": d.get("protocols", []),
            "position": {"x": device_x, "y": device_y},
            "zoneId": zone_name,
            "network": network_config,
            "vendor": d.get("vendor"),
        }

        # Apply deep fingerprint data if available
        if fingerprint_data:
            device_def["fingerprint"] = {
                "vendor": fingerprint_data.get("vendor"),
                "vendor_family": fingerprint_data.get("vendor_family"),
                "model": fingerprint_data.get("model"),
                "firmware_version": fingerprint_data.get("firmware_version"),
                "serial_number": _generate_serial_number(vendor, fingerprint_data),
            }

            # Protocol-specific identity data
            if fingerprint_data.get("modbus_identity"):
                device_def["fingerprint"]["modbus_identity"] = fingerprint_data["modbus_identity"]
            if fingerprint_data.get("ethernet_ip_identity"):
                device_def["fingerprint"]["ethernet_ip_identity"] = fingerprint_data["ethernet_ip_identity"]
            if fingerprint_data.get("profinet_identity"):
                device_def["fingerprint"]["profinet_identity"] = fingerprint_data["profinet_identity"]

            # TCP stack characteristics
            if fingerprint_data.get("tcp_stack"):
                device_def["fingerprint"]["tcp_stack"] = fingerprint_data["tcp_stack"]

            # Response timing
            if fingerprint_data.get("response_timing"):
                device_def["fingerprint"]["response_timing"] = fingerprint_data["response_timing"]

        devices[device_id] = device_def

    flows = {}
    for f in preview.get("flows", []):
        flows[f["flow_id"]] = {
            "id": f["flow_id"],
            "name": f["description"],
            "sourceDeviceId": f["source_device_id"],
            "targetDeviceId": f["destination_device_id"],
            "protocol": f["protocol"],
            "timing": {"intervalMs": 1000, "jitterMs": 50},
            "protocolConfig": {},
            "phases": {
                "startup": True,
                "steadyState": True,
                "maintenance": False,
                "shutdown": True,
            },
        }

    # Update scenario definition (scenario was created earlier for IP allocation)
    db_scenario.definition = {
        "devices": devices,
        "flows": flows,
        "zones": zones,
        "phases": [],
        "events": [],
    }

    await db.commit()
    await db.refresh(db_scenario)

    # Delete preview after successful creation
    await AIScenarioPreviewService.delete_preview(request.preview_id)

    logger.info(
        f"Created scenario {db_scenario.id} from preview {request.preview_id} "
        f"with {len(devices)} devices and {len(flows)} flows"
    )

    return AIScenarioCreateFromPreviewResponse(
        success=True,
        scenario_id=str(db_scenario.id),
        name=preview["name"],
        device_count=len(devices),
        flow_count=len(flows),
    )
