# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTCIP (National Transportation Communications for ITS Protocol) over SNMP.

Device models (each a pure function of device seed + wall-clock time):

- NTCIP 1201 Global objects — every device (``ntcip_1201``)
- NTCIP 1202 Actuated Signal Controller — ``asc`` (``ntcip_1202``)
- NTCIP 1203 Dynamic Message Sign — ``dms`` (``ntcip_1203``)
- NTCIP 1204 Environmental Sensor Station / RWIS — ``ess`` (``ntcip_1204``)

OIDs come from ``_mib_table`` (generated from the NTCIP MIB files by
``scripts/ntcip/gen_mib_table.py``). Sources and open questions:
``SPEC_NEEDS.md`` in this package.

Which objects a flow polls depends on what the destination IS (its NTCIP
kind) and who is ASKING (the poller's profile): an ATMS polls live status
every second, a historian collects volume/occupancy and readings, an
engineering workstation inventories configuration, and a jump server or
NMS sticks to MIB-II.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.protocol_engines.snmp.ntcip import ntcip_1201, ntcip_1202, ntcip_1203, ntcip_1204
from app.protocol_engines.snmp.ntcip._model import NtcipClock, NtcipDevice, stable_seed

NTCIP_ROOT = "1.3.6.1.4.1.1206.4.2"
NTCIP_ARC_KIND = {
    f"{NTCIP_ROOT}.1": "asc",
    f"{NTCIP_ROOT}.3": "dms",
    f"{NTCIP_ROOT}.5": "ess",
}

KIND_BY_DEVICE_TYPE = {
    "asc": "asc",
    "atc": "asc",
    "traffic_controller": "asc",
    "signal_controller": "asc",
    "traffic_signal_controller": "asc",
    "dms": "dms",
    "vms": "dms",
    "cms": "dms",
    "message_sign": "dms",
    "dynamic_message_sign": "dms",
    "ess": "ess",
    "rwis": "ess",
    "weather_station": "ess",
    "environmental_sensor": "ess",
}
# Device types too generic to decide from; fall back to the sysObjectID arc.
GENERIC_DEVICE_TYPES = {"", "controller", "cabinet_controller", "field_device", "unknown", "generic", "device"}

STATUS, DATA_COLLECTION, CONFIG = "status", "data_collection", "config"
PROFILE_BY_SOURCE_TYPE = {
    "historian": DATA_COLLECTION,
    "process_historian": DATA_COLLECTION,
    "data_collector": DATA_COLLECTION,
    "workstation": CONFIG,
    "engineering_workstation": CONFIG,
    "ews": CONFIG,
    "laptop": CONFIG,
}
# Pollers that only ever read MIB-II from field devices.
MIB2_ONLY_SOURCE_TYPES = {"jump_server", "nms", "network_monitor", "network_management", "snmp_manager"}


def resolve_kind(config: dict, destination: Any, sys_object_id: str | None) -> str | None:
    """NTCIP device kind of a flow's destination, or None for plain SNMP."""
    if config.get("ntcip") is False:
        return None
    explicit = config.get("device_type")
    if explicit:
        return KIND_BY_DEVICE_TYPE.get(str(explicit).lower())
    dtype = str(getattr(destination, "device_type", None) or "").lower()
    if dtype in KIND_BY_DEVICE_TYPE:
        return KIND_BY_DEVICE_TYPE[dtype]
    if dtype not in GENERIC_DEVICE_TYPES:
        return None
    oid = (sys_object_id or "").lstrip(".")
    for arc, kind in NTCIP_ARC_KIND.items():
        if oid == arc or oid.startswith(arc + "."):
            return kind
    return None


def resolve_profile(config: dict, source: Any) -> str | None:
    """What the poller reads: status / data_collection / config, or None (MIB-II)."""
    explicit = config.get("ntcip_profile")
    if explicit:
        return explicit if explicit in (STATUS, DATA_COLLECTION, CONFIG) else None
    stype = str(getattr(source, "device_type", None) or "").lower()
    if stype in MIB2_ONLY_SOURCE_TYPES:
        return None
    return PROFILE_BY_SOURCE_TYPE.get(stype, STATUS)


@dataclass(frozen=True)
class PollGroup:
    """One GetRequest PDU in a poll cycle.

    ``period_s`` 0 means every poll; otherwise the group is sent on the first
    poll of each ``period_s`` window (e.g. a new 60 s volume period).
    """

    name: str
    period_s: int
    oids: Callable[[NtcipDevice, NtcipClock], list[str]]


def _static(oids: list[str]) -> Callable[[NtcipDevice, NtcipClock], list[str]]:
    return lambda _dev, _clock: list(oids)


_IDENTITY = PollGroup("identity", 0, _static(ntcip_1201.identity_oids()))
_CLOCK = PollGroup("clock", 3600, _static(ntcip_1201.clock_oids()))

POLL_PLANS: dict[tuple[str, str], list[PollGroup]] = {
    ("asc", STATUS): [
        PollGroup("asc_status", 0, _static(ntcip_1202.STATUS_BLOCK)),
        PollGroup("asc_volume", ntcip_1202.VOLUME_PERIOD_S, _static(ntcip_1202.VOLUME_BLOCK)),
        _CLOCK,
    ],
    ("asc", DATA_COLLECTION): [PollGroup("asc_volume", 0, _static(ntcip_1202.VOLUME_BLOCK))],
    ("asc", CONFIG): [_IDENTITY, PollGroup("asc_config", 0, _static(ntcip_1202.CONFIG_BLOCK))],
    ("dms", STATUS): [
        PollGroup("dms_status", 0, _static(ntcip_1203.STATUS_BLOCK)),
        PollGroup("dms_message", 0, ntcip_1203.message_block),
        _CLOCK,
    ],
    ("dms", DATA_COLLECTION): [PollGroup("dms_status", 0, _static(ntcip_1203.STATUS_BLOCK))],
    ("dms", CONFIG): [_IDENTITY, PollGroup("dms_config", 0, _static(ntcip_1203.CONFIG_BLOCK))],
    ("ess", STATUS): [PollGroup("ess_status", 0, _static(ntcip_1204.STATUS_BLOCK)), _CLOCK],
    ("ess", DATA_COLLECTION): [PollGroup("ess_status", 0, _static(ntcip_1204.STATUS_BLOCK))],
    ("ess", CONFIG): [_IDENTITY, PollGroup("ess_config", 0, _static(ntcip_1204.CONFIG_BLOCK))],
}

_KIND_SNAPSHOT = {
    "asc": ntcip_1202.snapshot,
    "dms": ntcip_1203.snapshot,
    "ess": ntcip_1204.snapshot,
}


def make_device(destination: Any) -> NtcipDevice:
    """NtcipDevice for a DeviceContext (seeded by scenario + device id)."""
    fp = getattr(destination, "vendor_fingerprint", None) or {}
    scenario = getattr(destination, "scenario_id", None) or ""
    return NtcipDevice(
        seed=stable_seed(scenario, destination.device_id),
        region_seed=stable_seed("region", scenario),
        vendor=str(getattr(destination, "vendor", None) or fp.get("vendor") or ""),
        model=str(getattr(destination, "model", None) or fp.get("model") or ""),
        firmware=str(getattr(destination, "firmware_version", None) or fp.get("firmware_version") or ""),
    )


def snapshot(kind: str, dev: NtcipDevice, clock: NtcipClock) -> dict[str, tuple[Any, str]]:
    """Every modelled instance OID for this device: 1201 globals + its kind."""
    out = ntcip_1201.snapshot(kind, dev, clock)
    out.update(_KIND_SNAPSHOT[kind](dev, clock))
    return out


__all__ = [
    "CONFIG",
    "DATA_COLLECTION",
    "STATUS",
    "NtcipClock",
    "NtcipDevice",
    "POLL_PLANS",
    "PollGroup",
    "make_device",
    "resolve_kind",
    "resolve_profile",
    "snapshot",
]
