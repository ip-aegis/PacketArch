# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for AdaptiveController — composition of micro, schedule, and directives."""

import time
from unittest.mock import patch

import pytest

from app.protocol_engines.adaptive.controller import AdaptiveController
from app.protocol_engines.adaptive.types import (
    AdaptiveConfig,
    MicroVariationConfig,
    ScheduleConfig,
    SchedulePhase,
    DIRECTIVE_ADJUST_PROTOCOL_RATE,
    DIRECTIVE_ADJUST_FLOW_RATE,
    DIRECTIVE_SET_SCHEDULE_PHASE,
    DIRECTIVE_RESET,
)


def _micro_only_config(**overrides) -> AdaptiveConfig:
    micro = MicroVariationConfig(**overrides)
    return AdaptiveConfig(enabled=True, micro=micro, schedule=ScheduleConfig())


class TestControllerBasics:
    """Test basic controller behavior."""

    def test_disabled_returns_base_interval(self):
        config = AdaptiveConfig(enabled=False)
        ctrl = AdaptiveController(config, total_flows=1)
        ctrl.register_flow("f1", "siemens", 1000.0)
        assert ctrl.adjust_next_poll("f1", 1000.0) == 1000.0

    def test_enabled_varies_interval(self):
        ctrl = AdaptiveController(_micro_only_config(), total_flows=1)
        ctrl.register_flow("f1", "rockwell", 1000.0, protocol="modbus_tcp")

        values = set()
        for _ in range(100):
            values.add(ctrl.adjust_next_poll("f1", 1000.0))
        # Should not all be identical
        assert len(values) > 10

    def test_minimum_interval_floor_at_50ms(self):
        ctrl = AdaptiveController(_micro_only_config(), total_flows=1)
        ctrl.register_flow("f1", None, 10.0)
        for _ in range(100):
            val = ctrl.adjust_next_poll("f1", 10.0)
            assert val >= 50.0, f"Expected >= 50.0ms, got {val}"

    def test_register_flow_stores_protocol(self):
        ctrl = AdaptiveController(_micro_only_config(), total_flows=1)
        ctrl.register_flow("f1", "siemens", 1000.0, protocol="modbus_tcp")
        assert ctrl._flow_protocols["f1"] == "modbus_tcp"

    def test_state_snapshot_has_expected_keys(self):
        ctrl = AdaptiveController(_micro_only_config(), total_flows=1)
        ctrl.register_flow("f1", "siemens", 1000.0)
        ctrl.adjust_next_poll("f1", 1000.0)

        snap = ctrl.get_state_snapshot()
        assert "enabled" in snap
        assert "current_phase" in snap
        assert "rate_multiplier" in snap
        assert "active_directives" in snap
        assert "micro_stats" in snap
        assert "drift_adjustments" in snap["micro_stats"]


class TestRetransmitAndReset:
    """Test passthrough to micro-variation engine."""

    def test_disabled_no_retransmit(self):
        config = AdaptiveConfig(enabled=False)
        ctrl = AdaptiveController(config)
        assert not ctrl.should_retransmit("f1")

    def test_disabled_no_reset(self):
        config = AdaptiveConfig(enabled=False)
        ctrl = AdaptiveController(config)
        assert not ctrl.should_connection_reset("f1")

    def test_retransmit_passthrough(self):
        config = _micro_only_config(retransmit_probability=1.0)
        ctrl = AdaptiveController(config, total_flows=1)
        ctrl.register_flow("f1", None, 1000.0)
        assert ctrl.should_retransmit("f1")

    def test_connection_reset_passthrough(self):
        config = _micro_only_config(reset_interval_range_s=(0.01, 0.01))
        ctrl = AdaptiveController(config, total_flows=1)
        ctrl.register_flow("f1", None, 1000.0)
        time.sleep(0.05)
        assert ctrl.should_connection_reset("f1")


class TestDirectives:
    """Test server directive application and expiry."""

    def test_protocol_rate_directive(self):
        ctrl = AdaptiveController(_micro_only_config(timing_drift_enabled=False), total_flows=1)
        ctrl.register_flow("f1", None, 1000.0, protocol="modbus_tcp")

        ctrl.set_pending_directives([{
            "type": DIRECTIVE_ADJUST_PROTOCOL_RATE,
            "protocol": "modbus_tcp",
            "multiplier": 2.0,
            "reason": "test",
        }])

        # Next poll should consume the directive and apply the multiplier
        val = ctrl.adjust_next_poll("f1", 1000.0)
        # multiplier 2.0 => interval / 2.0 = 500ms
        assert val == pytest.approx(500.0, abs=1.0)

    def test_flow_rate_directive(self):
        ctrl = AdaptiveController(_micro_only_config(timing_drift_enabled=False), total_flows=1)
        ctrl.register_flow("f1", None, 1000.0)

        ctrl.set_pending_directives([{
            "type": DIRECTIVE_ADJUST_FLOW_RATE,
            "flow_id": "f1",
            "multiplier": 0.5,
            "reason": "slow down",
        }])

        val = ctrl.adjust_next_poll("f1", 1000.0)
        # multiplier 0.5 => interval / 0.5 = 2000ms
        assert val == pytest.approx(2000.0, abs=1.0)

    def test_combined_protocol_and_flow_directives(self):
        ctrl = AdaptiveController(_micro_only_config(timing_drift_enabled=False), total_flows=1)
        ctrl.register_flow("f1", None, 1000.0, protocol="modbus_tcp")

        ctrl.set_pending_directives([
            {"type": DIRECTIVE_ADJUST_PROTOCOL_RATE, "protocol": "modbus_tcp", "multiplier": 2.0},
            {"type": DIRECTIVE_ADJUST_FLOW_RATE, "flow_id": "f1", "multiplier": 2.0},
        ])

        val = ctrl.adjust_next_poll("f1", 1000.0)
        # combined multiplier = 2.0 * 2.0 = 4.0 => 1000 / 4.0 = 250ms
        assert val == pytest.approx(250.0, abs=1.0)

    def test_reset_directive_clears_all(self):
        ctrl = AdaptiveController(_micro_only_config(timing_drift_enabled=False), total_flows=1)
        ctrl.register_flow("f1", None, 1000.0, protocol="modbus_tcp")

        # Apply a directive first
        ctrl.set_pending_directives([{
            "type": DIRECTIVE_ADJUST_PROTOCOL_RATE,
            "protocol": "modbus_tcp",
            "multiplier": 2.0,
        }])
        ctrl.adjust_next_poll("f1", 1000.0)  # consume

        # Verify directive is active
        assert ctrl._protocol_multipliers.get("modbus_tcp") == 2.0

        # Reset
        ctrl.set_pending_directives([{"type": DIRECTIVE_RESET}])
        val = ctrl.adjust_next_poll("f1", 1000.0)  # consume reset

        assert val == pytest.approx(1000.0, abs=1.0)
        assert len(ctrl._active_directives) == 0
        assert len(ctrl._protocol_multipliers) == 0

    def test_directive_expiry(self):
        ctrl = AdaptiveController(_micro_only_config(timing_drift_enabled=False), total_flows=1)
        ctrl.register_flow("f1", None, 1000.0, protocol="modbus_tcp")

        ctrl.set_pending_directives([{
            "type": DIRECTIVE_ADJUST_PROTOCOL_RATE,
            "protocol": "modbus_tcp",
            "multiplier": 2.0,
        }])
        ctrl.adjust_next_poll("f1", 1000.0)  # consume

        # Manually expire the directive
        for d in ctrl._active_directives:
            d.created_at = time.time() - 999  # way past TTL

        val = ctrl.adjust_next_poll("f1", 1000.0)
        # After expiry, should revert to base interval
        assert val == pytest.approx(1000.0, abs=1.0)
        assert len(ctrl._active_directives) == 0

    def test_schedule_phase_override_directive(self):
        phases = [
            SchedulePhase(name="night", hours=(0, 12), rate_multiplier=0.5),
            SchedulePhase(name="day", hours=(12, 24), rate_multiplier=1.0),
        ]
        config = AdaptiveConfig(
            enabled=True,
            micro=MicroVariationConfig(timing_drift_enabled=False),
            schedule=ScheduleConfig(enabled=True, phases=phases, transition_minutes=0),
        )
        ctrl = AdaptiveController(config, total_flows=1)
        ctrl.register_flow("f1", None, 1000.0)

        ctrl.set_pending_directives([{
            "type": DIRECTIVE_SET_SCHEDULE_PHASE,
            "phase_name": "day",
        }])

        # Force processing even if time-of-day says night
        ctrl.adjust_next_poll("f1", 1000.0)
        assert ctrl._schedule_override == "day"

    def test_state_snapshot_counts_directives(self):
        ctrl = AdaptiveController(_micro_only_config(timing_drift_enabled=False), total_flows=1)
        ctrl.register_flow("f1", None, 1000.0, protocol="modbus_tcp")

        ctrl.set_pending_directives([
            {"type": DIRECTIVE_ADJUST_PROTOCOL_RATE, "protocol": "modbus_tcp", "multiplier": 2.0},
            {"type": DIRECTIVE_ADJUST_FLOW_RATE, "flow_id": "f1", "multiplier": 1.5},
        ])
        ctrl.adjust_next_poll("f1", 1000.0)  # consume

        snap = ctrl.get_state_snapshot()
        assert snap["active_directives"] == 2


class TestScheduleIntegration:
    """Test schedule + controller integration."""

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_schedule_affects_interval(self, mock_time):
        phases = [
            SchedulePhase(name="night", hours=(0, 12), rate_multiplier=0.5),
            SchedulePhase(name="day", hours=(12, 24), rate_multiplier=1.0),
        ]
        config = AdaptiveConfig(
            enabled=True,
            micro=MicroVariationConfig(timing_drift_enabled=False),
            schedule=ScheduleConfig(enabled=True, phases=phases, transition_minutes=0),
        )
        ctrl = AdaptiveController(config, total_flows=1)
        ctrl.register_flow("f1", None, 1000.0)

        # Night: rate 0.5 => interval / 0.5 = 2000ms
        mock_time.time.return_value = 3 * 3600.0
        val = ctrl.adjust_next_poll("f1", 1000.0)
        assert val == pytest.approx(2000.0, abs=1.0)

        # Day: rate 1.0 => interval / 1.0 = 1000ms
        mock_time.time.return_value = 14 * 3600.0
        val = ctrl.adjust_next_poll("f1", 1000.0)
        assert val == pytest.approx(1000.0, abs=1.0)

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_dormant_flow_gets_long_interval(self, mock_time):
        phases = [
            SchedulePhase(name="sparse", hours=(0, 24), rate_multiplier=0.5, active_flow_percent=0.0),
        ]
        config = AdaptiveConfig(
            enabled=True,
            micro=MicroVariationConfig(timing_drift_enabled=False),
            schedule=ScheduleConfig(enabled=True, phases=phases, transition_minutes=0),
        )
        ctrl = AdaptiveController(config, total_flows=10)
        ctrl.register_flow("f1", None, 1000.0)

        mock_time.time.return_value = 5 * 3600.0
        val = ctrl.adjust_next_poll("f1", 1000.0)
        # Dormant: interval * 100 = very long
        assert val > 10000


class TestCompositionOrder:
    """Test that schedule -> directives -> micro compose correctly."""

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_full_composition(self, mock_time):
        phases = [
            SchedulePhase(name="day", hours=(0, 24), rate_multiplier=2.0, active_flow_percent=100),
        ]
        config = AdaptiveConfig(
            enabled=True,
            micro=MicroVariationConfig(timing_drift_enabled=False),  # disable for determinism
            schedule=ScheduleConfig(enabled=True, phases=phases, transition_minutes=0),
        )
        ctrl = AdaptiveController(config, total_flows=1)
        ctrl.register_flow("f1", None, 1000.0, protocol="modbus_tcp")

        mock_time.time.return_value = 10 * 3600.0

        # Apply directive: protocol multiplier 1.5
        ctrl.set_pending_directives([{
            "type": DIRECTIVE_ADJUST_PROTOCOL_RATE,
            "protocol": "modbus_tcp",
            "multiplier": 1.5,
        }])

        val = ctrl.adjust_next_poll("f1", 1000.0)
        # Schedule: 1000 / 2.0 = 500
        # Directive: 500 / 1.5 = 333.3
        # Micro: disabled = 333.3
        assert val == pytest.approx(333.3, abs=1.0)


class TestFromDict:
    """Test config deserialization."""

    def test_empty_dict_creates_default(self):
        config = AdaptiveConfig.from_dict({})
        assert config.enabled is True
        assert config.micro.timing_drift_enabled is True
        assert config.schedule.enabled is False

    def test_explicit_disabled(self):
        config = AdaptiveConfig.from_dict({"enabled": False})
        assert config.enabled is False

    def test_nested_micro_config(self):
        config = AdaptiveConfig.from_dict({
            "micro": {
                "timing_drift_max_percent": 10.0,
                "retransmit_probability": 0.01,
            },
        })
        assert config.micro.timing_drift_max_percent == 10.0
        assert config.micro.retransmit_probability == 0.01

    def test_schedule_with_preset(self):
        config = AdaptiveConfig.from_dict({
            "schedule": {
                "enabled": True,
                "preset": "industrial_24h",
            },
        })
        assert config.schedule.enabled is True
        assert config.schedule.preset == "industrial_24h"
