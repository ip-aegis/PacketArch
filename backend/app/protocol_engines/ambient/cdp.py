"""Cisco Discovery Protocol (CDP) frame builder for ambient network noise.

Builds raw Ethernet frames for CDP advertisements that Cisco managed
switches send every 60 seconds.
"""

from __future__ import annotations

import struct

from scapy.layers.l2 import Dot3, LLC, SNAP
from scapy.packet import Raw

# CDP multicast destination MAC
CDP_MULTICAST_MAC = "01:00:0C:CC:CC:CC"

# CDP TLV type codes
_TLV_DEVICE_ID = 0x0001
_TLV_ADDRESSES = 0x0002
_TLV_PORT_ID = 0x0003
_TLV_CAPABILITIES = 0x0004
_TLV_SOFTWARE_VERSION = 0x0005
_TLV_PLATFORM = 0x0006
_TLV_NATIVE_VLAN = 0x000A
_TLV_DUPLEX = 0x000B
_TLV_MANAGEMENT_ADDRESS = 0x0016

# CDP capability bits
CDP_CAP_ROUTER = 0x01
CDP_CAP_TRANSPARENT_BRIDGE = 0x02
CDP_CAP_SOURCE_ROUTE_BRIDGE = 0x04
CDP_CAP_SWITCH = 0x08
CDP_CAP_HOST = 0x10
CDP_CAP_IGMP = 0x20
CDP_CAP_REPEATER = 0x40


def _build_tlv(tlv_type: int, value: bytes) -> bytes:
    """Build a CDP TLV (type-length-value)."""
    length = 4 + len(value)  # type(2) + length(2) + value
    return struct.pack(">HH", tlv_type, length) + value


def _build_address_tlv(ip: str) -> bytes:
    """Build a CDP Addresses TLV with a single IPv4 address."""
    # Number of addresses
    addr_data = struct.pack(">I", 1)
    # Protocol type (1=NLPID), protocol length (1), protocol (0xCC=IP)
    addr_data += struct.pack("BBB", 1, 1, 0xCC)
    # Address length + address
    ip_bytes = bytes(int(o) for o in ip.split("."))
    addr_data += struct.pack(">H", 4) + ip_bytes
    return _build_tlv(_TLV_ADDRESSES, addr_data)


def _checksum(data: bytes) -> int:
    """Compute CDP checksum (one's complement of 16-bit sum)."""
    if len(data) % 2:
        data = data + b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) + data[i + 1]
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return (~total) & 0xFFFF


def build_cdp_frame(
    src_mac: str,
    device_id: str,
    ip_address: str,
    port_id: str = "GigabitEthernet0/1",
    platform: str = "cisco IE-4010-16S12P",
    software_version: str = "Cisco IOS Software, IE4010 Software, Version 15.2(7)E",
    capabilities: int = CDP_CAP_ROUTER | CDP_CAP_SWITCH | CDP_CAP_IGMP,
    vlan_id: int | None = None,
    ttl: int = 180,
) -> bytes:
    """Build a Cisco Discovery Protocol frame.

    Args:
        src_mac: Source MAC address.
        device_id: Device hostname/ID.
        ip_address: Management IP address.
        port_id: Port identifier string.
        platform: Platform description.
        software_version: Software version string.
        capabilities: Capability bitmap.
        vlan_id: Native VLAN ID (optional).
        ttl: Time-to-live in seconds.

    Returns:
        Raw Ethernet frame bytes.
    """
    # Build TLV payload
    tlvs = bytearray()
    tlvs += _build_tlv(_TLV_DEVICE_ID, device_id.encode("ascii"))
    tlvs += _build_address_tlv(ip_address)
    tlvs += _build_tlv(_TLV_PORT_ID, port_id.encode("ascii"))
    tlvs += _build_tlv(_TLV_CAPABILITIES, struct.pack(">I", capabilities))
    tlvs += _build_tlv(_TLV_SOFTWARE_VERSION, software_version.encode("ascii"))
    tlvs += _build_tlv(_TLV_PLATFORM, platform.encode("ascii"))

    if vlan_id is not None:
        tlvs += _build_tlv(_TLV_NATIVE_VLAN, struct.pack(">H", vlan_id))

    # Duplex: full (0x01)
    tlvs += _build_tlv(_TLV_DUPLEX, b"\x01")

    # CDP header: version (1 byte) + TTL (1 byte) + checksum (2 bytes)
    header = struct.pack("BB", 0x02, ttl)  # CDPv2
    # Checksum placeholder
    header += struct.pack(">H", 0x0000)
    # Calculate checksum over header + TLVs
    cdp_payload = bytearray(header) + tlvs
    cksum = _checksum(bytes(cdp_payload))
    struct.pack_into(">H", cdp_payload, 2, cksum)

    # Build Ethernet frame with LLC/SNAP encapsulation
    # CDP uses 802.3 framing: Dot3 + LLC + SNAP(OUI=00:00:0C, code=0x2000)
    pkt = (
        Dot3(src=src_mac, dst=CDP_MULTICAST_MAC)
        / LLC(dsap=0xAA, ssap=0xAA, ctrl=0x03)
        / SNAP(OUI=0x00000C, code=0x2000)
        / Raw(load=bytes(cdp_payload))
    )
    return bytes(pkt)
