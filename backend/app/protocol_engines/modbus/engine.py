"""Modbus TCP protocol engine implementation.

Enhanced with:
- Fingerprint-based TCP stack characteristics
- Exception response injection with configurable rates
- Timeout behavior simulation
- Retry sequence generation
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
from app.protocol_engines.modbus.packets import (
    build_mbap_header,
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_handshake_ack,
    build_tcp_handshake_syn,
    build_tcp_handshake_syn_ack,
    build_tcp_packet,
    build_tcp_packet_fingerprinted,
)
from app.protocol_engines.jitter import get_response_delay
from app.protocol_engines.types import (
    ConversationState,
    ConversationStateBase,
    FlowContext,
    ModbusConversationState,
    PacketEvent,
    ProtocolType,
)
from app.traffic_generator.flow_coordinator import (
    sample_function_code,
    sample_address_range,
)


@register_engine(ProtocolType.MODBUS_TCP)
class ModbusTcpEngine(ProtocolEngine):
    """Modbus TCP protocol engine."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.MODBUS_TCP

    def create_initial_state(self, flow: FlowContext) -> ModbusConversationState:
        """Create initial conversation state using typed ModbusConversationState."""
        return ModbusConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            transaction_id=random.randint(1, 65535),
            sequence_number=random.randint(1000, 9999),
            tcp_seq_client=random.randint(100_000_000, 4_000_000_000),
            tcp_seq_server=random.randint(100_000_000, 4_000_000_000),
            tcp_ack_client=0,
            tcp_ack_server=0,
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ModbusConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate TCP three-way handshake."""
        # Get TCP sequence numbers from typed state
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # Get fingerprinted TCP options for client and server
        client_tcp_opts = flow.source.fingerprint_applicator.get_tcp_options()
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()

        # SYN from client
        syn_packet = build_tcp_handshake_syn(
            flow.source, flow.destination, client_seq, tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"type": "tcp_syn"},
        )

        # SYN-ACK from server (typical 1-2ms response)
        syn_ack_time = start_time_ms + random.uniform(1.0, 2.0)
        syn_ack_packet = build_tcp_handshake_syn_ack(
            flow.destination,
            flow.source,
            server_seq,
            client_seq + 1,
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=syn_ack_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"type": "tcp_syn_ack"},
        )

        # ACK from client (minimal delay)
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
            metadata={"type": "tcp_ack"},
        )

        # Update state with final sequence numbers
        state.tcp_seq_client = client_seq + 1
        state.tcp_seq_server = server_seq + 1
        state.tcp_ack_client = server_seq + 1
        state.tcp_ack_server = client_seq + 1

        # ============================================================
        # Modbus MEI Discovery (FC 43 — Read Device Identification)
        # ============================================================
        # Cisco Cyber Vision uses FC 43 responses to fingerprint Modbus
        # devices (vendor name, product code, firmware version).
        mei_start = start_time_ms + random.uniform(5.0, 15.0)
        yield from self._generate_mei_discovery(flow, state, mei_start)

    def _generate_mei_discovery(
        self,
        flow: FlowContext,
        state: ModbusConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Modbus FC 43 (Read Device Identification) request/response.

        Emits a MEI request (device_id_code=0x01 for basic identification)
        followed by a fingerprinted response containing vendor, model, and
        firmware version.  This is what Cisco Cyber Vision parses to identify
        Modbus devices on the network.
        """
        handler = get_handler(0x2B)
        applicator = flow.destination.fingerprint_applicator
        unit_id = flow.destination.unit_id or 1

        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        client_tcp_opts = flow.source.fingerprint_applicator.get_tcp_options()
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()

        # --- MEI Request (from HMI/scanner) ---
        config_mei = {"device_id_code": 0x02, "object_id": 0x00}
        request_pdu = handler.build_request(config_mei)
        state.transaction_id = (state.transaction_id + 1) % 65536
        request_mbap = build_mbap_header(state.transaction_id, unit_id, len(request_pdu))
        mei_request = request_mbap + request_pdu

        request_packet = build_tcp_packet(
            flow.source, flow.destination, mei_request,
            seq=client_seq, ack=server_seq, flags="PA",
            tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={"type": "modbus_mei_request", "function_code": 0x2B},
        )
        client_seq += len(mei_request)

        # --- MEI Response (from device with fingerprint identity) ---
        response_pdu = handler.build_response_from_fingerprint(config_mei, applicator)
        response_mbap = build_mbap_header(state.transaction_id, unit_id, len(response_pdu))
        mei_response = response_mbap + response_pdu

        response_delay = flow.destination.get_response_delay_ms()
        if response_delay <= 0:
            response_delay = random.uniform(2.0, 10.0)

        response_packet = build_tcp_packet(
            flow.destination, flow.source, mei_response,
            seq=server_seq, ack=client_seq, flags="PA",
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms + response_delay,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={"type": "modbus_mei_response", "function_code": 0x2B},
        )
        server_seq += len(mei_response)

        # Update state
        state.tcp_seq_client = client_seq
        state.tcp_seq_server = server_seq
        state.tcp_ack_client = server_seq
        state.tcp_ack_server = client_seq

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ModbusConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Modbus request/response pair with error injection support.

        Uses device fingerprint for:
        - TCP stack characteristics (TTL, window size, MSS)
        - Response timing distribution
        - Exception injection probability
        - Timeout simulation

        Enhanced with learned patterns:
        - Function code distribution from PCAP analysis
        - Address range patterns from real traffic
        """
        # Check for learned function code distribution
        fc_distribution = flow.config.get("function_code_distribution")
        if fc_distribution:
            # Sample function code from learned distribution
            function_code = sample_function_code(fc_distribution)
        else:
            # Use configured or default function code
            function_code = flow.config.get("function_code", 3)  # Default to Read Holding Registers

        # Check for learned address patterns
        address_patterns = flow.config.get("address_patterns")
        if address_patterns and isinstance(address_patterns, list):
            # Sample address range from learned patterns
            start_address, quantity = sample_address_range(address_patterns)
            # Update config with sampled values
            flow.config["start_address"] = start_address
            flow.config["quantity"] = min(quantity, 125)  # Modbus limit

        handler = get_handler(function_code)

        # Build request PDU
        request_pdu = handler.build_request(flow.config)

        # Build MBAP header
        unit_id = flow.destination.unit_id or 1
        mbap_header = build_mbap_header(state.transaction_id, unit_id, len(request_pdu))

        # Complete Modbus TCP request
        modbus_request = mbap_header + request_pdu

        # Get TCP sequence numbers from typed state
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # Build and yield request packet (using fingerprinted TCP options from source)
        request_packet = build_tcp_packet_fingerprinted(
            flow.source,
            flow.destination,
            modbus_request,
            seq=client_seq,
            ack=server_seq,
            flags="PA",
        )

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "modbus_request",
                "function_code": function_code,
                "transaction_id": state.transaction_id,
            },
        )

        # Get fingerprint applicator from destination device (responder)
        applicator = flow.destination.fingerprint_applicator

        # Check for timeout (no response)
        if applicator.should_timeout():
            # No response - simulate timeout
            # Track retry state using typed state attributes
            retry_count = state.retry_count
            max_retries = applicator.get_max_retries()

            if retry_count < max_retries and applicator.should_retry():
                # Schedule a retry
                state.retry_count = retry_count + 1
                state.pending_request = True
                # Don't update sequence numbers - will retry same request
            else:
                # Give up - update state for next cycle
                state.retry_count = 0
                state.pending_request = False
                state.transaction_id = (state.transaction_id + 1) % 65536
                state.tcp_seq_client = client_seq + len(modbus_request)

            # Yield timeout metadata event (no packet)
            yield PacketEvent(
                timestamp_ms=cycle_time_ms + 5000,  # Typical timeout
                flow_id=flow.flow_id,
                packet_bytes=b"",  # Empty - timeout marker
                direction="timeout",
                metadata={
                    "type": "modbus_timeout",
                    "function_code": function_code,
                    "transaction_id": state.transaction_id,
                    "retry_count": retry_count,
                },
            )
            return

        # Reset retry count on successful response
        state.retry_count = 0
        state.pending_request = False

        # Get response delay from fingerprint timing distribution
        timing_sample = applicator.get_response_delay()
        response_time = cycle_time_ms + timing_sample.delay_ms

        # Check for exception injection
        if applicator.should_inject_error():
            # Build exception response
            exception_code = applicator.get_random_exception_code()
            response_pdu = build_exception_response(function_code, exception_code)

            # Build response MBAP header
            response_mbap = build_mbap_header(state.transaction_id, unit_id, len(response_pdu))
            modbus_response = response_mbap + response_pdu

            # Update TCP sequence numbers for response
            client_seq_after = client_seq + len(modbus_request)

            # Build exception response packet (using fingerprinted TCP options)
            response_packet = build_tcp_packet_fingerprinted(
                flow.destination,
                flow.source,
                modbus_response,
                seq=server_seq,
                ack=client_seq_after,
                flags="PA",
            )

            yield PacketEvent(
                timestamp_ms=response_time,
                flow_id=flow.flow_id,
                packet_bytes=response_packet,
                direction="response",
                metadata={
                    "type": "modbus_exception",
                    "function_code": function_code,
                    "exception_code": exception_code,
                    "transaction_id": state.transaction_id,
                    "is_outlier": timing_sample.is_outlier,
                },
            )
        else:
            # Build normal response PDU
            # For FC 43 (Read Device Identification), use fingerprint applicator
            # to include vulnerable firmware versions from CVE overrides
            if function_code == 0x2B and hasattr(handler, "build_response_from_fingerprint"):
                response_pdu = handler.build_response_from_fingerprint(
                    flow.config, applicator
                )
            else:
                payload_template = flow.payload_template or {}
                # Use PayloadGenerator for register-read function codes
                if (
                    not payload_template.get("values")
                    and flow.payload_generator
                    and function_code in (0x03, 0x04)
                ):
                    quantity = flow.config.get("quantity", 1)
                    values = []
                    for i in range(quantity):
                        try:
                            raw = flow.payload_generator.get_value(
                                f"reg_{i}", cycle_time_ms, as_float=True
                            )
                            values.append(int(raw) & 0xFFFF)
                        except KeyError:
                            values.append(0)
                    payload_template = {**payload_template, "values": values}
                response_pdu = handler.build_response(flow.config, payload_template)

            # Build response MBAP header
            response_mbap = build_mbap_header(state.transaction_id, unit_id, len(response_pdu))
            modbus_response = response_mbap + response_pdu

            # Update TCP sequence numbers for response
            client_seq_after = client_seq + len(modbus_request)

            # Build response packet (using fingerprinted TCP options)
            response_packet = build_tcp_packet_fingerprinted(
                flow.destination,
                flow.source,
                modbus_response,
                seq=server_seq,
                ack=client_seq_after,
                flags="PA",
            )

            yield PacketEvent(
                timestamp_ms=response_time,
                flow_id=flow.flow_id,
                packet_bytes=response_packet,
                direction="response",
                metadata={
                    "type": "modbus_response",
                    "function_code": function_code,
                    "transaction_id": state.transaction_id,
                    "response_delay_ms": timing_sample.delay_ms,
                    "is_outlier": timing_sample.is_outlier,
                },
            )

        # Update state for next cycle
        state.transaction_id = (state.transaction_id + 1) % 65536
        state.tcp_seq_client = client_seq_after
        state.tcp_seq_server = server_seq + len(modbus_response)
        state.tcp_ack_server = client_seq_after
        state.tcp_ack_client = server_seq + len(modbus_response)

    def generate_retry_sequence(
        self,
        flow: FlowContext,
        state: ModbusConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate a retry sequence after timeout.

        This simulates the behavior of a master retrying after a timeout.

        Args:
            flow: Flow context
            state: Conversation state
            start_time_ms: Start timestamp

        Yields:
            PacketEvent for retry attempts
        """
        applicator = flow.destination.fingerprint_applicator
        max_retries = applicator.get_max_retries()
        retry_timeout_ms = 1000.0  # 1 second between retries

        for retry in range(max_retries):
            retry_time = start_time_ms + (retry * retry_timeout_ms)

            # Generate poll cycle for retry
            for event in self.generate_poll_cycle(flow, state, retry_time):
                event.metadata["retry_attempt"] = retry + 1
                yield event

            # Check if we got a response (not timeout)
            if not state.pending_request:
                break

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ModbusConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate TCP connection termination (FIN handshake)."""
        # Get TCP sequence numbers from typed state
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
            metadata={"type": "tcp_fin"},
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
            metadata={"type": "tcp_fin_ack"},
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
            metadata={"type": "tcp_ack"},
        )

    def validate_config(self, config: dict) -> list[str]:
        """Validate Modbus TCP configuration."""
        errors = []

        # Check function code
        function_code = config.get("function_code")
        if function_code is None:
            errors.append("function_code is required")
        elif function_code not in FUNCTION_CODE_HANDLERS:
            errors.append(f"Unsupported function_code: {function_code}")

        # Validate based on function code
        if function_code in [0x01, 0x02, 0x03, 0x04]:  # Read operations
            if "start_address" not in config:
                errors.append("start_address is required for read operations")
            if "quantity" not in config:
                errors.append("quantity is required for read operations")
            elif config["quantity"] < 1 or config["quantity"] > 125:
                errors.append("quantity must be between 1 and 125")

        elif function_code in [0x05, 0x06]:  # Write single
            if "address" not in config:
                errors.append("address is required for single write operations")
            if "value" not in config:
                errors.append("value is required for single write operations")

        elif function_code in [0x0F, 0x10]:  # Write multiple
            if "start_address" not in config:
                errors.append("start_address is required for multiple write operations")
            if "values" not in config:
                errors.append("values is required for multiple write operations")
            elif not isinstance(config["values"], list):
                errors.append("values must be a list")

        return errors
