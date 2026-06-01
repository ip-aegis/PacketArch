# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Canonical vendor and protocol name normalization.

The vendor-name normalization (``normalize_vendor`` + ``VENDOR_NAME_ALIASES``)
lives in ``app.protocol_engines.vendor_oui`` — a stdlib-only module that is
staged into the traffic agent, which has no access to ``app.core``. This module
re-exports them so existing backend imports keep working, and adds the
backend-only fuzzy ``vendors_match`` helper.
"""

# Re-exported from the staged vendor source-of-truth module.
from app.protocol_engines.vendor_oui import (  # noqa: F401
    VENDOR_NAME_ALIASES,
    normalize_vendor,
)


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
