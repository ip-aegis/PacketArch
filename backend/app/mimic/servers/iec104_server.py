# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IEC 60870-5-104 persona server (c104 / iec104-python).

Binds a real IEC-104 controlled station (RTU/substation telecontrol) and exposes
the persona's process values as information objects: read-only measurements
(M_ME_NC_1, short float) pushed live from the model, and single-command points
(C_SC_NA_1) whose received commands feed back into the model. Points are addressed
by IOA (integer), like Modbus registers — so it reuses the shared projection.

Fourth protocol, adding the power/substation vertical and a telecontrol wire shape
(ASDU, common address, cause-of-transmission, interrogation) distinct from Modbus,
OPC UA, and BACnet. c104 runs its own I/O threads, so command handling is
event-based (``on_receive``) rather than polled.
"""

# NOTE: no `from __future__ import annotations` here — c104 validates the
# on_receive callback against the REAL annotation objects (c104.Point etc.),
# which PEP 563 stringization would break.

import asyncio
import logging
from typing import Any

import c104

from ..interfaces import PointBinding, Projection, ProtocolServer

logger = logging.getLogger(__name__)


class Iec104PersonaServer(ProtocolServer):
    """A bound IEC-104 controlled station for one persona."""

    protocol = "iec104"

    def __init__(
        self,
        *,
        bind_ip: str,
        port: int,
        common_address: int,
        projection: Projection,
        sync_interval_s: float = 0.5,
    ) -> None:
        self._bind_ip = bind_ip
        self._port = port
        self._ca = common_address
        self._proj = projection
        self._sync_interval = sync_interval_s
        self._server: c104.Server | None = None
        self._sensors: list[tuple[PointBinding, Any]] = []
        self._sync_task: asyncio.Task | None = None
        self._running = False

    def _command_handler(self, binding: PointBinding):
        proj = self._proj

        # c104 validates the callback signature exactly (param names + annotations).
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
        self._sync_task = asyncio.create_task(self._sync_loop(), name=f"iec104-sync-{self._port}")
        logger.info("iec104 persona server on %s:%d (CA %d)", self._bind_ip, self._port, self._ca)

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
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        if self._server is not None:
            self._server.stop()
        logger.info("iec104 persona server on %s:%d stopped", self._bind_ip, self._port)
