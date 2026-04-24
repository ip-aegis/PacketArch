# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Modbus TCP packet building utilities.

TCP packet construction is now centralized in tcp_builder.py.
This module re-exports TCP functions for backward compatibility
and provides Modbus-specific builders (MBAP header, etc.).
"""

import struct

# Re-export TCP builders from unified module for backward compatibility.
# Consumers importing from modbus.packets continue to work unchanged.
from app.protocol_engines.tcp_builder import (  # noqa: F401
    build_tcp_ack as build_tcp_handshake_ack,
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_packet,
    build_tcp_packet_fingerprinted,
    build_tcp_syn as build_tcp_handshake_syn,
    build_tcp_syn_ack as build_tcp_handshake_syn_ack,
)


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
