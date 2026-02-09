"""Complete physical process model combining variables, equations, and state machine."""

from __future__ import annotations

import logging
from typing import Any

from .equations import Equation, EquationSet
from .state_machine import ProcessStateMachine, StateTransition
from .types import ProcessState
from .variables import ProcessVariable

logger = logging.getLogger(__name__)


class ProcessModel:
    """A complete physical process model with correlated variables.

    Combines:
    - :class:`ProcessVariable` instances (state holders with lag dynamics)
    - :class:`EquationSet` (physical relationships — algebraic + ODE)
    - :class:`ProcessStateMachine` (discrete lifecycle transitions)

    Multiple ``ProcessModel`` instances can run independently within a
    single scenario (e.g. a cooling loop and a production loop).
    """

    def __init__(
        self,
        model_id: str,
        name: str,
        variables: list[ProcessVariable],
        equations: list[Equation] | None = None,
        transitions: list[StateTransition] | None = None,
        initial_state: ProcessState = ProcessState.COLD_START,
    ) -> None:
        self.model_id = model_id
        self.name = name
        self.variables: dict[str, ProcessVariable] = {v.name: v for v in variables}
        self._equations = EquationSet(equations)
        self._state_machine = ProcessStateMachine(
            initial_state,
            transitions or [],
            self.variables,
        )
        self._sim_time_s: float = 0.0

    @property
    def state(self) -> ProcessState:
        return self._state_machine.current_state

    @property
    def sim_time_s(self) -> float:
        return self._sim_time_s

    def step(self, dt_s: float) -> ProcessState | None:
        """Advance the model by *dt_s* seconds.

        1. Advance simulation clock.
        2. Check state machine transitions (may change variable targets).
        3. Evaluate equations (algebraic then ODE).
        4. All variables step (lag + noise + clamp).

        Returns the new :class:`ProcessState` if a transition fired,
        ``None`` otherwise.
        """
        self._sim_time_s += dt_s

        # State transitions may change variable setpoints
        new_state = self._state_machine.step(self._sim_time_s)

        # Equations update targets (algebraic) and integrate (ODE)
        # This also calls var.step() for all variables
        self._equations.step(self.variables, dt_s)

        return new_state

    def get_value(self, variable_name: str) -> float:
        """Get the current value of a variable."""
        var = self.variables.get(variable_name)
        return var.value if var is not None else 0.0

    def force_state(self, state: ProcessState) -> None:
        """Force the state machine to a specific state."""
        self._state_machine.force_state(state, self._sim_time_s)

    def get_snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot for status reporting."""
        return {
            "model_id": self.model_id,
            "name": self.name,
            "state": self.state.value,
            "sim_time_s": round(self._sim_time_s, 2),
            "variables": {
                name: {
                    "value": round(var.value, 4),
                    "target": round(var.target, 4),
                    "unit": var.unit,
                }
                for name, var in self.variables.items()
            },
        }

    def reset(self) -> None:
        """Reset all variables and simulation clock to initial conditions."""
        for var in self.variables.values():
            var.reset()
        self._sim_time_s = 0.0
