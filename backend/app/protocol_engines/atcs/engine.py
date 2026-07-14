# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""ATCS (Advanced Train Control System) engine — ATCS Monitor relay feed.

ATCS's native transport is 900 MHz radio, not IP (see ``codeline.py``). The
IP-observable form is the **ATCS Monitor relay**: a monitoring client TCP-
connects to a relay/receiver, the relay assigns a UDP data port, and then
streams decoded codeline frames as ASCII-hex over UDP while the client sends
periodic version-string keep-alives. This engine emits that relay traffic so a
Cyber Vision sensor can see (and be trained to classify) an ATCS monitoring
feed. The valuable labeled content is the inner codeline frame carried in each
UDP datagram (built byte-structured in ``codeline.py`` with per-field
confidence tiers).

Relay transport fidelity: the control-handshake and UDP-framing *structure*
below (TCP setup on 4802, UDP feed on 30000+, ASCII-hex frames, version keep-
alive) follows the documented ATCS Monitor networking behaviour. The exact
control-message wording is reconstructed; the observable flow shape (ports,
directions, encoding) is what a DPI classifier keys on and is modelled
faithfully.

Flow roles:
- ``flow.source``      = monitoring client (opens TCP, sends version keep-alives)
- ``flow.destination`` = ATCS relay / receiver (assigns UDP port, streams frames)

Config keys (all optional):
- ``railroad_num``     3-digit AAR railroad number for ATCS addresses (default 125)
- ``codeline_num``     3-digit codeline/territory number (default 13)
- ``udp_slot``         relay UDP data-port slot: port = 30000 + slot (default 0)
- ``client_version``   version string the monitor client advertises (default "3.5.2")
- ``control_every``    emit an office->wayside control every N cycles (default 6; 0 disables)
- ``keepalive_every``  send a client version keep-alive every N cycles (default 4)
"""

from __future__ import annotations

import random
from collections.abc import Iterator

from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines import register_engine
from app.protocol_engines.atcs.codeline import (
    ATCS_TYPE_OFFICE,
    ATCS_TYPE_WAYSIDE,
    build_atcs_address,
    build_codeline_frame,
    build_control_usrdata,
    build_indication_usrdata,
)
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.tcp_builder import (
    build_tcp_ack,
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_packet,
    build_tcp_syn,
    build_tcp_syn_ack,
)
from app.protocol_engines.types import (
    ConversationState,
    DeviceContext,
    FlowContext,
    PacketEvent,
    ProtocolType,
)

ATCS_RELAY_TCP_PORT = 4802       # ATCS Monitor relay control listener
ATCS_RELAY_UDP_BASE = 30000      # relay UDP data ports: Base=30000,N


def _build_udp_packet(
    src: DeviceContext, dst: DeviceContext, sport: int, dport: int, payload: bytes,
) -> bytes:
    """Ethernet/IP/UDP packet with explicit ports (relay uses non-default UDP ports)."""
    pkt = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address, ttl=src.get_tcp_ttl())
        / UDP(sport=sport, dport=dport)
        / Raw(load=payload)
    )
    return bytes(pkt)


@register_engine(ProtocolType.ATCS)
class AtcsEngine(ProtocolEngine):
    """ATCS Monitor relay feed engine."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.ATCS

    # -- helpers ----------------------------------------------------------

    def _addresses(self, flow: FlowContext) -> tuple[str, str]:
        """Return (wayside_addr, office_addr) 10-digit ATCS addresses for this flow."""
        rr = flow.config.get("railroad_num", 125)
        cl = flow.config.get("codeline_num", 13)
        wayside = build_atcs_address(ATCS_TYPE_WAYSIDE, rr, cl, flow.config.get("wayside_serial", 826))
        office = build_atcs_address(ATCS_TYPE_OFFICE, rr, cl, flow.config.get("office_serial", 1))
        return wayside, office

    def _udp_ports(self, flow: FlowContext, state: ConversationState) -> tuple[int, int]:
        """(relay_data_port, client_data_port)."""
        relay_port = ATCS_RELAY_UDP_BASE + flow.config.get("udp_slot", 0)
        client_port = state.custom_data["client_udp_port"]
        return relay_port, client_port

    def _codeline_udp_event(
        self, flow: FlowContext, ts: float, src, dst, sport, dport,
        frame: bytes, fields: list[dict], kind: str,
    ) -> PacketEvent:
        """Wrap a codeline frame as an ASCII-hex UDP datagram from the relay."""
        hex_payload = frame.hex().upper().encode("ascii") + b"\n"
        packet = _build_udp_packet(src, dst, sport, dport, hex_payload)
        return PacketEvent(
            timestamp_ms=ts,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="response",
            metadata={
                "type": f"atcs_{kind}",
                "protocol": "atcs",
                "encoding": "ascii_hex",
                # UDP payload = Eth(14)+IP(20)+UDP(8) = 42; hex text starts there.
                "l7_offset": 42,
                "codeline_frame_hex": frame.hex().upper(),
                # offsets are into the DECODED binary frame (2 hex chars per byte)
                "codeline_fields": fields,
            },
        )

    # -- engine contract --------------------------------------------------

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        return ConversationState(
            flow_id=flow.flow_id,
            state_name="disconnected",
            transaction_id=0,
            sequence_number=0,
            custom_data={
                "tcp_seq_client": random.randint(1000, 900000),
                "tcp_seq_server": random.randint(1000, 900000),
                "client_udp_port": random.randint(40000, 60000),
                "sseq": random.randint(0, 127),
                "rseq": random.randint(0, 127),
                "frame_counter": random.randint(0, 127),
                "signal_aspect": random.randint(0, 3),
                "cycle": 0,
            },
        )

    def generate_startup_sequence(
        self, flow: FlowContext, state: ConversationState, start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """TCP control handshake + relay subscribe / UDP-port assignment."""
        t = start_time_ms
        cd = state.custom_data
        client_seq = cd["tcp_seq_client"]
        server_seq = cd["tcp_seq_server"]
        relay_udp, client_udp = self._udp_ports(flow, state)
        version = flow.config.get("client_version", "3.5.2")

        # TCP three-way handshake to the relay control port.
        yield PacketEvent(
            timestamp_ms=t, flow_id=flow.flow_id,
            packet_bytes=build_tcp_syn(
                flow.source, flow.destination, client_seq,
                tcp_options=flow.source.fingerprint_applicator.get_tcp_options()),
            direction="request", metadata={"type": "tcp_syn", "protocol": "atcs"},
        )
        t += random.uniform(1.0, 5.0)
        yield PacketEvent(
            timestamp_ms=t, flow_id=flow.flow_id,
            packet_bytes=build_tcp_syn_ack(
                flow.destination, flow.source, server_seq, client_seq + 1,
                tcp_options=flow.destination.fingerprint_applicator.get_tcp_options()),
            direction="response", metadata={"type": "tcp_syn_ack", "protocol": "atcs"},
        )
        t += random.uniform(0.1, 0.5)
        yield PacketEvent(
            timestamp_ms=t, flow_id=flow.flow_id,
            packet_bytes=build_tcp_ack(flow.source, flow.destination, client_seq + 1, server_seq + 1),
            direction="request", metadata={"type": "tcp_ack", "protocol": "atcs"},
        )
        client_seq += 1
        server_seq += 1

        # Client subscribe (advertises its version) over the TCP control channel.
        t += random.uniform(5.0, 20.0)
        sub = f"ATCSMON {version}\n".encode("ascii")
        yield PacketEvent(
            timestamp_ms=t, flow_id=flow.flow_id,
            packet_bytes=build_tcp_packet(
                flow.source, flow.destination, payload=sub, seq=client_seq, ack=server_seq,
                flags="PA", tcp_options=flow.source.fingerprint_applicator.get_tcp_options()),
            direction="request",
            metadata={"type": "atcs_relay_subscribe", "protocol": "atcs", "version": version},
        )
        client_seq += len(sub)

        # Relay assigns the UDP data port over the control channel.
        t += random.uniform(5.0, 20.0)
        assign = f"PORT {relay_udp}\n".encode("ascii")
        yield PacketEvent(
            timestamp_ms=t, flow_id=flow.flow_id,
            packet_bytes=build_tcp_packet(
                flow.destination, flow.source, payload=assign, seq=server_seq, ack=client_seq,
                flags="PA", tcp_options=flow.destination.fingerprint_applicator.get_tcp_options()),
            direction="response",
            metadata={"type": "atcs_relay_port_assign", "protocol": "atcs",
                      "udp_data_port": relay_udp},
        )
        server_seq += len(assign)

        cd["tcp_seq_client"] = client_seq
        cd["tcp_seq_server"] = server_seq
        state.state_name = "subscribed"

    def generate_poll_cycle(
        self, flow: FlowContext, state: ConversationState, cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Relay streams a codeline indication (+ periodic control / keep-alive)."""
        cd = state.custom_data
        wayside_addr, office_addr = self._addresses(flow)
        relay_udp, client_udp = self._udp_ports(flow, state)

        # Evolve wayside state and sequence numbers (modulo-128, like the sample).
        cd["signal_aspect"] = max(0, min(3, cd["signal_aspect"] + random.choice([-1, 0, 0, 1])))
        cd["sseq"] = (cd["sseq"] + 1) & 0x7F
        cd["frame_counter"] = (cd["frame_counter"] + 1) & 0x7F

        # Wayside -> office indication, streamed by the relay.
        ind = build_indication_usrdata(
            signal_aspect=cd["signal_aspect"],
            switch_normal=random.random() > 0.15,
            occupancy=random.getrandbits(8),
        )
        frame, fields = build_codeline_frame(
            src_addr=wayside_addr, dst_addr=office_addr, usrdata=ind,
            gfi=2, group=5, sseq=cd["sseq"], rseq=cd["rseq"],
            beacon=False, vital=random.random() > 0.5, frame_counter=cd["frame_counter"],
        )
        # Accumulate time across sub-events so per-cycle timestamps stay monotonic.
        t = cycle_time_ms
        yield self._codeline_udp_event(
            flow, t, flow.destination, flow.source, relay_udp, client_udp,
            frame, fields, "codeline_indication",
        )

        cd["cycle"] += 1

        # Periodic office -> wayside control, also visible on the relay feed.
        control_every = flow.config.get("control_every", 6)
        if control_every and cd["cycle"] % control_every == 0:
            cd["rseq"] = (cd["rseq"] + 1) & 0x7F
            cd["frame_counter"] = (cd["frame_counter"] + 1) & 0x7F
            ctl = build_control_usrdata(
                command=random.choice([1, 2, 3]),
                target=random.randint(1, 64), value=random.randint(0, 3),
            )
            cframe, cfields = build_codeline_frame(
                src_addr=office_addr, dst_addr=wayside_addr, usrdata=ctl,
                gfi=2, group=5, sseq=cd["rseq"], rseq=cd["sseq"],
                beacon=False, vital=True, frame_counter=cd["frame_counter"],
            )
            t += random.uniform(20.0, 90.0)
            yield self._codeline_udp_event(
                flow, t, flow.destination, flow.source, relay_udp, client_udp,
                cframe, cfields, "codeline_control",
            )

        # Periodic client version keep-alive back to the relay.
        keepalive_every = flow.config.get("keepalive_every", 4)
        if keepalive_every and cd["cycle"] % keepalive_every == 0:
            version = flow.config.get("client_version", "3.5.2")
            ka = f"{version}\n".encode("ascii")
            t += random.uniform(1.0, 10.0)
            yield PacketEvent(
                timestamp_ms=t,
                flow_id=flow.flow_id,
                packet_bytes=_build_udp_packet(
                    flow.source, flow.destination, client_udp, relay_udp, ka),
                direction="request",
                metadata={"type": "atcs_keepalive", "protocol": "atcs", "version": version},
            )

        state.sequence_number += 1

    def generate_shutdown_sequence(
        self, flow: FlowContext, state: ConversationState, start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Tear down the TCP control channel."""
        t = start_time_ms
        cd = state.custom_data
        client_seq = cd["tcp_seq_client"]
        server_seq = cd["tcp_seq_server"]

        yield PacketEvent(
            timestamp_ms=t, flow_id=flow.flow_id,
            packet_bytes=build_tcp_fin(flow.source, flow.destination, client_seq, server_seq),
            direction="request", metadata={"type": "tcp_fin", "protocol": "atcs"},
        )
        t += random.uniform(1.0, 5.0)
        yield PacketEvent(
            timestamp_ms=t, flow_id=flow.flow_id,
            packet_bytes=build_tcp_fin_ack(flow.destination, flow.source, server_seq, client_seq + 1),
            direction="response", metadata={"type": "tcp_fin_ack", "protocol": "atcs"},
        )
        t += random.uniform(0.1, 0.5)
        yield PacketEvent(
            timestamp_ms=t, flow_id=flow.flow_id,
            packet_bytes=build_tcp_ack(flow.source, flow.destination, client_seq + 1, server_seq + 1),
            direction="request", metadata={"type": "tcp_ack", "protocol": "atcs"},
        )
        state.state_name = "disconnected"

    def validate_config(self, config: dict) -> list[str]:
        errors: list[str] = []
        for key in ("railroad_num", "codeline_num", "wayside_serial", "office_serial"):
            val = config.get(key)
            if val is not None and (not isinstance(val, int) or not 0 <= val <= 999):
                errors.append(f"{key} must be an integer 0-999 (3 ATCS address digits)")
        slot = config.get("udp_slot")
        if slot is not None and (not isinstance(slot, int) or not 0 <= slot <= 59):
            errors.append("udp_slot must be an integer 0-59 (relay Base=30000,60)")
        for key in ("control_every", "keepalive_every"):
            val = config.get(key)
            if val is not None and (not isinstance(val, int) or val < 0):
                errors.append(f"{key} must be a non-negative integer")
        return errors
