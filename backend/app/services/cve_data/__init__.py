"""CVE data for ICS/OT vulnerabilities.

This module provides curated CVE vulnerability data for major ICS vendors
that can be used to generate protocol responses with vulnerable firmware
versions detectable by security scanners like Cisco Cyber Vision.
"""

from app.services.cve_data.rockwell_cves import ROCKWELL_CVES
from app.services.cve_data.siemens_cves import SIEMENS_CVES
from app.services.cve_data.schneider_cves import SCHNEIDER_CVES
from app.services.cve_data.honeywell_cves import HONEYWELL_CVES
from app.services.cve_data.ge_emerson_cves import GE_EMERSON_CVES
from app.services.cve_data.abb_cves import ABB_CVES

# Combined CVE data from all vendors
ALL_CVES: list[dict] = [
    *ROCKWELL_CVES,
    *SIEMENS_CVES,
    *SCHNEIDER_CVES,
    *HONEYWELL_CVES,
    *GE_EMERSON_CVES,
    *ABB_CVES,
]

# Index by CVE ID for quick lookup
CVE_BY_ID: dict[str, dict] = {cve["cve_id"]: cve for cve in ALL_CVES}

# Index by vendor
CVES_BY_VENDOR: dict[str, list[dict]] = {
    "Rockwell": ROCKWELL_CVES,
    "Siemens": SIEMENS_CVES,
    "Schneider": SCHNEIDER_CVES,
    "Honeywell": HONEYWELL_CVES,
    "GE": GE_EMERSON_CVES,
    "ABB": ABB_CVES,
}


def get_cve(cve_id: str) -> dict | None:
    """Get CVE data by ID.

    Args:
        cve_id: CVE identifier (e.g., "CVE-2022-1159")

    Returns:
        CVE data dictionary or None if not found
    """
    return CVE_BY_ID.get(cve_id)


def get_cves_for_vendor(vendor: str) -> list[dict]:
    """Get all CVEs for a specific vendor (case-insensitive).

    Args:
        vendor: Vendor name (Rockwell, Siemens, Schneider) - case-insensitive

    Returns:
        List of CVE data dictionaries
    """
    # Normalize to title case for case-insensitive lookup
    normalized = vendor.title() if vendor else ""
    return CVES_BY_VENDOR.get(normalized, [])


def get_cves_for_product_family(vendor: str, product_family: str) -> list[dict]:
    """Get CVEs affecting a specific product family.

    Args:
        vendor: Vendor name
        product_family: Product family name (e.g., "ControlLogix", "S7-1500")

    Returns:
        List of matching CVE data dictionaries
    """
    vendor_cves = get_cves_for_vendor(vendor)
    return [
        cve for cve in vendor_cves
        if cve["product_family"].lower() == product_family.lower()
    ]


def get_critical_cves() -> list[dict]:
    """Get all critical severity CVEs.

    Returns:
        List of critical CVE data dictionaries
    """
    return [cve for cve in ALL_CVES if cve["severity"] == "critical"]


__all__ = [
    "ALL_CVES",
    "CVE_BY_ID",
    "CVES_BY_VENDOR",
    "ROCKWELL_CVES",
    "SIEMENS_CVES",
    "SCHNEIDER_CVES",
    "HONEYWELL_CVES",
    "GE_EMERSON_CVES",
    "ABB_CVES",
    "get_cve",
    "get_cves_for_vendor",
    "get_cves_for_product_family",
    "get_critical_cves",
]
