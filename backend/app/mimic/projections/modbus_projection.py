# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Modbus projection: register/coil space ↔ process model.

Reads resolve live model values and scale them into 16-bit register counts (or
bits); writes to writable points feed back into the model as setpoints, closing
the control loop. Addressing is 0-based within each of the four Modbus spaces
(``holding``, ``input``, ``coil``, ``discrete``); the server binds these at
protocol addresses via zero-based mode.
"""

from __future__ import annotations

import logging
import threading

from app.protocol_engines.process_sim import ProcessModel

from ..interfaces import PointBinding, Projection

logger = logging.getLogger(__name__)

_REGISTER_SPACES = frozenset({"holding", "input"})
_BIT_SPACES = frozenset({"coil", "discrete"})
_U16 = 0xFFFF


class ModbusProjection(Projection):
    """Live Modbus view over a :class:`ProcessModel`."""

    protocol = "modbus"

    def __init__(self, model: ProcessModel, points: list[PointBinding]) -> None:
        self._model = model
        self._by_addr: dict[tuple[str, int], PointBinding] = {
            (p.space, p.address): p for p in points
        }
        self._counters: dict[tuple[str, int], int] = {}
        # Last-written state for actuator bits so a client reads back what it
        # wrote (a real coil holds its commanded state), while the write also
        # drives the model.
        self._bit_state: dict[tuple[str, int], bool] = {}
        self._lock = threading.Lock()

    # -- reads ------------------------------------------------------------- #

    def read_registers(self, space: str, address: int, count: int) -> list[int]:
        """Return ``count`` 16-bit register values starting at ``address``."""
        with self._lock:
            return [
                self._register_at(space, a) for a in range(address, address + count)
            ]

    def read_bits(self, space: str, address: int, count: int) -> list[bool]:
        """Return ``count`` bit values starting at ``address``."""
        with self._lock:
            return [self._bit_at(space, a) for a in range(address, address + count)]

    def _register_at(self, space: str, address: int) -> int:
        point = self._by_addr.get((space, address))
        if point is None:
            return 0
        raw = int(round(self._resolve(point) * point.scale + point.offset))
        return max(0, min(_U16, raw))

    def _bit_at(self, space: str, address: int) -> bool:
        point = self._by_addr.get((space, address))
        if point is None:
            return False
        # Actuator coil (writable, no read variable): reflect the commanded state.
        if point.writable and point.source != "variable":
            return self._bit_state.get((space, address), False)
        if point.source == "variable" and point.variable is None:
            return self._bit_state.get((space, address), False)
        return self._resolve(point) >= 0.5

    def _resolve(self, point: PointBinding) -> float:
        if point.source == "variable" and point.variable is not None:
            return self._model.get_value(point.variable)
        if point.source == "static":
            return float(point.static_value)
        if point.source == "counter":
            key = (point.space, point.address)
            self._counters[key] = self._counters.get(key, 0) + 1
            return float(self._counters[key] & _U16)
        return 0.0

    # -- writes (closed-loop feedback into the model) ---------------------- #

    def write_registers(self, space: str, address: int, values: list[int]) -> None:
        with self._lock:
            for offset, raw in enumerate(values):
                self._write_register(space, address + offset, raw)

    def write_bits(self, space: str, address: int, values: list[bool]) -> None:
        with self._lock:
            for offset, bit in enumerate(values):
                self._write_bit(space, address + offset, bool(bit))

    def _write_register(self, space: str, address: int, raw: int) -> None:
        point = self._by_addr.get((space, address))
        if point is None or not point.writable:
            return
        target = point.write_target or point.variable
        if target is None or target not in self._model.variables:
            return
        engineering = (raw - point.offset) / point.scale if point.scale else raw
        self._model.variables[target].set_target(engineering)
        logger.debug("write-back: %s -> %.3f (reg %s@%d)", target, engineering, space, address)

    def _write_bit(self, space: str, address: int, bit: bool) -> None:
        point = self._by_addr.get((space, address))
        if point is None or not point.writable:
            return
        self._bit_state[(space, address)] = bit
        target = point.write_target or point.variable
        if target is None or target not in self._model.variables:
            return
        value = point.write_true_value if bit else point.write_false_value
        self._model.variables[target].set_target(value)
        logger.debug("write-back: %s -> %.3f (bit %s@%d=%s)", target, value, space, address, bit)
