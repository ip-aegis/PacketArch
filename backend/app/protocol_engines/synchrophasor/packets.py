# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IEEE C37.118.2-2011 synchrophasor frame builders.

All builders are pure: given input bytes/numbers, they produce
output bytes — no side effects, no logging. Frames are returned
as the raw C37.118 PDU; wrap them in TCP/IP via the engine.

Common Frame Header (14 bytes, big-endian):
    SYNC       u16   0xAA + (type<<4 | version)
    FRAMESIZE  u16   total frame length including 2-byte CRC trailer
    IDCODE     u16   stream identifier
    SOC        u32   UNIX epoch seconds
    FRACSEC    u32   [time_quality:8][fraction:24]   fraction/time_base = seconds

The frame body follows the header. The frame ends with a 2-byte
CRC-CCITT (poly 0x1021, init 0xFFFF, no final XOR) computed over
everything up to (but not including) the CRC field.
"""

from __future__ import annotations

import struct

from app.protocol_engines.synchrophasor.types import (
    C37118Identity,
    FRAME_SYNC,
    FrameType,
)

# Header / footer sizes
HEADER_LEN = 14   # SYNC+FRAMESIZE+IDCODE+SOC+FRACSEC
CRC_LEN = 2


def crc_ccitt(data: bytes) -> int:
    """Compute CRC-CCITT (poly 0x1021, init 0xFFFF, no final XOR).

    This is the CRC variant specified in C37.118.2-2011 Annex B.
    """
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _pad_station_name(name: str) -> bytes:
    """ASCII-encode and right-pad a station name to 16 bytes."""
    raw = name.encode("ascii", errors="replace")[:16]
    return raw.ljust(16, b" ")


def _build_header(
    frame_type: FrameType,
    framesize: int,
    idcode: int,
    soc: int,
    fracsec: int,
) -> bytes:
    """Build the 14-byte common frame header.

    The full framesize (including the trailing CRC) must be known
    at header-build time, since FRAMESIZE counts the entire frame.
    """
    sync = FRAME_SYNC[frame_type]
    return struct.pack(
        ">HHHII",
        sync,
        framesize & 0xFFFF,
        idcode & 0xFFFF,
        soc & 0xFFFFFFFF,
        fracsec & 0xFFFFFFFF,
    )


def _finalize(frame_type: FrameType, idcode: int, soc: int, fracsec: int, body: bytes) -> bytes:
    """Prefix the common header and append CRC-CCITT trailer."""
    framesize = HEADER_LEN + len(body) + CRC_LEN
    header = _build_header(frame_type, framesize, idcode, soc, fracsec)
    pre_crc = header + body
    crc = crc_ccitt(pre_crc)
    return pre_crc + struct.pack(">H", crc)


def build_command_frame(
    idcode: int,
    cmd: int,
    soc: int,
    fracsec: int = 0,
    extended_data: bytes = b"",
) -> bytes:
    """Build a COMMAND frame (PDC -> PMU).

    Body layout: CMD(2) [+ extended_data]. Total frame length is
    14(header) + 2(cmd) + N(ext) + 2(crc).
    """
    body = struct.pack(">H", cmd & 0xFFFF) + extended_data
    return _finalize(FrameType.COMMAND, idcode, soc, fracsec, body)


def build_cfg2_frame(identity: C37118Identity, soc: int, fracsec: int = 0) -> bytes:
    """Build a Configuration-2 frame describing one PMU.

    CFG-2 body layout (single PMU):
        TIME_BASE   u32   (high byte reserved=0, low 24 bits = divisor)
        NUM_PMU     u16   = 1
        --- per-PMU block ---
        STN         16 bytes  ASCII station name, space-padded
        IDCODE      u16
        FORMAT      u16   phasor/analog/freq format flags
        PHNMR       u16   number of phasors
        ANNMR       u16   number of analogs
        DGNMR       u16   number of digital status words
        CHNAM       (PHNMR + ANNMR + 16*DGNMR) * 16 bytes
        PHUNIT      u32 * PHNMR
        ANUNIT      u32 * ANNMR
        DIGUNIT     u32 * DGNMR
        FNOM        u16   0=60Hz, 1=50Hz
        CFGCNT      u16
        --- end per-PMU block ---
        DATA_RATE   i16   frames/sec (>0) or -seconds/frame (<0)
    """
    body = bytearray()

    # TIME_BASE: top byte is reserved/flags, low 24 bits is divisor.
    body += struct.pack(">I", identity.time_base & 0x00FFFFFF)

    # NUM_PMU
    body += struct.pack(">H", 1)

    # --- per-PMU block ---
    body += _pad_station_name(identity.station_name)
    body += struct.pack(">H", identity.idcode & 0xFFFF)
    body += struct.pack(">H", identity.format_flags & 0xFFFF)

    phnmr = max(0, identity.num_phasors)
    annmr = max(0, identity.num_analog)
    dgnmr = max(0, identity.num_digital)
    body += struct.pack(">HHH", phnmr, annmr, dgnmr)

    # CHNAM — concatenated 16-byte ASCII names for each phasor, analog,
    # and 16 digital channels per digital word.
    expected_names = phnmr + annmr + 16 * dgnmr
    names = list(identity.channel_names)
    if len(names) < expected_names:
        # Auto-generate any missing channel names.
        for i in range(phnmr):
            if i >= len(names):
                names.append(f"VA_PH{i + 1}")
        for i in range(annmr):
            idx = phnmr + i
            if idx >= len(names):
                names.append(f"ANALOG{i + 1}")
        for i in range(16 * dgnmr):
            idx = phnmr + annmr + i
            if idx >= len(names):
                names.append(f"D{(i // 16) + 1}_{i % 16:02d}")
    for n in names[:expected_names]:
        body += _pad_station_name(n)

    # PHUNIT — one u32 per phasor. High byte: 0=voltage, 1=current.
    # Low 24 bits: conversion factor (10^-5 V or A per LSB).
    for i in range(phnmr):
        kind = 0 if (i % 2 == 0) else 1  # alternate V / I
        body += struct.pack(">I", (kind << 24) | 915527)  # ~1V/LSB scale

    # ANUNIT — one u32 per analog. High byte: 0=single point, 1=RMS, 2=peak.
    for _ in range(annmr):
        body += struct.pack(">I", (0 << 24) | 1)

    # DIGUNIT — one u32 per digital word: high u16 = "normal" mask,
    # low u16 = "valid bit" mask.
    for _ in range(dgnmr):
        body += struct.pack(">I", 0x0000FFFF)

    # FNOM + CFGCNT
    body += struct.pack(">H", identity.fnom_code() & 0xFFFF)
    body += struct.pack(">H", identity.config_count & 0xFFFF)

    # DATA_RATE — signed 16-bit, frames/sec
    body += struct.pack(">h", identity.data_rate)

    return _finalize(FrameType.CONFIG_2, identity.idcode, soc, fracsec, bytes(body))


def build_data_frame(
    identity: C37118Identity,
    soc: int,
    fracsec: int,
    phasors: list[tuple[int, int]] | None = None,
    freq: int = 0,
    dfreq: int = 0,
    analogs: list[int] | None = None,
    digitals: list[int] | None = None,
    stat: int = 0x0000,
) -> bytes:
    """Build a DATA frame for one PMU's measurement sample.

    This implementation assumes the FORMAT default (integer
    rectangular phasors, int16 freq/dfreq, int16 analogs) — the
    16-bit-per-component variant most common in field deployments.

    DATA body for one PMU:
        STAT     u16
        PHASORS  (i16 real, i16 imag) * PHNMR
        FREQ     i16   deviation from FNOM in mHz
        DFREQ    i16   ROCOF in 0.01 Hz/s
        ANALOG   i16 * ANNMR
        DIGITAL  u16 * DGNMR
    """
    body = bytearray()
    body += struct.pack(">H", stat & 0xFFFF)

    # Phasors (rectangular int16). Pad/truncate to PHNMR.
    phasors = phasors or []
    for i in range(identity.num_phasors):
        if i < len(phasors):
            re, im = phasors[i]
        else:
            re, im = 0, 0
        body += struct.pack(">hh", _clamp16(re), _clamp16(im))

    # FREQ / DFREQ (int16). Both are deviations, not absolute values.
    body += struct.pack(">hh", _clamp16(freq), _clamp16(dfreq))

    # Analogs (int16)
    analogs = analogs or []
    for i in range(identity.num_analog):
        v = analogs[i] if i < len(analogs) else 0
        body += struct.pack(">h", _clamp16(v))

    # Digital status words (u16)
    digitals = digitals or []
    for i in range(identity.num_digital):
        v = digitals[i] if i < len(digitals) else 0
        body += struct.pack(">H", v & 0xFFFF)

    return _finalize(FrameType.DATA, identity.idcode, soc, fracsec, bytes(body))


def build_header_frame(
    idcode: int,
    soc: int,
    fracsec: int,
    text: str,
) -> bytes:
    """Build a HEADER frame carrying free-form ASCII metadata."""
    body = text.encode("ascii", errors="replace")
    return _finalize(FrameType.HEADER, idcode, soc, fracsec, body)


def _clamp16(v: int) -> int:
    """Clamp an int to signed 16-bit range."""
    if v > 32767:
        return 32767
    if v < -32768:
        return -32768
    return v


def build_c37118_identity(config: dict | None) -> C37118Identity:
    """Construct a C37118Identity from a device template's
    ``c37118_identity`` config dict (or sensible defaults).
    """
    cfg = config or {}
    return C37118Identity(
        station_name=str(cfg.get("station_name", "PMU01")),
        idcode=int(cfg.get("idcode", 1)) & 0xFFFF,
        data_rate=int(cfg.get("data_rate", 30)),
        fnom=int(cfg.get("fnom", 60)),
        config_count=int(cfg.get("config_count", 1)) & 0xFFFF,
        time_base=int(cfg.get("time_base", 1_000_000)) & 0x00FFFFFF,
        num_phasors=int(cfg.get("num_phasors", 1)),
        num_analog=int(cfg.get("num_analog", 0)),
        num_digital=int(cfg.get("num_digital", 0)),
        channel_names=list(cfg.get("channel_names", [])),
        format_flags=int(cfg.get("format_flags", 0x0000)) & 0xFFFF,
    )
