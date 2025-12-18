"""Vendor fingerprint modules for major OT vendors.

This package contains comprehensive fingerprint data for major OT vendors
organized by vendor for maintainability. Each vendor module contains
detailed device fingerprints including protocol identities, TCP stack
characteristics, response timing distributions, and protocol quirks.

Usage:
    from app.services.vendor_fingerprints import get_all_vendor_fingerprints
    fingerprints = get_all_vendor_fingerprints()
"""

from typing import Any

from .rockwell import get_rockwell_fingerprints, ROCKWELL_OUI_PREFIXES
from .siemens import get_siemens_fingerprints, SIEMENS_OUI_PREFIXES
from .schneider import get_schneider_fingerprints, SCHNEIDER_OUI_PREFIXES
from .specialty import (
    get_specialty_fingerprints,
    SICK_OUI_PREFIXES,
    YOKOGAWA_OUI_PREFIXES,
    ENDRESS_HAUSER_OUI_PREFIXES,
    HONEYWELL_OUI_PREFIXES,
    ABB_OUI_PREFIXES,
    EMERSON_OUI_PREFIXES,
)

# ODVA Vendor IDs (official registrations)
ODVA_VENDOR_IDS = {
    "rockwell": 1,  # Allen-Bradley (Rockwell Automation)
    "schneider": 67,  # Schneider Electric
    "siemens": 285,  # Siemens
    "abb": 285,  # ABB also uses 285 in some products
    "honeywell": 50,  # Honeywell
    "emerson": 90,  # Emerson
    "ge": 82,  # General Electric
    "omron": 47,  # Omron
    "mitsubishi": 121,  # Mitsubishi
}

# PROFINET Vendor IDs
PROFINET_VENDOR_IDS = {
    "siemens": 0x002A,  # 42
    "schneider": 0x0095,  # 149
    "rockwell": 0x0001,  # 1
    "abb": 0x0037,  # 55
    "phoenix_contact": 0x00B8,  # 184
}

# Aggregated OUI prefixes by vendor
VENDOR_OUI_PREFIXES = {
    "rockwell": ROCKWELL_OUI_PREFIXES,
    "siemens": SIEMENS_OUI_PREFIXES,
    "schneider": SCHNEIDER_OUI_PREFIXES,
    "sick": SICK_OUI_PREFIXES,
    "yokogawa": YOKOGAWA_OUI_PREFIXES,
    "endress+hauser": ENDRESS_HAUSER_OUI_PREFIXES,
    "honeywell": HONEYWELL_OUI_PREFIXES,
    "abb": ABB_OUI_PREFIXES,
    "emerson": EMERSON_OUI_PREFIXES,
    "ge": [
        "00:14:49",  # GE Fanuc Automation
        "00:60:B0",  # GE Energy
        "1C:39:47",  # GE
    ],
}


def get_all_vendor_fingerprints() -> list[dict[str, Any]]:
    """Get all vendor fingerprints for seeding.

    Returns comprehensive fingerprints for all supported vendors:
    - Major vendors: Rockwell, Siemens, Schneider
    - Specialty vendors: SICK, Yokogawa, Endress+Hauser, Honeywell, ABB, Emerson
    """
    fingerprints = []
    fingerprints.extend(get_rockwell_fingerprints())
    fingerprints.extend(get_siemens_fingerprints())
    fingerprints.extend(get_schneider_fingerprints())
    fingerprints.extend(get_specialty_fingerprints())
    return fingerprints


def get_fingerprint_by_vendor_model(vendor: str, model: str) -> dict[str, Any] | None:
    """Find a fingerprint by vendor and model."""
    for fp in get_all_vendor_fingerprints():
        if fp["vendor"].lower() == vendor.lower() and fp.get("model") == model:
            return fp
    return None


def get_fingerprints_by_vendor(vendor: str) -> list[dict[str, Any]]:
    """Get all fingerprints for a vendor."""
    return [
        fp
        for fp in get_all_vendor_fingerprints()
        if fp["vendor"].lower() == vendor.lower()
    ]


def get_random_oui_for_vendor(vendor: str) -> str | None:
    """Get a random OUI prefix for a vendor."""
    import random

    ouis = VENDOR_OUI_PREFIXES.get(vendor.lower(), [])
    return random.choice(ouis) if ouis else None
