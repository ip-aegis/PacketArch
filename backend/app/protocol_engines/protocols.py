"""Protocol type definitions and mappings.

This module defines the canonical protocol identifiers and provides
mappings between protocol names and their identity keys. It serves as
the single source of truth for protocol support declarations.

The `supported_protocols` field in fingerprints is the authoritative
declaration of what protocols a device supports. Discovery and CVE
derivation should be gated by this field.
"""

from enum import Enum
from typing import Any


class ProtocolType(str, Enum):
    """Canonical protocol identifiers - Single Source of Truth.

    These are the valid values for the `supported_protocols` field
    in vendor fingerprints.
    """

    MODBUS = "modbus"
    ETHERNET_IP = "ethernet_ip"
    CIP = "cip"
    PROFINET = "profinet"
    PROFISAFE = "profisafe"
    S7COMM = "s7comm"
    S7COMM_PLUS = "s7comm_plus"
    BACNET = "bacnet"
    SNMP = "snmp"
    OPC_UA = "opc_ua"
    DNP3 = "dnp3"
    IEC104 = "iec104"


# Protocol to identity key mapping
# Maps protocol names to their corresponding fingerprint identity keys
PROTOCOL_TO_IDENTITY_KEY: dict[str, str] = {
    "modbus": "modbus_identity",
    "modbus_tcp": "modbus_identity",  # Alias used by scenario templates
    "ethernet_ip": "ethernet_ip_identity",
    "enip": "ethernet_ip_identity",  # Alias used by learned patterns
    "cip": "cip_identity_object",
    "profinet": "profinet_identity",
    "profisafe": "profinet_identity",  # PROFIsafe uses PROFINET identity
    "s7comm": "s7_identity",
    "s7comm_plus": "s7_identity",  # S7comm+ uses same identity structure
    "s7": "s7_identity",  # Alias used by learned patterns
    "bacnet": "bacnet_identity",
    "bacnet_ip": "bacnet_identity",  # Alias used by learned patterns
    "snmp": "snmp_identity",
    "opc_ua": "opc_ua_identity",
    "dnp3": "dnp3_identity",
    "iec104": "iec104_identity",
}

# Identity key to protocol(s) mapping (reverse lookup)
IDENTITY_KEY_TO_PROTOCOLS: dict[str, list[str]] = {
    "modbus_identity": ["modbus"],
    "ethernet_ip_identity": ["ethernet_ip"],
    "cip_identity_object": ["cip", "ethernet_ip"],
    "profinet_identity": ["profinet", "profisafe"],
    "s7_identity": ["s7comm", "s7comm_plus"],
    "bacnet_identity": ["bacnet"],
    "snmp_identity": ["snmp"],
    "opc_ua_identity": ["opc_ua"],
    "dnp3_identity": ["dnp3"],
    "iec104_identity": ["iec104"],
}

# Runtime engine alias map.
#
# Variant protocols (e.g. PROFIsafe, S7comm-Plus, CIP Safety) are wire-format
# variants of a parent protocol that share the same engine.  This map lets
# scenario flows reference the variant by name while the runtime resolves to
# the engine that actually knows how to emit packets.
#
# Values MUST be valid `app.protocol_engines.types.ProtocolType` values, since
# this map is consumed at the boundary where flow specs become FlowContexts
# (see `traffic_generator/tasks.py`).  Without this map, variant protocols
# raise ValueError on `ProtocolType("s7comm_plus")` and the entire flow is
# silently dropped.
PROTOCOL_ALIASES: dict[str, str] = {
    "s7comm_plus": "s7comm",
    "profisafe":   "profinet",
    "cip_safety":  "ethernet_ip",
    "modbus":      "modbus_tcp",
    "enip":        "ethernet_ip",
    "bacnet_ip":   "bacnet",
}


def resolve_protocol(name: str) -> str:
    """Return the engine-level protocol name for a (possibly variant) protocol string.

    Variant protocols (s7comm_plus, profisafe, cip_safety, ...) are mapped
    to their parent protocol whose engine actually emits packets.  Unknown
    protocol names are returned unchanged so the caller can decide what to
    do (typically: try `ProtocolType(name)` and warn on ValueError).
    """
    return PROTOCOL_ALIASES.get(name, name)

# Vendor-protocol affinities (for validation warnings)
# Maps vendor names to their typical/expected protocols
VENDOR_PROTOCOL_AFFINITIES: dict[str, list[str]] = {
    "siemens": ["profinet", "profisafe", "s7comm", "s7comm_plus", "modbus", "snmp"],
    "rockwell": ["ethernet_ip", "cip", "modbus"],
    "allen-bradley": ["ethernet_ip", "cip", "modbus"],
    "schneider": ["modbus", "ethernet_ip"],
    "schneider electric": ["modbus", "ethernet_ip"],
    "ge": ["modbus", "ethernet_ip", "opc_ua"],
    "honeywell": ["modbus", "bacnet", "snmp"],
    "johnson controls": ["bacnet", "snmp"],
    "trane": ["bacnet", "snmp"],
    "carrier": ["bacnet", "snmp"],
    "sel": ["modbus", "dnp3", "iec104"],
    "econolite": ["snmp"],
    "abb": ["modbus", "profinet", "ethernet_ip"],
    "emerson": ["modbus", "opc_ua"],
    "sick": ["ethernet_ip", "modbus"],
}


def get_identity_key_for_protocol(protocol: str) -> str | None:
    """Get the fingerprint identity key for a protocol.

    Args:
        protocol: Protocol name (e.g., "modbus", "ethernet_ip")

    Returns:
        Identity key (e.g., "modbus_identity") or None if not found
    """
    return PROTOCOL_TO_IDENTITY_KEY.get(protocol.lower())


def get_protocols_for_identity_key(identity_key: str) -> list[str]:
    """Get the protocols that use a given identity key.

    Args:
        identity_key: Identity key (e.g., "modbus_identity")

    Returns:
        List of protocol names that use this identity key
    """
    return IDENTITY_KEY_TO_PROTOCOLS.get(identity_key, [])


def get_supported_protocols(fingerprint: dict[str, Any]) -> list[str]:
    """Get supported protocols from a fingerprint with backward compatibility.

    If the fingerprint has an explicit `supported_protocols` field, that is
    returned as the authoritative list. Otherwise, protocols are inferred
    from the presence of identity keys for backward compatibility.

    Args:
        fingerprint: Vendor fingerprint dictionary

    Returns:
        List of protocol names the device supports
    """
    # Explicit declaration is authoritative
    if "supported_protocols" in fingerprint:
        return fingerprint["supported_protocols"]

    # Fallback: infer from identity existence (backward compatibility)
    inferred: list[str] = []
    for protocol, identity_key in PROTOCOL_TO_IDENTITY_KEY.items():
        # Skip duplicates (profisafe/profinet, s7comm/s7comm_plus share keys)
        if protocol in ("profisafe", "s7comm_plus"):
            continue

        identity = fingerprint.get(identity_key)
        if identity and isinstance(identity, dict):
            # Check for explicit None values (means explicitly disabled)
            if identity_key in fingerprint and fingerprint[identity_key] is None:
                continue
            inferred.append(protocol)

    # Also check for s7_identity in protocol_quirks (Siemens pattern)
    if "protocol_quirks" in fingerprint:
        quirks = fingerprint.get("protocol_quirks", {})
        if quirks.get("s7_identity") and "s7comm" not in inferred:
            inferred.append("s7comm")

    return inferred


def supports_protocol(fingerprint: dict[str, Any], protocol: str) -> bool:
    """Check if a fingerprint supports a specific protocol.

    Args:
        fingerprint: Vendor fingerprint dictionary
        protocol: Protocol name to check

    Returns:
        True if the device supports the protocol
    """
    supported = get_supported_protocols(fingerprint)
    return protocol.lower() in [p.lower() for p in supported]


def get_expected_protocols_for_vendor(vendor: str) -> list[str]:
    """Get the typical protocols for a vendor (for validation).

    Args:
        vendor: Vendor name

    Returns:
        List of protocols typically used by this vendor
    """
    vendor_lower = vendor.lower()
    return VENDOR_PROTOCOL_AFFINITIES.get(vendor_lower, [])


def validate_protocol_vendor_affinity(
    vendor: str,
    supported_protocols: list[str],
) -> list[str]:
    """Validate that protocols make sense for the vendor.

    Returns warning messages for unusual protocol/vendor combinations.

    Args:
        vendor: Vendor name
        supported_protocols: List of declared supported protocols

    Returns:
        List of warning messages (empty if no issues)
    """
    warnings: list[str] = []
    vendor_lower = vendor.lower()

    # Siemens should not use EtherNet/IP (except rare cases)
    if "siemens" in vendor_lower:
        if "ethernet_ip" in supported_protocols:
            warnings.append(
                "Siemens devices typically use PROFINET/S7comm, not EtherNet/IP. "
                "Verify this is intentional."
            )

    # Rockwell should not use PROFINET
    if "rockwell" in vendor_lower or "allen-bradley" in vendor_lower:
        if "profinet" in supported_protocols:
            warnings.append(
                "Rockwell/Allen-Bradley devices typically use EtherNet/IP, not PROFINET. "
                "Verify this is intentional."
            )

    # BMS vendors should typically have BACnet
    bms_vendors = ["johnson controls", "trane", "carrier", "tridium"]
    if any(v in vendor_lower for v in bms_vendors):
        if "bacnet" not in supported_protocols and "snmp" not in supported_protocols:
            warnings.append(
                f"BMS vendor '{vendor}' typically supports BACnet or SNMP."
            )

    # Transportation/ITS vendors should typically have SNMP
    its_vendors = ["econolite", "wavetronix", "mccain"]
    if any(v in vendor_lower for v in its_vendors):
        if "snmp" not in supported_protocols:
            warnings.append(
                f"ITS vendor '{vendor}' typically supports SNMP/NTCIP."
            )

    return warnings
