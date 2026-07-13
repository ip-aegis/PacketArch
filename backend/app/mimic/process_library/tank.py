# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Single-tank level loop — the library's first (P0) process model.

A gravity-drained tank with a pump-fed inflow:

    dLevel/dt = (inflow - outflow) * area_gain          [integrator]
    temperature = 22 + 0.05 * (level - 50)              [weakly coupled]

At start inflow == outflow, so the level holds near 50 % with sensor noise. The
``inflow`` variable is the control input: a persona write-back (e.g. a pump coil)
calls ``model.variables["inflow"].set_target(...)``, the pump ramps via its time
constant, and the level then rises or falls through the integrator — a visible,
physically-consistent response to a real client write. ``inflow`` carries no
state setpoints on purpose, so only write-back moves it.
"""

from __future__ import annotations

from app.protocol_engines.process_sim import (
    Equation,
    ProcessModel,
    ProcessState,
    ProcessVariable,
    VariableRole,
)

MODEL_ID = "tank_level"
MODEL_NAME = "Single-Tank Level Loop"

# Control-input targets a pump coil maps onto (L/s). Off drains (< outflow),
# on fills (> outflow), so both directions are demonstrable.
PUMP_ON_INFLOW = 8.0
PUMP_OFF_INFLOW = 0.0
NOMINAL_FLOW = 5.0


def build_model() -> ProcessModel:
    """Build a fresh single-tank level model in steady state."""
    variables = [
        ProcessVariable(
            name="level",
            role=VariableRole.LEVEL,
            unit="%",
            initial_value=50.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.15,
            time_constant_s=0.0,  # pure integrator; dynamics come from the ODE
        ),
        ProcessVariable(
            name="inflow",
            role=VariableRole.FLOW_RATE,
            unit="L/s",
            initial_value=NOMINAL_FLOW,
            min_value=0.0,
            max_value=20.0,
            noise_std=0.05,
            time_constant_s=3.0,  # pump ramp — write-back does not snap
        ),
        ProcessVariable(
            name="outflow",
            role=VariableRole.FLOW_RATE,
            unit="L/s",
            initial_value=NOMINAL_FLOW,
            min_value=0.0,
            max_value=20.0,
            noise_std=0.05,
            time_constant_s=0.0,
        ),
        ProcessVariable(
            name="temperature",
            role=VariableRole.TEMPERATURE,
            unit="degC",
            initial_value=22.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.05,
            time_constant_s=20.0,
        ),
    ]
    equations = [
        Equation(
            target="level",
            kind="ode",
            func=lambda v: (v["inflow"] - v["outflow"]) * 0.8,
            description="dLevel/dt = (inflow - outflow) * area_gain",
        ),
        Equation(
            target="temperature",
            kind="algebraic",
            func=lambda v: 22.0 + 0.05 * (v["level"] - 50.0),
            description="process temperature weakly coupled to level",
        ),
    ]
    return ProcessModel(
        model_id=MODEL_ID,
        name=MODEL_NAME,
        variables=variables,
        equations=equations,
        transitions=[],
        initial_state=ProcessState.STEADY_STATE,
    )
