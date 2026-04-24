# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Pattern normalization utilities for learned patterns.

Ensures consistent data formats across all extractors and consumers.
"""

from typing import Any


def normalize_function_code_distribution(
    function_codes: dict[Any, Any] | None,
) -> dict[str, Any]:
    """Normalize function code distribution to a standard format.

    The standard format is:
    {
        "<function_code>": {
            "name": "<human_readable_name>",
            "count": <int>,
            "frequency": <float 0-1>
        }
    }

    Input formats supported:
    - {fc: count, ...} - Simple count mapping
    - {fc: {"count": n}, ...} - Count dict mapping
    - {fc: {"frequency": f}, ...} - Frequency dict mapping
    - {fc: {"name": "...", "count": n, "frequency": f}, ...} - Full format

    Args:
        function_codes: Raw function code distribution from extractor

    Returns:
        Normalized function code distribution dict
    """
    if not function_codes:
        return {}

    normalized = {}
    total_count = 0

    # First pass: extract counts
    for fc, value in function_codes.items():
        fc_key = str(fc)

        if isinstance(value, (int, float)):
            # Simple count format: {fc: count}
            normalized[fc_key] = {
                "name": f"function_{fc}",
                "count": int(value),
                "frequency": 0.0,
            }
            total_count += int(value)

        elif isinstance(value, dict):
            count = value.get("count", 0)
            freq = value.get("frequency", 0.0)
            name = value.get("name", f"function_{fc}")

            # If only frequency is provided, estimate count
            if count == 0 and freq > 0:
                count = int(freq * 1000)  # Arbitrary scale for estimation

            normalized[fc_key] = {
                "name": name,
                "count": count,
                "frequency": freq,
            }
            total_count += count

    # Second pass: calculate frequencies if not provided
    if total_count > 0:
        for fc_key in normalized:
            if normalized[fc_key]["frequency"] == 0.0:
                normalized[fc_key]["frequency"] = (
                    normalized[fc_key]["count"] / total_count
                )

    return normalized


def extract_function_code_probabilities(
    function_codes: dict[Any, Any] | None,
) -> dict[int, float]:
    """Extract function code probabilities for sampling.

    Returns a simple {function_code: probability} mapping suitable
    for weighted random selection.

    Args:
        function_codes: Raw or normalized function code distribution

    Returns:
        Dict mapping int function codes to float probabilities
    """
    if not function_codes:
        return {}

    # First normalize the input
    normalized = normalize_function_code_distribution(function_codes)

    # Extract probabilities
    probabilities = {}
    for fc_str, data in normalized.items():
        try:
            fc_int = int(fc_str)
            freq = data.get("frequency", 0.0) if isinstance(data, dict) else 0.0
            if freq > 0:
                probabilities[fc_int] = freq
        except (ValueError, TypeError):
            continue

    # Ensure probabilities sum to 1
    total = sum(probabilities.values())
    if total > 0:
        probabilities = {fc: p / total for fc, p in probabilities.items()}

    return probabilities


def normalize_address_patterns(
    address_patterns: dict[Any, Any] | None,
) -> dict[str, Any]:
    """Normalize address/register patterns to a standard format.

    The standard format is:
    {
        "<region_name>": {
            "min_address": <int>,
            "max_address": <int>,
            "total_accesses": <int>,
            "unique_addresses": <int>,
            "hot_spots": [{"address": <int>, "access_count": <int>}, ...],
            "ranges": [{"start": <int>, "end": <int>, "size": <int>}, ...]
        }
    }

    Args:
        address_patterns: Raw address patterns from extractor

    Returns:
        Normalized address patterns dict
    """
    if not address_patterns:
        return {}

    normalized = {}

    for region, data in address_patterns.items():
        region_key = str(region)

        if isinstance(data, dict):
            normalized[region_key] = {
                "min_address": data.get("min_address", data.get("min", 0)),
                "max_address": data.get("max_address", data.get("max", 0)),
                "total_accesses": data.get("total_accesses", data.get("count", 0)),
                "unique_addresses": data.get("unique_addresses", 0),
                "hot_spots": data.get("hot_spots", []),
                "ranges": data.get("ranges", []),
            }
        elif isinstance(data, (list, tuple)):
            # List of address values
            addresses = [int(a) for a in data if isinstance(a, (int, float))]
            if addresses:
                normalized[region_key] = {
                    "min_address": min(addresses),
                    "max_address": max(addresses),
                    "total_accesses": len(addresses),
                    "unique_addresses": len(set(addresses)),
                    "hot_spots": [],
                    "ranges": [{"start": min(addresses), "end": max(addresses), "size": max(addresses) - min(addresses) + 1}],
                }

    return normalized


def normalize_exception_patterns(
    exception_patterns: dict[Any, Any] | None,
) -> dict[str, Any]:
    """Normalize exception/error patterns to a standard format.

    The standard format is:
    {
        "<error_code>": {
            "name": "<human_readable_name>",
            "count": <int>,
            "frequency": <float 0-1>
        }
    }

    Args:
        exception_patterns: Raw exception patterns from extractor

    Returns:
        Normalized exception patterns dict
    """
    if not exception_patterns:
        return {}

    normalized = {}
    total_count = 0

    # First pass: extract counts
    for err_code, value in exception_patterns.items():
        err_key = str(err_code)

        if isinstance(value, (int, float)):
            normalized[err_key] = {
                "name": f"error_{err_code}",
                "count": int(value),
                "frequency": 0.0,
            }
            total_count += int(value)

        elif isinstance(value, dict):
            count = value.get("count", 0)
            freq = value.get("frequency", 0.0)
            name = value.get("name", f"error_{err_code}")

            normalized[err_key] = {
                "name": name,
                "count": count,
                "frequency": freq,
            }
            total_count += count

    # Second pass: calculate frequencies
    if total_count > 0:
        for err_key in normalized:
            if normalized[err_key]["frequency"] == 0.0:
                normalized[err_key]["frequency"] = (
                    normalized[err_key]["count"] / total_count
                )

    return normalized


def normalize_protocol_pattern(pattern_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize all fields in a protocol pattern to standard formats.

    Args:
        pattern_data: Raw protocol pattern dict from extractor

    Returns:
        Normalized protocol pattern dict
    """
    normalized = dict(pattern_data)  # Copy

    # Normalize function codes
    if "function_codes" in normalized:
        normalized["function_codes"] = normalize_function_code_distribution(
            normalized["function_codes"]
        )

    # Normalize address patterns
    if "address_patterns" in normalized:
        normalized["address_patterns"] = normalize_address_patterns(
            normalized["address_patterns"]
        )

    # Normalize exception patterns
    if "exception_patterns" in normalized:
        normalized["exception_patterns"] = normalize_exception_patterns(
            normalized["exception_patterns"]
        )

    return normalized


def normalize_timing_distribution(
    timing_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Normalize timing distribution data.

    The standard format is:
    {
        "mean_ms": <float>,
        "min_ms": <float>,
        "max_ms": <float>,
        "std_ms": <float>,
        "samples": [<float>, ...],  # Optional
        "distribution_type": "<gaussian|lognormal|...>"
    }

    Args:
        timing_data: Raw timing data from extractor

    Returns:
        Normalized timing distribution dict
    """
    if not timing_data:
        return {}

    normalized = {}

    # Map common field names
    field_mappings = {
        "mean": "mean_ms",
        "mean_value": "mean_ms",
        "avg": "mean_ms",
        "average": "mean_ms",
        "min": "min_ms",
        "min_value": "min_ms",
        "max": "max_ms",
        "max_value": "max_ms",
        "std": "std_ms",
        "std_dev": "std_ms",
        "stddev": "std_ms",
        "standard_deviation": "std_ms",
    }

    for raw_key, normalized_key in field_mappings.items():
        if raw_key in timing_data:
            normalized[normalized_key] = timing_data[raw_key]

    # Copy through already-normalized keys
    for key in ["mean_ms", "min_ms", "max_ms", "std_ms", "samples", "distribution_type"]:
        if key in timing_data:
            normalized[key] = timing_data[key]

    return normalized
