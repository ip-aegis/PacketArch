# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""File-queue contract shared between the agent and its supervisor sibling.

Mirrors the packetarch-host-agent ``state.py`` pattern: atomic JSON writes on a
shared volume (default ``/state``). The agent NEVER recreates its own container;
on UPDATE_AGENT it drops an ``update-request`` here and the supervisor (which
holds docker.sock) performs the swap, writing progress/outcome back to
``update-status`` for the agent to relay, while the agent emits ``agent-online``
on every successful connect so the supervisor can confirm a swap took.

Artifacts (all under STATE_DIR):
  - update-request.json   agent → supervisor: "update from this server/token"
  - update-status.json    supervisor → agent: progress + terminal outcome
  - agent-online.json      agent → supervisor: health signal (version + ts)
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from typing import Any

STATE_DIR = os.environ.get("AGENT_STATE_DIR", "/state")
_REQUEST = "update-request.json"
_STATUS = "update-status.json"
_ONLINE = "agent-online.json"


def _path(name: str) -> str:
    return os.path.join(STATE_DIR, name)


def supervised() -> bool:
    """True when a supervisor sibling owns this agent's lifecycle.

    Set by install.sh (``AGENT_SUPERVISED=true`` + a mounted ``/state``). Old
    single-service installs lack both → the agent uses its legacy in-container
    self-update fallback.
    """
    return (
        os.environ.get("AGENT_SUPERVISED", "").lower() == "true"
        and os.path.isdir(STATE_DIR)
    )


def _write_atomic(name: str, data: dict[str, Any]) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, _path(name))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read(name: str) -> dict[str, Any] | None:
    try:
        with open(_path(name)) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _unlink(name: str) -> None:
    try:
        os.unlink(_path(name))
    except FileNotFoundError:
        pass


# --- update request (agent → supervisor) ---------------------------------
def write_update_request(req: dict[str, Any]) -> None:
    _write_atomic(_REQUEST, req)


def read_update_request() -> dict[str, Any] | None:
    return _read(_REQUEST)


def clear_update_request() -> None:
    _unlink(_REQUEST)


# --- update status (supervisor → agent → backend) ------------------------
def write_update_status(status: dict[str, Any]) -> None:
    _write_atomic(_STATUS, status)


def read_update_status() -> dict[str, Any] | None:
    return _read(_STATUS)


def clear_update_status() -> None:
    _unlink(_STATUS)


# --- agent online (agent → supervisor health signal) ---------------------
def write_agent_online(version: str | None) -> None:
    _write_atomic(_ONLINE, {"version": version, "ts": time.time()})


def read_agent_online() -> dict[str, Any] | None:
    return _read(_ONLINE)
