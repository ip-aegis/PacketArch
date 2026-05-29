# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Timing Model Factory Functions.

This module provides factory functions for creating timing models
from various sources:
- Vendor fingerprints
- Flow contexts
- Raw configuration
- Learned PCAP data
"""

import logging
from typing import Any

from .interface import (
    DEFAULT_TIMING_CONFIG,
    TimingConfig,
    TimingDistribution,
    TimingModel,
)
from .models import (
    LearnedTimingModel,
    TIMING_MODEL_CLASSES,
)

logger = logging.getLogger(__name__)


def create_timing_model(
    config: TimingConfig,
    seed: int | None = None,
) -> TimingModel:
    """Create a timing model from configuration.

    Args:
        config: TimingConfig with distribution parameters
        seed: Optional random seed for reproducibility

    Returns:
        TimingModel instance

    Raises:
        ValueError: If distribution type is unknown
    """
    model_class = TIMING_MODEL_CLASSES.get(config.distribution)
    if model_class is None:
        available = ", ".join(d.value for d in TimingDistribution)
        raise ValueError(
            f"Unknown timing distribution: {config.distribution}. "
            f"Available: {available}"
        )

    return model_class(config, seed)


def timing_model_from_fingerprint(
    fingerprint: dict[str, Any],
    seed: int | None = None,
) -> TimingModel:
    """Create a timing model from a vendor fingerprint.

    Args:
        fingerprint: Vendor fingerprint dictionary with response_timing
        seed: Optional random seed

    Returns:
        TimingModel configured from fingerprint
    """
    if not fingerprint:
        logger.debug("No fingerprint provided, using default timing")
        return create_timing_model(DEFAULT_TIMING_CONFIG, seed)

    config = TimingConfig.from_fingerprint(fingerprint)
    return create_timing_model(config, seed)


def timing_model_from_flow(
    flow_context: Any,  # FlowContext type - avoid circular import
    seed: int | None = None,
) -> TimingModel:
    """Create a timing model from a flow context.

    Uses the destination device's fingerprint for timing parameters.

    Args:
        flow_context: FlowContext with destination device info
        seed: Optional random seed

    Returns:
        TimingModel configured from flow
    """
    # Get fingerprint from destination device (the responder)
    fingerprint = {}
    if hasattr(flow_context, "destination"):
        dest = flow_context.destination
        if hasattr(dest, "vendor_fingerprint"):
            fingerprint = dest.vendor_fingerprint or {}

    # Also check timing_model field on flow context
    if hasattr(flow_context, "timing_model") and flow_context.timing_model:
        # Flow-specific timing overrides fingerprint
        timing_dict = flow_context.timing_model
        config = TimingConfig(
            distribution=TimingDistribution(timing_dict.get("distribution", "gaussian")),
            min_ms=timing_dict.get("min_ms", 1.0),
            max_ms=timing_dict.get("max_ms", 50.0),
            mean_ms=timing_dict.get("mean_ms", 10.0),
            std_dev_ms=timing_dict.get("std_dev_ms", 5.0),
            outlier_probability=timing_dict.get("outlier_probability", 0.01),
            outlier_multiplier=timing_dict.get("outlier_multiplier", 3.0),
            timeout_probability=timing_dict.get("timeout_probability", 0.0),
        )
        return create_timing_model(config, seed)

    return timing_model_from_fingerprint(fingerprint, seed)


def timing_model_from_learned_samples(
    samples: list[float],
    timeout_probability: float = 0.0,
    seed: int | None = None,
) -> LearnedTimingModel:
    """Create a timing model from learned PCAP data.

    Args:
        samples: List of delay samples in milliseconds
        timeout_probability: Observed timeout rate
        seed: Optional random seed

    Returns:
        LearnedTimingModel configured with samples
    """
    config = TimingConfig.from_learned_data(samples, timeout_probability)
    return LearnedTimingModel(config, seed)


def create_default_timing_model(seed: int | None = None) -> TimingModel:
    """Create a default timing model.

    Uses gaussian distribution with reasonable defaults.

    Args:
        seed: Optional random seed

    Returns:
        Default GaussianTimingModel
    """
    return create_timing_model(DEFAULT_TIMING_CONFIG, seed)


def create_fast_device_timing_model(seed: int | None = None) -> TimingModel:
    """Create timing model for fast devices (modern PLCs).

    Args:
        seed: Optional random seed

    Returns:
        TimingModel with fast response characteristics
    """
    from .interface import FAST_DEVICE_TIMING_CONFIG

    return create_timing_model(FAST_DEVICE_TIMING_CONFIG, seed)


def create_slow_device_timing_model(seed: int | None = None) -> TimingModel:
    """Create timing model for slow devices (legacy RTUs).

    Args:
        seed: Optional random seed

    Returns:
        TimingModel with slow response characteristics
    """
    from .interface import SLOW_DEVICE_TIMING_CONFIG

    return create_timing_model(SLOW_DEVICE_TIMING_CONFIG, seed)


def create_noisy_network_timing_model(seed: int | None = None) -> TimingModel:
    """Create timing model for noisy/congested networks.

    Args:
        seed: Optional random seed

    Returns:
        TimingModel with noisy network characteristics
    """
    from .interface import NOISY_NETWORK_TIMING_CONFIG

    return create_timing_model(NOISY_NETWORK_TIMING_CONFIG, seed)


def get_timing_model_for_protocol(
    protocol: str,
    fingerprint: dict[str, Any] | None = None,
    seed: int | None = None,
) -> TimingModel:
    """Get a timing model optimized for a specific protocol.

    Some protocols have specific timing characteristics. This function
    selects appropriate defaults when fingerprint is not available.

    Args:
        protocol: Protocol name (modbus, ethernet_ip, etc.)
        fingerprint: Optional vendor fingerprint
        seed: Optional random seed

    Returns:
        TimingModel appropriate for the protocol
    """
    if fingerprint:
        return timing_model_from_fingerprint(fingerprint, seed)

    # Protocol-specific defaults when no fingerprint available
    protocol_defaults: dict[str, TimingConfig] = {
        "modbus": TimingConfig(
            distribution=TimingDistribution.GAUSSIAN,
            min_ms=1.0,
            max_ms=100.0,
            mean_ms=15.0,
            std_dev_ms=8.0,
        ),
        "ethernet_ip": TimingConfig(
            distribution=TimingDistribution.GAUSSIAN,
            min_ms=0.5,
            max_ms=50.0,
            mean_ms=5.0,
            std_dev_ms=3.0,
        ),
        "profinet": TimingConfig(
            distribution=TimingDistribution.GAUSSIAN,
            min_ms=0.1,
            max_ms=10.0,
            mean_ms=1.0,
            std_dev_ms=0.5,
        ),
        "s7": TimingConfig(
            distribution=TimingDistribution.GAUSSIAN,
            min_ms=1.0,
            max_ms=100.0,
            mean_ms=10.0,
            std_dev_ms=5.0,
        ),
        "snmp": TimingConfig(
            distribution=TimingDistribution.GAUSSIAN,
            min_ms=5.0,
            max_ms=500.0,
            mean_ms=50.0,
            std_dev_ms=30.0,
        ),
        "bacnet": TimingConfig(
            distribution=TimingDistribution.GAUSSIAN,
            min_ms=10.0,
            max_ms=300.0,
            mean_ms=50.0,
            std_dev_ms=25.0,
        ),
        "dnp3": TimingConfig(
            distribution=TimingDistribution.LOGNORMAL,
            min_ms=10.0,
            max_ms=500.0,
            mean_ms=100.0,
            std_dev_ms=50.0,
        ),
        "iec_104": TimingConfig(
            distribution=TimingDistribution.LOGNORMAL,
            min_ms=10.0,
            max_ms=500.0,
            mean_ms=100.0,
            std_dev_ms=50.0,
        ),
        "opc_ua": TimingConfig(
            distribution=TimingDistribution.GAUSSIAN,
            min_ms=1.0,
            max_ms=100.0,
            mean_ms=10.0,
            std_dev_ms=5.0,
        ),
    }

    config = protocol_defaults.get(protocol.lower(), DEFAULT_TIMING_CONFIG)
    return create_timing_model(config, seed)
