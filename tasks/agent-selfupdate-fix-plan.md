# Agent self-update fix — handoff plan (2026-05-30)

## The bug (root-caused, high confidence)
Two CML-lab agents (`CV-PacketArch-Agent` 09955b81, `PacketAgent-CML` 756dab28)
died during a self-update: stuck `offline / restarting`, `last_seen` frozen at
the update-init moment, version still 1.45.1.

Cause: the agent self-updater (`docker/packetarch-agent/app/main.py`,
`_handle_update_agent`) spawns a detached **`alpine:latest`** container that runs
`apk add --no-cache docker-cli docker-cli-compose` — i.e. it fetches the docker
CLI **from the internet at update time** — and does so AFTER
`docker compose down --remove-orphans` has already removed the agent. On a
connectivity-constrained host (CML-lab VM behind the lab connector) the `apk`
step fails/hangs, so `up -d` never runs and the agent is stranded with no
container left for `restart: unless-stopped` to revive.

NOTE: the agent CODE did not change between the last known-good update and now
(1.45.1→1.46.0 was version-string-only). What changed is that this is the first
time the updater ran inside a constrained CML VM. The on-host local agent never
self-updates (host-agent reconcile recreates it), which is why it was unaffected.

## The fix (the intended change)
Run the updater container from **`packetarch-agent:latest` itself** instead of
alpine. The agent image already bundles `docker` + the compose plugin (see
`docker/packetarch-agent/Dockerfile` lines ~19-28) and is guaranteed present
locally (the agent is running it; the new image was just `docker load`ed). So the
updater needs NO `apk add` and NO image pull → zero internet dependency.
Apply to BOTH the compose path and the docker-run fallback; use an explicit
`entrypoint=["/bin/sh","-c"]` since the agent image's ENTRYPOINT is
`python -m app.main`.

## CURRENT REPO STATE (messy — verify before trusting)
- **`f65e869` is committed AND PUSHED to origin/master** with subject "Fix agent
  self-update stranding..." but it ONLY changed `version.py` (1.45.1→1.47.0 +
  history note). THE ACTUAL CODE FIX IS NOT IN THAT COMMIT. The pushed history is
  misleading; the served 1.47.0 image was built from buggy code.
- `docker/packetarch-agent/app/main.py` has UNCOMMITTED edits (this session's
  real attempt). The compose path looks converted, but a grep still shows
  1 `alpine` + 1 `apk add` remaining — UNVERIFIED whether comment or live code.
  DO NOT trust it; re-read and re-grep from scratch.
- A 1.47.0 agent image was already built + is being served at
  `/agent/image.tar.gz` — but it is BUILT FROM THE BUGGY CODE. Must rebuild after
  the real fix lands.
- The two dead CML agents are NOT recovered. Their CML nodes are still BOOTED
  (VMs alive): lab e7286f72 node 43c6d351 (CV-PacketArch-Agent),
  lab a696b621 node cfc7eeef (PacketAgent-CML). The local lab agent
  (Local-Sensor-68fca480) is healthy.

## PLAN (do in order, verify each step before the next)

### Phase 0 — confirm clean tooling
Run a multi-line echo + a `docker exec ... cat` and confirm output is complete.
If output truncates/empties, STOP and restart again.

### Phase 1 — land the REAL code fix
1. Re-read `main.py` `_handle_update_agent` (~lines 770-850). Re-grep
   `alpine` / `apk add` / `images.pull` — establish ground truth.
2. Ensure BOTH `containers.run(...)` calls use `"packetarch-agent:latest"` with
   `entrypoint=["/bin/sh","-c"]` and a command that does NOT `apk add` and does
   NOT pull. Remove the alpine pull/fallback-pull. Drop any stale "alpine"
   comments.
3. Verify: `grep -c alpine` and `grep -c 'apk add'` BOTH == 0;
   `python3 -c "import ast; ast.parse(open(...).read())"` OK.
4. Decide on the bogus `f65e869`: simplest honest path is a NEW commit that
   lands the real main.py fix (history already shows 1.47.0; either keep 1.47.0
   and amend intent in the message, or bump to 1.48.0 so the version line cleanly
   tracks "the build that actually contains the fix"). Recommend bump to 1.48.0
   to avoid two different 1.47.0 binaries. Commit + push.

### Phase 2 — rebuild the served agent image FROM fixed code
1. Login admin (pw from /home/rocsmith/PacketArch/.env ADMIN_PASSWORD via
   POST https://10.10.20.231/api/v1/auth/login).
2. POST /api/v1/agents/build-image ; poll /api/v1/agents/build-status to
   complete; confirm /api/v1/agents/image-status standard_version == the new ver.

### Phase 3 — redeploy the two dead CML agents (so they run FIXED code)
The dead agents can't receive the fix (they're dead) — they must be reinstalled.
Two options:
  (a) CML undeploy + redeploy via the API (POST /api/v1/cml/undeploy then
      /api/v1/cml/deploy) — clean but creates new nodes/agent rows.
  (b) SSH into the CML agent VMs and re-run the install one-liner / `docker
      compose up -d` to bring the agent back on the new image.
GET CML connectivity is confirmed (10.10.20.230 reachable, cml/status connected).
CONFIRM WITH USER which path (touches their CML labs).

### Phase 4 — TEST the self-update mechanism (the actual goal)
1. With at least one agent now running the FIXED agent code, bump the agent
   version once more (or rebuild), then trigger POST /api/v1/agents/{id}/update.
2. Watch /api/v1/agents/update-statuses → should go downloading→loading→
   restarting→(gone) then the agent reconnects ONLINE at the new version within
   ~60-90s. THAT is success: a clean self-update with no stranding.
3. Also verify a constrained-path proxy if possible (the CML agents are the real
   test since they're the ones that failed).

## Key facts / endpoints
- Server 10.10.20.231 ; admin pw in /home/rocsmith/PacketArch/.env ADMIN_PASSWORD
- Agents: GET /api/v1/agents (?page_size max 100), /api/v1/agents/update-statuses,
  POST /api/v1/agents/{id}/update, POST /api/v1/agents/build-image,
  GET /api/v1/agents/build-status, /api/v1/agents/image-status
- CML: /api/v1/cml/status, /labs, /labs/{id}/nodes, /deploy, /undeploy
- Agent image lifecycle: backend build_image_sync (agents.py ~211) builds
  `packetarch-agent:latest`, saves gzip tarball to the `agent_dist` volume,
  serves at /agent/image.tar.gz. install.sh + self-update consume THAT tarball
  (NOT ghcr). Dockerfile bundles docker + compose plugin.
- Memory: see remote_agents_feature.md, agent_image_staleness_fix.md,
  agent_installer_single_source.md, cml_environment.md.

## TOOLING WARNING
This session's bash/Read intermittently returned empty / truncated multi-line
output and cancelled parallel batches, which caused a false-fix commit. In the
new session: prefer ONE command per call, redirect to /tmp + Read, and ALWAYS
re-grep to confirm an Edit actually landed before committing or building.
