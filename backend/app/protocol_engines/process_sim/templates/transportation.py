"""Traffic signal control process template for transportation vertical.

Models an intersection signal controller:
signal phase cycle → vehicle queue length → average speed →
detector occupancy.

Includes pedestrian demand and coordination offset for arterial timing.
"""

from __future__ import annotations

from ..equations import Equation
from ..faults import FaultEffect, FaultScenario
from ..process_model import ProcessModel
from ..state_machine import StateTransition
from ..types import ProcessState, VariableRole
from ..variables import ProcessVariable

MODEL_ID = "traffic_signal"
MODEL_NAME = "Intersection Signal Control"


def build_model() -> ProcessModel:
    """Build the traffic signal process model."""
    variables = [
        ProcessVariable(
            name="cycle_length",
            role=VariableRole.SETPOINT,
            unit="s",
            initial_value=90.0,
            min_value=60.0,
            max_value=180.0,
            noise_std=0.0,
            time_constant_s=0.0,
            state_setpoints={
                ProcessState.COLD_START.value: 90.0,
                ProcessState.WARMING_UP.value: 90.0,
                ProcessState.STEADY_STATE.value: 120.0,
                ProcessState.MAINTENANCE.value: 90.0,
                ProcessState.SHUTDOWN.value: 90.0,
            },
        ),
        ProcessVariable(
            name="vehicle_count",
            role=VariableRole.COUNTER,
            unit="veh/min",
            initial_value=0.0,
            min_value=0.0,
            max_value=60.0,
            noise_std=2.0,
            time_constant_s=5.0,
            state_setpoints={
                ProcessState.COLD_START.value: 5.0,
                ProcessState.WARMING_UP.value: 15.0,
                ProcessState.STEADY_STATE.value: 30.0,
                ProcessState.MAINTENANCE.value: 20.0,
                ProcessState.SHUTDOWN.value: 5.0,
            },
        ),
        ProcessVariable(
            name="queue_length",
            role=VariableRole.LEVEL,
            unit="veh",
            initial_value=0.0,
            min_value=0.0,
            max_value=50.0,
            noise_std=1.0,
            time_constant_s=10.0,
        ),
        ProcessVariable(
            name="average_speed",
            role=VariableRole.SPEED,
            unit="mph",
            initial_value=35.0,
            min_value=0.0,
            max_value=65.0,
            noise_std=3.0,
            time_constant_s=5.0,
            state_setpoints={
                ProcessState.COLD_START.value: 35.0,
                ProcessState.WARMING_UP.value: 30.0,
                ProcessState.STEADY_STATE.value: 25.0,
                ProcessState.MAINTENANCE.value: 30.0,
                ProcessState.SHUTDOWN.value: 35.0,
            },
        ),
        ProcessVariable(
            name="detector_occupancy",
            role=VariableRole.LOAD,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=2.0,
            time_constant_s=3.0,
        ),
        ProcessVariable(
            name="ped_demand",
            role=VariableRole.COUNTER,
            unit="calls/min",
            initial_value=0.0,
            min_value=0.0,
            max_value=10.0,
            noise_std=0.5,
            time_constant_s=1.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 1.0,
                ProcessState.STEADY_STATE.value: 3.0,
                ProcessState.MAINTENANCE.value: 2.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
    ]

    equations = [
        # Queue length: builds with traffic volume, drains with cycle
        Equation(
            target="queue_length",
            kind="ode",
            func=lambda v: (
                v["vehicle_count"] * 0.1  # arrival rate
                - max(0.0, v["queue_length"]) * (90.0 / max(60.0, v["cycle_length"])) * 0.08
            ),
            description="dQ/dt = arrivals - departures_per_cycle",
        ),
        # Detector occupancy proportional to queue
        Equation(
            target="detector_occupancy",
            kind="algebraic",
            func=lambda v: min(100.0, (v["queue_length"] / 50.0) * 100.0),
            description="occupancy% = queue / capacity * 100",
        ),
        # Average speed inversely related to queue length
        Equation(
            target="average_speed",
            kind="algebraic",
            func=lambda v: max(5.0, 45.0 - v["queue_length"] * 0.6),
            description="speed = free_flow - congestion_effect",
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
            duration_s=30.0,
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
    """Build fault scenarios for the traffic signal model."""
    return [
        FaultScenario(
            name="detector_failure",
            effects=[
                FaultEffect("detector_occupancy", "set", value=0.0, delay_ms=0),
                FaultEffect("vehicle_count", "set", value=0.0, delay_ms=0),
            ],
        ),
        FaultScenario(
            name="signal_stuck_red",
            effects=[
                FaultEffect("queue_length", "add", value=15.0, delay_ms=0),
                FaultEffect("average_speed", "set", value=0.0, delay_ms=5000),
            ],
        ),
        FaultScenario(
            name="coordination_loss",
            effects=[
                FaultEffect("queue_length", "add", value=10.0, delay_ms=0),
                FaultEffect("average_speed", "add", value=-10.0, delay_ms=3000),
            ],
        ),
    ]
