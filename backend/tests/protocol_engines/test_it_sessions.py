# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""HTTPS / SSH / RDP / Telnet sessions carry their real opening exchange.

Before 2026-10-21 a template https/ssh/rdp/telnet flow with no
config.hostname put only a TCP handshake and teardown on the wire.
"""

from __future__ import annotations

import random
import struct

import pytest
from scapy.all import IP, TCP, Ether

from app.protocol_engines.cloud_service.engine import CloudServiceEngine
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType


def _flow(protocol: ProtocolType, config: dict | None = None) -> FlowContext:
    src = DeviceContext(device_id="ews", mac_address="00:15:5d:00:00:01", ip_address="10.1.1.10",
                        port=50000, device_name="TMC_Eng_WS")
    dst = DeviceContext(device_id="cam", mac_address="00:40:8c:00:00:02", ip_address="10.1.2.20",
                        port=443, device_name="Main_1st_CCTV")
    return FlowContext(flow_id="f", source=src, destination=dst, protocol=protocol,
                       config=config or {}, timing_model={})


def _session(protocol: ProtocolType, config: dict | None = None) -> list:
    random.seed(11)
    flow = _flow(protocol, config)
    engine = CloudServiceEngine()
    state = engine.create_initial_state(flow)
    return [Ether(e.packet_bytes) for e in engine.generate_poll_cycle(flow, state, 0.0)]


def _payloads(pkts, from_ip=None) -> list[bytes]:
    return [bytes(p[TCP].payload) for p in pkts
            if len(p[TCP].payload) and (from_ip is None or p[IP].src == from_ip)]


def _tls_records(data: bytes) -> list[tuple[int, int, bytes]]:
    out, i = [], 0
    while i < len(data):
        ctype, length = data[i], struct.unpack(">H", data[i + 3:i + 5])[0]
        out.append((ctype, length, data[i + 5:i + 5 + length]))
        i += 5 + length
    assert i == len(data), "records must tile the segment exactly"
    return out


@pytest.mark.parametrize("protocol", [ProtocolType.HTTPS, ProtocolType.SSH, ProtocolType.RDP, ProtocolType.TELNET])
def test_tcp_sequence_numbers_are_continuous(protocol):
    pkts = _session(protocol)
    nxt = {}
    for p in pkts:
        key = (p[IP].src, p[TCP].sport)
        seq, size = p[TCP].seq, len(p[TCP].payload) + (1 if p[TCP].flags & 0x03 else 0)
        if key in nxt:
            assert seq == nxt[key], (protocol, p.summary())
        nxt[key] = seq + size


def test_cloud_heartbeat_shape_is_unchanged():
    assert len(_session(ProtocolType.CLOUD_SERVICE, {"hostname": "m.talk2m.com"})) == 9
    assert len(_session(ProtocolType.CLOUD_SERVICE)) == 6


def test_https_without_hostname_runs_a_full_tls_handshake_and_carries_data():
    pkts = _session(ProtocolType.HTTPS)
    client = _payloads(pkts, "10.1.1.10")
    server = _payloads(pkts, "10.1.2.20")
    assert b"main-1st-cctv" in client[0]                   # SNI = canonical hostname
    flight = _tls_records(server[0])
    assert [r[2][0] for r in flight] == [2, 11, 12, 14]    # SH, Cert, SKE, SHD
    finish = _tls_records(client[1])
    assert [r[0] for r in finish] == [0x16, 0x14, 0x16] and finish[0][2][0] == 0x10
    appdata = [r for seg in client[2:] + server[2:] for r in _tls_records(seg)]
    assert appdata and all(ctype == 0x17 for ctype, _, _ in appdata)


def test_ssh_exchanges_identification_strings_and_kexinit():
    pkts = _session(ProtocolType.SSH)
    client = _payloads(pkts, "10.1.1.10")
    server = _payloads(pkts, "10.1.2.20")
    assert server[0].startswith(b"SSH-2.0-") and server[0].endswith(b"\r\n")
    assert client[0] == b"SSH-2.0-PuTTY_Release_0.81\r\n"
    for kexinit in (client[1], server[1]):
        length, pad = struct.unpack(">IB", kexinit[:5])
        assert length + 4 == len(kexinit) and (length + 4) % 8 == 0 and pad >= 4
        assert kexinit[5] == 20 and b"curve25519-sha256" in kexinit


def test_ssh_server_banner_comes_from_the_fingerprint_when_sourced():
    flow = _flow(ProtocolType.SSH)
    flow.destination.vendor_fingerprint = {"ssh_banner": "SSH-2.0-Cisco-1.25"}
    engine = CloudServiceEngine()
    pkts = [Ether(e.packet_bytes) for e in engine.generate_poll_cycle(flow, engine.create_initial_state(flow), 0.0)]
    assert _payloads(pkts, "10.1.2.20")[0] == b"SSH-2.0-Cisco-1.25\r\n"


def test_rdp_negotiates_then_starts_tls():
    pkts = _session(ProtocolType.RDP)
    client = _payloads(pkts, "10.1.1.10")
    server = _payloads(pkts, "10.1.2.20")
    cr = client[0]
    assert cr[:2] == b"\x03\x00" and struct.unpack(">H", cr[2:4])[0] == len(cr)
    assert cr[5] == 0xE0 and b"Cookie: mstshash=operator\r\n" in cr
    assert cr[-8:-4] == b"\x01\x00\x08\x00"                 # RDP_NEG_REQ
    assert server[0][5] == 0xD0 and server[0][-8] == 0x02    # CC + RDP_NEG_RSP
    assert client[1][0] == 0x16 and client[1][5] == 0x01   # TLS ClientHello follows


def test_telnet_opens_with_option_negotiation():
    pkts = _session(ProtocolType.TELNET)
    assert _payloads(pkts, "10.1.2.20")[0][:3] == bytes([255, 253, 24])
    assert _payloads(pkts, "10.1.1.10")[0][:3] == bytes([255, 251, 24])


@pytest.mark.parametrize("protocol", [ProtocolType.CLOUD_SERVICE, ProtocolType.HTTPS, ProtocolType.SSH,
                                      ProtocolType.RDP, ProtocolType.TELNET])
def test_registry_hands_out_the_session_engine(protocol):
    from app.protocol_engines import get_engine

    assert isinstance(get_engine(protocol), CloudServiceEngine)
