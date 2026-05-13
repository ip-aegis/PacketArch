# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Packet builders for cloud service TLS heartbeat traffic.

Generates TCP SYN + TLS 1.2 Client Hello packets that simulate
cloud service connectivity (EWON Talk2M, TeamViewer, AWS, etc.).

Ported from docker/packetarch-agent/app/cloud_traffic_scheduler.py.
"""

import random
import struct
import time

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

# TLS constants
TLS_HANDSHAKE = 0x16
TLS_CLIENT_HELLO = 0x01
TLS_VERSION_1_2 = (0x03, 0x03)


def build_tcp_syn(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq_num: int,
    ttl: int = 64,
) -> bytes:
    """Build a TCP SYN packet for cloud service connection initiation.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address (typically gateway)
        src_ip: Source IP address
        dst_ip: Destination IP address (cloud service)
        src_port: Source TCP port
        dst_port: Destination TCP port (typically 443)
        seq_num: TCP sequence number
        ttl: IP TTL value

    Returns:
        Raw packet bytes
    """
    packet = (
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=ttl)
        / TCP(
            sport=src_port,
            dport=dst_port,
            seq=seq_num,
            flags="S",
            window=65535,
            options=[
                ("MSS", 1460),
                ("NOP", None),
                ("WScale", 7),
                ("NOP", None),
                ("NOP", None),
                ("SAckOK", b""),
            ],
        )
    )
    return bytes(packet)


def build_tls_client_hello(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq_num: int,
    hostname: str,
    ttl: int = 64,
    tls_profile: str = "embedded_minimal",
) -> bytes:
    """Build a TLS 1.2 Client Hello packet with SNI extension.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address (typically gateway)
        src_ip: Source IP address
        dst_ip: Destination IP address (cloud service)
        src_port: Source TCP port
        dst_port: Destination TCP port (typically 443)
        seq_num: TCP sequence number (should be SYN seq + 1)
        hostname: Server hostname for SNI extension
        ttl: IP TTL value
        tls_profile: ClientHello shape preset. See
            ``CloudServiceConversationState.tls_profile`` for options.
            The shape drives the JA3 hash CV uses for device-class
            iconography — a minimalist 4-cipher ClientHello triggers a
            "Canon printer" icon, while a 25-cipher SChannel ClientHello
            with the full Windows extension set triggers a Windows icon.

    Returns:
        Raw packet bytes
    """
    if tls_profile == "windows_schannel_2016":
        tls_payload = _build_tls_client_hello_payload_schannel_2016(hostname)
    else:
        tls_payload = _build_tls_client_hello_payload(hostname)

    packet = (
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=ttl)
        / TCP(
            sport=src_port,
            dport=dst_port,
            seq=seq_num + 1,  # After SYN
            ack=1,
            flags="PA",
            window=65535,
        )
        / Raw(load=tls_payload)
    )
    return bytes(packet)


def build_tcp_fin(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq_num: int,
    ttl: int = 64,
) -> bytes:
    """Build a TCP FIN packet for connection teardown.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_port: Source TCP port
        dst_port: Destination TCP port
        seq_num: TCP sequence number
        ttl: IP TTL value

    Returns:
        Raw packet bytes
    """
    packet = (
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=ttl)
        / TCP(
            sport=src_port,
            dport=dst_port,
            seq=seq_num,
            flags="FA",
            window=65535,
        )
    )
    return bytes(packet)


def _build_tls_client_hello_payload(hostname: str) -> bytes:
    """Build TLS 1.2 Client Hello payload with SNI extension.

    Args:
        hostname: Server hostname for SNI

    Returns:
        TLS record bytes
    """
    # Random bytes (32 bytes: 4-byte timestamp + 28 random)
    random_bytes = struct.pack(">I", int(time.time())) + bytes(
        random.randint(0, 255) for _ in range(28)
    )

    # Session ID (empty for new connection)
    session_id = b""

    # Cipher suites (common TLS 1.2 suites)
    cipher_suites = bytes([
        0x00, 0x08,  # Length: 8 bytes = 4 suites
        0xC0, 0x2B,  # TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
        0xC0, 0x2F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
        0xC0, 0x2C,  # TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
        0xC0, 0x30,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
    ])

    # Compression methods (null only)
    compression = bytes([0x01, 0x00])

    # Extensions
    extensions = b""

    # SNI extension (0x0000)
    if hostname:
        hostname_bytes = hostname.encode("utf-8")
        sni_data = struct.pack(">BH", 0x00, len(hostname_bytes)) + hostname_bytes
        sni_list = struct.pack(">H", len(sni_data)) + sni_data
        extensions += struct.pack(">HH", 0x0000, len(sni_list)) + sni_list

    # Supported versions extension (0x002B) - indicate TLS 1.2/1.3
    supported_versions = bytes([0x03, 0x03, 0x03, 0x03, 0x04])
    extensions += struct.pack(">HH", 0x002B, len(supported_versions)) + supported_versions

    # EC point formats extension (0x000B)
    ec_formats = bytes([0x01, 0x00])  # uncompressed
    extensions += struct.pack(">HH", 0x000B, len(ec_formats)) + ec_formats

    # Supported groups extension (0x000A)
    groups = bytes([
        0x00, 0x06,  # length
        0x00, 0x1D,  # x25519
        0x00, 0x17,  # secp256r1
        0x00, 0x18,  # secp384r1
    ])
    extensions += struct.pack(">HH", 0x000A, len(groups)) + groups

    # Build Client Hello message
    client_hello = (
        bytes([TLS_VERSION_1_2[0], TLS_VERSION_1_2[1]])  # Legacy version
        + random_bytes
        + bytes([len(session_id)]) + session_id
        + cipher_suites
        + compression
        + struct.pack(">H", len(extensions)) + extensions
    )

    # Handshake header
    handshake = (
        bytes([TLS_CLIENT_HELLO])
        + struct.pack(">I", len(client_hello))[1:]
        + client_hello
    )

    # TLS Record header
    tls_record = (
        bytes([TLS_HANDSHAKE])
        + bytes([TLS_VERSION_1_2[0], TLS_VERSION_1_2[1]])
        + struct.pack(">H", len(handshake))
        + handshake
    )

    return tls_record


def _build_tls_client_hello_payload_schannel_2016(hostname: str) -> bytes:
    """Build a TLS 1.2 Client Hello shaped like Windows Server 2016 SChannel.

    Targets the JA3 hash Cyber Vision uses to render the Windows icon
    family. Without this, the minimalist 4-cipher ClientHello in
    `_build_tls_client_hello_payload` collides with embedded-printer JA3
    fingerprints (Canon iR series in particular) and CV draws the wrong
    icon even though SNMP / OUI identify the device as Microsoft.

    Cipher list and extension ordering taken from real SChannel captures
    on Windows Server 2016 build 14393 (1607). Matches the JA3
    `771,49196-...-10,0-23-65281-...,29-23-24,0` shape that CV's
    iconography rules tag as "Windows".
    """
    random_bytes = struct.pack(">I", int(time.time())) + bytes(
        random.randint(0, 255) for _ in range(28)
    )
    # Realistic SChannel 2016 includes a 32-byte session id (resumable).
    session_id = bytes(random.randint(0, 255) for _ in range(32))

    # 25 cipher suites in SChannel 2016 offer order (GCM ECDHE preferred,
    # then CBC ECDHE, then DHE, RSA, finally legacy 3DES). Order matters
    # for JA3 — do not reorder without re-checking the hash.
    schannel_ciphers = [
        0xC02C, 0xC02B, 0xC030, 0xC02F,
        0xC024, 0xC028, 0xC023, 0xC027,
        0xC00A, 0xC014, 0xC009, 0xC013,
        0x009F, 0x009E, 0x006B, 0x0067,
        0x0039, 0x0033, 0x009D, 0x009C,
        0x003D, 0x003C, 0x0035, 0x002F,
        0x000A,
    ]
    cs_bytes = struct.pack(">H", len(schannel_ciphers) * 2)
    for cs in schannel_ciphers:
        cs_bytes += struct.pack(">H", cs)

    compression = bytes([0x01, 0x00])  # null only

    extensions = b""

    # 0x0000 server_name (SNI) — Windows always sends this when a hostname
    # is known.
    if hostname:
        host_bytes = hostname.encode("utf-8")
        sni_entry = struct.pack(">BH", 0x00, len(host_bytes)) + host_bytes
        sni_list = struct.pack(">H", len(sni_entry)) + sni_entry
        extensions += struct.pack(">HH", 0x0000, len(sni_list)) + sni_list

    # 0x0017 extended_master_secret — empty body, SChannel always offers it
    extensions += struct.pack(">HH", 0x0017, 0)

    # 0xFF01 renegotiation_info — empty body (no prior session)
    extensions += struct.pack(">HH", 0xFF01, 1) + bytes([0x00])

    # 0x000A supported_groups — secp256r1, secp384r1, secp521r1, x25519
    groups = bytes([
        0x00, 0x08,           # length
        0x00, 0x17,           # secp256r1
        0x00, 0x18,           # secp384r1
        0x00, 0x19,           # secp521r1
        0x00, 0x1D,           # x25519
    ])
    extensions += struct.pack(">HH", 0x000A, len(groups)) + groups

    # 0x000B ec_point_formats — uncompressed only
    ec_formats = bytes([0x01, 0x00])
    extensions += struct.pack(">HH", 0x000B, len(ec_formats)) + ec_formats

    # 0x0023 session_ticket — empty body
    extensions += struct.pack(">HH", 0x0023, 0)

    # 0x000D signature_algorithms — SChannel 2016 offer
    sig_algs = bytes([
        0x00, 0x14,             # list length 20 bytes = 10 algorithms
        0x04, 0x01,             # rsa_pkcs1_sha256
        0x05, 0x01,             # rsa_pkcs1_sha384
        0x06, 0x01,             # rsa_pkcs1_sha512
        0x02, 0x01,             # rsa_pkcs1_sha1
        0x04, 0x03,             # ecdsa_secp256r1_sha256
        0x05, 0x03,             # ecdsa_secp384r1_sha384
        0x06, 0x03,             # ecdsa_secp521r1_sha512
        0x02, 0x03,             # ecdsa_sha1
        0x04, 0x02,             # dsa_sha256
        0x02, 0x02,             # dsa_sha1
    ])
    extensions += struct.pack(">HH", 0x000D, len(sig_algs)) + sig_algs

    # 0x0010 ALPN — http/1.1 (TeamViewer relay + Talk2M both speak
    # plain HTTPS over the tunnel)
    alpn_proto = b"http/1.1"
    alpn_entry = bytes([len(alpn_proto)]) + alpn_proto
    alpn_list = struct.pack(">H", len(alpn_entry)) + alpn_entry
    extensions += struct.pack(">HH", 0x0010, len(alpn_list)) + alpn_list

    # 0x0005 status_request — OCSP stapling (cert_status_type=1, empty
    # responder_id_list, empty extensions)
    status_req = bytes([0x01, 0x00, 0x00, 0x00, 0x00])
    extensions += struct.pack(">HH", 0x0005, len(status_req)) + status_req

    client_hello = (
        bytes([TLS_VERSION_1_2[0], TLS_VERSION_1_2[1]])
        + random_bytes
        + bytes([len(session_id)]) + session_id
        + cs_bytes
        + compression
        + struct.pack(">H", len(extensions)) + extensions
    )

    handshake = (
        bytes([TLS_CLIENT_HELLO])
        + struct.pack(">I", len(client_hello))[1:]
        + client_hello
    )

    tls_record = (
        bytes([TLS_HANDSHAKE])
        + bytes([TLS_VERSION_1_2[0], TLS_VERSION_1_2[1]])
        + struct.pack(">H", len(handshake))
        + handshake
    )

    return tls_record
