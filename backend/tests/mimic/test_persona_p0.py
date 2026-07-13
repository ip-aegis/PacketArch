# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""P0 go/no-go gate — the lab-independent half.

Brings a real Schneider M580 Modbus persona online on loopback and drives it with
a real pymodbus client to prove, end to end:

  * FC43 identity classifies it as the Schneider device (what CV / nmap read),
  * holding registers carry live, drifting process values (not static/random),
  * writing the pump coil feeds back into the model and moves the level,
  * an out-of-range request returns a correct Modbus exception, not a crash.

The remaining gate items (CV classification on a real sensor, nmap
modbus-discover, wire TTL) need the lab and are checked in the deployment
sub-phase. Run: ``python -m pytest tests/mimic/test_persona_p0.py``.
"""

from __future__ import annotations

import asyncio

import pytest
from pymodbus.client import AsyncModbusTcpClient

from app.mimic.persona import DevicePersona
from app.mimic.transport import LocalhostTransport

from .spec_m580_tank import build_spec

PORT = 15020
UNIT = 1


async def _read_regs(client: AsyncModbusTcpClient, addr: int, count: int) -> list[int]:
    rr = await client.read_holding_registers(addr, count=count, slave=UNIT)
    assert not rr.isError(), f"read {addr}x{count} errored: {rr}"
    return rr.registers


@pytest.mark.asyncio
async def test_p0_modbus_persona_gate() -> None:
    spec = build_spec(bind_ip="127.0.0.1", port=PORT, unit_id=UNIT)
    persona = DevicePersona(spec, transport=LocalhostTransport("127.0.0.1"))
    await persona.start()
    try:
        client = AsyncModbusTcpClient("127.0.0.1", port=PORT)
        await client.connect()
        assert client.connected, "client failed to connect to persona"

        # --- 1. FC43 identity: must classify as the Schneider M580 ---------- #
        rdi = await client.read_device_information(read_code=2, slave=UNIT)
        assert not rdi.isError(), f"FC43 errored: {rdi}"
        info = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in rdi.information.items()}
        # MEI object ids: 0 VendorName, 1 ProductCode, 2 MajorMinorRevision,
        # 3 VendorUrl, 4 ProductName, 5 ModelName.
        vendor = info.get(0, "")
        product = info.get(4, "")
        revision = info.get(2, "")
        assert "Schneider" in vendor, f"VendorName not Schneider: {info!r}"
        assert "M580" in product, f"ProductName not M580: {info!r}"
        assert revision == "V4.10", f"firmware revision unexpected: {info!r}"

        # --- 2. Live drift: level ~50%, moving with noise ------------------- #
        first = (await _read_regs(client, 0, 4))[0]
        await asyncio.sleep(1.0)
        second = (await _read_regs(client, 0, 4))[0]
        assert 3000 <= first <= 7000, f"level {first} outside plausible band"
        assert first != second, "registers static — not driven by the model"

        # --- 3. Write-back: pump ON fills, OFF drains ---------------------- #
        baseline = (await _read_regs(client, 0, 1))[0]
        wc = await client.write_coil(0, True, slave=UNIT)  # pump on
        assert not wc.isError(), f"write_coil errored: {wc}"
        # coil reads back what was commanded
        rc = await client.read_coils(0, count=1, slave=UNIT)
        assert rc.bits[0] is True, "pump coil did not read back ON"
        await asyncio.sleep(5.0)
        peak = (await _read_regs(client, 0, 1))[0]
        assert peak > baseline + 150, f"level did not rise on pump ON: {baseline}->{peak}"

        await client.write_coil(0, False, slave=UNIT)  # pump off (full stop → drain)
        await asyncio.sleep(7.0)
        drained = (await _read_regs(client, 0, 1))[0]
        assert drained < peak - 150, f"level did not fall on pump OFF: {peak}->{drained}"

        # --- 4. Out-of-range request → correct exception, no crash --------- #
        bad = await client.read_holding_registers(5000, count=1, slave=UNIT)
        assert bad.isError(), "out-of-range read should return a Modbus exception"

        # persona still healthy after the bad request
        assert not (await client.read_holding_registers(0, count=1, slave=UNIT)).isError()

        client.close()
    finally:
        await persona.stop()
