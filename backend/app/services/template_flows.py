# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Expand a scenario template's type-based flow specs into concrete flows.

One implementation shared by the create-from-template route, the template
definition builder (audit) and the validation scripts, so every path that
"builds the template" builds the same flows.

A flow spec names source/target device *types* (optionally narrowed to
zones) and how sources pair with targets:

``pairing: "round_robin"`` (default)
    max(len(sources), len(targets)) flows; source i pairs with target i,
    wrapping the shorter list. One master polling N devices gives N flows.
``pairing: "fan_out"``
    every source to every target, e.g. redundant ATMS servers or an NMS
    that each poll every field device.
``pairing: "same_group"``
    round-robin *within* each device ``group`` (e.g. one traffic cabinet),
    so a controller talks only to the detector/MMU in its own cabinet.
    Devices without a group never pair under this mode.

``config`` on a flow spec is copied onto every flow it produces (engine
options such as ``ntcip_profile``, ``snmp_version``, ``hostname``) when the
template opts in with ``honor_flow_config: True``. Templates written before
the opt-in already carry ``config`` blocks the create route always dropped
(e.g. energy IEC 61850 ``mode: goose`` on cross-zone flows), so honouring
them by default would change those scenarios' traffic.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any

ROUND_ROBIN = "round_robin"
FAN_OUT = "fan_out"
SAME_GROUP = "same_group"
PAIRINGS = (ROUND_ROBIN, FAN_OUT, SAME_GROUP)


def _timing(spec: dict[str, Any]) -> dict[str, Any]:
    timing: dict[str, Any] = {"intervalMs": spec.get("interval_ms", 1000)}
    if spec.get("jitter_ms"):
        timing["jitterMs"] = spec["jitter_ms"]
    if spec.get("jitter_type"):
        timing["jitterType"] = spec["jitter_type"]
    return timing


def _round_robin(sources: list[str], targets: list[str]) -> list[tuple[str, str]]:
    n = max(len(sources), len(targets))
    return [(sources[i % len(sources)], targets[i % len(targets)]) for i in range(n)]


def _pairs(spec: dict[str, Any], sources: list[str], targets: list[str],
           devices: dict[str, dict[str, Any]]) -> list[tuple[str, str]]:
    pairing = spec.get("pairing") or ROUND_ROBIN
    if pairing == FAN_OUT:
        return [(s, t) for s in sources for t in targets]
    if pairing == SAME_GROUP:
        src_by_group: dict[str, list[str]] = defaultdict(list)
        tgt_by_group: dict[str, list[str]] = defaultdict(list)
        for s in sources:
            if devices[s].get("group"):
                src_by_group[devices[s]["group"]].append(s)
        for t in targets:
            if devices[t].get("group"):
                tgt_by_group[devices[t]["group"]].append(t)
        pairs: list[tuple[str, str]] = []
        for group, group_sources in src_by_group.items():
            if tgt_by_group.get(group):
                pairs.extend(_round_robin(group_sources, tgt_by_group[group]))
        return pairs
    if pairing != ROUND_ROBIN:
        raise ValueError(f"unknown flow pairing {pairing!r}; expected one of {PAIRINGS}")
    return _round_robin(sources, targets)


def expand_template_flows(
    flow_specs: list[dict[str, Any]],
    devices: dict[str, dict[str, Any]],
    *,
    start_index: int = 0,
    honor_config: bool = False,
) -> dict[str, dict[str, Any]]:
    """Concrete flows (keyed ``flow_NNN``) for ``flow_specs`` over ``devices``.

    ``devices`` maps device id → device dict carrying ``type``, ``zoneId``
    and optionally ``group``. Insertion order of ``devices`` is the pairing
    order, exactly as the create route has always used it.
    """
    by_type: dict[str, list[str]] = {}
    by_type_zone: dict[tuple[str, str], list[str]] = {}
    for did, dev in devices.items():
        dtype = dev.get("type", "unknown")
        by_type.setdefault(dtype, []).append(did)
        by_type_zone.setdefault((dtype, dev.get("zoneId", "") or ""), []).append(did)

    flows: dict[str, dict[str, Any]] = {}
    index = start_index
    for spec in flow_specs:
        timing = _timing(spec)
        config = (spec.get("config") or {}) if honor_config else {}
        source_zones = spec.get("source_zones", [])
        target_zones = spec.get("target_zones", [])
        for source_type in spec.get("source_types", []):
            for target_type in spec.get("target_types", []):
                if source_zones:
                    sources = [d for z in source_zones for d in by_type_zone.get((source_type, z), [])]
                else:
                    sources = by_type.get(source_type, [])
                if target_zones:
                    targets = [d for z in target_zones for d in by_type_zone.get((target_type, z), [])]
                else:
                    targets = by_type.get(target_type, [])
                if not sources or not targets:
                    continue
                for source_id, target_id in _pairs(spec, sources, targets, devices):
                    if source_id == target_id:
                        continue
                    index += 1
                    flow_id = f"flow_{index:03d}"
                    flow: dict[str, Any] = {
                        "id": flow_id,
                        "sourceDeviceId": source_id,
                        "targetDeviceId": target_id,
                        "protocol": spec.get("protocol"),
                        "timing": timing,
                        "config": copy.deepcopy(config),
                    }
                    if spec.get("auto_repair_skip"):
                        flow["auto_repair_skip"] = True
                    flows[flow_id] = flow
    return flows
