# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Adaptive traffic generation package.

Provides micro-level timing variations, time-of-day scheduling,
and server-directed traffic adaptation for realistic OT traffic.

Uses only stdlib random + optional numpy. No scipy dependency.
"""

from app.protocol_engines.adaptive.types import (
    AdaptiveConfig,
    AdaptiveState,
    Directive,
    MicroVariationConfig,
    PhaseScheduleConfig,
    ScheduleConfig,
    SchedulePhase,
)

# Controller may fail on import if something goes wrong — caller should
# handle gracefully (adaptive is always optional).
from app.protocol_engines.adaptive.controller import AdaptiveController
from app.protocol_engines.adaptive.phase_scheduler import DeploymentPhase, PhaseScheduler

__all__ = [
    "AdaptiveConfig",
    "AdaptiveController",
    "AdaptiveState",
    "DeploymentPhase",
    "Directive",
    "MicroVariationConfig",
    "PhaseScheduleConfig",
    "PhaseScheduler",
    "ScheduleConfig",
    "SchedulePhase",
]
