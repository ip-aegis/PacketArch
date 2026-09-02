# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Off-box Mimic deployment onto CML nodes.

On-box, a persona runs in a netns on the host-agent's hub-bridge SPAN. Off-box on
CML, each persona IS its own Ubuntu node — a real host with a real kernel TCP/IP
stack (which is why off-box naturally defeats the leaked-TTL fingerprint tell). The
node boots stock Ubuntu, cloud-init installs Docker and runs the mimic-persona
container on the node's own NIC (``--network host`` → binds the node's data plane),
and the node sits on the CML data-plane switch where the SPAN mirrors it to a CV
sensor — exactly the reference agent topology, with a persona in the agent's slot.

Reuses the CML provisioning primitives in ``cml_service`` (node/interface/link,
management egress). The cloud-init here is the persona analogue of
``_build_cloud_init``.
"""

from __future__ import annotations

import base64
import json
import logging
import re

from app.services.device_templates import get_fingerprint_from_template

from .interfaces import PersonaSpec

logger = logging.getLogger(__name__)

# Unauthenticated path the node curls the runtime image from (served like the agent).
_IMAGE_PATH = "/agent/mimic-image.tar.gz"
_IMAGE_TAG = "mimic-persona:p0"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-") or "mimic-persona"


async def ensure_nat_egress(service, lab_id: str, exclude_node: str) -> str:
    """Ensure a NAT external connector + switch exist; return a free switch port.

    NAT (not System Bridge) is what gives CML nodes DHCP + internet egress here —
    outbound is all a persona needs (reach the backend for the image + check-in).
    Reuses an existing NAT connector/switch, else builds one.
    """
    nodes = await service._request("GET", f"/labs/{lab_id}/nodes", params={"data": "true"})  # noqa: SLF001
    nodes = [n for n in (nodes or []) if isinstance(n, dict) and n.get("id") != exclude_node]
    connectors = [n for n in nodes if n.get("node_definition") == "external_connector"
                  and "NAT" in str(n.get("configuration", ""))]
    switches = [n for n in nodes if n.get("node_definition") == "unmanaged_switch"]
    links = await service._request("GET", f"/labs/{lab_id}/links", params={"data": "true"})  # noqa: SLF001
    conn_ids = {c["id"] for c in connectors}
    for sw in switches:
        for link in (links or []):
            if isinstance(link, dict):
                a, b = link.get("node_a"), link.get("node_b")
                if sw["id"] in (a, b) and (a in conn_ids or b in conn_ids):
                    return await service._next_switch_port(lab_id, sw["id"])  # noqa: SLF001

    conn_id = await service._create_node(  # noqa: SLF001
        lab_id, label="pa-nat", node_definition="external_connector",
        image_definition="", ram_mb=0, cpus=0, configuration="NAT", x=-340, y=-200,
    )
    sw_id = await service._create_node(  # noqa: SLF001
        lab_id, label="pa-mgmt-switch", node_definition="unmanaged_switch",
        image_definition="", ram_mb=0, cpus=0, configuration="", x=-260, y=-120,
    )
    conn_port = await service._create_interface(lab_id, conn_id, 0)  # noqa: SLF001
    sw_uplink = await service._create_interface(lab_id, sw_id, 0)  # noqa: SLF001
    await service._link(lab_id, sw_uplink, conn_port)  # noqa: SLF001
    return await service._next_switch_port(lab_id, sw_id)  # noqa: SLF001


def build_persona_cloud_init(*, persona_spec: dict, server: str, insecure: bool, ttl: int) -> str:
    """Cloud-init that runs one persona container bound to the node's own NIC."""
    slug = _slug(str(persona_spec.get("name", "persona")))
    b64_spec = base64.b64encode(json.dumps(persona_spec).encode()).decode()
    k = "k" if insecure else ""  # curl -k for the self-signed backend
    server = server.rstrip("/")
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
            dhcp4: true
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
  - [ bash, -c, "sleep 20; IP=$(ip -4 -o addr show ens2 | awk '{{print $4}}' | cut -d/ -f1); MB=$(ss -tln 2>/dev/null | grep -c ':502'); RUN=$(docker ps --filter name=mimic-persona --filter status=running -q | wc -l); for i in $(seq 1 30); do curl -fsSL{k} \\"{server}/agent/mimic-checkin?name={slug}&ip=$IP&modbus_listening=$MB&running=$RUN\\" >/dev/null 2>&1 && break; sleep 10; done" ]
"""


async def deploy_persona_node(
    service,
    *,
    lab_id: str,
    persona: PersonaSpec,
    server: str,
    insecure: bool = True,
    x: int = -200,
    y: int = 40,
    wire_mgmt: bool = True,
    start: bool = True,
) -> dict:
    """Provision one persona as a CML node. Returns {node_id, data_iface, warnings}.

    ``wire_mgmt`` links ens2 to the management egress so the node can reach the
    backend (health, image download) and — since the persona binds 0.0.0.0 — be
    polled over management during bring-up. ens3 (data, returned as ``data_iface``)
    is left for the caller to wire onto the data-plane / SPAN switch.
    """
    persona.bind_ip = "0.0.0.0"
    fp = get_fingerprint_from_template(persona.template_id, firmware_version=persona.firmware_version) or {}
    ttl = int((fp.get("tcp_stack") or {}).get("ttl", 64))

    cloud_init = build_persona_cloud_init(
        persona_spec=persona.to_dict(), server=server.rstrip("/"), insecure=insecure, ttl=ttl,
    )
    node_id = await service._create_node(  # noqa: SLF001 - reusing CML provisioning primitives
        lab_id, label=persona.name, node_definition="ubuntu",
        image_definition="ubuntu-24-04-20241004", ram_mb=1536, cpus=1,
        configuration=cloud_init, x=x, y=y,
    )
    mgmt_iface = await service._create_interface(lab_id, node_id, 0)  # noqa: SLF001
    data_iface = await service._create_interface(lab_id, node_id, 1)  # noqa: SLF001

    warnings: list[str] = []
    if wire_mgmt:
        switch_port = await ensure_nat_egress(service, lab_id, node_id)
        await service._link(lab_id, mgmt_iface, switch_port)  # noqa: SLF001

    if start:
        await service._request("PUT", f"/labs/{lab_id}/nodes/{node_id}/state/start")  # noqa: SLF001

    logger.info("provisioned CML persona node %s (%s) in lab %s", persona.name, node_id, lab_id)
    return {"node_id": node_id, "data_iface": data_iface, "warnings": warnings}
