# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""OPC UA projection: named nodes ↔ process model.

Read-only sensor nodes take their value live from the model (pushed by the
server's sync loop); writable actuator nodes feed back into the model. Same
single-source-of-truth guarantee as the Modbus projection — a level exposed as
both a Modbus register and an OPC UA node resolves to one model variable.
"""

from __future__ import annotations

import logging

from app.protocol_engines.process_sim import ProcessModel

from ..interfaces import PointBinding, Projection

logger = logging.getLogger(__name__)


class OpcUaProjection(Projection):
    """Live OPC UA view over a :class:`ProcessModel`.

    Each :class:`PointBinding` is a node; ``source == "actuator"`` marks a writable
    Boolean command node (drives ``write_target`` via ``write_true/false_value``),
    everything else is a read-only numeric sensor node.
    """

    protocol = "opcua"

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
        """Current numeric value for a read-only sensor node."""
        if self._model is not None and point.source == "variable" and point.variable:
            return self._model.get_value(point.variable) * point.scale + point.offset
        if point.source == "static":
            return float(point.static_value)
        return 0.0

    def apply_write(self, point: PointBinding, node_value: object) -> None:
        """Feed a client write on an actuator node back into the model."""
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
        logger.debug("opcua write-back: %s -> %.3f (%s)", target, value, self.node_name(point))
