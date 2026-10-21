# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTCIP 1201 Global Objects (1.3.6.1.4.1.1206.4.2.6).

Every NTCIP field device implements the global group: module inventory, the
database transaction object, and time management (globalTime is what central
systems read — and periodically SET — to keep the cabinet clock in sync).
"""

from __future__ import annotations

from typing import Any

from app.protocol_engines.snmp.ntcip._model import NtcipClock, NtcipDevice, instance, value

# Which standards each device kind advertises in controllerBaseStandards.
BASE_STANDARDS = {
    "asc": "NTCIP 1201 v03, NTCIP 1202 v03",
    "dms": "NTCIP 1201 v03, NTCIP 1203 v03",
    "ess": "NTCIP 1201 v03, NTCIP 1204 v04",
}

# globalDaylightSaving: enableUSDST(3)
_ENABLE_US_DST = 3
# moduleType: hardware(2), software(3)
_HARDWARE, _SOFTWARE = 2, 3


def snapshot(kind: str, dev: NtcipDevice, clock: NtcipClock) -> dict[str, tuple[Any, str]]:
    """All modelled 1201 instances for this device at ``clock``."""
    vendor = dev.vendor or "Generic"
    model = dev.model or "Controller"
    firmware = dev.firmware or "1.0"
    return dict([
        value("globalTime", int(clock.epoch_s)),
        value("globalDaylightSaving", _ENABLE_US_DST),
        value("globalLocalTimeDifferential", clock.utc_offset_s),
        value("controllerLocalTime", int(clock.local_s)),
        value("globalMaxModules", 2),
        value("moduleMake", vendor, 1),
        value("moduleModel", model, 1),
        value("moduleVersion", "Rev " + "ABCD"[dev.seed % 4], 1),
        value("moduleType", _HARDWARE, 1),
        value("moduleMake", vendor, 2),
        value("moduleModel", f"{model} firmware", 2),
        value("moduleVersion", firmware, 2),
        value("moduleType", _SOFTWARE, 2),
        value("controllerBaseStandards", BASE_STANDARDS.get(kind, "NTCIP 1201 v03")),
        value("dbCreateTransaction", 1),  # normal(1)
    ])


def identity_oids() -> list[str]:
    """What an engineering workstation reads to inventory a field device."""
    return [
        instance("globalMaxModules"),
        instance("moduleMake", 1), instance("moduleModel", 1), instance("moduleVersion", 1),
        instance("moduleMake", 2), instance("moduleModel", 2), instance("moduleVersion", 2),
        instance("controllerBaseStandards"),
        instance("globalTime"),
        instance("globalDaylightSaving"),
    ]


def clock_oids() -> list[str]:
    """Hourly clock check by central (Phase 1 adds the corrective SET)."""
    return [instance("globalTime"), instance("globalDaylightSaving")]
