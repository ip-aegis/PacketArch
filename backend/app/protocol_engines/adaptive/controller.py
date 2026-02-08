"""Adaptive traffic controller — composes micro-variations, schedule, and directives.

The controller is called from a single hook point in UnifiedOrchestrator._handle_poll_event()
to adjust poll intervals before the next poll is scheduled. It operates entirely within the
orchestrator thread for per-flow state. Server directives arrive via atomic reference swap
from the async main loop.
"""

import hashlib
import logging
import time
from typing import Any

from app.protocol_engines.adaptive.micro_variations import MicroVariationEngine
from app.protocol_engines.adaptive.phase_scheduler import DeploymentPhase, PhaseScheduler
from app.protocol_engines.adaptive.types import (
    AdaptiveConfig,
    AdaptiveState,
    Directive,
    DIRECTIVE_ADJUST_FLOW_RATE,
    DIRECTIVE_ADJUST_PROTOCOL_RATE,
    DIRECTIVE_FORCE_PHASE,
    DIRECTIVE_PAUSE_PHASES,
    DIRECTIVE_RESET,
    DIRECTIVE_RESUME_PHASES,
    DIRECTIVE_SET_SCHEDULE_PHASE,
    DIRECTIVE_SKIP_PHASE,
)

logger = logging.getLogger(__name__)


class AdaptiveController:
    """Composes micro-variations, schedule, and server directives.

    Thread safety model:
    - adjust_next_poll(), register_flow(), should_retransmit(), should_connection_reset()
      are called from the orchestrator thread only.
    - set_pending_directives() is called from the async main loop (different thread).
      Uses atomic reference swap (Python GIL ensures safety).
    - get_state_snapshot() is called from the status reporter thread.
      Reads are safe without locks since Python dict/int reads are atomic.
    """

    def __init__(self, config: AdaptiveConfig, total_flows: int = 0) -> None:
        self._config = config
        self._total_flows = total_flows
        self._schedule = None  # type: ignore[assignment]  # set lazily if enabled
        self._phase_scheduler: PhaseScheduler | None = None

        # Micro-variation engine
        self._micro: MicroVariationEngine | None = None
        if config.enabled and config.micro.timing_drift_enabled:
            self._micro = MicroVariationEngine(config.micro)

        # Server directive state
        self._pending_directives: list[dict] | None = None  # atomic swap target
        self._active_directives: list[Directive] = []
        self._flow_multipliers: dict[str, float] = {}
        self._protocol_multipliers: dict[str, float] = {}
        self._schedule_override: str | None = None

        # Flow metadata for protocol-based directives
        self._flow_protocols: dict[str, str] = {}  # flow_id -> protocol string

        # State for status reporting
        self._state = AdaptiveState(enabled=config.enabled)

        # Initialize phase scheduler if configured
        if config.phase_schedule.enabled and config.phase_schedule.phases:
            try:
                phases = [DeploymentPhase.from_dict(p) for p in config.phase_schedule.phases]
                self._phase_scheduler = PhaseScheduler(phases, cycle=config.phase_schedule.cycle)
            except Exception as e:
                logger.warning(f"Failed to initialize phase scheduler: {e}")

        # Lazy-load schedule if configured
        if config.schedule.enabled or config.schedule.preset:
            try:
                from app.protocol_engines.adaptive.schedule import TrafficSchedule
                self._schedule = TrafficSchedule(config.schedule)
            except Exception as e:
                logger.warning(f"Failed to initialize traffic schedule: {e}")

        logger.info(
            f"AdaptiveController initialized: "
            f"micro={self._micro is not None}, "
            f"schedule={self._schedule is not None}, "
            f"phase_scheduler={self._phase_scheduler is not None}, "
            f"flows={total_flows}"
        )

    def register_flow(
        self,
        flow_id: str,
        vendor: str | None,
        base_poll_ms: float,
        protocol: str | None = None,
    ) -> None:
        """Register a flow for adaptive tracking.

        Args:
            flow_id: Unique flow identifier
            vendor: Destination device vendor name
            base_poll_ms: Base poll interval in milliseconds
            protocol: Protocol string (e.g. 'modbus_tcp') for directive matching
        """
        if self._micro:
            self._micro.register_flow(flow_id, vendor, base_poll_ms)
        if protocol:
            self._flow_protocols[flow_id] = protocol

    def adjust_next_poll(self, flow_id: str, base_interval_ms: float) -> float:
        """Adjust the next poll interval for a flow.

        Called every poll cycle from the orchestrator thread.
        Composition order: phase (lifecycle) -> schedule (time-of-day) -> directives -> micro (fine).

        Args:
            flow_id: Flow identifier
            base_interval_ms: Base poll interval in milliseconds

        Returns:
            Adjusted interval in milliseconds (minimum 50ms)
        """
        if not self._config.enabled:
            return base_interval_ms

        # Check for pending directives from the async thread
        pending = self._pending_directives
        if pending is not None:
            self._pending_directives = None  # consume
            self._apply_directives(pending)

        # Expire old directives
        self._expire_directives()

        interval = base_interval_ms

        # 0. Deployment phase multiplier (lifecycle sequencing)
        if self._phase_scheduler:
            phase = self._phase_scheduler.get_current_phase()
            if phase:
                self._state.deployment_phase = phase.name
                self._state.deployment_phase_id = phase.phase_id
                info = self._phase_scheduler.get_phase_info()
                self._state.deployment_phase_progress = info.get("progress_pct", 0.0)
                self._state.deployment_cycle_count = info.get("cycle_count", 0)

                # Higher rate_multiplier = more traffic = shorter interval
                interval = interval / max(0.1, phase.rate_multiplier)

                # Check if flow should be dormant in this phase
                if phase.active_flow_percent < 100.0:
                    hash_val = int(hashlib.md5(flow_id.encode()).hexdigest()[:8], 16) % 100
                    if hash_val >= phase.active_flow_percent:
                        return max(50.0, interval * 100)  # effectively pause

        # 1. Schedule multiplier (macro time-of-day shaping)
        if self._schedule:
            phase = self._schedule.get_current_phase(override=self._schedule_override)
            self._state.current_phase = phase.name
            self._state.rate_multiplier = phase.rate_multiplier

            # Higher rate_multiplier = more traffic = shorter interval
            interval = interval / max(0.1, phase.rate_multiplier)

            # Check if this flow should be dormant in current phase
            if not self._schedule.should_flow_be_active(flow_id, self._total_flows):
                return interval * 100  # effectively pause this flow

        # 2. Server directive multipliers (protocol-level and flow-level)
        protocol = self._flow_protocols.get(flow_id, "")
        protocol_mult = self._protocol_multipliers.get(protocol, 1.0)
        flow_mult = self._flow_multipliers.get(flow_id, 1.0)
        combined_mult = protocol_mult * flow_mult

        if combined_mult != 1.0:
            interval = interval / combined_mult

        # 3. Micro-variation drift (smallest effect, applied last)
        if self._micro:
            interval = self._micro.adjust_poll_interval(flow_id, interval)

        return max(50.0, interval)

    def should_retransmit(self, flow_id: str) -> bool:
        """Check if a retransmission should be simulated for this poll."""
        if not self._config.enabled or not self._micro:
            return False
        return self._micro.should_retransmit(flow_id)

    def should_connection_reset(self, flow_id: str) -> bool:
        """Check if a TCP connection reset should be triggered."""
        if not self._config.enabled or not self._micro:
            return False
        return self._micro.should_connection_reset(flow_id, time.monotonic())

    def set_pending_directives(self, directives: list[dict]) -> None:
        """Set pending directives from the async thread.

        Uses atomic reference swap — safe without locks under Python GIL.

        Args:
            directives: List of directive dicts from ADAPT_TRAFFIC message
        """
        self._pending_directives = directives

    def get_state_snapshot(self) -> dict[str, Any]:
        """Get a snapshot of current adaptation state for STATUS messages.

        Safe to call from any thread — reads atomic values only.
        """
        state = AdaptiveState(
            enabled=self._config.enabled,
            current_phase=self._state.current_phase,
            rate_multiplier=self._state.rate_multiplier,
            active_directive_count=len(self._active_directives),
            flow_multipliers=dict(self._flow_multipliers),
            deployment_phase=self._state.deployment_phase,
            deployment_phase_id=self._state.deployment_phase_id,
            deployment_phase_progress=self._state.deployment_phase_progress,
            deployment_cycle_count=self._state.deployment_cycle_count,
        )

        if self._micro:
            stats = self._micro.get_stats()
            state.drift_adjustments = stats["drift_adjustments"]
            state.retransmits_injected = stats["retransmits"]
            state.connection_resets = stats["connection_resets"]

        result = state.to_dict()

        # Include detailed phase info from scheduler
        if self._phase_scheduler:
            result["phase_schedule"] = self._phase_scheduler.get_phase_info()

        return result

    def _apply_directives(self, directive_dicts: list[dict]) -> None:
        """Apply directives from the server.

        Called from the orchestrator thread after atomic swap.
        """
        ttl = 300.0  # default TTL

        for d in directive_dicts:
            directive = Directive.from_dict(d, ttl=ttl)

            if directive.type == DIRECTIVE_RESET:
                self._active_directives.clear()
                self._flow_multipliers.clear()
                self._protocol_multipliers.clear()
                self._schedule_override = None
                logger.info("All adaptive directives cleared")
                continue

            if directive.type == DIRECTIVE_SET_SCHEDULE_PHASE:
                self._schedule_override = directive.phase_name
                logger.info(f"Schedule override set to phase: {directive.phase_name}")
                continue

            if directive.type == DIRECTIVE_SKIP_PHASE:
                if self._phase_scheduler:
                    self._phase_scheduler.skip_to_next()
                    logger.info("Skipped to next deployment phase")
                continue

            if directive.type == DIRECTIVE_FORCE_PHASE:
                if self._phase_scheduler and directive.phase_name:
                    self._phase_scheduler.force_phase(directive.phase_name)
                    logger.info(f"Forced deployment phase: {directive.phase_name}")
                continue

            if directive.type == DIRECTIVE_PAUSE_PHASES:
                if self._phase_scheduler:
                    self._phase_scheduler.pause()
                continue

            if directive.type == DIRECTIVE_RESUME_PHASES:
                if self._phase_scheduler:
                    self._phase_scheduler.resume()
                continue

            if directive.type == DIRECTIVE_ADJUST_PROTOCOL_RATE:
                if directive.protocol:
                    self._protocol_multipliers[directive.protocol] = directive.multiplier
                    logger.info(
                        f"Protocol rate adjusted: {directive.protocol} x{directive.multiplier} "
                        f"({directive.reason})"
                    )

            elif directive.type == DIRECTIVE_ADJUST_FLOW_RATE:
                if directive.flow_id:
                    self._flow_multipliers[directive.flow_id] = directive.multiplier
                    logger.info(
                        f"Flow rate adjusted: {directive.flow_id} x{directive.multiplier} "
                        f"({directive.reason})"
                    )

            self._active_directives.append(directive)

        self._state.active_directive_count = len(self._active_directives)

    def _expire_directives(self) -> None:
        """Remove expired directives and their multipliers."""
        if not self._active_directives:
            return

        before = len(self._active_directives)
        expired = [d for d in self._active_directives if d.is_expired]

        for d in expired:
            self._active_directives.remove(d)
            # Clean up associated multipliers
            if d.type == DIRECTIVE_ADJUST_PROTOCOL_RATE and d.protocol:
                self._protocol_multipliers.pop(d.protocol, None)
            elif d.type == DIRECTIVE_ADJUST_FLOW_RATE and d.flow_id:
                self._flow_multipliers.pop(d.flow_id, None)

        if expired:
            logger.debug(f"Expired {len(expired)} directives ({before} -> {len(self._active_directives)})")
            self._state.active_directive_count = len(self._active_directives)
