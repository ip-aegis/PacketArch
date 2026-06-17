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
    summary = {"preset_deleted": False, "groups_deleted": 0, "errors": []}
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

        # Best-effort: clear the scenario's own discovered entities (ghost cleanup).
        try:
            summary.update(await _purge_scenario_entities(svc, scenario))
        except Exception as e:  # noqa: BLE001 — never block teardown
            summary["errors"].append(f"entity purge: {e}")
    finally:
        await svc.close()

    logger.info(
        f"CV teardown for scenario {scenario.id}: preset_deleted={summary['preset_deleted']}, "
        f"groups_deleted={summary['groups_deleted']}, "
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
            state.update({"status": "polling", "groups": {}, "device_count": 0, "error": None})
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
            "error": None,
        })
        await _save_cv_state(db, scenario, state)
        logger.info(f"CV group provisioning complete for scenario {scenario_id}: {len(groups_state)} group(s)")
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
