"""Deterministic unique serial number generator.

Re-exports from protocol_engines for backwards compatibility.
Canonical implementation lives in app.protocol_engines.serial_number_generator.
"""

from app.protocol_engines.serial_number_generator import (  # noqa: F401
    SerialNumberGenerator,
    device_hash,
)
