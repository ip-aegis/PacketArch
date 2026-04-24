# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""OPC UA protocol engine implementation.

OPC UA (Open Platform Communications Unified Architecture) is a
machine-to-machine communication protocol for industrial automation.

Key features:
- TCP port 4840 (default)
- Binary or XML encoding
- Secure channel establishment
- Session management
- Read/Write/Subscribe services
"""

import random
import uuid
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.modbus.packets import (
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_handshake_ack,
    build_tcp_handshake_syn,
    build_tcp_handshake_syn_ack,
)
from app.protocol_engines.opc_ua.packets import (
    OPC_UA_PORT,
    build_acknowledge_message,
    build_create_session_request,
    build_create_session_response,
    build_hello_message,
    build_opc_ua_packet,
    build_open_secure_channel_request,
    build_open_secure_channel_response,
    build_read_request,
    build_read_response,
)
from app.protocol_engines.jitter import get_response_delay
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


@register_engine(ProtocolType.OPC_UA)
class OpcUaEngine(ProtocolEngine):
    """OPC UA protocol engine."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.OPC_UA

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state."""
        return ConversationState(
            flow_id=flow.flow_id,
            state_name="disconnected",
            transaction_id=0,
            sequence_number=1,
            custom_data={
                "tcp_seq_client": random.randint(1000, 9999),
                "tcp_seq_server": random.randint(1000, 9999),
                "channel_id": 0,
                "token_id": 0,
                "session_id": None,
                "request_id": 0,
            },
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate OPC UA connection establishment.

        Sequence:
        1. TCP handshake
        2. Hello/Acknowledge
        3. OpenSecureChannel
        4. CreateSession
        5. ActivateSession (simplified)
        """
        current_time = start_time_ms
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]

        # === TCP Three-Way Handshake ===

        # Get fingerprinted TCP options for client and server
        client_tcp_opts = flow.source.fingerprint_applicator.get_tcp_options()
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()

        # SYN
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

        # SYN-ACK
        current_time += random.uniform(1.0, 3.0)
        syn_ack_packet = build_tcp_handshake_syn_ack(
            flow.destination, flow.source, server_seq, client_seq + 1,
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"type": "tcp_syn_ack"},
        )

        # ACK
        current_time += random.uniform(0.1, 0.5)
        ack_packet = build_tcp_handshake_ack(
            flow.source, flow.destination, client_seq + 1, server_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

        client_seq += 1
        server_seq += 1

        # === OPC UA Hello ===

        current_time += random.uniform(5.0, 15.0)

        endpoint_url = flow.config.get(
            "endpoint_url",
            f"opc.tcp://{flow.destination.ip_address}:{OPC_UA_PORT}"
        )
        hello_msg = build_hello_message(endpoint_url=endpoint_url)
        hello_packet = build_opc_ua_packet(
            flow.source, flow.destination, hello_msg, seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=hello_packet,
            direction="request",
            metadata={"type": "opc_ua_hello"},
        )

        client_seq += len(hello_msg)

        # === OPC UA Acknowledge ===

        current_time += random.uniform(2.0, 8.0)

        ack_msg = build_acknowledge_message()
        ack_ua_packet = build_opc_ua_packet(
            flow.destination, flow.source, ack_msg, seq=server_seq, ack=client_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_ua_packet,
            direction="response",
            metadata={"type": "opc_ua_acknowledge"},
        )

        server_seq += len(ack_msg)

        # === OpenSecureChannel Request ===

        current_time += random.uniform(5.0, 10.0)
        state.custom_data["request_id"] = 1

        open_req = build_open_secure_channel_request(request_id=1)
        open_req_packet = build_opc_ua_packet(
            flow.source, flow.destination, open_req, seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=open_req_packet,
            direction="request",
            metadata={"type": "opc_ua_open_secure_channel_request"},
        )

        client_seq += len(open_req)

        # === OpenSecureChannel Response ===

        current_time += random.uniform(5.0, 15.0)

        channel_id = random.randint(1, 0xFFFFFFFF)
        token_id = random.randint(1, 0xFFFFFFFF)
        state.custom_data["channel_id"] = channel_id
        state.custom_data["token_id"] = token_id

        open_resp = build_open_secure_channel_response(
            security_token_id=token_id,
            channel_id=channel_id,
            request_id=1,
        )
        open_resp_packet = build_opc_ua_packet(
            flow.destination, flow.source, open_resp, seq=server_seq, ack=client_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=open_resp_packet,
            direction="response",
            metadata={
                "type": "opc_ua_open_secure_channel_response",
                "channel_id": channel_id,
                "token_id": token_id,
            },
        )

        server_seq += len(open_resp)

        # === CreateSession Request ===

        current_time += random.uniform(10.0, 20.0)
        state.custom_data["request_id"] = 2

        session_name = flow.config.get("session_name", "PacketArch-Session")
        create_session_req = build_create_session_request(
            session_name=session_name,
            request_id=2,
            channel_id=channel_id,
        )
        create_session_packet = build_opc_ua_packet(
            flow.source, flow.destination, create_session_req,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=create_session_packet,
            direction="request",
            metadata={"type": "opc_ua_create_session_request"},
        )

        client_seq += len(create_session_req)

        # === CreateSession Response ===

        current_time += random.uniform(10.0, 25.0)

        session_id = uuid.uuid4().bytes
        state.custom_data["session_id"] = session_id.hex()

        create_session_resp = build_create_session_response(
            session_id=session_id,
            request_id=2,
            channel_id=channel_id,
        )
        create_session_resp_packet = build_opc_ua_packet(
            flow.destination, flow.source, create_session_resp,
            seq=server_seq, ack=client_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=create_session_resp_packet,
            direction="response",
            metadata={
                "type": "opc_ua_create_session_response",
                "session_id": session_id.hex(),
            },
        )

        server_seq += len(create_session_resp)

        # Update state
        state.custom_data["tcp_seq_client"] = client_seq
        state.custom_data["tcp_seq_server"] = server_seq
        state.state_name = "session_active"

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate OPC UA Read request/response cycle."""
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]
        channel_id = state.custom_data["channel_id"]
        token_id = state.custom_data["token_id"]

        # Increment request ID
        state.custom_data["request_id"] += 1
        request_id = state.custom_data["request_id"]

        # Get node IDs to read from config
        node_ids = flow.config.get("node_ids", ["ns=2;i=1"])
        if isinstance(node_ids, str):
            node_ids = [node_ids]

        # === Read Request ===

        read_req = build_read_request(
            node_ids=node_ids,
            request_id=request_id,
            channel_id=channel_id,
            token_id=token_id,
        )
        read_req_packet = build_opc_ua_packet(
            flow.source, flow.destination, read_req,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=read_req_packet,
            direction="request",
            metadata={
                "type": "opc_ua_read_request",
                "request_id": request_id,
                "node_ids": node_ids,
            },
        )

        client_seq += len(read_req)

        # === Read Response ===

        response_delay = get_response_delay(flow.timing_model)
        response_time = cycle_time_ms + response_delay

        # Generate mock values based on config or random
        values = []
        value_config = flow.config.get("values", {})
        for node_id in node_ids:
            if node_id in value_config:
                val = value_config[node_id]
                if isinstance(val, bool):
                    values.append((1, val))
                elif isinstance(val, int):
                    values.append((6, val))
                elif isinstance(val, float):
                    values.append((11, val))
                else:
                    values.append((12, str(val)))
            else:
                # Random value
                values.append((11, random.uniform(0.0, 100.0)))

        read_resp = build_read_response(
            values=values,
            request_id=request_id,
            channel_id=channel_id,
            token_id=token_id,
        )
        read_resp_packet = build_opc_ua_packet(
            flow.destination, flow.source, read_resp,
            seq=server_seq, ack=client_seq
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=read_resp_packet,
            direction="response",
            metadata={
                "type": "opc_ua_read_response",
                "request_id": request_id,
                "value_count": len(values),
            },
        )

        server_seq += len(read_resp)

        # Update state
        state.custom_data["tcp_seq_client"] = client_seq
        state.custom_data["tcp_seq_server"] = server_seq
        state.sequence_number += 1

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate OPC UA disconnect sequence."""
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]

        # TCP FIN handshake
        current_time = start_time_ms

        # FIN from client
        fin_packet = build_tcp_fin(
            flow.source, flow.destination, client_seq, server_seq
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_packet,
            direction="request",
            metadata={"type": "tcp_fin"},
        )

        # FIN-ACK from server
        current_time += random.uniform(1.0, 3.0)
        fin_ack_packet = build_tcp_fin_ack(
            flow.destination, flow.source, server_seq, client_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack_packet,
            direction="response",
            metadata={"type": "tcp_fin_ack"},
        )

        # Final ACK from client
        current_time += random.uniform(0.1, 0.5)
        final_ack = build_tcp_handshake_ack(
            flow.source, flow.destination, client_seq + 1, server_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=final_ack,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

        state.state_name = "disconnected"

    def validate_config(self, config: dict) -> list[str]:
        """Validate OPC UA configuration."""
        errors = []

        # Validate endpoint URL
        endpoint_url = config.get("endpoint_url")
        if endpoint_url:
            if not endpoint_url.startswith("opc.tcp://"):
                errors.append("endpoint_url must start with 'opc.tcp://'")

        # Validate node IDs
        node_ids = config.get("node_ids")
        if node_ids:
            if isinstance(node_ids, str):
                node_ids = [node_ids]
            for node_id in node_ids:
                if not isinstance(node_id, str):
                    errors.append(f"node_id must be a string, got {type(node_id)}")
                elif not (node_id.startswith("ns=") or node_id.startswith("i=") or node_id.startswith("s=")):
                    errors.append(f"Invalid node_id format: {node_id}")

        # Validate session name
        session_name = config.get("session_name")
        if session_name:
            if not isinstance(session_name, str) or len(session_name) > 255:
                errors.append("session_name must be a string with max 255 characters")

        return errors
