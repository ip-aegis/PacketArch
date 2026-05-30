# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Host-level operations for local sensor labs.

Every function here is IDEMPOTENT — safe to re-run — because the reconcile loop
calls them repeatedly to make host reality match the desired specs. This is the
ported, multi-lab-aware version of scripts/local-sensor/*.sh (proven manually,
see the local_sensor_lab notes).

Runs inside the privileged, host-networked (`network_mode: host`), host-pid
(`pid: host`) host-agent container, so:
  - `ip link` / `ethtool` operate on the HOST network namespace directly,
  - `kill -HUP <dockerd>` reaches the host dockerd (live-reloads daemon.json),
  - `docker` talks to the host daemon over the mounted socket.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

import yaml

log = logging.getLogger("hostagent.hostops")

DAEMON_JSON = Path("/etc/docker/daemon.json")


class HostOpError(RuntimeError):
    pass


def _run(cmd: list[str], *, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
    log.debug("run: %s", " ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise HostOpError(f"{' '.join(cmd[:3])}… exited {p.returncode}: {p.stderr.strip() or p.stdout.strip()}")
    return p


# --- veth crossover (the local "SPAN") --------------------------------------

def _link_exists(name: str) -> bool:
    return _run(["ip", "link", "show", name], check=False).returncode == 0


def ensure_veth(gen_if: str, mon_if: str, mtu: int = 1500) -> None:
    """Create (if absent) an isolated veth crossover gen_if<->mon_if, both up +
    promiscuous, offloads disabled. No uplink — sim traffic can't leak."""
    if not _link_exists(gen_if):
        log.info("creating veth %s <-> %s (mtu %d)", gen_if, mon_if, mtu)
        _run(["ip", "link", "add", gen_if, "mtu", str(mtu),
              "type", "veth", "peer", "name", mon_if, "mtu", str(mtu)])
    for ifc in (gen_if, mon_if):
        _run(["ip", "link", "set", ifc, "up", "promisc", "on"])
        # best-effort: disable offloads so injected frames aren't coalesced
        _run(["ethtool", "-K", ifc, "tx", "off", "rx", "off",
              "gso", "off", "tso", "off", "gro", "off", "lro", "off"], check=False)


def remove_macvlan_networks_on(parent_if: str) -> None:
    """Remove any docker macvlan network whose parent is `parent_if`. Must run
    BEFORE delete_veth: a macvlan network holding the veth as its parent blocks
    both the veth delete and a later same-parent recreate ("cannot use mode
    passthru, macvlan ... already using parent interface"). Idempotent. Also
    catches orphans from older naming schemes that `docker compose down` (which
    only owns project-scoped names) would miss."""
    p = _run(["docker", "network", "ls", "--filter", "driver=macvlan",
              "--format", "{{.Name}}"], check=False)
    for net in p.stdout.split():
        info = _run(["docker", "network", "inspect", net,
                     "--format", "{{index .Options \"parent\"}}"], check=False)
        if info.stdout.strip() == parent_if:
            log.info("removing macvlan network %s (parent %s)", net, parent_if)
            _run(["docker", "network", "rm", net], check=False)


def delete_veth(gen_if: str) -> None:
    """Delete the veth pair (its peer goes with it). Idempotent."""
    if _link_exists(gen_if):
        log.info("deleting veth %s", gen_if)
        _run(["ip", "link", "del", gen_if], check=False)


def veth_ok(gen_if: str, mon_if: str) -> bool:
    return _link_exists(gen_if) and _link_exists(mon_if)


# --- insecure registry trust on the host daemon -----------------------------

def _dockerd_pids() -> list[str]:
    p = _run(["pidof", "dockerd"], check=False)
    return p.stdout.split() if p.returncode == 0 else []


def ensure_registry_trusted(registry: str) -> bool:
    """Add `registry` to /etc/docker/daemon.json insecure-registries and SIGHUP
    dockerd to live-reload (NEVER restart — that would bounce PacketArch).
    Returns True if a change was made. Idempotent."""
    if not registry:
        return False
    try:
        cfg = json.loads(DAEMON_JSON.read_text()) if DAEMON_JSON.exists() else {}
    except json.JSONDecodeError:
        cfg = {}
    regs = cfg.get("insecure-registries") or []
    if registry in regs:
        return False
    regs.append(registry)
    cfg["insecure-registries"] = regs
    DAEMON_JSON.write_text(json.dumps(cfg, indent=2))
    log.info("trusted insecure registry %s; SIGHUP dockerd", registry)
    for pid in _dockerd_pids():
        _run(["kill", "-HUP", pid], check=False)
    return True


def untrust_registry_if_unused(registry: str, all_specs: list[dict]) -> bool:
    """Remove `registry` from daemon.json iff no remaining spec references it.
    Returns True if removed. Idempotent."""
    if not registry or not DAEMON_JSON.exists():
        return False
    if any((s.get("registry") == registry) for s in all_specs):
        return False
    try:
        cfg = json.loads(DAEMON_JSON.read_text())
    except json.JSONDecodeError:
        return False
    regs = cfg.get("insecure-registries") or []
    if registry not in regs:
        return False
    regs.remove(registry)
    cfg["insecure-registries"] = regs
    DAEMON_JSON.write_text(json.dumps(cfg, indent=2))
    log.info("removed unused insecure registry %s; SIGHUP dockerd", registry)
    for pid in _dockerd_pids():
        _run(["kill", "-HUP", pid], check=False)
    return True


# --- compose generation (per-lab unique names) ------------------------------

def rewrite_sensor_compose(compose_text: str, *, slug: str, mon_if: str, sensor_container: str) -> str:
    """Rewrite the operator-pasted CV docker-compose so N labs coexist on one
    host: unique container name, unique docker network names, and the macvlan
    capture parent forced to this lab's mon_if. YAML-aware (the old sed only
    handled `parent:`, which collided across labs)."""
    doc = yaml.safe_load(compose_text)
    if not isinstance(doc, dict):
        raise HostOpError("sensor compose is not a valid YAML mapping")

    # 1) container_name on the (single) sensor service
    services = doc.get("services") or {}
    for svc in services.values():
        if isinstance(svc, dict):
            svc["container_name"] = sensor_container

    # 2) macvlan capture parent + per-lab network uniqueness.
    #
    # Per-lab uniqueness comes for FREE from `docker compose -p palab-<slug>-
    # sensor`, which project-prefixes every network's real name. So we must NOT
    # set an explicit `name:` — doing so both pins a global name (collisions
    # across labs) AND, when we renamed by driver, reordered the networks so the
    # gatewayless macvlan won the default-route slot, leaving the sensor with no
    # route to the CV Center ("no provisioning package found ... sleeping").
    #
    # We therefore STRIP any explicit `name:` (restoring compose's auto-prefix)
    # and only force the macvlan capture parent. Stripping keeps the original CV
    # network KEYS, whose ordering (`...-0-collection` before `...-capture-1`)
    # keeps the routable bridge as the default gateway.
    networks = doc.get("networks") or {}
    for key, net in networks.items():
        if not isinstance(net, dict):
            net = {}
            networks[key] = net
        net.pop("name", None)
        if str(net.get("driver")) == "macvlan":
            opts = net.get("driver_opts") or {}
            opts["parent"] = mon_if
            net["driver_opts"] = opts

    return yaml.safe_dump(doc, sort_keys=False)


def write_agent_compose(work: Path, spec: dict) -> Path:
    """Write a per-lab agent compose + .env (templated container name +
    injection interface). Mirrors backend/app/static/agent/install.sh."""
    env = (
        f"PACKETARCH_SERVER={spec['server_url']}\n"
        f"AGENT_TOKEN={spec['agent_token']}\n"
        f"DEFAULT_INTERFACE={spec['gen_if']}\n"
        f"LOG_LEVEL=INFO\n"
        f"SSL_VERIFY={'false' if spec.get('insecure') else 'true'}\n"
    )
    (work / ".env").write_text(env)
    compose = {
        "services": {
            "agent": {
                "image": "packetarch-agent:latest",
                "container_name": spec["agent_container"],
                "restart": "unless-stopped",
                "network_mode": "host",
                "cap_add": ["NET_ADMIN", "NET_RAW"],
                "env_file": [".env"],
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
                "logging": {"driver": "json-file",
                            "options": {"max-size": "10m", "max-file": "3"}},
            }
        }
    }
    path = work / "agent-compose.yml"
    path.write_text(yaml.safe_dump(compose, sort_keys=False))
    return path


# --- docker compose / image helpers -----------------------------------------

def _project(slug: str, suffix: str) -> str:
    return f"palab-{slug}-{suffix}"


def ensure_agent_image(spec: dict) -> None:
    """Ensure packetarch-agent:latest exists on the host; if missing, pull the
    tarball the backend serves and `docker load` it (mirrors install.sh)."""
    if _run(["docker", "image", "inspect", "packetarch-agent:latest"], check=False).returncode == 0:
        return
    url = f"{spec['server_url'].rstrip('/')}/agent/image.tar.gz"
    log.info("agent image missing — downloading %s", url)
    curl = ["curl", "-fsSL"] + (["-k"] if spec.get("insecure") else []) + ["-o", "/tmp/pa-agent.tar.gz", url]
    _run(curl, timeout=300)
    _run(["sh", "-c", "gunzip -c /tmp/pa-agent.tar.gz | docker load"], timeout=300)
    _run(["docker", "tag", "ghcr.io/ip-aegis/packetarch-agent:latest", "packetarch-agent:latest"], check=False)


def compose_up(compose_file: Path, project: str) -> None:
    _run(["docker", "compose", "-p", project, "-f", str(compose_file), "up", "-d"], timeout=300)


def compose_down(compose_file: Path, project: str) -> None:
    _run(["docker", "compose", "-p", project, "-f", str(compose_file),
          "down", "--remove-orphans"], check=False, timeout=300)


def container_running(name: str) -> bool:
    p = _run(["docker", "ps", "--filter", f"name=^{re.escape(name)}$",
              "--filter", "status=running", "--format", "{{.Names}}"], check=False)
    return name in p.stdout.split()


def sensor_compose_path(work: Path) -> Path:
    return work / "sensor-compose.yml"
