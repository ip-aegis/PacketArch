# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""DevicePersona — the composition root of the Mimic runtime.

Binds a persona's identity (shared fingerprint substrate) + transport + process
model + per-protocol projections + protocol servers into one running device, and
drives the process model forward on a wall-clock tick (personas are reactive, so
they live on wall time, never a virtual-time heap).

P0 wires Modbus only; the ``for binding in spec.protocols`` dispatch is the seam
where ENIP/S7/OPC-UA/etc. servers slot in behind the same interfaces.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.protocol_engines.fingerprint_applicator import FingerprintApplicator
from app.protocol_engines.process_sim import ProcessModel
from app.services.device_templates import get_fingerprint_from_template

from .client import modbus_client_loop
from .interfaces import PersonaSpec, ProtocolServer, Transport
from .process_library import build_process_model
from .projections.modbus_projection import ModbusProjection
from .projections.named_point import NamedPointProjection
from .servers.modbus_server import ModbusPersonaServer
from .servers.opcua_server import OpcUaPersonaServer
from .transport import NamespaceKernelStack

logger = logging.getLogger(__name__)


class DevicePersona:
    """One live, bound industrial device."""

    def __init__(self, spec: PersonaSpec, transport: Transport | None = None) -> None:
        self.spec = spec
        self.transport = transport or NamespaceKernelStack(spec.bind_ip)

        fingerprint = get_fingerprint_from_template(
            spec.template_id, firmware_version=spec.firmware_version
        )
        if fingerprint is None:
            raise ValueError(f"unknown device template: {spec.template_id!r}")
        self._fingerprint: dict[str, Any] = fingerprint
        self._modbus_identity: dict[str, Any] = fingerprint.get("modbus_identity") or {}
        self._firmware_version: str | None = (
            fingerprint.get("firmware_version") or spec.firmware_version
        )
        self._vendor: str = fingerprint.get("vendor") or ""
        self._model_name: str = fingerprint.get("model") or fingerprint.get("vendor_family") or ""
        # The applicator is the device "personality" (TTL/window, response
        # timing, error injection, deterministic serial). P0 uses it for the
        # stack fingerprint the netns transport will apply; later phases route
        # server response delay + error injection through it.
        self.applicator = FingerprintApplicator(
            fingerprint=fingerprint,
            device_id=spec.device_id,
            scenario_id=spec.scenario_id,
            device_name=spec.name,
        )

        self._model: ProcessModel | None = None
        self._servers: list[ProtocolServer] = []
        self._client_tasks: list[asyncio.Task] = []
        self._step_task: asyncio.Task | None = None
        self._built = False
        self._running = False

    @property
    def model(self) -> ProcessModel | None:
        return self._model

    def build(self) -> None:
        """Instantiate the process model and protocol servers (no binding yet)."""
        if self._built:
            return
        if not self.spec.protocols and not self.spec.clients:
            raise ValueError(
                f"persona {self.spec.name!r} has neither servers nor client loops"
            )
        if self.spec.process_model_id:
            self._model = build_process_model(self.spec.process_model_id)

        for binding in self.spec.protocols:
            if binding.protocol == "modbus":
                projection = ModbusProjection(self._model, binding.points)
                self._servers.append(
                    ModbusPersonaServer(
                        bind_ip=self.transport.bind_ip,
                        port=binding.port,
                        unit_id=binding.unit_id,
                        projection=projection,
                        modbus_identity=self._modbus_identity,
                        firmware_version=self._firmware_version,
                    )
                )
            elif binding.protocol == "opcua":
                projection = NamedPointProjection(self._model, binding.points)
                opcua_identity = self._fingerprint.get("opc_ua_identity") or {}
                self._servers.append(
                    OpcUaPersonaServer(
                        bind_ip=self.transport.bind_ip,
                        port=binding.port,
                        projection=projection,
                        identity={
                            "vendor": self._vendor,
                            "model_name": self._model_name or self.spec.name,
                            "firmware": self._firmware_version or "",
                            "device_name": self.spec.name,
                            "application_uri": opcua_identity.get("application_uri"),
                            "product_uri": opcua_identity.get("product_uri"),
                        },
                    )
                )
            elif binding.protocol == "iec104":
                from .servers.iec104_server import Iec104PersonaServer

                projection = NamedPointProjection(self._model, binding.points)
                self._servers.append(
                    Iec104PersonaServer(
                        bind_ip=self.transport.bind_ip,
                        port=binding.port,
                        common_address=binding.unit_id,
                        projection=projection,
                    )
                )
            elif binding.protocol == "bacnet":
                from .servers.bacnet_server import BacnetPersonaServer

                projection = NamedPointProjection(self._model, binding.points)
                bacnet_identity = self._fingerprint.get("bacnet_identity") or {}
                self._servers.append(
                    BacnetPersonaServer(
                        bind_ip=self.transport.bind_ip,
                        port=binding.port,
                        projection=projection,
                        device_id=self.spec.device_id,
                        identity={
                            "vendor_id": bacnet_identity.get("vendor_id", 0),
                            "object_name": bacnet_identity.get("object_name"),
                            "model_name": bacnet_identity.get("model_name") or self._model_name,
                            "device_name": self.spec.name,
                            "firmware": self._firmware_version or "",
                        },
                    )
                )
            else:
                raise ValueError(
                    f"protocol {binding.protocol!r} not yet supported by Mimic"
                )
        self._built = True

    async def start(self) -> None:
        """Bring the persona online: model tick, bind servers, run client loops."""
        self.build()
        self._running = True
        if self._model is not None:
            self._step_task = asyncio.create_task(
                self._step_loop(), name=f"persona-step-{self.spec.device_id[:8]}"
            )
        for server in self._servers:
            await server.start()
        for i, cb in enumerate(self.spec.clients):
            if cb.protocol == "modbus":
                self._client_tasks.append(
                    asyncio.create_task(
                        modbus_client_loop(cb, label=f"{self.spec.name}->{cb.target_ip}"),
                        name=f"persona-client-{self.spec.device_id[:8]}-{i}",
                    )
                )
            else:
                logger.warning("client protocol %r not supported (P1 = modbus)", cb.protocol)
        logger.info(
            "persona '%s' (%s) online at %s: %d server(s), %d client loop(s)",
            self.spec.name,
            self.spec.template_id,
            self.transport.bind_ip,
            len(self._servers),
            len(self._client_tasks),
        )

    async def _step_loop(self) -> None:
        dt_s = self.spec.step_interval_ms / 1000.0
        while self._running:
            try:
                self._model.step(dt_s)
            except Exception:  # noqa: BLE001 - a model error must not kill the servers
                logger.exception("process model step failed")
            await asyncio.sleep(dt_s)

    async def stop(self) -> None:
        self._running = False
        for server in self._servers:
            await server.stop()
        for task in (*self._client_tasks, self._step_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("persona '%s' stopped", self.spec.name)
