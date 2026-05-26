# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""LLM-driven site identity generator.

One Claude call per scenario at create-time. Produces a SiteIdentity
that locks in: site code, plant name, location, operator, naming
convention, per-role name patterns, per-zone short codes.

The generator is deterministic-fallback-friendly: if the LLM call
fails, raises, or returns invalid output, callers should fall back
to `deterministic_site_identity()` from site_identity.py.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ai_services.usage_recorder import AIUsageContext

from app.mcp_server.ai_providers.base import AIProvider
from app.services.architecture.site_identity import (
    DEFAULT_ROLE_PATTERNS,
    SiteIdentity,
)


logger = logging.getLogger(__name__)


SITE_IDENTITY_SKILL = "packetarch-device-naming"


def _build_user_prompt(
    *,
    vertical: str,
    template_name: str,
    template_description: str,
    archetype_id: str | None,
    zones: dict[str, dict[str, Any]],
    role_inventory: dict[str, int],
    avoid_site_codes: list[str],
    process_context: str | None = None,
) -> str:
    zone_lines = []
    for zid, zdata in (zones or {}).items():
        if isinstance(zdata, dict):
            zname = zdata.get("name", zid)
            zdesc = zdata.get("description", "")
            zone_lines.append(f"  - {zid} (display: {zname}) — {zdesc}")
        else:
            zone_lines.append(f"  - {zid}")
    zones_text = "\n".join(zone_lines) if zone_lines else "  - (none declared)"

    role_lines = [f"  - {role}: {count}" for role, count in sorted(role_inventory.items())]
    roles_text = "\n".join(role_lines) if role_lines else "  - (none)"

    avoid_text = (
        "\n".join(f"  - {c}" for c in avoid_site_codes)
        if avoid_site_codes
        else "  (no constraints — any realistic site code is fine)"
    )

    default_patterns_json = json.dumps(DEFAULT_ROLE_PATTERNS, indent=2)

    has_user_theme = bool(process_context and process_context.strip())
    user_context_block = (
        f"\n**USER-SUPPLIED SITE/PROCESS THEME — HIGHEST PRIORITY.**\n"
        f"Re-theme the ENTIRE scenario as if it is exactly this kind of\n"
        f"facility. The user's words override every default below. The\n"
        f"existing zone display names and template name describe the\n"
        f"ORIGINAL scenario shape, not the desired theme — ignore their\n"
        f"industrial flavor and replace it with the user theme. Pick:\n"
        f"  - a site_code, plant_name, and operator that read like a\n"
        f"    real plant of THIS kind\n"
        f"  - zone_codes (3-8 char tokens) that match THIS process\n"
        f"    (e.g. for a bakery: MIX / PROOF / BAKE / PACK / DMZ / OPS)\n"
        f"  - zone_names (human-readable display names for each zone,\n"
        f"    rewriting the originals into the new theme)\n"
        f"  - role_patterns that, where natural, use process-themed\n"
        f"    abbreviations instead of the manufacturing defaults\n"
        f"User theme:\n"
        f"  {process_context.strip()}\n"
        if has_user_theme
        else ""
    )

    prompt = f"""## SCENARIO CONTEXT

**Vertical:** {vertical}
**Template:** {template_name}
**Archetype:** {archetype_id or "(none — legacy template)"}
**Process description:** {template_description}
{user_context_block}
**Zones in this scenario:**
{zones_text}

**Role inventory (role_id: count):**
{roles_text}

**Site codes already taken by other scenarios on this PacketArch
install (DO NOT reuse any of these):**
{avoid_text}

## DEFAULT ROLE NAMING PATTERNS

These are the platform defaults. You MAY override any of them in your
output. Slots available in patterns: {{site}}, {{zone}}, {{n}}, {{nn}}, {{nnn}}, {{vendor}}, {{role_abbr}}.

```json
{default_patterns_json}
```

## TASK

Produce a JSON object that describes the SITE IDENTITY for this
scenario. Pretend this is one specific real plant of the kind described
above. Pick a realistic city, real-feeling operator name, plant
naming convention. Make every scenario you encounter feel like a
DIFFERENT real plant. Do not reuse generic placeholders.

Constraints:
  - `site_code` MUST NOT appear in the "already taken" list above.
  - `site_code` is short (2-12 chars), uppercase, hyphenable. Examples:
    "RR-P1", "AUS01", "TSV-FAB-1", "PNW-SUB1", "U2-NORTH".
  - `zone_codes` MUST map every zone id listed above to a short
    uppercase token (max 8 chars), suitable for embedding in device
    names.
  - `role_patterns` MUST include an entry for every role in the role
    inventory above. Use the slots; the renamer applies them
    deterministically with per-(zone, role) counters.
  - Pattern format MUST be valid Python format() strings using the
    slots shown above.
  - Pick a `naming_style` tag: one of "code_only", "site_role_idx",
    "vendor_prefixed", "hierarchical".
  - Include an optional `domain_suffix` (DNS-style FQDN suffix). It
    is OK to omit it (return null) if the site convention is bare
    hostnames.

Return ONLY a JSON object with this exact shape:

```json
{{
  "site_code": "...",
  "plant_name": "...",
  "location": "City, State/Region, Country",
  "operator": "Company name",
  "industry_context": "one-line context",
  "domain_suffix": "rr.example.com" or null,
  "naming_style": "site_role_idx",
  "zone_codes": {{ "zone_id_1": "Z1", "zone_id_2": "Z2", ... }},
  "zone_names": {{ "zone_id_1": "Display Name 1", "zone_id_2": "Display Name 2", ... }},
  "role_patterns": {{ "role_id": "{{site}}-...-{{nnn}}", ... }}
}}
```

`zone_names` is the human-readable display name for each zone after
re-theming. Include an entry for every zone id. When no user theme is
provided, you MAY copy each zone's existing display name verbatim.

No prose. No markdown outside the json block.
"""
    return prompt


def _parse_response(text: str) -> dict[str, Any]:
    # tolerate fenced or bare JSON
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        text = m.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]
    return json.loads(text)


def _validate_and_complete(
    data: dict[str, Any],
    *,
    role_inventory: dict[str, int],
    zone_ids: list[str],
) -> dict[str, Any]:
    """Backfill missing role_patterns/zone_codes with platform defaults
    so we still get a usable identity even if the LLM forgets a few."""
    role_patterns = dict(data.get("role_patterns") or {})
    for role in role_inventory:
        if role not in role_patterns and role in DEFAULT_ROLE_PATTERNS:
            role_patterns[role] = DEFAULT_ROLE_PATTERNS[role]
    data["role_patterns"] = role_patterns

    zone_codes = dict(data.get("zone_codes") or {})
    from app.services.architecture.site_identity import _derive_zone_code
    for zid in zone_ids:
        if zid not in zone_codes:
            zone_codes[zid] = _derive_zone_code(zid)
    data["zone_codes"] = zone_codes

    return data


async def generate_site_identity(
    *,
    ai_provider: AIProvider,
    vertical: str,
    template_name: str,
    template_description: str,
    archetype_id: str | None,
    zones: dict[str, dict[str, Any]],
    role_inventory: dict[str, int],
    avoid_site_codes: list[str],
    process_context: str | None = None,
    tracking: "AIUsageContext | None" = None,
) -> SiteIdentity:
    """Call Claude (or configured provider) to produce a SiteIdentity.

    Raises on failure — callers should catch and fall back to the
    deterministic identity.
    """
    zone_ids = list((zones or {}).keys())
    prompt = _build_user_prompt(
        vertical=vertical,
        template_name=template_name,
        template_description=template_description,
        archetype_id=archetype_id,
        zones=zones,
        role_inventory=role_inventory,
        avoid_site_codes=avoid_site_codes,
        process_context=process_context,
    )

    response = await ai_provider.chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        skills=[SITE_IDENTITY_SKILL],
        tracking=tracking,
    )

    text = ""
    for block in response.get("content", []) or []:
        if block.get("type") == "text":
            text += block.get("text", "")

    data = _parse_response(text)
    data = _validate_and_complete(
        data,
        role_inventory=role_inventory,
        zone_ids=zone_ids,
    )

    identity = SiteIdentity.from_dict({**data, "source": "llm"})

    if not identity.site_code or identity.site_code in set(avoid_site_codes):
        raise ValueError(
            f"LLM returned invalid/duplicate site_code {identity.site_code!r}; "
            f"falling back to deterministic identity"
        )

    logger.info(
        "Generated LLM site identity: %s / %s (%s)",
        identity.site_code, identity.plant_name, identity.location,
    )
    return identity
