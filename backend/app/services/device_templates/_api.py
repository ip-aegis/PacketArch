# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Public query API for the device template library."""

import random
from typing import Any

from app.services.device_templates._helpers import (
    generate_serial_number,
    generate_station_name,
    merge_identity,
)
from app.services.device_templates._registry import DEVICE_TEMPLATES
from app.services.device_templates._types import DeviceInstance, DeviceTemplate


def get_all_templates() -> list[DeviceTemplate]:
    """Get all registered device templates."""
    return list(DEVICE_TEMPLATES.values())


def get_template_by_id(template_id: str) -> DeviceTemplate | None:
    """Get a device template by its ID."""
    return DEVICE_TEMPLATES.get(template_id)


def get_templates_by_vendor(vendor: str) -> list[DeviceTemplate]:
    """Get all templates for a specific vendor."""
    vendor_lower = vendor.lower()
    return [t for t in DEVICE_TEMPLATES.values() if t.vendor.lower() == vendor_lower]


def get_templates_by_device_type(device_type: str) -> list[DeviceTemplate]:
    """Get all templates for a specific device type."""
    return [t for t in DEVICE_TEMPLATES.values() if t.device_type == device_type]


def get_templates_with_cves() -> list[DeviceTemplate]:
    """Get all templates that have vulnerable firmware variants."""
    return [t for t in DEVICE_TEMPLATES.values() if t.get_vulnerable_firmwares()]


def get_template_count() -> int:
    """Get total number of registered templates."""
    return len(DEVICE_TEMPLATES)


def get_total_firmware_variants() -> int:
    """Get total number of firmware variants across all templates."""
    return sum(len(t.firmware_variants) for t in DEVICE_TEMPLATES.values())


def get_total_cves() -> int:
    """Get total number of unique CVEs across all firmware variants."""
    cves = set()
    for template in DEVICE_TEMPLATES.values():
        for fw in template.firmware_variants:
            cves.update(fw.cves)
    return len(cves)


def generate_device_instance(
    template_id: str,
    firmware_version: str | None = None,
    station_name: str | None = None,
    serial_number: str | None = None,
    mac_address: str | None = None,
    ip_address: str | None = None,
    location: str | None = None,
    sequence: int = 1,
    existing_serials: set[str] | None = None,
    existing_names: set[str] | None = None,
) -> DeviceInstance | None:
    """Generate a device instance from a template.

    Args:
        template_id: Template ID to use
        firmware_version: Specific firmware version (or None for default)
        station_name: Override station name (or None to generate)
        serial_number: Override serial number (or None to generate)
        mac_address: MAC address (usually from IP management)
        ip_address: IP address (from IP management)
        location: Location hint for station name generation
        sequence: Sequence number for this device type
        existing_serials: Set of already-used serial numbers
        existing_names: Set of already-used station names

    Returns:
        DeviceInstance or None if template not found
    """
    template = get_template_by_id(template_id)
    if not template:
        return None

    # Get firmware variant
    if firmware_version:
        firmware = template.get_firmware_by_version(firmware_version)
    else:
        firmware = template.get_default_firmware()

    if not firmware:
        return None

    # Generate or use provided serial number
    if serial_number:
        final_serial = serial_number
    elif template.instance_rules:
        final_serial = generate_serial_number(
            template.instance_rules.serial_format,
            existing_serials
        )
    else:
        final_serial = generate_serial_number("{10ALPHANUM}", existing_serials)

    # Generate or use provided station name
    if station_name:
        final_name = station_name
    elif template.instance_rules:
        final_name = generate_station_name(
            template.instance_rules.station_name_pattern,
            role=template.device_type,
            vendor_short=template.instance_rules.vendor_short,
            model_short=template.instance_rules.model_short,
            sequence=sequence,
            location=location,
            existing_names=existing_names,
        )
    else:
        final_name = f"device-{sequence:03d}"

    # Generate MAC if not provided
    if not mac_address and template.oui_prefixes:
        oui = random.choice(template.oui_prefixes)
        suffix = ':'.join(f'{random.randint(0, 255):02X}' for _ in range(3))
        mac_address = f"{oui}:{suffix}"

    # Build merged identities
    merged = {}

    # Merge each protocol identity
    identity_keys = [
        ("modbus_identity", template.modbus_identity),
        ("ethernet_ip_identity", template.ethernet_ip_identity),
        ("profinet_identity", template.profinet_identity),
        ("s7_identity", template.s7_identity),
        ("bacnet_identity", template.bacnet_identity),
        ("snmp_identity", template.snmp_identity),
    ]

    for key, base_identity in identity_keys:
        if base_identity:
            fw_override = firmware.identity_overrides.get(key, {})
            instance_values = {
                "serial_number": final_serial,
                "station_name": final_name,
            }
            # Add firmware version to appropriate fields
            if key == "modbus_identity":
                instance_values["major_minor_revision"] = firmware.version
            elif key == "profinet_identity":
                instance_values["im0_sw_revision"] = firmware.version
            elif key == "ethernet_ip_identity":
                # Parse version for revision fields
                parts = firmware.version.lstrip("V").split(".")
                if len(parts) >= 2:
                    try:
                        instance_values["revision_major"] = int(parts[0])
                        instance_values["revision_minor"] = int(parts[1])
                    except ValueError:
                        pass
            elif key == "s7_identity":
                instance_values["plant_id"] = final_name

            merged[key] = merge_identity(base_identity, fw_override, instance_values)

    return DeviceInstance(
        template_id=template_id,
        firmware_version=firmware.version,
        serial_number=final_serial,
        station_name=final_name,
        mac_address=mac_address or "",
        ip_address=ip_address or "",
        cves=list(firmware.cves),
        merged_identities=merged,
    )
