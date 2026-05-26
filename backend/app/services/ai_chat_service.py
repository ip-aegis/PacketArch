# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""AI chat service - convergence detection, system prompt building, and chat loop logic.

This module contains the core chat processing pipeline extracted from ai.py routes.
"""

import json
import logging
import random
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp_server.ai_providers import AIProvider, AIProviderFactory, AITask
from app.mcp_server.server import mcp_server
from app.core.constants import MAX_DEVICES_PER_SCENARIO
from app.services.ai_session_service import AISessionService

logger = logging.getLogger(__name__)


def generate_serial_number(vendor: str, fingerprint_data: dict) -> str:
    """Generate a realistic serial number based on vendor patterns.

    NOTE: This function generates random serial numbers for display purposes.
    For protocol-specific serial numbers used by Cyber Vision, use
    enrich_device_serial_numbers() which uses deterministic generation.

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
    1. ``add_device`` called 5+ times consecutively = stuck loop (the
       model should be using ``generate_scenario_from_nl`` for bulk
       device creation; we intervene to force the right tool).
    2. Any tool called 5+ times consecutively where the inputs show
       little variety (≤2 unique input signatures) = stuck loop.
       Naturally-iterative tools — ``remove_device``, ``remove_flow``,
       ``apply_cve_to_device``, etc. — legitimately fire many times
       in a row with distinct inputs; that pattern is progress, not a
       loop, so we allow it.
    3. Same tool + identical parameters 3+ times consecutively = exact
       duplicate loop.
    4. Oscillating A-B-A-B-A-B pattern = ping-pong loop.
    """
    if len(tool_calls_history) < 3:
        return False, ""

    def _signature(tc: dict) -> str:
        try:
            return json.dumps(tc.get("input", {}), sort_keys=True)
        except (TypeError, ValueError):
            return str(tc.get("input", {}))

    # Rule 1: special-case add_device — the model should pick
    # generate_scenario_from_nl for bulk, so a 5-call streak is a
    # tool-selection bug worth interrupting.
    last_5_names = [tc.get("name") for tc in tool_calls_history[-5:]]
    if (
        len(last_5_names) == 5
        and len(set(last_5_names)) == 1
        and last_5_names[0] == "add_device"
    ):
        return True, "Detected add_device loop - model should be using generate_scenario_from_nl"

    # Rule 2: 5 consecutive calls to the same tool where the inputs
    # don't show variety. Bulk operations like remove_device produce
    # 5 unique signatures (different device_id each call) and slip
    # through this check; truly stuck loops hit the ≤2-unique guard.
    if len(last_5_names) == 5 and len(set(last_5_names)) == 1:
        sigs = {_signature(tc) for tc in tool_calls_history[-5:]}
        if len(sigs) <= 2:
            return True, (
                f"Detected {last_5_names[0]} loop - 5 consecutive calls with "
                f"only {len(sigs)} unique input(s)"
            )

    # Rule 3: Same tool + identical parameters 3+ times consecutively
    if len(tool_calls_history) >= 3:
        last_3 = tool_calls_history[-3:]
        sigs = []
        for tc in last_3:
            sigs.append((tc.get("name", ""), _signature(tc)))
        if len(set(sigs)) == 1:
            return True, f"Detected exact duplicate loop: {sigs[0][0]} called 3 times with identical parameters"

    # Rule 4: Oscillating patterns (A, B, A, B, A, B)
    if len(tool_calls_history) >= 6:
        last_6_names = [tc.get("name") for tc in tool_calls_history[-6:]]
        if (
            last_6_names[0] == last_6_names[2] == last_6_names[4]
            and last_6_names[1] == last_6_names[3] == last_6_names[5]
            and last_6_names[0] != last_6_names[1]
        ):
            return True, f"Detected oscillating pattern between {last_6_names[0]} and {last_6_names[1]}"

    return False, ""


async def get_ai_provider(
    db: AsyncSession,
    task: AITask | None = None,
) -> AIProvider:
    """Get configured AI provider for ``task``.

    The user picks a provider in Settings; this function resolves that
    provider and asks the model router to pick the best model for the
    given :class:`AITask`. Callers should pass the task they're about to
    execute — omitting it falls back to the provider's flagship.

    Args:
        db: Database session
        task: Which workload the provider will run. Drives model choice.

    Returns:
        Configured AI provider

    Raises:
        HTTPException: If API key not configured or provider unknown
    """
    try:
        return await AIProviderFactory.create(db, task=task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


def build_system_prompt(
    scenario_name: str,
    vertical: str,
    device_count: int,
    flow_count: int,
    device_count_info: str,
    device_limit_warning: str | None,
    parsed_counts: dict,
    compact: bool = False,
) -> str:
    """Build the AI system prompt with scenario context.

    Args:
        scenario_name: Name of the current scenario
        vertical: Industry vertical
        device_count: Number of devices in the scenario
        flow_count: Number of flows in the scenario
        device_count_info: Formatted device count info string
        device_limit_warning: Warning about device limits (or None)
        parsed_counts: Parsed device counts from user message
        compact: If True, return a compact version (for streaming)

    Returns:
        System prompt string
    """
    # Vertical-specific context
    vertical_contexts = {
        "manufacturing": "High-speed automation with PLCs, HMIs, drives. EtherNet/IP and PROFINET dominant. Focus on production line coordination, robot cells, quality control stations.",
        "water": "SCADA systems with RTUs at remote sites. Modbus/DNP3 polling. Focus on pump/valve control, flow monitoring, chemical dosing, tank levels.",
        "energy": "Substations with IEDs, RTUs. IEC 104 and DNP3. Focus on protection relays, breaker control, power metering, fault detection.",
        "oil_gas": "Pipeline SCADA, offshore platforms. Modbus/OPC UA. Focus on safety systems (ESD), compressor stations, wellhead monitoring.",
        "building_automation": "Building management systems with BACnet/IP controllers, Modbus TCP meters, HVAC units, lighting controllers. Focus on HVAC optimization, energy metering, access control.",
        "transportation": "ITS infrastructure with SNMP/NTCIP traffic controllers, DMS signs, radar/video detectors, weather stations, cameras. Focus on signal coordination, incident detection, traveler information.",
    }

    if compact:
        vertical_context = vertical_contexts.get(vertical, "General OT environment.")

        constraints = f"CRITICAL: Max {MAX_DEVICES_PER_SCENARIO} devices. {device_count_info}"
        if device_limit_warning:
            constraints += f" {device_limit_warning}"
        if parsed_counts["has_explicit_total"]:
            constraints += f" User requested {parsed_counts['total_requested']} devices - do NOT exceed."

        return f"""You are an expert OT network engineer AI assistant for PacketArch.
{constraints}

Current Scenario: {scenario_name} | Vertical: {vertical} - {vertical_context}
Devices: {device_count} | Flows: {flow_count}

Scenario id is auto-injected on every tool call — NEVER ask the user for it.
TOOL SELECTION: For new scenarios with devices, use generate_scenario_from_nl. Only use add_device for 1-3 device additions.
Apply vendor fingerprints for realism and suggest CVEs for security testing.
When done, stop calling tools and provide a summary."""

    vertical_context = vertical_contexts.get(vertical, "General OT environment with industrial devices and protocols.")

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

    return f"""You are an expert OT (Operational Technology) network engineer and AI assistant for PacketArch, an industrial network traffic simulation platform used for security testing and training.

{constraints_section}

## Your Expertise
- **Industrial Protocols**:
  - Core: Modbus TCP/RTU, EtherNet/IP, PROFINET, S7comm, OPC UA
  - SCADA/Utility: DNP3, IEC 104, IEC 61850 (MMS/GOOSE/SV)
  - Building Automation: BACnet/IP
  - Network: SNMP/NTCIP, LLDP, CDP
  - Vendor-Specific: PCCC (Allen-Bradley), Codesys, FINS (Omron), SLMP (Mitsubishi), EtherCAT (Beckhoff)
  - DCS: Emerson DeltaV, Honeywell Experion, Yokogawa Vnet/IP, Schneider Triconex
  - Specialized: FANUC FOCAS, WMI
- **OT Device Types**: PLCs, HMIs, RTUs, VFDs/drives, sensors, protective relays, IEDs, historians, engineering workstations, DCS controllers, CNCs, BMS controllers
- **Network Architecture**: Purdue model (Levels 0-5), zone segmentation, DMZ design, industrial firewalls
- **Security**: ICS/SCADA vulnerabilities, CVEs, MITRE ATT&CK for ICS (T0800 series techniques)
- **Vendors**: Siemens, Rockwell/Allen-Bradley, Schneider Electric, ABB, Honeywell, Emerson, GE, Omron, Mitsubishi, Beckhoff, FANUC, Yokogawa

## Protocol Selection by Vertical
- **Manufacturing**: EtherNet/IP, PROFINET, Modbus TCP, PCCC (Rockwell legacy), Codesys, EtherCAT (motion control)
- **Process Industries**: DCS (DeltaV, Experion), OPC UA, Modbus TCP
- **Power/Energy**: IEC 61850 (substations), IEC 104, DNP3
- **Building Automation**: BACnet/IP, Modbus TCP
- **Transportation/ITS**: SNMP/NTCIP

## Current Scenario Context
- **Scenario**: {scenario_name}
- **Vertical**: {vertical} - {vertical_context}
- **Devices**: {device_count} | **Flows**: {flow_count}

> Every tool you can call already operates on this scenario — the
> scenario identifier is injected automatically server-side. **Never
> ask the user for a scenario ID or UUID; just call the tool.**

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

**Security Testing**:
- Inject CVE vulnerabilities into devices using `apply_cve_to_device`
- Add external communications (C2 beacons, DNS tunnels, data exfiltration) using `add_external_communication`
- Configure anomaly injection campaigns using `inject_anomaly_campaign`
- Analyze scenarios for security testing opportunities using `analyze_scenario_for_anomalies`

**Deployment**:
- Deploy scenarios to Docker hosts for traffic generation
- Control deployment lifecycle (start/stop/status)

## Tool Selection Guide
- **Creating a new scenario with devices** -> Use `generate_scenario_from_nl` (handles everything automatically)
- **Adding 1-3 devices to existing scenario** -> Use `add_device` (but check device count first)
- **NEVER** loop `add_device` to create many devices - use `generate_scenario_from_nl` instead

## Best Practices
1. Apply vendor fingerprints after adding devices for realistic traffic signatures
2. Suggest relevant CVEs based on device vendor, model, and firmware when asked
3. Validate topology before deployment to catch configuration issues
4. Prefer specific vendors (Siemens, Rockwell, Schneider, Omron, Mitsubishi) over generic types
5. Protocol selection by context:
   - Manufacturing: EtherNet/IP (Rockwell), PROFINET (Siemens), PCCC (legacy AB), Codesys (WAGO/Beckhoff)
   - Utilities (Water/Gas): Modbus TCP, DNP3
   - Power substations: IEC 61850 (protection relays), IEC 104 (telecontrol)
   - Buildings: BACnet/IP (HVAC), Modbus TCP (meters)
   - Process/Oil&Gas: DCS protocols, OPC UA, Modbus TCP
   - Japanese/Asian PLCs: FINS (Omron), SLMP (Mitsubishi)
   - Transportation/ITS: SNMP/NTCIP (traffic controllers, DMS signs)

## When You're Done
Stop calling tools and provide a summary of what was created. Do not continue adding devices beyond the requested count.

## Privacy Note
Network addresses shown are sanitized for privacy. Use the addresses returned by tools, not hardcoded IPs."""


def build_completion_message(all_tool_calls: list[dict]) -> str:
    """Build a completion message based on tool calls executed.

    Args:
        all_tool_calls: List of tool calls that were executed

    Returns:
        Completion message string
    """
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
        return f"Scenario creation completed! {', '.join(completion_parts)}. The scenario is ready for review in the Scenario Studio."
    else:
        return "The operation completed. Please check the Scenario Studio for results."


async def execute_tool_call(
    tool_name: str,
    tool_input: dict,
    tool_id: str,
    scenario_id: str,
) -> dict:
    """Execute a single MCP tool call.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Input arguments for the tool
        tool_id: Unique tool call ID
        scenario_id: Current scenario ID (for injection)

    Returns:
        Tool result dict with type, tool_use_id, content, and optional is_error
    """
    try:
        if tool_name in mcp_server._tools:
            handler = mcp_server._tools[tool_name]["handler"]
            tool_def = mcp_server._tools[tool_name]

            # Only inject scenario_id for tools that require it
            input_schema = tool_def.get("input_schema", {})
            schema_props = input_schema.get("properties", {})

            if "scenario_id" in schema_props:
                tool_input["scenario_id"] = scenario_id
                logger.info(f"Executing tool: {tool_name} with scenario_id: {scenario_id}")
            else:
                if "scenario_id" in tool_input:
                    del tool_input["scenario_id"]
                    logger.info(f"Executing tool: {tool_name} (removed unexpected scenario_id)")
                else:
                    logger.info(f"Executing tool: {tool_name} (no scenario_id required)")

            result = await handler(**tool_input)
            result_str = json.dumps(result) if not isinstance(result, str) else result
            logger.info(f"Tool {tool_name} completed successfully")

            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_str,
                "success": True,
            }
        else:
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Error: Unknown tool '{tool_name}'",
                "is_error": True,
                "success": False,
            }
    except Exception as tool_error:
        logger.error(f"Error executing tool {tool_name}: {tool_error}")
        return {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": f"Error: {str(tool_error)}",
            "is_error": True,
            "success": False,
        }
