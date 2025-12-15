"""S7 Communication protocol engine for Siemens PLCs.

This package implements the S7comm protocol (ISO-on-TCP) for simulating
traffic to/from Siemens S7-300/400/1200/1500 PLCs.
"""

from .config import (
    S7Area,
    S7ConnectionType,
    S7CPUProfile,
    S7FlowConfig,
    S7Function,
    S7ReadArea,
    S7WriteArea,
    S7_CPU_PROFILES,
    get_cpu_profile,
)
from .engine import S7Engine

__all__ = [
    "S7Area",
    "S7ConnectionType",
    "S7CPUProfile",
    "S7Engine",
    "S7FlowConfig",
    "S7Function",
    "S7ReadArea",
    "S7WriteArea",
    "S7_CPU_PROFILES",
    "get_cpu_profile",
]
