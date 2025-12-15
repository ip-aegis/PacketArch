"""AI-enhanced protocol engine wrapper.

This module provides a wrapper that adds AI-powered capabilities to any
base protocol engine, including:
- Learned timing distributions
- Context-aware response delays
- Anomaly injection hooks
- Learned payload value generation
"""

import logging
from collections.abc import Iterator
from typing import Any, TYPE_CHECKING

from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)
from app.protocol_engines.ai_timing import (
    ContextAwareTimingModel,
    LearnedTimingService,
    get_device_personality,
    create_learned_jitter_model_from_pattern,
    DistributionParams,
    LearnedJitterModel,
)

if TYPE_CHECKING:
    from app.ai_services.learned_payload_generator import LearnedPayloadGenerator

logger = logging.getLogger(__name__)


class AIEnhancedProtocolEngine(ProtocolEngine):
    """Wrapper that adds AI-powered capabilities to a base protocol engine.

    This engine wraps any existing protocol engine and enhances it with:
    - Learned timing distributions from PCAP analysis
    - Device personality-based timing variations
    - Anomaly injection hooks
    - Context-aware response timing
    """

    def __init__(
        self,
        base_engine: ProtocolEngine,
        timing_patterns: list[dict[str, Any]] | None = None,
        payload_patterns: list[dict[str, Any]] | None = None,
        anomaly_config: dict[str, Any] | None = None,
    ):
        """Initialize AI-enhanced engine.

        Args:
            base_engine: The base protocol engine to wrap
            timing_patterns: Learned timing patterns from PCAP analysis
            payload_patterns: Learned payload patterns
            anomaly_config: Configuration for anomaly injection
        """
        self._base_engine = base_engine
        self._timing_patterns = timing_patterns or []
        self._payload_patterns = payload_patterns or []
        self._anomaly_config = anomaly_config or {}

        # Timing service
        self._timing_service = LearnedTimingService()

        # Flow-specific timing models
        self._flow_timing: dict[str, ContextAwareTimingModel] = {}

        # Payload generator (lazy loaded)
        self._payload_generator: "LearnedPayloadGenerator | None" = None

        # Anomaly injection state
        self._anomaly_injection_enabled = self._anomaly_config.get("enabled", False)
        self._anomaly_schedule: list[dict[str, Any]] = []

    @property
    def protocol_type(self) -> ProtocolType:
        """Return the protocol type from base engine."""
        return self._base_engine.protocol_type

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state via base engine.

        Also initializes AI-enhanced state tracking.
        """
        state = self._base_engine.create_initial_state(flow)

        # Initialize timing model for this flow
        vendor = flow.source.vendor or flow.destination.vendor
        self._flow_timing[flow.flow_id] = self._timing_service.get_model_for_flow(
            flow_id=flow.flow_id,
            protocol=self._base_engine.protocol_type.value,
            patterns=self._timing_patterns,
            vendor=vendor,
        )

        # Add AI state to custom_data
        state.custom_data["ai_enhanced"] = True
        state.custom_data["response_count"] = 0
        state.custom_data["error_count"] = 0

        return state

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate startup sequence with AI-enhanced timing.

        The base engine generates packets, but we adjust timing based
        on learned patterns.
        """
        for event in self._base_engine.generate_startup_sequence(flow, state, start_time_ms):
            # Apply learned timing adjustment
            adjusted_event = self._apply_timing_adjustment(flow, state, event)
            yield adjusted_event

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate poll cycle with AI-enhanced timing and payloads.

        This is where most of the AI enhancement happens:
        - Request timing from learned distributions
        - Response timing with device personality
        - Payload values from learned patterns
        - Anomaly injection if configured
        """
        # Check for scheduled anomaly injection
        should_inject_anomaly = self._should_inject_anomaly(cycle_time_ms)

        if should_inject_anomaly:
            # Generate anomaly instead of normal cycle
            yield from self._generate_anomaly_cycle(flow, state, cycle_time_ms)
            return

        # Normal poll cycle with AI-enhanced timing
        for event in self._base_engine.generate_poll_cycle(flow, state, cycle_time_ms):
            # Apply timing adjustment
            adjusted_event = self._apply_timing_adjustment(flow, state, event)

            # Track response for context-aware timing
            if event.direction == "response":
                state.custom_data["response_count"] = state.custom_data.get("response_count", 0) + 1
                timing_model = self._flow_timing.get(flow.flow_id)
                if timing_model:
                    timing_model.record_success()

            yield adjusted_event

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate shutdown sequence with AI-enhanced timing."""
        for event in self._base_engine.generate_shutdown_sequence(flow, state, start_time_ms):
            adjusted_event = self._apply_timing_adjustment(flow, state, event)
            yield adjusted_event

    def validate_config(self, config: dict) -> list[str]:
        """Validate configuration via base engine."""
        return self._base_engine.validate_config(config)

    # ========== AI Enhancement Methods ==========

    def _apply_timing_adjustment(
        self,
        flow: FlowContext,
        state: ConversationState,
        event: PacketEvent,
    ) -> PacketEvent:
        """Apply learned timing adjustments to a packet event.

        Args:
            flow: Flow context
            state: Conversation state
            event: Original packet event

        Returns:
            Adjusted packet event
        """
        timing_model = self._flow_timing.get(flow.flow_id)
        if not timing_model:
            return event

        # Only adjust response timing (requests use inter-arrival patterns)
        if event.direction == "response":
            # Get context-aware timing
            context = {
                "response_count": state.custom_data.get("response_count", 0),
                "error_count": state.custom_data.get("error_count", 0),
            }
            learned_delay = timing_model.get_timing(context)

            # Calculate offset from request time (stored in metadata)
            request_time = event.metadata.get("request_time_ms", event.timestamp_ms - 10)
            adjusted_timestamp = request_time + learned_delay

            return PacketEvent(
                timestamp_ms=adjusted_timestamp,
                flow_id=event.flow_id,
                packet_bytes=event.packet_bytes,
                direction=event.direction,
                metadata={
                    **event.metadata,
                    "original_timestamp_ms": event.timestamp_ms,
                    "learned_delay_ms": learned_delay,
                },
            )

        return event

    def _should_inject_anomaly(self, current_time_ms: float) -> bool:
        """Check if an anomaly should be injected at current time.

        Args:
            current_time_ms: Current simulation time

        Returns:
            True if anomaly should be injected
        """
        if not self._anomaly_injection_enabled:
            return False

        # Check scheduled anomalies
        for anomaly in self._anomaly_schedule:
            if (
                anomaly.get("start_time_ms", 0) <= current_time_ms
                and not anomaly.get("triggered", False)
            ):
                anomaly["triggered"] = True
                return True

        # Random anomaly injection
        anomaly_rate = self._anomaly_config.get("random_rate", 0.0)
        if anomaly_rate > 0:
            import random
            return random.random() < anomaly_rate

        return False

    def _generate_anomaly_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate an anomalous poll cycle.

        Types of anomalies:
        - Timeout: No response
        - Delayed: Very slow response
        - Error: Exception/error response
        - Duplicate: Multiple responses
        - Out-of-order: Response before request logged
        """
        anomaly_type = self._anomaly_config.get("type", "timeout")

        if anomaly_type == "timeout":
            # Generate request but no response
            for event in self._base_engine.generate_poll_cycle(flow, state, cycle_time_ms):
                if event.direction == "request":
                    yield event
                # Skip response events

        elif anomaly_type == "delayed":
            # Generate with very large delay
            delay_factor = self._anomaly_config.get("delay_factor", 10.0)
            for event in self._base_engine.generate_poll_cycle(flow, state, cycle_time_ms):
                if event.direction == "response":
                    yield PacketEvent(
                        timestamp_ms=event.timestamp_ms * delay_factor,
                        flow_id=event.flow_id,
                        packet_bytes=event.packet_bytes,
                        direction=event.direction,
                        metadata={**event.metadata, "anomaly": "delayed"},
                    )
                else:
                    yield event

        elif anomaly_type == "duplicate":
            # Generate duplicate responses
            events = list(self._base_engine.generate_poll_cycle(flow, state, cycle_time_ms))
            for event in events:
                yield event
                if event.direction == "response":
                    # Duplicate response with slight delay
                    yield PacketEvent(
                        timestamp_ms=event.timestamp_ms + 1.0,
                        flow_id=event.flow_id,
                        packet_bytes=event.packet_bytes,
                        direction=event.direction,
                        metadata={**event.metadata, "anomaly": "duplicate"},
                    )

        else:
            # Default: pass through with anomaly flag
            for event in self._base_engine.generate_poll_cycle(flow, state, cycle_time_ms):
                event.metadata["anomaly"] = anomaly_type
                yield event

        # Record error for context-aware timing
        state.custom_data["error_count"] = state.custom_data.get("error_count", 0) + 1
        timing_model = self._flow_timing.get(flow.flow_id)
        if timing_model:
            timing_model.record_error()

    def schedule_anomaly(
        self,
        start_time_ms: float,
        anomaly_type: str,
        duration_ms: float = 0,
        **kwargs,
    ) -> None:
        """Schedule an anomaly injection.

        Args:
            start_time_ms: When to inject the anomaly
            anomaly_type: Type of anomaly
            duration_ms: Duration for sustained anomalies
            **kwargs: Additional anomaly parameters
        """
        self._anomaly_schedule.append({
            "start_time_ms": start_time_ms,
            "type": anomaly_type,
            "duration_ms": duration_ms,
            "triggered": False,
            **kwargs,
        })

    def set_timing_patterns(self, patterns: list[dict[str, Any]]) -> None:
        """Update learned timing patterns.

        Args:
            patterns: New timing patterns from PCAP analysis
        """
        self._timing_patterns = patterns
        # Clear cached models to pick up new patterns
        self._flow_timing.clear()

    def set_payload_patterns(self, patterns: list[dict[str, Any]]) -> None:
        """Update learned payload patterns.

        Args:
            patterns: New payload patterns from PCAP analysis
        """
        self._payload_patterns = patterns
        self._payload_generator = None  # Reset to reload


def create_ai_enhanced_engine(
    protocol: ProtocolType,
    timing_patterns: list[dict[str, Any]] | None = None,
    payload_patterns: list[dict[str, Any]] | None = None,
    anomaly_config: dict[str, Any] | None = None,
) -> AIEnhancedProtocolEngine:
    """Create an AI-enhanced protocol engine.

    Args:
        protocol: Protocol type
        timing_patterns: Learned timing patterns
        payload_patterns: Learned payload patterns
        anomaly_config: Anomaly injection configuration

    Returns:
        AIEnhancedProtocolEngine wrapping the appropriate base engine
    """
    from app.protocol_engines import get_engine

    base_engine = get_engine(protocol)

    return AIEnhancedProtocolEngine(
        base_engine=base_engine,
        timing_patterns=timing_patterns,
        payload_patterns=payload_patterns,
        anomaly_config=anomaly_config,
    )


class AIEnhancedEngineFactory:
    """Factory for creating AI-enhanced engines with loaded patterns.

    This factory handles loading patterns from the database and creating
    appropriately configured AI-enhanced engines.
    """

    def __init__(self):
        """Initialize the factory."""
        self._timing_patterns: dict[str, list[dict[str, Any]]] = {}
        self._payload_patterns: dict[str, list[dict[str, Any]]] = {}

    async def load_patterns(self, db_session: Any) -> None:
        """Load all active patterns from the database.

        Args:
            db_session: Database session
        """
        from sqlalchemy import select
        from app.models.learned_pattern import LearnedPattern, PatternType

        # Load timing patterns
        timing_query = select(LearnedPattern).where(
            LearnedPattern.pattern_type == PatternType.TIMING,
            LearnedPattern.is_active == True,
        )
        result = await db_session.execute(timing_query)
        timing_patterns = result.scalars().all()

        for p in timing_patterns:
            protocol = p.protocol
            if protocol not in self._timing_patterns:
                self._timing_patterns[protocol] = []

            self._timing_patterns[protocol].append({
                "id": str(p.id),
                "name": p.name,
                "protocol": p.protocol,
                "source_ip": p.source_ip,
                "destination_ip": p.destination_ip,
                "distribution_type": p.distribution_type.value if p.distribution_type else "gaussian",
                "timing_params": p.timing_params or {},
                "min_value": p.min_value,
                "max_value": p.max_value,
                "mean_value": p.mean_value,
                "std_dev": p.std_dev,
                "confidence": p.confidence,
            })

        # Load payload patterns
        payload_query = select(LearnedPattern).where(
            LearnedPattern.pattern_type == PatternType.PAYLOAD,
            LearnedPattern.is_active == True,
        )
        result = await db_session.execute(payload_query)
        payload_patterns = result.scalars().all()

        for p in payload_patterns:
            protocol = p.protocol
            if protocol not in self._payload_patterns:
                self._payload_patterns[protocol] = []

            self._payload_patterns[protocol].append({
                "id": str(p.id),
                "name": p.name,
                "protocol": p.protocol,
                "payload_patterns": p.payload_patterns or {},
                "sample_count": p.sample_count,
                "confidence": p.confidence,
            })

        logger.info(
            f"Loaded {sum(len(v) for v in self._timing_patterns.values())} timing patterns "
            f"and {sum(len(v) for v in self._payload_patterns.values())} payload patterns"
        )

    def create_engine(
        self,
        protocol: ProtocolType,
        anomaly_config: dict[str, Any] | None = None,
    ) -> AIEnhancedProtocolEngine:
        """Create an AI-enhanced engine for a protocol.

        Args:
            protocol: Protocol type
            anomaly_config: Optional anomaly injection config

        Returns:
            Configured AIEnhancedProtocolEngine
        """
        protocol_name = protocol.value

        return create_ai_enhanced_engine(
            protocol=protocol,
            timing_patterns=self._timing_patterns.get(protocol_name, []),
            payload_patterns=self._payload_patterns.get(protocol_name, []),
            anomaly_config=anomaly_config,
        )

    def get_patterns_for_protocol(self, protocol: str) -> dict[str, list[dict[str, Any]]]:
        """Get all patterns for a protocol.

        Args:
            protocol: Protocol name

        Returns:
            Dictionary with timing_patterns and payload_patterns
        """
        return {
            "timing_patterns": self._timing_patterns.get(protocol, []),
            "payload_patterns": self._payload_patterns.get(protocol, []),
        }
