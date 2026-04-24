# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Attack orchestrator — manages kill-chain stage progression.

Integrates with :class:`~app.protocol_engines.unified_orchestrator.UnifiedOrchestrator`
by scheduling ``attack_stage_tick`` control events on the shared event heap.
Follows the same composition pattern as
:class:`~app.protocol_engines.adaptive.controller.AdaptiveController`.

Lifecycle::

    1. Created with a playbook + scenario context
    2. Registered with UnifiedOrchestrator → schedules initial tick
    3. Each tick: generate attack packets for current stage, schedule next tick
    4. When stage duration expires: advance to next stage (or stop)
    5. Runtime commands (start/stop/advance/pause) via atomic swap
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Iterator

from app.protocol_engines.external.engine import ExternalCommEngine, ExternalTrafficConfig
from app.protocol_engines.external.ip_pools import get_attack_source_ip
from app.protocol_engines.types import PacketEvent

from .action_registry import (
    ATTACK_FLOW_PREFIX,
    TargetInfo,
    get_action_generator,
)
from .types import (
    AttackAction,
    AttackPlaybook,
    AttackPlaybookConfig,
    AttackState,
    KillChainStage,
)

logger = logging.getLogger(__name__)

# How often the orchestrator ticks (ms) to check stage progress & generate packets
TICK_INTERVAL_MS = 2000.0

# Warm-up delay before the first attack event fires (ms)
DEFAULT_WARMUP_MS = 10_000.0


class AttackOrchestrator:
    """Manages attack playbook execution within the unified orchestrator.

    Thread-safety: the orchestrator thread calls :meth:`handle_tick` and
    :meth:`get_state_snapshot`.  The WebSocket thread calls
    :meth:`set_pending_command`.  Commands are exchanged via Python's
    GIL-guaranteed atomic reference swap (same pattern as
    ``AdaptiveController.set_pending_directives``).
    """

    def __init__(
        self,
        playbook: AttackPlaybook,
        devices: list[dict[str, Any]],
        config: AttackPlaybookConfig | None = None,
    ) -> None:
        self._playbook = playbook
        self._config = config or AttackPlaybookConfig(playbook_id=playbook.playbook_id)
        self._devices = devices

        # Apply stage overrides from config
        self._stages = list(playbook.stages)
        for stage in self._stages:
            override = self._config.stage_overrides.get(stage.stage_id, {})
            if "duration_seconds" in override:
                stage.duration_seconds = int(override["duration_seconds"])

        self._intensity = max(0.1, min(3.0, self._config.intensity))

        # Resolve targets once
        self._all_targets = self._resolve_targets(devices)
        self._attacker_ip = get_attack_source_ip(1)

        # External comm engine for C2/exfil/scan delegations
        self._external_engine = ExternalCommEngine(ExternalTrafficConfig())

        # Runtime state
        self._current_stage_idx = 0
        self._stage_start_monotonic = 0.0
        self._is_active = False
        self._is_paused = False
        self._is_completed = False

        # Counters
        self._actions_completed = 0
        self._packets_generated = 0
        self._stages_completed = 0

        # Atomic command swap
        self._pending_command: dict[str, Any] | None = None

        # Track which actions have been fired in the current stage
        self._stage_actions_fired: set[str] = set()

    # ------------------------------------------------------------------
    # Orchestrator integration
    # ------------------------------------------------------------------

    def schedule_initial_events(
        self,
        scheduler: Any,
        start_time_ms: float,
    ) -> None:
        """Schedule the first attack tick after a warm-up delay.

        Called by ``UnifiedOrchestrator.register_attack_orchestrator()``.
        """
        if self._config.start_mode == "manual":
            logger.info(
                f"Attack playbook '{self._playbook.name}' loaded in manual mode — "
                f"waiting for START_ATTACK command"
            )
            return

        warmup = DEFAULT_WARMUP_MS
        scheduler.schedule(
            start_time_ms + warmup,
            {"type": "attack_stage_tick"},
        )
        self._is_active = True
        self._stage_start_monotonic = time.monotonic()
        logger.info(
            f"Attack playbook '{self._playbook.name}' scheduled, "
            f"first tick at {start_time_ms + warmup:.0f}ms"
        )

    def handle_tick(
        self,
        current_time_ms: float,
        scheduler: Any,
    ) -> list[PacketEvent]:
        """Handle an attack_stage_tick event.

        Returns attack packets to schedule, and schedules the next tick.
        Called from ``UnifiedOrchestrator._handle_control_event()``.
        """
        # Process pending commands first
        self._process_pending_command(scheduler, current_time_ms)

        if not self._is_active or self._is_paused or self._is_completed:
            # Still schedule next tick to check for un-pause / start commands
            if not self._is_completed:
                scheduler.schedule(
                    current_time_ms + TICK_INTERVAL_MS,
                    {"type": "attack_stage_tick"},
                )
            return []

        if self._current_stage_idx >= len(self._stages):
            self._is_completed = True
            logger.info(f"Attack playbook '{self._playbook.name}' completed")
            return []

        stage = self._stages[self._current_stage_idx]

        # Check if stage duration has expired
        elapsed_s = time.monotonic() - self._stage_start_monotonic
        if elapsed_s >= stage.duration_seconds:
            if self._config.auto_advance:
                self._advance_stage()
                if self._is_completed:
                    return []
                stage = self._stages[self._current_stage_idx]
            else:
                # Wait for manual advance
                scheduler.schedule(
                    current_time_ms + TICK_INTERVAL_MS,
                    {"type": "attack_stage_tick"},
                )
                return []

        # Generate packets for current stage actions
        packets = self._generate_stage_packets(stage, current_time_ms)

        # Schedule next tick
        tick_interval = TICK_INTERVAL_MS / self._intensity
        scheduler.schedule(
            current_time_ms + tick_interval,
            {"type": "attack_stage_tick"},
        )

        return packets

    def get_state_snapshot(self) -> dict[str, Any]:
        """Return a serializable state snapshot for status reporting."""
        stage = (
            self._stages[self._current_stage_idx]
            if self._current_stage_idx < len(self._stages)
            else None
        )

        elapsed_s = 0.0
        progress_pct = 0.0
        remaining_s = 0.0
        if stage and self._is_active and self._stage_start_monotonic > 0:
            elapsed_s = time.monotonic() - self._stage_start_monotonic
            progress_pct = min(100.0, (elapsed_s / max(1, stage.duration_seconds)) * 100)
            remaining_s = max(0.0, stage.duration_seconds - elapsed_s)

        state = AttackState(
            playbook_id=self._playbook.playbook_id,
            playbook_name=self._playbook.name,
            current_stage_index=self._current_stage_idx,
            current_stage_id=stage.stage_id if stage else "",
            current_stage_name=stage.name if stage else "",
            current_stage_color=stage.color if stage else "#ff4d4f",
            is_active=self._is_active,
            is_paused=self._is_paused,
            is_completed=self._is_completed,
            stage_started_at=self._stage_start_monotonic,
            stage_progress_pct=progress_pct,
            stage_remaining_s=remaining_s,
            stages_completed=self._stages_completed,
            total_stages=len(self._stages),
            actions_completed=self._actions_completed,
            attack_packets_generated=self._packets_generated,
        )
        return state.to_dict()

    # ------------------------------------------------------------------
    # Runtime command processing (atomic swap)
    # ------------------------------------------------------------------

    def set_pending_command(self, command: dict[str, Any]) -> None:
        """Set a pending command (called from WebSocket thread)."""
        self._pending_command = command

    def _process_pending_command(
        self,
        scheduler: Any,
        current_time_ms: float,
    ) -> None:
        """Consume and process any pending command."""
        cmd = self._pending_command
        if cmd is None:
            return
        self._pending_command = None

        cmd_type = cmd.get("type", "")
        logger.info(f"Processing attack command: {cmd_type}")

        if cmd_type == "start":
            if not self._is_active:
                self._is_active = True
                self._is_paused = False
                self._is_completed = False
                self._current_stage_idx = 0
                self._stage_start_monotonic = time.monotonic()
                self._stage_actions_fired.clear()
                logger.info(f"Attack playbook '{self._playbook.name}' started")
            elif self._is_completed:
                # Restart from beginning
                self._is_completed = False
                self._current_stage_idx = 0
                self._stages_completed = 0
                self._actions_completed = 0
                self._packets_generated = 0
                self._stage_start_monotonic = time.monotonic()
                self._stage_actions_fired.clear()
                logger.info(f"Attack playbook '{self._playbook.name}' restarted")

        elif cmd_type == "stop":
            self._is_active = False
            self._is_completed = True
            logger.info(f"Attack playbook '{self._playbook.name}' stopped")

        elif cmd_type == "advance_stage":
            self._advance_stage()

        elif cmd_type == "pause":
            self._is_paused = cmd.get("paused", True)
            logger.info(
                f"Attack {'paused' if self._is_paused else 'resumed'}"
            )

    def check_wall_time_advancement(self, scheduler: Any, current_time_ms: float) -> None:
        """Advance stage if wall-clock says it's expired.

        Called from the event loop on every iteration (not just tick events).
        This prevents virtual-time lag from causing the UI to show "0s left"
        for extended periods while the scheduler catches up.
        """
        if not self._is_active or self._is_paused or self._is_completed:
            return
        if self._current_stage_idx >= len(self._stages):
            return

        stage = self._stages[self._current_stage_idx]
        elapsed_s = time.monotonic() - self._stage_start_monotonic

        if elapsed_s >= stage.duration_seconds and self._config.auto_advance:
            self._advance_stage()
            # Schedule an immediate tick so the new stage generates packets
            if not self._is_completed:
                scheduler.schedule(
                    current_time_ms + 1,
                    {"type": "attack_stage_tick"},
                )

    # ------------------------------------------------------------------
    # Stage management
    # ------------------------------------------------------------------

    def _advance_stage(self) -> None:
        """Advance to the next kill-chain stage."""
        if self._current_stage_idx < len(self._stages):
            old_stage = self._stages[self._current_stage_idx]
            logger.info(f"Completed attack stage: {old_stage.name}")
            self._stages_completed += 1

        self._current_stage_idx += 1
        self._stage_actions_fired.clear()

        if self._current_stage_idx >= len(self._stages):
            self._is_completed = True
            logger.info(f"Attack playbook '{self._playbook.name}' — all stages completed")
        else:
            new_stage = self._stages[self._current_stage_idx]
            self._stage_start_monotonic = time.monotonic()
            logger.info(
                f"Advancing to attack stage: {new_stage.name} "
                f"({new_stage.duration_seconds}s)"
            )

    # ------------------------------------------------------------------
    # Packet generation
    # ------------------------------------------------------------------

    def _generate_stage_packets(
        self,
        stage: KillChainStage,
        current_time_ms: float,
    ) -> list[PacketEvent]:
        """Generate attack packets for the current stage's actions."""
        packets: list[PacketEvent] = []

        elapsed_s = time.monotonic() - self._stage_start_monotonic
        stage_progress = elapsed_s / max(1, stage.duration_seconds)

        for action in stage.actions:
            # Determine when this action should fire based on its position
            # in the stage and whether it has already been executed
            action_key = f"{stage.stage_id}:{action.action_id}"

            if action.repeat_count <= 1:
                # Single-fire: fire once, skip on subsequent ticks
                if action_key in self._stage_actions_fired:
                    continue

                # Space actions across stage duration
                action_idx = stage.actions.index(action)
                action_trigger_pct = action_idx / max(1, len(stage.actions))
                if stage_progress < action_trigger_pct:
                    continue

                self._stage_actions_fired.add(action_key)
            else:
                # Repeating: check if it's time for the next repeat
                fire_count = self._stage_actions_fired.get(action_key, 0) if isinstance(
                    self._stage_actions_fired, dict) else (
                        1 if action_key in self._stage_actions_fired else 0
                    )
                # For repeating actions, we use a simple counter
                repeat_key = f"{action_key}:count"
                if repeat_key not in self._stage_actions_fired:
                    self._stage_actions_fired.add(repeat_key)
                    # Allow first fire
                else:
                    continue  # Already scheduled for this tick

            # Resolve targets for this action
            targets = self._select_targets(action)
            if not targets:
                self._actions_completed += 1
                continue

            # Get the generator function
            generator = get_action_generator(action.action_type)
            if generator is None:
                logger.warning(
                    f"No generator for action_type '{action.action_type}'"
                )
                self._actions_completed += 1
                continue

            # Generate packets
            try:
                action_packets = list(generator(
                    params=action.parameters,
                    targets=targets,
                    attacker_ip=self._attacker_ip,
                    start_time_ms=current_time_ms,
                ))
                packets.extend(action_packets)
                self._packets_generated += len(action_packets)
                self._actions_completed += 1

                if action_packets:
                    logger.debug(
                        f"Attack action '{action.name}' generated "
                        f"{len(action_packets)} packets"
                    )
            except Exception as e:
                logger.error(
                    f"Error in attack action '{action.name}': {e}",
                    exc_info=True,
                )

        return packets

    # ------------------------------------------------------------------
    # Target resolution
    # ------------------------------------------------------------------

    def _resolve_targets(self, devices: list[dict[str, Any]]) -> list[TargetInfo]:
        """Convert scenario device dicts to TargetInfo list."""
        targets: list[TargetInfo] = []

        # Filter to configured target device IDs if specified
        allowed_ids = set(self._config.target_device_ids) if self._config.target_device_ids else None

        for dev in devices:
            dev_id = dev.get("id", "")
            if allowed_ids and dev_id not in allowed_ids:
                continue

            network = dev.get("network", {})
            ip = network.get("ipAddress", "")
            mac = network.get("macAddress", "")
            if not ip:
                continue

            targets.append(TargetInfo(
                device_id=dev_id,
                ip_address=ip,
                mac_address=mac,
                device_type=dev.get("type", "unknown").lower(),
                protocols=dev.get("protocols", []),
                port=0,
            ))

        return targets

    def _select_targets(self, action: AttackAction) -> list[TargetInfo]:
        """Select targets matching an action's target_selector."""
        selector = action.target_selector.lower()

        if selector == "any" or selector == "all":
            return list(self._all_targets)

        # Filter by device type
        matching = [t for t in self._all_targets if t.device_type == selector]

        # If no devices match the specific type, fall back to all
        if not matching:
            matching = list(self._all_targets)

        # Return a subset for targeted actions
        if len(matching) > 3:
            return random.sample(matching, 3)

        return matching
