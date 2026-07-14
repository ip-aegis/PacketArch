# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Water pump station — PI discharge-pressure control via a VFD pump.

A variable-frequency drive modulates pump speed to hold header pressure at a
setpoint against a diurnal water demand. The wet-well level falls as demand
outruns supply — a correlated read-only sensor. Water/wastewater vertical.
"""

from __future__ import annotations

from app.protocol_engines.process_sim import (
    Equation, ProcessModel, ProcessState, ProcessVariable, VariableRole,
)

from .control import clock, diurnal, pi_loop

MODEL_ID = "pump_station"
MODEL_NAME = "Water Pump Station — Pressure Control"


def build_model() -> ProcessModel:
    clk_var, clk_eq = clock()
    variables = [
        clk_var,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="bar",
                        initial_value=4.0, min_value=1.0, max_value=8.0, time_constant_s=0.0),
        ProcessVariable(name="pressure", role=VariableRole.PRESSURE, unit="bar",
                        initial_value=4.0, min_value=0.0, max_value=10.0,
                        noise_std=0.02, time_constant_s=0.0),
        ProcessVariable(name="demand", role=VariableRole.FLOW_RATE, unit="m3/h",
                        initial_value=120.0, min_value=0.0, max_value=300.0,
                        noise_std=1.0, time_constant_s=0.0),
        ProcessVariable(name="pump_speed", role=VariableRole.SPEED, unit="%",
                        initial_value=60.0, min_value=0.0, max_value=100.0,
                        noise_std=0.1, time_constant_s=1.5),  # VFD ramp
        ProcessVariable(name="well_level", role=VariableRole.LEVEL, unit="%",
                        initial_value=70.0, min_value=0.0, max_value=100.0,
                        noise_std=0.1, time_constant_s=20.0),
    ]
    equations = [
        clk_eq,
        # diurnal water demand (a 120 s cycle stands in for a daily curve)
        Equation(target="demand", kind="algebraic",
                 func=diurnal(base=120.0, amplitude=45.0, period_s=120.0),
                 description="diurnal water demand"),
        # header pressure integrates supply (pump) minus draw (demand)
        Equation(target="pressure", kind="ode",
                 func=lambda v: (v["pump_speed"] * 0.08) - (v["demand"] * 0.04),
                 description="dPressure/dt = pump supply - demand draw"),
        # wet-well level correlated inversely to demand (read-only)
        Equation(target="well_level", kind="algebraic",
                 func=lambda v: 70.0 - 0.15 * (v["demand"] - 120.0),
                 description="wet-well level vs demand"),
    ]
    # PI: pump speed holds pressure at setpoint (no feed-forward — demand is a
    # different scale than the 0-100 % output, so the integral absorbs it).
    pi_vars, pi_eqs = pi_loop(measured="pressure", setpoint="setpoint", output="pump_speed",
                              kp=8.0, ki=1.2, integral_limit=100.0, initial_output=60.0)
    return ProcessModel(model_id=MODEL_ID, name=MODEL_NAME,
                        variables=variables + pi_vars, equations=equations + pi_eqs,
                        transitions=[], initial_state=ProcessState.STEADY_STATE)
