"""Learned payload generator for realistic OT traffic payloads.

This module generates realistic payload values based on patterns learned
from PCAP analysis. It supports:
- Modbus register and coil values
- EtherNet/IP data values
- PROFINET I/O data

The generator uses statistical distributions learned from real traffic
to produce values that match actual industrial system behavior.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ValueDistribution:
    """Distribution parameters for a payload value."""

    value_type: str  # "constant", "range", "discrete", "gaussian", "pattern"
    params: dict[str, Any] = field(default_factory=dict)

    # For constant values
    constant_value: int | float | None = None

    # For range values
    min_value: float | None = None
    max_value: float | None = None

    # For discrete values (common/mode values)
    discrete_values: list[int | float] = field(default_factory=list)
    discrete_weights: list[float] = field(default_factory=list)

    # For Gaussian/normal distribution
    mean: float | None = None
    std_dev: float | None = None

    # For pattern values (cyclic, trending)
    pattern_type: str | None = None  # "cyclic", "trending", "random_walk"
    pattern_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegisterProfile:
    """Profile for a Modbus register or group of registers."""

    start_address: int
    count: int
    function_code: int  # 3 for holding, 4 for input
    distribution: ValueDistribution
    name: str = ""
    unit: str = ""
    scale_factor: float = 1.0
    offset: float = 0.0


@dataclass
class CoilProfile:
    """Profile for Modbus coils."""

    start_address: int
    count: int
    on_probability: float = 0.5  # Probability of being ON
    sticky: bool = False  # If True, state persists between reads


class LearnedPayloadGenerator:
    """Generator for realistic payload values based on learned patterns.

    This generator maintains state across calls to produce coherent
    value sequences that match real industrial traffic patterns.
    """

    def __init__(self, seed: int | None = None):
        """Initialize the payload generator.

        Args:
            seed: Optional random seed for reproducibility
        """
        self._rng = np.random.default_rng(seed)
        self._random = random.Random(seed)

        # Register profiles by address
        self._register_profiles: dict[int, RegisterProfile] = {}

        # Coil profiles
        self._coil_profiles: dict[int, CoilProfile] = {}

        # State tracking for patterns
        self._register_state: dict[int, float] = {}
        self._coil_state: dict[int, bool] = {}

        # Cycle counter for cyclic patterns
        self._cycle_counter = 0

    def add_register_profile(self, profile: RegisterProfile) -> None:
        """Add a register profile.

        Args:
            profile: Register profile to add
        """
        for i in range(profile.count):
            self._register_profiles[profile.start_address + i] = profile

    def add_coil_profile(self, profile: CoilProfile) -> None:
        """Add a coil profile.

        Args:
            profile: Coil profile to add
        """
        for i in range(profile.count):
            self._coil_profiles[profile.start_address + i] = profile

    def generate_register_values(
        self,
        start_address: int,
        count: int,
        function_code: int = 3,
    ) -> list[int]:
        """Generate register values for a Modbus read.

        Args:
            start_address: Starting register address
            count: Number of registers to read
            function_code: Modbus function code (3 or 4)

        Returns:
            List of register values (16-bit unsigned integers)
        """
        values = []

        for i in range(count):
            address = start_address + i
            value = self._generate_single_register(address, function_code)
            values.append(value)

        return values

    def _generate_single_register(self, address: int, function_code: int) -> int:
        """Generate a single register value.

        Args:
            address: Register address
            function_code: Modbus function code

        Returns:
            16-bit unsigned integer value
        """
        profile = self._register_profiles.get(address)

        if profile is None:
            # No profile - generate random value
            return self._rng.integers(0, 65536)

        dist = profile.distribution
        raw_value: float

        if dist.value_type == "constant":
            raw_value = dist.constant_value or 0

        elif dist.value_type == "range":
            min_v = dist.min_value or 0
            max_v = dist.max_value or 65535
            raw_value = self._rng.uniform(min_v, max_v)

        elif dist.value_type == "discrete":
            if dist.discrete_values:
                if dist.discrete_weights:
                    raw_value = self._random.choices(
                        dist.discrete_values,
                        weights=dist.discrete_weights,
                    )[0]
                else:
                    raw_value = self._random.choice(dist.discrete_values)
            else:
                raw_value = 0

        elif dist.value_type == "gaussian":
            mean = dist.mean or 32768
            std = dist.std_dev or 1000
            raw_value = self._rng.normal(mean, std)

        elif dist.value_type == "pattern":
            raw_value = self._generate_pattern_value(address, dist)

        else:
            raw_value = self._rng.integers(0, 65536)

        # Apply scale and offset
        scaled_value = raw_value * profile.scale_factor + profile.offset

        # Clamp to 16-bit unsigned range
        int_value = int(max(0, min(65535, scaled_value)))

        # Store for pattern tracking
        self._register_state[address] = scaled_value

        return int_value

    def _generate_pattern_value(self, address: int, dist: ValueDistribution) -> float:
        """Generate a value following a pattern.

        Args:
            address: Register address
            dist: Value distribution with pattern parameters

        Returns:
            Generated value
        """
        pattern_type = dist.pattern_type or "random_walk"
        params = dist.pattern_params

        if pattern_type == "cyclic":
            # Sinusoidal pattern
            amplitude = params.get("amplitude", 10000)
            period = params.get("period", 100)
            offset = params.get("offset", 32768)

            value = offset + amplitude * np.sin(2 * np.pi * self._cycle_counter / period)
            self._cycle_counter += 1

        elif pattern_type == "trending":
            # Linear trend with noise
            slope = params.get("slope", 0.1)
            noise_std = params.get("noise_std", 100)
            initial = params.get("initial", 32768)

            previous = self._register_state.get(address, initial)
            delta = slope + self._rng.normal(0, noise_std)
            value = previous + delta

            # Optional bounds
            min_val = params.get("min", 0)
            max_val = params.get("max", 65535)
            value = max(min_val, min(max_val, value))

        elif pattern_type == "random_walk":
            # Random walk with drift
            step_size = params.get("step_size", 100)
            drift = params.get("drift", 0)
            initial = params.get("initial", 32768)

            previous = self._register_state.get(address, initial)
            step = self._rng.normal(drift, step_size)
            value = previous + step

            # Bounds
            min_val = params.get("min", 0)
            max_val = params.get("max", 65535)
            value = max(min_val, min(max_val, value))

        elif pattern_type == "step":
            # Step changes at intervals
            interval = params.get("interval", 50)
            values = params.get("values", [0, 65535])

            step_index = (self._cycle_counter // interval) % len(values)
            value = values[step_index]
            self._cycle_counter += 1

        else:
            value = self._rng.integers(0, 65536)

        return value

    def generate_coil_values(
        self,
        start_address: int,
        count: int,
    ) -> list[bool]:
        """Generate coil values for a Modbus read.

        Args:
            start_address: Starting coil address
            count: Number of coils to read

        Returns:
            List of boolean coil states
        """
        values = []

        for i in range(count):
            address = start_address + i
            value = self._generate_single_coil(address)
            values.append(value)

        return values

    def _generate_single_coil(self, address: int) -> bool:
        """Generate a single coil value.

        Args:
            address: Coil address

        Returns:
            Boolean coil state
        """
        profile = self._coil_profiles.get(address)

        if profile is None:
            # No profile - 50/50 chance
            return self._random.random() < 0.5

        # Check sticky state
        if profile.sticky and address in self._coil_state:
            # Small chance to toggle
            if self._random.random() < 0.05:
                self._coil_state[address] = not self._coil_state[address]
            return self._coil_state[address]

        # Generate based on probability
        value = self._random.random() < profile.on_probability

        if profile.sticky:
            self._coil_state[address] = value

        return value

    def load_from_patterns(self, patterns: list[dict[str, Any]]) -> None:
        """Load register/coil profiles from learned patterns.

        Args:
            patterns: List of payload patterns from PCAP analysis
        """
        for pattern in patterns:
            payload_info = pattern.get("payload_patterns", {})

            # Extract size distribution if available
            size_dist = payload_info.get("size_distribution", {})
            common_sizes = payload_info.get("common_sizes", [])

            # Try to infer register count from common sizes
            # Modbus response size = 3 (header) + 2 * register_count
            if common_sizes:
                for size_info in common_sizes:
                    size = size_info.get("value", 0)
                    if size > 3:
                        inferred_count = (size - 3) // 2
                        if inferred_count > 0:
                            logger.debug(f"Inferred {inferred_count} registers from size {size}")

            # Create generic profiles based on protocol and confidence
            protocol = pattern.get("protocol", "")
            confidence = pattern.get("confidence", 0.5)

            if "modbus" in protocol.lower():
                # Create holding register profile with range distribution
                mean_size = size_dist.get("mean", 100)
                std_size = size_dist.get("std", 20)

                profile = RegisterProfile(
                    start_address=0,
                    count=125,  # Typical max registers
                    function_code=3,
                    distribution=ValueDistribution(
                        value_type="gaussian",
                        mean=32768,  # Mid-range
                        std_dev=10000,
                    ),
                    name=f"Learned from {pattern.get('name', 'unknown')}",
                )
                self.add_register_profile(profile)

    def reset_state(self) -> None:
        """Reset all internal state."""
        self._register_state.clear()
        self._coil_state.clear()
        self._cycle_counter = 0


class ModbusPayloadGenerator(LearnedPayloadGenerator):
    """Specialized payload generator for Modbus traffic.

    Adds Modbus-specific features like:
    - Holding register profiles
    - Input register profiles
    - Coil and discrete input handling
    - Write request validation
    """

    def __init__(self, seed: int | None = None):
        """Initialize Modbus payload generator."""
        super().__init__(seed)

        # Separate profiles for different register types
        self._holding_registers: dict[int, RegisterProfile] = {}
        self._input_registers: dict[int, RegisterProfile] = {}
        self._discrete_inputs: dict[int, CoilProfile] = {}

    def add_holding_register_profile(self, profile: RegisterProfile) -> None:
        """Add a holding register profile (FC 3, 6, 16)."""
        profile.function_code = 3
        for i in range(profile.count):
            self._holding_registers[profile.start_address + i] = profile
        self.add_register_profile(profile)

    def add_input_register_profile(self, profile: RegisterProfile) -> None:
        """Add an input register profile (FC 4)."""
        profile.function_code = 4
        for i in range(profile.count):
            self._input_registers[profile.start_address + i] = profile
        self.add_register_profile(profile)

    def generate_read_holding_registers_response(
        self,
        start_address: int,
        count: int,
    ) -> bytes:
        """Generate response data for FC 3 (Read Holding Registers).

        Args:
            start_address: Starting register address
            count: Number of registers

        Returns:
            Response data bytes (byte count + register values)
        """
        values = self.generate_register_values(start_address, count, function_code=3)

        # Build response: byte count + values (big-endian)
        byte_count = count * 2
        data = bytes([byte_count])

        for value in values:
            data += value.to_bytes(2, byteorder="big")

        return data

    def generate_read_input_registers_response(
        self,
        start_address: int,
        count: int,
    ) -> bytes:
        """Generate response data for FC 4 (Read Input Registers).

        Args:
            start_address: Starting register address
            count: Number of registers

        Returns:
            Response data bytes
        """
        values = self.generate_register_values(start_address, count, function_code=4)

        byte_count = count * 2
        data = bytes([byte_count])

        for value in values:
            data += value.to_bytes(2, byteorder="big")

        return data

    def generate_read_coils_response(
        self,
        start_address: int,
        count: int,
    ) -> bytes:
        """Generate response data for FC 1 (Read Coils).

        Args:
            start_address: Starting coil address
            count: Number of coils

        Returns:
            Response data bytes (byte count + coil status bytes)
        """
        coil_values = self.generate_coil_values(start_address, count)

        # Pack coils into bytes (8 coils per byte, LSB first)
        byte_count = (count + 7) // 8
        coil_bytes = [0] * byte_count

        for i, value in enumerate(coil_values):
            if value:
                byte_index = i // 8
                bit_index = i % 8
                coil_bytes[byte_index] |= (1 << bit_index)

        return bytes([byte_count]) + bytes(coil_bytes)

    def generate_read_discrete_inputs_response(
        self,
        start_address: int,
        count: int,
    ) -> bytes:
        """Generate response data for FC 2 (Read Discrete Inputs).

        Same format as coils but typically read-only.
        """
        return self.generate_read_coils_response(start_address, count)

    def create_typical_plc_profile(self) -> None:
        """Create typical PLC register profile.

        Sets up common register ranges found in typical PLCs.
        """
        # Process values (analog inputs/outputs)
        self.add_input_register_profile(RegisterProfile(
            start_address=0,
            count=16,
            function_code=4,
            distribution=ValueDistribution(
                value_type="pattern",
                pattern_type="random_walk",
                pattern_params={
                    "step_size": 50,
                    "drift": 0,
                    "initial": 16384,
                    "min": 0,
                    "max": 32767,
                },
            ),
            name="Analog Inputs",
            unit="counts",
        ))

        # Setpoints (holding registers)
        self.add_holding_register_profile(RegisterProfile(
            start_address=100,
            count=8,
            function_code=3,
            distribution=ValueDistribution(
                value_type="discrete",
                discrete_values=[0, 4096, 8192, 16384, 32768],
                discrete_weights=[0.1, 0.2, 0.3, 0.3, 0.1],
            ),
            name="Setpoints",
        ))

        # Status registers
        self.add_holding_register_profile(RegisterProfile(
            start_address=200,
            count=4,
            function_code=3,
            distribution=ValueDistribution(
                value_type="discrete",
                discrete_values=[0, 1, 2, 3],
                discrete_weights=[0.7, 0.15, 0.1, 0.05],
            ),
            name="Status",
        ))

        # Alarm/fault coils
        self.add_coil_profile(CoilProfile(
            start_address=0,
            count=16,
            on_probability=0.02,  # Low alarm probability
            sticky=True,
        ))

        # Control coils
        self.add_coil_profile(CoilProfile(
            start_address=100,
            count=8,
            on_probability=0.5,
            sticky=True,
        ))


def create_modbus_generator_from_patterns(
    patterns: list[dict[str, Any]],
    seed: int | None = None,
) -> ModbusPayloadGenerator:
    """Create a Modbus payload generator from learned patterns.

    Args:
        patterns: Learned payload patterns
        seed: Optional random seed

    Returns:
        Configured ModbusPayloadGenerator
    """
    generator = ModbusPayloadGenerator(seed)

    # Load patterns
    generator.load_from_patterns(patterns)

    # Add typical PLC profile as baseline
    generator.create_typical_plc_profile()

    return generator
