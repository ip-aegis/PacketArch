# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Slim Modbus projection + server (pymodbus 3.8), decoupled from the substrate.

Same behaviour as the on-box Modbus server — register/coil reads and writes
resolve through the process model, FC43 identity comes from the RESOLVED
modbus_identity dict — but with no fingerprint_applicator dependency.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSparseDataBlock
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import ModbusTcpServer

from .psim import ProcessModel
from .spec import PointBinding

logger = logging.getLogger(__name__)
_U16 = 0xFFFF
_SPACE_SIZE = 256


class ModbusProjection:
    """Live Modbus view over a process model (holding/input registers, coils)."""

    def __init__(self, model: ProcessModel | None, points: list[PointBinding]) -> None:
        self._model = model
        self._by_addr = {(p.space, p.address): p for p in points}
        self._bit_state: dict[tuple[str, int], bool] = {}
        self._lock = threading.Lock()

    def read_registers(self, space: str, address: int, count: int) -> list[int]:
        with self._lock:
            return [self._reg(space, a) for a in range(address, address + count)]

    def read_bits(self, space: str, address: int, count: int) -> list[bool]:
        with self._lock:
            return [self._bit(space, a) for a in range(address, address + count)]

    def write_registers(self, space: str, address: int, values: list[int]) -> None:
        with self._lock:
            for off, raw in enumerate(values):
                self._write_reg(space, address + off, raw)

    def write_bits(self, space: str, address: int, values: list[bool]) -> None:
        with self._lock:
            for off, bit in enumerate(values):
                self._write_bit(space, address + off, bool(bit))

    def _resolve(self, p: PointBinding) -> float:
        if self._model is not None and p.source == "variable" and p.variable:
            return self._model.get_value(p.variable)
        if p.source == "static":
            return float(p.static_value)
        return 0.0

    def _reg(self, space: str, address: int) -> int:
        p = self._by_addr.get((space, address))
        if p is None:
            return 0
        return max(0, min(_U16, int(round(self._resolve(p) * p.scale + p.offset))))

    def _bit(self, space: str, address: int) -> bool:
        p = self._by_addr.get((space, address))
        if p is None:
            return False
        if p.writable and (p.source != "variable" or p.variable is None):
            return self._bit_state.get((space, address), False)
        return self._resolve(p) >= 0.5

    def _write_reg(self, space: str, address: int, raw: int) -> None:
        p = self._by_addr.get((space, address))
        if p is None or not p.writable or self._model is None:
            return
        target = p.write_target or p.variable
        if target and target in self._model.variables:
            eng = (raw - p.offset) / p.scale if p.scale else raw
            self._model.variables[target].set_target(eng)

    def _write_bit(self, space: str, address: int, bit: bool) -> None:
        p = self._by_addr.get((space, address))
        if p is None or not p.writable:
            return
        self._bit_state[(space, address)] = bit
        if self._model is None:
            return
        target = p.write_target or p.variable
        if target and target in self._model.variables:
            self._model.variables[target].set_target(p.write_true_value if bit else p.write_false_value)


class _LiveBlock(ModbusSparseDataBlock):
    def __init__(self, *, projection: ModbusProjection, space: str, kind: str, size: int = _SPACE_SIZE) -> None:
        self._proj = projection
        self._space = space
        self._kind = kind
        self._size = size
        super().__init__({0: 0}, mutable=True)

    def validate(self, address: int, count: int = 1) -> bool:
        base = address - 1
        return base >= 0 and (base + count) <= self._size

    def getValues(self, address: int, count: int = 1) -> list[Any]:
        base = address - 1
        if self._kind == "register":
            return self._proj.read_registers(self._space, base, count)
        return self._proj.read_bits(self._space, base, count)

    def setValues(self, address: int, values: list[Any], use_as_default: bool = False) -> None:
        base = address - 1
        if self._kind == "register":
            self._proj.write_registers(self._space, base, [int(v) & 0xFFFF for v in values])
        else:
            self._proj.write_bits(self._space, base, [bool(v) for v in values])


def _identity(modbus_identity: dict[str, Any], firmware: str) -> ModbusDeviceIdentification:
    ident = ModbusDeviceIdentification()
    ident.VendorName = modbus_identity.get("vendor_name", "")
    ident.ProductCode = modbus_identity.get("product_code", "")
    ident.VendorUrl = modbus_identity.get("vendor_url", "")
    ident.ProductName = modbus_identity.get("product_name", "")
    ident.ModelName = modbus_identity.get("model_name", "")
    ident.MajorMinorRevision = firmware or modbus_identity.get("major_minor_revision", "")
    return ident


class SlimModbusServer:
    protocol = "modbus"

    def __init__(self, *, bind_ip: str, port: int, unit_id: int,
                 projection: ModbusProjection, modbus_identity: dict[str, Any], firmware: str = "") -> None:
        self._bind_ip = bind_ip
        self._port = port
        self._unit_id = unit_id
        self._proj = projection
        self._ident = _identity(modbus_identity, firmware)
        self._server: ModbusTcpServer | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        slave = ModbusSlaveContext(
            di=_LiveBlock(projection=self._proj, space="discrete", kind="bit"),
            co=_LiveBlock(projection=self._proj, space="coil", kind="bit"),
            ir=_LiveBlock(projection=self._proj, space="input", kind="register"),
            hr=_LiveBlock(projection=self._proj, space="holding", kind="register"),
        )
        context = ModbusServerContext(slaves={self._unit_id: slave}, single=False)
        self._server = ModbusTcpServer(context, identity=self._ident, address=(self._bind_ip, self._port))
        self._task = asyncio.create_task(self._server.serve_forever(), name=f"slim-modbus-{self._port}")
        await asyncio.sleep(0.1)
        logger.info("slim modbus server on %s:%d (unit %d)", self._bind_ip, self._port, self._unit_id)

    async def stop(self) -> None:
        if self._server is not None:
            await self._server.shutdown()
        if self._task is not None:
            self._task.cancel()
