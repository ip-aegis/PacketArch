"""IP Range Management Service.

Handles allocation and management of IP ranges for scenarios.
Each scenario gets a unique 10.{n}.0.0/16 range where n is 1-254.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ip_range_allocation import IPRangeAllocation
from app.models.scenario import Scenario


class IPManagementService:
    """Service for managing scenario IP ranges."""

    @staticmethod
    async def allocate_range(
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

    @staticmethod
    async def get_allocation(
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

    @staticmethod
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
        allocation = await IPManagementService.get_allocation(db, scenario_id)

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

    @staticmethod
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

    @staticmethod
    async def list_all_allocations(db: AsyncSession) -> dict[str, Any]:
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

    @staticmethod
    async def release_range(db: AsyncSession, scenario_id: uuid.UUID) -> bool:
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
