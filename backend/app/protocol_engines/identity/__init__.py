"""Protocol Identity Builder Registry.

This module provides a registry for protocol-specific identity builders,
enabling a plugin architecture for device identification responses.

Each protocol engine that requires identity responses should use this registry
to get the appropriate builder rather than accessing FingerprintApplicator directly.

IMPORTANT: This is the single source of truth for:
1. Protocol identity building (vendor/model/firmware responses)
2. MAC address generation (via vendor_oui module)
3. Firmware version derivation

Usage:
    from app.protocol_engines.identity import get_builder, get_all_builders, generate_mac

    # Get a specific builder
    modbus_builder = get_builder("modbus")
    response = modbus_builder.build_identity_response(base_identity)

    # Get all registered builders
    all_builders = get_all_builders()

    # Generate MAC address
    mac = generate_mac(vendor="siemens", device_type="plc")

Adding a new protocol:
    1. Create a new builder module (e.g., myprotocol_builder.py)
    2. Subclass ProtocolIdentityBuilder
    3. Import and register in this file
"""

import logging
from typing import Any, Type

from .base import (
    FirmwareFields,
    IdentityResponse,
    ProtocolIdentityBuilder,
)

logger = logging.getLogger(__name__)

# Builder registry: protocol_name -> builder_class
_BUILDER_REGISTRY: dict[str, Type[ProtocolIdentityBuilder]] = {}

# Builder instance cache (lazily created)
_BUILDER_INSTANCES: dict[str, ProtocolIdentityBuilder] = {}


def register_builder(cls: Type[ProtocolIdentityBuilder]) -> Type[ProtocolIdentityBuilder]:
    """Decorator to register a protocol identity builder.

    Usage:
        @register_builder
        class ModbusIdentityBuilder(ProtocolIdentityBuilder):
            ...

    Args:
        cls: Builder class to register

    Returns:
        The same class (unchanged)
    """
    # Create an instance to get the protocol name
    instance = cls()
    protocol_name = instance.protocol_name

    if protocol_name in _BUILDER_REGISTRY:
        logger.warning(
            f"Overwriting existing builder for protocol '{protocol_name}': "
            f"{_BUILDER_REGISTRY[protocol_name].__name__} -> {cls.__name__}"
        )

    _BUILDER_REGISTRY[protocol_name] = cls
    logger.debug(f"Registered identity builder: {protocol_name} -> {cls.__name__}")

    return cls


def get_builder(protocol: str) -> ProtocolIdentityBuilder:
    """Get a builder instance for a protocol.

    Uses a cached instance for efficiency.

    Args:
        protocol: Protocol name (e.g., "modbus", "ethernet_ip")

    Returns:
        ProtocolIdentityBuilder instance

    Raises:
        KeyError: If no builder is registered for the protocol
    """
    if protocol not in _BUILDER_INSTANCES:
        if protocol not in _BUILDER_REGISTRY:
            available = ", ".join(sorted(_BUILDER_REGISTRY.keys()))
            raise KeyError(
                f"No identity builder registered for protocol '{protocol}'. "
                f"Available: {available}"
            )
        _BUILDER_INSTANCES[protocol] = _BUILDER_REGISTRY[protocol]()

    return _BUILDER_INSTANCES[protocol]


def get_builder_by_identity_key(identity_key: str) -> ProtocolIdentityBuilder | None:
    """Get a builder by its identity_key (e.g., 'modbus_identity').

    Args:
        identity_key: The key used in fingerprint dicts (e.g., 'modbus_identity')

    Returns:
        ProtocolIdentityBuilder instance or None if not found
    """
    for protocol in _BUILDER_REGISTRY:
        builder = get_builder(protocol)
        if builder.identity_key == identity_key:
            return builder
    return None


def get_all_builders() -> dict[str, ProtocolIdentityBuilder]:
    """Get all registered builder instances.

    Returns:
        Dictionary mapping protocol names to builder instances
    """
    # Ensure all instances are created
    for protocol in _BUILDER_REGISTRY:
        if protocol not in _BUILDER_INSTANCES:
            _BUILDER_INSTANCES[protocol] = _BUILDER_REGISTRY[protocol]()

    return dict(_BUILDER_INSTANCES)


def get_registered_protocols() -> list[str]:
    """Get list of all registered protocol names.

    Returns:
        List of protocol names
    """
    return list(_BUILDER_REGISTRY.keys())


def has_builder(protocol: str) -> bool:
    """Check if a builder is registered for a protocol.

    Args:
        protocol: Protocol name

    Returns:
        True if a builder is registered
    """
    return protocol in _BUILDER_REGISTRY


def build_identity_for_protocol(
    protocol: str,
    base_identity: dict[str, Any],
    vulnerability_override: dict[str, Any] | None = None,
    firmware_version: str | None = None,
    **kwargs: Any,
) -> IdentityResponse:
    """Convenience function to build an identity response for a protocol.

    Args:
        protocol: Protocol name
        base_identity: Base identity from vendor fingerprint
        vulnerability_override: Optional CVE-specific overrides
        firmware_version: Optional firmware version for derivation
        **kwargs: Protocol-specific arguments

    Returns:
        IdentityResponse with identity data
    """
    builder = get_builder(protocol)
    return builder.build_identity_response(
        base_identity=base_identity,
        vulnerability_override=vulnerability_override,
        firmware_version=firmware_version,
        **kwargs,
    )


def derive_firmware_fields_for_protocol(
    protocol: str,
    firmware_version: str,
    base_identity: dict[str, Any] | None = None,
) -> FirmwareFields:
    """Convenience function to derive firmware fields for a protocol.

    Args:
        protocol: Protocol name
        firmware_version: Firmware version string
        base_identity: Optional base identity for context

    Returns:
        FirmwareFields with protocol-specific fields
    """
    builder = get_builder(protocol)
    return builder.derive_firmware_fields(
        firmware_version=firmware_version,
        base_identity=base_identity,
    )


def derive_all_firmware_fields(
    firmware_version: str,
    base_identities: dict[str, dict[str, Any]] | None = None,
    protocols: list[str] | None = None,
) -> dict[str, FirmwareFields]:
    """Derive firmware fields for all (or specified) protocols.

    Args:
        firmware_version: Firmware version string
        base_identities: Optional dict mapping identity_key to base identity
        protocols: Optional list of protocols to derive for

    Returns:
        Dictionary mapping protocol names to FirmwareFields
    """
    target_protocols = protocols or list(_BUILDER_REGISTRY.keys())
    base_identities = base_identities or {}
    result = {}

    for protocol in target_protocols:
        if protocol not in _BUILDER_REGISTRY:
            continue

        builder = get_builder(protocol)
        base = base_identities.get(builder.identity_key, {})

        result[protocol] = builder.derive_firmware_fields(
            firmware_version=firmware_version,
            base_identity=base,
        )

    return result


# =============================================================================
# MAC Address Generation (centralized, delegates to vendor_oui)
# =============================================================================


def generate_mac(
    vendor: str | None = None,
    device_type: str | None = None,
    oui_patterns: list[str] | None = None,
) -> str:
    """Generate a MAC address using vendor-specific OUI prefix.

    This is the canonical MAC generation function. Use this instead of
    duplicating MAC generation logic elsewhere.

    Args:
        vendor: Vendor name (e.g., "siemens", "rockwell")
        device_type: Device type for fallback vendor selection (e.g., "plc", "hmi")
        oui_patterns: Optional list of OUI prefixes to choose from (for learned patterns)

    Returns:
        MAC address string in format "XX:XX:XX:XX:XX:XX"

    Example:
        >>> generate_mac(vendor="siemens")
        "00:0E:8C:AB:12:34"
        >>> generate_mac(oui_patterns=["00:1D:9C", "00:0E:8C"])
        "00:1D:9C:89:AB:CD"
    """
    import random

    from app.protocol_engines.vendor_oui import generate_mac_address as _vendor_oui_generate

    # If OUI patterns provided (e.g., from learned fingerprints), use those directly
    if oui_patterns:
        oui = random.choice(oui_patterns)
        # Generate the last 3 bytes randomly
        last_bytes = [random.randint(0, 255) for _ in range(3)]
        last_part = ":".join(f"{b:02x}" for b in last_bytes)
        return f"{oui}:{last_part}".upper()

    # Otherwise delegate to vendor_oui module
    return _vendor_oui_generate(vendor=vendor, device_type=device_type)


def generate_mac_from_fingerprint(
    fingerprint: dict[str, Any],
    fallback_vendor: str | None = None,
    fallback_device_type: str | None = None,
) -> str:
    """Generate a MAC address from a device fingerprint.

    Extracts OUI patterns or vendor info from a fingerprint dict and generates
    an appropriate MAC address.

    Args:
        fingerprint: Device fingerprint dict (may contain oui_patterns, inferred_vendor)
        fallback_vendor: Vendor to use if not in fingerprint
        fallback_device_type: Device type to use if no vendor info available

    Returns:
        MAC address string
    """
    # Try to get OUI patterns from fingerprint
    oui_patterns = fingerprint.get("oui_patterns", [])
    if oui_patterns:
        return generate_mac(oui_patterns=oui_patterns)

    # Try vendor from fingerprint
    vendor = fingerprint.get("inferred_vendor") or fingerprint.get("vendor") or fallback_vendor
    device_type = fingerprint.get("device_type") or fallback_device_type

    return generate_mac(vendor=vendor, device_type=device_type)


# Import and register all builders
# These imports trigger the @register_builder decorator

from .modbus_builder import ModbusIdentityBuilder
from .ethernet_ip_builder import EtherNetIPIdentityBuilder
from .profinet_builder import ProfinetIdentityBuilder
from .s7_builder import S7IdentityBuilder
from .snmp_builder import SNMPIdentityBuilder
from .bacnet_builder import BACnetIdentityBuilder
from .opc_ua_builder import OpcUaIdentityBuilder
from .dnp3_builder import DNP3IdentityBuilder
from .iec104_builder import IEC104IdentityBuilder

# Apply registration
register_builder(ModbusIdentityBuilder)
register_builder(EtherNetIPIdentityBuilder)
register_builder(ProfinetIdentityBuilder)
register_builder(S7IdentityBuilder)
register_builder(SNMPIdentityBuilder)
register_builder(BACnetIdentityBuilder)
register_builder(OpcUaIdentityBuilder)
register_builder(DNP3IdentityBuilder)
register_builder(IEC104IdentityBuilder)


# Public API
__all__ = [
    # Base types
    "ProtocolIdentityBuilder",
    "IdentityResponse",
    "FirmwareFields",
    # Registry functions
    "register_builder",
    "get_builder",
    "get_builder_by_identity_key",
    "get_all_builders",
    "get_registered_protocols",
    "has_builder",
    # Identity building
    "build_identity_for_protocol",
    "derive_firmware_fields_for_protocol",
    "derive_all_firmware_fields",
    # MAC generation (centralized)
    "generate_mac",
    "generate_mac_from_fingerprint",
    # Builder classes
    "ModbusIdentityBuilder",
    "EtherNetIPIdentityBuilder",
    "ProfinetIdentityBuilder",
    "S7IdentityBuilder",
    "SNMPIdentityBuilder",
    "BACnetIdentityBuilder",
    "OpcUaIdentityBuilder",
    "DNP3IdentityBuilder",
    "IEC104IdentityBuilder",
]
