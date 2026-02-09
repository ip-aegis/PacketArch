"""Process variables with first-order lag dynamics and noise."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .types import ProcessState, VariableRole


@dataclass
class ProcessVariable:
    """A single variable in a process model.

    Evolves toward a target value using first-order lag dynamics::

        alpha = dt / (time_constant + dt)
        value += alpha * (target - value)

    Gaussian sensor noise is added each step. Values are clamped to
    ``[min_value, max_value]``.

    ``state_setpoints`` maps :class:`ProcessState` values to target
    setpoints.  When the state machine transitions, the variable's
    target is updated and it ramps naturally via the lag.
    """

    name: str
    role: VariableRole = VariableRole.TEMPERATURE
    unit: str = ""
    initial_value: float = 0.0
    min_value: float = -1e6
    max_value: float = 1e6
    noise_std: float = 0.0
    time_constant_s: float = 0.0
    state_setpoints: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._value: float = self.initial_value
        self._target: float = self.initial_value

    @property
    def value(self) -> float:
        return self._value

    @property
    def target(self) -> float:
        return self._target

    def set_target(self, target: float) -> None:
        """Set the target value (will be clamped to bounds)."""
        self._target = max(self.min_value, min(self.max_value, target))

    def set_value(self, value: float) -> None:
        """Force the current value (bypasses lag)."""
        self._value = max(self.min_value, min(self.max_value, value))

    def step(self, dt_s: float) -> None:
        """Advance one time step: lag toward target, add noise, clamp."""
        if dt_s <= 0:
            return

        if self.time_constant_s > 0:
            alpha = dt_s / (self.time_constant_s + dt_s)
            self._value += alpha * (self._target - self._value)
        else:
            self._value = self._target

        if self.noise_std > 0:
            self._value += random.gauss(0, self.noise_std)

        self._value = max(self.min_value, min(self.max_value, self._value))

    def apply_state_setpoint(self, state: ProcessState) -> None:
        """Update target from per-state setpoint dict if present."""
        if state.value in self.state_setpoints:
            self.set_target(self.state_setpoints[state.value])

    def reset(self) -> None:
        """Reset to initial conditions."""
        self._value = self.initial_value
        self._target = self.initial_value
