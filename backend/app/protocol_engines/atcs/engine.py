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
- ``railroad_num``     3-digit AAR railroad number for ATCS addresses (default 125 = CSX)
- ``codeline_num``     3-digit codeline number (default: derived per-relay from the
                       destination device identity, so distinct relays differ)
- ``office_serial``    office address serial (default: derived from the source device)
- ``wayside_count``    distinct wayside MCPs this relay reports, rotated per cycle (default 6)
- ``udp_slot``         relay UDP data-port slot: port = 30000 + slot (default 0)
- ``client_version``   version string the monitor client advertises (default "3.5.2")
- ``control_every``    emit an office->wayside control every N cycles (default 6; 0 disables)
- ``keepalive_every``  send a client version keep-alive every N cycles (default 4)
"""

from __future__ import annotations

import random
import zlib
from collections.abc import Iterator

from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines import register_engine
from app.protocol_engines.atcs.codeline import (
    ATCS_EXT7_CONTROL,
    ATCS_EXT7_INDICATION,
    ATCS_GFI_DEFAULT,
    ATCS_GROUP_CONTROL,
    ATCS_GROUP_INDICATION,
    ATCS_TYPE_OFFICE,
    ATCS_TYPE_WAYSIDE_7,
    build_atcs_address_7series,
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

    @staticmethod
    def _stable_num(text: str, lo: int, hi: int) -> int:
        """Deterministic value in [lo, hi] from a string (stable across runs)."""
        return lo + (zlib.crc32(text.encode()) % (hi - lo + 1))

    def _territory(self, flow: FlowContext) -> tuple[int, int, int]:
        """(railroad_num, codeline_num, office_serial) for this relay flow.

        A territory is one railroad (default 125 = CSX's ATCS ID). The codeline
        is derived from the RELAY (flow.destination) device identity so distinct
        base-station relays cover distinct codelines, and the office serial from
        the subscribing office (flow.source) — both config-overridable. Without
        this, an empty flow config made every relay report the same single MCP.
        """
        cfg = flow.config
        rr = cfg.get("railroad_num", 125)
        relay_key = str(flow.destination.device_id or flow.destination.device_name or "relay")
        cl = cfg.get("codeline_num") or self._stable_num(relay_key, 1, 999)
        office_key = str(flow.source.device_id or flow.source.device_name or "office")
        office_serial = cfg.get("office_serial") or self._stable_num(office_key, 1, 998)
        return rr, cl, office_serial

    def _addresses(self, flow: FlowContext, serial: int) -> tuple[str, str, str]:
        """Return (wayside_indication_addr, wayside_control_addr, office_addr).

        7-series ATCS addresses (T-RRR-CCC-AAA-XXXX). The wayside MCP carries two
        extensions per the RF Codeline Protocol Reference: 0202 for field
        indications (what it transmits) and 0101 for command & control (what the
        office targets). The office/BCP is modelled as a type-2 7-series address.
        ``serial`` selects which wayside on this relay's codeline (the poll cycle
        rotates through a pool so the feed carries many distinct MCPs).
        """
        rr, cl, office_serial = self._territory(flow)
        wayside_ind = build_atcs_address_7series(rr, cl, serial, ATCS_EXT7_INDICATION, ATCS_TYPE_WAYSIDE_7)
        wayside_ctl = build_atcs_address_7series(rr, cl, serial, ATCS_EXT7_CONTROL, ATCS_TYPE_WAYSIDE_7)
        office = build_atcs_address_7series(rr, cl, office_serial, 0, ATCS_TYPE_OFFICE)
        return wayside_ind, wayside_ctl, office

    def _udp_ports(self, flow: FlowContext, state: ConversationState) -> tuple[int, int]:
        """(relay_data_port, client_data_port)."""
        relay_port = ATCS_RELAY_UDP_BASE + flow.config.get("udp_slot", 0)
        client_port = state.custom_data["client_udp_port"]
        return relay_port, client_port

    def _codeline_udp_event(
        self, flow: FlowContext, ts: float, src, dst, sport, dport,
        frame: bytes, fields: list[dict], kind: str,
    ) -> PacketEvent:
        """Wrap a codeline frame as an ATCS-Monitor-feed UDP datagram from the relay.

        The feed carries the codeline as RAW BINARY, one frame per datagram. The
        frame already begins with its RF address-type octet (0x23 for a ground
        datagram, which ATCSMon renders with a leading ``#`` in its ASCII gutter),
        so nothing is prepended here — verified against a real ATCS Monitor
        decoder, which parses this framing directly. (An earlier reconstruction
        emitted the frame as ASCII-hex text led by a synthetic ``#``; that was the
        ATCSMon *display* rendering plus a misread of the RF address-type byte.)
        """
        payload = frame
        packet = _build_udp_packet(src, dst, sport, dport, payload)
        return PacketEvent(
            timestamp_ms=ts,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="response",
            metadata={
                "type": f"atcs_{kind}",
                "protocol": "atcs",
                "encoding": "binary",
                # Where the L7 payload (the relay frame) starts — DERIVED from the
                # built packet, not assumed (see the EMP engine's note).
                "l7_offset": len(packet) - len(payload),
                # offsets are into the binary payload: byte at l7_offset + off
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
                # The relay covers a pool of wayside MCPs (rotated per cycle so the
                # feed carries many distinct addresses, like a real territory).
                "wayside_serials": list(range(1, flow.config.get("wayside_count", 6) + 1)),
                "wayside_idx": 0,
                "sseq_by_serial": {},        # per-MCP send sequence (monotonic per MCP)
                "signal_by_serial": {},      # per-MCP signal-aspect state
                "office_sseq": random.randint(0, 127),   # office send counter (controls)
                "message_number": random.randint(0, 127),
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
        relay_udp, client_udp = self._udp_ports(flow, state)

        # Rotate through the relay's wayside pool so the feed carries many
        # distinct MCP addresses (a real territory has many waysides per relay).
        serials = cd["wayside_serials"]
        serial = serials[cd["wayside_idx"] % len(serials)]
        cd["wayside_idx"] += 1
        wayside_ind_addr, wayside_ctl_addr, office_addr = self._addresses(flow, serial)

        # Per-MCP send sequence (monotonic per wayside so ATCSMon doesn't see
        # spurious sequence errors) + per-MCP signal-aspect state.
        cd["sseq_by_serial"].setdefault(serial, random.randint(0, 127))
        cd["sseq_by_serial"][serial] = (cd["sseq_by_serial"][serial] + 1) & 0x7F
        sseq = cd["sseq_by_serial"][serial]
        cd["signal_by_serial"].setdefault(serial, random.randint(0, 3))
        cd["signal_by_serial"][serial] = max(0, min(3, cd["signal_by_serial"][serial] + random.choice([-1, 0, 0, 1])))
        cd["message_number"] = (cd["message_number"] + 1) & 0x7F

        # Wayside -> office indication, streamed by the relay.
        ind = build_indication_usrdata(
            signal_aspect=cd["signal_by_serial"][serial],
            switch_normal=random.random() > 0.15,
            occupancy=random.getrandbits(8),
        )
        frame, fields = build_codeline_frame(
            src_addr=wayside_ind_addr, dst_addr=office_addr, usrdata=ind,
            sseq=sseq, rseq=cd["office_sseq"],
            vital=random.random() > 0.5,
            gfi=ATCS_GFI_DEFAULT, group=ATCS_GROUP_INDICATION,
            message_number=cd["message_number"],
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
            cd["office_sseq"] = (cd["office_sseq"] + 1) & 0x7F
            cd["message_number"] = (cd["message_number"] + 1) & 0x7F
            ctl = build_control_usrdata(
                command=random.choice([1, 2, 3]),
                target=random.randint(1, 64), value=random.randint(0, 3),
            )
            cframe, cfields = build_codeline_frame(
                src_addr=office_addr, dst_addr=wayside_ctl_addr, usrdata=ctl,
                sseq=cd["office_sseq"], rseq=sseq,
                vital=True,
                gfi=ATCS_GFI_DEFAULT, group=ATCS_GROUP_CONTROL,
                message_number=cd["message_number"],
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
