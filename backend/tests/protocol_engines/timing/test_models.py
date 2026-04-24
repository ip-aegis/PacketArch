# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for Unified Timing Model system."""

import pytest
import numpy as np

from app.protocol_engines.timing import (
    DEFAULT_TIMING_CONFIG,
    FAST_DEVICE_TIMING_CONFIG,
    SLOW_DEVICE_TIMING_CONFIG,
    ExponentialTimingModel,
    GammaTimingModel,
    GaussianTimingModel,
    LearnedTimingModel,
    LognormalTimingModel,
    TimingConfig,
    TimingDistribution,
    TimingSample,
    UniformTimingModel,
    create_default_timing_model,
    create_timing_model,
    get_timing_model_for_protocol,
    timing_model_from_fingerprint,
    timing_model_from_learned_samples,
)


class TestTimingConfig:
    """Tests for TimingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TimingConfig()
        assert config.distribution == TimingDistribution.GAUSSIAN
        assert config.min_ms == 1.0
        assert config.max_ms == 50.0
        assert config.mean_ms == 10.0
        assert config.std_dev_ms == 5.0
        assert config.outlier_probability == 0.01
        assert config.outlier_multiplier == 3.0
        assert config.timeout_probability == 0.0

    def test_from_fingerprint(self):
        """Test creating config from fingerprint."""
        fingerprint = {
            "response_timing": {
                "distribution": "lognormal",
                "min_ms": 2.0,
                "max_ms": 100.0,
                "mean_ms": 20.0,
                "std_dev_ms": 10.0,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
            },
        }

        config = TimingConfig.from_fingerprint(fingerprint)

        assert config.distribution == TimingDistribution.LOGNORMAL
        assert config.min_ms == 2.0
        assert config.max_ms == 100.0
        assert config.mean_ms == 20.0
        assert config.timeout_probability == 0.001

    def test_from_learned_data(self):
        """Test creating config from learned samples."""
        samples = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        config = TimingConfig.from_learned_data(samples, timeout_probability=0.01)

        assert config.distribution == TimingDistribution.LEARNED
        assert config.min_ms == 5.0
        assert config.max_ms == 10.0
        assert config.timeout_probability == 0.01
        assert len(config.learned_samples) == 6

    def test_frozen_immutability(self):
        """Test that config is immutable."""
        config = TimingConfig()
        with pytest.raises(Exception):  # FrozenInstanceError
            config.mean_ms = 100.0


class TestGaussianTimingModel:
    """Tests for GaussianTimingModel."""

    def test_sample_returns_timing_sample(self):
        """Test that sample returns TimingSample."""
        model = GaussianTimingModel(DEFAULT_TIMING_CONFIG, seed=42)
        sample = model.sample()

        assert isinstance(sample, TimingSample)
        assert sample.delay_ms >= 0

    def test_sample_within_bounds(self):
        """Test samples are within configured bounds."""
        config = TimingConfig(min_ms=5.0, max_ms=20.0, mean_ms=10.0, std_dev_ms=2.0)
        model = GaussianTimingModel(config, seed=42)

        # Generate many samples
        samples = [model.sample() for _ in range(100)]
        delays = [s.delay_ms for s in samples if not s.is_timeout]

        # Most should be within bounds (allowing outliers)
        normal_delays = [d for d in delays if d <= 20.0]
        assert len(normal_delays) >= 95  # At least 95% in bounds

    def test_seed_reproducibility(self):
        """Test that same seed produces same results."""
        config = TimingConfig(outlier_probability=0, timeout_probability=0)
        model1 = GaussianTimingModel(config, seed=42)
        model2 = GaussianTimingModel(config, seed=42)

        samples1 = [model1.sample().delay_ms for _ in range(10)]
        samples2 = [model2.sample().delay_ms for _ in range(10)]

        assert samples1 == samples2

    def test_timeout_probability(self):
        """Test timeout probability."""
        config = TimingConfig(timeout_probability=1.0)  # Always timeout
        model = GaussianTimingModel(config, seed=42)

        sample = model.sample()
        assert sample.is_timeout is True
        assert sample.delay_ms == 0


class TestLognormalTimingModel:
    """Tests for LognormalTimingModel."""

    def test_sample_positive_values(self):
        """Test that lognormal produces positive values."""
        config = TimingConfig(distribution=TimingDistribution.LOGNORMAL)
        model = LognormalTimingModel(config, seed=42)

        samples = [model.sample() for _ in range(100)]
        delays = [s.delay_ms for s in samples if not s.is_timeout]

        assert all(d > 0 for d in delays)

    def test_right_skewed_distribution(self):
        """Test that distribution is right-skewed (median < mean)."""
        config = TimingConfig(
            distribution=TimingDistribution.LOGNORMAL,
            min_ms=1.0,
            max_ms=500.0,  # Well above mean so right tail isn't clipped
            mean_ms=50.0,
            std_dev_ms=30.0,
            outlier_probability=0,
            timeout_probability=0,
        )
        model = LognormalTimingModel(config, seed=42)

        samples = [model.sample().delay_ms for _ in range(10000)]
        median = np.median(samples)
        mean = np.mean(samples)

        # For lognormal with unclipped right tail, median < mean
        assert median < mean


class TestUniformTimingModel:
    """Tests for UniformTimingModel."""

    def test_uniform_distribution(self):
        """Test uniform distribution coverage."""
        config = TimingConfig(
            distribution=TimingDistribution.UNIFORM,
            min_ms=10.0,
            max_ms=20.0,
            outlier_probability=0,
            timeout_probability=0,
        )
        model = UniformTimingModel(config, seed=42)

        samples = [model.sample().delay_ms for _ in range(1000)]

        assert min(samples) >= 10.0
        assert max(samples) <= 20.0
        # Check coverage - should cover most of the range
        assert max(samples) - min(samples) > 8.0  # Cover at least 80% of range


class TestExponentialTimingModel:
    """Tests for ExponentialTimingModel."""

    def test_exponential_positive(self):
        """Test exponential produces positive values."""
        config = TimingConfig(distribution=TimingDistribution.EXPONENTIAL)
        model = ExponentialTimingModel(config, seed=42)

        samples = [model.sample() for _ in range(100)]
        delays = [s.delay_ms for s in samples if not s.is_timeout]

        assert all(d > 0 for d in delays)


class TestGammaTimingModel:
    """Tests for GammaTimingModel."""

    def test_gamma_positive(self):
        """Test gamma produces positive values."""
        config = TimingConfig(distribution=TimingDistribution.GAMMA)
        model = GammaTimingModel(config, seed=42)

        samples = [model.sample() for _ in range(100)]
        delays = [s.delay_ms for s in samples if not s.is_timeout]

        assert all(d > 0 for d in delays)


class TestLearnedTimingModel:
    """Tests for LearnedTimingModel."""

    def test_cycles_through_samples(self):
        """Test that model cycles through learned samples."""
        samples = [10.0, 20.0, 30.0]
        config = TimingConfig.from_learned_data(samples)
        model = LearnedTimingModel(config, seed=42)

        # First three samples should be close to original (with jitter)
        results = [model.sample() for _ in range(3)]

        # Check they're approximately the original values (within jitter)
        for i, result in enumerate(results):
            assert abs(result.delay_ms - samples[i]) < samples[i] * 0.1  # 10% jitter

    def test_add_samples(self):
        """Test adding more samples."""
        samples = [10.0, 20.0]
        config = TimingConfig.from_learned_data(samples)
        model = LearnedTimingModel(config, seed=42)

        model.add_samples([30.0, 40.0])

        assert len(model._samples) == 4


class TestFactoryFunctions:
    """Tests for timing model factory functions."""

    def test_create_timing_model_gaussian(self):
        """Test creating Gaussian model."""
        config = TimingConfig(distribution=TimingDistribution.GAUSSIAN)
        model = create_timing_model(config)

        assert isinstance(model, GaussianTimingModel)

    def test_create_timing_model_lognormal(self):
        """Test creating Lognormal model."""
        config = TimingConfig(distribution=TimingDistribution.LOGNORMAL)
        model = create_timing_model(config)

        assert isinstance(model, LognormalTimingModel)

    def test_timing_model_from_fingerprint(self):
        """Test creating model from fingerprint."""
        fingerprint = {
            "response_timing": {
                "distribution": "gaussian",
                "mean_ms": 15.0,
            }
        }
        model = timing_model_from_fingerprint(fingerprint)

        assert isinstance(model, GaussianTimingModel)
        assert model.config.mean_ms == 15.0

    def test_timing_model_from_empty_fingerprint(self):
        """Test creating model from empty fingerprint uses defaults."""
        model = timing_model_from_fingerprint({})

        assert isinstance(model, GaussianTimingModel)
        assert model.config == DEFAULT_TIMING_CONFIG

    def test_timing_model_from_learned_samples(self):
        """Test creating model from learned samples."""
        samples = [5.0, 10.0, 15.0, 20.0]
        model = timing_model_from_learned_samples(samples)

        assert isinstance(model, LearnedTimingModel)

    def test_create_default_timing_model(self):
        """Test creating default model."""
        model = create_default_timing_model()

        assert isinstance(model, GaussianTimingModel)
        assert model.config == DEFAULT_TIMING_CONFIG

    def test_get_timing_model_for_protocol(self):
        """Test getting protocol-specific model."""
        modbus_model = get_timing_model_for_protocol("modbus")
        profinet_model = get_timing_model_for_protocol("profinet")

        assert isinstance(modbus_model, GaussianTimingModel)
        assert isinstance(profinet_model, GaussianTimingModel)

        # PROFINET should be faster
        assert profinet_model.config.mean_ms < modbus_model.config.mean_ms


class TestTimingSampleMetadata:
    """Tests for TimingSample metadata."""

    def test_outlier_detection(self):
        """Test outlier metadata."""
        config = TimingConfig(outlier_probability=1.0)  # Always outlier
        model = GaussianTimingModel(config, seed=42)

        sample = model.sample()

        assert sample.is_outlier is True

    def test_no_outlier(self):
        """Test non-outlier samples."""
        config = TimingConfig(outlier_probability=0)
        model = GaussianTimingModel(config, seed=42)

        samples = [model.sample() for _ in range(10)]

        assert all(not s.is_outlier for s in samples)
