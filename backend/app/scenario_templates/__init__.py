# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Scenario templates for different industry verticals."""

from typing import Any

from .manufacturing import MANUFACTURING_TEMPLATES
from .water import WATER_TEMPLATES
from .energy import ENERGY_TEMPLATES
from .oil_gas import OIL_GAS_TEMPLATES
from .transportation import TRANSPORTATION_TEMPLATES
from .building_automation import BUILDING_AUTOMATION_TEMPLATES
from .distribution_logistics import DISTRIBUTION_LOGISTICS_TEMPLATES
from .testing import TESTING_TEMPLATES
from .phases import PHASE_TEMPLATES, get_default_phases


# Aggregate all vertical templates
VERTICAL_TEMPLATES: dict[str, dict[str, Any]] = {
    "manufacturing": MANUFACTURING_TEMPLATES,
    "water_wastewater": WATER_TEMPLATES,
    "energy_power": ENERGY_TEMPLATES,
    "oil_gas": OIL_GAS_TEMPLATES,
    "transportation": TRANSPORTATION_TEMPLATES,
    "building_automation": BUILDING_AUTOMATION_TEMPLATES,
    "distribution_logistics": DISTRIBUTION_LOGISTICS_TEMPLATES,
    "testing": TESTING_TEMPLATES,
}


def get_template(vertical: str, template_name: str = "default") -> dict[str, Any] | None:
    """Get a specific template by vertical and name.

    Args:
        vertical: Industry vertical
        template_name: Template name within the vertical

    Returns:
        Template definition or None if not found
    """
    vertical_templates = VERTICAL_TEMPLATES.get(vertical, {})
    return vertical_templates.get(template_name)


_ARCHETYPE_SUMMARY_CACHE: dict[tuple[str, str], tuple[int, list[str]]] = {}


def _summarize_archetype_template(
    vertical: str, template_name: str
) -> tuple[int, list[str]] | None:
    """Materialize an archetype-backed template once to count devices/protocols.

    Returns (device_count, protocols) or None if the template is not
    archetype-backed (or generation fails). Cached after first call so the
    template list endpoint stays cheap.
    """
    key = (vertical, template_name)
    if key in _ARCHETYPE_SUMMARY_CACHE:
        return _ARCHETYPE_SUMMARY_CACHE[key]

    try:
        from app.services.architecture.legacy_template_archetypes import (
            get_archetype_config,
        )
        from app.services.architecture.scenario_generator import (
            generate_from_archetype,
        )
    except Exception:
        return None

    cfg = get_archetype_config(vertical, template_name)
    if cfg is None:
        return None

    try:
        defn = generate_from_archetype(
            cfg.archetype_id,
            vendor_profile=cfg.vendor_profile,
            scale=cfg.scale,
            overrides=cfg.overrides,
        )
    except Exception:
        return None

    devices = defn.get("devices") or {}
    flows = defn.get("flows") or {}
    if isinstance(devices, dict):
        device_count = len(devices)
    else:
        device_count = len(list(devices))
    protocols = sorted(
        {
            (f.get("protocol") if isinstance(f, dict) else None)
            for f in (flows.values() if isinstance(flows, dict) else flows)
            if (f.get("protocol") if isinstance(f, dict) else None)
        }
    )
    summary = (device_count, list(protocols))
    _ARCHETYPE_SUMMARY_CACHE[key] = summary
    return summary


def list_templates() -> list[dict[str, Any]]:
    """List all available templates.

    Returns:
        List of template summaries
    """
    templates = []
    for vertical, vertical_templates in VERTICAL_TEMPLATES.items():
        for template_name, template_data in vertical_templates.items():
            static_devices = template_data.get("devices", []) or []
            static_flows = template_data.get("flows", []) or []
            device_count = sum(d.get("count", 1) for d in static_devices)
            protocols = sorted(
                {f.get("protocol") for f in static_flows if f.get("protocol")}
            )

            # Archetype-backed templates carry empty devices/flows in their
            # static dict — materialize once so the card UI shows real
            # device counts and protocol badges.
            if not static_devices or not static_flows:
                summary = _summarize_archetype_template(vertical, template_name)
                if summary is not None:
                    arch_count, arch_protocols = summary
                    if not static_devices:
                        device_count = arch_count
                    if not static_flows:
                        protocols = arch_protocols

            templates.append({
                "vertical": vertical,
                "name": template_name,
                "display_name": template_data.get("name", template_name),
                "description": template_data.get("description", ""),
                "device_count": device_count,
                "protocols": list(protocols),
            })
    return templates


def list_verticals() -> list[dict[str, Any]]:
    """List all available verticals.

    Returns:
        List of vertical summaries
    """
    verticals = []
    for vertical, templates in VERTICAL_TEMPLATES.items():
        verticals.append({
            "id": vertical,
            "name": vertical.replace("_", " ").title(),
            "template_count": len(templates),
            "templates": list(templates.keys()),
        })
    return verticals


__all__ = [
    "VERTICAL_TEMPLATES",
    "PHASE_TEMPLATES",
    "get_template",
    "list_templates",
    "list_verticals",
    "get_default_phases",
]
