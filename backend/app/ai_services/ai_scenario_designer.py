# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ai_services.usage_recorder import AIUsageContext

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY

from app.ai_services.scenario_generator import (
    GeneratedDevice,
    GeneratedFlow,
    GeneratedScenario,
    ScenarioGenerator,
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


class AIConduitDesign(BaseModel):
    """Conduit design from AI (IEC 62443 zone-to-zone boundary)."""
    id: str
    name: str
    source_zone: str  # zone id
    target_zone: str  # zone id
    direction: str = "bidirectional"  # bidirectional, a_to_b, b_to_a
    allowed_protocols: list[str] = Field(default_factory=list)
    security_level: str = "standard"  # minimal, standard, high, critical
    description: str | None = None


class AIScenarioDesign(BaseModel):
    """Complete scenario design from AI."""
    vertical: str = "manufacturing"
    recommended_vendors: list[str] = Field(default_factory=list)
    recommended_protocols: list[str] = Field(default_factory=list)
    zones: list[AIZoneDesign] = Field(default_factory=list)
    devices: list[AIDeviceDesign] = Field(default_factory=list)
    flows: list[AIFlowDesign] = Field(default_factory=list)
    conduits: list[AIConduitDesign] = Field(default_factory=list)
    design_rationale: str | None = None


# ==================== Structured Output JSON Schema ====================
# Schema for Claude's output_config (structured outputs).
# Guarantees schema-compliant JSON via constrained decoding — no JSON
# repair or regex extraction needed.  All objects use
# additionalProperties: false and list every field in required (nullable
# fields use anyOf with null).

SCENARIO_DESIGN_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "vertical", "recommended_vendors", "recommended_protocols",
        "zones", "devices", "flows", "conduits", "design_rationale",
    ],
    "properties": {
        "vertical": {"type": "string"},
        "recommended_vendors": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommended_protocols": {
            "type": "array",
            "items": {"type": "string"},
        },
        "zones": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name", "description", "subnet_offset", "level", "vlan"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "subnet_offset": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                    "level": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                    "vlan": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                },
            },
        },
        "devices": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name", "device_type", "vendor", "fingerprint_model",
                    "zone_id", "role", "protocols",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "device_type": {"type": "string"},
                    "vendor": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "fingerprint_model": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "zone_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "role": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "protocols": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "flows": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source_name", "target_name", "protocol",
                    "description", "poll_interval_ms", "pattern",
                ],
                "properties": {
                    "source_name": {"type": "string"},
                    "target_name": {"type": "string"},
                    "protocol": {"type": "string"},
                    "description": {"type": "string"},
                    "poll_interval_ms": {"type": "integer"},
                    "pattern": {"type": "string"},
                },
            },
        },
        "conduits": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id", "name", "source_zone", "target_zone",
                    "direction", "allowed_protocols", "security_level",
                    "description",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "source_zone": {"type": "string"},
                    "target_zone": {"type": "string"},
                    "direction": {
                        "type": "string",
                        "enum": ["bidirectional", "a_to_b", "b_to_a"],
                    },
                    "allowed_protocols": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "security_level": {
                        "type": "string",
                        "enum": ["minimal", "standard", "high", "critical"],
                    },
                    "description": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
            },
        },
        "design_rationale": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
}


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

    # ---- Phased methods (used by streaming endpoint) ----

    async def phase_get_provider(self) -> Any:
        """Phase 1: Get the AI provider.

        Returns:
            AI provider instance

        Raises:
            ValueError: If provider is not configured
        """
        from app.mcp_server.ai_providers import AITask
        return await AIProviderFactory.create(
            self.db, task=AITask.SCENARIO_GENERATION,
        )

    def phase_build_prompts(
        self,
        description: str,
        vertical: str | None = None,
        preferred_vendors: list[str] | None = None,
        preferred_protocols: list[str] | None = None,
        total_device_count: int | None = None,
        device_counts: dict[str, int] | None = None,
        cell_isolation_mode: str = "off",
    ) -> tuple[str, str]:
        """Phase 2: Build system and user prompts.

        Returns:
            (system_prompt, user_prompt) tuple
        """
        system_prompt = self._get_system_prompt(
            vertical=vertical,
            preferred_vendors=preferred_vendors,
            preferred_protocols=preferred_protocols,
        )
        user_prompt = self._build_design_prompt(
            description=description,
            vertical=vertical,
            preferred_vendors=preferred_vendors,
            preferred_protocols=preferred_protocols,
            total_device_count=total_device_count,
            device_counts=device_counts,
            cell_isolation_mode=cell_isolation_mode,
        )
        return system_prompt, user_prompt

    async def phase_call_ai(
        self,
        provider: Any,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 32768,
        total_device_count: int | None = None,
        tracking: "AIUsageContext | None" = None,
    ) -> dict[str, Any]:
        """Phase 3: Call the AI provider.

        Uses structured outputs (output_config with json_schema) to guarantee
        schema-compliant JSON responses via constrained decoding.

        Returns:
            Raw AI response dict

        Raises:
            RuntimeError: On timeout, truncation, refusal, or API error
        """
        try:
            response = await asyncio.wait_for(
                provider.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=max_tokens,
                    output_config={
                        "format": {
                            "type": "json_schema",
                            "schema": SCENARIO_DESIGN_JSON_SCHEMA,
                        },
                    },
                    skills=[
                        "packetarch-scenario-authoring",
                        "packetarch-fingerprint-validator",
                        "packetarch-device-naming",
                    ],
                    tracking=tracking,
                ),
                timeout=300.0,
            )
        except asyncio.TimeoutError:
            logger.warning("AI design timed out after 300 seconds")
            raise RuntimeError(
                "AI scenario generation timed out. Try reducing the number of devices "
                "or simplifying the scenario description."
            )
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            raise RuntimeError(f"AI scenario generation failed: {e}") from e

        # Check for refusal (safety-related)
        stop_reason = response.get("stop_reason")
        if stop_reason == "refusal":
            logger.warning("AI refused to generate scenario")
            raise RuntimeError(
                "AI declined to generate this scenario. Try rephrasing the "
                "description or adjusting the parameters."
            )

        # Check for truncation
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

        # Log usage for monitoring
        usage = response.get("usage", {})
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_create = usage.get("cache_creation_input_tokens", 0)
        logger.info(
            f"AI scenario generation completed: "
            f"input={usage.get('input_tokens', 0)}, "
            f"output={usage.get('output_tokens', 0)}, "
            f"cache_read={cache_read}, cache_create={cache_create}"
        )

        return response

    def phase_parse_response(self, response: dict[str, Any]) -> "AIScenarioDesign":
        """Phase 4: Parse the AI response JSON.

        Returns:
            Parsed AIDesignSpec
        """
        try:
            return self._parse_ai_response(response)
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise RuntimeError(f"AI returned invalid response: {e}") from e

    def phase_build_scenario(
        self,
        ai_design: "AIScenarioDesign",
        name: str | None,
        description: str,
        duration_ms: int,
        vertical: str | None,
        cell_isolation_mode: str = "off",
    ) -> AIDesignResult:
        """Phase 5: Build the scenario from parsed AI design.

        Returns:
            AIDesignResult with generated scenario
        """
        try:
            scenario = self._build_scenario_from_ai_design(
                ai_design=ai_design,
                name=name,
                description=description,
                duration_ms=duration_ms,
                vertical=vertical or ai_design.vertical,
            )
            # Stamp the isolation mode into metadata so the route can
            # mirror it into definition.cell_isolation when persisting.
            if cell_isolation_mode and cell_isolation_mode != "off":
                scenario.metadata["cell_isolation"] = {
                    "mode": cell_isolation_mode,
                    "applies_to_levels": [0, 1, 2],
                }
            return AIDesignResult(
                scenario=scenario,
                ai_enhanced=True,
                ai_features=["vendors", "protocols", "device_names", "flow_descriptions", "zones", "conduits"],
                design_rationale=ai_design.design_rationale,
            )
        except Exception as e:
            logger.error(f"Failed to build scenario from AI design: {e}")
            raise RuntimeError(f"Failed to build scenario from AI design: {e}") from e

    # ---- Original monolithic method (backwards compat) ----

    async def design_scenario_via_archetype(
        self,
        description: str,
        name: str | None = None,
        duration_ms: int = 300000,
        vertical: str | None = None,
        scale: str | None = None,
        preferred_vendors: list[str] | None = None,
        tracking: "AIUsageContext | None" = None,
    ) -> AIDesignResult:
        """Architecture-rail design path (Phase 6 of the rollout).

        Asks the AI to pick an archetype + vendor profile + scale tier
        from the catalog, then materializes the scenario via
        `generate_from_archetype()`. Output is realism-clean by
        construction — nothing the AI can do gets past the audit.

        This path is preferred over the freeform `design_scenario()` for
        wizard-class UX. The freeform path is retained for users who
        want full control or for verticals not yet on the archetype
        rail.
        """
        from app.services.architecture import (
            ScaleTier,
            VendorProfile,
            list_archetypes,
        )
        from app.services.architecture.scenario_generator import (
            generate_from_archetype,
        )

        # Phase 1: provider.
        try:
            provider = await self.phase_get_provider()
        except ValueError as e:
            logger.warning(f"AI provider not available for archetype path: {e}")
            return self._fallback_to_rules(
                description=description,
                name=name,
                duration_ms=duration_ms,
                vertical=vertical,
                preferred_vendors=preferred_vendors,
                preferred_protocols=None,
                total_device_count=None,
                device_counts=None,
                reason="AI provider not configured",
            )

        # Phase 2: Build a tight archetype-selection prompt.
        archetype_catalog = "\n".join(
            f"  - {a.id} (vertical={a.vertical}, pattern={a.pattern.value}, "
            f"default_vendor={a.default_vendor_profile.value}): {a.description}"
            for a in list_archetypes()
        )
        vendor_options = ", ".join(vp.value for vp in VendorProfile)
        scale_options = ", ".join(s.value for s in ScaleTier)

        # Build a zone-id list per archetype so the AI knows what cells /
        # units / bays / stations / intersections / racks it can theme.
        # Most archetypes have at most 4-12 of any one zone kind; we list
        # the kinds for each archetype so the AI picks themes for the
        # right slot ids.
        zone_id_hints_lines = []
        for a in list_archetypes():
            zone_kinds: dict[str, list[str]] = {}
            for z in a.zones:
                # Group by zone-kind prefix (cell, bay, unit, ...) so the
                # AI sees "cell1..cellN" rather than the full enumeration.
                stem = z.id.rstrip("0123456789")
                zone_kinds.setdefault(stem, []).append(z.id)
            if any(len(v) > 1 for v in zone_kinds.values()):
                kinds_str = ", ".join(
                    f"{stem}1..{stem}{len(ids)}"
                    for stem, ids in zone_kinds.items()
                    if len(ids) > 1
                )
                zone_id_hints_lines.append(f"  - {a.id}: {kinds_str}")

        zone_id_hints = "\n".join(zone_id_hints_lines)

        system_prompt = (
            "You are a Cisco Cyber Vision OT-network architect. Given a "
            "user's natural-language scenario description, your job is to "
            "pick:\n"
            "  1. The closest matching archetype from the catalog.\n"
            "  2. The most-appropriate vendor profile.\n"
            "  3. The right scale tier (DEMO=tiny pilot, SMALL=small site, "
            "MEDIUM=standard plant, LARGE=enterprise, MULTI_SITE=many sites).\n"
            "  4. A semantic theme for each multi-instance zone (cell, bay, "
            "unit, station, intersection, rack) so devices land with "
            "meaningful names. For 'candy factory' the cells become "
            "Mixing / Cooking / Wrapping; for 'oil refinery' the units "
            "become Crude_Distillation / Hydrocracker / Reformer; etc.\n\n"
            "Constraints:\n"
            "  - The vendor profile MUST be in the archetype's "
            "`supported_vendor_profiles`.\n"
            "  - Pick the archetype that best matches the user's vertical "
            "and architecture pattern (DCS vs cell vs master/remote vs "
            "BAS vs ATMS vs DCIM).\n"
            "  - Be conservative on scale; users can always override.\n"
            "  - Zone themes are short snake_case identifiers (e.g. "
            "'Sugar_Mixing', 'CNC_Machining'). One per zone id. They "
            "replace the generic stem ('Cell1_…' becomes 'Sugar_Mixing_…') "
            "in device names. Provide themes ONLY for zone ids that exist "
            "for the chosen archetype.\n\n"
            f"Available archetypes:\n{archetype_catalog}\n\n"
            f"Multi-instance zone ids per archetype:\n{zone_id_hints}\n\n"
            f"Available vendor profiles: {vendor_options}\n"
            f"Available scale tiers: {scale_options}\n\n"
            "Respond with ONLY a JSON object:\n"
            '  {"archetype_id": "...", "vendor_profile": "...", '
            '"scale": "...", "zone_themes": {"cell1": "Mixing", '
            '"cell2": "Cooking", ...}, "reasoning": "one short sentence"}'
        )

        user_prompt_lines = [f"Scenario description: {description}"]
        if vertical:
            user_prompt_lines.append(f"User-specified vertical: {vertical}")
        if scale:
            user_prompt_lines.append(f"User-specified scale: {scale}")
        if preferred_vendors:
            user_prompt_lines.append(
                f"User-preferred vendors: {', '.join(preferred_vendors)}"
            )
        user_prompt = "\n".join(user_prompt_lines)

        # Phase 3: Call AI (smaller payload than full freeform design).
        response = await self.phase_call_ai(
            provider=provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            total_device_count=None,
            tracking=tracking,
        )

        # Phase 4: Parse {archetype_id, vendor_profile, scale}.
        import json
        raw = response.get("content") or response.get("text") or ""
        if isinstance(raw, list):
            # Anthropic SDK returns content blocks; concat text.
            raw = "".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in raw
            )
        try:
            # Locate the JSON object even if the model wrapped it in prose.
            start = raw.find("{")
            end = raw.rfind("}")
            if start < 0 or end < 0:
                raise ValueError(f"no JSON in AI response: {raw[:200]}")
            choice = json.loads(raw[start:end + 1])
        except Exception as e:  # noqa: BLE001
            logger.warning("Archetype selection parse failed: %s", e)
            return self._fallback_to_rules(
                description=description,
                name=name,
                duration_ms=duration_ms,
                vertical=vertical,
                preferred_vendors=preferred_vendors,
                preferred_protocols=None,
                total_device_count=None,
                device_counts=None,
                reason=f"AI archetype-selection parse failed: {e}",
            )

        archetype_id = choice.get("archetype_id")
        vendor_profile_str = choice.get("vendor_profile")
        scale_str = choice.get("scale", "medium")
        reasoning = choice.get("reasoning", "")
        # Sanitize AI-supplied zone themes — strip any non-string values
        # and normalize to safe identifier-ish strings before passing
        # them to the generator.
        raw_themes = choice.get("zone_themes") or {}
        zone_themes: dict[str, str] = {}
        if isinstance(raw_themes, dict):
            for k, v in raw_themes.items():
                if isinstance(k, str) and isinstance(v, str) and v.strip():
                    zone_themes[k] = v.strip().replace(" ", "_")

        # Phase 5: Validate + materialize.
        try:
            vendor_profile = VendorProfile(vendor_profile_str)
            scale_tier = ScaleTier(scale_str)
        except ValueError as e:
            logger.warning("Archetype selection invalid: %s", e)
            return self._fallback_to_rules(
                description=description,
                name=name,
                duration_ms=duration_ms,
                vertical=vertical,
                preferred_vendors=preferred_vendors,
                preferred_protocols=None,
                total_device_count=None,
                device_counts=None,
                reason=f"AI returned invalid archetype/vendor/scale: {e}",
            )

        try:
            definition = generate_from_archetype(
                archetype_id,
                vendor_profile=vendor_profile,
                scale=scale_tier,
                overrides={"zone_themes": zone_themes} if zone_themes else None,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Archetype materialization failed")
            return self._fallback_to_rules(
                description=description,
                name=name,
                duration_ms=duration_ms,
                vertical=vertical,
                preferred_vendors=preferred_vendors,
                preferred_protocols=None,
                total_device_count=None,
                device_counts=None,
                reason=f"Archetype materialization failed: {e}",
            )

        # Convert the generator's dict-shaped definition into the
        # GeneratedScenario / GeneratedDevice / GeneratedFlow dataclass
        # tree the rest of the AI pipeline expects.
        from app.ai_services.scenario_generator import (
            GeneratedDevice,
            GeneratedFlow,
            GeneratedScenario,
        )
        import uuid

        gen_devices: list[GeneratedDevice] = []
        for did, dev in definition.get("devices", {}).items():
            net = dev.get("network") or {}
            gen_devices.append(GeneratedDevice(
                device_id=did,
                device_type=dev.get("type", "device"),
                name=dev.get("name", did),
                vendor=dev.get("vendor"),
                model=dev.get("fingerprintModel"),
                ip_address=net.get("ipAddress") or net.get("ip_address") or "",
                mac_address=net.get("macAddress") or net.get("mac_address") or "",
                zone=dev.get("zoneId", ""),
                protocols=list(dev.get("protocols") or []),
                fingerprint_model=dev.get("fingerprintModel"),
                fingerprint_data=dev.get("vendorFingerprint"),
            ))

        gen_flows: list[GeneratedFlow] = []
        for fid, fl in definition.get("flows", {}).items():
            timing = fl.get("timing") or {}
            gen_flows.append(GeneratedFlow(
                flow_id=fid,
                source_device_id=fl.get("sourceDeviceId", ""),
                destination_device_id=fl.get("targetDeviceId", ""),
                protocol=fl.get("protocol", "snmp"),
                poll_interval_ms=int(timing.get("intervalMs", 1000)),
                description=(fl.get("config") or {}).get("pattern", "") or "",
            ))

        meta = definition.get("_generator_meta") or {}
        scenario = GeneratedScenario(
            scenario_id=str(uuid.uuid4()),
            name=name or f"AI: {description[:50]}",
            description=description,
            vertical=vertical or meta.get("vertical", "unknown"),
            devices=gen_devices,
            flows=gen_flows,
            zones=list(definition.get("zones", {}).values())
                if isinstance(definition.get("zones"), dict)
                else (definition.get("zones") or []),
            conduits=definition.get("conduits") or {},
            duration_ms=duration_ms,
            metadata={
                "ai_enhanced": True,
                "rail": "archetype",
                "archetype_id": archetype_id,
                "vendor_profile": vendor_profile.value,
                "scale": scale_tier.value,
                "reasoning": reasoning,
                "range_index": self.range_index,
                "ip_range": f"10.{self.range_index}.0.0/16",
            },
        )
        return AIDesignResult(
            scenario=scenario,
            ai_enhanced=True,
            ai_features=["archetype_selection", "matrix_driven_flows"],
            design_rationale=(
                f"Archetype rail: {archetype_id} "
                f"(vendor={vendor_profile.value}, scale={scale_tier.value}). "
                f"{reasoning}"
            ),
        )

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
        cell_isolation_mode: str = "off",
        tracking: "AIUsageContext | None" = None,
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
        # Phase 1: Get AI provider
        try:
            provider = await self.phase_get_provider()
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

        # Phase 2: Build prompts
        system_prompt, user_prompt = self.phase_build_prompts(
            description=description,
            vertical=vertical,
            preferred_vendors=preferred_vendors,
            preferred_protocols=preferred_protocols,
            total_device_count=total_device_count,
            device_counts=device_counts,
            cell_isolation_mode=cell_isolation_mode,
        )

        # Phase 3: Call AI
        response = await self.phase_call_ai(
            provider=provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            total_device_count=total_device_count,
            tracking=tracking,
        )

        # Phase 4: Parse response
        ai_design = self.phase_parse_response(response)

        # Phase 5: Build scenario
        return self.phase_build_scenario(
            ai_design=ai_design,
            name=name,
            description=description,
            duration_ms=duration_ms,
            vertical=vertical,
            cell_isolation_mode=cell_isolation_mode,
        )

    def _get_system_prompt(
        self,
        vertical: str | None = None,
        preferred_vendors: list[str] | None = None,
        preferred_protocols: list[str] | None = None,
    ) -> str:
        """Get the system prompt for Claude with pre-filtered fingerprints."""
        # Get available fingerprints with complete protocol identity data
        fingerprints = get_all_fingerprints()

        # Pre-filter fingerprints by user context to reduce prompt size
        if preferred_vendors or vertical or preferred_protocols:
            filtered = []
            vendor_lower = {v.lower() for v in (preferred_vendors or [])}
            proto_set = set(preferred_protocols or [])
            for fp in fingerprints:
                fp_vendor = (fp.get("vendor") or "").lower()
                fp_protos = set(fp.get("supported_protocols") or [])
                # Include if vendor matches user preference
                if vendor_lower and fp_vendor in vendor_lower:
                    filtered.append(fp)
                    continue
                # Include if fingerprint supports a preferred protocol
                if proto_set and fp_protos & proto_set:
                    filtered.append(fp)
                    continue
                # Include if fingerprint's verticals match
                fp_verticals = fp.get("vertical_hints") or []
                if vertical and vertical in fp_verticals:
                    filtered.append(fp)
                    continue
            # Use filtered list if it has enough variety, otherwise keep all
            if len(filtered) >= 5:
                fingerprints = filtered

        # Group fingerprints by vendor, showing model and supported protocols
        vendor_fingerprints: dict[str, list[str]] = {}
        for fp in fingerprints:
            vendor = fp.get("vendor", "Unknown")
            model = fp.get("model", "Unknown")
            family = fp.get("vendor_family", "")
            fp.get("supported_protocols", [])

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

        # Format as organized list with protocols shown (all models included)
        fingerprint_lines = []
        for vendor in sorted(vendor_fingerprints.keys()):
            fingerprint_lines.append(f"**{vendor}**:")
            for m in vendor_fingerprints[vendor]:
                fingerprint_lines.append(f"  - {m}")

        fingerprint_list = "\n".join(fingerprint_lines)

        # Only the dynamic, per-request fingerprint catalog lives in the
        # system prompt. Static authoring rules (Purdue, conduit
        # semantics, naming, flow coverage) come from the
        # ``packetarch-scenario-authoring`` +
        # ``packetarch-fingerprint-validator`` skills wired at the call
        # site in ``phase_call_ai()``.
        return f"""## Available Vendor Fingerprints (MUST use for fingerprint_model field)
Each model shows its supported protocols after the arrow (→). ONLY use
protocols listed for that model. Do NOT invent model names or use
"Generic" — only use exact models from the catalog below.

{fingerprint_list}

Recall from the authoring skill: `fingerprint_model` is an exact
string, protocols must be a subset of what the arrow lists, and cross-
zone flows need matching conduits."""

    def _build_design_prompt(
        self,
        description: str,
        vertical: str | None,
        preferred_vendors: list[str] | None,
        preferred_protocols: list[str] | None,
        total_device_count: int | None,
        device_counts: dict[str, int] | None,
        cell_isolation_mode: str = "off",
    ) -> str:
        """Build the user prompt for scenario design."""
        constraints = []

        # Cell-isolation mode is one of the highest-leverage constraints
        # because it changes the *shape* of the flow graph, so call it out
        # at the top. The skill body has the full rules.
        if cell_isolation_mode == "strict_northbound":
            constraints.append(
                "Cell isolation: STRICT_NORTHBOUND — author NO flows whose "
                "source and destination zones are both at Purdue level <= 2 "
                "(and not the same zone). Cells (L0-L2) communicate only "
                "northbound to L3+ zones. Do NOT author cell↔cell conduits."
            )
        elif cell_isolation_mode == "conduit_gated":
            constraints.append(
                "Cell isolation: CONDUIT_GATED — every flow whose source and "
                "destination zones are both L0-L2 cells (and not the same "
                "zone) MUST have a matching conduit listing the flow's "
                "protocol in allowed_protocols."
            )

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

    def _parse_ai_response(self, response: dict[str, Any]) -> AIScenarioDesign:
        """Parse and validate AI response.

        With structured outputs (output_config.format.json_schema), the API
        guarantees schema-compliant JSON in response.content[0].text.  We
        still validate via Pydantic for field normalization (clean_name,
        normalize_device_type) and to catch edge cases (refusal, truncation).
        """
        content = response.get("content", [])
        text = ""
        for block in content:
            if block.get("type") == "text":
                text += block.get("text", "")

        if not text:
            raise ValueError("AI response contained no text content")

        logger.debug(f"AI response length: {len(text)} chars")

        try:
            data = json.loads(text)
            return AIScenarioDesign.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            # Structured outputs should prevent this, but handle gracefully.
            # Try extracting JSON object if there's surrounding text.
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    data = json.loads(text[start:end])
                    logger.info("Parsed AI response using JSON extraction fallback")
                    return AIScenarioDesign.model_validate(data)
                except Exception:
                    pass

            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Response tail: {text[-1500:]}")
            raise ValueError(f"Could not parse AI JSON response: {e}") from e

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

        # Build conduits from AI design, then backfill missing cross-zone conduits
        conduits = self._build_conduits(ai_design, zones, devices, flows, device_name_to_id)

        # Create scenario
        scenario = GeneratedScenario(
            scenario_id=str(uuid.uuid4()),
            name=name or f"{vertical.replace('_', ' ').title()} Scenario",
            description=description,
            vertical=vertical,
            devices=devices,
            flows=flows,
            zones=zones,
            conduits=conduits,
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
            f"{len(devices)} devices, {len(flows)} flows, and {len(conduits)} conduits"
        )
        return scenario

    def _build_conduits(
        self,
        ai_design: "AIScenarioDesign",
        zones: list[dict[str, Any]],
        devices: list[GeneratedDevice],
        flows: list[GeneratedFlow],
        device_name_to_id: dict[str, str],
    ) -> dict[str, dict[str, Any]]:
        """Build conduit dict from AI-generated conduits, backfilling any missing cross-zone pairs.

        Converts AI conduit designs to the camelCase dict format used by the
        scenario definition, then ensures every cross-zone flow has a covering
        conduit by auto-generating missing ones via Purdue adjacency defaults.

        Args:
            ai_design: Parsed AI design with conduits list
            zones: Zone list (already built)
            devices: Device list (already built)
            flows: Flow list (already built, including orphan-fix flows)
            device_name_to_id: Mapping of device name -> device_id

        Returns:
            Dict of conduit_id -> conduit definition (camelCase keys)
        """
        zone_id_set = {z["id"] for z in zones}
        conduits: dict[str, dict[str, Any]] = {}

        # Convert AI-generated conduits
        for ai_conduit in ai_design.conduits:
            # Skip conduits referencing non-existent zones
            if ai_conduit.source_zone not in zone_id_set:
                logger.warning(
                    f"Skipping conduit '{ai_conduit.name}': source_zone "
                    f"'{ai_conduit.source_zone}' not found"
                )
                continue
            if ai_conduit.target_zone not in zone_id_set:
                logger.warning(
                    f"Skipping conduit '{ai_conduit.name}': target_zone "
                    f"'{ai_conduit.target_zone}' not found"
                )
                continue

            conduits[ai_conduit.id] = {
                "id": ai_conduit.id,
                "name": ai_conduit.name,
                "sourceZoneId": ai_conduit.source_zone,
                "targetZoneId": ai_conduit.target_zone,
                "direction": ai_conduit.direction,
                "allowedProtocols": ai_conduit.allowed_protocols,
                "securityLevel": ai_conduit.security_level,
                "description": ai_conduit.description,
                "autoGenerated": False,
            }

        # Determine which zone pairs already have conduits (order-agnostic)
        covered_pairs: set[tuple[str, str]] = set()
        for c in conduits.values():
            pair = tuple(sorted([c["sourceZoneId"], c["targetZoneId"]]))
            covered_pairs.add(pair)

        # Build device_id -> zone_id lookup
        device_zone_map: dict[str, str] = {}
        for zone in zones:
            for did in zone.get("device_ids", []):
                device_zone_map[did] = zone["id"]

        # Find cross-zone flow pairs that lack a conduit
        missing_pairs: dict[tuple[str, str], set[str]] = {}  # (z1, z2) -> protocols
        for flow in flows:
            src_zone = device_zone_map.get(flow.source_device_id)
            dst_zone = device_zone_map.get(flow.destination_device_id)
            if not src_zone or not dst_zone or src_zone == dst_zone:
                continue
            pair = tuple(sorted([src_zone, dst_zone]))
            if pair not in covered_pairs:
                if pair not in missing_pairs:
                    missing_pairs[pair] = set()
                missing_pairs[pair].add(flow.protocol)

        # Auto-generate conduits for missing cross-zone pairs
        if missing_pairs:
            zone_name_map = {z["id"]: z.get("name", z["id"]) for z in zones}
            conduit_idx = len(conduits)
            for (z1, z2), protocols in missing_pairs.items():
                conduit_idx += 1
                cid = f"conduit_{conduit_idx:03d}"
                z1_name = zone_name_map.get(z1, z1)
                z2_name = zone_name_map.get(z2, z2)
                conduits[cid] = {
                    "id": cid,
                    "name": f"{z1_name} \u2194 {z2_name}",
                    "sourceZoneId": z1,
                    "targetZoneId": z2,
                    "direction": "bidirectional",
                    "allowedProtocols": sorted(protocols),
                    "securityLevel": "standard",
                    "description": None,
                    "autoGenerated": True,
                }
                covered_pairs.add((z1, z2))

            logger.info(
                f"Auto-generated {len(missing_pairs)} conduit(s) for "
                f"cross-zone flows missing AI-designed conduits"
            )

        logger.info(
            f"Built {len(conduits)} conduit(s) "
            f"({len(ai_design.conduits)} from AI, "
            f"{len(conduits) - len([c for c in conduits.values() if not c.get('autoGenerated')])} auto-generated)"
        )
        return conduits

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
        [d for d in devices if d.device_type in self.SUPERVISORY_TYPES]

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
        {d.device_id: d for d in devices}

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
