# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Off-box CV sensor node on CML — captures a slim persona cell's OT segment.

A docker-capable Ubuntu CML node runs a Cisco Cyber Vision docker sensor: its
COLLECTION network (bridge, default route via ens2 mgmt) reaches the Center to
enroll; its CAPTURE network (macvlan passthru on ens3) sees the SPAN of the OT
data segment. The sensor is auto-provisioned via the CV API (deployment token →
per-sensor JWT), so no operator paste — the off-box twin of the on-box Local
Sensor Lab.

Milestone A (this module's `deploy_cv_sensor_node`): sensor enrolls + goes online
in the Center. The IOSvL2 SPAN that feeds the capture interface is wired by the
cell/topology deploy.
"""

from __future__ import annotations

import base64
import logging

from app.services.local_sensor_service import _synthesize_sensor_compose

logger = logging.getLogger(__name__)

_CHECKIN_PATH = "/agent/mimic-checkin"


def build_sensor_cloud_init(*, compose: str, registry_host: str, server: str, name: str,
                            capture_parent: str = "ens3") -> str:
    """Ubuntu cloud-init: trust the CV registry, install docker, run the sensor
    compose (capture macvlan parent forced to the SPAN-destination NIC), report."""
    server = server.rstrip("/")
    # Point the capture macvlan at the real SPAN-destination NIC (the synthesized
    # compose ships a 'placeholder' parent).
    compose = compose.replace("parent: placeholder", f"parent: {capture_parent}")
    b64_compose = base64.b64encode(compose.encode()).decode()
    daemon = f'{{"insecure-registries": ["{registry_host}"]}}'
    b64_daemon = base64.b64encode(daemon.encode()).decode()
    return f"""#cloud-config
write_files:
  - path: /opt/sensor/docker-compose.yml
    encoding: b64
    content: {b64_compose}
  - path: /etc/docker/daemon.json
    encoding: b64
    content: {b64_daemon}
runcmd:
  # The capture NIC has no DHCP (it's the SPAN-destination) so netplan leaves it
  # DOWN — bring it up + promisc so the macvlan passthru actually sees the mirror.
  - [ bash, -c, "ip link set {capture_parent} up && ip link set {capture_parent} promisc on" ]
  - [ bash, -c, "curl -fsSL https://get.docker.com | sh" ]
  - [ bash, -c, "systemctl restart docker" ]
  - [ bash, -c, "cd /opt/sensor && docker compose up -d" ]
  - [ bash, -c, "sleep 20; for i in $(seq 1 40); do RUN=$(docker ps --filter name=sensor --filter status=running -q | wc -l); curl -fsSLk \\"{server}{_CHECKIN_PATH}?name={name}&sensor_running=$RUN&i=$i\\" >/dev/null 2>&1; [ \\"$RUN\\" = 1 ] && break; sleep 15; done" ]
"""


def build_span_switch_config(n_sources: int, hostname: str = "pa-ot-span") -> str:
    """IOSvL2 startup-config: Gi0/0..Gi0/(n-1) carry the personas' OT segment and
    are SPAN-sourced (both directions) to Gi0/n, the sensor's capture port. All
    ports stay in the default VLAN so the personas switch to each other normally."""
    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in hostname)[:60] or "pa-ot-span"
    lines = [f"hostname {safe}", "!"]
    for i in range(n_sources + 1):
        lines += [f"interface GigabitEthernet0/{i}", " no shutdown", "!"]
    srcs = " , ".join(f"GigabitEthernet0/{i}" for i in range(n_sources))
    lines += [f"monitor session 1 source interface {srcs} both",
              f"monitor session 1 destination interface GigabitEthernet0/{n_sources}",
              "!", "end", ""]
    return "\n".join(lines)


async def deploy_cell_with_sensor(service, cv, *, lab_id: str, resolved_specs: list[dict],
                                  deployment_name: str, serial: str, server: str) -> dict:
    """Full off-box proof: a persona cell whose OT segment is an IOSvL2 SPAN switch,
    mirrored to a CV docker sensor node — so CV classifies the off-box personas.

    Each persona: eth0 -> mgmt egress, eth1 -> a SPAN-source port. Sensor: ens2 ->
    mgmt (collection -> Center), ens3 -> the SPAN-destination port.
    """
    from .slim_deploy import _node_resources, _slug, build_alpine_boot_config

    n = len(resolved_specs)
    span_id = await service._create_node(  # noqa: SLF001
        lab_id, label="pa-ot-span", node_definition="iosvl2", image_definition="iosvl2-2020",
        ram_mb=768, cpus=1, configuration=build_span_switch_config(n), x=0, y=120)
    results = []
    for i, spec in enumerate(resolved_specs):
        cfg = build_alpine_boot_config(resolved_spec=spec, server=server)
        ram_mb, cpus = _node_resources([p["protocol"] for p in spec.get("protocols", [])])
        node_id = await service._create_node(  # noqa: SLF001
            lab_id, label=_slug(str(spec.get("name", "persona"))),
            node_definition="alpine", image_definition="alpine-base-3-20-3",
            ram_mb=ram_mb, cpus=cpus, configuration=cfg, x=i * 200 - 100, y=-60)
        eth0 = await service._create_interface(lab_id, node_id, 0)  # noqa: SLF001
        eth1 = await service._create_interface(lab_id, node_id, 1)  # noqa: SLF001
        nodes = await service._request("GET", f"/labs/{lab_id}/nodes", params={"data": "true"})  # noqa: SLF001
        mgmt_port, _ = await service._ensure_management_egress(  # noqa: SLF001
            lab_id, [nn for nn in (nodes or []) if isinstance(nn, dict) and nn.get("id") != node_id])
        await service._link(lab_id, eth0, mgmt_port)  # noqa: SLF001
        gi = await service._create_interface(lab_id, span_id, i)  # noqa: SLF001 — SPAN source Gi0/i
        await service._link(lab_id, eth1, gi)  # noqa: SLF001
        results.append({"name": spec.get("name"), "node_id": node_id, "data_ip": spec.get("data_ip")})

    sensor = await deploy_cv_sensor_node(service, cv, lab_id=lab_id, deployment_name=deployment_name,
                                         serial=serial, server=server, x=0, y=280)
    gi_dest = await service._create_interface(lab_id, span_id, n)  # noqa: SLF001 — SPAN dest Gi0/n
    await service._link(lab_id, sensor["capture_iface"], gi_dest)  # noqa: SLF001
    await service._request("PUT", f"/labs/{lab_id}/start")  # noqa: SLF001 — start ALL nodes
    logger.info("provisioned cell+sensor (%d personas) in lab %s", n, lab_id)
    return {"span_switch": span_id, "personas": results, "sensor": sensor}


async def deploy_cv_sensor_node(service, cv, *, lab_id: str, deployment_name: str, serial: str,
                                server: str, x: int = 0, y: int = 200) -> dict:
    """Mint a sensor JWT, provision a docker Ubuntu sensor node, wire mgmt egress
    (collection → Center) + a capture interface (ens3, for the SPAN). Starts the lab.

    Returns the node id + the interface id of the capture port (the SPAN
    destination the OT switch should mirror to)."""
    jwt = await cv.mint_sensor_jwt(deployment_name, serial)
    compose = _synthesize_sensor_compose(image=cv.sensor_image_ref(), serial=serial, jwt=jwt)
    registry_host = cv.sensor_image_ref().rsplit("/", 1)[0]  # host:port
    cloud_init = build_sensor_cloud_init(compose=compose, registry_host=registry_host,
                                         server=server, name=serial)
    node_id = await service._create_node(  # noqa: SLF001
        lab_id, label=serial[:20], node_definition="ubuntu",
        image_definition="ubuntu-24-04-20241004", ram_mb=4096, cpus=2,
        configuration=cloud_init, x=x, y=y)
    ens2 = await service._create_interface(lab_id, node_id, 0)  # noqa: SLF001 — mgmt/collection
    ens3 = await service._create_interface(lab_id, node_id, 1)  # noqa: SLF001 — capture (SPAN dest)
    nodes = await service._request("GET", f"/labs/{lab_id}/nodes", params={"data": "true"})  # noqa: SLF001
    mgmt_port, _ = await service._ensure_management_egress(  # noqa: SLF001
        lab_id, [n for n in (nodes or []) if isinstance(n, dict) and n.get("id") != node_id])
    await service._link(lab_id, ens2, mgmt_port)  # noqa: SLF001
    logger.info("provisioned CV sensor node %s (serial %s) in lab %s", node_id, serial, lab_id)
    return {"node_id": node_id, "serial": serial, "capture_iface": ens3}
