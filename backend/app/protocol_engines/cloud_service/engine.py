# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cloud service protocol engine for TLS heartbeat traffic.

Generates a complete bidirectional TCP+TLS session that simulates cloud
service connectivity (EWON Talk2M, TeamViewer, AWS IoT, etc.).

Each poll cycle is a full, self-contained mini-session: TCP three-way
handshake, TLS ClientHello/ServerHello flight, then a graceful TCP close —
not just the client's half of the conversation.
"""

import random
from collections.abc import Iterator
from dataclasses import replace

from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.cloud_service.packets import (
    build_tcp_ack,
    build_tcp_fin,
    build_tcp_syn,
    build_tcp_syn_ack,
    build_tls_client_hello_payload,
    build_tls_server_hello_payload,
)
from app.protocol_engines.tcp_builder import build_tcp_packet
from app.protocol_engines.types import (
    CloudServiceConversationState,
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)

# Import register_engine here to avoid circular imports
# (engine files are imported by __init__.py after register_engine is defined)
from app.protocol_engines import register_engine


@register_engine(ProtocolType.CLOUD_SERVICE)
@register_engine(ProtocolType.SSH)
@register_engine(ProtocolType.TELNET)
@register_engine(ProtocolType.RDP)
@register_engine(ProtocolType.HTTPS)
class CloudServiceEngine(ProtocolEngine):
    """Engine for TCP/TLS heartbeat traffic.

    Originally cloud-service heartbeats (EWON Talk2M, TeamViewer); also
    serves SSH / Telnet / RDP / HTTPS for jump-server style remote-access
    flows. The packet shape is identical (TCP + TLS-shaped heartbeat);
    Cyber Vision identifies the protocol from the destination port that
    `traffic_generator/tasks.py` populates from `PROTOCOL_DEFAULT_PORTS`.

    Every poll cycle opens and gracefully closes its own TCP connection —
    startup/shutdown are deliberately no-ops. This isn't just a realism
    choice: the live agent's `_run_cloud_heartbeats()` wall-clock thread
    (see docker/packetarch-agent/app/orchestrator_pool.py, added v1.41.0 to
    dodge virtual-time starvation from high-rate OT poll cycles) calls
    ONLY `generate_poll_cycle()` for ProtocolType.CLOUD_SERVICE — it never
    calls `generate_startup_sequence`/`generate_shutdown_sequence`. Logic
    placed there would silently never fire for live cloud_service traffic.
    Keeping every packet in `generate_poll_cycle` keeps behavior identical
    across the PCAP path (heap-scheduled) and the live path (wall-clock
    thread) for all five registered protocol types.
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.CLOUD_SERVICE

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        return CloudServiceConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            src_port=random.randint(49152, 65535),
            hostname=flow.config.get("hostname", ""),
            tls_enabled=flow.config.get("tls_enabled", True),
            tls_profile=flow.config.get("tls_profile", "embedded_minimal"),
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        # See class docstring — cloud heartbeats self-contain their whole
        # session inside generate_poll_cycle; startup never fires on the
        # live agent's wall-clock heartbeat thread.
        return iter([])

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate one complete heartbeat: a full TCP+TLS session, open to close.

        SYN -> SYN-ACK -> ACK -> ClientHello -> ServerHello flight ->
        FIN -> FIN-ACK -> ACK. Each poll cycle is an independent
        connection (fresh sequence numbers, rotated ephemeral port) —
        matching how EWON Talk2M / TeamViewer clients actually reconnect
        per heartbeat rather than holding one long-lived socket open.
        """
        if not isinstance(state, CloudServiceConversationState):
            return

        client = replace(flow.source, port=state.src_port)
        server = flow.destination

        client_seq = random.randint(1, 4_294_967_295)
        server_seq = random.randint(1, 4_294_967_295)
        t = cycle_time_ms

        # TCP three-way handshake
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_syn(client, server, client_seq),
            direction="request",
        )
        t += random.uniform(20.0, 60.0)
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_syn_ack(server, client, server_seq, client_seq + 1),
            direction="response",
        )
        t += random.uniform(1.0, 5.0)
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_ack(client, server, client_seq + 1, server_seq + 1),
            direction="request",
        )
        client_seq += 1
        server_seq += 1

        # TLS handshake
        if state.tls_enabled and state.hostname:
            client_hello_payload = build_tls_client_hello_payload(
                state.hostname, state.tls_profile,
            )
            hello_bytes = build_tcp_packet(
                client, server, client_hello_payload, client_seq, server_seq, "PA",
                client.fingerprint_applicator.get_tcp_options(),
            )
            t += random.uniform(20.0, 60.0)
            yield PacketEvent(
                timestamp_ms=t,
                flow_id=flow.flow_id,
                packet_bytes=hello_bytes,
                direction="request",
            )
            client_seq += len(client_hello_payload)

            server_hello_payload = build_tls_server_hello_payload(state.tls_profile)
            server_hello_bytes = build_tcp_packet(
                server, client, server_hello_payload, server_seq, client_seq, "PA",
                server.fingerprint_applicator.get_tcp_options(),
            )
            t += random.uniform(30.0, 100.0)
            yield PacketEvent(
                timestamp_ms=t,
                flow_id=flow.flow_id,
                packet_bytes=server_hello_bytes,
                direction="response",
            )
            server_seq += len(server_hello_payload)

            t += random.uniform(1.0, 5.0)
            yield PacketEvent(
                timestamp_ms=t,
                flow_id=flow.flow_id,
                packet_bytes=build_tcp_ack(client, server, client_seq, server_seq),
                direction="request",
            )

        # Graceful TCP close
        t += random.uniform(5.0, 20.0)
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_fin(client, server, client_seq, server_seq),
            direction="request",
        )
        t += random.uniform(1.0, 5.0)
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_fin(server, client, server_seq, client_seq + 1),
            direction="response",
        )
        t += random.uniform(1.0, 5.0)
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_ack(client, server, client_seq + 1, server_seq + 1),
            direction="request",
        )

        # Rotate source port for the next independent connection
        state.src_port = random.randint(49152, 65535)

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        # See class docstring — each heartbeat already opens and closes
        # its own connection inside generate_poll_cycle; nothing is left
        # dangling at scenario shutdown.
        return iter([])

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        if not config.get("hostname"):
            errors.append("Cloud service requires 'hostname' for TLS SNI")
        return errors
