# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Mimic cell deployment — translate persona specs into a host-agent mimic cell.

The unprivileged backend never touches the host: it builds a kind="mimic" spec
(device wiring — container names, vendor-aligned MACs, IPs, veth names — plus each
`PersonaSpec`) and submits it over the host-agent file-queue. The privileged
host-agent provisions the personas onto the target lab's SPAN (hub-bridge + netns)
and the lab's existing CV sensor classifies them. No CV token, no new sensor.

P0: an optional active poller is appended so the passive sensor observes Modbus
traffic; P1 replaces it with a real active-master persona.
"""

from __future__ import annotations

import hashlib
import logging

from app.protocol_engines.canonical_identity import canonical_mac
from app.services import host_agent_client
from app.services.device_templates import get_fingerprint_from_template

from .interfaces import PersonaSpec

logger = logging.getLogger(__name__)


def _short(text: str, n: int = 8) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:n]


def build_cell_spec(
    *,
    lab_slug: str,
    gen_if: str,
    cell_name: str,
    personas: list[PersonaSpec],
    subnet: str = "10.60.0",
    add_poller: bool = True,
    persona_image: str | None = None,
) -> dict:
    """Build a kind="mimic" host-agent spec from persona specs.

    Assigns each persona an IP (``subnet.10``, ``.20``, …), a vendor-aligned MAC
    (deterministic from the shared identity substrate), TTL from the template
    ``tcp_stack``, and short veth names. When ``add_poller`` and there's a Modbus
    persona, appends a poller that drives FC43 + register reads at the first one.
    """
    cell_slug = "mm-" + _short(lab_slug + cell_name)
    devices: list[dict] = []
    first_modbus: tuple[str, int] | None = None

    for i, ps in enumerate(personas):
        ip = f"{subnet}.{10 + i * 10}"
        ps.bind_ip = ip
        fp = get_fingerprint_from_template(ps.template_id, firmware_version=ps.firmware_version) or {}
        ouis = fp.get("oui_prefixes") or ["02:00:00"]
        mac = canonical_mac(ps.device_id, ps.scenario_id, fp.get("vendor", ""), ouis)
        ttl = int((fp.get("tcp_stack") or {}).get("ttl", 64))
        tag = _short(ps.device_id, 6)
        dev = {
            "container": f"pa-mm-{cell_slug[3:]}-{tag}",
            "mac": mac,
            "ip": f"{ip}/24",
            "ttl": ttl,
            "veth_br": f"mmb-{tag}",
            "veth_ns": f"mmc-{tag}",
            "spec": ps.to_dict(),
        }
        if persona_image:
            dev["image"] = persona_image
        devices.append(dev)
        if first_modbus is None:
            for pb in ps.protocols:
                if pb.protocol == "modbus":
                    first_modbus = (ip, pb.port)
                    break

    if add_poller and first_modbus is not None:
        tip, tport = first_modbus
        ptag = _short(cell_slug + "poller", 6)
        poller = {
            "container": f"pa-mm-{cell_slug[3:]}-poll",
            "mac": f"02:60:00:00:00:{len(devices):02x}",
            "ip": f"{subnet}.200/24",
            "ttl": 64,
            "veth_br": f"mmb-{ptag}",
            "veth_ns": f"mmc-{ptag}",
            "command": ["python", "-m", "app.mimic.poll", tip, str(tport)],
        }
        if persona_image:
            poller["image"] = persona_image
        devices.append(poller)

    return {
        "kind": "mimic",
        "slug": cell_slug,
        "name": cell_name,
        "lab_slug": lab_slug,
        "gen_if": gen_if,
        "devices": devices,
    }


def deploy_cell(
    *,
    lab_slug: str,
    gen_if: str,
    cell_name: str,
    personas: list[PersonaSpec],
    persona_image: str | None = None,
) -> dict:
    """Build and submit a Mimic cell. Returns cell slug, request id, containers."""
    if not host_agent_client.is_available():
        raise host_agent_client.HostAgentUnavailable(
            "host-agent state volume not mounted — Mimic needs the on-box host-agent"
        )
    spec = build_cell_spec(lab_slug=lab_slug, gen_if=gen_if, cell_name=cell_name,
                           personas=personas, persona_image=persona_image)
    rid = host_agent_client.submit_emulate(spec)
    logger.info("submitted mimic cell %s (%d devices) for lab %s",
                spec["slug"], len(spec["devices"]), lab_slug)
    return {
        "cell_slug": spec["slug"],
        "request_id": rid,
        "containers": [d["container"] for d in spec["devices"]],
    }


def teardown_cell(cell_slug: str) -> str:
    """Tear down a Mimic cell (personas + hub-bridge; lab untouched)."""
    return host_agent_client.submit_teardown_mimic(cell_slug)
