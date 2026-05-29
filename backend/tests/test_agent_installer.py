# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Guards for the agent installer / self-update invariant.

Background: the agent self-updates by talking to the host Docker daemon
(``docker.from_env()`` → ``docker load`` the new image → restart itself).
That only works if the agent container has ``/var/run/docker.sock`` bind-
mounted. A stale *second* copy of ``install.sh`` (under
``docker/packetarch-agent/``) that omitted the mount diverged from the
served copy, so every curl-installed / CML-deployed agent silently failed
self-update with "Docker not available" (fixed in v1.5.3, consolidated in
v1.5.5).

These tests pin the invariant — the served installer (and any agent
installer anywhere in the repo) must mount the socket — and assert the
single-source-of-truth so the drift can't return unnoticed.
"""

import pytest
from httpx import AsyncClient

from app.api.routes.agent_install import STATIC_DIR

SOCKET_MOUNT = "/var/run/docker.sock:/var/run/docker.sock"
# STATIC_DIR == backend/app/static/agent → parents[3] is the repo root.
REPO_ROOT = STATIC_DIR.parents[3]
# Marker that uniquely identifies a compose stanza for the agent container
# (distinguishes the agent installer from the full-platform stack installer).
AGENT_CONTAINER_MARKER = "container_name: packetarch-agent"


def test_served_installer_exists_and_mounts_docker_socket():
    """The served /agent/install.sh must write a compose that mounts the socket."""
    install_sh = STATIC_DIR / "install.sh"
    assert install_sh.exists(), "served agent installer (static/agent/install.sh) is missing"
    text = install_sh.read_text()
    assert AGENT_CONTAINER_MARKER in text, "installer no longer writes the agent compose?"
    assert SOCKET_MOUNT in text, (
        "served agent installer's generated docker-compose.yml must bind-mount "
        "/var/run/docker.sock — without it the agent cannot self-update "
        "(fails with 'Docker not available')."
    )


def test_served_compose_mounts_docker_socket():
    """The served standalone /agent/docker-compose.yml must also mount the socket."""
    compose = STATIC_DIR / "docker-compose.agent.yml"
    assert compose.exists(), "served agent docker-compose.agent.yml is missing"
    assert SOCKET_MOUNT in compose.read_text(), (
        "served agent docker-compose.agent.yml must bind-mount /var/run/docker.sock."
    )


def test_no_divergent_agent_installer_without_socket():
    """Any install.sh in the repo that provisions the agent container must mount
    the socket — prevents re-introducing the stale, socket-less duplicate."""
    offenders: list[str] = []
    for sh in REPO_ROOT.rglob("install.sh"):
        parts = set(sh.parts)
        if "node_modules" in parts or "dist" in parts:
            continue  # build output / vendored, not source
        text = sh.read_text(errors="ignore")
        if AGENT_CONTAINER_MARKER in text and SOCKET_MOUNT not in text:
            offenders.append(str(sh.relative_to(REPO_ROOT)))
    assert not offenders, (
        "agent installer(s) provision the agent container without mounting the "
        f"Docker socket (breaks self-update): {offenders}"
    )


def test_agent_installer_is_single_source_of_truth():
    """Exactly one agent installer should exist in source (the served copy).

    The agent *source* dir (docker/packetarch-agent/) must not carry its own
    install.sh again — that fork is what drifted and shipped the bug."""
    stale = REPO_ROOT / "docker" / "packetarch-agent" / "install.sh"
    assert not stale.exists(), (
        "docker/packetarch-agent/install.sh has reappeared — the agent installer "
        "lives only at backend/app/static/agent/install.sh (served at /agent/install.sh)."
    )


@pytest.mark.asyncio
async def test_agent_image_download_is_not_admin_gated(client: AsyncClient):
    """The agent downloads its update image from /api/v1/agents/image using only
    its agent token (no admin JWT). If that route is admin-gated, self-update
    fails with HTTP 401 (regression fixed in v1.5.6). No image exists in the
    test env, so an un-authenticated request should reach the handler and 404 —
    NOT be rejected with 401/403."""
    resp = await client.get("/api/v1/agents/image")
    assert resp.status_code not in (401, 403), (
        f"/api/v1/agents/image must be reachable without admin auth for agent "
        f"self-update, got {resp.status_code}"
    )
