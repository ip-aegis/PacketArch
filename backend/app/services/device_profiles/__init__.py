"""Device profile modules for major OT vendors.

This package contains device profiles for Rockwell, Siemens, and
Schneider Electric devices. Each profile includes timing models,
payload templates, behavior models, and vendor fingerprint references.

Usage:
    from app.services.device_profiles import get_all_vendor_profiles
    profiles = get_all_vendor_profiles()
"""

from typing import Any

from .rockwell_profiles import ROCKWELL_PROFILES
from .siemens_profiles import SIEMENS_PROFILES
from .schneider_profiles import SCHNEIDER_PROFILES


def get_all_vendor_profiles() -> list[dict[str, Any]]:
    """Get all vendor-specific device profiles for seeding.

    Returns comprehensive device profiles for Rockwell, Siemens, and Schneider.
    """
    profiles = []
    profiles.extend(ROCKWELL_PROFILES)
    profiles.extend(SIEMENS_PROFILES)
    profiles.extend(SCHNEIDER_PROFILES)
    return profiles


def get_profiles_by_vendor(vendor: str) -> list[dict[str, Any]]:
    """Get all profiles for a specific vendor."""
    vendor_lower = vendor.lower()
    if vendor_lower == "rockwell":
        return ROCKWELL_PROFILES
    elif vendor_lower == "siemens":
        return SIEMENS_PROFILES
    elif vendor_lower == "schneider":
        return SCHNEIDER_PROFILES
    else:
        return []


def get_profile_by_name(name: str) -> dict[str, Any] | None:
    """Find a profile by name."""
    for profile in get_all_vendor_profiles():
        if profile["name"] == name:
            return profile
    return None
