# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Syslog engine: the flow SOURCE is the reporting device, the DESTINATION
the collector (an NMS / SIEM). One datagram per poll cycle; no response."""

from __future__ import annotations

import random
import time
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.snmp.packets import build_udp_packet
from app.protocol_engines.syslog import messages
from app.protocol_engines.types import ConversationState, FlowContext, PacketEvent, ProtocolType

SYSLOG_PORT = 514


@register_engine(ProtocolType.SYSLOG)
class SyslogEngine(ProtocolEngine):
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.SYSLOG

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        return ConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            custom_data={"seq": random.randint(1, 5000), "start_wall_s": time.time(),
                         # Devices send from a fixed source port (514 or a
                         # stable ephemeral one), not a new port per message.
                         "src_port": random.choice((SYSLOG_PORT, random.randint(49152, 65535)))},
        )

    def generate_startup_sequence(self, flow, state, start_time_ms) -> Iterator[PacketEvent]:
        return iter([])

    def generate_shutdown_sequence(self, flow, state, start_time_ms) -> Iterator[PacketEvent]:
        return iter([])

    def validate_config(self, config: dict) -> list[str]:
        return []

    def generate_poll_cycle(self, flow: FlowContext, state: ConversationState,
                            cycle_time_ms: float) -> Iterator[PacketEvent]:
        from app.protocol_engines import canonical_identity

        anchor = flow.config.get("_epoch_anchor_s") if isinstance(flow.config, dict) else None
        when = messages.utc(float(anchor if anchor is not None else state.custom_data["start_wall_s"])
                            + cycle_time_ms / 1000.0)
        device = flow.source
        hostname = canonical_identity.canonical_hostname(device.device_name or device.device_id)
        peer = flow.destination.ip_address
        if messages.is_cisco_ios(device.vendor_fingerprint or {}):
            state.custom_data["seq"] += 1
            line = messages.cisco_line(state.custom_data["seq"], hostname, when, peer)
        else:
            line = messages.rfc5424_line(hostname, when, peer)
        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=build_udp_packet(device, flow.destination, line,
                                          src_port=state.custom_data["src_port"], dst_port=SYSLOG_PORT),
            direction="request",
            metadata={"type": "syslog", "protocol": "syslog"},
        )
