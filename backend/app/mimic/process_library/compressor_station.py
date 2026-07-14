# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Gas compressor station — PI discharge-pressure control via compressor speed.

The unit ramps speed to hold discharge pressure at a setpoint against a diurnal
throughput demand. Suction pressure sags as throughput rises, and shaft power
tracks speed — both correlated read-only sensors. Oil & gas / pipeline.
"""

from __future__ import annotations

from app.protocol_engines.process_sim import (
    Equation, ProcessModel, ProcessState, ProcessVariable, VariableRole,
)

from .control import clock, diurnal, pi_loop

MODEL_ID = "compressor_station"
MODEL_NAME = "Gas Compressor — Discharge Pressure Control"


def build_model() -> ProcessModel:
    clk_var, clk_eq = clock()
    variables = [
        clk_var,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="bar",
                        initial_value=60.0, min_value=30.0, max_value=90.0, time_constant_s=0.0),
        ProcessVariable(name="discharge_pressure", role=VariableRole.PRESSURE, unit="bar",
                        initial_value=60.0, min_value=0.0, max_value=120.0,
                        noise_std=0.15, time_constant_s=0.0),
        ProcessVariable(name="throughput", role=VariableRole.FLOW_RATE, unit="MMSCFD",
                        initial_value=200.0, min_value=0.0, max_value=400.0,
                        noise_std=1.5, time_constant_s=0.0),
        ProcessVariable(name="speed", role=VariableRole.SPEED, unit="%",
                        initial_value=65.0, min_value=0.0, max_value=100.0,
                        noise_std=0.1, time_constant_s=2.0),
        ProcessVariable(name="suction_pressure", role=VariableRole.PRESSURE, unit="bar",
                        initial_value=20.0, min_value=0.0, max_value=60.0,
                        noise_std=0.05, time_constant_s=8.0),
        ProcessVariable(name="shaft_power", role=VariableRole.POWER, unit="MW",
                        initial_value=13.0, min_value=0.0, max_value=30.0,
                        noise_std=0.05, time_constant_s=2.0),
    ]
    equations = [
        clk_eq,
        Equation(target="throughput", kind="algebraic",
                 func=diurnal(base=200.0, amplitude=60.0, period_s=150.0),
                 description="pipeline throughput demand"),
        Equation(target="discharge_pressure", kind="ode",
                 func=lambda v: (v["speed"] * 0.18) - (v["throughput"] * 0.06),
                 description="dP/dt = compression - draw"),
        Equation(target="suction_pressure", kind="algebraic",
                 func=lambda v: 20.0 - 0.03 * (v["throughput"] - 200.0),
                 description="suction sag vs throughput"),
        Equation(target="shaft_power", kind="algebraic",
                 func=lambda v: 0.2 * v["speed"],
                 description="shaft power vs speed"),
    ]
    # PI: speed holds discharge pressure at setpoint (integral absorbs the demand).
    pi_vars, pi_eqs = pi_loop(measured="discharge_pressure", setpoint="setpoint", output="speed",
                              kp=5.0, ki=1.5, integral_limit=100.0, initial_output=66.0)
    return ProcessModel(model_id=MODEL_ID, name=MODEL_NAME,
                        variables=variables + pi_vars, equations=equations + pi_eqs,
                        transitions=[], initial_state=ProcessState.STEADY_STATE)
