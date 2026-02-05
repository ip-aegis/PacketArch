"""Modbus RTU packet building utilities.

Modbus RTU uses CRC-16 checksum instead of MBAP header.
This module supports both pure RTU frames and RTU-over-TCP encapsulation.

Frame format:
  [Unit ID (1 byte)] [Function Code (1 byte)] [Data (N bytes)] [CRC-16 (2 bytes)]

CRC-16 uses the IBM polynomial (0xA001) with initial value 0xFFFF.
"""

import struct
from typing import TYPE_CHECKING

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines.types import DeviceContext

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import TcpOptions


# CRC-16 lookup table for Modbus (polynomial 0xA001)
_CRC_TABLE: list[int] = []


def _init_crc_table() -> None:
    """Initialize the CRC-16 lookup table."""
    global _CRC_TABLE
    if _CRC_TABLE:
        return

    _CRC_TABLE = []
    for byte in range(256):
        crc = byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
        _CRC_TABLE.append(crc)


def calculate_crc16(data: bytes) -> int:
    """Calculate Modbus CRC-16 checksum.

    Uses the standard Modbus CRC-16 algorithm with:
    - Polynomial: 0xA001 (reflected 0x8005)
    - Initial value: 0xFFFF
    - Input/output reflected: Yes
    - Final XOR: 0x0000

    Args:
        data: Bytes to calculate CRC over

    Returns:
        16-bit CRC value
    """
    _init_crc_table()

    crc = 0xFFFF
    for byte in data:
        crc = (crc >> 8) ^ _CRC_TABLE[(crc ^ byte) & 0xFF]

    return crc


def verify_crc16(frame: bytes) -> bool:
    """Verify Modbus RTU frame CRC.

    Args:
        frame: Complete RTU frame including CRC

    Returns:
        True if CRC is valid
    """
    if len(frame) < 4:  # Minimum: unit_id + fc + crc
        return False

    data = frame[:-2]
    received_crc = struct.unpack("<H", frame[-2:])[0]
    calculated_crc = calculate_crc16(data)

    return received_crc == calculated_crc


def build_rtu_frame(unit_id: int, pdu: bytes) -> bytes:
    """Build a complete Modbus RTU frame with CRC.

    Args:
        unit_id: Unit identifier (slave address, 1-247)
        pdu: Protocol data unit (function code + data)

    Returns:
        Complete RTU frame: [unit_id][pdu][crc_lo][crc_hi]
    """
    frame_data = bytes([unit_id]) + pdu
    crc = calculate_crc16(frame_data)
    # CRC is transmitted low byte first (little-endian)
    return frame_data + struct.pack("<H", crc)


def build_rtu_over_tcp_packet(
    src: DeviceContext,
    dst: DeviceContext,
    rtu_frame: bytes,
    seq: int = 1000,
    ack: int = 1000,
    flags: str = "PA",
    tcp_options: "TcpOptions | None" = None,
) -> bytes:
    """Build a Modbus RTU over TCP packet.

    This encapsulates an RTU frame (with CRC) inside a TCP packet.
    Common in serial-to-Ethernet converters and gateways.

    Args:
        src: Source device context
        dst: Destination device context
        rtu_frame: Complete RTU frame with CRC
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags
        tcp_options: Optional TCP fingerprint options

    Returns:
        Complete Ethernet/IP/TCP packet bytes
    """
    # Use fingerprinted values if available
    if tcp_options:
        ttl = tcp_options.ttl
        window = tcp_options.window_size
        options = []
        if tcp_options.mss and "S" in flags:
            options.append(("MSS", tcp_options.mss))
        if tcp_options.sack_permitted and "S" in flags:
            options.append(("SAckOK", b""))
        if tcp_options.timestamps_enabled:
            options.append(("Timestamp", (0, 0)))
        if tcp_options.window_scaling is not None and "S" in flags:
            options.append(("WScale", tcp_options.window_scaling))
        if options and tcp_options.nop_padding:
            options.insert(0, ("NOP", None))
    else:
        ttl = 64
        window = 65535
        options = []

    ip_layer = IP(
        src=src.ip_address,
        dst=dst.ip_address,
        ttl=ttl,
    )

    if tcp_options and tcp_options.df_flag:
        ip_layer.flags = "DF"

    tcp_layer = TCP(
        sport=src.port,
        dport=dst.port,
        seq=seq,
        ack=ack,
        flags=flags,
        window=window,
    )

    if options:
        tcp_layer.options = options

    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / ip_layer
        / tcp_layer
        / Raw(load=rtu_frame)
    )

    return bytes(packet)


def build_rtu_over_tcp_fingerprinted(
    src: DeviceContext,
    dst: DeviceContext,
    rtu_frame: bytes,
    seq: int = 1000,
    ack: int = 1000,
    flags: str = "PA",
) -> bytes:
    """Build RTU over TCP packet using device fingerprint.

    Args:
        src: Source device context (provides fingerprint)
        dst: Destination device context
        rtu_frame: Complete RTU frame with CRC
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags

    Returns:
        Complete packet bytes with fingerprinted TCP stack
    """
    tcp_options = src.fingerprint_applicator.get_tcp_options()
    return build_rtu_over_tcp_packet(src, dst, rtu_frame, seq, ack, flags, tcp_options)


# Re-export TCP handshake functions from main packets module
from app.protocol_engines.modbus.packets import (
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_handshake_ack,
    build_tcp_handshake_syn,
    build_tcp_handshake_syn_ack,
)

__all__ = [
    "calculate_crc16",
    "verify_crc16",
    "build_rtu_frame",
    "build_rtu_over_tcp_packet",
    "build_rtu_over_tcp_fingerprinted",
    "build_tcp_handshake_syn",
    "build_tcp_handshake_syn_ack",
    "build_tcp_handshake_ack",
    "build_tcp_fin",
    "build_tcp_fin_ack",
]
