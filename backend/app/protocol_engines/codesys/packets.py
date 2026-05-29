# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Codesys packet building utilities.

Implements the Codesys block driver protocol with:
- 8-byte header (magic + length)
- V3 service requests/responses
- V2 legacy commands
- Variable read/write operations
"""

import struct
import random
import zlib

from app.protocol_engines.codesys.types import (
    BLOCK_DRIVER_MAGIC,
    MAX_PAYLOAD_SIZE,
    CodesysService,
    CodesysV2Command,
    CodesysStatus,
    CodesysDataType,
    CodesysDeviceIdentity,
    PLCState,
)


# =============================================================================
# Block Driver Frame Building
# =============================================================================

def build_block_driver_frame(payload: bytes) -> bytes:
    """Build Codesys block driver frame with magic number and length.

    Frame format:
    - Magic (4 bytes): 0xE8170100 (little-endian)
    - Length (4 bytes): Total frame length including header
    - Payload (up to 512 bytes)

    Args:
        payload: PDU payload bytes

    Returns:
        Complete frame bytes
    """
    if len(payload) > MAX_PAYLOAD_SIZE:
        raise ValueError(f"Payload exceeds max size: {len(payload)} > {MAX_PAYLOAD_SIZE}")

    # Total length includes the 8-byte header
    total_length = len(payload) + 8

    # Build header (magic is stored as 0x000117E8 but transmitted as E8 17 01 00)
    header = struct.pack("<II", BLOCK_DRIVER_MAGIC, total_length)

    return header + payload


def parse_block_driver_frame(data: bytes) -> tuple[bool, bytes]:
    """Parse a Codesys block driver frame.

    Args:
        data: Raw frame bytes

    Returns:
        Tuple of (valid, payload)
    """
    if len(data) < 8:
        return False, b""

    magic, length = struct.unpack("<II", data[:8])

    if magic != BLOCK_DRIVER_MAGIC:
        return False, b""

    if len(data) < length:
        return False, b""

    payload = data[8:length]
    return True, payload


# =============================================================================
# V3 PDU Building
# =============================================================================

def build_v3_header(
    service: int,
    session_id: int = 0,
    invoke_id: int = 0,
    data_length: int = 0,
) -> bytes:
    """Build V3 PDU header.

    Format:
    - Service (1 byte)
    - Flags (1 byte)
    - Session ID (4 bytes)
    - Invoke ID (2 bytes)
    - Data Length (2 bytes)

    Args:
        service: Service code
        session_id: Session identifier
        invoke_id: Request invoke ID
        data_length: Length of following data

    Returns:
        10-byte V3 header
    """
    flags = 0x00  # Request
    return struct.pack(
        "<BBIHH",
        service,
        flags,
        session_id,
        invoke_id,
        data_length,
    )


def build_v3_response_header(
    service: int,
    session_id: int,
    invoke_id: int,
    status: int,
    data_length: int = 0,
) -> bytes:
    """Build V3 PDU response header.

    Format:
    - Service (1 byte) with reply bit set (0x80)
    - Status (1 byte)
    - Session ID (4 bytes)
    - Invoke ID (2 bytes)
    - Data Length (2 bytes)

    Args:
        service: Service code
        session_id: Session identifier
        invoke_id: Request invoke ID (echoed)
        status: Response status
        data_length: Length of following data

    Returns:
        10-byte V3 response header
    """
    return struct.pack(
        "<BBIHH",
        service | 0x80,  # Reply bit
        status,
        session_id,
        invoke_id,
        data_length,
    )


# =============================================================================
# Device Information Services
# =============================================================================

def build_device_info_request(session_id: int, invoke_id: int) -> bytes:
    """Build Device Info request.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID

    Returns:
        Complete request PDU
    """
    header = build_v3_header(
        service=CodesysService.DEVICE_INFO,
        session_id=session_id,
        invoke_id=invoke_id,
    )
    return build_block_driver_frame(header)


def build_device_info_response(
    session_id: int,
    invoke_id: int,
    identity: CodesysDeviceIdentity,
    status: int = CodesysStatus.SUCCESS,
) -> bytes:
    """Build Device Info response.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        identity: Device identity information
        status: Response status

    Returns:
        Complete response PDU
    """
    # Build device info data
    data = b""

    # Vendor ID (4 bytes)
    data += struct.pack("<I", identity.vendor_id)

    # Vendor name (length-prefixed string)
    vendor_bytes = identity.vendor_name.encode("utf-8")[:63]
    data += struct.pack("<B", len(vendor_bytes)) + vendor_bytes

    # Device name (length-prefixed string)
    device_bytes = identity.device_name.encode("utf-8")[:63]
    data += struct.pack("<B", len(device_bytes)) + device_bytes

    # Device type (length-prefixed string)
    type_bytes = identity.device_type.encode("utf-8")[:31]
    data += struct.pack("<B", len(type_bytes)) + type_bytes

    # Serial number (length-prefixed string)
    serial_bytes = identity.serial_number.encode("utf-8")[:31]
    data += struct.pack("<B", len(serial_bytes)) + serial_bytes

    # Firmware version (4 bytes: major.minor.patch.build)
    version = identity.get_version_tuple()
    data += struct.pack("<BBBB", *version)

    # Target ID (4 bytes)
    data += struct.pack("<I", identity.target_id)

    # Target type (length-prefixed string)
    target_bytes = identity.target_type.encode("utf-8")[:31]
    data += struct.pack("<B", len(target_bytes)) + target_bytes

    # Build response header
    header = build_v3_response_header(
        service=CodesysService.DEVICE_INFO,
        session_id=session_id,
        invoke_id=invoke_id,
        status=status,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


def build_device_status_request(session_id: int, invoke_id: int) -> bytes:
    """Build Device Status request.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID

    Returns:
        Complete request PDU
    """
    header = build_v3_header(
        service=CodesysService.DEVICE_STATUS,
        session_id=session_id,
        invoke_id=invoke_id,
    )
    return build_block_driver_frame(header)


def build_device_status_response(
    session_id: int,
    invoke_id: int,
    plc_state: PLCState = PLCState.RUNNING,
    status: int = CodesysStatus.SUCCESS,
) -> bytes:
    """Build Device Status response.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        plc_state: Current PLC state
        status: Response status

    Returns:
        Complete response PDU
    """
    # Status data
    data = struct.pack(
        "<BBHI",
        plc_state,         # PLC state (1 byte)
        0,                 # Flags (1 byte)
        0,                 # Error code (2 bytes)
        0,                 # Reserved (4 bytes)
    )

    header = build_v3_response_header(
        service=CodesysService.DEVICE_STATUS,
        session_id=session_id,
        invoke_id=invoke_id,
        status=status,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


# =============================================================================
# Variable Read/Write Services
# =============================================================================

def build_variable_read_request(
    session_id: int,
    invoke_id: int,
    address: int,
    size: int,
    data_type: CodesysDataType = CodesysDataType.DWORD,
) -> bytes:
    """Build Variable Read request.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        address: Memory address to read
        size: Number of bytes to read
        data_type: Data type hint

    Returns:
        Complete request PDU
    """
    # Read specification
    data = struct.pack(
        "<IBH",
        address,      # Address (4 bytes)
        data_type,    # Data type (1 byte)
        size,         # Size (2 bytes)
    )

    header = build_v3_header(
        service=CodesysService.VAR_READ,
        session_id=session_id,
        invoke_id=invoke_id,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


def build_variable_read_response(
    session_id: int,
    invoke_id: int,
    data: bytes,
    status: int = CodesysStatus.SUCCESS,
) -> bytes:
    """Build Variable Read response.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        data: Variable data bytes
        status: Response status

    Returns:
        Complete response PDU
    """
    header = build_v3_response_header(
        service=CodesysService.VAR_READ,
        session_id=session_id,
        invoke_id=invoke_id,
        status=status,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


def build_variable_write_request(
    session_id: int,
    invoke_id: int,
    address: int,
    data: bytes,
    data_type: CodesysDataType = CodesysDataType.DWORD,
) -> bytes:
    """Build Variable Write request.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        address: Memory address to write
        data: Data bytes to write
        data_type: Data type hint

    Returns:
        Complete request PDU
    """
    # Write specification
    spec = struct.pack(
        "<IBH",
        address,          # Address (4 bytes)
        data_type,        # Data type (1 byte)
        len(data),        # Size (2 bytes)
    )

    header = build_v3_header(
        service=CodesysService.VAR_WRITE,
        session_id=session_id,
        invoke_id=invoke_id,
        data_length=len(spec) + len(data),
    )

    return build_block_driver_frame(header + spec + data)


def build_variable_write_response(
    session_id: int,
    invoke_id: int,
    status: int = CodesysStatus.SUCCESS,
) -> bytes:
    """Build Variable Write response.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        status: Response status

    Returns:
        Complete response PDU
    """
    header = build_v3_response_header(
        service=CodesysService.VAR_WRITE,
        session_id=session_id,
        invoke_id=invoke_id,
        status=status,
    )

    return build_block_driver_frame(header)


def build_variable_read_multiple_request(
    session_id: int,
    invoke_id: int,
    variables: list[tuple[int, int, CodesysDataType]],  # (address, size, type)
) -> bytes:
    """Build Multiple Variable Read request.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        variables: List of (address, size, data_type) tuples

    Returns:
        Complete request PDU
    """
    # Number of variables
    data = struct.pack("<H", len(variables))

    # Variable specifications
    for address, size, data_type in variables:
        data += struct.pack("<IBH", address, data_type, size)

    header = build_v3_header(
        service=CodesysService.VAR_READ_MULTIPLE,
        session_id=session_id,
        invoke_id=invoke_id,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


def build_variable_read_multiple_response(
    session_id: int,
    invoke_id: int,
    values: list[bytes],
    status: int = CodesysStatus.SUCCESS,
) -> bytes:
    """Build Multiple Variable Read response.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        values: List of value bytes for each variable
        status: Response status

    Returns:
        Complete response PDU
    """
    # Number of variables
    data = struct.pack("<H", len(values))

    # Value data with per-item status
    for value in values:
        data += struct.pack("<BH", CodesysStatus.SUCCESS, len(value))
        data += value

    header = build_v3_response_header(
        service=CodesysService.VAR_READ_MULTIPLE,
        session_id=session_id,
        invoke_id=invoke_id,
        status=status,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


# =============================================================================
# Authentication Services
# =============================================================================

def build_auth_login_request(
    session_id: int,
    invoke_id: int,
    username: str,
    password: str,
) -> bytes:
    """Build Authentication Login request.

    WARNING: Credentials are transmitted in PLAINTEXT!
    This is a known vulnerability in Codesys (CVE-2018-20026).

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        username: Username (plaintext)
        password: Password (plaintext)

    Returns:
        Complete request PDU
    """
    # Credentials (length-prefixed strings)
    user_bytes = username.encode("utf-8")[:63]
    pass_bytes = password.encode("utf-8")[:63]

    data = struct.pack("<B", len(user_bytes)) + user_bytes
    data += struct.pack("<B", len(pass_bytes)) + pass_bytes

    header = build_v3_header(
        service=CodesysService.AUTH_LOGIN,
        session_id=session_id,
        invoke_id=invoke_id,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


def build_auth_login_response(
    session_id: int,
    invoke_id: int,
    new_session_id: int,
    status: int = CodesysStatus.SUCCESS,
) -> bytes:
    """Build Authentication Login response.

    Args:
        session_id: Original session identifier
        invoke_id: Request invoke ID
        new_session_id: New authenticated session ID
        status: Response status

    Returns:
        Complete response PDU
    """
    data = struct.pack("<I", new_session_id)

    header = build_v3_response_header(
        service=CodesysService.AUTH_LOGIN,
        session_id=session_id,
        invoke_id=invoke_id,
        status=status,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


# =============================================================================
# Application Services
# =============================================================================

def build_app_info_request(session_id: int, invoke_id: int) -> bytes:
    """Build Application Info request.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID

    Returns:
        Complete request PDU
    """
    header = build_v3_header(
        service=CodesysService.APP_INFO,
        session_id=session_id,
        invoke_id=invoke_id,
    )
    return build_block_driver_frame(header)


def build_app_info_response(
    session_id: int,
    invoke_id: int,
    app_name: str = "Application",
    app_version: str = "1.0.0.0",
    status: int = CodesysStatus.SUCCESS,
) -> bytes:
    """Build Application Info response.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        app_name: Application name
        app_version: Application version
        status: Response status

    Returns:
        Complete response PDU
    """
    # Application info
    name_bytes = app_name.encode("utf-8")[:63]
    version_bytes = app_version.encode("utf-8")[:31]

    data = struct.pack("<B", len(name_bytes)) + name_bytes
    data += struct.pack("<B", len(version_bytes)) + version_bytes

    # CRC32 placeholder (for CVE-2020-6081 simulation)
    data += struct.pack("<I", zlib.crc32(name_bytes + version_bytes) & 0xFFFFFFFF)

    header = build_v3_response_header(
        service=CodesysService.APP_INFO,
        session_id=session_id,
        invoke_id=invoke_id,
        status=status,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


# =============================================================================
# Network Scanning Services
# =============================================================================

def build_network_scan_request(session_id: int, invoke_id: int) -> bytes:
    """Build Network Scan request.

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID

    Returns:
        Complete request PDU
    """
    header = build_v3_header(
        service=CodesysService.NETWORK_SCAN,
        session_id=session_id,
        invoke_id=invoke_id,
    )
    return build_block_driver_frame(header)


def build_network_scan_response(
    session_id: int,
    invoke_id: int,
    identity: CodesysDeviceIdentity,
    ip_address: str,
    status: int = CodesysStatus.SUCCESS,
) -> bytes:
    """Build Network Scan response (device announcement).

    Args:
        session_id: Session identifier
        invoke_id: Request invoke ID
        identity: Device identity
        ip_address: Device IP address
        status: Response status

    Returns:
        Complete response PDU
    """
    import socket

    # Build scan response data
    data = struct.pack("<I", identity.vendor_id)

    device_bytes = identity.device_name.encode("utf-8")[:63]
    data += struct.pack("<B", len(device_bytes)) + device_bytes

    serial_bytes = identity.serial_number.encode("utf-8")[:31]
    data += struct.pack("<B", len(serial_bytes)) + serial_bytes

    # IP address
    ip_bytes = socket.inet_aton(ip_address)
    data += ip_bytes

    header = build_v3_response_header(
        service=CodesysService.NETWORK_SCAN,
        session_id=session_id,
        invoke_id=invoke_id,
        status=status,
        data_length=len(data),
    )

    return build_block_driver_frame(header + data)


# =============================================================================
# V2 Legacy Commands
# =============================================================================

def build_v2_request(command: int, data: bytes = b"") -> bytes:
    """Build V2 legacy request.

    V2 format:
    - Command (1 byte)
    - Length (2 bytes)
    - Data

    Args:
        command: V2 command code
        data: Command data

    Returns:
        Complete V2 request (wrapped in block driver frame)
    """
    pdu = struct.pack("<BH", command, len(data)) + data
    return build_block_driver_frame(pdu)


def build_v2_response(
    command: int,
    status: int,
    data: bytes = b"",
) -> bytes:
    """Build V2 legacy response.

    Args:
        command: V2 command code
        status: Response status
        data: Response data

    Returns:
        Complete V2 response (wrapped in block driver frame)
    """
    pdu = struct.pack("<BBH", command | 0x80, status, len(data)) + data
    return build_block_driver_frame(pdu)


def build_v2_get_info_request() -> bytes:
    """Build V2 Get Info request."""
    return build_v2_request(CodesysV2Command.GET_INFO)


def build_v2_get_info_response(
    identity: CodesysDeviceIdentity,
    status: int = CodesysStatus.SUCCESS,
) -> bytes:
    """Build V2 Get Info response."""
    # Simplified V2 device info
    data = identity.device_name.encode("utf-8")[:32].ljust(32, b"\x00")
    data += identity.firmware_version.encode("utf-8")[:16].ljust(16, b"\x00")
    data += identity.serial_number.encode("utf-8")[:16].ljust(16, b"\x00")

    return build_v2_response(CodesysV2Command.GET_INFO, status, data)


# =============================================================================
# TCP/IP Packet Building
# =============================================================================

def build_ethernet_header(src_mac: str, dst_mac: str, ethertype: int = 0x0800) -> bytes:
    """Build Ethernet header."""
    dst_bytes = bytes.fromhex(dst_mac.replace(":", "").replace("-", ""))
    src_bytes = bytes.fromhex(src_mac.replace(":", "").replace("-", ""))
    return dst_bytes + src_bytes + struct.pack(">H", ethertype)


def build_tcp_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    payload: bytes,
    seq: int,
    ack: int,
    flags: str = "PA",
    ttl: int = 64,
    window: int = 65535,
) -> bytes:
    """Build a TCP/IP packet with Ethernet header."""
    import socket

    # Ethernet header
    eth_header = build_ethernet_header(src_mac, dst_mac, 0x0800)

    # IP header
    version_ihl = 0x45
    dscp_ecn = 0x00
    total_length = 20 + 20 + len(payload)
    identification = random.randint(1, 65535)
    flags_fragment = 0x4000
    protocol = 6
    checksum = 0

    src_ip_bytes = socket.inet_aton(src_ip)
    dst_ip_bytes = socket.inet_aton(dst_ip)

    ip_header = struct.pack(
        ">BBHHHBBH4s4s",
        version_ihl,
        dscp_ecn,
        total_length,
        identification,
        flags_fragment,
        ttl,
        protocol,
        checksum,
        src_ip_bytes,
        dst_ip_bytes,
    )

    # TCP header
    data_offset_flags = (5 << 12)
    if "S" in flags:
        data_offset_flags |= 0x02
    if "A" in flags:
        data_offset_flags |= 0x10
    if "P" in flags:
        data_offset_flags |= 0x08
    if "F" in flags:
        data_offset_flags |= 0x01
    if "R" in flags:
        data_offset_flags |= 0x04

    tcp_header = struct.pack(
        ">HHIIHHHH",
        src_port,
        dst_port,
        seq,
        ack,
        data_offset_flags,
        window,
        0,
        0,
    )

    return eth_header + ip_header + tcp_header + payload


def build_tcp_syn(src_mac, dst_mac, src_ip, dst_ip, src_port, dst_port, seq, ttl=64):
    """Build TCP SYN packet."""
    return build_tcp_packet(
        src_mac, dst_mac, src_ip, dst_ip,
        src_port, dst_port, b"", seq, 0, "S", ttl,
    )


def build_tcp_syn_ack(src_mac, dst_mac, src_ip, dst_ip, src_port, dst_port, seq, ack, ttl=64):
    """Build TCP SYN-ACK packet."""
    return build_tcp_packet(
        src_mac, dst_mac, src_ip, dst_ip,
        src_port, dst_port, b"", seq, ack, "SA", ttl,
    )


def build_tcp_ack(src_mac, dst_mac, src_ip, dst_ip, src_port, dst_port, seq, ack, ttl=64):
    """Build TCP ACK packet."""
    return build_tcp_packet(
        src_mac, dst_mac, src_ip, dst_ip,
        src_port, dst_port, b"", seq, ack, "A", ttl,
    )


def build_tcp_fin(src_mac, dst_mac, src_ip, dst_ip, src_port, dst_port, seq, ack, ttl=64):
    """Build TCP FIN packet."""
    return build_tcp_packet(
        src_mac, dst_mac, src_ip, dst_ip,
        src_port, dst_port, b"", seq, ack, "FA", ttl,
    )
