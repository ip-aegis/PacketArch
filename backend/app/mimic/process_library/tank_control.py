# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Closed-loop tank level control — the flagship "believable values" model.

A PI controller adjusts the inflow valve to hold tank level at a setpoint against
a periodic outflow demand. Unlike the open-loop ``tank_level`` model (values
random-walk unless driven), here the level TRACKS a setpoint and REJECTS
disturbances — the way a real controlled process behaves, which is what makes the
register values credible over time to a skilled observer.

Client interaction is realistic too: the writable point is the LEVEL SETPOINT
(write 60 → the loop drives level to 60 %), as an operator would change it — not a
raw pump on/off.
"""

from __future__ import annotations

from app.protocol_engines.process_sim import (
    Equation,
    ProcessModel,
    ProcessState,
    ProcessVariable,
    VariableRole,
)

from .control import clock, diurnal, pi_loop

MODEL_ID = "tank_level_control"
MODEL_NAME = "Single-Tank Level Control Loop"

_AREA_GAIN = 0.5        # L/s → %/s for a nominal tank
_KP = 1.5
_KI = 0.3


def build_model() -> ProcessModel:
    """Build a PI-controlled single-tank level loop in steady state."""
    clk_var, clk_eq = clock()
    variables = [
        clk_var,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="%",
                        initial_value=50.0, min_value=5.0, max_value=95.0, time_constant_s=0.0),
        ProcessVariable(name="level", role=VariableRole.LEVEL, unit="%",
                        initial_value=50.0, min_value=0.0, max_value=100.0,
                        noise_std=0.12, time_constant_s=0.0),
        ProcessVariable(name="outflow", role=VariableRole.FLOW_RATE, unit="L/s",
                        initial_value=5.0, min_value=0.0, max_value=20.0,
                        noise_std=0.05, time_constant_s=0.0),
        ProcessVariable(name="inflow", role=VariableRole.FLOW_RATE, unit="L/s",
                        initial_value=5.0, min_value=0.0, max_value=20.0,
                        noise_std=0.05, time_constant_s=0.5),  # valve travel lag
        ProcessVariable(name="temperature", role=VariableRole.TEMPERATURE, unit="degC",
                        initial_value=22.0, min_value=0.0, max_value=100.0,
                        noise_std=0.05, time_constant_s=15.0),
    ]
    equations = [
        clk_eq,
        # periodic outflow demand (a 90 s consumption cycle) — the disturbance
        Equation(target="outflow", kind="algebraic",
                 func=diurnal(base=5.0, amplitude=2.0, period_s=90.0),
                 description="periodic outflow demand"),
        # temperature weakly coupled to level (a correlated read-only sensor)
        Equation(target="temperature", kind="algebraic",
                 func=lambda v: 22.0 + 0.06 * (v["level"] - 50.0),
                 description="process temperature coupled to level"),
        # plant: level integrates net flow
        Equation(target="level", kind="ode",
                 func=lambda v: (v["inflow"] - v["outflow"]) * _AREA_GAIN,
                 description="dLevel/dt = (inflow - outflow) * area_gain"),
    ]
    # PI loop: inflow valve holds level at setpoint, feed-forwarding the demand.
    pi_vars, pi_eqs = pi_loop(
        measured="level", setpoint="setpoint", output="inflow",
        kp=_KP, ki=_KI, feedforward="outflow", integral_limit=30.0,
    )
    variables += pi_vars
    equations += pi_eqs

    return ProcessModel(
        model_id=MODEL_ID, name=MODEL_NAME,
        variables=variables, equations=equations,
        transitions=[], initial_state=ProcessState.STEADY_STATE,
    )
