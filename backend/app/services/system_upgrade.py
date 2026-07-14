# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Platform self-upgrade orchestration (git-clone installs).

The backend can't rebuild/restart *itself* while serving a request, so an
upgrade is run by a detached one-off "updater" container launched via the
mounted Docker socket. That container runs ``scripts/upgrade.sh`` against the
host install and writes JSON progress to a shared named volume (mounted at
``/state`` in both the updater and the backend) — which survives the backend
restarting mid-upgrade. The frontend polls the status across that restart.

Mirrors the agent build/update pattern in ``api/routes/agents.py`` (lazy
``import docker``, ``docker.from_env()``, build-on-demand).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Shared with the updater via the upgrade_state named volume (see compose).
STATE_DIR = Path("/state")
STATUS_FILE = STATE_DIR / "upgrade_status.json"

UPDATER_IMAGE = "packetarch-updater:latest"
UPDATER_BUILD_CONTEXT = "/docker/packetarch-updater"  # mounted into the backend
GITHUB_TAGS_URL = "https://api.github.com/repos/ip-aegis/PacketArch/tags"

# Canary bind mount for detecting the pre-v1.18.2 self-upgrade breakage: the
# compose file binds this host dir into the backend; if our own container's
# Source for it doesn't live under HOST_INSTALL_DIR, the updater resolved the
# compose file's relative binds against its /repo alias and the daemon mounted
# empty auto-created host dirs (404 on /agent/install.sh, empty agent build
# context). See heal_aliased_bind_mounts().
CANARY_BIND_DEST = "/app/app/static/agent"
CANARY_BIND_SUBPATH = "backend/app/static/agent"
HEALER_NAME = "packetarch-mount-heal"
# Recreate AFTER the in-flight updater's verify loop (60 x 5s poll) has had
# time to see a healthy backend — the heal itself bounces the backend.
HEALER_DELAY_SECONDS = 120

TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")
TERMINAL = {"success", "failed", "rolled_back"}


# --------------------------------------------------------------------------- #
# Status file (written by upgrade.sh, read here)
# --------------------------------------------------------------------------- #
def read_status() -> dict | None:
    """Return the current upgrade status dict, or None if no upgrade tracked."""
    try:
        if STATUS_FILE.exists():
            return json.loads(STATUS_FILE.read_text())
    except Exception as exc:  # never break the poll
        logger.warning("could not read upgrade status: %s", exc)
    return None


def is_running() -> bool:
    s = read_status()
    return bool(s and s.get("status") == "running")


def clear_status() -> None:
    """Remove a terminal status so the UI returns to idle."""
    try:
        STATUS_FILE.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("could not clear upgrade status: %s", exc)


def _write_queued(target: str, current: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "schema": 1,
        "upgrade_id": f"{now}-api",
        "from_version": current,
        "to_version": target,
        "phase": "queued",
        "status": "running",
        "message": f"Launching upgrade to {target}",
        "started_at": now,
        "updated_at": now,
        "finished_at": None,
        "backup_file": None,
        "error": None,
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(data))
    return data


# --------------------------------------------------------------------------- #
# Release discovery (GitHub tags; air-gap-safe)
# --------------------------------------------------------------------------- #
def _semver_key(tag: str) -> tuple[int, int, int]:
    return tuple(int(p) for p in tag[1:].split("."))  # type: ignore[return-value]


def _fetch_latest_tag_sync() -> str | None:
    req = urllib.request.Request(
        GITHUB_TAGS_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "packetarch"}
    )
    with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310 (trusted URL)
        tags = [t.get("name", "") for t in json.loads(resp.read())]
    valid = sorted((t for t in tags if TAG_RE.match(t)), key=_semver_key, reverse=True)
    return valid[0] if valid else None


async def get_latest_tag() -> str | None:
    """Latest vX.Y.Z release tag from GitHub, or None if unreachable/none."""
    try:
        return await asyncio.to_thread(_fetch_latest_tag_sync)
    except Exception as exc:  # offline / air-gapped / rate-limited
        logger.info("could not check latest release: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# Launch the updater container
# --------------------------------------------------------------------------- #
def _ensure_updater_image(client) -> None:
    import docker  # type: ignore

    try:
        client.images.get(UPDATER_IMAGE)
    except docker.errors.ImageNotFound:
        logger.info("updater image missing — building %s", UPDATER_IMAGE)
        client.images.build(path=UPDATER_BUILD_CONTEXT, tag=UPDATER_IMAGE, rm=True)


def launch_updater(target: str) -> None:
    """Start the detached updater container running upgrade.sh --to <target>.

    Blocking (builds the image on demand if missing); call via ``to_thread``.
    """
    import docker  # lazy, mirrors agents.py

    if not TAG_RE.match(target):
        raise ValueError(f"invalid target version: {target!r}")
    if not settings.host_install_dir:
        raise RuntimeError(
            "HOST_INSTALL_DIR is not set — self-upgrade needs the host install "
            "path to bind-mount into the updater (see .env.example)."
        )

    client = docker.from_env()
    _ensure_updater_image(client)

    state_volume = f"{settings.compose_project_name}_upgrade_state"
    group_add = [settings.docker_gid] if settings.docker_gid else []

    client.containers.run(
        image=UPDATER_IMAGE,
        # argv form — the tag is NEVER interpolated into a shell string.
        command=[
            "scripts/upgrade.sh",
            "--to", target,
            "--status-file", str(STATUS_FILE),
        ],
        detach=True,
        remove=True,
        # The install dir MUST be mounted at its host path (not an alias like
        # /repo): `docker compose up` inside the updater resolves the compose
        # file's relative bind mounts (./backend/app/static/agent, ./docker/...)
        # against the updater's cwd, but the HOST daemon creates the mounts.
        # An aliased path makes the daemon bind-mount empty auto-created host
        # dirs — the backend then serves an empty static/agent (404 on
        # /agent/install.sh) and loses the other source binds.
        working_dir=settings.host_install_dir,
        volumes={
            settings.host_install_dir: {"bind": settings.host_install_dir, "mode": "rw"},
            "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            state_volume: {"bind": "/state", "mode": "rw"},
        },
        environment={
            "COMPOSE_PROJECT_NAME": settings.compose_project_name,
            "DOCKER_GID": settings.docker_gid or "",
        },
        group_add=group_add,
        security_opt=["label:disable"],
    )
    logger.info("launched updater container for upgrade to %s", target)


async def start_upgrade(target: str, current_version: str) -> dict:
    """Write the queued status and launch the updater. Returns the status dict."""
    status = _write_queued(target, current_version)
    try:
        await asyncio.to_thread(launch_updater, target)
    except Exception:
        clear_status()
        raise
    return status


def heal_aliased_bind_mounts() -> str:
    """Boot-time repair for installs broken by the pre-v1.18.2 self-upgrade.

    Older backends launched the updater with the install dir mounted at the
    ``/repo`` alias; ``docker compose up`` inside it resolved the compose
    file's relative bind mounts against that alias, so the HOST daemon
    silently bind-mounted empty auto-created directories over
    ``static/agent`` and the ``./docker`` build contexts.

    Detection: inspect our OWN container's canary bind — its Source must be
    ``<HOST_INSTALL_DIR>/backend/app/static/agent``. If not, launch a
    detached healer container mounted at the REAL host path that re-runs
    ``docker compose up -d`` there: the corrected bind sources change the
    service config hash, so compose recreates the affected containers (this
    backend included) with good mounts. The healer sleeps first so an
    in-flight updater's health verify isn't disturbed. Blocking — call via
    ``asyncio.to_thread``.
    """
    if not settings.host_install_dir:
        return "skipped (HOST_INSTALL_DIR unset)"

    import socket

    import docker  # lazy, mirrors launch_updater

    try:
        client = docker.from_env()
        me = client.containers.get(socket.gethostname())
    except Exception as e:  # not in a container / no socket (dev uvicorn)
        return f"skipped (no docker introspection: {e})"

    canary = next(
        (
            m
            for m in me.attrs.get("Mounts", [])
            if m.get("Type") == "bind" and m.get("Destination") == CANARY_BIND_DEST
        ),
        None,
    )
    if canary is None:
        # Offline-bundle compose has no static/agent bind — nothing to heal.
        return "skipped (no static/agent bind mount)"

    expected = str(Path(settings.host_install_dir) / CANARY_BIND_SUBPATH)
    actual = canary.get("Source", "")
    if actual == expected:
        return "ok"

    logger.warning(
        "aliased bind mounts detected (static/agent bound from %s, expected %s) "
        "— launching healer to recreate the stack from %s",
        actual,
        expected,
        settings.host_install_dir,
    )
    group_add = [settings.docker_gid] if settings.docker_gid else []
    try:
        client.containers.run(
            image=UPDATER_IMAGE,
            name=HEALER_NAME,
            command=[
                "sh",
                "-c",
                f"sleep {HEALER_DELAY_SECONDS} && exec docker compose up -d",
            ],
            detach=True,
            remove=True,
            working_dir=settings.host_install_dir,
            volumes={
                settings.host_install_dir: {"bind": settings.host_install_dir, "mode": "rw"},
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            },
            environment={
                "COMPOSE_PROJECT_NAME": settings.compose_project_name,
                "DOCKER_GID": settings.docker_gid or "",
            },
            group_add=group_add,
            security_opt=["label:disable"],
        )
    except docker.errors.APIError as e:
        if "Conflict" in str(e):
            return "healer already running"
        logger.warning(
            "mount healer launch failed (%s) — repair manually: "
            "cd %s && docker compose up -d --force-recreate",
            e,
            settings.host_install_dir,
        )
        return f"healer launch failed: {e}"
    return (
        f"aliased mounts detected — healer launched (recreates stack from "
        f"{settings.host_install_dir} in {HEALER_DELAY_SECONDS}s)"
    )
