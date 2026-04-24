# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Health monitoring API endpoints."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter

from app.core.exceptions import NotFoundError
from app.services.health_monitor import health_monitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health-monitor", tags=["health-monitor"])


@router.get("/events")
async def get_health_events(
    limit: int = 50,
    offset: int = 0,
    severity: str | None = None,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Get health events, most recent first.

    Args:
        limit: Max events to return (default 50)
        offset: Skip this many events
        severity: Filter by severity (info, warning, critical)
        agent_id: Filter by agent UUID
    """
    events = health_monitor.get_events(
        limit=limit,
        offset=offset,
        severity_filter=severity,
        agent_filter=agent_id,
    )
    total = health_monitor.get_events_total(
        severity_filter=severity,
        agent_filter=agent_id,
    )
    return {
        "events": [e.to_dict() for e in events],
        "total": total,
        "unacknowledged_count": health_monitor.get_unacknowledged_count(),
        "counts_by_severity": health_monitor.get_counts_by_severity(),
    }


@router.get("/status")
async def get_health_status() -> dict[str, Any]:
    """Get health status for all tracked agents."""
    details = health_monitor.get_all_health_details()

    summary = {"healthy": 0, "warning": 0, "critical": 0, "offline": 0}
    for agent_detail in details.values():
        status = agent_detail["status"]
        if status in summary:
            summary[status] += 1

    return {
        "agents": details,
        "summary": summary,
        "auto_recovery_enabled": health_monitor.config.auto_recovery_enabled,
        "auto_redeploy_on_reconnect": health_monitor.config.auto_redeploy_on_reconnect,
        "monitoring_active": health_monitor._running,
    }


@router.get("/status/{agent_id}")
async def get_agent_health_status(agent_id: UUID) -> dict[str, Any]:
    """Get health status for a specific agent."""
    detail = health_monitor.get_agent_health_detail(agent_id)
    if detail is None:
        raise NotFoundError(
            "Agent health data not found",
            details={"agent_id": str(agent_id)},
        )
    return {"agent_id": str(agent_id), **detail}


@router.post("/events/{event_id}/acknowledge")
async def acknowledge_event(event_id: str) -> dict[str, Any]:
    """Mark a health event as acknowledged."""
    found = health_monitor.acknowledge_event(event_id)
    if not found:
        raise NotFoundError(
            "Health event not found",
            details={"event_id": event_id},
        )
    return {"acknowledged": True, "event_id": event_id}


@router.delete("/events")
async def clear_events() -> dict[str, Any]:
    """Clear all health events."""
    count = health_monitor.clear_events()
    return {"cleared": count}


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Get current health monitor configuration."""
    return health_monitor.get_config_dict()


@router.put("/config")
async def update_config(updates: dict[str, Any]) -> dict[str, Any]:
    """Update health monitor configuration.

    Accepts a dict of config keys to update. Invalid keys are ignored.
    """
    return health_monitor.update_config(updates)
