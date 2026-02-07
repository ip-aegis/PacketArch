"""IP Management API routes."""

from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import NotFoundError, ValidationError
from app.models.scenario import Scenario
from app.schemas.ip_management import (
    IPRangeAllocationResponse,
    IPRangeListResponse,
    NextIPResponse,
    ScenarioIPInfoResponse,
)
from app.services.ip_management import IPManagementService

router = APIRouter(prefix="/ip-management", tags=["IP Management"])


@router.get("", response_model=IPRangeListResponse)
async def list_ip_allocations(
    db: DBSession,
    current_user: CurrentUser,
) -> IPRangeListResponse:
    """List all IP range allocations across scenarios."""
    result = await IPManagementService.list_all_allocations(db)

    # Convert to response model
    items = [
        IPRangeAllocationResponse(
            id=item["id"],
            scenario_id=item["scenario_id"],
            scenario_name=item["scenario_name"],
            range_index=item["range_index"],
            cidr_range=item["cidr_range"],
            next_host_offset=item["next_host_offset"],
            created_at=item["created_at"],
        )
        for item in result["items"]
    ]

    return IPRangeListResponse(
        items=items,
        total=result["total"],
        available_ranges=result["available_ranges"],
    )


@router.get("/scenario/{scenario_id}", response_model=ScenarioIPInfoResponse)
async def get_scenario_ip_info(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ScenarioIPInfoResponse:
    """Get IP range info for a specific scenario."""
    # Get scenario (check ownership)
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", str(scenario_id))

    allocation = await IPManagementService.get_allocation(db, scenario_id)

    if not allocation:
        raise NotFoundError("IP range allocation", str(scenario_id))

    # Count devices with IPs
    devices = scenario.definition.get("devices", {})
    devices_with_ips = sum(
        1
        for d in devices.values()
        if d.get("network", {}).get("ipAddress")
    )

    # Calculate next available IP info
    range_idx = allocation.range_index
    offset = allocation.next_host_offset
    subnet = offset // 256
    host = offset % 256
    if host == 0:
        host = 1
    if host == 255:
        subnet += 1
        host = 1

    next_ip = f"10.{range_idx}.{subnet}.{host}"
    gateway = f"10.{range_idx}.{subnet}.1"

    return ScenarioIPInfoResponse(
        scenario_id=scenario_id,
        scenario_name=scenario.name,
        cidr_range=allocation.cidr_range,
        range_index=allocation.range_index,
        devices_with_ips=devices_with_ips,
        next_available_ip=next_ip,
        gateway=gateway,
    )


@router.get("/scenario/{scenario_id}/next-ip", response_model=NextIPResponse)
async def get_next_ip(
    scenario_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> NextIPResponse:
    """Get next available IP address for a scenario and increment the offset."""
    # Verify ownership
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", str(scenario_id))

    try:
        next_ip = await IPManagementService.get_next_ip(db, scenario_id)
        await db.commit()  # Commit the offset increment
        return NextIPResponse(**next_ip)
    except ValueError as e:
        raise ValidationError(str(e))
