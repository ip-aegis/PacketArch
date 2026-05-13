# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cloud service protocol engine for TLS heartbeat traffic.

Generates TCP SYN + TLS Client Hello heartbeat packets that simulate
cloud service connectivity (EWON Talk2M, TeamViewer, AWS IoT, etc.).

Each poll cycle generates a 2-packet heartbeat: SYN + Client Hello.
"""

import random
from collections.abc import Iterator

from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.cloud_service.packets import (
    build_tcp_fin,
    build_tcp_syn,
    build_tls_client_hello,
)
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
    flows. The packet shape is identical (TCP SYN + TLS Client Hello);
    Cyber Vision identifies the protocol from the destination port that
    `traffic_generator/tasks.py` populates from `PROTOCOL_DEFAULT_PORTS`.
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.CLOUD_SERVICE

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        return CloudServiceConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            src_port=random.randint(49152, 65535),
            seq_num=random.randint(1, 4294967295),
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
        # Cloud services don't need a persistent startup — each poll is independent
        return iter([])

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate a TLS heartbeat: TCP SYN + TLS Client Hello.

        Each poll cycle simulates a new connection attempt to the cloud service.
        """
        if not isinstance(state, CloudServiceConversationState):
            return

        src = flow.source
        dst = flow.destination

        # Use gateway MAC for cloud destinations (routed traffic)
        dst_mac = dst.mac_address if dst.mac_address else "ff:ff:ff:ff:ff:ff"

        # Packet 1: TCP SYN
        syn_bytes = build_tcp_syn(
            src_mac=src.mac_address,
            dst_mac=dst_mac,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.src_port,
            dst_port=dst.port,
            seq_num=state.seq_num,
        )
        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=syn_bytes,
            direction="request",
        )

        # Packet 2: TLS Client Hello (50ms after SYN)
        if state.tls_enabled and state.hostname:
            hello_bytes = build_tls_client_hello(
                src_mac=src.mac_address,
                dst_mac=dst_mac,
                src_ip=src.ip_address,
                dst_ip=dst.ip_address,
                src_port=state.src_port,
                dst_port=dst.port,
                seq_num=state.seq_num,
                hostname=state.hostname,
                tls_profile=state.tls_profile,
            )
            yield PacketEvent(
                timestamp_ms=cycle_time_ms + 50.0,
                flow_id=flow.flow_id,
                packet_bytes=hello_bytes,
                direction="request",
            )

        # Advance TCP state for next heartbeat
        state.seq_num = (state.seq_num + 100) % 4294967296
        # Rotate source port periodically
        state.src_port = random.randint(49152, 65535)

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate TCP FIN for clean shutdown."""
        if not isinstance(state, CloudServiceConversationState):
            return

        src = flow.source
        dst = flow.destination
        dst_mac = dst.mac_address if dst.mac_address else "ff:ff:ff:ff:ff:ff"

        fin_bytes = build_tcp_fin(
            src_mac=src.mac_address,
            dst_mac=dst_mac,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.src_port,
            dst_port=dst.port,
            seq_num=state.seq_num,
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=fin_bytes,
            direction="request",
        )

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        if not config.get("hostname"):
            errors.append("Cloud service requires 'hostname' for TLS SNI")
        return errors
