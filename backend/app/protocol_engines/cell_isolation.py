# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Purdue-aware cell isolation: runtime gate that drops cross-cell flows
before they reach UnifiedOrchestrator.add_flow().

Lives under protocol_engines/ so it ships to the agent automatically via
the existing _shared/ Docker staging — same module, same import path on
both server and agent. No DB or pydantic deps; pure dict-in / tuple-out.
"""

from __future__ import annotations

from typing import Any, Iterable

# Mode constants — also accepted as plain strings on the wire.
MODE_OFF = "off"
MODE_CONDUIT_GATED = "conduit_gated"
MODE_STRICT_NORTHBOUND = "strict_northbound"

VALID_MODES = frozenset({MODE_OFF, MODE_CONDUIT_GATED, MODE_STRICT_NORTHBOUND})

# Default Purdue levels considered "cells" (IEC 62443 area zones).
DEFAULT_CELL_LEVELS: tuple[int, ...] = (0, 1, 2)

# Protocol alias mapping mirrors conduit_compliance.py so a flow tagged
# 's7comm_plus' matches a conduit that allows 's7comm'. Kept local to
# avoid dragging the schemas package into the agent.
_PROTOCOL_ALIASES: dict[str, str] = {
    "profisafe": "profinet",
    "s7comm_plus": "s7comm",
    "cip_safety": "ethernet_ip",
    "modbus": "modbus_tcp",
    "enip": "ethernet_ip",
    "bacnet_ip": "bacnet",
}


def _resolve_protocol(protocol: str) -> str:
    return _PROTOCOL_ALIASES.get(protocol, protocol)


def parse_config(definition: dict[str, Any] | None) -> dict[str, Any]:
    """Pull and normalize the cell_isolation block from a scenario definition.

    Returns a dict with keys ``mode`` (str) and ``cell_levels`` (set[int]).
    Unknown / missing config defaults to {mode: off, cell_levels: {0,1,2}}.
    """
    if not definition:
        return {"mode": MODE_OFF, "cell_levels": set(DEFAULT_CELL_LEVELS)}

    raw = definition.get("cell_isolation") or {}
    mode = raw.get("mode", MODE_OFF)
    if mode not in VALID_MODES:
        mode = MODE_OFF

    levels_raw = raw.get("applies_to_levels") or list(DEFAULT_CELL_LEVELS)
    cell_levels: set[int] = set()
    for lvl in levels_raw:
        try:
            cell_levels.add(int(lvl))
        except (TypeError, ValueError):
            continue
    if not cell_levels:
        cell_levels = set(DEFAULT_CELL_LEVELS)

    return {"mode": mode, "cell_levels": cell_levels}


def _normalize_zones(zones: Any) -> dict[str, dict[str, Any]]:
    """Accept either {id: zone} dict or [zone, ...] list."""
    if isinstance(zones, dict):
        return zones
    if isinstance(zones, list):
        out: dict[str, dict[str, Any]] = {}
        for z in zones:
            zid = z.get("id")
            if zid:
                out[zid] = z
        return out
    return {}


def _normalize_devices(devices: Any) -> dict[str, dict[str, Any]]:
    if isinstance(devices, dict):
        return devices
    if isinstance(devices, list):
        out: dict[str, dict[str, Any]] = {}
        for d in devices:
            did = d.get("id") or d.get("deviceId")
            if did:
                out[did] = d
        return out
    return {}


def _normalize_conduits(conduits: Any) -> list[dict[str, Any]]:
    if isinstance(conduits, dict):
        return list(conduits.values())
    if isinstance(conduits, list):
        return conduits
    return []


def _zone_of(device_id: str, devices: dict, zones: dict) -> str | None:
    """Resolve the zone id for a device, matching conduit_compliance semantics."""
    device = devices.get(device_id, {})
    explicit = device.get("zoneId") or device.get("zone_id") or device.get("zone")
    if explicit:
        return explicit
    for zid, zone in zones.items():
        members = zone.get("deviceIds") or zone.get("device_ids") or []
        if device_id in members:
            return zid
    return None


def _zone_level(zone: dict[str, Any]) -> int | None:
    """Pull the Purdue level off a zone, returning None if missing/invalid."""
    raw = zone.get("level")
    if raw is None:
        return None
    try:
        # Levels can be 3.5 in the conduit catalog; we round down for
        # cell classification. A "DMZ" (3.5) is not a cell.
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def classify_cell_zones(
    zones: Any,
    cell_levels: Iterable[int] = DEFAULT_CELL_LEVELS,
) -> set[str]:
    """Return the set of zone ids whose Purdue level marks them as cells."""
    zones_norm = _normalize_zones(zones)
    cell_set = set(cell_levels)
    out: set[str] = set()
    for zid, zone in zones_norm.items():
        lvl = _zone_level(zone)
        if lvl is not None and lvl in cell_set:
            out.add(zid)
    return out


def _conduit_permits(
    conduit: dict[str, Any],
    source_zone: str,
    target_zone: str,
    protocol: str,
) -> bool:
    """True iff this conduit allows protocol traffic from source→target."""
    src = conduit.get("sourceZoneId") or conduit.get("source_zone_id")
    tgt = conduit.get("targetZoneId") or conduit.get("target_zone_id")
    direction = conduit.get("direction", "bidirectional")
    allowed = conduit.get("allowedProtocols") or conduit.get("allowed_protocols") or []

    forward = src == source_zone and tgt == target_zone
    reverse = src == target_zone and tgt == source_zone
    if not (forward or reverse):
        return False

    if direction == "a_to_b" and not forward:
        return False
    if direction == "b_to_a" and not reverse:
        return False

    resolved = _resolve_protocol(protocol)
    allowed_resolved = {_resolve_protocol(p) for p in allowed}
    return resolved in allowed_resolved


def should_drop_flow(
    flow: dict[str, Any],
    devices: Any,
    zones: Any,
    conduits: Any,
    isolation: dict[str, Any],
) -> tuple[bool, str | None]:
    """Decide whether a single flow should be suppressed.

    Returns (drop, reason). When drop is False, reason is None.
    Reasons are human-readable strings suitable for logging.

    Off mode never drops. conduit_gated drops cross-cell flows that have no
    permitting conduit. strict_northbound drops every cell↔cell flow
    unconditionally; cells may only originate flows to non-cell zones.
    """
    mode = isolation.get("mode", MODE_OFF)
    if mode == MODE_OFF:
        return False, None

    devices_n = _normalize_devices(devices)
    zones_n = _normalize_zones(zones)
    if not zones_n:
        # Nothing to classify against. Treat as permissive.
        return False, None

    source_id = (
        flow.get("source_device_id")
        or flow.get("sourceDeviceId")
        or flow.get("source")
    )
    target_id = (
        flow.get("destination_device_id")
        or flow.get("destinationDeviceId")
        or flow.get("targetDeviceId")
        or flow.get("target")
    )
    if not source_id or not target_id:
        return False, None

    src_zone = _zone_of(source_id, devices_n, zones_n)
    tgt_zone = _zone_of(target_id, devices_n, zones_n)
    if not src_zone or not tgt_zone:
        # Cannot place the device in a zone, can't enforce. Stay permissive.
        return False, None

    cell_levels = isolation.get("cell_levels") or set(DEFAULT_CELL_LEVELS)
    cell_zone_ids = classify_cell_zones(zones_n, cell_levels)

    src_is_cell = src_zone in cell_zone_ids
    tgt_is_cell = tgt_zone in cell_zone_ids

    # Same-zone flows are always intra-cell (or intra-non-cell) — never blocked.
    if src_zone == tgt_zone:
        return False, None

    # If neither endpoint is a cell, isolation does not apply.
    if not (src_is_cell or tgt_is_cell):
        return False, None

    if mode == MODE_STRICT_NORTHBOUND:
        # Block any cell↔cell traffic. A cell may still talk to a non-cell
        # (northbound to L3+).
        if src_is_cell and tgt_is_cell:
            src_lvl = _zone_level(zones_n[src_zone])
            tgt_lvl = _zone_level(zones_n[tgt_zone])
            return True, (
                f"strict_northbound: cell↔cell L{src_lvl}↔L{tgt_lvl} "
                f"({src_zone}→{tgt_zone}) blocked"
            )
        return False, None

    if mode == MODE_CONDUIT_GATED:
        # Only enforce when both endpoints are cells. Cell→non-cell
        # (northbound) is unconstrained in this mode.
        if not (src_is_cell and tgt_is_cell):
            return False, None
        protocol = flow.get("protocol", "")
        for conduit in _normalize_conduits(conduits):
            if _conduit_permits(conduit, src_zone, tgt_zone, protocol):
                return False, None
        return True, (
            f"conduit_gated: no conduit permits {protocol} "
            f"{src_zone}→{tgt_zone}"
        )

    return False, None


def is_cell_to_cell(
    flow: dict[str, Any],
    devices: Any,
    zones: Any,
    cell_levels: Iterable[int] = DEFAULT_CELL_LEVELS,
) -> bool:
    """Helper for UI/preview code: True if both endpoints are in cell zones
    in different zones (i.e. east/west cell traffic)."""
    devices_n = _normalize_devices(devices)
    zones_n = _normalize_zones(zones)
    if not zones_n:
        return False

    source_id = (
        flow.get("source_device_id")
        or flow.get("sourceDeviceId")
        or flow.get("source")
    )
    target_id = (
        flow.get("destination_device_id")
        or flow.get("destinationDeviceId")
        or flow.get("targetDeviceId")
        or flow.get("target")
    )
    if not source_id or not target_id:
        return False

    src_zone = _zone_of(source_id, devices_n, zones_n)
    tgt_zone = _zone_of(target_id, devices_n, zones_n)
    if not src_zone or not tgt_zone or src_zone == tgt_zone:
        return False

    cell_zone_ids = classify_cell_zones(zones_n, cell_levels)
    return src_zone in cell_zone_ids and tgt_zone in cell_zone_ids


def is_cell_to_cell_conduit(
    conduit: dict[str, Any],
    zones: Any,
    cell_levels: Iterable[int] = DEFAULT_CELL_LEVELS,
) -> bool:
    """True if the conduit connects two cell zones (the kind that
    strict_northbound mode prunes)."""
    zones_n = _normalize_zones(zones)
    src = conduit.get("sourceZoneId") or conduit.get("source_zone_id")
    tgt = conduit.get("targetZoneId") or conduit.get("target_zone_id")
    if not src or not tgt or src == tgt:
        return False
    cell_zone_ids = classify_cell_zones(zones_n, cell_levels)
    return src in cell_zone_ids and tgt in cell_zone_ids


def prune_for_strict_northbound(
    definition: dict[str, Any],
    cell_levels: Iterable[int] = DEFAULT_CELL_LEVELS,
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """Return a copy of the definition with cell↔cell flows and conduits
    removed, and the cell_isolation mode set to strict_northbound.

    Also returns a report dict mapping ``"flows"`` and ``"conduits"`` to
    the lists of removed item ids — used by the confirmation UI to show
    the user exactly what's about to disappear.
    """
    devices = definition.get("devices", {})
    zones = definition.get("zones", {})
    flows_raw = definition.get("flows", {})
    conduits_raw = definition.get("conduits", {})

    cell_levels_set = set(int(x) for x in cell_levels)

    removed: dict[str, list[str]] = {"flows": [], "conduits": []}

    # Filter flows
    if isinstance(flows_raw, dict):
        kept_flows: dict[str, Any] = {}
        for fid, flow in flows_raw.items():
            if is_cell_to_cell(flow, devices, zones, cell_levels_set):
                removed["flows"].append(fid)
            else:
                kept_flows[fid] = flow
        new_flows: Any = kept_flows
    elif isinstance(flows_raw, list):
        kept_list: list[Any] = []
        for flow in flows_raw:
            if is_cell_to_cell(flow, devices, zones, cell_levels_set):
                removed["flows"].append(flow.get("id", "<unnamed>"))
            else:
                kept_list.append(flow)
        new_flows = kept_list
    else:
        new_flows = flows_raw

    # Filter conduits
    if isinstance(conduits_raw, dict):
        kept_conduits: dict[str, Any] = {}
        for cid, conduit in conduits_raw.items():
            if is_cell_to_cell_conduit(conduit, zones, cell_levels_set):
                removed["conduits"].append(cid)
            else:
                kept_conduits[cid] = conduit
        new_conduits: Any = kept_conduits
    elif isinstance(conduits_raw, list):
        kept_clist: list[Any] = []
        for conduit in conduits_raw:
            if is_cell_to_cell_conduit(conduit, zones, cell_levels_set):
                removed["conduits"].append(conduit.get("id", "<unnamed>"))
            else:
                kept_clist.append(conduit)
        new_conduits = kept_clist
    else:
        new_conduits = conduits_raw

    new_definition = {**definition}
    new_definition["flows"] = new_flows
    new_definition["conduits"] = new_conduits
    new_definition["cell_isolation"] = {
        "mode": MODE_STRICT_NORTHBOUND,
        "applies_to_levels": sorted(cell_levels_set),
    }

    return new_definition, removed


def preview_strict_northbound(
    definition: dict[str, Any],
    cell_levels: Iterable[int] = DEFAULT_CELL_LEVELS,
) -> dict[str, list[dict[str, Any]]]:
    """Read-only preview of what prune_for_strict_northbound would remove.

    Returns rich item descriptors (id, name, source_zone, target_zone,
    protocol) so the confirmation modal can render a meaningful list
    without round-tripping back to the server.
    """
    devices = definition.get("devices", {})
    zones = definition.get("zones", {})
    flows_raw = definition.get("flows", {})
    conduits_raw = definition.get("conduits", {})
    cell_levels_set = set(int(x) for x in cell_levels)

    devices_n = _normalize_devices(devices)
    zones_n = _normalize_zones(zones)

    flows_iter = (
        flows_raw.items() if isinstance(flows_raw, dict)
        else ((f.get("id", ""), f) for f in flows_raw or [])
    )
    conduits_iter = (
        conduits_raw.items() if isinstance(conduits_raw, dict)
        else ((c.get("id", ""), c) for c in conduits_raw or [])
    )

    flow_previews: list[dict[str, Any]] = []
    for fid, flow in flows_iter:
        if not is_cell_to_cell(flow, devices_n, zones_n, cell_levels_set):
            continue
        src_id = (
            flow.get("source_device_id")
            or flow.get("sourceDeviceId")
            or flow.get("source")
        )
        tgt_id = (
            flow.get("destination_device_id")
            or flow.get("destinationDeviceId")
            or flow.get("targetDeviceId")
            or flow.get("target")
        )
        flow_previews.append({
            "id": fid,
            "name": flow.get("name") or f"{src_id} → {tgt_id}",
            "protocol": flow.get("protocol", ""),
            "source_zone": _zone_of(src_id, devices_n, zones_n),
            "target_zone": _zone_of(tgt_id, devices_n, zones_n),
        })

    conduit_previews: list[dict[str, Any]] = []
    for cid, conduit in conduits_iter:
        if not is_cell_to_cell_conduit(conduit, zones_n, cell_levels_set):
            continue
        conduit_previews.append({
            "id": cid,
            "name": conduit.get("name", cid),
            "source_zone": (
                conduit.get("sourceZoneId") or conduit.get("source_zone_id")
            ),
            "target_zone": (
                conduit.get("targetZoneId") or conduit.get("target_zone_id")
            ),
            "allowed_protocols": (
                conduit.get("allowedProtocols")
                or conduit.get("allowed_protocols")
                or []
            ),
        })

    return {"flows": flow_previews, "conduits": conduit_previews}
