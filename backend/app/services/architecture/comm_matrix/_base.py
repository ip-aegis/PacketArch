# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Communication matrix dataclasses + protocol resolver.

A `CommEntry` records that role X talks to role Y in vertical V using
pattern P at interval I. The actual wire protocol picked by the
generator depends on the source vendor profile and the catalog
supported_protocols of both endpoints — `resolve_protocol()` picks the
first candidate that both endpoints support.

Why the indirection: writing "modbus_tcp" in a flow spec only works if
the source endpoint actually serves Modbus TCP. The matrix declares
*intent* (poll, cyclic_io, subscription) and *preferences* (vendor-
native first, OPC UA cross-vendor, generic SNMP fallback); the
generator does the catalog-aware selection. This is the mechanism that
prevents the "Siemens HMI polling Rockwell PLC over modbus_tcp" class
of authoring bug from ever reaching a flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.architecture.archetypes._base import VendorProfile


SHARED_VERTICAL = "*"
"""Sentinel vertical for entries that apply across all verticals (e.g.
IDMZ patterns: jump_server → scada_primary)."""


# ---------------------------------------------------------------------------
# CommEntry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommEntry:
    """A typed (src_role, tgt_role, vertical) → comm pattern record.

    The matrix is keyed by (src_role, tgt_role, vertical). Lookup falls
    back to (src_role, tgt_role, "*") if no vertical-specific entry
    exists.
    """

    src_role: str
    """Role ID of the flow initiator. Must match a Role.id in the
    catalog."""

    tgt_role: str
    """Role ID of the flow target."""

    vertical: str
    """Vertical or SHARED_VERTICAL for cross-vertical patterns."""

    pattern: str
    """Communication pattern. One of: poll, cyclic_io, subscription,
    event, safety, heartbeat, replication, configuration."""

    interval_ms: tuple[int, int]
    """(min, max) interval in milliseconds. The generator picks within
    this range."""

    protocol_options: tuple[str, ...] = ()
    """Protocols ranked by preference. The first one supported by both
    endpoints (per their catalog supported_protocols) is chosen.
    Common values: ("ethernet_ip", "modbus_tcp", "opc_ua", "snmp")."""

    vendor_overrides: dict[str, tuple[str, ...]] = field(default_factory=dict)
    """Per-vendor-profile protocol override list. Tried before
    protocol_options. Key is VendorProfile.value (e.g. "siemens_shop")."""

    jitter_ms: tuple[int, int] = (0, 0)
    """(min, max) jitter on the interval. Default no jitter."""

    phase_tags: tuple[str, ...] = ("steady",)
    """Lifecycle phases when this flow is active. Common values:
    'steady' (always), 'startup', 'maintenance', 'fault'. Multiple
    tags = active in any of those phases."""

    conduit_required: bool = True
    """If src + tgt are in different zones, this flow must fit a
    conduit. Default True."""

    description: str = ""
    """One-line description for docs / canvas tooltips."""

    fan_out: str = "all"
    """How instances multiply when src or tgt has multiple instances:
    'all' (M×N — every src to every tgt),
    'pair' (M==N round-robin),
    'one_per_src' (each src picks one tgt round-robin)."""

    def applies_to(self, vertical: str) -> bool:
        return self.vertical == SHARED_VERTICAL or self.vertical == vertical


# ---------------------------------------------------------------------------
# Protocol resolver
# ---------------------------------------------------------------------------

# Universal cross-vendor fallback chain. Tried after vendor_overrides
# and protocol_options exhaust without a match.
_UNIVERSAL_FALLBACK: tuple[str, ...] = ("opc_ua", "snmp")


def resolve_protocol(
    entry: CommEntry,
    src_vendor_profile: VendorProfile | str,
    src_supported: set[str],
    tgt_supported: set[str],
) -> str | None:
    """Pick the protocol the generator should write into the flow.

    Precedence (first match wins):
      1. entry.vendor_overrides[src_vendor_profile]: protocols tried
         in order; first supported by both endpoints wins.
      2. entry.protocol_options: same rule.
      3. Universal fallback: OPC UA, then SNMP.

    Returns None if no protocol is supported by both endpoints — the
    generator surfaces this as a "no shared protocol" warning. (Should
    not happen in practice once the catalog is correct.)
    """
    if isinstance(src_vendor_profile, VendorProfile):
        vp_value = src_vendor_profile.value
    else:
        vp_value = src_vendor_profile

    candidates: list[str] = []
    candidates.extend(entry.vendor_overrides.get(vp_value, ()))
    candidates.extend(entry.protocol_options)
    candidates.extend(_UNIVERSAL_FALLBACK)

    seen: set[str] = set()
    for proto in candidates:
        if proto in seen:
            continue
        seen.add(proto)
        if proto in src_supported and proto in tgt_supported:
            return proto
    return None


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def find_entries(
    entries: list[CommEntry],
    src_role: str,
    tgt_role: str,
    vertical: str,
) -> list[CommEntry]:
    """Find all matching CommEntry records for a role-pair.

    Returns vertical-specific entries first, then SHARED_VERTICAL
    fallbacks. A role-pair can have multiple entries (e.g. the same
    SCADA→PLC pair has both a poll-pattern and an
    occasional-configuration pattern with different intervals).
    """
    out: list[CommEntry] = []
    for e in entries:
        if e.src_role != src_role or e.tgt_role != tgt_role:
            continue
        if e.vertical == vertical:
            out.append(e)
    for e in entries:
        if e.src_role != src_role or e.tgt_role != tgt_role:
            continue
        if e.vertical == SHARED_VERTICAL:
            out.append(e)
    return out


def has_entry(
    entries: list[CommEntry],
    src_role: str,
    tgt_role: str,
    vertical: str,
) -> bool:
    return bool(find_entries(entries, src_role, tgt_role, vertical))
