# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""ATCS (Advanced Train Control System) codeline frame building — AAR Spec 200.

ATCS is a legacy radio-code-line train-control system. Its native transport is
a 900 MHz FSK radio link, NOT IP — Layer 2 is X.25 LAPB for ground users and
HDLC balanced procedure for mobile/wayside users (AAR Spec 200). The only
IP-observable form of ATCS is the **ATCS Monitor relay** (see ``engine.py``),
which streams decoded codeline frames as ASCII-hex over UDP. This module builds
the inner codeline frame that rides inside that relay feed.

FIDELITY — three confidence tiers, carried per-field in the label map so a
downstream Cyber Vision dissector-training pipeline knows which bytes to trust
(CV has no rail DPI today; this generates labeled corpora to build one):

- ``spec``        — derivable to byte accuracy from public standards:
                    HDLC framing (0x7E flags), the 10-BCD-digit ATCS address
                    encoding, and the FCS (CRC-16/X.25). These are the ITU-T
                    X.25/HDLC standard and the confirmed ATCS address format.
- ``provisional`` — the exact bit-packing of the X.25-derived network header
                    fields (GFI, Group, SSeq, RSeq, Beacon, Vital) is defined by
                    AAR Spec 200 (paywalled) / the ATCSMon "RF Codeline Protocol
                    Reference" wiki (DNS-down at build time). The layout in
                    ``_build_network_header`` reproduces the known sample-frame
                    field *values* but its byte positions are RECONSTRUCTED and
                    must be certified against Spec 200 before this is called
                    byte-authoritative. It is isolated in one function for exactly
                    that correction.
- ``synthetic``   — UsrData payload content. Per-territory codeline bit semantics
                    live in private railroad ``.mcp`` databases; the bytes here
                    are plausible but invented.

Reference sample frame (sigidwiki), reproduced by this builder's field values::

    Wayside 5125013826  Frame=34 GFI=2 Group=5 SSeq=77 RSeq=45
    Beacon=0 Vital=0  UsrData=02 04 05 00 00 00
"""

from __future__ import annotations

import struct

ATCS_FLAG = 0x7E                 # HDLC opening/closing flag (spec)
ATCS_LAPB_ADDR = 0x03            # LAPB command address, ground users (spec-typical)

# ATCS address Type digit (first of the 10 BCD digits).
ATCS_TYPE_LOCOMOTIVE = 1
ATCS_TYPE_OFFICE = 2
ATCS_TYPE_BASE = 3
ATCS_TYPE_WAYSIDE = 5            # 5/7 seen for wayside/MCP
ATCS_TYPE_NAMES = {
    1: "locomotive",
    2: "office",
    3: "base_station",
    5: "wayside",
    7: "wayside",
}


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


def build_atcs_address(type_digit: int, railroad: int, codeline: int, serial: int) -> str:
    """Compose a 10-digit ATCS address string: Type(1) Railroad(3) Codeline(3) Serial(3).

    e.g. ``build_atcs_address(5, 125, 13, 826) -> "5125013826"`` (the sample
    wayside device). A separate 4-digit eXtension may follow in real addressing;
    it is out of scope for the base MCP address modelled here.
    """
    if not 0 <= type_digit <= 9:
        raise ValueError("type_digit must be a single digit")
    for name, val in (("railroad", railroad), ("codeline", codeline), ("serial", serial)):
        if not 0 <= val <= 999:
            raise ValueError(f"{name} must be 0-999 (3 digits)")
    return f"{type_digit:01d}{railroad:03d}{codeline:03d}{serial:03d}"


def encode_bcd_address(addr10: str) -> bytes:
    """Pack a 10-digit ATCS address into 5 BCD bytes (high nibble = first digit)."""
    if len(addr10) != 10 or not addr10.isdigit():
        raise ValueError("ATCS address must be exactly 10 decimal digits")
    return bytes(
        (int(addr10[i]) << 4) | int(addr10[i + 1]) for i in range(0, 10, 2)
    )


def decode_bcd_address(b: bytes) -> str:
    """Inverse of :func:`encode_bcd_address` (used by tests)."""
    return "".join(f"{(x >> 4) & 0xF}{x & 0xF}" for x in b)


def _build_network_header(
    gfi: int, group: int, sseq: int, beacon: bool, rseq: int, vital: bool,
) -> tuple[bytes, list[dict]]:
    """X.25-derived ATCS network header — PROVISIONAL bit-packing.

    Reproduces the confirmed field set (GFI, Group, SSeq, RSeq, Beacon, Vital)
    with the sample frame's value ranges (SSeq/RSeq are modulo-128, matching the
    sample's 77/45). Byte positions are RECONSTRUCTED, not certified — see the
    module docstring. Correct this one function against AAR Spec 200 to make the
    header byte-authoritative.

    Layout (provisional)::

        byte 0: GFI (bits 7-4) | Group (bits 3-0)
        byte 1: SSeq (bits 7-1) | Beacon (bit 0)
        byte 2: RSeq (bits 7-1) | Vital (bit 0)
    """
    b0 = ((gfi & 0x0F) << 4) | (group & 0x0F)
    b1 = ((sseq & 0x7F) << 1) | (1 if beacon else 0)
    b2 = ((rseq & 0x7F) << 1) | (1 if vital else 0)
    header = bytes([b0, b1, b2])
    fields = [
        {"off": 0, "len": 1, "field": "atcs.gfi_group",
         "value": {"gfi": gfi, "group": group}, "synthetic": False, "confidence": "provisional"},
        {"off": 1, "len": 1, "field": "atcs.sseq_beacon",
         "value": {"sseq": sseq, "beacon": int(beacon)}, "synthetic": False, "confidence": "provisional"},
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
    beacon: bool = False,
    vital: bool = False,
    frame_counter: int = 0,
) -> tuple[bytes, list[dict]]:
    """Build a complete ATCS codeline (HDLC) frame and its ground-truth field map.

    Frame structure::

        0x7E                 flag                     (spec)
        LAPB address (1B)                             (spec-typical)
        LAPB control (1B)    frame counter / I-frame  (provisional)
        --- X.25 network header (3B) ---              (provisional bit-packing)
        GFI|Group | SSeq|Beacon | RSeq|Vital
        src ATCS addr (5B BCD)                        (spec encoding)
        dst ATCS addr (5B BCD)                        (spec encoding)
        UsrData length (1B)                           (provisional)
        UsrData (NB)                                  (synthetic)
        --- ---
        FCS-16 (2B, little-endian)                    (spec algorithm, CRC-16/X.25)
        0x7E                 flag                     (spec)

    Returns ``(frame_bytes, field_map)``. Offsets in the field map are absolute
    within ``frame_bytes``. No HDLC bit-stuffing is applied: the ATCS Monitor
    relay delivers de-stuffed logical frames, which is what this represents.
    """
    src_bcd = encode_bcd_address(src_addr)
    dst_bcd = encode_bcd_address(dst_addr)
    net_hdr, net_fields = _build_network_header(gfi, group, sseq, beacon, rseq, vital)

    # LAPB control byte carries an I-frame send counter (provisional mapping of
    # the sample's "Frame=NN").
    lapb_control = (frame_counter & 0x7F) << 1

    body = bytearray()
    body.append(ATCS_LAPB_ADDR)
    body.append(lapb_control)
    body += net_hdr
    body += src_bcd
    body += dst_bcd
    body.append(len(usrdata) & 0xFF)
    body += usrdata
    fcs = crc16_x25(bytes(body))

    frame = bytearray()
    frame.append(ATCS_FLAG)
    frame += body
    frame += struct.pack("<H", fcs)          # FCS little-endian
    frame.append(ATCS_FLAG)

    # Build the absolute-offset field map. body starts at offset 1 (after flag).
    base = 1
    fields: list[dict] = [
        {"off": 0, "len": 1, "field": "atcs.flag_open", "value": 0x7E, "synthetic": False, "confidence": "spec"},
        {"off": base, "len": 1, "field": "atcs.lapb_address", "value": ATCS_LAPB_ADDR, "synthetic": False, "confidence": "spec"},
        {"off": base + 1, "len": 1, "field": "atcs.lapb_control", "value": frame_counter, "synthetic": False, "confidence": "provisional"},
    ]
    for f in net_fields:
        fields.append({**f, "off": base + 2 + f["off"]})
    addr_off = base + 2 + len(net_hdr)
    fields.append({"off": addr_off, "len": 5, "field": "atcs.src_addr",
                   "value": src_addr, "synthetic": False, "confidence": "spec"})
    fields.append({"off": addr_off + 5, "len": 5, "field": "atcs.dst_addr",
                   "value": dst_addr, "synthetic": False, "confidence": "spec"})
    len_off = addr_off + 10
    fields.append({"off": len_off, "len": 1, "field": "atcs.usrdata_len",
                   "value": len(usrdata), "synthetic": False, "confidence": "provisional"})
    fields.append({"off": len_off + 1, "len": len(usrdata), "field": "atcs.usrdata",
                   "value": usrdata.hex(), "synthetic": True, "confidence": "synthetic"})
    fcs_off = len_off + 1 + len(usrdata)
    fields.append({"off": fcs_off, "len": 2, "field": "atcs.fcs16",
                   "value": fcs, "synthetic": False, "confidence": "spec"})
    fields.append({"off": fcs_off + 2, "len": 1, "field": "atcs.flag_close",
                   "value": 0x7E, "synthetic": False, "confidence": "spec"})
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
