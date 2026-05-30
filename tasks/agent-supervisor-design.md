# Phase 2 — External Agent Supervisor (rearchitecture design, 2026-05-30)

Goal: make remote-agent updates reliable, observable, rollback-safe, and
premium. Kills the "container recreates itself from inside" flaw (audit
`tasks/agent-selfupdate-audit.md`). Mirrors the proven `packetarch-host-agent`
pattern (persistent privileged sibling + file-queue + reconcile loop).

## Core principle
The traffic agent NEVER modifies its own container. A persistent sibling
**agent-supervisor** owns the agent container's lifecycle (recreate, rollback).
The supervisor survives the agent's recreate (separate container,
`restart: unless-stopped`). The backend confirms success closed-loop.

## Topology — install.sh generates a 2-service compose + shared volume
```yaml
services:
  agent:                              # traffic agent — NO docker.sock anymore
    image: packetarch-agent:latest
    container_name: packetarch-agent
    restart: unless-stopped
    network_mode: host
    cap_add: [NET_ADMIN, NET_RAW]
    env_file: [.env]
    volumes:
      - agent_state:/state            # shared file-queue only
  supervisor:                         # same image, supervisor role
    image: packetarch-agent:latest
    container_name: packetarch-agent-supervisor
    restart: unless-stopped
    command: ["python","-m","app.supervisor"]
    environment: [AGENT_INSTALL_DIR=/opt/packetarch-agent]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock     # ONLY the supervisor
      - /opt/packetarch-agent:/opt/packetarch-agent   # compose dir (same host path)
      - agent_state:/state
volumes: { agent_state: {} }
```
Decisions baked in: (D1) reuse the agent image with an alt `command` — one image,
no extra build; (D2) docker.sock moves OFF the agent onto the supervisor
(security: agent can no longer touch the host daemon).

## Update flow (file-queue contract mirrors host-agent state.py)
Shared `/state`: `update-request.json` (agent→supervisor), `update-status.json`
(supervisor→agent, relayed to backend), `agent-online.json` (agent writes
{version} on each successful WS connect — the supervisor's health signal).

1. Backend sends `UPDATE_AGENT {target_version, image_url, checksum}` (existing WS).
2. Agent writes `update-request.json` (adds server_url + token for the download),
   relays `UPDATE_STATUS: queued`. **Agent does NOT touch docker.**
3. Supervisor reconcile loop:
   - download tarball (from the PacketArch server, token-auth — air-gap safe) →
     checksum verify → `docker load` (repoints `packetarch-agent:latest`).
   - compare loaded image id vs the running `agent` container's image id
     (supervisor inspects by container_name — reliable, it is NOT host-networked-
     blind). Same → `complete (already current)`.
   - `docker compose -f <compose> up -d --no-deps --force-recreate agent`
     (recreates ONLY the agent; supervisor keeps running).
   - watch: wait for `agent-online.json` to report `target_version` within a
     deadline (and `docker inspect` healthy). Success → `complete`.
   - failure/timeout → ROLLBACK: re-tag the retained old image id as
     `:latest`, recreate agent, write `failed` + error. (Old image retained
     until success — rollback is reachable because the supervisor is alive.)
4. Completion relay survives the recreate: the NEW agent reads
   `update-status.json` on startup and relays the terminal status. AND the
   backend independently confirms via the reconnect heartbeat (below).

## Backend — closed-loop status (folds in Phase 0)
`backend/app/services/agent_manager.py` + `agents.py`:
- **Reaper** background task: any non-terminal update status older than a
  deadline (~120-180s) → `failed`/`timeout`.
- **Completion on every heartbeat** (not gated on version-*delta*): pending
  update + reported version/SHA == target → `complete`.
- `clear_update_status` on `delete_agent` + token regen; list endpoint filters
  by live agent ids (kills the ghost entries).
- Agent reports `image_sha` in HEARTBEAT for robust matching.
- (Optional now) persist terminal outcome to `TrafficAgent`
  (last_update_status/error/at) so it survives backend restart.

## Agent code
- New `app/supervisor.py` (reconcile loop; uses docker SDK + bundled compose).
- New `app/agent_state.py` (atomic file-queue read/write; mirrors host-agent
  `state.py`).
- `app/main.py` `_handle_update_agent` → write request + relay queued; on
  startup relay any pending terminal `update-status.json`; write
  `agent-online.json {version}` on CONNECTED.
- Legacy in-container self-recreate: kept only as a guarded fallback when no
  supervisor/`/state` is present (back-compat for old single-service installs).

## install.sh + serving
- Generate the 2-service compose + shared volume; agent has no docker.sock.
- **Fix the baked-serving footgun**: bind-mount `install.sh` (and
  `docker-compose.agent.yml`) read-only into the backend so host edits go live
  without a backend rebuild. (Keeps the single-source-installer invariant.)

## Local-sensor agents (host-agent already supervises them)
- Make `local_lab_id` agents NON-self-updating: backend suppresses
  `UPDATE_AGENT`; the host-agent refreshes the image on reconcile (re-load
  latest + recreate). No supervisor sidecar needed there — the host-agent IS the
  supervisor. Prevents the self-update-vs-reconcile fight.

## CML
- Add SSH break-glass creds (`users:`/`ssh_authorized_keys:`) to
  `_build_cloud_init` so a stranded VM is recoverable without redeploy.
- cloud-init installs the new 2-service compose via the updated install.sh.

## Rollout (requires reinstall to get the supervisor)
1. Backend Phase 0 (reaper + clear-on-delete + SHA completion) — ship first,
   helps even old agents.
2. Fix install.sh serving (bind mount).
3. supervisor.py + agent_state.py + agent main.py + install.sh 2-service compose;
   bump agent MAJOR (protocol/role change).
4. Local-lab non-self-update + host-agent image refresh.
5. CML ssh creds.
6. Tests; rebuild backend (serve new install.sh) + agent image; redeploy the 2
   CML agents onto the supervisor topology; E2E self-update validation
   (trigger update → supervisor swaps → backend confirms complete; then force a
   failure → supervisor rolls back).

## Out of scope (Phase 3): image signing, resumable/delta downloads,
full DB persistence of update history. (The Watchtower sidecar in
docker-compose.agent.yml WAS removed — see below.)

---

## IMPLEMENTED + VALIDATED (2026-05-30, agent v2.0.x)
Shipped all of Phases 0-2:
- Backend closed-loop: reaper (`expire_stale_updates`, 300s deadline) +
  `reconcile_update_on_heartbeat` (confirm on ANY heartbeat reporting target
  version/SHA, not a version delta) + `clear_update_status` on delete/token-
  regen + list endpoint filtered by live agents. Reaper started in lifespan.
- Agent: `app/supervisor.py` (reconcile loop) + `app/agent_state.py`
  (file-queue) + `_handle_update_agent` supervised hand-off + on_connect
  agent-online signal + status relay + `/state/agent.log` (GET_LOGS works with
  NO docker.sock on the agent). docker.sock moved to the supervisor.
- install.sh + docker-compose.agent.yml: 2-service compose (agent +
  supervisor + agent_state volume); Watchtower removed.
- Local-lab agents: self-update blocked (ValidationError); they refresh via the
  host-agent reconcile (proven: Local-Sensor reached 2.0.2 on reconcile).
- docker-compose.yml: agent static dir bind-mounted so install.sh edits go live.

E2E PROVEN on the two real CML-lab agents: triggered UPDATE_AGENT → supervisor
went queued → swapping → complete; agents went 2.0.1 → 2.0.2; backend confirmed
complete; update-statuses had exactly the 2 live agents (no ghosts). The earlier
reaper run also proved a stuck update fails at the deadline (no eternal
"restarting").

### TWO GOTCHAS hit + fixed during validation
1. **Single-file bind mounts pin the original inode** — an atomic editor replace
   (new inode) keeps serving stale content. Fixed by binding the DIRECTORY
   `./backend/app/static/agent` (not `:ro` — the agent_dist volume must create
   its dist/ mountpoint under it), with the agent_dist volume overlaying dist/.
2. **compose `command:` is APPENDED to the image ENTRYPOINT** (`python -m
   app.main`), so the supervisor service was silently starting a SECOND agent.
   Fixed by overriding `entrypoint: ["python","-m","app.supervisor"]`.

### Deferred (low value now): CML cloud-init SSH break-glass creds — the
supervisor's rollback + the reaper largely obviate the "stranded, need SSH"
recovery that motivated it. Revisit only if a non-rollback-able failure mode
emerges.
