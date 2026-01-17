"""NTCIP (National Transportation Communications for ITS Protocol) module.

Provides OID definitions and utilities for NTCIP-compliant devices:
- NTCIP 1202: Actuated Traffic Signal Controllers (ASC)
- NTCIP 1203: Dynamic Message Signs (DMS)
- NTCIP 1204: Environmental Sensor Stations (ESS)
"""

from app.protocol_engines.snmp.ntcip.ntcip_1202 import (
    NTCIP_1202_DETECTOR_OIDS,
    NTCIP_1202_PHASE_OIDS,
    NTCIP_1202_TIMING_OIDS,
    ASCDeviceConfig,
    DetectorOIDs,
    PhaseOIDs,
    TimingOIDs,
    get_asc_poll_oids,
)
from app.protocol_engines.snmp.ntcip.ntcip_1203 import (
    NTCIP_1203_MESSAGE_OIDS,
    NTCIP_1203_STATUS_OIDS,
    DMSDeviceConfig,
    MessageOIDs,
    StatusOIDs,
    get_dms_poll_oids,
)
from app.protocol_engines.snmp.ntcip.ntcip_1204 import (
    NTCIP_1204_ATMOSPHERE_OIDS,
    NTCIP_1204_PAVEMENT_OIDS,
    NTCIP_1204_WIND_OIDS,
    AtmosphereOIDs,
    ESSDeviceConfig,
    PavementOIDs,
    WindOIDs,
    get_ess_poll_oids,
)

__all__ = [
    # NTCIP 1202 - Traffic Signal Controllers
    "PhaseOIDs",
    "DetectorOIDs",
    "TimingOIDs",
    "ASCDeviceConfig",
    "get_asc_poll_oids",
    "NTCIP_1202_PHASE_OIDS",
    "NTCIP_1202_DETECTOR_OIDS",
    "NTCIP_1202_TIMING_OIDS",
    # NTCIP 1203 - Dynamic Message Signs
    "MessageOIDs",
    "StatusOIDs",
    "DMSDeviceConfig",
    "get_dms_poll_oids",
    "NTCIP_1203_MESSAGE_OIDS",
    "NTCIP_1203_STATUS_OIDS",
    # NTCIP 1204 - Environmental Sensors
    "AtmosphereOIDs",
    "WindOIDs",
    "PavementOIDs",
    "ESSDeviceConfig",
    "get_ess_poll_oids",
    "NTCIP_1204_ATMOSPHERE_OIDS",
    "NTCIP_1204_WIND_OIDS",
    "NTCIP_1204_PAVEMENT_OIDS",
]
