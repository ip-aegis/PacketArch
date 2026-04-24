# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Deterministic unique serial number generator.

Re-exports from protocol_engines for backwards compatibility.
Canonical implementation lives in app.protocol_engines.serial_number_generator.
"""

from app.protocol_engines.serial_number_generator import (  # noqa: F401
    SerialNumberGenerator,
    device_hash,
)
