# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Provision Cyber Vision presets + zone groups from a PacketArch scenario.

Two-phase, mirroring the operator-built "Segmented Manufacturing" reference:

1. ``provision_preset`` — create a CV preset scoped to the scenario's /16,
   immediately, so the operator sees it right away.
2. ``provision_groups`` — after CV has had time to aggregate the simulated
   traffic, poll the preset until the discovered-device count stabilises, then
   create one CV group per scenario zone and assign the matched devices.

State is persisted on ``scenario.definition["cyber_vision"]``.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text

from app.core.name_normalize import normalize_acronyms
from app.models.ip_range_allocation import IPRangeAllocation
from app.models.scenario import Scenario
from app.services.cyber_vision_service import (
    CyberVisionService,
    cv_service_from_settings,
    is_broadcast_multicast,
    normalize_mac,
)
from app.services.cyber_vision_v1_service import cv_v1_service_from_settings

logger = logging.getLogger(__name__)

CV_STATE_KEY = "cyber_vision"

# Cyber Vision caps preset descriptions at 180 characters.
PRESET_DESCRIPTION_LIMIT = 180

# Shared group that collects broadcast/multicast endpoints (excluded from
# every per-scenario preset, mirroring the reference preset).
BROADCAST_GROUP_LABEL = "Broadcast"

# Industrial-impact (0-4) by zone security level, with a Purdue-level fallback.
_SECURITY_LEVEL_CRITICALNESS = {"critical": 4, "high": 3, "standard": 2, "minimal": 1}
# Neutral fallback / shared-group color (used for Broadcast and unknown verticals).
_GROUP_COLOR = "#06a2c9"

# Per-vertical zone-group colors, mirroring the frontend `verticalConfig`
# (frontend/src/components/scenarios/scenarioConstants.tsx) so CV groups are
# tinted to match how the vertical is shown everywhere else in PacketArch.
VERTICAL_GROUP_COLORS = {
    "manufacturing": "#6CC04A",
    "water_wastewater": "#00BCEB",
    "energy_power": "#FBAB18",
    "oil_gas": "#FF7043",
    "transportation": "#9C27B0",
    "building_automation": "#00BCD4",
    "distribution_logistics": "#78909C",
    # tolerant aliases for legacy / short vertical keys
    "water": "#00BCEB",
    "energy": "#FBAB18",
    "building": "#00BCD4",
}


def _color_for_vertical(vertical: str | None) -> str:
    """CV group color for a scenario's vertical (neutral fallback if unknown)."""
    if not vertical:
        return _GROUP_COLOR
    return VERTICAL_GROUP_COLORS.get(vertical.strip().lower(), _GROUP_COLOR)


# Cyber Vision caps group labels at 60 characters.
GROUP_LABEL_LIMIT = 60

# CV's new-UI Organization Hierarchy caps level names at just 20 characters —
# much stricter than Groups (60) or presets (100), and NOT documented in the
# OpenAPI spec (confirmed live: CV rejects longer names with "only 20
# characters allowed for name"; re-confirmed on CV 5.5.x). It also rejects
# non-ASCII characters (confirmed live: an "…" ellipsis or an em dash gets
# "Name is invalid"). The full-length _group_label value is still used for the
# matching CV Group/custom network, so the old-UI/new-UI names can visibly
# diverge when a zone or scenario name is long — that's a real CV constraint,
# not a bug.
OH_LEVEL_NAME_LIMIT = 20

# Non-ASCII → ASCII folds, applied before anything else. Scenario and zone names
# routinely carry typographic punctuation (em dashes from the scenario templates
# and the AI generator, degree signs from cold-storage zone names), and any one
# of them makes CV reject the whole level.
_OH_ASCII_FOLD = {
    "—": "-",  # em dash
    "–": "-",  # en dash
    "‑": "-",  # non-breaking hyphen
    "−": "-",  # minus sign
    " ": " ",  # no-break space
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "°": "deg",
    "µ": "u",
    "μ": "u",
}

# Multi-word phrases with a canonical short form in industrial networking.
# Applied first so "Substation Local Area Network" collapses to "Substation LAN"
# instead of being whittled down word by word. Matched case-insensitively on
# word boundaries.
_OH_PHRASE_ABBREV = {
    "local area network": "LAN",
    "wide area network": "WAN",
    "manufacturing execution system": "MES",
    "programmable logic controller": "PLC",
    "human machine interface": "HMI",
    "remote terminal unit": "RTU",
    "distributed control system": "DCS",
    "automated material handling": "AMHS",
}

# Grammatical connectors — pure filler at this budget. Dropped anywhere in the
# name, which is what keeps "Solar Farm with Battery…" from stranding on the
# preposition ("Solar Farm with") and "Point of Interconnection…" on "Point of".
_OH_CONNECTORS = {"with", "of", "the", "and", "for", "a", "an", "to", "in", "on"}

# Generic nouns that carry no distinguishing information once the head noun is
# present. Dropped from the TAIL inward only — "Network" is noise in "Bay
# Control Network" but load-bearing in "Network Operations".
_OH_GENERIC_TAIL = {
    "network",
    "networks",
    "net",
    "system",
    "systems",
    "zone",
    "line",
    "plant",
    "area",
    "segment",
}

# Word-level abbreviations, applied longest-source-word first and only until the
# name fits, so a mildly-over-budget name takes exactly one substitution.
_OH_WORD_ABBREV = {
    "interconnection": "Interconn",
    "instrumentation": "Instr",
    "instrumented": "Instr",
    "chromatography": "Chrom",
    "environmental": "Env",
    "semiconductor": "Semi",
    "refrigeration": "Refrig",
    "purification": "Purif",
    "distribution": "Distrib",
    "intersection": "Intersect",
    "temperature": "Temp",
    "substation": "Substn",
    "electrical": "Elec",
    "environment": "Env",
    "compressor": "Compr",
    "automotive": "Auto",
    "monitoring": "Mon",
    "management": "Mgmt",
    "protection": "Prot",
    "operations": "Ops",
    "bioreactor": "Bio",
    "controller": "Ctlr",
    "warehouse": "Whse",
    "municipal": "Muni",
    "treatment": "Treat",
    "detection": "Detect",
    "induction": "Induct",
    "cleanroom": "Cleanrm",
    "metrology": "Metrol",
    "deposition": "Depos",
    "diffusion": "Diff",
    "assembly": "Asm",
    "handling": "Hdlg",
    "material": "Matl",
    "metering": "Meter",
    "pipeline": "Pipe",
    "building": "Bldg",
    "stations": "Stns",
    "backhaul": "Bkhaul",
    "aseptic": "Asept",
    "battery": "Batt",
    "storage": "Stor",
    "station": "Stn",
    "control": "Ctrl",
    "cabinet": "Cab",
    "utility": "Util",
    "energy": "Engy",
    "remote": "Rem",
    "sorting": "Sort",
    "chilled": "Chill",
}

# Characters that must never end an OH level name — an opening bracket left by a
# dropped word, or a separator left by a dropped tail noun.
_OH_TRAILING_JUNK = " \t-_/,.:;+&([{'\""


def _oh_fold_ascii(text: str) -> str:
    """Fold typographic punctuation to ASCII and drop anything still non-ASCII."""
    for src, dst in _OH_ASCII_FOLD.items():
        text = text.replace(src, dst)
    text = "".join(c for c in text if ord(c) < 128)
    return " ".join(text.split())


def _oh_tidy(text: str) -> str:
    """Collapse whitespace and strip dangling connectors/punctuation from the end.

    Run after every shortening step so no intermediate result can be handed to
    CV ending on a preposition or an unbalanced bracket.
    """
    text = " ".join(text.split())
    while True:
        stripped = text.rstrip(_OH_TRAILING_JUNK)
        words = stripped.split()
        if len(words) > 1 and words[-1].lower() in _OH_CONNECTORS:
            text = " ".join(words[:-1])
            continue
        if stripped == text:
            return text
        text = stripped


def _oh_level_name(text: str, limit: int = OH_LEVEL_NAME_LIMIT) -> str:
    """Compact a name to fit CV's 20-char ASCII-only OH level cap.

    CV's cap is far too tight for real scenario and zone names, so a plain
    word-boundary truncation throws away the distinguishing part of the name
    ("Electrical Substation IED Network" → "Electrical") and can strand the
    result on a connector or an open bracket. This instead spends the 20-char
    budget deliberately, applying the cheapest meaning-preserving reduction
    first and stopping the moment the name fits:

    1. fold to ASCII (CV rejects non-ASCII names outright)
    2. canonical multi-word abbreviations ("Local Area Network" → "LAN")
    3. drop grammatical connectors ("with", "of", …)
    4. drop generic trailing nouns ("Network", "System", …)
    5. abbreviate words, longest source word first
    6. tighten " / " and " - " separators
    7. drop a trailing parenthetical
    8. word-boundary truncate as a last resort

    Deterministic and idempotent-ish by construction: every step is a pure
    string reduction, so the same input always yields the same level name (which
    is what makes ``_match_existing_oh_level``'s name-based fallback reliable).
    """
    text = _oh_tidy(_oh_fold_ascii(text or ""))
    if len(text) <= limit:
        return text

    # 2. canonical phrases
    for phrase, short in _OH_PHRASE_ABBREV.items():
        pattern = re.compile(r"\b" + r"\s+".join(map(re.escape, phrase.split())) + r"\b", re.I)
        text = _oh_tidy(pattern.sub(short, text))
        if len(text) <= limit:
            return text

    # 3. connectors, anywhere in the name
    words = text.split()
    kept = [w for w in words if w.lower().strip("()[[],.") not in _OH_CONNECTORS]
    if kept and len(kept) < len(words):
        text = _oh_tidy(" ".join(kept))
        if len(text) <= limit:
            return text

    # 4. generic nouns, from the tail inward
    words = text.split()
    while len(words) > 1 and words[-1].lower().strip("()[],.") in _OH_GENERIC_TAIL:
        words.pop()
        text = _oh_tidy(" ".join(words))
        if len(text) <= limit:
            return text
        words = text.split()

    # 5. word abbreviations, longest source word first
    for full, short in sorted(_OH_WORD_ABBREV.items(), key=lambda kv: -len(kv[0])):
        if len(full) <= len(short):
            continue
        pattern = re.compile(r"\b" + re.escape(full) + r"\b", re.I)
        if not pattern.search(text):
            continue
        text = _oh_tidy(pattern.sub(short, text))
        if len(text) <= limit:
            return text

    # 6. tighten separators — but only KEEP the tightening if it alone makes the
    # name fit. Gluing tokens together otherwise destroys the word boundaries the
    # truncation in step 8 relies on ("Parcel Sort Hub - 7/13/2026" would become
    # "Parcel Sort Hub-7/13/2026", stranding the fill at "Parcel Sort").
    tightened = _oh_tidy(re.sub(r"\s*([/+&-])\s*", r"\1", text))
    if len(tightened) <= limit:
        return tightened

    # 7. drop a trailing parenthetical
    text = _oh_tidy(re.sub(r"\s*[([][^)\]]*[)\]]?\s*$", "", text)) or text
    if len(text) <= limit:
        return text

    # 8. last resort — greedy word fill, so we spend as much of the budget as
    # whole words allow instead of backing off to the previous boundary.
    out = ""
    for word in text.split():
        candidate = f"{out} {word}".strip()
        if len(candidate) > limit:
            break
        out = candidate
    out = _oh_tidy(out)
    return out or _oh_tidy(text[:limit]) or text[:limit]

# CV "type" for the custom networks we mint for simulated OT ranges. CV also
# supports "IT Internal" / "External"; we default everything to "OT Internal"
# (matches CV's built-in ranges and is the only value confirmed on-install).
# Purdue-level-aware typing (enterprise/DMZ -> IT Internal) can layer on later.
DEFAULT_NETWORK_TYPE = "OT Internal"


def _group_label(scenario: Scenario, zone_name: str, duplicates: set[str]) -> str:
    """Readable CV group label (<=60 chars — CV's hard limit).

    Default is the bare zone name (matches the canvas). CV groups are a global
    flat namespace keyed by label, so a zone name shared across scenarios (e.g.
    "Industrial DMZ") must be deconflicted — but ONLY those: a name is suffixed
    with the scenario name iff it appears in ``duplicates`` (the set of zone
    names used by >=2 scenarios, computed deterministically from PacketArch's own
    DB — symmetric, so every colliding instance gets the suffix). Unique zone
    names stay bare.

    Acronym casing is normalized (Ot Dmz -> OT DMZ) so casing-variant near-dupes
    collapse and are detected as collisions.
    """
    zone = normalize_acronyms((zone_name or "").strip())
    if zone not in duplicates:
        return zone[:GROUP_LABEL_LIMIT]
    name = (getattr(scenario, "name", None) or "").strip()
    if not name:
        return zone[:GROUP_LABEL_LIMIT]
    suffix = f" ({name})"
    # Keep the zone name intact; truncate the scenario suffix if the pair overflows.
    avail = GROUP_LABEL_LIMIT - len(zone) - len(" ()")
    if avail < 3:
        return f"{zone} ({name})"[:GROUP_LABEL_LIMIT]
    return f"{zone} ({name[:avail].rstrip()})" if len(zone) + len(suffix) > GROUP_LABEL_LIMIT else f"{zone}{suffix}"


async def _duplicate_zone_names(db) -> set[str]:
    """Zone names used by >=2 scenarios (acronym-normalized) — need deconfliction.

    Source of truth is PacketArch's own scenarios (not CV's mutable state), so the
    result is deterministic and symmetric across re-provisions.
    """
    import collections

    rows = (await db.execute(select(Scenario))).scalars().all()
    counts: collections.Counter[str] = collections.Counter()
    for s in rows:
        names = {
            normalize_acronyms((z.get("name") or zid).strip())
            for zid, z in ((s.definition or {}).get("zones") or {}).items()
        }
        counts.update(names)
    return {name for name, n in counts.items() if n > 1}


def _criticalness_for_zone(zone: dict) -> int:
    """Map a scenario zone to a CV industrial-impact level (0-4).

    Prefers the zone's explicit ``security_level``; otherwise derives from the
    Purdue ``level`` (closer to the process = higher impact).
    """
    sl = (zone.get("security_level") or "").lower()
    if sl in _SECURITY_LEVEL_CRITICALNESS:
        return _SECURITY_LEVEL_CRITICALNESS[sl]

    level = zone.get("level")
    if level is None:
        return 2
    try:
        lv = float(level)
    except (TypeError, ValueError):
        return 2
    if lv <= 1:      # L0 process / L1 basic control
        return 4
    if lv <= 2:      # L2 supervisory control
        return 3
    if lv <= 3:      # L3 operations / IDMZ
        return 2
    return 1         # L4/L5 enterprise


def _build_preset_meta(scenario: Scenario, subnet: str | None) -> tuple[str, str]:
    """Build the CV preset label + description from a scenario."""
    definition = scenario.definition or {}
    zones = definition.get("zones", {}) or {}
    devices = definition.get("devices", {}) or {}

    label = scenario.name
    base_desc = (getattr(scenario, "description", None) or "").strip()

    zone_names = ", ".join(
        sorted(z.get("name", zid) for zid, z in zones.items())
    )
    parts = []
    if base_desc:
        parts.append(base_desc)
    summary = (
        f"PacketArch scenario — {len(devices)} device(s) across {len(zones)} "
        f"Purdue-segmented zone(s)"
    )
    if subnet:
        summary += f" on {subnet}"
    summary += "."
    parts.append(summary)
    if zone_names:
        parts.append(f"Zones: {zone_names}.")
    description = " ".join(parts)
    return label[:100], description


def _truncate_at_word(text: str, limit: int) -> str:
    """Truncate to ``limit`` chars on a word boundary with an ellipsis."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rstrip()
    if " " in cut:
        cut = cut[: cut.rfind(" ")].rstrip()
    return cut + "…"  # …


async def _fit_description(db, raw: str, limit: int = PRESET_DESCRIPTION_LIMIT) -> str:
    """Fit a preset description within ``limit`` chars.

    Tries an LLM summarization first (so the description stays meaningful);
    falls back to a word-boundary truncation if AI is unavailable or fails.
    """
    if len(raw) <= limit:
        return raw

    try:
        from app.mcp_server.ai_providers import AIProviderFactory, AITask

        provider = await AIProviderFactory.create(db, task=AITask.DESCRIPTION_GENERATION)
        response = await provider.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write terse Cisco Cyber Vision preset descriptions. "
                        f"Rewrite the user's text into at most {limit} characters. "
                        "Keep the concrete facts (zone names, device count, subnet) "
                        "and OT context. Return ONLY the description text, no quotes."
                    ),
                },
                {"role": "user", "content": raw},
            ],
            max_tokens=256,
        )
        content = response.get("content", []) if isinstance(response, dict) else []
        text = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
        if text:
            return text[:limit] if len(text) > limit else text
    except Exception as e:  # noqa: BLE001 — AI is best-effort here
        logger.info(f"LLM description summarization unavailable ({e}); truncating instead")

    return _truncate_at_word(raw, limit)


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _get_cv_state(scenario: Scenario) -> dict:
    return dict((scenario.definition or {}).get(CV_STATE_KEY) or {})


async def _save_cv_state(db, scenario: Scenario, state: dict) -> None:
    """Persist CV provisioning state onto ``definition['cyber_vision']``.

    Uses a targeted ``jsonb_set`` UPDATE against the live row rather than
    rewriting ``scenario.definition`` through the ORM. This avoids the
    expire-on-commit trap (the ORM attribute is stale after the first commit in
    a multi-save flow) and only touches the ``cyber_vision`` key, so it never
    clobbers — or gets clobbered by — other definition writers.
    """
    import json

    state["updated_at"] = _now()
    await db.execute(
        text(
            "UPDATE scenarios "
            "SET definition = jsonb_set(COALESCE(definition, '{}'::jsonb), "
            "'{cyber_vision}', CAST(:cv AS jsonb), true) "
            "WHERE id = :sid"
        ),
        {"cv": json.dumps(state), "sid": str(scenario.id)},
    )
    await db.commit()


async def get_scenario_subnet(db, scenario_id: UUID) -> str | None:
    """Return the scenario's allocated /16 CIDR, or None if unallocated."""
    result = await db.execute(
        select(IPRangeAllocation).where(IPRangeAllocation.scenario_id == scenario_id)
    )
    allocation = result.scalar_one_or_none()
    return allocation.cidr_range if allocation else None


# ---------------------------------------------------------------------------
# Custom networks — mirror the scenario's IP topology into CV's "network
# organization" so CV segments the map by scenario/zone instead of lumping
# everything under its built-in 10/8. One /16 for the scenario umbrella + one
# /24 per zone; names match the zone GROUP labels. Idempotent get-or-create
# keyed by ipRange; never touches CV's built-ins or other scenarios' ranges.
# ---------------------------------------------------------------------------
def _range_index_from_cidr(cidr: str | None) -> int | None:
    """Second octet of a ``10.{n}.0.0/16`` scenario CIDR (the range index)."""
    if not cidr:
        return None
    try:
        return int(cidr.split("/")[0].split(".")[1])
    except (ValueError, IndexError):
        return None


def _zone_subnet(zone: dict, range_index: int | None) -> str | None:
    """A zone's /24 CIDR: prefer the stored network config, else derive it
    from the scenario range index + the zone's subnet offset."""
    net = zone.get("network") or {}
    if net.get("subnet"):
        return net["subnet"]
    offset = net.get("subnet_offset")
    if offset is None:
        offset = zone.get("subnet_offset")
    if offset is None or range_index is None:
        return None
    return f"10.{range_index}.{int(offset)}.0/24"


def _net_item(name: str, ip_range: str) -> dict:
    """Build a CV custom-network payload item with our standard defaults."""
    return {
        "name": (name or "PacketArch")[:GROUP_LABEL_LIMIT],
        "ipRange": ip_range,
        "type": DEFAULT_NETWORK_TYPE,
        "vlanId": None,
        "duplicated": False,
        "splitDevicesPerSensor": False,
    }


def _desired_networks(scenario: Scenario, subnet: str | None, duplicates: set[str]) -> list[dict]:
    """Desired CV custom networks for a scenario: the scenario /16 umbrella plus
    one /24 per zone. Zone names reuse ``_group_label`` so the networks read
    identically to the zone groups in CV. De-duplicated by ipRange."""
    definition = scenario.definition or {}
    zones = definition.get("zones", {}) or {}
    range_index = _range_index_from_cidr(subnet)

    desired: list[dict] = []
    seen: set[str] = set()

    if subnet:
        desired.append(_net_item(getattr(scenario, "name", None) or "PacketArch scenario", subnet))
        seen.add(subnet)

    for zone_id, zone in zones.items():
        z24 = _zone_subnet(zone, range_index)
        if not z24 or z24 in seen:
            continue
        seen.add(z24)
        label = _group_label(scenario, zone.get("name") or zone_id, duplicates)
        desired.append(_net_item(label, z24))

    return desired


async def _save_cv_networks(db, scenario_id: UUID, networks_state: dict) -> None:
    """Persist ONLY ``definition['cyber_vision']['networks']`` via a targeted
    jsonb_set, so it never clobbers preset_id/groups (and isn't clobbered by
    them). The inner jsonb_set guarantees the ``cyber_vision`` object exists
    first, whether or not the preset step has run yet."""
    import json

    await db.execute(
        text(
            "UPDATE scenarios SET definition = jsonb_set("
            "jsonb_set(COALESCE(definition, '{}'::jsonb), '{cyber_vision}', "
            "COALESCE(definition->'cyber_vision', '{}'::jsonb), true), "
            "'{cyber_vision,networks}', CAST(:nw AS jsonb), true) "
            "WHERE id = :sid"
        ),
        {"nw": json.dumps(networks_state), "sid": str(scenario_id)},
    )
    await db.commit()


async def provision_networks(db, scenario: Scenario) -> dict:
    """Define CV custom networks for a scenario (scenario /16 + per-zone /24s).

    Idempotent get-or-create keyed by ipRange: ranges CV already has (built-ins
    like 10/8, or a prior deploy of this scenario) are left untouched; only the
    missing ones are created. Networks need no device aggregation, so this runs
    synchronously at deploy time. Self-contained (own CV client + targeted state
    save). Raises only if CV is unconfigured; the caller wraps it best-effort.

    Returns ``{created, existing, renamed, networks: {ipRange: {id, name, type}}}``.
    """
    svc = await cv_service_from_settings(db)
    if svc is None:
        raise RuntimeError("Cyber Vision is not configured")

    subnet = await get_scenario_subnet(db, scenario.id)
    duplicates = await _duplicate_zone_names(db)
    desired = _desired_networks(scenario, subnet, duplicates)

    result: dict = {"created": 0, "existing": 0, "renamed": 0, "networks": {}}
    if not desired:
        await svc.close()
        return result

    try:
        by_range = {n.get("ipRange"): n for n in await svc.get_networks() if n.get("ipRange")}
        to_create = [d for d in desired if d["ipRange"] not in by_range]
        if to_create:
            await svc.create_networks(to_create)
            # POST returns an empty body — re-fetch to resolve server-assigned ids.
            by_range = {n.get("ipRange"): n for n in await svc.get_networks() if n.get("ipRange")}

        # Realign names that drifted. Matching is by ipRange, so a renamed zone
        # would otherwise keep showing its old name in CV forever (e.g. a /24
        # left labelled "Water Control Network" after the zone became "Intake
        # Zone"). Scoped to ranges inside the scenario's own /16 so a CV built-in
        # (10/8 CONTAINS the /16 rather than nesting in it) can never be touched.
        to_rename = [
            {**live, "name": d["name"]}
            for d in desired
            if (live := by_range.get(d["ipRange"]))
            and live.get("id")
            and _range_within(d["ipRange"], subnet)
            and live.get("name") != d["name"]
        ]
        if to_rename:
            await svc.update_networks(to_rename)
            result["renamed"] = len(to_rename)
            by_range = {n.get("ipRange"): n for n in await svc.get_networks() if n.get("ipRange")}

        created_ranges = {d["ipRange"] for d in to_create}
        networks_state: dict = {}
        for d in desired:
            live = by_range.get(d["ipRange"])
            if not live:
                logger.warning(f"CV network {d['ipRange']} not present after create — skipping")
                continue
            networks_state[d["ipRange"]] = {
                "id": str(live.get("id")),
                "name": live.get("name"),
                "type": live.get("type"),
            }
            if d["ipRange"] in created_ranges:
                result["created"] += 1
            else:
                result["existing"] += 1
        result["networks"] = networks_state
    finally:
        await svc.close()

    await _save_cv_networks(db, scenario.id, result["networks"])
    logger.info(
        f"CV networks for scenario {scenario.id}: {result['created']} created, "
        f"{result['existing']} existing, {result['renamed']} renamed "
        f"({len(result['networks'])} total)"
    )
    return result


def _range_within(ip_range: str | None, scope_cidr: str | None) -> bool:
    """Whether ``ip_range`` is ``scope_cidr`` or nests inside it.

    The guard that keeps every write/delete confined to a scenario's own /16: a
    CV built-in like 10/8 CONTAINS the /16 rather than nesting in it, so it can
    never satisfy this. An unparseable range is never in scope. A missing scope
    matches nothing, so callers must handle "no allocated /16" explicitly rather
    than silently getting a free pass.

    Callers iterate over CV's whole network list, which includes IPv6 built-ins
    (``ff00::/8``, ``fe80::/10``, …) — ``subnet_of`` raises TypeError across
    address families, so mismatched versions are rejected up front.
    """
    import ipaddress

    if not ip_range or not scope_cidr:
        return False
    try:
        net = ipaddress.ip_network(ip_range, strict=False)
        scope = ipaddress.ip_network(scope_cidr, strict=False)
    except ValueError:
        return False
    if net.version != scope.version:
        return False
    return net == scope or net.subnet_of(scope)


def _scenario_network_ids(networks_state: dict, scenario_cidr: str | None) -> list[str]:
    """Network ids safe to delete on teardown: only those whose ipRange falls
    within the scenario's /16 (equal or a subnet). Guards against ever deleting
    a CV built-in or an out-of-scope range, even if state somehow recorded one.

    When the scenario has no allocated /16 there is nothing to scope against, so
    every recorded id is returned — teardown state is written by this module and
    only ever holds that scenario's own networks.
    """
    ids: list[str] = []
    for ip_range, meta in (networks_state or {}).items():
        nid = (meta or {}).get("id")
        if not nid:
            continue
        if scenario_cidr and not _range_within(ip_range, scenario_cidr):
            continue
        ids.append(str(nid))
    return ids


async def _save_cv_org_hierarchy(db, scenario_id: UUID, org_state: dict) -> None:
    """Persist ONLY ``definition['cyber_vision']['org_hierarchy']`` via a targeted
    jsonb_set (mirrors ``_save_cv_networks``)."""
    import json

    await db.execute(
        text(
            "UPDATE scenarios SET definition = jsonb_set("
            "jsonb_set(COALESCE(definition, '{}'::jsonb), '{cyber_vision}', "
            "COALESCE(definition->'cyber_vision', '{}'::jsonb), true), "
            "'{cyber_vision,org_hierarchy}', CAST(:oh AS jsonb), true) "
            "WHERE id = :sid"
        ),
        {"oh": json.dumps(org_state), "sid": str(scenario_id)},
    )
    await db.commit()


def _match_existing_oh_level(
    levels_by_id: dict, existing_id: str | None, parent_id: str, name: str
) -> str | None:
    """Resolve a level id: prefer the persisted id (if still live), else match
    by (parentLevelId, name) among the currently-fetched levels."""
    if existing_id and existing_id in levels_by_id:
        return existing_id
    for lid, lv in levels_by_id.items():
        if lv.get("parentLevelId") == parent_id and lv.get("name") == name:
            return lid
    return None


async def provision_org_hierarchy(
    db, scenario: Scenario, networks_state: dict | None = None
) -> dict:
    """Mirror a scenario's zones into CV's new-UI Organization Hierarchy.

    Creates one level for the scenario (under CV's built-in ``Global`` root)
    and one child level per zone — named identically to the zone's CV Group
    label (``_group_label``) so the same zone reads the same way in the old-UI
    Groups, the custom networks, and this tree. Assigns the scenario's already-
    provisioned custom networks (``provision_networks``) to the matching
    levels: the scenario's /16 to the scenario level, each zone's /24 to its
    zone level. OH membership is network/IP-based only (no per-device
    assignment exists in this API), so unlike ``provision_groups`` this needs
    no device/MAC polling and runs synchronously at deploy time.

    Idempotent get-or-create-or-rename, keyed first by persisted level ids and
    falling back to (parent, name) matching — safe to re-run (redeploy,
    reconcile) without creating duplicate levels.

    Raises:
        RuntimeError: if the New UI API token isn't configured (caller wraps
            this best-effort, same as ``provision_networks``).
    """
    svc = await cv_v1_service_from_settings(db)
    if svc is None:
        raise RuntimeError("Cyber Vision New UI API is not configured")

    if networks_state is None:
        networks_state = _get_cv_state(scenario).get("networks") or {}

    subnet = await get_scenario_subnet(db, scenario.id)
    duplicates = await _duplicate_zone_names(db)
    definition = scenario.definition or {}
    zones: dict = definition.get("zones", {}) or {}
    range_index = _range_index_from_cidr(subnet)
    prior = _get_cv_state(scenario).get("org_hierarchy") or {}
    prior_zones: dict = prior.get("zones") or {}

    try:
        levels = await svc.get_oh_levels()
        levels_by_id = {lv["id"]: lv for lv in levels if lv.get("id")}

        global_level = next(
            (lv for lv in levels if lv.get("name") == "Global" and not lv.get("parentLevelId")),
            None,
        )
        if global_level is None:
            raise RuntimeError("CV Organization Hierarchy has no 'Global' root level")
        global_id = global_level["id"]

        # _oh_level_name drops non-ASCII, so a name made entirely of typographic
        # characters folds to "" — which CV rejects. Fall back rather than 400.
        scenario_name = _oh_level_name(
            getattr(scenario, "name", None) or "PacketArch scenario"
        ) or _oh_level_name(f"Scenario {str(scenario.id)[:8]}")
        scenario_level_id = _match_existing_oh_level(
            levels_by_id, prior.get("scenario_level_id"), global_id, scenario_name
        )
        if scenario_level_id is None:
            await svc.create_oh_levels([{"name": scenario_name, "parentLevelId": global_id}])
            levels = await svc.get_oh_levels()
            levels_by_id = {lv["id"]: lv for lv in levels if lv.get("id")}
            scenario_level_id = _match_existing_oh_level(levels_by_id, None, global_id, scenario_name)
            if scenario_level_id is None:
                raise RuntimeError(f"CV org-hierarchy level '{scenario_name}' not found after create")
        elif levels_by_id[scenario_level_id].get("name") != scenario_name:
            await svc.rename_oh_level(scenario_level_id, scenario_name)
            levels_by_id[scenario_level_id]["name"] = scenario_name

        zone_labels = {
            zone_id: _oh_level_name(_group_label(scenario, zone.get("name") or zone_id, duplicates))
            or _oh_level_name(f"Zone {str(zone_id)[:8]}")
            for zone_id, zone in zones.items()
        }
        to_create = [
            {"name": label, "parentLevelId": scenario_level_id}
            for zone_id, label in zone_labels.items()
            if _match_existing_oh_level(levels_by_id, prior_zones.get(zone_id), scenario_level_id, label) is None
        ]
        if to_create:
            await svc.create_oh_levels(to_create)
            levels = await svc.get_oh_levels()
            levels_by_id = {lv["id"]: lv for lv in levels if lv.get("id")}

        zones_state: dict[str, str] = {}
        for zone_id, label in zone_labels.items():
            level_id = _match_existing_oh_level(
                levels_by_id, prior_zones.get(zone_id), scenario_level_id, label
            )
            if level_id is None:
                logger.warning(f"CV org-hierarchy level '{label}' not found after create — skipping zone {zone_id}")
                continue
            if levels_by_id[level_id].get("name") != label:
                await svc.rename_oh_level(level_id, label)
            zones_state[zone_id] = level_id

        # Assign the already-provisioned custom networks to the matching levels.
        if subnet and networks_state.get(subnet, {}).get("id"):
            await svc.assign_networks_to_level(scenario_level_id, [networks_state[subnet]["id"]])
        for zone_id, level_id in zones_state.items():
            z24 = _zone_subnet(zones[zone_id], range_index)
            net = networks_state.get(z24) if z24 else None
            if net and net.get("id"):
                await svc.assign_networks_to_level(level_id, [net["id"]])

        result = {"scenario_level_id": scenario_level_id, "zones": zones_state}
    finally:
        await svc.close()

    await _save_cv_org_hierarchy(db, scenario.id, result)
    logger.info(
        f"CV org-hierarchy for scenario {scenario.id}: scenario level {scenario_level_id}, "
        f"{len(zones_state)} zone level(s)"
    )
    return result


async def provision_preset(db, scenario: Scenario) -> dict:
    """Create a CV preset for the scenario and record it on the definition.

    Raises:
        RuntimeError: if Cyber Vision is not configured.
    """
    svc = await cv_service_from_settings(db)
    if svc is None:
        raise RuntimeError("Cyber Vision is not configured")

    subnet = await get_scenario_subnet(db, scenario.id)
    label, description = _build_preset_meta(scenario, subnet)
    description = await _fit_description(db, description)

    try:
        # Always exclude the shared Broadcast group from the preset (creating
        # the group if it doesn't exist yet), mirroring the reference preset.
        bgroup = await _ensure_broadcast_group(svc)
        preset = await svc.create_preset(
            label,
            description,
            subnet,
            exclude_groups=[{"id": bgroup.get("id"), "label": BROADCAST_GROUP_LABEL}],
        )
    finally:
        await svc.close()

    state = _get_cv_state(scenario)
    state.update({
        "preset_id": preset.get("id"),
        "preset_label": label,
        "subnet": subnet,
        "status": "preset_created",
        "error": None,
    })
    await _save_cv_state(db, scenario, state)
    logger.info(f"Provisioned CV preset {preset.get('id')} for scenario {scenario.id}")

    # Define CV custom networks (scenario /16 + per-zone /24s) so CV segments the
    # map by scenario/zone. Networks need no device aggregation, so unlike zone
    # groups they're created here at deploy time. Best-effort — never block the
    # preset (which is the operator-visible artifact) on network provisioning.
    try:
        state["networks"] = (await provision_networks(db, scenario)).get("networks", {})
    except Exception:  # noqa: BLE001 — network org is additive, never fatal
        logger.exception("CV network provisioning failed (continuing)")

    # Mirror the scenario/zones into CV's new-UI Organization Hierarchy, using
    # the networks just provisioned above. Best-effort and independently
    # optional (skipped entirely if the New UI API token isn't configured).
    try:
        state["org_hierarchy"] = await provision_org_hierarchy(
            db, scenario, networks_state=state.get("networks")
        )
    except Exception:  # noqa: BLE001 — org hierarchy is additive, never fatal
        logger.exception("CV org hierarchy provisioning failed (continuing)")

    # Keep the vertical roll-up preset in sync with this scenario's addition.
    vertical = getattr(scenario, "vertical", None)
    if vertical:
        try:
            await provision_vertical_preset(db, vertical)
        except Exception:  # noqa: BLE001 — roll-up is best-effort, never block
            logger.exception("vertical roll-up preset reconcile failed (continuing)")
    return state


async def _purge_scenario_entities(svc: CyberVisionService, scenario: Scenario) -> dict:
    """Best-effort delete of the CV components/devices this scenario produced.

    Scoped strictly to the scenario's OWN declared MACs, so it never touches
    another scenario's data. CV recreates components from live traffic, so for a
    running scenario this is self-healing; its real purpose is to clear the
    GHOSTS a stopped/deleted scenario leaves behind (which otherwise accrete and
    get sticky-merged across scenarios). Pure no-op if the CV API rejects entity
    deletion — whether CV 3.0 supports component/device DELETE is unconfirmed
    (live verification was out of scope), so every failure is swallowed.
    """
    summary = {"entities_deleted": 0, "entities_attempted": 0}
    devices = (scenario.definition or {}).get("devices") or {}
    macs = {
        normalize_mac((d.get("network") or {}).get("macAddress"))
        for d in devices.values()
    }
    macs.discard(None)
    if not macs:
        return summary
    try:
        raw_d, raw_c = await _fetch_cv_entities(svc)
        index = _build_entity_index(raw_d, raw_c)
    except Exception:  # noqa: BLE001 — can't enumerate; skip purge
        return summary
    seen: set[str] = set()
    for mac in macs:
        for e in _entities_for_mac(index, mac):
            eid = e["id"]
            if eid in seen:
                continue
            seen.add(eid)
            summary["entities_attempted"] += 1
            path = "/devices" if e.get("is_device") else "/components"
            try:
                await svc._request("DELETE", f"{path}/{eid}")
                summary["entities_deleted"] += 1
            except Exception:  # noqa: BLE001 — CV may not allow entity deletion
                pass
    return summary


async def teardown_cv_provisioning(db, scenario: Scenario) -> dict:
    """Best-effort removal of the CV objects PacketArch created for a scenario.

    Deletes the per-scenario preset, the zone groups, and (best-effort) the
    scenario's discovered components/devices by MAC — so a deleted scenario
    doesn't leave ghosts behind. Does NOT touch the shared Broadcast group.
    Never raises: teardown must not block scenario deletion.

    Returns a summary dict {preset_deleted, groups_deleted, entities_*, errors}.
    """
    summary = {
        "preset_deleted": False, "groups_deleted": 0, "networks_deleted": 0,
        "org_levels_deleted": 0, "errors": [],
    }
    state = _get_cv_state(scenario)
    if not state:
        return summary

    svc = await cv_service_from_settings(db)
    if svc is None:
        return summary

    try:
        for zone_id, g in (state.get("groups") or {}).items():
            gid = g.get("group_id")
            if not gid:
                continue
            try:
                await svc.delete_group(gid)
                summary["groups_deleted"] += 1
            except Exception as e:  # noqa: BLE001
                summary["errors"].append(f"group {gid}: {e}")
                logger.warning(f"CV teardown: failed to delete group {gid}: {e}")

        preset_id = state.get("preset_id")
        if preset_id:
            try:
                await svc.delete_preset(preset_id)
                summary["preset_deleted"] = True
            except Exception as e:  # noqa: BLE001
                summary["errors"].append(f"preset {preset_id}: {e}")
                logger.warning(f"CV teardown: failed to delete preset {preset_id}: {e}")

        # Delete the scenario's custom networks (scenario /16 + zone /24s),
        # scoped strictly to ranges within the scenario /16 so built-ins and
        # other scenarios' networks are never touched.
        net_ids = _scenario_network_ids(state.get("networks") or {}, state.get("subnet"))
        if net_ids:
            try:
                await svc.delete_networks(net_ids)
                summary["networks_deleted"] = len(net_ids)
            except Exception as e:  # noqa: BLE001
                summary["errors"].append(f"networks: {e}")
                logger.warning(f"CV teardown: failed to delete networks {net_ids}: {e}")

        # Delete this scenario's new-UI Organization Hierarchy levels — zone
        # (child) levels first, then the scenario level. Must run AFTER the
        # networks are deleted above: an OH level can't be deleted while a
        # network is still assigned to it, and there's no "unassign" call
        # (only reassignment) — deleting the underlying network is what frees
        # the level. Independently optional: skipped entirely if the New UI
        # API token isn't configured.
        org_hierarchy = state.get("org_hierarchy") or {}
        if org_hierarchy:
            v1 = await cv_v1_service_from_settings(db)
            if v1 is not None:
                try:
                    for zone_id, level_id in (org_hierarchy.get("zones") or {}).items():
                        try:
                            await v1.delete_oh_level(level_id)
                            summary["org_levels_deleted"] += 1
                        except Exception as e:  # noqa: BLE001
                            summary["errors"].append(f"org-hierarchy zone level {level_id}: {e}")
                            logger.warning(f"CV teardown: failed to delete org-hierarchy level {level_id}: {e}")
                    scenario_level_id = org_hierarchy.get("scenario_level_id")
                    if scenario_level_id:
                        try:
                            await v1.delete_oh_level(scenario_level_id)
                            summary["org_levels_deleted"] += 1
                        except Exception as e:  # noqa: BLE001
                            summary["errors"].append(f"org-hierarchy scenario level {scenario_level_id}: {e}")
                            logger.warning(f"CV teardown: failed to delete org-hierarchy level {scenario_level_id}: {e}")
                finally:
                    await v1.close()

        # Best-effort: clear the scenario's own discovered entities (ghost cleanup).
        try:
            summary.update(await _purge_scenario_entities(svc, scenario))
        except Exception as e:  # noqa: BLE001 — never block teardown
            summary["errors"].append(f"entity purge: {e}")
    finally:
        await svc.close()

    logger.info(
        f"CV teardown for scenario {scenario.id}: preset_deleted={summary['preset_deleted']}, "
        f"groups_deleted={summary['groups_deleted']}, networks_deleted={summary['networks_deleted']}, "
        f"org_levels_deleted={summary['org_levels_deleted']}, "
        f"entities_deleted={summary.get('entities_deleted', 0)}/{summary.get('entities_attempted', 0)}, "
        f"errors={len(summary['errors'])}"
    )
    return summary


def _build_entity_index(
    raw_devices: list[dict], raw_components: list[dict]
) -> dict[str, list[dict]]:
    """Index CV entities by normalized MAC -> list of {id, is_device}.

    Includes BOTH aggregated devices and raw components, because CV ingests
    components first and may not have aggregated them into devices yet — the
    component is the only thing groupable in that window. A scenario MAC can map
    to a device, one component, or two (CV's L2-only + L3 split per MAC).
    Group PATCH accepts device IDs on /devices and component IDs on /components.
    """
    index: dict[str, list[dict]] = {}
    for d in raw_devices:
        macs = d.get("mac")
        macs = macs if isinstance(macs, list) else [macs]
        for m in macs:
            norm = normalize_mac(m)
            if norm:
                index.setdefault(norm, []).append({"id": str(d.get("id")), "is_device": True})
    for c in raw_components:
        macs = c.get("mac")
        macs = macs if isinstance(macs, list) else [macs]
        for m in macs:
            norm = normalize_mac(m)
            if norm:
                index.setdefault(norm, []).append({"id": str(c.get("id")), "is_device": False})
    return index


def _entities_for_mac(index: dict[str, list[dict]], mac: str | None) -> list[dict]:
    """Return groupable entities for a MAC, preferring aggregated devices."""
    norm = normalize_mac(mac) if mac else None
    entities = index.get(norm or "", [])
    devices = [e for e in entities if e["is_device"]]
    return devices if devices else entities


async def _fetch_cv_entities(svc: CyberVisionService) -> tuple[list[dict], list[dict]]:
    """Fetch CV's aggregated devices and raw components (best-effort each)."""
    try:
        devices = await svc.get_devices_raw(preset_id=None)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"CV /devices fetch failed: {e}")
        devices = []
    try:
        components = await svc.get_components_raw()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"CV /components fetch failed: {e}")
        components = []
    return devices, components


async def _ensure_broadcast_group(svc: CyberVisionService) -> dict:
    """Return the shared Broadcast group, creating it if it doesn't exist."""
    for g in await svc.get_groups():
        if (g.get("label") or g.get("name")) == BROADCAST_GROUP_LABEL:
            return g
    return await svc.create_group(
        label=BROADCAST_GROUP_LABEL,
        description="Broadcast & multicast endpoints",
        color=_GROUP_COLOR,
        criticalness=0,
    )


async def classify_broadcast_multicast(svc: CyberVisionService) -> int:
    """Sweep all CV devices+components and classify broadcast/multicast into the
    Broadcast group. Idempotent (PATCH add). Returns the count assigned."""
    group = await _ensure_broadcast_group(svc)
    gid = str(group.get("id"))
    devices, components = await _fetch_cv_entities(svc)

    device_ids: list[str] = []
    component_ids: list[str] = []
    for d in devices:
        if is_broadcast_multicast(_first(d.get("mac")), d.get("ip")):
            device_ids.append(str(d.get("id")))
    for c in components:
        if is_broadcast_multicast(_first(c.get("mac")), c.get("ip")):
            component_ids.append(str(c.get("id")))

    if device_ids or component_ids:
        await svc.patch_group_members(gid, device_ids=device_ids, component_ids=component_ids)
    total = len(device_ids) + len(component_ids)
    logger.info(f"Broadcast sweep: classified {total} broadcast/multicast endpoint(s) into '{BROADCAST_GROUP_LABEL}'")
    return total


def _first(val):
    """First element if a list, else the value."""
    if isinstance(val, list):
        return val[0] if val else None
    return val


async def _poll_scenario_devices(
    svc: CyberVisionService,
    scenario_macs: set[str],
    max_polls: int,
    interval_seconds: int,
) -> tuple[dict[str, list[dict]], int]:
    """Poll CV (devices + components) until the scenario's MACs stabilise.

    Gates on how many of THIS scenario's MACs CV has indexed (as a device OR a
    component) — the same signal used to build groups, so the poll and the
    grouping never disagree.

    Returns ``(entity_index, matched_count)`` from the final poll.
    """
    prev = -1
    stable = 0
    index: dict[str, list[dict]] = {}
    matched = 0
    for i in range(max_polls):
        try:
            devices, components = await _fetch_cv_entities(svc)
            index = _build_entity_index(devices, components)
            matched = len(scenario_macs & set(index))
        except Exception as e:  # noqa: BLE001 — keep polling through transient errors
            logger.warning(f"CV poll {i + 1}/{max_polls} failed: {e}")
            matched = prev if prev >= 0 else 0

        if matched > 0 and matched == prev:
            stable += 1
        else:
            stable = 0
        prev = matched
        logger.info(
            f"CV poll {i + 1}/{max_polls}: {matched}/{len(scenario_macs)} "
            f"scenario entity(ies) discovered (stable={stable})"
        )

        # Stop early once growth settles, or as soon as CV has them all.
        if (matched > 0 and stable >= 2) or (scenario_macs and matched >= len(scenario_macs)):
            break
        if i < max_polls - 1:
            await asyncio.sleep(interval_seconds)
    return index, matched


async def provision_groups(
    db,
    scenario_id: UUID,
    poll: bool = True,
    max_polls: int = 15,
    interval_seconds: int = 60,
) -> dict:
    """Create one CV group per scenario zone and assign matched devices.

    Polls the preset until the device count stabilises (when ``poll``), resolves
    each zone's devices to CV device IDs by MAC, and creates/patches groups.
    """
    result = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if scenario is None:
        raise RuntimeError(f"Scenario {scenario_id} not found")

    state = _get_cv_state(scenario)
    preset_id = state.get("preset_id")
    definition = scenario.definition or {}
    zones: dict = definition.get("zones", {}) or {}
    devices: dict = definition.get("devices", {}) or {}
    # Tint this scenario's zone groups by its vertical (matches the rest of the UI).
    group_color = _color_for_vertical(getattr(scenario, "vertical", None))
    # Zone names shared across scenarios get a scenario-name suffix; unique ones
    # stay bare (readable). Computed from PacketArch's own DB — deterministic.
    duplicates = await _duplicate_zone_names(db)

    svc = await cv_service_from_settings(db)
    if svc is None:
        raise RuntimeError("Cyber Vision is not configured")

    state["status"] = "polling"
    await _save_cv_state(db, scenario, state)

    # Every MAC this scenario declares — the discovery + grouping signal.
    scenario_macs = {
        normalize_mac((d.get("network") or {}).get("macAddress"))
        for d in devices.values()
        if (d.get("network") or {}).get("macAddress")
    }
    scenario_macs.discard(None)

    try:
        # Broadcast/multicast sweep runs on every deploy, regardless of whether
        # the scenario's own devices have been discovered yet.
        try:
            await classify_broadcast_multicast(svc)
        except Exception:  # noqa: BLE001 — never block grouping on the sweep
            logger.exception("Broadcast/multicast sweep failed (continuing)")

        if poll:
            entity_index, _ = await _poll_scenario_devices(
                svc, scenario_macs, max_polls, interval_seconds
            )
        else:
            d, c = await _fetch_cv_entities(svc)
            entity_index = _build_entity_index(d, c)

        groups_state: dict = {}
        total_matched = 0
        for zone_id, zone in zones.items():
            zone_devices = [d for d in devices.values() if d.get("zoneId") == zone_id]
            if not zone_devices:
                continue

            device_ids: list[str] = []
            component_ids: list[str] = []
            unmatched = 0
            for dev in zone_devices:
                mac = (dev.get("network") or {}).get("macAddress")
                entities = _entities_for_mac(entity_index, mac)
                if not entities:
                    unmatched += 1
                    continue
                for e in entities:
                    (device_ids if e["is_device"] else component_ids).append(e["id"])

            if not device_ids and not component_ids:
                logger.info(f"Zone '{zone.get('name', zone_id)}': no devices/components in CV yet — skipping group")
                continue

            label = _group_label(scenario, zone.get("name") or zone_id, duplicates)
            criticalness = _criticalness_for_zone(zone)
            group = await _create_or_get_group(svc, label, criticalness, color=group_color)
            gid = str(group.get("id"))
            await svc.patch_group_members(gid, device_ids=device_ids, component_ids=component_ids)

            # Count distinct scenario devices placed (a MAC may map to 1-2 CV entities).
            placed = sum(
                1 for dev in zone_devices
                if _entities_for_mac(entity_index, (dev.get("network") or {}).get("macAddress"))
            )
            total_matched += placed
            groups_state[zone_id] = {
                "group_id": gid,
                "label": label,
                "criticalness": criticalness,
                "device_count": placed,
                "unmatched": unmatched,
            }
            logger.info(
                f"Zone '{label}' -> group {gid}: {placed} device(s) placed "
                f"({len(device_ids)} dev + {len(component_ids)} comp entities), {unmatched} not yet in CV"
            )

        # If CV hasn't surfaced any of this scenario's devices yet, stay in the
        # "polling" state (don't declare done with empty groups). The Celery
        # task re-arms itself so this becomes eventually consistent as CV's
        # aggregation catches up — no operator re-click needed.
        if total_matched == 0 and not groups_state:
            state.update({
                "status": "polling", "groups": {}, "device_count": 0,
                "expected_devices": len(scenario_macs), "error": None,
            })
            await _save_cv_state(db, scenario, state)
            logger.info(f"CV group provisioning for scenario {scenario_id}: no devices in CV yet — will retry")
            return state

        # Now that devices are grouped, refresh the preset so its
        # groupless:exclude view immediately reflects the grouped devices.
        if preset_id:
            await svc.refresh_preset_data(preset_id)

        state.update({
            "status": "groups_created",
            "groups": groups_state,
            "device_count": total_matched,
            "expected_devices": len(scenario_macs),
            "error": None,
        })
        await _save_cv_state(db, scenario, state)
        logger.info(
            f"CV group provisioning for scenario {scenario_id}: {len(groups_state)} group(s), "
            f"{total_matched}/{len(scenario_macs)} devices grouped"
        )
        return state
    except Exception as e:
        logger.exception(f"CV group provisioning failed for scenario {scenario_id}")
        state["status"] = "error"
        state["error"] = str(e)
        await _save_cv_state(db, scenario, state)
        raise
    finally:
        await svc.close()


async def _create_or_get_group(
    svc: CyberVisionService, label: str, criticalness: int, color: str = _GROUP_COLOR
) -> dict:
    """Create a group, reusing an existing one on label collision (409).

    When reusing an existing group whose color drifted (e.g. it predates
    vertical-colored groups), best-effort recolor it to ``color``.
    """
    import httpx

    try:
        return await svc.create_group(label=label, description="", color=color, criticalness=criticalness)
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 409:
            raise
        # Group with this label already exists — reuse it.
        for g in await svc.get_groups():
            if (g.get("label") or g.get("name")) == label:
                if color and g.get("color") != color:
                    try:
                        await svc.update_group(
                            str(g.get("id")),
                            label=label,
                            description=g.get("description", "") or "",
                            color=color,
                            criticalness=criticalness,
                        )
                        g["color"] = color
                    except Exception as ue:  # noqa: BLE001 — recolor is best-effort
                        logger.info(f"Could not recolor existing group '{label}': {ue}")
                logger.info(f"Reusing existing CV group '{label}' ({g.get('id')})")
                return g
        raise


async def reconcile_cv_group_names(db) -> dict:
    """Re-derive ALL CV group labels from the current scenario set in one pass.

    Idempotent cleanup lever: bare zone name + scenario-suffix for cross-scenario
    duplicates + acronym casing, applied across every scenario's groups. Fixes
    drift (e.g. a new scenario introduces a collision with an existing bare group
    → both get promoted to suffixed). Preserves each group's color/criticalness
    and rewrites the stored ``cyber_vision.groups`` labels so state stays in sync.
    """
    summary: dict = {"checked": 0, "renamed": 0, "errors": []}
    svc = await cv_service_from_settings(db)
    if svc is None:
        raise RuntimeError("Cyber Vision is not configured")
    try:
        live = {g.get("id"): g for g in await svc.get_groups()}
        duplicates = await _duplicate_zone_names(db)
        rows = (await db.execute(select(Scenario))).scalars().all()
        for s in rows:
            state = _get_cv_state(s)
            groups = state.get("groups") or {}
            if not groups:
                continue
            zones = (s.definition or {}).get("zones") or {}
            color = _color_for_vertical(getattr(s, "vertical", None))
            changed = False
            for zone_id, g in groups.items():
                gid = g.get("group_id")
                if not gid or gid not in live:
                    continue
                summary["checked"] += 1
                zname = (zones.get(zone_id) or {}).get("name") or zone_id
                target = _group_label(s, zname, duplicates)
                cur = live[gid].get("label") or live[gid].get("name")
                if cur == target:
                    continue
                crit = g.get("criticalness", live[gid].get("criticalness", 2))
                try:
                    await svc.update_group(gid, label=target, description="", color=color, criticalness=crit)
                    g["label"] = target
                    changed = True
                    summary["renamed"] += 1
                except Exception as e:  # noqa: BLE001
                    summary["errors"].append(f"group {gid}: {e}")
                    logger.warning(f"reconcile_cv_group_names: group {gid} -> '{target}' failed: {e}")
            if changed:
                state["groups"] = groups
                await _save_cv_state(db, s, state)
    finally:
        await svc.close()
    logger.info(f"reconcile_cv_group_names: checked={summary['checked']} renamed={summary['renamed']} errors={len(summary['errors'])}")
    return summary


async def reconcile_cv_networks(db) -> dict:
    """Ensure every scenario's CV custom networks (/16 + zone /24s) exist.

    One-shot cleanup lever mirroring ``reconcile_cv_group_names``: walks the
    current scenario set and get-or-creates each scenario's networks (idempotent
    by ipRange). Scenarios without an allocated /16 are skipped. Collects
    per-scenario failures instead of aborting the whole pass.
    """
    summary: dict = {"scenarios": 0, "created": 0, "existing": 0, "renamed": 0, "errors": []}
    # Fail fast if CV isn't configured, consistent with the sibling reconcilers.
    probe = await cv_service_from_settings(db)
    if probe is None:
        raise RuntimeError("Cyber Vision is not configured")
    await probe.close()

    rows = (await db.execute(select(Scenario))).scalars().all()
    for s in rows:
        if await get_scenario_subnet(db, s.id) is None:
            continue  # no allocated /16 → nothing to define
        summary["scenarios"] += 1
        try:
            res = await provision_networks(db, s)
            summary["created"] += res.get("created", 0)
            summary["existing"] += res.get("existing", 0)
            summary["renamed"] += res.get("renamed", 0)
        except Exception as e:  # noqa: BLE001
            summary["errors"].append(f"scenario {s.id}: {e}")
            logger.warning(f"reconcile_cv_networks: scenario {s.id} failed: {e}")

    logger.info(
        f"reconcile_cv_networks: scenarios={summary['scenarios']} created={summary['created']} "
        f"existing={summary['existing']} renamed={summary['renamed']} "
        f"errors={len(summary['errors'])}"
    )
    return summary


async def find_orphan_oh_levels(db) -> list[dict]:
    """Identify Organization Hierarchy levels that PacketArch created but has
    since lost track of — typically a scenario that was renamed, leaving its old
    tree behind (a fresh reconcile builds a NEW tree beside the stale one,
    because level matching is keyed on ``(parentLevelId, name)``).

    Attribution is deliberately conservative, because an OH tree is a shared
    surface and an operator's own levels are indistinguishable from ours by name
    alone. A level is only a candidate when BOTH hold:

    * no scenario's persisted ``org_hierarchy`` state references its id, and
    * it currently holds at least one network whose range falls inside some
      scenario's allocated /16 (``_range_within``, so a CV built-in never counts).

    That second condition is the actual evidence of ownership, and it is why this
    MUST run BEFORE ``provision_org_hierarchy`` — assigning a network to a level
    MOVES it, so once the push has run the stale level holds nothing and the
    evidence is gone. Ancestors of a candidate are included (a stale scenario
    level whose only content is its zone children holds no networks itself), and
    the result is ordered deepest-first so children are deletable before parents.

    Returns candidate dicts: ``{id, name, depth, networks: [ipRange, …]}``.
    Read-only — no CV writes. ``prune_orphan_oh_levels`` performs the deletion.
    """
    v1 = await cv_v1_service_from_settings(db)
    if v1 is None:
        return []

    scenarios = (await db.execute(select(Scenario))).scalars().all()
    referenced: set[str] = set()
    scopes: list[str] = []
    for s in scenarios:
        org = _get_cv_state(s).get("org_hierarchy") or {}
        if org.get("scenario_level_id"):
            referenced.add(str(org["scenario_level_id"]))
        referenced.update(str(v) for v in (org.get("zones") or {}).values() if v)
        cidr = await get_scenario_subnet(db, s.id)
        if cidr:
            scopes.append(cidr)

    try:
        levels = await v1.get_oh_levels()
        networks = await v1.get_networks()
    finally:
        await v1.close()

    by_id = {lv["id"]: lv for lv in levels if lv.get("id")}
    nets_by_level: dict[str, list[str]] = {}
    for n in networks:
        gid, ip_range = n.get("groupId"), n.get("ipRange")
        if gid and ip_range and any(_range_within(ip_range, c) for c in scopes):
            nets_by_level.setdefault(str(gid), []).append(ip_range)

    def depth(level_id: str) -> int:
        seen, d, cur = set(), 0, level_id
        while cur and cur in by_id and cur not in seen:
            seen.add(cur)
            cur = by_id[cur].get("parentLevelId")
            d += 1
        return d

    # Seed with levels holding in-scope networks, then pull in their ancestors so
    # a stale scenario level (empty itself) is pruned along with its zone levels.
    #
    # A ROOT level is never a candidate, however much scenario traffic it holds:
    # CV's built-in `Global` root is where every network sits until something
    # assigns it elsewhere, so a scenario whose OH step has not run yet parks its
    # whole /16 there and would otherwise make the root look PacketArch-owned.
    candidates: set[str] = {
        lid
        for lid in nets_by_level
        if lid in by_id and lid not in referenced and by_id[lid].get("parentLevelId")
    }
    for lid in list(candidates):
        cur = by_id[lid].get("parentLevelId")
        while cur and cur in by_id and by_id[cur].get("parentLevelId"):  # never the root
            if cur in referenced:
                break
            candidates.add(cur)
            cur = by_id[cur].get("parentLevelId")

    return sorted(
        (
            {
                "id": lid,
                "name": by_id[lid].get("name"),
                "depth": depth(lid),
                "networks": sorted(nets_by_level.get(lid, [])),
            }
            for lid in candidates
        ),
        key=lambda c: -c["depth"],
    )


async def prune_orphan_oh_levels(db, candidates: list[dict]) -> dict:
    """Delete the orphan levels found by ``find_orphan_oh_levels``.

    Call AFTER the provisioning push, so each candidate's networks have already
    been reassigned to their correct level. Deletes deepest-first (CV rejects
    deleting a level that still has children) and re-checks the live state first:
    any candidate that still holds a network or a child is SKIPPED rather than
    forced, so a level that turned out to be in use survives.
    """
    summary: dict = {"deleted": [], "skipped": [], "errors": []}
    if not candidates:
        return summary

    v1 = await cv_v1_service_from_settings(db)
    if v1 is None:
        summary["errors"].append("Cyber Vision New UI API token is not configured")
        return summary

    try:
        levels = await v1.get_oh_levels()
        networks = await v1.get_networks()
        child_count: dict[str, int] = {}
        for lv in levels:
            if lv.get("parentLevelId"):
                child_count[str(lv["parentLevelId"])] = child_count.get(str(lv["parentLevelId"]), 0) + 1
        held: dict[str, int] = {}
        for n in networks:
            if n.get("groupId"):
                held[str(n["groupId"])] = held.get(str(n["groupId"]), 0) + 1
        live_ids = {str(lv["id"]) for lv in levels if lv.get("id")}
        root_ids = {str(lv["id"]) for lv in levels if lv.get("id") and not lv.get("parentLevelId")}

        for cand in candidates:  # already deepest-first
            lid, name = str(cand["id"]), cand.get("name")
            if lid not in live_ids:
                summary["skipped"].append({"name": name, "reason": "already gone"})
                continue
            # Independent of how the candidate list was built — deleting CV's
            # root would take the whole hierarchy with it.
            if lid in root_ids:
                summary["skipped"].append({"name": name, "reason": "is a root level"})
                continue
            if held.get(lid):
                summary["skipped"].append(
                    {"name": name, "reason": f"still holds {held[lid]} network(s)"}
                )
                continue
            if child_count.get(lid):
                summary["skipped"].append(
                    {"name": name, "reason": f"still has {child_count[lid]} child level(s)"}
                )
                continue
            try:
                await v1.delete_oh_level(lid)
                summary["deleted"].append({"id": lid, "name": name})
                parent = next(
                    (str(lv["parentLevelId"]) for lv in levels
                     if str(lv.get("id")) == lid and lv.get("parentLevelId")),
                    None,
                )
                if parent:  # unblocks the parent later in this same pass
                    child_count[parent] = max(0, child_count.get(parent, 1) - 1)
            except Exception as e:  # noqa: BLE001
                summary["errors"].append(f"level {name!r} ({lid}): {e}")
                logger.warning(f"prune_orphan_oh_levels: failed to delete {name!r}: {e}")
    finally:
        await v1.close()

    logger.info(
        f"prune_orphan_oh_levels: deleted={len(summary['deleted'])} "
        f"skipped={len(summary['skipped'])} errors={len(summary['errors'])}"
    )
    return summary


async def reconcile_cv_org_hierarchy(db) -> dict:
    """Backfill/repair every scenario's new-UI Organization Hierarchy tree.

    Mirrors ``reconcile_cv_networks``, but SOFT-skips (returns a
    ``{"skipped": True}`` summary) rather than raising when the New UI API
    token isn't configured — unlike the classic CV connection the other
    reconcilers require, this integration is optional/additive, and an
    unconfigured token shouldn't abort the rest of a ``POST /reconcile`` pass.
    ``provision_org_hierarchy`` is get-or-create-or-rename in one pass, so this
    single reconciler covers both drift-repair and backfill for scenarios
    provisioned before this feature existed.
    """
    summary: dict = {"scenarios": 0, "errors": []}
    probe = await cv_v1_service_from_settings(db)
    if probe is None:
        summary["skipped"] = True
        summary["reason"] = "Cyber Vision New UI API token is not configured"
        return summary
    await probe.close()

    rows = (await db.execute(select(Scenario))).scalars().all()
    for s in rows:
        if await get_scenario_subnet(db, s.id) is None:
            continue  # no allocated /16 → nothing to mirror
        summary["scenarios"] += 1
        try:
            await provision_org_hierarchy(db, s)
        except Exception as e:  # noqa: BLE001
            summary["errors"].append(f"scenario {s.id}: {e}")
            logger.warning(f"reconcile_cv_org_hierarchy: scenario {s.id} failed: {e}")

    logger.info(
        f"reconcile_cv_org_hierarchy: scenarios={summary['scenarios']} errors={len(summary['errors'])}"
    )
    return summary


# ---------------------------------------------------------------------------
# Vertical roll-up presets — one CV preset per vertical aggregating ALL of that
# vertical's scenario /16s (same noise/broadcast/groupless filters as the
# per-scenario presets). Lets an operator view an entire vertical at once.
# ---------------------------------------------------------------------------
VERTICAL_DISPLAY_NAMES = {
    "manufacturing": "Manufacturing",
    "water_wastewater": "Water / Wastewater",
    "energy_power": "Energy & Power",
    "oil_gas": "Oil & Gas",
    "transportation": "Transportation",
    "building_automation": "Building Automation",
    "distribution_logistics": "Distribution & Logistics",
}


def _vertical_display(vertical: str | None) -> str:
    key = (vertical or "").strip().lower()
    return VERTICAL_DISPLAY_NAMES.get(key, (vertical or "").replace("_", " ").title())


def _vertical_preset_label(vertical: str | None) -> str:
    return f"{_vertical_display(vertical)} — All Scenarios"


async def _subnets_by_vertical(db) -> dict[str, list[str]]:
    """Map vertical -> sorted list of its scenarios' /16 CIDRs (DB = source of truth)."""
    rows = (
        await db.execute(
            select(Scenario.vertical, IPRangeAllocation.cidr_range).join(
                IPRangeAllocation, IPRangeAllocation.scenario_id == Scenario.id
            )
        )
    ).all()
    out: dict[str, set[str]] = {}
    for vertical, cidr in rows:
        v = (vertical or "").strip()
        if v and cidr:
            out.setdefault(v, set()).add(cidr)

    def _key(c: str) -> list[int]:
        try:
            return [int(o) for o in c.split("/")[0].split(".")]
        except Exception:  # noqa: BLE001
            return [0, 0, 0, 0]

    return {v: sorted(subs, key=_key) for v, subs in out.items()}


async def provision_vertical_preset(db, vertical: str) -> dict:
    """Create/replace the CV roll-up preset for one vertical (idempotent by label).

    Aggregates every current scenario /16 in the vertical. If the vertical has no
    scenarios, any stale roll-up preset is removed. Never raises on empty input.
    """
    label = _vertical_preset_label(vertical)
    subs = (await _subnets_by_vertical(db)).get(vertical, [])
    svc = await cv_service_from_settings(db)
    if svc is None:
        raise RuntimeError("Cyber Vision is not configured")
    try:
        existing = next(
            (p.get("id") for p in await svc.get_presets() if (p.get("label") or "") == label),
            None,
        )
        if existing:
            await svc.delete_preset(existing)
        if not subs:
            return {"vertical": vertical, "label": label, "subnets": [], "preset_id": None}
        bgroup = await _ensure_broadcast_group(svc)
        desc = (
            f"PacketArch vertical roll-up — {len(subs)} {_vertical_display(vertical)} "
            f"scenario subnet(s): " + ", ".join(subs)
        )
        preset = await svc.create_preset(
            label,
            desc,
            subnets=subs,
            exclude_groups=[{"id": bgroup.get("id"), "label": BROADCAST_GROUP_LABEL}],
        )
        logger.info(f"Provisioned vertical preset '{label}' ({len(subs)} subnets) -> {preset.get('id')}")
        return {"vertical": vertical, "label": label, "subnets": subs, "preset_id": preset.get("id")}
    finally:
        await svc.close()


async def reconcile_vertical_presets(db) -> list[dict]:
    """Re-provision every vertical's roll-up preset; drop rollups for empty verticals."""
    by_vert = await _subnets_by_vertical(db)
    verticals = sorted(set(by_vert) | set(VERTICAL_DISPLAY_NAMES))
    return [await provision_vertical_preset(db, v) for v in verticals]
