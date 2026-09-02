# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Closed-loop heat-exchanger outlet-temperature control.

A second controlled process, in a different domain (thermal), proving the PI
framework generalizes: a steam valve holds outlet temperature at a setpoint
against a periodic heat-demand disturbance. Same believable behaviour — tracks
setpoint, rejects disturbances — via the shared ``pi_loop``.
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

MODEL_ID = "heat_exchanger"
MODEL_NAME = "Heat-Exchanger Temperature Loop"

_THERMAL_GAIN = 0.3
_KP = 3.0
_KI = 0.5


def build_model() -> ProcessModel:
    """Build a PI-controlled heat-exchanger outlet-temperature loop."""
    clk_var, clk_eq = clock()
    variables = [
        clk_var,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="degC",
                        initial_value=60.0, min_value=30.0, max_value=85.0, time_constant_s=0.0),
        ProcessVariable(name="temperature", role=VariableRole.TEMPERATURE, unit="degC",
                        initial_value=60.0, min_value=0.0, max_value=150.0,
                        noise_std=0.08, time_constant_s=0.0),
        ProcessVariable(name="load", role=VariableRole.LOAD, unit="%",
                        initial_value=40.0, min_value=0.0, max_value=100.0,
                        noise_std=0.3, time_constant_s=0.0),
        ProcessVariable(name="steam_valve", role=VariableRole.VALVE_POSITION, unit="%",
                        initial_value=40.0, min_value=0.0, max_value=100.0,
                        noise_std=0.1, time_constant_s=1.0),  # valve travel lag
    ]
    equations = [
        clk_eq,
        Equation(target="load", kind="algebraic",
                 func=diurnal(base=40.0, amplitude=10.0, period_s=70.0),
                 description="periodic heat demand"),
        Equation(target="temperature", kind="ode",
                 func=lambda v: (v["steam_valve"] - v["load"]) * _THERMAL_GAIN,
                 description="dT/dt = (steam - heat demand) * thermal_gain"),
    ]
    pi_vars, pi_eqs = pi_loop(
        measured="temperature", setpoint="setpoint", output="steam_valve",
        kp=_KP, ki=_KI, feedforward="load", integral_limit=50.0,
    )
    variables += pi_vars
    equations += pi_eqs

    return ProcessModel(
        model_id=MODEL_ID, name=MODEL_NAME,
        variables=variables, equations=equations,
        transitions=[], initial_state=ProcessState.STEADY_STATE,
    )
