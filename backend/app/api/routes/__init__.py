"""API routes."""

from app.api.routes import (
    admin,
    ai,
    anomalies,
    auth,
    cve,
    deployments,
    devices,
    docker_hosts,
    fingerprints,
    generation,
    health,
    ip_management,

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
    "devices",
    "docker_hosts",
    "fingerprints",
    "generation",
    "health",
    "ip_management",

    "protocols",
    "scenarios",
    "stats",
    "templates",
    "users",
]
