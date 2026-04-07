"""DB-free scenario template → FlowContext builder.

Converts scenario templates into FlowContext objects without any database
dependency, enabling fully local PCAP generation and fingerprint validation.

Replicates the logic from:
  - api/routes/templates.py  (device creation, fingerprint resolution)
  - orchestrator_pool.py     (FlowContext building, protocol aliases)
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Imports from PacketArch (all DB-free, in-memory only)
# ─────────────────────────────────────────────────────────────────

import sys
from pathlib import Path

# Ensure backend is on path
_backend_dir = str(Path(__file__).parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType
from app.protocol_engines.vendor_oui import generate_mac_address
from app.scenario_templates import VERTICAL_TEMPLATES, get_template
from app.services.device_templates._fingerprints import get_fingerprint_by_vendor_model

# Single source of truth for protocol alias resolution and per-protocol
# default ports. Replaces the local copies that previously lived here and
# in flow_generator.py — all callers now agree on the same map.
from app.protocol_engines.protocols import (
    PROTOCOL_ALIASES,
    PROTOCOL_DEFAULT_PORTS as PROTOCOL_PORTS,
    get_default_port,
)

from scripts.lib.pcap_validators import DeviceExpectation


# ─────────────────────────────────────────────────────────────────
# Result Types
# ─────────────────────────────────────────────────────────────────

@dataclass
class ScenarioBuildResult:
    """Result of building a scenario from a template."""

    template_name: str
    vertical: str
    display_name: str
    devices: dict[str, dict[str, Any]]  # device_id → device dict
    flows: list[dict[str, Any]]         # flow dicts
    flow_contexts: list[FlowContext]    # Ready for UnifiedOrchestrator
    device_expectations: dict[str, DeviceExpectation]  # MAC(upper) → expected
    target_protocols: dict[str, set[str]]  # device_id → set of protocol names
    warnings: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────
# Main Builder
# ─────────────────────────────────────────────────────────────────

def build_scenario_from_template(
    vertical: str,
    template_name: str,
    range_index: int = 1,
) -> ScenarioBuildResult:
    """Build a complete scenario from a template without database.

    Args:
        vertical: Industry vertical (e.g., "manufacturing").
        template_name: Template name within the vertical.
        range_index: IP range index (10.{range_index}.x.x). Use different
                     values for different templates to avoid IP collisions.

    Returns:
        ScenarioBuildResult with devices, flows, FlowContexts, and expectations.
    """
    template = get_template(vertical, template_name)
    if not template:
        raise ValueError(f"Template '{vertical}/{template_name}' not found")

    display_name = template.get("name", template_name)
    warnings: list[str] = []

    # ── Step 1: Build zones ──────────────────────────────────────
    zones = template.get("zones", [])
    zone_map: dict[str, dict] = {}
    for z in zones:
        zone_map[z["id"]] = z

    # ── Step 2: Expand devices ───────────────────────────────────
    device_specs = template.get("devices", [])
    devices: dict[str, dict[str, Any]] = {}
    device_counter: dict[str, int] = {}  # zone → counter for IP assignment

    for spec in device_specs:
        count = spec.get("count", 1)
        for i in range(count):
            device_id = _make_device_id(spec, i, devices)
            zone_id = spec.get("zone", "control")
            zone = zone_map.get(zone_id, {})
            subnet_offset = zone.get("subnet_offset", 0)

            # Track per-zone IP counter
            zone_counter_key = f"{range_index}.{subnet_offset}"
            idx = device_counter.get(zone_counter_key, 10)
            device_counter[zone_counter_key] = idx + 1

            ip_address = f"10.{range_index}.{subnet_offset}.{idx}"

            # Resolve fingerprint
            vendor = spec.get("vendor", "unknown")
            fingerprint_model = spec.get("fingerprint_model", "")
            fingerprint = None
            if vendor and fingerprint_model:
                fingerprint = get_fingerprint_by_vendor_model(vendor, fingerprint_model)
                if not fingerprint:
                    warnings.append(
                        f"Unresolved fingerprint: {vendor}/{fingerprint_model} "
                        f"for device '{spec.get('name', device_id)}'"
                    )

            # Generate MAC — use fingerprint's OUI list when available
            fp_ouis = fingerprint.get("oui_prefixes") if fingerprint else None
            mac = generate_mac_address(
                vendor=vendor,
                device_type=spec.get("type"),
                oui_prefixes=fp_ouis if fp_ouis else None,
            )

            device_name = spec.get("name", device_id)
            if count > 1:
                device_name = f"{device_name}_{i + 1}"

            devices[device_id] = {
                "id": device_id,
                "name": device_name,
                "type": spec.get("type", "unknown"),
                "vendor": vendor,
                "fingerprintModel": fingerprint_model,
                "vendorFingerprint": fingerprint or {},
                "protocols": spec.get("protocols", []),
                "zone": zone_id,
                "role": spec.get("role", ""),
                "cve_ids": spec.get("cve_ids", []),
                "external_comms": spec.get("external_comms", False),
                "network": {
                    "ipAddress": ip_address,
                    "macAddress": mac,
                },
            }

    # ── Step 3: Build flows from template ────────────────────────
    flow_specs = template.get("flows", [])
    flows: list[dict[str, Any]] = []
    target_protocols: dict[str, set[str]] = {did: set() for did in devices}

    # Group devices by (type, zone) for source_types/target_types matching
    devices_by_type_zone: dict[tuple[str, str], list[str]] = {}
    devices_by_type: dict[str, list[str]] = {}
    for did, dev in devices.items():
        dtype = dev["type"]
        dzone = dev["zone"]
        devices_by_type_zone.setdefault((dtype, dzone), []).append(did)
        devices_by_type.setdefault(dtype, []).append(did)

    flow_counter = 0
    for fspec in flow_specs:
        protocol_raw = fspec.get("protocol", "modbus_tcp")
        source_types = fspec.get("source_types", [])
        target_types = fspec.get("target_types", [])
        source_zones = fspec.get("source_zones")  # Optional zone filter
        target_zones = fspec.get("target_zones")  # Optional zone filter

        # Collect matching source and target device IDs
        sources = _match_devices(
            devices, devices_by_type, devices_by_type_zone,
            source_types, source_zones,
        )
        targets = _match_devices(
            devices, devices_by_type, devices_by_type_zone,
            target_types, target_zones,
        )

        if not sources or not targets:
            continue

        # Avoid self-flows for same-type combinations
        # (e.g., PLC-to-PLC where source and target overlap)
        pairs = _build_flow_pairs(sources, targets, fspec)

        for src_id, dst_id in pairs:
            flow_counter += 1
            flow_id = f"flow_{flow_counter:04d}"

            flow_dict = {
                "id": flow_id,
                "sourceDeviceId": src_id,
                "targetDeviceId": dst_id,
                "protocol": protocol_raw,
                "config": {
                    "poll_interval_ms": fspec.get("interval_ms", 1000),
                    "jitter_ms": fspec.get("jitter_ms", 0),
                },
            }
            flows.append(flow_dict)

            # Track target protocols for validation
            target_protocols.setdefault(dst_id, set()).add(protocol_raw)
            # Source may also serve identity in some bidirectional protocols
            target_protocols.setdefault(src_id, set())

    # ── Step 4: Build FlowContexts ───────────────────────────────
    flow_contexts: list[FlowContext] = []
    scenario_id = f"validate-{template_name}"

    for flow_dict in flows:
        fc = _build_flow_context(flow_dict, devices, scenario_id)
        if fc:
            flow_contexts.append(fc)

    # ── Step 5: Build DeviceExpectations for ALL devices ─────────
    # Every device must be on-the-wire fingerprintable, not just targets.
    # Source-only devices get fingerprinted via ambient discovery
    # (Modbus MEI, EtherNet/IP ListIdentity, S7 SZL, SNMP GET, etc.)
    device_expectations: dict[str, DeviceExpectation] = {}
    for did, dev in devices.items():
        fp = dev.get("vendorFingerprint", {})
        if not fp:
            continue  # Skip devices with no fingerprint
        mac = dev["network"]["macAddress"].upper()
        serving = target_protocols.get(did, set())

        # Determine all protocols this device has (for ambient discovery)
        device_protocols = set(dev.get("protocols", []))

        device_expectations[mac] = DeviceExpectation(
            device_id=did,
            device_name=dev["name"],
            mac_address=mac,
            ip_address=dev["network"]["ipAddress"],
            vendor=fp.get("vendor", dev.get("vendor", "unknown")),
            model=fp.get("model", dev.get("fingerprintModel", "unknown")),
            fingerprint=fp,
            expected_oui_prefixes=fp.get("oui_prefixes", []),
            protocols_serving=serving,
            all_protocols=device_protocols,
        )

    return ScenarioBuildResult(
        template_name=template_name,
        vertical=vertical,
        display_name=display_name,
        devices=devices,
        flows=flows,
        flow_contexts=flow_contexts,
        device_expectations=device_expectations,
        target_protocols=target_protocols,
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────
# Enumeration Helpers
# ─────────────────────────────────────────────────────────────────

def list_all_templates() -> list[tuple[str, str]]:
    """Return all (vertical, template_name) pairs."""
    result = []
    for vertical, templates in VERTICAL_TEMPLATES.items():
        for tname in templates:
            result.append((vertical, tname))
    return result


def list_templates_for_vertical(vertical: str) -> list[str]:
    """Return template names for a vertical."""
    return list(VERTICAL_TEMPLATES.get(vertical, {}).keys())


# ─────────────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────────────

def _make_device_id(spec: dict, index: int, existing: dict) -> str:
    """Generate a unique device ID from the spec."""
    name = spec.get("name", spec.get("type", "device"))
    # Sanitize: lowercase, replace spaces with underscores
    base = name.lower().replace(" ", "_").replace("-", "_")
    count = spec.get("count", 1)
    if count > 1:
        candidate = f"{base}_{index + 1}"
    else:
        candidate = base

    # Ensure uniqueness
    if candidate in existing:
        candidate = f"{candidate}_{random.randint(1000, 9999)}"
    return candidate


def _match_devices(
    devices: dict[str, dict],
    devices_by_type: dict[str, list[str]],
    devices_by_type_zone: dict[tuple[str, str], list[str]],
    type_list: list[str],
    zone_filter: list[str] | None,
) -> list[str]:
    """Match devices by type and optional zone filter."""
    matched: list[str] = []
    for dtype in type_list:
        if zone_filter:
            for zone in zone_filter:
                matched.extend(devices_by_type_zone.get((dtype, zone), []))
        else:
            matched.extend(devices_by_type.get(dtype, []))
    return matched


def _build_flow_pairs(
    sources: list[str],
    targets: list[str],
    fspec: dict,
) -> list[tuple[str, str]]:
    """Build (source, target) pairs with round-robin distribution.

    Avoids self-flows where source == target.
    """
    pairs: list[tuple[str, str]] = []

    # For each source, assign targets round-robin
    if len(sources) <= len(targets):
        # Each source gets one or more targets
        for i, src in enumerate(sources):
            # Distribute targets across sources
            assigned_targets = [
                t for j, t in enumerate(targets) if t != src
            ]
            if not assigned_targets:
                continue
            # Assign proportionally
            chunk_size = max(1, len(assigned_targets) // len(sources))
            start = (i * chunk_size) % len(assigned_targets)
            for k in range(min(chunk_size, len(assigned_targets))):
                idx = (start + k) % len(assigned_targets)
                pairs.append((src, assigned_targets[idx]))
    else:
        # More sources than targets — each target gets flows from sources
        for i, tgt in enumerate(targets):
            assigned_sources = [s for s in sources if s != tgt]
            if not assigned_sources:
                continue
            chunk_size = max(1, len(assigned_sources) // len(targets))
            start = (i * chunk_size) % len(assigned_sources)
            for k in range(min(chunk_size, len(assigned_sources))):
                idx = (start + k) % len(assigned_sources)
                pairs.append((assigned_sources[idx], tgt))

    return pairs


def _build_flow_context(
    flow_dict: dict,
    devices: dict[str, dict],
    scenario_id: str,
) -> FlowContext | None:
    """Build a FlowContext from a flow dict and device map."""
    source_device = devices.get(flow_dict.get("sourceDeviceId", ""))
    target_device = devices.get(flow_dict.get("targetDeviceId", ""))

    if not source_device or not target_device:
        return None

    protocol_raw = flow_dict.get("protocol", "modbus_tcp")
    engine_protocol = PROTOCOL_ALIASES.get(protocol_raw, protocol_raw)

    try:
        protocol = ProtocolType(engine_protocol)
    except ValueError:
        logger.warning(f"Unknown protocol '{protocol_raw}' (engine: '{engine_protocol}'), skipping")
        return None

    default_port = get_default_port(protocol_raw)

    src_network = source_device.get("network", {})
    dst_network = target_device.get("network", {})

    source = DeviceContext(
        device_id=source_device["id"],
        mac_address=src_network.get("macAddress", "00:00:00:00:00:01"),
        ip_address=src_network.get("ipAddress", "10.0.0.1"),
        port=50000,  # Ephemeral source port
        vendor_fingerprint=source_device.get("vendorFingerprint", {}),
        scenario_id=scenario_id,
        device_name=source_device.get("name"),
    )

    destination = DeviceContext(
        device_id=target_device["id"],
        mac_address=dst_network.get("macAddress", "00:00:00:00:00:02"),
        ip_address=dst_network.get("ipAddress", "10.0.0.2"),
        port=default_port,
        unit_id=1,
        vendor_fingerprint=target_device.get("vendorFingerprint", {}),
        scenario_id=scenario_id,
        device_name=target_device.get("name"),
    )

    config = flow_dict.get("config", {})

    return FlowContext(
        flow_id=flow_dict["id"],
        source=source,
        destination=destination,
        protocol=protocol,
        config=config,
        timing_model={},
    )
