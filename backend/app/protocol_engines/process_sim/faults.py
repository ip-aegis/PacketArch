"""Fault scenarios with causal propagation chains.

A fault is a sequence of effects applied to process variables with
configurable delays, modelling how a real failure cascades through a
physical system.

Example — pump failure::

    FaultScenario(
        name="pump_failure",
        effects=[
            FaultEffect("pump_speed", "set", value=0.0, delay_ms=0),
            FaultEffect("flow_rate", "set", value=0.0, delay_ms=500),
            FaultEffect("tank_level", "multiply", value=0.98, delay_ms=5000),
        ],
    )
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

from .process_model import ProcessModel

logger = logging.getLogger(__name__)


@dataclass
class FaultEffect:
    """A single effect of a fault on a variable.

    Attributes:
        variable_name: Target process variable.
        effect: ``"set"``, ``"multiply"``, or ``"add"``.
        value: Operand for the effect.
        delay_ms: Causal propagation delay after fault activation.
    """

    variable_name: str
    effect: str  # "set", "multiply", "add"
    value: float = 0.0
    delay_ms: float = 0.0

    # Runtime: whether this effect has already been applied
    _applied: bool = False


@dataclass
class FaultScenario:
    """A fault that propagates causally through process variables.

    Attributes:
        name: Human-readable identifier.
        effects: Ordered list of effects with delays.
        trigger: ``"manual"``, ``"time"``, or ``"random"``.
        trigger_time_s: For time-based triggers, activation time.
        trigger_probability: Per-step probability for random triggers.
    """

    name: str
    effects: list[FaultEffect] = field(default_factory=list)
    trigger: str = "manual"
    trigger_time_s: float = 0.0
    trigger_probability: float = 0.0

    _activated_at_ms: float = -1.0
    _active: bool = False

    @property
    def is_active(self) -> bool:
        return self._active

    def activate(self, current_time_ms: float) -> None:
        """Activate the fault at *current_time_ms*."""
        if self._active:
            return
        self._activated_at_ms = current_time_ms
        self._active = True
        for effect in self.effects:
            effect._applied = False
        logger.info("Fault '%s' activated at t=%.1fms", self.name, current_time_ms)

    def check_auto_trigger(
        self, sim_time_s: float, current_time_ms: float,
    ) -> bool:
        """Check whether an automatic trigger condition is met.

        Returns ``True`` if the fault was just activated.
        """
        if self._active:
            return False
        if self.trigger == "time" and sim_time_s >= self.trigger_time_s:
            self.activate(current_time_ms)
            return True
        if self.trigger == "random" and random.random() < self.trigger_probability:
            self.activate(current_time_ms)
            return True
        return False

    def step(
        self,
        models: dict[str, ProcessModel],
        current_time_ms: float,
    ) -> None:
        """Apply pending effects whose delay has elapsed."""
        if not self._active:
            return

        elapsed_ms = current_time_ms - self._activated_at_ms

        for effect in self.effects:
            if effect._applied:
                continue
            if elapsed_ms < effect.delay_ms:
                continue

            # Find the variable in any model
            for model in models.values():
                var = model.variables.get(effect.variable_name)
                if var is None:
                    continue
                if effect.effect == "set":
                    var.set_target(effect.value)
                    var.set_value(effect.value)
                elif effect.effect == "multiply":
                    var.set_target(var.value * effect.value)
                elif effect.effect == "add":
                    var.set_target(var.value + effect.value)
                effect._applied = True
                logger.debug(
                    "Fault '%s' effect: %s %s %.2f (delay=%.0fms)",
                    self.name,
                    effect.effect,
                    effect.variable_name,
                    effect.value,
                    effect.delay_ms,
                )
                break

    def reset(self) -> None:
        """Reset the fault to inactive state."""
        self._active = False
        self._activated_at_ms = -1.0
        for effect in self.effects:
            effect._applied = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "trigger": self.trigger,
            "active": self._active,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FaultScenario:
        effects = [
            FaultEffect(
                variable_name=e["variable_name"],
                effect=e["effect"],
                value=e.get("value", 0.0),
                delay_ms=e.get("delay_ms", 0.0),
            )
            for e in d.get("effects", [])
        ]
        return cls(
            name=d["name"],
            effects=effects,
            trigger=d.get("trigger", "manual"),
            trigger_time_s=d.get("trigger_time_s", 0.0),
            trigger_probability=d.get("trigger_probability", 0.0),
        )
