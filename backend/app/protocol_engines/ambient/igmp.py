"""IGMPv2 membership report builder for ambient network noise.

Builds raw Ethernet frames for IGMP Membership Reports that devices
send to join multicast groups (BACnet, PROFINET, etc.).
"""

from __future__ import annotations

import struct

from scapy.layers.inet import IP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

# Common OT multicast groups
BACNET_MULTICAST = "255.255.255.255"  # BACnet uses broadcast, not multicast
PROFINET_DCP_MULTICAST = "224.0.0.2"  # PROFINET uses Layer 2, but IGMP for routers
ALL_HOSTS_MULTICAST = "224.0.0.1"

# IGMPv2 types
_IGMP_MEMBERSHIP_REPORT_V2 = 0x16


def _igmp_checksum(data: bytes) -> int:
    """Compute IGMP checksum (one's complement of 16-bit sum)."""
    if len(data) % 2:
        data = data + b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) + data[i + 1]
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return (~total) & 0xFFFF


def _multicast_mac(group_ip: str) -> str:
    """Derive multicast MAC from group IP (01:00:5E + lower 23 bits)."""
    octets = [int(o) for o in group_ip.split(".")]
    return f"01:00:5E:{octets[1] & 0x7F:02x}:{octets[2]:02x}:{octets[3]:02x}"


def build_igmpv2_report(
    src_mac: str,
    src_ip: str,
    group_ip: str,
) -> bytes:
    """Build an IGMPv2 Membership Report.

    Args:
        src_mac: Source device MAC address.
        src_ip: Source device IP address.
        group_ip: Multicast group being joined.

    Returns:
        Raw Ethernet frame bytes.
    """
    dst_mac = _multicast_mac(group_ip)

    # IGMPv2 Membership Report: 8 bytes
    igmp = bytearray(8)
    igmp[0] = _IGMP_MEMBERSHIP_REPORT_V2  # Type
    igmp[1] = 0x00  # Max Response Time (unused for reports)
    # Checksum at bytes 2-3 (compute after)
    # Group address at bytes 4-7
    group_octets = [int(o) for o in group_ip.split(".")]
    struct.pack_into(">I", igmp, 4,
                     (group_octets[0] << 24) | (group_octets[1] << 16)
                     | (group_octets[2] << 8) | group_octets[3])
    # Calculate checksum
    cksum = _igmp_checksum(bytes(igmp))
    struct.pack_into(">H", igmp, 2, cksum)

    # IP header with Router Alert option, TTL=1, protocol=2 (IGMP)
    # Scapy builds the IP header; we add Router Alert via options
    pkt = (
        Ether(src=src_mac, dst=dst_mac)
        / IP(
            src=src_ip,
            dst=group_ip,
            ttl=1,
            proto=2,
            options=[b"\x94\x04\x00\x00"],  # Router Alert option
        )
        / Raw(load=bytes(igmp))
    )
    return bytes(pkt)
