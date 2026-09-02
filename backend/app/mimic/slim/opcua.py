# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Slim OPC UA persona server (asyncua) — substrate-free twin of
``app.mimic.servers.opcua_server.OpcUaPersonaServer``.

Binds a real OPC UA endpoint; read-only sensor nodes are pushed live from the
model, writable actuator nodes feed back on client change. Identity (manufacturer,
product, software version) is written to the composite BuildInfo node (ns=0;i=2260)
so a browsing client / CV reads the resolved device.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

from asyncua import Server, ua

from .named_point import NamedPointProjection

logger = logging.getLogger(__name__)
_BUILD_DATE = datetime.datetime(2024, 1, 1)


class SlimOpcUaServer:
    protocol = "opcua"

    def __init__(self, *, bind_ip: str, port: int, projection: NamedPointProjection,
                 identity: dict[str, Any], sync_interval_s: float = 0.5) -> None:
        self._bind_ip = bind_ip
        self._port = port
        self._proj = projection
        self._identity = identity
        self._sync_interval = sync_interval_s
        self._server: Server | None = None
        self._nodes: list[tuple[Any, Any]] = []
        self._actuator_last: dict[str, Any] = {}
        self._sync_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        vendor = self._identity.get("vendor") or "PacketArch"
        model = self._identity.get("model_name") or "Device"
        firmware = self._identity.get("firmware") or "1.0"
        app_uri = self._identity.get("application_uri") or f"urn:packetarch:{model}".replace(" ", "")

        server = Server()
        await server.init()
        server.set_endpoint(f"opc.tcp://{self._bind_ip}:{self._port}/packetarch/server/")
        server.set_server_name(f"{vendor} {model}")
        server.set_application_uri(app_uri)
        idx = await server.register_namespace(app_uri)
        objects = server.get_objects_node()
        dev = await objects.add_object(idx, self._identity.get("device_name") or model)

        for point in self._proj.points:
            name = NamedPointProjection.node_name(point)
            if NamedPointProjection.is_actuator(point):
                node = await dev.add_variable(idx, name, False, ua.VariantType.Boolean)
                await node.set_writable()
                self._actuator_last[name] = False
            else:
                node = await dev.add_variable(idx, name, float(self._proj.read_value(point)),
                                              ua.VariantType.Double)
            self._nodes.append((point, node))

        await server.start()
        build = ua.BuildInfo()
        build.ProductUri = self._identity.get("product_uri") or app_uri
        build.ManufacturerName = vendor
        build.ProductName = model
        build.SoftwareVersion = firmware
        build.BuildNumber = "1"
        build.BuildDate = _BUILD_DATE
        try:
            await server.get_node(ua.NodeId(2260)).write_value(build)
        except Exception:  # noqa: BLE001
            logger.debug("opcua build-info write failed", exc_info=True)
        self._server = server
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop(), name=f"slim-opcua-{self._port}")
        logger.info("slim opcua server on opc.tcp://%s:%d", self._bind_ip, self._port)

    async def _sync_loop(self) -> None:
        while self._running:
            for point, node in self._nodes:
                try:
                    if NamedPointProjection.is_actuator(point):
                        name = NamedPointProjection.node_name(point)
                        value = await node.read_value()
                        if value != self._actuator_last.get(name):
                            self._proj.apply_write(point, value)
                            self._actuator_last[name] = value
                    else:
                        await node.write_value(
                            ua.Variant(float(self._proj.read_value(point)), ua.VariantType.Double))
                except Exception:  # noqa: BLE001
                    logger.debug("opcua node sync failed", exc_info=True)
            await asyncio.sleep(self._sync_interval)

    async def stop(self) -> None:
        self._running = False
        if self._sync_task is not None:
            self._sync_task.cancel()
        if self._server is not None:
            await self._server.stop()
