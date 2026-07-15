# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""EMP (Edge Message Protocol) v4 packet building for Interoperable Train Control.

EMP is the message envelope of the AAR ITC/PTC messaging stack:

    ITC application message  ->  EMP envelope (AAR S-9354)  ->  Class D (S-9356)
    ->  TCP  ->  IPv4  ->  Ethernet   (office / wayside / back-office IP side)

Fidelity scope (see backend .../protocol_engines/emp/README notes and the
Phase-0 findings):

- The **EMP envelope** byte layout below is reconstructed to byte-accuracy from
  public sources — Meteorcomm patent US10160466B1 and the open-source PTC-Sim
  reference (`dustinfast/PTC-Sim`, MIT). It is verified by round-trip in the
  test suite. Every EMP-envelope field emitted here is spec-derivable and is
  labelled ``synthetic=False`` in the ground-truth field map.
- The **Class D header** bytes (S-9356) and the **ITC application-message
  catalog** are paywalled (AAR MSRP Section K). We therefore do NOT invent
  Class-D header bytes — inventing them would poison a training corpus with
  false ground truth. Class D is modelled as TCP *session behaviour* only
  (connection, keep-alive, teardown) and EMP rides directly in the TCP payload.
  Application payload bytes are plausible-but-synthetic and are labelled
  ``synthetic=True`` so a downstream dissector-training pipeline can tell the
  spec-accurate envelope from the invented payload.

CRC note: PTC-Sim (Python 2) packs the trailing CRC-32 as a *signed* int32
(``>i``) using ``binascii.crc32``. We reproduce that signedness exactly so the
bytes match the reference wire format.

The 220 MHz ITCR radio air interface is out of scope (not IP). No well-known
IANA port is published for Class D — it is assigned per link at setup — so the
destination port is configurable (see ``EMP_DEFAULT_PORT``).
"""

from __future__ import annotations

import struct
from binascii import crc32

# EMP framing constants
EMP_VERSION = 4
EMP_MESSAGE_VERSION = 1
EMP_DEFAULT_TTL_S = 120
EMP_DEFAULT_QOS = 0

# There is NO universal port for ITC Class D — it is installation-configured and
# assigned per link at setup. Do NOT present any value as "the EMP port".
#
# 3001 is used here as the platform default because it is a REAL documented
# vendor default (Siemens wayside implementation, configurable), which makes
# generated traffic land on a port a rail engineer would recognise — unlike the
# previously invented 5361. It remains a vendor profile, not a protocol constant;
# override per-flow for any other installation.
EMP_SIEMENS_WAYSIDE_PORT = 3001
EMP_DEFAULT_PORT = EMP_SIEMENS_WAYSIDE_PORT

# Illustrative ITC/EMP message type IDs. The authoritative ITC message catalog
# is proprietary/paywalled; these IDs are plausible placeholders used to give a
# training corpus stable, distinguishable message classes. They are emitted in
# the (spec-accurate) EMP ``msg_type`` field but their *meaning* is our
# convention, not AAR's.
EMP_MSG_REGISTRATION = 6000   # node registration / session bring-up
EMP_MSG_KEEPALIVE = 6001      # heartbeat
EMP_MSG_WIU_STATUS = 7120     # Wayside Interface Unit status report (WIU -> BOS)
EMP_MSG_WDC_CONTROL = 7124    # Wayside Device Control command (BOS -> WIU)
EMP_MSG_ACK = 7200            # application-level acknowledgement

EMP_MSG_NAMES = {
    EMP_MSG_REGISTRATION: "registration",
    EMP_MSG_KEEPALIVE: "keepalive",
    EMP_MSG_WIU_STATUS: "wiu_status",
    EMP_MSG_WDC_CONTROL: "wdc_control",
    EMP_MSG_ACK: "ack",
}


def _signed_crc32(data: bytes) -> int:
    """CRC-32 wrapped into signed int32 range (PTC-Sim / py2 binascii semantics)."""
    v = crc32(data) & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def build_emp_message(
    msg_type: int,
    sender: str,
    dest: str,
    payload: bytes,
    ttl_s: int = EMP_DEFAULT_TTL_S,
    qos: int = EMP_DEFAULT_QOS,
    flags: int = 0,
) -> bytes:
    """Build a byte-accurate EMP v4 message (big-endian).

    Layout (verified against PTC-Sim ``lib_messaging.Message._to_raw``)::

        Common header (8B): B ver=4 | H msg_type | B msg_ver=1 | B flags
                            | I[1:] 24-bit body_size
        Var header (13+N):  B var_hdr_size | H ttl_s | H qos
                            | <sender>\\x00 | <dest>\\x00
        Body:               <payload> | i CRC-32 (signed) over all preceding

    ``body_size`` = 4 (CRC) + len(payload); ``var_hdr_size`` = len(sender) +
    len(dest) + 2. Minimum message size is 20 bytes.
    """
    sender_b = sender.encode("ascii")
    dest_b = dest.encode("ascii")
    body_size = 4 + len(payload)
    var_hdr_size = len(sender_b) + len(dest_b) + 2

    b = bytearray()
    b += struct.pack(">B", EMP_VERSION)
    b += struct.pack(">H", msg_type & 0xFFFF)
    b += struct.pack(">B", EMP_MESSAGE_VERSION)
    b += struct.pack(">B", flags & 0xFF)
    b += struct.pack(">I", body_size)[1:]          # 24-bit body size
    b += struct.pack(">B", var_hdr_size & 0xFF)
    b += struct.pack(">H", ttl_s & 0xFFFF)
    b += struct.pack(">H", qos & 0xFFFF)
    b += sender_b + b"\x00"
    b += dest_b + b"\x00"
    b += payload
    b += struct.pack(">i", _signed_crc32(bytes(b)))
    return bytes(b)


def emp_field_map(
    msg_type: int,
    sender: str,
    dest: str,
    payload: bytes,
    payload_fields: list[dict] | None = None,
    ttl_s: int = EMP_DEFAULT_TTL_S,
) -> list[dict]:
    """Ground-truth label map for one EMP message, EMP-relative byte offsets.

    Each entry is ``{off, len, field, value, synthetic}``. Envelope fields are
    ``synthetic=False`` (spec-derivable). ``payload_fields`` (from the payload
    builders) are appended with their offsets shifted to absolute EMP offsets.
    This is the record a CV dissector-training pipeline consumes; the corpus
    exporter (a later phase) turns these into the per-packet JSON sidecar.
    """
    sender_b = sender.encode("ascii")
    dest_b = dest.encode("ascii")
    var_hdr_size = len(sender_b) + len(dest_b) + 2
    payload_off = 13 + var_hdr_size
    total = payload_off + len(payload) + 4

    fields = [
        {"off": 0, "len": 1, "field": "emp.version", "value": EMP_VERSION, "synthetic": False},
        {"off": 1, "len": 2, "field": "emp.msg_type", "value": msg_type, "synthetic": False},
        {"off": 3, "len": 1, "field": "emp.msg_version", "value": EMP_MESSAGE_VERSION, "synthetic": False},
        {"off": 4, "len": 1, "field": "emp.flags", "value": 0, "synthetic": False},
        {"off": 5, "len": 3, "field": "emp.body_size", "value": 4 + len(payload), "synthetic": False},
        {"off": 8, "len": 1, "field": "emp.var_hdr_size", "value": var_hdr_size, "synthetic": False},
        {"off": 9, "len": 2, "field": "emp.ttl_s", "value": ttl_s, "synthetic": False},
        {"off": 11, "len": 2, "field": "emp.qos", "value": EMP_DEFAULT_QOS, "synthetic": False},
        {"off": 13, "len": len(sender_b) + 1, "field": "emp.src_addr", "value": sender, "synthetic": False},
        {"off": 13 + len(sender_b) + 1, "len": len(dest_b) + 1, "field": "emp.dst_addr", "value": dest, "synthetic": False},
    ]
    for pf in payload_fields or [{"off": 0, "len": len(payload), "field": "emp.payload", "value": payload.hex(), "synthetic": True}]:
        fields.append({
            "off": payload_off + pf["off"],
            "len": pf["len"],
            "field": pf["field"],
            "value": pf["value"],
            "synthetic": pf.get("synthetic", True),
        })
    fields.append({"off": total - 4, "len": 4, "field": "emp.crc32", "value": "signed-crc32", "synthetic": False})
    return fields


def emp_address(railroad: str, node_type: str, node: str) -> str:
    """Build an ITC-style EMP address string, e.g. ``aar.w.wiu007``.

    Format is ``<railroad>.<node_type>.<node>`` where node_type is a single
    letter: ``b`` back-office, ``w`` wayside, ``l`` locomotive. Illustrative of
    the ITC lowercase-alphanumeric address convention (the exact catalog is
    proprietary). Non-alphanumeric characters in ``node`` are stripped.
    """
    safe_node = "".join(c for c in node.lower() if c.isalnum()) or "node"
    safe_rr = "".join(c for c in railroad.lower() if c.isalnum()) or "aar"
    return f"{safe_rr}.{node_type}.{safe_node}"


# ---------------------------------------------------------------------------
# Synthetic application payloads (labelled synthetic=True).
# These model plausible wayside/back-office OT semantics so the traffic looks
# real, but their byte structure is our convention, not the AAR ITC catalog.
# ---------------------------------------------------------------------------

SIGNAL_ASPECTS = {0: "stop", 1: "approach", 2: "advance_approach", 3: "clear"}


def build_wiu_status_payload(
    wiu_id: int,
    signal_aspect: int,
    switch_normal: bool,
    track_occupancy: int,
    battery_dv: int,
    vital_ok: bool,
    epoch_s: int,
) -> tuple[bytes, list[dict]]:
    """Wayside Interface Unit status report (WIU -> BOS). Synthetic structure.

    Returns ``(payload_bytes, payload_field_map)`` where the field map uses
    payload-relative offsets (shifted to EMP-absolute by ``emp_field_map``).
    """
    payload = struct.pack(
        ">BHBBBHBI",
        0x01,                       # subtype: status report
        wiu_id & 0xFFFF,
        signal_aspect & 0xFF,
        0x00 if switch_normal else 0x01,
        track_occupancy & 0xFF,
        battery_dv & 0xFFFF,
        0x01 if vital_ok else 0x00,
        epoch_s & 0xFFFFFFFF,
    )
    fields = [
        {"off": 0, "len": 1, "field": "wiu.subtype", "value": 1, "synthetic": True},
        {"off": 1, "len": 2, "field": "wiu.wiu_id", "value": wiu_id, "synthetic": True},
        {"off": 3, "len": 1, "field": "wiu.signal_aspect",
         "value": SIGNAL_ASPECTS.get(signal_aspect, signal_aspect), "synthetic": True},
        {"off": 4, "len": 1, "field": "wiu.switch_position",
         "value": "normal" if switch_normal else "reverse", "synthetic": True},
        {"off": 5, "len": 1, "field": "wiu.track_occupancy", "value": track_occupancy, "synthetic": True},
        {"off": 6, "len": 2, "field": "wiu.battery_decivolts", "value": battery_dv, "synthetic": True},
        {"off": 8, "len": 1, "field": "wiu.vital_status", "value": "ok" if vital_ok else "fault", "synthetic": True},
        {"off": 9, "len": 4, "field": "wiu.timestamp_s", "value": epoch_s, "synthetic": True},
    ]
    return payload, fields


def build_wdc_control_payload(
    wiu_id: int,
    command: int,
    target: int,
    value: int,
    seq: int,
) -> tuple[bytes, list[dict]]:
    """Wayside Device Control command (BOS -> WIU). Synthetic structure."""
    payload = struct.pack(
        ">BHBHHH",
        0x02,                       # subtype: control command
        wiu_id & 0xFFFF,
        command & 0xFF,
        target & 0xFFFF,
        value & 0xFFFF,
        seq & 0xFFFF,
    )
    fields = [
        {"off": 0, "len": 1, "field": "wdc.subtype", "value": 2, "synthetic": True},
        {"off": 1, "len": 2, "field": "wdc.wiu_id", "value": wiu_id, "synthetic": True},
        {"off": 3, "len": 1, "field": "wdc.command", "value": command, "synthetic": True},
        {"off": 4, "len": 2, "field": "wdc.target", "value": target, "synthetic": True},
        {"off": 6, "len": 2, "field": "wdc.value", "value": value, "synthetic": True},
        {"off": 8, "len": 2, "field": "wdc.seq", "value": seq, "synthetic": True},
    ]
    return payload, fields


def build_ack_payload(ack_seq: int, status: int = 0) -> tuple[bytes, list[dict]]:
    """Application-level ACK. Synthetic structure."""
    payload = struct.pack(">BHB", 0x03, ack_seq & 0xFFFF, status & 0xFF)
    fields = [
        {"off": 0, "len": 1, "field": "ack.subtype", "value": 3, "synthetic": True},
        {"off": 1, "len": 2, "field": "ack.ack_seq", "value": ack_seq, "synthetic": True},
        {"off": 3, "len": 1, "field": "ack.status", "value": status, "synthetic": True},
    ]
    return payload, fields


def build_registration_payload(node_id: int, role: int) -> tuple[bytes, list[dict]]:
    """Node registration / session bring-up. Synthetic structure."""
    payload = struct.pack(">BHB", 0x00, node_id & 0xFFFF, role & 0xFF)
    fields = [
        {"off": 0, "len": 1, "field": "reg.subtype", "value": 0, "synthetic": True},
        {"off": 1, "len": 2, "field": "reg.node_id", "value": node_id, "synthetic": True},
        {"off": 3, "len": 1, "field": "reg.role", "value": role, "synthetic": True},
    ]
    return payload, fields
