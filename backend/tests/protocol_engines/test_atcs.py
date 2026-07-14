# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for the ATCS (Advanced Train Control System) engine.

ATCS is emitted as an ATCS Monitor relay feed (TCP control + UDP ASCII-hex
codeline frames). The inner codeline frame carries three-tier per-field
confidence labels: spec (HDLC framing, BCD address, CRC-16/X.25 FCS),
provisional (X.25 network-header bit-packing — AAR Spec 200 paywalled), and
synthetic (UsrData). Framing accuracy of the spec-tier parts is verified here.
"""

import struct

import pytest
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.atcs.codeline import (
    atcs_address_subfields,
    build_atcs_address_5series,
    build_atcs_address_7series,
    build_codeline_frame,
    build_indication_usrdata,
    crc16_x25,
    decode_bcd_address,
    encode_bcd_address,
)
from app.protocol_engines.atcs.engine import (
    ATCS_RELAY_TCP_PORT,
    ATCS_RELAY_UDP_BASE,
    AtcsEngine,
)
from app.protocol_engines.protocols import get_default_port, get_identity_key_for_protocol
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType


def by_field(fields, name):
    return next(f for f in fields if f["field"] == name)


def _dev(did, mac, ip, port, name):
    return DeviceContext(device_id=did, mac_address=mac, ip_address=ip, port=port, device_name=name)


def _flow(config=None):
    return FlowContext(
        flow_id="f-atcs",
        source=_dev("mon-1", "02:00:00:00:0a:01", "10.30.0.9", 51000, "ATCS_Monitor_01"),
        destination=_dev("relay-1", "02:00:00:00:0a:02", "10.30.0.2", ATCS_RELAY_TCP_PORT, "ATCS_Relay_01"),
        protocol=ProtocolType.ATCS,
        config=config or {},
        timing_model={},
    )


class TestAtcsAddressing:
    def test_5series_matches_sample(self):
        # RF Codeline Protocol Reference: 5-series = T-RRR-XX-AAAA.
        # sample wayside device 5125013826 = type5, rr125, ext01, addr3826
        assert build_atcs_address_5series(125, 1, 3826) == "5125013826"

    def test_7series_matches_sample(self):
        # 7-series = T-RRR-CCC-AAA-XXXX, e.g. 71253230040202
        assert build_atcs_address_7series(125, 323, 4, 202) == "71253230040202"

    def test_subfields_5series(self):
        sf = {f["name"]: f["digits"] for f in atcs_address_subfields("5125013826")}
        assert sf == {"type": "5", "railroad": "125", "extension": "01", "address": "3826"}

    def test_subfields_7series(self):
        sf = {f["name"]: f["digits"] for f in atcs_address_subfields("71253230040202")}
        assert sf == {"type": "7", "railroad": "125", "codeline": "323",
                      "address": "004", "extension": "0202"}

    def test_bcd_round_trip_both_series(self):
        for addr, nbytes in (("5125013826", 5), ("71253230040202", 7)):
            b = encode_bcd_address(addr)
            assert len(b) == nbytes
            assert decode_bcd_address(b) == addr
        assert encode_bcd_address("5125013826")[0] == 0x51

    def test_bad_address_rejected(self):
        with pytest.raises(ValueError):
            encode_bcd_address("123")               # wrong length
        with pytest.raises(ValueError):
            build_atcs_address_5series(1000, 1, 3826)  # railroad > 999
        with pytest.raises(ValueError):
            build_atcs_address_7series(125, 323, 4, 99999)  # extension > 4 digits


class TestCrc16X25:
    def test_known_vector(self):
        # CRC-16/X.25 of "123456789" is 0x906E (check value from the CRC catalogue)
        assert crc16_x25(b"123456789") == 0x906E


def _check_frame_layout(frame: bytes, fields: list[dict]) -> None:
    """Structural checks: every field is in-bounds; no wireline FCS; vital CRC
    (when present) is the internal last-4-octets field. Values are NOT validated
    for provisional fields (e.g. the vital CRC is deliberately filler)."""
    by_name = {f["field"]: f for f in fields}
    for f in fields:
        assert 0 <= f["off"] and f["off"] + f["len"] <= len(frame)
    assert "atcs.fcs16" not in by_name          # RF path: no wireline HDLC FCS
    if "atcs.vital_crc32" in by_name:
        vc = by_name["atcs.vital_crc32"]
        assert vc["len"] == 4 and vc["off"] + 4 == len(frame)   # last 4 octets


class TestCodelineFrame:
    def test_rf_frame_has_no_wireline_lapb_flags_or_fcs(self):
        # RF path (relay feed): no HDLC 0x7E flags, no LAPB byte, no wireline FCS.
        frame, fields = build_codeline_frame(
            src_addr="71253230040202", dst_addr="21250000010000",
            usrdata=b"\x02\x04", gfi=2, group=5, sseq=77, rseq=45, frame_counter=34,
        )
        names = {f["field"] for f in fields}
        assert not ({"atcs.lapb_address", "atcs.lapb_control",
                     "atcs.flag_open", "atcs.flag_close", "atcs.fcs16"} & names)
        # first byte is the radio-link frame counter, not a 0x7E flag
        assert frame[0] == 34 and frame[0] != 0x7E
        assert by_field(fields, "atcs.frame_counter")["off"] == 0

    def test_vital_crc_present_only_for_vital_and_is_filler(self):
        frame, fields = build_codeline_frame(
            src_addr="5125013826", dst_addr="2125000001", usrdata=b"\x02\x04\x05",
            sseq=1, rseq=2, frame_counter=3, vital=False,
        )
        assert "atcs.vital_crc32" not in {f["field"] for f in fields}
        _check_frame_layout(frame, fields)
        vframe, vfields = build_codeline_frame(
            src_addr="5125013826", dst_addr="2125000001", usrdata=b"\x02\x04\x05",
            sseq=1, rseq=2, frame_counter=3, vital=True,
        )
        vc = by_field(vfields, "atcs.vital_crc32")
        assert vc["len"] == 4 and vc["confidence"] == "provisional"  # filler, labeled
        _check_frame_layout(vframe, vfields)
        assert len(vframe) == len(frame) + 4         # only the internal vital CRC added

    def test_address_order_is_destination_first(self):
        # Appendix D: address-length octet, then DESTINATION address, then SOURCE.
        frame, fields = build_codeline_frame(
            src_addr="71253230040202", dst_addr="5125013826", usrdata=b"\x00",
            sseq=1, rseq=2,
        )
        alo = by_field(fields, "atcs.addr_len")
        # src has 14 digits, dst has 10 -> high nibble 14, low nibble 10
        assert frame[alo["off"]] == ((14 << 4) | 10)
        dst_f = by_field(fields, "atcs.dst_addr")
        src_f = by_field(fields, "atcs.src_addr")
        assert dst_f["off"] < src_f["off"]                     # destination first
        assert frame[dst_f["off"]:dst_f["off"] + dst_f["len"]] == encode_bcd_address("5125013826")
        assert frame[src_f["off"]:src_f["off"] + src_f["len"]] == encode_bcd_address("71253230040202")

    def test_field_map_confidence_tiers(self):
        frame, fields = build_codeline_frame(
            src_addr="5125013826", dst_addr="2125000001",
            usrdata=build_indication_usrdata(2, False, 5), sseq=1, rseq=2,
        )
        for f in fields:
            assert 0 <= f["off"] < len(frame)
            assert f["off"] + f["len"] <= len(frame)
            assert f["confidence"] in {"spec", "provisional", "synthetic"}
        by_name = {f["field"]: f for f in fields}
        assert by_name["atcs.addr_len"]["confidence"] == "spec"          # from Appendix D
        assert by_name["atcs.dst_addr"]["confidence"] == "spec"
        assert by_name["atcs.gfi_group"]["confidence"] == "provisional"  # Appendix G unread
        assert by_name["atcs.frame_counter"]["confidence"] == "provisional"
        assert by_name["atcs.usrdata"]["synthetic"] is True

    def test_datagram_header_reproduces_sample_values(self):
        frame, fields = build_codeline_frame(
            src_addr="5125013826", dst_addr="2125000001", usrdata=b"\x00",
            gfi=2, group=5, sseq=77, rseq=45, vital=False,
        )
        by_name = {f["field"]: f for f in fields}
        assert frame[by_name["atcs.gfi_group"]["off"]] == ((2 << 4) | 5)  # GFI=2, Group=5
        assert frame[by_name["atcs.sseq"]["off"]] >> 1 == 77             # SSeq=77
        assert frame[by_name["atcs.rseq_vital"]["off"]] >> 1 == 45       # RSeq=45


class TestAtcsEngine:
    def test_registered(self):
        engine = get_engine(ProtocolType.ATCS)
        assert isinstance(engine, AtcsEngine)
        assert engine.protocol_type == ProtocolType.ATCS
        assert ProtocolType.ATCS in list_supported_protocols()

    def test_validate_config(self):
        engine = AtcsEngine()
        assert engine.validate_config({}) == []
        assert engine.validate_config({"railroad_num": 1000})
        assert engine.validate_config({"udp_slot": 99})
        assert engine.validate_config({"control_every": -1})

    def test_full_relay_feed(self):
        engine = get_engine(ProtocolType.ATCS)
        flow = _flow({"railroad_num": 125, "codeline_num": 13, "control_every": 3, "keepalive_every": 2})
        state = engine.create_initial_state(flow)

        events = list(engine.generate_startup_sequence(flow, state, 0.0))
        for i in range(6):
            events += list(engine.generate_poll_cycle(flow, state, 1000.0 * (i + 1)))
        events += list(engine.generate_shutdown_sequence(flow, state, 9000.0))

        tcp_n = udp_codeline = udp_keepalive = 0
        for ev in events:
            pkt = Ether(ev.packet_bytes)
            assert IP in pkt
            assert bytes(pkt) == bytes(Ether(bytes(pkt)))   # well-formed
            if ev.metadata.get("type", "").startswith("atcs_codeline"):
                udp_codeline += 1
                assert UDP in pkt
                # UDP payload is ASCII-hex; decode and structurally validate
                hex_txt = bytes(pkt[UDP].payload).strip()
                frame = bytes.fromhex(hex_txt.decode("ascii"))
                assert frame.hex().upper() == ev.metadata["codeline_frame_hex"]
                _check_frame_layout(frame, ev.metadata["codeline_fields"])
            elif ev.metadata.get("type") == "atcs_keepalive":
                udp_keepalive += 1
                assert UDP in pkt
            elif ev.metadata.get("type", "").startswith("tcp_") or ev.metadata.get("type", "").startswith("atcs_relay"):
                tcp_n += 1
                assert TCP in pkt

        assert udp_codeline >= 6, f"expected >=6 codeline frames, got {udp_codeline}"
        assert udp_keepalive >= 1, "expected version keep-alives"
        # relay data port assignment present
        assert any(e.metadata.get("type") == "atcs_relay_port_assign" for e in events)
        ts = [e.timestamp_ms for e in events]
        assert ts == sorted(ts)

    def test_udp_data_port_in_relay_range(self):
        engine = get_engine(ProtocolType.ATCS)
        flow = _flow({"udp_slot": 5})
        state = engine.create_initial_state(flow)
        list(engine.generate_startup_sequence(flow, state, 0.0))
        ev = next(e for e in engine.generate_poll_cycle(flow, state, 1000.0)
                  if e.metadata.get("type", "").startswith("atcs_codeline"))
        udp = Ether(ev.packet_bytes)[UDP]
        assert udp.sport == ATCS_RELAY_UDP_BASE + 5


class TestAtcsRegistryWiring:
    def test_default_port(self):
        assert get_default_port("atcs") == ATCS_RELAY_TCP_PORT == 4802

    def test_identity_key(self):
        assert get_identity_key_for_protocol("atcs") == "atcs_identity"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
