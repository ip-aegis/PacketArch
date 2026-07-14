# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Off-box Mimic deployment on Ubuntu + Docker — the FULL on-box runtime, off-box.

Each persona is its own Ubuntu CML node running the exact ``app.mimic`` container
that runs on-box (``python -m app.mimic.run``), on a glibc base — so every protocol
and dependency (notably IEC-104's c104, which has no musl wheel) works with zero
reimplementation. Heavier than the slim Alpine path (Ubuntu + Docker + the 190 MB
image), but capability-complete: on-box and off-box are one codebase.

Topology is identical to the slim cell: each node's data NIC (ens3, a STATIC OT
segment IP) joins a shared switch; with a sensor, an IOSvL2 SPAN mirrors the
segment to an auto-provisioned CV sensor. Management (ens2, DHCP) reaches the
backend for the image + check-in. Reuses the CML + sensor primitives.
"""

from __future__ import annotations

import base64
import json
import logging

from app.services.device_templates import get_fingerprint_from_template

from .interfaces import ClientBinding, PersonaSpec
from .scaffold import _PORTS, scaffold_persona
from .slim_deploy import _slug
from .slim_sensor import build_span_switch_config, deploy_cv_sensor_node

logger = logging.getLogger(__name__)

_IMAGE_PATH = "/agent/mimic-image.tar.gz"
_IMAGE_TAG = "mimic-persona:p0"
_DATA_NET = "10.99.0"


def build_cell_personas(*, devices: list[dict], relationships: list[dict]) -> list[tuple[PersonaSpec, str]]:
    """Device graph → (PersonaSpec, data_ip) list. Full PersonaSpecs (identity is
    resolved inside the container); poll edges are baked to the peer's data IP."""
    by_key: dict[str, PersonaSpec] = {}
    proto_by_key: dict[str, str | None] = {}
    for d in devices:
        proto = d.get("protocol")
        by_key[d["key"]] = scaffold_persona(
            key=d["key"], name=d.get("name", d["key"]), template_id=d["template_id"],
            protocol=proto, process_model_id=d.get("process_model_id"))
        proto_by_key[d["key"]] = proto
    data_ip = {k: f"{_DATA_NET}.{10 + i * 10}" for i, k in enumerate(by_key)}
    for rel in relationships:
        src, dst = rel.get("source"), rel.get("target")
        if src not in by_key or dst not in by_key:
            continue
        tproto = proto_by_key.get(dst) or "modbus"
        by_key[src].clients.append(ClientBinding(
            protocol=tproto, target_device=dst, target_ip=data_ip[dst], port=_PORTS.get(tproto, 502)))
    return [(by_key[k], data_ip[k]) for k in by_key]


def build_persona_cloud_init(*, persona: PersonaSpec, data_ip: str, server: str,
                             insecure: bool = True, ttl: int = 64) -> str:
    """Cloud-init: static OT data IP on ens3, install docker, load + run the mimic
    persona container (--network host → binds ens3), then report in."""
    persona.bind_ip = "0.0.0.0"
    slug = _slug(persona.name)
    b64_spec = base64.b64encode(json.dumps(persona.to_dict()).encode()).decode()
    k = "k" if insecure else ""
    server = server.rstrip("/")
    port = persona.protocols[0].port if persona.protocols else 0
    listen = (f"ss -tln 2>/dev/null | grep -c ':{port} '" if port else "echo 1")
    return f"""#cloud-config
hostname: {slug}
manage_etc_hosts: true
write_files:
  - path: /etc/netplan/99-packetarch.yaml
    permissions: '0600'
    content: |
      network:
        version: 2
        ethernets:
          ens2:
            dhcp4: true
            optional: true
          ens3:
            addresses: [{data_ip}/24]
            optional: true
runcmd:
  - netplan apply
  - mkdir -p /opt/mimic
  - [ bash, -c, "echo {b64_spec} | base64 -d > /opt/mimic/persona.json" ]
  - [ bash, -c, "for i in $(seq 1 60); do curl -fsSL{k} {server}/health >/dev/null 2>&1 && break; sleep 5; done" ]
  - [ bash, -c, "curl -fsSL https://get.docker.com | sh" ]
  - [ bash, -c, "curl -fsSL{k} {server}{_IMAGE_PATH} -o /tmp/mimic.tar.gz && gunzip -c /tmp/mimic.tar.gz | docker load" ]
  - [ bash, -c, "sysctl -w net.ipv4.ip_default_ttl={ttl}" ]
  - [ bash, -c, "docker run -d --name mimic-persona --restart unless-stopped --network host --user 0 -v /opt/mimic/persona.json:/persona.json:ro --entrypoint python {_IMAGE_TAG} -m app.mimic.run /persona.json" ]
  - [ bash, -c, "sleep 20; L=$({listen}); RUN=$(docker ps --filter name=mimic-persona --filter status=running -q | wc -l); while true; do curl -fsSL{k} \\"{server}/agent/mimic-checkin?name={slug}&up=$RUN&listening=$L&running=$RUN\\" >/dev/null 2>&1; L=$({listen}); RUN=$(docker ps --filter name=mimic-persona --filter status=running -q | wc -l); sleep 30; done" ]
"""


async def _create_persona_node(service, *, lab_id: str, persona: PersonaSpec, data_ip: str,
                                server: str, x: int, y: int) -> str:
    fp = get_fingerprint_from_template(persona.template_id, firmware_version=persona.firmware_version) or {}
    ttl = int((fp.get("tcp_stack") or {}).get("ttl", 64))
    cfg = build_persona_cloud_init(persona=persona, data_ip=data_ip, server=server, ttl=ttl)
    return await service._create_node(  # noqa: SLF001
        lab_id, label=_slug(persona.name), node_definition="ubuntu",
        image_definition="ubuntu-24-04-20241004", ram_mb=1536, cpus=1, configuration=cfg, x=x, y=y)


async def _wire_persona(service, *, lab_id: str, node_id: str, data_switch: str, data_port_slot: int):
    ens2 = await service._create_interface(lab_id, node_id, 0)  # noqa: SLF001 — mgmt
    ens3 = await service._create_interface(lab_id, node_id, 1)  # noqa: SLF001 — data
    nodes = await service._request("GET", f"/labs/{lab_id}/nodes", params={"data": "true"})  # noqa: SLF001
    mgmt_port, _ = await service._ensure_management_egress(  # noqa: SLF001
        lab_id, [n for n in (nodes or []) if isinstance(n, dict) and n.get("id") != node_id])
    await service._link(lab_id, ens2, mgmt_port)  # noqa: SLF001
    if isinstance(data_switch, str) and data_port_slot is None:  # unmanaged data switch
        data_port = await service._next_switch_port(lab_id, data_switch)  # noqa: SLF001
    else:  # IOSvL2 SPAN-source port at the given slot
        data_port = await service._create_interface(lab_id, data_switch, data_port_slot)  # noqa: SLF001
    await service._link(lab_id, ens3, data_port)  # noqa: SLF001


async def deploy_docker_cell(service, *, lab_id: str, personas: list[tuple[PersonaSpec, str]],
                             server: str) -> dict:
    """Provision a cell of full-runtime Ubuntu persona nodes on a shared OT switch."""
    data_sw = await service._create_node(  # noqa: SLF001
        lab_id, label="pa-ot-switch", node_definition="unmanaged_switch",
        image_definition="", ram_mb=0, cpus=0, configuration="", x=0, y=200)
    results = []
    for i, (persona, data_ip) in enumerate(personas):
        node_id = await _create_persona_node(service, lab_id=lab_id, persona=persona,
                                             data_ip=data_ip, server=server, x=i * 200 - 100, y=-40)
        await _wire_persona(service, lab_id=lab_id, node_id=node_id, data_switch=data_sw, data_port_slot=None)
        results.append({"name": persona.name, "node_id": node_id, "data_ip": data_ip})
    await service._request("PUT", f"/labs/{lab_id}/start")  # noqa: SLF001
    logger.info("provisioned docker cell of %d personas in lab %s", len(results), lab_id)
    return {"data_switch": data_sw, "personas": results}


async def deploy_docker_cell_with_sensor(service, cv, *, lab_id: str,
                                         personas: list[tuple[PersonaSpec, str]],
                                         deployment_name: str, serial: str, server: str) -> dict:
    """Full-runtime cell whose OT segment is an IOSvL2 SPAN mirrored to a CV sensor."""
    n = len(personas)
    span_id = await service._create_node(  # noqa: SLF001
        lab_id, label="pa-ot-span", node_definition="iosvl2", image_definition="iosvl2-2020",
        ram_mb=768, cpus=1, configuration=build_span_switch_config(n), x=0, y=120)
    results = []
    for i, (persona, data_ip) in enumerate(personas):
        node_id = await _create_persona_node(service, lab_id=lab_id, persona=persona,
                                             data_ip=data_ip, server=server, x=i * 200 - 100, y=-60)
        await _wire_persona(service, lab_id=lab_id, node_id=node_id, data_switch=span_id, data_port_slot=i)
        results.append({"name": persona.name, "node_id": node_id, "data_ip": data_ip})
    sensor = await deploy_cv_sensor_node(service, cv, lab_id=lab_id, deployment_name=deployment_name,
                                         serial=serial, server=server, x=0, y=280)
    gi_dest = await service._create_interface(lab_id, span_id, n)  # noqa: SLF001 — SPAN dest
    await service._link(lab_id, sensor["capture_iface"], gi_dest)  # noqa: SLF001
    await service._request("PUT", f"/labs/{lab_id}/start")  # noqa: SLF001
    logger.info("provisioned docker cell+sensor (%d personas) in lab %s", n, lab_id)
    return {"span_switch": span_id, "personas": results, "sensor": sensor}
