# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Active Modbus poller: ``python -m app.mimic.poll <ip> <port> [interval_s]``.

A P0 stand-in for a real HMI so the passive CV sensor observes a Modbus
conversation (FC43 identity + register/coil reads) and classifies the persona.
This is the seed of P1's active-master persona (`ClientLoops`) — a persona that
polls its peers rather than a bare test client.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from pymodbus.client import AsyncModbusTcpClient

logger = logging.getLogger(__name__)


async def poll_forever(target: str, port: int, interval_s: float = 3.0, unit: int = 1) -> None:
    n = 0
    while True:
        try:
            client = AsyncModbusTcpClient(target, port=port)
            await client.connect()
            if client.connected:
                await client.read_device_information(read_code=2, slave=unit)
                rr = await client.read_holding_registers(0, count=4, slave=unit)
                await client.read_coils(0, count=1, slave=unit)
                n += 1
                if n % 10 == 0 and not rr.isError():
                    logger.info("poll %d %s:%d level=%s", n, target, port, rr.registers[0])
            client.close()
        except Exception as e:  # noqa: BLE001 - keep polling through transient errors
            logger.warning("poll %s:%d failed: %s", target, port, e)
        await asyncio.sleep(interval_s)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) < 2:
        print("usage: python -m app.mimic.poll <ip> <port> [interval_s]", file=sys.stderr)
        return 2
    target, port = argv[0], int(argv[1])
    interval = float(argv[2]) if len(argv) > 2 else 3.0
    asyncio.run(poll_forever(target, port, interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
