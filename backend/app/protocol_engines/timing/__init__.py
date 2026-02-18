"""Unified Timing Model System for Protocol Engines.

This package provides a standardized timing interface for all protocol
engines, ensuring consistent behavior across the traffic generation system.

Key components:
- TimingConfig: Immutable configuration for timing parameters
- TimingModel: Protocol (interface) for timing implementations
- TimingSample: Container for sampled delay values

Supported distributions:
- Gaussian: Normal distribution (most common)
- Lognormal: Skewed distribution (network delays)
- Uniform: Even distribution within bounds
- Exponential: Memoryless (random arrivals)
- Gamma: Flexible shape (response times)
- Learned: Replay from captured samples

Usage:
    from app.protocol_engines.timing import (
        timing_model_from_fingerprint,
        create_timing_model,
        TimingConfig,
    )

    # From vendor fingerprint
    model = timing_model_from_fingerprint(device.vendor_fingerprint)
    sample = model.sample()
    delay_ms, is_outlier = sample.delay_ms, sample.is_outlier

    # From configuration
    config = TimingConfig(
        distribution=TimingDistribution.GAUSSIAN,
        mean_ms=10.0,
        std_dev_ms=5.0,
    )
    model = create_timing_model(config)

    # From learned data
    model = timing_model_from_learned_samples([5.2, 6.1, 4.8, 7.3, 5.5])
"""

from .interface import (
    DEFAULT_TIMING_CONFIG,
    FAST_DEVICE_TIMING_CONFIG,
    NOISY_NETWORK_TIMING_CONFIG,
    SLOW_DEVICE_TIMING_CONFIG,
    TimingConfig,
    TimingDistribution,
    TimingModel,
    TimingSample,
)
from .models import (
    BaseTimingModel,
    ExponentialTimingModel,
    GammaTimingModel,
    GaussianTimingModel,
    LearnedTimingModel,
    LognormalTimingModel,
    UniformTimingModel,
)
from .factory import (
    create_default_timing_model,
    create_fast_device_timing_model,
    create_noisy_network_timing_model,
    create_slow_device_timing_model,
    create_timing_model,
    get_timing_model_for_protocol,
    timing_model_from_fingerprint,
    timing_model_from_flow,
    timing_model_from_learned_samples,
)


__all__ = [
    # Interface types
    "TimingConfig",
    "TimingDistribution",
    "TimingModel",
    "TimingSample",
    # Default configurations
    "DEFAULT_TIMING_CONFIG",
    "FAST_DEVICE_TIMING_CONFIG",
    "SLOW_DEVICE_TIMING_CONFIG",
    "NOISY_NETWORK_TIMING_CONFIG",
    # Model classes
    "BaseTimingModel",
    "GaussianTimingModel",
    "LognormalTimingModel",
    "UniformTimingModel",
    "ExponentialTimingModel",
    "GammaTimingModel",
    "LearnedTimingModel",
    # Factory functions
    "create_timing_model",
    "create_default_timing_model",
    "create_fast_device_timing_model",
    "create_slow_device_timing_model",
    "create_noisy_network_timing_model",
    "timing_model_from_fingerprint",
    "timing_model_from_flow",
    "timing_model_from_learned_samples",
    "get_timing_model_for_protocol",
]
