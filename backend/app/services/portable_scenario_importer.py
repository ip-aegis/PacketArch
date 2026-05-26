# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Portable scenario import service.

Translates a `PortableScenario` document (the public authoring format
described in `docs/SCENARIO_SPEC.md` and `schemas/packetarch-scenario.v1.json`)
into a fully-materialized internal scenario `definition` and persists it.

The materialization mirrors the path in
`api/routes/templates.py:create_scenario_from_template` so that scenarios
imported via the portable format are functionally identical to those
created from a built-in template.
"""

from __future__ import annotations

import logging
import random
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scenario import Scenario
from app.models.user import User
from app.schemas.portable_scenario import (
    PortableDevice,
    PortablePreferences,
    PortableScenario,
)

logger = logging.getLogger(__name__)


class FingerprintResolutionError(ValueError):
    """Raised when no fingerprint in the local catalog matches a device spec."""


def _normalize_protocols(protocols: list[str]) -> set[str]:
    """Apply protocol aliases so portable input and catalog data compare cleanly."""
    from app.protocol_engines.protocols import resolve_protocol

    return {resolve_protocol(p) for p in protocols}


def resolve_unspecified_fingerprints(
    portable: PortableScenario,
) -> tuple[PortableScenario, list[str]]:
    """Fill in missing vendor / fingerprint_model from the local catalog.

    Resolution is *tolerant*. The resolver tries progressively looser
    constraints before giving up, so an LLM that produced a slightly
    imperfect file still imports — at worst with a warning. Order:

      Tier 0 — fully-specified: vendor + fingerprint_model both set.
               If the model exists in the catalog, keep as-is. If not,
               demote to Tier 1 (vendor-pinned) with a warning.
      Tier 1 — vendor + type + protocols. If no match, demote to Tier 2.
      Tier 2 — type + protocols (capability mode). Honors preferences.
               If no match, demote to Tier 3.
      Tier 3 — type only. Last-resort: pick any device of this type and
               trust the importer's `auto_repair_protocols` to clean up.
               If even that fails, raise FingerprintResolutionError.

    Selection within a tier is deterministic (seeded by scenario name +
    device index) so the same portable JSON always produces the same
    materialized scenario.

    Returns:
        (resolved_scenario, warnings) — warnings is a human-readable list
        of demotions that happened, surfaced in the validate/import
        response so authors know exactly what got loosened.

    Raises:
        FingerprintResolutionError: when even Tier 3 fails.
    """
    from app.services.device_templates import (
        get_all_templates,
        get_fingerprint_by_vendor_model,
    )

    templates = get_all_templates()
    prefs = portable.preferences or PortablePreferences()
    seed_base = prefs.deterministic_seed or portable.name
    excluded = {v.lower() for v in prefs.exclude_vendors}
    preferred = [v.lower() for v in prefs.preferred_vendors]
    warnings: list[str] = []

    def _supports(t: Any, wanted: set[str]) -> bool:
        return wanted.issubset(_normalize_protocols(list(t.supported_protocols)))

    def _hint_text(dev: "PortableDevice", wanted_protos: list[str]) -> str:
        hints: list[str] = []
        if dev.vendor:
            same_vendor = [t for t in templates if t.vendor.lower() == dev.vendor.lower()]
            same_vendor_type = [t for t in same_vendor if t.device_type == dev.type]
            if same_vendor_type:
                protos_available = sorted({
                    p for t in same_vendor_type
                    for p in _normalize_protocols(list(t.supported_protocols))
                })
                hints.append(
                    f"vendor={dev.vendor!r} + type={dev.type!r} only supports "
                    f"protocols {protos_available} in the catalog."
                )
            elif same_vendor:
                types_for_vendor = sorted({t.device_type for t in same_vendor})
                hints.append(
                    f"vendor={dev.vendor!r} has no device of type={dev.type!r}. "
                    f"Available types: {types_for_vendor}."
                )
        type_and_protocol = [
            t for t in templates
            if t.device_type == dev.type
            and wanted_protos
            and set(wanted_protos).issubset(
                _normalize_protocols(list(t.supported_protocols))
            )
        ]
        if type_and_protocol:
            vendors_available = sorted({t.vendor.lower() for t in type_and_protocol})
            hints.append(
                f"type={dev.type!r} with these protocols is available from: "
                f"{vendors_available}."
            )
        return " " + " ".join(hints) if hints else ""

    new_devices: list[PortableDevice] = []
    for idx, dev in enumerate(portable.devices):
        device_label = (
            dev.name_pattern or f"{dev.type}#{idx}"
        )
        wanted = _normalize_protocols(dev.protocols)

        # ── Tier 0 — fully-specified ────────────────────────────────
        if dev.vendor and dev.fingerprint_model:
            if get_fingerprint_by_vendor_model(dev.vendor, dev.fingerprint_model):
                new_devices.append(dev)
                continue
            warnings.append(
                f"Device {device_label!r}: pinned vendor={dev.vendor!r} "
                f"fingerprint_model={dev.fingerprint_model!r} not in catalog — "
                f"falling back to vendor-pinned resolution."
            )
            dev = dev.model_copy(update={"fingerprint_model": None})

        # ── Tier 1 — vendor + type + protocols ──────────────────────
        candidates: list[Any] = []
        if dev.vendor:
            candidates = [
                t for t in templates
                if t.vendor.lower() == dev.vendor.lower()
                and t.device_type == dev.type
                and _supports(t, wanted)
            ]
            if not candidates:
                warnings.append(
                    f"Device {device_label!r}: no vendor={dev.vendor!r} + "
                    f"type={dev.type!r} + protocols={dev.protocols} match — "
                    f"falling back to capability mode (importer will pick "
                    f"any vendor)."
                )
                dev = dev.model_copy(update={"vendor": None})

        # ── Tier 2 — type + protocols (capability mode) ─────────────
        if not candidates:
            candidates = [
                t for t in templates
                if t.device_type == dev.type
                and t.vendor.lower() not in excluded
                and _supports(t, wanted)
            ]

        # ── Tier 3 — type only (last resort; auto_repair will fix
        # protocols downstream) ─────────────────────────────────────
        if not candidates:
            type_only = [
                t for t in templates
                if t.device_type == dev.type
                and t.vendor.lower() not in excluded
            ]
            if type_only:
                candidates = type_only
                warnings.append(
                    f"Device {device_label!r}: no catalog match for "
                    f"type={dev.type!r} + protocols={dev.protocols}. Picking "
                    f"any device of type={dev.type!r} and letting "
                    f"auto_repair_protocols reconcile protocols downstream."
                )

        if not candidates:
            raise FingerprintResolutionError(
                f"No fingerprint in the local catalog matches "
                f"device[{idx}] name_pattern={dev.name_pattern!r} "
                f"(type={dev.type!r}, vendor={dev.vendor!r}, "
                f"protocols={dev.protocols}). The catalog has no device of "
                f"this type at all — change the `type` field to one that "
                f"exists in fingerprint-registry.v1.json.{_hint_text(dev, sorted(wanted))}"
            )

        picker = random.Random(f"{seed_base}|{idx}|{dev.type}|{dev.zone}")

        if not dev.vendor and prefs.vendor_strategy == "preferred" and preferred:
            # Walk preferred_vendors in order, pick the first vendor that
            # has a matching template. This gives authors deterministic
            # control: "I prefer Schneider, then Rockwell, then anyone."
            for pv in preferred:
                hits = [t for t in candidates if t.vendor.lower() == pv]
                if hits:
                    candidates = hits
                    break

        if not dev.vendor and prefs.vendor_strategy == "diverse":
            vendors_in_play = sorted({t.vendor.lower() for t in candidates})
            chosen_vendor = vendors_in_play[idx % len(vendors_in_play)]
            candidates = [t for t in candidates if t.vendor.lower() == chosen_vendor]

        candidates.sort(key=lambda t: (t.vendor.lower(), t.model))
        chosen = picker.choice(candidates)
        new_devices.append(
            dev.model_copy(
                update={
                    "vendor": chosen.vendor.lower(),
                    "fingerprint_model": chosen.model,
                }
            )
        )
        logger.debug(
            "Resolved device[%d] type=%s → vendor=%s model=%s",
            idx,
            dev.type,
            chosen.vendor,
            chosen.model,
        )

    return portable.model_copy(update={"devices": new_devices}), warnings


def portable_to_template_dict(portable: PortableScenario) -> dict[str, Any]:
    """Translate a validated portable scenario into the legacy template dict shape.

    The template materializer in `routes/templates.py` consumes dicts in the
    shape produced by `scenario_templates/base.py`. The portable format is a
    near-1:1 match (snake_case throughout), so this is mostly key copying with
    a few renames.
    """
    template: dict[str, Any] = {
        "name": portable.name,
        "description": portable.description or "",
        "vertical": portable.vertical or "manufacturing",
        "total_duration_ms": portable.total_duration_ms,
        "zones": [
            {
                "id": z.id,
                "name": z.name,
                "level": z.purdue_level,
                "vlan": z.vlan,
                "subnet_offset": idx,
                "security_level": z.security_level,
                **({"subnet": z.subnet} if z.subnet else {}),
            }
            for idx, z in enumerate(portable.zones)
        ],
        "devices": [
            {
                "type": d.type,
                "vendor": d.vendor,
                "count": d.count,
                "zone": d.zone,
                "name_pattern": d.name_pattern or "{type}-{n:03d}",
                "protocols": list(d.protocols),
                **({"fingerprint_model": d.fingerprint_model} if d.fingerprint_model else {}),
                **({"role": d.role} if d.role else {}),
                **({"architectural_role": d.architectural_role} if d.architectural_role else {}),
                **({"cve_ids": list(d.cve_ids)} if d.cve_ids else {}),
                **(
                    {
                        "error_config": {
                            "exception_rate": d.error_config.exception_rate,
                            "timeout_rate": d.error_config.timeout_rate,
                            "retry_behavior": d.error_config.retry_behavior,
                            "max_retries": d.error_config.max_retries,
                        }
                    }
                    if d.error_config
                    else {}
                ),
            }
            for d in portable.devices
        ],
        "flows": [
            {
                "protocol": f.protocol,
                "pattern": f.pattern,
                "interval_ms": f.interval_ms,
                "source_types": list(f.source_types),
                "target_types": list(f.target_types),
                **({"source_zones": list(f.source_zones)} if f.source_zones else {}),
                **({"target_zones": list(f.target_zones)} if f.target_zones else {}),
                "jitter_ms": f.jitter_ms,
                "jitter_type": f.jitter_type,
            }
            for f in portable.flows
        ],
    }

    if portable.conduits:
        template["conduits"] = [
            {
                "id": c.id,
                "name": c.name or c.id,
                "source_zone": c.source_zone,
                "target_zone": c.target_zone,
                "direction": c.direction,
                "allowed_protocols": list(c.allowed_protocols),
                "security_level": c.security_level,
                **({"description": c.description} if c.description else {}),
            }
            for c in portable.conduits
        ]

    if portable.external_comms:
        template["external_comms"] = portable.external_comms.model_dump()

    if portable.anomalies:
        template["suggested_anomalies"] = portable.anomalies.model_dump()

    if portable.modes:
        if portable.modes.cell_isolation_mode != "off":
            template["cell_isolation"] = {"mode": portable.modes.cell_isolation_mode}

    return template


async def import_portable_scenario(
    portable: PortableScenario,
    *,
    current_user: User,
    db: AsyncSession,
    use_ai_naming: bool = True,
) -> Scenario:
    """Materialize a portable scenario into a persisted Scenario row.

    This reuses the template materializer's helpers so importer output is
    indistinguishable from a scenario created via the built-in templates.
    """
    from app.api.routes.templates import (
        _auto_assign_ips,
        _build_zones_from_template,
    )
    from app.protocol_engines.vendor_oui import generate_mac_address
    from app.services.architecture.role_catalog import default_role_for_device_type
    from app.services.architecture.site_naming_pipeline import (
        apply_site_naming_pipeline,
    )
    from app.services.conduit_service import generate_default_conduits
    from app.services.device_identity_enricher import (
        enrich_device_serial_numbers,
        enrich_device_unique_identifiers,
    )
    from app.services.device_templates._fingerprints import (
        get_fingerprint_by_vendor_model,
    )
    from app.services.ip_management import IPManagementService
    from app.scenario_templates.phases import get_default_phases
    from app.services.scenario_enrichment import (
        auto_repair_protocols,
        ensure_device_flow_coverage,
        repair_flow_protocols,
    )

    # Resolve any device specs that omit vendor / fingerprint_model
    # against the local catalog. After this call every device has both
    # fields populated, so the rest of the pipeline matches the path
    # that built-in templates take. Warnings document any auto-fallback
    # demotions (e.g., bad fingerprint_model → vendor-pinned → capability).
    portable, fallback_warnings = resolve_unspecified_fingerprints(portable)
    for w in fallback_warnings:
        logger.warning("portable import fallback: %s", w)

    template = portable_to_template_dict(portable)
    vertical = template["vertical"]

    # Step 1: create scenario shell so we have an ID for IP allocation
    scenario = Scenario(
        id=uuid.uuid4(),
        name=portable.name,
        description=portable.description or "",
        vertical=vertical,
        total_duration_ms=portable.total_duration_ms,
        definition={},
        user_id=current_user.id,
        version=1,
    )
    db.add(scenario)
    await db.flush()

    # Step 2: allocate /16 IP range
    allocation = None
    try:
        allocation = await IPManagementService.allocate_range(db, scenario.id)
        scenario.addressing_config = {
            "ip_range": allocation.cidr_range,
            "range_index": allocation.range_index,
            "auto_assign_enabled": True,
        }
    except ValueError:
        logger.warning("No IP ranges available for imported scenario %s", scenario.id)

    # Step 3: zones
    zones = _build_zones_from_template(template, allocation)

    # Step 4: devices (expand count, generate MAC, resolve fingerprint, enrich)
    devices: dict[str, dict[str, Any]] = {}
    device_index = 0
    for device_spec in template["devices"]:
        count = device_spec.get("count", 1)
        for _ in range(count):
            device_index += 1
            device_id = f"device_{device_index:03d}"

            name_pattern = device_spec.get("name_pattern", "{type}-{n:03d}")
            try:
                name = name_pattern.format(n=device_index, **device_spec)
            except (KeyError, IndexError):
                name = f"{device_spec.get('type', 'device')}-{device_index:03d}"

            device: dict[str, Any] = {
                "id": device_id,
                "name": name,
                "type": device_spec.get("type", "plc"),
                "protocols": list(device_spec.get("protocols", [])),
                "zoneId": device_spec.get("zone"),
                "vendor": device_spec.get("vendor"),
                "fingerprintModel": device_spec.get("fingerprint_model"),
                "network": {},
            }

            explicit_role = device_spec.get("architectural_role")
            if explicit_role:
                device["architecturalRole"] = explicit_role
            else:
                derived = default_role_for_device_type(device_spec.get("type"))
                if derived:
                    device["architecturalRole"] = derived

            vendor = device_spec.get("vendor")
            fingerprint_model = device_spec.get("fingerprint_model")
            full_fingerprint = None
            if vendor and fingerprint_model:
                full_fingerprint = get_fingerprint_by_vendor_model(vendor, fingerprint_model)
            if full_fingerprint:
                device["vendorFingerprint"] = full_fingerprint

            if device_spec.get("role"):
                device["role"] = device_spec.get("role")
            if device_spec.get("error_config"):
                device["errorConfig"] = device_spec["error_config"]
            if device_spec.get("cve_ids"):
                device["cveIds"] = list(device_spec["cve_ids"])

            fp_ouis = device.get("vendorFingerprint", {}).get("oui_prefixes") if full_fingerprint else None
            device["network"]["macAddress"] = generate_mac_address(
                vendor=vendor,
                device_type=device_spec.get("type"),
                oui_prefixes=fp_ouis,
            )

            enrich_device_serial_numbers(device, device_id, str(scenario.id))
            devices[device_id] = device

    # Step 4.5: enrich protocol identities with device names
    for device_id, device in devices.items():
        enrich_device_unique_identifiers(device, device_id, str(scenario.id))

    # Step 5: assign IPs from allocated range
    if zones:
        _auto_assign_ips(devices, zones, allocation)

    # Step 6: conduits (explicit or auto-generated from Purdue adjacency)
    template_conduits = template.get("conduits", [])
    if template_conduits:
        conduits: dict[str, dict[str, Any]] = {}
        for c in template_conduits:
            cid = c.get("id", f"conduit_{len(conduits) + 1:03d}")
            conduits[cid] = {
                "id": cid,
                "name": c.get("name", ""),
                "sourceZoneId": c.get("source_zone", ""),
                "targetZoneId": c.get("target_zone", ""),
                "direction": c.get("direction", "bidirectional"),
                "allowedProtocols": list(c.get("allowed_protocols", [])),
                "securityLevel": c.get("security_level", "standard"),
                "description": c.get("description"),
                "autoGenerated": False,
            }
    else:
        conduits = generate_default_conduits(zones)

    # Step 7: flows (template-driven matching, the standard path)
    flows: dict[str, dict[str, Any]] = {}
    devices_by_type: dict[str, list[str]] = {}
    devices_by_type_zone: dict[tuple[str, str], list[str]] = {}
    for device_id, device in devices.items():
        dtype = device.get("type", "unknown")
        dzone = device.get("zoneId", "")
        devices_by_type.setdefault(dtype, []).append(device_id)
        devices_by_type_zone.setdefault((dtype, dzone), []).append(device_id)

    flow_index = 0
    for flow_spec in template["flows"]:
        source_types = flow_spec.get("source_types", [])
        target_types = flow_spec.get("target_types", [])
        source_zones = flow_spec.get("source_zones", [])
        target_zones_ = flow_spec.get("target_zones", [])
        protocol = flow_spec.get("protocol")
        interval_ms = flow_spec.get("interval_ms", 1000)
        timing: dict[str, Any] = {"intervalMs": interval_ms}
        if flow_spec.get("jitter_ms"):
            timing["jitterMs"] = flow_spec["jitter_ms"]
        if flow_spec.get("jitter_type"):
            timing["jitterType"] = flow_spec["jitter_type"]

        for source_type in source_types:
            for target_type in target_types:
                if source_zones:
                    source_devices = []
                    for sz in source_zones:
                        source_devices.extend(devices_by_type_zone.get((source_type, sz), []))
                else:
                    source_devices = devices_by_type.get(source_type, [])

                if target_zones_:
                    target_devices = []
                    for tz in target_zones_:
                        target_devices.extend(devices_by_type_zone.get((target_type, tz), []))
                else:
                    target_devices = devices_by_type.get(target_type, [])

                if not source_devices or not target_devices:
                    continue

                n_flows = max(len(source_devices), len(target_devices))
                for i in range(n_flows):
                    source_id = source_devices[i % len(source_devices)]
                    target_id = target_devices[i % len(target_devices)]
                    if source_id == target_id:
                        continue
                    flow_index += 1
                    flow_id = f"flow_{flow_index:03d}"
                    flows[flow_id] = {
                        "id": flow_id,
                        "sourceDeviceId": source_id,
                        "targetDeviceId": target_id,
                        "protocol": protocol,
                        "timing": timing,
                        "config": {},
                    }

    # Step 8: phases — honor explicit, else derive from duration
    if portable.phases:
        phases = [
            {
                "name": p.name,
                "description": p.description or "",
                "start_time": p.start_time_ms,
                "duration": p.duration_ms,
            }
            for p in portable.phases
        ]
    else:
        phases = get_default_phases(
            total_duration_ms=portable.total_duration_ms,
            preset=None,
            vertical=vertical,
        )

    definition: dict[str, Any] = {
        "devices": devices,
        "flows": flows,
        "zones": zones,
        "conduits": conduits,
        "phases": phases,
    }

    if template.get("external_comms"):
        definition["external_comms"] = template["external_comms"]
    if template.get("cell_isolation"):
        definition["cell_isolation"] = template["cell_isolation"]
    if portable.modes:
        if portable.modes.clean_demo_mode:
            definition["clean_demo_mode"] = True
        if not portable.modes.broadcast_traffic_enabled:
            definition["broadcast_traffic_enabled"] = False

    # Step 9: protocol repair (vendor/fingerprint mismatch correction)
    definition = auto_repair_protocols(definition)
    definition = repair_flow_protocols(definition)

    # Step 9b: orphan-device coverage. The realism rules require every
    # device participates in at least one flow (Cyber Vision can't
    # fingerprint a silent device). This synthesises a coverage flow
    # for any orphan — typically an SNMP monitoring poll from the
    # plant NMS. Same behaviour the built-in template path uses.
    flow_count_before = len(definition.get("flows", {}))
    definition = await ensure_device_flow_coverage(definition)
    flow_count_after = len(definition.get("flows", {}))
    if flow_count_after > flow_count_before:
        logger.info(
            "portable import: synthesised %d orphan-coverage flow(s)",
            flow_count_after - flow_count_before,
        )

    # Step 10: site naming pipeline (deterministic or LLM-driven)
    try:
        await apply_site_naming_pipeline(
            db=db,
            definition=definition,
            scenario_id=str(scenario.id),
            vertical=vertical,
            template_name="portable_import",
            template_description=portable.description or "",
            archetype_id=None,
            use_llm=use_ai_naming,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Site naming failed for portable import %s: %s — keeping author names",
            scenario.id,
            exc,
        )

    scenario.definition = definition
    await db.commit()
    await db.refresh(scenario)
    return scenario


def summarize_expansion(portable: PortableScenario) -> dict[str, Any]:
    """Cheap preview of what the importer will produce.

    Used by the dry-run /validate/portable endpoint to surface counts before
    the author commits. Does not allocate IPs or hit the DB.
    """
    total_devices = sum(d.count for d in portable.devices)
    cross_zone_flows = 0
    intra_zone_flows = 0
    for f in portable.flows:
        if f.source_zones and f.target_zones and set(f.source_zones) != set(f.target_zones):
            cross_zone_flows += 1
        else:
            intra_zone_flows += 1
    return {
        "zone_count": len(portable.zones),
        "device_spec_count": len(portable.devices),
        "instantiated_device_count": total_devices,
        "flow_spec_count": len(portable.flows),
        "intra_zone_flows": intra_zone_flows,
        "cross_zone_flows": cross_zone_flows,
        "conduit_count": len(portable.conduits) if portable.conduits else cross_zone_flows,
        "auto_generated_conduits": not bool(portable.conduits),
    }
