# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IP Range Management Service.

Handles allocation and management of IP ranges for scenarios.
Each scenario gets a unique 10.{n}.0.0/16 range where n is 1-254.

This module uses module-level functions instead of a class with static methods
for cleaner imports and better testability.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ip_range_allocation import IPRangeAllocation
from app.models.scenario import Scenario


async def allocate_ip_range(
    db: AsyncSession, scenario_id: uuid.UUID
) -> IPRangeAllocation:
    """Allocate the next available /16 range to a scenario.

    Args:
        db: Database session
        scenario_id: UUID of the scenario to allocate to

    Returns:
        The created IPRangeAllocation

    Raises:
        ValueError: If no ranges are available (all 254 used)
    """
    # Find all used range indices
    result = await db.execute(
        select(IPRangeAllocation.range_index).order_by(
            IPRangeAllocation.range_index
        )
    )
    used_indices = {row[0] for row in result.fetchall()}

    # Find first available index (1-254)
    next_index = None
    for i in range(1, 255):
        if i not in used_indices:
            next_index = i
            break

    if next_index is None:
        raise ValueError("No available IP ranges (all 254 ranges allocated)")

    # Create allocation
    cidr_range = f"10.{next_index}.0.0/16"
    allocation = IPRangeAllocation(
        scenario_id=scenario_id,
        range_index=next_index,
        cidr_range=cidr_range,
        next_host_offset=10,  # Start at 10.{n}.0.10
    )

    db.add(allocation)
    return allocation


async def get_ip_allocation(
    db: AsyncSession, scenario_id: uuid.UUID
) -> IPRangeAllocation | None:
    """Get IP range allocation for a scenario.

    Args:
        db: Database session
        scenario_id: UUID of the scenario

    Returns:
        The IPRangeAllocation or None if not found
    """
    result = await db.execute(
        select(IPRangeAllocation).where(
            IPRangeAllocation.scenario_id == scenario_id
        )
    )
    return result.scalar_one_or_none()


async def get_next_ip(db: AsyncSession, scenario_id: uuid.UUID) -> dict[str, Any]:
    """Get next available IP address within scenario's range.

    Args:
        db: Database session
        scenario_id: UUID of the scenario

    Returns:
        Dict with ip_address, subnet_mask, gateway, cidr

    Raises:
        ValueError: If scenario has no IP range allocated
    """
    allocation = await get_ip_allocation(db, scenario_id)

    if not allocation:
        raise ValueError("Scenario has no IP range allocated")

    # Calculate next IP from offset
    range_idx = allocation.range_index
    offset = allocation.next_host_offset

    # Calculate subnet and host parts
    # For /16: 10.{range_idx}.{subnet}.{host}
    subnet = offset // 256
    host = offset % 256

    # Skip .0 (network) and .255 (broadcast) addresses
    if host == 0:
        host = 1
        subnet = offset // 256
    if host == 255:
        subnet += 1
        host = 1

    # Validate we haven't exceeded the /16
    if subnet > 255:
        raise ValueError("IP range exhausted (no more IPs available)")

    ip_address = f"10.{range_idx}.{subnet}.{host}"
    gateway = f"10.{range_idx}.{subnet}.1"

    # Increment offset for next call
    allocation.next_host_offset = offset + 1

    return {
        "ip_address": ip_address,
        "subnet_mask": "255.255.255.0",  # /24 subnets within the /16
        "gateway": gateway,
        "cidr": allocation.cidr_range,
    }


def get_zone_subnet(range_index: int, zone_offset: int) -> dict[str, Any]:
    """Get the subnet configuration for a zone within a scenario's range.

    Derives a /24 subnet from the scenario's /16 range based on zone offset.

    Args:
        range_index: The scenario's allocated range index (1-254)
        zone_offset: Zone offset (0-255) determines the third octet

    Returns:
        Dict with subnet, gateway, and subnet_mask
    """
    # Zone offset determines the third octet: 10.{range_idx}.{zone_offset}.0/24
    subnet = f"10.{range_index}.{zone_offset}.0/24"
    gateway = f"10.{range_index}.{zone_offset}.1"

    return {
        "subnet": subnet,
        "gateway": gateway,
        "subnet_mask": "255.255.255.0",
        "start_offset": 10,  # First device IP at .10
    }


async def list_all_ip_allocations(db: AsyncSession) -> dict[str, Any]:
    """List all IP range allocations with scenario info.

    Args:
        db: Database session

    Returns:
        Dict with items list, total count, and available_ranges
    """
    result = await db.execute(
        select(IPRangeAllocation, Scenario.name)
        .join(Scenario, IPRangeAllocation.scenario_id == Scenario.id)
        .order_by(IPRangeAllocation.range_index)
    )

    items = []
    used_indices = set()

    for allocation, scenario_name in result.fetchall():
        used_indices.add(allocation.range_index)
        items.append(
            {
                "id": allocation.id,
                "scenario_id": allocation.scenario_id,
                "scenario_name": scenario_name,
                "range_index": allocation.range_index,
                "cidr_range": allocation.cidr_range,
                "next_host_offset": allocation.next_host_offset,
                "created_at": allocation.created_at,
            }
        )

    # Calculate available ranges
    available = [i for i in range(1, 255) if i not in used_indices]

    return {
        "items": items,
        "total": len(items),
        "available_ranges": available,
    }


async def release_ip_range(db: AsyncSession, scenario_id: uuid.UUID) -> bool:
    """Release IP range when scenario is deleted.

    Note: This is typically handled by CASCADE delete, but can be
    called explicitly if needed.

    Args:
        db: Database session
        scenario_id: UUID of the scenario

    Returns:
        True if range was released, False if not found
    """
    result = await db.execute(
        select(IPRangeAllocation).where(
            IPRangeAllocation.scenario_id == scenario_id
        )
    )
    allocation = result.scalar_one_or_none()

    if allocation:
        await db.delete(allocation)
        return True
    return False


def assign_zone_subnet_offsets(
    zones: list[dict[str, Any]], range_index: int
) -> list[dict[str, Any]]:
    """Assign sequential subnet_offsets to zones and populate network config.

    This function ensures each zone has a unique subnet_offset and proper
    network configuration derived from the scenario's /16 range.

    Args:
        zones: List of zone dictionaries
        range_index: The scenario's allocated range index (1-254)

    Returns:
        Updated list of zones with subnet_offset and network config
    """
    for i, zone in enumerate(zones):
        # Use existing subnet_offset if present, otherwise assign sequentially
        subnet_offset = zone.get("subnet_offset", i)
        zone["subnet_offset"] = subnet_offset
        zone["network"] = {
            "subnet": f"10.{range_index}.{subnet_offset}.0/24",
            "gateway": f"10.{range_index}.{subnet_offset}.1",
            "subnet_offset": subnet_offset,
        }
    return zones


def validate_device_zone_ip_consistency(
    devices: dict[str, Any],
    zones: dict[str, Any],
    range_index: int,
) -> list[str]:
    """Validate that device IPs are within their zone's subnet.

    Checks each device's IP address to ensure it falls within the /24 subnet
    assigned to its zone based on the zone's subnet_offset.

    Args:
        devices: Dict of device_id -> device data (from scenario.definition["devices"])
        zones: Dict of zone_id -> zone data (from scenario.definition["zones"])
        range_index: The scenario's allocated range index (1-254)

    Returns:
        List of validation error messages (empty list if all valid)
    """
    errors = []

    for device_id, device in devices.items():
        zone_id = device.get("zoneId")
        if not zone_id or zone_id not in zones:
            continue

        zone = zones[zone_id]
        # Get subnet_offset from zone's network config or direct field
        network = zone.get("network", {})
        subnet_offset = network.get("subnet_offset")
        if subnet_offset is None:
            subnet_offset = zone.get("subnet_offset")
        if subnet_offset is None:
            continue

        # Check device IP matches expected prefix
        expected_prefix = f"10.{range_index}.{subnet_offset}."
        device_network = device.get("network", {})
        device_ip = device_network.get("ipAddress", "")

        if device_ip and not device_ip.startswith(expected_prefix):
            device_name = device.get("name", device_id)
            zone_name = zone.get("name", zone_id)
            errors.append(
                f"Device '{device_name}' has IP {device_ip} but is in zone "
                f"'{zone_name}' (expected {expected_prefix}x)"
            )

    return errors


# Backward compatibility: Keep the class as an alias
class IPManagementService:
    """Backward compatible class wrapping module functions.

    DEPRECATED: Use module-level functions directly instead.
    This class is maintained for backward compatibility with existing code.
    """

    allocate_range = staticmethod(allocate_ip_range)
    get_allocation = staticmethod(get_ip_allocation)
    get_next_ip = staticmethod(get_next_ip)
    get_zone_subnet = staticmethod(get_zone_subnet)
    list_all_allocations = staticmethod(list_all_ip_allocations)
    release_range = staticmethod(release_ip_range)
    assign_zone_subnet_offsets = staticmethod(assign_zone_subnet_offsets)
    validate_device_zone_ip_consistency = staticmethod(validate_device_zone_ip_consistency)
