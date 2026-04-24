# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Protocol validation helpers for device/fingerprint consistency.

This module provides utilities to validate that devices have proper protocol
identity support before generating traffic, preventing misattribution issues
like Siemens devices appearing as Rockwell in Cyber Vision.

The key principle is that device.protocols is the AUTHORITATIVE source for
what protocols a device will use. Identity blocks should not be created
from nothing - they must come from proper vendor fingerprint data.
"""

import logging
from typing import Any

from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY

logger = logging.getLogger(__name__)

# Map protocol identity keys to the required field that indicates real vendor data
# (not just a serial number placeholder)
IDENTITY_REQUIRED_FIELDS: dict[str, str] = {
    "ethernet_ip_identity": "vendor_id",
    "profinet_identity": "vendor_id",
    "s7_identity": "order_code",
    "modbus_identity": "vendor_name",
    "bacnet_identity": "vendor_id",
    "snmp_identity": "sys_descr",
    "opc_ua_identity": "manufacturer_name",
    "dnp3_identity": "vendor_name",
    "iec104_identity": "vendor_name",
}


def get_protocol_identity_key(protocol: str) -> str | None:
    """Get the identity dictionary key for a protocol.

    Args:
        protocol: Protocol name (e.g., "ethernet_ip", "profinet", "modbus_tcp")

    Returns:
        Identity key (e.g., "ethernet_ip_identity") or None if not mapped
    """
    return PROTOCOL_TO_IDENTITY_KEY.get(protocol)


def identity_has_vendor_data(
    identity: dict[str, Any] | None,
    identity_key: str,
) -> bool:
    """Check if an identity dictionary has real vendor data.

    This prevents creating traffic for identities that are empty placeholders
    or only have a serial_number field. Empty identities would cause devices
    to use default values (e.g., vendor_id=1 for EtherNet/IP = Rockwell).

    Args:
        identity: The identity dictionary to check
        identity_key: The identity key (e.g., "ethernet_ip_identity")

    Returns:
        True if identity has meaningful vendor data, False otherwise
    """
    if not identity or not isinstance(identity, dict):
        return False

    # Get the required field for this identity type
    required_field = IDENTITY_REQUIRED_FIELDS.get(identity_key)
    if required_field:
        # Check for the specific required field
        if identity.get(required_field) is not None:
            return True

    # Fallback: check if there's any field besides serial_number
    meaningful_keys = [k for k in identity.keys() if k not in ("serial_number", "im0_serial_number")]
    return len(meaningful_keys) > 0


def validate_device_protocols(
    device: dict[str, Any],
    fingerprint: dict[str, Any] | None = None,
) -> list[str]:
    """Validate and return only protocols that have proper identity support.

    This function ensures that a device only uses protocols for which it has
    proper fingerprint/identity data. This prevents misattribution issues.

    Args:
        device: Device definition with 'protocols' list
        fingerprint: Vendor fingerprint (if None, extracted from device)

    Returns:
        List of validated protocols (subset of device.protocols)
    """
    declared_protocols = device.get("protocols", []) or []
    if not declared_protocols:
        return []

    if fingerprint is None:
        # Check all possible fingerprint key names used in different code paths
        fingerprint = (
            device.get("vendorFingerprint")
            or device.get("vendor_fingerprint")
            or device.get("fingerprint")  # Used by create_scenario_from_preview
            or {}
        )

    validated = []

    for protocol in declared_protocols:
        identity_key = get_protocol_identity_key(protocol)

        if identity_key:
            # Protocol requires identity - check if fingerprint has it
            identity = fingerprint.get(identity_key)
            if identity_has_vendor_data(identity, identity_key):
                validated.append(protocol)
            else:
                logger.debug(
                    f"Protocol '{protocol}' declared but no valid {identity_key} "
                    f"in fingerprint for device"
                )
        else:
            # Protocol doesn't require identity (future protocols, raw TCP, etc.)
            validated.append(protocol)

    return validated


def validate_scenario_protocols(definition: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate all devices in a scenario for protocol/fingerprint consistency.

    Args:
        definition: Scenario definition with devices

    Returns:
        List of validation issues found
    """
    issues = []
    devices = definition.get("devices", {})

    if isinstance(devices, dict):
        device_items = devices.items()
    else:
        device_items = [(d.get("id", f"device_{i}"), d) for i, d in enumerate(devices)]

    for device_id, device in device_items:
        if not device_id or not device:
            continue

        # Check all possible fingerprint key names used in different code paths
        fingerprint = (
            device.get("vendorFingerprint")
            or device.get("vendor_fingerprint")
            or device.get("fingerprint")  # Used by create_scenario_from_preview
            or {}
        )
        protocols = device.get("protocols", []) or []
        device_name = device.get("name", device_id)

        for protocol in protocols:
            identity_key = get_protocol_identity_key(protocol)
            if not identity_key:
                continue

            identity = fingerprint.get(identity_key)

            if not identity or not isinstance(identity, dict):
                issues.append({
                    "device_id": device_id,
                    "device_name": device_name,
                    "protocol": protocol,
                    "severity": "warning",
                    "issue": f"Protocol '{protocol}' declared but no {identity_key} in fingerprint",
                    "recommendation": f"Remove '{protocol}' from protocols or add proper fingerprint data",
                })
            elif not identity_has_vendor_data(identity, identity_key):
                required_field = IDENTITY_REQUIRED_FIELDS.get(identity_key, "vendor data")
                # All protocol identity issues are warnings - traffic generator will skip
                # protocols without proper identity data, so deployment can proceed
                issues.append({
                    "device_id": device_id,
                    "device_name": device_name,
                    "protocol": protocol,
                    "severity": "warning",
                    "issue": f"{identity_key} exists but missing {required_field}",
                    "recommendation": f"Add {required_field} to {identity_key} or remove protocol",
                })

    return issues


def device_supports_protocol(
    fingerprint: dict[str, Any],
    protocol: str,
    declared_protocols: list[str] | None = None,
) -> bool:
    """Check if a device supports a specific protocol based on fingerprint.

    This is the authoritative check used by traffic generators. It verifies:
    1. Protocol is in declared_protocols (if provided)
    2. Fingerprint has supported_protocols field with protocol
    3. OR fingerprint has valid identity for the protocol (fallback)

    Args:
        fingerprint: Device vendor fingerprint
        protocol: Protocol to check (e.g., "ethernet_ip")
        declared_protocols: Optional list of protocols device declares

    Returns:
        True if device properly supports the protocol
    """
    if not fingerprint:
        return False

    # If declared_protocols provided, protocol must be in it
    if declared_protocols is not None and protocol not in declared_protocols:
        return False

    # Check explicit supported_protocols field (authoritative)
    supported = fingerprint.get("supported_protocols", [])
    if supported and protocol in supported:
        return True

    # Fallback: check for valid identity existence
    identity_key = get_protocol_identity_key(protocol)
    if identity_key:
        identity = fingerprint.get(identity_key)
        return identity_has_vendor_data(identity, identity_key)

    return False
