# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for ProcessModel — integrated variable + equation + state machine."""


from app.protocol_engines.process_sim.equations import Equation
from app.protocol_engines.process_sim.process_model import ProcessModel
from app.protocol_engines.process_sim.state_machine import StateTransition
from app.protocol_engines.process_sim.types import ProcessState
from app.protocol_engines.process_sim.variables import ProcessVariable


class TestProcessModel:
    """Test the integrated ProcessModel."""

    def _make_simple_model(self):
        """A simple tank model: level = level + (inflow - outflow) * dt."""
        variables = [
            ProcessVariable(
                name="inflow",
                initial_value=0.0,
                min_value=0.0,
                max_value=100.0,
                noise_std=0.0,
                time_constant_s=0.0,
                state_setpoints={
                    ProcessState.COLD_START.value: 0.0,
                    ProcessState.WARMING_UP.value: 50.0,
                    ProcessState.STEADY_STATE.value: 80.0,
                    ProcessState.SHUTDOWN.value: 0.0,
                },
            ),
            ProcessVariable(
                name="outflow",
                initial_value=0.0,
                min_value=0.0,
                max_value=100.0,
                noise_std=0.0,
                time_constant_s=0.0,
                state_setpoints={
                    ProcessState.COLD_START.value: 0.0,
                    ProcessState.WARMING_UP.value: 30.0,
                    ProcessState.STEADY_STATE.value: 80.0,
                    ProcessState.SHUTDOWN.value: 0.0,
                },
            ),
            ProcessVariable(
                name="level",
                initial_value=50.0,
                min_value=0.0,
                max_value=100.0,
                noise_std=0.0,
                time_constant_s=0.0,
            ),
        ]

        equations = [
            Equation(
                target="level",
                kind="ode",
                func=lambda v: v["inflow"] - v["outflow"],
            ),
        ]

        transitions = [
            StateTransition(
                from_state=ProcessState.COLD_START,
                to_state=ProcessState.WARMING_UP,
                condition="time",
                duration_s=5.0,
            ),
            StateTransition(
                from_state=ProcessState.WARMING_UP,
                to_state=ProcessState.STEADY_STATE,
                condition="time",
                duration_s=30.0,
            ),
        ]

        return ProcessModel(
            model_id="test_tank",
            name="Test Tank",
            variables=variables,
            equations=equations,
            transitions=transitions,
            initial_state=ProcessState.COLD_START,
        )

    def test_initial_state(self):
        model = self._make_simple_model()
        assert model.state == ProcessState.COLD_START
        assert model.get_value("level") == 50.0

    def test_step_advances_time(self):
        model = self._make_simple_model()
        model.step(1.0)
        assert model.sim_time_s == 1.0

    def test_state_transitions(self):
        model = self._make_simple_model()

        # Step through cold_start (5s) — use 51 steps to avoid
        # floating-point accumulation (0.1*50 ≈ 4.9999...)
        for _ in range(51):
            model.step(0.1)
        assert model.state == ProcessState.WARMING_UP

        # During warming: inflow=50, outflow=30, so level should rise
        level_at_warming = model.get_value("level")
        for _ in range(100):
            model.step(0.1)
        level_after = model.get_value("level")
        assert level_after > level_at_warming  # net inflow of 20

    def test_force_state(self):
        model = self._make_simple_model()
        model.force_state(ProcessState.STEADY_STATE)
        assert model.state == ProcessState.STEADY_STATE
        # At steady state: inflow=80, outflow=80, level should be stable
        assert model.variables["inflow"].target == 80.0
        assert model.variables["outflow"].target == 80.0

    def test_snapshot(self):
        model = self._make_simple_model()
        model.step(1.0)
        snap = model.get_snapshot()
        assert snap["model_id"] == "test_tank"
        assert snap["state"] == "cold_start"
        assert "level" in snap["variables"]
        assert "value" in snap["variables"]["level"]
        assert "target" in snap["variables"]["level"]

    def test_reset(self):
        model = self._make_simple_model()
        model.step(10.0)  # Advance past cold_start
        model.reset()
        assert model.sim_time_s == 0.0
        assert model.get_value("level") == 50.0

    def test_level_correlation(self):
        """Verify that level is correlated with net flow (inflow - outflow)."""
        model = self._make_simple_model()
        model.force_state(ProcessState.WARMING_UP)

        model.get_value("level")

        # Run for 10s: inflow=50, outflow=30 → net = 20/s
        for _ in range(100):
            model.step(0.1)

        final_level = model.get_value("level")
        # Level should have risen by ~20 * 10 = 200, but capped at 100
        assert final_level == 100.0  # Clamped at max


class TestProcessModelTemplates:
    """Test that built-in templates construct without error."""

    def test_manufacturing_template(self):
        from app.protocol_engines.process_sim.templates.manufacturing import (
            build_faults,
            build_model,
        )

        model = build_model()
        faults = build_faults()
        assert model.model_id == "manufacturing_cnc"
        assert len(model.variables) == 7
        assert len(faults) == 2

        # Run 100 steps without error
        for _ in range(100):
            model.step(0.1)
        assert model.sim_time_s > 0

    def test_water_template(self):
        from app.protocol_engines.process_sim.templates.water import (
            build_faults,
            build_model,
        )

        model = build_model()
        faults = build_faults()
        assert model.model_id == "water_treatment"
        assert len(model.variables) == 9
        assert len(faults) == 2

        for _ in range(100):
            model.step(0.1)

    def test_building_automation_template(self):
        from app.protocol_engines.process_sim.templates.building_automation import (
            build_faults,
            build_model,
        )

        model = build_model()
        faults = build_faults()
        assert model.model_id == "bms_hvac"
        assert len(model.variables) == 7
        assert len(faults) == 2

        for _ in range(100):
            model.step(0.1)

    def test_oil_gas_template(self):
        from app.protocol_engines.process_sim.templates.oil_gas import (
            build_faults,
            build_model,
        )

        model = build_model()
        faults = build_faults()
        assert model.model_id == "oil_gas_wellhead"
        assert len(model.variables) == 8
        assert len(faults) == 2

        for _ in range(100):
            model.step(0.1)
