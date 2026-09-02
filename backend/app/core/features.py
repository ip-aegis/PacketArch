# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Feature-flag surface.

Single source of truth for the flags exposed at /api/v1/about.features and
consumed by the frontend to hide UI. New flags go here, wired through to
config.Settings and the frontend feature types.

Usage in routes:
    from app.api.deps import RequireAIEnabled  # 503s when ai_enabled=false
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.config import settings


class Features(BaseModel):
    """Runtime feature flags. Serialized verbatim to the frontend."""

    ai_enabled: bool
    live_traffic_enabled: bool
    multi_sensor_topology_enabled: bool
    mimic_enabled: bool


def get_features() -> Features:
    """Resolve current feature flags from settings. Cheap — call per-request."""
    return Features(
        ai_enabled=settings.ai_enabled,
        live_traffic_enabled=settings.live_traffic_enabled,
        multi_sensor_topology_enabled=settings.multi_sensor_topology_enabled,
        mimic_enabled=settings.mimic_enabled,
    )
