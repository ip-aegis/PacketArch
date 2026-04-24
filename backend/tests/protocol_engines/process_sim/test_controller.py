# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for ProcessSimController — composition peer integration."""

import pytest

from app.protocol_engines.payload_generator import (
    PayloadGenerator,
    SensorProfile,
)
from app.protocol_engines.process_sim.controller import ProcessSimController
from app.protocol_engines.process_sim.equations import Equation
from app.protocol_engines.process_sim.faults import FaultEffect, FaultScenario
from app.protocol_engines.process_sim.process_model import ProcessModel
from app.protocol_engines.process_sim.state_machine import StateTransition
from app.protocol_engines.process_sim.types import ProcessSimConfig, ProcessState
from app.protocol_engines.process_sim.variables import ProcessVariable


class MockScheduler:
    """Minimal scheduler mock for testing."""

    def __init__(self):
        self.events: list[tuple[float, dict]] = []

    def schedule(self, time_ms: float, event) -> None:
        self.events.append((time_ms, event))


class TestProcessSimController:
    """Test controller lifecycle."""

    def _make_controller(self):
        """Create a simple controller with a tank model."""
        model = ProcessModel(
            model_id="tank",
            name="Tank",
            variables=[
                ProcessVariable(
                    name="level",
                    initial_value=50.0,
                    min_value=0.0,
                    max_value=100.0,
                    noise_std=0.0,
                    time_constant_s=0.0,
                    state_setpoints={
                        ProcessState.COLD_START.value: 50.0,
                        ProcessState.WARMING_UP.value: 70.0,
                        ProcessState.STEADY_STATE.value: 80.0,
                        ProcessState.SHUTDOWN.value: 20.0,
                    },
                ),
                ProcessVariable(
                    name="flow",
                    initial_value=10.0,
                    noise_std=0.0,
                    time_constant_s=0.0,
                    state_setpoints={
                        ProcessState.COLD_START.value: 0.0,
                        ProcessState.WARMING_UP.value: 10.0,
                        ProcessState.STEADY_STATE.value: 20.0,
                        ProcessState.SHUTDOWN.value: 0.0,
                    },
                ),
            ],
            equations=[
                Equation(
                    target="level",
                    kind="ode",
                    func=lambda v: v["flow"] * 0.1,
                ),
            ],
            transitions=[
                StateTransition(
                    from_state=ProcessState.COLD_START,
                    to_state=ProcessState.WARMING_UP,
                    condition="time",
                    duration_s=1.0,
                ),
            ],
        )

        gen = PayloadGenerator([
            SensorProfile(name="reg_0", nominal_value=0.0, noise_std=0.0),
            SensorProfile(name="reg_1", nominal_value=0.0, noise_std=0.0),
        ])

        config = ProcessSimConfig(enabled=True, step_interval_ms=100.0)

        from app.protocol_engines.process_sim.binder import VariableBinder
        from app.protocol_engines.process_sim.types import VariableBinding

        binder = VariableBinder([
            VariableBinding("level", "flow-1", "reg_0"),
            VariableBinding("flow", "flow-1", "reg_1"),
        ])

        controller = ProcessSimController(
            config=config,
            models=[model],
            flow_generators={"flow-1": gen},
            binder=binder,
        )

        return controller, gen, model

    def test_schedule_initial_events(self):
        controller, _, _ = self._make_controller()
        scheduler = MockScheduler()
        controller.schedule_initial_events(scheduler, warmup_ms=100.0)

        assert len(scheduler.events) == 1
        time_ms, event = scheduler.events[0]
        assert time_ms == 200.0  # 100 warmup + 100 step
        assert event["type"] == "process_sim_tick"

    def test_handle_tick_advances_model(self):
        controller, gen, model = self._make_controller()
        scheduler = MockScheduler()

        # First tick at 100ms
        controller.handle_tick(100.0, scheduler)

        # Model should have advanced
        assert model.sim_time_s > 0

        # Values should be pushed to generator
        assert gen.states["reg_0"].current_value != 0.0  # level pushed

        # Next tick should be scheduled
        assert len(scheduler.events) == 1
        assert scheduler.events[0][1]["type"] == "process_sim_tick"

    def test_handle_tick_multiple_steps(self):
        controller, gen, _ = self._make_controller()
        scheduler = MockScheduler()

        for t in range(10):
            scheduler.events.clear()
            controller.handle_tick(float(t * 100), scheduler)

        # Level should have changed from initial 50
        assert gen.states["reg_0"].current_value != 50.0

    def test_on_phase_change(self):
        controller, _, model = self._make_controller()

        controller.on_phase_change("steady_state")
        assert model.state == ProcessState.STEADY_STATE

    def test_on_phase_change_shutdown(self):
        controller, _, model = self._make_controller()

        controller.on_phase_change("shutdown")
        assert model.state == ProcessState.SHUTDOWN

    def test_on_phase_change_unknown(self):
        controller, _, model = self._make_controller()
        old_state = model.state

        controller.on_phase_change("unknown_phase")
        assert model.state == old_state  # Unchanged

    def test_on_phase_change_same_noop(self):
        controller, _, model = self._make_controller()
        controller.on_phase_change("startup")
        assert model.state == ProcessState.WARMING_UP

        # Same phase again — should not re-trigger
        controller.on_phase_change("startup")
        assert model.state == ProcessState.WARMING_UP

    def test_get_state_snapshot(self):
        controller, _, _ = self._make_controller()
        snap = controller.get_state_snapshot()

        assert snap["enabled"] is True
        assert "tank" in snap["models"]
        assert snap["binding_count"] == 2

    def test_pending_command_trigger_fault(self):
        fault = FaultScenario(
            name="test_fault",
            effects=[
                FaultEffect("level", "set", value=0.0, delay_ms=0),
            ],
        )
        controller, gen, model = self._make_controller()
        controller._faults = [fault]

        controller.set_pending_command(
            {"action": "trigger_fault", "fault_name": "test_fault"},
        )

        scheduler = MockScheduler()
        controller.handle_tick(1000.0, scheduler)

        assert fault.is_active
        # Level should have been set to 0
        assert model.variables["level"].value == 0.0

    def test_pending_command_force_state(self):
        controller, _, model = self._make_controller()

        controller.set_pending_command(
            {"action": "force_state", "state": "maintenance"},
        )

        scheduler = MockScheduler()
        controller.handle_tick(1000.0, scheduler)

        assert model.state == ProcessState.MAINTENANCE

    def test_pending_command_reset(self):
        controller, _, model = self._make_controller()

        # Advance model
        scheduler = MockScheduler()
        for t in range(20):
            controller.handle_tick(float(t * 100), scheduler)
            scheduler.events.clear()

        # Reset — note: handle_tick processes the reset command,
        # then still advances the model by one dt step.
        controller.set_pending_command({"action": "reset"})
        controller.handle_tick(2000.0, scheduler)

        # After reset + one step, sim_time should be very small
        assert model.sim_time_s < 0.2


class TestBuildFromVertical:
    """Test template registry."""

    def test_manufacturing(self):
        from app.protocol_engines.process_sim.templates import build_from_vertical

        models, faults = build_from_vertical("manufacturing")
        assert len(models) == 1
        assert len(faults) >= 1

    def test_water(self):
        from app.protocol_engines.process_sim.templates import build_from_vertical

        models, faults = build_from_vertical("water_wastewater")
        assert len(models) == 1

    def test_unknown_vertical(self):
        from app.protocol_engines.process_sim.templates import build_from_vertical

        models, faults = build_from_vertical("nonexistent")
        assert models == []
        assert faults == []
