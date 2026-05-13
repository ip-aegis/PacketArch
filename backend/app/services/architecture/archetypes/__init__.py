# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Per-vertical archetype registry.

Phase 2 ships the framework + two representative archetypes:

  - manufacturing_discrete_cell  (DISCRETE_CELL pattern)
  - energy_substation            (DISTRIBUTED_SUBSTATION pattern)

Subsequent phases extend coverage to all 9 verticals. Adding a new
archetype is a one-file change: write `vertical_pattern.py` exposing
an `ARCHETYPE` constant and add it to `_REGISTERED` below.
"""

from __future__ import annotations

from app.services.architecture.archetypes._base import (
    Archetype,
    ArchitecturePattern,
    ConduitTemplate,
    RoleSlot,
    ScaleTier,
    VendorProfile,
    ZoneDef,
)
from app.services.architecture.archetypes.building_automation_bas import (
    ARCHETYPE as _BAS_SUPERVISOR,
)
from app.services.architecture.archetypes.data_center_infra_dcim import (
    ARCHETYPE as _DCIM,
)
from app.services.architecture.archetypes.distribution_warehouse import (
    ARCHETYPE as _DISTRIBUTION_WAREHOUSE,
)
from app.services.architecture.archetypes.energy_generation import (
    ARCHETYPE as _ENERGY_GENERATION,
)
from app.services.architecture.archetypes.energy_substation import (
    ARCHETYPE as _ENERGY_SUBSTATION,
)
from app.services.architecture.archetypes.manufacturing_battery_cell import (
    ARCHETYPE as _MANUFACTURING_BATTERY_CELL,
)
from app.services.architecture.archetypes.manufacturing_discrete_cell import (
    ARCHETYPE as _MANUFACTURING_DISCRETE_CELL,
)
from app.services.architecture.archetypes.manufacturing_pharma_bioreactor import (
    ARCHETYPE as _MANUFACTURING_PHARMA_BIOREACTOR,
)
from app.services.architecture.archetypes.manufacturing_process_dcs import (
    ARCHETYPE as _MANUFACTURING_PROCESS_DCS,
)
from app.services.architecture.archetypes.manufacturing_semiconductor_fab import (
    ARCHETYPE as _MANUFACTURING_SEMICONDUCTOR_FAB,
)
from app.services.architecture.archetypes.oil_gas_refinery import (
    ARCHETYPE as _OIL_GAS_REFINERY,
)
from app.services.architecture.archetypes.transportation_atms import (
    ARCHETYPE as _TRANSPORTATION_ATMS,
)
from app.services.architecture.archetypes.transportation_toll_plaza import (
    ARCHETYPE as _TRANSPORTATION_TOLL_PLAZA,
)
from app.services.architecture.archetypes.transportation_tunnel import (
    ARCHETYPE as _TRANSPORTATION_TUNNEL,
)
from app.services.architecture.archetypes.water_utility_master_remote import (
    ARCHETYPE as _WATER_UTILITY_MASTER_REMOTE,
)


_REGISTERED: tuple[Archetype, ...] = (
    _MANUFACTURING_DISCRETE_CELL,
    _MANUFACTURING_PROCESS_DCS,
    _MANUFACTURING_SEMICONDUCTOR_FAB,
    _MANUFACTURING_BATTERY_CELL,
    _MANUFACTURING_PHARMA_BIOREACTOR,
    _ENERGY_SUBSTATION,
    _ENERGY_GENERATION,
    _OIL_GAS_REFINERY,
    _WATER_UTILITY_MASTER_REMOTE,
    _BAS_SUPERVISOR,
    _DCIM,
    _TRANSPORTATION_ATMS,
    _TRANSPORTATION_TOLL_PLAZA,
    _TRANSPORTATION_TUNNEL,
    _DISTRIBUTION_WAREHOUSE,
)


_BY_ID: dict[str, Archetype] = {a.id: a for a in _REGISTERED}

if len(_BY_ID) != len(_REGISTERED):
    seen: set[str] = set()
    dupes: list[str] = []
    for a in _REGISTERED:
        if a.id in seen:
            dupes.append(a.id)
        seen.add(a.id)
    raise RuntimeError(f"Duplicate archetype IDs: {dupes}")


def get_archetype(archetype_id: str) -> Archetype | None:
    return _BY_ID.get(archetype_id)


def list_archetypes() -> tuple[Archetype, ...]:
    return _REGISTERED


def list_archetypes_for_vertical(vertical: str) -> tuple[Archetype, ...]:
    return tuple(a for a in _REGISTERED if a.vertical == vertical)


__all__ = [
    "Archetype",
    "ArchitecturePattern",
    "ConduitTemplate",
    "RoleSlot",
    "ScaleTier",
    "VendorProfile",
    "ZoneDef",
    "get_archetype",
    "list_archetypes",
    "list_archetypes_for_vertical",
]
