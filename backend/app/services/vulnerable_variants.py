"""Vulnerable fingerprint variants service.

This module provides functions to generate VulnerableFingerprintVariant
records from CVE data, enabling devices to emit protocol identity
responses with vulnerable firmware versions.
"""

from typing import Any
import uuid

from app.services.cve_data import ALL_CVES, get_cve, get_cves_for_vendor


def get_all_vulnerable_variants() -> list[dict[str, Any]]:
    """Get all vulnerable fingerprint variants from CVE data.

    Returns:
        List of variant dictionaries ready for database seeding
    """
    variants = []

    for cve in ALL_CVES:
        cve_variants = cve.get("vulnerable_variants", [])
        for variant in cve_variants:
            variants.append(_build_variant_dict(cve, variant))

    return variants


def get_vulnerable_variants_for_cve(cve_id: str) -> list[dict[str, Any]]:
    """Get vulnerable variants for a specific CVE.

    Args:
        cve_id: CVE identifier (e.g., "CVE-2022-1159")

    Returns:
        List of variant dictionaries for the CVE
    """
    cve = get_cve(cve_id)
    if not cve:
        return []

    return [
        _build_variant_dict(cve, variant)
        for variant in cve.get("vulnerable_variants", [])
    ]


def get_vulnerable_variants_for_vendor(vendor: str) -> list[dict[str, Any]]:
    """Get all vulnerable variants for a specific vendor.

    Args:
        vendor: Vendor name (Rockwell, Siemens, Schneider)

    Returns:
        List of variant dictionaries for the vendor
    """
    variants = []
    for cve in get_cves_for_vendor(vendor):
        for variant in cve.get("vulnerable_variants", []):
            variants.append(_build_variant_dict(cve, variant))
    return variants


def _build_variant_dict(cve: dict, variant: dict) -> dict[str, Any]:
    """Build a variant dictionary from CVE and variant data.

    Args:
        cve: CVE data dictionary
        variant: Variant data from CVE

    Returns:
        Variant dictionary ready for database insertion
    """
    return {
        "id": str(uuid.uuid4()),
        "cve_id": cve["cve_id"],
        "display_name": variant["display_name"],
        "firmware_version": variant["firmware_version"],
        "target_vendor": cve["vendor"],
        "target_product_family": cve["product_family"],
        "target_models": cve.get("affected_models"),
        "modbus_identity_override": variant.get("modbus_identity_override"),
        "ethernet_ip_identity_override": variant.get("ethernet_ip_identity_override"),
        "profinet_identity_override": variant.get("profinet_identity_override"),
        "s7_identity_override": variant.get("s7_identity_override"),
        "is_builtin": True,
        "is_active": True,
        # Metadata from CVE
        "_cve_severity": cve["severity"],
        "_cve_cvss_score": cve.get("cvss_score"),
        "_cve_title": cve["title"],
    }


def apply_vulnerability_to_fingerprint(
    base_fingerprint: dict[str, Any],
    variant: dict[str, Any],
) -> dict[str, Any]:
    """Apply vulnerability overrides to a base fingerprint.

    This creates a new fingerprint dictionary with vulnerable firmware
    versions injected into the protocol identity responses.

    Args:
        base_fingerprint: The base fingerprint dictionary
        variant: The vulnerable variant to apply

    Returns:
        New fingerprint dictionary with vulnerability applied
    """
    import copy

    # Create a deep copy to avoid modifying the original
    fingerprint = copy.deepcopy(base_fingerprint)

    # Apply Modbus identity overrides
    if variant.get("modbus_identity_override"):
        if fingerprint.get("modbus_identity"):
            fingerprint["modbus_identity"].update(variant["modbus_identity_override"])
        else:
            fingerprint["modbus_identity"] = variant["modbus_identity_override"]

    # Apply EtherNet/IP identity overrides
    if variant.get("ethernet_ip_identity_override"):
        if fingerprint.get("ethernet_ip_identity"):
            fingerprint["ethernet_ip_identity"].update(variant["ethernet_ip_identity_override"])
        else:
            fingerprint["ethernet_ip_identity"] = variant["ethernet_ip_identity_override"]

    # Apply PROFINET identity overrides
    if variant.get("profinet_identity_override"):
        if fingerprint.get("profinet_identity"):
            fingerprint["profinet_identity"].update(variant["profinet_identity_override"])
        else:
            fingerprint["profinet_identity"] = variant["profinet_identity_override"]

    # Apply S7 identity overrides (stored in protocol_quirks for S7 devices)
    if variant.get("s7_identity_override"):
        if not fingerprint.get("protocol_quirks"):
            fingerprint["protocol_quirks"] = {}
        if fingerprint["protocol_quirks"].get("s7_identity"):
            fingerprint["protocol_quirks"]["s7_identity"].update(variant["s7_identity_override"])
        else:
            fingerprint["protocol_quirks"]["s7_identity"] = variant["s7_identity_override"]

    # Update firmware version in the fingerprint
    fingerprint["firmware_version"] = variant["firmware_version"]

    # Add vulnerability metadata
    fingerprint["vulnerability_info"] = {
        "cve_id": variant["cve_id"],
        "display_name": variant["display_name"],
        "is_vulnerable": True,
    }

    return fingerprint


def get_variant_summary() -> dict[str, Any]:
    """Get a summary of available vulnerable variants.

    Returns:
        Summary dictionary with counts by vendor and severity
    """
    all_variants = get_all_vulnerable_variants()

    by_vendor = {}
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    unique_cves = set()

    for variant in all_variants:
        vendor = variant["target_vendor"]
        severity = variant.get("_cve_severity", "medium")

        if vendor not in by_vendor:
            by_vendor[vendor] = 0
        by_vendor[vendor] += 1

        by_severity[severity] = by_severity.get(severity, 0) + 1
        unique_cves.add(variant["cve_id"])

    return {
        "total_variants": len(all_variants),
        "unique_cves": len(unique_cves),
        "by_vendor": by_vendor,
        "by_severity": by_severity,
    }


__all__ = [
    "get_all_vulnerable_variants",
    "get_vulnerable_variants_for_cve",
    "get_vulnerable_variants_for_vendor",
    "apply_vulnerability_to_fingerprint",
    "get_variant_summary",
]
