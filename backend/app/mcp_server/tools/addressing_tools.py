# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IP and MAC address assignment tools for MCP."""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario
from app.protocol_engines.vendor_oui import generate_mac_address


async def auto_assign_addresses(
    db: AsyncSession, scenario_id: str, scheme: str = "zone_based"
) -> str:
    """Automatically assign IP and MAC addresses to devices.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        scheme: Addressing scheme ('zone_based', 'sequential', 'vertical_based')

    Returns:
        JSON string with assignment results
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})
    definition.get("zones", {})

    if scheme == "zone_based":
        # Assign based on zones
        zone_subnets = {
            "plant_floor": "192.168.1",
            "dmz": "192.168.2",
            "corporate": "192.168.3",
            "remote": "10.0.0",
        }

        # Group devices by zone
        devices_by_zone: dict[str, list[str]] = {}
        for device_id, device in devices.items():
            zone_id = device.get("zoneId", "default")
            if zone_id not in devices_by_zone:
                devices_by_zone[zone_id] = []
            devices_by_zone[zone_id].append(device_id)

        # Assign addresses within each zone
        for zone_id, device_ids in devices_by_zone.items():
            # Get subnet for zone
            subnet = zone_subnets.get(zone_id, "192.168.99")

            # Assign IP addresses
            for i, device_id in enumerate(device_ids, start=10):
                device = devices[device_id]
                network = device.get("network", {})

                # Assign IP
                network["ipAddress"] = f"{subnet}.{i}"
                network["subnetMask"] = "255.255.255.0"
                network["gateway"] = f"{subnet}.1"

                # Assign MAC using vendor OUI database
                device_type = device.get("type", "")
                vendor = device.get("vendor") or device.get("vendorFingerprint", {}).get("vendor")
                network["macAddress"] = generate_mac_address(vendor=vendor, device_type=device_type)

                device["network"] = network

    elif scheme == "sequential":
        # Simple sequential assignment
        base_subnet = "192.168.100"

        for i, (device_id, device) in enumerate(devices.items(), start=10):
            network = device.get("network", {})

            # Assign IP
            network["ipAddress"] = f"{base_subnet}.{i}"
            network["subnetMask"] = "255.255.255.0"
            network["gateway"] = f"{base_subnet}.1"

            # Assign MAC using vendor OUI database
            device_type = device.get("type", "")
            vendor = device.get("vendor") or device.get("vendorFingerprint", {}).get("vendor")
            network["macAddress"] = generate_mac_address(vendor=vendor, device_type=device_type)

            device["network"] = network

    else:
        return json.dumps({"error": f"Unknown addressing scheme: {scheme}"})

    # Update scenario - use flag_modified to ensure JSONB change is detected
    definition["devices"] = devices
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "scheme": scheme,
        "devices_updated": len(devices),
    })


async def assign_device_address(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    network_config: dict[str, Any],
) -> str:
    """Assign network configuration to a specific device.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        network_config: Network configuration (IP, MAC, etc.)

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    # Update device network configuration
    device = devices[device_id]
    if "network" not in device:
        device["network"] = {}

    device["network"].update(network_config)

    # Update scenario - use flag_modified to ensure JSONB change is detected
    definition["devices"] = devices
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "network": device["network"],
    })


async def suggest_addressing_scheme(
    db: AsyncSession, scenario_id: str, vertical: str
) -> str:
    """Suggest an addressing scheme based on scenario and vertical.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        vertical: Industry vertical

    Returns:
        JSON string with addressing scheme suggestion
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    devices = definition.get("devices", {})
    zones = definition.get("zones", {})

    # Determine best scheme
    has_zones = len(zones) > 0
    device_count = len(devices)

    if has_zones:
        scheme = "zone_based"
        description = "Zone-based addressing groups devices by network zone with dedicated subnets"

        # Suggest subnets for each zone
        suggested_subnets = {}
        for zone_id, zone in zones.items():
            if zone_id == "plant_floor":
                suggested_subnets[zone_id] = "192.168.1.0/24"
            elif zone_id == "dmz":
                suggested_subnets[zone_id] = "192.168.2.0/24"
            elif zone_id == "corporate":
                suggested_subnets[zone_id] = "192.168.3.0/24"
            elif zone_id == "remote":
                suggested_subnets[zone_id] = "10.0.0.0/24"
            else:
                suggested_subnets[zone_id] = f"192.168.{len(suggested_subnets) + 10}.0/24"

        suggestion = {
            "scheme": scheme,
            "description": description,
            "subnets": suggested_subnets,
            "rationale": "Scenario has defined zones, zone-based addressing is recommended",
        }

    elif device_count < 50:
        scheme = "sequential"
        description = "Sequential addressing assigns consecutive IPs in a single subnet"
        suggestion = {
            "scheme": scheme,
            "description": description,
            "subnet": "192.168.100.0/24",
            "rationale": "Small scenario without zones, sequential addressing is simplest",
        }

    else:
        scheme = "vertical_based"
        description = "Vertical-based addressing uses industry-specific subnet ranges"

        vertical_subnets = {
            "manufacturing": {
                "plant_floor": "10.10.0.0/16",
                "dmz": "10.20.0.0/16",
            },
            "water_wastewater": {
                "scada": "192.168.10.0/24",
                "field": "192.168.20.0/24",
            },
            "energy_power": {
                "substation": "10.100.0.0/16",
                "control": "10.200.0.0/16",
            },
        }

        subnets = vertical_subnets.get(vertical, {
            "default": "192.168.0.0/16"
        })

        suggestion = {
            "scheme": scheme,
            "description": description,
            "subnets": subnets,
            "rationale": f"Large scenario for {vertical}, using industry-specific addressing",
        }

    return json.dumps({"suggestion": suggestion})


# Default zone to VLAN mapping
DEFAULT_ZONE_VLAN_MAP: dict[str, int] = {
    "enterprise": 10,
    "dmz": 20,
    "process": 30,
    "field": 40,
    "remote": 50,
    "safety": 60,
    "plant_floor": 100,
    "corporate": 110,
    "control": 120,
}


async def assign_vlans(
    db: AsyncSession,
    scenario_id: str,
    zone_vlan_map: dict[str, int] | None = None,
) -> str:
    """Assign VLANs to devices based on zone membership.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        zone_vlan_map: Optional custom zone->VLAN mapping

    Returns:
        JSON string with assignment results
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})
    zones = definition.get("zones", {})

    # Use provided mapping or default
    vlan_map = zone_vlan_map or DEFAULT_ZONE_VLAN_MAP

    # First, assign VLANs to zones if they don't have them
    zone_vlans_assigned = 0
    for zone_id, zone in zones.items():
        if "vlan" not in zone or zone.get("vlan") is None:
            zone["vlan"] = vlan_map.get(zone_id, 100 + len(zones))
            zone_vlans_assigned += 1

    # Assign VLANs to devices based on their zone
    device_vlans_assigned = 0
    for device_id, device in devices.items():
        zone_id = device.get("zoneId")

        # Get VLAN from zone or default
        if zone_id and zone_id in zones:
            vlan = zones[zone_id].get("vlan", vlan_map.get(zone_id, 100))
        else:
            vlan = vlan_map.get(zone_id, 100)

        # Update device network config
        network = device.get("network", {})
        if "vlan" not in network or network.get("vlan") is None:
            network["vlan"] = vlan
            device["network"] = network
            device_vlans_assigned += 1

    # Update scenario - use flag_modified to ensure JSONB change is detected
    definition["devices"] = devices
    definition["zones"] = zones
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "zone_vlans_assigned": zone_vlans_assigned,
        "device_vlans_assigned": device_vlans_assigned,
        "vlan_map_used": vlan_map,
    })


async def suggest_vlan_scheme(
    db: AsyncSession,
    scenario_id: str,
) -> str:
    """Suggest a VLAN scheme for a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string with VLAN scheme suggestion
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    zones = definition.get("zones", {})
    vertical = scenario.vertical

    # Generate VLAN suggestions based on zones and vertical
    suggestions = {}
    base_vlan = 10

    # Vertical-specific base VLANs
    vertical_bases = {
        "manufacturing": 100,
        "water_wastewater": 200,
        "energy_power": 300,
        "oil_gas": 400,
    }

    if vertical and vertical in vertical_bases:
        base_vlan = vertical_bases[vertical]

    for i, (zone_id, zone) in enumerate(zones.items()):
        zone_name = zone.get("name", zone_id)
        level = zone.get("level", 1)

        # Higher levels get lower VLAN numbers (enterprise = lower, field = higher)
        vlan = base_vlan + (5 - int(level)) * 10 + i

        suggestions[zone_id] = {
            "vlan": vlan,
            "zone_name": zone_name,
            "level": level,
            "rationale": f"Level {level} zone, VLAN {vlan}",
        }

    return json.dumps({
        "suggestions": suggestions,
        "vertical": vertical,
        "base_vlan": base_vlan,
        "rationale": f"VLAN scheme based on {vertical or 'generic'} vertical and zone levels",
    })
