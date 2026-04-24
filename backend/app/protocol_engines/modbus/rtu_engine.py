# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Modbus RTU protocol engine implementation.

Modbus RTU (Remote Terminal Unit) is the serial variant of Modbus.
This engine supports:
- Pure RTU frames (for serial capture simulation)
- RTU over TCP (for serial-to-Ethernet gateway scenarios)

Key differences from Modbus TCP:
- No MBAP header (7 bytes saved)
- Uses CRC-16 checksum (2 bytes added)
- Unit ID is part of the frame, not header
- Inter-frame gaps based on baud rate (3.5 character times)

Transport modes:
- RTU over TCP (port 502 or custom): RTU frames encapsulated in TCP
- Raw RTU: Pure serial bytes (for custom capture formats)
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.modbus.function_codes import (
    FUNCTION_CODE_HANDLERS,
    build_exception_response,
    get_handler,
)
from app.protocol_engines.modbus.rtu_packets import (
    build_rtu_frame,
    build_rtu_over_tcp_fingerprinted,
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_handshake_ack,
    build_tcp_handshake_syn,
    build_tcp_handshake_syn_ack,
    calculate_crc16,
)
from app.protocol_engines.types import (
    FlowContext,
    ModbusRtuConversationState,
    PacketEvent,
    ProtocolType,
)
from app.traffic_generator.flow_coordinator import (
    sample_address_range,
    sample_function_code,
)


# Inter-frame timing based on baud rate (3.5 character times)
# At 9600 baud: 1 char = 11 bits / 9600 = 1.146ms, so 3.5 chars = ~4ms
BAUD_RATE_TIMING_MS = {
    9600: 4.0,      # Common for RS-485
    19200: 2.0,     # Faster RS-485
    38400: 1.0,     # High-speed
    115200: 0.35,   # Maximum common baud
}


@register_engine(ProtocolType.MODBUS_RTU)
class ModbusRtuEngine(ProtocolEngine):
    """Modbus RTU protocol engine.

    Supports both pure RTU frames and RTU-over-TCP encapsulation.
    Uses the same function code handlers as Modbus TCP.
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.MODBUS_RTU

    def create_initial_state(self, flow: FlowContext) -> ModbusRtuConversationState:
        """Create initial conversation state for RTU."""
        # Get baud rate from config or default to 9600
        baud_rate = flow.config.get("baud_rate", 9600)
        transport_mode = flow.config.get("transport_mode", "rtu_over_tcp")

        return ModbusRtuConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            # RTU uses unit_id from frame, not transaction_id
            current_unit_id=flow.destination.unit_id or 1,
            # TCP sequence tracking for RTU-over-TCP mode
            tcp_seq_client=random.randint(1000, 9999),
            tcp_seq_server=random.randint(1000, 9999),
            tcp_ack_client=0,
            tcp_ack_server=0,
            # Serial timing
            baud_rate=baud_rate,
            inter_frame_gap_ms=BAUD_RATE_TIMING_MS.get(baud_rate, 4.0),
            transport_mode=transport_mode,
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ModbusRtuConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate startup sequence.

        For RTU-over-TCP: TCP three-way handshake
        For pure RTU: No startup needed (serial is always "connected")
        """
        if state.transport_mode != "rtu_over_tcp":
            # Pure serial - no startup handshake
            return

        # TCP three-way handshake for RTU-over-TCP
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # SYN from client
        syn_packet = build_tcp_handshake_syn(flow.source, flow.destination, client_seq)
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"type": "tcp_syn", "protocol": "modbus_rtu"},
        )

        # SYN-ACK from server
        syn_ack_time = start_time_ms + random.uniform(1.0, 2.0)
        syn_ack_packet = build_tcp_handshake_syn_ack(
            flow.destination,
            flow.source,
            server_seq,
            client_seq + 1,
        )
        yield PacketEvent(
            timestamp_ms=syn_ack_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"type": "tcp_syn_ack", "protocol": "modbus_rtu"},
        )

        # ACK from client
        ack_time = syn_ack_time + random.uniform(0.1, 0.5)
        ack_packet = build_tcp_handshake_ack(
            flow.source,
            flow.destination,
            client_seq + 1,
            server_seq + 1,
        )
        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack", "protocol": "modbus_rtu"},
        )

        # Update state
        state.tcp_seq_client = client_seq + 1
        state.tcp_seq_server = server_seq + 1
        state.tcp_ack_client = server_seq + 1
        state.tcp_ack_server = client_seq + 1

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ModbusRtuConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Modbus RTU request/response pair.

        Uses CRC-16 checksums instead of MBAP headers.
        Supports learned patterns for function codes and addresses.
        """
        # Sample function code from learned distribution or config
        fc_distribution = flow.config.get("function_code_distribution")
        if fc_distribution:
            function_code = sample_function_code(fc_distribution)
        else:
            function_code = flow.config.get("function_code", 3)

        # Sample address range from learned patterns
        address_patterns = flow.config.get("address_patterns")
        if address_patterns and isinstance(address_patterns, list):
            start_address, quantity = sample_address_range(address_patterns)
            flow.config["start_address"] = start_address
            flow.config["quantity"] = min(quantity, 125)

        handler = get_handler(function_code)

        # Build request PDU (function code + data)
        request_pdu = handler.build_request(flow.config)

        # Build complete RTU frame with CRC
        unit_id = state.current_unit_id
        request_frame = build_rtu_frame(unit_id, request_pdu)

        # Get sequence numbers for TCP encapsulation
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # Build request packet based on transport mode
        if state.transport_mode == "rtu_over_tcp":
            request_packet = build_rtu_over_tcp_fingerprinted(
                flow.source,
                flow.destination,
                request_frame,
                seq=client_seq,
                ack=server_seq,
                flags="PA",
            )
        else:
            # Pure RTU - just the frame bytes
            request_packet = request_frame

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "modbus_rtu_request",
                "function_code": function_code,
                "unit_id": unit_id,
                "crc": calculate_crc16(request_frame[:-2]),
                "frame_length": len(request_frame),
                "transport_mode": state.transport_mode,
            },
        )

        # Get fingerprint applicator for response timing and errors
        applicator = flow.destination.fingerprint_applicator

        # Check for timeout simulation
        if applicator.should_timeout():
            retry_count = state.retry_count
            max_retries = applicator.get_max_retries()

            if retry_count < max_retries and applicator.should_retry():
                state.retry_count = retry_count + 1
                state.pending_request = True
            else:
                state.retry_count = 0
                state.pending_request = False
                # Update TCP sequence for next cycle
                if state.transport_mode == "rtu_over_tcp":
                    state.tcp_seq_client = client_seq + len(request_frame)

            yield PacketEvent(
                timestamp_ms=cycle_time_ms + 5000,
                flow_id=flow.flow_id,
                packet_bytes=b"",
                direction="timeout",
                metadata={
                    "type": "modbus_rtu_timeout",
                    "function_code": function_code,
                    "unit_id": unit_id,
                    "retry_count": retry_count,
                },
            )
            return

        # Reset retry state on successful response
        state.retry_count = 0
        state.pending_request = False

        # Get response timing
        timing_sample = applicator.get_response_delay()

        # Add inter-frame gap for serial timing realism
        response_time = cycle_time_ms + timing_sample.delay_ms + state.inter_frame_gap_ms

        # Check for exception injection
        if applicator.should_inject_error():
            exception_code = applicator.get_random_exception_code()
            response_pdu = build_exception_response(function_code, exception_code)
        else:
            # Build normal response
            if function_code == 0x2B and hasattr(handler, "build_response_from_fingerprint"):
                response_pdu = handler.build_response_from_fingerprint(
                    flow.config, applicator
                )
            else:
                payload_template = flow.payload_template or {}
                response_pdu = handler.build_response(flow.config, payload_template)

        # Build response RTU frame with CRC
        response_frame = build_rtu_frame(unit_id, response_pdu)

        # Update TCP sequence numbers for response
        client_seq_after = client_seq + len(request_frame)

        # Build response packet
        if state.transport_mode == "rtu_over_tcp":
            response_packet = build_rtu_over_tcp_fingerprinted(
                flow.destination,
                flow.source,
                response_frame,
                seq=server_seq,
                ack=client_seq_after,
                flags="PA",
            )
        else:
            response_packet = response_frame

        is_exception = applicator.should_inject_error()
        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "modbus_rtu_exception" if is_exception else "modbus_rtu_response",
                "function_code": function_code,
                "unit_id": unit_id,
                "crc": calculate_crc16(response_frame[:-2]),
                "frame_length": len(response_frame),
                "response_delay_ms": timing_sample.delay_ms,
                "is_outlier": timing_sample.is_outlier,
                "baud_rate": state.baud_rate,
            },
        )

        # Update state for next cycle
        if state.transport_mode == "rtu_over_tcp":
            state.tcp_seq_client = client_seq_after
            state.tcp_seq_server = server_seq + len(response_frame)
            state.tcp_ack_server = client_seq_after
            state.tcp_ack_client = server_seq + len(response_frame)

    def generate_broadcast_request(
        self,
        flow: FlowContext,
        state: ModbusRtuConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Modbus RTU broadcast request (unit_id = 0).

        Broadcast requests are sent to all slaves on the bus.
        No response is expected (slaves execute silently).
        Commonly used for:
        - Clock synchronization
        - Global reset commands
        - Broadcast write operations

        Args:
            flow: Flow context
            state: Conversation state
            cycle_time_ms: Cycle timestamp

        Yields:
            Single broadcast request PacketEvent (no response)
        """
        function_code = flow.config.get("function_code", 6)  # Default: Write Single Register
        handler = get_handler(function_code)

        # Build request PDU
        request_pdu = handler.build_request(flow.config)

        # Build broadcast frame (unit_id = 0)
        broadcast_unit_id = 0
        request_frame = build_rtu_frame(broadcast_unit_id, request_pdu)

        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        if state.transport_mode == "rtu_over_tcp":
            request_packet = build_rtu_over_tcp_fingerprinted(
                flow.source,
                flow.destination,
                request_frame,
                seq=client_seq,
                ack=server_seq,
                flags="PA",
            )
        else:
            request_packet = request_frame

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "modbus_rtu_broadcast",
                "function_code": function_code,
                "unit_id": broadcast_unit_id,
                "crc": calculate_crc16(request_frame[:-2]),
                "no_response_expected": True,
            },
        )

        # Update TCP sequence (no response expected)
        if state.transport_mode == "rtu_over_tcp":
            state.tcp_seq_client = client_seq + len(request_frame)

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ModbusRtuConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate shutdown sequence.

        For RTU-over-TCP: TCP FIN handshake
        For pure RTU: No shutdown needed
        """
        if state.transport_mode != "rtu_over_tcp":
            return

        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # FIN from client
        fin_packet = build_tcp_fin(
            flow.source,
            flow.destination,
            client_seq,
            server_seq,
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=fin_packet,
            direction="request",
            metadata={"type": "tcp_fin", "protocol": "modbus_rtu"},
        )

        # FIN-ACK from server
        fin_ack_time = start_time_ms + random.uniform(1.0, 2.0)
        fin_ack_packet = build_tcp_fin_ack(
            flow.destination,
            flow.source,
            server_seq,
            client_seq + 1,
        )
        yield PacketEvent(
            timestamp_ms=fin_ack_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack_packet,
            direction="response",
            metadata={"type": "tcp_fin_ack", "protocol": "modbus_rtu"},
        )

        # Final ACK from client
        ack_time = fin_ack_time + random.uniform(0.1, 0.5)
        final_ack_packet = build_tcp_handshake_ack(
            flow.source,
            flow.destination,
            client_seq + 1,
            server_seq + 1,
        )
        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=final_ack_packet,
            direction="request",
            metadata={"type": "tcp_ack", "protocol": "modbus_rtu"},
        )

    def validate_config(self, config: dict) -> list[str]:
        """Validate Modbus RTU configuration."""
        errors = []

        # Validate transport mode
        transport_mode = config.get("transport_mode", "rtu_over_tcp")
        if transport_mode not in ("rtu_over_tcp", "raw_rtu"):
            errors.append(f"Invalid transport_mode: {transport_mode}")

        # Validate baud rate
        baud_rate = config.get("baud_rate", 9600)
        valid_baud_rates = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
        if baud_rate not in valid_baud_rates:
            errors.append(f"Invalid baud_rate: {baud_rate}. Valid: {valid_baud_rates}")

        # Check function code
        function_code = config.get("function_code")
        if function_code is None:
            errors.append("function_code is required")
        elif function_code not in FUNCTION_CODE_HANDLERS:
            errors.append(f"Unsupported function_code: {function_code}")

        # Validate based on function code (same as TCP)
        if function_code in [0x01, 0x02, 0x03, 0x04]:
            if "start_address" not in config:
                errors.append("start_address is required for read operations")
            if "quantity" not in config:
                errors.append("quantity is required for read operations")
            elif config.get("quantity", 0) < 1 or config.get("quantity", 0) > 125:
                errors.append("quantity must be between 1 and 125")

        elif function_code in [0x05, 0x06]:
            if "address" not in config:
                errors.append("address is required for single write operations")
            if "value" not in config:
                errors.append("value is required for single write operations")

        elif function_code in [0x0F, 0x10]:
            if "start_address" not in config:
                errors.append("start_address is required for multiple write operations")
            if "values" not in config:
                errors.append("values is required for multiple write operations")
            elif not isinstance(config.get("values"), list):
                errors.append("values must be a list")

        return errors
