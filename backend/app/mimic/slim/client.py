# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Slim active-master client loop — the polling half of a persona (e.g. an HMI).

Substrate-free twin of ``app.mimic.client.modbus_client_loop``. One loop per peer:
connect, FC43 identity + register/coil reads, disconnect, repeat — turning a fleet
of off-box personas into a conversing cell. Optionally reports its last read back to
the backend check-in URL, so a poll over the (sniffer-less) data segment is
observable without a SPAN.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
import urllib.request

from pymodbus.client import AsyncModbusTcpClient

from .spec import ClientBinding

logger = logging.getLogger(__name__)


def _report(checkin_url: str, name: str, target: str, value: object, polls: int) -> None:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        urllib.request.urlopen(
            f"{checkin_url}?name={name}&polls={polls}&target={target}&read={value}",
            timeout=5, context=ctx)
    except Exception:  # noqa: BLE001
        pass


async def modbus_client_loop(binding: ClientBinding, *, name: str = "",
                             checkin_url: str | None = None) -> None:
    """Poll one Modbus peer forever per the binding. Never raises."""
    if not binding.target_ip:
        logger.warning("client loop for %s has no target_ip; skipping", name)
        return
    tag = f"{binding.target_ip}:{binding.port}"
    polls = 0
    last: object = None
    while True:
        try:
            client = AsyncModbusTcpClient(binding.target_ip, port=binding.port)
            await client.connect()
            if client.connected:
                if binding.identity:
                    await client.read_device_information(read_code=2, slave=binding.unit_id)
                if binding.read_holding:
                    rr = await client.read_holding_registers(
                        0, count=binding.read_holding, slave=binding.unit_id)
                    if not rr.isError():
                        last = rr.registers[0]
                        polls += 1
                        if polls % 5 == 0:
                            logger.info("%s poll %d: hr0=%s", tag, polls, last)
                            if checkin_url:
                                _report(checkin_url, name, binding.target_ip, last, polls)
                if binding.read_coils:
                    await client.read_coils(0, count=binding.read_coils, slave=binding.unit_id)
            client.close()
        except Exception as e:  # noqa: BLE001 - keep the loop alive through peer churn
            logger.warning("client loop %s failed: %s", tag, e)
        await asyncio.sleep(binding.interval_s)
