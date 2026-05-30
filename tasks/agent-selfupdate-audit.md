# Agent self-update architecture audit (2026-05-30)

5-agent fan-out audit of the entire remote-agent self-update mechanism.
Triggered because, even after the 1.48.0 (apk) and 1.50.0 (install-dir mount +
fallback env) fixes, a real CML-lab self-update still reaches "restarting" then
silently no-ops — the agent stays online on the OLD version forever.

## Why it is failing RIGHT NOW (convergent root cause)

1. **install.sh is served BAKED into the backend image, not live.**
   `backend/Dockerfile` does `COPY . .`; the compose only mounts the
   `agent_dist` *volume* at `static/agent/dist/` (the built tarballs).
   `install.sh` lives one dir up in `static/agent/` → served from the frozen
   baked copy. So my v1.50 install.sh mount fix **never reached any agent** —
   it needs `docker compose up -d --build backend` to go live. The image
   tarball updates immediately (it's in dist/, on the volume); install.sh does
   not. (Confirmed live: `curl /agent/install.sh` has 0 occurrences of the fix.)
   → every redeployed agent STILL has no install-dir mount.

2. → `find_agent_install_path()` returns None *inside the container* (the host
   install dir isn't mounted in) → the agent takes the fragile **docker-run
   fallback** instead of the clean `docker compose down && up -d`.

3. **The docker-run fallback is broken several ways** (`main.py:836-868`):
   - Hard-codes `--name packetarch-agent`; the real container name can differ
     (CML host-networked, local-sensor per-lab names) → `docker stop/rm` no-op,
     old container keeps running, a duplicate may start.
   - Drops the install-dir mount + `AGENT_INSTALL_PATH` → even a *successful*
     fallback recreate can never heal back onto the compose path (stuck in
     fallback forever).
   - `network_mode: host` makes `HOSTNAME` the *host* name → self-inspect 404s
     (`running_image_id` stays None).
   - (Env passthrough was the only part fixed in 1.50; insufficient alone.)

4. **No closed-loop confirmation.** Backend infers success only when a heartbeat
   reports a version *different* from the cached one (`agent_manager.py:397` →
   `verify_update_on_reconnect`). A stranded agent (never reconnects) OR one that
   never dropped its WS (update failed but old container survived) never trips
   that gate → status rots at "restarting" forever. **No TTL/reaper exists.**
   `delete_agent` never clears the status dict → phantom entries for deleted
   agents (the 756dab28/09955b81 ghosts we saw).

5. **Self-recreation-from-inside is architecturally unsound.** The container
   launches a detached sibling whose job is to kill+replace the launcher. The
   gap between `down` and `up` has no surviving owner; rollback lives in the
   already-dead agent so it's unreachable for the failures that matter.

## Bug catalog (prioritized, with file:line)

### Critical
- **C1** Self-container identification broken under `network_mode: host`
  (`main.py:619-628`): `HOSTNAME` = host name, not container id → 404. Fix: read
  `/proc/self/cgroup` or `/proc/self/mountinfo`, or set `-e AGENT_CONTAINER_NAME`
  in compose and look it up.
- **C2** Fallback hard-codes `--name packetarch-agent` (`main.py:849-868`) →
  stop/rm no-op on differently-named containers; duplicate host-networked
  container; old keeps heartbeating old version. **This is the exact live
  symptom.**
- **C3** No terminal complete/failed for the recreate path (`main.py:761-769`);
  the only "complete" ever sent is the "already up to date" short-circuit. Status
  structurally stuck at "restarting".
- **C4 (backend)** Completion gated on version-*delta* heartbeat
  (`agent_manager.py:397,703`): misses "came back unchanged" and stranded cases.
  No reaper. Fix: on EVERY heartbeat, if a non-terminal update exists, compare
  reported version/SHA to target → complete; else past-deadline → failed.

### High
- Backend update-status is an in-memory dict (`agent_manager.py:79`); wiped on
  restart, never cleared on `delete_agent`/token-regen, no TTL → ghosts + leak.
- `build_status.json` wedges ALL future builds permanently if backend is killed
  mid-build (`status:"building"` with no `started_at` staleness check).
- Non-atomic tarball write in `build_image_sync` (gzip in place) → agents
  self-updating during a rebuild get partial/checksum-mismatched downloads.
  Fix: write temp + `os.replace()`, checksum/version after.
- Fallback recreate strips the install-dir mount + `AGENT_INSTALL_PATH` → agent
  degrades to fallback-forever (`main.py:856-867`).
- Local-sensor agents CAN self-update and would fight the host-agent reconcile
  loop (`hostops.py` compose has no mount, per-lab name). Should be non-self-
  updatable; host-agent should refresh image on reconcile instead.

### Medium / Low
- 3 divergent compose generators (`install.sh` local tag, `docker-compose.agent.yml`
  ghcr + a **Watchtower sidecar = a second, conflicting update mechanism**,
  `hostops.py`). Drift already present; `test_agent_installer.py` only pins the
  docker.sock mount.
- CML cloud-init sets NO ssh creds (`_build_cloud_init`) → a stranded CML agent
  is unrecoverable except by undeploy+redeploy.
- Racy concurrent-build guard (check-then-act on a file) + boot autobuild can
  race a manual build → interleaved gzip writes.
- `--remove-orphans` on the compose path could nuke a co-located CV sensor.
- Dead `subprocess.TimeoutExpired` handler in `_handle_update_agent`.

### Security
- `docker.sock` mounted into every agent = host root on host-networked agents
  (only there for self-update).
- Image authenticity is checksum-only (same channel) — no signing.
- Token re-plumbed through the updater container's env.

## Improvement options / recommended target architecture

**Phase 0 — backend-only, immediate symptom relief (no agent redeploy):**
1. Deadline + background reaper: stuck non-terminal status → `failed`/`timeout`
   after ~120-180s.
2. `delete_agent` (+ token regen) clears update status; list endpoint filters by
   live agent ids.
3. Agent reports `image_sha` in HEARTBEAT; backend confirms completion by SHA
   match within a deadline, NOT version-delta.

**Phase 1 — make the current mechanism actually work:**
4. Deploy the install.sh mount fix for real (rebuild backend so it's served) →
   compose path works for new installs. Consider serving install.sh from a mount
   so host edits go live (kills the footgun).
5. Robust self-container id (C1/C2/C3); fallback re-adds the mount + env so it
   self-heals; never `rm` the old image until backend confirms COMPLETE.
6. Atomic tarball write; build-status staleness guard.

**Phase 2 — externalize the lifecycle owner (the real fix):**
7. The repo ALREADY has the right pattern: `packetarch-host-agent` (persistent,
   privileged, `restart:unless-stopped`, reconcile loop, reboot-survive). Adopt
   an "agent supervisor" of that shape so the agent NEVER recreates itself; the
   supervisor performs the swap from outside, watches health, rolls back, and the
   backend confirms via deadline+SHA. Move `docker.sock` off the agent.
   Local-lab agents: route updates through the existing host-agent reconcile
   (no-op the in-agent path).

**Phase 3 — durability/security:** persist update status to DB; image signing;
resumable/delta downloads; unify install-time artifact source; drop the
Watchtower divergence.

## Current live state (this session)
- Local commits (UNPUSHED): e555133 (1.50.0 real fix), 1.51.0 verify bump; plus
  the user's 7f196bb (OVA) also unpushed. dd75894 (1.48.0) IS pushed.
- Served agent image: 1.51.0. Two CML agents online but stuck at 1.50.0
  (functional, just didn't self-update). Local-sensor agent healthy.
- The 1.50.0 install.sh fix is correct but was never SERVED (baked) — so it's
  unproven in the field; the audit shows it's necessary-but-insufficient anyway.
