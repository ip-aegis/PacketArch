# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for the EMP (Edge Message Protocol / ITC-PTC) engine.

Byte-accuracy of the EMP v4 envelope is anchored to the public reference
implementation (``dustinfast/PTC-Sim`` ``lib_messaging.py``, MIT) and verified
here by independent round-trip decode. Application payloads are synthetic and
labelled as such in the ground-truth field map.
"""

import struct
from binascii import crc32

import pytest
from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.emp.class_d import (
    CLASS_D_DATA,
    CLASS_D_HEADER_LEN,
    CLASS_D_KEEPALIVE,
    CLASS_D_OVERHEAD,
    build_ack,
    build_class_d,
    build_keepalive,
    build_nak,
    next_commid,
    parse_class_d,
)
from app.protocol_engines.emp.engine import EmpEngine
from app.protocol_engines.emp.packets import (
    EMP_DEFAULT_PORT,
    EMP_MSG_ACK,
    EMP_MSG_REGISTRATION,
    EMP_MSG_WDC_CONTROL,
    EMP_MSG_WIU_STATUS,
    build_emp_message,
    emp_address,
    emp_field_map,
)
from app.protocol_engines.protocols import (
    get_default_port,
    get_identity_key_for_protocol,
    resolve_protocol,
)
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType


def _signed_crc32(data: bytes) -> int:
    v = crc32(data) & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def _decode_emp(raw: bytes) -> dict:
    """Independent EMP v4 decoder (mirrors PTC-Sim ``Message._to_tuple``)."""
    assert len(raw) >= 20
    assert struct.unpack(">i", raw[-4:])[0] == _signed_crc32(raw[:-4]), "CRC"
    assert raw[0] == 4
    msg_type = struct.unpack(">H", raw[1:3])[0]
    body_size = struct.unpack(">I", b"\x00" + raw[5:8])[0]
    vhs = raw[8]
    ttl = struct.unpack(">H", raw[9:11])[0]
    vhead = raw[13:13 + vhs].split(b"\x00")
    payload = raw[13 + vhs:-4]
    return {
        "msg_type": msg_type, "body_size": body_size, "ttl": ttl,
        "src": vhead[0].decode(), "dst": vhead[1].decode(), "payload": payload,
    }


def _dev(did, mac, ip, port, name):
    return DeviceContext(device_id=did, mac_address=mac, ip_address=ip, port=port, device_name=name)


def _flow(config=None):
    return FlowContext(
        flow_id="f-emp",
        source=_dev("wiu-007", "02:00:00:00:00:07", "10.20.0.7", 51000, "Wayside_IU_07"),
        destination=_dev("bos-01", "02:00:00:00:00:01", "10.20.0.1", EMP_DEFAULT_PORT, "Back_Office_Server_01"),
        protocol=ProtocolType.EMP,
        config=config or {},
        timing_model={},
    )


class TestEmpEnvelope:
    def test_round_trip_byte_accurate(self):
        payload = bytes.fromhex("0204050000")
        raw = build_emp_message(EMP_MSG_WDC_CONTROL, "aar.b.bos01", "aar.w.wiu007", payload)
        dec = _decode_emp(raw)
        assert dec["msg_type"] == EMP_MSG_WDC_CONTROL
        assert dec["src"] == "aar.b.bos01"
        assert dec["dst"] == "aar.w.wiu007"
        assert dec["payload"] == payload
        assert dec["body_size"] == 4 + len(payload)
        assert dec["ttl"] == 120

    def test_known_offsets(self):
        raw = build_emp_message(7124, "arr.b:locop", "arr.l.arr.IDNM", b"\x00")
        assert raw[0] == 4                                   # version
        assert struct.unpack(">H", raw[1:3])[0] == 7124      # msg_type
        assert raw[3] == 1                                   # msg version
        assert struct.unpack(">H", raw[9:11])[0] == 120      # TTL

    def test_crc_is_signed(self):
        raw = build_emp_message(6000, "a.b.c", "d.e.f", b"payload")
        # trailing 4 bytes decode as a *signed* int equal to signed crc of prefix
        assert struct.unpack(">i", raw[-4:])[0] == _signed_crc32(raw[:-4])

    def test_field_map_offsets_align(self):
        payload = b"\x01\x02\x03"
        raw = build_emp_message(EMP_MSG_WIU_STATUS, "aar.w.a", "aar.b.b", payload)
        for f in emp_field_map(EMP_MSG_WIU_STATUS, "aar.w.a", "aar.b.b", payload):
            assert 0 <= f["off"] < len(raw)
            assert f["off"] + f["len"] <= len(raw)
            assert isinstance(f["synthetic"], bool)

    def test_emp_address_sanitizes(self):
        assert emp_address("BNSF", "w", "Wayside IU-07") == "bnsf.w.waysideiu07"


class TestEmpEngine:
    def test_registered(self):
        engine = get_engine(ProtocolType.EMP)
        assert isinstance(engine, EmpEngine)
        assert engine.protocol_type == ProtocolType.EMP
        assert ProtocolType.EMP in list_supported_protocols()

    def test_validate_config(self):
        engine = EmpEngine()
        assert engine.validate_config({}) == []
        assert engine.validate_config({"wiu_id": 70000})
        assert engine.validate_config({"control_every": -1})
        assert engine.validate_config({"source_node_type": "ww"})

    def test_full_sequence_wellformed(self):
        engine = get_engine(ProtocolType.EMP)
        flow = _flow({"railroad": "bnsf", "control_every": 3})
        state = engine.create_initial_state(flow)

        events = list(engine.generate_startup_sequence(flow, state, 0.0))
        for i in range(6):
            events += list(engine.generate_poll_cycle(flow, state, 1000.0 * (i + 1)))
        events += list(engine.generate_shutdown_sequence(flow, state, 9000.0))

        emp_frames = 0
        seen = set()
        for ev in events:
            pkt = Ether(ev.packet_bytes)
            assert IP in pkt and TCP in pkt
            # well-formed: scapy rebuild (recompute checksums/lengths) is stable
            assert bytes(pkt) == bytes(Ether(bytes(pkt)))
            if ev.metadata.get("protocol") == "emp" and "emp_fields" in ev.metadata:
                emp_frames += 1
                l7 = bytes(pkt[TCP].payload)
                cd = parse_class_d(l7)          # EMP never rides bare on TCP
                assert cd["message_type"] == CLASS_D_DATA
                dec = _decode_emp(cd["body"])
                assert dec["msg_type"] == ev.metadata["emp_msg_type"]
                assert dec["src"] == ev.metadata["emp_src"]
                assert dec["dst"] == ev.metadata["emp_dst"]
                seen.add(dec["msg_type"])

        # startup: registration + ack; 6 cycles: status + response each
        assert emp_frames == 14
        assert {EMP_MSG_REGISTRATION, EMP_MSG_WIU_STATUS, EMP_MSG_ACK, EMP_MSG_WDC_CONTROL} <= seen
        # timestamps non-decreasing
        ts = [e.timestamp_ms for e in events]
        assert ts == sorted(ts)

    def test_label_offsets_point_at_real_bytes(self):
        engine = get_engine(ProtocolType.EMP)
        flow = _flow()
        state = engine.create_initial_state(flow)
        events = list(engine.generate_startup_sequence(flow, state, 0.0))
        emp_ev = next(e for e in events if e.metadata.get("emp_fields"))
        l7 = bytes(Ether(emp_ev.packet_bytes)[TCP].payload)
        by_name = {f["field"]: f for f in emp_ev.metadata["emp_fields"]}
        assert l7[by_name["emp.version"]["off"]] == 4   # offsets are Class-D-relative
        mt = by_name["emp.msg_type"]
        assert struct.unpack(">H", l7[mt["off"]:mt["off"] + mt["len"]])[0] == emp_ev.metadata["emp_msg_type"]
        # payload fields are flagged synthetic, envelope fields are not
        assert by_name["emp.version"]["synthetic"] is False
        assert any(f["synthetic"] for f in emp_ev.metadata["emp_fields"])


class TestClassD:
    """AAR S-9356 Class D — the mandatory transport under EMP."""

    def test_wraps_body_with_header_and_etx(self):
        body = b"\x04\x01\x02"
        raw = build_class_d(body, commid=7, message_type=CLASS_D_DATA)
        assert len(raw) == len(body) + CLASS_D_OVERHEAD == len(body) + 13
        assert raw[0] == 0x02 and raw[-1] == 0x03      # STX / ETX
        assert raw[1] == 0x02                           # protocol version
        assert struct.unpack(">I", raw[2:6])[0] == 7    # COMMID, big-endian
        assert raw[6] == CLASS_D_DATA
        assert raw[7] == 0x02                           # message version
        assert struct.unpack(">I", raw[8:12])[0] == len(body)
        assert raw[CLASS_D_HEADER_LEN:CLASS_D_HEADER_LEN + len(body)] == body

    def test_emp_starts_at_offset_12(self):
        body = b"\xAA" * 20
        raw = build_class_d(body, commid=1)
        assert raw[CLASS_D_HEADER_LEN] == 0xAA
        assert parse_class_d(raw)["body"] == body

    def test_round_trip(self):
        raw = build_class_d(b"payload", commid=0x01020304)
        d = parse_class_d(raw)
        assert d["commid"] == 0x01020304 and d["body"] == b"payload"
        assert d["data_length"] == 7 and d["message_type"] == CLASS_D_DATA

    def test_ack_nak_keepalive_bodies(self):
        assert parse_class_d(build_ack(2, acked_commid=9))["body"] == struct.pack(">I", 9)
        nak = parse_class_d(build_nak(3, nakd_commid=9, error_code=0x7F))
        assert nak["body"] == struct.pack(">I", 9) + b"\x7f"
        ka = parse_class_d(build_keepalive(4))
        assert ka["body"] == b"" and ka["message_type"] == CLASS_D_KEEPALIVE

    def test_commid_rolls_to_one_never_zero(self):
        assert next_commid(1) == 2
        assert next_commid(0xFFFFFFFF) == 1     # rolls to 1, not 0

    def test_parse_rejects_corruption(self):
        raw = bytearray(build_class_d(b"abc", commid=1))
        for mutate, why in ((lambda b: b.__setitem__(0, 0x99), "bad STX"),
                            (lambda b: b.__setitem__(len(b) - 1, 0x99), "bad ETX"),
                            (lambda b: b.__setitem__(11, 0x40), "length mismatch")):
            bad = bytearray(raw)
            mutate(bad)
            with pytest.raises(ValueError):
                parse_class_d(bytes(bad))


class TestEmpRegistryWiring:
    def test_default_port_and_aliases(self):
        assert get_default_port("emp") == EMP_DEFAULT_PORT == 3001
        assert resolve_protocol("itc") == "emp"
        assert resolve_protocol("ptc") == "emp"
        assert get_default_port("itc") == 3001

    def test_identity_key(self):
        assert get_identity_key_for_protocol("emp") == "emp_identity"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
