# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Natural language parser for extracting device counts and scenario parameters.

This module provides utilities for parsing natural language descriptions
to extract device counts, types, and other scenario configuration parameters.
"""

import re
from typing import Any

# Word to number mapping for common numeric words
WORD_TO_NUM = {
    "zero": 0,
    "one": 1,
    "a": 1,
    "an": 1,
    "single": 1,
    "two": 2,
    "couple": 2,
    "three": 3,
    "few": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "dozen": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty-one": 21,
    "twenty-two": 22,
    "twenty-three": 23,
    "twenty-four": 24,
    "twenty-five": 25,
    "twenty-six": 26,
    "twenty-seven": 27,
    "twenty-eight": 28,
    "twenty-nine": 29,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "hundred": 100,
    "several": 4,
    "many": 8,
    "multiple": 3,
    "some": 3,
}

# Device type synonyms mapping to canonical types
DEVICE_TYPE_SYNONYMS = {
    # PLCs
    "plc": "plc",
    "plcs": "plc",
    "controller": "plc",
    "controllers": "plc",
    "programmable logic controller": "plc",
    "programmable logic controllers": "plc",
    # HMIs
    "hmi": "hmi",
    "hmis": "hmi",
    "human machine interface": "hmi",
    "human machine interfaces": "hmi",
    "operator panel": "hmi",
    "operator panels": "hmi",
    "touch panel": "hmi",
    "touch panels": "hmi",
    # Sensors
    "sensor": "sensor",
    "sensors": "sensor",
    # VFDs
    "vfd": "vfd",
    "vfds": "vfd",
    "drive": "vfd",
    "drives": "vfd",
    "variable frequency drive": "vfd",
    "variable frequency drives": "vfd",
    "motor drive": "vfd",
    "motor drives": "vfd",
    # RTUs
    "rtu": "rtu",
    "rtus": "rtu",
    "remote terminal unit": "rtu",
    "remote terminal units": "rtu",
    # I/O modules
    "io": "io",
    "i/o": "io",
    "io module": "io",
    "io modules": "io",
    "i/o module": "io",
    "i/o modules": "io",
    "remote io": "io",
    "remote i/o": "io",
    # Generic devices
    "device": "device",
    "devices": "device",
    # Servers
    "server": "server",
    "servers": "server",
    "historian": "historian",
    "historians": "historian",
    # Robots
    "robot": "robot",
    "robots": "robot",
    "robotic arm": "robot",
    "robotic arms": "robot",
}

# Build regex patterns dynamically
DEVICE_TYPES = list(set(DEVICE_TYPE_SYNONYMS.keys()))
WORD_NUMS = "|".join(re.escape(w) for w in WORD_TO_NUM.keys())


def _parse_number(text: str) -> int | None:
    """Parse a number from text (either digit or word form).

    Args:
        text: Text that might be a number

    Returns:
        Integer value or None if not parseable
    """
    text = text.strip().lower()

    # Try direct integer parsing
    try:
        return int(text)
    except ValueError:
        pass

    # Try word mapping
    if text in WORD_TO_NUM:
        return WORD_TO_NUM[text]

    # Try compound numbers like "twenty five" or "twenty-five"
    text_normalized = text.replace("-", " ").replace("  ", " ")
    parts = text_normalized.split()
    if len(parts) == 2:
        tens = WORD_TO_NUM.get(parts[0], 0)
        ones = WORD_TO_NUM.get(parts[1], 0)
        if tens >= 20 and ones < 10:
            return tens + ones

    return None


def extract_device_counts(description: str) -> dict[str, Any]:
    """Extract device type -> count mapping from natural language description.

    Parses descriptions like:
    - "5 PLCs and 2 HMIs"
    - "twenty-five devices"
    - "a dozen sensors"
    - "5-10 VFDs" (uses lower bound)
    - "several controllers"

    Args:
        description: Natural language description of a scenario

    Returns:
        Dictionary with:
        - Device type to count mappings (e.g., {"plc": 5, "hmi": 2})
        - "total_requested": Total explicit count requested
        - "total_max_requested": Max total if range specified
        - "has_explicit_total": Whether user specified a total device count
    """
    description_lower = description.lower()
    result: dict[str, Any] = {
        "total_requested": 0,
        "total_max_requested": 0,
        "has_explicit_total": False,
        "device_counts": {},
    }

    # Pattern 1: "X devices" total count (captures explicit total)
    total_pattern = rf"(?:(?:no more than|up to|at most|maximum|max)\s+)?(\d+|{WORD_NUMS})\s+(?:total\s+)?devices?"
    total_match = re.search(total_pattern, description_lower)
    if total_match:
        count = _parse_number(total_match.group(1))
        if count:
            result["total_requested"] = count
            result["total_max_requested"] = count
            result["has_explicit_total"] = True

    # Pattern 2: "no more than X devices" - explicit max
    max_pattern = rf"no more than\s+(\d+|{WORD_NUMS})\s+devices?"
    max_match = re.search(max_pattern, description_lower)
    if max_match:
        count = _parse_number(max_match.group(1))
        if count:
            result["total_requested"] = count
            result["total_max_requested"] = count
            result["has_explicit_total"] = True

    # Pattern 3: Specific device type counts
    # Build pattern for each device type
    for device_type in DEVICE_TYPES:
        # Pattern: "5 PLCs" or "five PLCs"
        pattern1 = rf"(\d+|{WORD_NUMS})\s*(?:x\s+)?{re.escape(device_type)}"
        # Pattern: "PLCs: 5" or "PLC (5)"
        pattern2 = rf"{re.escape(device_type)}[:\s]+\(?\s*(\d+|{WORD_NUMS})\s*\)?"
        # Pattern: range "5-10 PLCs"
        pattern3 = rf"(\d+)\s*[-–]\s*(\d+)\s*{re.escape(device_type)}"

        # Try range pattern first
        range_match = re.search(pattern3, description_lower)
        if range_match:
            min_count = int(range_match.group(1))
            max_count = int(range_match.group(2))
            canonical_type = DEVICE_TYPE_SYNONYMS.get(device_type, device_type)
            # Use lower bound for actual count
            result["device_counts"][canonical_type] = result["device_counts"].get(canonical_type, 0) + min_count
            continue

        # Try standard patterns
        for pattern in [pattern1, pattern2]:
            match = re.search(pattern, description_lower)
            if match:
                count = _parse_number(match.group(1))
                if count:
                    canonical_type = DEVICE_TYPE_SYNONYMS.get(device_type, device_type)
                    # Add to existing count (might have multiple mentions)
                    result["device_counts"][canonical_type] = result["device_counts"].get(canonical_type, 0) + count
                break

    # Calculate implicit total from device counts if no explicit total
    if not result["has_explicit_total"] and result["device_counts"]:
        result["total_requested"] = sum(result["device_counts"].values())
        result["total_max_requested"] = result["total_requested"]

    return result


def format_device_counts_for_prompt(counts: dict[str, Any]) -> str:
    """Format extracted device counts for inclusion in AI prompt.

    Args:
        counts: Result from extract_device_counts()

    Returns:
        Human-readable summary string
    """
    lines = []

    if counts["has_explicit_total"]:
        lines.append(f"Total devices requested: {counts['total_requested']} (HARD LIMIT)")
    elif counts["total_requested"] > 0:
        lines.append(f"Total devices implied: {counts['total_requested']}")

    if counts["device_counts"]:
        device_summary = ", ".join(
            f"{count} {dtype}(s)" for dtype, count in counts["device_counts"].items()
        )
        lines.append(f"Specific counts: {device_summary}")

    if not lines:
        lines.append("No specific device count detected")

    return "\n".join(lines)


def get_device_limit_warning(counts: dict[str, Any], max_devices: int = 100) -> str | None:
    """Generate a warning if requested count exceeds limit.

    Args:
        counts: Result from extract_device_counts()
        max_devices: Maximum allowed devices

    Returns:
        Warning string or None if under limit
    """
    requested = counts["total_requested"]
    if requested > max_devices:
        return (
            f"WARNING: User requested {requested} devices but maximum is {max_devices}. "
            f"Create at most {max_devices} devices."
        )
    return None
