# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""File-queue contract between the PacketArch backend and the host-agent.

The host-agent is the ONLY component that touches the host (veth creation,
/etc/docker/daemon.json, per-lab sensor+agent containers). The unprivileged
backend never holds privilege; it communicates over a shared volume instead of
a network port (no port to bind, no auth surface, survives container restart —
the same status-file convention `services/system_upgrade.py` already uses).

Directory layout (all under STATE_ROOT, the mounted `host_agent_state` volume):

    requests/<request_id>.json   backend writes  -> a build/teardown/reconcile op
    results/<request_id>.json    host-agent writes -> terminal outcome of a request
    specs/<slug>.json            host-agent writes -> DESIRED lab state (reconcile source)
    status/<slug>.json           host-agent writes -> LIVE lab status (progress + state)
    work/<slug>/...              host-agent writes -> generated composes + .env per lab

Desired state lives in `specs/`. The reconcile loop makes host reality match the
specs, which is what makes labs survive reboots. `requests/` is just the trigger
channel; losing a request is harmless because reconcile re-derives from specs.

Spec schema (specs/<slug>.json and the `lab` field of a build request):
    {
      "slug": "ab12cd34",                 # short, drives all resource names
      "name": "Bakery Sensor Lab",
      "gen_if": "pa-gen-ab12cd34",        # agent injects here
      "mon_if": "pa-mon-ab12cd34",        # sensor macvlan parent (capture)
      "mtu": 1500,
      "registry": "10.10.20.115:443",     # CV Center registry (insecure-trust)
      "sensor_compose": "<verbatim CV YAML>",
      "sensor_container": "ccv-sensor-ab12cd34",
      "agent_container": "packetarch-agent-ab12cd34",
      "agent_token": "...",
      "agent_name": "Local-...",
      "server_url": "https://localhost",  # agent phone-home target
      "insecure": true
    }

Mimic cell spec (kind="mimic" — device personas attached to an EXISTING lab's
SPAN; no sensor, no CV token). Stored in the same specs/ dir, own slug space:
    {
      "kind": "mimic",
      "slug": "mm-ab12cd34",              # mimic cell id (distinct from lab slug)
      "name": "Mimic Cell",
      "lab_slug": "07d51972",             # existing lab whose SPAN to attach to
      "gen_if": "pa-gen-07d51972",        # that lab's inject side (hub-bridged)
      "devices": [                        # one entry per persona / poller
        {"container": "pa-mm-...-plc", "mac": "00:00:54:..", "ip": "10.50.0.10/24",
         "ttl": 64, "veth_br": "...", "veth_ns": "...", "spec": {<PersonaSpec>}}
      ]
    }

Request schema (requests/<request_id>.json):
    { "id": "<uuid>", "action": <action>, "lab": {<spec>} }
    - build:          persist lab spec then provision (kind=lab)
    - teardown:       deprovision + delete spec/status/work for lab["slug"]
    - emulate:        persist mimic spec then provision personas (kind=mimic)
    - teardown_mimic: stop personas + hub-bridge, delete the mimic spec
    - reconcile:      re-converge ALL specs (routes by kind; lab may be omitted)

Status schema (status/<slug>.json):
    {
      "slug": "...", "name": "...",
      "state": "pending|provisioning|running|degraded|stopped|error",
      "stage": "veth|registry|compose|image|sensor|agent|done|teardown",
      "percent": 0-100, "message": "...", "updated_at": "<iso>",
      "resources": {"veth": bool, "sensor_running": bool, "agent_running": bool}
    }
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STATE_ROOT = Path(os.environ.get("HOST_AGENT_STATE", "/state/local-labs"))

REQUESTS_DIR = STATE_ROOT / "requests"
RESULTS_DIR = STATE_ROOT / "results"
SPECS_DIR = STATE_ROOT / "specs"
STATUS_DIR = STATE_ROOT / "status"
WORK_DIR = STATE_ROOT / "work"

_ALL_DIRS = (REQUESTS_DIR, RESULTS_DIR, SPECS_DIR, STATUS_DIR, WORK_DIR)


def ensure_dirs() -> None:
    for d in _ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically (tmp + rename) so a reader never sees a partial file."""
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


# --- requests ---------------------------------------------------------------

def list_requests() -> list[Path]:
    if not REQUESTS_DIR.exists():
        return []
    return sorted(
        (p for p in REQUESTS_DIR.glob("*.json")),
        key=lambda p: p.stat().st_mtime,
    )


def read_request(path: Path) -> dict | None:
    return _read_json(path)


def consume_request(path: Path) -> None:
    """Remove a processed request file (best-effort)."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def write_result(request_id: str, ok: bool, message: str, extra: dict | None = None) -> None:
    data = {"id": request_id, "ok": ok, "message": message, "finished_at": now_iso()}
    if extra:
        data.update(extra)
    _write_atomic(RESULTS_DIR / f"{request_id}.json", data)


# --- specs (desired state) --------------------------------------------------

def write_spec(spec: dict) -> None:
    _write_atomic(SPECS_DIR / f"{spec['slug']}.json", spec)


def read_spec(slug: str) -> dict | None:
    return _read_json(SPECS_DIR / f"{slug}.json")


def list_specs() -> list[dict]:
    if not SPECS_DIR.exists():
        return []
    out = []
    for p in sorted(SPECS_DIR.glob("*.json")):
        s = _read_json(p)
        if s:
            out.append(s)
    return out


def delete_spec(slug: str) -> None:
    try:
        (SPECS_DIR / f"{slug}.json").unlink()
    except FileNotFoundError:
        pass


# --- status (live) ----------------------------------------------------------

def write_status(
    slug: str,
    *,
    name: str = "",
    state: str,
    stage: str = "",
    percent: int = 0,
    message: str = "",
    resources: dict | None = None,
) -> None:
    _write_atomic(
        STATUS_DIR / f"{slug}.json",
        {
            "slug": slug,
            "name": name,
            "state": state,
            "stage": stage,
            "percent": percent,
            "message": message,
            "updated_at": now_iso(),
            "resources": resources or {},
        },
    )


def read_status(slug: str) -> dict | None:
    return _read_json(STATUS_DIR / f"{slug}.json")


def delete_status(slug: str) -> None:
    try:
        (STATUS_DIR / f"{slug}.json").unlink()
    except FileNotFoundError:
        pass


def work_dir(slug: str) -> Path:
    d = WORK_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d
