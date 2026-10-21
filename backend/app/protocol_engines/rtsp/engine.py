# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""RTSP engine: a VMS / NVR (flow source) pulling a camera stream (flow
destination). Startup sets the session up over TCP 554 with interleaved
transport; each poll cycle is a short, deliberately sparse slice of the
stream (a few RTP packets) plus periodic RTCP and keepalives. A real
2-6 Mbit/s stream would swamp the virtual-time scheduler, as PROFINET
cyclic traffic once did; the sparse slice keeps the session shape and the
protocol identity on the wire without the volume."""

from __future__ import annotations

import random
import time
from collections.abc import Iterator
from dataclasses import replace

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.cloud_service.packets import build_tcp_ack, build_tcp_syn, build_tcp_syn_ack
from app.protocol_engines.rtsp import messages
from app.protocol_engines.tcp_builder import build_tcp_packet
from app.protocol_engines.types import ConversationState, FlowContext, PacketEvent, ProtocolType

RTSP_PORT = 554
_RTP_PER_CYCLE = (1, 3)
_RTP_SIZE = (900, 1400)
_RTCP_EVERY_S = 5.0
_KEEPALIVE_EVERY_S = 40.0      # inside a 60 s session timeout
_RTP_CLOCK = 90_000


@register_engine(ProtocolType.RTSP)
class RtspEngine(ProtocolEngine):
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.RTSP

    def validate_config(self, config: dict) -> list[str]:
        return []

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        return ConversationState(flow_id=flow.flow_id, state_name="idle", custom_data={
            "src_port": random.randint(49152, 65535),
            "c_seq": random.randint(1, 2**31), "s_seq": random.randint(1, 2**31),
            "cseq": 1, "session": random.randint(10**8, 10**9 - 1),
            "ssrc": random.randint(1, 2**32 - 1), "rtp_seq": random.randint(0, 0xFFFF),
            "rtp_ts0": random.randint(0, 2**32 - 1), "packets": 0, "octets": 0,
            "last_rtcp_ms": 0.0, "last_keepalive_ms": 0.0, "start_wall_s": time.time(),
        })

    # -- helpers --------------------------------------------------------

    def _endpoints(self, flow, state):
        return replace(flow.source, port=state.custom_data["src_port"]), flow.destination

    def _send(self, flow, state, from_client: bool, payload: bytes, t: float) -> PacketEvent:
        client, server = self._endpoints(flow, state)
        cd = state.custom_data
        src, dst, mine, theirs = ((client, server, "c_seq", "s_seq") if from_client
                                  else (server, client, "s_seq", "c_seq"))
        pkt = build_tcp_packet(src, dst, payload, cd[mine], cd[theirs], "PA",
                               src.fingerprint_applicator.get_tcp_options())
        cd[mine] += len(payload)
        return PacketEvent(timestamp_ms=t, flow_id=flow.flow_id, packet_bytes=pkt,
                           direction="request" if from_client else "response",
                           metadata={"type": "rtsp", "protocol": "rtsp"})

    def _url(self, flow) -> str:
        vendor = (flow.destination.vendor_fingerprint or {}).get("vendor") or flow.destination.vendor or ""
        return f"rtsp://{flow.destination.ip_address}{messages.stream_path(vendor)}"

    # -- sequences ------------------------------------------------------

    def generate_startup_sequence(self, flow, state, start_time_ms) -> Iterator[PacketEvent]:
        client, server = self._endpoints(flow, state)
        cd = state.custom_data
        t = start_time_ms
        yield PacketEvent(timestamp_ms=t, flow_id=flow.flow_id, direction="request",
                          packet_bytes=build_tcp_syn(client, server, cd["c_seq"]))
        t += random.uniform(0.3, 3.0)
        yield PacketEvent(timestamp_ms=t, flow_id=flow.flow_id, direction="response",
                          packet_bytes=build_tcp_syn_ack(server, client, cd["s_seq"], cd["c_seq"] + 1))
        cd["c_seq"] += 1
        cd["s_seq"] += 1
        t += random.uniform(0.1, 1.0)
        yield PacketEvent(timestamp_ms=t, flow_id=flow.flow_id, direction="request",
                          packet_bytes=build_tcp_ack(client, server, cd["c_seq"], cd["s_seq"]))

        url = self._url(flow)
        session = str(cd["session"])
        steps = [
            ("OPTIONS", url, {}, {"Public": "OPTIONS, DESCRIBE, SETUP, PLAY, PAUSE, TEARDOWN, GET_PARAMETER"}, b""),
            ("DESCRIBE", url, {"Accept": "application/sdp"},
             {"Content-Base": url + "/", "Content-Type": "application/sdp"},
             messages.sdp(flow.destination.ip_address, cd["session"])),
            ("SETUP", url + "/trackID=1", {"Transport": "RTP/AVP/TCP;unicast;interleaved=0-1"},
             {"Transport": f"RTP/AVP/TCP;unicast;interleaved=0-1;ssrc={cd['ssrc']:08X};mode=\"PLAY\"",
              "Session": f"{session};timeout=60"}, b""),
            ("PLAY", url + "/", {"Session": session, "Range": "npt=0.000-"},
             {"Session": session, "RTP-Info": f"url={url}/trackID=1;seq={cd['rtp_seq']};rtptime={cd['rtp_ts0']}"},
             b""),
        ]
        for method, req_url, req_h, resp_h, body in steps:
            t += random.uniform(2.0, 15.0)
            yield self._send(flow, state, True, messages.request(method, req_url, cd["cseq"], req_h), t)
            t += random.uniform(1.0, 20.0)
            yield self._send(flow, state, False, messages.response(cd["cseq"], resp_h, body), t)
            cd["cseq"] += 1
        cd["last_rtcp_ms"] = cd["last_keepalive_ms"] = t
        cd["play_ms"] = t

    def generate_poll_cycle(self, flow, state, cycle_time_ms) -> Iterator[PacketEvent]:
        cd = state.custom_data
        if "play_ms" not in cd:
            return
        t = cycle_time_ms
        rtp_ts = cd["rtp_ts0"] + int((t - cd["play_ms"]) / 1000.0 * _RTP_CLOCK)
        n = random.randint(*_RTP_PER_CYCLE)
        for i in range(n):
            size = random.randint(*_RTP_SIZE)
            packet = messages.rtp(cd["rtp_seq"], rtp_ts, cd["ssrc"], size, marker=(i == n - 1))
            cd["rtp_seq"] = (cd["rtp_seq"] + 1) & 0xFFFF
            cd["packets"] += 1
            cd["octets"] += len(packet) - 12
            yield self._send(flow, state, False, messages.interleaved(0, packet), t)
            t += random.uniform(0.2, 1.5)
        if t - cd["last_rtcp_ms"] >= _RTCP_EVERY_S * 1000:
            anchor = flow.config.get("_epoch_anchor_s") if isinstance(flow.config, dict) else None
            wall = float(anchor if anchor is not None else cd["start_wall_s"]) + t / 1000.0
            sr = messages.rtcp_sender_report(cd["ssrc"], wall, rtp_ts, cd["packets"], cd["octets"])
            yield self._send(flow, state, False, messages.interleaved(1, sr), t)
            cd["last_rtcp_ms"] = t
        if t - cd["last_keepalive_ms"] >= _KEEPALIVE_EVERY_S * 1000:
            t += random.uniform(1.0, 5.0)
            yield self._send(flow, state, True, messages.request(
                "GET_PARAMETER", self._url(flow) + "/", cd["cseq"], {"Session": str(cd["session"])}), t)
            t += random.uniform(1.0, 10.0)
            yield self._send(flow, state, False, messages.response(cd["cseq"], {"Session": str(cd["session"])}), t)
            cd["cseq"] += 1
            cd["last_keepalive_ms"] = t

    def generate_shutdown_sequence(self, flow, state, start_time_ms) -> Iterator[PacketEvent]:
        cd = state.custom_data
        if "play_ms" not in cd:
            return
        t = start_time_ms
        yield self._send(flow, state, True, messages.request(
            "TEARDOWN", self._url(flow) + "/", cd["cseq"], {"Session": str(cd["session"])}), t)
        yield self._send(flow, state, False, messages.response(cd["cseq"]), t + random.uniform(1.0, 10.0))
