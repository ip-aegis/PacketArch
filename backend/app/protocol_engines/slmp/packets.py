"""Mitsubishi SLMP/MC Protocol packet building utilities.

SLMP (Seamless Message Protocol) is Mitsubishi's standardized communication
format for MELSEC PLCs (Q, iQ-R, iQ-F, L series).

Frame types:
- 3E Frame: Standard format (subheader 0x5000/0xD000)
- 4E Frame: Extended format with serial number (subheader 0x5400/0xD400)

Default port: TCP 5000
"""

import struct
from typing import TYPE_CHECKING

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines.types import DeviceContext

if TYPE_CHECKING:
    pass


# SLMP Constants
SLMP_PORT = 5000

# Subheader values (Big Endian in frame)
SUBHEADER_3E_REQUEST = 0x5000
SUBHEADER_3E_RESPONSE = 0xD000
SUBHEADER_4E_REQUEST = 0x5400
SUBHEADER_4E_RESPONSE = 0xD400


class SLMPCommand:
    """SLMP command codes."""
    # Device Access Commands
    BATCH_READ = 0x0401      # Read consecutive devices
    BATCH_WRITE = 0x1401     # Write consecutive devices
    RANDOM_READ = 0x0403     # Read non-consecutive word devices
    RANDOM_READ_BIT = 0x0402 # Read non-consecutive bit devices
    RANDOM_WRITE = 0x1402    # Write non-consecutive devices
    BLOCK_READ = 0x0406      # Read multiple blocks
    BLOCK_WRITE = 0x1406     # Write multiple blocks

    # Remote Control Commands
    REMOTE_RUN = 0x1001      # Start PLC execution
    REMOTE_STOP = 0x1002     # Stop PLC execution
    REMOTE_PAUSE = 0x1003    # Pause PLC execution
    REMOTE_LATCH_CLEAR = 0x1005  # Clear latched devices
    REMOTE_RESET = 0x1006    # Reset CPU module

    # CPU Information Commands
    READ_CPU_MODEL = 0x0101  # Read CPU model name
    READ_CPU_STATE = 0x0301  # Read CPU RUN/STOP status


class SLMPSubcommand:
    """SLMP subcommand codes."""
    WORD = 0x0000   # Word units access
    BIT = 0x0001    # Bit units access


class DeviceCode:
    """SLMP device codes for binary format."""
    D = 0xA8   # Data Register
    M = 0x90   # Internal Relay
    X = 0x9C   # Input (hex addressing)
    Y = 0x9D   # Output (hex addressing)
    W = 0xB4   # Link Register (hex addressing)
    B = 0xA0   # Link Relay (hex addressing)
    R = 0xAF   # File Register
    SM = 0x91  # Special Relay
    SD = 0xA9  # Special Register
    L = 0x92   # Latch Relay
    F = 0x93   # Annunciator
    V = 0x94   # Edge Relay
    S = 0x98   # Step Relay
    TN = 0xC2  # Timer Current Value
    TC = 0xC1  # Timer Contact
    TS = 0xC0  # Timer Coil
    CN = 0xC5  # Counter Current Value
    CC = 0xC4  # Counter Contact
    CS = 0xC3  # Counter Coil
    Z = 0xCC   # Index Register
    ZR = 0xB0  # File Register (extended)


class ResponseCode:
    """SLMP response/end codes."""
    NORMAL = 0x0000  # Normal completion

    # Command errors
    SUBHEADER_ERROR = 0xC050
    WORD_POINTS_ERROR = 0xC051
    BIT_POINTS_ERROR = 0xC052
    WRITE_TO_MONITORED = 0xC056
    DATA_LENGTH_MISMATCH = 0xC058
    COMMAND_ERROR = 0xC059
    DEVICE_READ_ERROR = 0xC05A
    DEVICE_WRITE_ERROR = 0xC05B
    CONTENT_ERROR = 0xC05C
    MONITOR_REG_ERROR = 0xC05D
    DATA_POINTS_MISMATCH = 0xC061
    MEMORY_EXT_ERROR = 0xC070
    CPU_RUN_MODE_ERROR = 0xC0B5
    LABEL_ERROR = 0xCCC0
    INDEX_ERROR = 0xCCCA


def build_3e_request_header(
    network_number: int = 0x00,
    pc_number: int = 0xFF,
    dest_module_io: int = 0x03FF,
    dest_module_station: int = 0x00,
    data_length: int = 0,
    monitoring_timer: int = 0x000A,
) -> bytes:
    """Build 3E frame request header (11 bytes before command).

    Args:
        network_number: Network number (0x00 = own station)
        pc_number: PC/Station number (0xFF = own station)
        dest_module_io: Destination module I/O number (0x03FF = CPU)
        dest_module_station: Destination module station number
        data_length: Length of data after this header (including timer, cmd, subcmd, data)
        monitoring_timer: Timeout in 250ms units (default 2.5s)

    Returns:
        11-byte 3E request header
    """
    # Subheader is Big Endian
    header = struct.pack(">H", SUBHEADER_3E_REQUEST)

    # Rest is Little Endian
    header += bytes([network_number, pc_number])
    header += struct.pack("<H", dest_module_io)
    header += bytes([dest_module_station])
    header += struct.pack("<H", data_length)
    header += struct.pack("<H", monitoring_timer)

    return header


def build_3e_response_header(
    network_number: int = 0x00,
    pc_number: int = 0xFF,
    dest_module_io: int = 0x03FF,
    dest_module_station: int = 0x00,
    data_length: int = 0,
    end_code: int = 0x0000,
) -> bytes:
    """Build 3E frame response header.

    Args:
        network_number: Network number (echo from request)
        pc_number: PC number (echo from request)
        dest_module_io: Destination module I/O (echo from request)
        dest_module_station: Destination module station (echo from request)
        data_length: Length of response data (including end code)
        end_code: Response/end code (0x0000 = success)

    Returns:
        11-byte 3E response header
    """
    # Subheader is Big Endian
    header = struct.pack(">H", SUBHEADER_3E_RESPONSE)

    # Rest is Little Endian
    header += bytes([network_number, pc_number])
    header += struct.pack("<H", dest_module_io)
    header += bytes([dest_module_station])
    header += struct.pack("<H", data_length)
    header += struct.pack("<H", end_code)

    return header


def build_4e_request_header(
    serial_number: int,
    network_number: int = 0x00,
    pc_number: int = 0xFF,
    dest_module_io: int = 0x03FF,
    dest_module_station: int = 0x00,
    data_length: int = 0,
    monitoring_timer: int = 0x000A,
) -> bytes:
    """Build 4E frame request header (15 bytes before command).

    Args:
        serial_number: Serial number for request/response matching
        network_number: Network number
        pc_number: PC/Station number
        dest_module_io: Destination module I/O number
        dest_module_station: Destination module station number
        data_length: Length of data after header
        monitoring_timer: Timeout in 250ms units

    Returns:
        15-byte 4E request header
    """
    # Subheader is Big Endian
    header = struct.pack(">H", SUBHEADER_4E_REQUEST)

    # Serial number and reserved (Little Endian)
    header += struct.pack("<H", serial_number)
    header += struct.pack("<H", 0x0000)  # Reserved

    # Rest same as 3E
    header += bytes([network_number, pc_number])
    header += struct.pack("<H", dest_module_io)
    header += bytes([dest_module_station])
    header += struct.pack("<H", data_length)
    header += struct.pack("<H", monitoring_timer)

    return header


def build_4e_response_header(
    serial_number: int,
    network_number: int = 0x00,
    pc_number: int = 0xFF,
    dest_module_io: int = 0x03FF,
    dest_module_station: int = 0x00,
    data_length: int = 0,
    end_code: int = 0x0000,
) -> bytes:
    """Build 4E frame response header.

    Args:
        serial_number: Serial number (echo from request)
        network_number: Network number
        pc_number: PC number
        dest_module_io: Destination module I/O
        dest_module_station: Destination module station
        data_length: Response data length
        end_code: Response/end code

    Returns:
        15-byte 4E response header
    """
    # Subheader is Big Endian
    header = struct.pack(">H", SUBHEADER_4E_RESPONSE)

    # Serial number and reserved
    header += struct.pack("<H", serial_number)
    header += struct.pack("<H", 0x0000)

    # Rest same as 3E response
    header += bytes([network_number, pc_number])
    header += struct.pack("<H", dest_module_io)
    header += bytes([dest_module_station])
    header += struct.pack("<H", data_length)
    header += struct.pack("<H", end_code)

    return header


def build_device_address(device_code: int, address: int) -> bytes:
    """Build device address (4 bytes).

    Format: [Address (3 bytes LE)] [Device Code (1 byte)]

    Args:
        device_code: Device code (see DeviceCode)
        address: Device number

    Returns:
        4-byte device address
    """
    # Address is 24-bit Little Endian
    addr_bytes = struct.pack("<I", address)[:3]  # Take lower 3 bytes
    return addr_bytes + bytes([device_code])


def build_batch_read_command(
    device_code: int,
    start_address: int,
    num_points: int,
    bit_access: bool = False,
) -> bytes:
    """Build Batch Read command data.

    Args:
        device_code: Device code
        start_address: Starting device address
        num_points: Number of points to read
        bit_access: True for bit access, False for word access

    Returns:
        Command data bytes (command + subcommand + device address + points)
    """
    subcommand = SLMPSubcommand.BIT if bit_access else SLMPSubcommand.WORD

    data = struct.pack("<H", SLMPCommand.BATCH_READ)
    data += struct.pack("<H", subcommand)
    data += build_device_address(device_code, start_address)
    data += struct.pack("<H", num_points)

    return data


def build_batch_write_command(
    device_code: int,
    start_address: int,
    write_data: bytes,
    bit_access: bool = False,
) -> bytes:
    """Build Batch Write command data.

    Args:
        device_code: Device code
        start_address: Starting device address
        write_data: Data to write
        bit_access: True for bit access, False for word access

    Returns:
        Command data bytes
    """
    subcommand = SLMPSubcommand.BIT if bit_access else SLMPSubcommand.WORD

    if bit_access:
        num_points = len(write_data)
    else:
        num_points = len(write_data) // 2

    data = struct.pack("<H", SLMPCommand.BATCH_WRITE)
    data += struct.pack("<H", subcommand)
    data += build_device_address(device_code, start_address)
    data += struct.pack("<H", num_points)
    data += write_data

    return data


def build_remote_run_command(forced: bool = False, clear_mode: int = 0) -> bytes:
    """Build Remote Run command.

    Args:
        forced: Force execution even if safety conditions not met
        clear_mode: Device clear mode (0 = no clear)

    Returns:
        Command data bytes
    """
    data = struct.pack("<H", SLMPCommand.REMOTE_RUN)
    data += struct.pack("<H", 0x0000)  # Subcommand
    data += struct.pack("<H", 0x0001 if forced else 0x0000)
    data += struct.pack("<H", clear_mode)

    return data


def build_remote_stop_command() -> bytes:
    """Build Remote Stop command.

    Returns:
        Command data bytes
    """
    data = struct.pack("<H", SLMPCommand.REMOTE_STOP)
    data += struct.pack("<H", 0x0000)  # Subcommand

    return data


def build_read_cpu_model_command() -> bytes:
    """Build Read CPU Model command.

    Returns:
        Command data bytes
    """
    data = struct.pack("<H", SLMPCommand.READ_CPU_MODEL)
    data += struct.pack("<H", 0x0000)  # Subcommand

    return data


def build_read_cpu_state_command() -> bytes:
    """Build Read CPU State command.

    Returns:
        Command data bytes
    """
    data = struct.pack("<H", SLMPCommand.READ_CPU_STATE)
    data += struct.pack("<H", 0x0000)  # Subcommand

    return data


def build_slmp_3e_frame(
    command_data: bytes,
    network_number: int = 0x00,
    pc_number: int = 0xFF,
    dest_module_io: int = 0x03FF,
    dest_module_station: int = 0x00,
    monitoring_timer: int = 0x000A,
) -> bytes:
    """Build complete 3E request frame.

    Args:
        command_data: Command + subcommand + data
        network_number: Network number
        pc_number: PC number
        dest_module_io: Destination module I/O
        dest_module_station: Destination module station
        monitoring_timer: Timeout in 250ms units

    Returns:
        Complete 3E frame
    """
    # Data length = monitoring timer (2) + command data
    data_length = 2 + len(command_data)

    header = build_3e_request_header(
        network_number=network_number,
        pc_number=pc_number,
        dest_module_io=dest_module_io,
        dest_module_station=dest_module_station,
        data_length=data_length,
        monitoring_timer=monitoring_timer,
    )

    # Header already includes monitoring timer position
    # Command data follows directly after header
    return header + command_data


def build_slmp_4e_frame(
    command_data: bytes,
    serial_number: int,
    network_number: int = 0x00,
    pc_number: int = 0xFF,
    dest_module_io: int = 0x03FF,
    dest_module_station: int = 0x00,
    monitoring_timer: int = 0x000A,
) -> bytes:
    """Build complete 4E request frame.

    Args:
        command_data: Command + subcommand + data
        serial_number: Serial number for matching
        network_number: Network number
        pc_number: PC number
        dest_module_io: Destination module I/O
        dest_module_station: Destination module station
        monitoring_timer: Timeout in 250ms units

    Returns:
        Complete 4E frame
    """
    data_length = 2 + len(command_data)

    header = build_4e_request_header(
        serial_number=serial_number,
        network_number=network_number,
        pc_number=pc_number,
        dest_module_io=dest_module_io,
        dest_module_station=dest_module_station,
        data_length=data_length,
        monitoring_timer=monitoring_timer,
    )

    return header + command_data


def build_slmp_tcp_packet(
    src: DeviceContext,
    dst: DeviceContext,
    slmp_frame: bytes,
    seq: int,
    ack: int,
    flags: str = "PA",
) -> bytes:
    """Build SLMP TCP packet.

    Args:
        src: Source device context
        dst: Destination device context
        slmp_frame: Complete SLMP frame
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags

    Returns:
        Complete Ethernet/IP/TCP packet bytes
    """
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port or SLMP_PORT, dport=dst.port or SLMP_PORT,
              seq=seq, ack=ack, flags=flags)
        / Raw(load=slmp_frame)
    )

    return bytes(packet)


# TCP handshake helpers
def build_tcp_handshake_syn(src: DeviceContext, dst: DeviceContext, seq: int) -> bytes:
    """Build TCP SYN packet."""
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port or SLMP_PORT, dport=dst.port or SLMP_PORT,
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
        / TCP(sport=src.port or SLMP_PORT, dport=dst.port or SLMP_PORT,
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
        / TCP(sport=src.port or SLMP_PORT, dport=dst.port or SLMP_PORT,
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
        / TCP(sport=src.port or SLMP_PORT, dport=dst.port or SLMP_PORT,
              seq=seq, ack=ack, flags="FA")
    )
    return bytes(packet)


__all__ = [
    "SLMP_PORT",
    "SUBHEADER_3E_REQUEST",
    "SUBHEADER_3E_RESPONSE",
    "SUBHEADER_4E_REQUEST",
    "SUBHEADER_4E_RESPONSE",
    "SLMPCommand",
    "SLMPSubcommand",
    "DeviceCode",
    "ResponseCode",
    "build_3e_request_header",
    "build_3e_response_header",
    "build_4e_request_header",
    "build_4e_response_header",
    "build_device_address",
    "build_batch_read_command",
    "build_batch_write_command",
    "build_remote_run_command",
    "build_remote_stop_command",
    "build_read_cpu_model_command",
    "build_read_cpu_state_command",
    "build_slmp_3e_frame",
    "build_slmp_4e_frame",
    "build_slmp_tcp_packet",
    "build_tcp_handshake_syn",
    "build_tcp_handshake_syn_ack",
    "build_tcp_handshake_ack",
    "build_tcp_fin",
]
