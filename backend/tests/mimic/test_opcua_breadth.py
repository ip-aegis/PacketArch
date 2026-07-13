# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Protocol-breadth gate: prove the seams generalize to OPC UA.

Brings an OPC UA persona online on loopback and drives it with a real asyncua
client to prove — behind the SAME Projection/ProtocolServer interfaces and the
SAME process model as Modbus — that:

  * the server advertises the device identity (manufacturer/product),
  * sensor nodes carry live, drifting process values,
  * writing the pump-command node feeds back and moves the level.

Run: ``python -m pytest tests/mimic/test_opcua_breadth.py``.
"""

from __future__ import annotations

import asyncio

import pytest
from asyncua import Client, ua

from app.mimic.interfaces import PersonaSpec, PointBinding, ProtocolBinding
from app.mimic.persona import DevicePersona
from app.mimic.transport import LocalhostTransport

PORT = 14840
URL = f"opc.tcp://127.0.0.1:{PORT}/packetarch/server/"


def _spec() -> PersonaSpec:
    pts = [
        PointBinding(space="", address=0, source="variable", variable="level", name="Level"),
        PointBinding(space="", address=1, source="variable", variable="temperature", name="Temperature"),
        PointBinding(space="", address=2, source="variable", variable="inflow", name="Inflow"),
        PointBinding(
            space="", address=3, source="actuator", name="PumpCommand",
            writable=True, write_target="inflow", write_true_value=8.0, write_false_value=0.0,
        ),
    ]
    return PersonaSpec(
        device_id="pb-s71500-opcua", scenario_id="mimic-pb", name="Reactor_PLC_OPCUA",
        template_id="siemens/s7-1500/cpu-1516-3", process_model_id="tank_level",
        protocols=[ProtocolBinding(protocol="opcua", port=PORT, points=pts)],
    )


async def _child(parent, name):
    for ch in await parent.get_children():
        bn = await ch.read_browse_name()
        if bn.Name == name:
            return ch
    raise AssertionError(f"node {name!r} not found")


@pytest.mark.asyncio
async def test_opcua_persona_breadth() -> None:
    persona = DevicePersona(_spec(), transport=LocalhostTransport("127.0.0.1"))
    await persona.start()
    try:
        client = Client(URL)
        await client.connect()
        try:
            # --- identity: server advertises the device manufacturer/product ---
            # ns=0;i=2260 = Server_ServerStatus_BuildInfo (standard OPC UA node).
            build = await client.get_node(ua.NodeId(2260)).read_value()
            assert "Siemens" in build.ManufacturerName, f"manufacturer: {build.ManufacturerName!r}"

            dev = await _child(client.get_objects_node(), "Reactor_PLC_OPCUA")
            level_node = await _child(dev, "Level")
            pump_node = await _child(dev, "PumpCommand")

            # --- live drift: Level ~50%, moving ---
            first = await level_node.read_value()
            await asyncio.sleep(1.2)
            second = await level_node.read_value()
            assert 30.0 <= first <= 70.0, f"level {first} outside band"
            assert first != second, "OPC UA node static — not driven by the model"

            # --- write-back: pump ON fills, OFF drains ---
            baseline = await level_node.read_value()
            await pump_node.write_value(True)
            await asyncio.sleep(5.0)
            peak = await level_node.read_value()
            assert peak > baseline + 1.5, f"level did not rise on pump ON: {baseline}->{peak}"

            await pump_node.write_value(False)
            await asyncio.sleep(7.0)
            drained = await level_node.read_value()
            assert drained < peak - 1.5, f"level did not fall on pump OFF: {peak}->{drained}"
        finally:
            await client.disconnect()
    finally:
        await persona.stop()
