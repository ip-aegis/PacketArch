# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Architectural knowledge base for OT scenario authoring.

Top-down model that encodes IEC 62443 / ISA-95 / Purdue conventions so
that templates and AI-generated scenarios start from a rational floor:

  - role_catalog: ~46 typed roles, each with Purdue level + per-vertical
    applicability + required/optional protocols + typical partners.
  - archetypes: per-vertical reference architectures (zone skeletons +
    role manifests) at multiple scale tiers.
  - comm_matrix: typed (src_role, tgt_role, vertical) -> protocol/pattern
    rules. The institutional knowledge of "what talks to what."
  - scenario_generator: composes archetype + vendor profile + scale +
    overrides into a fully-populated scenario definition.

Existing free-form scenario_templates remain authoritative for the
single-pass build path until Phase 5 refactors them onto this engine.
"""

from .archetypes import (
    Archetype,
    ArchitecturePattern,
    ConduitTemplate,
    RoleSlot,
    ScaleTier,
    VendorProfile,
    ZoneDef,
    get_archetype,
    list_archetypes,
    list_archetypes_for_vertical,
)
from .comm_matrix import (
    CommEntry,
    SHARED_VERTICAL,
    find_matrix_entries,
    has_matrix_entry,
    list_entries,
    list_entries_for_vertical,
    resolve_protocol,
)
from .role_catalog import (
    Role,
    RoleCategory,
    Vertical,
    VERTICALS,
    get_role,
    list_roles,
    list_roles_at_purdue_level,
    list_roles_for_vertical,
)

__all__ = [
    # role catalog
    "Role",
    "RoleCategory",
    "Vertical",
    "VERTICALS",
    "get_role",
    "list_roles",
    "list_roles_for_vertical",
    "list_roles_at_purdue_level",
    # archetypes
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
    # comm matrix
    "CommEntry",
    "SHARED_VERTICAL",
    "find_matrix_entries",
    "has_matrix_entry",
    "list_entries",
    "list_entries_for_vertical",
    "resolve_protocol",
]
