# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""STP/RSTP BPDU builders for ambient network noise.

Builds raw Ethernet frames for Spanning Tree Protocol Configuration
BPDUs. Managed switches send these every 2 seconds to maintain loop-free
topology.
"""

from __future__ import annotations

import struct

from scapy.layers.l2 import Ether, LLC
from scapy.packet import Raw


# STP multicast destination MAC (IEEE 802.1D)
STP_MULTICAST_MAC = "01:80:C2:00:00:00"


def _build_bridge_id(priority: int, mac: str) -> bytes:
    """Build an 8-byte Bridge ID (priority + MAC)."""
    # Priority is upper 4 bits of first 2 bytes in real STP,
    # but simplified here as a 2-byte value
    mac_bytes = bytes.fromhex(mac.replace(":", ""))
    return struct.pack(">H", priority) + mac_bytes


def build_stp_config_bpdu(
    src_mac: str,
    bridge_priority: int = 32768,
    root_bridge_mac: str | None = None,
    root_bridge_priority: int = 32768,
    root_path_cost: int = 0,
    port_id: int = 0x8001,
    message_age: int = 0,
    max_age: int = 20,
    hello_time: int = 2,
    forward_delay: int = 15,
) -> bytes:
    """Build an IEEE 802.1D STP Configuration BPDU.

    Args:
        src_mac: Source MAC address (switch port).
        bridge_priority: This bridge's priority (default 32768).
        root_bridge_mac: Root bridge MAC (defaults to src_mac = root).
        root_bridge_priority: Root bridge priority.
        root_path_cost: Cost to reach root bridge.
        port_id: Port identifier (priority + port number).
        message_age: Message age in seconds.
        max_age: Maximum age in seconds.
        hello_time: Hello interval in seconds.
        forward_delay: Forward delay in seconds.

    Returns:
        Raw Ethernet frame bytes.
    """
    if root_bridge_mac is None:
        root_bridge_mac = src_mac

    root_id = _build_bridge_id(root_bridge_priority, root_bridge_mac)
    bridge_id = _build_bridge_id(bridge_priority, src_mac)

    # STP BPDU payload (35 bytes for Configuration BPDU)
    bpdu = bytearray()
    bpdu += struct.pack(">H", 0x0000)  # Protocol ID
    bpdu += struct.pack("B", 0x00)     # Version: STP
    bpdu += struct.pack("B", 0x00)     # Type: Configuration BPDU
    bpdu += struct.pack("B", 0x00)     # Flags (TC=0, TCA=0)
    bpdu += root_id                     # Root Bridge ID (8 bytes)
    bpdu += struct.pack(">I", root_path_cost)  # Root Path Cost
    bpdu += bridge_id                   # Bridge ID (8 bytes)
    bpdu += struct.pack(">H", port_id)  # Port ID
    # Timer values are in 1/256th of a second
    bpdu += struct.pack(">H", message_age * 256)
    bpdu += struct.pack(">H", max_age * 256)
    bpdu += struct.pack(">H", hello_time * 256)
    bpdu += struct.pack(">H", forward_delay * 256)

    pkt = (
        Ether(src=src_mac, dst=STP_MULTICAST_MAC, type=len(bpdu) + 3)
        / LLC(dsap=0x42, ssap=0x42, ctrl=0x03)
        / Raw(load=bytes(bpdu))
    )
    return bytes(pkt)


def build_rstp_bpdu(
    src_mac: str,
    bridge_priority: int = 32768,
    root_bridge_mac: str | None = None,
    root_bridge_priority: int = 32768,
    root_path_cost: int = 0,
    port_id: int = 0x8001,
    port_role: int = 3,
    message_age: int = 0,
    max_age: int = 20,
    hello_time: int = 2,
    forward_delay: int = 15,
) -> bytes:
    """Build an IEEE 802.1w RSTP BPDU (version 2).

    Args:
        src_mac: Source MAC address (switch port).
        bridge_priority: This bridge's priority.
        root_bridge_mac: Root bridge MAC (defaults to src_mac).
        root_bridge_priority: Root bridge priority.
        root_path_cost: Cost to reach root bridge.
        port_id: Port identifier.
        port_role: Port role (0=unknown, 1=alt/backup, 2=root, 3=designated).
        message_age: Message age in seconds.
        max_age: Maximum age in seconds.
        hello_time: Hello interval in seconds.
        forward_delay: Forward delay in seconds.

    Returns:
        Raw Ethernet frame bytes.
    """
    if root_bridge_mac is None:
        root_bridge_mac = src_mac

    root_id = _build_bridge_id(root_bridge_priority, root_bridge_mac)
    bridge_id = _build_bridge_id(bridge_priority, src_mac)

    # RSTP flags: port_role in bits 2-3, forwarding+learning+agreement
    flags = (port_role & 0x03) << 2 | 0x30  # forwarding + learning

    bpdu = bytearray()
    bpdu += struct.pack(">H", 0x0000)  # Protocol ID
    bpdu += struct.pack("B", 0x02)     # Version: RSTP
    bpdu += struct.pack("B", 0x02)     # Type: RST BPDU
    bpdu += struct.pack("B", flags)
    bpdu += root_id
    bpdu += struct.pack(">I", root_path_cost)
    bpdu += bridge_id
    bpdu += struct.pack(">H", port_id)
    bpdu += struct.pack(">H", message_age * 256)
    bpdu += struct.pack(">H", max_age * 256)
    bpdu += struct.pack(">H", hello_time * 256)
    bpdu += struct.pack(">H", forward_delay * 256)
    bpdu += struct.pack("B", 0x00)     # Version 1 Length

    pkt = (
        Ether(src=src_mac, dst=STP_MULTICAST_MAC, type=len(bpdu) + 3)
        / LLC(dsap=0x42, ssap=0x42, ctrl=0x03)
        / Raw(load=bytes(bpdu))
    )
    return bytes(pkt)
