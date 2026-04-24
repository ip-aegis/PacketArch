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

    Returns:
        Raw packet bytes
    """
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
