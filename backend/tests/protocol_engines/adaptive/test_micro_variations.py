# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for MicroVariationEngine — timing drift, retransmissions, connection resets."""

import time


from app.protocol_engines.adaptive.micro_variations import (
    MicroVariationEngine,
    VENDOR_TRAITS,
)
from app.protocol_engines.adaptive.types import MicroVariationConfig


class TestMicroVariationEngineDefaults:
    """Test engine initialization and default behavior."""

    def test_default_config_enables_all_features(self):
        config = MicroVariationConfig()
        assert config.timing_drift_enabled is True
        assert config.retransmit_enabled is True
        assert config.connection_reset_enabled is True
        assert config.vendor_personality_enabled is True

    def test_unregistered_flow_returns_base_interval(self):
        engine = MicroVariationEngine(MicroVariationConfig())
        result = engine.adjust_poll_interval("unknown-flow", 1000.0)
        assert result == 1000.0

    def test_disabled_drift_returns_base_interval(self):
        config = MicroVariationConfig(timing_drift_enabled=False)
        engine = MicroVariationEngine(config)
        engine.register_flow("f1", "siemens", 1000.0)
        for _ in range(100):
            assert engine.adjust_poll_interval("f1", 1000.0) == 1000.0


class TestTimingDrift:
    """Test that drift stays bounded and varies between calls."""

    def test_drift_stays_within_bounds(self):
        config = MicroVariationConfig(timing_drift_max_percent=5.0)
        engine = MicroVariationEngine(config)
        engine.register_flow("f1", "rockwell", 1000.0)

        min_val, max_val = float("inf"), float("-inf")
        for _ in range(10_000):
            val = engine.adjust_poll_interval("f1", 1000.0)
            min_val = min(min_val, val)
            max_val = max(max_val, val)

        # After warmup (10 polls), drift should be within ±5% of base
        # Warmup can push up to ~1.2x, so upper bound is wider
        assert min_val >= 1000.0 * 0.93  # some slack for combined warmup + drift
        assert max_val <= 1000.0 * 1.25  # warmup factor can push early values higher

    def test_drift_varies_across_polls(self):
        engine = MicroVariationEngine(MicroVariationConfig())
        engine.register_flow("f1", "siemens", 1000.0)

        # After warmup, intervals should not all be identical
        # Skip first 15 polls (warmup period)
        for _ in range(15):
            engine.adjust_poll_interval("f1", 1000.0)

        values = [engine.adjust_poll_interval("f1", 1000.0) for _ in range(100)]
        unique = len(set(values))
        # Should have significant variation, not all the same
        assert unique > 50, f"Expected variety, got only {unique} unique values out of 100"

    def test_vendor_personality_affects_variation(self):
        """Siemens (consistency=0.95) should vary less than Rockwell (0.85)."""
        config = MicroVariationConfig(timing_drift_max_percent=5.0)

        engine_siemens = MicroVariationEngine(config)
        engine_siemens.register_flow("f1", "siemens", 1000.0)

        engine_rockwell = MicroVariationEngine(config)
        engine_rockwell.register_flow("f1", "rockwell", 1000.0)

        # Run 5000 iterations past warmup
        for _ in range(15):
            engine_siemens.adjust_poll_interval("f1", 1000.0)
            engine_rockwell.adjust_poll_interval("f1", 1000.0)

        siemens_vals = [engine_siemens.adjust_poll_interval("f1", 1000.0) for _ in range(5000)]
        rockwell_vals = [engine_rockwell.adjust_poll_interval("f1", 1000.0) for _ in range(5000)]

        siemens_std = _stdev(siemens_vals)
        rockwell_std = _stdev(rockwell_vals)

        # Rockwell should have higher standard deviation (less consistent)
        assert rockwell_std > siemens_std, (
            f"Expected Rockwell ({rockwell_std:.4f}) > Siemens ({siemens_std:.4f})"
        )

    def test_warmup_factor_slows_initial_polls(self):
        config = MicroVariationConfig(timing_drift_max_percent=0.01)  # near-zero drift
        engine = MicroVariationEngine(config)
        engine.register_flow("f1", "rockwell", 1000.0)  # warmup_factor=1.2

        # First poll should be slower due to warmup
        first = engine.adjust_poll_interval("f1", 1000.0)
        assert first > 1050, f"First poll should be >1050ms due to warmup, got {first:.1f}"

        # Skip through warmup
        for _ in range(20):
            engine.adjust_poll_interval("f1", 1000.0)

        # Post-warmup should be near base
        post_warmup = engine.adjust_poll_interval("f1", 1000.0)
        assert 950 < post_warmup < 1050, f"Post-warmup should be near 1000ms, got {post_warmup:.1f}"

    def test_unknown_vendor_uses_default_traits(self):
        engine = MicroVariationEngine(MicroVariationConfig())
        engine.register_flow("f1", "unknown_corp", 1000.0)

        # Should still work — uses default personality
        vals = [engine.adjust_poll_interval("f1", 1000.0) for _ in range(50)]
        assert len(set(vals)) > 10  # has variation

    def test_none_vendor_uses_default_traits(self):
        engine = MicroVariationEngine(MicroVariationConfig())
        engine.register_flow("f1", None, 1000.0)
        val = engine.adjust_poll_interval("f1", 1000.0)
        assert val > 0

    def test_vendor_prefix_matching(self):
        """Vendor 'Siemens AG' should match 'siemens' trait."""
        engine = MicroVariationEngine(MicroVariationConfig())
        engine.register_flow("f1", "Siemens AG", 1000.0)
        state = engine._flow_states["f1"]
        assert state.traits["consistency"] == VENDOR_TRAITS["siemens"]["consistency"]

    def test_minimum_interval_floor(self):
        """adjust_poll_interval should never return below 1.0ms."""
        config = MicroVariationConfig(timing_drift_max_percent=99.0)  # extreme
        engine = MicroVariationEngine(config)
        engine.register_flow("f1", None, 0.5)

        for _ in range(100):
            val = engine.adjust_poll_interval("f1", 0.5)
            assert val >= 1.0


class TestRetransmissions:
    """Test retransmission probability."""

    def test_retransmit_disabled_always_false(self):
        config = MicroVariationConfig(retransmit_enabled=False)
        engine = MicroVariationEngine(config)
        engine.register_flow("f1", None, 1000.0)
        assert all(not engine.should_retransmit("f1") for _ in range(1000))

    def test_retransmit_rate_approximately_correct(self):
        config = MicroVariationConfig(retransmit_probability=0.01)  # 1% for faster test
        engine = MicroVariationEngine(config)
        engine.register_flow("f1", None, 1000.0)

        count = sum(1 for _ in range(100_000) if engine.should_retransmit("f1"))
        # 1% of 100K = ~1000 ± some margin
        assert 700 < count < 1400, f"Expected ~1000 retransmits, got {count}"

    def test_retransmit_counter_tracks(self):
        config = MicroVariationConfig(retransmit_probability=1.0)  # always
        engine = MicroVariationEngine(config)
        engine.register_flow("f1", None, 1000.0)

        for _ in range(10):
            engine.should_retransmit("f1")

        stats = engine.get_stats()
        assert stats["retransmits"] == 10


class TestConnectionResets:
    """Test periodic connection reset triggers."""

    def test_reset_disabled_always_false(self):
        config = MicroVariationConfig(connection_reset_enabled=False)
        engine = MicroVariationEngine(config)
        engine.register_flow("f1", None, 1000.0)
        assert not engine.should_connection_reset("f1", time.monotonic() + 99999)

    def test_reset_triggers_after_interval(self):
        config = MicroVariationConfig(reset_interval_range_s=(1.0, 1.0))
        engine = MicroVariationEngine(config)
        t0 = time.monotonic()
        engine.register_flow("f1", None, 1000.0)

        # Should not trigger immediately
        assert not engine.should_connection_reset("f1", t0 + 0.5)

        # Should trigger after 1 second
        assert engine.should_connection_reset("f1", t0 + 1.5)

        # Should reset counter and not trigger again immediately
        assert not engine.should_connection_reset("f1", t0 + 1.6)

        # Should trigger again after another interval
        assert engine.should_connection_reset("f1", t0 + 3.0)

    def test_reset_counter_tracks(self):
        config = MicroVariationConfig(reset_interval_range_s=(0.1, 0.1))
        engine = MicroVariationEngine(config)
        t0 = time.monotonic()
        engine.register_flow("f1", None, 1000.0)

        engine.should_connection_reset("f1", t0 + 0.2)
        engine.should_connection_reset("f1", t0 + 0.4)

        stats = engine.get_stats()
        assert stats["connection_resets"] == 2

    def test_unregistered_flow_no_reset(self):
        engine = MicroVariationEngine(MicroVariationConfig())
        assert not engine.should_connection_reset("unknown", time.monotonic() + 99999)


class TestStats:
    """Test stats reporting."""

    def test_stats_initial_zeroes(self):
        engine = MicroVariationEngine(MicroVariationConfig())
        stats = engine.get_stats()
        assert stats == {"drift_adjustments": 0, "retransmits": 0, "connection_resets": 0}

    def test_drift_adjustments_counted(self):
        engine = MicroVariationEngine(MicroVariationConfig())
        engine.register_flow("f1", None, 1000.0)
        for _ in range(50):
            engine.adjust_poll_interval("f1", 1000.0)
        assert engine.get_stats()["drift_adjustments"] == 50


def _stdev(values: list[float]) -> float:
    """Calculate sample standard deviation."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return var ** 0.5
