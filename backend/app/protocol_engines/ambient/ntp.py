# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTP packet builders for ambient network noise.

Builds raw Ethernet frames for NTP client queries and server responses.
Uses NTPv4 (version 4) packets.
"""

import struct
import time

from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

# NTP epoch offset: seconds between 1900-01-01 and 1970-01-01
_NTP_EPOCH_OFFSET = 2208988800


def _ntp_timestamp(unix_ts: float) -> bytes:
    """Convert a Unix timestamp to 8-byte NTP timestamp (seconds + fraction)."""
    ntp_seconds = int(unix_ts) + _NTP_EPOCH_OFFSET
    fraction = int((unix_ts % 1) * (2**32))
    return struct.pack(">II", ntp_seconds, fraction)


def build_ntp_query(
    src_mac: str,
    src_ip: str,
    dst_ip: str,
    dst_mac: str = "ff:ff:ff:ff:ff:ff",
    src_port: int = 123,
) -> bytes:
    """Build an NTPv4 client query packet.

    Args:
        src_mac: Source MAC address.
        src_ip: Source IP address.
        dst_ip: NTP server IP address.
        dst_mac: Destination MAC (gateway or broadcast).
        src_port: Source UDP port.

    Returns:
        Raw Ethernet frame bytes.
    """
    # NTP v4 client request: LI=0, VN=4, Mode=3
    payload = bytearray(48)
    payload[0] = 0x23  # LI=0 (00), VN=4 (100), Mode=3 (011) = 0b00_100_011
    # Transmit timestamp at offset 40
    now = time.time()
    payload[40:48] = _ntp_timestamp(now)

    pkt = (
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=64)
        / UDP(sport=src_port, dport=123)
        / Raw(load=bytes(payload))
    )
    return bytes(pkt)


def build_ntp_response(
    src_mac: str,
    src_ip: str,
    dst_mac: str,
    dst_ip: str,
    dst_port: int,
) -> bytes:
    """Build an NTPv4 server response packet.

    Args:
        src_mac: NTP server MAC address.
        src_ip: NTP server IP address.
        dst_mac: Client MAC address.
        dst_ip: Client IP address.
        dst_port: Client source UDP port.

    Returns:
        Raw Ethernet frame bytes.
    """
    # NTP v4 server response: LI=0, VN=4, Mode=4
    payload = bytearray(48)
    payload[0] = 0x24  # LI=0, VN=4, Mode=4 (server)
    payload[1] = 0x03  # Stratum 3 (secondary reference)
    payload[2] = 0x06  # Poll interval 2^6 = 64 seconds
    payload[3] = 0xEC  # Precision ~2^-20 seconds

    now = time.time()
    ts = _ntp_timestamp(now)
    # Reference timestamp (last sync)
    payload[16:24] = _ntp_timestamp(now - 60.0)
    # Origin timestamp (client's transmit time — echoed back)
    payload[24:32] = ts
    # Receive timestamp
    payload[32:40] = ts
    # Transmit timestamp
    payload[40:48] = ts

    pkt = (
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=64)
        / UDP(sport=123, dport=dst_port)
        / Raw(load=bytes(payload))
    )
    return bytes(pkt)
