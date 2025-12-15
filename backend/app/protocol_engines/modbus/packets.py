"""Modbus TCP packet building utilities.

Includes TCP fingerprinting support for hyper-realistic device emulation.
"""

import struct
from typing import TYPE_CHECKING

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines.types import DeviceContext

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import TcpOptions


def build_mbap_header(transaction_id: int, unit_id: int, pdu_length: int) -> bytes:
    """Build Modbus Application Protocol header.

    Args:
        transaction_id: Transaction identifier
        unit_id: Unit identifier (slave address)
        pdu_length: Length of PDU (protocol data unit)

    Returns:
        7-byte MBAP header
    """
    protocol_id = 0  # Always 0 for Modbus TCP
    length = pdu_length + 1  # PDU length + unit_id byte

    return struct.pack(">HHHB", transaction_id, protocol_id, length, unit_id)


def build_tcp_packet(
    src: DeviceContext,
    dst: DeviceContext,
    payload: bytes,
    seq: int = 1000,
    ack: int = 1000,
    flags: str = "PA",
    tcp_options: "TcpOptions | None" = None,
) -> bytes:
    """Build a complete TCP packet with Ethernet/IP/TCP headers.

    Args:
        src: Source device context
        dst: Destination device context
        payload: TCP payload bytes
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags (e.g., "S" for SYN, "PA" for PSH+ACK)
        tcp_options: Optional TCP options from fingerprint (TTL, window, MSS, etc.)

    Returns:
        Complete packet bytes
    """
    # Use fingerprinted values if available
    if tcp_options:
        ttl = tcp_options.ttl
        window = tcp_options.window_size
        # Build TCP options list
        options = []
        if tcp_options.mss and "S" in flags:  # MSS only in SYN
            options.append(("MSS", tcp_options.mss))
        if tcp_options.sack_permitted and "S" in flags:
            options.append(("SAckOK", b""))
        if tcp_options.timestamps_enabled:
            # Timestamp value and echo reply
            options.append(("Timestamp", (0, 0)))
        if tcp_options.window_scaling is not None and "S" in flags:
            options.append(("WScale", tcp_options.window_scaling))
        if options and tcp_options.nop_padding:
            options.insert(0, ("NOP", None))
    else:
        ttl = 64
        window = 65535
        options = []

    # Build IP layer with fingerprinted TTL
    ip_layer = IP(
        src=src.ip_address,
        dst=dst.ip_address,
        ttl=ttl,
    )

    # Set DF flag if specified
    if tcp_options and tcp_options.df_flag:
        ip_layer.flags = "DF"

    # Build TCP layer with fingerprinted window
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
        / Raw(load=payload)
    )

    return bytes(packet)


def build_tcp_packet_fingerprinted(
    src: DeviceContext,
    dst: DeviceContext,
    payload: bytes,
    seq: int = 1000,
    ack: int = 1000,
    flags: str = "PA",
) -> bytes:
    """Build a TCP packet using the device's fingerprint for TCP options.

    This is a convenience function that extracts TCP options from the
    source device's fingerprint applicator.

    Args:
        src: Source device context (provides fingerprint)
        dst: Destination device context
        payload: TCP payload bytes
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags

    Returns:
        Complete packet bytes with fingerprinted TCP stack
    """
    tcp_options = src.fingerprint_applicator.get_tcp_options()
    return build_tcp_packet(src, dst, payload, seq, ack, flags, tcp_options)


def build_tcp_handshake_syn(src: DeviceContext, dst: DeviceContext, seq: int) -> bytes:
    """Build TCP SYN packet for connection establishment.

    Args:
        src: Source device context
        dst: Destination device context
        seq: Initial sequence number

    Returns:
        SYN packet bytes
    """
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port, dport=dst.port, seq=seq, flags="S")
    )

    return bytes(packet)


def build_tcp_handshake_syn_ack(
    src: DeviceContext,
    dst: DeviceContext,
    seq: int,
    ack: int,
) -> bytes:
    """Build TCP SYN-ACK packet for connection establishment.

    Args:
        src: Source device context
        dst: Destination device context
        seq: Sequence number
        ack: Acknowledgment number

    Returns:
        SYN-ACK packet bytes
    """
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port, dport=dst.port, seq=seq, ack=ack, flags="SA")
    )

    return bytes(packet)


def build_tcp_handshake_ack(
    src: DeviceContext,
    dst: DeviceContext,
    seq: int,
    ack: int,
) -> bytes:
    """Build TCP ACK packet for connection establishment.

    Args:
        src: Source device context
        dst: Destination device context
        seq: Sequence number
        ack: Acknowledgment number

    Returns:
        ACK packet bytes
    """
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port, dport=dst.port, seq=seq, ack=ack, flags="A")
    )

    return bytes(packet)


def build_tcp_fin(
    src: DeviceContext,
    dst: DeviceContext,
    seq: int,
    ack: int,
) -> bytes:
    """Build TCP FIN packet for connection termination.

    Args:
        src: Source device context
        dst: Destination device context
        seq: Sequence number
        ack: Acknowledgment number

    Returns:
        FIN packet bytes
    """
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port, dport=dst.port, seq=seq, ack=ack, flags="FA")
    )

    return bytes(packet)


def build_tcp_fin_ack(
    src: DeviceContext,
    dst: DeviceContext,
    seq: int,
    ack: int,
) -> bytes:
    """Build TCP FIN-ACK packet for connection termination.

    Args:
        src: Source device context
        dst: Destination device context
        seq: Sequence number
        ack: Acknowledgment number

    Returns:
        FIN-ACK packet bytes
    """
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address)
        / TCP(sport=src.port, dport=dst.port, seq=seq, ack=ack, flags="FA")
    )

    return bytes(packet)
