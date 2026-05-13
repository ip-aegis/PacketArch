# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Archetype dataclasses + supporting enums.

An archetype is a per-vertical reference architecture that codifies:

  - Which Purdue zones exist (zone skeleton).
  - Which roles belong in each zone, split into REQUIRED (must be
    present at every scale tier) vs OPTIONAL (added as scale grows).
  - How role counts scale across DEMO / SMALL / MEDIUM / LARGE /
    MULTI_SITE tiers.
  - Default vendor profile and which protocols cross which conduits.

Templates and the AI wizard select an archetype + scale + vendor and
the scenario_generator does the rest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.services.architecture.role_catalog import Vertical


# ---------------------------------------------------------------------------
# Scale tiers
# ---------------------------------------------------------------------------

class ScaleTier(str, Enum):
    """Scale tiers governing device counts and zone collapse.

    DEMO and SMALL collapse IDMZ into operations. MEDIUM separates
    them. LARGE adds historian replicas, asset management, NMS,
    full-vendor IDMZ. MULTI_SITE replicates the LARGE pattern at a
    site and adds inter-site SCADA aggregation.
    """

    DEMO = "demo"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    MULTI_SITE = "multi_site"

    @property
    def numeric(self) -> int:
        return {"demo": 0, "small": 1, "medium": 2,
                "large": 3, "multi_site": 4}[self.value]


# ---------------------------------------------------------------------------
# Vendor profiles
# ---------------------------------------------------------------------------

class VendorProfile(str, Enum):
    """Vendor-affinity selector.

    Drives which catalog fingerprints are picked when materializing
    devices. The comm matrix uses the vendor profile to rank protocol
    options (vendor-native first, OPC UA cross-vendor, generic fallback).
    """

    # Discrete / multi-purpose shops.
    SIEMENS_SHOP = "siemens_shop"
    ROCKWELL_SHOP = "rockwell_shop"
    SCHNEIDER_SHOP = "schneider_shop"
    ABB_SHOP = "abb_shop"
    MULTI_VENDOR = "multi_vendor"

    # Process-vertical DCS profiles.
    DCS_EMERSON = "dcs_emerson"
    DCS_HONEYWELL = "dcs_honeywell"
    DCS_YOKOGAWA = "dcs_yokogawa"
    DCS_ABB = "dcs_abb"

    # Master-remote / mixed-field profiles (water, substation, oil&gas).
    MIXED_FIELD = "mixed_field"
    SEL_PROTECTION = "sel_protection"
    SCADAPACK = "scadapack"

    # Verticals where vendor-affinity is unconventional or single-domain.
    BAS_TRIDIUM = "bas_tridium"
    ATMS_NTCIP = "atms_ntcip"
    DCIM_CISCO = "dcim_cisco"


# ---------------------------------------------------------------------------
# Architecture patterns (within-vertical sub-shapes)
# ---------------------------------------------------------------------------

class ArchitecturePattern(str, Enum):
    """High-level shape of the OT network.

    Independent of vertical (multiple verticals can use the same pattern):

      - DISCRETE_CELL: cells with their own cell_controller + area_hmi,
        coordinated by L3 SCADA. Manufacturing, distribution_logistics.
      - CONTINUOUS_DCS: DCS controllers + field instruments + L3 SCADA.
        Manufacturing_process, oil_gas, energy_generation.
      - MASTER_REMOTE_SCADA: central aggregator_rtu + remote field_rtus
        over WAN. Water utility, energy substation, oil&gas pipeline.
      - DISTRIBUTED_SUBSTATION: per-bay protection relays + GOOSE +
        station bus. Energy_substation only.
      - ATMS_CORRIDOR: traffic master + roadside cabinet controllers.
        Transportation_its only.
      - BAS_SUPERVISOR: BAS supervisor + per-zone field controllers.
        Building_automation only.
      - WAREHOUSE_PICK: WCS + conveyor/sortation + AGV.
        Distribution_logistics.
      - DCIM_FACILITY: DCIM server + PDU/UPS/CRAC.
        Data_center_infra.
    """

    DISCRETE_CELL = "discrete_cell"
    CONTINUOUS_DCS = "continuous_dcs"
    MASTER_REMOTE_SCADA = "master_remote_scada"
    DISTRIBUTED_SUBSTATION = "distributed_substation"
    ATMS_CORRIDOR = "atms_corridor"
    BAS_SUPERVISOR = "bas_supervisor"
    WAREHOUSE_PICK = "warehouse_pick"
    DCIM_FACILITY = "dcim_facility"


# ---------------------------------------------------------------------------
# Zone slot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoleSlot:
    """A role slot inside a zone.

    `count_by_scale` lets the archetype scale device counts up/down
    by tier without redeclaring zones. `optional_at` says which scale
    tiers can omit this slot entirely.

    Example: `process_historian` has count_by_scale={"demo": 0,
    "small": 1, "medium": 1, "large": 2, "multi_site": 2} and
    `optional_at=("demo",)` — DEMO scenarios can skip the historian
    entirely; LARGE scenarios get a primary + replica.
    """

    role_id: str
    """Reference to a Role in role_catalog."""

    count_by_scale: dict[str, int]
    """{ScaleTier.value: instance_count}. Defaults to 1 at every scale."""

    optional_at: tuple[str, ...] = ()
    """Scale tiers (by .value) at which this slot may be omitted entirely
    (count=0). Beyond those tiers the slot is required."""

    name_prefix: str | None = None
    """Optional override for generated device name prefix. If None,
    derived from role_id."""

    role_hint: str | None = None
    """Optional sub-role label (e.g. 'Main', 'Backup', 'Material Handling')
    that the generator uses to disambiguate when role_id has count > 1."""

    def count_at(self, scale: ScaleTier) -> int:
        return self.count_by_scale.get(scale.value, 1)

    def is_optional_at(self, scale: ScaleTier) -> bool:
        return scale.value in self.optional_at


# ---------------------------------------------------------------------------
# Zone definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ZoneDef:
    """Per-zone declaration in an archetype.

    Zones are the IEC 62443 zones — Purdue-aligned but archetype-specific
    (e.g., a refinery has separate `process_field` and `safety` zones at
    L1 even though both are L1).
    """

    id: str
    """Stable zone identifier used by conduits, flows, and overrides."""

    name: str
    """Human-readable zone name (rendered in canvas + readiness)."""

    purdue_level: float
    """Numeric Purdue level for display + conduit-direction rules."""

    role_slots: tuple[RoleSlot, ...]
    """Roles in this zone (required + optional, scale-aware)."""

    is_external: bool = False
    """Marks L4+ / cloud / partner zones (skipped by Cyber Vision)."""

    security_level: str = "standard"
    """IEC 62443 informal zone security level: external, standard, high,
    critical."""

    description: str = ""
    """One-line zone description for docs / readiness UI."""


# ---------------------------------------------------------------------------
# Conduit template
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConduitTemplate:
    """A conduit between two zones in the archetype.

    Conduits are the IEC 62443 boundary objects. Cross-zone flows must
    fit a conduit (matched by source_zone + target_zone + protocol);
    flows that don't are rejected in strict-northbound cell isolation
    mode.

    The archetype declares the conduit; the generator materializes the
    flows that use it from the comm matrix.
    """

    id: str
    """Stable conduit identifier."""

    name: str
    """Human-readable conduit name."""

    source_zone: str
    """Source zone id (relative to the archetype's zones)."""

    target_zone: str
    """Target zone id."""

    direction: str = "bidirectional"
    """One of: 'north', 'south', 'bidirectional'. Northbound = flows
    from lower Purdue to higher; southbound = the reverse."""

    allowed_protocols: tuple[str, ...] = ()
    """Protocols permitted to cross this conduit. Subset of what the
    flows materialize to."""

    security_level: str = "standard"
    """external | standard | high | critical."""

    description: str = ""


# ---------------------------------------------------------------------------
# Archetype
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Archetype:
    """A per-vertical reference architecture.

    Templates and AI scenarios pick an archetype + scale + vendor; the
    scenario generator combines those with the role catalog and comm
    matrix to materialize a fully-populated scenario.
    """

    id: str
    """Stable archetype identifier (e.g. 'manufacturing_discrete_cell')."""

    name: str
    """Human-readable name."""

    vertical: str
    """One of Vertical enum values."""

    pattern: ArchitecturePattern
    """High-level network shape."""

    description: str
    """One-paragraph description of when to use this archetype."""

    default_vendor_profile: VendorProfile
    """Default vendor profile when the caller doesn't override."""

    supported_vendor_profiles: tuple[VendorProfile, ...] = ()
    """Vendor profiles that are valid for this archetype. Empty = only
    the default is supported."""

    zones: tuple[ZoneDef, ...] = ()
    """Zone skeleton. Order is rendered as canvas left-to-right top-to-
    bottom; logically L0 .. L4."""

    conduits: tuple[ConduitTemplate, ...] = ()
    """Inter-zone conduits permitted by IEC 62443."""

    min_scale: ScaleTier = ScaleTier.DEMO
    """The smallest scale this archetype supports. Some patterns (e.g.
    multi-vendor enterprise) don't make sense at DEMO."""

    cell_isolation_default: str = "off"
    """Default cell_isolation.mode. One of: off | conduit_gated |
    strict_northbound."""

    notes: tuple[str, ...] = ()
    """Authoring notes / caveats. Surfaced in reference-architecture docs."""

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def supports_vendor_profile(self, vp: VendorProfile) -> bool:
        if not self.supported_vendor_profiles:
            return vp == self.default_vendor_profile
        return vp in self.supported_vendor_profiles

    def get_zone(self, zone_id: str) -> ZoneDef | None:
        for z in self.zones:
            if z.id == zone_id:
                return z
        return None

    def all_role_ids(self) -> tuple[str, ...]:
        out: list[str] = []
        for z in self.zones:
            for s in z.role_slots:
                if s.role_id not in out:
                    out.append(s.role_id)
        return tuple(out)
