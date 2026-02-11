# PacketArch Packaging, Versioning & IP Protection Plan

> **Status:** Not started — saved for future reference
> **Created:** 2026-02-10
> **Scope:** 6 new files, 13 modified files, ~1-2 days of work

## Context

PacketArch is a production-grade OT traffic simulation platform distributed as Docker containers. Despite 59 agent version bumps and 40+ Alembic migrations, the app itself has no unified version (backend/frontend stuck at placeholder 0.1.0), no git tags, no CHANGELOG, no license file, and no auto-migration on deploy. This plan introduces a proper release and IP protection framework.

---

## Phase 1: Source-Available License (BSL 1.1)

**What:** Add a Business Source License 1.1 file at the repo root. Same license HashiCorp uses for Terraform. Lets customers read the source code (important for OT security trust), but prevents anyone from reselling PacketArch or offering it as a service. After 4 years each release auto-converts to Apache 2.0, giving customers long-term assurance. No code changes, no runtime enforcement — just a legal file.

**Why BSL 1.1 over alternatives:**
- SSPL (MongoDB) is too aggressive — requires anyone offering as a service to open-source their entire infrastructure stack. Rejected by OSI.
- FSL (Sentry, newer) lacks legal precedent.
- PolyForm licenses lack the auto-conversion feature that reassures customers.

**License parameters:**
- Licensor: IP Aegis
- Licensed Work: PacketArch
- Additional Use Grant: Internal business use allowed. No reselling, no offering as managed service.
- Change Date: 4 years from each release
- Change License: Apache 2.0

**Files:**

| Action | File |
|--------|------|
| Create BSL 1.1 license text | `LICENSE` (new) |
| Set license field to `BUSL-1.1` | `package.json` |
| Add `license = "BUSL-1.1"` | `backend/pyproject.toml` |
| Add `"license": "BUSL-1.1"` | `frontend/package.json` |

---

## Phase 2: Unified Version System

**What:** Create a single `VERSION` file at the repo root containing `1.0.0`. Backend reads it at startup, frontend bakes it in at build time, the `/health` endpoint returns it, and the sidebar displays it. Today neither the backend nor frontend has a real version.

**Agent stays independent:** The agent keeps its own version (currently 1.22.0 in `docker/packetarch-agent/app/version.py`) since protocol engine changes don't warrant a full app release. The relationship is documented: "PacketArch 1.0.0 ships with Agent 1.22.0."

### 2a. Version source of truth

| Action | File |
|--------|------|
| Create file containing `1.0.0` | `VERSION` (new) |

### 2b. Backend reads VERSION

| Action | File | Detail |
|--------|------|--------|
| Add `_read_version()` function | `backend/app/core/config.py` | Checks `Path("/app/VERSION")` (Docker) then `Path(__file__).parents[3] / "VERSION"` (dev), falls back to `0.0.0-dev` |
| Change `app_version` default | `backend/app/core/config.py` | `app_version: str = "0.1.0"` → `app_version: str = _read_version()` |
| Dynamic version export | `backend/app/__init__.py` | `__version__ = "0.1.0"` → `from app.core.config import settings; __version__ = settings.app_version` |
| Update metadata | `backend/pyproject.toml` | `version = "0.1.0"` → `version = "1.0.0"` |

### 2c. Backend Dockerfile gets VERSION via build arg

| Action | File | Detail |
|--------|------|--------|
| Add `ARG APP_VERSION` + `RUN echo` | `backend/Dockerfile` | `ARG APP_VERSION=0.0.0-dev` then `RUN echo "${APP_VERSION}" > /app/VERSION` after `COPY . .` |
| Add OCI labels | `backend/Dockerfile` | `org.opencontainers.image.version`, `.licenses=BUSL-1.1`, `.vendor=IP Aegis` |
| Pass build arg | `docker-compose.yml` | `build: { context: ./backend, args: { APP_VERSION: ${APP_VERSION:-1.0.0} } }` |

### 2d. Frontend reads VERSION at build time

| Action | File | Detail |
|--------|------|--------|
| Inject version define | `frontend/vite.config.ts` | `import fs from 'fs'`, read `../VERSION`, add `define: { __APP_VERSION__: JSON.stringify(version) }` |
| Export version constant | `frontend/src/version.ts` (new) | Exports `APP_VERSION` from `__APP_VERSION__` define, with dev fallback |
| Add `ARG APP_VERSION` | `frontend/Dockerfile` | Set `ENV VITE_APP_VERSION=${APP_VERSION}` for Docker builds |
| Update metadata | `frontend/package.json` | `"version": "0.1.0"` → `"version": "1.0.0"` |

### 2e. Display version in UI

| Action | File | Detail |
|--------|------|--------|
| Show version in sidebar | `frontend/src/components/layout/AppLayout.tsx` (line 260) | Change `Backend Connected` text to `v{APP_VERSION}`, import from `@/version` |

### 2f. Include version in health endpoint

| Action | File | Detail |
|--------|------|--------|
| Add version field | `backend/app/api/routes/health.py` | Add `"version": settings.app_version` to health check response |

---

## Phase 3: CHANGELOG & Git Tags

**What:** A `CHANGELOG.md` following the Keep a Changelog standard, and a small shell script that validates everything and creates an annotated git tag. No heavy tooling like semantic-release — too much ceremony for a 1-2 person team. Today there are zero git tags and no release history.

### 3a. Create CHANGELOG

| Action | File |
|--------|------|
| Create with initial 1.0.0 entry | `CHANGELOG.md` (new) |

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Initial entry summarizes all current capabilities (6 protocol engines, 295 templates, agent v1.22.0, etc.).

### 3b. Create release script

| Action | File |
|--------|------|
| Create tag helper | `scripts/release.sh` (new) |

Script behavior:
1. Read version from `VERSION` file
2. Check tag `v{version}` doesn't already exist
3. Verify `CHANGELOG.md` has a `[{version}]` entry
4. Check no uncommitted changes
5. Create annotated tag: `git tag -a v{version} -m "Release v{version}"`
6. Print push command: `git push origin v{version}`

### 3c. CI version validation

| Action | File | Detail |
|--------|------|--------|
| Add `version-check` job | `.github/workflows/ci.yml` | Validate VERSION is valid semver; on tag pushes, verify CHANGELOG has matching entry |

### 3d. GitHub Release workflow

| Action | File | Detail |
|--------|------|--------|
| Create release workflow | `.github/workflows/release.yml` (new) | Triggers on `v*` tag push, extracts changelog section, creates GitHub Release |

---

## Phase 4: Deploy Reliability

### 4a. Auto-migrate on startup

**What:** A backend entrypoint script that runs `alembic upgrade head` before starting uvicorn. Today, DB migrations are a manual step that's easy to forget after pushing code changes.

| Action | File | Detail |
|--------|------|--------|
| Create entrypoint | `backend/entrypoint.sh` (new) | Prints version, runs `alembic upgrade head`, then `exec "$@"` |
| Switch to ENTRYPOINT pattern | `backend/Dockerfile` | `ENTRYPOINT ["/entrypoint.sh"]` + `CMD ["uvicorn", ...]` |

Note: Celery worker shares the same image but runs a different command. `alembic upgrade head` is idempotent — second container sees DB is at head, returns instantly.

### 4b. Pre-migration database backup

**What:** Before running migrations, take a `pg_dump` snapshot so the database can be recovered if a migration goes wrong.

| Action | File | Detail |
|--------|------|--------|
| Add pg_dump step to entrypoint | `backend/entrypoint.sh` | If `DEBUG=false`, run `pg_dump` to `/app/data/backups/pre-migrate-{timestamp}.sql`. Best-effort (non-blocking on failure). Keep last 5 backups. |
| Install `postgresql-client` | `backend/Dockerfile` | Add to `apt-get install` line alongside existing `curl` |
| Add backup volume | `docker-compose.yml` | `db_backups:/app/data/backups` volume for backend service |

### 4c. Reduce deploy downtime (60s → 5s)

**What:** Change the deploy workflow from "tear everything down, rebuild, bring back up" to rolling restarts.

| Action | File | Detail |
|--------|------|--------|
| Replace down/up with rolling restart | `.github/workflows/deploy.yml` | 1) `docker compose build` (no downtime during build), 2) `docker compose up -d --no-deps backend`, 3) wait for health check, 4) `docker compose up -d --no-deps frontend` |

### 4d. Pin agent dependencies

**What:** Lock agent `requirements.txt` to exact versions to prevent supply-chain drift on rebuild.

| Action | File | Detail |
|--------|------|--------|
| Pin exact versions | `docker/packetarch-agent/requirements.txt` | Get exact versions from `pip freeze` in a working container. E.g. `scapy==2.6.1` instead of `scapy>=2.5.0` |

---

## All Files Summary

### New Files (6)

| File | Purpose |
|------|---------|
| `VERSION` | Single version source of truth (`1.0.0`) |
| `LICENSE` | BSL 1.1 license text |
| `CHANGELOG.md` | Release history (Keep a Changelog format) |
| `scripts/release.sh` | Git tag creation helper |
| `backend/entrypoint.sh` | Auto-migrate + pre-deploy DB backup |
| `frontend/src/version.ts` | Frontend version constant export |

### Modified Files (13)

| File | Change |
|------|--------|
| `package.json` | License field → `BUSL-1.1` |
| `backend/pyproject.toml` | Version → `1.0.0`, license → `BUSL-1.1` |
| `backend/app/__init__.py` | Dynamic version from config |
| `backend/app/core/config.py` | `_read_version()` reads VERSION file |
| `backend/app/api/routes/health.py` | Add version to response |
| `backend/Dockerfile` | Build arg, entrypoint, postgresql-client, OCI labels |
| `frontend/package.json` | Version → `1.0.0`, license → `BUSL-1.1` |
| `frontend/vite.config.ts` | Inject `__APP_VERSION__` define |
| `frontend/Dockerfile` | Build arg, OCI labels |
| `frontend/src/components/layout/AppLayout.tsx` | Show version in sidebar |
| `docker-compose.yml` | Build args for backend/frontend, backup volume |
| `.github/workflows/ci.yml` | Version validation job |
| `.github/workflows/deploy.yml` | Rolling restart, version passing |

### New Workflow (1)

| File | Purpose |
|------|---------|
| `.github/workflows/release.yml` | Create GitHub Release on tag push |

### Intentionally Unchanged

| File | Reason |
|------|--------|
| `docker/packetarch-agent/app/version.py` | Agent versions independently (1.22.0) |
| `backend/app/core/database.py` | `init_db()` kept for test suite compatibility |

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Entrypoint migration fails, blocks startup | Medium | This is *desired* — running against a wrong schema is worse. Pre-migration pg_dump backup allows manual recovery. |
| Celery worker also runs migrations | Low | `alembic upgrade head` is idempotent. Second container sees DB at head, returns in <1s. |
| Rolling restart: brief 502s from nginx | Low | ~5s window. Frontend already handles API errors. Much better than 60s full outage. |
| VERSION file missing in dev | Low | `_read_version()` falls back to `0.0.0-dev`. |
| BSL 1.1 deters open-source contributors | Low | PacketArch isn't seeking OSS contributors. Source-available is the right tradeoff for a commercial OT product. |
| Pinning agent deps too tight | Low | Bump pins when security patches arrive. Loose pins risk surprise breakage. |

## Rewards

| Reward | Impact |
|--------|--------|
| Legal IP protection | BSL 1.1 prevents unauthorized commercial use without runtime enforcement complexity |
| Users know what they're running | Version in sidebar, health endpoint, and Docker labels |
| Traceable releases | Git tags + CHANGELOG = answer "what changed?" for any release |
| No more forgotten migrations | Auto-migrate on startup eliminates the most common deploy failure |
| Recoverable deploys | Pre-migration pg_dump means DB can always be rolled back |
| Less downtime | Rolling restarts cut deploy downtime from ~60s to ~5s |
| Reproducible agent builds | Pinned deps prevent "it worked yesterday" surprises |
| GitHub Releases | Tagged releases with changelog notes — professional distribution for customers |

## What This Plan Does NOT Include

- No license key system (decided against)
- No in-app EULA (decided against)
- No zero-downtime blue-green deploys (overkill for single-server)
- No monorepo version locking between app and agent (different cadences)
- No auto-version-bump from commit messages (too much ceremony for small team)
- No offline/air-gapped installation improvements
- No Let's Encrypt integration

---

## Verification Checklist

1. **License**: `cat LICENSE` shows BSL 1.1 text
2. **Version plumbing**: `curl localhost:8001/health` returns `"version": "1.0.0"`
3. **Frontend version**: UI sidebar shows `v1.0.0` under "System Online"
4. **Docker build**: `docker compose build` passes with build args
5. **Auto-migration**: `docker compose up backend` logs show "Running database migrations..." then "Migrations complete."
6. **Backup**: `/app/data/backups/` contains `pre-migrate-*.sql` after restart
7. **Release script**: `./scripts/release.sh` creates `v1.0.0` annotated git tag
8. **CI**: Push branch → `version-check` job passes
9. **GitHub Release**: Push tag → release created with changelog body
