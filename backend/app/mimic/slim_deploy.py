# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Off-box slim-persona deployment onto Alpine CML nodes.

Each persona is its own 512 MB Alpine node (a real host with a real stack). The
backend RESOLVES the persona's identity from the substrate at deploy time (so the
node needs no substrate), and the node's boot config installs Python + pymodbus,
fetches the tiny slim runtime, and runs the persona as a persistent daemon.

Learnings baked in: start the WHOLE lab (switch + connector too); the check-in is
a GET; the sourced boot config runs as a real shell but backgrounded processes
don't survive it — so setup + daemon launch go in an OpenRC ``local.d`` script
(runs after networking) and the persona is launched with ``start-stop-daemon
--background`` (which properly persists).
"""

from __future__ import annotations

import base64
import json
import logging
import re

from app.services.device_templates import get_fingerprint_from_template

logger = logging.getLogger(__name__)

_IMAGE_SLIM_PATH = "/agent/mimic-slim.tar.gz"
_CHECKIN_PATH = "/agent/mimic-checkin"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-") or "mimic-persona"


def resolve_persona(*, name: str, template_id: str, firmware_version: str | None,
                    process_model_id: str | None, protocol: str, port: int, unit_id: int,
                    points: list[dict]) -> dict:
    """Resolve a persona into a self-contained spec (identity baked in)."""
    fp = get_fingerprint_from_template(template_id, firmware_version=firmware_version) or {}
    identity = fp.get(f"{protocol}_identity") or fp.get("modbus_identity") or {}
    return {
        "name": name,
        "bind_ip": "0.0.0.0",
        "firmware_version": fp.get("firmware_version") or firmware_version or "",
        "process_model_id": process_model_id,
        "protocols": [{"protocol": protocol, "port": port, "unit_id": unit_id,
                       "identity": identity, "points": points}],
    }


def build_alpine_boot_config(*, resolved_spec: dict, server: str) -> str:
    """Alpine 'sourced at boot' config: stage the spec + a local.d setup script
    that installs deps, fetches the slim runtime, and daemonizes the persona."""
    server = server.rstrip("/")
    slug = _slug(str(resolved_spec.get("name", "persona")))
    b64_spec = base64.b64encode(json.dumps(resolved_spec).encode()).decode()

    name = _slug(str(resolved_spec.get("name", "persona")))
    port = resolved_spec["protocols"][0]["port"]
    ci = f"wget -q --no-check-certificate -O /dev/null '{server}{_CHECKIN_PATH}?name={name}"
    # pymodbus is pinned to 3.8.x — 3.9+ changed the datastore/device API the slim
    # runtime builds against (would ImportError on 3.14). The persona reports its
    # own liveness via run.py's check-in; setup.sh pings back ONLY if the persona
    # fails to bind, with a scrubbed log tail so a stuck deploy is diagnosable.
    setup = f"""#!/bin/sh
for i in $(seq 1 60); do ip -4 -o addr show eth0 2>/dev/null | grep -q 'inet ' && break; sleep 2; done
apk add --no-cache python3 py3-pip >/dev/null 2>&1
pip3 install --break-system-packages 'pymodbus>=3.8.0,<3.9.0' >/dev/null 2>&1 || pip3 install 'pymodbus>=3.8.0,<3.9.0' >/dev/null 2>&1
cd /opt/mimic && wget --no-check-certificate -qO slim.tar.gz {server}{_IMAGE_SLIM_PATH} && tar xzf slim.tar.gz
start-stop-daemon --start --background --stdout /opt/mimic/persona.log --stderr /opt/mimic/persona.log \\
  --make-pidfile --pidfile /run/mimic.pid --chdir /opt/mimic \\
  --exec /usr/bin/python3 -- -m mimic_slim.run /opt/mimic/spec.json {server}{_CHECKIN_PATH}
sleep 6
if ! netstat -ltn 2>/dev/null | grep -q ':{port}'; then
  ERR=$(tail -c 400 /opt/mimic/persona.log 2>/dev/null | tr '\\n' '~' | tr -cd 'A-Za-z0-9 :~._/-')
  {ci}&stage=bootstrap-failed&err='$ERR 2>/dev/null
fi
"""
    b64_setup = base64.b64encode(setup.encode()).decode()

    # Launch setup.sh via start-stop-daemon --background so it double-forks and
    # survives the boot shell (a plain '&' / setsid does NOT persist here, and
    # Alpine's `local` service already ran before this config, so rc-service is
    # a no-op). setup.sh then waits for the network on its own.
    return f"""# this is a shell script which will be sourced at boot
hostname {slug}
mkdir -p /opt/mimic
echo {b64_spec} | base64 -d > /opt/mimic/spec.json
echo {b64_setup} | base64 -d > /opt/mimic/setup.sh
chmod +x /opt/mimic/setup.sh
start-stop-daemon --start --background --exec /bin/sh -- /opt/mimic/setup.sh
"""


async def deploy_slim_alpine(service, *, lab_id: str, resolved_spec: dict, server: str,
                             x: int = 0, y: int = 0) -> dict:
    """Provision one slim persona as an Alpine node and start the whole lab."""
    cfg = build_alpine_boot_config(resolved_spec=resolved_spec, server=server)
    node_id = await service._create_node(  # noqa: SLF001
        lab_id, label=_slug(str(resolved_spec.get("name", "persona"))),
        node_definition="alpine", image_definition="alpine-base-3-20-3",
        ram_mb=512, cpus=1, configuration=cfg, x=x, y=y,
    )
    eth0 = await service._create_interface(lab_id, node_id, 0)  # noqa: SLF001
    nodes = await service._request("GET", f"/labs/{lab_id}/nodes", params={"data": "true"})  # noqa: SLF001
    port, _ = await service._ensure_management_egress(  # noqa: SLF001
        lab_id, [n for n in (nodes or []) if isinstance(n, dict) and n.get("id") != node_id])
    await service._link(lab_id, eth0, port)  # noqa: SLF001
    await service._request("PUT", f"/labs/{lab_id}/start")  # noqa: SLF001 — start ALL nodes
    logger.info("provisioned slim Alpine persona %s in lab %s", node_id, lab_id)
    return {"node_id": node_id}
