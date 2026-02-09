"""Water treatment train process template.

Models a simplified water treatment process:
intake → raw water tank → coagulation/flocculation → filtration →
clearwell → distribution.

Key relationships:
- Tank levels are ODEs (inflow - outflow).
- Turbidity reduction depends on coagulant dose.
- Filter differential pressure increases as filter loads.
- Chlorine residual is a function of dose rate and contact time.
"""

from __future__ import annotations

from ..equations import Equation
from ..faults import FaultEffect, FaultScenario
from ..process_model import ProcessModel
from ..state_machine import StateTransition
from ..types import ProcessState, VariableRole
from ..variables import ProcessVariable

MODEL_ID = "water_treatment"
MODEL_NAME = "Water Treatment Train"


def build_model() -> ProcessModel:
    """Build the water treatment process model."""
    variables = [
        ProcessVariable(
            name="intake_flow",
            role=VariableRole.FLOW_RATE,
            unit="m3/h",
            initial_value=0.0,
            min_value=0.0,
            max_value=500.0,
            noise_std=2.0,
            time_constant_s=5.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 100.0,
                ProcessState.STEADY_STATE.value: 350.0,
                ProcessState.MAINTENANCE.value: 150.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="pump_speed",
            role=VariableRole.SPEED,
            unit="%",
            initial_value=0.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.5,
            time_constant_s=3.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 30.0,
                ProcessState.STEADY_STATE.value: 75.0,
                ProcessState.MAINTENANCE.value: 40.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="raw_water_level",
            role=VariableRole.LEVEL,
            unit="%",
            initial_value=50.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.3,
            time_constant_s=0.0,  # direct ODE, no lag
        ),
        ProcessVariable(
            name="coag_dose_rate",
            role=VariableRole.FLOW_RATE,
            unit="mg/L",
            initial_value=0.0,
            min_value=0.0,
            max_value=50.0,
            noise_std=0.2,
            time_constant_s=2.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 10.0,
                ProcessState.STEADY_STATE.value: 25.0,
                ProcessState.MAINTENANCE.value: 15.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="floc_turbidity",
            role=VariableRole.CONCENTRATION,
            unit="NTU",
            initial_value=8.0,
            min_value=0.0,
            max_value=50.0,
            noise_std=0.3,
            time_constant_s=10.0,
        ),
        ProcessVariable(
            name="filter_dp",
            role=VariableRole.PRESSURE,
            unit="kPa",
            initial_value=5.0,
            min_value=0.0,
            max_value=80.0,
            noise_std=0.2,
            time_constant_s=0.0,
        ),
        ProcessVariable(
            name="clearwell_level",
            role=VariableRole.LEVEL,
            unit="%",
            initial_value=60.0,
            min_value=0.0,
            max_value=100.0,
            noise_std=0.2,
            time_constant_s=0.0,
        ),
        ProcessVariable(
            name="chlorine_residual",
            role=VariableRole.CONCENTRATION,
            unit="mg/L",
            initial_value=0.0,
            min_value=0.0,
            max_value=5.0,
            noise_std=0.05,
            time_constant_s=8.0,
            state_setpoints={
                ProcessState.COLD_START.value: 0.0,
                ProcessState.WARMING_UP.value: 0.5,
                ProcessState.STEADY_STATE.value: 1.8,
                ProcessState.MAINTENANCE.value: 1.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="ph_level",
            role=VariableRole.CONCENTRATION,
            unit="pH",
            initial_value=7.0,
            min_value=5.0,
            max_value=9.0,
            noise_std=0.05,
            time_constant_s=15.0,
            state_setpoints={
                ProcessState.COLD_START.value: 7.0,
                ProcessState.WARMING_UP.value: 7.2,
                ProcessState.STEADY_STATE.value: 7.4,
                ProcessState.MAINTENANCE.value: 7.2,
                ProcessState.SHUTDOWN.value: 7.0,
            },
        ),
    ]

    equations = [
        # Raw water tank level: intake minus pump draw
        Equation(
            target="raw_water_level",
            kind="ode",
            func=lambda v: (
                v["intake_flow"] * 0.005  # inflow contribution
                - v["pump_speed"] * 0.006  # pump draw
            ),
            description="d(level)/dt = intake - pump_draw",
        ),
        # Turbidity reduction from coagulant
        Equation(
            target="floc_turbidity",
            kind="algebraic",
            func=lambda v: max(
                0.1,
                8.0 * (1.0 - min(1.0, v["coag_dose_rate"] / 30.0) * 0.85),
            ) if v["intake_flow"] > 10 else 0.5,
            description="turbidity = raw * (1 - coag_effectiveness)",
        ),
        # Filter DP increases with loading (resets during maintenance)
        Equation(
            target="filter_dp",
            kind="ode",
            func=lambda v: (
                v["floc_turbidity"] * 0.002  # loading from turbidity
                if v["pump_speed"] > 10
                else -0.1  # drain during idle
            ),
            description="d(dp)/dt = loading_rate(turbidity)",
        ),
        # Clearwell level: filtered water in, distribution demand out
        Equation(
            target="clearwell_level",
            kind="ode",
            func=lambda v: (
                v["pump_speed"] * 0.004  # filtered water inflow
                - 0.25  # constant distribution demand
            ),
            description="d(level)/dt = filter_flow - demand",
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
        # Filter backwash cycle every ~30 min
        StateTransition(
            from_state=ProcessState.STEADY_STATE,
            to_state=ProcessState.MAINTENANCE,
            condition="threshold",
            variable="filter_dp",
            threshold=60.0,
            comparison=">",
        ),
        StateTransition(
            from_state=ProcessState.MAINTENANCE,
            to_state=ProcessState.STEADY_STATE,
            condition="time",
            duration_s=120.0,
        ),
        # High turbidity alarm
        StateTransition(
            from_state=ProcessState.STEADY_STATE,
            to_state=ProcessState.ALARM,
            condition="threshold",
            variable="floc_turbidity",
            threshold=15.0,
            comparison=">",
        ),
        StateTransition(
            from_state=ProcessState.ALARM,
            to_state=ProcessState.STEADY_STATE,
            condition="threshold",
            variable="floc_turbidity",
            threshold=5.0,
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
    """Build fault scenarios for the water treatment model."""
    return [
        FaultScenario(
            name="pump_failure",
            effects=[
                FaultEffect("pump_speed", "set", value=0.0, delay_ms=0),
                FaultEffect("clearwell_level", "add", value=-0.5, delay_ms=5000),
                FaultEffect("clearwell_level", "add", value=-1.0, delay_ms=15000),
            ],
        ),
        FaultScenario(
            name="chemical_feed_loss",
            effects=[
                FaultEffect("coag_dose_rate", "set", value=0.0, delay_ms=0),
                FaultEffect("chlorine_residual", "multiply", value=0.5, delay_ms=10000),
                FaultEffect("chlorine_residual", "set", value=0.1, delay_ms=60000),
            ],
        ),
    ]
