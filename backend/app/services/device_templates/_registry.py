"""Device template registry.

Maintains the global DEVICE_TEMPLATES dictionary and handles
registration of all vendor template modules.
"""

from app.services.device_templates._types import DeviceTemplate

DEVICE_TEMPLATES: dict[str, DeviceTemplate] = {}


def _register_template(template: DeviceTemplate) -> None:
    """Register a device template in the library."""
    DEVICE_TEMPLATES[template.id] = template


def _register_all() -> None:
    """Import and register all vendor templates. Called once at module load."""
    from app.services.device_templates.vendors import (
        abb,
        building_automation,
        cisco,
        emerson,
        fieldbus_networking,
        ge,
        hms,
        honeywell,
        it_ot_boundary,
        japanese_plc,
        process_instruments,
        robotics_logistics,
        rockwell,
        schneider,
        sel,
        siemens,
        transportation,
        yokogawa,
    )

    all_modules = [
        siemens, rockwell, schneider, honeywell, abb, yokogawa,
        cisco, emerson, ge, sel, hms,
        building_automation, transportation, process_instruments,
        robotics_logistics, fieldbus_networking, it_ot_boundary,
        japanese_plc,
    ]
    for mod in all_modules:
        for template in mod.TEMPLATES:
            _register_template(template)

    _count = len(DEVICE_TEMPLATES)
    if _count < 295:  # 301 _register calls, 6 pre-existing duplicate IDs = 295 unique
        raise RuntimeError(f"Expected at least 295 templates, got {_count}")


_register_all()
