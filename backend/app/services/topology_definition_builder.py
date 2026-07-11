# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Inject the derived topology's switches/core into a scenario definition.

Given a scenario definition and a ``topology_planner`` result, materialize the
per-zone IE3500 switches and the IE9320 core as real (synthetic) devices in a
DEEP COPY of the definition — so Cyber Vision fingerprints them as Cisco
industrial switches and they participate in per-segment traffic. The source
scenario is never mutated.

The injected devices carry ``_topology_synthetic: True`` so the planner treats
them as infrastructure (not endpoints needing their own switch) while still
routing their own management traffic. They are orphans on injection;
``ensure_device_flow_coverage`` then gives each an SNMP monitoring flow.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

_SWITCH_PROTOCOLS = ["snmp", "lldp", "cdp"]


def _deep_containers(definition: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy only the mutated containers (devices/zones/flows), share rest."""
    out = dict(definition)
    for key in ("devices", "zones", "flows"):
        if key in out:
            out[key] = copy.deepcopy(out[key])
    return out


def _add_device(devices: Any, device: dict[str, Any]) -> None:
    if isinstance(devices, list):
        devices.append(device)
    else:
        devices[device["id"]] = device


def _zone_add_member(zones: Any, zone_id: str, device_id: str) -> None:
    zone = None
    if isinstance(zones, list):
        zone = next((z for z in zones if z.get("id") == zone_id), None)
    else:
        zone = zones.get(zone_id)
    if zone is None:
        return
    key = "deviceIds" if "deviceIds" in zone or "device_ids" not in zone else "device_ids"
    zone.setdefault(key, [])
    if device_id not in zone[key]:
        zone[key].append(device_id)


def _switch_device(
    *, device_id: str, name: str, template_id: str, zone_id: str,
    ip: str | None, mac: str, fingerprint: dict | None,
) -> dict[str, Any]:
    dev: dict[str, Any] = {
        "id": device_id,
        "name": name,
        "type": "network_switch",
        "protocols": list(_SWITCH_PROTOCOLS),
        "zoneId": zone_id,
        "vendor": "cisco",
        "architecturalRole": "network_infrastructure",
        "_topology_synthetic": True,
        "network": {"macAddress": mac},
    }
    if ip:
        dev["network"]["ipAddress"] = ip
    if fingerprint:
        dev["vendorFingerprint"] = fingerprint
        if fingerprint.get("model"):
            dev["fingerprintModel"] = fingerprint["model"]
    return dev


def build_topology_definition(
    definition: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    """Return a deep copy of ``definition`` with switches/core injected.

    ``plan`` is a ``TopologyPlan.as_dict()`` (or ``preview()``) result. No-op
    (returns a shallow copy) if the plan is invalid.
    """
    if not plan.get("valid"):
        return dict(definition)

    from app.services.device_templates import get_fingerprint_from_template

    out = _deep_containers(definition)
    devices = out.setdefault("devices", {})
    zones = out.get("zones", {})

    injected = 0
    for zone_id, sw in (plan.get("switches") or {}).items():
        fp = None
        try:
            fp = get_fingerprint_from_template(sw["template_id"])
        except Exception as e:  # fingerprint lookup must never break generation
            logger.warning("topology: fingerprint lookup failed for %s: %s", sw["template_id"], e)
        dev = _switch_device(
            device_id=sw["id"], name=sw["name"], template_id=sw["template_id"],
            zone_id=zone_id, ip=sw.get("mgmt_ip"), mac=sw["mac"], fingerprint=fp,
        )
        _add_device(devices, dev)
        _zone_add_member(zones, zone_id, sw["id"])
        injected += 1

    core = plan.get("core")
    if core:
        # Core management homes in the zone whose SVI carries its mgmt IP.
        home_zone = None
        for zid, svi in (core.get("svis") or {}).items():
            if svi.get("ip") == core.get("mgmt_ip"):
                home_zone = zid
                break
        fp = None
        try:
            fp = get_fingerprint_from_template(core["template_id"])
        except Exception as e:
            logger.warning("topology: core fingerprint lookup failed: %s", e)
        dev = _switch_device(
            device_id=core["id"], name=core["name"], template_id=core["template_id"],
            zone_id=home_zone or next(iter(plan.get("switches") or {}), None),
            ip=core.get("mgmt_ip"), mac=core["mac"], fingerprint=fp,
        )
        if home_zone:
            _zone_add_member(zones, home_zone, core["id"])
        _add_device(devices, dev)
        injected += 1

    logger.info("topology: injected %d switch/core devices", injected)
    return out
