# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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
        beckwith,
        building_automation,
        carlo_gavazzi,
        cisco,
        danfoss,
        elvaco,
        emerson,
        fieldbus_networking,
        ge,
        hms,
        honeywell,
        it_ot_boundary,
        janitza,
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
        cisco, emerson, ge, sel, hms, beckwith,
        building_automation, transportation, process_instruments,
        robotics_logistics, fieldbus_networking, it_ot_boundary,
        japanese_plc, carlo_gavazzi, janitza, elvaco, danfoss,
    ]
    for mod in all_modules:
        for template in mod.TEMPLATES:
            _register_template(template)

    _count = len(DEVICE_TEMPLATES)
    if _count < 332:  # 284 + 5 EU energy-metering templates (Carlo Gavazzi x2, Janitza, Elvaco, Danfoss)
        raise RuntimeError(f"Expected at least 284 templates, got {_count}")


_register_all()
