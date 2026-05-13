# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""DB-free scenario-template definition builder.

Mirrors the production path in `routes/templates.py:create_scenario_from_template`
without the DB writes. Used by the audit harness to evaluate every
template against the realism rules in `packetarch-scenario-authoring`
without polluting the database.

Limitations vs production builder:
  - No IP allocation (devices get synthetic IPs from a deterministic
    /16 range so subnet checks still produce sensible results).
  - No AI naming (uses the template's name/name_pattern only).
  - No CVE resolution (not relevant to scenario-authoring audit).
  - No serial-number enrichment (uniqueness from device_id + dummy
    scenario_id; collisions across templates are fine for audit).
  - No DB cloud_service lookup (uses BUILTIN_CLOUD_SERVICES so the
    cloud_service_links list is still populated).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


# Reuse a single dummy scenario id for all audited templates so serial
# numbers are deterministic and identical across runs. The audit doesn't
# create real scenarios, so collision risk is zero.
_AUDIT_SCENARIO_ID = "audit-template-00000000-0000-0000-0000-000000000000"

# Synthetic /16 base for the audit. Mirrors the production "10.{n}.0.0/16"
# allocation pattern; we just hardcode n=99 so audited definitions have
# realistic-looking IPs without touching IPManagementService.
_AUDIT_RANGE_INDEX = 99
_AUDIT_CIDR = f"10.{_AUDIT_RANGE_INDEX}.0.0/16"


class _SyntheticAllocation:
    """Stand-in for IPRangeAllocation that satisfies the builder helpers."""

    def __init__(self) -> None:
        self.cidr_range = _AUDIT_CIDR
        self.range_index = _AUDIT_RANGE_INDEX


def populate_definition_from_template(
    vertical: str,
    template_name: str,
) -> dict[str, Any] | None:
    """Build a fully-populated scenario.definition dict for an audit run.

    Returns None if the template is not found.
    """
    from app.api.routes.templates import (
        _build_zones_from_template,
        _auto_assign_ips,
    )
    from app.scenario_templates import get_template, VERTICAL_TEMPLATES
    from app.services.conduit_service import generate_default_conduits
    from app.services.device_templates._fingerprints import (
        get_fingerprint_by_vendor_model,
        get_fingerprint_from_template,
    )
    from app.protocol_engines.vendor_oui import generate_mac_address
    from app.services.device_identity_enricher import (
        enrich_device_serial_numbers,
        enrich_device_unique_identifiers,
    )
    from app.scenario_templates.phases import get_default_phases

    template = get_template(vertical, template_name)
    if not template:
        return None

    # Archetype-driven path: if this legacy template is mapped to an
    # archetype (Phase 5 of the architecture rollout), materialize via
    # the generator instead of the freeform device/flow lists.
    from app.services.architecture.legacy_template_archetypes import (
        get_archetype_config,
    )
    arch_cfg = get_archetype_config(vertical, template_name)
    if arch_cfg is not None:
        from app.services.architecture.scenario_generator import (
            generate_from_archetype,
        )
        from app.services.architecture.site_naming_pipeline import (
            apply_site_naming_pipeline_sync,
        )
        defn = generate_from_archetype(
            arch_cfg.archetype_id,
            vendor_profile=arch_cfg.vendor_profile,
            scale=arch_cfg.scale,
            overrides=arch_cfg.overrides,
        )
        # Preserve template-level metadata that some downstream consumers
        # expect to find on the definition.
        if template.get("name"):
            defn.setdefault("_template_meta", {})["name"] = template["name"]
        if template.get("description"):
            defn.setdefault("_template_meta", {})["description"] = (
                template["description"]
            )
        # Apply deterministic site naming so the audit sees the same
        # final, site-coherent names that the create-from-template
        # route produces (minus the optional LLM step).
        audit_scenario_id = (
            f"audit-{arch_cfg.archetype_id}-"
            f"{arch_cfg.vendor_profile.value}-{arch_cfg.scale.value}-"
            f"{vertical}-{template_name}"
        )
        apply_site_naming_pipeline_sync(
            definition=defn,
            scenario_id=audit_scenario_id,
            vertical=vertical,
            template_name=template_name,
            template_description=template.get("description", ""),
        )
        return defn

    allocation = _SyntheticAllocation()

    # ---- Zones ----------------------------------------------------------
    zones = _build_zones_from_template(template, allocation)

    # ---- Devices --------------------------------------------------------
    devices: dict[str, dict[str, Any]] = {}
    device_index = 0
    for device_spec in template.get("devices", []):
        count = device_spec.get("count", 1)
        for i in range(count):
            device_index += 1
            device_id = f"device_{device_index:03d}"

            if device_spec.get("name"):
                name = device_spec.get("name")
            else:
                pattern = device_spec.get("name_pattern", "{type}-{n:03d}")
                try:
                    name = pattern.format(n=device_index, **device_spec)
                except KeyError:
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

            from app.services.architecture.role_catalog import (
                default_role_for_device_type,
            )
            explicit_role = (
                device_spec.get("architectural_role")
                or device_spec.get("architecturalRole")
            )
            if explicit_role:
                device["architecturalRole"] = explicit_role
            else:
                default_role = default_role_for_device_type(device_spec.get("type"))
                if default_role:
                    device["architecturalRole"] = default_role

            vendor = device_spec.get("vendor")
            fingerprint_model = device_spec.get("fingerprint_model")
            fingerprint_id = device_spec.get("fingerprint_id")
            full_fingerprint = None
            if fingerprint_id:
                full_fingerprint = get_fingerprint_from_template(fingerprint_id)
                if full_fingerprint and not fingerprint_model:
                    device["fingerprintModel"] = full_fingerprint.get("model")
            elif vendor and fingerprint_model:
                full_fingerprint = get_fingerprint_by_vendor_model(
                    vendor, fingerprint_model
                )
            if full_fingerprint:
                device["vendorFingerprint"] = full_fingerprint

            if device_spec.get("role"):
                device["role"] = device_spec.get("role")
            if device_spec.get("error_config"):
                device["errorConfig"] = device_spec.get("error_config")
            if device_spec.get("cve_ids"):
                device["cveIds"] = list(device_spec.get("cve_ids"))

            mac_override = device_spec.get("mac_address")
            if mac_override:
                device["network"]["macAddress"] = mac_override
            else:
                fp_ouis = (
                    (device.get("vendorFingerprint") or {}).get("oui_prefixes")
                )
                device["network"]["macAddress"] = generate_mac_address(
                    vendor=device_spec.get("vendor"),
                    device_type=device_spec.get("type"),
                    oui_prefixes=fp_ouis if fp_ouis else None,
                )

            if device_spec.get("ip_host_offset") is not None:
                device["_ip_host_offset"] = device_spec["ip_host_offset"]

            enrich_device_serial_numbers(device, device_id, _AUDIT_SCENARIO_ID)
            devices[device_id] = device

    # ---- Identity enrichment (skip AI naming) ---------------------------
    for device_id, device in devices.items():
        enrich_device_unique_identifiers(device, device_id, _AUDIT_SCENARIO_ID)

    # ---- IP assignment --------------------------------------------------
    _auto_assign_ips(devices, zones, allocation)

    # ---- Conduits -------------------------------------------------------
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

    # ---- Flows ----------------------------------------------------------
    flows: dict[str, dict[str, Any]] = {}
    flow_index = 0

    devices_by_type: dict[str, list[str]] = {}
    devices_by_type_zone: dict[tuple[str, str], list[str]] = {}
    for did, dev in devices.items():
        dtype = dev.get("type", "unknown")
        dzone = dev.get("zoneId", "") or ""
        devices_by_type.setdefault(dtype, []).append(did)
        devices_by_type_zone.setdefault((dtype, dzone), []).append(did)

    for flow_spec in template.get("flows", []):
        source_types = flow_spec.get("source_types", [])
        target_types = flow_spec.get("target_types", [])
        source_zones = flow_spec.get("source_zones", [])
        target_zones = flow_spec.get("target_zones", [])
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
                    sources = []
                    for sz in source_zones:
                        sources.extend(
                            devices_by_type_zone.get((source_type, sz), [])
                        )
                else:
                    sources = devices_by_type.get(source_type, [])

                if target_zones:
                    targets = []
                    for tz in target_zones:
                        targets.extend(
                            devices_by_type_zone.get((target_type, tz), [])
                        )
                else:
                    targets = devices_by_type.get(target_type, [])

                if not sources or not targets:
                    continue

                n = max(len(sources), len(targets))
                for i in range(n):
                    sid = sources[i % len(sources)]
                    tid = targets[i % len(targets)]
                    if sid == tid:
                        continue
                    flow_index += 1
                    fid = f"flow_{flow_index:03d}"
                    flow_obj: dict[str, Any] = {
                        "id": fid,
                        "sourceDeviceId": sid,
                        "targetDeviceId": tid,
                        "protocol": protocol,
                        "timing": timing,
                        "config": {},
                    }
                    if flow_spec.get("auto_repair_skip"):
                        flow_obj["auto_repair_skip"] = True
                    flows[fid] = flow_obj

    # ---- Cloud-service links (sync, BUILTIN catalog) --------------------
    cloud_service_links = _build_cloud_links_sync(template, devices)

    # ---- Phases ---------------------------------------------------------
    total_duration_ms = template.get("total_duration_ms", 300000)
    phases = get_default_phases(
        total_duration_ms=total_duration_ms,
        preset=None,
        vertical=vertical,
    )

    # ---- Definition assembly --------------------------------------------
    definition: dict[str, Any] = {
        "devices": devices,
        "flows": flows,
        "zones": zones,
        "conduits": conduits,
        "phases": phases,
    }
    if cloud_service_links:
        definition["cloud_service_links"] = cloud_service_links
    if template.get("external_comms"):
        definition["external_comms"] = template["external_comms"]
    if template.get("cell_isolation"):
        definition["cell_isolation"] = template["cell_isolation"]

    # Apply the same auto-repair passes the production create-scenario
    # route runs (routes/templates.py:create_scenario_from_template).
    # Without these, the audit sees pre-repair protocol mismatches that
    # never reach a real scenario.
    from app.services.scenario_enrichment import (
        auto_repair_protocols,
        repair_flow_protocols,
    )
    definition = auto_repair_protocols(definition)
    definition = repair_flow_protocols(definition)

    # Apply deterministic site naming so the audit harness validates
    # the final, renamed scenario (no LLM in the audit path).
    from app.services.architecture.site_naming_pipeline import (
        apply_site_naming_pipeline_sync,
    )
    audit_scenario_id = f"audit-legacy-{vertical}-{template_name}"
    apply_site_naming_pipeline_sync(
        definition=definition,
        scenario_id=audit_scenario_id,
        vertical=vertical,
        template_name=template_name,
        template_description=template.get("description", ""),
    )

    return definition


def _build_cloud_links_sync(
    template: dict[str, Any],
    devices: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Mirror _create_cloud_service_links_from_template without the DB
    lookup. Uses BUILTIN_CLOUD_SERVICES from cloud_service_data."""
    from app.services.cloud_service_data import (
        get_cloud_service_by_provider_region,
    )

    cloud_links: list[dict[str, Any]] = []
    cloud_services_config = template.get("cloud_services") or []
    if not cloud_services_config:
        return cloud_links

    link_index = 0
    for cloud_config in cloud_services_config:
        provider = cloud_config.get("provider")
        region = cloud_config.get("region")
        device_types = cloud_config.get("device_types") or []
        heartbeat_interval_ms = cloud_config.get("heartbeat_interval_ms", 30000)
        if not provider:
            continue
        endpoint = get_cloud_service_by_provider_region(provider, region)
        if endpoint is None:
            continue
        for did, dev in devices.items():
            dtype = (dev.get("type") or "").lower()
            if dtype not in [t.lower() for t in device_types]:
                continue
            link_index += 1
            cloud_links.append(
                {
                    "id": f"csl_{link_index:03d}",
                    "device_id": did,
                    "cloud_service_id": "audit-synthetic",
                    "heartbeat_interval_ms": heartbeat_interval_ms,
                    "enabled": True,
                    "cloud_service": {
                        "name": endpoint.get("name"),
                        "provider": endpoint.get("provider"),
                        "primary_ip": endpoint.get("primary_ip"),
                        "port": endpoint.get("port"),
                        "hostname": endpoint.get("hostname"),
                        "tls_enabled": endpoint.get("tls_enabled"),
                    },
                }
            )
    return cloud_links
