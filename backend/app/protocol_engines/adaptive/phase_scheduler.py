"""Deployment phase scheduler for sequential lifecycle phase cycling.

Tracks elapsed deployment time and cycles through phases like
startup → steady_state → maintenance → shutdown, applying distinct
traffic rate multipliers per phase.

Unlike TrafficSchedule (wall-clock time-of-day), this operates on
elapsed deployment time and supports sequential cycling.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DeploymentPhase:
    """A single phase in the deployment lifecycle."""

    phase_id: str  # e.g. "startup", "steady_state"
    name: str  # e.g. "System Startup"
    duration_seconds: float  # how long this phase lasts
    rate_multiplier: float  # traffic rate (0.1 = 10%, 1.0 = normal)
    active_flow_percent: float = 100.0  # 0-100
    behaviors: list[str] = field(default_factory=list)
    protocol_patterns: dict[str, str] = field(default_factory=dict)
    color: str = "#1890ff"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DeploymentPhase:
        return cls(
            phase_id=d.get("phase_id", d.get("id", "")),
            name=d.get("name", ""),
            duration_seconds=float(d.get("duration_seconds", 300)),
            rate_multiplier=float(d.get("rate_multiplier", d.get("traffic_multiplier", 1.0))),
            active_flow_percent=float(d.get("active_flow_percent", 100.0)),
            behaviors=d.get("behaviors", []),
            protocol_patterns=d.get("protocol_patterns", {}),
            color=d.get("color", "#1890ff"),
        )


class PhaseScheduler:
    """Elapsed-time phase scheduler for deployment lifecycle.

    Cycles through a sequence of phases based on time elapsed since
    the deployment started. Supports cycling (repeat after last phase),
    skip/force/pause controls.

    Thread safety: all methods are called from the orchestrator thread
    except get_phase_info() which may be called from the status reporter.
    Read-only methods are safe without locks (Python GIL).
    """

    def __init__(self, phases: list[DeploymentPhase], cycle: bool = True) -> None:
        if not phases:
            raise ValueError("PhaseScheduler requires at least one phase")

        self._phases = phases
        self._cycle = cycle
        self._start_time = time.monotonic()
        self._time_offset: float = 0.0  # for skip/force adjustments
        self._paused = False
        self._pause_time: float = 0.0  # monotonic time when paused
        self._forced_phase_id: str | None = None
        self._last_phase_id: str = ""  # track transitions for logging

        self._cycle_duration = sum(p.duration_seconds for p in phases)
        if self._cycle_duration <= 0:
            raise ValueError("Total phase duration must be positive")

        logger.info(
            f"PhaseScheduler initialized: {len(phases)} phases, "
            f"cycle_duration={self._cycle_duration:.0f}s, cycle={cycle}"
        )

    @property
    def phases(self) -> list[DeploymentPhase]:
        return self._phases

    @property
    def cycle_duration(self) -> float:
        return self._cycle_duration

    def _elapsed(self) -> float:
        """Get elapsed time in seconds, accounting for pause and offset."""
        if self._paused:
            return self._pause_time - self._start_time + self._time_offset
        return time.monotonic() - self._start_time + self._time_offset

    def get_current_phase(self) -> DeploymentPhase | None:
        """Get the current deployment phase based on elapsed time.

        Returns:
            Current phase, or None if all phases are done (non-cycling mode).
        """
        # Check forced override
        if self._forced_phase_id:
            for p in self._phases:
                if p.phase_id == self._forced_phase_id:
                    return p
            # Unknown forced phase — clear it
            self._forced_phase_id = None

        elapsed = self._elapsed()

        if not self._cycle and elapsed >= self._cycle_duration:
            # Non-cycling: stay on last phase
            return self._phases[-1]

        # Find current phase within cycle
        position = elapsed % self._cycle_duration if self._cycle else elapsed
        accumulated = 0.0

        for phase in self._phases:
            accumulated += phase.duration_seconds
            if position < accumulated:
                # Log phase transitions
                if phase.phase_id != self._last_phase_id:
                    if self._last_phase_id:
                        logger.info(
                            f"Phase transition: {self._last_phase_id} → {phase.phase_id} "
                            f"(rate={phase.rate_multiplier}x)"
                        )
                    self._last_phase_id = phase.phase_id
                return phase

        # Shouldn't reach here, but return last phase as fallback
        return self._phases[-1]

    def get_phase_info(self) -> dict[str, Any]:
        """Get detailed info about current phase state for status reporting.

        Safe to call from any thread (read-only snapshot).
        """
        phase = self.get_current_phase()
        if not phase:
            return {"active": False}

        elapsed = self._elapsed()
        cycle_count = int(elapsed / self._cycle_duration) if self._cycle else 0

        # Calculate progress within current phase
        position = elapsed % self._cycle_duration if self._cycle else min(elapsed, self._cycle_duration)
        accumulated = 0.0
        phase_start = 0.0
        phase_index = 0

        for i, p in enumerate(self._phases):
            if p.phase_id == phase.phase_id and accumulated + p.duration_seconds > position:
                phase_start = accumulated
                phase_index = i
                break
            accumulated += p.duration_seconds

        phase_elapsed = position - phase_start
        phase_progress = min(100.0, (phase_elapsed / phase.duration_seconds) * 100.0)
        phase_remaining = max(0.0, phase.duration_seconds - phase_elapsed)

        return {
            "active": True,
            "phase_id": phase.phase_id,
            "name": phase.name,
            "color": phase.color,
            "rate_multiplier": phase.rate_multiplier,
            "progress_pct": round(phase_progress, 1),
            "elapsed_s": round(phase_elapsed, 1),
            "remaining_s": round(phase_remaining, 1),
            "duration_s": phase.duration_seconds,
            "cycle_count": cycle_count,
            "total_phases": len(self._phases),
            "phase_index": phase_index,
            "cycling": self._cycle,
            "paused": self._paused,
            "forced": self._forced_phase_id is not None,
            "behaviors": phase.behaviors,
            "phases": [
                {
                    "phase_id": p.phase_id,
                    "name": p.name,
                    "color": p.color,
                    "duration_s": p.duration_seconds,
                    "rate_multiplier": p.rate_multiplier,
                }
                for p in self._phases
            ],
        }

    def skip_to_next(self) -> None:
        """Advance to the next phase boundary."""
        elapsed = self._elapsed()
        position = elapsed % self._cycle_duration if self._cycle else elapsed
        accumulated = 0.0

        for phase in self._phases:
            accumulated += phase.duration_seconds
            if position < accumulated:
                # Jump to end of current phase
                skip_amount = accumulated - position
                self._time_offset += skip_amount
                self._forced_phase_id = None  # clear any force
                logger.info(f"Skipped {skip_amount:.1f}s to next phase")
                return

    def force_phase(self, phase_id: str) -> bool:
        """Force a specific phase regardless of elapsed time.

        The override is cleared when skip_to_next() is called or
        when clear_force() is called.

        Returns:
            True if phase_id was found, False otherwise.
        """
        for p in self._phases:
            if p.phase_id == phase_id:
                self._forced_phase_id = phase_id
                logger.info(f"Forced phase: {phase_id}")
                return True
        logger.warning(f"Unknown phase_id for force: {phase_id}")
        return False

    def clear_force(self) -> None:
        """Clear any forced phase override."""
        if self._forced_phase_id:
            logger.info(f"Cleared forced phase: {self._forced_phase_id}")
            self._forced_phase_id = None

    def pause(self) -> None:
        """Pause phase cycling (freeze elapsed time)."""
        if not self._paused:
            self._paused = True
            self._pause_time = time.monotonic()
            logger.info("Phase cycling paused")

    def resume(self) -> None:
        """Resume phase cycling after pause."""
        if self._paused:
            # Adjust start_time to account for pause duration
            pause_duration = time.monotonic() - self._pause_time
            self._start_time += pause_duration
            self._paused = False
            logger.info(f"Phase cycling resumed (paused for {pause_duration:.1f}s)")
