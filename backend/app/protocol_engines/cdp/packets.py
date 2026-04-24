# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""CDP (Cisco Discovery Protocol) packet building utilities.

CDP is a Layer 2 protocol for discovering Cisco devices on the network.
Uses LLC/SNAP encapsulation with Cisco's OUI.

Frame structure:
- Ethernet header (dest: 01:00:0c:cc:cc:cc multicast)
- LLC header (DSAP=0xAA, SSAP=0xAA, Control=0x03)
- SNAP header (OUI=0x00000c, Protocol=0x2000)
- CDP header (version, TTL, checksum)
- TLV data
"""

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Any


# CDP Constants
CDP_MULTICAST_MAC = "01:00:0c:cc:cc:cc"
CDP_LLC_HEADER = bytes([0xAA, 0xAA, 0x03])  # DSAP, SSAP, Control
CDP_SNAP_OUI = bytes([0x00, 0x00, 0x0C])  # Cisco OUI
CDP_SNAP_PROTOCOL = bytes([0x20, 0x00])  # CDP protocol ID

# CDP Versions
CDP_VERSION_1 = 0x01
CDP_VERSION_2 = 0x02

# Default timing
CDP_DEFAULT_TTL = 180  # seconds
CDP_DEFAULT_INTERVAL = 60  # seconds


class CDPTLVType(IntEnum):
    """CDP TLV type codes."""

    DEVICE_ID = 0x0001
    ADDRESSES = 0x0002
    PORT_ID = 0x0003
    CAPABILITIES = 0x0004
    SOFTWARE_VERSION = 0x0005
    PLATFORM = 0x0006
    IP_PREFIX = 0x0007
    PROTOCOL_HELLO = 0x0008
    VTP_DOMAIN = 0x0009
    NATIVE_VLAN = 0x000A
    DUPLEX = 0x000B
    VOIP_VLAN_REPLY = 0x000E
    VOIP_VLAN_QUERY = 0x000F
    POWER_CONSUMPTION = 0x0010
    MTU = 0x0011
    TRUST_BITMAP = 0x0012
    UNTRUSTED_COS = 0x0013
    SYSTEM_NAME = 0x0014
    SYSTEM_OID = 0x0015
    MANAGEMENT_ADDR = 0x0016
    LOCATION = 0x0017
    EXTERNAL_PORT_ID = 0x0018
    POWER_REQUEST = 0x0019
    POWER_AVAILABLE = 0x001A


class CDPCapability(IntEnum):
    """CDP capability flags (bitmask)."""

    ROUTER = 0x01
    TRANSPARENT_BRIDGE = 0x02
    SOURCE_ROUTE_BRIDGE = 0x04
    SWITCH = 0x08
    HOST = 0x10
    IGMP_CAPABLE = 0x20
    REPEATER = 0x40
    VOIP_PHONE = 0x80


class CDPAddressProtocol(IntEnum):
    """CDP address protocol types."""

    NLPID = 0x01  # ISO/CCITT
    IPV4 = 0xCC  # IPv4 address
    IPV6 = 0xDD  # IPv6 address (unofficial but used)


@dataclass
class CDPAddress:
    """CDP address entry."""

    protocol: CDPAddressProtocol
    address: bytes  # Raw address bytes (4 for IPv4, 16 for IPv6)

    def pack(self) -> bytes:
        """Pack address entry for CDP packet."""
        # Protocol type (1 byte) + length (1 byte) + address data
        return bytes([self.protocol, len(self.address)]) + self.address

    @classmethod
    def from_ipv4(cls, ip_str: str) -> "CDPAddress":
        """Create address from IPv4 string."""
        parts = [int(p) for p in ip_str.split(".")]
        return cls(protocol=CDPAddressProtocol.IPV4, address=bytes(parts))


def calculate_cdp_checksum(data: bytes) -> int:
    """Calculate CDP checksum using ones-complement addition.

    CDP uses RFC 1071 style checksum with odd-length padding.

    Args:
        data: CDP packet data (with checksum field zeroed)

    Returns:
        16-bit checksum value
    """
    # Pad if odd length
    if len(data) % 2:
        data = data + b"\x00"

    # Sum 16-bit words
    checksum = 0
    for i in range(0, len(data), 2):
        word = int.from_bytes(data[i : i + 2], byteorder="big", signed=False)
        checksum += word
        # End-around carry for ones-complement
        while checksum > 0xFFFF:
            checksum = (checksum & 0xFFFF) + (checksum >> 16)

    # Return ones-complement
    return (~checksum) & 0xFFFF


def build_tlv(tlv_type: CDPTLVType, value: bytes) -> bytes:
    """Build a CDP TLV (Type-Length-Value) entry.

    Args:
        tlv_type: TLV type code
        value: TLV value data

    Returns:
        Complete TLV bytes including type and length header
    """
    # Length includes Type (2) + Length (2) + Value
    length = 4 + len(value)
    header = struct.pack("!HH", tlv_type, length)
    return header + value


def build_device_id_tlv(device_id: str) -> bytes:
    """Build Device ID TLV (0x0001).

    Args:
        device_id: Device hostname/identifier

    Returns:
        Device ID TLV bytes
    """
    return build_tlv(CDPTLVType.DEVICE_ID, device_id.encode("ascii"))


def build_addresses_tlv(addresses: list[CDPAddress]) -> bytes:
    """Build Addresses TLV (0x0002).

    Args:
        addresses: List of CDPAddress entries

    Returns:
        Addresses TLV bytes
    """
    # Number of addresses (4 bytes for CDP)
    value = struct.pack("!I", len(addresses))
    for addr in addresses:
        value += addr.pack()
    return build_tlv(CDPTLVType.ADDRESSES, value)


def build_port_id_tlv(port_id: str) -> bytes:
    """Build Port ID TLV (0x0003).

    Args:
        port_id: Interface name (e.g., "GigabitEthernet0/1")

    Returns:
        Port ID TLV bytes
    """
    return build_tlv(CDPTLVType.PORT_ID, port_id.encode("ascii"))


def build_capabilities_tlv(capabilities: int) -> bytes:
    """Build Capabilities TLV (0x0004).

    Args:
        capabilities: Bitmask of CDPCapability flags

    Returns:
        Capabilities TLV bytes
    """
    return build_tlv(CDPTLVType.CAPABILITIES, struct.pack("!I", capabilities))


def build_software_version_tlv(version: str) -> bytes:
    """Build Software Version TLV (0x0005).

    Args:
        version: Software/firmware version string

    Returns:
        Software Version TLV bytes
    """
    return build_tlv(CDPTLVType.SOFTWARE_VERSION, version.encode("ascii"))


def build_platform_tlv(platform: str) -> bytes:
    """Build Platform TLV (0x0006).

    Args:
        platform: Hardware platform string (e.g., "Catalyst 2960X")

    Returns:
        Platform TLV bytes
    """
    return build_tlv(CDPTLVType.PLATFORM, platform.encode("ascii"))


def build_vtp_domain_tlv(domain: str) -> bytes:
    """Build VTP Management Domain TLV (0x0009).

    Args:
        domain: VTP domain name

    Returns:
        VTP Domain TLV bytes
    """
    return build_tlv(CDPTLVType.VTP_DOMAIN, domain.encode("ascii"))


def build_native_vlan_tlv(vlan_id: int) -> bytes:
    """Build Native VLAN TLV (0x000A).

    Args:
        vlan_id: Native VLAN ID (1-4094)

    Returns:
        Native VLAN TLV bytes
    """
    return build_tlv(CDPTLVType.NATIVE_VLAN, struct.pack("!H", vlan_id))


def build_duplex_tlv(full_duplex: bool) -> bytes:
    """Build Duplex TLV (0x000B).

    Args:
        full_duplex: True for full-duplex, False for half-duplex

    Returns:
        Duplex TLV bytes
    """
    return build_tlv(CDPTLVType.DUPLEX, bytes([0x01 if full_duplex else 0x00]))


def build_power_consumption_tlv(power_mw: int) -> bytes:
    """Build Power Consumption TLV (0x0010).

    Args:
        power_mw: Power consumption in milliwatts

    Returns:
        Power Consumption TLV bytes
    """
    return build_tlv(CDPTLVType.POWER_CONSUMPTION, struct.pack("!H", power_mw))


def build_mtu_tlv(mtu: int) -> bytes:
    """Build MTU TLV (0x0011).

    Args:
        mtu: Maximum transmission unit in bytes

    Returns:
        MTU TLV bytes
    """
    return build_tlv(CDPTLVType.MTU, struct.pack("!I", mtu))


def build_trust_bitmap_tlv(trusted: bool) -> bytes:
    """Build Trust Bitmap TLV (0x0012).

    Args:
        trusted: True if port is trusted

    Returns:
        Trust Bitmap TLV bytes
    """
    return build_tlv(CDPTLVType.TRUST_BITMAP, bytes([0x01 if trusted else 0x00]))


def build_management_addr_tlv(addresses: list[CDPAddress]) -> bytes:
    """Build Management Address TLV (0x0016).

    Args:
        addresses: List of management addresses

    Returns:
        Management Address TLV bytes
    """
    # Same format as addresses TLV
    value = struct.pack("!I", len(addresses))
    for addr in addresses:
        value += addr.pack()
    return build_tlv(CDPTLVType.MANAGEMENT_ADDR, value)


def build_location_tlv(location: str) -> bytes:
    """Build Location TLV (0x0017).

    Args:
        location: Physical location string

    Returns:
        Location TLV bytes
    """
    return build_tlv(CDPTLVType.LOCATION, location.encode("ascii"))


def build_system_name_tlv(name: str) -> bytes:
    """Build System Name TLV (0x0014).

    Args:
        name: System name

    Returns:
        System Name TLV bytes
    """
    return build_tlv(CDPTLVType.SYSTEM_NAME, name.encode("ascii"))


def build_voip_vlan_reply_tlv(vlan_id: int) -> bytes:
    """Build VoIP VLAN Reply TLV (0x000E).

    Args:
        vlan_id: Voice VLAN ID

    Returns:
        VoIP VLAN Reply TLV bytes
    """
    # Format: 1 byte data + 2 byte VLAN ID
    return build_tlv(CDPTLVType.VOIP_VLAN_REPLY, bytes([0x01]) + struct.pack("!H", vlan_id))


def build_cdp_header(version: int, ttl: int, checksum: int) -> bytes:
    """Build CDP header.

    Args:
        version: CDP version (1 or 2)
        ttl: Time to live in seconds
        checksum: Calculated checksum

    Returns:
        CDP header bytes (4 bytes)
    """
    return struct.pack("!BBH", version, ttl, checksum)


def build_cdp_packet(
    version: int = CDP_VERSION_2,
    ttl: int = CDP_DEFAULT_TTL,
    tlvs: list[bytes] | None = None,
) -> bytes:
    """Build complete CDP packet payload (without Ethernet/LLC headers).

    Args:
        version: CDP version (default 2)
        ttl: Time to live in seconds (default 180)
        tlvs: List of TLV bytes to include

    Returns:
        Complete CDP packet bytes
    """
    if tlvs is None:
        tlvs = []

    # Build TLV data
    tlv_data = b"".join(tlvs)

    # Build header with zeroed checksum for calculation
    header_no_checksum = struct.pack("!BBH", version, ttl, 0x0000)
    full_packet = header_no_checksum + tlv_data

    # Calculate checksum
    checksum = calculate_cdp_checksum(full_packet)

    # Rebuild header with checksum
    header = build_cdp_header(version, ttl, checksum)

    return header + tlv_data


def build_llc_snap_header() -> bytes:
    """Build LLC/SNAP header for CDP.

    Returns:
        LLC/SNAP header bytes (8 bytes)
    """
    return CDP_LLC_HEADER + CDP_SNAP_OUI + CDP_SNAP_PROTOCOL


def build_ethernet_header(
    src_mac: str,
    dst_mac: str = CDP_MULTICAST_MAC,
) -> bytes:
    """Build Ethernet header for CDP frame.

    Args:
        src_mac: Source MAC address (colon-separated)
        dst_mac: Destination MAC address (default CDP multicast)

    Returns:
        Ethernet header bytes (14 bytes with length field)
    """

    def mac_to_bytes(mac: str) -> bytes:
        return bytes.fromhex(mac.replace(":", "").replace("-", ""))

    dst = mac_to_bytes(dst_mac)
    src = mac_to_bytes(src_mac)

    # For LLC frames, we need length field instead of EtherType
    # Length will be filled in by the caller based on payload size
    return dst + src


def build_cdp_frame(
    src_mac: str,
    device_id: str,
    port_id: str,
    addresses: list[str] | None = None,
    capabilities: int = CDPCapability.SWITCH,
    software_version: str = "Cisco IOS Software",
    platform: str = "Cisco Device",
    native_vlan: int | None = None,
    vtp_domain: str | None = None,
    full_duplex: bool = True,
    management_addresses: list[str] | None = None,
    version: int = CDP_VERSION_2,
    ttl: int = CDP_DEFAULT_TTL,
) -> bytes:
    """Build complete CDP Ethernet frame.

    Args:
        src_mac: Source MAC address
        device_id: Device hostname/identifier
        port_id: Interface name
        addresses: List of IPv4 addresses (strings)
        capabilities: Capability bitmask
        software_version: Software version string
        platform: Hardware platform string
        native_vlan: Native VLAN ID (optional)
        vtp_domain: VTP domain name (optional)
        full_duplex: Duplex mode
        management_addresses: Management IP addresses (optional)
        version: CDP version (default 2)
        ttl: TTL in seconds (default 180)

    Returns:
        Complete CDP Ethernet frame bytes
    """
    # Build TLVs
    tlvs = [
        build_device_id_tlv(device_id),
        build_port_id_tlv(port_id),
    ]

    # Add addresses
    if addresses:
        addr_list = [CDPAddress.from_ipv4(ip) for ip in addresses]
        tlvs.append(build_addresses_tlv(addr_list))

    # Required TLVs
    tlvs.append(build_capabilities_tlv(capabilities))
    tlvs.append(build_software_version_tlv(software_version))
    tlvs.append(build_platform_tlv(platform))

    # Optional CDPv2 TLVs
    if version == CDP_VERSION_2:
        if native_vlan is not None:
            tlvs.append(build_native_vlan_tlv(native_vlan))
        if vtp_domain:
            tlvs.append(build_vtp_domain_tlv(vtp_domain))
        tlvs.append(build_duplex_tlv(full_duplex))

    # Management addresses
    if management_addresses:
        mgmt_list = [CDPAddress.from_ipv4(ip) for ip in management_addresses]
        tlvs.append(build_management_addr_tlv(mgmt_list))

    # Build CDP packet
    cdp_payload = build_cdp_packet(version=version, ttl=ttl, tlvs=tlvs)

    # Build LLC/SNAP header
    llc_snap = build_llc_snap_header()

    # Full payload (LLC/SNAP + CDP)
    full_payload = llc_snap + cdp_payload

    # Build Ethernet header
    eth_header = build_ethernet_header(src_mac)

    # Add length field (2 bytes, big-endian) for 802.3 frame
    length_field = struct.pack("!H", len(full_payload))

    return eth_header + length_field + full_payload


def build_cdp_advertisement(
    src_mac: str,
    src_ip: str,
    device_config: dict[str, Any],
) -> bytes:
    """Build CDP advertisement frame from device configuration.

    Args:
        src_mac: Source MAC address
        src_ip: Source IP address
        device_config: Device configuration dictionary with optional keys:
            - device_id: Device hostname (default: derived from MAC)
            - port_id: Port name (default: "Ethernet0")
            - capabilities: Capability flags (default: SWITCH)
            - software_version: Software version (default: "Cisco IOS")
            - platform: Hardware platform (default: "Cisco Device")
            - native_vlan: Native VLAN ID
            - vtp_domain: VTP domain name
            - full_duplex: Duplex mode (default: True)
            - management_ip: Management IP address

    Returns:
        Complete CDP frame bytes
    """
    # Extract configuration with defaults
    device_id = device_config.get("device_id", f"Device-{src_mac[-8:].replace(':', '')}")
    port_id = device_config.get("port_id", "Ethernet0")
    capabilities = device_config.get("capabilities", CDPCapability.SWITCH)
    software_version = device_config.get(
        "software_version", "Cisco IOS Software, Version 15.2(4)M1"
    )
    platform = device_config.get("platform", "Cisco Device")
    native_vlan = device_config.get("native_vlan")
    vtp_domain = device_config.get("vtp_domain")
    full_duplex = device_config.get("full_duplex", True)
    management_ip = device_config.get("management_ip")

    # Build addresses list
    addresses = [src_ip] if src_ip else None
    management_addresses = [management_ip] if management_ip else None

    return build_cdp_frame(
        src_mac=src_mac,
        device_id=device_id,
        port_id=port_id,
        addresses=addresses,
        capabilities=capabilities,
        software_version=software_version,
        platform=platform,
        native_vlan=native_vlan,
        vtp_domain=vtp_domain,
        full_duplex=full_duplex,
        management_addresses=management_addresses,
    )
