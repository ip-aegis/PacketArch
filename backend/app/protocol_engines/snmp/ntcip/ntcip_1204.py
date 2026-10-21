# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTCIP 1204 Environmental Sensor Station / RWIS (1.3.6.1.4.1.1206.4.2.5).

Humidity, wind, precipitation rate and pressure are answered from the
"BUFR" objects (essBufr*, 1206.4.2.5.1.*). NTCIP 1204 v04 deprecates them,
but they are what deployed central software still polls (MnDOT IRIS's
MIB1204 reads exactly these), so they are what a sensor sees on real
networks. See SPEC_NEEDS.md.
"""

from __future__ import annotations

from typing import Any

from app.protocol_engines.snmp.ntcip._model import NtcipClock, NtcipDevice, instance, value
from app.protocol_engines.snmp.ntcip.weather import regional

# essNtcipCategory permanent(2)
_PERMANENT = 2
# essPrecipSituation
_NO_PRECIP, _SNOW = 3, (7, 8, 9)
_RAIN = (10, 11, 12)
# essVisibilitySituation
_VIS_CLEAR, _VIS_FOG, _VIS_BLOWING_SNOW = 3, 4, 6
# essSurfaceStatus
_DRY, _WET, _CHEM_WET, _ICE_WARNING, _SNOW_WARNING = 3, 5, 6, 7, 9
# essSurfaceBlackIceSignal
_NO_ICE, _BLACK_ICE = 2, 3


def _tenths(c: float) -> int:
    return max(-1000, min(1000, int(round(c * 10))))


def _intensity(rate_mm_h: float, codes: tuple[int, int, int]) -> int:
    if rate_mm_h < 2.5:
        return codes[0]
    if rate_mm_h < 7.6:
        return codes[1]
    return codes[2]


def snapshot(dev: NtcipDevice, clock: NtcipClock) -> dict[str, tuple[Any, str]]:
    """All modelled 1204 instances for this station at ``clock``."""
    w = regional(dev.region_seed, clock, dev.seed)
    if w.precip_kind == "snow":
        precip_situation = _intensity(w.precip_mm_h, _SNOW)
    elif w.precip_kind == "rain":
        precip_situation = _intensity(w.precip_mm_h, _RAIN)
    else:
        precip_situation = _NO_PRECIP

    treated = w.surface_c < 1.0          # agencies pre-treat when near freezing
    if w.precip_kind == "snow":
        surface_status = _SNOW_WARNING
    elif w.surface_wet and w.surface_c <= 0.0:
        surface_status = _ICE_WARNING
    elif w.surface_wet:
        surface_status = _CHEM_WET if treated else _WET
    else:
        surface_status = _DRY
    freeze_point = -9.0 if treated else 0.0

    if w.fog:
        vis_situation = _VIS_FOG
    elif w.precip_kind == "snow" and w.wind_ms > 6:
        vis_situation = _VIS_BLOWING_SNOW
    else:
        vis_situation = _VIS_CLEAR

    # g/m^2/s in tenths: 1 mm/h of water = 1000 g/m^2 / 3600 s
    precip_rate = int(round(w.precip_mm_h * 1000 / 3600 * 10))

    return dict([
        value("essNtcipCategory", _PERMANENT),
        value("essTypeofStation", 1),
        value("essNumTemperatureSensors", 1),
        value("numEssPavementSensors", 1),
        value("essAirTemperature", _tenths(w.air_c), 1),
        value("essDewpointTemp", _tenths(w.dewpoint_c)),
        value("essMaxTemp", _tenths(w.air_c + 3.0)),
        value("essMinTemp", _tenths(w.air_c - 4.0)),
        value("essRelativeHumidity", int(round(w.rh_pct))),
        value("essAvgWindDirection", w.wind_dir_deg),
        value("essAvgWindSpeed", int(round(w.wind_ms * 10))),
        value("essSpotWindSpeed", int(round(w.wind_ms * 10 * 1.05))),
        value("essMaxWindGustSpeed", int(round(w.gust_ms * 10))),
        value("essPrecipRate", precip_rate),
        value("essPrecipSituation", precip_situation),
        value("essAtmosphericPressure", int(round(w.pressure_hpa * 10))),
        value("essVisibility", int(round(w.visibility_m * 10))),
        value("essVisibilitySituation", vis_situation),
        value("essSurfaceStatus", surface_status, 1),
        value("essSurfaceTemperature", _tenths(w.surface_c), 1),
        value("essPavementTemperature", _tenths(w.pavement_c), 1),
        value("essSurfaceFreezePoint", _tenths(freeze_point), 1),
        value("essSurfaceBlackIceSignal", _BLACK_ICE if surface_status == _ICE_WARNING else _NO_ICE, 1),
    ])


STATUS_BLOCK = [
    instance("essAirTemperature", 1),
    instance("essDewpointTemp"),
    instance("essRelativeHumidity"),
    instance("essAvgWindDirection"),
    instance("essAvgWindSpeed"),
    instance("essMaxWindGustSpeed"),
    instance("essPrecipRate"),
    instance("essPrecipSituation"),
    instance("essAtmosphericPressure"),
    instance("essVisibility"),
    instance("essVisibilitySituation"),
    instance("essSurfaceStatus", 1),
    instance("essSurfaceTemperature", 1),
    instance("essPavementTemperature", 1),
    instance("essSurfaceFreezePoint", 1),
    instance("essSurfaceBlackIceSignal", 1),
]

CONFIG_BLOCK = [
    instance("essNtcipCategory"),
    instance("essTypeofStation"),
    instance("essNumTemperatureSensors"),
    instance("numEssPavementSensors"),
]
