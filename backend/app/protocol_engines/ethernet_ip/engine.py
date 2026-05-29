# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""EtherNet/IP protocol engine implementation.

Enhanced with:
- Fingerprint-based TCP stack characteristics
- CIP error response injection
- Timeout behavior simulation
- Connection recovery sequences
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.ethernet_ip.packets import (
    CIP_CLASS_IDENTITY,
    CIP_SERVICE_GET_ATTRIBUTE_ALL,
    CIP_SERVICE_GET_ATTRIBUTE_SINGLE,
    CIP_STATUS_CONNECTION_LOST,
    CIP_STATUS_RESOURCE_UNAVAILABLE,
    build_cip_error_response,
    build_cip_forward_open_request,
    build_cip_forward_open_response,
    build_cip_get_attribute_all_response,
    build_cip_get_attribute_single_response,
    build_cip_io_data,
    build_cip_unconnected_send_request,
    build_cip_unconnected_send_response,
    build_enip_packet,
    build_enip_packet_fingerprinted,
    build_forward_open_error_response,
    build_list_identity_request_packet,
    build_list_identity_response_packet,
    build_list_services_response,
    build_register_session_request,
    build_register_session_response,
)
from app.protocol_engines.tcp_builder import (
    build_tcp_ack as build_tcp_handshake_ack,
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_syn as build_tcp_handshake_syn,
    build_tcp_syn_ack as build_tcp_handshake_syn_ack,
)
from app.protocol_engines.types import (
    ConversationState,
    EtherNetIPConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


@register_engine(ProtocolType.ETHERNET_IP)
class EtherNetIPEngine(ProtocolEngine):
    """EtherNet/IP protocol engine."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.ETHERNET_IP

    def create_initial_state(self, flow: FlowContext) -> EtherNetIPConversationState:
        """Create initial conversation state using typed EtherNetIPConversationState."""
        return EtherNetIPConversationState(
            flow_id=flow.flow_id,
            state_name="unconnected",
            transaction_id=0,
            sequence_number=random.randint(1, 65535),
            tcp_seq_client=random.randint(100_000_000, 4_000_000_000),
            tcp_seq_server=random.randint(100_000_000, 4_000_000_000),
            tcp_ack_client=0,
            tcp_ack_server=0,
            session_handle=0,
            connection_id=0,
            io_sequence=0,
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate TCP handshake + RegisterSession + ForwardOpen."""
        current_time = start_time_ms

        # Get TCP sequence numbers from state
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # === TCP Three-Way Handshake ===

        # Get fingerprinted TCP options for client and server
        client_tcp_opts = flow.source.fingerprint_applicator.get_tcp_options()
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()

        # SYN from client
        syn_packet = build_tcp_handshake_syn(
            flow.source, flow.destination, client_seq, tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"type": "tcp_syn"},
        )

        # SYN-ACK from server
        current_time += random.uniform(1.0, 2.0)
        syn_ack_packet = build_tcp_handshake_syn_ack(
            flow.destination,
            flow.source,
            server_seq,
            client_seq + 1,
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"type": "tcp_syn_ack"},
        )

        # ACK from client
        current_time += random.uniform(0.1, 0.5)
        ack_packet = build_tcp_handshake_ack(
            flow.source,
            flow.destination,
            client_seq + 1,
            server_seq + 1,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

        # Update TCP sequence numbers
        client_seq += 1
        server_seq += 1

        # === RegisterSession ===

        current_time += random.uniform(5.0, 10.0)

        # RegisterSession request
        register_request = build_register_session_request()
        register_packet = build_enip_packet(
            flow.source,
            flow.destination,
            register_request,
            seq=client_seq,
            ack=server_seq,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=register_packet,
            direction="request",
            metadata={"type": "enip_register_session_request"},
        )

        # RegisterSession response
        response_delay = random.uniform(2.0, 5.0)
        current_time += response_delay

        session_handle = random.randint(1, 0xFFFFFFFF)
        state.session_handle = session_handle

        register_response = build_register_session_response(session_handle)
        response_packet = build_enip_packet(
            flow.destination,
            flow.source,
            register_response,
            seq=server_seq,
            ack=client_seq + len(register_request),
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "enip_register_session_response",
                "session_handle": session_handle,
            },
        )

        # Update sequence numbers
        client_seq += len(register_request)
        server_seq += len(register_response)

        # === ForwardOpen (Optional, for explicit messaging) ===

        if flow.config.get("use_forward_open", True):
            current_time += random.uniform(10.0, 20.0)

            # ForwardOpen request — wraps in EIP encap (cmd 0x6F SendRRData)
            # using the session_handle assigned by RegisterSession.
            forward_open_request = build_cip_forward_open_request(
                session_handle=session_handle,
            )
            forward_open_packet = build_enip_packet(
                flow.source,
                flow.destination,
                forward_open_request,
                seq=client_seq,
                ack=server_seq,
                flags="PA",
            )
            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=forward_open_packet,
                direction="request",
                metadata={"type": "enip_forward_open_request"},
            )

            # ForwardOpen response
            response_delay = random.uniform(5.0, 10.0)
            current_time += response_delay

            connection_id = random.randint(1, 0xFFFFFFFF)
            state.connection_id = connection_id

            forward_open_response = build_cip_forward_open_response(
                success=True,
                session_handle=session_handle,
            )
            response_packet = build_enip_packet(
                flow.destination,
                flow.source,
                forward_open_response,
                seq=server_seq,
                ack=client_seq + len(forward_open_request),
                flags="PA",
            )
            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=response_packet,
                direction="response",
                metadata={
                    "type": "enip_forward_open_response",
                    "connection_id": connection_id,
                },
            )

            client_seq += len(forward_open_request)
            server_seq += len(forward_open_response)

        # === CIP Identity Discovery (in-band, after TCP session is established) ===
        # Cisco Cyber Vision fingerprints via GetAttributeAll on Identity Object.
        # These MUST happen inside the TCP session — scheduling as a deferred event
        # fires before the TCP handshake completes (timing race).

        applicator = flow.destination.fingerprint_applicator
        sender_context = bytes([random.randint(0, 255) for _ in range(8)])

        # --- GetAttributeAll on Identity Object (Class 0x01, Instance 1) ---
        current_time += random.uniform(10.0, 30.0)

        get_all_request = build_cip_unconnected_send_request(
            service=CIP_SERVICE_GET_ATTRIBUTE_ALL,
            class_id=CIP_CLASS_IDENTITY,
            instance_id=1,
            attribute_id=None,
            session_handle=session_handle,
            sender_context=sender_context,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=build_enip_packet_fingerprinted(
                flow.source, flow.destination, get_all_request,
                seq=client_seq, ack=server_seq, flags="PA",
            ),
            direction="request",
            metadata={"type": "cip_get_attribute_all_request", "class": CIP_CLASS_IDENTITY, "instance": 1},
        )

        timing_sample = applicator.get_response_delay()
        current_time += timing_sample.delay_ms

        cip_response = build_cip_get_attribute_all_response(applicator, CIP_CLASS_IDENTITY, 1)
        get_all_response = build_cip_unconnected_send_response(cip_response, session_handle, sender_context)
        client_seq += len(get_all_request)

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=build_enip_packet_fingerprinted(
                flow.destination, flow.source, get_all_response,
                seq=server_seq, ack=client_seq, flags="PA",
            ),
            direction="response",
            metadata={"type": "cip_get_attribute_all_response", "class": CIP_CLASS_IDENTITY, "instance": 1},
        )
        server_seq += len(get_all_response)

        # --- GetAttributeSingle for extended attributes ---
        for attr_id, attr_name in [
            (9, "configuration_consistency_value"),
            (10, "heartbeat_interval"),
            (19, "protection_mode"),
            (20, "maximum_cip_connections"),
        ]:
            current_time += random.uniform(5.0, 15.0)
            sender_context = bytes([random.randint(0, 255) for _ in range(8)])

            get_single_request = build_cip_unconnected_send_request(
                service=CIP_SERVICE_GET_ATTRIBUTE_SINGLE,
                class_id=CIP_CLASS_IDENTITY,
                instance_id=1,
                attribute_id=attr_id,
                session_handle=session_handle,
                sender_context=sender_context,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=build_enip_packet_fingerprinted(
                    flow.source, flow.destination, get_single_request,
                    seq=client_seq, ack=server_seq, flags="PA",
                ),
                direction="request",
                metadata={"type": "cip_get_attribute_single_request", "attribute": attr_id, "attribute_name": attr_name},
            )

            timing_sample = applicator.get_response_delay()
            current_time += timing_sample.delay_ms

            cip_resp = build_cip_get_attribute_single_response(applicator, CIP_CLASS_IDENTITY, 1, attr_id)
            get_single_response = build_cip_unconnected_send_response(cip_resp, session_handle, sender_context)
            client_seq += len(get_single_request)

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=build_enip_packet_fingerprinted(
                    flow.destination, flow.source, get_single_response,
                    seq=server_seq, ack=client_seq, flags="PA",
                ),
                direction="response",
                metadata={"type": "cip_get_attribute_single_response", "attribute": attr_id, "attribute_name": attr_name},
            )
            server_seq += len(get_single_response)

        # --- ListServices ---
        current_time += random.uniform(5.0, 15.0)
        sender_context = bytes([random.randint(0, 255) for _ in range(8)])

        from app.protocol_engines.ethernet_ip.packets import (
            ENIP_CMD_LIST_SERVICES,
            build_encapsulation_header,
        )
        list_svc_request = build_encapsulation_header(
            command=ENIP_CMD_LIST_SERVICES,
            length=0,
            session_handle=0,
            sender_context=sender_context,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=build_enip_packet_fingerprinted(
                flow.source, flow.destination, list_svc_request,
                seq=client_seq, ack=server_seq, flags="PA",
            ),
            direction="request",
            metadata={"type": "enip_list_services_request"},
        )

        timing_sample = applicator.get_response_delay()
        current_time += timing_sample.delay_ms

        list_svc_response = build_list_services_response(applicator, sender_context)
        client_seq += len(list_svc_request)

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=build_enip_packet_fingerprinted(
                flow.destination, flow.source, list_svc_response,
                seq=server_seq, ack=client_seq, flags="PA",
            ),
            direction="response",
            metadata={"type": "enip_list_services_response"},
        )
        server_seq += len(list_svc_response)

        # Update state
        state.tcp_seq_client = client_seq
        state.tcp_seq_server = server_seq
        state.tcp_ack_client = server_seq
        state.tcp_ack_server = client_seq
        state.state_name = "io_active"

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate I/O data exchange with error injection support.

        Uses device fingerprint for:
        - TCP stack characteristics (TTL, window size, MSS)
        - Response timing distribution
        - Error injection probability
        - Timeout simulation
        """
        # Get I/O data from config or use default
        io_data_size = flow.config.get("io_data_size", 8)
        if flow.payload_template and "io_data" in flow.payload_template:
            io_data = flow.payload_template["io_data"]
        elif flow.payload_generator:
            io_data = bytearray()
            num_values = io_data_size // 2
            remainder = io_data_size % 2
            for j in range(num_values):
                try:
                    io_data.extend(
                        flow.payload_generator.get_value(f"io_{j}", cycle_time_ms)
                    )
                except KeyError:
                    io_data.extend(b"\x00\x00")
            if remainder:
                io_data.extend(b"\x00")
            io_data = bytes(io_data[:io_data_size])
        else:
            io_data = b"\x00" * io_data_size

        # Build I/O data packet
        state.io_sequence = (state.io_sequence + 1) % 65536
        io_packet_data = build_cip_io_data(io_data)

        # Get TCP sequence numbers
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # I/O request (O->T direction) - using fingerprinted packet
        request_packet = build_enip_packet_fingerprinted(
            flow.source,
            flow.destination,
            io_packet_data,
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
                "type": "enip_io_data",
                "io_sequence": state.io_sequence,
            },
        )

        # Get fingerprint applicator from destination device (responder)
        applicator = flow.destination.fingerprint_applicator

        # Check for timeout (no response)
        if applicator.should_timeout():
            # No response - simulate connection timeout
            retry_count = state.retry_count

            # Yield timeout metadata event
            yield PacketEvent(
                timestamp_ms=cycle_time_ms + 5000,  # RPI timeout (typically 4x RPI)
                flow_id=flow.flow_id,
                packet_bytes=b"",  # Empty - timeout marker
                direction="timeout",
                metadata={
                    "type": "enip_io_timeout",
                    "io_sequence": state.io_sequence,
                    "retry_count": retry_count,
                },
            )

            # Track connection issue
            state.consecutive_timeouts = state.consecutive_timeouts + 1

            # Update sequence (client sent data but no response)
            state.tcp_seq_client = client_seq + len(io_packet_data)
            return

        # Reset consecutive timeouts on successful response
        state.consecutive_timeouts = 0

        # Get response delay from fingerprint timing distribution
        timing_sample = applicator.get_response_delay()
        response_time = cycle_time_ms + timing_sample.delay_ms

        # Check for error injection
        if applicator.should_inject_error():
            # Build CIP error response (connection lost or resource unavailable)
            cip_errors = [CIP_STATUS_CONNECTION_LOST, CIP_STATUS_RESOURCE_UNAVAILABLE]
            error_status = random.choice(cip_errors)
            error_data = build_cip_error_response(0x00, error_status)

            # Build error response packet
            response_packet = build_enip_packet_fingerprinted(
                flow.destination,
                flow.source,
                error_data,
                seq=server_seq,
                ack=client_seq + len(io_packet_data),
                flags="PA",
            )

            yield PacketEvent(
                timestamp_ms=response_time,
                flow_id=flow.flow_id,
                packet_bytes=response_packet,
                direction="response",
                metadata={
                    "type": "enip_cip_error",
                    "cip_status": error_status,
                    "io_sequence": state.io_sequence,
                    "is_outlier": timing_sample.is_outlier,
                },
            )

            # Track connection issue
            state.error_count = state.error_count + 1

            # Update sequence numbers
            state.tcp_seq_client = client_seq + len(io_packet_data)
            state.tcp_seq_server = server_seq + len(error_data)
            return

        # Normal I/O response (T->O direction)
        response_packet = build_enip_packet_fingerprinted(
            flow.destination,
            flow.source,
            io_packet_data,
            seq=server_seq,
            ack=client_seq + len(io_packet_data),
            flags="PA",
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "enip_io_data_response",
                "io_sequence": state.io_sequence,
                "response_delay_ms": timing_sample.delay_ms,
                "is_outlier": timing_sample.is_outlier,
            },
        )

        # Update sequence numbers
        state.tcp_seq_client = client_seq + len(io_packet_data)
        state.tcp_seq_server = server_seq + len(io_packet_data)
        state.tcp_ack_client = server_seq + len(io_packet_data)
        state.tcp_ack_server = client_seq + len(io_packet_data)

    def generate_connection_recovery(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate connection recovery sequence after errors/timeouts.

        This simulates re-establishing the CIP connection after failures.

        Args:
            flow: Flow context
            state: Conversation state
            start_time_ms: Start timestamp

        Yields:
            PacketEvent for recovery sequence
        """
        current_time = start_time_ms
        applicator = flow.destination.fingerprint_applicator

        # Check if recovery is needed
        consecutive_timeouts = state.consecutive_timeouts
        error_count = state.error_count

        # Only attempt recovery if we have significant issues
        if consecutive_timeouts < 3 and error_count < 5:
            return

        # Reset counters
        state.consecutive_timeouts = 0
        state.error_count = 0

        # Get TCP sequence numbers
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # ForwardOpen to re-establish connection — wraps in EIP encap (0x6F)
        forward_open_request = build_cip_forward_open_request(
            session_handle=getattr(state, "session_handle", 0) or 0,
        )
        forward_open_packet = build_enip_packet_fingerprinted(
            flow.source,
            flow.destination,
            forward_open_request,
            seq=client_seq,
            ack=server_seq,
            flags="PA",
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=forward_open_packet,
            direction="request",
            metadata={"type": "enip_forward_open_recovery"},
        )

        # Response timing from fingerprint
        timing_sample = applicator.get_response_delay()
        current_time += timing_sample.delay_ms

        # Generate success or failure response
        if random.random() < 0.9:  # 90% success rate for recovery
            connection_id = random.randint(1, 0xFFFFFFFF)
            state.connection_id = connection_id

            forward_open_response = build_cip_forward_open_response(
                success=True,
                session_handle=getattr(state, "session_handle", 0) or 0,
            )
            response_packet = build_enip_packet_fingerprinted(
                flow.destination,
                flow.source,
                forward_open_response,
                seq=server_seq,
                ack=client_seq + len(forward_open_request),
                flags="PA",
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=response_packet,
                direction="response",
                metadata={
                    "type": "enip_forward_open_recovery_success",
                    "connection_id": connection_id,
                },
            )

            state.state_name = "io_active"
        else:
            # Recovery failed
            forward_open_error = build_forward_open_error_response()
            response_packet = build_enip_packet_fingerprinted(
                flow.destination,
                flow.source,
                forward_open_error,
                seq=server_seq,
                ack=client_seq + len(forward_open_request),
                flags="PA",
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=response_packet,
                direction="response",
                metadata={"type": "enip_forward_open_recovery_failed"},
            )

            state.state_name = "connection_failed"

        # Update sequence numbers
        state.tcp_seq_client = client_seq + len(forward_open_request)
        state.tcp_seq_server = server_seq + len(forward_open_response if random.random() < 0.9 else forward_open_error)

    def generate_discovery_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate ListIdentity discovery request/response sequence.

        ListIdentity is the EtherNet/IP device discovery mechanism. Scanners
        like Cyber Vision use this to identify devices and detect vulnerable
        firmware versions.

        The response includes:
        - Vendor ID (ODVA assigned)
        - Device Type (PLC, IO adapter, etc.)
        - Product Code
        - Revision (firmware version) - KEY FOR CVE DETECTION
        - Serial Number
        - Product Name

        Args:
            flow: Flow context with source/destination devices
            state: Conversation state
            start_time_ms: Start timestamp

        Yields:
            PacketEvent for ListIdentity request and response
        """
        current_time = start_time_ms

        # Generate a random sender context for the request
        sender_context = bytes([random.randint(0, 255) for _ in range(8)])

        # ListIdentity Request (UDP broadcast/unicast to port 44818)
        request_packet = build_list_identity_request_packet(
            flow.source,
            flow.destination,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "enip_list_identity_request",
                "protocol": "udp",
                "dst_port": 44818,
            },
        )

        # Get response delay from fingerprint (typically fast for discovery)
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        # Discovery responses are typically faster than I/O
        response_delay = min(timing_sample.delay_ms, 50.0) + random.uniform(1.0, 5.0)
        current_time += response_delay

        # ListIdentity Response (uses fingerprint with vulnerability override)
        # The fingerprint_applicator now includes cve_identity_overrides
        # which will emit vulnerable firmware versions in the response
        response_packet = build_list_identity_response_packet(
            flow.destination,  # Source is the responding device (has fingerprint)
            flow.source,       # Destination is the requester
            sender_context=sender_context,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "enip_list_identity_response",
                "protocol": "udp",
                "has_vulnerability_override": applicator._vulnerability_override is not None,
            },
        )

    def generate_cip_discovery_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate CIP Identity Object attribute query sequence for deep fingerprinting.

        This sequence simulates what Cisco Cyber Vision does during detailed device
        discovery beyond basic ListIdentity:

        1. Establish TCP connection (if not already connected)
        2. RegisterSession to get a session handle
        3. GetAttributeAll on Identity Object (Class 0x01, Instance 0x01)
        4. GetAttributeSingle queries for extended attributes (9, 10, 19, 20)
        5. ListServices to discover capabilities

        The responses include detailed device information like:
        - Configuration Consistency Value
        - Heartbeat Interval
        - Maximum CIP Connections
        - Protection Mode (Rockwell-specific)
        - Supported languages

        Args:
            flow: Flow context with source/destination devices
            state: Conversation state (should be in "registered" state)
            start_time_ms: Start timestamp

        Yields:
            PacketEvent for CIP discovery requests and responses
        """
        current_time = start_time_ms
        applicator = flow.destination.fingerprint_applicator
        session_handle = state.session_handle or 1

        # Get TCP sequence numbers
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # Generate sender context
        sender_context = bytes([random.randint(0, 255) for _ in range(8)])

        # === GetAttributeAll on Identity Object (Class 0x01, Instance 0x01) ===
        # This is the primary deep fingerprinting query

        get_all_request = build_cip_unconnected_send_request(
            service=CIP_SERVICE_GET_ATTRIBUTE_ALL,
            class_id=CIP_CLASS_IDENTITY,
            instance_id=1,
            attribute_id=None,
            session_handle=session_handle,
            sender_context=sender_context,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=build_enip_packet_fingerprinted(
                flow.source,
                flow.destination,
                get_all_request,
                seq=client_seq,
                ack=server_seq,
                flags="PA",
            ),
            direction="request",
            metadata={
                "type": "cip_get_attribute_all_request",
                "class": CIP_CLASS_IDENTITY,
                "instance": 1,
            },
        )

        # Response timing
        timing_sample = applicator.get_response_delay()
        current_time += timing_sample.delay_ms

        # Build GetAttributeAll response with fingerprint data
        cip_response = build_cip_get_attribute_all_response(
            applicator,
            CIP_CLASS_IDENTITY,
            1,
        )
        get_all_response = build_cip_unconnected_send_response(
            cip_response,
            session_handle,
            sender_context,
        )

        client_seq += len(get_all_request)

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=build_enip_packet_fingerprinted(
                flow.destination,
                flow.source,
                get_all_response,
                seq=server_seq,
                ack=client_seq,
                flags="PA",
            ),
            direction="response",
            metadata={
                "type": "cip_get_attribute_all_response",
                "class": CIP_CLASS_IDENTITY,
                "instance": 1,
            },
        )

        server_seq += len(get_all_response)
        current_time += random.uniform(10.0, 30.0)

        # === GetAttributeSingle queries for extended attributes ===
        # Cyber Vision queries specific attributes for deeper fingerprinting

        extended_attributes = [
            (9, "configuration_consistency_value"),
            (10, "heartbeat_interval"),
            (19, "protection_mode"),
            (20, "maximum_cip_connections"),
        ]

        for attr_id, attr_name in extended_attributes:
            sender_context = bytes([random.randint(0, 255) for _ in range(8)])

            get_single_request = build_cip_unconnected_send_request(
                service=CIP_SERVICE_GET_ATTRIBUTE_SINGLE,
                class_id=CIP_CLASS_IDENTITY,
                instance_id=1,
                attribute_id=attr_id,
                session_handle=session_handle,
                sender_context=sender_context,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=build_enip_packet_fingerprinted(
                    flow.source,
                    flow.destination,
                    get_single_request,
                    seq=client_seq,
                    ack=server_seq,
                    flags="PA",
                ),
                direction="request",
                metadata={
                    "type": "cip_get_attribute_single_request",
                    "class": CIP_CLASS_IDENTITY,
                    "instance": 1,
                    "attribute": attr_id,
                    "attribute_name": attr_name,
                },
            )

            # Response timing
            timing_sample = applicator.get_response_delay()
            current_time += timing_sample.delay_ms

            # Build GetAttributeSingle response
            cip_response = build_cip_get_attribute_single_response(
                applicator,
                CIP_CLASS_IDENTITY,
                1,
                attr_id,
            )
            get_single_response = build_cip_unconnected_send_response(
                cip_response,
                session_handle,
                sender_context,
            )

            client_seq += len(get_single_request)

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=build_enip_packet_fingerprinted(
                    flow.destination,
                    flow.source,
                    get_single_response,
                    seq=server_seq,
                    ack=client_seq,
                    flags="PA",
                ),
                direction="response",
                metadata={
                    "type": "cip_get_attribute_single_response",
                    "class": CIP_CLASS_IDENTITY,
                    "instance": 1,
                    "attribute": attr_id,
                    "attribute_name": attr_name,
                },
            )

            server_seq += len(get_single_response)
            current_time += random.uniform(5.0, 15.0)

        # === ListServices to discover capabilities ===
        sender_context = bytes([random.randint(0, 255) for _ in range(8)])

        # Build ListServices request (simple encapsulation header only)
        from app.protocol_engines.ethernet_ip.packets import (
            ENIP_CMD_LIST_SERVICES,
            build_encapsulation_header,
        )
        list_services_request = build_encapsulation_header(
            command=ENIP_CMD_LIST_SERVICES,
            length=0,
            session_handle=0,
            sender_context=sender_context,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=build_enip_packet_fingerprinted(
                flow.source,
                flow.destination,
                list_services_request,
                seq=client_seq,
                ack=server_seq,
                flags="PA",
            ),
            direction="request",
            metadata={"type": "enip_list_services_request"},
        )

        # Response timing
        timing_sample = applicator.get_response_delay()
        current_time += timing_sample.delay_ms

        # Build ListServices response
        list_services_response_payload = build_list_services_response(
            applicator,
            sender_context,
        )

        client_seq += len(list_services_request)

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=build_enip_packet_fingerprinted(
                flow.destination,
                flow.source,
                list_services_response_payload,
                seq=server_seq,
                ack=client_seq,
                flags="PA",
            ),
            direction="response",
            metadata={"type": "enip_list_services_response"},
        )

        # Update state
        state.tcp_seq_client = client_seq + len(list_services_request)
        state.tcp_seq_server = server_seq + len(list_services_response_payload)

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate TCP FIN handshake for connection termination."""
        # Get TCP sequence numbers
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

        state.state_name = "unconnected"

    def validate_config(self, config: dict) -> list[str]:
        """Validate EtherNet/IP configuration."""
        errors = []

        # Check I/O data size if specified
        io_data_size = config.get("io_data_size")
        if io_data_size is not None:
            if not isinstance(io_data_size, int) or io_data_size < 1 or io_data_size > 500:
                errors.append("io_data_size must be between 1 and 500 bytes")

        # Check use_forward_open flag
        use_forward_open = config.get("use_forward_open")
        if use_forward_open is not None and not isinstance(use_forward_open, bool):
            errors.append("use_forward_open must be a boolean")

        return errors
