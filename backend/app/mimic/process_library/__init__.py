# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Mimic process-model library.

A model-addressable library of parameterized plant models that back device
personas. Built on the shared ``process_sim`` engine (``ProcessModel``,
``ProcessVariable``, ``Equation`` — imported, not copied); the model *definitions*
here are Mimic's own, authored to be write-back-friendly (a client write drives a
model input so the emulated device is controllable).

P0 seeds the library with one model (``tank_level``). Reactor, pump-station,
feeder, etc. slot in as sibling modules registered below — this is a named goal
of the build, not a one-off.
"""

from __future__ import annotations

from app.protocol_engines.process_sim import ProcessModel

from . import heat_exchanger, tank, tank_control

_BUILDERS: dict[str, callable] = {
    tank.MODEL_ID: tank.build_model,
    tank_control.MODEL_ID: tank_control.build_model,
    heat_exchanger.MODEL_ID: heat_exchanger.build_model,
}


def build_process_model(model_id: str) -> ProcessModel:
    """Instantiate a fresh process model by id.

    Raises:
        KeyError: if ``model_id`` is not in the library.
    """
    if model_id not in _BUILDERS:
        raise KeyError(
            f"unknown process model {model_id!r}; available: {sorted(_BUILDERS)}"
        )
    return _BUILDERS[model_id]()


def available_models() -> list[str]:
    """Sorted list of model ids in the library."""
    return sorted(_BUILDERS)
