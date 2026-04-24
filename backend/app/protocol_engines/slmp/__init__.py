# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Mitsubishi SLMP/MC Protocol engine for MELSEC PLCs.

SLMP (Seamless Message Protocol) is Mitsubishi's standardized communication
format for MELSEC PLCs over Ethernet.

Supported PLCs:
- MELSEC Q series
- MELSEC iQ-R series
- MELSEC iQ-F series
- MELSEC L series

Frame types:
- 3E Frame: Standard format (most common)
- 4E Frame: Extended format with serial number

Default port: TCP 5000

Features:
- Device batch read/write (D, M, X, Y, W, B, R, etc.)
- Remote Run/Stop control
- CPU model and status read
"""

from app.protocol_engines.slmp.engine import SLMPEngine

__all__ = ["SLMPEngine"]
