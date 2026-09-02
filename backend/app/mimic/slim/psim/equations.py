# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Equation sets for defining physical relationships between process variables.

Supports two equation kinds:

- **Algebraic**: ``x = f(variables)`` — evaluated directly each step.
- **ODE**: ``dx/dt = f(variables)`` — integrated via forward Euler.

Execution order: algebraic first (so derived values are available to ODEs),
then ODE integration, then all variables step (first-order lag + noise).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .variables import ProcessVariable


@dataclass
class Equation:
    """A single relationship between process variables.

    Attributes:
        target: Name of the variable being computed.
        kind: ``"ode"`` for differential or ``"algebraic"`` for direct.
        func: Callable taking ``dict[str, float]`` (current values) and
              returning a ``float`` — the new value (algebraic) or
              derivative (ODE).
        description: Human-readable explanation.
    """

    target: str
    kind: str  # "ode" or "algebraic"
    func: Callable[[dict[str, float]], float]
    description: str = ""


class EquationSet:
    """Collection of equations defining variable relationships.

    Algebraic equations are evaluated first so that derived values are
    available to ODE equations.  ODEs are integrated via forward Euler.
    """

    def __init__(self, equations: list[Equation] | None = None) -> None:
        self._algebraic: list[Equation] = []
        self._ode: list[Equation] = []
        for eq in equations or []:
            if eq.kind == "algebraic":
                self._algebraic.append(eq)
            else:
                self._ode.append(eq)

    def step(self, variables: dict[str, ProcessVariable], dt_s: float) -> None:
        """Advance all equations by *dt_s* seconds.

        1. Snapshot current values.
        2. Evaluate algebraic equations (set target directly).
        3. Evaluate ODE equations (forward Euler on current value).
        4. Step all variables (first-order lag + noise + clamp).
        """
        if dt_s <= 0:
            return

        # Snapshot current values for equation evaluation
        values: dict[str, float] = {name: var.value for name, var in variables.items()}

        # Algebraic: direct assignment
        for eq in self._algebraic:
            result = eq.func(values)
            var = variables.get(eq.target)
            if var is not None:
                var.set_target(result)
                values[eq.target] = result  # Update snapshot for chaining

        # ODE: forward Euler
        for eq in self._ode:
            derivative = eq.func(values)
            var = variables.get(eq.target)
            if var is not None:
                new_value = var.value + derivative * dt_s
                var.set_target(new_value)

        # Step all variables (apply lag toward target, add noise, clamp)
        for var in variables.values():
            var.step(dt_s)
