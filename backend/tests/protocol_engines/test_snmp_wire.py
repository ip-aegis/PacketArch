# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Wire-level SNMP correctness: BER tags, request/response pairing, run clock."""
from unittest.mock import MagicMock

from scapy.layers.inet import UDP
from scapy.layers.l2 import Ether
from scapy.layers.snmp import SNMP

from app.protocol_engines.snmp.engine import SnmpEngine
from app.protocol_engines.snmp.oids import SystemOIDs
from app.protocol_engines.snmp.packets import _value_to_asn1
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType
from scapy.asn1.asn1 import ASN1_Codecs

BER = ASN1_Codecs.BER


def _ber(value, value_type) -> bytes:
    return _value_to_asn1(value, value_type).enc(BER)


def test_application_types_use_smi_tags():
    """Counter32/Gauge32/TimeTicks carry [APPLICATION n] tags, not INTEGER."""
    assert _ber(5, "counter")[0] == 0x41
    assert _ber(5, "gauge")[0] == 0x42
    assert _ber(5, "timeticks")[0] == 0x43
    assert _ber(5, "integer")[0] == 0x02


def test_octets_value_type_is_binary_octet_string():
    raw = bytes([3, 0, 1, 0xAB, 0xCD])
    enc = _ber(raw, "octets")
    assert enc[0] == 0x04 and enc[2:] == raw


def _flow(device_id="tc-1", anchor=1_700_000_000.0, flow_id="f1", src_ip="10.0.0.10"):
    app = MagicMock()
    app.should_timeout.return_value = False
    app.get_sys_descr.return_value = "Generic"
    app.get_sys_object_id.return_value = "1.3.6.1.4.1.9.1.1"
    src = DeviceContext(device_id="mgr", mac_address="02:00:00:00:00:01", ip_address=src_ip, port=0)
    dst = DeviceContext(
        device_id=device_id, mac_address="02:00:00:00:00:02", ip_address="10.0.0.20",
        port=161, scenario_id="scn-1",
    )
    dst._fingerprint_applicator = app
    return FlowContext(
        flow_id=flow_id, source=src, destination=dst, protocol=ProtocolType.SNMP,
        config={"_epoch_anchor_s": anchor}, timing_model={},
    )


def test_startup_responses_pair_with_request_port():
    engine = SnmpEngine()
    flow = _flow()
    events = list(engine.generate_startup_sequence(flow, engine.create_initial_state(flow), 0.0))
    reqs = [Ether(e.packet_bytes) for e in events if e.direction == "request"]
    resps = [Ether(e.packet_bytes) for e in events if e.direction == "response"]
    assert reqs and len(reqs) == len(resps)
    for rq, rs in zip(reqs, resps):
        assert rs[UDP].dport == rq[UDP].sport
        assert rs[UDP].sport == 161


def _uptime(engine, flow, t_ms):
    state = engine.create_initial_state(flow)
    return engine._generate_snmp_values(flow, state, SystemOIDs.SYS_UPTIME.oid, t_ms).value


def test_uptime_follows_virtual_clock_not_wall_clock():
    engine = SnmpEngine()
    flow = _flow()
    t0 = _uptime(engine, flow, 0.0)
    t1 = _uptime(engine, flow, 3_600_000.0)  # one virtual hour later
    assert t1 - t0 == 360_000  # TimeTicks are 1/100 s
    assert t0 >= 7200 * 100  # devices were already up before monitoring started


def test_uptime_is_identical_for_every_poller_of_a_device():
    engine = SnmpEngine()
    a = _flow(flow_id="atms", src_ip="10.0.0.10")
    b = _flow(flow_id="historian", src_ip="10.0.0.11")
    assert _uptime(engine, a, 42_000.0) == _uptime(engine, b, 42_000.0)
    assert _uptime(engine, a, 0.0) != _uptime(engine, _flow(device_id="tc-2"), 0.0)


def test_uptime_on_wire_is_timeticks():
    engine = SnmpEngine()
    flow = _flow()
    flow.config["poll_oids"] = [SystemOIDs.SYS_UPTIME.oid]
    events = list(engine.generate_poll_cycle(flow, engine.create_initial_state(flow), 1000.0))
    resp = next(e for e in events if e.direction == "response")
    raw = bytes(Ether(resp.packet_bytes)[SNMP])
    oid_ber = bytes.fromhex("06082b06010201010300")  # 1.3.6.1.2.1.1.3.0
    assert raw[raw.index(oid_ber) + len(oid_ber)] == 0x43
