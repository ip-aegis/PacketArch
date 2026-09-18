# Docker build-network egress: make the operator workaround supported

## Problem

On a fresh source install, `docker compose up -d --build` dies on the first
network-touching `RUN` (pip/poetry/apt/npm/apk) when the host's *bridged
container* egress is broken — firewalld/nftables FORWARD drop (RHEL family),
MTU mismatch behind a VPN, unreachable DNS, or a docker bridge subnet that
collides with the site network. Operators reach for `build.network: host`,
which forces `build: ./backend` into long form (`context:` + `network:`).

That workaround is an edit to a TRACKED file, and it breaks the self-upgrade:
`scripts/upgrade.sh:118` fails preflight on a dirty tree, and `--force`
`git stash push`es the edit with **no pop anywhere in the script**, then runs
`$DC build` (line 191) without it — so the upgrade fails on exactly the host
that needed it, and the edit is gone.

## Plan

- [x] 1. `docker-compose.yml`: `network: ${DOCKER_BUILD_NETWORK:-default}` on
      ALL FIVE build stanzas (backend, celery_worker, frontend, host-agent,
      updater). Long form where needed. No behavior change when unset.
- [x] 2. `scripts/server-init.sh`: commented `DOCKER_BUILD_NETWORK=` in the
      generated `.env`.
- [x] 3. Preflight egress doctor: test the real BuildKit sandbox before the
      build, and on failure name the likely cause + the daemon.json fix.
- [x] 4. SDK builds honor the same knob — `client.images.build(network_mode=)`
      in `api/routes/agents.py` (agent image) and `services/system_upgrade.py`
      (updater). These bypass compose entirely via the mounted socket.
- [x] 5. `scripts/upgrade.sh`: restore the autostash (independent bug — today
      `--force` silently discards ANY local tracked edit).
- [x] 6. DEPLOY.md troubleshooting entry.
- [x] 7. Verify: `docker compose config`, `bash -n`, python syntax, real build.

## Non-goals

- `docker-compose.offline.yml` — all `image:`, no builds, unaffected.
- Runtime `network_mode: host` on backend/frontend. That one is harmful
  (kills embedded DNS for `postgres`/`redis`, nginx can't reach the
  `expose`-only backend, and `ports:` is ignored so the deliberate
  127.0.0.1 binds on Postgres/unauthenticated Redis go to every interface).

## Review

### What shipped

| File | Change |
|------|--------|
| `docker-compose.yml` | `network: ${DOCKER_BUILD_NETWORK:-default}` on all 5 build stanzas (backend, celery_worker, frontend, host-agent, updater) + `DOCKER_BUILD_NETWORK` passed into the backend's env |
| `backend/app/core/config.py` | `docker_build_network: str = ""` setting |
| `backend/app/api/routes/agents.py` | agent image build honours it (`network_mode=`) — this build is reached from `startup.py:384` on every boot as well as the UI button |
| `backend/app/services/system_upgrade.py` | updater build-on-demand honours it |
| `scripts/check-docker-egress.sh` | **new** — preflight doctor, distro-agnostic probes, firewall remedy adapts to firewalld / ufw / raw nftables |
| `scripts/server-init.sh` | runs the doctor before the build; offers the stopgap; commented knob in the generated `.env` |
| `scripts/upgrade.sh` | autostash is now **restored** (was created and never popped) |
| `scripts/build-release.sh` | its 3 raw `docker build` calls honour the knob too — they bypass compose AND the SDK |
| `DEPLOY.md` | "When the build can't reach the network" + `.env` table row + troubleshooting row |

### Verification

- `docker compose config` resolves to `network: default` unset, `network: host`
  when set; all 5 stanzas (`--profile updater` to see the 5th).
- Doctor: passes clean on this box; every probe proven to DISCRIMINATE, not
  just pass — `docker build --network none` fails it, `--dns 203.0.113.1`
  fails the DNS probe, `--network none` fails the TCP probe.
- docker-py guards `if network_mode:`, so `"" -> None` is safely omitted.
- Backend suite: **1255 passed**, 40 deselected, 2 xfailed.
- upgrade.sh stash logic tested in a throwaway repo: clean pop reapplies the
  edit; conflicting pop resets to the tag's tree, keeps the stash, warns.

### Three bugs found while building this

1. **`upgrade.sh` autostash was never restored.** `git stash push` at the
   preflight with no `pop` anywhere. Any local tracked-file edit was silently
   discarded, and the rebuild that followed then failed on exactly the host
   that needed the edit. Fixed, and the stash is now resolved by message
   rather than by `stash@{0}` position.
2. **Restoring it introduced a rollback hazard**, caught in review and fixed:
   a successful pop leaves the tree dirty, and if the operator's edit merged
   into a file the new tag also changed, `git checkout $CURRENT_REF` in
   `rollback()` is REFUSED — so a failed upgrade would have silently stayed on
   the broken version. Proven in a throwaway repo. `rollback()` now re-stashes
   before reverting, then reapplies.
3. **The new preflight prompt would have broken `curl ... | bash` installs.**
   Under `curl | bash` stdin IS the script, so `read` hits EOF and returns
   non-zero — and under `set -e` that aborts the install. Verified: a bare
   `read` at EOF exits 1. Now TTY-guarded with a `|| true`, and a
   non-interactive run prints the manual stopgap instead. Both paths
   re-tested under a `set -e` parent with stdin closed.

### Note

`tasks/todo.md` previously held the lab-management UI consolidation plan; it
was overwritten by this plan per the standard workflow and is recoverable from
git history.
