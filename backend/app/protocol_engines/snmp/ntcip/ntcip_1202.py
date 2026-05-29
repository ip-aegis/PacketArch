# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""NTCIP 1202 - Actuated Traffic Signal Controller (ASC) OIDs.

Defines OIDs for traffic signal controller polling including:
- Phase status (red/yellow/green indicators)
- Detector status and volume counts
- Timing plan and coordination
- Preemption and priority
"""

from dataclasses import dataclass, field

from app.protocol_engines.snmp.oids import NTCIP_ASC, OIDDefinition


class PhaseOIDs:
    """NTCIP 1202 Phase Status OIDs (1.3.6.1.4.1.1206.4.2.2.1)."""

    # Phase Status Group
    PHASE_STATUS_GROUP_REDS = OIDDefinition(
        oid=f"{NTCIP_ASC}.1.4.1.0",
        name="phaseStatusGroupReds",
        description="Bitmask of phases currently displaying red",
        value_type="integer",
        access="read-only",
    )

    PHASE_STATUS_GROUP_YELLOWS = OIDDefinition(
        oid=f"{NTCIP_ASC}.1.4.2.0",
        name="phaseStatusGroupYellows",
        description="Bitmask of phases currently displaying yellow",
        value_type="integer",
        access="read-only",
    )

    PHASE_STATUS_GROUP_GREENS = OIDDefinition(
        oid=f"{NTCIP_ASC}.1.4.3.0",
        name="phaseStatusGroupGreens",
        description="Bitmask of phases currently displaying green",
        value_type="integer",
        access="read-only",
    )

    PHASE_STATUS_GROUP_DONT_WALKS = OIDDefinition(
        oid=f"{NTCIP_ASC}.1.4.4.0",
        name="phaseStatusGroupDontWalks",
        description="Bitmask of phases displaying pedestrian don't walk",
        value_type="integer",
        access="read-only",
    )

    PHASE_STATUS_GROUP_PED_CLEARS = OIDDefinition(
        oid=f"{NTCIP_ASC}.1.4.5.0",
        name="phaseStatusGroupPedClears",
        description="Bitmask of phases in pedestrian clearance",
        value_type="integer",
        access="read-only",
    )

    PHASE_STATUS_GROUP_WALKS = OIDDefinition(
        oid=f"{NTCIP_ASC}.1.4.6.0",
        name="phaseStatusGroupWalks",
        description="Bitmask of phases displaying walk signal",
        value_type="integer",
        access="read-only",
    )

    PHASE_STATUS_GROUP_VEH_CALLS = OIDDefinition(
        oid=f"{NTCIP_ASC}.1.4.7.0",
        name="phaseStatusGroupVehCalls",
        description="Bitmask of phases with active vehicle calls",
        value_type="integer",
        access="read-only",
    )

    PHASE_STATUS_GROUP_PED_CALLS = OIDDefinition(
        oid=f"{NTCIP_ASC}.1.4.8.0",
        name="phaseStatusGroupPedCalls",
        description="Bitmask of phases with active pedestrian calls",
        value_type="integer",
        access="read-only",
    )

    ALL = [
        PHASE_STATUS_GROUP_REDS,
        PHASE_STATUS_GROUP_YELLOWS,
        PHASE_STATUS_GROUP_GREENS,
        PHASE_STATUS_GROUP_DONT_WALKS,
        PHASE_STATUS_GROUP_PED_CLEARS,
        PHASE_STATUS_GROUP_WALKS,
        PHASE_STATUS_GROUP_VEH_CALLS,
        PHASE_STATUS_GROUP_PED_CALLS,
    ]


class DetectorOIDs:
    """NTCIP 1202 Detector OIDs (1.3.6.1.4.1.1206.4.2.2.2)."""

    # Detector Status
    MAX_VEHICLE_DETECTORS = OIDDefinition(
        oid=f"{NTCIP_ASC}.2.1.0",
        name="maxVehicleDetectors",
        description="Maximum number of vehicle detectors supported",
        value_type="integer",
        access="read-only",
        default_value=64,
    )

    VEHICLE_DETECTOR_STATUS_GROUP_ACTIVE = OIDDefinition(
        oid=f"{NTCIP_ASC}.2.8.1.0",
        name="vehicleDetectorStatusGroupActive",
        description="Bitmask of detectors currently active (vehicle present)",
        value_type="integer",
        access="read-only",
    )

    # Detector Volume (indexed by detector number)
    VEHICLE_DETECTOR_VOLUME = f"{NTCIP_ASC}.2.5.1.5"  # .{detector_num}

    # Detector Occupancy
    VEHICLE_DETECTOR_OCCUPANCY = f"{NTCIP_ASC}.2.5.1.6"  # .{detector_num}

    ALL = [
        MAX_VEHICLE_DETECTORS,
        VEHICLE_DETECTOR_STATUS_GROUP_ACTIVE,
    ]


class TimingOIDs:
    """NTCIP 1202 Timing and Coordination OIDs (1.3.6.1.4.1.1206.4.2.2.3)."""

    CURRENT_TIMING_PLAN = OIDDefinition(
        oid=f"{NTCIP_ASC}.3.1.0",
        name="currentTimingPlan",
        description="Currently active timing plan number (1-255)",
        value_type="integer",
        access="read-only",
    )

    CURRENT_ACTION_PLAN = OIDDefinition(
        oid=f"{NTCIP_ASC}.3.2.0",
        name="currentActionPlan",
        description="Currently active action plan",
        value_type="integer",
        access="read-only",
    )

    LOCAL_CYCLE_COUNTER = OIDDefinition(
        oid=f"{NTCIP_ASC}.3.3.0",
        name="localCycleCounter",
        description="Local cycle counter (0-255, wraps)",
        value_type="integer",
        access="read-only",
    )

    COORD_CYCLE_STATUS = OIDDefinition(
        oid=f"{NTCIP_ASC}.3.4.0",
        name="coordCycleStatus",
        description="Coordination cycle status",
        value_type="integer",
        access="read-only",
    )

    COORD_SYNC_STATUS = OIDDefinition(
        oid=f"{NTCIP_ASC}.3.5.0",
        name="coordSyncStatus",
        description="Coordination sync status (1=free, 2=in-step, 3=transition)",
        value_type="integer",
        access="read-only",
    )

    SYSTEM_PATTERN = OIDDefinition(
        oid=f"{NTCIP_ASC}.3.6.0",
        name="systemPattern",
        description="System pattern command from master",
        value_type="integer",
        access="read-write",
    )

    ALL = [
        CURRENT_TIMING_PLAN,
        CURRENT_ACTION_PLAN,
        LOCAL_CYCLE_COUNTER,
        COORD_CYCLE_STATUS,
        COORD_SYNC_STATUS,
        SYSTEM_PATTERN,
    ]


# Default OID lists for polling
NTCIP_1202_PHASE_OIDS = [oid_def.oid for oid_def in PhaseOIDs.ALL]
NTCIP_1202_DETECTOR_OIDS = [oid_def.oid for oid_def in DetectorOIDs.ALL]
NTCIP_1202_TIMING_OIDS = [oid_def.oid for oid_def in TimingOIDs.ALL]


@dataclass
class ASCDeviceConfig:
    """Configuration for an Actuated Signal Controller device."""

    max_phases: int = 8
    max_detectors: int = 64
    max_timing_plans: int = 16
    supports_coordination: bool = True
    supports_preemption: bool = True
    ntcip_version: str = "1202v03"
    custom_oids: list[str] = field(default_factory=list)


def get_asc_poll_oids(config: ASCDeviceConfig | None = None) -> list[str]:
    """Get recommended poll OIDs for a traffic signal controller.

    Args:
        config: Optional device configuration

    Returns:
        List of OIDs to poll
    """
    # Essential phase status OIDs
    oids = [
        PhaseOIDs.PHASE_STATUS_GROUP_REDS.oid,
        PhaseOIDs.PHASE_STATUS_GROUP_YELLOWS.oid,
        PhaseOIDs.PHASE_STATUS_GROUP_GREENS.oid,
        PhaseOIDs.PHASE_STATUS_GROUP_VEH_CALLS.oid,
    ]

    # Timing OIDs
    oids.extend([
        TimingOIDs.CURRENT_TIMING_PLAN.oid,
        TimingOIDs.LOCAL_CYCLE_COUNTER.oid,
    ])

    # Detector status if configured
    if config and config.max_detectors > 0:
        oids.append(DetectorOIDs.VEHICLE_DETECTOR_STATUS_GROUP_ACTIVE.oid)

    # Coordination status if supported
    if config and config.supports_coordination:
        oids.extend([
            TimingOIDs.COORD_CYCLE_STATUS.oid,
            TimingOIDs.COORD_SYNC_STATUS.oid,
        ])

    # Add any custom OIDs
    if config and config.custom_oids:
        oids.extend(config.custom_oids)

    return oids
