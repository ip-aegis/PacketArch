# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Slim IEC 60870-5-104 persona server (c104) — substrate-free twin of
``app.mimic.servers.iec104_server.Iec104PersonaServer``.

Controlled station: read-only measurements (M_ME_NC_1) pushed live from the model,
single-commands (C_SC_NA_1) whose received commands feed back. Addressed by IOA.

NB: c104 has no musllinux wheel, so on a bare Alpine node it builds from source
(the deploy bootstrap adds build-base/cmake/python3-dev for iec104 personas).
"""

# NOTE: no `from __future__ import annotations` — c104 validates the on_receive
# callback against the REAL annotation objects; PEP 563 stringization breaks it.

import asyncio
import logging
from typing import Any

import c104

from .named_point import NamedPointProjection
from .spec import PointBinding

logger = logging.getLogger(__name__)


class SlimIec104Server:
    protocol = "iec104"

    def __init__(self, *, bind_ip: str, port: int, common_address: int,
                 projection: NamedPointProjection, sync_interval_s: float = 0.5) -> None:
        self._bind_ip = bind_ip
        self._port = port
        self._ca = common_address
        self._proj = projection
        self._sync_interval = sync_interval_s
        self._server: Any = None
        self._sensors: list = []
        self._sync_task: asyncio.Task | None = None
        self._running = False

    def _command_handler(self, binding: PointBinding):
        proj = self._proj

        def _on_receive(
            point: c104.Point,
            previous_info: c104.Information,
            message: c104.IncomingMessage,
        ) -> c104.ResponseState:  # runs on a c104 I/O thread
            try:
                proj.apply_write(binding, bool(point.value))
                return c104.ResponseState.SUCCESS
            except Exception:  # noqa: BLE001
                logger.debug("iec104 command handling failed", exc_info=True)
                return c104.ResponseState.FAILURE

        return _on_receive

    async def start(self) -> None:
        server = c104.Server(ip=self._bind_ip, port=self._port)
        station = server.add_station(common_address=self._ca)
        for point in self._proj.points:
            if self._proj.is_actuator(point):
                cmd = station.add_point(io_address=point.address, type=c104.Type.C_SC_NA_1)
                cmd.on_receive(callable=self._command_handler(point))
            else:
                meas = station.add_point(io_address=point.address, type=c104.Type.M_ME_NC_1)
                meas.value = float(self._proj.read_value(point))
                self._sensors.append((point, meas))
        server.start()
        self._server = server
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop(), name=f"slim-iec104-{self._port}")
        logger.info("slim iec104 server on %s:%d (CA %d)", self._bind_ip, self._port, self._ca)

    async def _sync_loop(self) -> None:
        while self._running:
            for point, meas in self._sensors:
                try:
                    meas.value = float(self._proj.read_value(point))
                except Exception:  # noqa: BLE001
                    logger.debug("iec104 measurement sync failed", exc_info=True)
            await asyncio.sleep(self._sync_interval)

    async def stop(self) -> None:
        self._running = False
        if self._sync_task is not None:
            self._sync_task.cancel()
        if self._server is not None:
            self._server.stop()
