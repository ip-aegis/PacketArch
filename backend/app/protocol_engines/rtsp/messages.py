# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""RTSP/1.0 requests and responses, SDP, and interleaved RTP/RTCP frames.

- RTSP methods, CSeq/Session/Transport headers: RFC 2326.
- Interleaved binary data over the RTSP TCP connection: RFC 2326 10.12
  (``$`` + channel + 16-bit length + RTP/RTCP packet).
- RTP fixed header and RTCP sender report: RFC 3550; H.264 payload
  format with dynamic payload type 96 and a 90 kHz clock: RFC 6184.

Stream paths are the vendors' documented ones where known (Axis VAPIX
``/axis-media/media.amp``; Bosch ``/rtsp_tunnel``); others use a generic
path. No Server / User-Agent product strings are invented.
"""

from __future__ import annotations

import random
import struct

VENDOR_PATHS = {"axis": "/axis-media/media.amp", "bosch": "/rtsp_tunnel"}
GENERIC_PATH = "/stream1"


def stream_path(vendor: str) -> str:
    v = (vendor or "").lower()
    return next((p for k, p in VENDOR_PATHS.items() if k in v), GENERIC_PATH)


def request(method: str, url: str, cseq: int, extra: dict[str, str] | None = None) -> bytes:
    lines = [f"{method} {url} RTSP/1.0", f"CSeq: {cseq}"]
    lines += [f"{k}: {v}" for k, v in (extra or {}).items()]
    return ("\r\n".join(lines) + "\r\n\r\n").encode()


def response(cseq: int, extra: dict[str, str] | None = None, body: bytes = b"") -> bytes:
    lines = ["RTSP/1.0 200 OK", f"CSeq: {cseq}"]
    lines += [f"{k}: {v}" for k, v in (extra or {}).items()]
    if body:
        lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode() + body


def sdp(server_ip: str, session_id: int) -> bytes:
    return (
        "v=0\r\n"
        f"o=- {session_id} 1 IN IP4 {server_ip}\r\n"
        "s=Media Presentation\r\n"
        "c=IN IP4 0.0.0.0\r\n"
        "t=0 0\r\n"
        "a=control:*\r\n"
        "m=video 0 RTP/AVP 96\r\n"
        "a=rtpmap:96 H264/90000\r\n"
        "a=fmtp:96 packetization-mode=1;profile-level-id=4d0029\r\n"
        "a=control:trackID=1\r\n"
    ).encode()


def interleaved(channel: int, packet: bytes) -> bytes:
    return b"$" + bytes([channel]) + struct.pack(">H", len(packet)) + packet


def rtp(seq: int, timestamp: int, ssrc: int, size: int, marker: bool) -> bytes:
    """RTP header (V=2, PT=96) + an H.264 FU-A fragment of opaque bytes."""
    header = struct.pack(">BBHII", 0x80, (0x80 if marker else 0) | 96, seq & 0xFFFF,
                         timestamp & 0xFFFFFFFF, ssrc)
    fu = bytes([0x7C, 0x45 if marker else 0x05])   # FU indicator / header (NAL type 5)
    return header + fu + random.randbytes(max(0, size - len(header) - len(fu)))


def rtcp_sender_report(ssrc: int, ntp_s: float, rtp_ts: int, packets: int, octets: int) -> bytes:
    secs = int(ntp_s) + 2208988800
    frac = int((ntp_s % 1) * (1 << 32))
    return struct.pack(">BBHIIIIII", 0x80, 200, 6, ssrc, secs & 0xFFFFFFFF, frac,
                       rtp_ts & 0xFFFFFFFF, packets & 0xFFFFFFFF, octets & 0xFFFFFFFF)
