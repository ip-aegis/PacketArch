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

Frame model — VERIFIED against a corpus of real ATCSMon-decoded frames (every
corpus frame round-trips to ATCSMon's reported fields and both CRC-16/X.25
values reproduce exactly)::

    RF header (5B)                       — the relay/RF-link container
      [0]     RF address type            0x23 ground datagram ('#' in ATCSMon's gutter)
      [1]     # pad bits in last RS block
      [2]     # of Reed-Solomon blocks   the RF "length" field
      [3..4]  header CRC-16/X.25 over [0..2], little-endian
    --- datagram (frame bytes [5:-2], covered by the datagram CRC) ---
    network header (5B)
      [5]     (GFI << 4) | Group
      [6]     spare
      [7]     send sequence << 1
      [8]     receive sequence << 1
      [9]     source_length << 4 | destination_length   (digit counts; 0xA == 10)
    destination ATCS address (BCD)       — destination FIRST
    source ATCS address (BCD)
    facility-length octet (1B)
    transport header (5B)                Spec 250 — msg#/part#/len|vital, label
    UsrData (NB)                         Spec 250 — application payload
    vital CRC (4B, inner)                — vital msgs only, before the datagram CRC
    --- end datagram ---
    datagram CRC (2B)                    CRC-16/X.25 over [5:-2], little-endian

ATCSMon has NO explicit UsrData-length octet — it derives UsrData=N from the
received byte count minus the fixed overhead (RF header + network header +
addresses + facility + transport + datagram CRC). The two framing CRCs are the
standard HDLC/X.25 FCS (poly 0x1021, init/xor 0xFFFF, reflected, stored LE).

FIDELITY — three confidence tiers, per-field in the label map so a downstream
Cyber Vision dissector-training pipeline knows which bytes to trust (CV has no
rail DPI today; this generates labeled corpora to build one):

- ``spec``        — corpus-verified: the 5-byte RF header (address type / pad
                    bits / block count / header CRC), both CRC-16/X.25 fields,
                    the GFI|Group octet, spare, send/recv sequences, the
                    address-length nibble octet, destination-first BCD addresses
                    (0xA == 0), and the facility-length octet.
- ``spec_legacy`` — spec-derived from a legacy source, not corpus-pinned byte for
                    byte: the transport-header field breakdown (Spec 250) and the
                    31-bit K-II vital CRC (verified against the mandatory vector
                    01 02 -> 25 ED BD 70, but its placement in a real *vital*
                    frame is unconfirmed — the corpus is all Vital=0).
- ``synthetic``   — UsrData payload content (per-territory codeline bit semantics
                    live in private railroad ``.mcp`` databases).

The RF-header block-count/pad-bits (bytes [1..2]) encode the frame length as
Reed-Solomon blocks of 60 frame-bits each; ATCSMon rejects a frame whose byte
count doesn't reconcile with them. The exact formula (``_rf_length_fields``) was
recovered from the corpus and confirmed live against ATCSMon. See ``SPEC_NEEDS.md``.

Reference corpus frame whose fields this builder reproduces::

    To Dispatch 2802063007  Frame=32 GFI=6 Group=8 SSeq=35 RSeq=0  Vital=0  UsrData=4
"""

from __future__ import annotations

import struct

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


# ATCS datagram octet [5] = (GFI << 4) | Group ("message type & priority").
# Verified against the relay corpus: 0x68 -> GFI 6 / Group 8, 0x25 -> GFI 2 /
# Group 5, 0x6C -> GFI 6 / Group 12. GFI = Group Format Identifier.
ATCS_GFI_DEFAULT = 6
ATCS_GROUP_INDICATION = 8      # inbound-to-ground indication datagrams (corpus A1/A4)
ATCS_GROUP_CONTROL = 12        # inbound-to-ground control datagrams (corpus A5-A7)


def build_network_header(
    src_addr: str,
    dst_addr: str,
    sseq: int,
    rseq: int,
    *,
    gfi: int = ATCS_GFI_DEFAULT,
    group: int = ATCS_GROUP_INDICATION,
) -> tuple[bytes, list[dict]]:
    """ATCS 5-octet datagram network header — VERIFIED against the relay corpus.

    Layout (datagram offsets = frame bytes [5..9])::

        0  (GFI << 4) | Group        message type & priority
        1  spare / reserved          (0x00 across the corpus)
        2  send sequence << 1        P(S); low bit zero
        3  receive sequence << 1     P(R); low bit zero
        4  source_length << 4 | destination_length   (digit counts; nibble 0xA == 10)

    NOTE the asymmetry: the length octet carries SOURCE length in the high
    nibble, yet the DESTINATION address is transmitted first (corpus-confirmed).
    A 10-digit address is length nibble 0xA, a 14-digit address is 0xE.
    """
    header = bytes([
        ((gfi & 0x0F) << 4) | (group & 0x0F),
        0x00,
        (sseq & 0x7F) << 1,
        (rseq & 0x7F) << 1,
        ((len(src_addr) & 0x0F) << 4) | (len(dst_addr) & 0x0F),
    ])
    fields = [
        {"off": 0, "len": 1, "field": "atcs.gfi_group",
         "value": {"gfi": gfi, "group": group},
         "synthetic": False, "confidence": "spec"},
        {"off": 1, "len": 1, "field": "atcs.spare",
         "value": 0, "synthetic": False, "confidence": "spec"},
        {"off": 2, "len": 1, "field": "atcs.send_sequence",
         "value": sseq, "synthetic": False, "confidence": "spec"},
        {"off": 3, "len": 1, "field": "atcs.receive_sequence",
         "value": rseq, "synthetic": False, "confidence": "spec"},
        {"off": 4, "len": 1, "field": "atcs.addr_len",
         "value": {"src_digits": len(src_addr), "dst_digits": len(dst_addr)},
         "synthetic": False, "confidence": "spec"},
    ]
    return header, fields


# RF-header address-type octet [0]. 0x23 (renders as '#' in ATCSMon's ASCII
# gutter — which is why it looked like a start flag) is the ground-datagram type
# on the To-Dispatch corpus (A1/A3-A7); 0xFF broadcast and 0x00 CC_ID also occur.
ATCS_RF_ADDRTYPE_GROUND = 0x23

# RF-header length field. ATCSMon reconstructs the expected frame length from
# the RF header's Reed-Solomon block_count + pad_bits and REJECTS any frame whose
# byte count doesn't match ("Invalid ATCS Packet Length" — confirmed live: a
# frame with a 1-block-off pad_bits is thrown out). Each RS block carries 60
# frame-bits, so:
#     block_count = ceil(8 * total_len / 60)  = ceil(2 * total_len / 15)
#     pad_bits    = 60 * block_count - 8 * total_len          (always 0..59)
# Recovered by fitting 8 real corpus frames (32/37/38/42/56/76/109/151 bytes),
# which the formula reproduces EXACTLY, and confirmed against a live ATCS
# Monitor 4.1.0 decoder (both replayed-real and generated frames decode with no
# length error once these bytes are formula-correct).
# Corpus check: {32:(44,5), 37:(4,5), 38:(56,6), 42:(24,6), 56:(32,8),
#                76:(52,11), 109:(28,15), 151:(52,21)}  as (pad_bits, block_count).
def _rf_length_fields(total_len: int) -> tuple[int, int]:
    """(pad_bits, block_count) that ATCSMon accepts for a ``total_len``-byte frame."""
    block_count = -(-8 * total_len // 60)          # ceil(8*total_len / 60)
    pad_bits = 60 * block_count - 8 * total_len     # 0..59
    return pad_bits, block_count


def build_rf_header(
    total_frame_len: int,
    *,
    address_type: int = ATCS_RF_ADDRTYPE_GROUND,
    pad_bits: int | None = None,
    block_count: int | None = None,
) -> tuple[bytes, list[dict]]:
    """ATCS 5-octet RF header (+ header CRC) — VERIFIED against the relay corpus.

    Layout (frame bytes [0..4])::

        0     RF address type       0x23 ground / 0xFF broadcast / 0x00 CC_ID
        1     # pad bits in last RS block
        2     # of Reed-Solomon blocks    (the RF "length" field)
        3..4  header CRC-16/X.25 over [0..2], little-endian

    ``total_frame_len`` (RF header + datagram + datagram CRC) selects
    corpus-grounded ``pad_bits``/``block_count`` unless given explicitly.
    """
    pb, bc = _rf_length_fields(total_frame_len)
    if pad_bits is None:
        pad_bits = pb
    if block_count is None:
        block_count = bc
    head3 = bytes([address_type & 0xFF, pad_bits & 0xFF, block_count & 0xFF])
    hcrc = crc16_x25(head3)
    header = head3 + bytes([hcrc & 0xFF, (hcrc >> 8) & 0xFF])
    fields = [
        {"off": 0, "len": 1, "field": "relay.rf_address_type",
         "value": address_type, "synthetic": False, "confidence": "spec"},
        {"off": 1, "len": 1, "field": "relay.rf_pad_bits",
         "value": pad_bits, "synthetic": False, "confidence": "spec"},
        {"off": 2, "len": 1, "field": "relay.rf_block_count",
         "value": block_count, "synthetic": False, "confidence": "spec",
         "note": "RF length field: # Reed-Solomon blocks (corpus-grounded)"},
        {"off": 3, "len": 2, "field": "relay.rf_header_crc",
         "value": hcrc, "synthetic": False, "confidence": "spec",
         "note": "CRC-16/X.25 over [0..2], little-endian"},
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
    gfi: int = ATCS_GFI_DEFAULT,
    group: int = ATCS_GROUP_INDICATION,
    message_number: int = 0,
    part_number: int = 0,
    label: int = 0,
    address_type: int = ATCS_RF_ADDRTYPE_GROUND,
    pad_bits: int | None = None,
    block_count: int | None = None,
) -> tuple[bytes, list[dict]]:
    """Build an ATCS relay-feed frame (as ATCSMon parses it) + field map.

    Layout is VERIFIED against a corpus of real ATCSMon-decoded frames — every
    corpus frame round-trips to ATCSMon's reported GFI/Group/SSeq/RSeq/addresses/
    UsrData, and both CRC-16/X.25 fields reproduce exactly::

        RF header (5B)                      [spec]
          [0]     RF address type           0x23 ground datagram
          [1]     # pad bits in last RS block
          [2]     # of Reed-Solomon blocks  (the RF length field)
          [3..4]  header CRC-16/X.25 over [0..2], little-endian
        --- datagram (bytes [5:-2], covered by the datagram CRC) ---
        network header (5B)                 [spec]
          [5]     (GFI << 4) | Group
          [6]     spare
          [7]     send sequence << 1
          [8]     receive sequence << 1
          [9]     source_length << 4 | destination_length
        destination ATCS address (BCD)      [spec]  destination FIRST
        source ATCS address (BCD)           [spec]
        facility length (1B)                [spec]
        transport header (5B)               [spec_legacy]  (Spec 250, synthetic values)
        UsrData (NB)                        [synthetic]
        vital CRC (4B)                      [spec_legacy]  present when vital=1
        --- end datagram ---
        datagram CRC (2B)                   [spec]  CRC-16/X.25 over [5:-2], LE

    ATCSMon derives UsrData length from the received byte count minus the fixed
    overhead, so the transport header's message-number is free: unknown numbers
    display as "Unknown Message Function" and still pass the length gate. The
    31-bit K-II vital CRC (verified against 01 02 -> 25 ED BD 70) is an inner,
    L7-region field carried before the datagram CRC when ``vital`` is set; its
    exact placement in a real vital frame is unconfirmed (corpus is all Vital=0),
    hence its ``spec_legacy`` tier.
    """
    src_bcd = encode_bcd_address(src_addr)
    dst_bcd = encode_bcd_address(dst_addr)
    net_hdr, net_fields = build_network_header(
        src_addr, dst_addr, sseq, rseq, gfi=gfi, group=group,
    )
    tx_hdr, tx_fields = build_transport_header(
        len(usrdata), message_number=message_number, part_number=part_number,
        vital=vital, label=label,
    )

    # Datagram = frame bytes [5:-2] (GFI octet through end of L7 data).
    dgram = bytearray()
    dgram += net_hdr
    vcrc_start = 4                         # addr-length octet, within the datagram
    dgram += dst_bcd                       # destination address FIRST
    dgram += src_bcd
    dgram.append(0x00)                     # facility length (no facility emitted)
    dgram += tx_hdr
    ud_off_in_dgram = len(dgram)
    dgram += usrdata
    if vital:
        dgram += vital_crc_bytes(bytes(dgram[vcrc_start:]))

    dcrc = crc16_x25(bytes(dgram))
    dgram_crc = bytes([dcrc & 0xFF, (dcrc >> 8) & 0xFF])
    total_len = 5 + len(dgram) + 2
    rf_hdr, rf_fields = build_rf_header(
        total_len, address_type=address_type, pad_bits=pad_bits, block_count=block_count,
    )

    frame = bytes(rf_hdr) + bytes(dgram) + dgram_crc

    base = len(rf_hdr)                     # datagram fields start at frame offset 5
    fields: list[dict] = list(rf_fields)
    for f in net_fields:
        fields.append({**f, "off": base + f["off"]})
    dst_off = base + len(net_hdr)
    fields.append({"off": dst_off, "len": len(dst_bcd), "field": "atcs.dst_addr",
                   "value": dst_addr, "subfields": atcs_address_subfields(dst_addr),
                   "synthetic": False, "confidence": "spec"})
    src_off = dst_off + len(dst_bcd)
    fields.append({"off": src_off, "len": len(src_bcd), "field": "atcs.src_addr",
                   "value": src_addr, "subfields": atcs_address_subfields(src_addr),
                   "synthetic": False, "confidence": "spec"})
    fac_off = src_off + len(src_bcd)
    fields.append({"off": fac_off, "len": 1, "field": "atcs.facility_len",
                   "value": 0, "synthetic": False, "confidence": "spec"})
    tx_off = fac_off + 1
    for f in tx_fields:
        fields.append({**f, "off": tx_off + f["off"]})
    ud_off = base + ud_off_in_dgram
    fields.append({"off": ud_off, "len": len(usrdata), "field": "atcs.usrdata",
                   "value": usrdata.hex(), "synthetic": True, "confidence": "synthetic"})
    if vital:
        fields.append({"off": ud_off + len(usrdata), "len": 4, "field": "atcs.vital_crc",
                       "value": "crc31", "synthetic": False, "confidence": "spec_legacy",
                       "note": "31-bit CRC, K-II; covers addr-len octet .. end of L7 data"})
    fields.append({"off": 5 + len(dgram), "len": 2, "field": "atcs.datagram_crc",
                   "value": dcrc, "synthetic": False, "confidence": "spec",
                   "note": "CRC-16/X.25 over datagram [5:-2], little-endian"})
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
