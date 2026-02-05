"""AI-powered scenario designer using Claude for intelligent generation.

This module provides AI-enhanced scenario generation that uses Claude to:
- Select appropriate vendors and protocols based on scenario context
- Generate descriptive, contextual device names
- Design realistic communication flow patterns
- Create meaningful zone names
- Optimize poll intervals by data type
"""

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY

from app.ai_services.scenario_generator import (
    GeneratedDevice,
    GeneratedFlow,
    GeneratedScenario,
    ScenarioGenerator,
    VERTICAL_TEMPLATES,
    DEVICE_PROTOCOL_MAP,
)
from app.mcp_server.ai_providers import AIProviderFactory
from app.protocol_engines.vendor_oui import generate_mac_address
from app.services.device_templates import (
    get_all_fingerprints,
    get_fingerprint_by_vendor_model,
)

logger = logging.getLogger(__name__)


# ==================== Pydantic Models for AI Response ====================


class AIZoneDesign(BaseModel):
    """Zone design from AI."""
    id: str
    name: str
    description: str | None = None
    subnet_offset: int | None = None  # 0-99 for third octet in /24 subnet
    level: int | None = None          # Purdue model level (0-5)
    vlan: int | None = None           # VLAN ID


class AIDeviceDesign(BaseModel):
    """Device design from AI."""
    name: str
    device_type: str
    vendor: str | None = None
    fingerprint_model: str | None = None
    zone_id: str | None = None
    role: str | None = None
    protocols: list[str] = Field(default_factory=lambda: ["modbus_tcp"])

    @field_validator('name')
    @classmethod
    def clean_name(cls, v: str) -> str:
        """Ensure name is clean and consistent."""
        # Replace spaces and hyphens with underscores
        cleaned = re.sub(r'[\s\-]+', '_', v)
        # Remove any non-alphanumeric characters except underscores
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '', cleaned)
        return cleaned

    @field_validator('device_type')
    @classmethod
    def normalize_device_type(cls, v: str) -> str:
        """Normalize device type to lowercase."""
        return v.lower()


class AIFlowDesign(BaseModel):
    """Flow design from AI."""
    source_name: str
    target_name: str
    protocol: str = "modbus_tcp"
    description: str = ""
    poll_interval_ms: int = 1000
    pattern: str = "polling"


class AIScenarioDesign(BaseModel):
    """Complete scenario design from AI."""
    vertical: str = "manufacturing"
    recommended_vendors: list[str] = Field(default_factory=list)
    recommended_protocols: list[str] = Field(default_factory=list)
    zones: list[AIZoneDesign] = Field(default_factory=list)
    devices: list[AIDeviceDesign] = Field(default_factory=list)
    flows: list[AIFlowDesign] = Field(default_factory=list)
    design_rationale: str | None = None


# ==================== Result Dataclass ====================


@dataclass
class AIDesignResult:
    """Result from AI scenario design."""
    scenario: GeneratedScenario
    ai_enhanced: bool
    ai_features: list[str] = field(default_factory=list)
    fallback_reason: str | None = None
    design_rationale: str | None = None


# ==================== AI Scenario Designer ====================


class AIScenarioDesigner:
    """Scenario designer that uses Claude AI for intelligent generation.

    This designer:
    1. Attempts to use Claude AI for context-aware scenario design
    2. Falls back to rule-based ScenarioGenerator if AI fails
    3. Validates AI responses with Pydantic models
    4. Fills gaps in AI responses with sensible defaults
    """

    def __init__(self, db: AsyncSession, range_index: int = 1):
        """Initialize the AI scenario designer.

        Args:
            db: Database session for loading AI provider config
            range_index: The scenario's /16 IP range index (1-254)
        """
        self.db = db
        self.range_index = range_index
        self._rule_generator = ScenarioGenerator(range_index=range_index)
        self._ip_counter = 10
        self._mac_counter = 1
        self._zone_subnet_map: dict[str, int] = {}  # zone_id -> subnet_offset

    async def design_scenario(
        self,
        description: str,
        name: str | None = None,
        duration_ms: int = 300000,
        vertical: str | None = None,
        preferred_vendors: list[str] | None = None,
        preferred_protocols: list[str] | None = None,
        total_device_count: int | None = None,
        device_counts: dict[str, int] | None = None,
        include_vulnerable_devices: bool = False,
    ) -> AIDesignResult:
        """Design a scenario using AI with rule-based fallback.

        Args:
            description: Natural language scenario description
            name: Optional scenario name
            duration_ms: Scenario duration in milliseconds
            vertical: Industry vertical (manufacturing, water, energy, oil_gas)
            preferred_vendors: User-selected vendors (None = AI decides)
            preferred_protocols: User-selected protocols (None = AI decides)
            total_device_count: Target total device count (AI decides mix)
            device_counts: Specific counts per device type
            include_vulnerable_devices: Include CVE-vulnerable devices for security testing

        Returns:
            AIDesignResult with generated scenario and metadata
        """
        # Try to get AI provider
        try:
            provider = await AIProviderFactory.create(self.db)
        except ValueError as e:
            logger.warning(f"AI provider not available: {e}")
            return self._fallback_to_rules(
                description=description,
                name=name,
                duration_ms=duration_ms,
                vertical=vertical,
                preferred_vendors=preferred_vendors,
                preferred_protocols=preferred_protocols,
                total_device_count=total_device_count,
                device_counts=device_counts,
                reason="AI provider not configured",
            )

        # Build prompts
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_design_prompt(
            description=description,
            vertical=vertical,
            preferred_vendors=preferred_vendors,
            preferred_protocols=preferred_protocols,
            total_device_count=total_device_count,
            device_counts=device_counts,
        )

        # Use maximum tokens for all scenarios to prevent truncation
        # Claude Opus 4.5 supports up to 16384 output tokens
        max_tokens = 16384

        # Call Claude with timeout (2 minutes to allow for complex scenarios)
        try:
            response = await asyncio.wait_for(
                provider.chat(
                    messages=[
                        {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
                    ],
                    max_tokens=max_tokens,
                ),
                timeout=180.0,  # Increase timeout for large scenarios
            )
        except asyncio.TimeoutError:
            logger.warning("AI design timed out after 180 seconds")
            raise RuntimeError(
                "AI scenario generation timed out. Try reducing the number of devices "
                "or simplifying the scenario description."
            )
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            raise RuntimeError(f"AI scenario generation failed: {e}") from e

        # Check for truncation - stop_reason will be "max_tokens" if response was cut off
        stop_reason = response.get("stop_reason")
        if stop_reason == "max_tokens":
            output_tokens = response.get("usage", {}).get("output_tokens", 0)
            logger.error(
                f"AI response was truncated (stop_reason=max_tokens, output_tokens={output_tokens}). "
                f"Requested max_tokens={max_tokens}."
            )
            raise RuntimeError(
                f"AI response was truncated after {output_tokens} tokens. "
                f"Try reducing the number of devices (currently {total_device_count or 'unspecified'}) "
                "or simplifying the scenario description."
            )

        # Parse AI response
        try:
            ai_design = self._parse_ai_response(response)
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise RuntimeError(f"AI returned invalid response: {e}") from e

        # Build scenario from AI design
        try:
            scenario = self._build_scenario_from_ai_design(
                ai_design=ai_design,
                name=name,
                description=description,
                duration_ms=duration_ms,
                vertical=vertical or ai_design.vertical,
            )

            return AIDesignResult(
                scenario=scenario,
                ai_enhanced=True,
                ai_features=["vendors", "protocols", "device_names", "flow_descriptions", "zones"],
                design_rationale=ai_design.design_rationale,
            )
        except Exception as e:
            logger.error(f"Failed to build scenario from AI design: {e}")
            raise RuntimeError(f"Failed to build scenario from AI design: {e}") from e

    def _get_system_prompt(self) -> str:
        """Get the system prompt for Claude."""
        # Get available fingerprints with complete protocol identity data
        fingerprints = get_all_fingerprints()

        # Group fingerprints by vendor, showing model and supported protocols
        vendor_fingerprints: dict[str, list[str]] = {}
        for fp in fingerprints:
            vendor = fp.get("vendor", "Unknown")
            model = fp.get("model", "Unknown")
            family = fp.get("vendor_family", "")
            supported_protocols = fp.get("supported_protocols", [])

            # Determine actual protocols this fingerprint has identity data for
            available_protocols = []
            if fp.get("modbus_identity"):
                available_protocols.append("modbus_tcp")
            if fp.get("ethernet_ip_identity"):
                available_protocols.append("ethernet_ip")
            if fp.get("profinet_identity"):
                available_protocols.append("profinet")
            if fp.get("s7_identity"):
                available_protocols.append("s7comm")
            if fp.get("snmp_identity"):
                available_protocols.append("snmp")
            if fp.get("bacnet_identity"):
                available_protocols.append("bacnet")

            # Skip fingerprints with no protocol identities
            if not available_protocols:
                continue

            if vendor not in vendor_fingerprints:
                vendor_fingerprints[vendor] = []

            # Format: model (family) → protocols
            protocols_str = ", ".join(available_protocols)
            if family:
                entry = f"{model} ({family}) → {protocols_str}"
            else:
                entry = f"{model} → {protocols_str}"
            vendor_fingerprints[vendor].append(entry)

        # Format as organized list with protocols shown
        fingerprint_lines = []
        for vendor in sorted(vendor_fingerprints.keys()):
            models = vendor_fingerprints[vendor][:10]  # Limit to 10 models per vendor
            if len(vendor_fingerprints[vendor]) > 10:
                models.append("... (more available)")
            fingerprint_lines.append(f"**{vendor}**:")
            for m in models:
                fingerprint_lines.append(f"  - {m}")

        fingerprint_list = "\n".join(fingerprint_lines)

        return f"""You are an expert OT (Operational Technology) network architect designing realistic industrial control system scenarios for PacketArch, a traffic simulation platform used for security testing.

## Your Task
Design a complete OT network scenario with devices, communication flows, and network zones based on the user's description. Generate REALISTIC, CONTEXTUAL names and configurations.

## Available Vendor Fingerprints (MUST use for fingerprint_model field)
Each model shows its supported protocols after the arrow (→). ONLY use protocols listed for that model.

{fingerprint_list}

## Protocol Selection Rules (CRITICAL)
- fingerprint_model MUST be an EXACT model from the list above (e.g., "6ES7 517-3AP00-0AB0", "1756-L85E")
- ONLY assign protocols that appear after the → for your chosen model
- If you need ethernet_ip, select a Rockwell model (1756-L85E, 1769-L33ER, etc.)
- If you need profinet/s7comm, select a Siemens model (6ES7 517-3AP00-0AB0, etc.)
- modbus_tcp is supported by most models
- Do NOT invent model names or use "Generic" - only use exact models from the list

## Industry Verticals
- manufacturing: PLCs, HMIs, drives, robots, sensors (Rockwell, Siemens, Schneider)
- water: RTUs, PLCs, pump controllers, flow meters, level sensors (Schneider, Honeywell, GE)
- energy: RTUs, IEDs, PMUs, meters (GE, ABB, Siemens)
- oil_gas: RTUs, PLCs, flow computers, compressor controllers (Emerson, Honeywell, ABB)
- transportation: Traffic controllers, DMS, radars, cameras, RSUs, weather stations (Econolite, Siemens ITS, McCain, Wavetronix, Axis, FLIR)

## Vendor Selection Guidelines
- Rockwell: Best for EtherNet/IP scenarios (Allen-Bradley PLCs, drives)
- Siemens: Best for PROFINET/S7comm scenarios (S7-1500, S7-1200, SINAMICS)
- Schneider: Best for Modbus TCP scenarios (Modicon M580, M340)
- GE: Good for hybrid EtherNet/IP and Modbus scenarios (PACSystems)
- Transportation ITS vendors: Use for SNMP/NTCIP traffic scenarios

## Zone and IP Address Rules
- Each zone MUST have a unique subnet_offset (0, 1, 2, etc.)
- Zone subnet_offset determines the third octet: 10.X.{{subnet_offset}}.0/24
- Assign Purdue model level to each zone: 0=Field, 1=Control, 2=Supervisory, 3=Operations
- Device IPs are auto-assigned within their zone's /24 subnet
- Do NOT hardcode specific IP addresses - they will be auto-assigned

## Output Format
Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{
  "vertical": "manufacturing|water|energy|oil_gas",
  "recommended_vendors": ["vendor1", "vendor2"],
  "recommended_protocols": ["protocol1", "protocol2"],
  "zones": [
    {{"id": "zone_1", "name": "Descriptive_Zone_Name", "description": "Purpose of this zone", "subnet_offset": 0, "level": 2, "vlan": 100}}
  ],
  "devices": [
    {{
      "name": "Descriptive_Device_Name",
      "device_type": "plc|hmi|rtu|drive|sensor|robot|ied|meter|pump_controller|flow_meter|level_sensor|flow_computer|traffic_controller|dms|rsu|radar_sensor|lidar_sensor|weather_station|camera|thermal_sensor|lighting_controller|ventilation_controller|toll_controller|anpr_camera|jump_server|remote_gateway|cloud_connector|ewon_gateway",
      "vendor": "rockwell|siemens|schneider|abb|honeywell|emerson|ge|econolite|siemens_its|mccain|wavetronix|flir|vaisala|daktronics|axis|pelco|hikvision|bosch|kapsch|q-free|hms|microsoft|teamviewer",
      "fingerprint_model": "REQUIRED: EXACT model from fingerprint list (e.g., '6ES7 517-3AP00-0AB0', '1756-L85E')",
      "zone_id": "zone_1",
      "role": "Brief description of device's role in the scenario",
      "protocols": ["modbus_tcp"]
    }}
  ],
  "flows": [
    {{
      "source_name": "Device_Name",
      "target_name": "Device_Name",
      "protocol": "modbus_tcp|ethernet_ip|profinet|snmp",
      "description": "Contextual description of this communication flow",
      "poll_interval_ms": 1000,
      "pattern": "polling|event|periodic"
    }}
  ],
  "design_rationale": "Brief explanation of why you made these design choices"
}}

## CRITICAL CONNECTIVITY RULES (MUST FOLLOW)

1. **EVERY device MUST appear in at least one flow** - No orphan devices allowed. If you create a device, it MUST be either a source or target in at least one flow.

2. **OT Hierarchy (Purdue Model)**:
   - Level 2 (Supervisory): HMI, SCADA servers, historians, engineering stations
   - Level 1 (Control): PLCs, RTUs, DCS controllers
   - Level 0 (Field): Sensors, drives, meters, I/O modules, actuators, flow meters, level sensors

3. **Communication Direction Rules (STRICT)**:
   - Controllers (PLC/RTU) are SOURCES that poll field devices (sensors, drives, meters)
   - Field devices (sensors/drives/meters) are TARGETS only - they respond to polls, never initiate
   - HMIs poll controllers (HMI → PLC), never field devices directly
   - SCADA polls controllers or receives from historians

4. **Flow Coverage Requirements**:
   - Every controller MUST have flows TO field devices it controls
   - Every field device MUST be polled BY at least one controller
   - Every HMI MUST poll at least one controller
   - If SCADA exists, it MUST connect to controllers

5. **Device-to-Flow Ratio**:
   - Minimum: 1 flow per device (every device connected)
   - Recommended: 1.5-2x flows vs devices for realistic topology
   - Example: 10 devices should have 15-20 flows

## Design Guidelines

1. **Device Names**: Use descriptive, scenario-specific names with underscores
   - GOOD: "Bottling_Line_Main_PLC", "Tank_A_Level_Sensor", "Packaging_HMI_01"
   - BAD: "PLC-001", "SENSOR-002", "Device_1"

2. **Realistic Topology Pattern**:
   - PLCs/RTUs at center, polling multiple field devices each
   - HMIs connect to PLCs for operator visualization
   - Each PLC should poll 3-8 field devices
   - Group devices by physical area/function

3. **Poll Intervals by Data Type**:
   - Safety/interlocks: 50-100ms
   - Process control: 100-500ms
   - Monitoring/trending: 1000-5000ms

4. **Zone Names**: Reflect physical or logical areas
   - GOOD: "Packaging_Area", "Quality_Control_Lab", "Pump_Station_1"
   - BAD: "Zone_1", "Area_A", "Field"

5. **Flow Descriptions**: Explain the PURPOSE of communication
   - GOOD: "Main PLC reads tank level for fill control logic"
   - BAD: "PLC polling sensor"
"""

    def _build_design_prompt(
        self,
        description: str,
        vertical: str | None,
        preferred_vendors: list[str] | None,
        preferred_protocols: list[str] | None,
        total_device_count: int | None,
        device_counts: dict[str, int] | None,
    ) -> str:
        """Build the user prompt for scenario design."""
        constraints = []

        if vertical:
            constraints.append(f"Industry vertical: {vertical}")
        else:
            constraints.append("Industry vertical: Determine from description")

        if total_device_count:
            constraints.append(f"Target device count: {total_device_count} devices total")
        elif device_counts:
            counts_str = ", ".join(f"{k}: {v}" for k, v in device_counts.items())
            constraints.append(f"Specific device counts: {counts_str}")
        else:
            constraints.append("Device count: Determine appropriate count based on scenario")

        if preferred_vendors:
            constraints.append(f"Preferred vendors: {', '.join(preferred_vendors)}")
        else:
            constraints.append("Vendors: Select appropriate vendors for the scenario")

        if preferred_protocols:
            constraints.append(f"Preferred protocols: {', '.join(preferred_protocols)}")
        else:
            constraints.append("Protocols: Select appropriate protocols for the vendors")

        constraints.append("Maximum devices: 100")
        constraints.append("Minimum devices: 5")

        # For large scenarios, instruct AI to be concise to avoid token limits
        if total_device_count and total_device_count > 20:
            constraints.append(
                "IMPORTANT: Keep descriptions SHORT (max 10 words) - "
                "this is a large scenario"
            )

        constraints_text = "\n- ".join(constraints)

        return f"""Design an OT network scenario for the following description:

"{description}"

Constraints:
- {constraints_text}

Generate the JSON response with realistic device names, appropriate vendors/protocols, meaningful zones, and contextual flow descriptions."""

    def _repair_json(self, json_str: str) -> str:
        """Attempt to repair common JSON issues from AI responses.

        Fixes:
        - Trailing commas in arrays and objects
        - Missing commas between elements (common AI mistake)
        - Control characters in strings
        """
        # Remove trailing commas before ] or }
        json_str = re.sub(r',(\s*[\]}])', r'\1', json_str)

        # Fix missing commas between array elements (e.g., "}" followed by "{" without comma)
        # This handles: }{ -> },{
        json_str = re.sub(r'\}(\s*)\{', r'},\1{', json_str)

        # Fix missing commas between string values and objects
        # e.g., "value" { -> "value", {
        json_str = re.sub(r'\"(\s*)\{', r'",\1{', json_str)

        # Fix missing commas between } and "
        # e.g., } "key" -> }, "key"
        json_str = re.sub(r'\}(\s*)\"', r'},\1"', json_str)

        # Fix missing commas between ] and "
        json_str = re.sub(r'\](\s*)\"', r'],\1"', json_str)

        # Fix missing commas between ] and {
        json_str = re.sub(r'\](\s*)\{', r'],\1{', json_str)

        # Fix missing commas between numbers/booleans and "
        json_str = re.sub(r'(\d)(\s*)\"', r'\1,\2"', json_str)
        json_str = re.sub(r'(true|false|null)(\s*)\"', r'\1,\2"', json_str)

        return json_str

    def _parse_ai_response(self, response: dict[str, Any]) -> AIScenarioDesign:
        """Parse and validate AI response."""
        # Extract text content from response
        content = response.get("content", [])
        text = ""
        for block in content:
            if block.get("type") == "text":
                text += block.get("text", "")

        logger.debug(f"Raw AI response length: {len(text)} chars")

        # Try to extract JSON from the response
        # Handle cases where AI might wrap JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_str = text.strip()

        # Parse JSON with repair attempts
        parse_attempts = [
            ("direct", json_str),
            ("repaired", self._repair_json(json_str)),
        ]

        # Also try extracting just the JSON object if wrapped in text
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            extracted = text[start:end]
            parse_attempts.extend([
                ("extracted", extracted),
                ("extracted_repaired", self._repair_json(extracted)),
            ])

        last_error = None
        for attempt_name, json_to_try in parse_attempts:
            try:
                data = json.loads(json_to_try)
                if attempt_name != "direct":
                    logger.info(f"JSON parsed successfully using '{attempt_name}' method")
                return AIScenarioDesign.model_validate(data)
            except json.JSONDecodeError as e:
                last_error = e
                logger.debug(f"JSON parse attempt '{attempt_name}' failed: {e}")
            except Exception as e:
                last_error = e
                logger.debug(f"Validation attempt '{attempt_name}' failed: {e}")

        # All attempts failed - log context for debugging
        logger.error(f"All JSON parse attempts failed. Last error: {last_error}")
        logger.error(f"JSON string around error (chars 24000-25500): {json_str[24000:25500] if len(json_str) > 25500 else json_str[-1500:]}")

        raise ValueError(f"Could not parse AI JSON response: {last_error}")

    def _build_scenario_from_ai_design(
        self,
        ai_design: AIScenarioDesign,
        name: str | None,
        description: str,
        duration_ms: int,
        vertical: str,
    ) -> GeneratedScenario:
        """Convert AI design to GeneratedScenario."""
        # Reset counters
        self._ip_counter = 10
        self._mac_counter = 1
        self._zone_subnet_map = {}  # Reset zone subnet mapping

        # Build zone mapping with subnet_offset
        zone_map = {}  # zone_id -> zone_name
        zone_id_map = {}  # zone_name -> zone_id (for IP generation)
        zones = []
        for i, zone in enumerate(ai_design.zones):
            zone_map[zone.id] = zone.name
            zone_id_map[zone.name] = zone.id
            # Use AI-provided subnet_offset or assign sequentially
            subnet_offset = zone.subnet_offset if zone.subnet_offset is not None else i
            self._zone_subnet_map[zone.id] = subnet_offset
            zones.append({
                "id": zone.id,
                "name": zone.name,
                "description": zone.description,
                "subnet_offset": subnet_offset,
                "level": zone.level,
                "vlan": zone.vlan or (100 + i * 10),
                "network": {
                    "subnet": f"10.{self.range_index}.{subnet_offset}.0/24",
                    "gateway": f"10.{self.range_index}.{subnet_offset}.1",
                    "subnet_offset": subnet_offset,
                },
                "device_count": 0,
                "device_ids": [],
            })

        # Default zone if none specified
        if not zones:
            default_id = "default"
            self._zone_subnet_map[default_id] = 0
            zones.append({
                "id": default_id,
                "name": "Process_Control",
                "description": "Main process control zone",
                "subnet_offset": 0,
                "level": 2,
                "vlan": 100,
                "network": {
                    "subnet": f"10.{self.range_index}.0.0/24",
                    "gateway": f"10.{self.range_index}.0.1",
                    "subnet_offset": 0,
                },
                "device_count": 0,
                "device_ids": [],
            })
            zone_map["default"] = "Process_Control"
            zone_id_map["Process_Control"] = default_id

        # Build devices
        devices = []
        device_name_to_id = {}

        for ai_device in ai_design.devices:
            device_id = str(uuid.uuid4())
            device_name_to_id[ai_device.name] = device_id

            # Get zone info - use zone_id for IP generation, zone_name for display
            device_zone_id = ai_device.zone_id or zones[0]["id"]
            zone_name = zone_map.get(device_zone_id, zones[0]["name"])

            # Get fingerprint data if model specified
            fingerprint_data = None
            # Track the actual fingerprint model to use
            actual_fingerprint_model = ai_device.fingerprint_model

            if ai_device.fingerprint_model and ai_device.vendor:
                fingerprint_data = get_fingerprint_by_vendor_model(
                    ai_device.vendor, ai_device.fingerprint_model
                )

                # If specific model not found, try to find a compatible fingerprint
                # from the same vendor for the same device type
                if not fingerprint_data:
                    logger.info(
                        f"Device '{ai_device.name}': Fingerprint '{ai_device.fingerprint_model}' "
                        f"not found for {ai_device.vendor}, searching for compatible fingerprint..."
                    )
                    from app.services.fingerprint_cache import get_fingerprints_by_vendor
                    vendor_fps = get_fingerprints_by_vendor(ai_device.vendor)

                    # Try to find a fingerprint matching the device type
                    device_type_lower = ai_device.device_type.lower()
                    for fp in vendor_fps:
                        fp_model = fp.get("model", "")
                        fp_family = (fp.get("vendor_family") or "").lower()

                        # Match HMIs to HMI fingerprints, PLCs to PLC fingerprints, etc.
                        if device_type_lower in ["hmi", "panel", "display"]:
                            if "hmi" in fp_family or "panel" in fp_family or "comfort" in fp_family:
                                fingerprint_data = fp
                                actual_fingerprint_model = fp_model
                                logger.info(
                                    f"Device '{ai_device.name}': Using fallback fingerprint "
                                    f"'{fp_model}' (matched device type: {ai_device.device_type})"
                                )
                                break
                        elif device_type_lower in ["plc", "controller", "cpu"]:
                            if any(k in fp_family for k in ["plc", "cpu", "controller", "s7"]):
                                fingerprint_data = fp
                                actual_fingerprint_model = fp_model
                                logger.info(
                                    f"Device '{ai_device.name}': Using fallback fingerprint "
                                    f"'{fp_model}' (matched device type: {ai_device.device_type})"
                                )
                                break
                        elif device_type_lower in ["vfd", "drive", "motor"]:
                            if any(k in fp_family for k in ["drive", "vfd", "powerflex", "acs"]):
                                fingerprint_data = fp
                                actual_fingerprint_model = fp_model
                                logger.info(
                                    f"Device '{ai_device.name}': Using fallback fingerprint "
                                    f"'{fp_model}' (matched device type: {ai_device.device_type})"
                                )
                                break

                    # If still no match, use first available fingerprint from vendor
                    if not fingerprint_data and vendor_fps:
                        fingerprint_data = vendor_fps[0]
                        actual_fingerprint_model = fingerprint_data.get("model")
                        logger.info(
                            f"Device '{ai_device.name}': Using generic vendor fingerprint "
                            f"'{actual_fingerprint_model}' from {ai_device.vendor}"
                        )

                    # If still nothing, clear the fingerprint model
                    if not fingerprint_data:
                        actual_fingerprint_model = None
                        logger.warning(
                            f"Device '{ai_device.name}': No fingerprints available for "
                            f"{ai_device.vendor}, device will have no protocols"
                        )

            # Generate MAC address
            if fingerprint_data and fingerprint_data.get("oui_prefixes"):
                import random
                oui = random.choice(fingerprint_data["oui_prefixes"])
                mac_address = self._generate_mac_with_oui(oui)
            else:
                mac_address = generate_mac_address(
                    vendor=ai_device.vendor,
                    device_type=ai_device.device_type,
                )

            # Get error config
            error_config = None
            if fingerprint_data:
                error_behavior = fingerprint_data.get("error_behavior", {})
                if error_behavior:
                    error_config = {
                        "exception_rate": error_behavior.get("exception_probability", 0.001),
                        "timeout_rate": error_behavior.get("timeout_probability", 0.0005),
                    }

            # Ensure device has at least one TCP/UDP protocol for IP traffic generation
            # Layer 2 only protocols (profinet, profisafe) don't generate IP traffic
            device_protocols = ai_device.protocols
            has_tcp_udp = any(p in self.TCP_UDP_PROTOCOLS for p in device_protocols)
            if not has_tcp_udp:
                # Add a TCP/UDP protocol based on device type and vendor
                fallback_protocol = self._get_fallback_tcp_protocol(
                    ai_device.device_type, ai_device.vendor
                )
                device_protocols = device_protocols + [fallback_protocol]
                logger.info(
                    f"Added {fallback_protocol} to {ai_device.name} (had only Layer 2 protocols)"
                )

            # Filter protocols to only those supported by the fingerprint identity data
            # This prevents protocol_identity_mismatch validation errors at deploy time
            # Note: fingerprint_data already contains proper identity from vendor fingerprints
            # (with fallback to vendor's generic fingerprint if no specific model match)
            device_protocols = self._filter_protocols_by_fingerprint(
                device_protocols, fingerprint_data, ai_device.name
            )

            device = GeneratedDevice(
                device_id=device_id,
                device_type=ai_device.device_type,
                name=ai_device.name,
                vendor=ai_device.vendor,
                model=actual_fingerprint_model,
                ip_address=self._generate_ip(device_zone_id),
                mac_address=mac_address,
                zone=zone_name,
                protocols=device_protocols,
                fingerprint_model=actual_fingerprint_model,
                error_config=error_config,
                fingerprint_data=fingerprint_data,
            )
            devices.append(device)

            # Update zone device count
            for zone in zones:
                if zone.get("id") == device_zone_id or zone["name"] == zone_name:
                    zone["device_count"] += 1
                    zone["device_ids"].append(device_id)
                    break

        # Build flows from AI design
        flows = []
        for ai_flow in ai_design.flows:
            source_id = device_name_to_id.get(ai_flow.source_name)
            target_id = device_name_to_id.get(ai_flow.target_name)

            if not source_id or not target_id:
                logger.warning(
                    f"Skipping flow: source={ai_flow.source_name}, target={ai_flow.target_name} - device not found"
                )
                continue

            flow = GeneratedFlow(
                flow_id=str(uuid.uuid4()),
                source_device_id=source_id,
                destination_device_id=target_id,
                protocol=ai_flow.protocol,
                poll_interval_ms=ai_flow.poll_interval_ms,
                description=ai_flow.description,
            )
            flows.append(flow)

        # Ensure all devices are connected (fix orphans)
        flows = self._ensure_connectivity(devices, flows)

        # Validate OT hierarchy (log warnings but don't fail)
        hierarchy_warnings = self._validate_hierarchy(devices, flows)
        for warning in hierarchy_warnings:
            logger.warning(f"Hierarchy issue: {warning}")

        # Create scenario
        scenario = GeneratedScenario(
            scenario_id=str(uuid.uuid4()),
            name=name or f"{vertical.replace('_', ' ').title()} Scenario",
            description=description,
            vertical=vertical,
            devices=devices,
            flows=flows,
            zones=zones,
            duration_ms=duration_ms,
            metadata={
                "ai_enhanced": True,
                "ai_design_rationale": ai_design.design_rationale,
                "recommended_vendors": ai_design.recommended_vendors,
                "recommended_protocols": ai_design.recommended_protocols,
                "range_index": self.range_index,
                "ip_range": f"10.{self.range_index}.0.0/16",
            },
        )

        logger.info(
            f"Built AI-designed scenario '{scenario.name}' with "
            f"{len(devices)} devices and {len(flows)} flows"
        )
        return scenario

    def _generate_ip(self, zone_id: str) -> str:
        """Generate an IP address within a zone's /24 subnet.

        Uses the scenario's allocated /16 range and the zone's subnet_offset
        to generate IPs in the format: 10.{range_index}.{subnet_offset}.{host}

        Args:
            zone_id: The zone identifier to get subnet_offset from

        Returns:
            IP address string
        """
        # Get or assign subnet_offset for this zone
        if zone_id not in self._zone_subnet_map:
            self._zone_subnet_map[zone_id] = len(self._zone_subnet_map)

        subnet_offset = self._zone_subnet_map[zone_id]
        ip = f"10.{self.range_index}.{subnet_offset}.{self._ip_counter}"
        self._ip_counter += 1
        if self._ip_counter > 254:
            self._ip_counter = 10

        return ip

    def _generate_mac_with_oui(self, oui: str) -> str:
        """Generate a MAC address with a specific OUI prefix."""
        nic = [
            (self._mac_counter >> 16) & 0xFF,
            (self._mac_counter >> 8) & 0xFF,
            self._mac_counter & 0xFF,
        ]
        self._mac_counter += 1
        return f"{oui}:{nic[0]:02X}:{nic[1]:02X}:{nic[2]:02X}"

    def _get_fallback_tcp_protocol(self, device_type: str, vendor: str | None) -> str:
        """Get a fallback TCP/UDP protocol for a device that only has Layer 2 protocols.

        Selects appropriate TCP/UDP protocol based on vendor and device type:
        - Siemens: s7comm_plus (PLCs/HMIs) or modbus_tcp (drives/IO)
        - Rockwell: ethernet_ip
        - Transportation: snmp
        - Others: modbus_tcp (most universal)
        """
        vendor_lower = (vendor or "").lower()

        # Vendor-specific protocols
        if "siemens" in vendor_lower:
            if device_type in {"plc", "hmi", "safety_plc"}:
                return "s7comm_plus"
            return "modbus_tcp"
        if "rockwell" in vendor_lower or "allen" in vendor_lower:
            return "ethernet_ip"
        if "schneider" in vendor_lower or "modicon" in vendor_lower:
            return "modbus_tcp"

        # Device type specific
        if device_type in self.CONTROLLER_TYPES:
            return "modbus_tcp"
        if device_type in {"camera", "dms", "rsu", "radar_sensor", "weather_station"}:
            return "snmp"
        if device_type in self.SUPERVISORY_TYPES:
            return "modbus_tcp"

        # Universal fallback
        return "modbus_tcp"

    # Required fields for each identity type to be considered valid
    IDENTITY_REQUIRED_FIELDS: dict[str, str] = {
        "ethernet_ip_identity": "vendor_id",
        "profinet_identity": "vendor_id",
        "s7_identity": "order_code",
        "modbus_identity": "vendor_name",
        "bacnet_identity": "vendor_id",
        "snmp_identity": "sys_descr",
        "opc_ua_identity": "manufacturer_name",
        "dnp3_identity": "vendor_name",
        "iec104_identity": "vendor_name",
    }

    def _filter_protocols_by_fingerprint(
        self,
        protocols: list[str],
        fingerprint_data: dict | None,
        device_name: str,
    ) -> list[str]:
        """Filter protocols to only those supported by the fingerprint identity data.

        This prevents protocol_identity_mismatch validation errors at deploy time.
        The fingerprint_data should already contain proper identity from vendor fingerprints
        (with fallback to vendor's generic fingerprint handled by get_fingerprint_by_vendor_model).

        Per protocol_validator.py design principle:
        "Identity blocks should not be created from nothing - they must come from
        proper vendor fingerprint data."

        Args:
            protocols: List of requested protocols
            fingerprint_data: Device fingerprint data (should have proper identity)
            device_name: Device name for logging

        Returns:
            List of protocols that have valid identity support in the fingerprint
        """
        if not protocols:
            return ["modbus_tcp"]

        # If no fingerprint data at all, we cannot assign protocols that require identities
        # because there's no identity data to use. Return empty list - device will be
        # excluded from protocol traffic (but can still be in scenario for display).
        if not fingerprint_data:
            logger.warning(
                f"Device '{device_name}': No fingerprint data available - "
                "device will have no protocols (no identity data for traffic generation)."
            )
            return []

        validated = []
        removed = []

        for protocol in protocols:
            identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)

            if identity_key:
                # Protocol requires identity - check if fingerprint has it
                identity = fingerprint_data.get(identity_key)
                if self._identity_has_vendor_data(identity, identity_key):
                    validated.append(protocol)
                else:
                    removed.append(protocol)
            else:
                # Protocol doesn't require identity mapping (future protocols, raw TCP, etc.)
                validated.append(protocol)

        if removed:
            logger.info(
                f"Device '{device_name}': Removed protocols {removed} "
                f"(no identity data in fingerprint), keeping {validated}"
            )

        # If no protocols validated, fall back to protocols the fingerprint supports
        if not validated:
            # Check what identities the fingerprint actually has
            available_protocols = []
            for proto, identity_key in PROTOCOL_TO_IDENTITY_KEY.items():
                identity = fingerprint_data.get(identity_key)
                if self._identity_has_vendor_data(identity, identity_key):
                    available_protocols.append(proto)

            if available_protocols:
                # Prefer modbus_tcp if available, otherwise take first available
                if "modbus_tcp" in available_protocols:
                    validated = ["modbus_tcp"]
                else:
                    validated = [available_protocols[0]]
                logger.info(
                    f"Device '{device_name}': No requested protocols valid, "
                    f"using fingerprint's supported protocols: {validated}"
                )
            else:
                logger.warning(
                    f"Device '{device_name}': Fingerprint has no protocol identities. "
                    "Device may fail validation at deploy time."
                )
                # Return modbus_tcp anyway - validation will catch this if it's a problem
                validated = ["modbus_tcp"]

        return validated

    def _identity_has_vendor_data(
        self,
        identity: dict | None,
        identity_key: str,
    ) -> bool:
        """Check if an identity dictionary has real vendor data.

        Args:
            identity: The identity dictionary to check
            identity_key: The identity key (e.g., "ethernet_ip_identity")

        Returns:
            True if identity has meaningful vendor data, False otherwise
        """
        if not identity or not isinstance(identity, dict):
            return False

        # Get the required field for this identity type
        required_field = self.IDENTITY_REQUIRED_FIELDS.get(identity_key)
        if required_field:
            # Check for the specific required field
            if identity.get(required_field) is not None:
                return True

        # Fallback: check if there's any field besides serial_number
        meaningful_keys = [k for k in identity.keys() if k not in ("serial_number", "im0_serial_number")]
        return len(meaningful_keys) > 0

    # ==================== Connectivity & Hierarchy Validation ====================

    # Device type classifications for OT hierarchy
    CONTROLLER_TYPES = {"plc", "rtu", "dcs", "safety_plc", "traffic_controller", "toll_controller"}
    FIELD_DEVICE_TYPES = {
        # Traditional OT field devices
        "sensor", "drive", "meter", "io_module", "flow_meter",
        "level_sensor", "pump_controller", "servo", "actuator",
        "temperature_sensor", "pressure_sensor", "valve",
        # Transportation field devices
        "radar_sensor", "lidar_sensor", "thermal_sensor", "weather_station",
        "camera", "video_detector", "anpr_camera", "dms", "rsu",
        "lighting_controller", "ventilation_controller",
    }
    SUPERVISORY_TYPES = {"hmi", "scada_server", "historian", "engineering_station", "tmc",
                          "jump_server", "remote_gateway", "cloud_connector", "ewon_gateway"}

    # TCP/UDP protocols that generate IP traffic (required for Cyber Vision discovery)
    # Layer 2 protocols like PROFINET don't include IP addresses in packets
    TCP_UDP_PROTOCOLS = {
        "modbus_tcp", "modbus", "ethernet_ip", "s7comm", "s7comm_plus",
        "bacnet", "snmp", "opc_ua", "dnp3", "iec104", "iec_104", "https",
    }
    # Layer 2 only protocols (no IP in packets)
    LAYER2_ONLY_PROTOCOLS = {"profinet", "profisafe"}

    def _ensure_connectivity(
        self,
        devices: list[GeneratedDevice],
        flows: list[GeneratedFlow],
    ) -> list[GeneratedFlow]:
        """Ensure all devices have flows, applying OT hierarchy rules.

        This method detects orphaned devices (those not in any flow) and
        generates appropriate flows based on OT hierarchy:
        - Field devices get connected to controllers
        - HMIs get connected to controllers
        - Controllers without targets get connected to field devices

        Args:
            devices: List of generated devices
            flows: List of AI-generated flows

        Returns:
            Updated list of flows with orphans connected
        """
        if not devices:
            return flows

        # Categorize devices by OT level
        controllers = [d for d in devices if d.device_type in self.CONTROLLER_TYPES]
        field_devices = [d for d in devices if d.device_type in self.FIELD_DEVICE_TYPES]
        supervisory = [d for d in devices if d.device_type in self.SUPERVISORY_TYPES]

        # Find devices already in flows
        devices_in_flows: set[str] = set()
        for flow in flows:
            devices_in_flows.add(flow.source_device_id)
            devices_in_flows.add(flow.destination_device_id)

        # Find orphaned devices
        orphaned = [d for d in devices if d.device_id not in devices_in_flows]

        if not orphaned:
            logger.debug("All devices are connected - no orphans detected")
            return flows

        logger.info(f"Detected {len(orphaned)} orphaned devices - generating flows")

        new_flows: list[GeneratedFlow] = []
        device_map = {d.device_id: d for d in devices}

        for orphan in orphaned:
            if orphan.device_type in self.FIELD_DEVICE_TYPES:
                # Field device: should be polled by a controller
                controller = self._find_compatible_controller(orphan, controllers, devices_in_flows)
                if controller:
                    new_flows.append(self._create_hierarchy_flow(
                        source=controller,
                        target=orphan,
                        flow_type="controller_to_field",
                    ))
                    devices_in_flows.add(orphan.device_id)
                    logger.debug(f"Connected field device {orphan.name} to controller {controller.name}")

            elif orphan.device_type in self.SUPERVISORY_TYPES:
                # HMI/SCADA: should poll a controller
                if controllers:
                    # Find a controller that's already connected (prefer busy controllers)
                    target_controller = None
                    for c in controllers:
                        if c.device_id in devices_in_flows:
                            target_controller = c
                            break
                    if not target_controller:
                        target_controller = controllers[0]

                    new_flows.append(self._create_hierarchy_flow(
                        source=orphan,
                        target=target_controller,
                        flow_type="supervisory_to_controller",
                    ))
                    devices_in_flows.add(orphan.device_id)
                    logger.debug(f"Connected supervisory {orphan.name} to controller {target_controller.name}")

            elif orphan.device_type in self.CONTROLLER_TYPES:
                # Controller without any connections: connect to field devices
                unconnected_field = [
                    f for f in field_devices
                    if f.device_id not in devices_in_flows
                ]
                # If all field devices connected, just pick some anyway
                if not unconnected_field:
                    unconnected_field = field_devices[:5]

                for target in unconnected_field[:5]:  # Connect to up to 5 field devices
                    new_flows.append(self._create_hierarchy_flow(
                        source=orphan,
                        target=target,
                        flow_type="controller_to_field",
                    ))
                    devices_in_flows.add(target.device_id)

                devices_in_flows.add(orphan.device_id)
                logger.debug(f"Connected controller {orphan.name} to {min(5, len(unconnected_field))} field devices")

        if new_flows:
            logger.info(f"Generated {len(new_flows)} additional flows to connect orphaned devices")

        return flows + new_flows

    def _find_compatible_controller(
        self,
        field_device: GeneratedDevice,
        controllers: list[GeneratedDevice],
        devices_in_flows: set[str],
    ) -> GeneratedDevice | None:
        """Find a compatible controller for a field device.

        Prioritizes controllers that:
        1. Share a protocol with the field device
        2. Are in the same zone
        3. Are already connected to other devices (prefer busy controllers)
        """
        if not controllers:
            return None

        # Score controllers by compatibility
        scored: list[tuple[int, GeneratedDevice]] = []
        for controller in controllers:
            score = 0

            # Protocol match (most important)
            common_protocols = set(controller.protocols) & set(field_device.protocols)
            if common_protocols:
                score += 10

            # Same zone
            if controller.zone == field_device.zone:
                score += 5

            # Already connected (prefer consolidation)
            if controller.device_id in devices_in_flows:
                score += 3

            scored.append((score, controller))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else controllers[0]

    def _create_hierarchy_flow(
        self,
        source: GeneratedDevice,
        target: GeneratedDevice,
        flow_type: str,
    ) -> GeneratedFlow:
        """Create a flow following OT hierarchy patterns."""
        # Determine protocol - MUST use TCP/UDP protocol for IP traffic
        common_protocols = set(source.protocols) & set(target.protocols)

        # Filter to TCP/UDP protocols only (exclude Layer 2 like PROFINET)
        tcp_udp_common = common_protocols & self.TCP_UDP_PROTOCOLS
        if tcp_udp_common:
            protocol = list(tcp_udp_common)[0]
        else:
            # No common TCP/UDP protocol - find any TCP/UDP from either device
            source_tcp = set(source.protocols) & self.TCP_UDP_PROTOCOLS
            target_tcp = set(target.protocols) & self.TCP_UDP_PROTOCOLS
            if source_tcp:
                protocol = list(source_tcp)[0]
            elif target_tcp:
                protocol = list(target_tcp)[0]
            else:
                # Neither device has TCP/UDP protocol - use modbus_tcp as universal fallback
                protocol = "modbus_tcp"
                logger.warning(
                    f"No TCP/UDP protocol found for flow {source.name} -> {target.name}, "
                    f"using modbus_tcp fallback"
                )

        # Determine poll interval based on flow type
        if flow_type == "controller_to_field":
            # Control loop - faster polling
            poll_interval_ms = 500
            description = f"{source.name} polls {target.name} for process data"
        elif flow_type == "supervisory_to_controller":
            # HMI/SCADA - slower polling
            poll_interval_ms = 1000
            description = f"{source.name} reads status from {target.name}"
        else:
            poll_interval_ms = 1000
            description = f"{source.name} communicates with {target.name}"

        return GeneratedFlow(
            flow_id=str(uuid.uuid4()),
            source_device_id=source.device_id,
            destination_device_id=target.device_id,
            protocol=protocol,
            poll_interval_ms=poll_interval_ms,
            description=description,
        )

    def _validate_hierarchy(
        self,
        devices: list[GeneratedDevice],
        flows: list[GeneratedFlow],
    ) -> list[str]:
        """Validate flows follow OT hierarchy. Returns list of warnings.

        Checks for hierarchy violations like:
        - Field devices initiating communication to controllers
        - HMIs directly controlling field devices
        - Missing controller in the topology
        """
        warnings: list[str] = []

        if not devices or not flows:
            return warnings

        device_type_map = {d.device_id: d.device_type for d in devices}
        device_name_map = {d.device_id: d.name for d in devices}

        # Check for hierarchy violations in flows
        for flow in flows:
            source_type = device_type_map.get(flow.source_device_id)
            target_type = device_type_map.get(flow.destination_device_id)
            source_name = device_name_map.get(flow.source_device_id, "Unknown")
            target_name = device_name_map.get(flow.destination_device_id, "Unknown")

            # Field devices should not be sources to controllers
            if source_type in self.FIELD_DEVICE_TYPES and target_type in self.CONTROLLER_TYPES:
                warnings.append(
                    f"Inverted hierarchy: field device '{source_name}' ({source_type}) "
                    f"→ controller '{target_name}' ({target_type})"
                )

            # HMIs should not directly control field devices
            if source_type in self.SUPERVISORY_TYPES and target_type in self.FIELD_DEVICE_TYPES:
                warnings.append(
                    f"Bypassed controller: supervisory '{source_name}' ({source_type}) "
                    f"→ field device '{target_name}' ({target_type})"
                )

        # Check for missing controller
        has_controller = any(d.device_type in self.CONTROLLER_TYPES for d in devices)
        has_field_devices = any(d.device_type in self.FIELD_DEVICE_TYPES for d in devices)

        if has_field_devices and not has_controller:
            warnings.append(
                "Missing controller: scenario has field devices but no PLC/RTU to control them"
            )

        return warnings

    def _fallback_to_rules(
        self,
        description: str,
        name: str | None,
        duration_ms: int,
        vertical: str | None,
        preferred_vendors: list[str] | None,
        preferred_protocols: list[str] | None,
        total_device_count: int | None,
        device_counts: dict[str, int] | None,
        reason: str,
    ) -> AIDesignResult:
        """Fall back to rule-based scenario generation."""
        logger.info(f"Falling back to rule-based generation: {reason}")

        scenario = self._rule_generator.generate_from_description(
            description=description,
            name=name,
            duration_ms=duration_ms,
            preferred_vendors=preferred_vendors,
            preferred_protocols=preferred_protocols,
            vertical=vertical,
            total_device_count=total_device_count,
            device_counts=device_counts,
        )

        # Apply protocol filtering to fallback devices (same as AI-generated)
        # This ensures devices only have protocols for which they have identities
        for device in scenario.devices:
            fingerprint_data = None
            if device.fingerprint_model and device.vendor:
                fingerprint_data = get_fingerprint_by_vendor_model(
                    device.vendor, device.fingerprint_model
                )
            # Filter protocols using same logic as AI path
            device.protocols = self._filter_protocols_by_fingerprint(
                device.protocols, fingerprint_data, device.name
            )

        # Apply same connectivity and hierarchy validation to fallback scenarios
        scenario.flows = self._ensure_connectivity(scenario.devices, scenario.flows)

        hierarchy_warnings = self._validate_hierarchy(scenario.devices, scenario.flows)
        for warning in hierarchy_warnings:
            logger.warning(f"Fallback hierarchy issue: {warning}")

        return AIDesignResult(
            scenario=scenario,
            ai_enhanced=False,
            ai_features=[],
            fallback_reason=reason,
        )
