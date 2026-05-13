# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Architecture-rail public API.

Surface the role catalog, archetypes, and comm matrix to:

  - The frontend canvas (Phase 7 — flow validation hints)
  - The reference-architecture docs UI (Phase 8)
  - External integrations / SDK consumers
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.architecture import (
    Vertical,
    get_archetype,
    get_role,
    list_archetypes,
    list_archetypes_for_vertical,
    list_entries_for_vertical,
    list_roles,
    list_roles_for_vertical,
)
from app.services.architecture.archetypes._base import (
    ScaleTier,
    VendorProfile,
)
from app.services.architecture.comm_matrix import (
    find_matrix_entries,
    has_matrix_entry,
)


router = APIRouter(prefix="/architecture", tags=["Architecture"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RoleSummary(BaseModel):
    id: str
    name: str
    category: str
    purdue_level: float
    description: str
    when_to_include: str
    primary_device_types: list[str]
    vertical_applicability: list[str]
    required_protocols: list[str]
    optional_protocols: list[str]
    typical_partners: list[str]
    examples: list[str]


class ArchetypeSummary(BaseModel):
    id: str
    name: str
    vertical: str
    pattern: str
    description: str
    default_vendor_profile: str
    supported_vendor_profiles: list[str]
    zones: list[dict[str, Any]]
    conduits: list[dict[str, Any]]
    notes: list[str]


class CommMatrixEntrySummary(BaseModel):
    src_role: str
    tgt_role: str
    vertical: str
    pattern: str
    interval_ms_min: int
    interval_ms_max: int
    protocol_options: list[str]
    description: str


class FlowCheckRequest(BaseModel):
    src_role: str
    tgt_role: str
    vertical: str
    protocol: str | None = None


class FlowCheckResponse(BaseModel):
    in_matrix: bool
    """True if the matrix has at least one entry for this role pair."""

    matrix_entries: list[CommMatrixEntrySummary]
    """All matrix entries that match the role pair (vertical-specific
    first, SHARED last)."""

    suggestion: str | None = None
    """One-line authoring suggestion when the protocol doesn't match
    a matrix entry but a closely-related entry does exist."""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/verticals", response_model=list[str])
def get_verticals() -> list[str]:
    """List all supported industrial verticals."""
    return [v.value for v in Vertical]


@router.get("/scale-tiers", response_model=list[str])
def get_scale_tiers() -> list[str]:
    """List the scale tiers available for archetype materialization."""
    return [s.value for s in ScaleTier]


@router.get("/vendor-profiles", response_model=list[str])
def get_vendor_profiles() -> list[str]:
    """List all vendor profiles defined in the architecture rail."""
    return [vp.value for vp in VendorProfile]


@router.get("/roles", response_model=list[RoleSummary])
def get_roles(vertical: str | None = None) -> list[RoleSummary]:
    """List roles in the catalog. Optionally filter by vertical."""
    roles = list_roles_for_vertical(vertical) if vertical else list_roles()
    return [_role_to_summary(r) for r in roles]


@router.get("/roles/{role_id}", response_model=RoleSummary)
def get_role_by_id(role_id: str) -> RoleSummary:
    role = get_role(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role not found: {role_id}")
    return _role_to_summary(role)


@router.get("/archetypes", response_model=list[ArchetypeSummary])
def get_archetypes(vertical: str | None = None) -> list[ArchetypeSummary]:
    """List archetypes. Optionally filter by vertical."""
    arches = (
        list_archetypes_for_vertical(vertical) if vertical
        else list_archetypes()
    )
    return [_archetype_to_summary(a) for a in arches]


@router.get("/archetypes/{archetype_id}", response_model=ArchetypeSummary)
def get_archetype_by_id(archetype_id: str) -> ArchetypeSummary:
    arch = get_archetype(archetype_id)
    if arch is None:
        raise HTTPException(
            status_code=404, detail=f"Archetype not found: {archetype_id}",
        )
    return _archetype_to_summary(arch)


@router.get("/comm-matrix", response_model=list[CommMatrixEntrySummary])
def get_comm_matrix(vertical: str) -> list[CommMatrixEntrySummary]:
    """List all comm-matrix entries that apply to a given vertical
    (includes SHARED cross-vertical entries)."""
    entries = list_entries_for_vertical(vertical)
    return [_entry_to_summary(e) for e in entries]


@router.post("/check-flow", response_model=FlowCheckResponse)
def check_flow(request: FlowCheckRequest) -> FlowCheckResponse:
    """Check whether a (src_role, tgt_role, vertical [, protocol]) flow
    is endorsed by the comm matrix. Used by the canvas authoring
    validator (Phase 7) to surface gentle hints when a user-drawn flow
    falls outside the architecture rail.
    """
    entries = find_matrix_entries(
        request.src_role, request.tgt_role, request.vertical,
    )
    in_matrix = bool(entries)
    suggestion: str | None = None

    if in_matrix and request.protocol:
        # The pair is in the matrix; check whether the protocol matches.
        protocols_in_matrix: set[str] = set()
        for e in entries:
            protocols_in_matrix.update(e.protocol_options)
            for plist in e.vendor_overrides.values():
                protocols_in_matrix.update(plist)
        if request.protocol not in protocols_in_matrix:
            suggestion = (
                f"Matrix supports {sorted(protocols_in_matrix)} for this "
                f"role pair; you used {request.protocol}. Consider switching."
            )
    elif not in_matrix:
        suggestion = (
            f"No matrix entry for {request.src_role} → {request.tgt_role} "
            f"in {request.vertical}. Templates and AI scenarios won't "
            "generate this pattern. Use only if you intend an off-rail "
            "authoring choice."
        )

    return FlowCheckResponse(
        in_matrix=in_matrix,
        matrix_entries=[_entry_to_summary(e) for e in entries],
        suggestion=suggestion,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _role_to_summary(r: Any) -> RoleSummary:
    return RoleSummary(
        id=r.id,
        name=r.name,
        category=r.category.value,
        purdue_level=r.purdue_level,
        description=r.description,
        when_to_include=r.when_to_include,
        primary_device_types=list(r.primary_device_types),
        vertical_applicability=(
            sorted(r.vertical_applicability)
            if r.vertical_applicability else []
        ),
        required_protocols=list(r.required_protocols),
        optional_protocols=list(r.optional_protocols),
        typical_partners=list(r.typical_partners),
        examples=list(r.examples),
    )


def _archetype_to_summary(a: Any) -> ArchetypeSummary:
    zones = [
        {
            "id": z.id,
            "name": z.name,
            "purdue_level": z.purdue_level,
            "security_level": z.security_level,
            "description": z.description,
            "is_external": z.is_external,
            "role_slots": [
                {
                    "role_id": s.role_id,
                    "count_by_scale": dict(s.count_by_scale),
                    "optional_at": list(s.optional_at),
                }
                for s in z.role_slots
            ],
        }
        for z in a.zones
    ]
    conduits = [
        {
            "id": c.id,
            "name": c.name,
            "source_zone": c.source_zone,
            "target_zone": c.target_zone,
            "direction": c.direction,
            "allowed_protocols": list(c.allowed_protocols),
            "security_level": c.security_level,
            "description": c.description,
        }
        for c in a.conduits
    ]
    return ArchetypeSummary(
        id=a.id,
        name=a.name,
        vertical=a.vertical,
        pattern=a.pattern.value,
        description=a.description,
        default_vendor_profile=a.default_vendor_profile.value,
        supported_vendor_profiles=[
            v.value for v in a.supported_vendor_profiles
        ] or [a.default_vendor_profile.value],
        zones=zones,
        conduits=conduits,
        notes=list(a.notes),
    )


def _entry_to_summary(e: Any) -> CommMatrixEntrySummary:
    return CommMatrixEntrySummary(
        src_role=e.src_role,
        tgt_role=e.tgt_role,
        vertical=e.vertical,
        pattern=e.pattern,
        interval_ms_min=e.interval_ms[0],
        interval_ms_max=e.interval_ms[1],
        protocol_options=list(e.protocol_options),
        description=e.description,
    )


__all__ = ["router"]
