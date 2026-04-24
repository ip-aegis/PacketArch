# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Helper functions for device template instance generation."""

import random
import re
import string
from typing import Any


def generate_serial_number(format_pattern: str, existing_serials: set[str] | None = None) -> str:
    """Generate a unique serial number based on format pattern.

    Supported placeholders:
    - {NHEX}: N random hex characters (e.g., {8HEX})
    - {NNUM}: N random digits (e.g., {6NUM})
    - {NALPHA}: N random uppercase letters (e.g., {4ALPHA})
    - {NALPHANUM}: N random alphanumeric (e.g., {10ALPHANUM})
    """
    existing = existing_serials or set()
    max_attempts = 100

    for _ in range(max_attempts):
        result = format_pattern

        # Process hex placeholders
        for match in re.finditer(r'\{(\d+)HEX\}', format_pattern):
            n = int(match.group(1))
            hex_str = ''.join(random.choices('0123456789ABCDEF', k=n))
            result = result.replace(match.group(0), hex_str, 1)

        # Process numeric placeholders
        for match in re.finditer(r'\{(\d+)NUM\}', format_pattern):
            n = int(match.group(1))
            num_str = ''.join(random.choices('0123456789', k=n))
            result = result.replace(match.group(0), num_str, 1)

        # Process alpha placeholders
        for match in re.finditer(r'\{(\d+)ALPHA\}', format_pattern):
            n = int(match.group(1))
            alpha_str = ''.join(random.choices(string.ascii_uppercase, k=n))
            result = result.replace(match.group(0), alpha_str, 1)

        # Process alphanumeric placeholders
        for match in re.finditer(r'\{(\d+)ALPHANUM\}', format_pattern):
            n = int(match.group(1))
            alphanum_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))
            result = result.replace(match.group(0), alphanum_str, 1)

        if result not in existing:
            return result

    raise ValueError(f"Could not generate unique serial after {max_attempts} attempts")


def generate_station_name(
    pattern: str,
    role: str = "device",
    vendor_short: str = "DEV",
    model_short: str = "001",
    sequence: int = 1,
    location: str | None = None,
    existing_names: set[str] | None = None,
) -> str:
    """Generate a unique station name based on pattern.

    Supported placeholders:
    - {role}: Device role (plc, hmi, drive, etc.)
    - {vendor_short}: Abbreviated vendor name
    - {model_short}: Abbreviated model name
    - {seq}: Sequence number (zero-padded to 3 digits)
    - {seq2}: Sequence number (zero-padded to 2 digits)
    - {location}: User-provided location or "loc"
    """
    existing = existing_names or set()

    result = pattern.lower()
    result = result.replace("{role}", role.lower())
    result = result.replace("{vendor_short}", vendor_short.lower())
    result = result.replace("{model_short}", model_short.lower())
    result = result.replace("{seq}", f"{sequence:03d}")
    result = result.replace("{seq2}", f"{sequence:02d}")
    result = result.replace("{location}", (location or "loc").lower())

    # Ensure uniqueness by appending sequence if needed
    base_name = result
    counter = sequence
    while result in existing:
        counter += 1
        result = f"{base_name}-{counter}"

    return result


def merge_identity(
    base_identity: dict[str, Any],
    firmware_overrides: dict[str, Any],
    instance_values: dict[str, Any],
) -> dict[str, Any]:
    """Merge base identity with firmware and instance overrides.

    Priority (highest to lowest):
    1. Instance values (serial_number, station_name)
    2. Firmware overrides (version-specific fields)
    3. Base identity (static template values)
    """
    result = dict(base_identity) if base_identity else {}

    # Apply firmware overrides
    if firmware_overrides:
        result.update(firmware_overrides)

    # Apply instance values
    if instance_values:
        result.update(instance_values)

    return result
