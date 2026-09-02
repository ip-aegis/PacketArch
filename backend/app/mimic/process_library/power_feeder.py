# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Distribution feeder — PI bus-voltage regulation via an LTC tap changer.

Bus voltage sags as feeder load rises; a load tap changer boosts it back to the
setpoint. Feeder current and active power track the load — correlated read-only
sensors. Energy / substation vertical; pairs well with IEC-104 / DNP3 personas.
"""

from __future__ import annotations

from app.protocol_engines.process_sim import (
    Equation, ProcessModel, ProcessState, ProcessVariable, VariableRole,
)

from .control import clock, diurnal, pi_loop

MODEL_ID = "power_feeder"
MODEL_NAME = "Distribution Feeder — Voltage Regulation"


def build_model() -> ProcessModel:
    clk_var, clk_eq = clock()
    variables = [
        clk_var,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="%",
                        initial_value=100.0, min_value=95.0, max_value=105.0, time_constant_s=0.0),
        ProcessVariable(name="voltage", role=VariableRole.LEVEL, unit="%",  # bus voltage, % of nominal
                        initial_value=100.0, min_value=90.0, max_value=110.0,
                        noise_std=0.05, time_constant_s=0.0),
        ProcessVariable(name="load", role=VariableRole.LOAD, unit="%",
                        initial_value=55.0, min_value=0.0, max_value=100.0,
                        noise_std=0.4, time_constant_s=0.0),
        ProcessVariable(name="tap", role=VariableRole.POSITION, unit="step",
                        initial_value=3.0, min_value=-16.0, max_value=16.0,
                        noise_std=0.0, time_constant_s=3.0),  # LTC moves slowly
        ProcessVariable(name="current", role=VariableRole.FLOW_RATE, unit="A",
                        initial_value=275.0, min_value=0.0, max_value=600.0,
                        noise_std=1.0, time_constant_s=1.0),
        ProcessVariable(name="active_power", role=VariableRole.POWER, unit="MW",
                        initial_value=5.5, min_value=0.0, max_value=15.0,
                        noise_std=0.03, time_constant_s=1.0),
    ]
    equations = [
        clk_eq,
        Equation(target="load", kind="algebraic",
                 func=diurnal(base=55.0, amplitude=25.0, period_s=140.0),
                 description="feeder load curve"),
        # voltage: tap boost minus load droop
        Equation(target="voltage", kind="ode",
                 func=lambda v: (v["tap"] * 0.06) - (v["load"] - 55.0) * 0.02,
                 description="dV/dt = tap boost - load droop"),
        Equation(target="current", kind="algebraic",
                 func=lambda v: 5.0 * v["load"],
                 description="feeder current vs load"),
        Equation(target="active_power", kind="algebraic",
                 func=lambda v: 0.1 * v["load"],
                 description="active power vs load"),
    ]
    # PI: tap position holds bus voltage at setpoint (voltage low → raise tap).
    pi_vars, pi_eqs = pi_loop(measured="voltage", setpoint="setpoint", output="tap",
                              kp=2.0, ki=0.4, integral_limit=16.0, initial_output=3.0)
    return ProcessModel(model_id=MODEL_ID, name=MODEL_NAME,
                        variables=variables + pi_vars, equations=equations + pi_eqs,
                        transitions=[], initial_state=ProcessState.STEADY_STATE)
