"""Conveyor and AGV process template for distribution/logistics vertical.

Models a fulfillment center line:
order rate → conveyor speed → package throughput → zone fill level.

Includes AGV fleet utilization and cold storage temperature.
"""

from __future__ import annotations

from ..equations import Equation
from ..faults import FaultEffect, FaultScenario
from ..process_model import ProcessModel
from ..state_machine import StateTransition
from ..types import ProcessState, VariableRole
from ..variables import ProcessVariable

MODEL_ID = "fulfillment_line"
MODEL_NAME = "Fulfillment Conveyor Line"


def build_model() -> ProcessModel:
    """Build the distribution logistics process model."""
    variables = [
        ProcessVariable(
            name="order_rate",
            role=VariableRole.SETPOINT,
            unit="pkg/min",
            initial_value=0.0,
            min_value=0.0,
            max_value=200.0,
            noise_std=0.0,
            time_constant_s=0.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 30.0,
                ProcessState.STEADY_STATE.value: 120.0,
                ProcessState.MAINTENANCE.value: 40.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="conveyor_speed",
            role=VariableRole.SPEED,
            unit="m/s",
            initial_value=0.0,
            min_value=0.0,
            max_value=3.0,
            noise_std=0.02,
            time_constant_s=5.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 1.0,
                ProcessState.STEADY_STATE.value: 2.5,
                ProcessState.MAINTENANCE.value: 0.5,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="throughput",
            role=VariableRole.FLOW_RATE,
            unit="pkg/min",
            initial_value=0.0,
            min_value=0.0,
            max_value=200.0,
            noise_std=3.0,
            time_constant_s=8.0,
        ),
        ProcessVariable(
            name="zone_fill_level",
            role=VariableRole.LEVEL,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=1.0,
            time_constant_s=30.0,
        ),
        ProcessVariable(
            name="agv_utilization",
            role=VariableRole.LOAD,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=2.0,
            time_constant_s=10.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 20.0,
                ProcessState.STEADY_STATE.value: 75.0,
                ProcessState.MAINTENANCE.value: 10.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="cold_storage_temp",
            role=VariableRole.TEMPERATURE,
            unit="C",
            initial_value=-18.0,
            min_value=-25.0,
            max_value=5.0,
            noise_std=0.3,
            time_constant_s=60.0,
            state_setpoints={
                ProcessState.COLD_START.value: 5.0,
                ProcessState.WARMING_UP.value: -10.0,
                ProcessState.STEADY_STATE.value: -18.0,
                ProcessState.MAINTENANCE.value: -15.0,
                ProcessState.SHUTDOWN.value: -5.0,
            },
        ),
    ]

    equations = [
        # Throughput proportional to conveyor speed and order demand
        Equation(
            target="throughput",
            kind="algebraic",
            func=lambda v: min(
                v["order_rate"],
                v["conveyor_speed"] / 2.5 * 120.0  # max 120 at full speed
            ),
            description="throughput = min(demand, conveyor_capacity)",
        ),
        # Zone fill level: accumulates with throughput, drains with dispatch
        Equation(
            target="zone_fill_level",
            kind="ode",
            func=lambda v: (
                v["throughput"] * 0.01  # inbound fill
                - max(0.0, v["zone_fill_level"]) * 0.005  # outbound dispatch
            ),
            description="dFill/dt = inbound - outbound",
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
    """Build fault scenarios for the distribution logistics model."""
    return [
        FaultScenario(
            name="conveyor_jam",
            effects=[
                FaultEffect("conveyor_speed", "set", value=0.0, delay_ms=0),
                FaultEffect("throughput", "set", value=0.0, delay_ms=2000),
                FaultEffect("zone_fill_level", "add", value=20.0, delay_ms=10000),
            ],
        ),
        FaultScenario(
            name="agv_fleet_failure",
            effects=[
                FaultEffect("agv_utilization", "set", value=0.0, delay_ms=0),
                FaultEffect("zone_fill_level", "add", value=15.0, delay_ms=30000),
            ],
        ),
        FaultScenario(
            name="cold_chain_breach",
            effects=[
                FaultEffect("cold_storage_temp", "add", value=10.0, delay_ms=0),
            ],
        ),
    ]
