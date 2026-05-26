# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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

    # Enrich deployments with scenario names + mode flags from DB. The mode
    # flags drive the badges shown on each Live Traffic deployment card.
    deployments = snapshot.get("deployments", [])
    all_ids = [d["scenario_id"] for d in deployments if d.get("scenario_id")]
    if all_ids:
        try:
            from sqlalchemy import select

            # Single DB hit for name + vertical + definition. The
            # dashboard cards then get modes + a vertical pill + a
            # static protocol-mix fallback without a second round-trip.
            async with async_session_maker() as db:
                result = await db.execute(
                    select(
                        Scenario.id, Scenario.name,
                        Scenario.vertical, Scenario.definition,
                    ).where(Scenario.id.in_(all_ids))
                )
                rows_by_id = {str(row[0]): row for row in result.all()}

            for d in deployments:
                row = rows_by_id.get(d["scenario_id"])
                if not row:
                    continue
                _, name, vertical, definition = row
                if not d.get("scenario_name") and name:
                    d["scenario_name"] = name
                    traffic_dashboard.set_scenario_name(d["scenario_id"], name)
                definition = definition or {}
                d["vertical"] = vertical
                d["scenario_modes"] = {
                    "clean_demo_mode": bool(
                        definition.get("clean_demo_mode", False)
                    ),
                    "broadcast_traffic_enabled": bool(
                        definition.get("broadcast_traffic_enabled", True)
                    ),
                    "cell_isolation_mode": str(
                        (definition.get("cell_isolation") or {}).get("mode", "off")
                    ),
                }
                # Static protocol mix from the scenario definition. The
                # live `protocol_breakdown` field still wins for runtime
                # rates; this is a cheap fallback when an agent hasn't
                # yet reported a breakdown.
                proto_counts: dict[str, int] = {}
                devices = definition.get("devices") or {}
                device_iter = (
                    devices.values() if isinstance(devices, dict) else devices
                )
                for dev in device_iter:
                    if not isinstance(dev, dict):
                        continue
                    for p in (dev.get("protocols") or []):
                        if isinstance(p, str) and p:
                            proto_counts[p] = proto_counts.get(p, 0) + 1
                d["scenario_protocol_mix"] = sorted(
                    [{"protocol": p, "device_count": c}
                     for p, c in proto_counts.items()],
                    key=lambda r: r["device_count"], reverse=True,
                )
        except Exception as e:
            logger.error(f"Failed to fetch scenario names/modes: {e}")

    # Enrich with health data
    health_statuses = health_monitor.get_all_health_statuses()
    recent_events = health_monitor.get_events(limit=10)
    snapshot["health"] = {
        "agent_statuses": {str(k): v.value for k, v in health_statuses.items()},
        "recent_events": [e.to_dict() for e in recent_events],
        "unacknowledged_count": health_monitor.get_unacknowledged_count(),
    }

    return snapshot
