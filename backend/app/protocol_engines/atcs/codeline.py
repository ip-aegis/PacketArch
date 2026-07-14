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

Frame model (decoded RF logical frame)::

    radio-link frame counter (1B)        Appendix L   — the ATCSMon "Frame=NN"
    radio datagram header (3B)           Appendix G   — GFI/Group, SSeq, RSeq/Vital
    address-length octet (1B)            Appendix D   — src digits (hi nibble) | dst (lo)
    destination ATCS address (BCD)       Appendix D   — destination FIRST
    source ATCS address (BCD)            Appendix D
    packet label / UsrData length (1B)   Spec 250
    UsrData (NB)                         Spec 250     — application payload
    FCS-16 (2B, CRC-16/X.25)             Layer 2      — on every message
    vital CRC (4B)                       Appendix Y   — vital messages ONLY (32-bit)

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


def vital_crc32(data: bytes) -> int:
    """32-bit vital/presentation CRC appended to VITAL messages (last 4 octets).

    Per K-II, vital messages carry additional (Layer 4 / Layer 6) redundancy
    checks beyond the Layer-2 FCS; the vital CRC is 32 bits. The exact
    polynomial and bit/byte order are defined in ATCS Spec 250 §3.2.1.1, which
    was not reachable from the build host — so the CRC's PRESENCE and 4-octet
    POSITION are spec-derived but its VALUE (computed here as a standard CRC-32)
    is provisional until the Spec 250 polynomial is confirmed. See SPEC_NEEDS.md.
    """
    return crc32(data) & 0xFFFFFFFF


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


def encode_bcd_address(addr: str) -> bytes:
    """Pack a 10- or 14-digit ATCS address into BCD bytes (high nibble first).

    On-wire encoding is modelled as packed BCD (2 digits/byte); AAR Spec 200
    defines the authoritative encoding.
    """
    if len(addr) not in (10, 14) or not addr.isdigit():
        raise ValueError("ATCS address must be 10 (5-series) or 14 (7-series) digits")
    return bytes(
        (int(addr[i]) << 4) | int(addr[i + 1]) for i in range(0, len(addr), 2)
    )


def decode_bcd_address(b: bytes) -> str:
    """Inverse of :func:`encode_bcd_address` (used by tests)."""
    return "".join(f"{(x >> 4) & 0xF}{x & 0xF}" for x in b)


def _build_radio_datagram_header(
    gfi: int, group: int, sseq: int, rseq: int, vital: bool,
) -> tuple[bytes, list[dict]]:
    """ATCS radio-datagram (Appendix G, Layer 3) header — PROVISIONAL bit-packing.

    Reproduces the confirmed field set (GFI, Group, SSeq, RSeq, datagram Vital
    flag) with the sample frame's value ranges (SSeq/RSeq modulo-128, matching
    the sample's 77/45). The exact bit widths/positions live in K-II Appendix G
    (~K-II-57) which was not reachable from the build host — so byte positions
    are best-effort. Correct THIS function once Appendix G is read.

    Layout (provisional)::

        byte 0: GFI (bits 7-4) | Group (bits 3-0)   [X.25-derived: 4-bit GFI + 4-bit group]
        byte 1: SSeq (bits 7-1) | flag (bit 0)
        byte 2: RSeq (bits 7-1) | datagram Vital (bit 0)
    """
    b0 = ((gfi & 0x0F) << 4) | (group & 0x0F)
    b1 = ((sseq & 0x7F) << 1)
    b2 = ((rseq & 0x7F) << 1) | (1 if vital else 0)
    header = bytes([b0, b1, b2])
    fields = [
        {"off": 0, "len": 1, "field": "atcs.gfi_group",
         "value": {"gfi": gfi, "group": group}, "synthetic": False, "confidence": "provisional"},
        {"off": 1, "len": 1, "field": "atcs.sseq",
         "value": {"sseq": sseq}, "synthetic": False, "confidence": "provisional"},
        {"off": 2, "len": 1, "field": "atcs.rseq_vital",
         "value": {"rseq": rseq, "vital": int(vital)}, "synthetic": False, "confidence": "provisional"},
    ]
    return header, fields


def build_codeline_frame(
    src_addr: str,
    dst_addr: str,
    usrdata: bytes,
    *,
    gfi: int = 2,
    group: int = 5,
    sseq: int = 0,
    rseq: int = 0,
    vital: bool = False,
    transport_vital: bool = False,
    frame_counter: int = 0,
) -> tuple[bytes, list[dict]]:
    """Build a decoded ATCS RF codeline frame (relay-feed form) + field map.

    This models the RF path the ATCS Monitor relay decodes (radio datagram over
    radio link), NOT the wireline LAPB path — so there is no LAPB address/control
    byte and no HDLC 0x7E flags (those are wireline artifacts). See the module
    docstring for the layer references and confidence tiers.

    Frame model::

        radio-link frame counter (1B)         Appendix L   (provisional)
        radio datagram header (3B)            Appendix G   (provisional widths)
        address-length octet (1B)             Appendix D   src digits<<4 | dst digits
        destination ATCS address (BCD)        Appendix D   (spec; destination FIRST)
        source ATCS address (BCD)             Appendix D   (spec)
        packet label / UsrData length (1B)    Spec 250     (provisional)
        UsrData (NB)                          Spec 250     (synthetic)
        FCS-16 (2B, CRC-16/X.25, LE)          Layer 2      (spec algorithm)
        vital CRC (4B)                        Appendix Y   (vital msgs only; value provisional)

    ``vital`` sets the radio-datagram Vital flag AND triggers the trailing 32-bit
    vital CRC. ``transport_vital`` is the separate transport-layer vital bit
    (Appendix D §2.11), carried in the packet-label octet. Returns
    ``(frame_bytes, field_map)`` with absolute offsets.
    """
    src_bcd = encode_bcd_address(src_addr)
    dst_bcd = encode_bcd_address(dst_addr)
    dgram_hdr, dgram_fields = _build_radio_datagram_header(gfi, group, sseq, rseq, vital)

    # Address-length octet: source digit count (high nibble) | dest digit count
    # (low nibble), in units of BCD digits (Appendix D §2.3-2.4).
    addr_len_octet = ((len(src_addr) & 0x0F) << 4) | (len(dst_addr) & 0x0F)
    # Packet label / UsrData length octet (Spec 250). Bit 0 carries the transport
    # vital bit (Appendix D §2.11); the remaining bits are the user-data length.
    packet_label = ((len(usrdata) & 0x7F) << 1) | (1 if transport_vital else 0)

    body = bytearray()
    body.append(frame_counter & 0xFF)          # radio-link frame counter
    body += dgram_hdr                           # radio datagram header
    body.append(addr_len_octet)
    body += dst_bcd                             # destination FIRST
    body += src_bcd
    body.append(packet_label)
    body += usrdata
    fcs = crc16_x25(bytes(body))

    frame = bytearray(body)
    frame += struct.pack("<H", fcs)             # 16-bit FCS, little-endian
    if vital:
        frame += struct.pack(">I", vital_crc32(bytes(frame)))  # 32-bit vital CRC

    # Absolute-offset field map.
    fields: list[dict] = [
        {"off": 0, "len": 1, "field": "atcs.frame_counter",
         "value": frame_counter, "synthetic": False, "confidence": "provisional"},
    ]
    for f in dgram_fields:
        fields.append({**f, "off": 1 + f["off"]})
    alo = 1 + len(dgram_hdr)
    fields.append({"off": alo, "len": 1, "field": "atcs.addr_len",
                   "value": {"src_digits": len(src_addr), "dst_digits": len(dst_addr)},
                   "synthetic": False, "confidence": "spec"})
    dst_off = alo + 1
    fields.append({"off": dst_off, "len": len(dst_bcd), "field": "atcs.dst_addr",
                   "value": dst_addr, "subfields": atcs_address_subfields(dst_addr),
                   "synthetic": False, "confidence": "spec"})
    src_off = dst_off + len(dst_bcd)
    fields.append({"off": src_off, "len": len(src_bcd), "field": "atcs.src_addr",
                   "value": src_addr, "subfields": atcs_address_subfields(src_addr),
                   "synthetic": False, "confidence": "spec"})
    label_off = src_off + len(src_bcd)
    fields.append({"off": label_off, "len": 1, "field": "atcs.packet_label",
                   "value": {"usrdata_len": len(usrdata), "transport_vital": int(transport_vital)},
                   "synthetic": False, "confidence": "provisional"})
    ud_off = label_off + 1
    fields.append({"off": ud_off, "len": len(usrdata), "field": "atcs.usrdata",
                   "value": usrdata.hex(), "synthetic": True, "confidence": "synthetic"})
    fcs_off = ud_off + len(usrdata)
    fields.append({"off": fcs_off, "len": 2, "field": "atcs.fcs16",
                   "value": fcs, "synthetic": False, "confidence": "spec"})
    if vital:
        fields.append({"off": fcs_off + 2, "len": 4, "field": "atcs.vital_crc32",
                       "value": "crc32", "synthetic": False, "confidence": "provisional"})
    return bytes(frame), fields


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
