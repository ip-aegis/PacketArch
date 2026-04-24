# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Variable binder — maps process variables to PayloadGenerator sensors.

The binder is the critical integration piece between the process
simulation and the existing traffic generation pipeline.  It pushes
correlated process variable values into each flow's
``PayloadGenerator.states`` dict so that protocol engines read
physically modelled data instead of independent random trends.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .process_model import ProcessModel
from .types import VariableBinding, VariableRole

if TYPE_CHECKING:
    from app.protocol_engines.payload_generator import PayloadGenerator

logger = logging.getLogger(__name__)

# Maps VariableRole to likely sensor profile name patterns
# used for auto-binding heuristics.
_ROLE_NAME_HINTS: dict[VariableRole, list[str]] = {
    VariableRole.TEMPERATURE: ["temp", "temperature"],
    VariableRole.PRESSURE: ["press", "pressure"],
    VariableRole.FLOW_RATE: ["flow", "rate"],
    VariableRole.LEVEL: ["level", "tank"],
    VariableRole.SPEED: ["speed", "rpm"],
    VariableRole.POSITION: ["position", "pos"],
    VariableRole.POWER: ["power", "watt"],
    VariableRole.LOAD: ["load", "torque"],
    VariableRole.VIBRATION: ["vibration", "vib"],
    VariableRole.CONCENTRATION: ["concentration", "ppm", "ph", "chlorine"],
    VariableRole.COUNTER: ["count", "counter", "part"],
    VariableRole.HUMIDITY: ["humidity", "rh"],
    VariableRole.VALVE_POSITION: ["valve", "damper"],
    VariableRole.STATUS: ["status", "state", "run"],
}


class VariableBinder:
    """Binds :class:`ProcessModel` variables to :class:`PayloadGenerator`
    sensor states.

    Two modes:

    1. **Explicit bindings** — a list of :class:`VariableBinding` provided
       by the user or template.
    2. **Auto-binding** — matches variable roles to sensor profiles by name
       pattern or positional order.

    The :meth:`push_values` method writes process variable values directly
    into ``SensorState.current_value`` and sets ``SensorProfile.nominal_value``
    with ``trend_type = STABLE``.  This means the ``PayloadGenerator.get_value()``
    still handles encoding and noise, but the base trend comes from the
    process model.
    """

    def __init__(self, bindings: list[VariableBinding]) -> None:
        self._bindings = bindings
        # Pre-index by flow_id for fast lookup
        self._flow_bindings: dict[
            str, list[tuple[str, str, float, float, float | None, float | None]]
        ] = {}
        for b in bindings:
            self._flow_bindings.setdefault(b.flow_id, []).append(
                (b.variable_name, b.sensor_name, b.scale, b.offset,
                 b.clamp_min, b.clamp_max)
            )

    @property
    def binding_count(self) -> int:
        return len(self._bindings)

    def push_values(
        self,
        models: dict[str, ProcessModel],
        flow_generators: dict[str, PayloadGenerator],
    ) -> None:
        """Push process variable values into PayloadGenerator sensor states.

        For each binding:
        1. Read variable value from the ProcessModel.
        2. Apply scale + offset.
        3. Write directly to ``SensorState.current_value`` and
           ``SensorProfile.nominal_value``.
        4. Set ``SensorProfile.trend_type`` to ``STABLE`` so the
           generator doesn't apply its own trend (noise still applied).
        """
        from app.protocol_engines.payload_generator import TrendType

        for flow_id, bindings in self._flow_bindings.items():
            gen = flow_generators.get(flow_id)
            if gen is None:
                continue

            for var_name, sensor_name, scale, offset, c_min, c_max in bindings:
                # Find variable across all models
                raw_value: float | None = None
                for model in models.values():
                    var = model.variables.get(var_name)
                    if var is not None:
                        raw_value = var.value
                        break
                if raw_value is None:
                    continue

                # Scale and offset
                sensor_value = raw_value * scale + offset

                # Clamp overrides
                if c_min is not None:
                    sensor_value = max(c_min, sensor_value)
                if c_max is not None:
                    sensor_value = min(c_max, sensor_value)

                # Push into PayloadGenerator state
                state = gen.states.get(sensor_name)
                profile = gen.profiles.get(sensor_name)
                if state is not None and profile is not None:
                    state.current_value = sensor_value
                    profile.nominal_value = sensor_value
                    profile.trend_type = TrendType.STABLE

    @classmethod
    def from_dicts(cls, binding_dicts: list[dict[str, Any]]) -> VariableBinder:
        """Create from a list of raw dicts (e.g. from scenario definition)."""
        bindings = [
            VariableBinding(
                variable_name=d["variable_name"],
                flow_id=d["flow_id"],
                sensor_name=d["sensor_name"],
                scale=d.get("scale", 1.0),
                offset=d.get("offset", 0.0),
                clamp_min=d.get("clamp_min"),
                clamp_max=d.get("clamp_max"),
            )
            for d in binding_dicts
        ]
        return cls(bindings)

    @classmethod
    def auto_bind(
        cls,
        models: dict[str, ProcessModel],
        flow_generators: dict[str, PayloadGenerator],
    ) -> VariableBinder:
        """Auto-generate bindings by matching variable roles to sensor names.

        Strategy:
        - Collect all process variables and their roles.
        - For each flow's PayloadGenerator, try to match sensor names to
          variable names or role hints.
        - Fall back to positional binding (first variable → first sensor).
        """
        all_variables: list[tuple[str, Any]] = []
        for model in models.values():
            for var in model.variables.values():
                all_variables.append((var.name, var))

        bindings: list[VariableBinding] = []

        for flow_id, gen in flow_generators.items():
            if gen is None:
                continue

            sensor_names = list(gen.profiles.keys())
            if not sensor_names:
                continue

            bound_sensors: set[str] = set()
            bound_vars: set[str] = set()

            # Pass 1: match by name substring
            for var_name, var in all_variables:
                if var_name in bound_vars:
                    continue
                for sensor_name in sensor_names:
                    if sensor_name in bound_sensors:
                        continue
                    # Check if variable name appears in sensor name or vice versa
                    if var_name in sensor_name or sensor_name in var_name:
                        bindings.append(VariableBinding(
                            variable_name=var_name,
                            flow_id=flow_id,
                            sensor_name=sensor_name,
                        ))
                        bound_sensors.add(sensor_name)
                        bound_vars.add(var_name)
                        break

            # Pass 2: match by role hints
            for var_name, var in all_variables:
                if var_name in bound_vars:
                    continue
                hints = _ROLE_NAME_HINTS.get(var.role, [])
                for sensor_name in sensor_names:
                    if sensor_name in bound_sensors:
                        continue
                    if any(h in sensor_name.lower() for h in hints):
                        bindings.append(VariableBinding(
                            variable_name=var_name,
                            flow_id=flow_id,
                            sensor_name=sensor_name,
                        ))
                        bound_sensors.add(sensor_name)
                        bound_vars.add(var_name)
                        break

            # Pass 3: positional fallback for remaining unbound sensors
            unbound_vars = [
                (vn, v) for vn, v in all_variables if vn not in bound_vars
            ]
            unbound_sensors = [s for s in sensor_names if s not in bound_sensors]
            for (var_name, _), sensor_name in zip(unbound_vars, unbound_sensors):
                bindings.append(VariableBinding(
                    variable_name=var_name,
                    flow_id=flow_id,
                    sensor_name=sensor_name,
                ))

        logger.info("Auto-bound %d process variables to sensors", len(bindings))
        return cls(bindings)
