# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Discrete state machine for process lifecycle management."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from .types import ProcessState
from .variables import ProcessVariable

logger = logging.getLogger(__name__)


@dataclass
class StateTransition:
    """A transition between process states.

    Attributes:
        from_state: Source state.
        to_state: Target state.
        condition: ``"time"``, ``"threshold"``, or ``"random"``.
        duration_s: For time-based transitions, seconds before firing.
        variable: For threshold transitions, which variable to watch.
        threshold: Threshold value for comparison.
        comparison: ``">"`` or ``"<"``.
        probability: Per-step trigger probability for random transitions.
    """

    from_state: ProcessState
    to_state: ProcessState
    condition: str = "time"
    duration_s: float = 0.0
    variable: str = ""
    threshold: float = 0.0
    comparison: str = ">"
    probability: float = 0.0


class ProcessStateMachine:
    """Manages discrete process lifecycle transitions.

    When the state changes, each variable's ``state_setpoints`` dict
    is consulted and the variable target is updated.  The first-order
    lag in :class:`ProcessVariable` handles the ramp naturally.
    """

    def __init__(
        self,
        initial_state: ProcessState,
        transitions: list[StateTransition],
        variables: dict[str, ProcessVariable],
    ) -> None:
        self._current_state = initial_state
        self._transitions = transitions
        self._variables = variables
        self._state_entry_time: float = 0.0
        self._apply_state_setpoints()

    @property
    def current_state(self) -> ProcessState:
        return self._current_state

    def step(self, sim_time_s: float) -> ProcessState | None:
        """Check transitions and advance state if triggered.

        Returns the new state if a transition fired, ``None`` otherwise.
        """
        for trans in self._transitions:
            if trans.from_state != self._current_state:
                continue
            if self._check_condition(trans, sim_time_s):
                old_state = self._current_state
                self._current_state = trans.to_state
                self._state_entry_time = sim_time_s
                self._apply_state_setpoints()
                logger.debug(
                    "Process state: %s -> %s at t=%.1fs",
                    old_state.value,
                    self._current_state.value,
                    sim_time_s,
                )
                return self._current_state
        return None

    def force_state(self, state: ProcessState, sim_time_s: float) -> None:
        """Force transition to *state* (e.g. from deployment phase mapping)."""
        if state == self._current_state:
            return
        old_state = self._current_state
        self._current_state = state
        self._state_entry_time = sim_time_s
        self._apply_state_setpoints()
        logger.debug(
            "Process state forced: %s -> %s at t=%.1fs",
            old_state.value,
            state.value,
            sim_time_s,
        )

    def _check_condition(self, trans: StateTransition, sim_time_s: float) -> bool:
        elapsed = sim_time_s - self._state_entry_time
        if trans.condition == "time":
            return elapsed >= trans.duration_s
        if trans.condition == "threshold":
            var = self._variables.get(trans.variable)
            if var is None:
                return False
            if trans.comparison == ">":
                return var.value > trans.threshold
            return var.value < trans.threshold
        if trans.condition == "random":
            return random.random() < trans.probability
        return False

    def _apply_state_setpoints(self) -> None:
        """Update all variable targets from their per-state setpoint dicts."""
        for var in self._variables.values():
            var.apply_state_setpoint(self._current_state)
