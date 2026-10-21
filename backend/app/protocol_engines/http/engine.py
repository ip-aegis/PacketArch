# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""HTTP engine (RFC 9110/9112): an operator or engineering host loading a
device's web interface over port 80.

The device's behaviour comes from its fingerprint (``http_profile``):
``redirect_https`` answers 301 to https:// (e.g. RUGGEDCOM ROS, whose
port-80 server redirects to 443); otherwise the device serves its page.
No Server header is sent: products do not publish theirs consistently,
and an invented one would mislead identification.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import replace

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.cloud_service.packets import (
    build_tcp_ack,
    build_tcp_fin,
    build_tcp_syn,
    build_tcp_syn_ack,
)
from app.protocol_engines.tcp_builder import build_tcp_packet
from app.protocol_engines.types import ConversationState, FlowContext, PacketEvent, ProtocolType

HTTP_PORT = 80
# A current desktop Chrome on Windows (the operator's browser).
_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _http_profile(fingerprint: dict) -> str:
    quirks = (fingerprint.get("protocol_quirks") or {}).get("http") or {}
    return fingerprint.get("http_profile") or quirks.get("profile") or "page"


def _request(host: str, path: str) -> bytes:
    return (f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {_USER_AGENT}\r\n"
            "Accept: text/html,application/xhtml+xml,*/*;q=0.8\r\nAccept-Language: en-US,en;q=0.9\r\n"
            "Connection: close\r\n\r\n").encode()


def _response(profile: str, host: str, title: str) -> bytes:
    if profile == "redirect_https":
        return (f"HTTP/1.1 301 Moved Permanently\r\nLocation: https://{host}/\r\n"
                "Content-Length: 0\r\nConnection: close\r\n\r\n").encode()
    body = (f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>{title}</title></head>"
            "<body><form method=\"post\" action=\"/login\"><input name=\"user\">"
            "<input name=\"password\" type=\"password\"></form></body></html>").encode()
    return (f"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n").encode() + body


@register_engine(ProtocolType.HTTP)
class HttpEngine(ProtocolEngine):
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.HTTP

    def validate_config(self, config: dict) -> list[str]:
        return []

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        return ConversationState(flow_id=flow.flow_id, state_name="idle",
                                 custom_data={"src_port": random.randint(49152, 65535)})

    def generate_startup_sequence(self, flow, state, start_time_ms) -> Iterator[PacketEvent]:
        return iter([])

    def generate_shutdown_sequence(self, flow, state, start_time_ms) -> Iterator[PacketEvent]:
        return iter([])

    def generate_poll_cycle(self, flow: FlowContext, state: ConversationState,
                            cycle_time_ms: float) -> Iterator[PacketEvent]:
        """One page load: connect, GET /, response, close (Connection: close)."""
        client = replace(flow.source, port=state.custom_data["src_port"])
        server = flow.destination
        fp = server.vendor_fingerprint or {}
        host = server.ip_address
        cs, ss = random.randint(1, 2**32 - 1), random.randint(1, 2**32 - 1)
        t = cycle_time_ms

        def ev(pkt: bytes, from_client: bool) -> PacketEvent:
            return PacketEvent(timestamp_ms=t, flow_id=flow.flow_id, packet_bytes=pkt,
                               direction="request" if from_client else "response",
                               metadata={"type": "http", "protocol": "http"})

        yield ev(build_tcp_syn(client, server, cs), True)
        t += random.uniform(0.3, 3.0)
        yield ev(build_tcp_syn_ack(server, client, ss, cs + 1), False)
        cs, ss = cs + 1, ss + 1
        t += random.uniform(0.1, 1.0)
        yield ev(build_tcp_ack(client, server, cs, ss), True)

        req = _request(host, "/")
        t += random.uniform(1.0, 5.0)
        yield ev(build_tcp_packet(client, server, req, cs, ss, "PA",
                                  client.fingerprint_applicator.get_tcp_options()), True)
        cs += len(req)
        resp = _response(_http_profile(fp), host, fp.get("model_name") or fp.get("model") or "Login")
        t += random.uniform(2.0, 40.0)
        yield ev(build_tcp_packet(server, client, resp, ss, cs, "PA",
                                  server.fingerprint_applicator.get_tcp_options()), False)
        ss += len(resp)
        # Server closes (Connection: close), client acknowledges and closes.
        t += random.uniform(0.2, 2.0)
        yield ev(build_tcp_fin(server, client, ss, cs), False)
        t += random.uniform(0.2, 2.0)
        yield ev(build_tcp_fin(client, server, cs, ss + 1), True)
        t += random.uniform(0.2, 2.0)
        yield ev(build_tcp_ack(server, client, ss + 1, cs + 1), False)
        state.custom_data["src_port"] = random.randint(49152, 65535)
