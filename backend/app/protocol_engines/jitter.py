# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Timing utilities for packet generation."""

import random
from abc import ABC, abstractmethod
from typing import Any


class JitterModel(ABC):
    """Abstract base for jitter models."""

    @abstractmethod
    def apply(self, base_time: float) -> float:
        """Apply jitter to base time.

        Args:
            base_time: Base time value

        Returns:
            Time with jitter applied
        """
        pass


class GaussianJitter(JitterModel):
    """Gaussian (normal) distribution jitter."""

    def __init__(self, std_dev_ms: float):
        """Initialize Gaussian jitter.

        Args:
            std_dev_ms: Standard deviation in milliseconds
        """
        self.std_dev_ms = std_dev_ms

    def apply(self, base_time: float) -> float:
        """Apply Gaussian jitter."""
        jitter = random.gauss(0, self.std_dev_ms)
        return max(0, base_time + jitter)


class UniformJitter(JitterModel):
    """Uniform distribution jitter."""

    def __init__(self, min_jitter_ms: float, max_jitter_ms: float):
        """Initialize uniform jitter.

        Args:
            min_jitter_ms: Minimum jitter in milliseconds
            max_jitter_ms: Maximum jitter in milliseconds
        """
        self.min_jitter_ms = min_jitter_ms
        self.max_jitter_ms = max_jitter_ms

    def apply(self, base_time: float) -> float:
        """Apply uniform jitter."""
        jitter = random.uniform(self.min_jitter_ms, self.max_jitter_ms)
        return max(0, base_time + jitter)


class ExponentialJitter(JitterModel):
    """Exponential distribution jitter (for burst patterns)."""

    def __init__(self, lambda_ms: float):
        """Initialize exponential jitter.

        Args:
            lambda_ms: Lambda parameter (mean) in milliseconds
        """
        self.lambda_ms = lambda_ms

    def apply(self, base_time: float) -> float:
        """Apply exponential jitter."""
        jitter = random.expovariate(1.0 / self.lambda_ms) if self.lambda_ms > 0 else 0
        return max(0, base_time + jitter)


def get_jitter_model(timing_config: dict[str, Any]) -> JitterModel | None:
    """Create jitter model from timing configuration.

    Args:
        timing_config: Timing configuration dictionary with jitter settings

    Returns:
        JitterModel instance or None if no jitter configured
    """
    jitter_config = timing_config.get("jitter", {})
    jitter_type = jitter_config.get("type")

    if jitter_type == "gaussian":
        std_dev = jitter_config.get("std_dev_ms", 1.0)
        return GaussianJitter(std_dev)
    elif jitter_type == "uniform":
        min_jitter = jitter_config.get("min_ms", 0.0)
        max_jitter = jitter_config.get("max_ms", 5.0)
        return UniformJitter(min_jitter, max_jitter)
    elif jitter_type == "exponential":
        lambda_val = jitter_config.get("lambda_ms", 2.0)
        return ExponentialJitter(lambda_val)

    return None


def get_response_delay(timing_model: dict[str, Any]) -> float:
    """Get response delay from timing model.

    Args:
        timing_model: Timing model configuration

    Returns:
        Response delay in milliseconds
    """
    base_delay = timing_model.get("response_delay_ms", 5.0)
    jitter_model = get_jitter_model(timing_model)

    if jitter_model:
        return jitter_model.apply(base_delay)

    return base_delay


def apply_jitter(base_time: float, timing_model: dict[str, Any]) -> float:
    """Apply jitter to a base time value.

    Args:
        base_time: Base time in milliseconds
        timing_model: Timing model configuration

    Returns:
        Time with jitter applied in milliseconds
    """
    jitter_model = get_jitter_model(timing_model)

    if jitter_model:
        return jitter_model.apply(base_time)

    return base_time
