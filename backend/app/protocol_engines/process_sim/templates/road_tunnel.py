# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Road tunnel ventilation and drainage process template.

Models a twin-bore road tunnel's life-safety plant:
traffic volume -> CO and visibility (extinction) in the bore -> jet-fan
speed under proportional control -> CO cleared; seepage/rain inflow ->
drainage sump level -> duty pump cycling on start/stop levels.

Faults act on the model's inputs (fan and pump availability, inflow,
traffic), never on a computed variable: an algebraic equation recomputes
its target every tick, so a fault that ``set`` one would last one tick.

Selected per scenario by ``process_model: "road_tunnel"`` on a template
(the transportation vertical default is the intersection model).
"""

from __future__ import annotations

from ..equations import Equation
from ..faults import FaultEffect, FaultScenario
from ..process_model import ProcessModel
from ..state_machine import StateTransition
from ..types import ProcessState, VariableRole
from ..variables import ProcessVariable

MODEL_ID = "road_tunnel"
MODEL_NAME = "Road Tunnel Ventilation and Drainage"

# Jet fans ramp toward full speed as CO approaches this level (ppm).
CO_CONTROL_PPM = 50.0
# Duty pump starts at this sump level and stops at the lower one (%).
SUMP_START_PCT = 40.0
SUMP_STOP_PCT = 20.0
PUMP_RATED_LPS = 30.0


def build_model() -> ProcessModel:
    variables = [
        ProcessVariable(
            name="traffic_flow", role=VariableRole.COUNTER, unit="veh/min",
            initial_value=10.0, min_value=0.0, max_value=120.0, noise_std=4.0, time_constant_s=30.0,
            state_setpoints={
                ProcessState.COLD_START.value: 10.0,
                ProcessState.WARMING_UP.value: 35.0,
                ProcessState.STEADY_STATE.value: 60.0,
                ProcessState.MAINTENANCE.value: 15.0,
                ProcessState.SHUTDOWN.value: 0.0,
            },
        ),
        ProcessVariable(
            name="co_ppm", role=VariableRole.CONCENTRATION, unit="ppm",
            initial_value=5.0, min_value=0.0, max_value=250.0, noise_std=0.1, time_constant_s=0.0,
        ),
        ProcessVariable(
            name="visibility_k", role=VariableRole.CONCENTRATION, unit="1/km",
            initial_value=1.0, min_value=0.0, max_value=12.0, noise_std=0.01, time_constant_s=0.0,
        ),
        ProcessVariable(
            name="jet_fan_speed", role=VariableRole.SPEED, unit="%",
            initial_value=0.0, min_value=0.0, max_value=100.0, noise_std=0.5, time_constant_s=20.0,
        ),
        ProcessVariable(
            name="air_temperature", role=VariableRole.TEMPERATURE, unit="degC",
            initial_value=14.0, min_value=-10.0, max_value=45.0, noise_std=0.2, time_constant_s=300.0,
        ),
        ProcessVariable(
            name="sump_level", role=VariableRole.LEVEL, unit="%",
            initial_value=25.0, min_value=0.0, max_value=100.0, noise_std=0.02, time_constant_s=0.0,
        ),
        ProcessVariable(
            name="inflow_rate", role=VariableRole.FLOW_RATE, unit="L/s",
            initial_value=4.0, min_value=0.0, max_value=60.0, noise_std=0.2, time_constant_s=120.0,
        ),
        ProcessVariable(
            name="pump_running", role=VariableRole.STATUS, unit="bool",
            initial_value=0.0, min_value=0.0, max_value=1.0,
        ),
        # Availability inputs (1 = healthy). Faults trip these.
        ProcessVariable(
            name="fans_available", role=VariableRole.STATUS, unit="bool",
            initial_value=1.0, min_value=0.0, max_value=1.0,
        ),
        ProcessVariable(
            name="pump_available", role=VariableRole.STATUS, unit="bool",
            initial_value=1.0, min_value=0.0, max_value=1.0,
        ),
        ProcessVariable(
            name="pump_flow", role=VariableRole.FLOW_RATE, unit="L/s",
            initial_value=0.0, min_value=0.0, max_value=80.0, noise_std=0.2, time_constant_s=10.0,
        ),
        ProcessVariable(
            name="lighting_power", role=VariableRole.POWER, unit="kW",
            initial_value=120.0, min_value=0.0, max_value=400.0, noise_std=1.0, time_constant_s=30.0,
            state_setpoints={
                ProcessState.COLD_START.value: 120.0,
                ProcessState.WARMING_UP.value: 180.0,
                ProcessState.STEADY_STATE.value: 240.0,
                ProcessState.MAINTENANCE.value: 300.0,
                ProcessState.SHUTDOWN.value: 60.0,
            },
        ),
    ]

    equations = [
        # Emissions in proportion to traffic; fans dilute.
        Equation(
            target="co_ppm", kind="ode",
            func=lambda v: v["traffic_flow"] * 0.005 - v["co_ppm"] * (0.002 + v["jet_fan_speed"] * 0.0002),
            description="dCO/dt = emissions(traffic) - dilution(fans)",
        ),
        Equation(
            target="visibility_k", kind="ode",
            func=lambda v: v["traffic_flow"] * 0.0003 - v["visibility_k"] * (0.002 + v["jet_fan_speed"] * 0.0002),
            description="dK/dt = particulates(traffic) - dilution(fans)",
        ),
        # Proportional ventilation control on CO (with a 10% idle floor in traffic).
        Equation(
            target="jet_fan_speed", kind="algebraic",
            func=lambda v: v["fans_available"] * min(100.0, max(
                10.0 if v["traffic_flow"] > 5 else 0.0, (v["co_ppm"] / CO_CONTROL_PPM) * 100.0)),
            description="fan% = CO / CO_setpoint * 100 (floor 10% with traffic), 0 when tripped",
        ),
        # Level-switch latch: start at the high level, stop at the low level,
        # otherwise hold. Without the band the pump would chatter every tick.
        Equation(
            target="pump_running", kind="algebraic",
            func=lambda v: 1.0 if v["sump_level"] >= SUMP_START_PCT
            else 0.0 if v["sump_level"] <= SUMP_STOP_PCT else v["pump_running"],
            description="pump latch: on at start level, off at stop level",
        ),
        Equation(
            target="pump_flow", kind="algebraic",
            func=lambda v: v["pump_running"] * v["pump_available"] * PUMP_RATED_LPS,
            description="pump flow = rated flow while running and available",
        ),
        Equation(
            target="sump_level", kind="ode",
            func=lambda v: (v["inflow_rate"] - v["pump_flow"]) * 0.02,
            description="dLevel/dt = (inflow - pumped) / sump capacity",
        ),
    ]

    transitions = [
        StateTransition(from_state=ProcessState.COLD_START, to_state=ProcessState.WARMING_UP,
                        condition="time", duration_s=15.0),
        StateTransition(from_state=ProcessState.WARMING_UP, to_state=ProcessState.STEADY_STATE,
                        condition="time", duration_s=60.0),
    ]

    return ProcessModel(
        model_id=MODEL_ID, name=MODEL_NAME, variables=variables, equations=equations,
        transitions=transitions, initial_state=ProcessState.COLD_START,
    )


def build_faults() -> list[FaultScenario]:
    return [
        # Fans lose supply: CO climbs on its own toward the 250 ppm clamp.
        FaultScenario(name="jet_fan_trip", effects=[
            FaultEffect("fans_available", "set", value=0.0, delay_ms=0),
        ]),
        # Duty pump fails during a storm: the sump fills.
        FaultScenario(name="drainage_pump_failure", effects=[
            FaultEffect("pump_available", "set", value=0.0, delay_ms=0),
            FaultEffect("inflow_rate", "set", value=12.0, delay_ms=0),
        ]),
        # Stopped traffic after a crash: CO and opacity rise, fans saturate.
        FaultScenario(name="incident_congestion", effects=[
            FaultEffect("traffic_flow", "set", value=110.0, delay_ms=0),
        ]),
    ]
