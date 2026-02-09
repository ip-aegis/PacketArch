"""Tests for ProcessVariable first-order lag dynamics."""

import pytest

from app.protocol_engines.process_sim.types import ProcessState, VariableRole
from app.protocol_engines.process_sim.variables import ProcessVariable


class TestProcessVariable:
    """Test ProcessVariable behavior."""

    def test_initial_value(self):
        var = ProcessVariable(name="temp", initial_value=25.0)
        assert var.value == 25.0
        assert var.target == 25.0

    def test_set_target_clamps(self):
        var = ProcessVariable(
            name="level", min_value=0.0, max_value=100.0, initial_value=50.0,
        )
        var.set_target(150.0)
        assert var.target == 100.0

        var.set_target(-10.0)
        assert var.target == 0.0

    def test_step_no_lag_instant(self):
        """With time_constant_s=0, value jumps to target immediately."""
        var = ProcessVariable(
            name="v", initial_value=0.0, time_constant_s=0.0, noise_std=0.0,
        )
        var.set_target(100.0)
        var.step(0.1)
        assert var.value == 100.0

    def test_step_with_lag(self):
        """With time_constant_s > 0, value approaches target exponentially."""
        var = ProcessVariable(
            name="v", initial_value=0.0, time_constant_s=1.0, noise_std=0.0,
            min_value=-1e6, max_value=1e6,
        )
        var.set_target(100.0)

        # After 1 time constant, should be ~50% of target (first-order lag)
        var.step(1.0)
        assert 45.0 < var.value < 55.0  # alpha = 1/(1+1) = 0.5

        # After another step, closer to target
        var.step(1.0)
        assert var.value > 70.0

    def test_step_with_noise(self):
        """Noise adds Gaussian perturbation."""
        var = ProcessVariable(
            name="v", initial_value=50.0, time_constant_s=0.0,
            noise_std=1.0, min_value=0.0, max_value=100.0,
        )
        var.set_target(50.0)

        # Run many steps, collect values
        values = []
        for _ in range(1000):
            var.step(0.1)
            values.append(var.value)

        # Mean should be close to 50, std should be close to 1
        mean = sum(values) / len(values)
        assert 48.0 < mean < 52.0

    def test_step_clamps_value(self):
        var = ProcessVariable(
            name="v", initial_value=99.0, min_value=0.0, max_value=100.0,
            time_constant_s=0.0, noise_std=0.0,
        )
        var.set_target(200.0)
        var.step(0.1)
        assert var.value == 100.0

    def test_step_zero_dt_noop(self):
        var = ProcessVariable(name="v", initial_value=50.0)
        var.set_target(100.0)
        var.step(0.0)
        assert var.value == 50.0

    def test_apply_state_setpoint(self):
        var = ProcessVariable(
            name="v", initial_value=0.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.STEADY_STATE.value: 75.0,
            },
        )
        var.apply_state_setpoint(ProcessState.STEADY_STATE)
        assert var.target == 75.0

    def test_apply_state_setpoint_missing(self):
        var = ProcessVariable(name="v", initial_value=50.0)
        var.set_target(50.0)
        var.apply_state_setpoint(ProcessState.ALARM)
        # Target unchanged
        assert var.target == 50.0

    def test_reset(self):
        var = ProcessVariable(name="v", initial_value=10.0)
        var.set_target(90.0)
        var.step(1.0)
        var.reset()
        assert var.value == 10.0
        assert var.target == 10.0

    def test_set_value_bypasses_lag(self):
        var = ProcessVariable(
            name="v", initial_value=0.0, time_constant_s=10.0,
            min_value=-100.0, max_value=100.0,
        )
        var.set_value(75.0)
        assert var.value == 75.0
