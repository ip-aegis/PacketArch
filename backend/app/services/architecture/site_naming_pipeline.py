# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Site-identity + rename pipeline orchestrator.

Single entry point used by both the create-from-template route and the
admin regenerate-names endpoint. Picks a SiteIdentity (LLM or
deterministic), applies it to every device, then re-runs the per-device
serial + SNMP sys_name enrichments so identity downstream matches the
new names.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.architecture.site_identity import (
    SiteIdentity,
    deterministic_site_identity,
)
from app.services.architecture.site_naming import apply_site_identity


logger = logging.getLogger(__name__)


async def _collect_taken_site_codes(
    db: AsyncSession,
    exclude_scenario_id: str | None = None,
) -> list[str]:
    """Return site_codes already in use by other scenarios on this install."""
    from app.models.scenario import Scenario

    result = await db.execute(select(Scenario))
    taken: list[str] = []
    for sc in result.scalars().all():
        if exclude_scenario_id and str(sc.id) == str(exclude_scenario_id):
            continue
        defn = sc.definition or {}
        si = defn.get("site_identity") or {}
        code = si.get("site_code")
        if code:
            taken.append(code)
    return taken


def _gather_inventory(definition: dict[str, Any]) -> tuple[list[str], dict[str, int]]:
    devs = definition.get("devices") or {}
    if isinstance(devs, dict):
        devs_iter = list(devs.values())
    else:
        devs_iter = list(devs)
    zones = definition.get("zones") or {}
    if isinstance(zones, dict):
        zone_ids = list(zones.keys())
    else:
        zone_ids = [z.get("id") for z in zones if isinstance(z, dict) and z.get("id")]
    role_counts: Counter[str] = Counter()
    for d in devs_iter:
        role = (
            d.get("architectural_role")
            or d.get("role_id")
            or d.get("_role")
            or d.get("role")
        )
        if role:
            role_counts[role] += 1
    return zone_ids, dict(role_counts)


def _re_enrich_devices(
    definition: dict[str, Any],
    scenario_id: str,
) -> None:
    """Re-run serial + unique-identifier enrichment against the real
    scenario_id and the (already renamed) device names so SNMP sys_name,
    Modbus product_name, EtherNet/IP product_name etc. all line up with
    the new site-coherent labels."""
    from app.services.device_identity_enricher import (
        enrich_device_serial_numbers,
        enrich_device_unique_identifiers,
    )

    devs = definition.get("devices") or {}
    if isinstance(devs, list):
        items = [(d.get("id"), d) for d in devs if d.get("id")]
    else:
        items = list(devs.items())

    for did, dev in items:
        try:
            enrich_device_serial_numbers(dev, did, scenario_id)
            enrich_device_unique_identifiers(dev, did, scenario_id)
        except Exception:  # noqa: BLE001
            logger.exception("Re-enrichment failed for device %s", did)


async def _resolve_identity_via_llm(
    *,
    db: AsyncSession,
    vertical: str,
    template_name: str,
    template_description: str,
    archetype_id: str | None,
    zones: dict[str, dict[str, Any]],
    role_inventory: dict[str, int],
    avoid_site_codes: list[str],
) -> SiteIdentity | None:
    """Best-effort LLM identity. Returns None on any failure so the
    caller can drop back to the deterministic identity."""
    try:
        from app.core.features import get_features
        from app.mcp_server.ai_providers import AIProviderFactory
        from app.ai_services.site_identity_generator import generate_site_identity

        if not get_features().ai_enabled:
            return None

        provider = await AIProviderFactory.create(db)
        identity = await generate_site_identity(
            ai_provider=provider,
            vertical=vertical,
            template_name=template_name,
            template_description=template_description,
            archetype_id=archetype_id,
            zones=zones,
            role_inventory=role_inventory,
            avoid_site_codes=avoid_site_codes,
        )
        return identity
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "LLM site identity generation failed: %s — using deterministic fallback",
            e,
        )
        return None


async def apply_site_naming_pipeline(
    *,
    db: AsyncSession,
    definition: dict[str, Any],
    scenario_id: str,
    vertical: str,
    template_name: str,
    template_description: str,
    archetype_id: str | None,
    use_llm: bool = True,
    exclude_scenario_id: str | None = None,
) -> SiteIdentity:
    """Site-identity + rename + re-enrichment pipeline.

    Mutates `definition` in place. Returns the SiteIdentity applied.

    Args:
        db: DB session (used to look up taken site codes and AI settings)
        definition: Scenario definition dict (zones/devices already
            populated, repair_flow_protocols already run)
        scenario_id: Real scenario UUID — used for deterministic serial
            generation so identifiers are stable AND unique per scenario
        vertical, template_name, template_description, archetype_id:
            metadata to drive LLM identity quality
        use_llm: When False, skip the LLM entirely and use only the
            deterministic identity. Defaults True.
        exclude_scenario_id: when re-running on an existing scenario,
            pass the scenario id so we don't treat its own site_code as
            "taken".
    """
    zone_ids, role_inventory = _gather_inventory(definition)
    avoid = await _collect_taken_site_codes(
        db,
        exclude_scenario_id=exclude_scenario_id,
    )

    identity: SiteIdentity | None = None
    if use_llm:
        identity = await _resolve_identity_via_llm(
            db=db,
            vertical=vertical,
            template_name=template_name,
            template_description=template_description,
            archetype_id=archetype_id,
            zones=definition.get("zones") or {},
            role_inventory=role_inventory,
            avoid_site_codes=avoid,
        )

    if identity is None:
        # Deterministic fallback. Use the real scenario_id so each
        # scenario picks a distinct (but stable) entry from the bank.
        identity = deterministic_site_identity(
            scenario_id=scenario_id,
            vertical=vertical,
            zone_ids=zone_ids,
            role_ids=list(role_inventory.keys()),
            template_name=template_name,
        )
        # If the deterministic-pick lands on a code already used by a
        # sibling scenario, rotate through the SAME template sub-bank
        # (don't borrow a pharma city for a discrete plant).
        if identity.site_code in set(avoid):
            from app.services.architecture.site_identity import (
                filter_bank_for_template,
            )
            sub_bank = filter_bank_for_template(vertical, template_name)
            taken = set(avoid)
            chosen = next(
                (entry for entry in sub_bank if entry["site_code"] not in taken),
                None,
            )
            if chosen is not None:
                identity.site_code = chosen["site_code"]
                identity.plant_name = chosen["plant_name"]
                identity.location = chosen["location"]
                identity.operator = chosen["operator"]
                identity.industry_context = chosen["context"]
                identity.domain_suffix = chosen.get("domain")
            else:
                # Sub-bank exhausted — suffix the original pick so we
                # stay in the right industrial context (better:
                # AUS01-02 for a 2nd Austin plant) than:
                # borrow RR-P1 for a discrete plant.
                base = identity.site_code
                seq = 2
                while f"{base}-{seq:02d}" in taken:
                    seq += 1
                identity.site_code = f"{base}-{seq:02d}"

    apply_site_identity(definition=definition, identity=identity)
    _re_enrich_devices(definition, scenario_id)
    logger.info(
        "Applied site identity %s (source=%s) — %d devices renamed",
        identity.site_code,
        identity.source,
        len(definition.get("devices") or {}),
    )
    return identity


def apply_site_naming_pipeline_sync(
    *,
    definition: dict[str, Any],
    scenario_id: str,
    vertical: str,
    template_name: str,
    template_description: str,
    avoid_site_codes: list[str] | None = None,
) -> SiteIdentity:
    """Sync, no-LLM, no-DB variant for the audit harness path.

    Always uses the deterministic identity. Mutates definition in place.
    """
    zone_ids, role_inventory = _gather_inventory(definition)
    identity = deterministic_site_identity(
        scenario_id=scenario_id,
        vertical=vertical,
        zone_ids=zone_ids,
        role_ids=list(role_inventory.keys()),
        template_name=template_name,
    )
    if avoid_site_codes and identity.site_code in set(avoid_site_codes):
        identity.site_code = f"{identity.site_code}-{len(avoid_site_codes) + 1:02d}"

    apply_site_identity(definition=definition, identity=identity)
    _re_enrich_devices(definition, scenario_id)
    return identity
