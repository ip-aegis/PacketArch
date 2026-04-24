# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for TrafficSchedule — time-of-day traffic shaping."""

from unittest.mock import patch

import pytest

from app.protocol_engines.adaptive.schedule import (
    TrafficSchedule,
    SCHEDULE_PRESETS,
    _DEFAULT_PHASE,
)
from app.protocol_engines.adaptive.types import ScheduleConfig, SchedulePhase


def _make_config(
    preset: str | None = None,
    phases: list[SchedulePhase] | None = None,
    transition_minutes: float = 0.0,
    tz_offset: float = 0.0,
) -> ScheduleConfig:
    return ScheduleConfig(
        enabled=True,
        preset=preset,
        phases=phases or [],
        transition_minutes=transition_minutes,
        timezone_offset_hours=tz_offset,
    )


class TestSchedulePresets:
    """Test loading and using preset schedules."""

    def test_industrial_24h_preset_loads(self):
        config = _make_config(preset="industrial_24h")
        schedule = TrafficSchedule(config)
        # Should have 6 phases
        assert len(schedule._phases) == 6

    def test_office_hours_preset_loads(self):
        config = _make_config(preset="office_hours")
        schedule = TrafficSchedule(config)
        assert len(schedule._phases) == 3

    def test_data_center_preset_loads(self):
        config = _make_config(preset="data_center")
        schedule = TrafficSchedule(config)
        assert len(schedule._phases) == 5

    def test_constant_preset_returns_default(self):
        config = _make_config(preset="constant")
        schedule = TrafficSchedule(config)
        assert len(schedule._phases) == 0
        # Should always return default phase
        phase = schedule.get_current_phase()
        assert phase.rate_multiplier == 1.0

    def test_unknown_preset_returns_default(self):
        config = _make_config(preset="nonexistent_preset")
        schedule = TrafficSchedule(config)
        assert len(schedule._phases) == 0

    def test_all_preset_phases_cover_24h(self):
        """All presets should collectively cover 0-24 hours."""
        for preset_name, phases in SCHEDULE_PRESETS.items():
            if not phases:  # skip constant
                continue
            hours = set()
            for p in phases:
                start, end = p["hours"]
                for h in range(start, end):
                    hours.add(h)
            assert hours == set(range(24)), (
                f"Preset '{preset_name}' doesn't cover all 24 hours: missing {set(range(24)) - hours}"
            )


class TestPhaseResolution:
    """Test correct phase determination from time."""

    def _two_phase_schedule(self) -> TrafficSchedule:
        phases = [
            SchedulePhase(name="night", hours=(0, 12), rate_multiplier=0.5, active_flow_percent=60),
            SchedulePhase(name="day", hours=(12, 24), rate_multiplier=1.0, active_flow_percent=100),
        ]
        return TrafficSchedule(_make_config(phases=phases))

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_night_phase_at_3am(self, mock_time):
        schedule = self._two_phase_schedule()
        # 3:00 AM UTC = 3 * 3600 seconds into the day
        mock_time.time.return_value = 3 * 3600.0
        phase = schedule.get_current_phase()
        assert phase.name == "night"
        assert phase.rate_multiplier == 0.5

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_day_phase_at_2pm(self, mock_time):
        schedule = self._two_phase_schedule()
        mock_time.time.return_value = 14 * 3600.0
        phase = schedule.get_current_phase()
        assert phase.name == "day"
        assert phase.rate_multiplier == 1.0

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_phase_at_boundary(self, mock_time):
        schedule = self._two_phase_schedule()
        # Exactly at noon (12:00) should be start of day phase
        mock_time.time.return_value = 12 * 3600.0
        phase = schedule.get_current_phase()
        assert phase.name == "day"

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_timezone_offset(self, mock_time):
        phases = [
            SchedulePhase(name="night", hours=(0, 12), rate_multiplier=0.5),
            SchedulePhase(name="day", hours=(12, 24), rate_multiplier=1.0),
        ]
        # UTC+5 offset: 3am UTC = 8am local (still night in UTC but day in local)
        config = _make_config(phases=phases, tz_offset=5.0)
        schedule = TrafficSchedule(config)
        # 3am UTC
        mock_time.time.return_value = 3 * 3600.0
        phase = schedule.get_current_phase()
        # With +5h offset: 3 + 5 = 8, which is night phase (0-12)
        assert phase.name == "night"

        # 9am UTC with +5h = 14:00 local -> day phase
        mock_time.time.return_value = 9 * 3600.0
        phase = schedule.get_current_phase()
        assert phase.name == "day"


class TestScheduleOverride:
    """Test manual phase override."""

    def _two_phase_schedule(self) -> TrafficSchedule:
        phases = [
            SchedulePhase(name="night", hours=(0, 12), rate_multiplier=0.5),
            SchedulePhase(name="day", hours=(12, 24), rate_multiplier=1.0),
        ]
        return TrafficSchedule(_make_config(phases=phases))

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_override_forces_phase(self, mock_time):
        schedule = self._two_phase_schedule()
        mock_time.time.return_value = 3 * 3600.0  # 3am → normally night
        phase = schedule.get_current_phase(override="day")
        assert phase.name == "day"
        assert phase.rate_multiplier == 1.0

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_unknown_override_falls_through(self, mock_time):
        schedule = self._two_phase_schedule()
        mock_time.time.return_value = 3 * 3600.0
        phase = schedule.get_current_phase(override="nonexistent")
        assert phase.name == "night"  # falls through to time-based


class TestSmoothInterpolation:
    """Test smooth transitions at phase boundaries."""

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_interpolation_at_boundary(self, mock_time):
        phases = [
            SchedulePhase(name="night", hours=(0, 12), rate_multiplier=0.5),
            SchedulePhase(name="day", hours=(12, 24), rate_multiplier=1.0),
        ]
        config = _make_config(phases=phases, transition_minutes=10.0)
        schedule = TrafficSchedule(config)

        # 1 minute into day phase (12:01) — deep in transition zone
        mock_time.time.return_value = (12 * 60 + 1) * 60.0
        phase = schedule.get_current_phase()
        # Should be interpolated between night (0.5) and day (1.0)
        assert 0.5 < phase.rate_multiplier < 1.0
        assert "->" in phase.name  # transition name format

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_no_interpolation_mid_phase(self, mock_time):
        phases = [
            SchedulePhase(name="night", hours=(0, 12), rate_multiplier=0.5),
            SchedulePhase(name="day", hours=(12, 24), rate_multiplier=1.0),
        ]
        config = _make_config(phases=phases, transition_minutes=10.0)
        schedule = TrafficSchedule(config)

        # 3pm — well into day phase, no interpolation
        mock_time.time.return_value = 15 * 3600.0
        phase = schedule.get_current_phase()
        assert phase.rate_multiplier == 1.0
        assert phase.name == "day"

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_zero_transition_no_interpolation(self, mock_time):
        phases = [
            SchedulePhase(name="night", hours=(0, 12), rate_multiplier=0.5),
            SchedulePhase(name="day", hours=(12, 24), rate_multiplier=1.0),
        ]
        config = _make_config(phases=phases, transition_minutes=0.0)
        schedule = TrafficSchedule(config)

        mock_time.time.return_value = 12 * 3600.0 + 1  # 1 second into day
        phase = schedule.get_current_phase()
        assert phase.rate_multiplier == 1.0


class TestFlowActivation:
    """Test consistent-hash flow activation."""

    def test_all_active_at_100_percent(self):
        phases = [
            SchedulePhase(name="full", hours=(0, 24), rate_multiplier=1.0, active_flow_percent=100.0),
        ]
        schedule = TrafficSchedule(_make_config(phases=phases))
        for i in range(100):
            assert schedule.should_flow_be_active(f"flow-{i}", 100)

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_none_active_at_0_percent(self, mock_time):
        phases = [
            SchedulePhase(name="dead", hours=(0, 24), rate_multiplier=0.1, active_flow_percent=0.0),
        ]
        config = _make_config(phases=phases)
        schedule = TrafficSchedule(config)
        mock_time.time.return_value = 5 * 3600.0
        for i in range(100):
            assert not schedule.should_flow_be_active(f"flow-{i}", 100)

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_partial_activation_is_deterministic(self, mock_time):
        phases = [
            SchedulePhase(name="partial", hours=(0, 24), rate_multiplier=0.5, active_flow_percent=50.0),
        ]
        config = _make_config(phases=phases)
        schedule = TrafficSchedule(config)
        mock_time.time.return_value = 5 * 3600.0

        # Same flow_id should always give the same result
        results_a = [schedule.should_flow_be_active(f"flow-{i}", 100) for i in range(100)]
        results_b = [schedule.should_flow_be_active(f"flow-{i}", 100) for i in range(100)]
        assert results_a == results_b

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_partial_activation_roughly_correct(self, mock_time):
        phases = [
            SchedulePhase(name="partial", hours=(0, 24), rate_multiplier=0.5, active_flow_percent=60.0),
        ]
        config = _make_config(phases=phases)
        schedule = TrafficSchedule(config)
        mock_time.time.return_value = 5 * 3600.0

        active_count = sum(
            1 for i in range(1000)
            if schedule.should_flow_be_active(f"flow-{i}", 1000)
        )
        # 60% of 1000 = ~600, allow ±10% margin
        assert 500 < active_count < 700, f"Expected ~600 active, got {active_count}"

    def test_empty_schedule_always_active(self):
        schedule = TrafficSchedule(_make_config(preset="constant"))
        for i in range(20):
            assert schedule.should_flow_be_active(f"flow-{i}", 20)


class TestRateMultiplierConvenience:
    """Test convenience methods."""

    @patch("app.protocol_engines.adaptive.schedule.time")
    def test_get_rate_multiplier(self, mock_time):
        phases = [
            SchedulePhase(name="night", hours=(0, 12), rate_multiplier=0.5),
            SchedulePhase(name="day", hours=(12, 24), rate_multiplier=1.0),
        ]
        schedule = TrafficSchedule(_make_config(phases=phases))
        mock_time.time.return_value = 3 * 3600.0
        assert schedule.get_rate_multiplier() == 0.5
