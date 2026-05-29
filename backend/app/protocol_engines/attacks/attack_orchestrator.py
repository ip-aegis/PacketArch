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
from typing import Any

from app.protocol_engines.external.engine import ExternalCommEngine, ExternalTrafficConfig
from app.protocol_engines.external.ip_pools import get_attack_source_ip
from app.protocol_engines.types import PacketEvent

from .action_registry import (
    TargetInfo,
    get_action_generator,
)
from .types import (
    ActionReport,
    AttackAction,
    AttackPlaybook,
    AttackPlaybookConfig,
    AttackReport,
    AttackState,
    KillChainStage,
    StageReport,
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

        # ── After-action report telemetry ────────────────────────────
        # Built incrementally as the attack progresses. The orchestrator
        # owns the report so the data lives close to where it's captured
        # (per-action packet counts, IOCs, target hits). Snapshots are
        # exposed via get_report() and surfaced through the state
        # endpoint so the dashboard can render the post-run summary.
        self._report = AttackReport(
            playbook_id=playbook.playbook_id,
            playbook_name=playbook.name,
            mitre_software_id=playbook.mitre_software_id,
            severity=playbook.severity,
            category=playbook.category,
            intensity=self._intensity,
            auto_advance=self._config.auto_advance,
            attacker_ip=self._attacker_ip,
            target_device_count=len(self._all_targets),
            total_stages=len(self._stages),
            stages=[
                StageReport(
                    stage_id=s.stage_id,
                    stage_name=s.name,
                    color=s.color,
                    description=s.description,
                    planned_duration_s=s.duration_seconds,
                    mitre_tactics=list(s.mitre_tactics),
                    expected_cv_alerts=list(s.expected_cv_alerts),
                    status="pending",
                    actions=[
                        # Pre-seed the action records so the report always
                        # shows what WOULD have run, even if a stage never
                        # fired (e.g. attack stopped early).
                        ActionReport(
                            action_id=a.action_id,
                            action_name=a.name,
                            action_type=a.action_type,
                            mitre_technique=a.mitre_technique,
                            expected_cv_detection=a.expected_cv_detection,
                            description=a.description,
                        )
                        for a in s.actions
                    ],
                )
                for s in self._stages
            ],
        )

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
        self._mark_report_started()
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
            self._mark_report_completed("completed")
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
        snapshot = state.to_dict()
        # Embed the after-action report so it rides the existing
        # agent→traffic_dashboard pipeline without a separate channel.
        # The report endpoint pulls this directly from the cached state.
        snapshot["report"] = self.get_report()
        return snapshot

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
                self._mark_report_started()
                logger.info(f"Attack playbook '{self._playbook.name}' started")
            elif self._is_completed:
                # Restart from beginning — reset the report too so the
                # post-run summary reflects the new run only.
                self._is_completed = False
                self._current_stage_idx = 0
                self._stages_completed = 0
                self._actions_completed = 0
                self._packets_generated = 0
                self._stage_start_monotonic = time.monotonic()
                self._stage_actions_fired.clear()
                self._reset_report()
                self._mark_report_started()
                logger.info(f"Attack playbook '{self._playbook.name}' restarted")

        elif cmd_type == "stop":
            self._is_active = False
            self._is_completed = True
            self._mark_report_completed("stopped")
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
            self._mark_stage_completed(self._current_stage_idx)

        self._current_stage_idx += 1
        self._stage_actions_fired.clear()

        if self._current_stage_idx >= len(self._stages):
            self._is_completed = True
            self._mark_report_completed("completed")
            logger.info(f"Attack playbook '{self._playbook.name}' — all stages completed")
        else:
            new_stage = self._stages[self._current_stage_idx]
            self._stage_start_monotonic = time.monotonic()
            self._mark_stage_started(self._current_stage_idx)
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
                self._stage_actions_fired.get(action_key, 0) if isinstance(
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
                self._record_action_fired(
                    stage_idx=self._current_stage_idx,
                    action=action,
                    targets=targets,
                    packet_count=len(action_packets),
                )

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

    # ------------------------------------------------------------------
    # After-action report
    # ------------------------------------------------------------------

    def get_report(self) -> dict[str, Any]:
        """Return the structured after-action report as a dict.

        Available throughout execution and after completion. Includes
        per-stage and per-action telemetry, packet counts, IOCs, and
        aggregate totals.
        """
        self._refresh_report_totals()
        return self._report.to_dict()

    def _mark_report_started(self) -> None:
        if self._report.started_at == 0.0:
            self._report.started_at = time.time()
        self._report.status = "in_progress"
        # Mark the first stage as in_progress on the report (if any).
        if self._report.stages and self._current_stage_idx < len(self._report.stages):
            self._mark_stage_started(self._current_stage_idx)

    def _mark_stage_started(self, stage_idx: int) -> None:
        if stage_idx >= len(self._report.stages):
            return
        s = self._report.stages[stage_idx]
        if s.started_at == 0.0:
            s.started_at = time.time()
        s.status = "in_progress"

    def _mark_stage_completed(self, stage_idx: int) -> None:
        if stage_idx >= len(self._report.stages):
            return
        s = self._report.stages[stage_idx]
        s.completed_at = time.time()
        if s.started_at:
            s.actual_duration_s = round(s.completed_at - s.started_at, 2)
        s.status = "completed"

    def _mark_report_completed(self, status: str) -> None:
        """Finalise the report. ``status`` ∈ {``completed``, ``stopped``}."""
        if self._report.completed_at is not None:
            return
        self._report.completed_at = time.time()
        self._report.status = status
        # Close out the current stage if it's still open.
        if self._current_stage_idx < len(self._report.stages):
            s = self._report.stages[self._current_stage_idx]
            if s.status == "in_progress":
                s.completed_at = time.time()
                if s.started_at:
                    s.actual_duration_s = round(s.completed_at - s.started_at, 2)
                s.status = "completed" if status == "completed" else "skipped"
        # Refresh aggregate totals one final time.
        self._refresh_report_totals()

    def _reset_report(self) -> None:
        """Wipe per-run report state. Called on a restart command."""
        for s in self._report.stages:
            s.started_at = 0.0
            s.completed_at = None
            s.actual_duration_s = 0.0
            s.packets_emitted = 0
            s.status = "pending"
            for a in s.actions:
                a.fired_at = 0.0
                a.fire_count = 0
                a.packets_emitted = 0
                a.targets_hit = []
                a.iocs = {}
        self._report.started_at = 0.0
        self._report.completed_at = None
        self._report.status = "in_progress"
        self._report.total_packets = 0
        self._report.total_actions = 0
        self._report.stages_completed = 0
        self._report.techniques_used = []
        self._report.tactics_covered = []
        self._report.targets_hit = []

    def _record_action_fired(
        self,
        stage_idx: int,
        action: AttackAction,
        targets: list[TargetInfo],
        packet_count: int,
    ) -> None:
        """Update per-action telemetry after a generator runs.

        Captures IOCs (attacker IP, target IPs/ports, register
        addresses, function codes, SNMP communities) so the after-action
        report shows what the action actually did, not just what it
        intended.
        """
        if stage_idx >= len(self._report.stages):
            return
        stage_report = self._report.stages[stage_idx]
        action_report = next(
            (a for a in stage_report.actions if a.action_id == action.action_id),
            None,
        )
        if action_report is None:
            return

        if action_report.fired_at == 0.0:
            action_report.fired_at = time.time()
        action_report.fire_count += 1
        action_report.packets_emitted += packet_count

        # Merge target device IDs (unique).
        existing = set(action_report.targets_hit)
        for t in targets:
            if t.device_id and t.device_id not in existing:
                action_report.targets_hit.append(t.device_id)
                existing.add(t.device_id)

        # Capture IOCs from action parameters + targets. Best-effort:
        # different action types use different param names, so we pull
        # whatever's there. The report renderer formats this kindly.
        iocs = action_report.iocs
        iocs.setdefault("attacker_ip", self._attacker_ip)

        target_ips = sorted({t.ip_address for t in targets if t.ip_address})
        if target_ips:
            existing_ips = set(iocs.get("target_ips", []))
            for ip in target_ips:
                existing_ips.add(ip)
            iocs["target_ips"] = sorted(existing_ips)

        params = action.parameters or {}
        # Common protocol-specific IOC fields. Each key is only added if
        # the action actually exercises it.
        for ioc_key in (
            "ports", "port_range", "function_codes", "register_address",
            "register_count", "coil_address", "snmp_community", "communities",
            "object_id", "exfil_size_bytes", "beacon_pattern", "c2_domain",
            "c2_ip", "exfil_protocol", "scan_type", "payload_hex",
        ):
            if ioc_key in params and ioc_key not in iocs:
                iocs[ioc_key] = params[ioc_key]

        stage_report.packets_emitted += packet_count

    def _refresh_report_totals(self) -> None:
        """Recompute aggregate totals from per-stage state.

        Cheap to call on every snapshot — keeps the report self-consistent.
        """
        report = self._report
        report.total_packets = sum(s.packets_emitted for s in report.stages)
        report.total_actions = sum(
            sum(1 for a in s.actions if a.fire_count > 0)
            for s in report.stages
        )
        report.stages_completed = sum(
            1 for s in report.stages if s.status == "completed"
        )

        techniques: set[str] = set()
        tactics: set[str] = set()
        targets: set[str] = set()
        for s in report.stages:
            if s.status in ("completed", "in_progress"):
                tactics.update(s.mitre_tactics)
            for a in s.actions:
                if a.fire_count > 0:
                    if a.mitre_technique:
                        techniques.add(a.mitre_technique)
                    targets.update(a.targets_hit)
        report.techniques_used = sorted(techniques)
        report.tactics_covered = sorted(tactics)
        report.targets_hit = sorted(targets)
