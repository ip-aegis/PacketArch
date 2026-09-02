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
             feedforward: str | None = None, integral_limit: float = 100.0,
             initial_output: float = 0.0):
    integ = f"_{output}_integ"
    seed = max(-integral_limit, min(integral_limit, (initial_output / ki) if ki else 0.0))
    variables = [ProcessVariable(name=integ, role=VariableRole.SETPOINT, unit="",
                                 initial_value=seed, min_value=-integral_limit,
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


def _pump_station() -> ProcessModel:
    clk, clk_eq = _clock()
    variables = [
        clk,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="bar", initial_value=4.0,
                        min_value=1.0, max_value=8.0, time_constant_s=0.0),
        ProcessVariable(name="pressure", role=VariableRole.PRESSURE, unit="bar", initial_value=4.0,
                        min_value=0.0, max_value=10.0, noise_std=0.02, time_constant_s=0.0),
        ProcessVariable(name="demand", role=VariableRole.FLOW_RATE, unit="m3/h", initial_value=120.0,
                        min_value=0.0, max_value=300.0, noise_std=1.0, time_constant_s=0.0),
        ProcessVariable(name="pump_speed", role=VariableRole.SPEED, unit="%", initial_value=60.0,
                        min_value=0.0, max_value=100.0, noise_std=0.1, time_constant_s=1.5),
        ProcessVariable(name="well_level", role=VariableRole.LEVEL, unit="%", initial_value=70.0,
                        min_value=0.0, max_value=100.0, noise_std=0.1, time_constant_s=20.0),
    ]
    equations = [
        clk_eq,
        Equation(target="demand", kind="algebraic", func=_diurnal(120.0, 45.0, 120.0), description="demand"),
        Equation(target="pressure", kind="ode",
                 func=lambda v: (v["pump_speed"] * 0.08) - (v["demand"] * 0.04), description="dP/dt"),
        Equation(target="well_level", kind="algebraic",
                 func=lambda v: 70.0 - 0.15 * (v["demand"] - 120.0), description="well level"),
    ]
    pv, pe = _pi_loop(measured="pressure", setpoint="setpoint", output="pump_speed",
                      kp=8.0, ki=1.2, integral_limit=100.0, initial_output=60.0)
    return ProcessModel(model_id="pump_station", name="Water Pump Station — Pressure Control",
                        variables=variables + pv, equations=equations + pe, transitions=[],
                        initial_state=ProcessState.STEADY_STATE)


def _chemical_reactor() -> ProcessModel:
    clk, clk_eq = _clock()
    variables = [
        clk,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="degC", initial_value=85.0,
                        min_value=40.0, max_value=120.0, time_constant_s=0.0),
        ProcessVariable(name="reactor_temp", role=VariableRole.TEMPERATURE, unit="degC", initial_value=85.0,
                        min_value=0.0, max_value=200.0, noise_std=0.1, time_constant_s=0.0),
        ProcessVariable(name="feed_rate", role=VariableRole.FLOW_RATE, unit="kg/h", initial_value=50.0,
                        min_value=0.0, max_value=100.0, noise_std=0.4, time_constant_s=0.0),
        ProcessVariable(name="coolant_valve", role=VariableRole.VALVE_POSITION, unit="%", initial_value=60.0,
                        min_value=0.0, max_value=100.0, noise_std=0.1, time_constant_s=1.0),
        ProcessVariable(name="pressure", role=VariableRole.PRESSURE, unit="bar", initial_value=2.0,
                        min_value=0.0, max_value=10.0, noise_std=0.02, time_constant_s=5.0),
        ProcessVariable(name="concentration", role=VariableRole.CONCENTRATION, unit="%", initial_value=45.0,
                        min_value=0.0, max_value=100.0, noise_std=0.1, time_constant_s=10.0),
    ]
    equations = [
        clk_eq,
        Equation(target="feed_rate", kind="algebraic", func=_diurnal(50.0, 15.0, 100.0), description="feed"),
        Equation(target="reactor_temp", kind="ode",
                 func=lambda v: v["feed_rate"] * 0.6 - v["coolant_valve"] * 0.5, description="dT/dt"),
        Equation(target="pressure", kind="algebraic",
                 func=lambda v: 2.0 + 0.03 * (v["reactor_temp"] - 85.0), description="pressure"),
        Equation(target="concentration", kind="algebraic",
                 func=lambda v: 45.0 - 0.25 * (v["reactor_temp"] - 85.0), description="concentration"),
    ]
    pv, pe = _pi_loop(measured="reactor_temp", setpoint="setpoint", output="coolant_valve",
                      kp=-4.0, ki=-0.6, integral_limit=150.0, initial_output=60.0)  # reverse-acting (cooling)
    return ProcessModel(model_id="chemical_reactor", name="Exothermic Reactor — Temperature Control",
                        variables=variables + pv, equations=equations + pe, transitions=[],
                        initial_state=ProcessState.STEADY_STATE)


def _compressor_station() -> ProcessModel:
    clk, clk_eq = _clock()
    variables = [
        clk,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="bar", initial_value=60.0,
                        min_value=30.0, max_value=90.0, time_constant_s=0.0),
        ProcessVariable(name="discharge_pressure", role=VariableRole.PRESSURE, unit="bar", initial_value=60.0,
                        min_value=0.0, max_value=120.0, noise_std=0.15, time_constant_s=0.0),
        ProcessVariable(name="throughput", role=VariableRole.FLOW_RATE, unit="MMSCFD", initial_value=200.0,
                        min_value=0.0, max_value=400.0, noise_std=1.5, time_constant_s=0.0),
        ProcessVariable(name="speed", role=VariableRole.SPEED, unit="%", initial_value=65.0,
                        min_value=0.0, max_value=100.0, noise_std=0.1, time_constant_s=2.0),
        ProcessVariable(name="suction_pressure", role=VariableRole.PRESSURE, unit="bar", initial_value=20.0,
                        min_value=0.0, max_value=60.0, noise_std=0.05, time_constant_s=8.0),
        ProcessVariable(name="shaft_power", role=VariableRole.POWER, unit="MW", initial_value=13.0,
                        min_value=0.0, max_value=30.0, noise_std=0.05, time_constant_s=2.0),
    ]
    equations = [
        clk_eq,
        Equation(target="throughput", kind="algebraic", func=_diurnal(200.0, 60.0, 150.0), description="demand"),
        Equation(target="discharge_pressure", kind="ode",
                 func=lambda v: (v["speed"] * 0.18) - (v["throughput"] * 0.06), description="dP/dt"),
        Equation(target="suction_pressure", kind="algebraic",
                 func=lambda v: 20.0 - 0.03 * (v["throughput"] - 200.0), description="suction"),
        Equation(target="shaft_power", kind="algebraic", func=lambda v: 0.2 * v["speed"], description="power"),
    ]
    pv, pe = _pi_loop(measured="discharge_pressure", setpoint="setpoint", output="speed",
                      kp=5.0, ki=1.5, integral_limit=100.0, initial_output=66.0)
    return ProcessModel(model_id="compressor_station", name="Gas Compressor — Discharge Pressure Control",
                        variables=variables + pv, equations=equations + pe, transitions=[],
                        initial_state=ProcessState.STEADY_STATE)


def _power_feeder() -> ProcessModel:
    clk, clk_eq = _clock()
    variables = [
        clk,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="%", initial_value=100.0,
                        min_value=95.0, max_value=105.0, time_constant_s=0.0),
        ProcessVariable(name="voltage", role=VariableRole.LEVEL, unit="%", initial_value=100.0,
                        min_value=90.0, max_value=110.0, noise_std=0.05, time_constant_s=0.0),
        ProcessVariable(name="load", role=VariableRole.LOAD, unit="%", initial_value=55.0,
                        min_value=0.0, max_value=100.0, noise_std=0.4, time_constant_s=0.0),
        ProcessVariable(name="tap", role=VariableRole.POSITION, unit="step", initial_value=3.0,
                        min_value=-16.0, max_value=16.0, noise_std=0.0, time_constant_s=3.0),
        ProcessVariable(name="current", role=VariableRole.FLOW_RATE, unit="A", initial_value=275.0,
                        min_value=0.0, max_value=600.0, noise_std=1.0, time_constant_s=1.0),
        ProcessVariable(name="active_power", role=VariableRole.POWER, unit="MW", initial_value=5.5,
                        min_value=0.0, max_value=15.0, noise_std=0.03, time_constant_s=1.0),
    ]
    equations = [
        clk_eq,
        Equation(target="load", kind="algebraic", func=_diurnal(55.0, 25.0, 140.0), description="load"),
        Equation(target="voltage", kind="ode",
                 func=lambda v: (v["tap"] * 0.06) - (v["load"] - 55.0) * 0.02, description="dV/dt"),
        Equation(target="current", kind="algebraic", func=lambda v: 5.0 * v["load"], description="current"),
        Equation(target="active_power", kind="algebraic", func=lambda v: 0.1 * v["load"], description="power"),
    ]
    pv, pe = _pi_loop(measured="voltage", setpoint="setpoint", output="tap",
                      kp=2.0, ki=0.4, integral_limit=16.0, initial_output=3.0)
    return ProcessModel(model_id="power_feeder", name="Distribution Feeder — Voltage Regulation",
                        variables=variables + pv, equations=equations + pe, transitions=[],
                        initial_state=ProcessState.STEADY_STATE)


_BUILDERS = {
    "tank_level": _tank,
    "tank_level_control": _tank_control,
    "heat_exchanger": _heat_exchanger,
    "pump_station": _pump_station,
    "chemical_reactor": _chemical_reactor,
    "compressor_station": _compressor_station,
    "power_feeder": _power_feeder,
}


def build_process_model(model_id: str) -> ProcessModel:
    if model_id not in _BUILDERS:
        raise KeyError(f"unknown slim process model {model_id!r}")
    return _BUILDERS[model_id]()
