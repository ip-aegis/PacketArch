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
    ATCS_BCD_ZERO,
    atcs_address_subfields,
    build_datagram_octet0,
    build_network_header,
    build_transport_header,
    vital_crc,
    vital_crc_bytes,
    vital_crc_check,
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


class TestVitalCrc:
    """AAR MSRP K-II 31-bit vital CRC — the spec ships a mandatory vector."""

    def test_kii_mandatory_vector(self):
        # K-II: input 01 02 -> CRC 25 ED BD 70
        assert vital_crc_bytes(bytes([0x01, 0x02])).hex().upper() == "25EDBD70"

    def test_register_is_31_bit(self):
        for data in (b"", b"\x01\x02", bytes(range(64)), b"ATCS" * 9):
            assert vital_crc(data) < (1 << 31), "high bit must always be zero"

    def test_self_check_residue_is_zero(self):
        """Spec invariant: a message with its CRC appended reduces to zero."""
        for data in (bytes([0x01, 0x02]), b"\xde\xad\xbe\xef", bytes(range(16)), b"ATCS"):
            assert vital_crc_check(data + vital_crc_bytes(data))

    def test_detects_corruption(self):
        data = bytes(range(24))
        good = data + vital_crc_bytes(data)
        assert vital_crc_check(good)
        for i in range(len(good)):
            bad = bytearray(good)
            bad[i] ^= 0x01          # single-bit flip anywhere
            assert not vital_crc_check(bytes(bad)), f"missed corruption at octet {i}"


def _check_frame_layout(frame: bytes, fields: list[dict]) -> None:
    """Structural checks: fields in-bounds, no wireline artifacts, valid tiers."""
    by_name = {f["field"]: f for f in fields}
    for f in fields:
        assert 0 <= f["off"] and f["off"] + f["len"] <= len(frame)
        assert f["confidence"] in {"spec_legacy", "spec", "provisional", "synthetic"}
    # RF path: none of the wireline-HDLC artifacts belong here
    assert not ({"atcs.lapb_address", "atcs.lapb_control", "atcs.flag_open",
                 "atcs.flag_close", "atcs.fcs16", "atcs.gfi_group"} & set(by_name))


class TestCodelineFrame:
    """Structure per AAR MSRP K-II: 5-octet network header, addresses (dest
    first), facility length, 5-octet transport header, UsrData, vital CRC."""

    def test_datagram_octet0_layout(self):
        # Q D 1 0 P P P A — bits 5-4 are the literal '10'; Q=0 for data
        o = build_datagram_octet0(priority=0)
        assert o & 0x30 == 0x20, "bits 5-4 must be literal 10"
        assert o >> 7 == 0, "Q must be 0 for an ordinary data datagram"
        assert build_datagram_octet0(priority=5) >> 1 & 0x07 == 5
        assert build_datagram_octet0(q=True) >> 7 == 1
        assert build_datagram_octet0(delivery_confirmation=True) >> 6 & 1 == 1
        assert build_datagram_octet0(arq_disable=True) & 1 == 1

    def test_network_header_is_five_octets(self):
        hdr, fields = build_network_header("71253230040202", "5125013826", sseq=77, rseq=45)
        assert len(hdr) == 5
        assert hdr[0] & 0x30 == 0x20            # QD10PPPA
        assert hdr[1] == 0                       # logical channel
        assert hdr[2] >> 1 == 77 and hdr[2] & 1 == 0   # send seq, low bit zero
        assert hdr[3] >> 1 == 45 and hdr[3] & 1 == 0   # recv seq, low bit zero
        # length octet: SOURCE length high nibble, DESTINATION low nibble
        assert hdr[4] == ((14 << 4) | 10)
        assert {f["confidence"] for f in fields} == {"spec_legacy"}

    def test_transport_header_carries_vital_bit(self):
        hdr, _ = build_transport_header(6, message_number=3, part_number=1,
                                        vital=True, label=0x1234)
        assert len(hdr) == 5
        assert hdr[0] >> 1 == 3                  # message number
        assert hdr[1] >> 1 == 1                  # part number
        assert hdr[2] >> 1 == 6                  # message length
        assert hdr[2] & 1 == 1                   # VITAL lives in transport octet 2
        assert hdr[3] == 0x12 and hdr[4] == 0x34  # 16-bit label

    def test_bcd_zero_is_nibble_A(self):
        """K-II: a zero digit is carried as 0xA, not 0x0."""
        assert ATCS_BCD_ZERO == 0xA
        b = encode_bcd_address("2125000001")     # lots of zeros
        assert 0x00 not in b, "plain-BCD zeros would be wrong on the wire"
        assert (b[2] >> 4) == 0xA                 # a '0' digit -> 0xA
        assert decode_bcd_address(b) == "2125000001"

    def test_frame_order_dest_before_src(self):
        frame, fields = build_codeline_frame(
            src_addr="71253230040202", dst_addr="5125013826",
            usrdata=b"\x02\x04", sseq=1, rseq=2,
        )
        dst_f = by_field(fields, "atcs.dst_addr")
        src_f = by_field(fields, "atcs.src_addr")
        assert dst_f["off"] < src_f["off"]
        assert frame[dst_f["off"]:dst_f["off"] + dst_f["len"]] == encode_bcd_address("5125013826")
        assert frame[src_f["off"]:src_f["off"] + src_f["len"]] == encode_bcd_address("71253230040202")
        _check_frame_layout(frame, fields)

    def test_vital_crc_real_and_verifiable(self):
        """Vital CRC is now spec-derived: it must self-check to zero."""
        plain, pf = build_codeline_frame("5125013826", "2125000001", b"\x02\x04\x05",
                                         sseq=1, rseq=2, vital=False)
        assert "atcs.vital_crc" not in {f["field"] for f in pf}
        vframe, vf = build_codeline_frame("5125013826", "2125000001", b"\x02\x04\x05",
                                          sseq=1, rseq=2, vital=True)
        crc_f = by_field(vf, "atcs.vital_crc")
        assert crc_f["len"] == 4 and crc_f["confidence"] == "spec_legacy"
        assert crc_f["off"] + 4 == len(vframe)
        # coverage: address-length octet (network header octet 4) .. end of L7 data
        alo = by_field(vf, "atcs.addr_len")["off"]
        assert vital_crc_check(vframe[alo:]), "CRC must reduce the covered span to zero"
        assert len(vframe) == len(plain) + 4

    def test_relay_counter_is_labelled_as_relay_not_atcs(self):
        """The frame counter is ATCSMon relay container, not an ATCS field."""
        _, no_relay = build_codeline_frame("5125013826", "2125000001", b"\x00", sseq=1, rseq=2)
        assert "relay.frame_counter" not in {f["field"] for f in no_relay}
        frame, fields = build_codeline_frame("5125013826", "2125000001", b"\x00",
                                             sseq=1, rseq=2, relay_frame_counter=34)
        rc = by_field(fields, "relay.frame_counter")
        assert rc["off"] == 0 and frame[0] == 34
        assert rc["confidence"] == "provisional"   # relay container still unconfirmed
        assert "atcs.frame_counter" not in {f["field"] for f in fields}

    def test_confidence_tiers(self):
        frame, fields = build_codeline_frame(
            "5125013826", "2125000001", build_indication_usrdata(2, False, 5),
            sseq=1, rseq=2, vital=True,
        )
        by_name = {f["field"]: f for f in fields}
        assert by_name["atcs.control"]["confidence"] == "spec_legacy"
        assert by_name["atcs.addr_len"]["confidence"] == "spec_legacy"
        assert by_name["atcs.dst_addr"]["confidence"] == "spec_legacy"
        assert by_name["atcs.vital_crc"]["confidence"] == "spec_legacy"
        assert by_name["atcs.usrdata"]["synthetic"] is True
        _check_frame_layout(frame, fields)


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
