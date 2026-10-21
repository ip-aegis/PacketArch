# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""HTTP engine: one page load per cycle; redirect profile."""

from scapy.all import TCP, Ether

from app.protocol_engines import get_engine
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType


def _exchange(fingerprint: dict) -> tuple[bytes, bytes]:
    ews = DeviceContext(device_id="w", mac_address="00:15:5d:00:00:01", ip_address="10.1.1.7", port=50000)
    dev = DeviceContext(device_id="d", mac_address="00:06:77:00:00:02", ip_address="10.1.3.4", port=80,
                        vendor_fingerprint=fingerprint)
    flow = FlowContext(flow_id="f", source=ews, destination=dev, protocol=ProtocolType.HTTP, config={},
                       timing_model={})
    engine = get_engine(ProtocolType.HTTP)
    pkts = [Ether(e.packet_bytes) for e in engine.generate_poll_cycle(flow, engine.create_initial_state(flow), 0.0)]
    data = [bytes(p[TCP].payload) for p in pkts if len(p[TCP].payload)]
    assert [p[TCP].dport for p in pkts if p[TCP].flags == "S"] == [80]
    return data[0], data[1]


def test_page_load():
    req, resp = _exchange({"model_name": "SICK TIC502 Traffic Information Collector"})
    assert req.startswith(b"GET / HTTP/1.1\r\nHost: 10.1.3.4\r\n")
    head, body = resp.split(b"\r\n\r\n", 1)
    assert head.startswith(b"HTTP/1.1 200 OK") and b"Server:" not in head
    assert f"Content-Length: {len(body)}".encode() in head
    assert b"<title>SICK TIC502" in body


def test_redirect_profile():
    _req, resp = _exchange({"protocol_quirks": {"http": {"profile": "redirect_https"}}})
    assert resp.startswith(b"HTTP/1.1 301 Moved Permanently\r\nLocation: https://10.1.3.4/\r\n")
