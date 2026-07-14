# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Slim process-model library (mirrors app.mimic.process_library, on vendored psim).

A reusable PI-control framework + the tank / controlled-tank / heat-exchanger
models, so an off-box persona produces the same believable, controlled values as
on-box — without any heavy dependency.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from .psim import Equation, ProcessModel, ProcessState, ProcessVariable, VariableRole


def _clock(name: str = "clock") -> tuple[ProcessVariable, Equation]:
    var = ProcessVariable(name=name, role=VariableRole.COUNTER, unit="s",
                          initial_value=0.0, min_value=0.0, max_value=1e12, time_constant_s=0.0)
    return var, Equation(target=name, kind="ode", func=lambda v: 1.0, description="clock")


def _diurnal(base: float, amplitude: float, period_s: float, clock_name: str = "clock") -> Callable[[dict], float]:
    def _f(v: dict) -> float:
        return base + amplitude * math.sin(2.0 * math.pi * v.get(clock_name, 0.0) / period_s)
    return _f


def _pi_loop(*, measured: str, setpoint: str, output: str, kp: float, ki: float,
             feedforward: str | None = None, integral_limit: float = 100.0):
    integ = f"_{output}_integ"
    variables = [ProcessVariable(name=integ, role=VariableRole.SETPOINT, unit="",
                                 initial_value=0.0, min_value=-integral_limit,
                                 max_value=integral_limit, time_constant_s=0.0)]

    def _integrate(v: dict) -> float:
        return v[setpoint] - v[measured]

    def _output(v: dict) -> float:
        ff = v.get(feedforward, 0.0) if feedforward else 0.0
        return kp * (v[setpoint] - v[measured]) + ki * v[integ] + ff

    equations = [
        Equation(target=integ, kind="ode", func=_integrate, description=f"{output} PI integral"),
        Equation(target=output, kind="algebraic", func=_output, description=f"{output} PI control"),
    ]
    return variables, equations


def _tank() -> ProcessModel:
    variables = [
        ProcessVariable(name="level", role=VariableRole.LEVEL, unit="%", initial_value=50.0,
                        min_value=0.0, max_value=100.0, noise_std=0.15, time_constant_s=0.0),
        ProcessVariable(name="inflow", role=VariableRole.FLOW_RATE, unit="L/s", initial_value=5.0,
                        min_value=0.0, max_value=20.0, noise_std=0.05, time_constant_s=3.0),
        ProcessVariable(name="outflow", role=VariableRole.FLOW_RATE, unit="L/s", initial_value=5.0,
                        min_value=0.0, max_value=20.0, noise_std=0.05, time_constant_s=0.0),
        ProcessVariable(name="temperature", role=VariableRole.TEMPERATURE, unit="degC", initial_value=22.0,
                        min_value=0.0, max_value=100.0, noise_std=0.05, time_constant_s=20.0),
    ]
    equations = [
        Equation(target="level", kind="ode", func=lambda v: (v["inflow"] - v["outflow"]) * 0.8,
                 description="dLevel/dt"),
        Equation(target="temperature", kind="algebraic", func=lambda v: 22.0 + 0.05 * (v["level"] - 50.0),
                 description="temp coupled to level"),
    ]
    return ProcessModel(model_id="tank_level", name="Single-Tank Level Loop", variables=variables,
                        equations=equations, transitions=[], initial_state=ProcessState.STEADY_STATE)


def _tank_control() -> ProcessModel:
    clk, clk_eq = _clock()
    variables = [
        clk,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="%", initial_value=50.0,
                        min_value=5.0, max_value=95.0, time_constant_s=0.0),
        ProcessVariable(name="level", role=VariableRole.LEVEL, unit="%", initial_value=50.0,
                        min_value=0.0, max_value=100.0, noise_std=0.12, time_constant_s=0.0),
        ProcessVariable(name="outflow", role=VariableRole.FLOW_RATE, unit="L/s", initial_value=5.0,
                        min_value=0.0, max_value=20.0, noise_std=0.05, time_constant_s=0.0),
        ProcessVariable(name="inflow", role=VariableRole.FLOW_RATE, unit="L/s", initial_value=5.0,
                        min_value=0.0, max_value=20.0, noise_std=0.05, time_constant_s=0.5),
        ProcessVariable(name="temperature", role=VariableRole.TEMPERATURE, unit="degC", initial_value=22.0,
                        min_value=0.0, max_value=100.0, noise_std=0.05, time_constant_s=15.0),
    ]
    equations = [
        clk_eq,
        Equation(target="outflow", kind="algebraic", func=_diurnal(5.0, 2.0, 90.0), description="demand"),
        Equation(target="temperature", kind="algebraic", func=lambda v: 22.0 + 0.06 * (v["level"] - 50.0),
                 description="temp coupled"),
        Equation(target="level", kind="ode", func=lambda v: (v["inflow"] - v["outflow"]) * 0.5,
                 description="dLevel/dt"),
    ]
    pv, pe = _pi_loop(measured="level", setpoint="setpoint", output="inflow", kp=1.5, ki=0.3,
                      feedforward="outflow", integral_limit=30.0)
    return ProcessModel(model_id="tank_level_control", name="Single-Tank Level Control Loop",
                        variables=variables + pv, equations=equations + pe, transitions=[],
                        initial_state=ProcessState.STEADY_STATE)


def _heat_exchanger() -> ProcessModel:
    clk, clk_eq = _clock()
    variables = [
        clk,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="degC", initial_value=60.0,
                        min_value=30.0, max_value=85.0, time_constant_s=0.0),
        ProcessVariable(name="temperature", role=VariableRole.TEMPERATURE, unit="degC", initial_value=60.0,
                        min_value=0.0, max_value=150.0, noise_std=0.08, time_constant_s=0.0),
        ProcessVariable(name="load", role=VariableRole.LOAD, unit="%", initial_value=40.0,
                        min_value=0.0, max_value=100.0, noise_std=0.3, time_constant_s=0.0),
        ProcessVariable(name="steam_valve", role=VariableRole.VALVE_POSITION, unit="%", initial_value=40.0,
                        min_value=0.0, max_value=100.0, noise_std=0.1, time_constant_s=1.0),
    ]
    equations = [
        clk_eq,
        Equation(target="load", kind="algebraic", func=_diurnal(40.0, 10.0, 70.0), description="heat demand"),
        Equation(target="temperature", kind="ode", func=lambda v: (v["steam_valve"] - v["load"]) * 0.3,
                 description="dT/dt"),
    ]
    pv, pe = _pi_loop(measured="temperature", setpoint="setpoint", output="steam_valve", kp=3.0, ki=0.5,
                      feedforward="load", integral_limit=50.0)
    return ProcessModel(model_id="heat_exchanger", name="Heat-Exchanger Temperature Loop",
                        variables=variables + pv, equations=equations + pe, transitions=[],
                        initial_state=ProcessState.STEADY_STATE)


_BUILDERS = {
    "tank_level": _tank,
    "tank_level_control": _tank_control,
    "heat_exchanger": _heat_exchanger,
}


def build_process_model(model_id: str) -> ProcessModel:
    if model_id not in _BUILDERS:
        raise KeyError(f"unknown slim process model {model_id!r}")
    return _BUILDERS[model_id]()
