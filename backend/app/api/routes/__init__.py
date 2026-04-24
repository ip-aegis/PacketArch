# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""API routes."""

from app.api.routes import (
    admin,
    ai,
    anomalies,
    auth,
    cve,
    deployments,
    fingerprints,
    generation,
    health,
    ip_management,
    ldap,

    protocols,
    scenarios,
    stats,
    templates,
    users,
)

__all__ = [
    "admin",
    "ai",
    "anomalies",
    "auth",
    "cve",
    "deployments",
    "fingerprints",
    "generation",
    "health",
    "ip_management",
    "ldap",

    "protocols",
    "scenarios",
    "stats",
    "templates",
    "users",
]
