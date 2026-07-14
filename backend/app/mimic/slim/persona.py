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
from .modbus import ModbusProjection, SlimModbusServer
from .spec import ResolvedPersonaSpec

logger = logging.getLogger(__name__)


class SlimPersona:
    def __init__(self, spec: ResolvedPersonaSpec) -> None:
        self.spec = spec
        self._model = build_process_model(spec.process_model_id) if spec.process_model_id else None
        self._servers: list = []
        self._step_task: asyncio.Task | None = None
        self._running = False

    @property
    def model(self):
        return self._model

    def build(self) -> None:
        for binding in self.spec.protocols:
            if binding.protocol == "modbus":
                projection = ModbusProjection(self._model, binding.points)
                self._servers.append(SlimModbusServer(
                    bind_ip=self.spec.bind_ip, port=binding.port, unit_id=binding.unit_id,
                    projection=projection, modbus_identity=binding.identity,
                    firmware=self.spec.firmware_version,
                ))
            else:
                logger.warning("slim runtime: protocol %r not supported (modbus only)", binding.protocol)

    async def start(self) -> None:
        if not self._servers:
            self.build()
        self._running = True
        if self._model is not None:
            self._step_task = asyncio.create_task(self._step_loop(), name="slim-step")
        for server in self._servers:
            await server.start()
        logger.info("slim persona '%s' online at %s: %d server(s)",
                    self.spec.name, self.spec.bind_ip, len(self._servers))

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
        for server in self._servers:
            await server.stop()
        if self._step_task is not None:
            self._step_task.cancel()
