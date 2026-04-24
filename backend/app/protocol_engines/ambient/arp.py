# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""ARP packet builders for ambient network noise.

Builds raw Ethernet frames for ARP request, reply, and gratuitous ARP.
"""

from scapy.layers.l2 import ARP, Ether


def build_arp_request(sender_mac: str, sender_ip: str, target_ip: str) -> bytes:
    """Build an ARP 'who-has' request (broadcast).

    Args:
        sender_mac: Source MAC address.
        sender_ip: Source IP address.
        target_ip: IP address being queried.

    Returns:
        Raw Ethernet frame bytes.
    """
    pkt = Ether(src=sender_mac, dst="ff:ff:ff:ff:ff:ff") / ARP(
        op="who-has",
        hwsrc=sender_mac,
        psrc=sender_ip,
        hwdst="00:00:00:00:00:00",
        pdst=target_ip,
    )
    return bytes(pkt)


def build_arp_reply(
    sender_mac: str,
    sender_ip: str,
    target_mac: str,
    target_ip: str,
) -> bytes:
    """Build an ARP 'is-at' reply (unicast).

    Args:
        sender_mac: Responder MAC address.
        sender_ip: Responder IP address.
        target_mac: Original requester MAC address.
        target_ip: Original requester IP address.

    Returns:
        Raw Ethernet frame bytes.
    """
    pkt = Ether(src=sender_mac, dst=target_mac) / ARP(
        op="is-at",
        hwsrc=sender_mac,
        psrc=sender_ip,
        hwdst=target_mac,
        pdst=target_ip,
    )
    return bytes(pkt)


def build_gratuitous_arp(mac: str, ip: str) -> bytes:
    """Build a gratuitous ARP announcement (broadcast).

    Devices send these to announce their MAC-IP binding. Common after
    boot or network interface changes.

    Args:
        mac: Device MAC address.
        ip: Device IP address.

    Returns:
        Raw Ethernet frame bytes.
    """
    pkt = Ether(src=mac, dst="ff:ff:ff:ff:ff:ff") / ARP(
        op="who-has",
        hwsrc=mac,
        psrc=ip,
        hwdst="00:00:00:00:00:00",
        pdst=ip,
    )
    return bytes(pkt)
