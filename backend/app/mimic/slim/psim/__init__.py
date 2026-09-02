# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Vendored process-sim core for the slim off-box runtime.

These are copies of the pure-Python process-model classes from
``app.protocol_engines.process_sim`` (process_model / variables / equations /
types / state_machine), WITHOUT the package that pulls in the payload generator
+ scapy. Vendoring keeps the Alpine node's runtime dependency-free (stdlib +
pymodbus only), which is what makes a persona fit in a 512 MB node.
"""

from __future__ import annotations

from .equations import Equation, EquationSet
from .process_model import ProcessModel
from .state_machine import ProcessStateMachine, StateTransition
from .types import ProcessState, VariableRole
from .variables import ProcessVariable

__all__ = [
    "Equation", "EquationSet", "ProcessModel", "ProcessState",
    "ProcessStateMachine", "StateTransition", "VariableRole", "ProcessVariable",
]
