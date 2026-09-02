# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""BACnet/IP persona server (bacpypes3).

Binds a real BACnet/IP device and exposes the persona's process values as BACnet
objects: read-only sensors as Analog Value objects (present-value pushed live from
the model), writable actuators as Binary Value objects (fed back into the model on
change). The Device object carries the identity CV reads — vendor-identifier,
model-name, firmware-revision.

Third protocol behind the shared ``NamedPointProjection`` — building-automation
BACnet is a very different wire (UDP/BVLC/NPDU, Who-Is/I-Am discovery, object
database) from Modbus registers and OPC UA nodes, so it further validates that the
Mimic seams generalize.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.local.device import DeviceObject
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.pdu import Address

from ..interfaces import ProtocolServer
from ..projections.named_point import NamedPointProjection

logger = logging.getLogger(__name__)


def _device_instance(device_id: str) -> int:
    """Stable BACnet device instance (0..4194302) from the persona id."""
    return abs(hash(device_id)) % 4_000_000 + 1


class BacnetPersonaServer(ProtocolServer):
    """A bound BACnet/IP responder for one persona."""

    protocol = "bacnet"

    def __init__(
        self,
        *,
        bind_ip: str,
        port: int,
        projection: NamedPointProjection,
        identity: dict[str, Any],
        device_id: str,
        sync_interval_s: float = 0.5,
    ) -> None:
        self._bind_ip = bind_ip
        self._port = port
        self._proj = projection
        self._identity = identity
        self._device_id = device_id
        self._sync_interval = sync_interval_s
        self._app: NormalApplication | None = None
        self._objs: list[tuple[Any, Any, bool]] = []  # (point, object, is_actuator)
        self._actuator_last: dict[str, Any] = {}
        self._sync_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        vendor_id = int(self._identity.get("vendor_id", 0))
        device = DeviceObject(
            objectIdentifier=("device", _device_instance(self._device_id)),
            objectName=self._identity.get("object_name") or self._identity.get("device_name") or "Device",
            vendorIdentifier=vendor_id,
            modelName=self._identity.get("model_name") or "Device",
            firmwareRevision=str(self._identity.get("firmware") or "1.0"),
            applicationSoftwareVersion=str(self._identity.get("firmware") or "1.0"),
        )
        app = NormalApplication(device, Address(f"{self._bind_ip}/24:{self._port}"))

        analog_i = binary_i = 1
        for point in self._proj.points:
            name = NamedPointProjection.node_name(point)
            if NamedPointProjection.is_actuator(point):
                obj = BinaryValueObject(
                    objectIdentifier=("binaryValue", binary_i),
                    objectName=name, presentValue="inactive",
                )
                binary_i += 1
                self._actuator_last[name] = False
            else:
                obj = AnalogValueObject(
                    objectIdentifier=("analogValue", analog_i),
                    objectName=name, presentValue=float(self._proj.read_value(point)),
                )
                analog_i += 1
            app.add_object(obj)
            self._objs.append((point, obj, NamedPointProjection.is_actuator(point)))

        self._app = app
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop(), name=f"bacnet-sync-{self._port}")
        logger.info("bacnet persona server on %s:%d (device %s)", self._bind_ip, self._port,
                    self._identity.get("model_name"))

    async def _sync_loop(self) -> None:
        while self._running:
            for point, obj, is_actuator in self._objs:
                try:
                    if is_actuator:
                        name = NamedPointProjection.node_name(point)
                        active = str(obj.presentValue) == "active" or obj.presentValue == 1
                        if active != self._actuator_last.get(name):
                            self._proj.apply_write(point, active)
                            self._actuator_last[name] = active
                    else:
                        obj.presentValue = float(self._proj.read_value(point))
                except Exception:  # noqa: BLE001 - one object must not stall the loop
                    logger.debug("bacnet object sync failed", exc_info=True)
            await asyncio.sleep(self._sync_interval)

    async def stop(self) -> None:
        self._running = False
        if self._sync_task is not None:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        if self._app is not None:
            self._app.close()
        logger.info("bacnet persona server on %s:%d stopped", self._bind_ip, self._port)
