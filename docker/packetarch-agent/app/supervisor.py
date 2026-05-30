# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PacketArch agent supervisor.

A long-lived sibling container (same image, ``python -m app.supervisor``) that
OWNS the traffic agent's container lifecycle. The agent never recreates itself:
on UPDATE_AGENT it drops an ``update-request`` on the shared ``/state`` volume,
and this supervisor performs the whole swap from OUTSIDE the agent —
download → ``docker load`` → ``docker compose up -d agent`` → health-watch →
rollback — then writes the outcome back for the agent to relay.

Why this exists: a container cannot reliably recreate itself (nothing owns the
down→up gap; rollback lives in the already-dead process). This mirrors the
proven ``packetarch-host-agent`` reconcile pattern. The supervisor holds the
only docker.sock mount; the agent has none.
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import time

import docker
import httpx

from app import agent_state

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("agent-supervisor")

POLL_INTERVAL = float(os.environ.get("SUPERVISOR_POLL_INTERVAL", "3"))
HEALTH_DEADLINE = float(os.environ.get("SUPERVISOR_HEALTH_DEADLINE", "150"))
DOWNLOAD_TIMEOUT = float(os.environ.get("SUPERVISOR_DOWNLOAD_TIMEOUT", "600"))
INSTALL_DIR = os.environ.get("AGENT_INSTALL_DIR", "/opt/packetarch-agent")
AGENT_SERVICE = os.environ.get("AGENT_COMPOSE_SERVICE", "agent")
IMAGE_REPO = "packetarch-agent"
IMAGE_TAG = f"{IMAGE_REPO}:latest"
_TMP_TARBALL = "/tmp/packetarch-agent-update.tar"


def _compose_file() -> str:
    return os.path.join(INSTALL_DIR, "docker-compose.yml")


def _status(state: str, message: str, **extra) -> None:
    """Publish update progress for the agent to relay to the backend."""
    agent_state.write_update_status(
        {"status": state, "message": message, "ts": time.time(), **extra}
    )
    log.info("update[%s]: %s", state, message)


def _compose(*args: str, timeout: float = 150.0) -> subprocess.CompletedProcess:
    """Run a `docker compose -f <agent compose>` subcommand. Raises on failure."""
    return subprocess.run(
        ["docker", "compose", "-f", _compose_file(), *args],
        check=True, capture_output=True, text=True, timeout=timeout,
    )


def _recreate_agent() -> None:
    """Recreate ONLY the agent service on the current :latest image. `--no-deps`
    keeps the supervisor itself (a sibling service) untouched."""
    _compose("up", "-d", "--no-deps", "--force-recreate", AGENT_SERVICE)


def _wait_healthy(since_ts: float, target_version: str | None) -> bool:
    """Wait for the recreated agent to report it connected (fresh agent-online
    written after `since_ts`), optionally matching the target version."""
    deadline = time.time() + HEALTH_DEADLINE
    while time.time() < deadline:
        online = agent_state.read_agent_online()
        if online and float(online.get("ts", 0)) >= since_ts:
            if not target_version or online.get("version") == target_version:
                return True
        time.sleep(2)
    return False


def _download_and_load(client: docker.DockerClient, req: dict) -> str | None:
    """Download the served tarball (token-auth, air-gap safe) → verify checksum
    → docker load. Returns the loaded image id, or None on failure."""
    server = req["server_url"].rstrip("/")
    image_url = f"{server}/api/v1/agents/image"
    ssl_verify = bool(req.get("ssl_verify", True))
    token = req.get("token", "")

    _status("downloading", "Downloading new agent image...")
    hasher = hashlib.sha256()
    expected = None
    with httpx.stream(
        "GET", image_url,
        headers={"Authorization": f"Bearer {token}"},
        verify=ssl_verify, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True,
    ) as resp:
        resp.raise_for_status()
        expected = resp.headers.get("x-checksum-sha256")
        with open(_TMP_TARBALL, "wb") as f:
            for chunk in resp.iter_bytes(65536):
                f.write(chunk)
                hasher.update(chunk)

    if expected and hasher.hexdigest().lower() != expected.lower():
        _status("failed", "Checksum verification failed", error="checksum")
        _safe_unlink(_TMP_TARBALL)
        return None

    _status("loading", "Loading new image into Docker...")
    with open(_TMP_TARBALL, "rb") as f:
        loaded = client.images.load(f)
    _safe_unlink(_TMP_TARBALL)
    return loaded[0].id if loaded else None


def _handle_request(client: docker.DockerClient, req: dict) -> None:
    target_version = req.get("target_version")

    # Capture the current image for rollback BEFORE the load repoints :latest.
    old_image_id = None
    try:
        old_image_id = client.images.get(IMAGE_TAG).id
    except docker.errors.ImageNotFound:
        log.warning("no current %s image — rollback unavailable", IMAGE_TAG)
    except Exception as e:
        log.warning("could not read current image: %s", e)

    new_image_id = _download_and_load(client, req)
    if new_image_id is None:
        return  # status already set to failed

    if old_image_id and new_image_id == old_image_id:
        _status("complete", "Agent already up to date")
        return

    _status("swapping", "Recreating agent container on the new image...")
    swap_ts = time.time()
    try:
        _recreate_agent()
    except subprocess.CalledProcessError as e:
        _status("failed", f"compose up failed: {(e.stderr or '')[:200]}", error="recreate")
        _rollback(client, old_image_id)
        return
    except subprocess.TimeoutExpired:
        _status("failed", "compose up timed out", error="recreate-timeout")
        _rollback(client, old_image_id)
        return

    if _wait_healthy(swap_ts, target_version):
        _status("complete", f"Update complete (v{target_version or '?'})")
    else:
        _status(
            "failed",
            "New agent did not reconnect within the deadline; rolling back",
            error="health-timeout",
        )
        _rollback(client, old_image_id)


def _rollback(client: docker.DockerClient, old_image_id: str | None) -> None:
    if not old_image_id:
        log.error("rollback requested but no previous image is available")
        return
    log.warning("rolling back to %s", old_image_id[:12])
    try:
        client.images.get(old_image_id).tag(IMAGE_REPO, "latest")
        _recreate_agent()
        _status("failed", "Rolled back to the previous agent version", error="rolledback")
    except Exception as e:
        log.error("rollback failed: %s", e)


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _boot_reconcile() -> None:
    """Ensure the agent service is up on boot (reboot survival)."""
    try:
        _compose("up", "-d", "--no-deps", AGENT_SERVICE)
        log.info("boot reconcile: agent service ensured up")
    except Exception as e:
        log.warning("boot reconcile failed (will retry on next request): %s", e)


def main() -> None:
    log.info("PacketArch agent supervisor starting (install_dir=%s)", INSTALL_DIR)
    try:
        client = docker.from_env()
    except docker.errors.DockerException as e:
        log.error("Docker not available to supervisor: %s", e)
        raise SystemExit(1)

    _boot_reconcile()

    while True:
        try:
            req = agent_state.read_update_request()
            if req:
                agent_state.clear_update_request()
                log.info("update request received")
                _handle_request(client, req)
        except Exception as e:  # never let one bad request kill the supervisor
            log.exception("update handling failed: %s", e)
            try:
                _status("failed", f"supervisor error: {e}", error="exception")
            except Exception:
                pass
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
