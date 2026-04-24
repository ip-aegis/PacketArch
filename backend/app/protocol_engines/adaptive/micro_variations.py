# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Micro-level traffic variations for realistic OT traffic generation.

Introduces subtle, always-on variations that make traffic look non-robotic:
- Timing drift: bounded random walk simulating crystal oscillator drift
- Retransmissions: occasional duplicate packets
- Connection resets: periodic TCP reset/reconnect cycles
- Vendor personality: per-vendor behavioral traits affecting drift patterns
"""

import logging
import random
import time
from typing import Any

from app.protocol_engines.adaptive.types import MicroVariationConfig

logger = logging.getLogger(__name__)

# Self-contained vendor personality traits — no scipy/ai_timing dependency.
# consistency (0-1): higher = less timing variation
# warmup_factor (>1): initial polls are slower by this factor
# eager: device tends to drift toward shorter intervals
VENDOR_TRAITS: dict[str, dict[str, Any]] = {
    "siemens": {"consistency": 0.95, "warmup_factor": 1.1, "eager": True},
    "rockwell": {"consistency": 0.85, "warmup_factor": 1.2, "eager": False},
    "allen-bradley": {"consistency": 0.85, "warmup_factor": 1.2, "eager": False},
    "schneider": {"consistency": 0.88, "warmup_factor": 1.15, "eager": False},
    "abb": {"consistency": 0.92, "warmup_factor": 1.1, "eager": False},
    "honeywell": {"consistency": 0.87, "warmup_factor": 1.25, "eager": False},
    "emerson": {"consistency": 0.90, "warmup_factor": 1.15, "eager": False},
    "ge": {"consistency": 0.89, "warmup_factor": 1.2, "eager": False},
    "mitsubishi": {"consistency": 0.93, "warmup_factor": 1.1, "eager": True},
    "omron": {"consistency": 0.91, "warmup_factor": 1.1, "eager": True},
    "beckhoff": {"consistency": 0.94, "warmup_factor": 1.05, "eager": True},
    "phoenix contact": {"consistency": 0.90, "warmup_factor": 1.15, "eager": False},
    "wago": {"consistency": 0.88, "warmup_factor": 1.15, "eager": False},
    "moxa": {"consistency": 0.87, "warmup_factor": 1.2, "eager": False},
    "advantech": {"consistency": 0.86, "warmup_factor": 1.2, "eager": False},
}

# Default personality for unknown vendors
_DEFAULT_TRAITS: dict[str, Any] = {
    "consistency": 0.90,
    "warmup_factor": 1.15,
    "eager": False,
}


class _FlowDriftState:
    """Per-flow state for timing drift random walk."""

    __slots__ = (
        "drift_pct", "poll_count", "traits",
        "last_reset_time", "next_reset_after",
    )

    def __init__(self, traits: dict[str, Any], wall_time: float, reset_range: tuple[float, float]):
        self.drift_pct: float = 0.0
        self.poll_count: int = 0
        self.traits = traits
        self.last_reset_time = wall_time
        self.next_reset_after = random.uniform(reset_range[0], reset_range[1])


class MicroVariationEngine:
    """Introduces realistic micro-level traffic variations per flow.

    All methods are called from the orchestrator thread — no locking needed.
    Uses stdlib random only (numpy optional, not required).
    """

    def __init__(self, config: MicroVariationConfig) -> None:
        self._config = config
        self._rng = random.Random()
        self._flow_states: dict[str, _FlowDriftState] = {}

        # Counters for status reporting
        self._drift_adjustments = 0
        self._retransmits_injected = 0
        self._connection_resets = 0

    def register_flow(
        self,
        flow_id: str,
        vendor: str | None,
        base_poll_ms: float,
    ) -> None:
        """Register a flow for micro-variation tracking.

        Args:
            flow_id: Unique flow identifier
            vendor: Device vendor name (for personality lookup)
            base_poll_ms: Base poll interval in milliseconds
        """
        traits = _DEFAULT_TRAITS
        if vendor and self._config.vendor_personality_enabled:
            vendor_key = vendor.lower().strip()
            # Try exact match first, then prefix match
            if vendor_key in VENDOR_TRAITS:
                traits = VENDOR_TRAITS[vendor_key]
            else:
                for key, val in VENDOR_TRAITS.items():
                    if vendor_key.startswith(key) or key.startswith(vendor_key):
                        traits = val
                        break

        state = _FlowDriftState(
            traits=traits,
            wall_time=time.monotonic(),
            reset_range=self._config.reset_interval_range_s,
        )
        self._flow_states[flow_id] = state

    def adjust_poll_interval(self, flow_id: str, base_ms: float) -> float:
        """Apply timing drift to a poll interval.

        Uses a bounded random walk (Brownian motion) that simulates
        crystal oscillator drift. The walk is clamped to ±max_percent
        and biased by vendor personality traits.

        Args:
            flow_id: Flow identifier
            base_ms: Base poll interval in milliseconds

        Returns:
            Adjusted interval with drift applied
        """
        if not self._config.timing_drift_enabled:
            return base_ms

        state = self._flow_states.get(flow_id)
        if not state:
            return base_ms

        state.poll_count += 1
        traits = state.traits
        consistency = traits["consistency"]
        max_pct = self._config.timing_drift_max_percent

        # Random walk step: tiny relative to base, dampened by consistency
        # Higher consistency = smaller steps = more stable timing
        step = self._rng.gauss(0, base_ms * 0.002)
        step *= (1.0 - consistency)

        # Eager devices bias toward shorter intervals (negative drift)
        if traits["eager"]:
            step -= base_ms * 0.0005 * (1.0 - consistency)

        # Mean-reversion force: drift tends back toward zero
        # Stronger when further from center, prevents permanent offset
        reversion_strength = 0.02
        step -= state.drift_pct * reversion_strength

        # Apply step and clamp
        state.drift_pct += step
        state.drift_pct = max(-max_pct, min(max_pct, state.drift_pct))

        # Warmup factor: first 10 polls are slower
        warmup = 1.0
        if state.poll_count <= 10 and traits["warmup_factor"] > 1.0:
            progress = state.poll_count / 10.0
            warmup = traits["warmup_factor"] - progress * (traits["warmup_factor"] - 1.0)

        adjusted = base_ms * (1.0 + state.drift_pct / 100.0) * warmup
        self._drift_adjustments += 1

        return max(1.0, adjusted)

    def should_retransmit(self, flow_id: str) -> bool:
        """Check if this poll cycle should simulate a retransmission.

        Args:
            flow_id: Flow identifier

        Returns:
            True if a retransmission should be injected
        """
        if not self._config.retransmit_enabled:
            return False

        if self._rng.random() < self._config.retransmit_probability:
            self._retransmits_injected += 1
            return True
        return False

    def should_connection_reset(self, flow_id: str, wall_time: float) -> bool:
        """Check if enough time has elapsed for a TCP connection reset.

        Args:
            flow_id: Flow identifier
            wall_time: Current wall time (time.monotonic())

        Returns:
            True if a connection reset should be triggered
        """
        if not self._config.connection_reset_enabled:
            return False

        state = self._flow_states.get(flow_id)
        if not state:
            return False

        elapsed = wall_time - state.last_reset_time
        if elapsed >= state.next_reset_after:
            state.last_reset_time = wall_time
            state.next_reset_after = self._rng.uniform(
                self._config.reset_interval_range_s[0],
                self._config.reset_interval_range_s[1],
            )
            self._connection_resets += 1
            logger.debug(f"Connection reset triggered for flow {flow_id} after {elapsed:.0f}s")
            return True
        return False

    def get_stats(self) -> dict[str, int]:
        """Get counters for status reporting."""
        return {
            "drift_adjustments": self._drift_adjustments,
            "retransmits": self._retransmits_injected,
            "connection_resets": self._connection_resets,
        }
