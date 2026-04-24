# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""HVAC loop process template for building automation.

Models a single-zone air handling unit (AHU):
setpoint → damper/valve → supply air temperature → zone temperature →
return air temperature.

Includes humidity and fan speed. Thermal dynamics use a simplified
single-zone model with heat loss to ambient.
"""

from __future__ import annotations

from ..equations import Equation
from ..faults import FaultEffect, FaultScenario
from ..process_model import ProcessModel
from ..state_machine import StateTransition
from ..types import ProcessState, VariableRole
from ..variables import ProcessVariable

MODEL_ID = "bms_hvac"
MODEL_NAME = "HVAC AHU Loop"


def build_model() -> ProcessModel:
    """Build the HVAC process model."""
    variables = [
        ProcessVariable(
            name="setpoint",
            role=VariableRole.SETPOINT,
            unit="C",
            initial_value=22.0,
            min_value=18.0,
            max_value=28.0,
            noise_std=0.0,
            time_constant_s=0.0,
            state_setpoints={
                ProcessState.COLD_START.value: 22.0,
                ProcessState.WARMING_UP.value: 22.0,
                ProcessState.STEADY_STATE.value: 22.0,
                ProcessState.MAINTENANCE.value: 22.0,
                ProcessState.SHUTDOWN.value: 18.0,
            },
        ),
        ProcessVariable(
            name="zone_temp",
            role=VariableRole.TEMPERATURE,
            unit="C",
            initial_value=26.0,
            min_value=10.0,
            max_value=40.0,
            noise_std=0.1,
            time_constant_s=0.0,  # direct ODE
        ),
        ProcessVariable(
            name="supply_air_temp",
            role=VariableRole.TEMPERATURE,
            unit="C",
            initial_value=22.0,
            min_value=10.0,
            max_value=35.0,
            noise_std=0.15,
            time_constant_s=5.0,
        ),
        ProcessVariable(
            name="return_air_temp",
            role=VariableRole.TEMPERATURE,
            unit="C",
            initial_value=24.0,
            min_value=10.0,
            max_value=40.0,
            noise_std=0.1,
            time_constant_s=3.0,
        ),
        ProcessVariable(
            name="damper_position",
            role=VariableRole.VALVE_POSITION,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.5,
            time_constant_s=2.0,
        ),
        ProcessVariable(
            name="fan_speed",
            role=VariableRole.SPEED,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.3,
            time_constant_s=3.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 40.0,
                ProcessState.STEADY_STATE.value: 60.0,
                ProcessState.MAINTENANCE.value: 30.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="humidity",
            role=VariableRole.HUMIDITY,
            unit="%RH",
            initial_value=50.0,
            min_value=20.0,
            max_value=80.0,
            noise_std=0.5,
            time_constant_s=20.0,
            state_setpoints={
                ProcessState.COLD_START.value: 55.0,
                ProcessState.WARMING_UP.value: 50.0,
                ProcessState.STEADY_STATE.value: 45.0,
                ProcessState.MAINTENANCE.value: 50.0,
                ProcessState.SHUTDOWN.value: 55.0,
            },
        ),
    ]

    equations = [
        # PID-like damper control: error drives damper position
        Equation(
            target="damper_position",
            kind="algebraic",
            func=lambda v: max(0.0, min(100.0,
                50.0 + (v["zone_temp"] - v["setpoint"]) * 8.0
            )),
            description="damper = 50 + error * gain (cooling mode)",
        ),
        # Supply air temp depends on damper (more open = colder)
        Equation(
            target="supply_air_temp",
            kind="algebraic",
            func=lambda v: (
                15.0 + (100.0 - v["damper_position"]) * 0.12
                if v["fan_speed"] > 10
                else v["zone_temp"]  # no fan = no cooling
            ),
            description="supply_temp = f(damper, fan)",
        ),
        # Zone temperature ODE: supply air cooling vs heat gains
        Equation(
            target="zone_temp",
            kind="ode",
            func=lambda v: (
                (v["supply_air_temp"] - v["zone_temp"])
                * v["fan_speed"] / 100.0
                * 0.02  # airflow coupling
                + 0.005  # internal heat gains (people, equipment)
                + 0.002 * (32.0 - v["zone_temp"])  # envelope heat transfer
            ),
            description="dT/dt = airflow_cooling + heat_gains + envelope",
        ),
        # Return air is zone temp plus duct heat gain
        Equation(
            target="return_air_temp",
            kind="algebraic",
            func=lambda v: v["zone_temp"] + 0.5 if v["fan_speed"] > 10 else v["zone_temp"],
            description="return_temp = zone_temp + duct_gain",
        ),
    ]

    transitions = [
        StateTransition(
            from_state=ProcessState.COLD_START,
            to_state=ProcessState.WARMING_UP,
            condition="time",
            duration_s=10.0,
        ),
        StateTransition(
            from_state=ProcessState.WARMING_UP,
            to_state=ProcessState.STEADY_STATE,
            condition="time",
            duration_s=60.0,
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
    """Build fault scenarios for the HVAC model."""
    return [
        FaultScenario(
            name="fan_failure",
            effects=[
                FaultEffect("fan_speed", "set", value=0.0, delay_ms=0),
                # Zone temp will drift naturally via ODE
            ],
        ),
        FaultScenario(
            name="sensor_drift",
            effects=[
                # Zone temp sensor reads 3C high — causes overcooling
                FaultEffect("zone_temp", "add", value=3.0, delay_ms=0),
            ],
        ),
    ]
