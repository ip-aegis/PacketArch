"""Unified TCP packet builder shared across all protocol engines.

Provides fingerprinted TCP packet construction with vendor-specific
TTL, window size, MSS, WScale, SAckOK, timestamps, and DF flag.
Replaces per-engine TCP duplication in Modbus, S7, and EtherNet/IP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines.types import DeviceContext

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import TcpOptions


def extract_tcp_options(
    tcp_options: TcpOptions | None,
    flags: str = "",
) -> tuple[int, int, list, bool]:
    """Extract TTL, window, options list, and DF flag from TcpOptions.

    MSS, SAckOK, and WScale are only included in SYN/SYN-ACK packets.
    Timestamps are included in all packets when enabled.

    Args:
        tcp_options: TCP fingerprint options (or None for defaults)
        flags: TCP flags string (e.g. "S", "SA", "PA") — used to
               determine which options are SYN-only

    Returns:
        Tuple of (ttl, window_size, options_list, df_flag)
    """
    if not tcp_options:
        return 64, 65535, [], True

    ttl = tcp_options.ttl
    window = tcp_options.window_size
    df = tcp_options.df_flag
    is_syn = "S" in flags

    options: list = []
    if tcp_options.mss and is_syn:
        options.append(("MSS", tcp_options.mss))
    if tcp_options.sack_permitted and is_syn:
        options.append(("SAckOK", b""))
    if tcp_options.timestamps_enabled:
        options.append(("Timestamp", (0, 0)))
    if tcp_options.window_scaling is not None and is_syn:
        options.append(("WScale", tcp_options.window_scaling))
    if options and tcp_options.nop_padding:
        options.insert(0, ("NOP", None))

    return ttl, window, options, df


def build_tcp_packet(
    src: DeviceContext,
    dst: DeviceContext,
    payload: bytes,
    seq: int = 1000,
    ack: int = 1000,
    flags: str = "PA",
    tcp_options: TcpOptions | None = None,
) -> bytes:
    """Build a complete TCP packet with Ethernet/IP/TCP headers.

    Args:
        src: Source device context
        dst: Destination device context
        payload: TCP payload bytes (may be empty)
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags (e.g., "S", "SA", "PA", "FA")
        tcp_options: Optional TCP options from fingerprint

    Returns:
        Complete packet bytes
    """
    ttl, window, options, df = extract_tcp_options(tcp_options, flags)

    ip_layer = IP(src=src.ip_address, dst=dst.ip_address, ttl=ttl)
    if df:
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

    ether = Ether(src=src.mac_address, dst=dst.mac_address)

    if payload:
        packet = ether / ip_layer / tcp_layer / Raw(load=payload)
    else:
        packet = ether / ip_layer / tcp_layer

    return bytes(packet)


def build_tcp_packet_fingerprinted(
    src: DeviceContext,
    dst: DeviceContext,
    payload: bytes,
    seq: int = 1000,
    ack: int = 1000,
    flags: str = "PA",
) -> bytes:
    """Build a TCP packet using the source device's fingerprint for TCP options.

    Convenience function that extracts TCP options from the source
    device's fingerprint applicator automatically.

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


def build_tcp_syn(
    src: DeviceContext,
    dst: DeviceContext,
    seq: int,
    tcp_options: TcpOptions | None = None,
) -> bytes:
    """Build TCP SYN packet for connection establishment."""
    return build_tcp_packet(src, dst, b"", seq, 0, "S", tcp_options)


def build_tcp_syn_ack(
    src: DeviceContext,
    dst: DeviceContext,
    seq: int,
    ack: int,
    tcp_options: TcpOptions | None = None,
) -> bytes:
    """Build TCP SYN-ACK packet for connection establishment."""
    return build_tcp_packet(src, dst, b"", seq, ack, "SA", tcp_options)


def build_tcp_ack(
    src: DeviceContext,
    dst: DeviceContext,
    seq: int,
    ack: int,
    tcp_options: TcpOptions | None = None,
) -> bytes:
    """Build TCP ACK packet."""
    return build_tcp_packet(src, dst, b"", seq, ack, "A", tcp_options)


def build_tcp_fin(
    src: DeviceContext,
    dst: DeviceContext,
    seq: int,
    ack: int,
    tcp_options: TcpOptions | None = None,
) -> bytes:
    """Build TCP FIN-ACK packet for connection termination."""
    return build_tcp_packet(src, dst, b"", seq, ack, "FA", tcp_options)


def build_tcp_fin_ack(
    src: DeviceContext,
    dst: DeviceContext,
    seq: int,
    ack: int,
    tcp_options: TcpOptions | None = None,
) -> bytes:
    """Build TCP FIN-ACK packet for connection termination."""
    return build_tcp_packet(src, dst, b"", seq, ack, "FA", tcp_options)
