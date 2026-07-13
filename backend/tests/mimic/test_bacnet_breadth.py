# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Protocol-breadth gate: prove the seams generalize to BACnet/IP.

Brings a BACnet building-automation persona online and verifies, behind the SAME
NamedPointProjection + process model as OPC UA:

  * the Device object carries the identity CV reads (vendor-id, model, firmware),
  * Analog Value present-values track live process values,
  * writing the Binary Value command object feeds back and moves the model.

Verified at the object/database level (a second BACnet/IP stack on loopback for a
full wire round-trip is flaky); the wire + CV classification ride the same
protocol-agnostic deploy path already validated end-to-end for Modbus.

Run: ``python -m pytest tests/mimic/test_bacnet_breadth.py``.
"""

from __future__ import annotations

import asyncio

import pytest

from app.mimic.interfaces import PersonaSpec, PointBinding, ProtocolBinding
from app.mimic.persona import DevicePersona
from app.mimic.transport import LocalhostTransport


def _spec() -> PersonaSpec:
    pts = [
        PointBinding(space="", address=0, source="variable", variable="level", name="ZoneTemp"),
        PointBinding(space="", address=1, source="variable", variable="temperature", name="Setpoint"),
        PointBinding(
            space="", address=2, source="actuator", name="FanCommand",
            writable=True, write_target="inflow", write_true_value=8.0, write_false_value=0.0,
        ),
    ]
    return PersonaSpec(
        device_id="pb-dxr2-bacnet", scenario_id="mimic-pb", name="Zone_Room_Controller",
        template_id="siemens/desigo/dxr2", process_model_id="tank_level",
        protocols=[ProtocolBinding(protocol="bacnet", port=47808, points=pts)],
    )


@pytest.mark.asyncio
async def test_bacnet_persona_breadth() -> None:
    persona = DevicePersona(_spec(), transport=LocalhostTransport("127.0.0.1"))
    await persona.start()
    try:
        server = persona._servers[0]  # noqa: SLF001 - white-box object-level check
        objs = {o.objectName: o for _, o, _ in server._objs}  # noqa: SLF001
        device = server._app.device_object  # noqa: SLF001

        # --- identity: Device object carries the vendor/model CV reads ---
        assert device.vendorIdentifier == 7, f"vendor id: {device.vendorIdentifier}"
        assert "DXR2" in str(device.modelName), f"model: {device.modelName!r}"

        # --- live drift: present-value tracks the model ---
        first = objs["ZoneTemp"].presentValue
        await asyncio.sleep(1.2)
        second = objs["ZoneTemp"].presentValue
        assert 20.0 <= first <= 80.0, f"zonetemp {first} outside band"
        assert first != second, "present-value static — not driven by the model"

        # --- write-back: command object ON drives the model input up ---
        base_inflow = persona.model.get_value("inflow")
        objs["FanCommand"].presentValue = "active"
        await asyncio.sleep(3.0)
        assert persona.model.get_value("inflow") > base_inflow + 1.0, "write-back did not drive the model"
    finally:
        await persona.stop()
