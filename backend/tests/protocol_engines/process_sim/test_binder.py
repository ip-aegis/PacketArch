# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for VariableBinder — process variable → PayloadGenerator mapping."""

import pytest

from app.protocol_engines.payload_generator import (
    PayloadGenerator,
    SensorProfile,
    TrendType,
)
from app.protocol_engines.process_sim.binder import VariableBinder
from app.protocol_engines.process_sim.process_model import ProcessModel
from app.protocol_engines.process_sim.types import VariableBinding, VariableRole
from app.protocol_engines.process_sim.variables import ProcessVariable


class TestVariableBinder:
    """Test push_values and auto_bind."""

    def _make_model_and_generator(self):
        """Create a simple model and PayloadGenerator for testing."""
        model = ProcessModel(
            model_id="test",
            name="Test",
            variables=[
                ProcessVariable(
                    name="temperature",
                    role=VariableRole.TEMPERATURE,
                    initial_value=25.0,
                    noise_std=0.0,
                    time_constant_s=0.0,
                ),
                ProcessVariable(
                    name="pressure",
                    role=VariableRole.PRESSURE,
                    initial_value=5.0,
                    noise_std=0.0,
                    time_constant_s=0.0,
                ),
            ],
        )

        gen = PayloadGenerator([
            SensorProfile(name="reg_0", nominal_value=0.0, noise_std=0.0),
            SensorProfile(name="reg_1", nominal_value=0.0, noise_std=0.0),
        ])

        return model, gen

    def test_explicit_binding_push_values(self):
        model, gen = self._make_model_and_generator()

        binder = VariableBinder([
            VariableBinding(
                variable_name="temperature",
                flow_id="flow-1",
                sensor_name="reg_0",
            ),
            VariableBinding(
                variable_name="pressure",
                flow_id="flow-1",
                sensor_name="reg_1",
            ),
        ])

        models = {"test": model}
        generators = {"flow-1": gen}

        binder.push_values(models, generators)

        # Check that sensor states reflect process variable values
        assert gen.states["reg_0"].current_value == 25.0
        assert gen.states["reg_1"].current_value == 5.0

        # Check that profiles are set to STABLE
        assert gen.profiles["reg_0"].trend_type == TrendType.STABLE
        assert gen.profiles["reg_0"].nominal_value == 25.0

    def test_scale_and_offset(self):
        model, gen = self._make_model_and_generator()

        binder = VariableBinder([
            VariableBinding(
                variable_name="temperature",
                flow_id="flow-1",
                sensor_name="reg_0",
                scale=10.0,
                offset=100.0,
            ),
        ])

        binder.push_values({"test": model}, {"flow-1": gen})

        # 25.0 * 10 + 100 = 350.0
        assert gen.states["reg_0"].current_value == 350.0

    def test_clamp_override(self):
        model, gen = self._make_model_and_generator()

        binder = VariableBinder([
            VariableBinding(
                variable_name="temperature",
                flow_id="flow-1",
                sensor_name="reg_0",
                scale=100.0,  # 25 * 100 = 2500
                clamp_max=1000.0,
            ),
        ])

        binder.push_values({"test": model}, {"flow-1": gen})

        assert gen.states["reg_0"].current_value == 1000.0

    def test_missing_flow_id_ignored(self):
        model, gen = self._make_model_and_generator()

        binder = VariableBinder([
            VariableBinding(
                variable_name="temperature",
                flow_id="nonexistent",
                sensor_name="reg_0",
            ),
        ])

        # Should not raise
        binder.push_values({"test": model}, {"flow-1": gen})

    def test_missing_variable_ignored(self):
        model, gen = self._make_model_and_generator()

        binder = VariableBinder([
            VariableBinding(
                variable_name="nonexistent",
                flow_id="flow-1",
                sensor_name="reg_0",
            ),
        ])

        # Should not raise; reg_0 stays unchanged
        binder.push_values({"test": model}, {"flow-1": gen})
        assert gen.states["reg_0"].current_value == 0.0  # nominal from profile

    def test_auto_bind_positional(self):
        model, gen = self._make_model_and_generator()
        models = {"test": model}
        generators = {"flow-1": gen}

        binder = VariableBinder.auto_bind(models, generators)

        assert binder.binding_count >= 2  # Both variables should bind

        binder.push_values(models, generators)
        # Values should be set (non-zero)
        values = [gen.states["reg_0"].current_value, gen.states["reg_1"].current_value]
        assert any(v != 0.0 for v in values)

    def test_from_dicts(self):
        binder = VariableBinder.from_dicts([
            {
                "variable_name": "temp",
                "flow_id": "f1",
                "sensor_name": "reg_0",
                "scale": 2.0,
                "offset": 10.0,
            },
        ])
        assert binder.binding_count == 1

    def test_binding_count(self):
        binder = VariableBinder([
            VariableBinding("a", "f1", "s1"),
            VariableBinding("b", "f1", "s2"),
            VariableBinding("c", "f2", "s1"),
        ])
        assert binder.binding_count == 3
