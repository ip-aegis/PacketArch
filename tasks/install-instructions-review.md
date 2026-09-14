# PacketArch — App State & Install Instructions Review

**Date:** 2026-09-14
**Reviewed ref:** `origin/master` @ `1b275af` (tag `v1.19.2`)
**Test method:** clean Ubuntu 24.04.4 LTS VM (`pa-installtest`, 10.10.20.90, 8GB/4vCPU/58G)
on the Alpha hypervisor, built from the `noble` cloud image with cloud-init.
Instructions were executed **verbatim** as a copy-paste user would.

---

## 1. Install-path findings (empirically tested)

### 🔴 BLOCKER — README.md Quick Start clone line fails for every new user

`README.md:33` tells a first-time visitor:

```bash
git clone git@github.com:ip-aegis/PacketArch.git
```

This is an **SSH** clone of a **public** repo. On the clean VM:

```
Cloning into 'PacketArch'...
Host key verification failed.
fatal: Could not read from remote repository.
exit 128
```

The README is the first thing a GitHub visitor reads, and its very first
command fails. `DEPLOY.md` already does this correctly over HTTPS
("public repo, HTTPS — no SSH key needed") and clones fine (exit 0, lands on
`v1.19.2`). Fix: make README match DEPLOY.md.

### 🔴 BLOCKER — README/CLAUDE.md dev setup references a file that does not exist

`README.md:37` and `CLAUDE.md` (lines 30, 76, 90) instruct:

```bash
cd docker && docker-compose -f docker-compose.dev.yml up -d
```

`docker/docker-compose.dev.yml` **does not exist anywhere in the repo.**
Every compose file in `origin/master`:

- `docker-compose.yml` (production stack)
- `docker-compose.host-agent-dev.yml`
- `backend/app/static/agent/docker-compose.agent.yml`
- `scripts/local-sensor/docker-compose.agent.local.yml`
- `scripts/release-bundle/docker-compose.offline.yml`

The entire documented local-development workflow is therefore dead on arrival.

### 🟠 `scripts/server-init.sh` is not executable in git

`DEPLOY.md` offers the one-shot helper as `./scripts/server-init.sh`, but the
file is committed mode `100644`:

```
100755 scripts/packetarch-backup.sh
100755 scripts/packetarch-restore.sh
100644 scripts/server-init.sh      <-- the only non-executable script
100755 scripts/upgrade.sh
```

A fresh clone gets `Permission denied`. Fix: `git update-index --chmod=+x`.

### 🟠 DEPLOY.md references two GitHub workflows that do not exist

DEPLOY.md documents `deploy.yml` (SSH auto-deploy, with a secrets table) and
`build-agent.yml`. `origin/master` `.github/workflows/` contains only
`ci.yml` and `release.yml`. The secrets table is instructions for a
workflow that was never committed.

### 🟡 README documents the wrong admin-password env var

README's config table lists `FIRST_USER_PASSWORD` as the ".env" variable.
That is the **internal** setting name. `docker-compose.yml:55,138` maps
`FIRST_USER_PASSWORD: ${ADMIN_PASSWORD:-}`, so the variable an operator
actually sets in `.env` is `ADMIN_PASSWORD` (which is what DEPLOY.md and
`server-init.sh` correctly use). Setting `FIRST_USER_PASSWORD` in `.env` as
the README says has no effect.

### 🟡 README protocol table is badly out of date

README marks **OPC UA, DNP3 and IEC 104 as "Planned"**. All three are
Production per CLAUDE.md and shipped engines. The table also omits S7comm
variants, IEC 61850 (MMS/GOOSE/SV), C37.118, EMP and ATCS entirely — i.e. it
undersells the platform by 6+ production protocols.

### 🟡 Dev docs say pnpm; the build uses npm

README/CLAUDE.md prerequisites say "Node.js 18+ with pnpm" and `pnpm install`.
`frontend/Dockerfile` does `COPY package.json package-lock.json` + `npm ci`,
and `frontend/` carries `package-lock.json`. The repo root does carry
`pnpm-workspace.yaml` + `pnpm-lock.yaml`. Mixed package managers — the
container build (the path that matters) is npm.

### 🟡 `newgrp docker` in a copy-paste block

DEPLOY.md step 1 ends with `newgrp docker`, which spawns an interactive
subshell. Pasted as part of a block, everything after it runs in that
subshell / stalls. Not fatal (a fresh SSH session picks the group up
correctly — verified), but it breaks a single paste.

### 🟢 What worked, verbatim, on the clean VM

| Step | Result |
|------|--------|
| DEPLOY.md step 1 — Docker Engine + compose install | ✅ docker-ce 29.8.0, compose 5.5.1 |
| DEPLOY.md step 2 — HTTPS clone | ✅ exit 0, lands on `v1.19.2` |
| DEPLOY.md step 3 — `.env` heredoc | ✅ all 7 vars non-empty, `DOCKER_GID=988` as documented |
| DEPLOY.md step 4 — `docker compose up -d --build` | (see §2) |

### 🔴 The public "Latest release" is v1.18.2 — five releases behind

Anyone landing on the GitHub Releases page (the OVA / offline-bundle install
path) gets **v1.18.2, published 2026-07-14** — two months and five releases
stale. Everything since is still an unpublished **draft**:

| Tag | Public? |
|-----|---------|
| v1.19.2, v1.19.1, v1.19.0, v1.18.5, v1.18.3 | ❌ draft — invisible to the public |
| v1.18.2 | ✅ latest published (2026-07-14), 7 assets |

Assets on v1.18.2: `packetarch-1.18.2-appliance.ova`,
`packetarch-1.18.2-offline.tar.gz`, `packetarch-1.18.2-pcap-offline.tar.gz`,
plus LICENSE/NOTICE/release-notes/third-party.

Cutting a release drafts it by design (`release.yml`), so this is the known
"publish manually" step — but five drafts have queued up. Note `upgrade.sh`
is **not** affected: it resolves targets from **git tags**, not the Releases
API, so `./scripts/upgrade.sh` correctly finds v1.19.2. Only the
bundle/OVA download path is stale.

---

## 2. Fresh-install verification (clean Ubuntu 24.04 VM, DEPLOY.md path)

`docker compose up -d --build` completed **exit 0** from a cold cache
(no pre-pulled images). All six services came up:

```
packetarch-backend-1       Up (healthy)
packetarch-celery_worker-1 Up (healthy)
packetarch-frontend-1      Up
packetarch-host-agent      Up
packetarch-postgres-1      Up (healthy)
packetarch-redis-1         Up (healthy)
```

### First-run behaviour — matches the documented contract exactly

| Check | Expected (CLAUDE.md / DEPLOY.md) | Actual | |
|---|---|---|---|
| `GET https://<ip>/` | 200, setup wizard | 200 | ✅ |
| `GET http://<ip>/` | 301 → https | 301 → `https://10.10.20.90/` | ✅ |
| `/health` | healthy | `{"status":"healthy"}` | ✅ |
| `/api/v1/setup/status` | `setup_complete:false` | `false`, variant `full` | ✅ |
| `/api/v1/scenarios` pre-setup | 503 (setup gate) | 503 | ✅ |
| `/api/v1/about` | version | **1.19.2** | ✅ |
| `/agent/install.sh` | served | 200 | ✅ |
| Feature flags | ai/live/multi-sensor on, mimic off | exactly that | ✅ |
| Alembic | single head, migrations run on boot | `add_cyber_vision_centers (head)`, `RUN_MIGRATIONS=true — alembic at head` | ✅ |

### Setup wizard → live app

`POST /api/v1/setup/complete` returned `setup_complete:true` with auto-login
tokens. After that:

- `/api/v1/scenarios` went **503 → 403 unauth / 200 authenticated** — the gate
  lifts correctly.
- Fresh `POST /api/v1/auth/login` with the wizard-chosen credentials → **200**.
- `POST /api/v1/templates/create` (manufacturing / siemens_discrete_manufacturing)
  built a real scenario: **36 devices, 66 flows, 4 zones, 3 phases**.

So the *documented* install path produces a working platform. The defects in
§1 are documentation/packaging defects, not runtime ones.

### 🟠 `/api/docs` 404s on every documented install

Both README ("available at `/api/docs`") and DEPLOY.md's Access-URLs table
promise `https://<server>/api/docs`. On the fresh install it returns **404**.

Root cause — `backend/app/main.py:82-84`:

```python
_docs_url    = "/api/docs" if settings.debug else None
_redoc_url   = "/api/redoc" if settings.debug else None
_openapi_url = "/api/openapi.json" if settings.debug else None
```

Both DEPLOY.md step 3 and `server-init.sh` write `DEBUG=false`, so the docs
are disabled on every install done by the book. (`/docs` and `/openapi.json`
appear to return 200 through nginx, but that is the SPA catch-all serving
`index.html` — confirmed 404 against the backend directly.)

This is a deliberate hardening choice, so the fix is a **doc** fix: say the
API docs require `DEBUG=true`. Exposing an unauthenticated schema on a
production box should stay opt-in.

### 🟡 `build_commit` is `dev` on source installs

`/api/v1/about` reports `"build_commit":"dev"`. `version.py:get_build_commit()`
reads `BUILD_COMMIT` from the environment, but neither `docker-compose.yml`,
DEPLOY.md, nor `server-init.sh` passes it as a build arg. Every
git-clone-and-build install therefore self-reports as `dev` in the About
dialog and startup banner — so a support request can't identify the build.

---

## 3. Where the app is

### Healthy

- **Backend test suite: 1188 passed, 39 xfailed, 0 failures** (~2m41s, full run;
  measured on `d8e8a8c`, the pre-pull HEAD).
- **Lint is green on current HEAD.** CI's exact invocation
  (`ruff check . --select=E,F,W --ignore=E501`, run from `backend/`) →
  *All checks passed* on `1b275af`. (Note: plain `ruff check .` with default
  rules reports 575 findings — CI's narrower ruleset is the actual contract.)
- **Alembic: single head** (`add_cyber_vision_centers`), 43 migrations, and it
  applies cleanly on a fresh boot via `RUN_MIGRATIONS=true`.
- **0 open GitHub issues.**
- Feature flags resolve consistently end to end (config → features → `/about`).
- `tasks/lessons.md` is actively maintained (11 entries, most recent 2026-09-11).

### Scope snapshot (verified against the running container)

| Metric | Count |
|---|---|
| `backend/app` | ~205,800 LOC / 524 `.py` files |
| `frontend/src` | ~73,100 LOC / 319 `.ts(x)` files |
| Registered API routes | 296 across 34 groups |
| Protocol engines | 25 `ProtocolEngine` subclasses |
| Device templates | **348** across **24** vendor modules |
| Scenario templates | **37** across **8** verticals |
| Agent version | 4.1.3 |

### 🔴 The Release workflow does not gate on CI

Tags `v1.19.0`, `v1.19.1` and `v1.19.2` were all cut while master CI was
**red** — `Lint Backend / Ruff` was failing on each (an unused
`AsyncMock` import in `backend/tests/api/test_local_sensor.py`, since fixed in
`12918e0`). Backend and frontend *tests* passed throughout; only lint was red.

The lint failure itself is now resolved (confirmed green on `1b275af` after
pulling), but the *gating gap* remains: nothing stops the next tag from being
cut over a red build.

This is the same mechanism behind two already-recorded incidents
(`tasks/lessons.md:18` "CI was red for 4 days and nobody noticed" and
`lessons.md:226` the v1.19.0 Settings-Overview 422 that reached production).
Adding a CI-success condition to `release.yml` would close it.

### 🟠 The dev box was running 1.19.1 while origin was at 1.19.2

Resolved during this review — pulled to `1b275af`. Worth noting that
`/api/v1/about` could not have told you: it reports `build_commit: "dev"` and a
`build_date` of *now* rather than of the image build, so it offers no usable
build provenance (see the `BUILD_COMMIT` finding in §2).

### 🟡 Seven open PRs, one of them likely superseded

| # | Title | Age |
|---|---|---|
| 19 | Fix CV Org Hierarchy: name truncation, network rename, orphan cleanup | 3d |
| 18 | docs: lean CLAUDE.md map + reference docs split (DRAFT) | 5d |
| 17 | Close three of four remaining pin-ratchet gaps | 5d |
| 16 | Remove seven duplicate device templates | 5d |
| 15 | Force LF on checkout for files Docker executes | 5d |
| 14 | Pick instruments that can measure what their tag says | 5d |
| 8 | Agent EMP port fix (3001) + ATCSMon harness | **2 months** |

**PR #19 needs a supersession check before anyone rebases it:** it puts
+466/-37 into `backend/app/services/cv_provisioning_service.py` for CV
org-hierarchy name handling, and merged PR #23 (v1.19.2) has since changed the
same file for the same concern, with its tests in `test_name_normalize.py`
instead of #19's new `test_cv_oh_level_names.py`.

**PR #18 rewrites CLAUDE.md**, which is the file carrying the count drift fixed
in §4 — worth resolving together to avoid a conflict.

### 🟡 Mimic is enabled on the dev box against a ship-dark default

`mimic_enabled` defaults to `False` (`config.py:101`) and the fresh VM install
correctly reports `mimic_enabled: false`. The dev box's `.env` sets it `true`.
That's intentional for development, but it means `/mimic` and
`/api/v1/mimic/*` are live locally and **503/redirect on any real install** —
anything validated locally against Mimic is validating a surface customers
don't have yet.

### 🟡 `tasks/todo.md` is a completed-work archive, not a roadmap

50 of 52 items checked; the two open ones are stale July follow-ups
(`todo.md:161,163`). There's no forward plan in it.

---

## 4. Fixes applied in this review

Documentation + one file mode. No application code changed.

| File | Change |
|------|--------|
| `README.md` | Quick Start rewritten: HTTPS clone, working `.env` heredoc, `docker compose up -d --build`, pointer to DEPLOY.md. Dev Setup now uses `docker compose up -d postgres redis` with the `packetarch_dev` password that matches the backend's default `DATABASE_URL`. Protocol table refreshed to 13 production protocols. `/api/docs` documented as `DEBUG`-only. `FIRST_USER_PASSWORD` row replaced with `ADMIN_PASSWORD` + `DOCKER_GID`. Dual package-manager split documented. |
| `DEPLOY.md` | `server-init.sh` invocation fixed (`curl \| bash` and `bash scripts/...`). Phantom `deploy.yml` / `build-agent.yml` section replaced with the two workflows that exist + a note that releases are drafts. `/api/docs` marked `DEBUG`-only. `newgrp docker` subshell papercut explained. |
| `CLAUDE.md` | Three dead `docker-compose.dev.yml` references replaced with the real commands. Counts corrected: 8 verticals / 37 templates (was "6 verticals"), 348 templates / 24 vendor modules (was 332/20), fingerprint-validator skill 348 (was 295), Mimic substrate 348 (was 332). |
| `backend/app/ai_services/skills/packetarch-fingerprint-validator/SKILL.md` | Template count 295 → 348. This body is fed to the model at runtime, so the stale count was more than cosmetic. |
| `scripts/server-init.sh` | `git update-index --chmod=+x` — now `100755`, so DEPLOY.md's invocation works from a fresh clone. |

Counts were verified against the running container, not taken on trust:
`len(DEVICE_TEMPLATES) == 348`, 24 vendor modules, `VERTICAL_TEMPLATES` = 8
verticals / 37 templates.

**The protocol table was verified too, and CLAUDE.md was wrong.** Checking
`PROTOCOL_DEFAULT_PORTS` (`protocol_engines/protocols.py:153`) against the
engines turned up two errors that would have been copied straight into the
public README:

- **EtherNet/IP was listed as "44818 (TCP), 2222 (UDP)".** In this codebase
  2222 is **PCCC over TCP** (legacy SLC-5/05, PLC-5E — `pccc/types.py:25`),
  not EtherNet/IP implicit I/O. Corrected in both files.
- **PROFINET was listed as "Layer 2" only.** It is Layer 2 (EtherType 0x8892)
  for RT *and* UDP 34964 for DCE/RPC AR setup — both of which appear in the
  PCAP this review generated. Corrected in both files.

C37.118 (4712 TCP / 4713 UDP), ATCS (4802 TCP + 30000+ UDP) and EMP (3001,
installation-configured) were each confirmed against their engines.

**A `DEBUG=true` caveat was added rather than a bare pointer.** `settings.debug`
also drives `logging.DEBUG`, SQLAlchemy `echo` on both engines
(`core/database.py:18,40`) and raw exception text in API responses
(`main.py:157`) — so "flip DEBUG to read the docs" would have been a footgun.

### Re-verified after the fixes

The README Quick Start block was extracted programmatically and run
**verbatim** on the VM after wiping every prior install and volume:

```
GET /                         -> 200
setup_complete: False | variant: full
version: 1.19.2
GET /api/v1/scenarios (gated) -> 503
GET /agent/install.sh         -> 200
.env: 7/7 vars set, perms 600
all six containers healthy
```

`scripts/server-init.sh` was also run end to end on the VM (`INIT_EXIT=0`),
producing a healthy six-container v1.19.2 install that the unprivileged user
can drive with `docker compose` afterward — confirming the missing exec bit was
its only defect.

---

## 5. Paths reviewed but NOT executed

Called out so the evidence isn't overstated:

- **`scripts/release-bundle/install.sh` (offline/air-gapped bundle)** — read
  only. It looks well built (idempotent, root check, `--upgrade` /
  `--force-env` guards, refuses to run outside an extracted release dir).
  **This is the most discoverable install route for an outside user** — the
  GitHub Releases page — and it is the one path here that was not exercised.
  Combined with the finding that the public "Latest" is **v1.18.2**, an outside
  installer today gets a two-month-old bundle via an untested script.
- **`scripts/upgrade.sh`** — read only. Confirmed it resolves targets from
  **git tags** (`upgrade.sh:93`), not the Releases API, so the draft-release
  backlog does not break it. The rollback path was not exercised.
- **OVA appliance** (`scripts/ova/`) — not touched.
- **Traffic agent install** (`/agent/install.sh`) — confirmed *served* (200) but
  not installed onto a second host.

---

## 6. Recommended next steps

1. **Publish the release drafts** (or publish v1.19.2 at minimum) so the
   public Releases page isn't two months stale.
2. **Gate `release.yml` on CI success** — three tags were cut over red lint.
3. **Test the offline bundle install** on a clean VM; it's the most
   discoverable path and the least verified.
4. **Pass `BUILD_COMMIT`/`BUILD_DATE` as build args** in `docker-compose.yml`
   so `/about` reports real provenance instead of `dev`.
5. **Triage PR #19** against merged v1.19.2 before rebasing; land PR #18
   together with this review's CLAUDE.md edits.
6. Decide whether the dual lockfile (pnpm for CI, npm for the image) is
   intentional; it's a latent source of "works in CI, differs in the image".

---

## Test environment

VM `pa-installtest` on Alpha (10.10.20.62), reachable at **10.10.20.90**,
currently holding a **fresh un-completed setup wizard** from the corrected
README instructions. 8GB/4vCPU/58G, Ubuntu 24.04.4, Docker 29.8.0.
Tear down with:

```bash
ssh rocsmith@10.10.20.62 'sudo virsh destroy pa-installtest && \
  sudo virsh undefine pa-installtest --remove-all-storage'
```

---

## 7. Handoff round (same session) — making the doc actually handable

Scope chosen: **internet-connected box** (clone + build). Release backlog:
**publish all**.

### The fourth install doc nobody was looking at

`backend/app/api/routes/downloads.py` served
**`PacketArch-Installation-Guide-v1.10.1.pdf`** — a June PDF, nine versions
behind — as "PacketArch Installation Guide" in **Settings → Downloads**. That
is the doc an operator actually receives, and text extraction confirmed it
carried the **same three defects** as the README: the `git@github.com` SSH
clone, `docker-compose.dev.yml`, and a bare `/api/docs` URL.

Two independent reasons it could never keep up:

- `scripts/build_install_guide_pdf.py` hardcoded `VERSION = "1.10.1"`,
  `COMMIT = "70f97ae"`, `DATE = "June 25, 2026"`.
- `downloads.py` pinned the exact filename, so even a regenerated PDF wouldn't
  be picked up without a code edit.

**Fixed:** the generator now derives the version from `app_version` and the
commit from `git`; `downloads.py` resolves the guide by glob
(`PacketArch-Installation-Guide-v*.pdf`, newest wins). Regenerated at v1.19.2
and verified live: the catalog lists the new file, it downloads (200, 25,956
bytes), and the stale name 404s. The two stale committed copies were removed.

### Drift guard (so it stays fixed)

Nothing in `build-release.sh` or `release.yml` regenerates the guide, so
auto-deriving the version only helps if a human remembers to run it.
`scripts/check_install_guide_version.py` now fails CI when the committed
guide's version doesn't match `app_version`. Verified against all three
failure modes: stale version, two guides committed, no guide at all — plus
the real v1.10.1 case, which it catches.

### Releases published

All five drafts published (oldest first so ordering is right). Public
**Latest is now v1.19.2** with all 7 assets, including
`packetarch-1.19.2-offline.tar.gz` (890 MB),
`packetarch-1.19.2-pcap-offline.tar.gz` (759 MB) and
`packetarch-1.19.2-appliance.ova` (931 MB). Previously the public saw
v1.18.2 from 2026-07-14.

### Final end-to-end proof

The README was fetched **from raw.githubusercontent.com** (not the working
tree), its Quick Start block extracted programmatically, and run on a VM
wiped with `docker system prune -af --volumes` — a genuine cold build:

```
git@github.com occurrences:        0
docker-compose.dev.yml occurrences: 0
PUBLISHED_README_EXIT=0
GET /                -> 200
setup wizard shown:  True
version:             1.19.2
all six containers healthy
```

### Commits

- `a0d65d4` Install instructions a new user can actually follow
- `8bd5bc3` Keep the install guide from going stale again

Both pushed to `origin/master`.

### Still open (not done, deliberately)

- **`release.yml` does not gate on CI** — the finding in §3 stands. Three tags
  were cut over red lint. Not changed here; it's a release-policy decision.
- **The offline bundle path is still unexecuted.** Now that v1.19.2 is
  published, `packetarch-1.19.2-offline.tar.gz` is downloadable and could be
  tested in the VM against `scripts/release-bundle/install.sh`.
- **The OVA path** is untouched.
