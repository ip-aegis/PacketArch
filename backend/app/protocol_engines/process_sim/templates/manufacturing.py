# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""CNC machining loop process template.

Models a CNC machining cell with correlated variables:
spindle speed → spindle load → coolant temperature → vibration → part count.

The model includes realistic thermal dynamics (coolant heating from spindle
load, exponential cooling) and tool wear accumulation.
"""

from __future__ import annotations

from ..equations import Equation
from ..faults import FaultEffect, FaultScenario
from ..process_model import ProcessModel
from ..state_machine import StateTransition
from ..types import ProcessState, VariableRole
from ..variables import ProcessVariable

MODEL_ID = "manufacturing_cnc"
MODEL_NAME = "CNC Machining Loop"


def build_model() -> ProcessModel:
    """Build the CNC machining process model."""
    variables = [
        ProcessVariable(
            name="spindle_speed",
            role=VariableRole.SPEED,
            unit="RPM",
            initial_value=0.0,
            min_value=0.0,
            max_value=15000.0,
            noise_std=5.0,
            time_constant_s=2.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 3000.0,
                ProcessState.STEADY_STATE.value: 12000.0,
                ProcessState.LOAD_CHANGE.value: 8000.0,
                ProcessState.MAINTENANCE.value: 0.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="feed_rate",
            role=VariableRole.SPEED,
            unit="mm/min",
            initial_value=0.0,
            min_value=0.0,
            max_value=800.0,
            noise_std=2.0,
            time_constant_s=1.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 0.0,
                ProcessState.STEADY_STATE.value: 500.0,
                ProcessState.LOAD_CHANGE.value: 300.0,
                ProcessState.MAINTENANCE.value: 0.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="spindle_load",
            role=VariableRole.LOAD,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=120.0,
            noise_std=1.5,
            time_constant_s=0.5,
        ),
        ProcessVariable(
            name="coolant_temp",
            role=VariableRole.TEMPERATURE,
            unit="C",
            initial_value=22.0,
            min_value=15.0,
            max_value=90.0,
            noise_std=0.3,
            time_constant_s=30.0,
            state_setpoints={
                ProcessState.COLD_START.value: 22.0,
                ProcessState.WARMING_UP.value: 25.0,
                ProcessState.STEADY_STATE.value: 45.0,
                ProcessState.MAINTENANCE.value: 30.0,
                ProcessState.SHUTDOWN.value: 22.0,
            },
        ),
        ProcessVariable(
            name="vibration",
            role=VariableRole.VIBRATION,
            unit="mm/s",
            initial_value=0.0,
            min_value=0.0,
            max_value=25.0,
            noise_std=0.2,
            time_constant_s=0.3,
        ),
        ProcessVariable(
            name="part_count",
            role=VariableRole.COUNTER,
            unit="parts",
            initial_value=0.0,
            min_value=0.0,
            max_value=1e6,
            noise_std=0.0,
            time_constant_s=0.0,
        ),
        ProcessVariable(
            name="tool_wear",
            role=VariableRole.LOAD,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.0,
            time_constant_s=0.0,
        ),
    ]

    equations = [
        # Spindle load proportional to speed * feed rate
        Equation(
            target="spindle_load",
            kind="algebraic",
            func=lambda v: (v["spindle_speed"] / 15000.0) * (v["feed_rate"] / 500.0) * 65.0
            + v.get("tool_wear", 0) * 0.2,
            description="Load = f(speed, feed, tool_wear)",
        ),
        # Coolant temperature ODE: heating from load, exponential cooling
        Equation(
            target="coolant_temp",
            kind="ode",
            func=lambda v: (
                v["spindle_load"] * 0.008  # heat input from machining
                - 0.03 * (v["coolant_temp"] - 22.0)  # cooling to ambient
            ),
            description="dT/dt = heat_input - cooling_rate * (T - T_ambient)",
        ),
        # Tool wear accumulates slowly
        Equation(
            target="tool_wear",
            kind="ode",
            func=lambda v: v["spindle_load"] * 0.0001 if v["spindle_load"] > 5 else 0.0,
            description="d(wear)/dt = load * wear_rate",
        ),
        # Vibration from load + tool wear
        Equation(
            target="vibration",
            kind="algebraic",
            func=lambda v: (
                v["spindle_load"] * 0.05
                + v.get("tool_wear", 0) * 0.08
                + (0.5 if v["spindle_speed"] > 0 else 0.0)
            ),
            description="vibration = f(load, wear, running)",
        ),
        # Part count increments in steady state
        Equation(
            target="part_count",
            kind="ode",
            func=lambda v: 1.0 / 60.0 if v["feed_rate"] > 100 else 0.0,
            description="~1 part per minute when machining",
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
        # Periodic load changes (tool change every ~10 min)
        StateTransition(
            from_state=ProcessState.STEADY_STATE,
            to_state=ProcessState.LOAD_CHANGE,
            condition="time",
            duration_s=600.0,
        ),
        StateTransition(
            from_state=ProcessState.LOAD_CHANGE,
            to_state=ProcessState.STEADY_STATE,
            condition="time",
            duration_s=30.0,
        ),
    ]

    return ProcessModel(
        model_id=MODEL_ID,
        name=MODEL_NAME,
        variables=variables,
        equations=equations,
        transitions=transitions,
        initial_state=ProcessState.COLD_START,
    )


def build_faults() -> list[FaultScenario]:
    """Build fault scenarios for the CNC machining model."""
    return [
        FaultScenario(
            name="tool_breakage",
            effects=[
                FaultEffect("spindle_load", "set", value=110.0, delay_ms=0),
                FaultEffect("vibration", "set", value=20.0, delay_ms=50),
                FaultEffect("spindle_speed", "set", value=0.0, delay_ms=500),
                FaultEffect("feed_rate", "set", value=0.0, delay_ms=500),
            ],
        ),
        FaultScenario(
            name="coolant_failure",
            effects=[
                # Coolant stops flowing — temperature rises
                FaultEffect("coolant_temp", "add", value=2.0, delay_ms=0),
                FaultEffect("coolant_temp", "add", value=5.0, delay_ms=10000),
                FaultEffect("coolant_temp", "add", value=10.0, delay_ms=30000),
            ],
        ),
    ]
