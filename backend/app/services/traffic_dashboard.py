# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""In-memory traffic dashboard aggregation service.

Stores per-deployment stats and rolling time-series for the live traffic
dashboard. Fed from agent STATUS messages via agent_hub.py.
No database persistence — data rebuilds naturally as agents reconnect.
"""

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)

# Maximum time-series points per deployment (5 min at ~5s intervals)
MAX_TIME_SERIES_POINTS = 60


@dataclass
class DeploymentDashboardStats:
    """Rich stats for a single active deployment."""

    scenario_id: str
    agent_id: str
    agent_name: str
    scenario_name: str | None = None
    state: str = "starting"
    packets_sent: int = 0
    bytes_sent: int = 0
    flow_count: int = 0
    packets_per_second: float = 0.0
    bytes_per_second: float = 0.0
    protocol_breakdown: dict[str, dict] | None = None
    adaptation: dict | None = None
    attack: dict | None = None
    started_at: datetime | None = None
    last_updated: datetime | None = None
    time_series: deque = field(
        default_factory=lambda: deque(maxlen=MAX_TIME_SERIES_POINTS)
    )


class TrafficDashboardService:
    """In-memory service for live traffic dashboard data.

    Thread-safe via a lock. Updated from the WebSocket message handler
    and read by the REST API endpoint.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Key is scenario_id (str) — one deployment per scenario
        self._deployment_stats: dict[str, DeploymentDashboardStats] = {}

    def update_from_status(
        self,
        agent_id: str | UUID,
        scenario_id: str,
        message: dict,
        agent_name: str | None = None,
        scenario_name: str | None = None,
    ) -> None:
        """Update stats from an agent STATUS message.

        Args:
            agent_id: Agent UUID
            scenario_id: Scenario UUID
            message: Raw STATUS message dict from agent
            agent_name: Agent display name
            scenario_name: Scenario display name
        """
        now = datetime.now(timezone.utc)
        state = message.get("state", "unknown")
        agent_id_str = str(agent_id)

        with self._lock:
            ds = self._deployment_stats.get(scenario_id)
            if ds is None:
                ds = DeploymentDashboardStats(
                    scenario_id=scenario_id,
                    agent_id=agent_id_str,
                    agent_name=agent_name or "Unknown",
                    scenario_name=scenario_name,
                    started_at=now,
                )
                self._deployment_stats[scenario_id] = ds

            ds.state = state
            ds.packets_sent = message.get("packets_sent", ds.packets_sent)
            ds.bytes_sent = message.get("bytes_sent", ds.bytes_sent)
            ds.flow_count = message.get("flow_count", ds.flow_count)
            ds.packets_per_second = message.get("packets_per_second", ds.packets_per_second)
            ds.bytes_per_second = message.get("bytes_per_second", ds.bytes_per_second)
            ds.protocol_breakdown = message.get("protocol_breakdown", ds.protocol_breakdown)
            if "adaptation" in message:
                ds.adaptation = message["adaptation"]
            if "attack" in message:
                ds.attack = message["attack"]
            ds.last_updated = now

            if agent_name:
                ds.agent_name = agent_name
            if scenario_name:
                ds.scenario_name = scenario_name

            # Append time-series data point
            ds.time_series.append({
                "t": now.isoformat(),
                "pps": ds.packets_per_second,
                "bps": ds.bytes_per_second,
            })

            # Remove deployment if it reached a terminal state
            if state in ("stopped", "error", "disconnected"):
                # Keep it for a moment so the dashboard can show final state
                pass

    def get_stall_candidates(self, stall_threshold_seconds: float) -> list[dict]:
        """Get deployments that may be stalled (running but no recent packets).

        Args:
            stall_threshold_seconds: Seconds of 0 pps before considered stalled.

        Returns:
            List of dicts with scenario_id, agent_id, agent_name, pps, elapsed_seconds.
        """
        now = datetime.now(timezone.utc)
        candidates = []
        with self._lock:
            for sid, ds in self._deployment_stats.items():
                if ds.state == "running" and ds.last_updated is not None:
                    elapsed = (now - ds.last_updated).total_seconds()
                    if ds.packets_per_second == 0 and elapsed > stall_threshold_seconds:
                        candidates.append({
                            "scenario_id": sid,
                            "agent_id": ds.agent_id,
                            "agent_name": ds.agent_name,
                            "pps": ds.packets_per_second,
                            "last_updated": ds.last_updated,
                            "elapsed_seconds": elapsed,
                        })
        return candidates

    def set_scenario_name(self, scenario_id: str, name: str) -> None:
        """Set the scenario name for a deployment (called from dashboard route)."""
        with self._lock:
            ds = self._deployment_stats.get(scenario_id)
            if ds is not None:
                ds.scenario_name = name

    def remove_deployment(self, scenario_id: str) -> None:
        """Remove a deployment from the dashboard (e.g., on disconnect)."""
        with self._lock:
            self._deployment_stats.pop(scenario_id, None)

    def remove_agent_deployments(self, agent_id: str | UUID) -> None:
        """Remove all deployments for a disconnected agent."""
        agent_id_str = str(agent_id)
        with self._lock:
            to_remove = [
                sid for sid, ds in self._deployment_stats.items()
                if ds.agent_id == agent_id_str
            ]
            for sid in to_remove:
                del self._deployment_stats[sid]

    def get_deployment(self, scenario_id: str) -> dict | None:
        """Get deployment stats dict for a scenario.

        Used by attack_service to read current attack state.

        Returns:
            Dict with deployment fields (including 'attack') or None
        """
        with self._lock:
            ds = self._deployment_stats.get(scenario_id)
            if ds is None:
                return None
            return {
                "scenario_id": ds.scenario_id,
                "state": ds.state,
                "attack": ds.attack,
                "adaptation": ds.adaptation,
            }

    def get_dashboard_snapshot(
        self,
        agent_connections: list[dict] | None = None,
    ) -> dict:
        """Get complete dashboard data for the API.

        Args:
            agent_connections: List of agent connection info dicts from agent_manager.
                Each should have: agent_id, agent_name, hostname, cpu_percent,
                memory_percent, is_online, running_scenarios.

        Returns:
            Full dashboard response dict.
        """
        with self._lock:
            # Active deployments (exclude terminal states)
            active = {
                sid: ds for sid, ds in self._deployment_stats.items()
                if ds.state in ("starting", "running")
            }

            # Aggregate stats
            total_pps = sum(ds.packets_per_second for ds in active.values())
            total_bps = sum(ds.bytes_per_second for ds in active.values())
            total_packets = sum(ds.packets_sent for ds in active.values())
            total_bytes = sum(ds.bytes_sent for ds in active.values())

            # Build deployment list
            deployments = []
            now = datetime.now(timezone.utc)
            for ds in active.values():
                uptime = (now - ds.started_at).total_seconds() if ds.started_at else 0
                deployments.append({
                    "scenario_id": ds.scenario_id,
                    "scenario_name": ds.scenario_name,
                    "agent_id": ds.agent_id,
                    "agent_name": ds.agent_name,
                    "state": ds.state,
                    "packets_sent": ds.packets_sent,
                    "bytes_sent": ds.bytes_sent,
                    "flow_count": ds.flow_count,
                    "packets_per_second": ds.packets_per_second,
                    "bytes_per_second": ds.bytes_per_second,
                    "uptime_seconds": round(uptime),
                    "protocol_breakdown": ds.protocol_breakdown,
                    "adaptation": ds.adaptation,
                    "attack": ds.attack,
                    "time_series": list(ds.time_series),
                })

        # Build agents list from connections
        agents = []
        connected_count = 0
        if agent_connections:
            for conn in agent_connections:
                is_online = conn.get("is_online", False)
                if is_online:
                    connected_count += 1
                agent_id_str = str(conn.get("agent_id", ""))
                # Sum pps for this agent from active deployments
                agent_pps = sum(
                    d["packets_per_second"] for d in deployments
                    if d["agent_id"] == agent_id_str
                )
                agent_bps = sum(
                    d["bytes_per_second"] for d in deployments
                    if d["agent_id"] == agent_id_str
                )
                agent_active = sum(
                    1 for d in deployments
                    if d["agent_id"] == agent_id_str
                )
                agents.append({
                    "agent_id": agent_id_str,
                    "agent_name": conn.get("agent_name", "Unknown"),
                    "hostname": conn.get("hostname"),
                    "cpu_percent": conn.get("cpu_percent", 0.0),
                    "memory_percent": conn.get("memory_percent", 0.0),
                    "is_online": is_online,
                    "active_deployments": agent_active,
                    "total_packets_per_second": round(agent_pps, 1),
                    "total_bytes_per_second": round(agent_bps, 1),
                    "kind": conn.get("kind", "manual"),
                    "lab_name": conn.get("lab_name"),
                    "group_key": conn.get("group_key"),
                    "group_label": conn.get("group_label"),
                    "is_conductor": conn.get("is_conductor", False),
                })

        return {
            "aggregate": {
                "total_packets_per_second": round(total_pps, 1),
                "total_bytes_per_second": round(total_bps, 1),
                "active_deployments": len(active),
                "connected_agents": connected_count,
                "total_packets_sent": total_packets,
                "total_bytes_sent": total_bytes,
            },
            "agents": agents,
            "deployments": deployments,
        }


# Global singleton
traffic_dashboard = TrafficDashboardService()
