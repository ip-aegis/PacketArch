# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Syslog engine: framing per sender, one datagram per cycle."""

import re

from scapy.all import UDP, Ether

from app.protocol_engines import get_engine
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType

_RFC5424 = re.compile(rb"^<(\d{1,3})>1 \d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z (\S+) (\S+) - - - .+$")
_CISCO = re.compile(rb"^<(\d{1,3})>\d+: (\S+): [A-Z][a-z]{2} \d\d \d\d:\d\d:\d\d\.\d{3}: %[A-Z_]+-[0-7]-[A-Z_0-9]+: .+$")


def _lines(fingerprint: dict, n: int = 20) -> list[bytes]:
    dev = DeviceContext(device_id="d", mac_address="00:0a:dc:00:00:01", ip_address="10.1.2.3", port=514,
                        device_name="Main_1st_CabSW", vendor_fingerprint=fingerprint)
    nms = DeviceContext(device_id="n", mac_address="00:50:56:00:00:02", ip_address="10.1.1.5", port=514)
    flow = FlowContext(flow_id="f", source=dev, destination=nms, protocol=ProtocolType.SYSLOG,
                       config={"_epoch_anchor_s": 1792558800}, timing_model={})
    engine = get_engine(ProtocolType.SYSLOG)
    state = engine.create_initial_state(flow)
    out = []
    for i in range(n):
        (event,) = list(engine.generate_poll_cycle(flow, state, i * 60_000.0))
        pkt = Ether(event.packet_bytes)
        assert pkt[UDP].dport == 514
        out.append(bytes(pkt[UDP].payload))
    return out


def test_generic_devices_send_rfc5424():
    for line in _lines({"snmp_identity": {"sys_descr": "RuggedCom RS900 ROS v5.10.1"}}):
        m = _RFC5424.match(line)
        assert m, line
        assert int(m.group(1)) < 192 and m.group(2) == b"main-1st-cabsw"


def test_cisco_ios_devices_send_ios_format_with_rising_sequence():
    lines = _lines({"snmp_identity": {"sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE9300"}})
    seqs = []
    for line in lines:
        m = _CISCO.match(line)
        assert m, line
        assert int(m.group(1)) // 8 == 23           # facility local7
        seqs.append(int(line.split(b">")[1].split(b":")[0]))
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
