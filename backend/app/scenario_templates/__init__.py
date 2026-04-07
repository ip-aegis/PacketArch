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


def list_templates() -> list[dict[str, Any]]:
    """List all available templates.

    Returns:
        List of template summaries
    """
    templates = []
    for vertical, vertical_templates in VERTICAL_TEMPLATES.items():
        for template_name, template_data in vertical_templates.items():
            templates.append({
                "vertical": vertical,
                "name": template_name,
                "display_name": template_data.get("name", template_name),
                "description": template_data.get("description", ""),
                "device_count": sum(d.get("count", 1) for d in template_data.get("devices", [])),
                "protocols": list(set(f.get("protocol") for f in template_data.get("flows", []))),
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
