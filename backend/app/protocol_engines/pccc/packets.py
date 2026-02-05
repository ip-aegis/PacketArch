"""PCCC/DF1 packet building utilities.

Builds packets for:
- PCCC over TCP (port 2222) - Legacy SLC-5/05, PLC-5E
- PCCC over EtherNet/IP (port 44818) - Modern devices
- DF1 serial frames (for reference/logging)
"""

import struct
import random
from typing import Any

from app.protocol_engines.pccc.types import (
    PCCC_TCP_PORT,
    ETHERNET_IP_PORT,
    DF1FrameChar,
    PCCCCommand,
    PCCCFunction,
    PCCCStatus,
    PCCCFileType,
    PCCCAddress,
    PCCCDeviceIdentity,
    ABDeviceType,
    AB_VENDOR_ID,
)


# =============================================================================
# PCCC Packet Building (Core Protocol)
# =============================================================================

def build_pccc_header(
    command: int,
    status: int,
    transaction_id: int,
    function: int | None = None,
) -> bytes:
    """Build PCCC header.

    Format:
    - CMD (1 byte): Command code
    - STS (1 byte): Status (0x00 for requests)
    - TNSW (2 bytes): Transaction sequence word (little-endian)
    - FNC (1 byte, optional): Function code

    Args:
        command: PCCC command code
        status: Status code (0x00 for requests)
        transaction_id: Transaction sequence word
        function: Optional function code

    Returns:
        PCCC header bytes
    """
    header = struct.pack(
        "<BBH",
        command,
        status,
        transaction_id,
    )

    if function is not None:
        header += bytes([function])

    return header


def build_pccc_request(
    command: int,
    transaction_id: int,
    function: int | None = None,
    data: bytes = b"",
) -> bytes:
    """Build complete PCCC request.

    Args:
        command: PCCC command code
        transaction_id: Transaction sequence word
        function: Optional function code
        data: PCCC data payload

    Returns:
        Complete PCCC request bytes
    """
    header = build_pccc_header(command, 0x00, transaction_id, function)
    return header + data


def build_pccc_response(
    command: int,
    transaction_id: int,
    status: int = PCCCStatus.SUCCESS,
    function: int | None = None,
    data: bytes = b"",
    extended_status: int | None = None,
) -> bytes:
    """Build PCCC response.

    Args:
        command: PCCC command code (echoed from request)
        transaction_id: Transaction sequence word (echoed)
        status: Status code
        function: Optional function code
        data: Response data
        extended_status: Extended status code (if status indicates)

    Returns:
        Complete PCCC response bytes
    """
    header = build_pccc_header(command, status, transaction_id, function)

    if extended_status is not None:
        header += bytes([extended_status])

    return header + data


# =============================================================================
# PCCC Commands
# =============================================================================

def build_diagnostic_status_request(transaction_id: int) -> bytes:
    """Build Diagnostic Status request (CMD 0x03).

    Returns basic PLC status and identity information.

    Args:
        transaction_id: Transaction sequence word

    Returns:
        PCCC diagnostic request bytes
    """
    return build_pccc_request(
        command=PCCCCommand.DIAGNOSTIC_STATUS,
        transaction_id=transaction_id,
    )


def build_diagnostic_status_response(
    transaction_id: int,
    identity: PCCCDeviceIdentity,
    status: int = PCCCStatus.SUCCESS,
) -> bytes:
    """Build Diagnostic Status response.

    Args:
        transaction_id: Transaction sequence word
        identity: Device identity information
        status: Status code

    Returns:
        PCCC diagnostic response bytes
    """
    # Build status data (varies by device, simplified version)
    data = struct.pack(
        "<HHHBBIH32s",
        identity.vendor_id,                    # Vendor ID
        identity.device_type,                  # Device type
        identity.product_code,                 # Product code
        identity.revision_major,               # Major revision
        identity.revision_minor,               # Minor revision
        identity.serial_number,                # Serial number
        len(identity.product_name),            # Product name length
        identity.product_name.encode("ascii").ljust(32, b"\x00"),  # Product name
    )

    return build_pccc_response(
        command=PCCCCommand.DIAGNOSTIC_STATUS,
        transaction_id=transaction_id,
        status=status,
        data=data,
    )


def build_echo_request(transaction_id: int, echo_data: bytes = b"PCCC") -> bytes:
    """Build Echo request (CMD 0x06).

    Args:
        transaction_id: Transaction sequence word
        echo_data: Data to echo back

    Returns:
        PCCC echo request bytes
    """
    return build_pccc_request(
        command=PCCCCommand.ECHO,
        transaction_id=transaction_id,
        data=echo_data,
    )


def build_echo_response(
    transaction_id: int,
    echo_data: bytes,
    status: int = PCCCStatus.SUCCESS,
) -> bytes:
    """Build Echo response.

    Args:
        transaction_id: Transaction sequence word
        echo_data: Echoed data
        status: Status code

    Returns:
        PCCC echo response bytes
    """
    return build_pccc_response(
        command=PCCCCommand.ECHO,
        transaction_id=transaction_id,
        status=status,
        data=echo_data,
    )


def build_protected_typed_read_request(
    transaction_id: int,
    address: PCCCAddress,
    num_elements: int = 1,
) -> bytes:
    """Build Protected Typed Logical Read request (CMD 0x0F, FNC 0xA2).

    Uses 3 address fields: file_type, file_number, element/subelement.

    Args:
        transaction_id: Transaction sequence word
        address: PCCC address to read
        num_elements: Number of elements to read

    Returns:
        PCCC read request bytes
    """
    # Build address fields
    # Format: byte_size, file_number, file_type, element_number, subelement
    data = struct.pack(
        "<BBBHB",
        num_elements * 2,          # Byte size (2 bytes per integer)
        address.file_number,       # File number
        address.file_type,         # File type
        address.element,           # Element number
        address.subelement,        # Subelement
    )

    return build_pccc_request(
        command=PCCCCommand.WORD_RANGE_READ,
        transaction_id=transaction_id,
        function=PCCCFunction.PROTECTED_TYPED_READ_3ADDR,
        data=data,
    )


def build_protected_typed_read_response(
    transaction_id: int,
    values: list[int],
    status: int = PCCCStatus.SUCCESS,
) -> bytes:
    """Build Protected Typed Logical Read response.

    Args:
        transaction_id: Transaction sequence word
        values: List of integer values read
        status: Status code

    Returns:
        PCCC read response bytes
    """
    # Pack values as little-endian 16-bit integers
    data = b"".join(struct.pack("<H", v & 0xFFFF) for v in values)

    return build_pccc_response(
        command=PCCCCommand.WORD_RANGE_READ,
        transaction_id=transaction_id,
        status=status,
        function=PCCCFunction.PROTECTED_TYPED_READ_3ADDR,
        data=data,
    )


def build_protected_typed_write_request(
    transaction_id: int,
    address: PCCCAddress,
    values: list[int],
) -> bytes:
    """Build Protected Typed Logical Write request (CMD 0x0F, FNC 0xAA).

    Args:
        transaction_id: Transaction sequence word
        address: PCCC address to write
        values: Values to write

    Returns:
        PCCC write request bytes
    """
    # Build address fields
    data = struct.pack(
        "<BBBHB",
        len(values) * 2,           # Byte size
        address.file_number,       # File number
        address.file_type,         # File type
        address.element,           # Element number
        address.subelement,        # Subelement
    )

    # Add values
    data += b"".join(struct.pack("<H", v & 0xFFFF) for v in values)

    return build_pccc_request(
        command=PCCCCommand.WORD_RANGE_WRITE,
        transaction_id=transaction_id,
        function=PCCCFunction.PROTECTED_TYPED_WRITE_3ADDR,
        data=data,
    )


def build_protected_typed_write_response(
    transaction_id: int,
    status: int = PCCCStatus.SUCCESS,
) -> bytes:
    """Build Protected Typed Logical Write response.

    Args:
        transaction_id: Transaction sequence word
        status: Status code

    Returns:
        PCCC write response bytes
    """
    return build_pccc_response(
        command=PCCCCommand.WORD_RANGE_WRITE,
        transaction_id=transaction_id,
        status=status,
        function=PCCCFunction.PROTECTED_TYPED_WRITE_3ADDR,
    )


def build_unprotected_read_request(
    transaction_id: int,
    address: int,
    size: int,
) -> bytes:
    """Build Unprotected Read request (CMD 0x01).

    Reads from the common interface file (File 9).

    Args:
        transaction_id: Transaction sequence word
        address: Byte address in file 9
        size: Number of bytes to read

    Returns:
        PCCC unprotected read request bytes
    """
    data = struct.pack("<HB", address, size)

    return build_pccc_request(
        command=PCCCCommand.UNPROTECTED_READ,
        transaction_id=transaction_id,
        data=data,
    )


def build_unprotected_read_response(
    transaction_id: int,
    data: bytes,
    status: int = PCCCStatus.SUCCESS,
) -> bytes:
    """Build Unprotected Read response.

    Args:
        transaction_id: Transaction sequence word
        data: Data read from file 9
        status: Status code

    Returns:
        PCCC unprotected read response bytes
    """
    return build_pccc_response(
        command=PCCCCommand.UNPROTECTED_READ,
        transaction_id=transaction_id,
        status=status,
        data=data,
    )


# =============================================================================
# PCCC over TCP Encapsulation
# =============================================================================

def build_pccc_tcp_header(pccc_length: int) -> bytes:
    """Build PCCC over TCP encapsulation header.

    CSPv4 (Client-Server Protocol v4) header format:
    - Length (2 bytes, big-endian): Total message length

    Args:
        pccc_length: Length of PCCC payload

    Returns:
        TCP encapsulation header bytes
    """
    return struct.pack(">H", pccc_length)


def build_pccc_tcp_packet(pccc_data: bytes) -> bytes:
    """Build complete PCCC over TCP packet.

    Args:
        pccc_data: PCCC message bytes

    Returns:
        TCP-encapsulated PCCC packet
    """
    header = build_pccc_tcp_header(len(pccc_data))
    return header + pccc_data


# =============================================================================
# PCCC over EtherNet/IP Encapsulation
# =============================================================================

# EtherNet/IP Encapsulation Commands
EIP_REGISTER_SESSION = 0x0065
EIP_UNREGISTER_SESSION = 0x0066
EIP_SEND_RR_DATA = 0x006F
EIP_SEND_UNIT_DATA = 0x0070


def build_eip_header(
    command: int,
    session_handle: int = 0,
    sender_context: bytes = b"\x00" * 8,
    data_length: int = 0,
) -> bytes:
    """Build EtherNet/IP encapsulation header.

    Args:
        command: Encapsulation command
        session_handle: Session handle
        sender_context: 8-byte sender context
        data_length: Length of command-specific data

    Returns:
        24-byte EtherNet/IP header
    """
    return struct.pack(
        "<HHII8sI",
        command,           # Command (2 bytes)
        data_length,       # Length (2 bytes)
        session_handle,    # Session handle (4 bytes)
        0,                 # Status (4 bytes) - always 0 for requests
        sender_context[:8].ljust(8, b"\x00"),  # Sender context (8 bytes)
        0,                 # Options (4 bytes)
    )


def build_eip_register_session_request() -> bytes:
    """Build EtherNet/IP Register Session request.

    Returns:
        Complete Register Session request
    """
    # Command-specific data
    data = struct.pack(
        "<HH",
        1,  # Protocol version
        0,  # Options flags
    )

    header = build_eip_header(
        command=EIP_REGISTER_SESSION,
        data_length=len(data),
    )

    return header + data


def build_eip_register_session_response(session_handle: int) -> bytes:
    """Build EtherNet/IP Register Session response.

    Args:
        session_handle: Assigned session handle

    Returns:
        Complete Register Session response
    """
    data = struct.pack(
        "<HH",
        1,  # Protocol version
        0,  # Options flags
    )

    header = build_eip_header(
        command=EIP_REGISTER_SESSION,
        session_handle=session_handle,
        data_length=len(data),
    )

    return header + data


def build_eip_unregister_session_request(session_handle: int) -> bytes:
    """Build EtherNet/IP Unregister Session request.

    Args:
        session_handle: Session handle to unregister

    Returns:
        Complete Unregister Session request
    """
    return build_eip_header(
        command=EIP_UNREGISTER_SESSION,
        session_handle=session_handle,
    )


def build_eip_send_rr_data(
    session_handle: int,
    pccc_data: bytes,
    sender_context: bytes = b"\x00" * 8,
) -> bytes:
    """Build EtherNet/IP SendRRData with PCCC payload.

    Used for unconnected PCCC messaging over EtherNet/IP.

    Args:
        session_handle: Session handle
        pccc_data: PCCC message bytes
        sender_context: Sender context for correlation

    Returns:
        Complete SendRRData packet
    """
    # CPF (Common Packet Format) with 2 items:
    # Item 0: Null Address (type 0x0000)
    # Item 1: Unconnected Data (type 0x00B2)

    # Interface handle (0 for CIP) + timeout (0)
    cpf_prefix = struct.pack("<IH", 0, 0)

    # Item count
    item_count = struct.pack("<H", 2)

    # Null Address item
    null_addr = struct.pack("<HH", 0x0000, 0)

    # Unconnected Data item with PCCC
    # Wrap PCCC in "Execute PCCC" CIP service (0x4B)
    cip_service = 0x4B
    cip_path = bytes([
        0x01,  # Path size (1 word = 2 bytes)
        0x00,  # Padding
        0x01,  # Class segment (8-bit)
        0xF0,  # Class 0xF0 (PCCC Object)
    ])

    cip_data = bytes([cip_service]) + cip_path + pccc_data
    unconnected_data = struct.pack("<HH", 0x00B2, len(cip_data)) + cip_data

    # Combine CPF
    cpf_data = cpf_prefix + item_count + null_addr + unconnected_data

    # Build header
    header = build_eip_header(
        command=EIP_SEND_RR_DATA,
        session_handle=session_handle,
        sender_context=sender_context,
        data_length=len(cpf_data),
    )

    return header + cpf_data


def parse_eip_send_rr_data_response(data: bytes) -> tuple[int, bytes]:
    """Parse EtherNet/IP SendRRData response.

    Args:
        data: Response data (after header)

    Returns:
        Tuple of (status, pccc_data)
    """
    # Skip interface handle (4) and timeout (2)
    offset = 6

    # Item count
    item_count = struct.unpack_from("<H", data, offset)[0]
    offset += 2

    pccc_data = b""
    status = 0

    for _ in range(item_count):
        item_type, item_length = struct.unpack_from("<HH", data, offset)
        offset += 4

        if item_type == 0x00B2:  # Unconnected Data
            # Skip CIP service response header
            cip_reply_service = data[offset]
            # Check for error
            if cip_reply_service & 0x80:  # Reply bit set
                status = data[offset + 2]  # General status
                pccc_data = data[offset + 4:offset + item_length]
            else:
                pccc_data = data[offset + 4:offset + item_length]

        offset += item_length

    return status, pccc_data


# =============================================================================
# TCP/IP Packet Building
# =============================================================================

def build_ethernet_header(src_mac: str, dst_mac: str, ethertype: int = 0x0800) -> bytes:
    """Build Ethernet header.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        ethertype: EtherType (default IPv4)

    Returns:
        14-byte Ethernet header
    """
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
    """Build a TCP/IP packet with Ethernet header.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_port: Source TCP port
        dst_port: Destination TCP port
        payload: TCP payload
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags string (S, A, P, F, R)
        ttl: IP TTL
        window: TCP window size

    Returns:
        Complete packet bytes
    """
    import socket

    # Ethernet header
    eth_header = build_ethernet_header(src_mac, dst_mac, 0x0800)

    # IP header
    version_ihl = 0x45
    dscp_ecn = 0x00
    total_length = 20 + 20 + len(payload)
    identification = random.randint(1, 65535)
    flags_fragment = 0x4000  # Don't fragment
    protocol = 6  # TCP
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
        0,  # Checksum placeholder
        0,  # Urgent pointer
    )

    return eth_header + ip_header + tcp_header + payload


def build_tcp_syn(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ttl: int = 64,
) -> bytes:
    """Build TCP SYN packet."""
    return build_tcp_packet(
        src_mac, dst_mac, src_ip, dst_ip,
        src_port, dst_port, b"", seq, 0, "S", ttl,
    )


def build_tcp_syn_ack(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    ttl: int = 64,
) -> bytes:
    """Build TCP SYN-ACK packet."""
    return build_tcp_packet(
        src_mac, dst_mac, src_ip, dst_ip,
        src_port, dst_port, b"", seq, ack, "SA", ttl,
    )


def build_tcp_ack(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    ttl: int = 64,
) -> bytes:
    """Build TCP ACK packet."""
    return build_tcp_packet(
        src_mac, dst_mac, src_ip, dst_ip,
        src_port, dst_port, b"", seq, ack, "A", ttl,
    )


def build_tcp_fin(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    ttl: int = 64,
) -> bytes:
    """Build TCP FIN packet."""
    return build_tcp_packet(
        src_mac, dst_mac, src_ip, dst_ip,
        src_port, dst_port, b"", seq, ack, "FA", ttl,
    )


# =============================================================================
# DF1 Serial Frame Building (Reference)
# =============================================================================

def build_df1_frame(
    destination: int,
    source: int,
    pccc_data: bytes,
    use_crc: bool = True,
) -> bytes:
    """Build DF1 serial frame (for reference/logging).

    Format: DLE STX DST SRC CMD STS TNSW DATA DLE ETX BCC/CRC

    Args:
        destination: Destination node address (0-255)
        source: Source node address (0-255)
        pccc_data: PCCC command data
        use_crc: Use CRC-16 if True, BCC if False

    Returns:
        Complete DF1 frame bytes
    """
    # Build message content
    content = bytes([destination, source]) + pccc_data

    # DLE stuffing (escape any DLE in content)
    stuffed = b""
    for byte in content:
        stuffed += bytes([byte])
        if byte == DF1FrameChar.DLE:
            stuffed += bytes([DF1FrameChar.DLE])  # Double DLE

    # Build frame
    frame = bytes([DF1FrameChar.DLE, DF1FrameChar.STX])
    frame += stuffed
    frame += bytes([DF1FrameChar.DLE, DF1FrameChar.ETX])

    # Calculate check (BCC or CRC)
    if use_crc:
        crc = _calculate_df1_crc(content)
        frame += struct.pack("<H", crc)
    else:
        bcc = _calculate_df1_bcc(content)
        frame += bytes([bcc])

    return frame


def _calculate_df1_bcc(data: bytes) -> int:
    """Calculate DF1 BCC (2's complement checksum)."""
    checksum = 0
    for byte in data:
        checksum = (checksum + byte) & 0xFF
    return (~checksum + 1) & 0xFF


def _calculate_df1_crc(data: bytes) -> int:
    """Calculate DF1 CRC-16."""
    crc = 0x0000
    polynomial = 0x8005

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ polynomial
            else:
                crc >>= 1

    return crc
