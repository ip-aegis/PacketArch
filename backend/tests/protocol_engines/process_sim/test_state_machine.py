# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for ProcessStateMachine transitions."""

import pytest

from app.protocol_engines.process_sim.state_machine import (
    ProcessStateMachine,
    StateTransition,
)
from app.protocol_engines.process_sim.types import ProcessState
from app.protocol_engines.process_sim.variables import ProcessVariable


class TestProcessStateMachine:
    """Test state machine transitions."""

    def _make_variables(self):
        return {
            "temp": ProcessVariable(
                name="temp",
                initial_value=20.0,
                state_setpoints={
                    ProcessState.COLD_START.value: 20.0,
                    ProcessState.WARMING_UP.value: 40.0,
                    ProcessState.STEADY_STATE.value: 60.0,
                },
            ),
        }

    def test_initial_state(self):
        variables = self._make_variables()
        sm = ProcessStateMachine(
            ProcessState.COLD_START, [], variables,
        )
        assert sm.current_state == ProcessState.COLD_START

    def test_time_transition(self):
        variables = self._make_variables()
        transitions = [
            StateTransition(
                from_state=ProcessState.COLD_START,
                to_state=ProcessState.WARMING_UP,
                condition="time",
                duration_s=5.0,
            ),
        ]
        sm = ProcessStateMachine(ProcessState.COLD_START, transitions, variables)

        # Before duration: no transition
        assert sm.step(4.0) is None
        assert sm.current_state == ProcessState.COLD_START

        # At/after duration: transition fires
        result = sm.step(5.0)
        assert result == ProcessState.WARMING_UP
        assert sm.current_state == ProcessState.WARMING_UP

    def test_threshold_transition_greater(self):
        variables = {
            "pressure": ProcessVariable(
                name="pressure", initial_value=50.0,
                state_setpoints={
                    ProcessState.STEADY_STATE.value: 50.0,
                    ProcessState.ALARM.value: 50.0,
                },
            ),
        }
        transitions = [
            StateTransition(
                from_state=ProcessState.STEADY_STATE,
                to_state=ProcessState.ALARM,
                condition="threshold",
                variable="pressure",
                threshold=80.0,
                comparison=">",
            ),
        ]
        sm = ProcessStateMachine(ProcessState.STEADY_STATE, transitions, variables)

        # Below threshold
        assert sm.step(1.0) is None

        # Push above threshold
        variables["pressure"].set_value(85.0)
        result = sm.step(2.0)
        assert result == ProcessState.ALARM

    def test_threshold_transition_less(self):
        variables = {
            "level": ProcessVariable(
                name="level", initial_value=50.0,
                state_setpoints={
                    ProcessState.STEADY_STATE.value: 50.0,
                    ProcessState.ALARM.value: 50.0,
                },
            ),
        }
        transitions = [
            StateTransition(
                from_state=ProcessState.STEADY_STATE,
                to_state=ProcessState.ALARM,
                condition="threshold",
                variable="level",
                threshold=10.0,
                comparison="<",
            ),
        ]
        sm = ProcessStateMachine(ProcessState.STEADY_STATE, transitions, variables)

        # Above threshold
        assert sm.step(1.0) is None

        # Push below threshold
        variables["level"].set_value(5.0)
        result = sm.step(2.0)
        assert result == ProcessState.ALARM

    def test_force_state(self):
        variables = self._make_variables()
        sm = ProcessStateMachine(ProcessState.COLD_START, [], variables)

        sm.force_state(ProcessState.STEADY_STATE, 10.0)
        assert sm.current_state == ProcessState.STEADY_STATE
        # Variable target should be updated
        assert variables["temp"].target == 60.0

    def test_force_same_state_noop(self):
        variables = self._make_variables()
        sm = ProcessStateMachine(ProcessState.COLD_START, [], variables)
        sm.force_state(ProcessState.COLD_START, 1.0)
        assert sm.current_state == ProcessState.COLD_START

    def test_setpoints_applied_on_transition(self):
        variables = self._make_variables()
        transitions = [
            StateTransition(
                from_state=ProcessState.COLD_START,
                to_state=ProcessState.WARMING_UP,
                condition="time",
                duration_s=1.0,
            ),
        ]
        sm = ProcessStateMachine(ProcessState.COLD_START, transitions, variables)

        # Initial setpoint applied
        assert variables["temp"].target == 20.0

        # Transition should apply warming_up setpoint
        sm.step(1.0)
        assert variables["temp"].target == 40.0

    def test_chained_transitions(self):
        variables = self._make_variables()
        transitions = [
            StateTransition(
                from_state=ProcessState.COLD_START,
                to_state=ProcessState.WARMING_UP,
                condition="time",
                duration_s=1.0,
            ),
            StateTransition(
                from_state=ProcessState.WARMING_UP,
                to_state=ProcessState.STEADY_STATE,
                condition="time",
                duration_s=2.0,
            ),
        ]
        sm = ProcessStateMachine(ProcessState.COLD_START, transitions, variables)

        sm.step(1.0)
        assert sm.current_state == ProcessState.WARMING_UP

        # Need to accumulate 2s in WARMING_UP state
        sm.step(2.0)  # 1s since transition
        assert sm.current_state == ProcessState.WARMING_UP

        sm.step(3.0)  # 2s since transition
        assert sm.current_state == ProcessState.STEADY_STATE
