# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Backend-side client for the privileged host-agent.

The backend never touches the host directly. It communicates with the
host-agent (docker/packetarch-host-agent) over a shared volume file-queue:
the backend writes desired lab specs + build/teardown requests; the host-agent
reconciles host reality and writes back live status. This module is the typed
wrapper around that contract (kept in lockstep with
docker/packetarch-host-agent/app/state.py).

Reliability first: writes are atomic (tmp + rename) so the host-agent never
reads a partial file; losing a request is harmless because `specs/` is the
durable desired state the host-agent reconciles from.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path

# The backend mounts the same `host_agent_state` volume the host-agent uses,
# at /hostagent, so the queue root matches the host-agent's HOST_AGENT_STATE.
STATE_ROOT = Path(os.environ.get("HOST_AGENT_STATE", "/hostagent/local-labs"))
REQUESTS_DIR = STATE_ROOT / "requests"
RESULTS_DIR = STATE_ROOT / "results"
SPECS_DIR = STATE_ROOT / "specs"
STATUS_DIR = STATE_ROOT / "status"


class HostAgentUnavailable(RuntimeError):
    """Raised when the shared state volume isn't mounted (host-agent not wired)."""


def is_available() -> bool:
    """True if the shared state volume is mounted (host-agent deployment present)."""
    return STATE_ROOT.parent.exists()


def _ensure_dirs() -> None:
    if not is_available():
        raise HostAgentUnavailable(
            f"host-agent state volume not mounted at {STATE_ROOT.parent} — "
            "is the host-agent service running and the volume shared with the backend?"
        )
    for d in (REQUESTS_DIR, RESULTS_DIR, SPECS_DIR, STATUS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _read_json(path: Path) -> dict | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def submit_build(spec: dict) -> str:
    """Queue a build request for a lab spec. Returns the request id."""
    _ensure_dirs()
    rid = str(uuid.uuid4())
    _write_atomic(REQUESTS_DIR / f"{rid}.json", {"id": rid, "action": "build", "lab": spec})
    return rid


def submit_teardown(slug: str) -> str:
    """Queue a full-delete teardown for a lab slug. Returns the request id."""
    _ensure_dirs()
    rid = str(uuid.uuid4())
    _write_atomic(REQUESTS_DIR / f"{rid}.json",
                  {"id": rid, "action": "teardown", "lab": {"slug": slug}})
    return rid


def submit_emulate(spec: dict) -> str:
    """Queue a Mimic-cell provision (device personas on an existing lab's SPAN).
    `spec` is a kind="mimic" spec (see host-agent state.py). Returns request id."""
    _ensure_dirs()
    rid = str(uuid.uuid4())
    _write_atomic(REQUESTS_DIR / f"{rid}.json", {"id": rid, "action": "emulate", "lab": spec})
    return rid


def submit_teardown_mimic(slug: str) -> str:
    """Queue teardown of a Mimic cell (stops personas + hub-bridge, keeps the
    underlying lab). Returns the request id."""
    _ensure_dirs()
    rid = str(uuid.uuid4())
    _write_atomic(REQUESTS_DIR / f"{rid}.json",
                  {"id": rid, "action": "teardown_mimic", "lab": {"slug": slug}})
    return rid


def submit_reconcile() -> str:
    """Ask the host-agent to re-converge all desired specs (used on boot)."""
    _ensure_dirs()
    rid = str(uuid.uuid4())
    _write_atomic(REQUESTS_DIR / f"{rid}.json", {"id": rid, "action": "reconcile"})
    return rid


def list_specs() -> list[dict]:
    """All desired specs the host-agent is reconciling (labs and mimic cells)."""
    if not SPECS_DIR.exists():
        return []
    out: list[dict] = []
    for p in sorted(SPECS_DIR.glob("*.json")):
        s = _read_json(p)
        if s:
            out.append(s)
    return out


def read_status(slug: str) -> dict | None:
    """Live per-lab status the host-agent writes (state/stage/percent/resources)."""
    return _read_json(STATUS_DIR / f"{slug}.json")


def read_result(request_id: str) -> dict | None:
    """Terminal outcome of a request, if the host-agent has finished it."""
    return _read_json(RESULTS_DIR / f"{request_id}.json")


def host_agent_seen() -> bool:
    """Heuristic liveness: the host-agent creates these dirs on boot."""
    return STATUS_DIR.exists() or SPECS_DIR.exists()
