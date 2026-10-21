# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""LiveOutput — one persistent L2 socket per output, never one per packet.

A per-packet ``sendp()`` costs ~12 ms of socket setup, which capped every live
scenario at ~55 pps and let the orchestrator's virtual clock fall ~18x behind
wall time. The load-bearing property is that the socket is opened once.
"""

import pytest

import scapy.arch

from app.protocol_engines.output import LiveOutput


class _FakeSocket:
    opened: list["_FakeSocket"] = []

    def __init__(self, iface: str) -> None:
        self.iface = iface
        self.sent: list[bytes] = []
        self.closed = False
        self.fail_next = False
        _FakeSocket.opened.append(self)

    def send(self, data: bytes) -> None:
        if self.fail_next:
            raise OSError("No such device")
        self.sent.append(data)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_socket(monkeypatch):
    _FakeSocket.opened = []
    monkeypatch.setattr(scapy.arch, "L2Socket", _FakeSocket)
    return _FakeSocket


def test_reuses_one_socket_across_packets(fake_socket):
    out = LiveOutput(interface="pa-gen-test")
    for i in range(5):
        out.write_packet(bytes([i]) * 60, timestamp_ms=0.0)

    assert len(fake_socket.opened) == 1
    sock = fake_socket.opened[0]
    assert sock.iface == "pa-gen-test"
    assert sock.sent == [bytes([i]) * 60 for i in range(5)]
    assert out.packet_count == 5
    assert out.bytes_sent == 300

    out.close()
    assert sock.closed


def test_send_failure_reopens_socket_on_next_packet(fake_socket):
    out = LiveOutput(interface="pa-gen-test")
    out.write_packet(b"a" * 60, timestamp_ms=0.0)
    fake_socket.opened[0].fail_next = True

    with pytest.raises(OSError):
        out.write_packet(b"b" * 60, timestamp_ms=0.0)
    assert fake_socket.opened[0].closed
    assert out.packet_count == 1

    out.write_packet(b"c" * 60, timestamp_ms=0.0)
    assert len(fake_socket.opened) == 2
    assert fake_socket.opened[1].sent == [b"c" * 60]
    assert out.packet_count == 2
