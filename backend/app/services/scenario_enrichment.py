# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Deploy-time scenario enrichment.

Helpers that augment a scenario definition with derivable behavior
before it is sent to an agent. Keeps the on-disk scenario clean while
guaranteeing that certain device archetypes (remote-access gateways,
etc.) always exhibit their characteristic traffic pattern.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud_service import CloudServiceEndpoint, CloudServiceProvider

logger = logging.getLogger(__name__)


# Device types that ALWAYS need a cloud-service link so CV sees them as
# remote-access endpoints. Mapping: device_type -> (provider, region_hint).
# region_hint is best-effort; the helper falls back to any region for the
# provider if the specific region isn't seeded.
#
# Any device whose entire purpose is to terminate an inbound or outbound
# external tunnel belongs here — without an external destination the device
# has no observable traffic and Cyber Vision sees a silent box.
_REMOTE_ACCESS_DEVICE_TYPES: dict[str, tuple[str, str | None]] = {
    # eWON / HMS family
    "ewon_gateway": ("talk2m", "us-west"),
    "ewon": ("talk2m", "us-west"),
    "remote_gateway": ("talk2m", "us-west"),
    # Cellular / industrial routers — phone home to vendor cloud
    "cellular_gateway": ("talk2m", "us-west"),
    "industrial_router": ("talk2m", "us-west"),
    "remote_access_gateway": ("talk2m", "us-west"),
    # Bastion / jump / RDP — administrators reach in via relay
    "jump_server": ("teamviewer", "global"),
    "bastion": ("teamviewer", "global"),
    "rdp_gateway": ("teamviewer", "global"),
    "vpn_gateway": ("teamviewer", "global"),
    # Generic IoT cloud connectors
    "cloud_connector": ("azure_iot", "us"),
    "iot_gateway": ("azure_iot", "us"),
    "edge_gateway": ("aws_iot", "us-east-1"),
}


async def ensure_remote_access_cloud_links(
    db: AsyncSession,
    definition: dict[str, Any],
) -> dict[str, Any]:
    """Auto-attach a cloud_service_link to every remote-access device that
    doesn't already have one.

    EWON / jump server / remote-access gateways exist in scenarios for one
    reason: to talk out to a cloud relay. Without a link CV sees them as
    silent boxes. We synthesise the link at deploy time so the user doesn't
    have to wire one up by hand. Idempotent: a device with an existing link
    is left alone.

    Returns the (possibly mutated copy of the) definition.
    """
    devices = definition.get("devices", {})
    if isinstance(devices, list):
        devices = {d.get("id", str(i)): d for i, d in enumerate(devices)}
    if not devices:
        return definition

    existing_links = list(definition.get("cloud_service_links", []) or [])
    linked_device_ids = {
        link.get("device_id") for link in existing_links if link.get("device_id")
    }

    additions: list[dict[str, Any]] = []
    next_index = len(existing_links)
    for device_id, device in devices.items():
        device_type = (device.get("type") or "").lower()
        if device_type not in _REMOTE_ACCESS_DEVICE_TYPES:
            continue
        if device_id in linked_device_ids:
            continue

        provider, region_hint = _REMOTE_ACCESS_DEVICE_TYPES[device_type]
        try:
            provider_enum = CloudServiceProvider(provider)
        except ValueError:
            logger.warning(
                "Unknown cloud provider %r for device type %s — skipping",
                provider, device_type,
            )
            continue

        # Region-preferred lookup, fallback to any region for the provider.
        query = select(CloudServiceEndpoint).where(
            CloudServiceEndpoint.provider == provider_enum,
            CloudServiceEndpoint.is_active.is_(True),  # noqa: E712
        )
        endpoint = None
        if region_hint:
            scoped = query.where(CloudServiceEndpoint.region == region_hint)
            endpoint = (await db.execute(scoped.limit(1))).scalar_one_or_none()
        if endpoint is None:
            endpoint = (await db.execute(query.limit(1))).scalar_one_or_none()
        if endpoint is None:
            logger.warning(
                "No cloud endpoint seeded for provider %s — %s (%s) will have "
                "no external comms",
                provider, device.get("name") or device_id, device_type,
            )
            continue

        next_index += 1
        link_id = f"csl_auto_{next_index:03d}"
        additions.append({
            "id": link_id,
            "device_id": device_id,
            "cloud_service_id": str(endpoint.id),
            "heartbeat_interval_ms": endpoint.heartbeat_interval_ms or 30000,
            "enabled": True,
            "auto_generated": True,
            "cloud_service": {
                "name": endpoint.name,
                "provider": endpoint.provider.value,
                "primary_ip": endpoint.primary_ip,
                "port": endpoint.port,
                "hostname": endpoint.hostname,
                "tls_enabled": endpoint.tls_enabled,
            },
        })
        logger.info(
            "Auto-attached cloud link %s: %s (%s) -> %s (%s)",
            link_id, device.get("name") or device_id, device_type,
            endpoint.name, endpoint.primary_ip,
        )

    if not additions:
        return definition

    new_def = {**definition}
    new_def["cloud_service_links"] = existing_links + additions
    return new_def


# ----------------------------------------------------------------------
# Device-flow coverage: prevent orphan devices
# ----------------------------------------------------------------------

# Manager-shaped device types that naturally poll other devices.
_MANAGER_TYPES: tuple[str, ...] = (
    "hmi", "scada_server", "historian",
    "engineering_workstation", "engineering_station",
    "fleet_manager", "server", "workstation",
)
# PLCs poll their cell's field devices over PROFINET / EtherNet-IP / Modbus.
_PLC_TYPES: tuple[str, ...] = (
    "plc", "safety_plc", "rtu", "controller", "robot_controller",
)
# Field devices typically polled by their cell's PLC.
_FIELD_TYPES: tuple[str, ...] = (
    "drive", "vfd", "servo", "io_module", "sensor", "actuator",
    "valve", "transmitter", "analyzer",
)
# Network-management peers for switches/routers.
_NETWORK_DEVICE_TYPES: tuple[str, ...] = ("switch", "router", "firewall")

# Protocol preference for synthesising coverage flows.
# Layer-3 protocols only — PROFINET RT/DCP and other L2-only protocols are
# excluded because they don't help CV correlate MAC↔IP, which is the whole
# reason coverage flows exist.
_PROTOCOL_PRIORITY: tuple[str, ...] = (
    "s7comm_plus", "s7comm",          # Siemens vendor-native
    "ethernet_ip", "cip_safety",      # Rockwell / ODVA
    "opc_ua",                          # cross-vendor industrial control
    "modbus_tcp",                      # widest interop
    "bacnet", "dnp3", "iec104",       # vertical-specific fallbacks
    "fins", "slmp",
    # Remote-access protocols rank above SNMP — when a jump server is
    # paired with a switch (only "ssh" and "snmp" shared), the snap picks
    # ssh because that's how the admin actually accesses the gear.
    "ssh", "telnet", "rdp", "https",
    "snmp",                            # universal monitoring overlay
)
# L3 Operations zone manager priority — matches Purdue convention where
# engineering workstations program PLCs, SCADA monitors them, etc.
_L3_MANAGER_PRIORITY: tuple[str, ...] = (
    "engineering_workstation", "engineering_station",
    "scada_server", "historian", "hmi",
    "fleet_manager", "server", "workstation",
)


def _zone_id_of(device: dict[str, Any]) -> str | None:
    """Resolve zone id matching cell_isolation._zone_of priority."""
    return (
        device.get("zoneId")
        or device.get("zone_id")
        or device.get("zone")
        or None
    )


def _zone_level(zone: dict[str, Any]) -> int | None:
    """Floor-int the Purdue level on a zone (handles 3.5 DMZ → 3)."""
    raw = zone.get("level")
    if raw is None:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _device_type(device: dict[str, Any]) -> str:
    return (device.get("type") or "").lower().strip()


def _device_protocols(device: dict[str, Any]) -> list[str]:
    return [
        str(p).lower().strip()
        for p in (device.get("protocols") or [])
        if p
    ]


def _flow_endpoints(flow: dict[str, Any]) -> tuple[str | None, str | None]:
    src = (
        flow.get("sourceDeviceId")
        or flow.get("source_device_id")
        or flow.get("source")
    )
    tgt = (
        flow.get("targetDeviceId")
        or flow.get("destinationDeviceId")
        or flow.get("destination_device_id")
        or flow.get("target")
    )
    return src, tgt


def _normalize_devices(devices: Any) -> dict[str, dict[str, Any]]:
    if isinstance(devices, list):
        return {d.get("id", str(i)): d for i, d in enumerate(devices)}
    return dict(devices or {})


def _normalize_flows(flows: Any) -> dict[str, dict[str, Any]]:
    if isinstance(flows, list):
        return {f.get("id", str(i)): f for i, f in enumerate(flows)}
    return dict(flows or {})


def _normalize_zones(zones: Any) -> dict[str, dict[str, Any]]:
    if isinstance(zones, list):
        return {z.get("id", str(i)): z for i, z in enumerate(zones)}
    return dict(zones or {})


def _pick_protocol(
    orphan_protos: list[str],
    partner_protos: list[str],
) -> str | None:
    """Pick the most realistic shared L3 protocol for a coverage flow."""
    common = set(orphan_protos) & set(partner_protos)
    for p in _PROTOCOL_PRIORITY:
        if p in common:
            return p
    # No shared protocol — fall back to SNMP if either speaks it (overlay
    # monitoring is realistic for any IP device).
    if "snmp" in orphan_protos or "snmp" in partner_protos:
        return "snmp"
    # Last resort: any L3 protocol the orphan speaks (partner can speak it
    # for the synthetic flow even if not declared on the partner — the
    # poll-source role is lighter than the responder role).
    for p in _PROTOCOL_PRIORITY:
        if p in orphan_protos:
            return p
    return None


def _pick_partner(
    orphan: dict[str, Any],
    devices: dict[str, dict[str, Any]],
    zones: dict[str, dict[str, Any]],
    cell_levels: set[int],
) -> tuple[dict[str, Any] | None, str]:
    """Pick a rational partner for a coverage flow.

    Returns (partner, direction). direction ∈ {'inbound', 'outbound'}:
      - inbound: partner polls the orphan (orphan is response source)
      - outbound: orphan polls the partner (orphan is request source)
    inbound is preferred — keeps the orphan as the device whose IP we
    most want CV to bind to its MAC.

    Walks the priority list defined in the design doc and never picks a
    cross-cell partner; cell→L3+ northbound is always allowed.
    """
    orphan_id = orphan.get("id")
    orphan_type = _device_type(orphan)
    orphan_zone_id = _zone_id_of(orphan)
    orphan_zone = zones.get(orphan_zone_id, {}) if orphan_zone_id else {}
    _zone_level(orphan_zone)

    def _candidate_iter(
        zone_filter: str | None = None,
        zone_level: int | None = None,
        zone_level_min: int | None = None,
        zone_level_max: int | None = None,
        type_filter: tuple[str, ...] | None = None,
        type_priority: tuple[str, ...] | None = None,
    ):
        """Yield candidate devices matching constraints. Type-priority
        ordering returns higher-priority types first."""
        candidates: list[dict[str, Any]] = []
        for d in devices.values():
            if d.get("id") == orphan_id:
                continue
            d_zone_id = _zone_id_of(d)
            if zone_filter is not None and d_zone_id != zone_filter:
                continue
            d_zone = zones.get(d_zone_id, {}) if d_zone_id else {}
            d_lvl = _zone_level(d_zone)
            if zone_level is not None and d_lvl != zone_level:
                continue
            if zone_level_min is not None and (
                d_lvl is None or d_lvl < zone_level_min
            ):
                continue
            if zone_level_max is not None and (
                d_lvl is None or d_lvl > zone_level_max
            ):
                continue
            d_type = _device_type(d)
            if type_filter is not None and d_type not in type_filter:
                continue
            candidates.append(d)
        if type_priority:
            order = {t: i for i, t in enumerate(type_priority)}
            candidates.sort(
                key=lambda d: order.get(_device_type(d), len(type_priority))
            )
        return candidates

    # Step 1: same-zone manager — always intra-zone, safe in every isolation
    if orphan_zone_id:
        same_zone_managers = _candidate_iter(
            zone_filter=orphan_zone_id,
            type_filter=_MANAGER_TYPES,
        )
        if same_zone_managers:
            return same_zone_managers[0], "inbound"

    # Step 2: same-zone PLC for field-shaped orphans
    if orphan_zone_id and orphan_type in _FIELD_TYPES:
        same_zone_plcs = _candidate_iter(
            zone_filter=orphan_zone_id,
            type_filter=_PLC_TYPES,
        )
        if same_zone_plcs:
            return same_zone_plcs[0], "inbound"

    # Step 3: L3 Operations zone manager (northbound)
    l3_managers = _candidate_iter(
        zone_level=3,
        type_filter=_MANAGER_TYPES,
        type_priority=_L3_MANAGER_PRIORITY,
    )
    if l3_managers:
        return l3_managers[0], "inbound"

    # Step 4: L3.5 DMZ (any device — gateways live here typically)
    dmz = _candidate_iter(zone_level_min=3, zone_level_max=4)
    if dmz:
        return dmz[0], "inbound"

    # Step 5: nothing rational found
    return None, "inbound"


async def ensure_device_flow_coverage(
    definition: dict[str, Any],
) -> dict[str, Any]:
    """Guarantee every device participates in at least one flow.

    For each orphan device, synthesises a coverage flow with a rational
    partner (same-zone manager → same-zone PLC for field devices → L3
    Operations → L3.5 DMZ) using a shared L3 protocol. Cell-isolation
    aware: never creates cell↔cell traffic.

    This protects CV asset classification from gaps when the user (or AI
    generation) leaves a device wired to nothing, AND clears the way for
    future ambient-traffic suppression (clean_demo_mode v2) without
    losing fingerprintability for devices that depended on ambient
    discovery alone.

    Idempotent: orphan-only — devices already in a flow are untouched.
    """
    devices = _normalize_devices(definition.get("devices"))
    flows = _normalize_flows(definition.get("flows"))
    zones = _normalize_zones(definition.get("zones"))

    if not devices:
        return definition

    # Build set of devices that already participate in some flow.
    in_flow: set[str] = set()
    for f in flows.values():
        s, t = _flow_endpoints(f)
        if s:
            in_flow.add(s)
        if t:
            in_flow.add(t)

    orphan_ids = [did for did in devices if did not in in_flow]
    if not orphan_ids:
        return definition

    iso = definition.get("cell_isolation") or {}
    cell_levels = set(iso.get("applies_to_levels") or [0, 1, 2])

    new_flows = dict(flows)
    next_idx = len(new_flows) + 1
    healed = 0
    for orphan_id in orphan_ids:
        orphan = devices[orphan_id]
        orphan_name = orphan.get("name", orphan_id)
        partner, direction = _pick_partner(orphan, devices, zones, cell_levels)
        if partner is None:
            logger.warning(
                "Orphan device %s (%s) — no rational partner found; "
                "leaving orphan (readiness check will flag it)",
                orphan_name, _device_type(orphan) or "unknown",
            )
            continue

        protocol = _pick_protocol(
            _device_protocols(orphan),
            _device_protocols(partner),
        )
        if not protocol:
            logger.warning(
                "Orphan device %s — no shared L3 protocol with partner "
                "%s; leaving orphan",
                orphan_name, partner.get("name", partner.get("id")),
            )
            continue

        if direction == "inbound":
            src_id, tgt_id = partner.get("id"), orphan_id
            src_name, tgt_name = (
                partner.get("name", src_id),
                orphan_name,
            )
        else:
            src_id, tgt_id = orphan_id, partner.get("id")
            src_name, tgt_name = (
                orphan_name,
                partner.get("name", tgt_id),
            )

        flow_id = f"flow_auto_{next_idx:03d}"
        next_idx += 1
        new_flows[flow_id] = {
            "id": flow_id,
            "sourceDeviceId": src_id,
            "targetDeviceId": tgt_id,
            "protocol": protocol,
            "auto_generated": True,
            "coverage_flow": True,
            "description": (
                f"Coverage flow: {src_name} → {tgt_name} via {protocol}"
            ),
            "timing_model": {"poll_interval_ms": 5000},
        }
        healed += 1
        logger.info(
            "Coverage flow %s: %s -> %s via %s (orphan healed)",
            flow_id, src_name, tgt_name, protocol,
        )

    if healed == 0:
        return definition

    new_def = {**definition}
    new_def["flows"] = new_flows
    return new_def


# ----------------------------------------------------------------------
# Protocol consistency: device.protocols must match fingerprint capabilities
# ----------------------------------------------------------------------

def auto_repair_protocols(definition: dict[str, Any]) -> dict[str, Any]:
    """Sync each device's `protocols` list with its fingerprint's
    authoritative `supported_protocols`.

    Bidirectional:
      - REMOVE: protocols on the device that aren't in supported_protocols.
      - ADD: protocols in supported_protocols but missing from the device.

    The fingerprint converter populates `supported_protocols` from the
    template's explicit declaration (when present) or a vendor-aware
    computed default that filters by both vendor-native heuristics AND
    populated identity blocks. Plus an SNMP carve-out so every
    fingerprintable device exposes SNMP for monitoring.

    Pure / idempotent.
    """
    from app.protocol_engines.protocols import get_supported_protocols
    from app.services.fingerprint_cache import get_fingerprint_cache

    devices_raw = definition.get("devices") or {}
    if isinstance(devices_raw, list):
        devices = {d.get("id", str(i)): d for i, d in enumerate(devices_raw)}
        was_list = True
    else:
        devices = dict(devices_raw)
        was_list = False
    if not devices:
        return definition

    cache = get_fingerprint_cache()
    repaired = 0
    new_devices: dict[str, dict[str, Any]] = {}

    for did, device in devices.items():
        fp_inline = (
            device.get("vendorFingerprint")
            or device.get("vendor_fingerprint")
            or device.get("fingerprint")
            or {}
        )
        vendor = (fp_inline.get("vendor") or "").strip()
        model = (fp_inline.get("model") or "").strip()
        if not vendor or not model:
            new_devices[did] = device
            continue

        full_fp = cache.get_by_vendor_model(vendor, model)
        if not full_fp:
            new_devices[did] = device
            continue

        supported_list = get_supported_protocols(full_fp)
        supported = {p.lower() for p in supported_list}
        existing = [str(p) for p in (device.get("protocols") or [])]
        existing_lower = {p.lower() for p in existing}

        # Keep order: existing-and-supported first, then any newly-added.
        kept = [p for p in existing if p.lower() in supported]
        added = [p for p in supported_list if p.lower() not in existing_lower]
        removed = [p for p in existing if p.lower() not in supported]
        new_protocols = kept + added

        # Also stamp the canonical supported_protocols onto the inline
        # vendorFingerprint so validators reading the inline copy see the
        # same authoritative list. Without this, the inline fp may have
        # stale `*_identity = None` entries that make validators flag
        # protocols the canonical fingerprint actually supports.
        new_inline_fp = dict(fp_inline)
        new_inline_fp["supported_protocols"] = list(supported_list)

        if added or removed or fp_inline.get("supported_protocols") != supported_list:
            repaired += 1
            if added or removed:
                logger.info(
                    "auto_repair_protocols: %s (%s/%s) "
                    "+%s -%s; final %s",
                    device.get("name", did), vendor, model,
                    sorted(added), sorted(removed), sorted(new_protocols),
                )
            new_device = {**device, "protocols": new_protocols}
            # Restore under whichever inline fingerprint key the device used.
            if "vendorFingerprint" in device:
                new_device["vendorFingerprint"] = new_inline_fp
            elif "vendor_fingerprint" in device:
                new_device["vendor_fingerprint"] = new_inline_fp
            elif "fingerprint" in device:
                new_device["fingerprint"] = new_inline_fp
            new_devices[did] = new_device
        else:
            new_devices[did] = device

    if repaired == 0:
        return definition

    new_def = {**definition}
    if was_list:
        order = [d.get("id", str(i)) for i, d in enumerate(devices_raw)]
        new_def["devices"] = [new_devices[k] for k in order if k in new_devices]
    else:
        new_def["devices"] = new_devices
    return new_def


# Vendor-native protocol whitelist. Used by narrow_protocols_by_vendor
# to undo over-broad protocol additions that crept in when fingerprints
# carried identity blocks for protocols the device doesn't actually speak.
# Conservative — when uncertain, list a protocol; the worst case is leaving
# it in place. Vendor names are matched case-insensitive on the leading
# brand word ("Siemens AG" → "siemens", "Rockwell Automation" → "rockwell").
_VENDOR_NATIVE_PROTOCOLS: dict[str, set[str]] = {
    "siemens": {
        "s7", "s7comm", "s7comm_plus",
        "profinet", "profisafe",
        "opc_ua", "snmp", "modbus_tcp", "modbus",
    },
    "rockwell": {
        "ethernet_ip", "enip", "cip_safety",
        "modbus_tcp", "modbus", "opc_ua", "snmp",
    },
    "allen-bradley": {
        "ethernet_ip", "enip", "cip_safety",
        "modbus_tcp", "modbus", "opc_ua", "snmp",
    },
    "schneider": {
        "modbus_tcp", "modbus",
        "ethernet_ip", "enip", "opc_ua", "snmp",
    },
    "abb": {
        "modbus_tcp", "modbus", "profinet", "ethernet_ip", "enip",
        "opc_ua", "snmp", "iec104", "dnp3",
    },
    "honeywell": {"modbus_tcp", "modbus", "opc_ua", "bacnet", "snmp"},
    "yokogawa": {"modbus_tcp", "modbus", "opc_ua", "snmp"},
    "emerson": {"modbus_tcp", "modbus", "opc_ua", "snmp"},
    "ge": {"modbus_tcp", "modbus", "opc_ua", "snmp", "dnp3"},
    "mitsubishi": {"slmp", "modbus_tcp", "modbus", "snmp"},
    "omron": {"fins", "ethernet_ip", "enip", "modbus_tcp", "modbus", "snmp"},
    "fanuc": {"ethernet_ip", "enip", "snmp"},
    "kuka": {"ethernet_ip", "enip", "profinet", "profisafe", "snmp"},
    "abb-robotics": {"ethernet_ip", "enip", "profinet", "snmp"},
    "sel": {"dnp3", "modbus_tcp", "modbus", "snmp"},
    "hms": {"modbus_tcp", "modbus", "https", "snmp"},
    "cisco": {
        "snmp", "ethernet_ip", "enip", "profinet", "profisafe",
    },
    "moxa": {"modbus_tcp", "modbus", "snmp", "ethernet_ip", "enip"},
    "phoenix": {"modbus_tcp", "modbus", "profinet", "ethernet_ip", "enip", "snmp"},
    "phoenix-contact": {"modbus_tcp", "modbus", "profinet", "ethernet_ip", "enip", "snmp"},
    "wago": {"modbus_tcp", "modbus", "ethernet_ip", "enip", "profinet", "snmp"},
    "beckhoff": {"profinet", "ethernet_ip", "enip", "modbus_tcp", "modbus", "opc_ua", "snmp"},
    "microsoft": {"snmp", "https", "rdp"},
    "vmware": {"snmp", "https"},
}


def _vendor_brand(vendor: str) -> str:
    """Strip suffixes ('AG', 'Inc.', 'Automation', 'Group', etc.) and
    lowercase to match the keys in _VENDOR_NATIVE_PROTOCOLS."""
    if not vendor:
        return ""
    first = vendor.strip().lower().split()[0]
    return first.rstrip(".,;:")


def narrow_protocols_by_vendor(definition: dict[str, Any]) -> dict[str, Any]:
    """Trim each device's protocols list to (vendor-native ∪ flow-declared).

    Repair pass for scenarios whose protocols got over-broadened by the
    additive repair logic (since rolled back). Protocols actually used in
    a configured flow involving this device are always preserved — the
    template author's intent wins over vendor-native heuristics. Beyond
    flow-declared, only vendor-native protocols survive.

    Pure / idempotent. Conservative: vendors not in the static whitelist
    are left alone; SNMP and the device's flow-declared protocols are
    always retained.
    """
    devices_raw = definition.get("devices") or {}
    if isinstance(devices_raw, list):
        devices = {d.get("id", str(i)): d for i, d in enumerate(devices_raw)}
        was_list = True
    else:
        devices = dict(devices_raw)
        was_list = False
    if not devices:
        return definition

    flows_raw = definition.get("flows") or {}
    if isinstance(flows_raw, list):
        flows_iter = flows_raw
    else:
        flows_iter = flows_raw.values()

    # Build a per-device set of protocols that flows use this device for.
    flow_protocols_by_device: dict[str, set[str]] = {}
    for f in flows_iter:
        proto = (f.get("protocol") or "").strip().lower()
        if not proto:
            continue
        s, t = _flow_endpoints(f)
        if s:
            flow_protocols_by_device.setdefault(s, set()).add(proto)
        if t:
            flow_protocols_by_device.setdefault(t, set()).add(proto)

    narrowed = 0
    new_devices: dict[str, dict[str, Any]] = {}
    for did, device in devices.items():
        fp_inline = (
            device.get("vendorFingerprint")
            or device.get("vendor_fingerprint")
            or device.get("fingerprint")
            or {}
        )
        vendor_brand = _vendor_brand(fp_inline.get("vendor") or "")
        natives = _VENDOR_NATIVE_PROTOCOLS.get(vendor_brand)
        if not natives:
            new_devices[did] = device
            continue

        existing = [str(p).lower() for p in (device.get("protocols") or [])]
        flow_set = flow_protocols_by_device.get(did, set())
        # Keep set: vendor natives + flow-declared (template intent) + SNMP.
        keep_set = set(natives) | flow_set | {"snmp"}
        kept = [p for p in existing if p in keep_set]
        removed = [p for p in existing if p not in keep_set]
        if removed:
            narrowed += 1
            logger.info(
                "narrow_protocols_by_vendor: %s (%s) dropped %s; kept %s",
                device.get("name", did), vendor_brand,
                sorted(removed), sorted(kept),
            )
            new_devices[did] = {**device, "protocols": kept}
        else:
            new_devices[did] = device

    if narrowed == 0:
        return definition

    new_def = {**definition}
    if was_list:
        order = [d.get("id", str(i)) for i, d in enumerate(devices_raw)]
        new_def["devices"] = [new_devices[k] for k in order if k in new_devices]
    else:
        new_def["devices"] = new_devices
    return new_def


# ----------------------------------------------------------------------
# Flow-protocol consistency: each flow.protocol must be one both
# endpoints actually support
# ----------------------------------------------------------------------

def repair_flow_protocols(definition: dict[str, Any]) -> dict[str, Any]:
    """Snap each flow's protocol to one both endpoints actually support.

    Today's failure mode: a flow says `protocol: "modbus_tcp"` but neither
    endpoint device declares modbus_tcp in its protocols. The traffic
    generator silently skips the flow, CV sees nothing, and the readiness
    check raises a "flow protocol consistency" warning. This pass heals
    them at deploy/save time so authored flows produce traffic.

    Algorithm per flow:
      1. If `flow.protocol` is in BOTH endpoints' supported_protocols, keep.
      2. Else, find shared = source.supported ∩ target.supported.
      3. If shared is non-empty, pick the highest-priority match using
         `_PROTOCOL_PRIORITY` (vendor-native protocols come first, so
         Siemens↔Siemens picks s7 family; Rockwell↔Rockwell picks EnIP;
         mixed picks OPC UA / Modbus).
      4. If shared is empty, log a warning and leave the flow alone — we
         don't fabricate a protocol when there's no rational choice.

    Skips:
      - Cloud-service flows (config.external == True) — own protocol logic
      - Coverage flows (coverage_flow == True) — already authored correctly
      - Flows with auto_repair_skip == True — explicit escape hatch

    Marks repaired flows with auto_protocol_repaired=True and stores the
    original protocol in `original_protocol` for traceability.

    Pure / idempotent.
    """
    from app.protocol_engines.protocols import get_supported_protocols
    from app.services.fingerprint_cache import get_fingerprint_cache

    devices = _normalize_devices(definition.get("devices"))
    flows_raw = definition.get("flows") or {}
    if isinstance(flows_raw, list):
        flows = {f.get("id", str(i)): f for i, f in enumerate(flows_raw)}
        was_list = True
    else:
        flows = dict(flows_raw)
        was_list = False
    if not flows or not devices:
        return definition

    cache = get_fingerprint_cache()

    def _device_supported(device: dict[str, Any]) -> set[str]:
        """Resolve a device's authoritative supported_protocols set,
        preferring the canonical fingerprint cache over the (possibly
        stale) inline copy."""
        fp_inline = (
            device.get("vendorFingerprint")
            or device.get("vendor_fingerprint")
            or device.get("fingerprint")
            or {}
        )
        vendor = (fp_inline.get("vendor") or "").strip()
        model = (fp_inline.get("model") or "").strip()
        if vendor and model:
            canonical = cache.get_by_vendor_model(vendor, model)
            if canonical:
                return {p.lower() for p in get_supported_protocols(canonical)}
        # Cache miss — fall back to inline + identity-key inference.
        return {p.lower() for p in get_supported_protocols(fp_inline)}

    # Cache per device since each may appear in many flows.
    supported_by_device: dict[str, set[str]] = {
        did: _device_supported(d) for did, d in devices.items()
    }

    new_flows: dict[str, dict[str, Any]] = {}
    repaired = 0
    no_shared = 0
    for fid, flow in flows.items():
        # Exemptions
        if (
            flow.get("coverage_flow")
            or flow.get("auto_repair_skip")
            or (flow.get("config") or {}).get("external")
        ):
            new_flows[fid] = flow
            continue

        src_id, tgt_id = _flow_endpoints(flow)
        if not src_id or not tgt_id:
            new_flows[fid] = flow
            continue

        src_supp = supported_by_device.get(src_id)
        tgt_supp = supported_by_device.get(tgt_id)
        if not src_supp or not tgt_supp:
            # One or both endpoints have no fingerprint — can't decide.
            new_flows[fid] = flow
            continue

        current = (flow.get("protocol") or "").strip().lower()
        shared = src_supp & tgt_supp

        # Generic protocols (snmp/http/telnet) are valid as a fallback but
        # poor when a real industrial protocol is also available. If the
        # flow's current protocol is generic but shared has something
        # better, promote — likely a degraded snap from when one endpoint
        # had narrower supported_protocols.
        _GENERIC = {"snmp", "http", "telnet"}
        if (
            current
            and current in src_supp
            and current in tgt_supp
            and current not in _GENERIC
        ):
            new_flows[fid] = flow
            continue
        if (
            current
            and current in _GENERIC
            and current in shared
            and not (shared - _GENERIC)
        ):
            # Generic is the only choice — keep it.
            new_flows[fid] = flow
            continue

        if not shared:
            no_shared += 1
            logger.warning(
                "repair_flow_protocols: flow %s (%s -> %s) has no shared "
                "protocol — leaving as-is (current=%r, src_supp=%s, "
                "tgt_supp=%s)",
                fid, src_id, tgt_id, current,
                sorted(src_supp), sorted(tgt_supp),
            )
            new_flows[fid] = flow
            continue

        # Pick the highest-priority shared protocol. _PROTOCOL_PRIORITY
        # already orders vendor-native protocols first, so Siemens↔Siemens
        # naturally lands on s7-family.
        chosen: str | None = None
        for p in _PROTOCOL_PRIORITY:
            if p in shared:
                chosen = p
                break
        if chosen is None:
            # Shared but none in our priority list — use any deterministic
            # pick to keep idempotency.
            chosen = sorted(shared)[0]

        repaired += 1
        new_flow = {
            **flow,
            "protocol": chosen,
            "auto_protocol_repaired": True,
            "original_protocol": flow.get("protocol"),
        }
        new_flows[fid] = new_flow
        logger.info(
            "repair_flow_protocols: flow %s snapped %r -> %r "
            "(src=%s, tgt=%s, shared=%s)",
            fid, current or "<unset>", chosen, src_id, tgt_id,
            sorted(shared),
        )

    if repaired == 0 and no_shared == 0:
        return definition

    new_def = {**definition}
    if was_list:
        order = [f.get("id", str(i)) for i, f in enumerate(flows_raw)]
        new_def["flows"] = [new_flows[k] for k in order if k in new_flows]
    else:
        new_def["flows"] = new_flows
    return new_def
