# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""RTSP engine: control session, interleaved RTP, TCP continuity."""

import random
import struct

from scapy.all import IP, TCP, Ether

from app.protocol_engines import get_engine
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType


def _run(cycles: int = 50):
    random.seed(5)
    vms = DeviceContext(device_id="v", mac_address="00:15:5d:00:00:01", ip_address="10.1.1.5", port=50000)
    cam = DeviceContext(device_id="c", mac_address="00:40:8c:00:00:02", ip_address="10.1.2.9", port=554,
                        vendor_fingerprint={"vendor": "Axis"})
    flow = FlowContext(flow_id="f", source=vms, destination=cam, protocol=ProtocolType.RTSP,
                       config={"_epoch_anchor_s": 1792558800}, timing_model={})
    engine = get_engine(ProtocolType.RTSP)
    state = engine.create_initial_state(flow)
    events = list(engine.generate_startup_sequence(flow, state, 0.0))
    for i in range(cycles):
        events += list(engine.generate_poll_cycle(flow, state, 1000.0 * (i + 1)))
    events += list(engine.generate_shutdown_sequence(flow, state, 1000.0 * (cycles + 1)))
    return [Ether(e.packet_bytes) for e in events]


def test_control_session_follows_rfc2326():
    pkts = _run()
    text = [bytes(p[TCP].payload) for p in pkts if bytes(p[TCP].payload)[:1] not in (b"$", b"")]
    reqs = [t for t in text if not t.startswith(b"RTSP/1.0")]
    methods = [t.split(b" ", 1)[0] for t in reqs]
    assert methods[:4] == [b"OPTIONS", b"DESCRIBE", b"SETUP", b"PLAY"] and methods[-1] == b"TEARDOWN"
    assert b"GET_PARAMETER" in methods                          # keepalive within 60 s timeout
    assert reqs[0].startswith(b"OPTIONS rtsp://10.1.2.9/axis-media/media.amp RTSP/1.0\r\n")
    resps = [t for t in text if t.startswith(b"RTSP/1.0 200 OK")]
    assert len(resps) == len(reqs)
    for req, resp in zip(reqs, resps):
        cseq = [ln for ln in req.split(b"\r\n") if ln.startswith(b"CSeq:")][0]
        assert cseq in resp.split(b"\r\n")
    describe = resps[1]
    head, body = describe.split(b"\r\n\r\n", 1)
    assert int([ln for ln in head.split(b"\r\n") if ln.startswith(b"Content-Length")][0].split(b":")[1]) == len(body)
    assert b"a=rtpmap:96 H264/90000" in body
    assert b"interleaved=0-1" in resps[2] and b"Session:" in resps[2]


def test_interleaved_rtp_is_well_formed_and_sparse():
    pkts = _run()
    frames = [bytes(p[TCP].payload) for p in pkts if bytes(p[TCP].payload)[:1] == b"$"]
    rtp = [f for f in frames if f[1] == 0]
    assert any(f[1] == 1 and f[5] == 200 for f in frames)       # RTCP sender report on channel 1
    seqs = []
    for f in rtp:
        assert struct.unpack(">H", f[2:4])[0] == len(f) - 4
        assert f[4] >> 6 == 2 and f[5] & 0x7F == 96
        seqs.append(struct.unpack(">H", f[6:8])[0])
    assert all((b - a) & 0xFFFF == 1 for a, b in zip(seqs, seqs[1:]))
    assert len(rtp) <= 3 * 50                                   # capped per cycle


def test_tcp_sequence_numbers_are_continuous():
    nxt = {}
    for p in _run(20):
        key = (p[IP].src, p[TCP].sport)
        size = len(p[TCP].payload) + (1 if p[TCP].flags & 0x03 else 0)
        if key in nxt:
            assert p[TCP].seq == nxt[key]
        nxt[key] = p[TCP].seq + size
