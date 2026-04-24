# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Timing Model Interface and Configuration.

This module defines the interface for timing models and configuration
dataclasses. All protocol engines should use these abstractions for
consistent timing behavior.

Timing models sample delays between requests and responses based on
realistic distributions derived from vendor fingerprints or learned
from actual network captures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class TimingDistribution(str, Enum):
    """Supported timing distribution types."""

    UNIFORM = "uniform"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"
    GAMMA = "gamma"
    LOGNORMAL = "lognormal"
    LEARNED = "learned"  # From PCAP analysis


@dataclass(frozen=True)
class TimingConfig:
    """Configuration for timing model behavior.

    This is immutable (frozen) to prevent accidental modifications
    during packet generation.

    Attributes:
        distribution: Type of distribution to sample from
        min_ms: Minimum delay in milliseconds
        max_ms: Maximum delay in milliseconds
        mean_ms: Mean delay (for gaussian, gamma, lognormal)
        std_dev_ms: Standard deviation (for gaussian, gamma, lognormal)
        outlier_probability: Probability of an outlier (0.0-1.0)
        outlier_multiplier: Multiplier for outlier delays
        timeout_probability: Probability of no response (0.0-1.0)
        learned_samples: Sample data for LEARNED distribution
    """

    distribution: TimingDistribution = TimingDistribution.GAUSSIAN
    min_ms: float = 1.0
    max_ms: float = 50.0
    mean_ms: float = 10.0
    std_dev_ms: float = 5.0
    outlier_probability: float = 0.01
    outlier_multiplier: float = 3.0
    timeout_probability: float = 0.0
    learned_samples: tuple[float, ...] = field(default_factory=tuple)

    @classmethod
    def from_fingerprint(cls, fingerprint: dict[str, Any]) -> "TimingConfig":
        """Create timing config from a vendor fingerprint.

        Args:
            fingerprint: Vendor fingerprint dictionary with response_timing

        Returns:
            TimingConfig with fingerprint parameters
        """
        timing = fingerprint.get("response_timing", {})
        error = fingerprint.get("error_behavior", {})

        distribution_str = timing.get("distribution", "gaussian")
        try:
            distribution = TimingDistribution(distribution_str)
        except ValueError:
            distribution = TimingDistribution.GAUSSIAN

        return cls(
            distribution=distribution,
            min_ms=timing.get("min_ms", 1.0),
            max_ms=timing.get("max_ms", 50.0),
            mean_ms=timing.get("mean_ms", 10.0),
            std_dev_ms=timing.get("std_dev_ms", 5.0),
            outlier_probability=timing.get("outlier_probability", 0.01),
            outlier_multiplier=timing.get("outlier_multiplier", 3.0),
            timeout_probability=error.get("timeout_probability", 0.0),
        )

    @classmethod
    def from_learned_data(
        cls,
        samples: list[float],
        timeout_probability: float = 0.0,
    ) -> "TimingConfig":
        """Create timing config from learned PCAP data.

        Args:
            samples: List of observed delay samples in milliseconds
            timeout_probability: Observed timeout rate

        Returns:
            TimingConfig configured for LEARNED distribution
        """
        return cls(
            distribution=TimingDistribution.LEARNED,
            learned_samples=tuple(samples),
            timeout_probability=timeout_probability,
            # Calculate bounds from samples
            min_ms=min(samples) if samples else 1.0,
            max_ms=max(samples) if samples else 50.0,
            mean_ms=sum(samples) / len(samples) if samples else 10.0,
        )


@dataclass
class TimingSample:
    """A sampled timing value with metadata.

    Attributes:
        delay_ms: Delay in milliseconds
        is_outlier: True if this is an outlier sample
        is_timeout: True if this represents a timeout (no response)
    """

    delay_ms: float
    is_outlier: bool = False
    is_timeout: bool = False


@runtime_checkable
class TimingModel(Protocol):
    """Protocol (interface) for timing models.

    All timing model implementations must provide these methods.
    Use @runtime_checkable for isinstance() support.
    """

    @property
    def config(self) -> TimingConfig:
        """Get the timing configuration.

        Returns:
            TimingConfig used by this model
        """
        ...

    def sample(self, context: dict[str, Any] | None = None) -> TimingSample:
        """Sample a delay from the timing distribution.

        Args:
            context: Optional context dict for learned/adaptive timing
                    (e.g., current time, flow state, etc.)

        Returns:
            TimingSample with delay and metadata
        """
        ...

    def should_timeout(self) -> bool:
        """Determine if the next request should timeout.

        Returns:
            True if a timeout should occur (no response)
        """
        ...

    def get_delay_ms(self, context: dict[str, Any] | None = None) -> float:
        """Convenience method to get just the delay value.

        Args:
            context: Optional context for sampling

        Returns:
            Delay in milliseconds (0 for timeout)
        """
        ...


# Default timing configurations for common scenarios

DEFAULT_TIMING_CONFIG = TimingConfig(
    distribution=TimingDistribution.GAUSSIAN,
    min_ms=1.0,
    max_ms=50.0,
    mean_ms=10.0,
    std_dev_ms=5.0,
    outlier_probability=0.01,
    outlier_multiplier=3.0,
    timeout_probability=0.0005,
)

FAST_DEVICE_TIMING_CONFIG = TimingConfig(
    distribution=TimingDistribution.GAUSSIAN,
    min_ms=0.5,
    max_ms=10.0,
    mean_ms=2.0,
    std_dev_ms=1.0,
    outlier_probability=0.005,
    outlier_multiplier=2.0,
    timeout_probability=0.0001,
)

SLOW_DEVICE_TIMING_CONFIG = TimingConfig(
    distribution=TimingDistribution.LOGNORMAL,
    min_ms=10.0,
    max_ms=500.0,
    mean_ms=100.0,
    std_dev_ms=50.0,
    outlier_probability=0.02,
    outlier_multiplier=3.0,
    timeout_probability=0.002,
)

NOISY_NETWORK_TIMING_CONFIG = TimingConfig(
    distribution=TimingDistribution.GAMMA,
    min_ms=5.0,
    max_ms=200.0,
    mean_ms=30.0,
    std_dev_ms=20.0,
    outlier_probability=0.05,
    outlier_multiplier=4.0,
    timeout_probability=0.01,
)
