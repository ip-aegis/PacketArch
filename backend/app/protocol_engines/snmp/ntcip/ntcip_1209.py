# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTCIP 1209 Transportation Sensor System (1.3.6.1.4.1.1206.4.2.4).

A mainline detection station (e.g. a side-fire radar): one sensor zone per
lane, both directions, reporting volume, occupancy and mean speed per
sample period. Values come from ``sampleDataTable`` (INDEX zone, entry,
class): entry 1 is the period in progress, entry 2 the last completed one,
class 1 the all-vehicle aggregate. The deprecated ``dataCollectionTable``
mirrors entry 2 / class 1, as the MIB requires of devices that keep it.

Traffic is a deterministic function of (station seed, sample period):
lane flow follows the time-of-day demand curve; a seeded share of stations
sit at a bottleneck and break down to congested speeds at peak demand.
Occupancy follows from density (flow / speed) times effective vehicle
length. See SPEC_NEEDS.md for confidence tiers.
"""

from __future__ import annotations

from typing import Any

from app.protocol_engines.snmp.ntcip._model import (
    NtcipClock,
    NtcipDevice,
    demand_level,
    instance,
    smooth_noise,
    unit,
    value,
)

SAMPLE_PERIOD_S = 30
_OK = 2                  # sensorSystemStatus / zone status oK(2)
_TECH_OTHER = 1          # sensorTechnology other(1): microwave radar
_CLOCK_YES = 1
_ENTRIES = 2             # 1 = in progress, 2 = last completed
_CLASS_ALL = 1
_MISSING = 65535

_LANE_CAPACITY_VPH = 1900.0
_FREE_FLOW_KMH = 105.0
_EFFECTIVE_LENGTH_KM = 0.0065   # vehicle + detection zone


def zone_count(dev: NtcipDevice) -> int:
    """Lanes covered: two to four per direction."""
    return 2 * (2 + int(unit(dev.seed, "lanes") * 3))


def _zone_label(dev: NtcipDevice, zone: int) -> str:
    per_dir = zone_count(dev) // 2
    direction = "NB" if zone <= per_dir else "SB"
    lane = (zone - 1) % per_dir + 1
    return f"{direction} Lane {lane}"


def _lane_sample(dev: NtcipDevice, zone: int, period: int, local_s: float, fraction: float = 1.0) -> tuple[int, int, int]:
    """(volume, occupancy tenths %, speed tenths km/h) for one lane-period."""
    hour = (local_s % 86400) / 3600.0
    demand = demand_level(hour)
    per_dir = zone_count(dev) // 2
    lane = (zone - 1) % per_dir
    lane_share = 1.0 - 0.12 * lane / max(1, per_dir - 1)   # inside lanes carry more
    wobble = 1.0 + 0.08 * smooth_noise(dev.seed + zone, local_s, (600.0, 1700.0))
    flow_vph = _LANE_CAPACITY_VPH * demand * lane_share * wobble

    bottleneck = unit(dev.seed, "bottleneck") < 0.3
    if bottleneck and demand >= 0.95:
        speed = 35.0 + 20.0 * unit(dev.seed, "jam", period)
        flow_vph *= 0.75                                   # capacity drop
    else:
        speed = _FREE_FLOW_KMH - 25.0 * max(0.0, demand - 0.6) - 4.0 * lane
        speed += 3.0 * smooth_noise(dev.seed - zone, local_s, (300.0, 900.0))

    exact = flow_vph * SAMPLE_PERIOD_S / 3600.0 * fraction
    volume = int(exact) + (1 if unit(dev.seed, zone, period, "dither") < exact % 1 else 0)
    occupancy = min(1000, int(round(flow_vph / speed * _EFFECTIVE_LENGTH_KM * 1000)))
    speed_tenths = int(round(speed * 10)) if volume else _MISSING
    return volume, occupancy, speed_tenths


def snapshot(dev: NtcipDevice, clock: NtcipClock) -> dict[str, tuple[Any, str]]:
    """All modelled 1209 instances for this station at ``clock``."""
    local = clock.local_s
    period = int(local // SAMPLE_PERIOD_S)
    into = local - period * SAMPLE_PERIOD_S
    zones = zone_count(dev)
    out: dict[str, tuple[Any, str]] = dict([
        value("sensorSystemStatus", _OK),
        value("maxSensorZones", zones),
        value("clockAvailable", _CLOCK_YES),
        value("sensorTechnology", _TECH_OTHER),
        value("maxSampleDataEntries", _ENTRIES),
    ])
    for z in range(1, zones + 1):
        out.update(dict([
            value("sensorZoneNumber", z, z),
            value("sensorZoneSamplePeriod", SAMPLE_PERIOD_S, z),
            value("sensorZoneLabel", _zone_label(dev, z), z),
            value("sensorZoneStatus", _OK, z),
            value("numSampleDataEntries", _ENTRIES, z),
            value("numSensorZoneClass", 1, z),
        ]))
        rows = {
            1: (period, local, _lane_sample(dev, z, period, local, into / SAMPLE_PERIOD_S)),
            2: (period - 1, period * SAMPLE_PERIOD_S,
                _lane_sample(dev, z, period - 1, (period - 1) * SAMPLE_PERIOD_S)),
        }
        for entry, (seq, end_s, (vol, occ, spd)) in rows.items():
            idx = (z, entry, _CLASS_ALL)
            out.update(dict([
                value("sampleEndTime", int(end_s) % 2**32, *idx),
                value("sampleVolumeData", vol, *idx),
                value("samplePercentOccupancy", occ, *idx),
                value("sampleSpeedData", spd, *idx),
                value("sampleZoneStatus", _OK, *idx),
                value("sampleSequenceNumber", seq % 65536, *idx),
            ]))
        _, end_s, (vol, occ, spd) = rows[2]
        out.update(dict([
            value("endTime", int(end_s) % 2**32, z),
            value("volumeData", vol, z),
            value("percentOccupancy", occ, z),
            value("speedData", spd, z),
            value("zoneStatus", _OK, z),
        ]))
    return out


def status_block(dev: NtcipDevice, _clock: NtcipClock) -> list[str]:
    """Last completed period, every lane: what central software collects."""
    oids = [instance("sensorSystemStatus")]
    for z in range(1, zone_count(dev) + 1):
        idx = (z, 2, _CLASS_ALL)
        oids += [instance(n, *idx) for n in (
            "sampleSequenceNumber", "sampleEndTime", "sampleVolumeData",
            "samplePercentOccupancy", "sampleSpeedData", "sampleZoneStatus")]
    return oids


def config_block(dev: NtcipDevice, _clock: NtcipClock) -> list[str]:
    oids = [instance(n) for n in ("maxSensorZones", "sensorTechnology", "clockAvailable",
                                  "maxSampleDataEntries")]
    for z in range(1, zone_count(dev) + 1):
        oids += [instance(n, z) for n in ("sensorZoneLabel", "sensorZoneSamplePeriod",
                                          "sensorZoneStatus", "numSensorZoneClass")]
    return oids
