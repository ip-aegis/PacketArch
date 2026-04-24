# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Configuration and state types for adaptive traffic generation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MicroVariationConfig:
    """Configuration for micro-level traffic variations."""

    timing_drift_enabled: bool = True
    timing_drift_max_percent: float = 5.0
    retransmit_enabled: bool = True
    retransmit_probability: float = 0.002
    connection_reset_enabled: bool = True
    reset_interval_range_s: tuple[float, float] = (3600.0, 7200.0)
    vendor_personality_enabled: bool = True

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MicroVariationConfig:
        reset_range = d.get("reset_interval_range_s", [3600.0, 7200.0])
        if isinstance(reset_range, list) and len(reset_range) == 2:
            reset_range = (float(reset_range[0]), float(reset_range[1]))
        else:
            reset_range = (3600.0, 7200.0)
        return cls(
            timing_drift_enabled=d.get("timing_drift_enabled", True),
            timing_drift_max_percent=d.get("timing_drift_max_percent", 5.0),
            retransmit_enabled=d.get("retransmit_enabled", True),
            retransmit_probability=d.get("retransmit_probability", 0.002),
            connection_reset_enabled=d.get("connection_reset_enabled", True),
            reset_interval_range_s=reset_range,
            vendor_personality_enabled=d.get("vendor_personality_enabled", True),
        )


@dataclass
class SchedulePhase:
    """A single phase in a traffic schedule."""

    name: str
    hours: tuple[int, int]  # [start_hour, end_hour)
    rate_multiplier: float  # >1 = more traffic, <1 = less
    active_flow_percent: float = 100.0  # 0-100

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SchedulePhase:
        hours = d.get("hours", [0, 24])
        if isinstance(hours, list) and len(hours) == 2:
            hours = (int(hours[0]), int(hours[1]))
        else:
            hours = (0, 24)
        return cls(
            name=d.get("name", "default"),
            hours=hours,
            rate_multiplier=d.get("rate_multiplier", d.get("rate", 1.0)),
            active_flow_percent=d.get("active_flow_percent", d.get("active", 100.0)),
        )


@dataclass
class ScheduleConfig:
    """Configuration for time-of-day traffic scheduling."""

    enabled: bool = False
    timezone_offset_hours: float = 0.0
    phases: list[SchedulePhase] = field(default_factory=list)
    transition_minutes: float = 5.0
    preset: str | None = None  # Name of preset to use

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScheduleConfig:
        phases = [SchedulePhase.from_dict(p) for p in d.get("phases", [])]
        return cls(
            enabled=d.get("enabled", False),
            timezone_offset_hours=d.get("timezone_offset_hours", 0.0),
            phases=phases,
            transition_minutes=d.get("transition_minutes", 5.0),
            preset=d.get("preset"),
        )


@dataclass
class PhaseScheduleConfig:
    """Configuration for deployment phase scheduling.

    Controls sequential phase cycling (startup → steady → maintenance → shutdown)
    during live deployments. Each phase has its own duration, rate multiplier,
    and behavior hints.
    """

    enabled: bool = False
    cycle: bool = True  # Repeat phases after last one completes
    phases: list[dict[str, Any]] = field(default_factory=list)  # Raw phase dicts

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PhaseScheduleConfig:
        return cls(
            enabled=d.get("enabled", False),
            cycle=d.get("cycle", True),
            phases=d.get("phases", []),
        )


@dataclass
class AdaptiveConfig:
    """Top-level adaptive traffic configuration.

    When absent from scenario definition, defaults to enabled with
    micro-variations on and schedule off.
    """

    enabled: bool = True
    micro: MicroVariationConfig = field(default_factory=MicroVariationConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    phase_schedule: PhaseScheduleConfig = field(default_factory=PhaseScheduleConfig)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AdaptiveConfig:
        if not d:
            return cls()
        return cls(
            enabled=d.get("enabled", True),
            micro=MicroVariationConfig.from_dict(d.get("micro", d.get("micro_variations", {}))),
            schedule=ScheduleConfig.from_dict(d.get("schedule", {})),
            phase_schedule=PhaseScheduleConfig.from_dict(d.get("phase_schedule", {})),
        )


@dataclass
class AdaptiveState:
    """Snapshot of adaptive controller state for status reporting."""

    enabled: bool = False
    current_phase: str = "default"
    rate_multiplier: float = 1.0
    active_directive_count: int = 0
    drift_adjustments: int = 0
    retransmits_injected: int = 0
    connection_resets: int = 0
    flow_multipliers: dict[str, float] = field(default_factory=dict)
    # Deployment phase fields
    deployment_phase: str = ""
    deployment_phase_id: str = ""
    deployment_phase_progress: float = 0.0
    deployment_cycle_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "enabled": self.enabled,
            "current_phase": self.current_phase,
            "rate_multiplier": self.rate_multiplier,
            "active_directives": self.active_directive_count,
            "micro_stats": {
                "drift_adjustments": self.drift_adjustments,
                "retransmits": self.retransmits_injected,
                "connection_resets": self.connection_resets,
            },
        }
        if self.deployment_phase:
            d["deployment_phase"] = {
                "name": self.deployment_phase,
                "phase_id": self.deployment_phase_id,
                "progress_pct": self.deployment_phase_progress,
                "cycle_count": self.deployment_cycle_count,
            }
        return d


# Directive types for server -> agent communication
DIRECTIVE_ADJUST_PROTOCOL_RATE = "adjust_protocol_rate"
DIRECTIVE_ADJUST_FLOW_RATE = "adjust_flow_rate"
DIRECTIVE_SET_SCHEDULE_PHASE = "set_schedule_phase"
DIRECTIVE_RESET = "reset_adaptations"
DIRECTIVE_SKIP_PHASE = "skip_phase"
DIRECTIVE_FORCE_PHASE = "force_phase"
DIRECTIVE_PAUSE_PHASES = "pause_phases"
DIRECTIVE_RESUME_PHASES = "resume_phases"


@dataclass
class Directive:
    """A server-sent adaptation directive."""

    type: str
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0
    # Type-specific fields
    protocol: str | None = None
    flow_id: str | None = None
    multiplier: float = 1.0
    phase_name: str | None = None
    reason: str = ""

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds

    @classmethod
    def from_dict(cls, d: dict[str, Any], ttl: float = 300.0) -> Directive:
        return cls(
            type=d.get("type", ""),
            ttl_seconds=ttl,
            protocol=d.get("protocol"),
            flow_id=d.get("flow_id"),
            multiplier=d.get("multiplier", 1.0),
            phase_name=d.get("phase_name"),
            reason=d.get("reason", ""),
        )
