# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Protocol-breadth gate: prove the seams generalize to IEC 60870-5-104.

Brings an IEC-104 substation persona online and drives it with a real c104 client
(full wire round-trip — c104's client uses an ephemeral port, no loopback clash),
proving behind the SAME projection + process model:

  * a client can interrogate the station and read live, drifting measurements,
  * sending a single-command feeds back and moves the model.

Run: ``python -m pytest tests/mimic/test_iec104_breadth.py``.
"""

from __future__ import annotations

import asyncio

import c104
import pytest

from app.mimic.interfaces import PersonaSpec, PointBinding, ProtocolBinding
from app.mimic.persona import DevicePersona
from app.mimic.transport import LocalhostTransport

PORT = 24041
CA = 1
LEVEL_IOA = 11
CMD_IOA = 21


def _spec() -> PersonaSpec:
    pts = [
        PointBinding(space="", address=LEVEL_IOA, source="variable", variable="level"),
        PointBinding(
            space="", address=CMD_IOA, source="actuator",
            writable=True, write_target="inflow", write_true_value=8.0, write_false_value=0.0,
        ),
    ]
    return PersonaSpec(
        device_id="pb-rtu-104", scenario_id="mimic-pb", name="Substation_RTU",
        template_id="schneider/modicon-m580/bmep584040", process_model_id="tank_level",
        protocols=[ProtocolBinding(protocol="iec104", port=PORT, unit_id=CA, points=pts)],
    )


@pytest.mark.asyncio
async def test_iec104_persona_breadth() -> None:
    persona = DevicePersona(_spec(), transport=LocalhostTransport("127.0.0.1"))
    await persona.start()
    client = c104.Client()
    conn = client.add_connection(ip="127.0.0.1", port=PORT)
    # Mirror the station/points on the client BEFORE starting (c104 requirement).
    station = conn.add_station(common_address=CA)
    level = station.add_point(io_address=LEVEL_IOA, type=c104.Type.M_ME_NC_1)
    cmd = station.add_point(io_address=CMD_IOA, type=c104.Type.C_SC_NA_1)
    try:
        client.start()
        for _ in range(50):
            if conn.is_connected:
                break
            await asyncio.sleep(0.1)
        assert conn.is_connected, "client failed to connect to IEC-104 station"

        # --- interrogate + live drift ---
        conn.interrogation(common_address=CA)
        await asyncio.sleep(1.0)
        first = level.value
        await asyncio.sleep(1.2)
        conn.interrogation(common_address=CA)
        await asyncio.sleep(0.5)
        second = level.value
        assert first is not None and 30.0 <= first <= 70.0, f"level {first} outside band"
        assert first != second, "measurement static — not driven by the model"

        # --- command write-back: single command ON drives the model input up ---
        base_inflow = persona.model.get_value("inflow")
        cmd.value = True
        cmd.transmit(cause=c104.Cot.ACTIVATION)
        await asyncio.sleep(3.0)
        assert persona.model.get_value("inflow") > base_inflow + 1.0, "command write-back did not drive the model"
    finally:
        client.stop()
        await persona.stop()
