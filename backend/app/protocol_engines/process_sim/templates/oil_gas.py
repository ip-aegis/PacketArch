# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Wellhead production loop process template for oil and gas.

Models a simplified wellhead production system:
choke valve → wellhead pressure → oil/gas flow rates → separator →
pipeline pressure.

Uses the Bernoulli-like flow equation where flow rate is proportional
to choke opening and the square root of the pressure differential.
"""

from __future__ import annotations

import math

from ..equations import Equation
from ..faults import FaultEffect, FaultScenario
from ..process_model import ProcessModel
from ..state_machine import StateTransition
from ..types import ProcessState, VariableRole
from ..variables import ProcessVariable

MODEL_ID = "oil_gas_wellhead"
MODEL_NAME = "Wellhead Production Loop"

# Reservoir pressure (constant for this simplified model)
_RESERVOIR_PRESSURE = 250.0  # bar


def build_model() -> ProcessModel:
    """Build the wellhead production process model."""
    variables = [
        ProcessVariable(
            name="choke_position",
            role=VariableRole.VALVE_POSITION,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.3,
            time_constant_s=5.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 15.0,
                ProcessState.STEADY_STATE.value: 60.0,
                ProcessState.LOAD_CHANGE.value: 40.0,
                ProcessState.MAINTENANCE.value: 10.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="wellhead_pressure",
            role=VariableRole.PRESSURE,
            unit="bar",
            initial_value=_RESERVOIR_PRESSURE,
            min_value=0.0,
            max_value=300.0,
            noise_std=0.5,
            time_constant_s=10.0,
        ),
        ProcessVariable(
            name="wellhead_temp",
            role=VariableRole.TEMPERATURE,
            unit="C",
            initial_value=45.0,
            min_value=20.0,
            max_value=120.0,
            noise_std=0.3,
            time_constant_s=30.0,
            state_setpoints={
                ProcessState.COLD_START.value: 45.0,
                ProcessState.WARMING_UP.value: 55.0,
                ProcessState.STEADY_STATE.value: 75.0,
                ProcessState.MAINTENANCE.value: 55.0,
                ProcessState.SHUTDOWN.value: 45.0,
            },
        ),
        ProcessVariable(
            name="flow_rate_oil",
            role=VariableRole.FLOW_RATE,
            unit="bbl/d",
            initial_value=0.0,
            min_value=0.0,
            max_value=2000.0,
            noise_std=5.0,
            time_constant_s=3.0,
        ),
        ProcessVariable(
            name="flow_rate_gas",
            role=VariableRole.FLOW_RATE,
            unit="MSCF/d",
            initial_value=0.0,
            min_value=0.0,
            max_value=5000.0,
            noise_std=10.0,
            time_constant_s=3.0,
        ),
        ProcessVariable(
            name="separator_level",
            role=VariableRole.LEVEL,
            unit="%",
            initial_value=30.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.5,
            time_constant_s=0.0,
        ),
        ProcessVariable(
            name="pipeline_pressure",
            role=VariableRole.PRESSURE,
            unit="bar",
            initial_value=40.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.3,
            time_constant_s=15.0,
            state_setpoints={
                ProcessState.COLD_START.value: 40.0,
                ProcessState.WARMING_UP.value: 45.0,
                ProcessState.STEADY_STATE.value: 55.0,
                ProcessState.MAINTENANCE.value: 45.0,
                ProcessState.SHUTDOWN.value: 40.0,
            },
        ),
        ProcessVariable(
            name="h2s_level",
            role=VariableRole.CONCENTRATION,
            unit="ppm",
            initial_value=5.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.5,
            time_constant_s=10.0,
            state_setpoints={
                ProcessState.COLD_START.value: 5.0,
                ProcessState.WARMING_UP.value: 8.0,
                ProcessState.STEADY_STATE.value: 12.0,
                ProcessState.MAINTENANCE.value: 8.0,
                ProcessState.SHUTDOWN.value: 5.0,
            },
        ),
    ]

    equations = [
        # Wellhead pressure drops as choke opens (more flow = less pressure)
        Equation(
            target="wellhead_pressure",
            kind="algebraic",
            func=lambda v: _RESERVOIR_PRESSURE - v["choke_position"] * 1.5,
            description="WHP = reservoir_P - choke_drop",
        ),
        # Oil flow: Bernoulli-like — proportional to choke * sqrt(delta_P)
        Equation(
            target="flow_rate_oil",
            kind="algebraic",
            func=lambda v: (
                v["choke_position"] / 100.0
                * 15.0
                * math.sqrt(max(0.1, v["wellhead_pressure"] - v["pipeline_pressure"]))
            ),
            description="flow = choke * Cv * sqrt(dP)",
        ),
        # Gas flow correlated with oil (GOR ~2.5)
        Equation(
            target="flow_rate_gas",
            kind="algebraic",
            func=lambda v: v["flow_rate_oil"] * 2.5,
            description="gas = oil * GOR",
        ),
        # Separator level: oil inflow minus outlet
        Equation(
            target="separator_level",
            kind="ode",
            func=lambda v: (
                v["flow_rate_oil"] * 0.001  # oil inflow
                - 0.8  # outlet pump (constant rate)
            ),
            description="d(level)/dt = inflow - outlet",
        ),
    ]

    transitions = [
        StateTransition(
            from_state=ProcessState.COLD_START,
            to_state=ProcessState.WARMING_UP,
            condition="time",
            duration_s=15.0,
        ),
        StateTransition(
            from_state=ProcessState.WARMING_UP,
            to_state=ProcessState.STEADY_STATE,
            condition="time",
            duration_s=120.0,
        ),
        # Choke adjustment every ~20 min
        StateTransition(
            from_state=ProcessState.STEADY_STATE,
            to_state=ProcessState.LOAD_CHANGE,
            condition="time",
            duration_s=1200.0,
        ),
        StateTransition(
            from_state=ProcessState.LOAD_CHANGE,
            to_state=ProcessState.STEADY_STATE,
            condition="time",
            duration_s=60.0,
        ),
        # High separator level alarm
        StateTransition(
            from_state=ProcessState.STEADY_STATE,
            to_state=ProcessState.ALARM,
            condition="threshold",
            variable="separator_level",
            threshold=90.0,
            comparison=">",
        ),
        StateTransition(
            from_state=ProcessState.ALARM,
            to_state=ProcessState.STEADY_STATE,
            condition="threshold",
            variable="separator_level",
            threshold=60.0,
            comparison="<",
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
    """Build fault scenarios for the wellhead model."""
    return [
        FaultScenario(
            name="choke_stuck",
            effects=[
                # Choke valve locks in current position — can't adjust
                FaultEffect("choke_position", "set", value=60.0, delay_ms=0),
            ],
        ),
        FaultScenario(
            name="pipeline_leak",
            effects=[
                FaultEffect("pipeline_pressure", "multiply", value=0.7, delay_ms=0),
                FaultEffect("pipeline_pressure", "multiply", value=0.5, delay_ms=10000),
                # Increased flow through leak
                FaultEffect("flow_rate_oil", "multiply", value=1.3, delay_ms=5000),
            ],
        ),
    ]
