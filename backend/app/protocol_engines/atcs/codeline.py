# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""ATCS (Advanced Train Control System) codeline frame building.

ATCS is a legacy radio-code-line train-control system whose native transport is
a 900 MHz FSK radio link, NOT IP. Its layering (AAR MSRP Section K-II, formerly
ATCS Spec 200 = S-5800) has TWO distinct Layer-2s: X.25 **LAPB** on the ground
point-to-point wireline interfaces, and an **HDLC-balanced radio link** for the
mobile/wayside RF path. The only IP-observable form of ATCS is the **ATCS
Monitor relay** (see ``engine.py``), which streams *decoded* codeline frames as
ASCII-hex over UDP.

The relay feed carries the **RF path**, so this module models the decoded RF
logical frame — a radio datagram (Appendix G, Layer 3) over the radio link
(Appendix L, Layer 2) — and deliberately does NOT emit the wireline-LAPB
address/control bytes or HDLC 0x7E flags (those belong to the ground wireline
path). The physical FEC / 85-bit-block encoding (Appendix W) is stripped by the
receiver before the relay sees it, so it is out of scope.

Frame model (decoded RF logical frame — octet order per K-II Appendix D)::

    radio-link frame counter (1B)        Appendix L   — the ATCSMon "Frame=NN"
    radio datagram header (3B)           Appendix G   — GFI/Group, SSeq, RSeq/Vital
    packet prefix (4B)                   §2.x         — QD10PPPA + 3 zero octets
    address-length octet (1B)            §2.3-2.4     — src digits (hi) | dst (lo)
    destination ATCS address (BCD)       §2.3-2.4     — destination FIRST
    source ATCS address (BCD)            §2.3-2.4
    facility-length octet (1B)           §2.x
    transport header (3B)                §2.11-2.13   — msg#, part#, len | vital bit
    packet label (2B)                    Spec 250
    UsrData (NB)                         Spec 250     — application payload
    vital CRC (4B, internal)             Appendix Y   — vital msgs ONLY; last 4 octets

There is NO explicit UsrData-length octet (ATCSMon's UsrData=N is derived) and
NO wireline HDLC FCS / 0x7E flags on the RF path (integrity there is FEC/85-bit
blocks, Appendix W, stripped before the relay). The vital CRC is internal to the
packet (last 4 octets, over address-length octet .. end of UsrData) and is
FILLER — the real polynomial (Spec 250 §3.2.1.1) was unread.

FIDELITY — three confidence tiers, per-field in the label map so a downstream
Cyber Vision dissector-training pipeline knows which bytes to trust (CV has no
rail DPI today; this generates labeled corpora to build one):

- ``spec``        — derivable/confirmed: the ATCS address decimal structure and
                    BCD packing, destination-first ordering + address-length
                    octet (K-II Appendix D §2.3-2.4), CRC-16/X.25 FCS, and the
                    presence + position of the 32-bit vital CRC (Appendix Y).
- ``provisional`` — NOT yet read from the primary source: the exact bit widths
                    of the radio-datagram header (GFI/Group/SSeq/RSeq/Vital,
                    Appendix G, ~K-II-57) and the radio-link frame counter
                    (Appendix L, ~K-II-70), plus the vital-CRC polynomial
                    (Spec 250 §3.2.1.1). Reproduces the known sample values;
                    byte positions are best-effort pending a direct read of those
                    appendices. Isolated in ``_build_radio_datagram_header`` for
                    exactly that correction. See ``SPEC_NEEDS.md``.
- ``synthetic``   — UsrData payload content (per-territory codeline bit semantics
                    live in private railroad ``.mcp`` databases).

NOTE: this layering was corrected from an earlier LAPB-based model per K-II
findings; the exact Appendix G/L byte tables were unreachable from the build
host and remain the one open item. There are TWO distinct "vital" concepts — a
transport vital bit (Appendix D §2.11) and the radio-datagram Vital flag; both
are modeled.

Reference sample (sigidwiki) whose field VALUES this builder reproduces::

    Wayside 5125013826  Frame=34 GFI=2 Group=5 SSeq=77 RSeq=45  Vital=0
"""

from __future__ import annotations

import struct
from binascii import crc32

# ATCS address Type digit (first digit of the address).
ATCS_TYPE_LOCOMOTIVE = 1
ATCS_TYPE_OFFICE = 2
ATCS_TYPE_BASE = 3
ATCS_TYPE_WAYSIDE_5 = 5         # 5-series MCP (10-digit address)
ATCS_TYPE_WAYSIDE_7 = 7         # 7-series MCP (14-digit address)
ATCS_TYPE_NAMES = {
    1: "locomotive",
    2: "office",
    3: "base_station",
    5: "wayside",
    7: "wayside",
}

# Extension (rightmost digits) semantics, per the ATCSMon "RF Codeline Protocol
# Reference" (NS 7-series / CSX 5-series conventions). Used to make synthetic
# indication vs control frames address realistic MCP logic partitions.
ATCS_EXT7_INDICATION = 202     # 0202: native ATCS VLC, field indication packets
ATCS_EXT7_CONTROL = 101        # 0101: diagnostic / MCP command & control
ATCS_EXT5_CONTROL = 1          # 01: command & control (5-series)
ATCS_EXT5_INDICATION = 2       # 02: field control & indication (5-series)


def crc16_x25(data: bytes) -> int:
    """CRC-16/X.25 (poly 0x1021 reflected = 0x8408, init 0xFFFF, xorout 0xFFFF).

    This is the standard HDLC/X.25 Frame Check Sequence. Transmitted
    little-endian (low byte first) in the HDLC frame.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
    return crc ^ 0xFFFF


# ATCS vital CRC — AAR MSRP Section K-II (ATCS Spec 200 family), Version 4.0.
#
#   poly = x^31 + x^30 + x^28 + x^25 + x^19 + x^18 + x^16 + x^15 + x^11 + x^9 + x^7 + 1
#
# 31-bit register; the low-order mask (excluding the implicit x^31) is 0x520D8A81.
# Data octets are processed LSB-first (ATCS data bit ordering), so the reflected
# polynomial is used. The resulting 31-bit register is placed on the wire
# least-significant-octet first, which is what makes the spec's stored form read
# "most-significant byte first, highest stored bit always zero".
#
# VERIFIED against the K-II mandatory regression vector:
#     input 01 02 -> 25 ED BD 70      (see tests/protocol_engines/test_atcs.py)
# and against the spec's self-check invariant: a message with its CRC appended
# reduces to zero.
VITAL_CRC_POLY = 0x520D8A81
VITAL_CRC_WIDTH = 31
_VITAL_CRC_MASK = (1 << VITAL_CRC_WIDTH) - 1


def _reflect(value: int, width: int) -> int:
    out = 0
    for i in range(width):
        if value & (1 << i):
            out |= 1 << (width - 1 - i)
    return out


_VITAL_CRC_POLY_REF = _reflect(VITAL_CRC_POLY, VITAL_CRC_WIDTH)


def vital_crc(data: bytes) -> int:
    """ATCS 31-bit vital CRC over ``data`` (K-II). Returns the register value.

    Coverage per spec: from the address-length octet through the end of the
    Layer-7 data. Use :func:`vital_crc_bytes` for the on-wire form.
    """
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ _VITAL_CRC_POLY_REF if crc & 1 else crc >> 1
    return crc & _VITAL_CRC_MASK


def vital_crc_bytes(data: bytes) -> bytes:
    """On-wire 4-octet form of the vital CRC (K-II vector: 01 02 -> 25 ED BD 70)."""
    return struct.pack("<I", vital_crc(data))


def vital_crc_check(data_with_crc: bytes) -> bool:
    """Spec self-check: a message with its CRC appended reduces to zero."""
    return vital_crc(data_with_crc) == 0


def build_atcs_address_7series(
    railroad: int, codeline: int, serial: int, extension: int, type_digit: int = 7,
) -> str:
    """Compose a 14-digit 7-series ATCS address: T-RRR-CCC-AAA-XXXX.

    Per the ATCSMon RF Codeline Protocol Reference: Type(1) Railroad(3)
    Codeline(3) Address(3) eXtension(4). e.g.
    ``build_atcs_address_7series(125, 323, 4, 202) -> "71253230040202"``.
    """
    if not 0 <= type_digit <= 9:
        raise ValueError("type_digit must be a single digit")
    for name, val in (("railroad", railroad), ("codeline", codeline), ("serial", serial)):
        if not 0 <= val <= 999:
            raise ValueError(f"{name} must be 0-999 (3 digits)")
    if not 0 <= extension <= 9999:
        raise ValueError("extension must be 0-9999 (4 digits)")
    return f"{type_digit:01d}{railroad:03d}{codeline:03d}{serial:03d}{extension:04d}"


def build_atcs_address_5series(
    railroad: int, extension: int, serial: int, type_digit: int = 5,
) -> str:
    """Compose a 10-digit 5-series ATCS address: T-RRR-XX-AAAA.

    Per the ATCSMon RF Codeline Protocol Reference: Type(1) Railroad(3)
    eXtension(2) Address(4). e.g. the sample wayside device
    ``build_atcs_address_5series(125, 1, 3826) -> "5125013826"`` (ext 01 =
    command & control).
    """
    if not 0 <= type_digit <= 9:
        raise ValueError("type_digit must be a single digit")
    if not 0 <= railroad <= 999:
        raise ValueError("railroad must be 0-999 (3 digits)")
    if not 0 <= extension <= 99:
        raise ValueError("extension must be 0-99 (2 digits)")
    if not 0 <= serial <= 9999:
        raise ValueError("serial must be 0-9999 (4 digits)")
    return f"{type_digit:01d}{railroad:03d}{extension:02d}{serial:04d}"


def atcs_address_subfields(addr: str) -> list[dict]:
    """Decompose an ATCS address into labelled decimal sub-fields.

    Handles 10-digit (5-series: T-RRR-XX-AAAA) and 14-digit (7-series:
    T-RRR-CCC-AAA-XXXX) addresses per the RF Codeline Protocol Reference.
    Returns ``{name, digits}`` entries — the digit *structure* is spec-confirmed;
    the on-wire byte packing (modelled as BCD) is the assumed encoding.
    """
    if len(addr) == 14:
        return [
            {"name": "type", "digits": addr[0:1], "meaning": ATCS_TYPE_NAMES.get(int(addr[0]), "unknown")},
            {"name": "railroad", "digits": addr[1:4]},
            {"name": "codeline", "digits": addr[4:7]},
            {"name": "address", "digits": addr[7:10]},
            {"name": "extension", "digits": addr[10:14]},
        ]
    if len(addr) == 10:
        return [
            {"name": "type", "digits": addr[0:1], "meaning": ATCS_TYPE_NAMES.get(int(addr[0]), "unknown")},
            {"name": "railroad", "digits": addr[1:4]},
            {"name": "extension", "digits": addr[4:6]},
            {"name": "address", "digits": addr[6:10]},
        ]
    raise ValueError("ATCS address must be 10 (5-series) or 14 (7-series) digits")


# ATCS packs address digits two-per-octet, but a decimal ZERO is encoded as the
# nibble 0xA — NOT 0x0 (K-II). Plain BCD would put 0x0 on the wire and every
# address containing a zero would be wrong.
ATCS_BCD_ZERO = 0xA


def _digit_to_nibble(d: str) -> int:
    return ATCS_BCD_ZERO if d == "0" else int(d)


def _nibble_to_digit(n: int) -> str:
    return "0" if n == ATCS_BCD_ZERO else str(n)


def encode_bcd_address(addr: str) -> bytes:
    """Pack a 10- or 14-digit ATCS address into ATCS-BCD octets (high nibble first).

    Per K-II, a zero digit is carried as nibble 0xA (see :data:`ATCS_BCD_ZERO`);
    an odd digit count is padded with a zero nibble. Both supported address forms
    (10-digit 5-series, 14-digit 7-series) are even, so no padding is emitted today.
    """
    if len(addr) not in (10, 14) or not addr.isdigit():
        raise ValueError("ATCS address must be 10 (5-series) or 14 (7-series) digits")
    return bytes(
        (_digit_to_nibble(addr[i]) << 4) | _digit_to_nibble(addr[i + 1])
        for i in range(0, len(addr), 2)
    )


def decode_bcd_address(b: bytes) -> str:
    """Inverse of :func:`encode_bcd_address` (0xA decodes back to '0')."""
    return "".join(
        _nibble_to_digit((x >> 4) & 0xF) + _nibble_to_digit(x & 0xF) for x in b
    )


def build_datagram_octet0(
    priority: int = 0,
    q: bool = False,
    delivery_confirmation: bool = False,
    arq_disable: bool = False,
) -> int:
    """ATCS datagram octet 0 — ``Q D 1 0 P P P A`` (K-II).

    Bits 5-4 are the literal ``10``. ``Q`` is 0 for an ordinary data datagram.
    """
    return (
        ((1 if q else 0) << 7)
        | ((1 if delivery_confirmation else 0) << 6)
        | 0x20
        | ((priority & 0x07) << 1)
        | (1 if arq_disable else 0)
    )


def build_network_header(
    src_addr: str,
    dst_addr: str,
    sseq: int,
    rseq: int,
    *,
    priority: int = 0,
    q: bool = False,
    delivery_confirmation: bool = False,
    arq_disable: bool = False,
    logical_channel: int = 0,
) -> tuple[bytes, list[dict]]:
    """ATCS 5-octet network (datagram) header, per K-II.

    Layout::

        0  Q D 1 0 P P P A
        1  logical channel number            (0 in current deployments)
        2  send sequence << 1                (low bit zero)
        3  receive sequence << 1             (low bit zero)
        4  source_length << 4 | destination_length   (in BCD digits)

    NOTE the asymmetry: the length octet carries SOURCE length in the high
    nibble, yet the DESTINATION address is transmitted first.
    """
    header = bytes([
        build_datagram_octet0(priority, q, delivery_confirmation, arq_disable),
        logical_channel & 0xFF,
        (sseq & 0x7F) << 1,
        (rseq & 0x7F) << 1,
        ((len(src_addr) & 0x0F) << 4) | (len(dst_addr) & 0x0F),
    ])
    fields = [
        {"off": 0, "len": 1, "field": "atcs.control",
         "value": {"q": int(q), "delivery_confirmation": int(delivery_confirmation),
                   "priority": priority, "arq_disable": int(arq_disable)},
         "synthetic": False, "confidence": "spec_legacy"},
        {"off": 1, "len": 1, "field": "atcs.logical_channel",
         "value": logical_channel, "synthetic": False, "confidence": "spec_legacy"},
        {"off": 2, "len": 1, "field": "atcs.send_sequence",
         "value": sseq, "synthetic": False, "confidence": "spec_legacy"},
        {"off": 3, "len": 1, "field": "atcs.receive_sequence",
         "value": rseq, "synthetic": False, "confidence": "spec_legacy"},
        {"off": 4, "len": 1, "field": "atcs.addr_len",
         "value": {"src_digits": len(src_addr), "dst_digits": len(dst_addr)},
         "synthetic": False, "confidence": "spec_legacy"},
    ]
    return header, fields


def build_transport_header(
    usrdata_len: int,
    *,
    message_number: int = 0,
    more: bool = False,
    part_number: int = 0,
    end_to_end_ack: bool = False,
    vital: bool = False,
    label: int = 0,
) -> tuple[bytes, list[dict]]:
    """ATCS 5-octet transport header, per K-II.

    Layout::

        0  message_number << 1 | more
        1  part_number    << 1 | end_to_end_ack
        2  message_length << 1 | vital        <- the VITAL flag lives HERE
        3  label, high octet
        4  label, low octet
    """
    header = bytes([
        ((message_number & 0x7F) << 1) | (1 if more else 0),
        ((part_number & 0x7F) << 1) | (1 if end_to_end_ack else 0),
        ((usrdata_len & 0x7F) << 1) | (1 if vital else 0),
        (label >> 8) & 0xFF,
        label & 0xFF,
    ])
    fields = [
        {"off": 0, "len": 1, "field": "atcs.message_number",
         "value": {"message_number": message_number, "more": int(more)},
         "synthetic": False, "confidence": "spec_legacy"},
        {"off": 1, "len": 1, "field": "atcs.part_number",
         "value": {"part_number": part_number, "end_to_end_ack": int(end_to_end_ack)},
         "synthetic": False, "confidence": "spec_legacy"},
        {"off": 2, "len": 1, "field": "atcs.message_length_vital",
         "value": {"message_length": usrdata_len, "vital": int(vital)},
         "synthetic": False, "confidence": "spec_legacy"},
        {"off": 3, "len": 2, "field": "atcs.label",
         "value": label, "synthetic": False, "confidence": "spec_legacy"},
    ]
    return header, fields


def build_codeline_frame(
    src_addr: str,
    dst_addr: str,
    usrdata: bytes,
    *,
    sseq: int = 0,
    rseq: int = 0,
    vital: bool = False,
    priority: int = 0,
    logical_channel: int = 0,
    message_number: int = 0,
    part_number: int = 0,
    label: int = 0,
    relay_frame_counter: int | None = None,
) -> tuple[bytes, list[dict]]:
    """Build an ATCS codeline datagram (as the relay decodes it) + field map.

    Structure per AAR MSRP Section K-II (Version 4.0), which supersedes the
    earlier reconstructed layout::

        network header (5B)                 [spec_legacy]
          0  Q D 1 0 P P P A
          1  logical channel number
          2  send sequence << 1
          3  receive sequence << 1
          4  source_length << 4 | destination_length
        destination ATCS address (BCD)      [spec_legacy]  destination FIRST
        source ATCS address (BCD)           [spec_legacy]
        facility length (1B)                [spec_legacy]
        facility (variable)                 (none emitted)
        transport header (5B)               [spec_legacy]
          0  message_number << 1 | more
          1  part_number    << 1 | end_to_end_ack
          2  message_length << 1 | vital    <- the VITAL flag lives here
          3..4 label (16-bit)
        UsrData (NB)                        [synthetic]
        vital CRC (4B)                      [spec_legacy]  present when vital=1

    The vital CRC covers the address-length octet (network header octet 4)
    through the end of the Layer-7 data, and is verified against the K-II
    mandatory vector (01 02 -> 25 ED BD 70).

    ``relay_frame_counter`` is NOT part of the ATCS datagram — it belongs to the
    ATCS Monitor relay container, whose framing is still unconfirmed. When set it
    is prefixed and labelled ``relay.frame_counter`` (confidence ``provisional``)
    so a consumer can tell relay bytes from protocol bytes.
    """
    src_bcd = encode_bcd_address(src_addr)
    dst_bcd = encode_bcd_address(dst_addr)
    net_hdr, net_fields = build_network_header(
        src_addr, dst_addr, sseq, rseq,
        priority=priority, logical_channel=logical_channel,
    )
    tx_hdr, tx_fields = build_transport_header(
        len(usrdata), message_number=message_number, part_number=part_number,
        vital=vital, label=label,
    )

    body = bytearray()
    relay_len = 0
    if relay_frame_counter is not None:
        body.append(relay_frame_counter & 0xFF)
        relay_len = 1
    dgram_start = len(body)
    body += net_hdr
    # Vital CRC coverage starts at the address-length octet (net header octet 4).
    vcrc_start = dgram_start + 4
    body += dst_bcd                       # destination address FIRST
    body += src_bcd
    body.append(0x00)                     # facility length (no facility emitted)
    body += tx_hdr
    ud_off = len(body)
    body += usrdata
    if vital:
        body += vital_crc_bytes(bytes(body[vcrc_start:]))

    frame = bytes(body)

    fields: list[dict] = []
    if relay_frame_counter is not None:
        fields.append({
            "off": 0, "len": 1, "field": "relay.frame_counter",
            "value": relay_frame_counter, "synthetic": False,
            "confidence": "provisional",
            "note": "ATCS Monitor relay container, not part of the ATCS datagram",
        })
    for f in net_fields:
        fields.append({**f, "off": dgram_start + f["off"]})
    dst_off = dgram_start + len(net_hdr)
    fields.append({"off": dst_off, "len": len(dst_bcd), "field": "atcs.dst_addr",
                   "value": dst_addr, "subfields": atcs_address_subfields(dst_addr),
                   "synthetic": False, "confidence": "spec_legacy"})
    src_off = dst_off + len(dst_bcd)
    fields.append({"off": src_off, "len": len(src_bcd), "field": "atcs.src_addr",
                   "value": src_addr, "subfields": atcs_address_subfields(src_addr),
                   "synthetic": False, "confidence": "spec_legacy"})
    fac_off = src_off + len(src_bcd)
    fields.append({"off": fac_off, "len": 1, "field": "atcs.facility_len",
                   "value": 0, "synthetic": False, "confidence": "spec_legacy"})
    tx_off = fac_off + 1
    for f in tx_fields:
        fields.append({**f, "off": tx_off + f["off"]})
    fields.append({"off": ud_off, "len": len(usrdata), "field": "atcs.usrdata",
                   "value": usrdata.hex(), "synthetic": True, "confidence": "synthetic"})
    if vital:
        fields.append({"off": ud_off + len(usrdata), "len": 4, "field": "atcs.vital_crc",
                       "value": "crc31", "synthetic": False, "confidence": "spec_legacy",
                       "note": "31-bit CRC, K-II; covers addr-len octet .. end of L7 data"})
    return frame, fields


# ---------------------------------------------------------------------------
# Synthetic UsrData builders (confidence=synthetic). Model plausible codeline
# indications/controls; the bit meanings are our convention, not AAR Spec 200.
# ---------------------------------------------------------------------------

def build_indication_usrdata(signal_aspect: int, switch_normal: bool, occupancy: int) -> bytes:
    """Wayside -> office indication (synthetic). Mirrors the sample's 6-byte UsrData."""
    return struct.pack(
        ">BBBBBB",
        0x02,                                  # message class: indication
        0x04,                                  # sub-type
        signal_aspect & 0xFF,
        0x00 if switch_normal else 0x01,
        occupancy & 0xFF,
        0x00,                                  # reserved / padding
    )


def build_control_usrdata(command: int, target: int, value: int) -> bytes:
    """Office -> wayside control (synthetic)."""
    return struct.pack(">BBBBB", 0x01, command & 0xFF, target & 0xFF, value & 0xFF, 0x00)
