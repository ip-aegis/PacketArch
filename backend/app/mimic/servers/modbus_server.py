# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Modbus TCP persona server (pymodbus 3.8).

Binds a real Modbus TCP socket and answers as the persona's device:

- Register/coil reads and writes resolve through a :class:`ModbusProjection`, so
  values track the live process model and writes feed back into it.
- FC43 / MEI-14 "Read Device Identification" is answered from the shared
  fingerprint identity (VendorName / ProductCode / ProductName / ModelName /
  MajorMinorRevision) — this is what Cyber Vision and ``nmap modbus-discover``
  read to classify the device.
- Malformed PDUs and out-of-range addresses get correct Modbus exceptions
  (pymodbus handles the wire framing), not a crash — a key anti-honeypot tell.

pymodbus's ``ModbusSlaveContext`` offsets every request by +1 before reaching the
data block, so the block maps datastore address ``a`` back to 0-based projection
address ``a - 1`` (the persona's point map is authored 0-based, matching the wire).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pymodbus.datastore import (
    ModbusServerContext,
    ModbusSlaveContext,
    ModbusSparseDataBlock,
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import ModbusTcpServer

from ..interfaces import ProtocolServer
from ..projections.modbus_projection import ModbusProjection

logger = logging.getLogger(__name__)

# Wire-addressable size per space (0..SIZE-1). Reads/writes outside → the server
# returns an IllegalAddress exception, as a real constrained PLC would.
_DEFAULT_SPACE_SIZE = 256


class _LiveBlock(ModbusSparseDataBlock):
    """A pymodbus data block backed live by a :class:`ModbusProjection`.

    ``kind`` is ``"register"`` (16-bit words) or ``"bit"`` (coils/discretes).
    Incoming ``address`` is wire-address + 1 (see module docstring); we serve the
    0-based projection address ``address - 1``.
    """

    def __init__(
        self,
        *,
        projection: ModbusProjection,
        space: str,
        kind: str,
        size: int = _DEFAULT_SPACE_SIZE,
    ) -> None:
        self._projection = projection
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
            return self._projection.read_registers(self._space, base, count)
        return self._projection.read_bits(self._space, base, count)

    def setValues(self, address: int, values: list[Any], use_as_default: bool = False) -> None:
        base = address - 1
        if self._kind == "register":
            self._projection.write_registers(
                self._space, base, [int(v) & 0xFFFF for v in values]
            )
        else:
            self._projection.write_bits(self._space, base, [bool(v) for v in values])


def build_identity(modbus_identity: dict[str, Any], firmware_version: str | None) -> ModbusDeviceIdentification:
    """Build the FC43 device-identification block from the fingerprint identity."""
    identity = ModbusDeviceIdentification()
    identity.VendorName = modbus_identity.get("vendor_name", "")
    identity.ProductCode = modbus_identity.get("product_code", "")
    identity.VendorUrl = modbus_identity.get("vendor_url", "")
    identity.ProductName = modbus_identity.get("product_name", "")
    identity.ModelName = modbus_identity.get("model_name", "")
    identity.MajorMinorRevision = firmware_version or modbus_identity.get(
        "major_minor_revision", ""
    )
    return identity


class ModbusPersonaServer(ProtocolServer):
    """A bound Modbus TCP responder for one persona."""

    protocol = "modbus"

    def __init__(
        self,
        *,
        bind_ip: str,
        port: int,
        unit_id: int,
        projection: ModbusProjection,
        modbus_identity: dict[str, Any],
        firmware_version: str | None = None,
        space_size: int = _DEFAULT_SPACE_SIZE,
    ) -> None:
        self._bind_ip = bind_ip
        self._port = port
        self._unit_id = unit_id
        self._projection = projection
        self._identity = build_identity(modbus_identity, firmware_version)
        self._space_size = space_size
        self._server: ModbusTcpServer | None = None
        self._task: asyncio.Task | None = None

    def _build_context(self) -> ModbusServerContext:
        slave = ModbusSlaveContext(
            di=_LiveBlock(projection=self._projection, space="discrete", kind="bit", size=self._space_size),
            co=_LiveBlock(projection=self._projection, space="coil", kind="bit", size=self._space_size),
            ir=_LiveBlock(projection=self._projection, space="input", kind="register", size=self._space_size),
            hr=_LiveBlock(projection=self._projection, space="holding", kind="register", size=self._space_size),
        )
        # single=False + a unit-id-keyed map so the persona answers on its own
        # unit id and returns a gateway exception for others (realistic routing).
        return ModbusServerContext(slaves={self._unit_id: slave}, single=False)

    async def start(self) -> None:
        context = self._build_context()
        self._server = ModbusTcpServer(
            context,
            identity=self._identity,
            address=(self._bind_ip, self._port),
        )
        self._task = asyncio.create_task(
            self._server.serve_forever(), name=f"modbus-{self._bind_ip}:{self._port}"
        )
        # Let the listener bind before returning.
        await asyncio.sleep(0.1)
        logger.info(
            "modbus persona server listening on %s:%d (unit %d)",
            self._bind_ip,
            self._port,
            self._unit_id,
        )

    async def stop(self) -> None:
        if self._server is not None:
            await self._server.shutdown()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 - best-effort teardown
                pass
        logger.info("modbus persona server on %s:%d stopped", self._bind_ip, self._port)
