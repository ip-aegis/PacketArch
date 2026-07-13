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
        # Fetch agent names + kind linkage from DB. Kind drives the dashboard's
        # local-vs-remote split: LOCAL agents (local sensor labs) all run on
        # the PacketArch host and share its CPU/RAM, so the UI shows one host
        # gauge for them; CML/manual agents run elsewhere and keep their own.
        agent_ids = [conn.agent_id for conn in connections]
        agent_names: dict[str, str] = {}
        agent_kinds: dict[str, str] = {}
        agent_labs: dict[str, str] = {}   # agent_id -> local lab name
        group_labels: dict[str, str] = {}  # scenario short-id -> scenario name

        try:
            import re

            from sqlalchemy import String, cast, func, select

            from app.models.local_lab import LocalLab

            async with async_session_maker() as db:
                result = await db.execute(
                    select(
                        TrafficAgent.id, TrafficAgent.name,
                        TrafficAgent.local_lab_id, TrafficAgent.cml_lab_id,
                    ).where(TrafficAgent.id.in_(agent_ids))
                )
                for row in result.all():
                    agent_names[str(row[0])] = row[1]
                    agent_kinds[str(row[0])] = (
                        "local" if row[2] else "cml" if row[3] else "manual"
                    )

                # Topology grouping: labs named `topo-<scn8>-<span>` group by
                # scenario (the `-core` lab's agent is that group's conductor).
                result = await db.execute(
                    select(LocalLab.agent_id, LocalLab.name).where(
                        LocalLab.agent_id.in_(agent_ids)
                    )
                )
                for aid, lab_name in result.all():
                    agent_labs[str(aid)] = lab_name
                short_ids = {
                    m.group(1)
                    for name in agent_labs.values()
                    if (m := re.match(r"^topo-([0-9a-f]{8})-", name))
                }
                if short_ids:
                    result = await db.execute(
                        select(Scenario.id, Scenario.name).where(
                            func.left(cast(Scenario.id, String), 8).in_(short_ids)
                        )
                    )
                    for sid, sname in result.all():
                        group_labels[str(sid)[:8]] = sname
        except Exception as e:
            logger.error(f"Failed to fetch agent names: {e}")

        import re

        for conn in connections:
            aid = str(conn.agent_id)
            lab_name = agent_labs.get(aid)
            group_key = None
            group_label = None
            is_conductor = False
            if lab_name:
                m = re.match(r"^topo-([0-9a-f]{8})-(.+)$", lab_name)
                if m:
                    group_key = m.group(1)
                    group_label = group_labels.get(group_key)
                    is_conductor = m.group(2) == "core"
            agent_connections.append({
                "agent_id": aid,
                "agent_name": agent_names.get(aid, "Unknown"),
                "hostname": conn.hostname,
                "cpu_percent": conn.cpu_percent,
                "memory_percent": conn.memory_percent,
                "is_online": True,
                "running_scenarios": list(conn.running_scenarios),
                "kind": agent_kinds.get(aid, "manual"),
                "lab_name": lab_name,
                "group_key": group_key,
                "group_label": group_label,
                "is_conductor": is_conductor,
            })

    snapshot = traffic_dashboard.get_dashboard_snapshot(
        agent_connections=agent_connections,
    )

    # Host-level CPU/RAM for the dashboard's local-agents section (all local
    # agents share the PacketArch host, so one gauge covers them all).
    from app.services.host_stats import get_host_stats

    snapshot["host"] = get_host_stats()

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
                cv = definition.get("cyber_vision")
                if cv and cv.get("status"):
                    d["cyber_vision"] = {
                        "status": cv.get("status", "not_started"),
                        "preset_label": cv.get("preset_label"),
                        "subnet": cv.get("subnet"),
                        "group_count": len(cv.get("groups") or {}),
                        "device_count": int(cv.get("device_count") or 0),
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
