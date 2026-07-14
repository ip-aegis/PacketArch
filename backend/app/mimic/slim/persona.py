# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Slim device persona — composes a process model + protocol servers from a
fully-resolved spec, with no substrate dependency. The off-box analogue of
``app.mimic.persona.DevicePersona``."""

from __future__ import annotations

import asyncio
import logging

from .models import build_process_model
from .spec import ResolvedPersonaSpec

logger = logging.getLogger(__name__)


class SlimPersona:
    def __init__(self, spec: ResolvedPersonaSpec, checkin_url: str | None = None) -> None:
        self.spec = spec
        self._checkin_url = checkin_url
        self._model = build_process_model(spec.process_model_id) if spec.process_model_id else None
        self._servers: list = []
        self._client_tasks: list[asyncio.Task] = []
        self._step_task: asyncio.Task | None = None
        self._built = False
        self._running = False

    @property
    def model(self):
        return self._model

    def build(self) -> None:
        # Protocol libs are imported LAZILY per branch: a node only has the pip dep
        # for the protocol(s) it actually serves (pymodbus / asyncua / bacpypes3 /
        # c104), so importing the others at module load would crash it.
        for binding in self.spec.protocols:
            if binding.protocol == "modbus":
                from .modbus import ModbusProjection, SlimModbusServer
                projection = ModbusProjection(self._model, binding.points)
                self._servers.append(SlimModbusServer(
                    bind_ip=self.spec.bind_ip, port=binding.port, unit_id=binding.unit_id,
                    projection=projection, modbus_identity=binding.identity,
                    firmware=self.spec.firmware_version,
                ))
            elif binding.protocol == "opcua":
                from .named_point import NamedPointProjection
                from .opcua import SlimOpcUaServer
                self._servers.append(SlimOpcUaServer(
                    bind_ip=self.spec.bind_ip, port=binding.port,
                    projection=NamedPointProjection(self._model, binding.points),
                    identity=binding.identity,
                ))
            elif binding.protocol == "bacnet":
                from .bacnet import SlimBacnetServer
                from .named_point import NamedPointProjection
                self._servers.append(SlimBacnetServer(
                    bind_ip=self.spec.bind_ip, port=binding.port,
                    projection=NamedPointProjection(self._model, binding.points),
                    identity=binding.identity, device_id=self.spec.name,
                ))
            elif binding.protocol == "iec104":
                from .iec104 import SlimIec104Server
                from .named_point import NamedPointProjection
                self._servers.append(SlimIec104Server(
                    bind_ip=self.spec.bind_ip, port=binding.port, common_address=binding.unit_id,
                    projection=NamedPointProjection(self._model, binding.points),
                ))
            else:
                logger.warning("slim runtime: protocol %r not supported", binding.protocol)
        self._built = True

    async def start(self) -> None:
        if not self._built:
            self.build()
        self._running = True
        if self._model is not None:
            self._step_task = asyncio.create_task(self._step_loop(), name="slim-step")
        for server in self._servers:
            await server.start()
        # Active-master client loops (e.g. an HMI polling PLC peers). A persona may
        # be client-only (no servers) — a pure master.
        for i, cb in enumerate(self.spec.clients):
            if cb.protocol == "modbus":
                from .client import modbus_client_loop
                self._client_tasks.append(asyncio.create_task(
                    modbus_client_loop(cb, name=self.spec.name, checkin_url=self._checkin_url),
                    name=f"slim-client-{i}"))
            else:
                logger.warning("slim client protocol %r not supported (modbus only)", cb.protocol)
        logger.info("slim persona '%s' online at %s: %d server(s), %d client loop(s)",
                    self.spec.name, self.spec.bind_ip, len(self._servers), len(self._client_tasks))

    async def _step_loop(self) -> None:
        dt = self.spec.step_interval_ms / 1000.0
        while self._running:
            try:
                self._model.step(dt)
            except Exception:  # noqa: BLE001
                logger.exception("slim model step failed")
            await asyncio.sleep(dt)

    async def stop(self) -> None:
        self._running = False
        for task in self._client_tasks:
            task.cancel()
        for server in self._servers:
            await server.stop()
        if self._step_task is not None:
            self._step_task.cancel()
