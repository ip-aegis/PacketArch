# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Reusable closed-loop control for the process-model library.

Real industrial values are *controlled*, not free-running: a PLC holds level,
temperature, or pressure at a setpoint and rejects disturbances. Static or
random-walk register values are a documented fingerprinting tell — so Mimic's
flagship models run a PI loop, making values track a setpoint with believable
transients and disturbance rejection.

Everything is expressed with the existing `process_sim` primitives (a PI loop is
just an integral ODE + an algebraic output equation), so this adds control without
touching the shared substrate. `pi_loop` returns the extra variables + equations to
drop into a `ProcessModel`; `clock` gives models a time base for periodic
disturbances (equation funcs see variable values, not sim time).
"""

from __future__ import annotations

import math
from collections.abc import Callable

from app.protocol_engines.process_sim import Equation, ProcessVariable, VariableRole


def clock(name: str = "clock") -> tuple[ProcessVariable, Equation]:
    """A variable that tracks elapsed sim time (d/dt = 1), for time-based
    disturbances inside equation funcs."""
    var = ProcessVariable(name=name, role=VariableRole.COUNTER, unit="s",
                          initial_value=0.0, min_value=0.0, max_value=1e12, time_constant_s=0.0)
    eq = Equation(target=name, kind="ode", func=lambda v: 1.0, description="sim-time clock")
    return var, eq


def diurnal(base: float, amplitude: float, period_s: float, clock_name: str = "clock") -> Callable[[dict], float]:
    """An equation func for a smooth periodic disturbance: base + amplitude·sin(2π·t/period)."""
    def _f(v: dict) -> float:
        return base + amplitude * math.sin(2.0 * math.pi * v.get(clock_name, 0.0) / period_s)
    return _f


def pi_loop(
    *,
    measured: str,
    setpoint: str,
    output: str,
    kp: float,
    ki: float,
    feedforward: str | None = None,
    integral_limit: float = 100.0,
    initial_output: float = 0.0,
) -> tuple[list[ProcessVariable], list[Equation]]:
    """Build a PI controller that drives ``output`` to hold ``measured`` at
    ``setpoint``.

    Creates the integral state variable (bounded ±``integral_limit`` for
    anti-windup) and returns the (variables, equations) to add to the model. The
    caller owns ``measured``/``setpoint`` and the ``output`` variable — clamp the
    actuator range via that variable's ``min_value``/``max_value``. Algebraic
    equations evaluate before ODEs each step, so the output uses the current
    integral and plant state (standard discrete PI).
    """
    integ = f"_{output}_integ"
    # Seed the integral so the loop STARTS at its steady output (output = ki·integ
    # at zero error) — avoids a cold-start transient where the actuator snaps to 0.
    seed = max(-integral_limit, min(integral_limit, (initial_output / ki) if ki else 0.0))
    variables = [
        ProcessVariable(
            name=integ, role=VariableRole.SETPOINT, unit="",
            initial_value=seed, min_value=-integral_limit, max_value=integral_limit,
            time_constant_s=0.0,
        )
    ]

    def _integrate(v: dict) -> float:  # d(integral)/dt = error
        return v[setpoint] - v[measured]

    def _output(v: dict) -> float:  # PI + optional feed-forward (variable clamps range)
        error = v[setpoint] - v[measured]
        ff = v.get(feedforward, 0.0) if feedforward else 0.0
        return kp * error + ki * v[integ] + ff

    equations = [
        Equation(target=integ, kind="ode", func=_integrate, description=f"{output} PI integral"),
        Equation(target=output, kind="algebraic", func=_output, description=f"{output} PI control action"),
    ]
    return variables, equations
