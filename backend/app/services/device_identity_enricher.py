"""Shared device identity enrichment for serial numbers and unique identifiers.

Consolidates serial number and unique identifier enrichment logic previously
duplicated across scenarios.py, templates.py, and ai.py route files.

Serial numbers are critical for Cisco Cyber Vision to correctly identify
distinct devices. Unique identifiers ensure meaningful device names are
displayed instead of generic model names.
"""

import logging
from typing import Any

from app.services.serial_number_generator import SerialNumberGenerator

logger = logging.getLogger(__name__)


def _identity_has_vendor_data(identity: dict | None, required_key: str) -> bool:
    """Check if identity has real vendor data, not just a serial number placeholder.

    Args:
        identity: Protocol identity dict or None
        required_key: Key that must be present to confirm real vendor data

    Returns:
        True if identity has meaningful vendor data
    """
    if not identity or not isinstance(identity, dict):
        return False
    # For EtherNet/IP, vendor_id is required to avoid defaulting to Rockwell
    if required_key == "vendor_id":
        return identity.get("vendor_id") is not None
    # For other protocols, check for any key besides serial_number
    return any(k != "serial_number" for k in identity.keys())


# Protocol enrichment rules: (identity_key, required_field, protocol_names, generator)
_PROTOCOL_SERIAL_RULES = [
    ("ethernet_ip_identity", "vendor_id", ["ethernet_ip"], "ethernet_ip"),
    ("s7_identity", "order_code", ["s7comm", "s7comm_plus"], "s7"),
    ("profinet_identity", "vendor_id", ["profinet", "profisafe"], "profinet"),
    ("modbus_identity", "vendor_name", ["modbus_tcp", "modbus"], "s7"),
    ("bacnet_identity", "vendor_id", ["bacnet"], "s7"),
    ("snmp_identity", "sys_descr", ["snmp"], "s7"),
    ("opc_ua_identity", "manufacturer_name", ["opc_ua"], "s7"),
]


def enrich_device_serial_numbers(
    device: dict,
    device_id: str,
    scenario_id: str,
    skip_existing: bool = False,
) -> bool:
    """Add unique serial numbers to a device's vendor fingerprint.

    Enriches serial numbers for any protocol identity that exists in the
    fingerprint with proper vendor data. The fingerprint defines what
    protocols the device actually supports.

    Args:
        device: Device dictionary (modified in place)
        device_id: Unique device identifier
        scenario_id: Scenario UUID for deterministic serial generation
        skip_existing: If True, only enrich identities missing serial_number.
            Used as a deployment-time guardrail for legacy scenarios.

    Returns:
        True if any serial numbers were added (useful for skip_existing logging).
    """
    fingerprint = device.get("vendorFingerprint") or device.get("vendor_fingerprint") or {}
    enriched_any = False

    for identity_key, required_field, _protocol_names, generator_type in _PROTOCOL_SERIAL_RULES:
        existing_identity = fingerprint.get(identity_key)
        if not _identity_has_vendor_data(existing_identity, required_field):
            continue

        if skip_existing and existing_identity.get("serial_number"):
            continue

        enriched_any = True

        if generator_type == "ethernet_ip":
            existing_identity["serial_number"] = SerialNumberGenerator.generate_ethernet_ip(
                device_id, scenario_id
            )
        elif generator_type == "profinet":
            serial = SerialNumberGenerator.generate_profinet(device_id, scenario_id)
            existing_identity["serial_number"] = serial
            existing_identity["im0_serial_number"] = serial
        else:
            existing_identity["serial_number"] = SerialNumberGenerator.generate_s7(
                device_id, scenario_id
            )

    # Update both camelCase and snake_case versions for compatibility
    device["vendorFingerprint"] = fingerprint
    device["vendor_fingerprint"] = fingerprint

    logger.debug(f"Enriched serial numbers for device {device_id}")

    return enriched_any


def enrich_definition_serial_numbers(
    definition: dict,
    scenario_id: str,
    skip_existing: bool = False,
) -> dict:
    """Enrich all devices in a scenario definition with unique serial numbers.

    Supports both dict and list device formats.

    Args:
        definition: Scenario definition dict
        scenario_id: Scenario UUID for deterministic generation
        skip_existing: If True, only enrich devices missing serial numbers.
            Logs a warning summarizing how many devices were backfilled.

    Returns:
        Updated definition with serial numbers added
    """
    devices = definition.get("devices", {})
    if not devices:
        return definition

    # Handle both dict and list formats
    if isinstance(devices, dict):
        device_items = devices.items()
    else:
        device_items = [(d.get("id", f"device_{i}"), d) for i, d in enumerate(devices)]

    devices_enriched = 0
    for device_id, device in device_items:
        if not device_id or not device:
            continue
        was_enriched = enrich_device_serial_numbers(
            device, device_id, scenario_id, skip_existing=skip_existing
        )
        if was_enriched and skip_existing:
            devices_enriched += 1

    if skip_existing and devices_enriched > 0:
        logger.warning(
            f"Scenario {scenario_id}: {devices_enriched} device(s) were missing serial numbers "
            f"and were backfilled at deployment time. Consider recreating from template."
        )

    return definition


def enrich_device_unique_identifiers(
    device: dict,
    device_id: str,
    scenario_id: str,
) -> None:
    """Add unique identifiers to device's protocol identities based on device name.

    Ensures Cisco Cyber Vision displays meaningful device names instead of
    generic model names. Uses the device's name to populate protocol-specific
    identifier fields.

    Should be called AFTER AI naming to use the contextual names.

    Args:
        device: Device dictionary (modified in place)
        device_id: Unique device identifier
        scenario_id: Scenario UUID
    """
    from app.services.unique_identifier_generator import UniqueIdentifierGenerator

    device_name = device.get("name")
    fingerprint = device.get("vendorFingerprint") or device.get("vendor_fingerprint") or {}
    protocols = device.get("protocols", []) or []
    model = fingerprint.get("model", "")
    vendor_family = fingerprint.get("vendor_family", "")
    vendor = fingerprint.get("vendor", "")

    def identity_exists(identity: dict | None) -> bool:
        """Check if identity has any data."""
        return bool(identity and isinstance(identity, dict) and len(identity) > 0)

    # EtherNet/IP identity - product_name (what CV displays for Rockwell devices)
    if "ethernet_ip" in protocols:
        existing_identity = fingerprint.get("ethernet_ip_identity")
        if identity_exists(existing_identity):
            existing_identity["product_name"] = (
                UniqueIdentifierGenerator.generate_ethernet_ip_product_name(
                    device_id=device_id,
                    scenario_id=scenario_id,
                    device_name=device_name,
                    model=model,
                    vendor_family=vendor_family,
                    vendor=vendor,
                )
            )

    # PROFINET identity - station_name (must be unique on PROFINET network)
    if "profinet" in protocols or "profisafe" in protocols:
        existing_identity = fingerprint.get("profinet_identity")
        if identity_exists(existing_identity):
            existing_identity["station_name"] = (
                UniqueIdentifierGenerator.generate_profinet_station_name(
                    device_id=device_id,
                    scenario_id=scenario_id,
                    device_name=device_name,
                    model=model,
                    vendor_family=vendor_family,
                    vendor=vendor,
                )
            )

    # S7comm identity - plc_name (what CV displays for Siemens devices)
    if "s7comm" in protocols or "s7comm_plus" in protocols:
        existing_identity = fingerprint.get("s7_identity")
        if identity_exists(existing_identity):
            existing_identity["plc_name"] = (
                UniqueIdentifierGenerator.generate_s7_plc_name(
                    device_id=device_id,
                    scenario_id=scenario_id,
                    device_name=device_name,
                    model=model,
                    vendor_family=vendor_family,
                    vendor=vendor,
                )
            )

    # Modbus identity - product_name (from FC43 MEI response)
    if "modbus_tcp" in protocols or "modbus" in protocols:
        existing_identity = fingerprint.get("modbus_identity")
        if identity_exists(existing_identity):
            if device_name:
                existing_identity["product_name"] = device_name
            elif model:
                hash_bytes = UniqueIdentifierGenerator._generate_hash(device_id, scenario_id)
                hash_suffix = hash_bytes[:2].hex().upper()
                existing_identity["product_name"] = f"{model}-{hash_suffix}"

    # SNMP identity - sys_name (what CV displays for network devices)
    if "snmp" in protocols:
        existing_identity = fingerprint.get("snmp_identity")
        if identity_exists(existing_identity):
            existing_identity["sys_name"] = (
                UniqueIdentifierGenerator.generate_snmp_sys_name(
                    device_id=device_id,
                    scenario_id=scenario_id,
                    device_name=device_name,
                    model=model,
                    vendor_family=vendor_family,
                    vendor=vendor,
                )
            )

    # BACnet identity - object_name and device_instance
    if "bacnet" in protocols:
        existing_identity = fingerprint.get("bacnet_identity")
        if identity_exists(existing_identity):
            existing_identity["device_instance"] = (
                UniqueIdentifierGenerator.generate_bacnet_device_instance(
                    device_id=device_id,
                    scenario_id=scenario_id,
                )
            )
            existing_identity["object_name"] = (
                UniqueIdentifierGenerator.generate_bacnet_object_name(
                    device_id=device_id,
                    scenario_id=scenario_id,
                    device_name=device_name,
                    model=model,
                    vendor_family=vendor_family,
                    vendor=vendor,
                )
            )

    # Update both camelCase and snake_case versions for compatibility
    device["vendorFingerprint"] = fingerprint
    device["vendor_fingerprint"] = fingerprint

    logger.debug(f"Enriched unique identifiers for device {device_id}: name={device_name}")
