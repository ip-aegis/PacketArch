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

import re
import uuid

# Linux interface names cap at 15 chars: "pa-gen-" (7) + 8-char slug = 15. OK.
_SLUG_LEN = 8

# CV's own sensor-name field validates against an alphanumeric-dot-dash
# pattern (confirmed by reading the CV Center's own web UI bundle). CV does
# NOT document a max length, but live-testing against a real Center found a
# hard one: the provisioning JWT embeds the serial alongside the Center's own
# host/IP, and CV rejects the mint outright ("Generated JWT would be too long
# for the sensor application") once the encoded token gets too big — a 12-char
# centerHost allowed at most a 45-char serial. That budget shrinks for any
# Center with a longer hostname/FQDN, which we can't know in advance, so stay
# well clear of it rather than precompute a cap that only holds for this one
# Center — short names over a nice-but-fragile long one.
_SENSOR_SERIAL_MAX_LEN = 24


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


def sensor_serial(name: str, slug: str) -> str:
    """CV sensor serial/name: a short, sanitized, human-recognizable prefix
    (from the lab's own name — e.g. the scenario name, when a lab is built as
    part of deploying one) plus the lab's unique slug, so the sensor shows up
    in the CV Center as something like `bakery-sensor-a1b2c3d4` instead of an
    opaque id — kept deliberately short (see _SENSOR_SERIAL_MAX_LEN) to stay
    well clear of CV's JWT-length limit. CV requires sensor names to be
    unique per Center; the slug guarantees that regardless of how many labs
    share a human-readable name (scenario names aren't unique in PacketArch).
    """
    slug_suffix = f"-{slug}"
    budget = _SENSOR_SERIAL_MAX_LEN - len(slug_suffix)
    sanitized = re.sub(r"[^a-zA-Z0-9.-]+", "-", name.strip()).strip("-").lower()
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    prefix = sanitized[:budget].rstrip("-") or "lab"
    return f"{prefix}{slug_suffix}"
