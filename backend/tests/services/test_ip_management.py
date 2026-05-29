# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for IP management service.

Tests cover both pure utility functions (no DB required) and
async database functions (using mocks for DB operations).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ip_management import (
    allocate_ip_range,
    assign_zone_subnet_offsets,
    get_ip_allocation,
    get_next_ip,
    get_zone_subnet,
    list_all_ip_allocations,
    release_ip_range,
    validate_device_zone_ip_consistency,
    IPManagementService,
)


# =============================================================================
# Pure function tests (no database required)
# =============================================================================


class TestGetZoneSubnet:
    """Test get_zone_subnet pure function."""

    def test_basic_zone_subnet(self):
        """Test basic zone subnet generation."""
        result = get_zone_subnet(range_index=1, zone_offset=0)
        assert result["subnet"] == "10.1.0.0/24"
        assert result["gateway"] == "10.1.0.1"
        assert result["subnet_mask"] == "255.255.255.0"
        assert result["start_offset"] == 10

    def test_zone_subnet_different_range(self):
        """Test zone subnet with different range index."""
        result = get_zone_subnet(range_index=100, zone_offset=0)
        assert result["subnet"] == "10.100.0.0/24"
        assert result["gateway"] == "10.100.0.1"

    def test_zone_subnet_with_offset(self):
        """Test zone subnet with non-zero zone offset."""
        result = get_zone_subnet(range_index=5, zone_offset=10)
        assert result["subnet"] == "10.5.10.0/24"
        assert result["gateway"] == "10.5.10.1"

    def test_zone_subnet_max_offset(self):
        """Test zone subnet with maximum zone offset (255)."""
        result = get_zone_subnet(range_index=1, zone_offset=255)
        assert result["subnet"] == "10.1.255.0/24"
        assert result["gateway"] == "10.1.255.1"

    def test_zone_subnet_max_range(self):
        """Test zone subnet with maximum range index (254)."""
        result = get_zone_subnet(range_index=254, zone_offset=0)
        assert result["subnet"] == "10.254.0.0/24"
        assert result["gateway"] == "10.254.0.1"

    def test_zone_subnet_min_range(self):
        """Test zone subnet with minimum range index (1)."""
        result = get_zone_subnet(range_index=1, zone_offset=0)
        assert result["subnet"] == "10.1.0.0/24"
        assert result["gateway"] == "10.1.0.1"

    def test_zone_subnet_returns_dict(self):
        """Test that zone subnet returns all expected keys."""
        result = get_zone_subnet(range_index=1, zone_offset=0)
        assert "subnet" in result
        assert "gateway" in result
        assert "subnet_mask" in result
        assert "start_offset" in result


class TestAssignZoneSubnetOffsets:
    """Test assign_zone_subnet_offsets pure function."""

    def test_basic_assignment(self):
        """Test basic sequential zone assignment."""
        zones = [
            {"name": "Zone A"},
            {"name": "Zone B"},
            {"name": "Zone C"},
        ]
        result = assign_zone_subnet_offsets(zones, range_index=5)

        assert len(result) == 3
        assert result[0]["subnet_offset"] == 0
        assert result[1]["subnet_offset"] == 1
        assert result[2]["subnet_offset"] == 2

    def test_network_config_populated(self):
        """Test that network config is populated for each zone."""
        zones = [{"name": "Zone A"}]
        result = assign_zone_subnet_offsets(zones, range_index=3)

        assert "network" in result[0]
        network = result[0]["network"]
        assert network["subnet"] == "10.3.0.0/24"
        assert network["gateway"] == "10.3.0.1"
        assert network["subnet_offset"] == 0

    def test_preserves_existing_offset(self):
        """Test that existing subnet_offset is preserved."""
        zones = [
            {"name": "Zone A", "subnet_offset": 10},
            {"name": "Zone B"},
        ]
        result = assign_zone_subnet_offsets(zones, range_index=5)

        assert result[0]["subnet_offset"] == 10
        assert result[0]["network"]["subnet"] == "10.5.10.0/24"
        # Second zone gets sequential offset (index 1)
        assert result[1]["subnet_offset"] == 1

    def test_empty_zones(self):
        """Test assignment with empty zone list."""
        result = assign_zone_subnet_offsets([], range_index=1)
        assert result == []

    def test_modifies_zones_in_place(self):
        """Test that original zones list is modified in place."""
        zones = [{"name": "Zone A"}]
        result = assign_zone_subnet_offsets(zones, range_index=1)
        assert result is zones
        assert "subnet_offset" in zones[0]
        assert "network" in zones[0]

    def test_multiple_ranges(self):
        """Test with different range indices produce correct subnets."""

        result1 = assign_zone_subnet_offsets([{"name": "Z1"}], range_index=1)
        result2 = assign_zone_subnet_offsets([{"name": "Z2"}], range_index=200)

        assert result1[0]["network"]["subnet"] == "10.1.0.0/24"
        assert result2[0]["network"]["subnet"] == "10.200.0.0/24"


class TestValidateDeviceZoneIpConsistency:
    """Test validate_device_zone_ip_consistency pure function."""

    def test_valid_device_ip(self):
        """Test valid device IP in correct zone."""
        devices = {
            "dev-1": {
                "name": "PLC-1",
                "zoneId": "zone-1",
                "network": {"ipAddress": "10.5.0.10"},
            },
        }
        zones = {
            "zone-1": {
                "name": "Production",
                "subnet_offset": 0,
                "network": {"subnet_offset": 0},
            },
        }
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert errors == []

    def test_invalid_device_ip(self):
        """Test device IP not matching zone subnet."""
        devices = {
            "dev-1": {
                "name": "PLC-1",
                "zoneId": "zone-1",
                "network": {"ipAddress": "10.5.99.10"},  # Wrong subnet
            },
        }
        zones = {
            "zone-1": {
                "name": "Production",
                "subnet_offset": 0,
                "network": {"subnet_offset": 0},
            },
        }
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert len(errors) == 1
        assert "PLC-1" in errors[0]
        assert "10.5.99.10" in errors[0]

    def test_device_with_wrong_range_index(self):
        """Test device IP with wrong range index."""
        devices = {
            "dev-1": {
                "name": "PLC-1",
                "zoneId": "zone-1",
                "network": {"ipAddress": "10.99.0.10"},  # Wrong range
            },
        }
        zones = {
            "zone-1": {
                "name": "Production",
                "subnet_offset": 0,
                "network": {"subnet_offset": 0},
            },
        }
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert len(errors) == 1

    def test_device_in_nonexistent_zone(self):
        """Test device referencing a non-existent zone is skipped."""
        devices = {
            "dev-1": {
                "name": "PLC-1",
                "zoneId": "zone-nonexistent",
                "network": {"ipAddress": "10.5.0.10"},
            },
        }
        zones = {
            "zone-1": {
                "name": "Production",
                "subnet_offset": 0,
            },
        }
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        # Should be skipped, not an error
        assert errors == []

    def test_device_without_zone_id(self):
        """Test device without zoneId is skipped."""
        devices = {
            "dev-1": {
                "name": "PLC-1",
                "network": {"ipAddress": "10.5.0.10"},
            },
        }
        zones = {}
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert errors == []

    def test_device_without_ip(self):
        """Test device without ipAddress is skipped."""
        devices = {
            "dev-1": {
                "name": "PLC-1",
                "zoneId": "zone-1",
                "network": {},
            },
        }
        zones = {
            "zone-1": {
                "name": "Production",
                "subnet_offset": 0,
                "network": {"subnet_offset": 0},
            },
        }
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert errors == []

    def test_zone_without_subnet_offset(self):
        """Test zone without subnet_offset is skipped."""
        devices = {
            "dev-1": {
                "name": "PLC-1",
                "zoneId": "zone-1",
                "network": {"ipAddress": "10.5.0.10"},
            },
        }
        zones = {
            "zone-1": {
                "name": "Production",
                # No subnet_offset or network.subnet_offset
            },
        }
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert errors == []

    def test_multiple_devices_mixed_validity(self):
        """Test multiple devices where some are valid and some are not."""
        devices = {
            "dev-1": {
                "name": "PLC-1",
                "zoneId": "zone-1",
                "network": {"ipAddress": "10.5.0.10"},
            },
            "dev-2": {
                "name": "PLC-2",
                "zoneId": "zone-1",
                "network": {"ipAddress": "10.5.99.20"},  # Wrong subnet
            },
            "dev-3": {
                "name": "PLC-3",
                "zoneId": "zone-2",
                "network": {"ipAddress": "10.5.1.30"},
            },
        }
        zones = {
            "zone-1": {
                "name": "Zone 1",
                "subnet_offset": 0,
                "network": {"subnet_offset": 0},
            },
            "zone-2": {
                "name": "Zone 2",
                "subnet_offset": 1,
                "network": {"subnet_offset": 1},
            },
        }
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert len(errors) == 1
        assert "PLC-2" in errors[0]

    def test_empty_devices(self):
        """Test with empty devices dict."""
        errors = validate_device_zone_ip_consistency({}, {}, range_index=5)
        assert errors == []

    def test_subnet_offset_from_zone_field(self):
        """Test subnet_offset read from zone field (not network)."""
        devices = {
            "dev-1": {
                "name": "PLC-1",
                "zoneId": "zone-1",
                "network": {"ipAddress": "10.5.3.10"},
            },
        }
        zones = {
            "zone-1": {
                "name": "Zone 1",
                "subnet_offset": 3,
                # network dict exists but has no subnet_offset
                "network": {},
            },
        }
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert errors == []

    def test_fallback_device_id_in_error(self):
        """Test that device_id is used in error if name is missing."""
        devices = {
            "dev-1": {
                # No "name" field
                "zoneId": "zone-1",
                "network": {"ipAddress": "10.5.99.10"},
            },
        }
        zones = {
            "zone-1": {
                "name": "Production",
                "subnet_offset": 0,
                "network": {"subnet_offset": 0},
            },
        }
        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert len(errors) == 1
        assert "dev-1" in errors[0]


# =============================================================================
# Async database function tests (using mocks)
# =============================================================================


class TestAllocateIpRange:
    """Test allocate_ip_range async function."""

    @pytest.mark.asyncio
    async def test_allocate_first_range(self):
        """Test allocating the first available range."""
        mock_db = AsyncMock()

        # Mock: no existing allocations
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        scenario_id = uuid.uuid4()
        allocation = await allocate_ip_range(mock_db, scenario_id)

        assert allocation.scenario_id == scenario_id
        assert allocation.range_index == 1
        assert allocation.cidr_range == "10.1.0.0/16"
        assert allocation.next_host_offset == 10
        mock_db.add.assert_called_once_with(allocation)

    @pytest.mark.asyncio
    async def test_allocate_next_available_range(self):
        """Test allocating the next range when some are taken."""
        mock_db = AsyncMock()

        # Mock: indices 1, 2, 3 are used
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1,), (2,), (3,)]
        mock_db.execute.return_value = mock_result

        scenario_id = uuid.uuid4()
        allocation = await allocate_ip_range(mock_db, scenario_id)

        assert allocation.range_index == 4
        assert allocation.cidr_range == "10.4.0.0/16"

    @pytest.mark.asyncio
    async def test_allocate_fills_gaps(self):
        """Test that allocation fills gaps in used indices."""
        mock_db = AsyncMock()

        # Mock: indices 1, 3, 5 are used (gaps at 2, 4)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1,), (3,), (5,)]
        mock_db.execute.return_value = mock_result

        scenario_id = uuid.uuid4()
        allocation = await allocate_ip_range(mock_db, scenario_id)

        assert allocation.range_index == 2  # Fills the gap

    @pytest.mark.asyncio
    async def test_allocate_all_ranges_exhausted(self):
        """Test error when all 254 ranges are allocated."""
        mock_db = AsyncMock()

        # Mock: all 254 indices used
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(i,) for i in range(1, 255)]
        mock_db.execute.return_value = mock_result

        scenario_id = uuid.uuid4()
        with pytest.raises(ValueError, match="No available IP ranges"):
            await allocate_ip_range(mock_db, scenario_id)


class TestGetIpAllocation:
    """Test get_ip_allocation async function."""

    @pytest.mark.asyncio
    async def test_get_existing_allocation(self):
        """Test getting an existing allocation."""
        mock_db = AsyncMock()
        mock_allocation = MagicMock()
        mock_allocation.range_index = 5
        mock_allocation.cidr_range = "10.5.0.0/16"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_allocation
        mock_db.execute.return_value = mock_result

        scenario_id = uuid.uuid4()
        result = await get_ip_allocation(mock_db, scenario_id)

        assert result is mock_allocation
        assert result.range_index == 5

    @pytest.mark.asyncio
    async def test_get_nonexistent_allocation(self):
        """Test getting allocation for scenario without one."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        scenario_id = uuid.uuid4()
        result = await get_ip_allocation(mock_db, scenario_id)
        assert result is None


class TestGetNextIp:
    """Test get_next_ip async function."""

    @pytest.mark.asyncio
    async def test_get_first_ip(self):
        """Test getting the first IP (offset=10)."""
        mock_db = AsyncMock()
        mock_allocation = MagicMock()
        mock_allocation.range_index = 5
        mock_allocation.next_host_offset = 10
        mock_allocation.cidr_range = "10.5.0.0/16"

        # Mock get_ip_allocation
        with patch("app.services.ip_management.get_ip_allocation") as mock_get:
            mock_get.return_value = mock_allocation
            scenario_id = uuid.uuid4()
            result = await get_next_ip(mock_db, scenario_id)

        assert result["ip_address"] == "10.5.0.10"
        assert result["subnet_mask"] == "255.255.255.0"
        assert result["gateway"] == "10.5.0.1"
        assert result["cidr"] == "10.5.0.0/16"
        # Offset should be incremented
        assert mock_allocation.next_host_offset == 11

    @pytest.mark.asyncio
    async def test_get_sequential_ips(self):
        """Test sequential IP allocation increments offset."""
        mock_db = AsyncMock()
        mock_allocation = MagicMock()
        mock_allocation.range_index = 3
        mock_allocation.next_host_offset = 10
        mock_allocation.cidr_range = "10.3.0.0/16"

        with patch("app.services.ip_management.get_ip_allocation") as mock_get:
            mock_get.return_value = mock_allocation

            scenario_id = uuid.uuid4()
            result1 = await get_next_ip(mock_db, scenario_id)
            assert result1["ip_address"] == "10.3.0.10"

            # Manually check offset incremented
            assert mock_allocation.next_host_offset == 11

    @pytest.mark.asyncio
    async def test_get_ip_no_allocation(self):
        """Test error when scenario has no allocation."""
        mock_db = AsyncMock()

        with patch("app.services.ip_management.get_ip_allocation") as mock_get:
            mock_get.return_value = None
            scenario_id = uuid.uuid4()

            with pytest.raises(ValueError, match="no IP range allocated"):
                await get_next_ip(mock_db, scenario_id)

    @pytest.mark.asyncio
    async def test_ip_skips_network_address(self):
        """Test that .0 addresses are skipped."""
        mock_db = AsyncMock()
        mock_allocation = MagicMock()
        mock_allocation.range_index = 1
        # offset 256 would give 10.1.1.0 (network), should skip to .1
        mock_allocation.next_host_offset = 256
        mock_allocation.cidr_range = "10.1.0.0/16"

        with patch("app.services.ip_management.get_ip_allocation") as mock_get:
            mock_get.return_value = mock_allocation
            result = await get_next_ip(mock_db, uuid.uuid4())

        assert result["ip_address"] == "10.1.1.1"

    @pytest.mark.asyncio
    async def test_ip_skips_broadcast_address(self):
        """Test that .255 addresses are skipped."""
        mock_db = AsyncMock()
        mock_allocation = MagicMock()
        mock_allocation.range_index = 1
        # offset 255 would give 10.1.0.255 (broadcast), should skip to next subnet .1
        mock_allocation.next_host_offset = 255
        mock_allocation.cidr_range = "10.1.0.0/16"

        with patch("app.services.ip_management.get_ip_allocation") as mock_get:
            mock_get.return_value = mock_allocation
            result = await get_next_ip(mock_db, uuid.uuid4())

        assert result["ip_address"] == "10.1.1.1"

    @pytest.mark.asyncio
    async def test_ip_range_exhausted(self):
        """Test error when IP range is fully exhausted."""
        mock_db = AsyncMock()
        mock_allocation = MagicMock()
        mock_allocation.range_index = 1
        # offset that would push subnet beyond 255
        mock_allocation.next_host_offset = 256 * 256  # 65536 -> subnet = 256
        mock_allocation.cidr_range = "10.1.0.0/16"

        with patch("app.services.ip_management.get_ip_allocation") as mock_get:
            mock_get.return_value = mock_allocation

            with pytest.raises(ValueError, match="IP range exhausted"):
                await get_next_ip(mock_db, uuid.uuid4())


class TestReleaseIpRange:
    """Test release_ip_range async function."""

    @pytest.mark.asyncio
    async def test_release_existing_range(self):
        """Test releasing an existing IP range allocation."""
        mock_db = AsyncMock()
        mock_allocation = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_allocation
        mock_db.execute.return_value = mock_result

        scenario_id = uuid.uuid4()
        result = await release_ip_range(mock_db, scenario_id)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_allocation)

    @pytest.mark.asyncio
    async def test_release_nonexistent_range(self):
        """Test releasing a range that doesn't exist returns False."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        scenario_id = uuid.uuid4()
        result = await release_ip_range(mock_db, scenario_id)

        assert result is False
        mock_db.delete.assert_not_called()


class TestListAllIpAllocations:
    """Test list_all_ip_allocations async function."""

    @pytest.mark.asyncio
    async def test_list_empty(self):
        """Test listing allocations when none exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        result = await list_all_ip_allocations(mock_db)

        assert result["items"] == []
        assert result["total"] == 0
        assert len(result["available_ranges"]) == 254  # 1-254 all available

    @pytest.mark.asyncio
    async def test_list_with_allocations(self):
        """Test listing allocations with some existing."""
        mock_db = AsyncMock()

        mock_alloc1 = MagicMock()
        mock_alloc1.id = uuid.uuid4()
        mock_alloc1.scenario_id = uuid.uuid4()
        mock_alloc1.range_index = 1
        mock_alloc1.cidr_range = "10.1.0.0/16"
        mock_alloc1.next_host_offset = 15
        mock_alloc1.created_at = "2024-01-01"

        mock_alloc2 = MagicMock()
        mock_alloc2.id = uuid.uuid4()
        mock_alloc2.scenario_id = uuid.uuid4()
        mock_alloc2.range_index = 5
        mock_alloc2.cidr_range = "10.5.0.0/16"
        mock_alloc2.next_host_offset = 20
        mock_alloc2.created_at = "2024-01-02"

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (mock_alloc1, "Scenario A"),
            (mock_alloc2, "Scenario B"),
        ]
        mock_db.execute.return_value = mock_result

        result = await list_all_ip_allocations(mock_db)

        assert result["total"] == 2
        assert len(result["items"]) == 2
        assert result["items"][0]["range_index"] == 1
        assert result["items"][0]["scenario_name"] == "Scenario A"
        assert result["items"][1]["range_index"] == 5
        assert result["items"][1]["scenario_name"] == "Scenario B"

        # Check available ranges excludes used indices
        assert 1 not in result["available_ranges"]
        assert 5 not in result["available_ranges"]
        assert 2 in result["available_ranges"]
        assert len(result["available_ranges"]) == 252  # 254 - 2 used


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestIPManagementServiceBackwardCompat:
    """Test backward-compatible class wrapper."""

    def test_class_exists(self):
        """Test IPManagementService class exists."""
        assert IPManagementService is not None

    def test_static_method_aliases(self):
        """Test that class methods are aliases for module functions."""
        assert IPManagementService.allocate_range is allocate_ip_range
        assert IPManagementService.get_allocation is get_ip_allocation
        assert IPManagementService.get_next_ip is get_next_ip
        assert IPManagementService.get_zone_subnet is get_zone_subnet
        assert IPManagementService.list_all_allocations is list_all_ip_allocations
        assert IPManagementService.release_range is release_ip_range
        assert IPManagementService.assign_zone_subnet_offsets is assign_zone_subnet_offsets
        assert (
            IPManagementService.validate_device_zone_ip_consistency
            is validate_device_zone_ip_consistency
        )


# =============================================================================
# Edge Case and Integration Tests
# =============================================================================


class TestIpAddressCalculation:
    """Test IP address calculation edge cases."""

    def test_zone_subnet_various_offsets(self):
        """Test zone subnet calculation with various offsets."""
        for offset in [0, 1, 50, 100, 200, 255]:
            result = get_zone_subnet(range_index=10, zone_offset=offset)
            assert f"10.10.{offset}.0/24" == result["subnet"]
            assert f"10.10.{offset}.1" == result["gateway"]

    def test_zone_subnet_various_ranges(self):
        """Test zone subnet calculation with various range indices."""
        for idx in [1, 50, 100, 200, 254]:
            result = get_zone_subnet(range_index=idx, zone_offset=0)
            assert f"10.{idx}.0.0/24" == result["subnet"]
            assert f"10.{idx}.0.1" == result["gateway"]

    def test_assign_many_zones(self):
        """Test assigning subnets to many zones."""
        zones = [{"name": f"Zone {i}"} for i in range(50)]
        result = assign_zone_subnet_offsets(zones, range_index=1)
        assert len(result) == 50
        for i, zone in enumerate(result):
            assert zone["subnet_offset"] == i
            assert zone["network"]["subnet"] == f"10.1.{i}.0/24"

    def test_validation_with_many_devices(self):
        """Test validation with many devices in correct zones."""
        devices = {}
        zones = {}
        for i in range(10):
            zone_id = f"zone-{i}"
            zones[zone_id] = {
                "name": f"Zone {i}",
                "subnet_offset": i,
                "network": {"subnet_offset": i},
            }
            for j in range(5):
                dev_id = f"dev-{i}-{j}"
                devices[dev_id] = {
                    "name": f"Device {i}-{j}",
                    "zoneId": zone_id,
                    "network": {"ipAddress": f"10.5.{i}.{10 + j}"},
                }

        errors = validate_device_zone_ip_consistency(devices, zones, range_index=5)
        assert errors == []
