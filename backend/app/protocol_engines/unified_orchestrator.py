# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unified traffic orchestrator for both PCAP generation and live injection.

Combines the best of TrafficOrchestrator (discovery, identity, timing) and the
agent's LiveTrafficOrchestrator (perpetual mode, real-time scheduling).

Usage:
    # PCAP mode (timed)
    output = PcapOutput("output.pcap")
    orch = UnifiedOrchestrator(output=output, duration_ms=60000)

    # Live mode (perpetual)
    output = LiveOutput(interface="eth0")
    orch = UnifiedOrchestrator(output=output, duration_ms=None)
    orch.run(stop_event=some_event)
"""

from __future__ import annotations

import logging
import random
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.protocol_engines import get_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.jitter import apply_jitter
from app.protocol_engines.output import PacketOutput
from app.protocol_engines.traffic_stats import TrafficStats
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)
from app.traffic_generator.scheduler import EventScheduler

if TYPE_CHECKING:
    from app.protocol_engines.adaptive.controller import AdaptiveController
    from app.protocol_engines.ambient.noise_generator import BackgroundNoiseGenerator
    from app.protocol_engines.attacks.attack_orchestrator import AttackOrchestrator
    from app.protocol_engines.process_sim.controller import ProcessSimController

logger = logging.getLogger(__name__)


@dataclass
class FlowState:
    """State tracking for a flow during generation."""

    flow: FlowContext
    conversation: ConversationState
    engine: ProtocolEngine
    next_poll_time: float = 0.0
    is_started: bool = False
    is_stopped: bool = False
    poll_interval_ms: float = 1000.0


@dataclass
class OrchestrationResult:
    """Result of unified orchestration."""

    packets_generated: int = 0
    duration_ms: float = 0.0
    stopped_by_event: bool = False
    error: str | None = None


class UnifiedOrchestrator:
    """Unified orchestrator for PCAP and live traffic generation.

    Supports two modes:
    - Timed mode (duration_ms set): generates traffic for a fixed duration,
      then runs shutdown sequences. Used for PCAP generation.
    - Perpetual mode (duration_ms=None): generates traffic indefinitely
      until stop_event is set. Used by live agents.
    """

    def __init__(
        self,
        output: PacketOutput,
        duration_ms: int | None = None,
    ) -> None:
        self.output = output
        self.duration_ms = duration_ms
        self.flows: list[FlowState] = []
        self.scheduler = EventScheduler()
        self.current_time_ms = 0.0
        self._flow_map: dict[str, FlowState] = {}
        self.stats = TrafficStats()
        self._adaptive_controller: AdaptiveController | None = None
        self._attack_orchestrator: AttackOrchestrator | None = None
        self._ambient_generator: BackgroundNoiseGenerator | None = None
        self._process_sim: ProcessSimController | None = None
        self._last_process_phase: str | None = None
        # Pending hot-attach injection (atomic swap from WebSocket thread)
        self._pending_attack_injection: dict[str, Any] | None = None

    def add_flow(self, flow_context: FlowContext) -> None:
        """Add a flow to be generated.

        Args:
            flow_context: Flow context to add
        """
        engine = get_engine(flow_context.protocol)
        conversation_state = engine.create_initial_state(flow_context)

        poll_interval = flow_context.timing_model.get("poll_interval_ms", 1000.0)

        flow_state = FlowState(
            flow=flow_context,
            conversation=conversation_state,
            engine=engine,
            poll_interval_ms=poll_interval,
        )

        # Auto-create PayloadGenerator when not explicitly provided
        if flow_context.payload_generator is None:
            from app.protocol_engines.payload_defaults import (
                create_default_payload_generator,
            )

            flow_context.payload_generator = create_default_payload_generator(
                protocol=flow_context.protocol,
                config=flow_context.config
                if not isinstance(flow_context.config, dict)
                else flow_context.config,
                vertical=flow_context.config.get("_vertical")
                if isinstance(flow_context.config, dict)
                else None,
            )

        self.flows.append(flow_state)
        self._flow_map[flow_context.flow_id] = flow_state
        self.stats.register_flow(flow_context.flow_id, flow_context.protocol.value)
        logger.info(
            f"Added flow {flow_context.flow_id} "
            f"({flow_context.protocol.value}, interval={poll_interval}ms)"
        )

    def register_adaptive_controller(self, controller: AdaptiveController) -> None:
        """Register an adaptive controller for runtime traffic adjustment.

        The controller is called once per poll cycle to adjust poll intervals.
        Must be called after all flows are added via add_flow().

        Args:
            controller: AdaptiveController instance
        """
        self._adaptive_controller = controller
        for fs in self.flows:
            vendor = None
            dst = fs.flow.destination
            if hasattr(dst, "vendor") and dst.vendor:
                vendor = dst.vendor
            elif dst.vendor_fingerprint:
                vendor = dst.vendor_fingerprint.get("vendor")
            controller.register_flow(
                flow_id=fs.flow.flow_id,
                vendor=vendor,
                base_poll_ms=fs.poll_interval_ms,
                protocol=fs.flow.protocol.value,
            )
        logger.info(
            f"Adaptive controller registered for {len(self.flows)} flows"
        )

    def register_attack_orchestrator(self, attack_orch: AttackOrchestrator) -> None:
        """Register an attack orchestrator for playbook execution.

        The orchestrator schedules ``attack_stage_tick`` control events on
        the shared event heap, interleaving attack packets with legitimate
        traffic.

        Args:
            attack_orch: AttackOrchestrator instance
        """
        self._attack_orchestrator = attack_orch
        # Schedule initial attack events after a warm-up period
        warmup_ms = 10_000.0  # 10s after start for discovery/startup to complete
        attack_orch.schedule_initial_events(self.scheduler, warmup_ms)
        logger.info("Attack orchestrator registered")

    def set_pending_attack_injection(self, config: dict[str, Any]) -> None:
        """Queue an attack playbook injection for the scenario thread.

        Uses atomic reference swap — safe without locks under Python GIL.
        The scenario thread picks this up on the next event-loop iteration
        via ``_check_pending_attack_injection()``.

        Args:
            config: Dict with ``playbook_id``, ``config``, and ``devices`` keys.
        """
        self._pending_attack_injection = config

    def _check_pending_attack_injection(self) -> None:
        """Check for and process a pending attack injection.

        Called from the scenario thread's event loop so that
        ``register_attack_orchestrator()`` (which touches the heap)
        runs in the correct thread.
        """
        injection = self._pending_attack_injection
        if injection is None:
            return
        self._pending_attack_injection = None

        try:
            from app.protocol_engines.attacks import (
                AttackOrchestrator,
                get_playbook,
            )
            from app.protocol_engines.attacks.types import AttackPlaybookConfig

            playbook_id = injection.get("playbook_id")
            playbook = get_playbook(playbook_id)
            if not playbook:
                logger.warning(
                    f"INJECT_ATTACK: playbook '{playbook_id}' not found"
                )
                return

            # Config fields may be at the top level (from injection) or nested
            # under a "config" key (from deploy-time).  Support both.
            raw_config = injection.get("config") or injection
            config = AttackPlaybookConfig.from_dict(raw_config)
            devices = injection.get("devices", [])

            attack_orch = AttackOrchestrator(
                playbook=playbook,
                devices=devices,
                config=config,
            )
            self.register_attack_orchestrator(attack_orch)
            logger.info(f"Hot-attached attack playbook '{playbook.name}'")
        except Exception as exc:
            logger.error(f"Failed to hot-attach attack: {exc}", exc_info=True)

    def register_ambient_generator(self, generator: BackgroundNoiseGenerator) -> None:
        """Register a background noise generator for ambient traffic.

        Schedules gratuitous ARP, NTP queries, and other ambient packets
        on the shared event heap, interleaved with protocol traffic.

        Args:
            generator: BackgroundNoiseGenerator instance
        """
        self._ambient_generator = generator
        # Schedule ambient events after startup sequences (~500ms)
        generator.schedule_initial_events(self.scheduler, warmup_ms=500.0)
        logger.info(
            f"Ambient noise generator registered for {len(generator.devices)} devices"
        )

    def register_process_sim(self, controller: ProcessSimController) -> None:
        """Register a process simulation controller.

        The controller schedules periodic ``process_sim_tick`` control events
        on the shared heap.  Each tick advances the physical models and pushes
        correlated values into each flow's :class:`PayloadGenerator`.

        Args:
            controller: ProcessSimController instance
        """
        self._process_sim = controller
        controller.schedule_initial_events(self.scheduler, warmup_ms=100.0)
        logger.info("Process simulation controller registered")

    def run(self, stop_event: threading.Event | None = None) -> OrchestrationResult:
        """Run traffic generation.

        Args:
            stop_event: Optional threading event to signal stop (perpetual mode).
                        When set, the orchestrator finishes the current event
                        and runs shutdown sequences before returning.

        Returns:
            OrchestrationResult with stats
        """
        import time

        wall_start = time.monotonic()
        packets = 0
        stopped_by_event = False

        try:
            logger.info(
                f"Starting unified orchestration: "
                f"{len(self.flows)} flows, "
                f"mode={'timed ' + str(self.duration_ms) + 'ms' if self.duration_ms else 'perpetual'}"
            )

            # Phase 1: Discovery sequences (device fingerprinting)
            self._schedule_discovery_sequences()

            # Phase 2: Startup sequences (TCP handshake, session setup)
            self._schedule_startup_sequences()

            # Phase 3: Main event loop
            while self.scheduler.has_events():
                # Check for hot-attach attack injection (atomic swap)
                self._check_pending_attack_injection()

                # Check wall-time stage advancement (prevents virtual-time lag)
                if self._attack_orchestrator:
                    self._attack_orchestrator.check_wall_time_advancement(
                        self.scheduler, self.current_time_ms,
                    )

                # Check external stop signal
                if stop_event and stop_event.is_set():
                    logger.info("Stop event received, initiating shutdown")
                    stopped_by_event = True
                    break

                event_data = self.scheduler.pop_next()
                if not event_data:
                    break

                timestamp_ms, event = event_data
                self.current_time_ms = timestamp_ms

                # Check timed duration limit
                if self.duration_ms is not None and timestamp_ms > self.duration_ms:
                    logger.info(
                        f"Reached duration limit at {timestamp_ms:.1f}ms"
                    )
                    break

                # Dispatch event
                if isinstance(event, PacketEvent):
                    self.output.write_packet(event.packet_bytes, timestamp_ms)
                    packets += 1
                    # Ambient/attack packets already recorded stats in their handlers
                    if not event.flow_id.startswith(("ambient_", "__attack__")):
                        fs = self._flow_map.get(event.flow_id)
                        proto = fs.flow.protocol.value if fs else "unknown"
                        self.stats.record_packet(proto, len(event.packet_bytes))
                    if packets % 1000 == 0:
                        logger.debug(f"Generated {packets} packets")
                elif isinstance(event, dict):
                    self._handle_control_event(event)

            # Phase 4: Shutdown sequences
            self._schedule_shutdown_sequences()
            while self.scheduler.has_events():
                event_data = self.scheduler.pop_next()
                if not event_data:
                    break
                timestamp_ms, event = event_data
                self.current_time_ms = timestamp_ms
                if isinstance(event, PacketEvent):
                    self.output.write_packet(event.packet_bytes, timestamp_ms)
                    packets += 1
                    if not event.flow_id.startswith(("ambient_", "__attack__")):
                        fs = self._flow_map.get(event.flow_id)
                        proto = fs.flow.protocol.value if fs else "unknown"
                        self.stats.record_packet(proto, len(event.packet_bytes))

            wall_elapsed_ms = (time.monotonic() - wall_start) * 1000.0
            logger.info(
                f"Orchestration complete: {packets} packets in {wall_elapsed_ms:.0f}ms wall time"
            )

            return OrchestrationResult(
                packets_generated=packets,
                duration_ms=wall_elapsed_ms,
                stopped_by_event=stopped_by_event,
            )

        except Exception as e:
            wall_elapsed_ms = (time.monotonic() - wall_start) * 1000.0
            logger.error(f"Orchestration error: {e}", exc_info=True)
            return OrchestrationResult(
                packets_generated=packets,
                duration_ms=wall_elapsed_ms,
                stopped_by_event=stopped_by_event,
                error=str(e),
            )

        finally:
            self.output.close()

    # ------------------------------------------------------------------
    # Discovery scheduling
    # ------------------------------------------------------------------

    def _schedule_discovery_sequences(self) -> None:
        """Schedule protocol-specific discovery sequences for device fingerprinting.

        Discovery sequences emit device identity information that scanners like
        Cisco Cyber Vision use to identify devices.
        """
        discovery_time = 0.0

        for fs in self.flows:
            protocol = fs.flow.protocol

            if protocol == ProtocolType.ETHERNET_IP:
                # UDP ListIdentity discovery — independent of TCP, works at any time
                if hasattr(fs.engine, "generate_discovery_sequence"):
                    for pkt in fs.engine.generate_discovery_sequence(
                        fs.flow, fs.conversation, start_time_ms=discovery_time,
                    ):
                        self.scheduler.schedule(pkt.timestamp_ms, pkt)
                    discovery_time += random.uniform(50.0, 150.0)

                # CIP deep discovery (GetAttributeAll, etc.) is now performed
                # inside generate_startup_sequence() after the TCP session is
                # established, eliminating the timing race where discovery
                # fired before RegisterSession completed.

            elif protocol == ProtocolType.PROFINET:
                if hasattr(fs.engine, "generate_dcp_discovery_sequence"):
                    for pkt in fs.engine.generate_dcp_discovery_sequence(
                        fs.flow, fs.conversation, start_time_ms=discovery_time,
                    ):
                        self.scheduler.schedule(pkt.timestamp_ms, pkt)
                    discovery_time += random.uniform(50.0, 150.0)

        if discovery_time > 0:
            logger.info(f"Scheduled discovery sequences up to {discovery_time:.1f}ms")

    # ------------------------------------------------------------------
    # Startup scheduling
    # ------------------------------------------------------------------

    # Role-based startup offset ranges (ms).  Infrastructure and supervisory
    # devices boot first; field devices come up last.
    _STARTUP_OFFSETS: dict[str, tuple[float, float]] = {
        "scada": (0, 2000),
        "hmi": (0, 2000),
        "server": (0, 2000),
        "workstation": (0, 2000),
        "plc": (2000, 10000),
        "controller": (2000, 10000),
        "rtu": (2000, 10000),
        "safety_controller": (2000, 10000),
        "sensor": (5000, 20000),
        "actuator": (5000, 20000),
        "drive": (5000, 20000),
        "meter": (5000, 20000),
        "io_module": (5000, 20000),
        "field_device": (5000, 20000),
    }
    _DEFAULT_OFFSET = (1000, 15000)

    def _compute_startup_offset(self, fs: FlowState) -> float:
        """Compute a startup offset for a flow based on device role.

        In timed mode, offsets are capped to 10% of total duration so that
        short PCAP captures aren't eaten up by stagger.

        Returns:
            Offset in milliseconds
        """
        # Honour explicit offset if the caller pre-set it
        if fs.flow.startup_offset_ms > 0:
            return fs.flow.startup_offset_ms

        device_type = ""
        dst = fs.flow.destination
        if dst.vendor_fingerprint:
            device_type = dst.vendor_fingerprint.get("device_type", "").lower()

        lo, hi = self._STARTUP_OFFSETS.get(device_type, self._DEFAULT_OFFSET)

        # In timed mode, cap offset to 10% of the total duration
        if self.duration_ms is not None:
            cap = self.duration_ms * 0.10
            lo = min(lo, cap)
            hi = min(hi, cap)

        return random.uniform(lo, hi)

    def _schedule_startup_sequences(self) -> None:
        """Schedule startup sequences for all flows with staggered offsets.

        Devices boot in a realistic order: supervisory first, then
        controllers, then field devices — each with a random offset
        within their role-based range.
        """
        for fs in self.flows:
            offset = self._compute_startup_offset(fs)
            fs.flow.startup_offset_ms = offset

            for pkt in fs.engine.generate_startup_sequence(
                fs.flow, fs.conversation, start_time_ms=offset,
            ):
                self.scheduler.schedule(pkt.timestamp_ms, pkt)

            fs.is_started = True

            first_poll = offset + apply_jitter(
                fs.poll_interval_ms, fs.flow.timing_model,
            )
            fs.next_poll_time = first_poll
            self.scheduler.schedule(
                first_poll,
                {"type": "poll", "flow_id": fs.flow.flow_id},
            )

    # ------------------------------------------------------------------
    # Shutdown scheduling
    # ------------------------------------------------------------------

    def _schedule_shutdown_sequences(self) -> None:
        """Schedule shutdown sequences for all active flows."""
        shutdown_time = self.current_time_ms

        for fs in self.flows:
            if fs.is_stopped:
                continue

            for pkt in fs.engine.generate_shutdown_sequence(
                fs.flow, fs.conversation, start_time_ms=shutdown_time,
            ):
                self.scheduler.schedule(pkt.timestamp_ms, pkt)

            fs.is_stopped = True

    # ------------------------------------------------------------------
    # Control event dispatch
    # ------------------------------------------------------------------

    def _handle_control_event(self, event: dict[str, Any]) -> None:
        """Handle control events (poll triggers, CIP discovery, ambient, etc.)."""
        event_type = event.get("type", "")

        if event_type == "poll":
            self._handle_poll_event(event["flow_id"])
        elif event_type == "attack_stage_tick":
            self._handle_attack_tick()
        elif event_type == "process_sim_tick":
            self._handle_process_sim_tick()
        elif event_type.startswith("ambient_"):
            self._handle_ambient_event(event)

    def _handle_poll_event(self, flow_id: str) -> None:
        """Handle a poll trigger for a flow."""
        fs = self._flow_map.get(flow_id)
        if not fs:
            logger.warning(f"Flow {flow_id} not found for poll event")
            return

        for pkt in fs.engine.generate_poll_cycle(
            fs.flow, fs.conversation, cycle_time_ms=self.current_time_ms,
        ):
            self.scheduler.schedule(pkt.timestamp_ms, pkt)

        # Apply adaptive adjustment to poll interval
        effective_interval = fs.poll_interval_ms
        if self._adaptive_controller:
            effective_interval = self._adaptive_controller.adjust_next_poll(
                flow_id, fs.poll_interval_ms,
            )

        # Schedule next poll
        next_poll = self.current_time_ms + apply_jitter(
            effective_interval, fs.flow.timing_model,
        )

        # In timed mode, only schedule within duration; in perpetual mode, always schedule
        if self.duration_ms is None or next_poll < self.duration_ms:
            fs.next_poll_time = next_poll
            self.scheduler.schedule(
                next_poll,
                {"type": "poll", "flow_id": flow_id},
            )

    def _handle_attack_tick(self) -> None:
        """Handle an attack stage tick — generate attack packets."""
        if not self._attack_orchestrator:
            return
        packets = self._attack_orchestrator.handle_tick(
            self.current_time_ms, self.scheduler,
        )
        for pkt in packets:
            self.scheduler.schedule(pkt.timestamp_ms, pkt)
            self.stats.record_packet("attack", len(pkt.packet_bytes))

    def _handle_ambient_event(self, event: dict[str, Any]) -> None:
        """Handle an ambient noise event — generate ARP/NTP/discovery packets.

        Wrapped in try/except so that a single handler failure does NOT
        crash the entire orchestration run loop.
        """
        if not self._ambient_generator:
            return
        try:
            packets = self._ambient_generator.handle_event(
                event, self.current_time_ms, self.scheduler,
            )
            for pkt in packets:
                self.scheduler.schedule(pkt.timestamp_ms, pkt)
                self.stats.record_packet("ambient", len(pkt.packet_bytes))
        except Exception as e:
            logger.warning(
                "Ambient event '%s' failed (device=%s): %s",
                event.get("type", "?"),
                event.get("device_id", "?"),
                e,
                exc_info=True,
            )

    def _handle_process_sim_tick(self) -> None:
        """Handle a process simulation tick — advance models, push values."""
        if not self._process_sim:
            return

        # Forward deployment phase changes to process state machine
        if self._adaptive_controller:
            snapshot = self._adaptive_controller.get_state_snapshot()
            phase_id = snapshot.get("deployment_phase_id") if snapshot else None
            if phase_id and phase_id != self._last_process_phase:
                self._last_process_phase = phase_id
                self._process_sim.on_phase_change(phase_id)

        self._process_sim.handle_tick(self.current_time_ms, self.scheduler)

    def get_stats_snapshot(self) -> dict | None:
        """Get a JSON-serializable snapshot of current traffic stats."""
        snapshot = self.stats.snapshot()
        if snapshot and self._adaptive_controller:
            snapshot["adaptation"] = self._adaptive_controller.get_state_snapshot()
        if snapshot and self._attack_orchestrator:
            snapshot["attack"] = self._attack_orchestrator.get_state_snapshot()
        if snapshot and self._process_sim:
            snapshot["process_sim"] = self._process_sim.get_state_snapshot()
        return snapshot
