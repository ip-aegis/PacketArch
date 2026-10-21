# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTCIP 1203 Dynamic Message Sign (1.3.6.1.4.1.1206.4.2.3).

A full-matrix freeway sign run from central. By day it shows travel times
that are recomputed every two minutes; a few times a day an incident message
replaces them; overnight it is blank. Central reads ``dmsMsgTableSource`` to
learn which message-table entry is on the sign, then reads that entry's
MULTI string, which is the two-step query real ATMS software performs.

``dmsMessageCRC`` is CRC-16 (ISO/IEC 3309, X.25 form) over the MULTI string,
beacon and pixel-service octets, byte-swapped. That matches MnDOT IRIS's
DmsMessageCRC, which interoperates with production signs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.protocol_engines.snmp.ntcip._model import NtcipClock, NtcipDevice, instance, unit, value
from app.protocol_engines.snmp.ntcip.weather import regional, solar_fraction

# dmsMessageMemoryType
CHANGEABLE, BLANK = 3, 7
# dmsMessageStatus valid(4); dmsControlMode central(4); dmsSignType vmsFull(6)
_VALID, _CENTRAL, _VMS_FULL = 4, 4, 6
_INFINITE = 65535                 # dmsMessageTimeRemaining: infinite duration
_OWNER = "central"

TRAVEL_TIME_MSG, INCIDENT_MSG = 1, 2
_INCIDENT_TEXT = (
    "CRASH AHEAD[nl]RIGHT LANE BLOCKED[nl]USE CAUTION",
    "STALLED VEHICLE[nl]LEFT LANE BLOCKED[nl]EXPECT DELAYS",
    "ROAD WORK AHEAD[nl]RIGHT 2 LANES CLOSED[nl]MERGE LEFT",
    "DEBRIS ON ROAD[nl]SHOULDER BLOCKED[nl]USE CAUTION",
)
_DESTINATIONS = (
    ("DOWNTOWN", "AIRPORT"), ("I-94", "HWY 62"), ("I-35W", "US 169"), ("DOWNTOWN", "I-494"),
)


def crc16_x25(data: bytes) -> int:
    """CRC-16/X-25: poly 0x1021 reflected, init 0xFFFF, xorout 0xFFFF."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc ^ 0xFFFF


def message_crc(multi: str, beacon: int = 0, pixel_service: int = 0) -> int:
    """dmsMessageCRC as deployed central software computes it."""
    crc = crc16_x25(multi.encode("ascii") + bytes([beacon, pixel_service]))
    return ((crc & 0xFF) << 8) | (crc >> 8)


def message_id_code(memory_type: int, number: int, crc: int) -> bytes:
    """MessageIDCode OCTET STRING: memoryType(1) messageNumber(2) CRC(2)."""
    return bytes([memory_type, number >> 8, number & 0xFF, crc >> 8, crc & 0xFF])


@dataclass(frozen=True)
class Message:
    memory_type: int
    number: int
    multi: str

    @property
    def crc(self) -> int:
        return 0 if self.memory_type == BLANK else message_crc(self.multi)


def _incident_window(dev: NtcipDevice, clock: NtcipClock) -> int | None:
    """Index of today's incident text if one is on the sign now."""
    day = clock.local_day
    for i in range(int(unit(dev.seed, "incidents", day) * 3)):        # 0-2 per day
        start = 6.5 + 13.0 * unit(dev.seed, "inc_start", day, i)
        hours = (25 + 50 * unit(dev.seed, "inc_len", day, i)) / 60.0
        if start <= clock.hour < start + hours:
            return int(unit(dev.seed, "inc_text", day, i) * len(_INCIDENT_TEXT))
    return None


def current_message(dev: NtcipDevice, clock: NtcipClock) -> Message:
    if not 5.5 <= clock.hour < 21.5:
        return Message(BLANK, 1, "")
    incident = _incident_window(dev, clock)
    if incident is not None:
        return Message(CHANGEABLE, INCIDENT_MSG, _INCIDENT_TEXT[incident])
    first, second = _DESTINATIONS[dev.seed % len(_DESTINATIONS)]
    bucket = int(clock.epoch_s // 120)              # travel times refresh every 2 min
    congestion = 1.0
    if 6.5 <= clock.hour < 9.0 or 15.0 <= clock.hour < 18.5:
        congestion = 1.6
    lines = []
    for i, dest in enumerate((first, second)):
        free_flow = 6 + int(unit(dev.seed, "tt", i) * 12)
        minutes = int(round(free_flow * congestion * (0.9 + 0.25 * unit(dev.seed, "ttn", i, bucket))))
        lines.append(f"{dest} {minutes} MIN")
    return Message(CHANGEABLE, TRAVEL_TIME_MSG, "[jl3]" + "[nl][jl3]".join(lines))


def snapshot(dev: NtcipDevice, clock: NtcipClock) -> dict[str, tuple[Any, str]]:
    """All modelled 1203 instances for this sign at ``clock``."""
    msg = current_message(dev, clock)
    weather = regional(dev.region_seed, clock, dev.seed)
    sun = solar_fraction(clock)
    ambient = int(round(weather.air_c))
    housing = ambient + 4 + int(round(10 * sun))
    out = dict([
        value("dmsSignType", _VMS_FULL),
        value("vmsSignHeightPixels", 27),
        value("vmsSignWidthPixels", 105 if dev.seed % 2 else 125),
        value("dmsNumChangeableMsg", 2),
        value("dmsMaxChangeableMsg", 100),
        value("dmsMsgTableSource", message_id_code(msg.memory_type, msg.number, msg.crc)),
        value("dmsMessageTimeRemaining", _INFINITE),
        value("dmsControlMode", _CENTRAL),
        value("dmsIllumControl", 2),                       # photocell(2)
        value("dmsIllumPhotocellLevelStatus", int(200 + 65000 * sun)),
        value("dmsIllumBrightLevelStatus", 1 + int(round(15 * sun))),
        value("shortErrorStatus", 0),
        value("dmsStatDoorOpen", 0),
        value("lineVolts", 118 + dev.seed % 5),
        value("tempMinAmbient", ambient - 1),
        value("tempMaxAmbient", ambient + 1),
        value("tempMinSignHousing", housing - 2),
        value("tempMaxSignHousing", housing + 2),
    ])
    for entry in (msg, Message(BLANK, 1, "")):
        idx = (entry.memory_type, entry.number)
        out.update([
            value("dmsMessageMultiString", entry.multi, *idx),
            value("dmsMessageOwner", _OWNER if entry.memory_type == CHANGEABLE else "", *idx),
            value("dmsMessageCRC", entry.crc, *idx),
            value("dmsMessageBeacon", 0, *idx),
            value("dmsMessagePixelService", 0, *idx),
            value("dmsMessageRunTimePriority", 3, *idx),
            value("dmsMessageStatus", _VALID, *idx),
        ])
    return out


STATUS_BLOCK = [
    instance("dmsMsgTableSource"),
    instance("dmsMessageTimeRemaining"),
    instance("dmsControlMode"),
    instance("shortErrorStatus"),
    instance("dmsIllumBrightLevelStatus"),
    instance("dmsIllumPhotocellLevelStatus"),
    instance("tempMinSignHousing"),
    instance("tempMaxSignHousing"),
    instance("lineVolts"),
]


def message_block(dev: NtcipDevice, clock: NtcipClock) -> list[str]:
    """Follow-up read of the entry dmsMsgTableSource pointed at (none if blank)."""
    msg = current_message(dev, clock)
    if msg.memory_type == BLANK:
        return []
    idx = (msg.memory_type, msg.number)
    return [
        instance("dmsMessageMultiString", *idx),
        instance("dmsMessageOwner", *idx),
        instance("dmsMessageStatus", *idx),
    ]


CONFIG_BLOCK = [
    instance("dmsSignType"),
    instance("vmsSignHeightPixels"),
    instance("vmsSignWidthPixels"),
    instance("dmsNumChangeableMsg"),
    instance("dmsMaxChangeableMsg"),
]
