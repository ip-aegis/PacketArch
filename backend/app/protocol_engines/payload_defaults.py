"""Factory for creating default PayloadGenerator instances per flow.

Auto-selects sensor profiles based on protocol type and industry vertical,
so that protocol engines produce realistic evolving values instead of
zeros or random bytes.
"""

from __future__ import annotations

from typing import Any

from app.protocol_engines.payload_generator import (
    DataType,
    PayloadGenerator,
    SensorProfile,
    TrendType,
    get_profiles_for_vertical,
    MANUFACTURING_PROFILES,
)
from app.protocol_engines.types import ProtocolType


# Generic fallback profiles when no vertical-specific ones are available.
# Covers common OT sensor archetypes with varied trend types.
_GENERIC_PROFILES: list[SensorProfile] = [
    SensorProfile(
        name="_temperature", data_type=DataType.FLOAT32,
        min_value=15.0, max_value=85.0, nominal_value=45.0,
        trend_type=TrendType.SINUSOIDAL, trend_period=3600.0, noise_std=0.5,
    ),
    SensorProfile(
        name="_pressure", data_type=DataType.FLOAT32,
        min_value=0.0, max_value=10.0, nominal_value=5.0,
        trend_type=TrendType.STABLE, noise_std=0.1,
    ),
    SensorProfile(
        name="_flow_rate", data_type=DataType.FLOAT32,
        min_value=0.0, max_value=1000.0, nominal_value=500.0,
        trend_type=TrendType.RANDOM_WALK, drift_rate=5.0, noise_std=10.0,
    ),
    SensorProfile(
        name="_level", data_type=DataType.FLOAT32,
        min_value=0.0, max_value=100.0, nominal_value=50.0,
        trend_type=TrendType.RANDOM_WALK, drift_rate=0.5, noise_std=1.0,
    ),
    SensorProfile(
        name="_speed", data_type=DataType.FLOAT32,
        min_value=0.0, max_value=3000.0, nominal_value=1500.0,
        trend_type=TrendType.STABLE, noise_std=5.0,
    ),
]


def _select_base_profiles(vertical: str | None) -> list[SensorProfile]:
    """Select base sensor profiles for the given industry vertical."""
    if vertical:
        profiles = get_profiles_for_vertical(vertical)
        if profiles:
            return profiles
    # Fall back to manufacturing if vertical unrecognised, then generic
    profiles = MANUFACTURING_PROFILES
    return profiles if profiles else _GENERIC_PROFILES


def _clone_as(
    base: SensorProfile,
    name: str,
    data_type: DataType,
) -> SensorProfile:
    """Clone a base profile with a new name and data type.

    Scales min/max for integer types so the value fits naturally.
    """
    # For integer types, scale the float range into the integer domain
    if data_type == DataType.UINT16:
        # Map the profile's physical range into 0–65535
        scale = 65535.0 / max(base.max_value - base.min_value, 1.0)
        return SensorProfile(
            name=name,
            data_type=data_type,
            min_value=0.0,
            max_value=min(base.max_value * scale, 65535.0),
            nominal_value=min(base.nominal_value * scale, 65535.0),
            drift_rate=base.drift_rate * scale,
            noise_std=base.noise_std * scale,
            trend_type=base.trend_type,
            trend_period=base.trend_period,
            step_size=base.step_size,
            unit=base.unit,
        )
    # For FLOAT32 / FLOAT64, keep as-is
    return SensorProfile(
        name=name,
        data_type=data_type,
        min_value=base.min_value,
        max_value=base.max_value,
        nominal_value=base.nominal_value,
        drift_rate=base.drift_rate,
        noise_std=base.noise_std,
        trend_type=base.trend_type,
        trend_period=base.trend_period,
        step_size=base.step_size,
        unit=base.unit,
    )


def create_default_payload_generator(
    protocol: ProtocolType,
    config: dict[str, Any],
    vertical: str | None = None,
) -> PayloadGenerator | None:
    """Create a PayloadGenerator with auto-selected sensor profiles.

    Returns None if the protocol is not one that benefits from payload
    generation (e.g. BACnet, SNMP have their own identity-based payloads).

    Args:
        protocol: Protocol type for this flow.
        config: Flow-level protocol config dict.
        vertical: Industry vertical (e.g. "manufacturing", "water").

    Returns:
        A PayloadGenerator instance, or None if not applicable.
    """
    base_profiles = _select_base_profiles(vertical)

    if protocol in (ProtocolType.MODBUS_TCP, ProtocolType.MODBUS_RTU):
        quantity = config.get("quantity", config.get("register_count", 10))
        gen_profiles = [
            _clone_as(base_profiles[i % len(base_profiles)], f"reg_{i}", DataType.UINT16)
            for i in range(quantity)
        ]
        return PayloadGenerator(gen_profiles)

    if protocol == ProtocolType.S7COMM:
        # Calculate total bytes across all read areas
        read_areas = config.get("read_areas", [])
        if read_areas:
            total_bytes = sum(
                a.get("size", 10) if isinstance(a, dict) else getattr(a, "size", 10)
                for a in read_areas
            )
        else:
            total_bytes = 20
        num_sensors = max(1, total_bytes // 4)
        gen_profiles = [
            _clone_as(base_profiles[i % len(base_profiles)], f"s7_val_{i}", DataType.FLOAT32)
            for i in range(num_sensors)
        ]
        return PayloadGenerator(gen_profiles)

    if protocol == ProtocolType.ETHERNET_IP:
        io_size = config.get("io_data_size", 8)
        num_sensors = max(1, io_size // 2)
        gen_profiles = [
            _clone_as(base_profiles[i % len(base_profiles)], f"io_{i}", DataType.UINT16)
            for i in range(num_sensors)
        ]
        return PayloadGenerator(gen_profiles)

    return None
