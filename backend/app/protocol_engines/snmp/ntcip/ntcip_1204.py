"""NTCIP 1204 - Environmental Sensor Station (ESS) OIDs.

Defines OIDs for roadside weather station polling including:
- Atmospheric conditions (temperature, humidity, pressure)
- Wind measurements (speed, direction, gusts)
- Pavement conditions (temperature, state, water depth)
- Visibility and precipitation
"""

from dataclasses import dataclass, field
from typing import Any

from app.protocol_engines.snmp.oids import NTCIP_ESS, OIDDefinition


class AtmosphereOIDs:
    """NTCIP 1204 Atmospheric OIDs (1.3.6.1.4.1.1206.4.2.4.1)."""

    ESS_AIR_TEMPERATURE = OIDDefinition(
        oid=f"{NTCIP_ESS}.1.1.0",
        name="essAirTemperature",
        description="Air temperature in tenths of degrees Celsius",
        value_type="integer",
        access="read-only",
    )

    ESS_HUMIDITY = OIDDefinition(
        oid=f"{NTCIP_ESS}.1.2.0",
        name="essHumidity",
        description="Relative humidity in percent (0-100)",
        value_type="integer",
        access="read-only",
    )

    ESS_DEW_POINT = OIDDefinition(
        oid=f"{NTCIP_ESS}.1.3.0",
        name="essDewpoint",
        description="Dew point temperature in tenths of degrees Celsius",
        value_type="integer",
        access="read-only",
    )

    ESS_ATMOSPHERIC_PRESSURE = OIDDefinition(
        oid=f"{NTCIP_ESS}.1.4.0",
        name="essAtmosphericPressure",
        description="Atmospheric pressure in tenths of millibars",
        value_type="integer",
        access="read-only",
    )

    ESS_VISIBILITY = OIDDefinition(
        oid=f"{NTCIP_ESS}.1.5.0",
        name="essVisibility",
        description="Visibility distance in meters",
        value_type="integer",
        access="read-only",
    )

    ESS_VISIBILITY_SITUATION = OIDDefinition(
        oid=f"{NTCIP_ESS}.1.6.0",
        name="essVisibilitySituation",
        description="Visibility condition (1=clear, 2=fog, 3=smoke, 4=haze)",
        value_type="integer",
        access="read-only",
    )

    ALL = [
        ESS_AIR_TEMPERATURE,
        ESS_HUMIDITY,
        ESS_DEW_POINT,
        ESS_ATMOSPHERIC_PRESSURE,
        ESS_VISIBILITY,
        ESS_VISIBILITY_SITUATION,
    ]


class WindOIDs:
    """NTCIP 1204 Wind OIDs (1.3.6.1.4.1.1206.4.2.4.2)."""

    ESS_AVG_WIND_SPEED = OIDDefinition(
        oid=f"{NTCIP_ESS}.2.1.0",
        name="essAvgWindSpeed",
        description="Average wind speed in tenths of m/s",
        value_type="integer",
        access="read-only",
    )

    ESS_AVG_WIND_DIRECTION = OIDDefinition(
        oid=f"{NTCIP_ESS}.2.2.0",
        name="essAvgWindDirection",
        description="Average wind direction in degrees (0-359)",
        value_type="integer",
        access="read-only",
    )

    ESS_SPOT_WIND_SPEED = OIDDefinition(
        oid=f"{NTCIP_ESS}.2.3.0",
        name="essSpotWindSpeed",
        description="Instantaneous wind speed in tenths of m/s",
        value_type="integer",
        access="read-only",
    )

    ESS_SPOT_WIND_DIRECTION = OIDDefinition(
        oid=f"{NTCIP_ESS}.2.4.0",
        name="essSpotWindDirection",
        description="Instantaneous wind direction in degrees (0-359)",
        value_type="integer",
        access="read-only",
    )

    ESS_GUST_WIND_SPEED = OIDDefinition(
        oid=f"{NTCIP_ESS}.2.5.0",
        name="essGustWindSpeed",
        description="Wind gust speed in tenths of m/s",
        value_type="integer",
        access="read-only",
    )

    ESS_GUST_WIND_DIRECTION = OIDDefinition(
        oid=f"{NTCIP_ESS}.2.6.0",
        name="essGustWindDirection",
        description="Wind gust direction in degrees (0-359)",
        value_type="integer",
        access="read-only",
    )

    ALL = [
        ESS_AVG_WIND_SPEED,
        ESS_AVG_WIND_DIRECTION,
        ESS_SPOT_WIND_SPEED,
        ESS_SPOT_WIND_DIRECTION,
        ESS_GUST_WIND_SPEED,
        ESS_GUST_WIND_DIRECTION,
    ]


class PavementOIDs:
    """NTCIP 1204 Pavement Sensor OIDs (1.3.6.1.4.1.1206.4.2.4.3)."""

    ESS_SURFACE_TEMPERATURE = OIDDefinition(
        oid=f"{NTCIP_ESS}.3.1.0",
        name="essSurfaceTemperature",
        description="Pavement surface temperature in tenths of degrees Celsius",
        value_type="integer",
        access="read-only",
    )

    ESS_SURFACE_STATUS = OIDDefinition(
        oid=f"{NTCIP_ESS}.3.2.0",
        name="essSurfaceStatus",
        description="Pavement condition (1=dry, 2=wet, 3=ice, 4=snow, 5=slush)",
        value_type="integer",
        access="read-only",
    )

    ESS_PAVEMENT_TEMPERATURE = OIDDefinition(
        oid=f"{NTCIP_ESS}.3.3.0",
        name="essPavementTemperature",
        description="Subsurface pavement temperature in tenths of degrees Celsius",
        value_type="integer",
        access="read-only",
    )

    ESS_SURFACE_WATER_DEPTH = OIDDefinition(
        oid=f"{NTCIP_ESS}.3.4.0",
        name="essSurfaceWaterDepth",
        description="Water film depth on pavement in hundredths of mm",
        value_type="integer",
        access="read-only",
    )

    ESS_SURFACE_SALINITY = OIDDefinition(
        oid=f"{NTCIP_ESS}.3.5.0",
        name="essSurfaceSalinity",
        description="Surface salinity/contamination level",
        value_type="integer",
        access="read-only",
    )

    ESS_SURFACE_ICE_OR_WATER = OIDDefinition(
        oid=f"{NTCIP_ESS}.3.6.0",
        name="essSurfaceIceOrWater",
        description="Ice/water detection (1=none, 2=water, 3=ice)",
        value_type="integer",
        access="read-only",
    )

    ESS_SURFACE_CONDUCTIVITY = OIDDefinition(
        oid=f"{NTCIP_ESS}.3.7.0",
        name="essSurfaceConductivity",
        description="Surface conductivity percentage (0-100)",
        value_type="integer",
        access="read-only",
    )

    ESS_SURFACE_FREEZE_POINT = OIDDefinition(
        oid=f"{NTCIP_ESS}.3.8.0",
        name="essSurfaceFreezePoint",
        description="Freezing point of surface in tenths of degrees Celsius",
        value_type="integer",
        access="read-only",
    )

    ALL = [
        ESS_SURFACE_TEMPERATURE,
        ESS_SURFACE_STATUS,
        ESS_PAVEMENT_TEMPERATURE,
        ESS_SURFACE_WATER_DEPTH,
        ESS_SURFACE_SALINITY,
        ESS_SURFACE_ICE_OR_WATER,
        ESS_SURFACE_CONDUCTIVITY,
        ESS_SURFACE_FREEZE_POINT,
    ]


class PrecipitationOIDs:
    """NTCIP 1204 Precipitation OIDs (1.3.6.1.4.1.1206.4.2.4.4)."""

    ESS_PRECIP_YES_NO = OIDDefinition(
        oid=f"{NTCIP_ESS}.4.1.0",
        name="essPrecipYesNo",
        description="Precipitation detected (1=no, 2=yes)",
        value_type="integer",
        access="read-only",
    )

    ESS_PRECIP_RATE = OIDDefinition(
        oid=f"{NTCIP_ESS}.4.2.0",
        name="essPrecipRate",
        description="Precipitation rate in tenths of mm/hour",
        value_type="integer",
        access="read-only",
    )

    ESS_PRECIP_SITUATION = OIDDefinition(
        oid=f"{NTCIP_ESS}.4.3.0",
        name="essPrecipSituation",
        description="Precipitation type (1=none, 2=light, 3=moderate, 4=heavy)",
        value_type="integer",
        access="read-only",
    )

    ESS_PRECIP_ONE_HOUR = OIDDefinition(
        oid=f"{NTCIP_ESS}.4.4.0",
        name="essPrecipOneHour",
        description="1-hour precipitation total in tenths of mm",
        value_type="integer",
        access="read-only",
    )

    ESS_PRECIP_THREE_HOURS = OIDDefinition(
        oid=f"{NTCIP_ESS}.4.5.0",
        name="essPrecipThreeHours",
        description="3-hour precipitation total in tenths of mm",
        value_type="integer",
        access="read-only",
    )

    ESS_PRECIP_SIX_HOURS = OIDDefinition(
        oid=f"{NTCIP_ESS}.4.6.0",
        name="essPrecipSixHours",
        description="6-hour precipitation total in tenths of mm",
        value_type="integer",
        access="read-only",
    )

    ESS_PRECIP_TWELVE_HOURS = OIDDefinition(
        oid=f"{NTCIP_ESS}.4.7.0",
        name="essPrecipTwelveHours",
        description="12-hour precipitation total in tenths of mm",
        value_type="integer",
        access="read-only",
    )

    ESS_PRECIP_24_HOURS = OIDDefinition(
        oid=f"{NTCIP_ESS}.4.8.0",
        name="essPrecip24Hours",
        description="24-hour precipitation total in tenths of mm",
        value_type="integer",
        access="read-only",
    )

    ALL = [
        ESS_PRECIP_YES_NO,
        ESS_PRECIP_RATE,
        ESS_PRECIP_SITUATION,
        ESS_PRECIP_ONE_HOUR,
        ESS_PRECIP_THREE_HOURS,
        ESS_PRECIP_SIX_HOURS,
        ESS_PRECIP_TWELVE_HOURS,
        ESS_PRECIP_24_HOURS,
    ]


# Default OID lists for polling
NTCIP_1204_ATMOSPHERE_OIDS = [oid_def.oid for oid_def in AtmosphereOIDs.ALL]
NTCIP_1204_WIND_OIDS = [oid_def.oid for oid_def in WindOIDs.ALL]
NTCIP_1204_PAVEMENT_OIDS = [oid_def.oid for oid_def in PavementOIDs.ALL]


@dataclass
class ESSDeviceConfig:
    """Configuration for an Environmental Sensor Station device."""

    has_atmosphere_sensor: bool = True
    has_wind_sensor: bool = True
    has_pavement_sensor: bool = False
    has_precipitation_sensor: bool = True
    has_visibility_sensor: bool = False
    has_water_level_sensor: bool = False
    sensor_height_m: float = 10.0
    ntcip_version: str = "1204v03"
    custom_oids: list[str] = field(default_factory=list)


def get_ess_poll_oids(config: ESSDeviceConfig | None = None) -> list[str]:
    """Get recommended poll OIDs for an environmental sensor station.

    Args:
        config: Optional device configuration

    Returns:
        List of OIDs to poll
    """
    oids = []

    # Atmospheric sensors (most common)
    if config is None or config.has_atmosphere_sensor:
        oids.extend([
            AtmosphereOIDs.ESS_AIR_TEMPERATURE.oid,
            AtmosphereOIDs.ESS_HUMIDITY.oid,
            AtmosphereOIDs.ESS_DEW_POINT.oid,
        ])

    # Wind sensors
    if config is None or config.has_wind_sensor:
        oids.extend([
            WindOIDs.ESS_AVG_WIND_SPEED.oid,
            WindOIDs.ESS_AVG_WIND_DIRECTION.oid,
            WindOIDs.ESS_GUST_WIND_SPEED.oid,
        ])

    # Pavement sensors
    if config and config.has_pavement_sensor:
        oids.extend([
            PavementOIDs.ESS_SURFACE_TEMPERATURE.oid,
            PavementOIDs.ESS_SURFACE_STATUS.oid,
            PavementOIDs.ESS_SURFACE_WATER_DEPTH.oid,
        ])

    # Precipitation sensors
    if config is None or config.has_precipitation_sensor:
        oids.extend([
            PrecipitationOIDs.ESS_PRECIP_YES_NO.oid,
            PrecipitationOIDs.ESS_PRECIP_RATE.oid,
            PrecipitationOIDs.ESS_PRECIP_ONE_HOUR.oid,
        ])

    # Visibility sensor
    if config and config.has_visibility_sensor:
        oids.extend([
            AtmosphereOIDs.ESS_VISIBILITY.oid,
            AtmosphereOIDs.ESS_VISIBILITY_SITUATION.oid,
        ])

    # Add any custom OIDs
    if config and config.custom_oids:
        oids.extend(config.custom_oids)

    return oids
