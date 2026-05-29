# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Realistic payload value generator for OT traffic simulation.

This module provides classes for generating realistic, evolving sensor values
that follow industry-typical patterns including drift, noise, and trends.
"""

import math
import random
import struct
from dataclasses import dataclass
from enum import Enum


class TrendType(str, Enum):
    """Types of value trends for sensor simulation."""

    STABLE = "stable"  # Value stays around nominal with noise
    INCREASING = "increasing"  # Gradual increase over time
    DECREASING = "decreasing"  # Gradual decrease over time
    SINUSOIDAL = "sinusoidal"  # Periodic oscillation (e.g., temperature cycles)
    RANDOM_WALK = "random_walk"  # Brownian motion-like wandering
    STEP = "step"  # Discrete step changes at intervals
    RAMP = "ramp"  # Linear ramp then reset (sawtooth)


class DataType(str, Enum):
    """Data types for sensor values with their byte sizes."""

    BOOL = "bool"  # 1 bit
    INT8 = "int8"  # 1 byte signed
    UINT8 = "uint8"  # 1 byte unsigned
    INT16 = "int16"  # 2 bytes signed (common for Modbus)
    UINT16 = "uint16"  # 2 bytes unsigned (common for Modbus)
    INT32 = "int32"  # 4 bytes signed
    UINT32 = "uint32"  # 4 bytes unsigned
    FLOAT32 = "float32"  # 4 bytes IEEE 754
    FLOAT64 = "float64"  # 8 bytes IEEE 754
    INT64 = "int64"  # 8 bytes signed
    UINT64 = "uint64"  # 8 bytes unsigned


# Struct format codes for each data type (big-endian by default)
DATA_TYPE_FORMATS: dict[DataType, str] = {
    DataType.BOOL: ">?",
    DataType.INT8: ">b",
    DataType.UINT8: ">B",
    DataType.INT16: ">h",
    DataType.UINT16: ">H",
    DataType.INT32: ">i",
    DataType.UINT32: ">I",
    DataType.FLOAT32: ">f",
    DataType.FLOAT64: ">d",
    DataType.INT64: ">q",
    DataType.UINT64: ">Q",
}

# Byte sizes for each data type
DATA_TYPE_SIZES: dict[DataType, int] = {
    DataType.BOOL: 1,
    DataType.INT8: 1,
    DataType.UINT8: 1,
    DataType.INT16: 2,
    DataType.UINT16: 2,
    DataType.INT32: 4,
    DataType.UINT32: 4,
    DataType.FLOAT32: 4,
    DataType.FLOAT64: 8,
    DataType.INT64: 8,
    DataType.UINT64: 8,
}


@dataclass
class SensorProfile:
    """Defines realistic behavior for a simulated sensor value.

    Attributes:
        name: Unique identifier for this sensor
        data_type: Data type for encoding the value
        min_value: Minimum allowed value (clamped)
        max_value: Maximum allowed value (clamped)
        nominal_value: Center/typical value
        drift_rate: Rate of change per second for trending types
        noise_std: Standard deviation of Gaussian noise
        trend_type: Type of value evolution over time
        trend_period: Period in seconds for sinusoidal/step trends
        step_size: Size of discrete steps for STEP trend type
        unit: Engineering unit for display (e.g., "°C", "bar")
    """

    name: str
    data_type: DataType = DataType.FLOAT32
    min_value: float = 0.0
    max_value: float = 100.0
    nominal_value: float = 50.0
    drift_rate: float = 0.0  # units per second
    noise_std: float = 0.5  # standard deviation
    trend_type: TrendType = TrendType.STABLE
    trend_period: float | None = None  # seconds
    step_size: float | None = None  # for STEP trend
    unit: str = ""
    byte_order: str = "big"  # "big" or "little"

    def get_format_string(self) -> str:
        """Get struct format string with correct byte order."""
        fmt = DATA_TYPE_FORMATS[self.data_type]
        if self.byte_order == "little":
            fmt = "<" + fmt[1:]  # Replace > with <
        return fmt

    def get_byte_size(self) -> int:
        """Get size in bytes for this data type."""
        return DATA_TYPE_SIZES[self.data_type]


@dataclass
class SensorState:
    """Internal state for tracking sensor value evolution."""

    current_value: float
    last_update_ms: float
    random_walk_velocity: float = 0.0  # For random walk smoothing
    step_last_change_ms: float = 0.0  # For step timing


class PayloadGenerator:
    """Generates realistic, evolving payload values for OT traffic simulation.

    This class maintains state for multiple sensors and generates values that
    follow realistic industrial patterns including gradual drift, noise,
    periodic oscillations, and step changes.

    Example:
        >>> profiles = [
        ...     SensorProfile(name="temp1", min_value=15, max_value=85,
        ...                   nominal_value=45, trend_type=TrendType.SINUSOIDAL,
        ...                   trend_period=3600, noise_std=0.5),
        ...     SensorProfile(name="pressure1", min_value=0, max_value=10,
        ...                   nominal_value=5, trend_type=TrendType.STABLE,
        ...                   noise_std=0.1),
        ... ]
        >>> gen = PayloadGenerator(profiles)
        >>> value_bytes = gen.get_value("temp1", timestamp_ms=1000)
    """

    def __init__(self, profiles: list[SensorProfile] | None = None):
        """Initialize with sensor profiles.

        Args:
            profiles: List of sensor profiles to manage. Can be added later.
        """
        self.profiles: dict[str, SensorProfile] = {}
        self.states: dict[str, SensorState] = {}

        if profiles:
            for profile in profiles:
                self.add_profile(profile)

    def add_profile(self, profile: SensorProfile) -> None:
        """Add a sensor profile.

        Args:
            profile: Sensor profile to add
        """
        self.profiles[profile.name] = profile
        # Initialize state with nominal value
        self.states[profile.name] = SensorState(
            current_value=profile.nominal_value,
            last_update_ms=0.0,
        )

    def get_value(
        self, sensor_name: str, timestamp_ms: float, as_float: bool = False
    ) -> bytes | float:
        """Get the next value for a sensor at the given timestamp.

        Args:
            sensor_name: Name of the sensor profile
            timestamp_ms: Current simulation timestamp in milliseconds
            as_float: If True, return float instead of bytes

        Returns:
            Encoded bytes for the value, or float if as_float=True

        Raises:
            KeyError: If sensor_name not found in profiles
        """
        if sensor_name not in self.profiles:
            raise KeyError(f"Unknown sensor: {sensor_name}")

        profile = self.profiles[sensor_name]
        state = self.states[sensor_name]

        # Calculate elapsed time
        elapsed_s = (timestamp_ms - state.last_update_ms) / 1000.0
        if elapsed_s < 0:
            # Handle time reset/wrap
            elapsed_s = 0.0

        # Apply trend
        base_value = self._apply_trend(profile, state, timestamp_ms, elapsed_s)

        # Apply noise
        noise = random.gauss(0, profile.noise_std) if profile.noise_std > 0 else 0.0
        value = base_value + noise

        # Clamp to bounds
        value = max(profile.min_value, min(profile.max_value, value))

        # Update state
        state.current_value = value
        state.last_update_ms = timestamp_ms

        if as_float:
            return value

        # Encode to bytes
        return self._encode_value(value, profile)

    def get_multiple_values(
        self, sensor_names: list[str], timestamp_ms: float
    ) -> bytes:
        """Get values for multiple sensors concatenated as bytes.

        Args:
            sensor_names: List of sensor names in order
            timestamp_ms: Current simulation timestamp

        Returns:
            Concatenated bytes for all sensor values
        """
        result = b""
        for name in sensor_names:
            result += self.get_value(name, timestamp_ms)
        return result

    def reset_sensor(self, sensor_name: str) -> None:
        """Reset a sensor to its nominal value.

        Args:
            sensor_name: Name of the sensor to reset
        """
        if sensor_name in self.profiles:
            profile = self.profiles[sensor_name]
            self.states[sensor_name] = SensorState(
                current_value=profile.nominal_value,
                last_update_ms=0.0,
            )

    def reset_all(self) -> None:
        """Reset all sensors to their nominal values."""
        for name in self.profiles:
            self.reset_sensor(name)

    def _apply_trend(
        self,
        profile: SensorProfile,
        state: SensorState,
        timestamp_ms: float,
        elapsed_s: float,
    ) -> float:
        """Apply trend behavior to calculate base value before noise.

        Args:
            profile: Sensor profile
            state: Current sensor state
            timestamp_ms: Current timestamp
            elapsed_s: Elapsed time in seconds

        Returns:
            Base value after applying trend
        """
        if profile.trend_type == TrendType.STABLE:
            # Stay around nominal value
            return profile.nominal_value

        elif profile.trend_type == TrendType.INCREASING:
            # Linear increase from current value
            new_value = state.current_value + profile.drift_rate * elapsed_s
            # Reset if we hit max
            if new_value >= profile.max_value:
                return profile.nominal_value
            return new_value

        elif profile.trend_type == TrendType.DECREASING:
            # Linear decrease from current value
            new_value = state.current_value - profile.drift_rate * elapsed_s
            # Reset if we hit min
            if new_value <= profile.min_value:
                return profile.nominal_value
            return new_value

        elif profile.trend_type == TrendType.SINUSOIDAL:
            # Periodic oscillation around nominal
            period = profile.trend_period or 3600.0  # Default 1 hour
            amplitude = (profile.max_value - profile.min_value) / 4.0
            phase = (timestamp_ms / 1000.0) * (2 * math.pi / period)
            return profile.nominal_value + amplitude * math.sin(phase)

        elif profile.trend_type == TrendType.RANDOM_WALK:
            # Brownian motion with drift and momentum
            # Update velocity with some persistence
            momentum = 0.9  # How much velocity persists
            new_velocity_component = random.gauss(0, profile.drift_rate)
            state.random_walk_velocity = (
                momentum * state.random_walk_velocity + (1 - momentum) * new_velocity_component
            )
            new_value = state.current_value + state.random_walk_velocity * elapsed_s
            # Soft bounce off boundaries
            if new_value < profile.min_value:
                new_value = profile.min_value + abs(new_value - profile.min_value)
                state.random_walk_velocity = abs(state.random_walk_velocity)
            elif new_value > profile.max_value:
                new_value = profile.max_value - abs(new_value - profile.max_value)
                state.random_walk_velocity = -abs(state.random_walk_velocity)
            return new_value

        elif profile.trend_type == TrendType.STEP:
            # Discrete step changes at intervals
            period = profile.trend_period or 60.0  # Default 1 minute
            step_size = profile.step_size or (profile.max_value - profile.min_value) / 10.0

            if timestamp_ms - state.step_last_change_ms >= period * 1000:
                state.step_last_change_ms = timestamp_ms
                # Random step up or down
                direction = random.choice([-1, 1])
                new_value = state.current_value + direction * step_size
                return max(profile.min_value, min(profile.max_value, new_value))
            return state.current_value

        elif profile.trend_type == TrendType.RAMP:
            # Linear ramp then reset (sawtooth pattern)
            period = profile.trend_period or 60.0
            progress = ((timestamp_ms / 1000.0) % period) / period
            value_range = profile.max_value - profile.min_value
            return profile.min_value + progress * value_range

        else:
            return profile.nominal_value

    def _encode_value(self, value: float, profile: SensorProfile) -> bytes:
        """Encode a float value to bytes using the profile's data type.

        Args:
            value: Float value to encode
            profile: Sensor profile with data type info

        Returns:
            Encoded bytes
        """
        fmt = profile.get_format_string()

        # Convert float to appropriate integer type if needed
        if profile.data_type == DataType.BOOL:
            int_value = bool(value >= 0.5)
        elif profile.data_type in (
            DataType.INT8, DataType.UINT8, DataType.INT16, DataType.UINT16,
            DataType.INT32, DataType.UINT32, DataType.INT64, DataType.UINT64,
        ):
            int_value = int(round(value))
        else:
            # Float types
            int_value = value

        return struct.pack(fmt, int_value)


# =============================================================================
# Predefined Industry Sensor Profiles
# =============================================================================

# Temperature sensors
TEMPERATURE_SENSOR = SensorProfile(
    name="temperature",
    data_type=DataType.FLOAT32,
    min_value=15.0,
    max_value=85.0,
    nominal_value=45.0,
    drift_rate=0.01,
    noise_std=0.5,
    trend_type=TrendType.SINUSOIDAL,
    trend_period=86400.0,  # 24 hours
    unit="°C",
)

TEMPERATURE_SENSOR_INT16 = SensorProfile(
    name="temperature_int16",
    data_type=DataType.INT16,
    min_value=150,  # 15.0°C * 10
    max_value=850,  # 85.0°C * 10
    nominal_value=450,
    drift_rate=0.1,
    noise_std=5.0,
    trend_type=TrendType.SINUSOIDAL,
    trend_period=86400.0,
    unit="0.1°C",
)

# Pressure sensors
PRESSURE_SENSOR = SensorProfile(
    name="pressure",
    data_type=DataType.FLOAT32,
    min_value=0.0,
    max_value=10.0,
    nominal_value=5.0,
    drift_rate=0.001,
    noise_std=0.1,
    trend_type=TrendType.STABLE,
    unit="bar",
)

PRESSURE_SENSOR_UINT16 = SensorProfile(
    name="pressure_uint16",
    data_type=DataType.UINT16,
    min_value=0,
    max_value=10000,  # 0-10 bar * 1000
    nominal_value=5000,
    drift_rate=1.0,
    noise_std=100.0,
    trend_type=TrendType.STABLE,
    unit="mbar",
)

# Flow rate sensors
FLOW_RATE_SENSOR = SensorProfile(
    name="flow_rate",
    data_type=DataType.FLOAT32,
    min_value=0.0,
    max_value=1000.0,
    nominal_value=500.0,
    drift_rate=5.0,
    noise_std=10.0,
    trend_type=TrendType.RANDOM_WALK,
    unit="L/min",
)

FLOW_RATE_SENSOR_UINT16 = SensorProfile(
    name="flow_rate_uint16",
    data_type=DataType.UINT16,
    min_value=0,
    max_value=10000,  # 0-1000 L/min * 10
    nominal_value=5000,
    drift_rate=50.0,
    noise_std=100.0,
    trend_type=TrendType.RANDOM_WALK,
    unit="0.1 L/min",
)

# Level sensors (tanks)
LEVEL_SENSOR = SensorProfile(
    name="level",
    data_type=DataType.FLOAT32,
    min_value=0.0,
    max_value=100.0,
    nominal_value=50.0,
    drift_rate=0.5,
    noise_std=1.0,
    trend_type=TrendType.RANDOM_WALK,
    unit="%",
)

LEVEL_SENSOR_UINT16 = SensorProfile(
    name="level_uint16",
    data_type=DataType.UINT16,
    min_value=0,
    max_value=10000,  # 0-100% * 100
    nominal_value=5000,
    drift_rate=50.0,
    noise_std=100.0,
    trend_type=TrendType.RANDOM_WALK,
    unit="0.01%",
)

# Speed sensors (motor drives)
SPEED_SENSOR = SensorProfile(
    name="speed",
    data_type=DataType.FLOAT32,
    min_value=0.0,
    max_value=3000.0,
    nominal_value=1500.0,
    drift_rate=1.0,
    noise_std=10.0,
    trend_type=TrendType.STABLE,
    unit="RPM",
)

SPEED_SENSOR_UINT16 = SensorProfile(
    name="speed_uint16",
    data_type=DataType.UINT16,
    min_value=0,
    max_value=30000,  # 0-3000 RPM * 10
    nominal_value=15000,
    drift_rate=10.0,
    noise_std=100.0,
    trend_type=TrendType.STABLE,
    unit="0.1 RPM",
)

# Position sensors (actuators, linear encoders)
POSITION_SENSOR = SensorProfile(
    name="position",
    data_type=DataType.FLOAT32,
    min_value=0.0,
    max_value=1000.0,
    nominal_value=500.0,
    drift_rate=10.0,
    noise_std=0.1,
    trend_type=TrendType.SINUSOIDAL,
    trend_period=60.0,  # 1 minute cycle
    unit="mm",
)

POSITION_SENSOR_INT32 = SensorProfile(
    name="position_int32",
    data_type=DataType.INT32,
    min_value=0,
    max_value=1000000,  # 0-1000mm * 1000
    nominal_value=500000,
    drift_rate=10000.0,
    noise_std=100.0,
    trend_type=TrendType.SINUSOIDAL,
    trend_period=60.0,
    unit="µm",
)

# Analog input (generic 0-10V)
ANALOG_INPUT = SensorProfile(
    name="analog_input",
    data_type=DataType.FLOAT32,
    min_value=0.0,
    max_value=10.0,
    nominal_value=5.0,
    drift_rate=0.01,
    noise_std=0.05,
    trend_type=TrendType.STABLE,
    unit="V",
)

ANALOG_INPUT_UINT16 = SensorProfile(
    name="analog_input_uint16",
    data_type=DataType.UINT16,
    min_value=0,
    max_value=32767,  # 0-10V mapped to 0-32767 (15-bit ADC)
    nominal_value=16383,
    drift_rate=10.0,
    noise_std=50.0,
    trend_type=TrendType.STABLE,
    unit="counts",
)

# Current sensor (motor current)
CURRENT_SENSOR = SensorProfile(
    name="current",
    data_type=DataType.FLOAT32,
    min_value=0.0,
    max_value=100.0,
    nominal_value=25.0,
    drift_rate=0.5,
    noise_std=0.5,
    trend_type=TrendType.STABLE,
    unit="A",
)

# Voltage sensor
VOLTAGE_SENSOR = SensorProfile(
    name="voltage",
    data_type=DataType.FLOAT32,
    min_value=380.0,
    max_value=420.0,
    nominal_value=400.0,
    drift_rate=0.1,
    noise_std=1.0,
    trend_type=TrendType.STABLE,
    unit="V",
)

# Power sensor
POWER_SENSOR = SensorProfile(
    name="power",
    data_type=DataType.FLOAT32,
    min_value=0.0,
    max_value=100000.0,  # 100 kW
    nominal_value=50000.0,
    drift_rate=100.0,
    noise_std=500.0,
    trend_type=TrendType.SINUSOIDAL,
    trend_period=3600.0,  # 1 hour cycle
    unit="W",
)

# Counter (pulse counter, parts counter)
COUNTER_SENSOR = SensorProfile(
    name="counter",
    data_type=DataType.UINT32,
    min_value=0,
    max_value=4294967295,
    nominal_value=0,
    drift_rate=10.0,  # 10 counts per second
    noise_std=0.0,  # Counters are deterministic
    trend_type=TrendType.INCREASING,
    unit="counts",
)

# Binary status (on/off, running/stopped)
BINARY_STATUS = SensorProfile(
    name="binary_status",
    data_type=DataType.BOOL,
    min_value=0,
    max_value=1,
    nominal_value=1,
    drift_rate=0,
    noise_std=0,
    trend_type=TrendType.STABLE,
    unit="",
)


# =============================================================================
# Profile Collections by Industry Vertical
# =============================================================================

MANUFACTURING_PROFILES: list[SensorProfile] = [
    SensorProfile(name="spindle_speed", data_type=DataType.UINT16, min_value=0, max_value=30000,
                  nominal_value=15000, noise_std=50, trend_type=TrendType.STABLE, unit="RPM"),
    SensorProfile(name="spindle_load", data_type=DataType.UINT16, min_value=0, max_value=1000,
                  nominal_value=500, noise_std=20, trend_type=TrendType.RANDOM_WALK, unit="0.1%"),
    SensorProfile(name="feed_rate", data_type=DataType.UINT16, min_value=0, max_value=50000,
                  nominal_value=10000, noise_std=100, trend_type=TrendType.STABLE, unit="mm/min"),
    SensorProfile(name="axis_position_x", data_type=DataType.INT32, min_value=-500000, max_value=500000,
                  nominal_value=0, drift_rate=5000, noise_std=10, trend_type=TrendType.SINUSOIDAL,
                  trend_period=30, unit="µm"),
    SensorProfile(name="axis_position_y", data_type=DataType.INT32, min_value=-500000, max_value=500000,
                  nominal_value=0, drift_rate=5000, noise_std=10, trend_type=TrendType.SINUSOIDAL,
                  trend_period=45, unit="µm"),
    SensorProfile(name="coolant_temp", data_type=DataType.INT16, min_value=150, max_value=400,
                  nominal_value=220, noise_std=5, trend_type=TrendType.STABLE, unit="0.1°C"),
    SensorProfile(name="part_count", data_type=DataType.UINT32, min_value=0, max_value=4294967295,
                  nominal_value=0, drift_rate=0.1, noise_std=0, trend_type=TrendType.INCREASING, unit=""),
]

WATER_PROFILES: list[SensorProfile] = [
    SensorProfile(name="inlet_pressure", data_type=DataType.UINT16, min_value=0, max_value=10000,
                  nominal_value=5000, noise_std=100, trend_type=TrendType.STABLE, unit="mbar"),
    SensorProfile(name="outlet_pressure", data_type=DataType.UINT16, min_value=0, max_value=10000,
                  nominal_value=4500, noise_std=100, trend_type=TrendType.STABLE, unit="mbar"),
    SensorProfile(name="flow_rate", data_type=DataType.UINT16, min_value=0, max_value=50000,
                  nominal_value=25000, noise_std=500, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=100, unit="0.1 L/min"),
    SensorProfile(name="tank_level", data_type=DataType.UINT16, min_value=0, max_value=10000,
                  nominal_value=7000, noise_std=50, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=20, unit="0.01%"),
    SensorProfile(name="chlorine_level", data_type=DataType.UINT16, min_value=0, max_value=500,
                  nominal_value=200, noise_std=10, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=5, unit="0.01 ppm"),
    SensorProfile(name="ph_level", data_type=DataType.UINT16, min_value=600, max_value=800,
                  nominal_value=700, noise_std=5, trend_type=TrendType.STABLE, unit="0.01 pH"),
    SensorProfile(name="turbidity", data_type=DataType.UINT16, min_value=0, max_value=1000,
                  nominal_value=50, noise_std=10, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=2, unit="0.1 NTU"),
    SensorProfile(name="pump_status", data_type=DataType.UINT16, min_value=0, max_value=1,
                  nominal_value=1, noise_std=0, trend_type=TrendType.STABLE, unit=""),
]

ENERGY_PROFILES: list[SensorProfile] = [
    SensorProfile(name="voltage_l1", data_type=DataType.FLOAT32, min_value=380, max_value=420,
                  nominal_value=400, noise_std=2, trend_type=TrendType.STABLE, unit="V"),
    SensorProfile(name="voltage_l2", data_type=DataType.FLOAT32, min_value=380, max_value=420,
                  nominal_value=400, noise_std=2, trend_type=TrendType.STABLE, unit="V"),
    SensorProfile(name="voltage_l3", data_type=DataType.FLOAT32, min_value=380, max_value=420,
                  nominal_value=400, noise_std=2, trend_type=TrendType.STABLE, unit="V"),
    SensorProfile(name="current_l1", data_type=DataType.FLOAT32, min_value=0, max_value=500,
                  nominal_value=250, noise_std=5, trend_type=TrendType.SINUSOIDAL,
                  trend_period=3600, unit="A"),
    SensorProfile(name="current_l2", data_type=DataType.FLOAT32, min_value=0, max_value=500,
                  nominal_value=250, noise_std=5, trend_type=TrendType.SINUSOIDAL,
                  trend_period=3600, unit="A"),
    SensorProfile(name="current_l3", data_type=DataType.FLOAT32, min_value=0, max_value=500,
                  nominal_value=250, noise_std=5, trend_type=TrendType.SINUSOIDAL,
                  trend_period=3600, unit="A"),
    SensorProfile(name="active_power", data_type=DataType.FLOAT32, min_value=0, max_value=500000,
                  nominal_value=250000, noise_std=1000, trend_type=TrendType.SINUSOIDAL,
                  trend_period=3600, unit="W"),
    SensorProfile(name="reactive_power", data_type=DataType.FLOAT32, min_value=-100000, max_value=100000,
                  nominal_value=50000, noise_std=500, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=100, unit="VAR"),
    SensorProfile(name="frequency", data_type=DataType.FLOAT32, min_value=49.5, max_value=50.5,
                  nominal_value=50.0, noise_std=0.01, trend_type=TrendType.STABLE, unit="Hz"),
    SensorProfile(name="power_factor", data_type=DataType.FLOAT32, min_value=0.7, max_value=1.0,
                  nominal_value=0.95, noise_std=0.01, trend_type=TrendType.STABLE, unit=""),
]

OIL_GAS_PROFILES: list[SensorProfile] = [
    SensorProfile(name="wellhead_pressure", data_type=DataType.FLOAT32, min_value=0, max_value=500,
                  nominal_value=250, noise_std=5, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=2, unit="bar"),
    SensorProfile(name="wellhead_temp", data_type=DataType.FLOAT32, min_value=20, max_value=150,
                  nominal_value=85, noise_std=1, trend_type=TrendType.STABLE, unit="°C"),
    SensorProfile(name="flow_rate_oil", data_type=DataType.FLOAT32, min_value=0, max_value=10000,
                  nominal_value=5000, noise_std=100, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=50, unit="bbl/d"),
    SensorProfile(name="flow_rate_gas", data_type=DataType.FLOAT32, min_value=0, max_value=100000,
                  nominal_value=50000, noise_std=1000, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=500, unit="scf/d"),
    SensorProfile(name="separator_level", data_type=DataType.UINT16, min_value=0, max_value=10000,
                  nominal_value=5000, noise_std=100, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=20, unit="0.01%"),
    SensorProfile(name="pipeline_pressure", data_type=DataType.FLOAT32, min_value=0, max_value=100,
                  nominal_value=60, noise_std=1, trend_type=TrendType.STABLE, unit="bar"),
    SensorProfile(name="compressor_speed", data_type=DataType.UINT16, min_value=0, max_value=10000,
                  nominal_value=7500, noise_std=50, trend_type=TrendType.STABLE, unit="RPM"),
    SensorProfile(name="h2s_level", data_type=DataType.FLOAT32, min_value=0, max_value=100,
                  nominal_value=5, noise_std=0.5, trend_type=TrendType.RANDOM_WALK,
                  drift_rate=0.2, unit="ppm"),
]


def get_profiles_for_vertical(vertical: str) -> list[SensorProfile]:
    """Get predefined sensor profiles for an industry vertical.

    Args:
        vertical: Industry vertical name (manufacturing, water, energy, oil_gas)

    Returns:
        List of sensor profiles appropriate for that vertical
    """
    profiles_map = {
        "manufacturing": MANUFACTURING_PROFILES,
        "water": WATER_PROFILES,
        "wastewater": WATER_PROFILES,
        "energy": ENERGY_PROFILES,
        "power": ENERGY_PROFILES,
        "oil_gas": OIL_GAS_PROFILES,
        "oil": OIL_GAS_PROFILES,
        "gas": OIL_GAS_PROFILES,
    }
    return profiles_map.get(vertical.lower(), [])
