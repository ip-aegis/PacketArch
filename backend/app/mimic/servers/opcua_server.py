# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""OPC UA persona server (asyncua).

Binds a real OPC UA endpoint and exposes the persona's process values as nodes:
read-only sensor nodes are pushed live from the model, writable actuator nodes
feed back into it. Server identity (application name, manufacturer, product,
software version) comes from the shared fingerprint, so a client browsing the
server — and CV's OPC UA discovery — see the intended device.

Proves the Mimic seams generalize past Modbus: a completely different protocol
shape (object/node model + sessions, not registers) behind the same
``Projection`` / ``ProtocolServer`` interfaces, driven by the same process model.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

from asyncua import Server, ua

from ..interfaces import ProtocolServer
from ..projections.opcua_projection import OpcUaProjection

logger = logging.getLogger(__name__)

# Fixed build date — a plausible constant; avoids wall-clock nondeterminism.
_BUILD_DATE = datetime.datetime(2024, 1, 1)


class OpcUaPersonaServer(ProtocolServer):
    """A bound OPC UA responder for one persona."""

    protocol = "opcua"

    def __init__(
        self,
        *,
        bind_ip: str,
        port: int,
        projection: OpcUaProjection,
        identity: dict[str, Any],
        sync_interval_s: float = 0.5,
    ) -> None:
        self._bind_ip = bind_ip
        self._port = port
        self._proj = projection
        self._identity = identity
        self._sync_interval = sync_interval_s
        self._server: Server | None = None
        self._nodes: list[tuple[Any, Any]] = []
        self._actuator_last: dict[str, Any] = {}  # node name -> last value applied
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
            name = OpcUaProjection.node_name(point)
            if OpcUaProjection.is_actuator(point):
                node = await dev.add_variable(idx, name, False, ua.VariantType.Boolean)
                await node.set_writable()
                # Seed last-applied so the resting state isn't force-written every
                # cycle (which would override the model's nominal input). Write-back
                # then fires only on an actual client change, like Modbus.
                self._actuator_last[name] = False
            else:
                node = await dev.add_variable(
                    idx, name, float(self._proj.read_value(point)), ua.VariantType.Double
                )
            self._nodes.append((point, node))

        await server.start()
        # asyncua's set_build_info is a no-op in 2.0 (BuildInfo keeps FreeOpcUa
        # defaults), so write the composite BuildInfo node (ns=0;i=2260) directly
        # — this is what an OPC UA client / CV reads as the device manufacturer.
        build = ua.BuildInfo()
        build.ProductUri = self._identity.get("product_uri") or app_uri
        build.ManufacturerName = vendor
        build.ProductName = model
        build.SoftwareVersion = firmware
        build.BuildNumber = "1"
        build.BuildDate = _BUILD_DATE
        try:
            await server.get_node(ua.NodeId(2260)).write_value(build)
        except Exception:  # noqa: BLE001 - identity is best-effort, never fatal to serving
            logger.debug("opcua build-info write failed", exc_info=True)
        self._server = server
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop(), name=f"opcua-sync-{self._port}")
        logger.info("opcua persona server listening on opc.tcp://%s:%d", self._bind_ip, self._port)

    async def _sync_loop(self) -> None:
        while self._running:
            for point, node in self._nodes:
                try:
                    if OpcUaProjection.is_actuator(point):
                        name = OpcUaProjection.node_name(point)
                        value = await node.read_value()
                        if value != self._actuator_last.get(name):  # a real client write
                            self._proj.apply_write(point, value)
                            self._actuator_last[name] = value
                    else:
                        await node.write_value(
                            ua.Variant(float(self._proj.read_value(point)), ua.VariantType.Double)
                        )
                except Exception:  # noqa: BLE001 - one node error must not stall the loop
                    logger.debug("opcua node sync failed", exc_info=True)
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
            await self._server.stop()
        logger.info("opcua persona server on %s:%d stopped", self._bind_ip, self._port)
