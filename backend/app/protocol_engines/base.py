# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Base protocol engine abstract class."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


class ProtocolEngine(ABC):
    """Abstract base class for protocol engines."""

    @property
    @abstractmethod
    def protocol_type(self) -> ProtocolType:
        """Return the protocol type this engine handles."""
        pass

    @abstractmethod
    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state for a flow.

        Args:
            flow: The flow context

        Returns:
            Initial conversation state
        """
        pass

    @abstractmethod
    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate startup packet sequence (e.g., TCP handshake, session setup).

        Args:
            flow: The flow context
            state: Current conversation state
            start_time_ms: Start time in milliseconds

        Yields:
            Packet events for startup sequence
        """
        pass

    @abstractmethod
    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate a single poll cycle (request/response).

        Args:
            flow: The flow context
            state: Current conversation state
            cycle_time_ms: Time of this cycle in milliseconds

        Yields:
            Packet events for poll cycle
        """
        pass

    @abstractmethod
    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate shutdown packet sequence (e.g., TCP FIN).

        Args:
            flow: The flow context
            state: Current conversation state
            start_time_ms: Start time in milliseconds

        Yields:
            Packet events for shutdown sequence
        """
        pass

    @abstractmethod
    def validate_config(self, config: dict) -> list[str]:
        """Validate protocol-specific configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        pass
