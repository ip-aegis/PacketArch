# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Time-of-day traffic scheduling for realistic macro-level traffic shaping.

Simulates time-of-day patterns: morning startup ramp, daytime steady state,
shift changes, overnight reduced polling. Runs autonomously on the agent
using wall clock time — works even if the server disconnects.

For PCAP (timed) mode, maps simulation time to a 24-hour cycle.
"""

import hashlib
import logging
import time
from typing import Any

from app.protocol_engines.adaptive.types import ScheduleConfig, SchedulePhase

logger = logging.getLogger(__name__)

# Built-in schedule presets
SCHEDULE_PRESETS: dict[str, list[dict[str, Any]]] = {
    "industrial_24h": [
        {"name": "overnight", "hours": [0, 6], "rate": 0.3, "active": 60},
        {"name": "morning_ramp", "hours": [6, 8], "rate": 0.7, "active": 85},
        {"name": "day_shift", "hours": [8, 16], "rate": 1.0, "active": 100},
        {"name": "shift_change", "hours": [16, 17], "rate": 1.2, "active": 100},
        {"name": "evening", "hours": [17, 22], "rate": 0.6, "active": 75},
        {"name": "night_ramp", "hours": [22, 24], "rate": 0.4, "active": 65},
    ],
    "office_hours": [
        {"name": "off_hours", "hours": [0, 7], "rate": 0.2, "active": 40},
        {"name": "business", "hours": [7, 18], "rate": 1.0, "active": 100},
        {"name": "evening", "hours": [18, 24], "rate": 0.3, "active": 50},
    ],
    "data_center": [
        {"name": "low_load", "hours": [0, 6], "rate": 0.7, "active": 90},
        {"name": "ramp_up", "hours": [6, 9], "rate": 0.9, "active": 95},
        {"name": "peak", "hours": [9, 17], "rate": 1.0, "active": 100},
        {"name": "ramp_down", "hours": [17, 21], "rate": 0.85, "active": 95},
        {"name": "night", "hours": [21, 24], "rate": 0.7, "active": 90},
    ],
    "constant": [],  # No schedule — always 1.0
}

# Default phase returned when no schedule is active
_DEFAULT_PHASE = SchedulePhase(
    name="default",
    hours=(0, 24),
    rate_multiplier=1.0,
    active_flow_percent=100.0,
)


class TrafficSchedule:
    """Time-of-day traffic schedule that cycles automatically.

    Uses wall clock time so a deployment started at 2pm will immediately
    be in the correct schedule phase for that time of day.
    """

    def __init__(self, config: ScheduleConfig) -> None:
        self._config = config
        self._phases: list[SchedulePhase] = []
        self._transition_s = config.transition_minutes * 60.0
        self._tz_offset_s = config.timezone_offset_hours * 3600.0

        # Load from preset if specified, otherwise use explicit phases
        if config.preset and config.preset in SCHEDULE_PRESETS:
            preset_data = SCHEDULE_PRESETS[config.preset]
            self._phases = [SchedulePhase.from_dict(p) for p in preset_data]
            logger.info(f"Loaded schedule preset: {config.preset} ({len(self._phases)} phases)")
        elif config.phases:
            self._phases = list(config.phases)
            logger.info(f"Loaded custom schedule with {len(self._phases)} phases")

        # Sort phases by start hour for binary search
        self._phases.sort(key=lambda p: p.hours[0])

    def get_current_phase(self, override: str | None = None) -> SchedulePhase:
        """Determine the current schedule phase.

        Args:
            override: If set, force this phase name regardless of time.

        Returns:
            Current SchedulePhase with potentially interpolated rate_multiplier
            at phase boundaries.
        """
        if not self._phases:
            return _DEFAULT_PHASE

        # Handle manual override
        if override:
            for phase in self._phases:
                if phase.name == override:
                    return phase
            # Unknown override name — fall through to time-based

        current_hour = self._get_current_hour()
        phase = self._find_phase(current_hour)

        if phase is None:
            return _DEFAULT_PHASE

        # Smooth interpolation at phase boundaries
        if self._transition_s > 0:
            return self._interpolate_at_boundary(phase, current_hour)

        return phase

    def should_flow_be_active(self, flow_id: str, total_flows: int) -> bool:
        """Determine if a flow should be actively polling in the current phase.

        Uses consistent hashing so the same flows are always active/dormant
        at a given percentage — prevents flapping.

        Args:
            flow_id: Flow identifier
            total_flows: Total number of flows in the scenario

        Returns:
            True if the flow should be actively polling
        """
        if not self._phases:
            return True

        phase = self.get_current_phase()
        if phase.active_flow_percent >= 100.0:
            return True
        if phase.active_flow_percent <= 0.0:
            return False

        # Consistent hash: same flow_id always gets same position 0-99
        hash_val = int(hashlib.md5(flow_id.encode()).hexdigest()[:8], 16) % 100
        return hash_val < phase.active_flow_percent

    def get_rate_multiplier(self) -> float:
        """Convenience: get current rate multiplier."""
        return self.get_current_phase().rate_multiplier

    def _get_current_hour(self) -> float:
        """Get current hour of day (0.0-24.0) adjusted for timezone."""
        now = time.time() + self._tz_offset_s
        # Extract hour as float (e.g. 14.5 = 2:30 PM)
        day_seconds = now % 86400
        return day_seconds / 3600.0

    def _find_phase(self, hour: float) -> SchedulePhase | None:
        """Find the phase that contains the given hour.

        Args:
            hour: Hour of day (0.0-24.0)

        Returns:
            Matching phase or None
        """
        for phase in self._phases:
            start, end = phase.hours
            if start <= hour < end:
                return phase
        return None

    def _interpolate_at_boundary(
        self,
        current_phase: SchedulePhase,
        current_hour: float,
    ) -> SchedulePhase:
        """Smoothly interpolate rate_multiplier at phase boundaries.

        If we're within transition_minutes of a phase boundary, linearly
        interpolate between the previous and current phase's multiplier.

        Returns a modified SchedulePhase with interpolated values.
        """
        transition_hours = self._transition_s / 3600.0
        start_hour = current_phase.hours[0]

        # How far into the phase are we?
        hours_into_phase = current_hour - start_hour

        if hours_into_phase < transition_hours:
            # We're in the transition zone — interpolate from previous phase
            prev_phase = self._find_previous_phase(current_phase)
            if prev_phase and prev_phase.name != current_phase.name:
                t = hours_into_phase / transition_hours  # 0.0 to 1.0
                # Smooth step (ease-in-out) instead of linear
                t = t * t * (3.0 - 2.0 * t)

                interp_rate = (
                    prev_phase.rate_multiplier * (1.0 - t)
                    + current_phase.rate_multiplier * t
                )
                interp_active = (
                    prev_phase.active_flow_percent * (1.0 - t)
                    + current_phase.active_flow_percent * t
                )

                return SchedulePhase(
                    name=f"{prev_phase.name}->{current_phase.name}",
                    hours=current_phase.hours,
                    rate_multiplier=interp_rate,
                    active_flow_percent=interp_active,
                )

        return current_phase

    def _find_previous_phase(self, current: SchedulePhase) -> SchedulePhase | None:
        """Find the phase immediately before the current one."""
        if not self._phases:
            return None

        idx = None
        for i, phase in enumerate(self._phases):
            if phase.name == current.name and phase.hours == current.hours:
                idx = i
                break

        if idx is None:
            return None
        if idx == 0:
            # Wrap around to last phase (previous day's last phase)
            return self._phases[-1]
        return self._phases[idx - 1]
