"""Live traffic orchestrator - injects packets onto network interface."""

import heapq
import logging
import random
import struct
import time
from dataclasses import dataclass, field
from typing import Any

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw
from scapy.sendrecv import sendp

logger = logging.getLogger(__name__)


@dataclass
class DeviceContext:
    """Context information for a device in a flow."""
    device_id: str
    mac_address: str
    ip_address: str
    port: int
    unit_id: int = 1


@dataclass
class FlowContext:
    """Context for a communication flow between devices."""
    flow_id: str
    source: DeviceContext
    destination: DeviceContext
    protocol: str
    config: dict[str, Any] = field(default_factory=dict)
    timing_model: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowState:
    """State tracking for a flow during generation."""
    flow: FlowContext
    transaction_id: int = 0
    seq_number: int = 1000
    ack_number: int = 1000
    next_poll_time: float = 0.0
    is_started: bool = False
    poll_interval_ms: float = 1000.0


class LiveTrafficOrchestrator:
    """Orchestrates live traffic injection across multiple flows."""

    def __init__(self, interface: str, duration_ms: int | None):
        """Initialize orchestrator.

        Args:
            interface: Network interface for packet injection
            duration_ms: Total duration in milliseconds, or None for perpetual mode
        """
        self.interface = interface
        self.duration_ms = duration_ms
        self.perpetual = duration_ms is None
        self.flows: list[FlowState] = []
        self.event_queue: list[tuple[float, int, Any]] = []  # (time_ms, counter, event)
        self.event_counter = 0
        self.packets_sent = 0
        self.start_time: float = 0
        self._running = True  # Flag for graceful shutdown

    def add_flow(self, flow_context: FlowContext) -> None:
        """Add a flow to be generated."""
        poll_interval = flow_context.timing_model.get("poll_interval_ms", 1000.0)

        flow_state = FlowState(
            flow=flow_context,
            poll_interval_ms=poll_interval,
            seq_number=random.randint(1000, 50000),
            ack_number=random.randint(1000, 50000),
        )

        self.flows.append(flow_state)
        logger.info(f"Added flow {flow_context.flow_id} ({flow_context.protocol})")

    def _schedule_event(self, time_ms: float, event: Any) -> None:
        """Schedule an event at a specific time."""
        heapq.heappush(self.event_queue, (time_ms, self.event_counter, event))
        self.event_counter += 1

    def _apply_jitter(self, interval_ms: float, timing_model: dict) -> float:
        """Apply jitter to an interval."""
        jitter_min = timing_model.get("jitter_min_ms", 0)
        jitter_max = timing_model.get("jitter_max_ms", 50)
        jitter = random.uniform(jitter_min, jitter_max)
        return interval_ms + jitter

    def _send_packet(self, packet_bytes: bytes) -> None:
        """Send a packet on the interface."""
        try:
            # packet_bytes is already a complete Ethernet frame from _build_tcp_packet
            # Use Raw to send the bytes directly without additional parsing
            sendp(Raw(packet_bytes), iface=self.interface, verbose=False)
            self.packets_sent += 1

            if self.packets_sent % 100 == 0:
                logger.info(f"Sent {self.packets_sent} packets")
        except Exception as e:
            logger.error(f"Failed to send packet: {e}")

    def _build_tcp_packet(
        self,
        src: DeviceContext,
        dst: DeviceContext,
        payload: bytes,
        seq: int,
        ack: int,
        flags: str = "PA",
    ) -> bytes:
        """Build a TCP packet with full headers."""
        packet = (
            Ether(src=src.mac_address, dst=dst.mac_address)
            / IP(src=src.ip_address, dst=dst.ip_address)
            / TCP(sport=src.port, dport=dst.port, seq=seq, ack=ack, flags=flags)
        )
        if payload:
            packet = packet / Raw(load=payload)
        return bytes(packet)

    def _build_modbus_request(
        self, transaction_id: int, unit_id: int, function_code: int,
        start_addr: int, quantity: int
    ) -> bytes:
        """Build a Modbus TCP request."""
        pdu = struct.pack(">BHH", function_code, start_addr, quantity)
        length = len(pdu) + 1
        mbap = struct.pack(">HHHB", transaction_id, 0, length, unit_id)
        return mbap + pdu

    def _build_modbus_response(
        self, transaction_id: int, unit_id: int, function_code: int,
        register_values: list[int]
    ) -> bytes:
        """Build a Modbus TCP response."""
        byte_count = len(register_values) * 2
        data = struct.pack(">" + "H" * len(register_values), *register_values)
        pdu = struct.pack(">BB", function_code, byte_count) + data
        length = len(pdu) + 1
        mbap = struct.pack(">HHHB", transaction_id, 0, length, unit_id)
        return mbap + pdu

    def _generate_startup(self, flow_state: FlowState, time_ms: float) -> None:
        """Generate TCP handshake for a flow."""
        flow = flow_state.flow
        src = flow.source
        dst = flow.destination

        # SYN from client
        syn = self._build_tcp_packet(src, dst, b"", flow_state.seq_number, 0, "S")
        self._schedule_event(time_ms, ("packet", syn))

        # SYN-ACK from server
        syn_ack = self._build_tcp_packet(
            dst, src, b"", flow_state.ack_number, flow_state.seq_number + 1, "SA"
        )
        self._schedule_event(time_ms + 5, ("packet", syn_ack))

        # ACK from client
        ack = self._build_tcp_packet(
            src, dst, b"", flow_state.seq_number + 1, flow_state.ack_number + 1, "A"
        )
        self._schedule_event(time_ms + 10, ("packet", ack))

        flow_state.seq_number += 1
        flow_state.ack_number += 1
        flow_state.is_started = True

    def _generate_poll_cycle(self, flow_state: FlowState, time_ms: float) -> None:
        """Generate a request/response cycle."""
        flow = flow_state.flow
        src = flow.source
        dst = flow.destination

        flow_state.transaction_id += 1

        if flow.protocol == "modbus_tcp":
            # Modbus request
            config = flow.config
            function_code = config.get("function_code", 3)
            start_addr = config.get("start_address", 0)
            quantity = config.get("quantity", 10)
            unit_id = dst.unit_id or 1

            request_payload = self._build_modbus_request(
                flow_state.transaction_id, unit_id, function_code, start_addr, quantity
            )
            request_pkt = self._build_tcp_packet(
                src, dst, request_payload, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(time_ms, ("packet", request_pkt))

            # Response with random values
            response_values = [random.randint(0, 65535) for _ in range(quantity)]
            response_payload = self._build_modbus_response(
                flow_state.transaction_id, unit_id, function_code, response_values
            )

            # Response timing with jitter
            response_delay = random.uniform(5, 50)
            response_pkt = self._build_tcp_packet(
                dst, src, response_payload,
                flow_state.ack_number, flow_state.seq_number + len(request_payload)
            )
            self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

            # Update sequence numbers
            flow_state.seq_number += len(request_payload)
            flow_state.ack_number += len(response_payload)

        else:
            # Generic TCP traffic for other protocols (profinet, ethernet_ip, etc.)
            # Generate a simple request/response with random payload data
            request_payload = struct.pack(
                ">HHI",
                flow_state.transaction_id,  # Transaction ID
                random.randint(1, 100),     # Function/command code
                random.randint(0, 1000),    # Data value
            ) + bytes(random.randint(0, 255) for _ in range(random.randint(4, 20)))

            request_pkt = self._build_tcp_packet(
                src, dst, request_payload, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(time_ms, ("packet", request_pkt))

            # Generate response
            response_payload = struct.pack(
                ">HHI",
                flow_state.transaction_id,
                0,  # Success status
                random.randint(0, 65535),
            ) + bytes(random.randint(0, 255) for _ in range(random.randint(8, 32)))

            response_delay = random.uniform(5, 50)
            response_pkt = self._build_tcp_packet(
                dst, src, response_payload,
                flow_state.ack_number, flow_state.seq_number + len(request_payload)
            )
            self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

            # Update sequence numbers
            flow_state.seq_number += len(request_payload)
            flow_state.ack_number += len(response_payload)

    def _generate_shutdown(self, flow_state: FlowState, time_ms: float) -> None:
        """Generate TCP connection teardown."""
        flow = flow_state.flow
        src = flow.source
        dst = flow.destination

        # FIN from client
        fin = self._build_tcp_packet(
            src, dst, b"", flow_state.seq_number, flow_state.ack_number, "FA"
        )
        self._schedule_event(time_ms, ("packet", fin))

        # FIN-ACK from server
        fin_ack = self._build_tcp_packet(
            dst, src, b"", flow_state.ack_number, flow_state.seq_number + 1, "FA"
        )
        self._schedule_event(time_ms + 5, ("packet", fin_ack))

        # ACK from client
        ack = self._build_tcp_packet(
            src, dst, b"", flow_state.seq_number + 1, flow_state.ack_number + 1, "A"
        )
        self._schedule_event(time_ms + 10, ("packet", ack))

    def stop(self) -> None:
        """Signal the orchestrator to stop (for graceful shutdown)."""
        self._running = False

    def run(self) -> int:
        """Run the traffic generation.

        Returns:
            Number of packets sent
        """
        logger.info(f"Starting live traffic generation on interface {self.interface}")
        if self.perpetual:
            logger.info(f"Mode: PERPETUAL (runs until stopped), Flows: {len(self.flows)}")
        else:
            logger.info(f"Duration: {self.duration_ms}ms, Flows: {len(self.flows)}")

        self.start_time = time.time() * 1000

        # Schedule startup for all flows
        for i, flow_state in enumerate(self.flows):
            startup_offset = i * 100  # Stagger startups
            self._generate_startup(flow_state, startup_offset)

            # Schedule first poll
            first_poll = startup_offset + 50 + self._apply_jitter(
                flow_state.poll_interval_ms, flow_state.flow.timing_model
            )
            self._schedule_event(first_poll, ("poll", flow_state.flow.flow_id))

        # Main event loop
        while self.event_queue and self._running:
            event_time, _, event = heapq.heappop(self.event_queue)

            # Check if we've exceeded duration (only for timed mode)
            if not self.perpetual and event_time > self.duration_ms:
                break

            # Wait until event time
            current_time = (time.time() * 1000) - self.start_time
            if event_time > current_time:
                sleep_time = (event_time - current_time) / 1000
                time.sleep(sleep_time)

            # Handle event
            if event[0] == "packet":
                self._send_packet(event[1])
            elif event[0] == "poll":
                flow_id = event[1]
                for flow_state in self.flows:
                    if flow_state.flow.flow_id == flow_id:
                        self._generate_poll_cycle(flow_state, event_time)
                        # Schedule next poll
                        next_poll = event_time + self._apply_jitter(
                            flow_state.poll_interval_ms, flow_state.flow.timing_model
                        )
                        # In perpetual mode, always schedule next poll
                        # In timed mode, only if within duration
                        if self.perpetual or next_poll < self.duration_ms:
                            self._schedule_event(next_poll, ("poll", flow_id))
                        break

        # Generate shutdown sequences (only for timed mode or when stopped)
        if not self.perpetual or not self._running:
            current_time = (time.time() * 1000) - self.start_time
            shutdown_time = self.duration_ms if not self.perpetual else current_time
            for flow_state in self.flows:
                self._generate_shutdown(flow_state, shutdown_time)
                shutdown_time += 20

            # Process remaining shutdown events
            while self.event_queue:
                event_time, _, event = heapq.heappop(self.event_queue)
                current_time = (time.time() * 1000) - self.start_time
                if event_time > current_time:
                    sleep_time = (event_time - current_time) / 1000
                    time.sleep(sleep_time)

                if event[0] == "packet":
                    self._send_packet(event[1])

        logger.info(f"Generation complete: {self.packets_sent} packets sent")
        return self.packets_sent
