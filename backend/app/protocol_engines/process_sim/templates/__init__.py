"""Process simulation template registry.

Maps industry verticals to their process model + fault builders.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from ..faults import FaultScenario
from ..process_model import ProcessModel

logger = logging.getLogger(__name__)

# Registry: vertical name -> (model_builder, fault_builder)
_REGISTRY: dict[str, tuple[
    Callable[[], ProcessModel],
    Callable[[], list[FaultScenario]],
]] = {}


def _register() -> None:
    """Lazy registration of built-in templates."""
    if _REGISTRY:
        return

    from . import building_automation, manufacturing, oil_gas, water

    _REGISTRY["manufacturing"] = (manufacturing.build_model, manufacturing.build_faults)
    _REGISTRY["water_wastewater"] = (water.build_model, water.build_faults)
    _REGISTRY["water"] = (water.build_model, water.build_faults)
    _REGISTRY["building_automation"] = (
        building_automation.build_model,
        building_automation.build_faults,
    )
    _REGISTRY["oil_gas"] = (oil_gas.build_model, oil_gas.build_faults)


def get_available_verticals() -> list[str]:
    """Return list of verticals with process simulation templates."""
    _register()
    return list(_REGISTRY.keys())


def build_from_vertical(
    vertical: str,
) -> tuple[list[ProcessModel], list[FaultScenario]]:
    """Build process model(s) and faults for the given vertical.

    Returns:
        Tuple of (models, faults). If no template exists for the vertical,
        returns empty lists.
    """
    _register()
    entry = _REGISTRY.get(vertical)
    if entry is None:
        logger.warning("No process simulation template for vertical '%s'", vertical)
        return [], []

    model_builder, fault_builder = entry
    model = model_builder()
    faults = fault_builder()
    logger.info(
        "Built process template '%s': %d variables, %d faults",
        vertical,
        len(model.variables),
        len(faults),
    )
    return [model], faults
