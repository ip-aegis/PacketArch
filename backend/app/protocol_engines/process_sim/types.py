"""Core types for the process simulation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProcessState(str, Enum):
    """Discrete process lifecycle states."""

    COLD_START = "cold_start"
    WARMING_UP = "warming_up"
    STEADY_STATE = "steady_state"
    LOAD_CHANGE = "load_change"
    ALARM = "alarm"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"


class VariableRole(str, Enum):
    """Semantic role of a process variable for auto-binding."""

    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    FLOW_RATE = "flow_rate"
    LEVEL = "level"
    SPEED = "speed"
    POSITION = "position"
    POWER = "power"
    SETPOINT = "setpoint"
    VALVE_POSITION = "valve_position"
    STATUS = "status"
    COUNTER = "counter"
    CONCENTRATION = "concentration"
    LOAD = "load"
    VIBRATION = "vibration"
    HUMIDITY = "humidity"


@dataclass
class VariableBinding:
    """Maps a process variable to a PayloadGenerator sensor in a flow.

    Attributes:
        variable_name: Name in the ProcessModel (e.g. ``"tank_level"``)
        flow_id: Target flow ID in the orchestrator
        sensor_name: Sensor name in the flow's PayloadGenerator (e.g. ``"reg_0"``)
        scale: Multiply process value by this to get sensor-domain value
        offset: Add to scaled value
        clamp_min: Optional override of sensor profile lower clamp
        clamp_max: Optional override of sensor profile upper clamp
    """

    variable_name: str
    flow_id: str
    sensor_name: str
    scale: float = 1.0
    offset: float = 0.0
    clamp_min: float | None = None
    clamp_max: float | None = None


@dataclass
class ProcessSimConfig:
    """Top-level configuration for process simulation.

    Deserialized from the scenario definition ``process_sim`` key.
    """

    enabled: bool = False
    vertical: str | None = None
    template_id: str | None = None
    models: list[dict[str, Any]] = field(default_factory=list)
    bindings: list[dict[str, Any]] = field(default_factory=list)
    faults: list[dict[str, Any]] = field(default_factory=list)
    step_interval_ms: float = 100.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProcessSimConfig:
        if not d:
            return cls()
        return cls(
            enabled=d.get("enabled", False),
            vertical=d.get("vertical"),
            template_id=d.get("template_id"),
            models=d.get("models", []),
            bindings=d.get("bindings", []),
            faults=d.get("faults", []),
            step_interval_ms=d.get("step_interval_ms", 100.0),
        )
