# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTCIP 1203 - Dynamic Message Sign (DMS) OIDs.

Defines OIDs for dynamic message sign polling including:
- Sign configuration and capabilities
- Current message display
- Sign status and health
- Illumination and environmental
"""

from dataclasses import dataclass, field
from typing import Any

from app.protocol_engines.snmp.oids import NTCIP_DMS, OIDDefinition


class MessageOIDs:
    """NTCIP 1203 Message Display OIDs (1.3.6.1.4.1.1206.4.2.3.5)."""

    DMS_MESSAGE_STATUS = OIDDefinition(
        oid=f"{NTCIP_DMS}.5.1.0",
        name="dmsMessageStatus",
        description="Current message display status (1=off, 2=displayed, 3=activating)",
        value_type="integer",
        access="read-only",
    )

    DMS_MESSAGE_SOURCE_MODE = OIDDefinition(
        oid=f"{NTCIP_DMS}.5.2.0",
        name="dmsMessageSourceMode",
        description="Source of current message (1=other, 2=local, 3=central, 4=schedule)",
        value_type="integer",
        access="read-only",
    )

    DMS_MESSAGE_MULTI_STRING = OIDDefinition(
        oid=f"{NTCIP_DMS}.5.3.0",
        name="dmsMessageMultiString",
        description="Current message in MULTI markup format",
        value_type="string",
        access="read-only",
    )

    DMS_MESSAGE_OWNER = OIDDefinition(
        oid=f"{NTCIP_DMS}.5.4.0",
        name="dmsMessageOwner",
        description="Owner/source identifier of current message",
        value_type="string",
        access="read-only",
    )

    DMS_MESSAGE_CRC = OIDDefinition(
        oid=f"{NTCIP_DMS}.5.5.0",
        name="dmsMessageCRC",
        description="CRC of current message for verification",
        value_type="integer",
        access="read-only",
    )

    DMS_MESSAGE_BEACON = OIDDefinition(
        oid=f"{NTCIP_DMS}.5.6.0",
        name="dmsMessageBeacon",
        description="Beacon activation status (1=off, 2=flashing)",
        value_type="integer",
        access="read-only",
    )

    DMS_MESSAGE_PRIORITY = OIDDefinition(
        oid=f"{NTCIP_DMS}.5.7.0",
        name="dmsMessagePriority",
        description="Priority level of current message (1-255)",
        value_type="integer",
        access="read-only",
    )

    ALL = [
        DMS_MESSAGE_STATUS,
        DMS_MESSAGE_SOURCE_MODE,
        DMS_MESSAGE_MULTI_STRING,
        DMS_MESSAGE_OWNER,
        DMS_MESSAGE_CRC,
        DMS_MESSAGE_BEACON,
        DMS_MESSAGE_PRIORITY,
    ]


class StatusOIDs:
    """NTCIP 1203 Sign Status OIDs (1.3.6.1.4.1.1206.4.2.3.9)."""

    DMS_CONTROL_MODE = OIDDefinition(
        oid=f"{NTCIP_DMS}.9.1.0",
        name="dmsControlMode",
        description="Current control mode (1=other, 2=local, 3=central, 4=schedule)",
        value_type="integer",
        access="read-write",
    )

    DMS_LAMP_STATUS = OIDDefinition(
        oid=f"{NTCIP_DMS}.9.3.0",
        name="dmsLampStatus",
        description="Overall lamp/pixel status (1=noError, 2=error, 3=critical)",
        value_type="integer",
        access="read-only",
    )

    DMS_LAMP_TEST_ACTIVATION = OIDDefinition(
        oid=f"{NTCIP_DMS}.9.4.0",
        name="dmsLampTestActivation",
        description="Lamp test status (1=off, 2=allOn, 3=allOff)",
        value_type="integer",
        access="read-write",
    )

    DMS_AMBIENT_TEMPERATURE = OIDDefinition(
        oid=f"{NTCIP_DMS}.9.6.0",
        name="dmsAmbientTemperature",
        description="Internal cabinet temperature in Celsius",
        value_type="integer",
        access="read-only",
    )

    DMS_HOUSING_TEMPERATURE = OIDDefinition(
        oid=f"{NTCIP_DMS}.9.7.0",
        name="dmsHousingTemperature",
        description="Sign housing temperature in Celsius",
        value_type="integer",
        access="read-only",
    )

    DMS_POWER_STATUS = OIDDefinition(
        oid=f"{NTCIP_DMS}.9.8.0",
        name="dmsPowerStatus",
        description="Power supply status (1=ok, 2=fail)",
        value_type="integer",
        access="read-only",
    )

    DMS_COMM_STATUS = OIDDefinition(
        oid=f"{NTCIP_DMS}.9.9.0",
        name="dmsCommStatus",
        description="Communication module status",
        value_type="integer",
        access="read-only",
    )

    ALL = [
        DMS_CONTROL_MODE,
        DMS_LAMP_STATUS,
        DMS_LAMP_TEST_ACTIVATION,
        DMS_AMBIENT_TEMPERATURE,
        DMS_HOUSING_TEMPERATURE,
        DMS_POWER_STATUS,
        DMS_COMM_STATUS,
    ]


class IlluminationOIDs:
    """NTCIP 1203 Illumination OIDs (1.3.6.1.4.1.1206.4.2.3.7)."""

    DMS_ILLUM_CONTROL = OIDDefinition(
        oid=f"{NTCIP_DMS}.7.1.0",
        name="dmsIllumControl",
        description="Illumination control mode (1=other, 2=photocell, 3=timer, 4=manual)",
        value_type="integer",
        access="read-write",
    )

    DMS_ILLUM_BRIGHT_LEVEL_STATUS = OIDDefinition(
        oid=f"{NTCIP_DMS}.7.2.0",
        name="dmsIllumBrightLevelStatus",
        description="Current brightness level (0-255)",
        value_type="integer",
        access="read-only",
    )

    DMS_ILLUM_LIGHT_SENSOR = OIDDefinition(
        oid=f"{NTCIP_DMS}.7.3.0",
        name="dmsIllumLightSensor",
        description="Ambient light sensor reading",
        value_type="integer",
        access="read-only",
    )

    ALL = [
        DMS_ILLUM_CONTROL,
        DMS_ILLUM_BRIGHT_LEVEL_STATUS,
        DMS_ILLUM_LIGHT_SENSOR,
    ]


# Default OID lists for polling
NTCIP_1203_MESSAGE_OIDS = [oid_def.oid for oid_def in MessageOIDs.ALL]
NTCIP_1203_STATUS_OIDS = [oid_def.oid for oid_def in StatusOIDs.ALL]


@dataclass
class DMSDeviceConfig:
    """Configuration for a Dynamic Message Sign device."""

    sign_height_pixels: int = 32
    sign_width_pixels: int = 128
    character_height: int = 18
    supports_multi: bool = True
    supports_graphics: bool = False
    max_messages: int = 50
    supports_beacon: bool = True
    ntcip_version: str = "1203v03"
    custom_oids: list[str] = field(default_factory=list)


def get_dms_poll_oids(config: DMSDeviceConfig | None = None) -> list[str]:
    """Get recommended poll OIDs for a dynamic message sign.

    Args:
        config: Optional device configuration

    Returns:
        List of OIDs to poll
    """
    # Essential message OIDs
    oids = [
        MessageOIDs.DMS_MESSAGE_STATUS.oid,
        MessageOIDs.DMS_MESSAGE_MULTI_STRING.oid,
        MessageOIDs.DMS_MESSAGE_SOURCE_MODE.oid,
    ]

    # Status OIDs
    oids.extend([
        StatusOIDs.DMS_LAMP_STATUS.oid,
        StatusOIDs.DMS_AMBIENT_TEMPERATURE.oid,
        StatusOIDs.DMS_POWER_STATUS.oid,
    ])

    # Illumination
    oids.append(IlluminationOIDs.DMS_ILLUM_BRIGHT_LEVEL_STATUS.oid)

    # Beacon status if supported
    if config and config.supports_beacon:
        oids.append(MessageOIDs.DMS_MESSAGE_BEACON.oid)

    # Add any custom OIDs
    if config and config.custom_oids:
        oids.extend(config.custom_oids)

    return oids
