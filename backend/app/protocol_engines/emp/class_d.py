# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Class D messaging layer (AAR S-9356) — the transport that carries EMP.

The Interoperable Train Control stack is::

    ITC application message
      └─ EMP envelope            (AAR S-9354)
          └─ Class D message     (AAR S-9356)   <- this module
              └─ TCP
                  └─ IPv4

Class D is MANDATORY: EMP never rides bare on TCP. Every Class D message frames
the payload with a fixed 12-octet header and a trailing ETX, all multi-octet
header values big-endian::

    off  size  field
    0    1     STX               = 0x02
    1    1     protocol_version  = 0x02
    2    4     COMMID            uint32
    6    1     message_type      (1 = Data)
    7    1     message_version   = 0x02
    8    4     data_length       = len(body), uint32
    12   N     message_body      (for Data: the complete EMP envelope)
    12+N 1     ETX               = 0x03

So ``len(class_d) == len(body) + 13`` and, for a Data message, EMP begins at
TCP-payload offset 12.

COMMID starts at 1, increments independently per link, and rolls from
0xFFFFFFFF back to 1 (never 0).

Confidence: ``spec_legacy`` — sourced from the publicly available 2010 S-9356
DRAFT, not a purchased final revision. The layering (EMP carried through Class D
over TCP/IP) is independently corroborated by Meteorcomm patent US10160466B1.
"""

from __future__ import annotations

import struct

CLASS_D_STX = 0x02
CLASS_D_ETX = 0x03
CLASS_D_PROTOCOL_VERSION = 0x02
CLASS_D_MESSAGE_VERSION = 0x02
CLASS_D_HEADER_LEN = 12
CLASS_D_OVERHEAD = CLASS_D_HEADER_LEN + 1  # + ETX

# Message types (S-9356)
CLASS_D_DATA = 1
CLASS_D_ACK = 2
CLASS_D_NAK = 3
CLASS_D_KEEPALIVE = 4
CLASS_D_CONFORMANCE_TEST = 30
CLASS_D_TEST_ECHO_REQUEST = 31
CLASS_D_TEST_ECHO_RESPONSE = 32
CLASS_D_OP_ECHO_REQUEST = 40
CLASS_D_OP_ECHO_RESPONSE = 41

CLASS_D_TYPE_NAMES = {
    CLASS_D_DATA: "data",
    CLASS_D_ACK: "ack",
    CLASS_D_NAK: "nak",
    CLASS_D_KEEPALIVE: "keepalive",
    CLASS_D_CONFORMANCE_TEST: "conformance_test",
    CLASS_D_TEST_ECHO_REQUEST: "test_echo_request",
    CLASS_D_TEST_ECHO_RESPONSE: "test_echo_response",
    CLASS_D_OP_ECHO_REQUEST: "op_echo_request",
    CLASS_D_OP_ECHO_RESPONSE: "op_echo_response",
}

COMMID_MIN = 1
COMMID_MAX = 0xFFFFFFFF


def next_commid(current: int) -> int:
    """Advance a per-link COMMID; rolls 0xFFFFFFFF -> 1 (never 0)."""
    return COMMID_MIN if current >= COMMID_MAX else current + 1


def build_class_d(
    body: bytes,
    commid: int,
    message_type: int = CLASS_D_DATA,
) -> bytes:
    """Wrap ``body`` (an EMP envelope for a Data message) in a Class D message."""
    out = bytearray()
    out.append(CLASS_D_STX)
    out.append(CLASS_D_PROTOCOL_VERSION)
    out += struct.pack(">I", commid & 0xFFFFFFFF)
    out.append(message_type & 0xFF)
    out.append(CLASS_D_MESSAGE_VERSION)
    out += struct.pack(">I", len(body))
    out += body
    out.append(CLASS_D_ETX)
    return bytes(out)


def build_ack(commid: int, acked_commid: int) -> bytes:
    """Class D ACK — body is the acknowledged COMMID."""
    return build_class_d(struct.pack(">I", acked_commid & 0xFFFFFFFF), commid, CLASS_D_ACK)


def build_nak(commid: int, nakd_commid: int, error_code: int) -> bytes:
    """Class D NAK — body is the COMMID plus a one-octet error code."""
    body = struct.pack(">I", nakd_commid & 0xFFFFFFFF) + bytes([error_code & 0xFF])
    return build_class_d(body, commid, CLASS_D_NAK)


def build_keepalive(commid: int) -> bytes:
    """Class D keep-alive — zero-length body."""
    return build_class_d(b"", commid, CLASS_D_KEEPALIVE)


def parse_class_d(raw: bytes) -> dict:
    """Decode a Class D message (used by tests as an independent check)."""
    if len(raw) < CLASS_D_OVERHEAD:
        raise ValueError(f"Class D message too short: {len(raw)} < {CLASS_D_OVERHEAD}")
    if raw[0] != CLASS_D_STX:
        raise ValueError(f"bad STX 0x{raw[0]:02X}")
    if raw[-1] != CLASS_D_ETX:
        raise ValueError(f"bad ETX 0x{raw[-1]:02X}")
    data_length = struct.unpack(">I", raw[8:12])[0]
    body = raw[CLASS_D_HEADER_LEN:CLASS_D_HEADER_LEN + data_length]
    if len(body) != data_length:
        raise ValueError(f"data_length {data_length} != actual body {len(body)}")
    if len(raw) != CLASS_D_OVERHEAD + data_length:
        raise ValueError("declared length does not account for the whole message")
    return {
        "protocol_version": raw[1],
        "commid": struct.unpack(">I", raw[2:6])[0],
        "message_type": raw[6],
        "message_version": raw[7],
        "data_length": data_length,
        "body": body,
    }


def class_d_field_map(commid: int, message_type: int, body_len: int) -> list[dict]:
    """Ground-truth label map for the Class D header + ETX (frame-relative)."""
    return [
        {"off": 0, "len": 1, "field": "classd.stx", "value": CLASS_D_STX,
         "synthetic": False, "confidence": "spec_legacy"},
        {"off": 1, "len": 1, "field": "classd.protocol_version",
         "value": CLASS_D_PROTOCOL_VERSION, "synthetic": False, "confidence": "spec_legacy"},
        {"off": 2, "len": 4, "field": "classd.commid", "value": commid,
         "synthetic": False, "confidence": "spec_legacy"},
        {"off": 6, "len": 1, "field": "classd.message_type",
         "value": CLASS_D_TYPE_NAMES.get(message_type, message_type),
         "synthetic": False, "confidence": "spec_legacy"},
        {"off": 7, "len": 1, "field": "classd.message_version",
         "value": CLASS_D_MESSAGE_VERSION, "synthetic": False, "confidence": "spec_legacy"},
        {"off": 8, "len": 4, "field": "classd.data_length", "value": body_len,
         "synthetic": False, "confidence": "spec_legacy"},
        {"off": CLASS_D_HEADER_LEN + body_len, "len": 1, "field": "classd.etx",
         "value": CLASS_D_ETX, "synthetic": False, "confidence": "spec_legacy"},
    ]
