# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IEEE C37.118.2-2011 (Synchrophasor) protocol engine.

C37.118 is the wire format spoken by Phasor Measurement Units
(PMUs) and Phasor Data Concentrators (PDCs) in modern power-grid
wide-area measurement systems (WAMS).

Session model (TCP, port 4712):
1. PDC opens TCP to PMU.
2. PDC sends COMMAND(send CFG-2). PMU replies with CFG-2 frame.
3. PDC sends COMMAND(turn on TX). PMU starts streaming DATA frames
   at the configured frame rate (commonly 30 or 60 fps).
4. To stop, PDC sends COMMAND(turn off TX); TCP teardown follows.
"""

from __future__ import annotations

import math
import random
import time
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
from app.protocol_engines.synchrophasor.packets import (
    build_c37118_identity,
    build_cfg2_frame,
    build_command_frame,
    build_data_frame,
)
from app.protocol_engines.synchrophasor.types import (
    CMD_SEND_CFG_2,
    CMD_TURN_OFF_TX,
    CMD_TURN_ON_TX,
    C37118Identity,
)
from app.protocol_engines.tcp_builder import build_tcp_packet
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


def _fracsec(seconds_into: float, time_base: int) -> int:
    """Encode a sub-second offset as the lower-24-bit FRACSEC field.

    Upper 8 bits (time-quality flags) are left zero.
    """
    frac = int((seconds_into - math.floor(seconds_into)) * time_base) & 0x00FFFFFF
    return frac


@register_engine(ProtocolType.C37118)
class C37118Engine(ProtocolEngine):
    """IEEE C37.118.2-2011 synchrophasor protocol engine."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.C37118

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state."""
        identity = self._resolve_identity(flow)
        return ConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            transaction_id=0,
            sequence_number=0,
            custom_data={
                "tcp_seq_client": random.randint(1000, 9999),
                "tcp_seq_server": random.randint(1000, 9999),
                "idcode": identity.idcode,
                "data_rate": identity.data_rate,
                "config_count": identity.config_count,
                "soc_anchor": int(time.time()),
                "frame_count": 0,
                "transmission_enabled": False,
                "config_sent": False,
            },
        )

    # ------------------------------------------------------------------
    # Startup: TCP handshake -> CMD(send CFG-2) -> CFG-2 -> CMD(enable)
    # ------------------------------------------------------------------
    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        current_time = start_time_ms
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]
        identity = self._resolve_identity(flow)
        soc_anchor = int(state.custom_data["soc_anchor"])

        # === TCP three-way handshake ===
        syn = build_tcp_handshake_syn(flow.source, flow.destination, client_seq)
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn,
            direction="request",
            metadata={"type": "tcp_syn"},
        )

        current_time += random.uniform(1.0, 5.0)
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()
        syn_ack = build_tcp_handshake_syn_ack(
            flow.destination, flow.source, server_seq, client_seq + 1,
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack,
            direction="response",
            metadata={"type": "tcp_syn_ack"},
        )

        current_time += random.uniform(0.1, 0.5)
        ack = build_tcp_handshake_ack(
            flow.source, flow.destination, client_seq + 1, server_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=ack,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

        client_seq += 1
        server_seq += 1

        # === PDC requests CFG-2 ===
        current_time += random.uniform(10.0, 40.0)
        cmd_cfg2 = build_command_frame(
            idcode=identity.idcode,
            cmd=CMD_SEND_CFG_2,
            soc=soc_anchor,
            fracsec=_fracsec(current_time / 1000.0, identity.time_base),
        )
        cmd_pkt = build_tcp_packet(
            flow.source, flow.destination, cmd_cfg2,
            seq=client_seq, ack=server_seq, flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=cmd_pkt,
            direction="request",
            metadata={"type": "c37118_cmd_send_cfg2", "cmd": CMD_SEND_CFG_2},
        )
        client_seq += len(cmd_cfg2)

        # === PMU responds with CFG-2 ===
        current_time += random.uniform(5.0, 25.0)
        cfg2_body = build_cfg2_frame(
            identity,
            soc=soc_anchor,
            fracsec=_fracsec(current_time / 1000.0, identity.time_base),
        )
        cfg2_pkt = build_tcp_packet(
            flow.destination, flow.source, cfg2_body,
            seq=server_seq, ack=client_seq, flags="PA",
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=cfg2_pkt,
            direction="response",
            metadata={
                "type": "c37118_cfg2",
                "idcode": identity.idcode,
                "data_rate": identity.data_rate,
                "num_phasors": identity.num_phasors,
            },
        )
        server_seq += len(cfg2_body)
        state.custom_data["config_sent"] = True

        # === PDC enables data transmission ===
        current_time += random.uniform(5.0, 20.0)
        cmd_on = build_command_frame(
            idcode=identity.idcode,
            cmd=CMD_TURN_ON_TX,
            soc=soc_anchor,
            fracsec=_fracsec(current_time / 1000.0, identity.time_base),
        )
        cmd_on_pkt = build_tcp_packet(
            flow.source, flow.destination, cmd_on,
            seq=client_seq, ack=server_seq, flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=cmd_on_pkt,
            direction="request",
            metadata={"type": "c37118_cmd_enable_tx", "cmd": CMD_TURN_ON_TX},
        )
        client_seq += len(cmd_on)

        state.custom_data["tcp_seq_client"] = client_seq
        state.custom_data["tcp_seq_server"] = server_seq
        state.custom_data["transmission_enabled"] = True
        state.state_name = "streaming"

    # ------------------------------------------------------------------
    # Poll cycle: one (or more) DATA frame(s)
    # ------------------------------------------------------------------
    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]
        identity = self._resolve_identity(flow)
        soc_anchor = int(state.custom_data["soc_anchor"])
        frame_count = int(state.custom_data["frame_count"])

        # Bursts: at high frame rates, callers may want N data frames
        # per scheduler tick. Default is 1 — the scheduler is expected
        # to fire at the PMU's data rate.
        burst = max(1, int(flow.config.get("frames_per_cycle", 1)))

        # Per-frame inter-arrival = 1/data_rate seconds.
        frame_period_ms = 1000.0 / max(1, identity.data_rate)
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()

        for i in range(burst):
            ts_ms = cycle_time_ms + i * frame_period_ms
            ts_s = ts_ms / 1000.0
            soc = soc_anchor + int(ts_s // 1)

            # Synthesize one measurement sample. We render a slowly
            # rotating phasor and a near-nominal frequency to keep the
            # PCAP visually realistic without claiming any specific
            # power-system topology.
            angle = (frame_count + i) * (2.0 * math.pi / max(1, identity.data_rate))
            phasor_re = int(7000 * math.cos(angle))
            phasor_im = int(7000 * math.sin(angle))
            phasors = [(phasor_re, phasor_im)] * identity.num_phasors

            # FREQ is deviation from FNOM in millihertz, int16.
            freq = random.randint(-50, 50)
            # DFREQ is ROCOF in 0.01 Hz/s, int16.
            dfreq = random.randint(-5, 5)

            analogs = [random.randint(-32000, 32000) for _ in range(identity.num_analog)]
            digitals = [0x0000 for _ in range(identity.num_digital)]

            data_body = build_data_frame(
                identity,
                soc=soc,
                fracsec=_fracsec(ts_s, identity.time_base),
                phasors=phasors,
                freq=freq,
                dfreq=dfreq,
                analogs=analogs,
                digitals=digitals,
                stat=0x0000,
            )
            data_pkt = build_tcp_packet(
                flow.destination, flow.source, data_body,
                seq=server_seq, ack=client_seq, flags="PA",
                tcp_options=server_tcp_opts,
            )
            yield PacketEvent(
                timestamp_ms=ts_ms,
                flow_id=flow.flow_id,
                packet_bytes=data_pkt,
                direction="response",
                metadata={
                    "type": "c37118_data",
                    "idcode": identity.idcode,
                    "frame_number": frame_count + i + 1,
                },
            )
            server_seq += len(data_body)

        frame_count += burst
        state.custom_data["tcp_seq_client"] = client_seq
        state.custom_data["tcp_seq_server"] = server_seq
        state.custom_data["frame_count"] = frame_count
        state.sequence_number += burst

    # ------------------------------------------------------------------
    # Shutdown: CMD(turn off TX) -> TCP FIN handshake
    # ------------------------------------------------------------------
    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        current_time = start_time_ms
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]
        identity = self._resolve_identity(flow)
        soc_anchor = int(state.custom_data["soc_anchor"])

        # === PDC tells PMU to stop streaming ===
        cmd_off = build_command_frame(
            idcode=identity.idcode,
            cmd=CMD_TURN_OFF_TX,
            soc=soc_anchor,
            fracsec=_fracsec(current_time / 1000.0, identity.time_base),
        )
        cmd_off_pkt = build_tcp_packet(
            flow.source, flow.destination, cmd_off,
            seq=client_seq, ack=server_seq, flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=cmd_off_pkt,
            direction="request",
            metadata={"type": "c37118_cmd_disable_tx", "cmd": CMD_TURN_OFF_TX},
        )
        client_seq += len(cmd_off)
        state.custom_data["transmission_enabled"] = False

        # === TCP FIN handshake ===
        current_time += random.uniform(10.0, 30.0)
        fin = build_tcp_fin(flow.source, flow.destination, client_seq, server_seq)
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin,
            direction="request",
            metadata={"type": "tcp_fin"},
        )

        current_time += random.uniform(1.0, 5.0)
        fin_ack = build_tcp_fin_ack(
            flow.destination, flow.source, server_seq, client_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack,
            direction="response",
            metadata={"type": "tcp_fin_ack"},
        )

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

        state.state_name = "stopped"

    def validate_config(self, config: dict) -> list[str]:
        """Validate C37.118 flow configuration."""
        errors: list[str] = []

        idcode = config.get("idcode")
        if idcode is not None:
            if not isinstance(idcode, int) or idcode < 1 or idcode > 65534:
                errors.append("idcode must be 1-65534")

        data_rate = config.get("data_rate")
        if data_rate is not None:
            if not isinstance(data_rate, int) or data_rate < 1 or data_rate > 240:
                errors.append("data_rate must be 1-240 frames/sec")

        fnom = config.get("fnom")
        if fnom is not None and fnom not in (50, 60):
            errors.append("fnom must be 50 or 60 (Hz)")

        num_phasors = config.get("num_phasors")
        if num_phasors is not None:
            if not isinstance(num_phasors, int) or num_phasors < 0 or num_phasors > 256:
                errors.append("num_phasors must be 0-256")

        return errors

    # ------------------------------------------------------------------
    # Identity helpers
    # ------------------------------------------------------------------
    def _resolve_identity(self, flow: FlowContext) -> C37118Identity:
        """Resolve the PMU identity from the device fingerprint or flow config.

        Search order:
          1. flow.config["c37118_identity"]   (per-flow override)
          2. destination device's vendor_fingerprint["c37118_identity"]
          3. defaults from build_c37118_identity(None)
        """
        cfg = flow.config.get("c37118_identity") if flow.config else None
        if not cfg:
            fp = flow.destination.vendor_fingerprint or {}
            cfg = fp.get("c37118_identity")
        return build_c37118_identity(cfg)
