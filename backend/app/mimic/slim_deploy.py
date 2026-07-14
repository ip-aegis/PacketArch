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

# Per-protocol: default port, the pinned pip dep, and any apk build deps the node
# needs. c104 (IEC-104) has no musllinux wheel, so it builds from source on Alpine
# — hence the toolchain. pymodbus/asyncua/bacpypes3 install from wheels.
PROTOCOL_DEPS: dict[str, dict[str, str]] = {
    "modbus": {"port": "502", "pip": "pymodbus>=3.8.0,<3.9.0", "apk": ""},
    "opcua": {"port": "4840", "pip": "asyncua>=2.0.1,<2.1.0", "apk": ""},
    "bacnet": {"port": "47808", "pip": "bacpypes3>=0.0.106,<0.1.0", "apk": ""},
    "iec104": {"port": "2404", "pip": "c104>=2.2.1,<2.3.0", "apk": "build-base cmake python3-dev linux-headers"},
}

# Protocols whose dep must COMPILE on the node (no musl wheel) need a bigger node —
# a pybind11/C++ build OOMs the 512 MB slim default. FOLLOW-UP: serve a prebuilt
# musllinux c104 wheel so iec104 nodes can stay slim + skip the multi-minute build.
_COMPILE_PROTOCOLS = {"iec104"}
_SLIM_RAM_MB, _SLIM_CPUS = 512, 1
_COMPILE_RAM_MB, _COMPILE_CPUS = 2048, 2


def _node_resources(protocols: list[str]) -> tuple[int, int]:
    if any(p in _COMPILE_PROTOCOLS for p in protocols):
        return _COMPILE_RAM_MB, _COMPILE_CPUS
    return _SLIM_RAM_MB, _SLIM_CPUS


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-") or "mimic-persona"


def default_port(protocol: str) -> int:
    return int(PROTOCOL_DEPS.get(protocol, {}).get("port", "502"))


def _resolve_identity(fp: dict, protocol: str, name: str, firmware: str) -> dict:
    """Build the wire-identity dict for one protocol from the fingerprint — the
    slim (deploy-time) twin of what DevicePersona.build() assembles on-box."""
    vendor = fp.get("vendor") or ""
    model = fp.get("model") or fp.get("vendor_family") or name
    if protocol == "modbus":
        return fp.get("modbus_identity") or {}
    if protocol == "opcua":
        oi = fp.get("opc_ua_identity") or {}
        return {"vendor": vendor, "model_name": model, "firmware": firmware,
                "device_name": name, "application_uri": oi.get("application_uri"),
                "product_uri": oi.get("product_uri")}
    if protocol == "bacnet":
        bi = fp.get("bacnet_identity") or {}
        return {"vendor_id": bi.get("vendor_id", 0), "object_name": bi.get("object_name"),
                "model_name": bi.get("model_name") or model, "device_name": name,
                "firmware": firmware}
    return {}  # iec104 carries no identity dict


def resolve_persona(*, name: str, template_id: str, firmware_version: str | None,
                    process_model_id: str | None, protocol: str, port: int | None, unit_id: int,
                    points: list[dict]) -> dict:
    """Resolve a persona into a self-contained spec (identity baked in at deploy
    time, so the node needs no substrate)."""
    fp = get_fingerprint_from_template(template_id, firmware_version=firmware_version) or {}
    firmware = fp.get("firmware_version") or firmware_version or ""
    return {
        "name": name,
        "bind_ip": "0.0.0.0",
        "firmware_version": firmware,
        "process_model_id": process_model_id,
        "protocols": [{"protocol": protocol, "port": port or default_port(protocol),
                       "unit_id": unit_id,
                       "identity": _resolve_identity(fp, protocol, name, firmware),
                       "points": points}],
    }


def build_alpine_boot_config(*, resolved_spec: dict, server: str) -> str:
    """Alpine 'sourced at boot' config: stage the spec + a local.d setup script
    that installs deps, fetches the slim runtime, and daemonizes the persona."""
    server = server.rstrip("/")
    slug = _slug(str(resolved_spec.get("name", "persona")))
    b64_spec = base64.b64encode(json.dumps(resolved_spec).encode()).decode()

    name = _slug(str(resolved_spec.get("name", "persona")))
    protos = [p["protocol"] for p in resolved_spec.get("protocols", [])]
    clients = resolved_spec.get("clients", [])
    port = resolved_spec["protocols"][0]["port"] if resolved_spec.get("protocols") else default_port("modbus")
    # Collect the pip + apk deps for exactly the protocol(s) this persona serves —
    # each pinned (a fresh pip grabs the latest, e.g. pymodbus 3.14 breaks the
    # datastore API). c104/iec104 pulls the build toolchain (no musl wheel). A
    # client-only persona (HMI, no servers) still needs pymodbus for its poll loop.
    dep_protos = list(protos)
    if any(c.get("protocol", "modbus") == "modbus" for c in clients):
        dep_protos.append("modbus")
    pips = " ".join(dict.fromkeys(
        f"'{PROTOCOL_DEPS[p]['pip']}'" for p in dep_protos if p in PROTOCOL_DEPS))
    apks = " ".join(dict.fromkeys(
        d for p in dep_protos for d in PROTOCOL_DEPS.get(p, {}).get("apk", "").split() if d))
    # Static data-segment IP (eth1) for the OT plane — the mgmt path (eth0) stays
    # DHCP for tarball fetch + check-in. A client-only HMI has no server to bind,
    # so skip the netstat check for it.
    data_ip = resolved_spec.get("data_ip")
    data_pfx = resolved_spec.get("data_prefix", 24)
    eth1 = (f"ip addr add {data_ip}/{data_pfx} dev eth1 2>/dev/null; ip link set eth1 up 2>/dev/null\n"
            if data_ip else "")
    bind_check = bool(resolved_spec.get("protocols"))
    ci = f"wget -q --no-check-certificate -O /dev/null '{server}{_CHECKIN_PATH}?name={name}"
    # The persona reports its own liveness via run.py's check-in; setup.sh pings
    # back ONLY if it fails to bind, with a scrubbed log tail so a stuck deploy is
    # diagnosable (CML's API console is read-only).
    fail_check = (f"""sleep 6
if ! netstat -ln 2>/dev/null | grep -q ':{port} '; then
  ERR=$(tail -c 400 /opt/mimic/persona.log 2>/dev/null | tr '\\n' '~' | tr -cd 'A-Za-z0-9 :~._/-')
  {ci}&stage=bootstrap-failed&err='$ERR 2>/dev/null
fi
""" if bind_check else "")
    setup = f"""#!/bin/sh
for i in $(seq 1 60); do ip -4 -o addr show eth0 2>/dev/null | grep -q 'inet ' && break; sleep 2; done
{eth1}apk add --no-cache python3 py3-pip {apks} >/dev/null 2>&1
pip3 install --break-system-packages {pips} >/dev/null 2>&1 || pip3 install {pips} >/dev/null 2>&1
cd /opt/mimic && wget --no-check-certificate -qO slim.tar.gz {server}{_IMAGE_SLIM_PATH} && tar xzf slim.tar.gz
start-stop-daemon --start --background --stdout /opt/mimic/persona.log --stderr /opt/mimic/persona.log \\
  --make-pidfile --pidfile /run/mimic.pid --chdir /opt/mimic \\
  --exec /usr/bin/python3 -- -m mimic_slim.run /opt/mimic/spec.json {server}{_CHECKIN_PATH}
{fail_check}"""
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
    ram_mb, cpus = _node_resources([p["protocol"] for p in resolved_spec.get("protocols", [])])
    node_id = await service._create_node(  # noqa: SLF001
        lab_id, label=_slug(str(resolved_spec.get("name", "persona"))),
        node_definition="alpine", image_definition="alpine-base-3-20-3",
        ram_mb=ram_mb, cpus=cpus, configuration=cfg, x=x, y=y,
    )
    eth0 = await service._create_interface(lab_id, node_id, 0)  # noqa: SLF001
    nodes = await service._request("GET", f"/labs/{lab_id}/nodes", params={"data": "true"})  # noqa: SLF001
    port, _ = await service._ensure_management_egress(  # noqa: SLF001
        lab_id, [n for n in (nodes or []) if isinstance(n, dict) and n.get("id") != node_id])
    await service._link(lab_id, eth0, port)  # noqa: SLF001
    await service._request("PUT", f"/labs/{lab_id}/start")  # noqa: SLF001 — start ALL nodes
    logger.info("provisioned slim Alpine persona %s in lab %s", node_id, lab_id)
    return {"node_id": node_id}


async def deploy_slim_cell(service, *, lab_id: str, resolved_specs: list[dict], server: str) -> dict:
    """Provision a CELL of slim personas that talk over a shared OT data segment.

    Each node gets eth0 → management egress (DHCP: tarball fetch + check-in) and
    eth1 → a shared unmanaged data switch, statically addressed via ``data_ip`` in
    the spec. An HMI's client bindings target a peer's ``data_ip`` — so the poll
    traffic rides the isolated data segment, where a CV sensor can later capture it.
    """
    # Shared OT data-plane switch.
    data_sw = await service._create_node(  # noqa: SLF001
        lab_id, label="pa-ot-switch", node_definition="unmanaged_switch",
        image_definition="", ram_mb=0, cpus=0, configuration="", x=0, y=200)
    results = []
    for i, spec in enumerate(resolved_specs):
        cfg = build_alpine_boot_config(resolved_spec=spec, server=server)
        ram_mb, cpus = _node_resources([p["protocol"] for p in spec.get("protocols", [])])
        node_id = await service._create_node(  # noqa: SLF001
            lab_id, label=_slug(str(spec.get("name", "persona"))),
            node_definition="alpine", image_definition="alpine-base-3-20-3",
            ram_mb=ram_mb, cpus=cpus, configuration=cfg, x=i * 200 - 100, y=-40)
        eth0 = await service._create_interface(lab_id, node_id, 0)  # noqa: SLF001
        eth1 = await service._create_interface(lab_id, node_id, 1)  # noqa: SLF001
        nodes = await service._request("GET", f"/labs/{lab_id}/nodes", params={"data": "true"})  # noqa: SLF001
        mgmt_port, _ = await service._ensure_management_egress(  # noqa: SLF001
            lab_id, [n for n in (nodes or []) if isinstance(n, dict) and n.get("id") != node_id])
        await service._link(lab_id, eth0, mgmt_port)  # noqa: SLF001
        data_port = await service._next_switch_port(lab_id, data_sw)  # noqa: SLF001
        await service._link(lab_id, eth1, data_port)  # noqa: SLF001
        results.append({"name": spec.get("name"), "node_id": node_id, "data_ip": spec.get("data_ip")})
    await service._request("PUT", f"/labs/{lab_id}/start")  # noqa: SLF001 — start ALL nodes
    logger.info("provisioned slim cell of %d personas in lab %s", len(results), lab_id)
    return {"data_switch": data_sw, "personas": results}
