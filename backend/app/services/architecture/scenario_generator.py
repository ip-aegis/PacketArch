# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Scenario generator: Archetype + ScaleTier + VendorProfile -> definition.

This is the new authoring primitive. Templates and the AI wizard call
`generate_from_archetype()` and get back a definition that's already
been:

  - shaped to the archetype's zone skeleton at the requested scale,
  - populated with vendor-pinned devices via the catalog,
  - flow-generated from the comm matrix (no flow exists unless the
    matrix has an entry for the role-pair),
  - protocol-resolved (each flow's protocol is the first the matrix
    suggests that BOTH endpoints' catalog supported_protocols agrees on),
  - conduit-validated (cross-zone flows match a declared conduit),
  - phase-tagged from default lifecycle phases.

Side benefit: the generator is the place where realism rules become
*ergonomic to enforce*. Anything not declared in the matrix can't be
generated. The audit harness will keep its job (verify post-overrides)
but the floor of quality is high before audit even runs.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.name_normalize import normalize_acronyms
from app.protocol_engines.vendor_oui import generate_mac_address
from app.scenario_templates.phases import get_default_phases
from app.services.architecture.archetypes import (
    Archetype,
    ScaleTier,
    VendorProfile,
)
from app.services.architecture.archetypes._base import RoleSlot, ZoneDef
from app.services.architecture.comm_matrix import (
    find_matrix_entries,
    resolve_protocol,
)
from app.services.architecture.role_catalog import get_role
from app.services.architecture.vendor_pinning import (
    get_pin_candidates,
    round_robin_pick,
)
from app.services.device_identity_enricher import (
    enrich_device_serial_numbers,
    enrich_device_unique_identifiers,
)
from app.services.device_templates._fingerprints import (
    get_fingerprint_by_vendor_model,
    get_fingerprint_from_template,
    get_template_by_vendor_model,
)
from app.services.device_templates.firmware_distribution import (
    select_firmware_variant,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cell-zone scaling: how many cells (per archetype) at each tier
# ---------------------------------------------------------------------------

# Sub-vendor rotation for MULTI_VENDOR profile. Each zone of a multi-
# vendor scenario is assigned one sub-vendor from this cycle in order;
# all roles in that zone resolve through that sub-vendor's pinning.
_MULTI_VENDOR_CYCLE: tuple[VendorProfile, ...] = (
    VendorProfile.SIEMENS_SHOP,
    VendorProfile.ROCKWELL_SHOP,
    VendorProfile.SCHNEIDER_SHOP,
    VendorProfile.ABB_SHOP,
)


# Zone-prefix → max-count-by-scale. Zones whose id starts with one of
# these prefixes are limited to the count for the chosen scale tier.
# Other zones (idmz, operations, safety, utilities, station_ops, ...)
# are always kept.
_ZONE_SCALING: dict[str, dict[str, int]] = {
    "cell": {"demo": 1, "small": 2, "medium": 3, "large": 4,
             "multi_site": 4},
    "bay": {"demo": 1, "small": 2, "medium": 3, "large": 4,
            "multi_site": 6},
    "unit": {"demo": 1, "small": 2, "medium": 3, "large": 4,
             "multi_site": 4},
    "station": {"demo": 1, "small": 3, "medium": 5, "large": 8,
                "multi_site": 12},
    "zone": {"demo": 1, "small": 2, "medium": 3, "large": 4,
             "multi_site": 4},
    "intersection": {"demo": 1, "small": 3, "medium": 6, "large": 10,
                     "multi_site": 16},
    "rack": {"demo": 1, "small": 2, "medium": 4, "large": 8,
             "multi_site": 16},
    "lane": {"demo": 1, "small": 2, "medium": 4, "large": 6,
             "multi_site": 8},
    "tunnel_section": {"demo": 1, "small": 2, "medium": 3, "large": 4,
                       "multi_site": 4},
}


def _zone_scaling_prefix(zone_id: str) -> str | None:
    """Return the scaling-prefix matching this zone id, or None if the
    zone is always kept."""
    for prefix in _ZONE_SCALING:
        if zone_id.startswith(prefix) and zone_id != prefix:
            # Only treat as scaled when there's a numeric suffix —
            # `unit` alone matches but `unit1`, `unit2`, ... scale.
            return prefix
    return None


def _select_zones(arch: Archetype, scale: ScaleTier) -> list[ZoneDef]:
    """Pick which zones to materialize for this archetype + scale.

    Zones whose id matches a scaling prefix (cell, bay, unit, station,
    zone, intersection, rack) are limited to the per-scale count.
    Singleton zones (idmz, operations, safety, ...) are always kept.
    """
    counts: dict[str, int] = {p: 0 for p in _ZONE_SCALING}
    out: list[ZoneDef] = []
    for z in arch.zones:
        prefix = _zone_scaling_prefix(z.id)
        if prefix is None:
            out.append(z)
            continue
        limit = _ZONE_SCALING[prefix].get(scale.value, 1)
        if counts[prefix] >= limit:
            continue
        counts[prefix] += 1
        out.append(z)
    return out


# ---------------------------------------------------------------------------
# IP / subnet allocation (intra-scenario)
# ---------------------------------------------------------------------------

def _allocate_ip(zone_offset: int, host_offset: int) -> str:
    """Assign a /16-style address inside the scenario.

    Uses 10.42.{zone_offset}.{host_offset}. The scenario's full /16
    range (10.{n}.0.0/16) is allocated separately at deploy time by
    IPRangeAllocation; this is the per-zone /24 carve-up.
    """
    return f"10.42.{zone_offset}.{host_offset}"


# Matches the leading "zone stem" in slot name_prefixes, e.g.
# "Cell1_Main_PLC" → stem "Cell1_". Used by `_apply_zone_theme` to
# substitute the stem with a semantic theme like "Sugar_Mixing_".
_ZONE_STEM_RE = re.compile(
    r'^(?:Cell|Bay|Unit|Zone|Station|Intersection|Rack|Lane|Tunnel_Section)\d+_'
)


def _apply_zone_theme(
    name_prefix: str | None, theme: str | None,
) -> str | None:
    """Replace a generic zone stem (Cell1_, Bay2_, ...) with a semantic
    theme. Used so AI-generated and template-customized scenarios
    surface meaningful device names ("Sugar_Mixing_Main_PLC") instead
    of the archetype's generic "Cell1_Main_PLC".

    Leaves the prefix alone if it has no zone stem (e.g. IDMZ /
    operations devices) or if no theme is provided.
    """
    if not name_prefix or not theme:
        return name_prefix
    # Normalize theme: collapse spaces to underscores so callers can
    # pass "Sugar Mixing" or "Sugar_Mixing" interchangeably.
    norm = theme.strip().replace(" ", "_")
    if not norm:
        return name_prefix
    if _ZONE_STEM_RE.match(name_prefix):
        return _ZONE_STEM_RE.sub(f"{norm}_", name_prefix)
    return name_prefix


# ---------------------------------------------------------------------------
# Device materialization
# ---------------------------------------------------------------------------

def _materialize_device(
    *,
    device_id: str,
    role_id: str,
    slot: RoleSlot,
    instance_index: int,
    total_count: int,
    zone_id: str,
    zone_offset: int,
    host_offset: int,
    vendor_profile: VendorProfile,
    archetype_vertical: str,
    zone_theme: str | None = None,
) -> dict[str, Any] | None:
    """Build a single device dict matching the existing definition format.

    Returns None if the role is unknown or no fingerprint can be
    resolved (caller should warn but continue).
    """
    role = get_role(role_id)
    if role is None:
        logger.warning("Generator: unknown role_id %s", role_id)
        return None

    # For MULTI_VENDOR profile, pick a per-zone sub-vendor and apply it
    # consistently to every role in that zone. Real multi-vendor plants
    # are arranged as adjacent single-vendor cells (Cell1 all Siemens,
    # Cell2 all Rockwell), not as vendor-mixed cells. Without this, a
    # Schneider PLC ends up wired to Siemens IO and the only shared
    # protocol is SNMP — exactly the audit's "irrational" pattern.
    if vendor_profile == VendorProfile.MULTI_VENDOR:
        sub_vendor = _MULTI_VENDOR_CYCLE[
            zone_offset % len(_MULTI_VENDOR_CYCLE)
        ]
        candidates = get_pin_candidates(sub_vendor, role_id)
        # Fall back to MULTI_VENDOR catalog (IDMZ / network roles) if
        # the sub-vendor lacks a pin for this role.
        if not candidates:
            candidates = get_pin_candidates(vendor_profile, role_id)
        pin = round_robin_pick(candidates, instance_index)
    else:
        candidates = get_pin_candidates(vendor_profile, role_id)
        pin = round_robin_pick(candidates, instance_index)

    cve_ids: list[str] = []
    if pin is None:
        # No pin — emit a minimal device with the role's primary type and
        # no fingerprint. Auto-repair will populate something later.
        vendor = ""
        fingerprint_model = None
        full_fingerprint: dict[str, Any] = {}
    else:
        vendor, fingerprint_model = pin
        # Template-defined mix: resolve the device template, pick the firmware
        # variant for THIS instance, and source BOTH the emitted firmware and
        # the CVEs from that single variant so they always agree on the wire.
        template = _resolve_cve_template(vendor, fingerprint_model)
        variant = (
            select_firmware_variant(template, instance_index, total_count)
            if template else None
        )
        if template and variant:
            full_fingerprint = (
                get_fingerprint_from_template(
                    template.id, firmware_version=variant.version
                ) or {}
            )
            cve_ids = list(variant.cves)
        else:
            full_fingerprint = (
                get_fingerprint_by_vendor_model(vendor, fingerprint_model) or {}
            )
        if not full_fingerprint:
            logger.warning(
                "Generator: catalog missing %s/%s for role %s — "
                "emitting vendor-only device",
                vendor, fingerprint_model, role_id,
            )

    # Pick the canonical device.type for this role.
    device_type = role.primary_device_types[0] if role.primary_device_types else "device"

    # Name: use slot.name_prefix + numeric suffix when slot has >1
    # instances at the chosen scale; bare prefix otherwise. Keeps
    # demo scenarios uncluttered while making large scenarios
    # unambiguous.
    #
    # When a zone_theme is provided (template overrides or AI wizard
    # context like "candy factory"), the generic zone stem (Cell1_,
    # Bay2_, ...) is replaced with the theme so devices land with
    # semantic names like "Mixing_Main_PLC" instead of "Cell1_Main_PLC".
    base_name = slot.name_prefix or role.name.replace(" ", "_")
    base_name = _apply_zone_theme(base_name, zone_theme) or base_name
    if total_count > 1:
        name = f"{base_name}_{instance_index + 1:02d}"
    else:
        name = base_name

    protocols = list(full_fingerprint.get("supported_protocols") or
                     role.required_protocols or ("snmp",))

    fp_ouis = full_fingerprint.get("oui_prefixes") if full_fingerprint else None
    mac = generate_mac_address(
        vendor=vendor or None,
        device_type=device_type,
        oui_prefixes=fp_ouis if fp_ouis else None,
    ) if vendor else None

    device: dict[str, Any] = {
        "id": device_id,
        "name": name,
        "type": device_type,
        "zoneId": zone_id,
        "vendor": vendor,
        "vendorFingerprint": full_fingerprint,
        "fingerprintModel": fingerprint_model,
        "protocols": protocols,
        "network": {
            "ipAddress": _allocate_ip(zone_offset, host_offset),
            "macAddress": mac,
        },
        "role": role.name,
        "architectural_role": role_id,
    }
    if cve_ids:
        device["cveIds"] = cve_ids
    return device


# ---------------------------------------------------------------------------
# Flow generation
# ---------------------------------------------------------------------------

def _materialize_flows(
    devices_by_zone: dict[str, list[dict[str, Any]]],
    archetype: Archetype,
    vendor_profile: VendorProfile,
) -> dict[str, dict[str, Any]]:
    """Walk every (zone_pair x role_pair) combo and emit flows for any
    pair that has a comm-matrix entry."""
    flows: dict[str, dict[str, Any]] = {}
    flow_idx = 0

    # Build role-id -> [device_dict] maps per zone for fast pair-lookup.
    role_index: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for zone_id, devs in devices_by_zone.items():
        role_index[zone_id] = {}
        for d in devs:
            ar = d.get("architectural_role")
            if ar:
                role_index[zone_id].setdefault(ar, []).append(d)

    # All (src_zone, tgt_zone) pairs to consider. Same-zone pairs first
    # (intra-zone flows always allowed); cross-zone only if a conduit
    # exists.
    zone_pairs: list[tuple[str, str]] = []
    zone_ids = list(devices_by_zone.keys())
    for sz in zone_ids:
        for tz in zone_ids:
            zone_pairs.append((sz, tz))

    conduit_set: set[tuple[str, str]] = set()
    for c in archetype.conduits:
        conduit_set.add((c.source_zone, c.target_zone))
        if c.direction == "bidirectional":
            conduit_set.add((c.target_zone, c.source_zone))

    for src_zone, tgt_zone in zone_pairs:
        cross_zone = (src_zone != tgt_zone)
        if cross_zone and (src_zone, tgt_zone) not in conduit_set:
            continue
        for src_role, src_devs in role_index.get(src_zone, {}).items():
            for tgt_role, tgt_devs in role_index.get(tgt_zone, {}).items():
                if src_role == tgt_role and src_zone == tgt_zone:
                    # Same-role same-zone fan-out only meaningful for
                    # protection_relay GOOSE; skip otherwise.
                    if src_role != "protection_relay":
                        continue
                entries = find_matrix_entries(
                    src_role, tgt_role, archetype.vertical,
                )
                if not entries:
                    continue
                for entry in entries:
                    flow_idx = _emit_flows(
                        flows=flows,
                        flow_idx=flow_idx,
                        entry=entry,
                        src_devs=src_devs,
                        tgt_devs=tgt_devs,
                        vendor_profile=vendor_profile,
                    )

    return flows


def _emit_flows(
    *,
    flows: dict[str, dict[str, Any]],
    flow_idx: int,
    entry: Any,  # CommEntry
    src_devs: list[dict[str, Any]],
    tgt_devs: list[dict[str, Any]],
    vendor_profile: VendorProfile,
) -> int:
    """Emit zero or more flow dicts per CommEntry × (src, tgt) device
    pair. Returns the new flow_idx."""
    for src in src_devs:
        for tgt in tgt_devs:
            if src["id"] == tgt["id"]:
                continue
            src_supp = set(src.get("protocols") or [])
            tgt_supp = set(tgt.get("protocols") or [])
            proto = resolve_protocol(
                entry, vendor_profile, src_supp, tgt_supp,
            )
            if proto is None:
                logger.warning(
                    "Generator: no shared protocol for %s -> %s "
                    "(matrix entry expected %s)",
                    src["name"], tgt["name"], entry.protocol_options,
                )
                continue
            flow_idx += 1
            fid = f"flow_{flow_idx:03d}"
            interval = (entry.interval_ms[0] + entry.interval_ms[1]) // 2
            timing: dict[str, Any] = {"intervalMs": interval}
            if entry.jitter_ms[1] > 0:
                timing["jitterMs"] = entry.jitter_ms[1]
                timing["jitterType"] = "uniform"
            flows[fid] = {
                "id": fid,
                "sourceDeviceId": src["id"],
                "targetDeviceId": tgt["id"],
                "protocol": proto,
                "timing": timing,
                "config": {
                    "pattern": entry.pattern,
                    "phase_tags": list(entry.phase_tags),
                    "matrix_origin": True,
                },
            }
    return flow_idx


# ---------------------------------------------------------------------------
# Top-level entry
# ---------------------------------------------------------------------------

# Hand-verified scenario-model -> device-template-model aliases (same product
# family, CVEs verifiably apply). Mirrors the scenario-template projection.
_CVE_MODEL_ALIAS = {
    ("rockwell", "PowerFlex 525"): "25B-D030N104",
    ("delta_controls", "Manager"): "enteliBUS Manager",
    ("econolite", "Cobalt ATC"): "ASC/3-2100 Cobalt",
    ("siemens", "6ES7 516-3FN01-0AB0"): "6ES7 516-3AN02-0AB0",
    ("siemens", "6ES7 516-3FN02-0AB0"): "6ES7 516-3AN02-0AB0",
    ("siemens", "6ES7 517-3AP00-0AB0"): "6ES7 516-3AN02-0AB0",
    ("rockwell", "1756-L84E"): "1756-L83E",
    ("rockwell", "1756-L85E"): "1756-L83E",
    ("rockwell", "1756-L83ES"): "1756-L83E",
}


def _resolve_cve_template(vendor: str, fingerprint_model: str | None):
    """Resolve the device template backing a pin, applying cross-family model
    aliases. Returns a ``DeviceTemplate`` or None.

    The alias map handles scenario models that share a product family (and CVE
    applicability) with a differently-named template model, e.g. a GuardLogix
    catalog number mapped to its ControlLogix template. ``firmware_variants`` on
    the resolved template are the single source of truth for the instance's
    firmware + CVEs (see ``select_firmware_variant``).
    """
    if not fingerprint_model:
        return None
    model = _CVE_MODEL_ALIAS.get((vendor.lower(), fingerprint_model), fingerprint_model)
    return get_template_by_vendor_model(vendor, model)


def generate_from_archetype(
    archetype: Archetype | str,
    vendor_profile: VendorProfile | str = None,  # type: ignore[assignment]
    scale: ScaleTier | str = ScaleTier.MEDIUM,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize a full scenario definition from an archetype.

    The returned dict matches the existing scenario `definition` shape
    used by `populate_definition_from_template` and the audit harness:
    `{devices, flows, zones, conduits, phases, cell_isolation}`.

    Parameters
    ----------
    archetype: Archetype or archetype id string.
    vendor_profile: VendorProfile or its .value. If None, the
        archetype's default_vendor_profile is used.
    scale: ScaleTier or its .value.
    overrides: free-form dict of per-zone or per-device overrides.
        Honored as-is (caller's responsibility) — the flag enables
        the AI wizard's strict-composition + explicit override path.
    """
    from app.services.architecture.archetypes import get_archetype

    if isinstance(archetype, str):
        a = get_archetype(archetype)
        if a is None:
            raise ValueError(f"Unknown archetype: {archetype}")
        archetype = a

    if vendor_profile is None:
        vendor_profile = archetype.default_vendor_profile
    elif isinstance(vendor_profile, str):
        vendor_profile = VendorProfile(vendor_profile)

    if not archetype.supports_vendor_profile(vendor_profile):
        raise ValueError(
            f"Archetype {archetype.id} does not support "
            f"vendor profile {vendor_profile.value}"
        )

    if isinstance(scale, str):
        scale = ScaleTier(scale)

    if scale.numeric < archetype.min_scale.numeric:
        raise ValueError(
            f"Archetype {archetype.id} requires scale >= "
            f"{archetype.min_scale.value}; got {scale.value}"
        )

    overrides = overrides or {}
    # Zone themes: maps zone_id -> theme string. The theme replaces
    # generic stems (Cell1_, Bay2_, Unit3_) in device names AND becomes
    # the zone's display name. Used by templates (per-template themes
    # in legacy_template_archetypes.py) and the AI wizard ("candy
    # factory" -> Mixing/Cooking/Wrapping).
    zone_themes: dict[str, str] = dict(overrides.get("zone_themes") or {})

    def _themed_zone_name(z: ZoneDef) -> str:
        theme = zone_themes.get(z.id)
        name = theme.strip().replace("_", " ") if theme else z.name
        return normalize_acronyms(name)

    # ----- 1. Zone materialization ------------------------------------
    selected_zones = _select_zones(archetype, scale)
    zone_dicts: dict[str, dict[str, Any]] = {}
    zone_offset_map: dict[str, int] = {}
    for offset, z in enumerate(selected_zones):
        zone_offset_map[z.id] = offset
        zone_dicts[z.id] = {
            "id": z.id,
            "name": _themed_zone_name(z),
            "level": z.purdue_level,
            "network": {
                "subnet": f"10.42.{offset}.0/24",
                "subnet_offset": offset,
                "vlan": 100 + offset,
            },
            "security_level": z.security_level,
            "is_external": z.is_external,
            "description": z.description,
        }

    # ----- 2. Device materialization ----------------------------------
    devices: dict[str, dict[str, Any]] = {}
    devices_by_zone: dict[str, list[dict[str, Any]]] = {
        z.id: [] for z in selected_zones
    }
    device_idx = 0
    for z in selected_zones:
        if z.is_external:
            # External zones host no devices we generate (they may host
            # cloud_service_link IPs but those are managed elsewhere).
            host_off = 10
            for slot in z.role_slots:
                count = slot.count_at(scale)
                for i in range(count):
                    device_idx += 1
                    did = f"device_{device_idx:03d}"
                    dev = _materialize_device(
                        device_id=did,
                        role_id=slot.role_id,
                        slot=slot,
                        instance_index=i,
                        total_count=count,
                        zone_id=z.id,
                        zone_offset=zone_offset_map[z.id],
                        host_offset=host_off,
                        vendor_profile=vendor_profile,
                        archetype_vertical=archetype.vertical,
                        zone_theme=zone_themes.get(z.id),
                    )
                    if dev:
                        devices[did] = dev
                        devices_by_zone[z.id].append(dev)
                        host_off += 1
            continue

        host_off = 10  # leave .1-.9 for switches / gateway
        for slot in z.role_slots:
            count = slot.count_at(scale)
            for i in range(count):
                device_idx += 1
                did = f"device_{device_idx:03d}"
                dev = _materialize_device(
                    device_id=did,
                    role_id=slot.role_id,
                    slot=slot,
                    instance_index=i,
                    total_count=count,
                    zone_id=z.id,
                    zone_offset=zone_offset_map[z.id],
                    host_offset=host_off,
                    vendor_profile=vendor_profile,
                    archetype_vertical=archetype.vertical,
                    zone_theme=zone_themes.get(z.id),
                )
                if dev:
                    devices[did] = dev
                    devices_by_zone[z.id].append(dev)
                    host_off += 1

    # ----- 3. Identity enrichment (serials, station names) ------------
    # The enricher is per-device + scenario_id; we use a synthesized
    # scenario id so deterministic-per-instance serials are stable
    # within a single generator run.
    pseudo_scenario_id = (
        f"gen-{archetype.id}-{vendor_profile.value}-{scale.value}"
    )
    for did, dev in devices.items():
        try:
            enrich_device_serial_numbers(dev, did, pseudo_scenario_id)
            enrich_device_unique_identifiers(dev, did, pseudo_scenario_id)
        except Exception:  # noqa: BLE001
            logger.exception("Generator: enrichment failed for %s", did)

    # ----- 4. Flow materialization (matrix-driven) --------------------
    flows = _materialize_flows(devices_by_zone, archetype, vendor_profile)

    # ----- 5. Conduit materialization ---------------------------------
    selected_zone_ids = {z.id for z in selected_zones}
    conduits: dict[str, dict[str, Any]] = {}
    for c in archetype.conduits:
        if c.source_zone not in selected_zone_ids:
            continue
        if c.target_zone not in selected_zone_ids:
            continue
        conduits[c.id] = {
            "id": c.id,
            "name": c.name,
            "sourceZoneId": c.source_zone,
            "targetZoneId": c.target_zone,
            "direction": c.direction,
            "allowedProtocols": list(c.allowed_protocols),
            "securityLevel": c.security_level,
            "description": c.description,
            "autoGenerated": False,
        }

    # ----- 6. Phases --------------------------------------------------
    phases = get_default_phases(
        total_duration_ms=overrides.get("total_duration_ms", 600_000),
        preset=overrides.get("phase_preset"),
        vertical=archetype.vertical,
    )

    # CVEs are assigned per-instance in _materialize_device() from the chosen
    # firmware variant (template-defined mix), so firmware + CVEs always agree
    # on the wire. No separate post-pass projection.

    # ----- 7. Definition assembly -------------------------------------
    definition: dict[str, Any] = {
        "devices": devices,
        "flows": flows,
        "zones": zone_dicts,
        "conduits": conduits,
        "phases": phases,
        "cell_isolation": {
            "mode": archetype.cell_isolation_default,
        },
        "_generator_meta": {
            "archetype": archetype.id,
            "vendor_profile": vendor_profile.value,
            "scale": scale.value,
            "vertical": archetype.vertical,
        },
    }

    return definition
