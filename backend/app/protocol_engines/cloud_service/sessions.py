# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Payload builders for interactive IT sessions: HTTPS, SSH, RDP, Telnet.

Only framing that is observable in clear on the wire is modelled; anything
after encryption starts is random bytes inside correctly framed records or
packets. Sources:

- TLS 1.2 handshake and record layer: RFC 5246; ECDHE ServerKeyExchange:
  RFC 8422 section 5.4 (named curve x25519 = 29, RFC 8422 / RFC 7748).
- SSH identification string and binary packet / KEXINIT layout: RFC 4253
  sections 4.2, 6 and 7.1; curve25519-sha256 key exchange: RFC 8731.
- RDP: TPKT (RFC 1006) + X.224 Connection Request carrying the
  "Cookie: mstshash=" token and RDP_NEG_REQ / RDP_NEG_RSP ([MS-RDPBCGR]
  2.2.1.1 / 2.2.1.2); requestedProtocols TLS|CredSSP|CredSSP-EX = 0x0B.
- Telnet option negotiation: RFC 854 / RFC 855 (IAC DO/WILL), TERMINAL-TYPE
  (24), NAWS (31), ECHO (1), SUPPRESS-GO-AHEAD (3).
"""

from __future__ import annotations

import random
import struct

from app.protocol_engines.cloud_service.packets import build_tls_server_hello_payload

_TLS12 = b"\x03\x03"
_HANDSHAKE, _CCS, _APPDATA = 0x16, 0x14, 0x17


def _record(content_type: int, body: bytes) -> bytes:
    return bytes([content_type]) + _TLS12 + struct.pack(">H", len(body)) + body


def _handshake(msg_type: int, body: bytes) -> bytes:
    return bytes([msg_type]) + struct.pack(">I", len(body))[1:] + body


# --------------------------------------------------------------------------
# TLS 1.2 full handshake (ECDHE) and application data
# --------------------------------------------------------------------------

def tls_server_flight(tls_profile: str) -> bytes:
    """ServerHello + Certificate + ServerKeyExchange + ServerHelloDone.

    The cloud-heartbeat flight omits ServerKeyExchange; an ECDHE cipher
    requires it, so the interactive path inserts it before ServerHelloDone.
    """
    flight = build_tls_server_hello_payload(tls_profile)
    done = _record(_HANDSHAKE, _handshake(0x0E, b""))
    assert flight.endswith(done)
    ecdsa = tls_profile == "windows_schannel_2016"
    sig_alg, sig_len = ((0x0403, 71) if ecdsa else (0x0401, 256))
    params = bytes([3]) + struct.pack(">H", 29) + bytes([32]) + random.randbytes(32)
    ske = params + struct.pack(">HH", sig_alg, sig_len) + random.randbytes(sig_len)
    return flight[: -len(done)] + _record(_HANDSHAKE, _handshake(0x0C, ske)) + done


def tls_client_finish() -> bytes:
    """ClientKeyExchange + ChangeCipherSpec + (encrypted) Finished."""
    cke = _record(_HANDSHAKE, _handshake(0x10, bytes([32]) + random.randbytes(32)))
    return cke + _record(_CCS, b"\x01") + _record(_HANDSHAKE, random.randbytes(40))


def tls_server_finish() -> bytes:
    """ChangeCipherSpec + (encrypted) Finished."""
    return _record(_CCS, b"\x01") + _record(_HANDSHAKE, random.randbytes(40))


def tls_application_data(size: int) -> bytes:
    return _record(_APPDATA, random.randbytes(size))


# --------------------------------------------------------------------------
# SSH
# --------------------------------------------------------------------------

# Client identification strings of common admin tools. Servers announce
# their own string from the device fingerprint (ssh_banner) when one is
# sourced; otherwise the software name without a version, rather than an
# invented version number.
SSH_CLIENT_BANNER = b"SSH-2.0-PuTTY_Release_0.81\r\n"
SSH_DEFAULT_SERVER_BANNER = b"SSH-2.0-OpenSSH\r\n"

_KEX_NAMES = [
    b"curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,diffie-hellman-group14-sha256",
    b"ssh-ed25519,ecdsa-sha2-nistp256,rsa-sha2-512,rsa-sha2-256",
    b"aes128-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com",
    b"aes128-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com",
    b"hmac-sha2-256,hmac-sha2-512",
    b"hmac-sha2-256,hmac-sha2-512",
    b"none",
    b"none",
    b"",
    b"",
]


def ssh_packet(payload: bytes, block: int = 8) -> bytes:
    """RFC 4253 binary packet (unencrypted): length, padding length, payload, padding."""
    pad = block - ((5 + len(payload)) % block)
    if pad < 4:
        pad += block
    return struct.pack(">IB", 1 + len(payload) + pad, pad) + payload + random.randbytes(pad)


def ssh_kexinit() -> bytes:
    body = bytes([20]) + random.randbytes(16)
    for names in _KEX_NAMES:
        body += struct.pack(">I", len(names)) + names
    body += b"\x00" + struct.pack(">I", 0)
    return ssh_packet(body)


def ssh_ecdh_init() -> bytes:
    return ssh_packet(bytes([30]) + struct.pack(">I", 32) + random.randbytes(32))


def ssh_ecdh_reply() -> bytes:
    host_key = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + random.randbytes(32)
    signature = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 64) + random.randbytes(64)
    body = (bytes([31]) + struct.pack(">I", len(host_key)) + host_key
            + struct.pack(">I", 32) + random.randbytes(32)
            + struct.pack(">I", len(signature)) + signature)
    return ssh_packet(body)


def ssh_newkeys() -> bytes:
    return ssh_packet(bytes([21]))


def ssh_encrypted(size: int) -> bytes:
    """An encrypted packet: opaque bytes plus a 32-byte hmac-sha2-256 tag."""
    return random.randbytes(max(16, size - size % 16)) + random.randbytes(32)


# --------------------------------------------------------------------------
# RDP
# --------------------------------------------------------------------------

_RDP_PROTOCOL_SSL, _RDP_PROTOCOL_HYBRID, _RDP_PROTOCOL_HYBRID_EX = 0x01, 0x02, 0x08


def _tpkt(payload: bytes) -> bytes:
    return b"\x03\x00" + struct.pack(">H", 4 + len(payload)) + payload


def rdp_connection_request(username: str) -> bytes:
    cookie = f"Cookie: mstshash={username[:9]}\r\n".encode()
    neg_req = struct.pack("<BBHI", 0x01, 0x00, 8,
                          _RDP_PROTOCOL_SSL | _RDP_PROTOCOL_HYBRID | _RDP_PROTOCOL_HYBRID_EX)
    x224 = cookie + neg_req
    return _tpkt(bytes([6 + len(x224), 0xE0, 0, 0, 0, 0, 0]) + x224)


def rdp_connection_confirm() -> bytes:
    neg_rsp = struct.pack("<BBHI", 0x02, 0x1F, 8, _RDP_PROTOCOL_HYBRID)
    return _tpkt(bytes([6 + len(neg_rsp), 0xD0, 0, 0, 0x12, 0x34, 0]) + neg_rsp)


# --------------------------------------------------------------------------
# Telnet
# --------------------------------------------------------------------------

IAC, DO, WILL, WONT = 255, 253, 251, 252
_ECHO, _SGA, _TTYPE, _NAWS = 1, 3, 24, 31


def telnet_server_greeting(prompt: bytes = b"\r\nlogin: ") -> bytes:
    return bytes([IAC, DO, _TTYPE, IAC, DO, _NAWS, IAC, WILL, _ECHO, IAC, WILL, _SGA]) + prompt


def telnet_client_negotiation() -> bytes:
    return bytes([IAC, WILL, _TTYPE, IAC, WILL, _NAWS, IAC, DO, _ECHO, IAC, DO, _SGA])

