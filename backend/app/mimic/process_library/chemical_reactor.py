# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Exothermic stirred reactor — PI temperature control via jacket coolant.

The reaction generates heat proportional to feed; a coolant valve removes it. This
is a REVERSE-acting loop (temperature above setpoint → open the coolant valve), so
the PI gains are negative. Reactor pressure and reactant concentration are
correlated read-only sensors. Oil & gas / chemical manufacturing.
"""

from __future__ import annotations

from app.protocol_engines.process_sim import (
    Equation, ProcessModel, ProcessState, ProcessVariable, VariableRole,
)

from .control import clock, diurnal, pi_loop

MODEL_ID = "chemical_reactor"
MODEL_NAME = "Exothermic Reactor — Temperature Control"


def build_model() -> ProcessModel:
    clk_var, clk_eq = clock()
    variables = [
        clk_var,
        ProcessVariable(name="setpoint", role=VariableRole.SETPOINT, unit="degC",
                        initial_value=85.0, min_value=40.0, max_value=120.0, time_constant_s=0.0),
        ProcessVariable(name="reactor_temp", role=VariableRole.TEMPERATURE, unit="degC",
                        initial_value=85.0, min_value=0.0, max_value=200.0,
                        noise_std=0.1, time_constant_s=0.0),
        ProcessVariable(name="feed_rate", role=VariableRole.FLOW_RATE, unit="kg/h",
                        initial_value=50.0, min_value=0.0, max_value=100.0,
                        noise_std=0.4, time_constant_s=0.0),
        ProcessVariable(name="coolant_valve", role=VariableRole.VALVE_POSITION, unit="%",
                        initial_value=60.0, min_value=0.0, max_value=100.0,
                        noise_std=0.1, time_constant_s=1.0),
        ProcessVariable(name="pressure", role=VariableRole.PRESSURE, unit="bar",
                        initial_value=2.0, min_value=0.0, max_value=10.0,
                        noise_std=0.02, time_constant_s=5.0),
        ProcessVariable(name="concentration", role=VariableRole.CONCENTRATION, unit="%",
                        initial_value=45.0, min_value=0.0, max_value=100.0,
                        noise_std=0.1, time_constant_s=10.0),
    ]
    equations = [
        clk_eq,
        Equation(target="feed_rate", kind="algebraic",
                 func=diurnal(base=50.0, amplitude=15.0, period_s=100.0),
                 description="reactor feed cycle"),
        # heat balance: exothermic generation from feed minus jacket cooling
        Equation(target="reactor_temp", kind="ode",
                 func=lambda v: v["feed_rate"] * 0.6 - v["coolant_valve"] * 0.5,
                 description="dT/dt = reaction heat - cooling"),
        Equation(target="pressure", kind="algebraic",
                 func=lambda v: 2.0 + 0.03 * (v["reactor_temp"] - 85.0),
                 description="vapour pressure vs temperature"),
        Equation(target="concentration", kind="algebraic",
                 func=lambda v: 45.0 - 0.25 * (v["reactor_temp"] - 85.0),
                 description="reactant consumed as temperature rises"),
    ]
    # REVERSE-acting PI (negative gains): hotter than setpoint → open coolant.
    pi_vars, pi_eqs = pi_loop(measured="reactor_temp", setpoint="setpoint", output="coolant_valve",
                              kp=-4.0, ki=-0.6, integral_limit=150.0, initial_output=60.0)
    return ProcessModel(model_id=MODEL_ID, name=MODEL_NAME,
                        variables=variables + pi_vars, equations=equations + pi_eqs,
                        transitions=[], initial_state=ProcessState.STEADY_STATE)
