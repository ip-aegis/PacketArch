"""Live traffic dashboard API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter

from app.core.database import async_session_maker
from app.models.scenario import Scenario
from app.models.traffic_agent import TrafficAgent
from app.services.agent_manager import agent_manager
from app.services.health_monitor import health_monitor
from app.services.traffic_dashboard import traffic_dashboard

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/live")
async def get_live_dashboard() -> dict[str, Any]:
    """Get live traffic dashboard data.

    Returns aggregate stats, per-agent stats, and per-deployment stats
    including protocol breakdowns and time-series data for charts.
    """
    # Build agent connection info with names from DB
    connections = agent_manager.get_all_connections()
    agent_connections = []

    if connections:
        # Fetch agent names from DB
        agent_ids = [conn.agent_id for conn in connections]
        agent_names: dict[str, str] = {}

        try:
            from sqlalchemy import select

            async with async_session_maker() as db:
                result = await db.execute(
                    select(TrafficAgent.id, TrafficAgent.name).where(
                        TrafficAgent.id.in_(agent_ids)
                    )
                )
                for row in result.all():
                    agent_names[str(row[0])] = row[1]
        except Exception as e:
            logger.error(f"Failed to fetch agent names: {e}")

        for conn in connections:
            agent_connections.append({
                "agent_id": str(conn.agent_id),
                "agent_name": agent_names.get(str(conn.agent_id), "Unknown"),
                "hostname": conn.hostname,
                "cpu_percent": conn.cpu_percent,
                "memory_percent": conn.memory_percent,
                "is_online": True,
                "running_scenarios": list(conn.running_scenarios),
            })

    snapshot = traffic_dashboard.get_dashboard_snapshot(
        agent_connections=agent_connections,
    )

    # Enrich deployments with scenario names from DB
    deployments = snapshot.get("deployments", [])
    unnamed_ids = [
        d["scenario_id"] for d in deployments if not d.get("scenario_name")
    ]
    if unnamed_ids:
        try:
            from sqlalchemy import select

            async with async_session_maker() as db:
                result = await db.execute(
                    select(Scenario.id, Scenario.name).where(
                        Scenario.id.in_(unnamed_ids)
                    )
                )
                scenario_names = {str(row[0]): row[1] for row in result.all()}

            for d in deployments:
                if not d.get("scenario_name"):
                    name = scenario_names.get(d["scenario_id"])
                    if name:
                        d["scenario_name"] = name
                        # Also update the in-memory cache so subsequent polls don't re-query
                        traffic_dashboard.set_scenario_name(d["scenario_id"], name)
        except Exception as e:
            logger.error(f"Failed to fetch scenario names: {e}")

    # Enrich with health data
    health_statuses = health_monitor.get_all_health_statuses()
    recent_events = health_monitor.get_events(limit=10)
    snapshot["health"] = {
        "agent_statuses": {str(k): v.value for k, v in health_statuses.items()},
        "recent_events": [e.to_dict() for e in recent_events],
        "unacknowledged_count": health_monitor.get_unacknowledged_count(),
    }

    return snapshot
