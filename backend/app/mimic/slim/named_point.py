# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Named-point projection for the slim runtime — the substrate-free twin of
``app.mimic.projections.named_point.NamedPointProjection``.

Shared by the protocols that address by name (OPC UA nodes, BACnet objects) or by
integer IOA (IEC-104). Read-only points take the live model value; actuator points
feed a client write back into the model. Single source of truth: every protocol
projecting the same variable agrees by construction.
"""

from __future__ import annotations

import logging

from .psim import ProcessModel
from .spec import PointBinding

logger = logging.getLogger(__name__)


class NamedPointProjection:
    protocol = "named"

    def __init__(self, model: ProcessModel | None, points: list[PointBinding]) -> None:
        self._model = model
        self.points = points

    @staticmethod
    def node_name(point: PointBinding) -> str:
        return point.name or point.variable or f"pt{point.address}"

    @staticmethod
    def is_actuator(point: PointBinding) -> bool:
        return point.writable and point.source == "actuator"

    def read_value(self, point: PointBinding) -> float:
        if self._model is not None and point.source == "variable" and point.variable:
            return self._model.get_value(point.variable) * point.scale + point.offset
        if point.source == "static":
            return float(point.static_value)
        return 0.0

    def apply_write(self, point: PointBinding, node_value: object) -> None:
        if self._model is None or not point.writable:
            return
        target = point.write_target or point.variable
        if target is None or target not in self._model.variables:
            return
        if isinstance(node_value, bool):
            value = point.write_true_value if node_value else point.write_false_value
        else:
            try:
                raw = float(node_value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return
            value = (raw - point.offset) / point.scale if point.scale else raw
        self._model.variables[target].set_target(value)
        logger.debug("write-back: %s -> %.3f (%s)", target, value, self.node_name(point))
