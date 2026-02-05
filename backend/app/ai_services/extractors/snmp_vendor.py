"""SNMP-based vendor detection.

Extracts vendor identification from SNMP data:
- sysObjectID enterprise OID mapping
- sysDescr text pattern matching

This provides more accurate vendor identification than MAC OUI alone,
especially for OT devices that use embedded NICs from other manufacturers.
"""

import re
from typing import Any

# SNMP Enterprise OID to Vendor mapping
# Format: 1.3.6.1.4.1.{enterprise_number}...
# Reference: https://www.iana.org/assignments/enterprise-numbers/
ENTERPRISE_OID_VENDORS: dict[int, str] = {
    # Building Automation
    4399: "Johnson Controls",  # Johnson Controls, Inc.
    4194: "Trane",  # Trane Technologies
    4131: "Honeywell",  # Honeywell International Inc.
    17420: "Schneider Electric",  # Schneider Electric - Building Automation
    2699: "Carrier",  # Carrier Corporation
    3401: "Andover Controls",  # Andover Controls (now Schneider)
    17095: "Delta Controls",  # Delta Controls Inc.
    36849: "Distech Controls",  # Distech Controls Inc.
    8750: "Automated Logic",  # Automated Logic Corporation
    2904: "Cimetrics",  # Cimetrics Inc. (BACnet)

    # Industrial Automation - Major Vendors
    318: "ABB",  # ABB (Asea Brown Boveri)
    3755: "Siemens",  # Siemens AG
    4526: "Rockwell Automation",  # Rockwell Automation (Allen-Bradley)
    3833: "Schneider Electric",  # Schneider Electric SE
    2566: "Emerson",  # Emerson Electric Co.
    4491: "GE",  # General Electric Company
    8072: "Beckhoff",  # Beckhoff Automation GmbH
    19390: "Phoenix Contact",  # Phoenix Contact GmbH & Co. KG
    25506: "Wago",  # WAGO Kontakttechnik GmbH

    # Networking & Infrastructure
    9: "Cisco",  # Cisco Systems, Inc.
    11: "HP",  # Hewlett-Packard Company
    2636: "Juniper Networks",  # Juniper Networks, Inc.
    6486: "Alcatel-Lucent",  # Alcatel-Lucent
    207: "Allied Telesis",  # Allied Telesis, Inc.
    674: "Dell",  # Dell Inc.

    # Industrial Networking
    8691: "Moxa",  # Moxa Inc.
    10002: "Advantech",  # Advantech Co., Ltd.
    10297: "HMS Industrial Networks",  # HMS Industrial Networks AB

    # Traffic / ITS
    1206: "Econolite",  # Econolite Control Products
    24766: "McCain",  # McCain Inc.
    332: "Trafficware",  # Trafficware Group Inc.

    # Energy / Utilities
    3815: "SEL",  # Schweitzer Engineering Laboratories
    6574: "ABB Power",  # ABB Power T&D Company

    # Safety / Security
    10088: "Pilz",  # Pilz GmbH & Co. KG

    # Asian Vendors
    1083: "Mitsubishi Electric",  # Mitsubishi Electric Corporation
    1113: "Omron",  # Omron Corporation
    278: "Yokogawa",  # Yokogawa Electric Corporation
    2011: "Fuji Electric",  # Fuji Electric Co., Ltd.
}

# Patterns to extract vendor from sysDescr text
# Order matters - more specific patterns first
SYSDESCR_VENDOR_PATTERNS: list[tuple[str, str]] = [
    # Building Automation - Specific products first
    (r"Johnson\s*Controls", "Johnson Controls"),
    (r"Metasys", "Johnson Controls"),  # Johnson Controls product line
    (r"NAE\d+", "Johnson Controls"),  # Network Automation Engine
    (r"NCE\d+", "Johnson Controls"),  # Network Control Engine
    (r"FEC\d+", "Johnson Controls"),  # Field Equipment Controller
    (r"Trane\s", "Trane"),
    (r"Tracer\s*(SC|ES|Summit)", "Trane"),  # Trane product lines
    (r"Honeywell", "Honeywell"),
    (r"Niagara\s*(AX|4|N4)", "Tridium"),  # Tridium (Honeywell)
    (r"Delta\s*Controls", "Delta Controls"),
    (r"Distech\s*Controls", "Distech Controls"),
    (r"Automated\s*Logic", "Automated Logic"),
    (r"Carrier\s", "Carrier"),
    (r"i-Vu", "Carrier"),  # Carrier product line

    # Industrial Automation
    (r"Siemens", "Siemens"),
    (r"SIMATIC", "Siemens"),
    (r"SCALANCE", "Siemens"),
    (r"S7-\d+", "Siemens"),
    (r"Allen[-\s]?Bradley", "Rockwell Automation"),
    (r"Rockwell", "Rockwell Automation"),
    (r"ControlLogix", "Rockwell Automation"),
    (r"CompactLogix", "Rockwell Automation"),
    (r"Schneider\s*Electric", "Schneider Electric"),
    (r"Modicon", "Schneider Electric"),
    (r"Quantum", "Schneider Electric"),
    (r"M340", "Schneider Electric"),
    (r"ABB\s", "ABB"),
    (r"Emerson", "Emerson"),
    (r"DeltaV", "Emerson"),
    (r"GE\s*(Fanuc|Automation)", "GE"),
    (r"Phoenix\s*Contact", "Phoenix Contact"),
    (r"Beckhoff", "Beckhoff"),
    (r"WAGO", "WAGO"),

    # Traffic / ITS
    (r"Econolite", "Econolite"),
    (r"ASC[/\s]?3", "Econolite"),  # Econolite traffic controller
    (r"Cobalt", "Econolite"),  # Econolite product line
    (r"McCain", "McCain"),
    (r"Trafficware", "Trafficware"),
    (r"NTCIP", "Traffic Controller"),  # Generic ITS

    # Networking
    (r"Cisco\s*(IOS|Systems|Nexus)?", "Cisco"),
    (r"Juniper", "Juniper Networks"),
    (r"Moxa", "Moxa"),
    (r"Advantech", "Advantech"),

    # Asian Vendors
    (r"Mitsubishi\s*Electric", "Mitsubishi Electric"),
    (r"MELSEC", "Mitsubishi Electric"),
    (r"Omron", "Omron"),
    (r"Yokogawa", "Yokogawa"),
]


def extract_enterprise_oid(sys_object_id: str) -> int | None:
    """Extract enterprise number from sysObjectID.

    Args:
        sys_object_id: Full OID string (e.g., "1.3.6.1.4.1.4399.2.1.1")

    Returns:
        Enterprise number or None if not parseable
    """
    if not sys_object_id:
        return None

    # Standard prefix is 1.3.6.1.4.1 (iso.org.dod.internet.private.enterprises)
    parts = sys_object_id.split(".")

    # Need at least 7 parts: 1.3.6.1.4.1.{enterprise}
    if len(parts) >= 7:
        try:
            # Check for standard enterprise prefix
            if parts[:6] == ["1", "3", "6", "1", "4", "1"]:
                return int(parts[6])
        except (ValueError, IndexError):
            pass

    return None


def vendor_from_enterprise_oid(sys_object_id: str) -> str | None:
    """Get vendor name from sysObjectID enterprise number.

    Args:
        sys_object_id: Full OID string

    Returns:
        Vendor name or None if not found
    """
    enterprise = extract_enterprise_oid(sys_object_id)
    if enterprise:
        return ENTERPRISE_OID_VENDORS.get(enterprise)
    return None


def vendor_from_sysdescr(sys_descr: str) -> str | None:
    """Extract vendor name from sysDescr text using pattern matching.

    Args:
        sys_descr: SNMP sysDescr string

    Returns:
        Vendor name or None if not found
    """
    if not sys_descr:
        return None

    for pattern, vendor in SYSDESCR_VENDOR_PATTERNS:
        if re.search(pattern, sys_descr, re.IGNORECASE):
            return vendor

    return None


def extract_vendor_from_snmp(snmp_identity: dict[str, Any]) -> str | None:
    """Extract vendor from SNMP identity data.

    Prioritizes sysObjectID enterprise OID over sysDescr pattern matching,
    as enterprise OID is more authoritative.

    Args:
        snmp_identity: Dict with SNMP fields (sysDescr, sysObjectID, etc.)

    Returns:
        Vendor name or None if not determinable
    """
    if not snmp_identity:
        return None

    # Try sysObjectID first (more authoritative)
    sys_object_id = snmp_identity.get("sysObjectID") or snmp_identity.get("sys_object_id")
    if sys_object_id:
        vendor = vendor_from_enterprise_oid(sys_object_id)
        if vendor:
            return vendor

    # Fall back to sysDescr pattern matching
    sys_descr = snmp_identity.get("sysDescr") or snmp_identity.get("sys_descr")
    if sys_descr:
        vendor = vendor_from_sysdescr(sys_descr)
        if vendor:
            return vendor

    return None


def extract_model_from_snmp(snmp_identity: dict[str, Any]) -> dict[str, str | None]:
    """Extract model and firmware info from SNMP identity.

    Args:
        snmp_identity: Dict with SNMP fields

    Returns:
        Dict with model, firmware_version, and device_type if found
    """
    result: dict[str, str | None] = {
        "model": None,
        "firmware_version": None,
        "device_type": None,
    }

    sys_descr = snmp_identity.get("sysDescr") or snmp_identity.get("sys_descr") or ""

    # Johnson Controls Metasys pattern: "Johnson Controls Metasys NAE55 v12.0.3"
    match = re.search(r"(NAE|NCE|FEC|NIE|OAS)(\d+)\s+v?([\d.]+)?", sys_descr, re.IGNORECASE)
    if match:
        result["model"] = f"{match.group(1).upper()}{match.group(2)}"
        if match.group(3):
            result["firmware_version"] = match.group(3)
        result["device_type"] = "Building Controller"
        return result

    # Trane Tracer pattern: "Trane Tracer SC v5.2"
    match = re.search(r"Tracer\s*(SC|ES|Summit)\s*v?([\d.]+)?", sys_descr, re.IGNORECASE)
    if match:
        result["model"] = f"Tracer {match.group(1).upper()}"
        if match.group(2):
            result["firmware_version"] = match.group(2)
        result["device_type"] = "Building Controller"
        return result

    # Siemens pattern: "Siemens SIMATIC S7-1200 v4.5"
    match = re.search(r"S7-(\d+)\s*v?([\d.]+)?", sys_descr, re.IGNORECASE)
    if match:
        result["model"] = f"S7-{match.group(1)}"
        if match.group(2):
            result["firmware_version"] = match.group(2)
        result["device_type"] = "PLC"
        return result

    # Generic version pattern: extract version number after 'v' or 'version'
    match = re.search(r"(?:v|version)\s*([\d.]+)", sys_descr, re.IGNORECASE)
    if match:
        result["firmware_version"] = match.group(1)

    return result


def get_vendor_confidence(
    snmp_vendor: str | None,
    oui_vendor: str | None,
    snmp_identity: dict[str, Any] | None = None,
) -> tuple[str | None, float]:
    """Determine best vendor with confidence score.

    SNMP-derived vendor is preferred over OUI-derived vendor because:
    1. Enterprise OID is registered by the actual vendor
    2. sysDescr is set by the device itself
    3. MAC OUI may be from embedded NIC manufacturer, not device vendor

    Args:
        snmp_vendor: Vendor from SNMP data
        oui_vendor: Vendor from MAC OUI lookup
        snmp_identity: Full SNMP identity dict for additional context

    Returns:
        Tuple of (vendor_name, confidence) where confidence is 0.0-1.0
    """
    # SNMP enterprise OID - highest confidence
    if snmp_identity:
        sys_object_id = snmp_identity.get("sysObjectID") or snmp_identity.get("sys_object_id")
        if sys_object_id:
            oid_vendor = vendor_from_enterprise_oid(sys_object_id)
            if oid_vendor:
                return (oid_vendor, 0.95)

    # SNMP sysDescr pattern match - high confidence
    if snmp_vendor:
        return (snmp_vendor, 0.85)

    # MAC OUI - moderate confidence (may be NIC vendor, not device vendor)
    if oui_vendor:
        return (oui_vendor, 0.50)

    return (None, 0.0)
