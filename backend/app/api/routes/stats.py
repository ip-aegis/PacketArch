"""Stats API routes for dashboard statistics."""

import os
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.models.scenario import Scenario
from app.models.device_profile import DeviceProfile
from app.core.config import settings

router = APIRouter(prefix="/stats", tags=["Stats"])


class OverviewStatsResponse(BaseModel):
    """Overview statistics for dashboard."""

    scenarios: int
    devices: int
    protocols: int
    pcaps: int


@router.get("/overview", response_model=OverviewStatsResponse)
async def get_overview_stats(
    db: DBSession,
    current_user: CurrentUser,
) -> OverviewStatsResponse:
    """Get overview statistics for the dashboard.

    Returns counts of scenarios, device profiles, protocols, and generated PCAPs.
    """
    # Count user's scenarios
    scenario_count = await db.scalar(
        select(func.count(Scenario.id)).where(Scenario.user_id == current_user.id)
    ) or 0

    # Count device profiles (global, not user-specific)
    device_count = await db.scalar(select(func.count(DeviceProfile.id))) or 0

    # Count unique protocols used across user's scenarios
    protocols_set: set[str] = set()
    result = await db.execute(
        select(Scenario.definition).where(Scenario.user_id == current_user.id)
    )
    for (definition,) in result:
        if definition:
            # Extract protocols from devices
            devices = definition.get("devices", {})
            for device in devices.values() if isinstance(devices, dict) else devices:
                if isinstance(device, dict):
                    device_protocols = device.get("protocols", [])
                    if isinstance(device_protocols, list):
                        protocols_set.update(device_protocols)
            # Extract protocols from flows
            flows = definition.get("flows", {})
            for flow in flows.values() if isinstance(flows, dict) else flows:
                if isinstance(flow, dict):
                    protocol = flow.get("protocol")
                    if protocol:
                        protocols_set.add(protocol)

    # Count PCAP files in output directory
    pcap_count = 0
    output_dir = Path(settings.output_dir) / "pcap"
    if output_dir.exists():
        pcap_count = len(list(output_dir.glob("*.pcap"))) + len(list(output_dir.glob("*.pcapng")))

    return OverviewStatsResponse(
        scenarios=scenario_count,
        devices=device_count,
        protocols=len(protocols_set),
        pcaps=pcap_count,
    )
