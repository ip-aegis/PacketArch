"""AI-enhanced device naming service.

This module generates meaningful, contextual device names based on:
- The industrial vertical (manufacturing, water, energy, etc.)
- The template description and process context
- The device's type, role, and zone
- The industrial process being simulated

Names like "PLC-MAIN-01" become "CNC_Machining_Cell_1_Controller".
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.mcp_server.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)


# ==================== Data Classes ====================


@dataclass
class DeviceNamingContext:
    """Context for generating meaningful device names."""

    vertical: str
    """Industry vertical (manufacturing, water, energy, etc.)"""

    template_name: str
    """Template name or scenario name"""

    template_description: str
    """Description of the industrial process"""

    zones: dict[str, Any] = field(default_factory=dict)
    """Zone definitions with IDs and descriptions"""

    process_context: str | None = None
    """Optional additional context from user"""


# ==================== Pydantic Models ====================


class DeviceNameMapping(BaseModel):
    """Single device name mapping from AI."""

    device_id: str
    new_name: str

    @field_validator("new_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        """Ensure name is clean and consistent."""
        # Replace spaces and hyphens with underscores
        cleaned = re.sub(r"[\s\-]+", "_", v)
        # Remove any non-alphanumeric characters except underscores
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "", cleaned)
        # Ensure reasonable length
        if len(cleaned) > 50:
            cleaned = cleaned[:50]
        return cleaned


class DeviceNamingResponse(BaseModel):
    """AI response containing device name mappings."""

    devices: list[DeviceNameMapping] = Field(default_factory=list)


# ==================== System Prompt ====================

DEVICE_NAMING_SYSTEM_PROMPT = """You are an OT (Operational Technology) naming expert specializing in industrial control systems. Your task is to generate meaningful, descriptive device names that reflect:

1. **The industrial process being performed** - Names should indicate what the device controls or monitors
2. **The device's specific function** - What role does this device play in the process?
3. **The physical location or zone** - Where is this device located?
4. **The control hierarchy** - Is this a main controller, auxiliary, field device, etc.?

## NAMING RULES

1. **Use underscores** to separate words (e.g., "Assembly_Line_Main_PLC")
2. **Keep names under 40 characters** for readability
3. **Include process/area context** (e.g., "Packaging_", "Paint_Booth_", "CNC_Cell_")
4. **Include function context** (e.g., "_Motor_Drive", "_Level_Sensor", "_Controller")
5. **Use sequential numbering only** when multiple identical devices exist in the same area
6. **Ensure ALL names are UNIQUE** - no two devices should have the same name
7. **Be specific** - avoid generic names that don't convey meaning

## GOOD EXAMPLES (Process-Aware)

- "CNC_Cell_1_Main_Controller" (not "PLC-MAIN-01")
- "Paint_Booth_Exhaust_VFD" (not "VFD-01")
- "Conveyor_Zone_A_IO_Module" (not "IO-01")
- "Packaging_Line_Operator_HMI" (not "HMI-01")
- "Assembly_Robot_Servo_X_Axis" (not "SERVO-01")
- "Cooling_Tower_Pump_Drive" (not "VFD-02")
- "Material_Handling_Safety_PLC" (not "PLC-SAFETY-01")
- "Welding_Cell_2_Spot_Welder_IO" (not "ET200SP-01")

## BAD EXAMPLES (Generic)

- "PLC-001", "VFD-02", "SENSOR-003" (too generic, no process context)
- "Device_1", "Controller_A" (meaningless)
- "Siemens_PLC_1" (vendor is not process context)
- "Zone_1_Device_1" (zone alone is not enough)

## RESPONSE FORMAT

Return a JSON object with a "devices" array containing objects with "device_id" and "new_name" keys:

```json
{
  "devices": [
    {"device_id": "device_001", "new_name": "CNC_Cell_1_Main_Controller"},
    {"device_id": "device_002", "new_name": "Assembly_Line_Motor_Drive_1"}
  ]
}
```"""


# ==================== AIDeviceNamer Service ====================


class AIDeviceNamer:
    """AI service for generating contextual, meaningful device names.

    This service uses Claude AI to transform generic device names like
    "PLC-MAIN-01" into meaningful names like "CNC_Machining_Cell_1_Controller"
    based on the industrial context.
    """

    async def enhance_device_names(
        self,
        devices: list[dict[str, Any]],
        context: DeviceNamingContext,
        ai_provider: AIProvider,
    ) -> list[dict[str, Any]]:
        """Enhance device names with AI-generated contextual names.

        Args:
            devices: List of device dictionaries with generic names
            context: Naming context (vertical, description, zones)
            ai_provider: Configured AI provider

        Returns:
            Devices with enhanced, meaningful names

        Raises:
            ValueError: If AI response cannot be parsed
        """
        if not devices:
            return devices

        logger.info(
            f"Enhancing names for {len(devices)} devices "
            f"(vertical={context.vertical}, template={context.template_name})"
        )

        # Build the user prompt with device details
        user_prompt = self._build_user_prompt(devices, context)

        # Call AI
        messages = [
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await ai_provider.chat(
                messages=messages,
                max_tokens=4096,
            )

            # Parse response
            name_mappings = self._parse_ai_response(response)

            # Apply mappings to devices
            enhanced_devices = self._apply_name_mappings(devices, name_mappings)

            # Validate uniqueness (safety net)
            enhanced_devices = self._ensure_unique_names(enhanced_devices)

            logger.info(f"Successfully enhanced {len(enhanced_devices)} device names")
            return enhanced_devices

        except Exception as e:
            logger.error(f"AI device naming failed: {e}")
            raise

    def _build_user_prompt(
        self,
        devices: list[dict[str, Any]],
        context: DeviceNamingContext,
    ) -> str:
        """Build the user prompt for device naming."""
        # Build zone descriptions
        zone_descriptions = []
        zones = context.zones
        if isinstance(zones, dict):
            for zone_id, zone_data in zones.items():
                if isinstance(zone_data, dict):
                    zone_name = zone_data.get("name", zone_id)
                    zone_desc = zone_data.get("description", "")
                    zone_descriptions.append(f"  - {zone_id}: {zone_name} ({zone_desc})")
        zones_text = "\n".join(zone_descriptions) if zone_descriptions else "  - default: Main Process Zone"

        # Build device list
        device_lines = []
        for device in devices:
            device_id = device.get("id", "unknown")
            current_name = device.get("name", "Unnamed")
            device_type = device.get("type", "unknown")
            vendor = device.get("vendor", "unknown")
            role = device.get("role", "")
            zone_id = device.get("zoneId", "default")
            protocols = device.get("protocols", [])

            line = f"""- Device ID: {device_id}
  Current Name: {current_name}
  Type: {device_type}
  Vendor: {vendor}
  Role: {role}
  Zone: {zone_id}
  Protocols: {', '.join(protocols) if protocols else 'none'}"""
            device_lines.append(line)

        devices_text = "\n".join(device_lines)

        # Build full prompt
        prompt = f"""{DEVICE_NAMING_SYSTEM_PROMPT}

---

## SCENARIO CONTEXT

**Vertical:** {context.vertical}
**Template:** {context.template_name}
**Process Description:** {context.template_description}

**Zones:**
{zones_text}

{f"**Additional Context:** {context.process_context}" if context.process_context else ""}

---

## DEVICES TO NAME

{devices_text}

---

Generate meaningful, process-aware names for ALL {len(devices)} devices listed above.
Return a JSON object with a "devices" array. Ensure all names are UNIQUE."""

        return prompt

    def _parse_ai_response(self, response: dict[str, Any]) -> dict[str, str]:
        """Parse AI response to extract name mappings.

        Returns:
            Dictionary mapping device_id to new_name
        """
        # Extract text content from response
        content = response.get("content", [])
        text = ""
        for block in content:
            if block.get("type") == "text":
                text += block.get("text", "")

        # Try to extract JSON from the response
        # Handle cases where AI might wrap JSON in markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
            else:
                raise ValueError(f"No valid JSON found in AI response: {text[:500]}")

        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response JSON: {e}")

        # Validate with Pydantic
        naming_response = DeviceNamingResponse.model_validate(data)

        # Build mapping
        return {item.device_id: item.new_name for item in naming_response.devices}

    def _apply_name_mappings(
        self,
        devices: list[dict[str, Any]],
        name_mappings: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Apply name mappings to devices."""
        result = []
        for device in devices:
            device_copy = device.copy()
            device_id = device.get("id", "")
            if device_id in name_mappings:
                old_name = device_copy.get("name", "")
                new_name = name_mappings[device_id]
                device_copy["name"] = new_name
                logger.debug(f"Renamed device {device_id}: '{old_name}' -> '{new_name}'")
            result.append(device_copy)
        return result

    def _ensure_unique_names(
        self,
        devices: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Ensure all device names are unique, appending suffix if needed.

        This is a safety net in case AI generates duplicate names.
        """
        seen: dict[str, int] = {}
        result = []

        for device in devices:
            device_copy = device.copy()
            name = device_copy.get("name", "Device")

            if name in seen:
                # Append incrementing suffix
                seen[name] += 1
                new_name = f"{name}_{seen[name]}"
                logger.warning(
                    f"Duplicate name '{name}' detected, renaming to '{new_name}'"
                )
                device_copy["name"] = new_name
            else:
                seen[name] = 1

            result.append(device_copy)

        return result
