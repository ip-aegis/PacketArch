# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Omron FINS packet building utilities.

FINS (Factory Interface Network Service) is Omron's proprietary protocol
for PLC communication. It supports both UDP and TCP transport on port 9600.

Frame structure:
- FINS Header (10 bytes): ICF, RSV, GCT, DNA, DA1, DA2, SNA, SA1, SA2, SID
- Command (2 bytes): MRC (Main Request Code), SRC (Sub Request Code)
- Data (variable): Command-specific data

Supported PLCs:
- CJ/CS series
- NJ/NX series
- CP series
- CV series
"""

import struct
from typing import TYPE_CHECKING

from scapy.layers.inet import IP, UDP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines.types import DeviceContext

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import TcpOptions


# FINS Constants
FINS_PORT = 9600
FINS_TCP_MAGIC = b"FINS"  # 0x46494E53

# ICF (Information Control Field) values
ICF_COMMAND = 0x80          # Command frame, response required
ICF_COMMAND_NO_RESP = 0x81  # Command frame, no response required
ICF_RESPONSE = 0xC0         # Response frame
ICF_RESPONSE_NO_RESP = 0xC1 # Response frame, no response required


class FINSCommand:
    """FINS command codes (MRC << 8 | SRC)."""
    # Memory Area Operations
    MEMORY_AREA_READ = 0x0101
    MEMORY_AREA_WRITE = 0x0102
    MEMORY_AREA_FILL = 0x0103
    MEMORY_AREA_MULTI_READ = 0x0104
    MEMORY_AREA_TRANSFER = 0x0105

    # Parameter Area Operations
    PARAMETER_AREA_READ = 0x0201
    PARAMETER_AREA_WRITE = 0x0202
    PARAMETER_AREA_CLEAR = 0x0203

    # Program Area Operations
    PROGRAM_AREA_PROTECT = 0x0304
    PROGRAM_AREA_PROTECT_CLEAR = 0x0305
    PROGRAM_AREA_READ = 0x0306
    PROGRAM_AREA_WRITE = 0x0307
    PROGRAM_AREA_CLEAR = 0x0308

    # Operating Mode Commands
    RUN = 0x0401
    STOP = 0x0402
    RESET = 0x0403

    # Status and Information
    CONTROLLER_DATA_READ = 0x0501
    CONNECTION_DATA_READ = 0x0502
    CONTROLLER_STATUS_READ = 0x0601
    NETWORK_STATUS_READ = 0x0602
    DATA_LINK_STATUS_READ = 0x0603
    CYCLE_TIME_READ = 0x0620

    # Clock Operations
    CLOCK_READ = 0x0701
    CLOCK_WRITE = 0x0702

    # Testing
    LOOP_BACK_TEST = 0x0801

    # Error and Access
    MESSAGE_READ = 0x0920
    ACCESS_RIGHT_ACQUIRE = 0x0C01
    ACCESS_RIGHT_FORCED_ACQUIRE = 0x0C02
    ACCESS_RIGHT_RELEASE = 0x0C03
    ERROR_CLEAR = 0x2101
    ERROR_LOG_READ = 0x2102
    ERROR_LOG_CLEAR = 0x2103

    # Forced Set/Reset
    FORCED_SET_RESET = 0x2301
    FORCED_SET_RESET_CANCEL = 0x2302


class MemoryArea:
    """FINS memory area codes."""
    # Word access codes
    CIO_WORD = 0xB0      # Core I/O (CS1/CJ1)
    WR_WORD = 0xB1       # Work Area
    HR_WORD = 0xB2       # Holding Relay
    AR_WORD = 0xB3       # Auxiliary Relay
    DM_WORD = 0x82       # Data Memory
    EM_CURRENT = 0x98    # Current Extended Memory
    EM0_WORD = 0xA0      # Extended Memory Bank 0
    TIM_WORD = 0x89      # Timer/Counter PV

    # Bit access codes
    CIO_BIT = 0x30       # Core I/O (bit)
    WR_BIT = 0x31        # Work Area (bit)
    HR_BIT = 0x32        # Holding Relay (bit)
    AR_BIT = 0x33        # Auxiliary Relay (bit)
    DM_BIT = 0x02        # Data Memory (bit)


class FINSTcpCommand:
    """FINS/TCP frame command codes."""
    CLIENT_NODE_ADDR_SEND = 0x00000000
    SERVER_NODE_ADDR_SEND = 0x00000001
    FRAME_SEND = 0x00000002
    FRAME_SEND_ERROR = 0x00000003
    CONNECTION_CONFIRM = 0x00000006


class ResponseCode:
    """FINS response codes (MRES << 8 | SRES)."""
    NORMAL = 0x0000
    SERVICE_CANCELED = 0x0001

    # Local node errors
    LOCAL_NODE_NOT_IN_NETWORK = 0x0101
    TOKEN_TIMEOUT = 0x0102
    RETRIES_FAILED = 0x0103

    # Destination node errors
    DST_NODE_NOT_IN_NETWORK = 0x0201
    UNIT_MISSING = 0x0202
    DST_NODE_BUSY = 0x0204
    RESPONSE_TIMEOUT = 0x0205

    # Command errors
    UNDEFINED_COMMAND = 0x0401
    NOT_SUPPORTED = 0x0402

    # Parameter errors
    ADDRESS_RANGE_ERROR = 0x1103
    ADDRESS_RANGE_EXCEEDED = 0x1104

    # Mode errors
    NOT_EXECUTABLE_IN_RUN = 0x2202
    NOT_EXECUTABLE_IN_PROGRAM = 0x2203


def build_fins_header(
    dst_node: int,
    src_node: int,
    sid: int,
    dst_network: int = 0x00,
    src_network: int = 0x00,
    dst_unit: int = 0x00,
    src_unit: int = 0x00,
    icf: int = ICF_COMMAND,
    gct: int = 0x02,
) -> bytes:
    """Build FINS header (10 bytes).

    Args:
        dst_node: Destination node address (DA1)
        src_node: Source node address (SA1)
        sid: Service ID (transaction identifier)
        dst_network: Destination network address (DNA)
        src_network: Source network address (SNA)
        dst_unit: Destination unit address (DA2)
        src_unit: Source unit address (SA2)
        icf: Information Control Field
        gct: Gateway Count

    Returns:
        10-byte FINS header
    """
    return bytes([
        icf,          # ICF
        0x00,         # RSV (reserved)
        gct,          # GCT (gateway count)
        dst_network,  # DNA
        dst_node,     # DA1
        dst_unit,     # DA2
        src_network,  # SNA
        src_node,     # SA1
        src_unit,     # SA2
        sid,          # SID
    ])


def build_memory_read_command(
    area_code: int,
    address: int,
    num_items: int,
    bit_position: int = 0,
) -> bytes:
    """Build Memory Area Read command data.

    Args:
        area_code: Memory area code (see MemoryArea)
        address: Starting word address
        num_items: Number of items to read
        bit_position: Bit position within word (0 for word access)

    Returns:
        Command data bytes
    """
    return bytes([
        0x01, 0x01,  # Command: Memory Area Read
        area_code,
        (address >> 8) & 0xFF,
        address & 0xFF,
        bit_position,
        (num_items >> 8) & 0xFF,
        num_items & 0xFF,
    ])


def build_memory_write_command(
    area_code: int,
    address: int,
    data: bytes,
    bit_position: int = 0,
) -> bytes:
    """Build Memory Area Write command data.

    Args:
        area_code: Memory area code
        address: Starting word address
        data: Data to write (2 bytes per word)
        bit_position: Bit position within word

    Returns:
        Command data bytes
    """
    num_items = len(data) // 2
    return bytes([
        0x01, 0x02,  # Command: Memory Area Write
        area_code,
        (address >> 8) & 0xFF,
        address & 0xFF,
        bit_position,
        (num_items >> 8) & 0xFF,
        num_items & 0xFF,
    ]) + data


def build_controller_data_read_command() -> bytes:
    """Build Controller Data Read command.

    Returns:
        Command data bytes
    """
    return bytes([0x05, 0x01])  # Controller Data Read


def build_controller_status_read_command() -> bytes:
    """Build Controller Status Read command.

    Returns:
        Command data bytes
    """
    return bytes([0x06, 0x01])  # Controller Status Read


def build_clock_read_command() -> bytes:
    """Build Clock Read command.

    Returns:
        Command data bytes
    """
    return bytes([0x07, 0x01])  # Clock Read


def build_run_command(mode: int = 0x02) -> bytes:
    """Build Run command.

    Args:
        mode: Run mode (0x01=Debug, 0x02=Monitor, 0x04=Run)

    Returns:
        Command data bytes
    """
    return bytes([0x04, 0x01, 0x00, 0x00, mode, 0x00])


def build_stop_command() -> bytes:
    """Build Stop command.

    Returns:
        Command data bytes
    """
    return bytes([0x04, 0x02])


def build_fins_response_header(
    dst_node: int,
    src_node: int,
    sid: int,
    dst_network: int = 0x00,
    src_network: int = 0x00,
) -> bytes:
    """Build FINS response header.

    Args:
        dst_node: Destination node (original source)
        src_node: Source node (original destination)
        sid: Service ID (matches request)
        dst_network: Destination network
        src_network: Source network

    Returns:
        10-byte FINS response header
    """
    return build_fins_header(
        dst_node=dst_node,
        src_node=src_node,
        sid=sid,
        dst_network=dst_network,
        src_network=src_network,
        icf=ICF_RESPONSE,
    )


def build_fins_response(
    command: int,
    response_code: int,
    data: bytes = b"",
) -> bytes:
    """Build FINS response data (after header).

    Args:
        command: Original command code
        response_code: Response code (MRES << 8 | SRES)
        data: Response data

    Returns:
        Response data bytes
    """
    mrc = (command >> 8) & 0xFF
    src = command & 0xFF
    mres = (response_code >> 8) & 0xFF
    sres = response_code & 0xFF

    return bytes([mrc, src, mres, sres]) + data


def build_fins_udp_packet(
    src: DeviceContext,
    dst: DeviceContext,
    fins_frame: bytes,
) -> bytes:
    """Build FINS/UDP packet.

    Args:
        src: Source device context
        dst: Destination device context
        fins_frame: Complete FINS frame (header + command + data)

    Returns:
        Complete Ethernet/IP/UDP packet bytes
    """
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / UDP(sport=FINS_PORT, dport=FINS_PORT)
        / Raw(load=fins_frame)
    )

    return bytes(packet)


def build_fins_tcp_header(
    command: int,
    data_length: int,
    error_code: int = 0,
) -> bytes:
    """Build FINS/TCP header (16 bytes).

    Args:
        command: TCP command code (see FINSTcpCommand)
        data_length: Length of data following header
        error_code: Error code (0 for normal)

    Returns:
        16-byte FINS/TCP header
    """
    # Total length includes: command (4) + error (4) + data
    total_length = 8 + data_length

    return (
        FINS_TCP_MAGIC +
        struct.pack(">I", total_length) +
        struct.pack(">I", command) +
        struct.pack(">I", error_code)
    )


def build_tcp_client_handshake(client_node: int = 0x00) -> bytes:
    """Build TCP client node address exchange request.

    Args:
        client_node: Client node address (0 = auto-assign)

    Returns:
        Complete TCP handshake request
    """
    header = build_fins_tcp_header(
        command=FINSTcpCommand.CLIENT_NODE_ADDR_SEND,
        data_length=4,
    )
    return header + struct.pack(">I", client_node)


def build_tcp_server_handshake(client_node: int, server_node: int) -> bytes:
    """Build TCP server node address exchange response.

    Args:
        client_node: Assigned client node address
        server_node: Server node address

    Returns:
        Complete TCP handshake response
    """
    header = build_fins_tcp_header(
        command=FINSTcpCommand.SERVER_NODE_ADDR_SEND,
        data_length=8,
    )
    return header + struct.pack(">I", client_node) + struct.pack(">I", server_node)


def build_fins_tcp_frame(fins_frame: bytes) -> bytes:
    """Wrap FINS frame in TCP header.

    Args:
        fins_frame: Complete FINS frame (header + command + data)

    Returns:
        FINS/TCP frame with header
    """
    header = build_fins_tcp_header(
        command=FINSTcpCommand.FRAME_SEND,
        data_length=len(fins_frame),
    )
    return header + fins_frame


def build_fins_tcp_packet(
    src: DeviceContext,
    dst: DeviceContext,
    tcp_frame: bytes,
    seq: int,
    ack: int,
    flags: str = "PA",
) -> bytes:
    """Build FINS/TCP packet.

    Args:
        src: Source device context
        dst: Destination device context
        tcp_frame: FINS/TCP frame (with TCP header)
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags

    Returns:
        Complete Ethernet/IP/TCP packet bytes
    """
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port or FINS_PORT, dport=dst.port or FINS_PORT,
              seq=seq, ack=ack, flags=flags)
        / Raw(load=tcp_frame)
    )

    return bytes(packet)


# TCP handshake helpers (reuse from modbus)
def build_tcp_handshake_syn(src: DeviceContext, dst: DeviceContext, seq: int) -> bytes:
    """Build TCP SYN packet."""
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port or FINS_PORT, dport=dst.port or FINS_PORT,
              seq=seq, flags="S")
    )
    return bytes(packet)


def build_tcp_handshake_syn_ack(
    src: DeviceContext, dst: DeviceContext, seq: int, ack: int
) -> bytes:
    """Build TCP SYN-ACK packet."""
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port or FINS_PORT, dport=dst.port or FINS_PORT,
              seq=seq, ack=ack, flags="SA")
    )
    return bytes(packet)


def build_tcp_handshake_ack(
    src: DeviceContext, dst: DeviceContext, seq: int, ack: int
) -> bytes:
    """Build TCP ACK packet."""
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port or FINS_PORT, dport=dst.port or FINS_PORT,
              seq=seq, ack=ack, flags="A")
    )
    return bytes(packet)


def build_tcp_fin(
    src: DeviceContext, dst: DeviceContext, seq: int, ack: int
) -> bytes:
    """Build TCP FIN packet."""
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port or FINS_PORT, dport=dst.port or FINS_PORT,
              seq=seq, ack=ack, flags="FA")
    )
    return bytes(packet)


__all__ = [
    "FINS_PORT",
    "ICF_COMMAND",
    "ICF_RESPONSE",
    "FINSCommand",
    "MemoryArea",
    "FINSTcpCommand",
    "ResponseCode",
    "build_fins_header",
    "build_memory_read_command",
    "build_memory_write_command",
    "build_controller_data_read_command",
    "build_controller_status_read_command",
    "build_clock_read_command",
    "build_run_command",
    "build_stop_command",
    "build_fins_response_header",
    "build_fins_response",
    "build_fins_udp_packet",
    "build_fins_tcp_header",
    "build_tcp_client_handshake",
    "build_tcp_server_handshake",
    "build_fins_tcp_frame",
    "build_fins_tcp_packet",
    "build_tcp_handshake_syn",
    "build_tcp_handshake_syn_ack",
    "build_tcp_handshake_ack",
    "build_tcp_fin",
]
