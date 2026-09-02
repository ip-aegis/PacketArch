# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Realism gate: closed-loop process control end-to-end through a protocol.

Real industrial register values are CONTROLLED — held at a setpoint, rejecting
disturbances — not static or random-walking (a documented fingerprinting tell).
This drives a PI-controlled level persona over Modbus and proves, on the wire:

  * writing the setpoint register moves the process to that setpoint (tracking),
  * the process then holds a tight band across a demand-disturbance cycle
    (disturbance rejection) — believable controlled behaviour to a skilled observer.

Run: ``python -m pytest tests/mimic/test_process_control.py``.
"""

from __future__ import annotations

import asyncio

import pytest
from pymodbus.client import AsyncModbusTcpClient

from app.mimic.interfaces import PersonaSpec, PointBinding, ProtocolBinding
from app.mimic.persona import DevicePersona
from app.mimic.transport import LocalhostTransport

PORT = 15021
UNIT = 1
LEVEL = 0
SETPOINT = 3  # holding register, writable, scale 100


def _spec() -> PersonaSpec:
    pts = [
        PointBinding(space="holding", address=LEVEL, source="variable", variable="level", scale=100.0),
        PointBinding(space="holding", address=SETPOINT, source="variable", variable="setpoint",
                     scale=100.0, writable=True, write_target="setpoint"),
    ]
    return PersonaSpec(
        device_id="ctrl-m580", scenario_id="mimic-ctrl", name="Level_Control_PLC",
        template_id="schneider/modicon-m580/bmep584040", process_model_id="tank_level_control",
        protocols=[ProtocolBinding(protocol="modbus", port=PORT, unit_id=UNIT, points=pts)],
    )


async def _level(client: AsyncModbusTcpClient) -> float:
    rr = await client.read_holding_registers(LEVEL, count=1, slave=UNIT)
    assert not rr.isError()
    return rr.registers[0] / 100.0


@pytest.mark.asyncio
async def test_process_control_tracks_setpoint() -> None:
    persona = DevicePersona(_spec(), transport=LocalhostTransport("127.0.0.1"))
    await persona.start()
    try:
        client = AsyncModbusTcpClient("127.0.0.1", port=PORT)
        await client.connect()
        assert client.connected

        await asyncio.sleep(2.0)
        rest = await _level(client)
        assert 45.0 <= rest <= 55.0, f"rest level {rest} not near 50 setpoint"

        # --- write a new setpoint (70%); the loop should drive level there ---
        wr = await client.write_register(SETPOINT, 7000, slave=UNIT)  # 70.00 * 100
        assert not wr.isError()
        await asyncio.sleep(9.0)
        tracked = await _level(client)
        assert abs(tracked - 70.0) <= 3.0, f"level did not track setpoint 70: {tracked}"

        # --- disturbance rejection: hold, sample across a demand cycle ---
        lo = hi = tracked
        for _ in range(18):
            await asyncio.sleep(0.5)
            lv = await _level(client)
            lo, hi = min(lo, lv), max(hi, lv)
        assert hi - lo <= 6.0, f"level band {hi - lo:.1f}% too wide — control not rejecting disturbance"

        # --- lower the setpoint (40%) and confirm it tracks down ---
        await client.write_register(SETPOINT, 4000, slave=UNIT)
        await asyncio.sleep(10.0)
        lowered = await _level(client)
        assert abs(lowered - 40.0) <= 3.0, f"level did not track setpoint 40: {lowered}"

        client.close()
    finally:
        await persona.stop()
