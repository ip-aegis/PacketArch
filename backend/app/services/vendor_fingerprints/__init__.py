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

from app.protocol_engines.vendor_oui import VENDOR_OUIS

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
from .transportation import (
    get_transportation_fingerprints,
    ECONOLITE_OUI_PREFIXES,
    SIEMENS_ITS_OUI_PREFIXES,
    MCCAIN_OUI_PREFIXES,
    WAVETRONIX_OUI_PREFIXES,
    FLIR_OUI_PREFIXES,
    DAKTRONICS_OUI_PREFIXES,
    KAPSCH_OUI_PREFIXES,
    QFREE_OUI_PREFIXES,
    AXIS_OUI_PREFIXES,
    PELCO_OUI_PREFIXES,
    BOSCH_OUI_PREFIXES,
    HIKVISION_OUI_PREFIXES,
)
from .building_automation import (
    get_building_automation_fingerprints,
    JOHNSON_CONTROLS_OUI_PREFIXES,
    TRIDIUM_OUI_PREFIXES,
    TRANE_OUI_PREFIXES,
    CARRIER_OUI_PREFIXES,
    DELTA_CONTROLS_OUI_PREFIXES,
    DISTECH_OUI_PREFIXES,
    CAREL_OUI_PREFIXES,
    AUTOMATED_LOGIC_OUI_PREFIXES,
    SIEMENS_BUILDING_OUI_PREFIXES,
    SCHNEIDER_BMS_OUI_PREFIXES,
)
from .energy import (
    get_energy_fingerprints,
    SEL_OUI_PREFIXES,
    SIEMENS_PROTECTION_OUI_PREFIXES,
    GE_MULTILIN_OUI_PREFIXES,
    BASLER_OUI_PREFIXES,
)
from .ge import get_ge_fingerprints, GE_OUI_PREFIXES
from .microsoft import get_microsoft_fingerprints, MICROSOFT_OUI_PREFIXES
from .logistics import (
    get_logistics_fingerprints,
    KUKA_OUI_PREFIXES,
    MIR_OUI_PREFIXES,
    COGNEX_OUI_PREFIXES,
    IMPINJ_OUI_PREFIXES,
    ZEBRA_OUI_PREFIXES,
    DEMATIC_OUI_PREFIXES,
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
    # Logistics / AGV vendors
    "kuka": 368,  # KUKA Roboter GmbH
    "cognex": 112,  # Cognex Corporation
}

# PROFINET Vendor IDs
PROFINET_VENDOR_IDS = {
    "siemens": 0x002A,  # 42
    "schneider": 0x0095,  # 149
    "rockwell": 0x0001,  # 1
    "abb": 0x0037,  # 55
    "phoenix_contact": 0x00B8,  # 184
}

# Aggregated OUI prefixes by vendor.
# Canonical source is VENDOR_OUIS from vendor_oui.py.
# Sub-module constants add vendor division aliases not in the canonical source.
VENDOR_OUI_PREFIXES: dict[str, list[str]] = {
    **VENDOR_OUIS,
    # Aliases / vendor divisions not in vendor_oui.py
    "endress+hauser": ENDRESS_HAUSER_OUI_PREFIXES,
    "ge_multilin": GE_MULTILIN_OUI_PREFIXES,
    "siemens_building": SIEMENS_BUILDING_OUI_PREFIXES,
    "schneider_bms": SCHNEIDER_BMS_OUI_PREFIXES,
    "siemens_protection": SIEMENS_PROTECTION_OUI_PREFIXES,
    "microsoft": MICROSOFT_OUI_PREFIXES,
}


def get_all_vendor_fingerprints() -> list[dict[str, Any]]:
    """Get all vendor fingerprints for seeding.

    Returns comprehensive fingerprints for all supported vendors:
    - Major vendors: Rockwell, Siemens, Schneider, GE
    - Specialty vendors: SICK, Yokogawa, Endress+Hauser, Honeywell, ABB, Emerson
    - Transportation vendors: Econolite, McCain, Wavetronix, FLIR, Daktronics, etc.
    - Building Automation: Johnson Controls, Trane, Carrier, Delta Controls, etc.
    - Energy / Protection: SEL, GE Multilin, Siemens SIPROTEC, ABB Relion
    - IT/OT Boundary: Microsoft Windows jump servers
    - Logistics / Warehouse: KUKA, MiR, Cognex, Impinj, Zebra, Dematic
    """
    fingerprints = []
    fingerprints.extend(get_rockwell_fingerprints())
    fingerprints.extend(get_siemens_fingerprints())
    fingerprints.extend(get_schneider_fingerprints())
    fingerprints.extend(get_specialty_fingerprints())
    fingerprints.extend(get_transportation_fingerprints())
    fingerprints.extend(get_building_automation_fingerprints())
    fingerprints.extend(get_energy_fingerprints())
    fingerprints.extend(get_ge_fingerprints())
    fingerprints.extend(get_microsoft_fingerprints())
    fingerprints.extend(get_logistics_fingerprints())
    return fingerprints


def get_fingerprint_by_vendor_model(vendor: str, model: str) -> dict[str, Any] | None:
    """Find a fingerprint by vendor and model.

    DEPRECATED: Use device_templates.get_fingerprint_by_vendor_model() instead.
    This function is maintained for backwards compatibility and will be removed
    in a future version.

    Matches against multiple fields for flexibility:
    - model (exact match, e.g., "6ES7 517-3AP00-0AB0")
    - profinet_identity.device_type (e.g., "CPU 1517-3 PN/DP")
    - modbus_identity.product_name (e.g., "CPU 1517-3 PN/DP")
    - ethernet_ip_identity.product_name (e.g., "1756-L85E/B")
    - s7_identity.module_type (e.g., "CPU 1517-3 PN/DP")
    """
    import warnings
    warnings.warn(
        "vendor_fingerprints.get_fingerprint_by_vendor_model() is deprecated. "
        "Use device_templates.get_fingerprint_by_vendor_model() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Try device templates first (new source of truth)
    from app.services.device_templates import get_fingerprint_by_vendor_model as new_fn
    result = new_fn(vendor, model)
    if result:
        return result

    # Fall back to fingerprint cache for backwards compatibility
    from app.services.fingerprint_cache import get_fingerprint_cache
    cache = get_fingerprint_cache()
    return cache.get_by_vendor_model(vendor, model)


def get_fingerprints_by_vendor(vendor: str) -> list[dict[str, Any]]:
    """Get all fingerprints for a vendor.

    DEPRECATED: Use device_templates.get_fingerprints_by_vendor() instead.
    This function is maintained for backwards compatibility and will be removed
    in a future version.
    """
    import warnings
    warnings.warn(
        "vendor_fingerprints.get_fingerprints_by_vendor() is deprecated. "
        "Use device_templates.get_fingerprints_by_vendor() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Try device templates first (new source of truth)
    from app.services.device_templates import get_fingerprints_by_vendor as new_fn
    results = new_fn(vendor)
    if results:
        return results

    # Fall back to fingerprint cache for backwards compatibility
    from app.services.fingerprint_cache import get_fingerprint_cache
    cache = get_fingerprint_cache()
    return cache.get_by_vendor(vendor)


def get_random_oui_for_vendor(vendor: str) -> str | None:
    """Get a random OUI prefix for a vendor."""
    import random

    ouis = VENDOR_OUI_PREFIXES.get(vendor.lower(), [])
    return random.choice(ouis) if ouis else None
