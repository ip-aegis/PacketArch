# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Regional weather shared by every ESS (and DMS ambient sensor) in a scenario.

A pure function of (region seed, wall-clock time): seasonal and diurnal air
temperature, slow-moving fronts, precipitation events, fog when the air is
saturated, and pavement temperature driven by solar gain and night cooling.
Stations in one scenario see the same weather with small per-site offsets,
so an RWIS and a nearby sign never disagree about whether it is snowing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.protocol_engines.snmp.ntcip._model import NtcipClock, smooth_noise, unit

_FRONT_PERIODS_S = (3.3 * 86400, 1.7 * 86400, 0.61 * 86400)
_WET_PERIODS_S = (2.9 * 86400, 1.1 * 86400, 0.37 * 86400, 0.13 * 86400)


@dataclass(frozen=True)
class Weather:
    air_c: float
    dewpoint_c: float
    rh_pct: float
    wind_ms: float
    gust_ms: float
    wind_dir_deg: int
    pressure_hpa: float
    precip_mm_h: float
    precip_kind: str          # "none" | "rain" | "snow"
    visibility_m: float
    fog: bool
    surface_c: float
    pavement_c: float
    surface_wet: bool


def regional(region_seed: int, clock: NtcipClock, site_seed: int = 0) -> Weather:
    t = clock.epoch_s
    seasonal = 11.0 - 14.0 * math.cos(2 * math.pi * (clock.day_of_year - 15) / 365.25)
    diurnal = 6.0 * math.sin(2 * math.pi * (clock.hour - 9.0) / 24.0)
    front = 4.0 * smooth_noise(region_seed, t, _FRONT_PERIODS_S)
    site = (unit(site_seed, "t") - 0.5) * 1.2
    air = seasonal + diurnal + front + site

    wet = smooth_noise(region_seed ^ 0x5A5A, t, _WET_PERIODS_S)
    raining = wet > 0.45
    precip = max(0.0, (wet - 0.45) * 18.0) if raining else 0.0
    kind = "none" if not raining else ("snow" if air < 0.5 else "rain")

    spread = 0.5 if raining else 3.0 + 4.0 * (0.5 + 0.5 * math.sin(2 * math.pi * (clock.hour - 15) / 24))
    dew = air - spread
    rh = 100.0 * math.exp(17.625 * dew / (243.04 + dew)) / math.exp(17.625 * air / (243.04 + air))
    fog = rh > 97.0 and 3 <= clock.hour <= 9 and not raining

    wind = 3.0 + 2.5 * smooth_noise(region_seed ^ 0x77, t, (0.9 * 86400, 0.21 * 86400)) + (3.0 if raining else 0.0)
    wind = max(0.3, wind)
    gust = wind * (1.4 + 0.3 * unit(region_seed, "gust", int(t // 600)))
    wind_dir = int((225 + 120 * smooth_noise(region_seed ^ 0x33, t, (1.3 * 86400, 0.4 * 86400))) % 360)
    pressure = 1013.0 + 12.0 * smooth_noise(region_seed, t, _FRONT_PERIODS_S) - (6.0 if raining else 0.0)

    if fog:
        visibility = 150 + 600 * unit(region_seed, "fog", int(t // 900))
    elif kind == "snow":
        visibility = max(200.0, 4000.0 - precip * 900)
    elif kind == "rain":
        visibility = max(1500.0, 12000.0 - precip * 1200)
    else:
        visibility = 16000.0

    sun = max(0.0, math.sin(math.pi * (clock.hour - 6.0) / 13.0)) if 6 <= clock.hour <= 19 else 0.0
    solar_gain = sun * (4.0 + 8.0 * (0.5 - 0.5 * math.cos(2 * math.pi * (clock.day_of_year - 15) / 365.25)))
    surface = air + solar_gain - (1.8 if sun == 0 and not raining else 0.0)
    pavement = seasonal + 0.4 * diurnal + 0.5 * solar_gain + 1.0
    surface_wet = raining or smooth_noise(region_seed ^ 0x5A5A, t - 5400, _WET_PERIODS_S) > 0.45

    return Weather(
        air_c=air, dewpoint_c=dew, rh_pct=min(100.0, rh), wind_ms=wind, gust_ms=gust,
        wind_dir_deg=wind_dir, pressure_hpa=pressure, precip_mm_h=precip, precip_kind=kind,
        visibility_m=visibility, fog=fog, surface_c=surface, pavement_c=pavement,
        surface_wet=surface_wet,
    )


def solar_fraction(clock: NtcipClock) -> float:
    """0 at night, 1 at solar noon — drives DMS photocells."""
    if not 6 <= clock.hour <= 19:
        return 0.0
    return max(0.0, math.sin(math.pi * (clock.hour - 6.0) / 13.0))
