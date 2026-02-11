"""Power generation process template for energy/power vertical.

Models a synchronous generator unit:
governor setpoint → turbine speed → generator frequency → active power (MW)
Exciter controls voltage/reactive power.

Includes transformer loading and grid frequency deviation.
"""

from __future__ import annotations

from ..equations import Equation
from ..faults import FaultEffect, FaultScenario
from ..process_model import ProcessModel
from ..state_machine import StateTransition
from ..types import ProcessState, VariableRole
from ..variables import ProcessVariable

MODEL_ID = "power_generation"
MODEL_NAME = "Synchronous Generator Unit"


def build_model() -> ProcessModel:
    """Build the power generation process model."""
    variables = [
        ProcessVariable(
            name="power_setpoint",
            role=VariableRole.SETPOINT,
            unit="MW",
            initial_value=0.0,
            min_value=0.0,
            max_value=200.0,
            noise_std=0.0,
            time_constant_s=0.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 50.0,
                ProcessState.STEADY_STATE.value: 160.0,
                ProcessState.LOAD_CHANGE.value: 120.0,
                ProcessState.MAINTENANCE.value: 80.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="active_power",
            role=VariableRole.POWER,
            unit="MW",
            initial_value=0.0,
            min_value=0.0,
            max_value=200.0,
            noise_std=0.5,
            time_constant_s=10.0,
        ),
        ProcessVariable(
            name="grid_frequency",
            role=VariableRole.SPEED,
            unit="Hz",
            initial_value=60.0,
            min_value=59.5,
            max_value=60.5,
            noise_std=0.005,
            time_constant_s=2.0,
        ),
        ProcessVariable(
            name="generator_voltage",
            role=VariableRole.POWER,
            unit="kV",
            initial_value=13.8,
            min_value=12.0,
            max_value=15.0,
            noise_std=0.02,
            time_constant_s=1.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 13.8,
                ProcessState.STEADY_STATE.value: 13.8,
                ProcessState.MAINTENANCE.value: 13.8,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="turbine_speed",
            role=VariableRole.SPEED,
            unit="RPM",
            initial_value=0.0,
            min_value=0.0,
            max_value=3700.0,
            noise_std=1.0,
            time_constant_s=15.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 3600.0,
                ProcessState.STEADY_STATE.value: 3600.0,
                ProcessState.MAINTENANCE.value: 3600.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="transformer_loading",
            role=VariableRole.LOAD,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=120.0,
            noise_std=0.3,
            time_constant_s=5.0,
        ),
        ProcessVariable(
            name="exhaust_temp",
            role=VariableRole.TEMPERATURE,
            unit="C",
            initial_value=25.0,
            min_value=20.0,
            max_value=650.0,
            noise_std=2.0,
            time_constant_s=30.0,
            state_setpoints={
                ProcessState.COLD_START.value: 25.0,
                ProcessState.WARMING_UP.value: 350.0,
                ProcessState.STEADY_STATE.value: 550.0,
                ProcessState.MAINTENANCE.value: 400.0,
                ProcessState.SHUTDOWN.value: 25.0,
            },
        ),
    ]

    equations = [
        # Active power tracks setpoint with governor droop
        Equation(
            target="active_power",
            kind="ode",
            func=lambda v: (v["power_setpoint"] - v["active_power"]) * 0.05,
            description="dP/dt = governor_response * error",
        ),
        # Grid frequency: deviation proportional to load-generation mismatch
        Equation(
            target="grid_frequency",
            kind="algebraic",
            func=lambda v: 60.0 + (v["active_power"] - v["power_setpoint"]) * 0.002,
            description="freq = 60Hz + droop_response",
        ),
        # Transformer loading proportional to active power
        Equation(
            target="transformer_loading",
            kind="algebraic",
            func=lambda v: (v["active_power"] / 200.0) * 100.0,
            description="loading% = MW / rated_MW * 100",
        ),
    ]

    transitions = [
        StateTransition(
            from_state=ProcessState.COLD_START,
            to_state=ProcessState.WARMING_UP,
            condition="time",
            duration_s=30.0,
        ),
        StateTransition(
            from_state=ProcessState.WARMING_UP,
            to_state=ProcessState.STEADY_STATE,
            condition="time",
            duration_s=120.0,
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
    """Build fault scenarios for the power generation model."""
    return [
        FaultScenario(
            name="governor_failure",
            effects=[
                FaultEffect("active_power", "set", value=0.0, delay_ms=0),
                FaultEffect("turbine_speed", "add", value=100.0, delay_ms=5000),
            ],
        ),
        FaultScenario(
            name="transformer_overload",
            effects=[
                FaultEffect("transformer_loading", "set", value=115.0, delay_ms=0),
                FaultEffect("exhaust_temp", "add", value=50.0, delay_ms=10000),
            ],
        ),
        FaultScenario(
            name="grid_frequency_deviation",
            effects=[
                FaultEffect("grid_frequency", "add", value=-0.3, delay_ms=0),
            ],
        ),
    ]
