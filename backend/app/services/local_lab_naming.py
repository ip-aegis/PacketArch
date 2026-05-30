# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Per-lab resource naming — single source of truth.

These pure functions derive every host resource name for a local sensor lab from
its slug, so N labs coexist on one host without collisions. The backend uses
them to write lab specs; the host-agent derives the same names when it acts.
Keep the scheme in lockstep with docker/packetarch-host-agent (the host-agent
templates container/network names itself from gen_if/mon_if/sensor_container in
the spec, so the authoritative names are the ones produced here).
"""

from __future__ import annotations

import uuid

# Linux interface names cap at 15 chars: "pa-gen-" (7) + 8-char slug = 15. OK.
_SLUG_LEN = 8


def make_slug(lab_id: uuid.UUID | str) -> str:
    """Short, stable, DNS/iface-safe slug from a lab UUID (first 8 hex chars)."""
    s = str(lab_id).replace("-", "")
    return s[:_SLUG_LEN]


def gen_if(slug: str) -> str:
    """Agent injection interface (veth gen end)."""
    return f"pa-gen-{slug}"


def mon_if(slug: str) -> str:
    """Sensor capture interface (veth mon end = macvlan parent)."""
    return f"pa-mon-{slug}"


def agent_container(slug: str) -> str:
    return f"packetarch-agent-{slug}"


def sensor_container(slug: str) -> str:
    return f"ccv-sensor-{slug}"


def agent_name_default(slug: str) -> str:
    return f"Local-Sensor-{slug}"
