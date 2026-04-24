# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Concrete Timing Model Implementations.

This module provides timing model implementations for different
distribution types used in OT traffic simulation.

Supported models:
- GaussianTimingModel: Normal distribution (most common)
- LognormalTimingModel: Skewed distribution (network delays)
- UniformTimingModel: Even distribution within bounds
- ExponentialTimingModel: Memoryless (good for random arrivals)
- GammaTimingModel: Flexible shape (good for response times)
- LearnedTimingModel: Replay from captured samples
"""

import logging
import random
from typing import Any

import numpy as np

from .interface import (
    TimingConfig,
    TimingDistribution,
    TimingModel,
    TimingSample,
)

logger = logging.getLogger(__name__)


class BaseTimingModel:
    """Base implementation for timing models.

    Provides common functionality like timeout checking and
    outlier application.
    """

    def __init__(self, config: TimingConfig, seed: int | None = None):
        """Initialize timing model.

        Args:
            config: TimingConfig with distribution parameters
            seed: Optional random seed for reproducibility
        """
        self._config = config
        self._rng = np.random.default_rng(seed)

    @property
    def config(self) -> TimingConfig:
        """Get the timing configuration."""
        return self._config

    def should_timeout(self) -> bool:
        """Determine if a timeout should occur.

        Returns:
            True if timeout should occur
        """
        if self._config.timeout_probability <= 0:
            return False
        return random.random() < self._config.timeout_probability

    def get_delay_ms(self, context: dict[str, Any] | None = None) -> float:
        """Get delay value from sample.

        Args:
            context: Optional context for sampling

        Returns:
            Delay in milliseconds (0 for timeout)
        """
        sample = self.sample(context)
        return sample.delay_ms if not sample.is_timeout else 0

    def _apply_outlier(self, delay: float) -> tuple[float, bool]:
        """Apply outlier transformation if needed.

        Args:
            delay: Base delay value

        Returns:
            Tuple of (adjusted_delay, is_outlier)
        """
        is_outlier = random.random() < self._config.outlier_probability
        if is_outlier:
            delay *= self._config.outlier_multiplier
        return delay, is_outlier

    def _clamp_delay(self, delay: float, is_outlier: bool = False) -> float:
        """Clamp delay to configured bounds.

        Args:
            delay: Delay value to clamp
            is_outlier: Whether this is an outlier (extends max)

        Returns:
            Clamped delay value
        """
        min_val = self._config.min_ms
        max_val = self._config.max_ms

        if is_outlier:
            max_val *= self._config.outlier_multiplier

        return max(min_val, min(max_val, delay))

    def sample(self, context: dict[str, Any] | None = None) -> TimingSample:
        """Sample a delay (to be implemented by subclasses).

        Args:
            context: Optional context for sampling

        Returns:
            TimingSample with delay and metadata
        """
        raise NotImplementedError("Subclass must implement sample()")


class GaussianTimingModel(BaseTimingModel):
    """Timing model using normal (gaussian) distribution.

    Most common distribution for network response times when
    the system is in steady state.
    """

    def sample(self, context: dict[str, Any] | None = None) -> TimingSample:
        """Sample from gaussian distribution.

        Args:
            context: Optional context (unused)

        Returns:
            TimingSample with delay
        """
        if self.should_timeout():
            return TimingSample(delay_ms=0, is_timeout=True)

        # Sample from gaussian
        delay = self._rng.normal(self._config.mean_ms, self._config.std_dev_ms)

        # Apply outlier transformation
        delay, is_outlier = self._apply_outlier(delay)

        # Clamp to bounds
        delay = self._clamp_delay(delay, is_outlier)

        return TimingSample(delay_ms=delay, is_outlier=is_outlier)


class LognormalTimingModel(BaseTimingModel):
    """Timing model using lognormal distribution.

    Good for modeling network delays where most responses are
    fast but occasional slow responses occur (right-skewed).
    """

    def __init__(self, config: TimingConfig, seed: int | None = None):
        super().__init__(config, seed)
        # Convert mean/std_dev to lognormal parameters
        mean = config.mean_ms
        std = config.std_dev_ms

        if mean > 0 and std > 0:
            self._mu = np.log(mean**2 / np.sqrt(std**2 + mean**2))
            self._sigma = np.sqrt(np.log(1 + (std**2 / mean**2)))
        else:
            self._mu = np.log(10)  # Default mean ~10ms
            self._sigma = 0.5  # Default moderate spread

    def sample(self, context: dict[str, Any] | None = None) -> TimingSample:
        """Sample from lognormal distribution.

        Args:
            context: Optional context (unused)

        Returns:
            TimingSample with delay
        """
        if self.should_timeout():
            return TimingSample(delay_ms=0, is_timeout=True)

        # Sample from lognormal
        delay = self._rng.lognormal(self._mu, self._sigma)

        # Apply outlier transformation
        delay, is_outlier = self._apply_outlier(delay)

        # Clamp to bounds
        delay = self._clamp_delay(delay, is_outlier)

        return TimingSample(delay_ms=delay, is_outlier=is_outlier)


class UniformTimingModel(BaseTimingModel):
    """Timing model using uniform distribution.

    Simple even distribution within bounds. Useful for testing
    or when no specific distribution is known.
    """

    def sample(self, context: dict[str, Any] | None = None) -> TimingSample:
        """Sample from uniform distribution.

        Args:
            context: Optional context (unused)

        Returns:
            TimingSample with delay
        """
        if self.should_timeout():
            return TimingSample(delay_ms=0, is_timeout=True)

        # Sample uniformly between min and max
        delay = self._rng.uniform(self._config.min_ms, self._config.max_ms)

        # Apply outlier transformation
        delay, is_outlier = self._apply_outlier(delay)

        # Clamp (outliers can exceed normal max)
        delay = self._clamp_delay(delay, is_outlier)

        return TimingSample(delay_ms=delay, is_outlier=is_outlier)


class ExponentialTimingModel(BaseTimingModel):
    """Timing model using exponential distribution.

    Memoryless distribution, good for modeling random arrivals
    or inter-event times.
    """

    def sample(self, context: dict[str, Any] | None = None) -> TimingSample:
        """Sample from exponential distribution.

        Args:
            context: Optional context (unused)

        Returns:
            TimingSample with delay
        """
        if self.should_timeout():
            return TimingSample(delay_ms=0, is_timeout=True)

        # Sample from exponential (scale = mean)
        delay = self._rng.exponential(self._config.mean_ms)

        # Apply outlier transformation
        delay, is_outlier = self._apply_outlier(delay)

        # Clamp to bounds
        delay = self._clamp_delay(delay, is_outlier)

        return TimingSample(delay_ms=delay, is_outlier=is_outlier)


class GammaTimingModel(BaseTimingModel):
    """Timing model using gamma distribution.

    Flexible distribution that can model various response time
    patterns depending on shape parameter.
    """

    def __init__(self, config: TimingConfig, seed: int | None = None):
        super().__init__(config, seed)
        # Calculate gamma parameters from mean/std_dev
        mean = config.mean_ms
        std = config.std_dev_ms

        if mean > 0 and std > 0:
            self._shape = (mean / std) ** 2
            self._scale = mean / self._shape
        else:
            self._shape = 2.0
            self._scale = 5.0

    def sample(self, context: dict[str, Any] | None = None) -> TimingSample:
        """Sample from gamma distribution.

        Args:
            context: Optional context (unused)

        Returns:
            TimingSample with delay
        """
        if self.should_timeout():
            return TimingSample(delay_ms=0, is_timeout=True)

        # Sample from gamma
        delay = self._rng.gamma(self._shape, self._scale)

        # Apply outlier transformation
        delay, is_outlier = self._apply_outlier(delay)

        # Clamp to bounds
        delay = self._clamp_delay(delay, is_outlier)

        return TimingSample(delay_ms=delay, is_outlier=is_outlier)


class LearnedTimingModel(BaseTimingModel):
    """Timing model that replays learned timing data.

    Uses actual timing samples from PCAP analysis to produce
    realistic traffic patterns.
    """

    def __init__(self, config: TimingConfig, seed: int | None = None):
        super().__init__(config, seed)
        self._samples = list(config.learned_samples) if config.learned_samples else []
        self._sample_index = 0

        if not self._samples:
            logger.warning("LearnedTimingModel created with no samples, using defaults")
            self._samples = [10.0]  # Fallback

    def sample(self, context: dict[str, Any] | None = None) -> TimingSample:
        """Sample from learned data.

        Cycles through learned samples in order, optionally adding
        small random jitter for variety.

        Args:
            context: Optional context dict
                    - "jitter_percent": Add jitter as percentage (default 5%)

        Returns:
            TimingSample with delay
        """
        if self.should_timeout():
            return TimingSample(delay_ms=0, is_timeout=True)

        # Get next sample (cycle through)
        delay = self._samples[self._sample_index]
        self._sample_index = (self._sample_index + 1) % len(self._samples)

        # Add jitter if requested
        jitter_percent = 5.0
        if context:
            jitter_percent = context.get("jitter_percent", 5.0)

        if jitter_percent > 0:
            jitter = delay * (jitter_percent / 100.0)
            delay += self._rng.uniform(-jitter, jitter)

        # Apply outlier transformation
        delay, is_outlier = self._apply_outlier(delay)

        # Clamp to bounds
        delay = self._clamp_delay(delay, is_outlier)

        return TimingSample(delay_ms=max(0.1, delay), is_outlier=is_outlier)

    def add_samples(self, samples: list[float]) -> None:
        """Add more learned samples.

        Args:
            samples: List of delay values in milliseconds
        """
        self._samples.extend(samples)
        logger.debug(f"LearnedTimingModel now has {len(self._samples)} samples")


# Model class registry for factory pattern
TIMING_MODEL_CLASSES: dict[TimingDistribution, type[BaseTimingModel]] = {
    TimingDistribution.GAUSSIAN: GaussianTimingModel,
    TimingDistribution.LOGNORMAL: LognormalTimingModel,
    TimingDistribution.UNIFORM: UniformTimingModel,
    TimingDistribution.EXPONENTIAL: ExponentialTimingModel,
    TimingDistribution.GAMMA: GammaTimingModel,
    TimingDistribution.LEARNED: LearnedTimingModel,
}
