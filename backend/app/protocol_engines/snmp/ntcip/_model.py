# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Shared building blocks for the NTCIP device models.

Every NTCIP device model is a *pure function* of (device seed, wall-clock
epoch). That is what lets several pollers of one controller (ATMS at 1 s,
historian at 60 s, engineering workstation at 10 min) see one consistent
device, and lets the PCAP path and the live agent emit the same intersection.
No per-flow mutable state is involved.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass
from typing import Any

from app.protocol_engines.snmp.ntcip._mib_table import MIB_OBJECTS


def stable_seed(*parts: object) -> int:
    """Process-independent 32-bit seed (``hash()`` is salted per process)."""
    return zlib.crc32(":".join(str(p) for p in parts).encode())


def unit(seed: int, *keys: object) -> float:
    """Deterministic pseudo-random float in [0, 1) for (seed, keys)."""
    return stable_seed(seed, *keys) / 4294967296.0


def smooth_noise(seed: int, t_s: float, periods_s: tuple[float, ...]) -> float:
    """Smooth, deterministic noise in roughly [-1, 1] (sum of seeded sines)."""
    total = 0.0
    for i, period in enumerate(periods_s):
        phase = unit(seed, "phase", i) * 2 * math.pi
        total += math.sin(2 * math.pi * t_s / period + phase)
    return total / len(periods_s)


@dataclass(frozen=True)
class NtcipDevice:
    """Identity inputs for an NTCIP device model."""

    seed: int          # per device: crc32(scenario_id:device_id)
    region_seed: int   # per scenario: shared corridor cycle lengths, weather
    vendor: str = ""
    model: str = ""
    firmware: str = ""


@dataclass(frozen=True)
class NtcipClock:
    """Wall-clock instant plus the site's UTC offset."""

    epoch_s: float
    utc_offset_s: int = 0

    @property
    def local_s(self) -> float:
        return self.epoch_s + self.utc_offset_s

    @property
    def local_day(self) -> int:
        return int(self.local_s // 86400)

    @property
    def seconds_of_day(self) -> float:
        return self.local_s % 86400

    @property
    def hour(self) -> float:
        return self.seconds_of_day / 3600.0

    @property
    def day_of_year(self) -> int:
        # 1970-01-01 is day 0; close enough for a seasonal curve.
        return int((self.local_s / 86400.0) % 365.2425)


def oid_of(name: str) -> str:
    return MIB_OBJECTS[name][0]


def instance(name: str, *index: int) -> str:
    """Instance OID: ``<column>.<index...>`` for table columns, ``<scalar>.0``."""
    base, _vtype, _access, columnar = MIB_OBJECTS[name]
    if columnar:
        if not index:
            raise ValueError(f"{name} is a table column and needs an index")
        return base + "." + ".".join(str(i) for i in index)
    return base + ".0"


def value(name: str, val: Any, *index: int) -> tuple[str, tuple[Any, str]]:
    """``(instance_oid, (value, value_type))`` with the MIB's value type."""
    return instance(name, *index), (val, MIB_OBJECTS[name][1])


def demand_level(hour: float) -> float:
    """Typical urban arterial demand (0..1) by local hour."""
    if hour < 5:
        return 0.15
    if hour < 6.5:
        return 0.45
    if hour < 9:
        return 0.95
    if hour < 15:
        return 0.65
    if hour < 18.5:
        return 1.0
    if hour < 22:
        return 0.5
    return 0.25
