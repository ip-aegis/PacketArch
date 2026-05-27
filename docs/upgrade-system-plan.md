# PacketArch Upgrade System — Phased Plan

Status as of 2026-05-27. Tracks how remote/lab installs get updated.

## Decision: labs track tagged RELEASES, not `master`

`master` is the dev=prod bleeding edge on the build box. Lab installs track
`vX.Y.Z` git tags. Tagging triggers `release.yml` (offline bundles). This gives
controlled rollout, a meaningful "update available" signal, and a changelog.

Loop: **fix → push `master` → tag a release → labs run the upgrade.**

## Phase 0 — manual (works today)
```bash
cd ~/packetarch && git fetch --tags && git checkout <tag> && docker compose up -d --build
```

## Phase 1 — `scripts/upgrade.sh`  ✅ SHIPPED (commit bc67622)
Safe primitive, called by everything else:
backup (`packetarch-backup.sh`) → checkout target tag → rebuild → migrate
(`alembic upgrade head`, run BEFORE app boot so `create_all` can't race
new-table migrations) → poll backend health → **auto-rollback code + DB**
(`packetarch-restore.sh --yes`) on failure. Flags: `--check`, `--list`,
`--to <tag>`, `--no-backup`, `--force`. Stamps alembic head on first run for
installs that were never alembic-tracked.

## Phase 1.5 — fix the create_all/alembic split (PREREQUISITE for clean Phase 2)
The app builds tables via SQLAlchemy `create_all` on boot (`database.py`) AND
ships alembic migrations that `create_all` can't apply to existing tables
(e.g. column adds). This is fragile.

**Fix:** run `alembic upgrade head` in the backend container entrypoint and
drop `create_all`. Stamp head once on fresh installs. After this, every path
(fresh install, `upgrade.sh`, the Phase 2 button) is correct by construction
and `upgrade.sh` can drop its stamp/ordering workaround.

## Phase 2 — one-button UI upgrade
Wraps Phase 1. Mirrors the existing agent-update flow
(`POST /agents/{id}/update` + `GET /agents/{id}/update-status`).

- **Self-restart problem:** the backend can't rebuild/restart itself while
  holding the HTTP request. Solution: the backend (which already drives Docker
  via the mounted socket — see `agents.py` `docker.from_env()`) launches a
  **detached one-shot updater container** that runs `upgrade.sh` and writes
  progress to Redis/DB. Backend restarting under it is fine; the UI reconnects
  to the new backend and reads final status.
- **Endpoints (admin-only, audited):**
  - `GET /api/v1/system/version` → current, latest-available, `update_available`
    (extend `/api/v1/about`, which already carries version from `core/version.py`).
  - `POST /api/v1/system/upgrade` → launch updater, return job id.
  - `GET /api/v1/system/upgrade-status` → `fetching → backing-up → building →
    migrating → restarting → healthy | rolled-back | failed`.
- **Frontend:** Settings → System panel: version card (current vs available +
  changelog) + Update button + progress view. Reuse agent update-status polling.
- **Air-gapped labs:** can't reach GitHub. Offer "upload offline bundle"
  (existing `release.yml` / `build-release.sh` tarball) as the alternate source.
- **Security:** runs host code via the Docker socket — admin-only, rate-limited,
  audit-logged (reuse the `ai_call_audit` pattern for a system-action log).

## Phase 3 — polish (optional)
- Release-channel UX: changelog from GitHub Releases API; stable vs edge channels.
- Fleet view: central box sees/triggers upgrades across labs (bigger lift).
- Per-install fix branches + PRs (scoped deploy token) instead of patch-back,
  once many labs feed fixes upstream.

## Open items / risks
- Phase 1.5 should land before Phase 2 ships.
- Need a first release tag (`git tag v1.0.0 && git push origin v1.0.0`) — until
  then `upgrade.sh` exits with "no release tags found".
- Brief downtime during `compose up` recreate — acceptable for a lab tool; no
  blue/green needed.
