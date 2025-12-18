"""Traffic generation orchestrator."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import UUID

from app.protocol_engines import get_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.timing import apply_jitter
from app.protocol_engines.types import ConversationState, FlowContext, PacketEvent, ProtocolType
from app.traffic_generator.models import GenerationResult, JobStatus
from app.traffic_generator.pcap_writer import PcapWriter
from app.traffic_generator.scheduler import EventScheduler

if TYPE_CHECKING:
    from app.protocol_engines.ai_enhanced_base import AIEnhancedEngineFactory

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for traffic generation."""

    job_id: str
    scenario_id: UUID
    total_duration_ms: int
    output_path: str | Path

    # AI-enhanced generation options
    use_ai_timing: bool = False
    use_learned_patterns: bool = False
    anomaly_injection_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowState:
    """State tracking for a flow during generation."""

    flow: FlowContext
    conversation: ConversationState
    engine: ProtocolEngine
    next_poll_time: float = 0.0
    is_started: bool = False
    is_stopped: bool = False
    poll_interval_ms: float = 1000.0  # Default 1 second


class TrafficOrchestrator:
    """Orchestrates traffic generation across multiple flows."""

    def __init__(self, config: GenerationConfig):
        """Initialize traffic orchestrator.

        Args:
            config: Generation configuration
        """
        self.config = config
        self.flows: list[FlowState] = []
        self.scheduler = EventScheduler()
        self.current_time_ms = 0.0

        # AI-enhanced generation support
        self._ai_engine_factory: "AIEnhancedEngineFactory | None" = None
        self._ai_patterns_loaded = False

    async def load_ai_patterns(self, db_session: Any) -> None:
        """Load learned patterns from the database for AI-enhanced generation.

        Args:
            db_session: Database session
        """
        if not (self.config.use_ai_timing or self.config.use_learned_patterns):
            return

        from app.protocol_engines.ai_enhanced_base import AIEnhancedEngineFactory

        self._ai_engine_factory = AIEnhancedEngineFactory()
        await self._ai_engine_factory.load_patterns(db_session)
        self._ai_patterns_loaded = True

        logger.info("Loaded AI patterns for enhanced traffic generation")

    def _get_engine_for_flow(self, flow_context: FlowContext) -> ProtocolEngine:
        """Get the appropriate engine for a flow.

        Uses AI-enhanced engine if patterns are loaded and AI mode is enabled.

        Args:
            flow_context: Flow context

        Returns:
            Protocol engine (standard or AI-enhanced)
        """
        if self._ai_patterns_loaded and self._ai_engine_factory:
            return self._ai_engine_factory.create_engine(
                protocol=flow_context.protocol,
                anomaly_config=self.config.anomaly_injection_config,
            )
        else:
            return get_engine(flow_context.protocol)

    def add_flow(self, flow_context: FlowContext) -> None:
        """Add a flow to be generated.

        Args:
            flow_context: Flow context to add
        """
        # Get appropriate protocol engine (AI-enhanced or standard)
        engine = self._get_engine_for_flow(flow_context)

        # Create initial conversation state
        conversation_state = engine.create_initial_state(flow_context)

        # Get poll interval from timing model
        poll_interval = flow_context.timing_model.get("poll_interval_ms", 1000.0)

        # Create flow state
        flow_state = FlowState(
            flow=flow_context,
            conversation=conversation_state,
            engine=engine,
            poll_interval_ms=poll_interval,
        )

        self.flows.append(flow_state)
        logger.info(
            f"Added flow {flow_context.flow_id} with protocol {flow_context.protocol}"
        )

    def generate(self) -> GenerationResult:
        """Generate traffic for all flows.

        Returns:
            Generation result with statistics
        """
        from datetime import datetime

        start_time = datetime.utcnow()
        packets_generated = 0

        try:
            # Create PCAP writer
            with PcapWriter(self.config.output_path) as pcap_writer:
                logger.info(f"Starting traffic generation for job {self.config.job_id}")
                logger.info(f"Duration: {self.config.total_duration_ms}ms")
                logger.info(f"Output: {self.config.output_path}")
                logger.info(f"Flows: {len(self.flows)}")

                # Schedule discovery sequences first (device identity fingerprinting)
                self._schedule_discovery_sequences()

                # Schedule startup sequences for all flows
                self._schedule_startup_sequences()

                # Main generation loop
                while self.scheduler.has_events():
                    # Get next event
                    event_data = self.scheduler.pop_next()
                    if not event_data:
                        break

                    timestamp_ms, event = event_data

                    # Update current time
                    self.current_time_ms = timestamp_ms

                    # Check if we've exceeded total duration
                    if timestamp_ms > self.config.total_duration_ms:
                        logger.info(
                            f"Reached end of simulation at {timestamp_ms:.2f}ms"
                        )
                        break

                    # Handle different event types
                    if isinstance(event, PacketEvent):
                        # Write packet to PCAP
                        pcap_writer.write_packet(event.packet_bytes, timestamp_ms)
                        packets_generated += 1

                        if packets_generated % 1000 == 0:
                            logger.debug(f"Generated {packets_generated} packets")

                    elif isinstance(event, dict):
                        # Control events (poll, shutdown, etc.)
                        self._handle_control_event(event)

                # Schedule shutdown sequences for all flows
                self._schedule_shutdown_sequences()

                # Process remaining shutdown events
                while self.scheduler.has_events():
                    event_data = self.scheduler.pop_next()
                    if not event_data:
                        break

                    timestamp_ms, event = event_data
                    self.current_time_ms = timestamp_ms

                    if isinstance(event, PacketEvent):
                        pcap_writer.write_packet(event.packet_bytes, timestamp_ms)
                        packets_generated += 1

                # Close PCAP file
                pcap_writer.close()

                end_time = datetime.utcnow()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                logger.info(f"Generation complete: {packets_generated} packets")
                logger.info(f"File size: {pcap_writer.file_size} bytes")

                return GenerationResult(
                    job_id=self.config.job_id,
                    scenario_id=self.config.scenario_id,
                    status=JobStatus.COMPLETED,
                    pcap_path=str(self.config.output_path),
                    packets_generated=packets_generated,
                    duration_ms=duration_ms,
                    file_size_bytes=pcap_writer.file_size,
                    started_at=start_time,
                    completed_at=end_time,
                )

        except Exception as e:
            logger.error(f"Error during traffic generation: {e}", exc_info=True)
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return GenerationResult(
                job_id=self.config.job_id,
                scenario_id=self.config.scenario_id,
                status=JobStatus.FAILED,
                error_message=str(e),
                packets_generated=packets_generated,
                duration_ms=duration_ms,
                started_at=start_time,
                completed_at=end_time,
            )

    def _schedule_discovery_sequences(self) -> None:
        """Schedule protocol-specific discovery sequences for device fingerprinting.

        Discovery sequences emit device identity information that scanners like
        Cisco Cyber Vision use to identify devices and detect vulnerable firmware.

        For EtherNet/IP:
        - ListIdentity (UDP): Basic device identification
        - CIP Identity Object queries (TCP): Deep fingerprinting with extended attributes

        For PROFINET:
        - DCP Identify: Device identification including I&M data
        """
        import random

        discovery_time = 0.0  # Start discovery before main traffic

        for flow_state in self.flows:
            protocol = flow_state.flow.protocol

            # EtherNet/IP discovery sequences
            if protocol == ProtocolType.ETHERNET_IP:
                engine = flow_state.engine

                # ListIdentity discovery (UDP unicast to simulate scanner query)
                if hasattr(engine, "generate_discovery_sequence"):
                    discovery_events = engine.generate_discovery_sequence(
                        flow_state.flow,
                        flow_state.conversation,
                        start_time_ms=discovery_time,
                    )
                    for packet_event in discovery_events:
                        self.scheduler.schedule(packet_event.timestamp_ms, packet_event)
                    discovery_time += random.uniform(50.0, 150.0)

                # CIP deep fingerprinting (after TCP connection established)
                # This needs to run after startup, so we schedule it differently
                if hasattr(engine, "generate_cip_discovery_sequence"):
                    # Schedule CIP discovery after connection is established
                    # We use a control event to trigger this after startup
                    self.scheduler.schedule(
                        discovery_time + 500.0,  # After TCP setup
                        {
                            "type": "cip_discovery",
                            "flow_id": flow_state.flow.flow_id,
                        },
                    )
                    discovery_time += random.uniform(100.0, 200.0)

            # PROFINET discovery sequences
            elif protocol == ProtocolType.PROFINET:
                engine = flow_state.engine

                # DCP Identify discovery
                if hasattr(engine, "generate_dcp_discovery_sequence"):
                    discovery_events = engine.generate_dcp_discovery_sequence(
                        flow_state.flow,
                        flow_state.conversation,
                        start_time_ms=discovery_time,
                    )
                    for packet_event in discovery_events:
                        self.scheduler.schedule(packet_event.timestamp_ms, packet_event)
                    discovery_time += random.uniform(50.0, 150.0)

            # Modbus TCP - FC 43 Read Device Identification is handled in poll cycles
            # when device_id_code is configured, so no separate discovery needed

        if discovery_time > 0:
            logger.info(f"Scheduled discovery sequences up to {discovery_time:.2f}ms")

    def _schedule_startup_sequences(self) -> None:
        """Schedule startup sequences for all flows."""
        for flow_state in self.flows:
            # Generate startup sequence (e.g., TCP handshake)
            startup_events = flow_state.engine.generate_startup_sequence(
                flow_state.flow,
                flow_state.conversation,
                start_time_ms=0.0,
            )

            for packet_event in startup_events:
                self.scheduler.schedule(packet_event.timestamp_ms, packet_event)

            # Mark flow as started
            flow_state.is_started = True

            # Schedule first poll cycle
            first_poll_time = apply_jitter(
                flow_state.poll_interval_ms,
                flow_state.flow.timing_model,
            )
            flow_state.next_poll_time = first_poll_time

            self.scheduler.schedule(
                first_poll_time,
                {"type": "poll", "flow_id": flow_state.flow.flow_id},
            )

    def _schedule_shutdown_sequences(self) -> None:
        """Schedule shutdown sequences for all flows."""
        shutdown_time = self.config.total_duration_ms

        for flow_state in self.flows:
            if flow_state.is_stopped:
                continue

            # Generate shutdown sequence (e.g., TCP FIN)
            shutdown_events = flow_state.engine.generate_shutdown_sequence(
                flow_state.flow,
                flow_state.conversation,
                start_time_ms=shutdown_time,
            )

            for packet_event in shutdown_events:
                self.scheduler.schedule(packet_event.timestamp_ms, packet_event)

            flow_state.is_stopped = True

    def _handle_control_event(self, event: dict[str, Any]) -> None:
        """Handle control events (poll triggers, etc.).

        Args:
            event: Control event dictionary
        """
        event_type = event.get("type")

        if event_type == "poll":
            flow_id = event.get("flow_id")
            self._handle_poll_event(flow_id)
        elif event_type == "cip_discovery":
            flow_id = event.get("flow_id")
            self._handle_cip_discovery_event(flow_id)

    def _handle_poll_event(self, flow_id: str) -> None:
        """Handle a poll event for a flow.

        Args:
            flow_id: Flow identifier
        """
        # Find the flow
        flow_state = None
        for fs in self.flows:
            if fs.flow.flow_id == flow_id:
                flow_state = fs
                break

        if not flow_state:
            logger.warning(f"Flow {flow_id} not found for poll event")
            return

        # Generate poll cycle packets
        poll_events = flow_state.engine.generate_poll_cycle(
            flow_state.flow,
            flow_state.conversation,
            cycle_time_ms=self.current_time_ms,
        )

        for packet_event in poll_events:
            self.scheduler.schedule(packet_event.timestamp_ms, packet_event)

        # Schedule next poll cycle
        next_poll_time = self.current_time_ms + apply_jitter(
            flow_state.poll_interval_ms,
            flow_state.flow.timing_model,
        )

        # Only schedule if within total duration
        if next_poll_time < self.config.total_duration_ms:
            flow_state.next_poll_time = next_poll_time
            self.scheduler.schedule(
                next_poll_time,
                {"type": "poll", "flow_id": flow_id},
            )

    def _handle_cip_discovery_event(self, flow_id: str) -> None:
        """Handle CIP deep fingerprinting discovery for EtherNet/IP.

        This generates CIP Identity Object queries that Cisco Cyber Vision
        uses for detailed device identification beyond basic ListIdentity.

        Args:
            flow_id: Flow identifier
        """
        # Find the flow
        flow_state = None
        for fs in self.flows:
            if fs.flow.flow_id == flow_id:
                flow_state = fs
                break

        if not flow_state:
            logger.warning(f"Flow {flow_id} not found for CIP discovery event")
            return

        # Check if engine supports CIP discovery
        if not hasattr(flow_state.engine, "generate_cip_discovery_sequence"):
            return

        # Generate CIP discovery sequence (GetAttributeAll, GetAttributeSingle)
        cip_events = flow_state.engine.generate_cip_discovery_sequence(
            flow_state.flow,
            flow_state.conversation,
            start_time_ms=self.current_time_ms,
        )

        for packet_event in cip_events:
            self.scheduler.schedule(packet_event.timestamp_ms, packet_event)

        logger.debug(f"Scheduled CIP discovery for flow {flow_id}")
