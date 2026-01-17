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
from app.services.cve_data.transportation_cves import TRANSPORTATION_CVES
from app.services.cve_data.building_automation_cves import BUILDING_AUTOMATION_CVES
from app.services.cve_data.energy_cves import ENERGY_CVES
from app.services.cve_data.oil_gas_cves import OIL_GAS_CVES

# Combined CVE data from all vendors
ALL_CVES: list[dict] = [
    *ROCKWELL_CVES,
    *SIEMENS_CVES,
    *SCHNEIDER_CVES,
    *HONEYWELL_CVES,
    *GE_EMERSON_CVES,
    *ABB_CVES,
    *TRANSPORTATION_CVES,
    *BUILDING_AUTOMATION_CVES,
    *ENERGY_CVES,
    *OIL_GAS_CVES,
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
    # Transportation vendors
    "Daktronics": [cve for cve in TRANSPORTATION_CVES if cve["vendor"] == "Daktronics"],
    "Kapsch": [cve for cve in TRANSPORTATION_CVES if cve["vendor"] == "Kapsch"],
    "Econolite": [cve for cve in TRANSPORTATION_CVES if cve["vendor"] == "Econolite"],
    "Wavetronix": [cve for cve in TRANSPORTATION_CVES if cve["vendor"] == "Wavetronix"],
    "Axis": [cve for cve in TRANSPORTATION_CVES if cve["vendor"] == "Axis"],
    "Q-Free": [cve for cve in TRANSPORTATION_CVES if cve["vendor"] == "Q-Free"],
    "Pelco": [cve for cve in TRANSPORTATION_CVES if cve["vendor"] == "Pelco"],
    "FLIR": [cve for cve in TRANSPORTATION_CVES if cve["vendor"] == "FLIR"],
    "Hikvision": [cve for cve in TRANSPORTATION_CVES if cve["vendor"] == "Hikvision"],
    # Building Automation / BMS vendors
    "Johnson Controls": [cve for cve in BUILDING_AUTOMATION_CVES if cve["vendor"] == "Johnson Controls"],
    "Trane": [cve for cve in BUILDING_AUTOMATION_CVES if cve["vendor"] == "Trane"],
    "Carrier": [cve for cve in BUILDING_AUTOMATION_CVES if cve["vendor"] == "Carrier"],
    "Delta Controls": [cve for cve in BUILDING_AUTOMATION_CVES if cve["vendor"] == "Delta Controls"],
    "Distech Controls": [cve for cve in BUILDING_AUTOMATION_CVES if cve["vendor"] == "Distech Controls"],
    "Automated Logic": [cve for cve in BUILDING_AUTOMATION_CVES if cve["vendor"] == "Automated Logic"],
    # Energy / Protection Relay vendors
    "SEL": [cve for cve in ENERGY_CVES if cve["vendor"] == "SEL"],
    # Oil & Gas / Process Industry vendors
    "Yokogawa": [cve for cve in OIL_GAS_CVES if cve["vendor"] == "Yokogawa"],
    "Emerson": [cve for cve in OIL_GAS_CVES if cve["vendor"] == "Emerson"],
    "Endress+Hauser": [cve for cve in OIL_GAS_CVES if cve["vendor"] == "Endress+Hauser"],
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
    "TRANSPORTATION_CVES",
    "BUILDING_AUTOMATION_CVES",
    "ENERGY_CVES",
    "OIL_GAS_CVES",
    "get_cve",
    "get_cves_for_vendor",
    "get_cves_for_product_family",
    "get_critical_cves",
]
