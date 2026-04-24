# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Canonical vendor and protocol name normalization.

This module provides the single source of truth for normalizing vendor names
and protocol names across the entire codebase. All other modules should import
from here instead of defining their own normalization logic.
"""

# Vendor name aliases: maps variations to canonical form
VENDOR_NAME_ALIASES: dict[str, str] = {
    # Full names -> canonical short names
    "johnson controls": "johnson_controls",
    "schneider electric": "schneider",
    "delta controls": "delta_controls",
    "distech controls": "distech",
    "automated logic": "automated_logic",
    "endress+hauser": "endress_hauser",
    "endress hauser": "endress_hauser",
    "ge multilin": "ge_multilin",
    # Handle underscore variants in lookups
    "johnson_controls": "johnson_controls",
    "schneider_electric": "schneider",
    "delta_controls": "delta_controls",
    "distech_controls": "distech",
    "automated_logic": "automated_logic",
    "endress_hauser": "endress_hauser",
    "ge_multilin": "ge_multilin",
    # Handle Allen-Bradley variations
    "allen-bradley": "allen_bradley",
    "allen bradley": "allen_bradley",
    "allen_bradley": "allen_bradley",
}


def normalize_vendor(vendor: str) -> str:
    """Normalize vendor name for consistent lookups.

    Handles variations like:
    - "Johnson Controls" -> "johnson_controls"
    - "Schneider Electric" -> "schneider"
    - "johnson_controls" -> "johnson_controls"
    - "Allen-Bradley" -> "allen_bradley"

    Args:
        vendor: Raw vendor name

    Returns:
        Normalized lowercase vendor name
    """
    lower = vendor.lower().strip()
    return VENDOR_NAME_ALIASES.get(lower, lower)


def vendors_match(query: str, fingerprint_vendor: str) -> bool:
    """Check if vendor names match, handling abbreviations and variations.

    Examples that should match:
    - "distech" matches "distech controls"
    - "delta_controls" matches "delta controls"
    - "johnson_controls" matches "johnson controls"

    Args:
        query: Vendor name to search for
        fingerprint_vendor: Vendor name from fingerprint data

    Returns:
        True if vendors match
    """
    q = _normalize_for_matching(query)
    fp = _normalize_for_matching(fingerprint_vendor)

    # Exact match
    if q == fp:
        return True

    # Query is prefix of fingerprint vendor
    if fp.startswith(q + " ") or fp.startswith(q):
        return True

    # Fingerprint vendor starts with query (reverse check)
    if q.startswith(fp + " ") or q.startswith(fp):
        return True

    return False


def _normalize_for_matching(name: str) -> str:
    """Normalize a name for fuzzy matching (strips separators)."""
    return name.lower().replace("_", " ").replace("-", " ").replace("+", " ").strip()
