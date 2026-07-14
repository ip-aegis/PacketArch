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


async def opcua_client_loop(binding: ClientBinding, *, label: str = "") -> None:
    """Poll one OPC UA peer: connect, read its BuildInfo identity, browse the device
    object and read its variables, disconnect, repeat."""
    from asyncua import Client, ua
    if not binding.target_ip:
        return
    tag = label or f"{binding.target_ip}:{binding.port}"
    url = f"opc.tcp://{binding.target_ip}:{binding.port}/packetarch/server/"
    n = 0
    while True:
        try:
            async with Client(url, timeout=5) as client:
                if binding.identity:
                    await client.get_node(ua.NodeId(2260)).read_value()  # BuildInfo
                for obj in await client.nodes.objects.get_children():
                    for node in await obj.get_children():
                        try:
                            await node.read_value()
                        except Exception:  # noqa: BLE001 - method/object nodes aren't readable
                            pass
                n += 1
                if n % 10 == 0:
                    logger.info("%s opcua poll %d", tag, n)
        except Exception as e:  # noqa: BLE001
            logger.warning("opcua client loop %s failed: %s", tag, e)
        await asyncio.sleep(binding.interval_s)


async def bacnet_client_loop(binding: ClientBinding, *, label: str = "") -> None:
    """Poll one BACnet peer: Who-Is the target, then ReadProperty its device object.
    A persistent client application (like a real BAS supervisor)."""
    import socket

    from bacpypes3.ipv4.app import NormalApplication
    from bacpypes3.local.device import DeviceObject
    from bacpypes3.pdu import Address
    if not binding.target_ip:
        return
    tag = label or f"{binding.target_ip}:{binding.port}"
    # bacpypes3 needs a real interface for its broadcast transport — discover the
    # local IP on the route to the target (the persona's data-segment address).
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((binding.target_ip, binding.port))
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    device = DeviceObject(objectIdentifier=("device", 4001), objectName="Mimic_Supervisor",
                          vendorIdentifier=999)
    app = NormalApplication(device, Address(f"{local_ip}/24:{binding.port}"))
    n = 0
    try:
        while True:
            try:
                iams = await app.who_is(address=Address(f"{binding.target_ip}:{binding.port}"))
                for iam in iams or []:
                    await app.read_property(iam.pduSource, iam.iAmDeviceIdentifier, "objectName")
                n += 1
                if n % 10 == 0:
                    logger.info("%s bacnet poll %d", tag, n)
            except Exception as e:  # noqa: BLE001
                logger.warning("bacnet client loop %s failed: %s", tag, e)
            await asyncio.sleep(binding.interval_s)
    finally:
        app.close()


async def iec104_client_loop(binding: ClientBinding, *, label: str = "") -> None:
    """Poll one IEC-104 peer: connect, issue a general interrogation each cycle so
    the controlled station reports its measured values (a real SCADA master)."""
    import c104
    if not binding.target_ip:
        return
    tag = label or f"{binding.target_ip}:{binding.port}"
    client = c104.Client()
    conn = client.add_connection(ip=binding.target_ip, port=binding.port)
    conn.add_station(common_address=binding.unit_id)
    client.start()
    n = 0
    try:
        while True:
            try:
                if conn.state == c104.ConnectionState.OPEN:
                    conn.interrogation(common_address=binding.unit_id, cause=c104.Cot.ACTIVATION)
                    n += 1
                    if n % 10 == 0:
                        logger.info("%s iec104 interrogation %d", tag, n)
            except Exception as e:  # noqa: BLE001
                logger.warning("iec104 client loop %s failed: %s", tag, e)
            await asyncio.sleep(binding.interval_s)
    finally:
        client.stop()


# protocol -> client loop coroutine
CLIENT_LOOPS = {
    "modbus": modbus_client_loop,
    "opcua": opcua_client_loop,
    "bacnet": bacnet_client_loop,
    "iec104": iec104_client_loop,
}
