# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Process simulation engine for correlated sensor values.

Provides physically-modelled process variables that evolve according to
ODE/algebraic equations and a discrete state machine.  Values are pushed
into existing :class:`PayloadGenerator` instances so that protocol engines
read correlated, realistic data without any modification.

Usage::

    from app.protocol_engines.process_sim import (
        ProcessSimConfig,
        ProcessSimController,
        build_from_vertical,
    )

    config = ProcessSimConfig.from_dict(definition.get("process_sim", {}))
    models, faults = build_from_vertical(config.vertical or "manufacturing")
    controller = ProcessSimController(config, models, flow_generators, faults=faults)
    orchestrator.register_process_sim(controller)
"""

from .binder import VariableBinder
from .controller import ProcessSimController
from .equations import Equation, EquationSet
from .faults import FaultEffect, FaultScenario
from .process_model import ProcessModel
from .state_machine import ProcessStateMachine, StateTransition
from .templates import build_from_vertical
from .types import ProcessSimConfig, ProcessState, VariableBinding, VariableRole
from .variables import ProcessVariable

__all__ = [
    "Equation",
    "EquationSet",
    "FaultEffect",
    "FaultScenario",
    "ProcessModel",
    "ProcessSimConfig",
    "ProcessSimController",
    "ProcessState",
    "ProcessStateMachine",
    "StateTransition",
    "VariableBinder",
    "VariableBinding",
    "VariableRole",
    "ProcessVariable",
    "build_from_vertical",
]
