# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Communication matrix registry.

Aggregates per-vertical entry sets + cross-vertical SHARED entries.
"""

from __future__ import annotations

from app.services.architecture.comm_matrix._base import (
    SHARED_VERTICAL,
    CommEntry,
    find_entries,
    has_entry,
    resolve_protocol,
)
from app.services.architecture.comm_matrix.building_automation import (
    BUILDING_AUTOMATION_ENTRIES,
)
from app.services.architecture.comm_matrix.data_center_infra import (
    DATA_CENTER_INFRA_ENTRIES,
)
from app.services.architecture.comm_matrix.distribution_logistics import (
    DISTRIBUTION_LOGISTICS_ENTRIES,
)
from app.services.architecture.comm_matrix.energy_generation import (
    ENERGY_GENERATION_ENTRIES,
)
from app.services.architecture.comm_matrix.energy_substation import (
    ENERGY_SUBSTATION_ENTRIES,
)
from app.services.architecture.comm_matrix.manufacturing_discrete import (
    MANUFACTURING_DISCRETE_ENTRIES,
)
from app.services.architecture.comm_matrix.manufacturing_process import (
    MANUFACTURING_PROCESS_ENTRIES,
    OIL_GAS_REFINERY_ENTRIES,
)
from app.services.architecture.comm_matrix.shared import SHARED_ENTRIES
from app.services.architecture.comm_matrix.transportation_its import (
    TRANSPORTATION_ITS_ENTRIES,
)
from app.services.architecture.comm_matrix.water_utility import (
    WATER_UTILITY_ENTRIES,
)


# Combined registry. Order matters for `find_entries`: vertical-specific
# entries appear first, SHARED last (function-side fallback rule).
_ALL_ENTRIES: tuple[CommEntry, ...] = (
    MANUFACTURING_DISCRETE_ENTRIES
    + MANUFACTURING_PROCESS_ENTRIES
    + ENERGY_SUBSTATION_ENTRIES
    + ENERGY_GENERATION_ENTRIES
    + OIL_GAS_REFINERY_ENTRIES
    + WATER_UTILITY_ENTRIES
    + BUILDING_AUTOMATION_ENTRIES
    + DATA_CENTER_INFRA_ENTRIES
    + TRANSPORTATION_ITS_ENTRIES
    + DISTRIBUTION_LOGISTICS_ENTRIES
    + SHARED_ENTRIES
)

_ALL_LIST: list[CommEntry] = list(_ALL_ENTRIES)


def list_entries() -> tuple[CommEntry, ...]:
    return _ALL_ENTRIES


def list_entries_for_vertical(vertical: str) -> tuple[CommEntry, ...]:
    """Vertical-specific + SHARED entries for the given vertical."""
    return tuple(
        e for e in _ALL_ENTRIES if e.applies_to(vertical)
    )


def find_matrix_entries(
    src_role: str,
    tgt_role: str,
    vertical: str,
) -> list[CommEntry]:
    """Look up matrix entries for a role-pair in a given vertical.

    Returns vertical-specific matches first, then SHARED fallbacks.
    """
    return find_entries(_ALL_LIST, src_role, tgt_role, vertical)


def has_matrix_entry(
    src_role: str,
    tgt_role: str,
    vertical: str,
) -> bool:
    return has_entry(_ALL_LIST, src_role, tgt_role, vertical)


__all__ = [
    "CommEntry",
    "SHARED_VERTICAL",
    "find_matrix_entries",
    "has_matrix_entry",
    "list_entries",
    "list_entries_for_vertical",
    "resolve_protocol",
]
