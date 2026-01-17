"""AI-powered timing models using learned distributions from PCAP analysis.

This module provides timing models that sample from statistical distributions
learned from real traffic captures, enabling hyper-realistic traffic generation.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from app.protocol_engines.jitter import JitterModel

logger = logging.getLogger(__name__)


@dataclass
class DistributionParams:
    """Parameters for a statistical distribution."""

    distribution_type: str  # gaussian, lognormal, exponential, gamma, uniform
    params: dict[str, float] = field(default_factory=dict)
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    std_dev: float | None = None


class LearnedJitterModel(JitterModel):
    """Jitter model that samples from learned statistical distributions.

    This model uses distribution parameters extracted from PCAP analysis
    to generate timing values that match real traffic patterns.
    """

    def __init__(
        self,
        distribution_params: DistributionParams,
        outlier_probability: float = 0.01,
        outlier_multiplier: float = 3.0,
        seed: int | None = None,
    ):
        """Initialize learned jitter model.

        Args:
            distribution_params: Learned distribution parameters
            outlier_probability: Probability of generating an outlier
            outlier_multiplier: Multiplier for outlier values
            seed: Optional random seed for reproducibility
        """
        self.params = distribution_params
        self.outlier_probability = outlier_probability
        self.outlier_multiplier = outlier_multiplier
        self._rng = np.random.default_rng(seed)

        # Build scipy distribution object
        self._dist = self._build_distribution()

    def _build_distribution(self) -> Any:
        """Build scipy distribution from parameters.

        Returns:
            Frozen scipy distribution or None
        """
        dist_type = self.params.distribution_type.lower()
        p = self.params.params

        try:
            if dist_type == "gaussian":
                mean = p.get("mean", self.params.mean_value or 10.0)
                std = p.get("std", self.params.std_dev or 2.0)
                return stats.norm(loc=mean, scale=std)

            elif dist_type == "lognormal":
                s = p.get("s", 0.5)
                loc = p.get("loc", 0)
                scale = p.get("scale", self.params.mean_value or 10.0)
                return stats.lognorm(s=s, loc=loc, scale=scale)

            elif dist_type == "exponential":
                loc = p.get("loc", 0)
                scale = p.get("scale", self.params.mean_value or 10.0)
                return stats.expon(loc=loc, scale=scale)

            elif dist_type == "gamma":
                a = p.get("a", 2.0)
                loc = p.get("loc", 0)
                scale = p.get("scale", self.params.mean_value or 5.0)
                return stats.gamma(a=a, loc=loc, scale=scale)

            elif dist_type == "uniform":
                min_val = self.params.min_value or 1.0
                max_val = self.params.max_value or 20.0
                return stats.uniform(loc=min_val, scale=max_val - min_val)

            else:
                # Fallback to Gaussian
                logger.warning(f"Unknown distribution {dist_type}, using Gaussian")
                mean = self.params.mean_value or 10.0
                std = self.params.std_dev or 2.0
                return stats.norm(loc=mean, scale=std)

        except Exception as e:
            logger.error(f"Failed to build distribution: {e}")
            return None

    def sample(self) -> float:
        """Sample a single value from the learned distribution.

        Returns:
            Sampled timing value in milliseconds
        """
        if self._dist is None:
            return self.params.mean_value or 10.0

        # Check for outlier
        is_outlier = self._rng.random() < self.outlier_probability

        # Sample from distribution
        value = float(self._dist.rvs(random_state=self._rng))

        # Apply outlier multiplier
        if is_outlier:
            value *= self.outlier_multiplier

        # Clamp to min/max if specified
        if self.params.min_value is not None:
            min_bound = self.params.min_value
            if is_outlier:
                min_bound *= 0.5  # Allow lower outliers
            value = max(min_bound, value)

        if self.params.max_value is not None:
            max_bound = self.params.max_value
            if is_outlier:
                max_bound *= self.outlier_multiplier
            value = min(max_bound, value)

        return value

    def apply(self, base_time: float) -> float:
        """Apply learned jitter to base time.

        Note: For learned timing, we typically replace rather than add to base_time,
        since the learned distribution already captures the full timing characteristic.

        Args:
            base_time: Base time value (used as reference/fallback)

        Returns:
            Sampled time value
        """
        return self.sample()


class ContextAwareTimingModel:
    """Timing model that considers device state and cross-flow dependencies.

    This model provides context-aware timing that can:
    - Vary based on device load/state
    - Account for cross-flow dependencies
    - Apply vendor-specific personality traits
    """

    def __init__(
        self,
        base_model: LearnedJitterModel,
        device_personality: "DevicePersonality | None" = None,
    ):
        """Initialize context-aware timing model.

        Args:
            base_model: Base learned jitter model
            device_personality: Optional device personality traits
        """
        self.base_model = base_model
        self.personality = device_personality
        self._rng = np.random.default_rng()

        # State tracking
        self._load_factor = 1.0
        self._consecutive_errors = 0
        self._last_response_time = 0.0

    def set_load_factor(self, load: float) -> None:
        """Set current device load factor (0.0 - 1.0+).

        Higher load increases response times.
        """
        self._load_factor = max(0.1, load)

    def record_error(self) -> None:
        """Record an error occurrence, affecting subsequent timing."""
        self._consecutive_errors += 1

    def record_success(self) -> None:
        """Record a successful response, resetting error state."""
        self._consecutive_errors = 0

    def get_timing(self, context: dict[str, Any] | None = None) -> float:
        """Get a context-aware timing value.

        Args:
            context: Optional context dictionary with state information

        Returns:
            Timing value in milliseconds
        """
        # Base sample from learned distribution
        base_time = self.base_model.sample()

        # Apply load factor
        if self._load_factor > 1.0:
            # Under heavy load, responses slow down
            load_multiplier = 1.0 + (self._load_factor - 1.0) * 0.5
            base_time *= load_multiplier

        # Apply error recovery penalty
        if self._consecutive_errors > 0:
            # Each consecutive error adds some delay
            error_penalty = min(1.5, 1.0 + self._consecutive_errors * 0.1)
            base_time *= error_penalty

        # Apply personality traits
        if self.personality:
            base_time = self.personality.apply_timing_trait(base_time)

        self._last_response_time = base_time
        return base_time


@dataclass
class DevicePersonality:
    """Vendor-specific behavioral characteristics for a device.

    This captures subtle timing and behavioral differences between vendors
    that make traffic more realistic.
    """

    vendor: str
    model: str | None = None

    # Timing personality
    response_consistency: float = 0.9  # 0-1, higher = more consistent
    load_sensitivity: float = 0.5  # 0-1, higher = more affected by load
    warmup_factor: float = 1.0  # Initial responses may be slower

    # Behavioral personality
    eager_responder: bool = False  # Responds as fast as possible
    batches_responses: bool = False  # May batch multiple responses

    # Internal state
    _response_count: int = field(default=0, repr=False)
    _rng: Any = field(default=None, repr=False)

    def __post_init__(self):
        self._rng = np.random.default_rng()

    def apply_timing_trait(self, base_time: float) -> float:
        """Apply personality-based timing modifications.

        Args:
            base_time: Base timing value

        Returns:
            Modified timing value
        """
        self._response_count += 1

        # Apply consistency - more consistent devices have less variation
        if self.response_consistency < 1.0:
            variation = 1.0 - self.response_consistency
            jitter = self._rng.normal(0, variation * base_time * 0.2)
            base_time += jitter

        # Apply warmup factor for initial responses
        if self._response_count < 10 and self.warmup_factor > 1.0:
            warmup = self.warmup_factor - (self._response_count / 10) * (self.warmup_factor - 1.0)
            base_time *= warmup

        # Eager responders are faster but with minimum bound
        if self.eager_responder:
            base_time *= 0.7
            base_time = max(0.5, base_time)

        return max(0.1, base_time)


# Pre-defined device personalities for major vendors
VENDOR_PERSONALITIES = {
    "rockwell": DevicePersonality(
        vendor="Rockwell",
        response_consistency=0.85,
        load_sensitivity=0.6,
        warmup_factor=1.2,
        eager_responder=False,
    ),
    "siemens": DevicePersonality(
        vendor="Siemens",
        response_consistency=0.95,
        load_sensitivity=0.3,
        warmup_factor=1.1,
        eager_responder=True,
    ),
    "schneider": DevicePersonality(
        vendor="Schneider",
        response_consistency=0.88,
        load_sensitivity=0.5,
        warmup_factor=1.15,
        eager_responder=False,
    ),
    "abb": DevicePersonality(
        vendor="ABB",
        response_consistency=0.92,
        load_sensitivity=0.4,
        warmup_factor=1.1,
        eager_responder=False,
    ),
    "honeywell": DevicePersonality(
        vendor="Honeywell",
        response_consistency=0.87,
        load_sensitivity=0.55,
        warmup_factor=1.25,
        eager_responder=False,
    ),
    "emerson": DevicePersonality(
        vendor="Emerson",
        response_consistency=0.90,
        load_sensitivity=0.45,
        warmup_factor=1.15,
        eager_responder=False,
    ),
    "ge": DevicePersonality(
        vendor="GE",
        response_consistency=0.89,
        load_sensitivity=0.5,
        warmup_factor=1.2,
        eager_responder=False,
    ),
}


def get_device_personality(vendor: str) -> DevicePersonality:
    """Get device personality for a vendor.

    Args:
        vendor: Vendor name (case-insensitive)

    Returns:
        DevicePersonality for the vendor
    """
    vendor_key = vendor.lower()
    if vendor_key in VENDOR_PERSONALITIES:
        # Return a copy to avoid state sharing
        template = VENDOR_PERSONALITIES[vendor_key]
        return DevicePersonality(
            vendor=template.vendor,
            model=template.model,
            response_consistency=template.response_consistency,
            load_sensitivity=template.load_sensitivity,
            warmup_factor=template.warmup_factor,
            eager_responder=template.eager_responder,
            batches_responses=template.batches_responses,
        )

    # Default personality
    return DevicePersonality(vendor=vendor)


def create_learned_jitter_model_from_pattern(pattern: dict[str, Any]) -> LearnedJitterModel:
    """Create a LearnedJitterModel from a learned pattern dictionary.

    Args:
        pattern: Pattern dictionary from database (LearnedPattern attributes)

    Returns:
        Configured LearnedJitterModel
    """
    dist_params = DistributionParams(
        distribution_type=pattern.get("distribution_type", "gaussian"),
        params=pattern.get("timing_params", {}),
        min_value=pattern.get("min_value"),
        max_value=pattern.get("max_value"),
        mean_value=pattern.get("mean_value"),
        std_dev=pattern.get("std_dev"),
    )

    return LearnedJitterModel(
        distribution_params=dist_params,
        outlier_probability=0.01,
        outlier_multiplier=3.0,
    )


class LearnedTimingService:
    """Service for managing learned timing models across flows.

    This service loads learned patterns from the database and provides
    appropriate timing models for each flow.
    """

    def __init__(self):
        """Initialize the learned timing service."""
        self._models: dict[str, LearnedJitterModel] = {}
        self._context_models: dict[str, ContextAwareTimingModel] = {}

    async def load_patterns_for_protocol(
        self,
        protocol: str,
        db_session: Any,
    ) -> list[dict[str, Any]]:
        """Load learned timing patterns for a protocol from the database.

        Args:
            protocol: Protocol name (e.g., 'modbus_tcp')
            db_session: Database session

        Returns:
            List of pattern dictionaries
        """
        from sqlalchemy import select
        from app.models.learned_pattern import LearnedPattern, PatternType

        query = select(LearnedPattern).where(
            LearnedPattern.protocol == protocol,
            LearnedPattern.pattern_type == PatternType.TIMING,
            LearnedPattern.is_active == True,
        ).order_by(LearnedPattern.confidence.desc())

        result = await db_session.execute(query)
        patterns = result.scalars().all()

        return [
            {
                "id": str(p.id),
                "name": p.name,
                "protocol": p.protocol,
                "source_ip": p.source_ip,
                "destination_ip": p.destination_ip,
                "distribution_type": p.distribution_type.value if p.distribution_type else "gaussian",
                "timing_params": p.timing_params or {},
                "min_value": p.min_value,
                "max_value": p.max_value,
                "mean_value": p.mean_value,
                "std_dev": p.std_dev,
                "confidence": p.confidence,
            }
            for p in patterns
        ]

    def get_model_for_flow(
        self,
        flow_id: str,
        protocol: str,
        patterns: list[dict[str, Any]],
        vendor: str | None = None,
    ) -> ContextAwareTimingModel:
        """Get or create a timing model for a flow.

        Args:
            flow_id: Flow identifier
            protocol: Protocol name
            patterns: Available learned patterns
            vendor: Optional vendor name for personality

        Returns:
            ContextAwareTimingModel for the flow
        """
        if flow_id in self._context_models:
            return self._context_models[flow_id]

        # Find best matching pattern
        best_pattern = None
        best_confidence = 0

        for pattern in patterns:
            if pattern.get("protocol") == protocol:
                confidence = pattern.get("confidence", 0)
                if confidence > best_confidence:
                    best_pattern = pattern
                    best_confidence = confidence

        # Create learned jitter model
        if best_pattern:
            base_model = create_learned_jitter_model_from_pattern(best_pattern)
        else:
            # Fallback to default parameters
            base_model = LearnedJitterModel(
                DistributionParams(
                    distribution_type="gaussian",
                    mean_value=10.0,
                    std_dev=2.0,
                    min_value=1.0,
                    max_value=50.0,
                )
            )

        # Get device personality
        personality = get_device_personality(vendor) if vendor else None

        # Create context-aware model
        context_model = ContextAwareTimingModel(
            base_model=base_model,
            device_personality=personality,
        )

        self._context_models[flow_id] = context_model
        return context_model

    def clear_models(self) -> None:
        """Clear all cached models."""
        self._models.clear()
        self._context_models.clear()
