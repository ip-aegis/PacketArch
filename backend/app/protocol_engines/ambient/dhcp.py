# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""DHCP DORA sequence builders for ambient network noise.

Builds raw Ethernet frames for the DHCP boot sequence
(Discover-Offer-Request-Acknowledge) that workstations and HMIs
perform at startup.
"""

from __future__ import annotations

import struct

from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

# DHCP magic cookie
_DHCP_MAGIC = b"\x63\x82\x53\x63"

# DHCP message types
_DISCOVER = 1
_OFFER = 2
_REQUEST = 3
_ACK = 5


def _mac_to_chaddr(mac: str) -> bytes:
    """Convert MAC string to 16-byte chaddr field."""
    mac_bytes = bytes.fromhex(mac.replace(":", ""))
    return mac_bytes + b"\x00" * 10  # pad to 16 bytes


def _build_dhcp_options(
    msg_type: int,
    server_ip: str = "",
    requested_ip: str = "",
    subnet_mask: str = "",
    gateway: str = "",
    lease_time: int = 0,
    hostname: str = "",
) -> bytes:
    """Build DHCP options field."""
    opts = bytearray()
    # Option 53: Message Type
    opts += b"\x35\x01" + struct.pack("B", msg_type)

    if hostname:
        name_bytes = hostname.encode("ascii")[:255]
        opts += b"\x0c" + struct.pack("B", len(name_bytes)) + name_bytes

    if requested_ip:
        opts += b"\x32\x04" + _ip_bytes(requested_ip)

    if server_ip:
        opts += b"\x36\x04" + _ip_bytes(server_ip)

    if subnet_mask:
        opts += b"\x01\x04" + _ip_bytes(subnet_mask)

    if gateway:
        opts += b"\x03\x04" + _ip_bytes(gateway)

    if lease_time > 0:
        opts += b"\x33\x04" + struct.pack(">I", lease_time)

    # End option
    opts += b"\xff"
    # Pad to at least 64 bytes (minimum DHCP options)
    if len(opts) < 64:
        opts += b"\x00" * (64 - len(opts))
    return bytes(opts)


def _ip_bytes(ip: str) -> bytes:
    """Convert dotted-quad IP to 4 bytes."""
    return bytes(int(o) for o in ip.split("."))


def _build_dhcp_frame(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    op: int,
    xid: int,
    client_mac: str,
    yiaddr: str = "0.0.0.0",
    siaddr: str = "0.0.0.0",
    options: bytes = b"",
) -> bytes:
    """Build a complete DHCP Ethernet frame."""
    # BOOTP/DHCP payload
    bootp = bytearray(236)
    bootp[0] = op  # 1=BOOTREQUEST, 2=BOOTREPLY
    bootp[1] = 1   # Hardware type: Ethernet
    bootp[2] = 6   # Hardware address length
    bootp[3] = 0   # Hops
    struct.pack_into(">I", bootp, 4, xid)  # Transaction ID
    # yiaddr at offset 16
    if yiaddr != "0.0.0.0":
        bootp[16:20] = _ip_bytes(yiaddr)
    # siaddr at offset 20
    if siaddr != "0.0.0.0":
        bootp[20:24] = _ip_bytes(siaddr)
    # chaddr at offset 28
    bootp[28:44] = _mac_to_chaddr(client_mac)

    payload = bytes(bootp) + _DHCP_MAGIC + options

    pkt = (
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=64)
        / UDP(sport=68 if op == 1 else 67, dport=67 if op == 1 else 68)
        / Raw(load=payload)
    )
    return bytes(pkt)


def build_dhcp_discover(
    client_mac: str,
    xid: int,
    hostname: str = "",
) -> bytes:
    """Build a DHCP Discover broadcast.

    Args:
        client_mac: Client MAC address.
        xid: Transaction ID.
        hostname: Optional hostname for Option 12.

    Returns:
        Raw Ethernet frame bytes.
    """
    options = _build_dhcp_options(msg_type=_DISCOVER, hostname=hostname)
    return _build_dhcp_frame(
        src_mac=client_mac,
        dst_mac="ff:ff:ff:ff:ff:ff",
        src_ip="0.0.0.0",
        dst_ip="255.255.255.255",
        op=1,
        xid=xid,
        client_mac=client_mac,
        options=options,
    )


def build_dhcp_offer(
    server_mac: str,
    server_ip: str,
    client_mac: str,
    offered_ip: str,
    xid: int,
    subnet_mask: str = "255.255.255.0",
    gateway: str = "",
    lease_time: int = 86400,
) -> bytes:
    """Build a DHCP Offer.

    Args:
        server_mac: DHCP server MAC address.
        server_ip: DHCP server IP address.
        client_mac: Client MAC address.
        offered_ip: IP address being offered.
        xid: Transaction ID.
        subnet_mask: Subnet mask.
        gateway: Default gateway.
        lease_time: Lease duration in seconds.

    Returns:
        Raw Ethernet frame bytes.
    """
    options = _build_dhcp_options(
        msg_type=_OFFER,
        server_ip=server_ip,
        subnet_mask=subnet_mask,
        gateway=gateway,
        lease_time=lease_time,
    )
    return _build_dhcp_frame(
        src_mac=server_mac,
        dst_mac="ff:ff:ff:ff:ff:ff",
        src_ip=server_ip,
        dst_ip="255.255.255.255",
        op=2,
        xid=xid,
        client_mac=client_mac,
        yiaddr=offered_ip,
        siaddr=server_ip,
        options=options,
    )


def build_dhcp_request(
    client_mac: str,
    xid: int,
    requested_ip: str,
    server_ip: str,
) -> bytes:
    """Build a DHCP Request broadcast.

    Args:
        client_mac: Client MAC address.
        xid: Transaction ID.
        requested_ip: IP address being requested.
        server_ip: DHCP server IP.

    Returns:
        Raw Ethernet frame bytes.
    """
    options = _build_dhcp_options(
        msg_type=_REQUEST,
        requested_ip=requested_ip,
        server_ip=server_ip,
    )
    return _build_dhcp_frame(
        src_mac=client_mac,
        dst_mac="ff:ff:ff:ff:ff:ff",
        src_ip="0.0.0.0",
        dst_ip="255.255.255.255",
        op=1,
        xid=xid,
        client_mac=client_mac,
        options=options,
    )


def build_dhcp_ack(
    server_mac: str,
    server_ip: str,
    client_mac: str,
    assigned_ip: str,
    xid: int,
    subnet_mask: str = "255.255.255.0",
    gateway: str = "",
    lease_time: int = 86400,
) -> bytes:
    """Build a DHCP ACK.

    Args:
        server_mac: DHCP server MAC address.
        server_ip: DHCP server IP address.
        client_mac: Client MAC address.
        assigned_ip: Assigned IP address.
        xid: Transaction ID.
        subnet_mask: Subnet mask.
        gateway: Default gateway.
        lease_time: Lease duration in seconds.

    Returns:
        Raw Ethernet frame bytes.
    """
    options = _build_dhcp_options(
        msg_type=_ACK,
        server_ip=server_ip,
        subnet_mask=subnet_mask,
        gateway=gateway,
        lease_time=lease_time,
    )
    return _build_dhcp_frame(
        src_mac=server_mac,
        dst_mac="ff:ff:ff:ff:ff:ff",
        src_ip=server_ip,
        dst_ip="255.255.255.255",
        op=2,
        xid=xid,
        client_mac=client_mac,
        yiaddr=assigned_ip,
        siaddr=server_ip,
        options=options,
    )
