# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Omron FINS protocol engine for Omron PLCs.

FINS (Factory Interface Network Service) is Omron's proprietary protocol
for PLC communication over Ethernet, Controller Link, and serial interfaces.

Supported transport:
- FINS/UDP (port 9600) - Connectionless, most common
- FINS/TCP (port 9600) - Connection-oriented with node address exchange

Supported PLCs:
- CJ/CS series (CJ1, CJ2, CS1)
- NJ/NX series (newer machine automation controllers)
- CP series (compact PLCs)
- CV series (older series)

Features:
- Memory area read/write (CIO, WR, HR, AR, DM, EM)
- Controller data and status read
- Clock read/write
- Run/Stop mode control
"""

from app.protocol_engines.fins.engine import FINSEngine

__all__ = ["FINSEngine"]
