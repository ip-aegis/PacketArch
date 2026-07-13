# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Active-master client loops — the polling half of a persona.

A persona with ``ClientBinding``s (e.g. an HMI) runs one loop per peer: connect,
issue FC43 identity + register/coil reads, disconnect, repeat. This is what turns
a fleet of personas into a conversing cell rather than a set of devices waiting to
be scanned. ``app.mimic.poll`` is the standalone (P0) entrypoint over the same
loop; ``DevicePersona`` runs these loops in-process alongside its servers.
"""

from __future__ import annotations

import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient

from .interfaces import ClientBinding

logger = logging.getLogger(__name__)


async def modbus_client_loop(binding: ClientBinding, *, label: str = "") -> None:
    """Poll one Modbus peer forever per the binding. Never raises — transient
    peer errors are logged and retried."""
    if not binding.target_ip:
        logger.warning("client loop %s has no target_ip; skipping", label or binding.target_device)
        return
    tag = label or f"{binding.target_ip}:{binding.port}"
    n = 0
    while True:
        try:
            client = AsyncModbusTcpClient(binding.target_ip, port=binding.port)
            await client.connect()
            if client.connected:
                if binding.identity:
                    await client.read_device_information(read_code=2, slave=binding.unit_id)
                if binding.read_holding:
                    rr = await client.read_holding_registers(
                        0, count=binding.read_holding, slave=binding.unit_id
                    )
                    n += 1
                    if n % 10 == 0 and not rr.isError():
                        logger.info("%s poll %d: hr0=%s", tag, n, rr.registers[0])
                if binding.read_coils:
                    await client.read_coils(0, count=binding.read_coils, slave=binding.unit_id)
            client.close()
        except Exception as e:  # noqa: BLE001 - keep the loop alive through peer churn
            logger.warning("client loop %s failed: %s", tag, e)
        await asyncio.sleep(binding.interval_s)
