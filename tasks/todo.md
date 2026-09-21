# DB password mismatch: fail loudly, and stop creating it

## Problem (from a real remote install, 2026-09-18)

`POSTGRES_PASSWORD` is only honoured when Postgres initialises an EMPTY data
directory. If `packetarch_postgres_data` survives and `.env` is regenerated,
the volume keeps the old password. Reproduced exactly: `pg_isready` still
reports "accepting connections", and a client on the docker network gets
`FATAL: password authentication failed for user "packetarch"`.

What the operator saw on the affected host: **4 of 6 containers green**.

| Container | Reported | Reality |
|-----------|----------|---------|
| postgres | healthy | `pg_isready` never authenticates |
| celery_worker | healthy 4h | healthcheck is `celery inspect ping` — Redis only. It could not reach the DB either. |
| backend | "Up About a minute (unhealthy)" | crashlooping, **restartCount=220** |
| frontend | `Created` | blocked on `backend: service_healthy` |

So the only component that checks the DB is the only one complaining, and it
complains as "unhealthy" rather than "wrong password". The entrypoint retried
30x at 2s and dumped a full SQLAlchemy traceback each cycle — an auth failure
can never resolve by retrying, so that is 60s of noise hiding a one-line cause.

## Plan

- [x] 1. `backend/entrypoint.sh`: classify the failure. Auth failure => fail
      FAST with a precise diagnosis + the exact remedy. Connection refused =>
      keep retrying (that one does resolve). No repeated tracebacks.
- [x] 2. `scripts/fix-db-password.sh` (new): realign the role's password with
      `.env` in one command, so the remedy is not a manual secret copy-paste.
- [x] 3. `docker-compose.yml`: celery_worker healthcheck must check the DB it
      depends on, not just Redis — it must not report healthy while broken.
- [x] 4. Installer preflight (`server-init.sh`, `release-bundle/install.sh`):
      refuse to write a fresh POSTGRES_PASSWORD when the data volume already
      exists. Covers `--force-env` too, whose warning does not mention that the
      failure presents as green healthchecks.
- [x] 5. DEPLOY.md troubleshooting entry.
- [x] 6. Version bump to v1.20.2 + release notes + install-guide PDF.
- [x] 7. Verify: reproduce the break in a throwaway stack, prove each change.

## Non-goals

- Changing how Postgres handles POSTGRES_PASSWORD (upstream behaviour).
- Auto-repairing the password on boot. Silently rewriting a DB credential is
  the wrong default; tell the operator and hand them one command.

## Review

### What shipped (v1.20.2)

| File | Change |
|------|--------|
| `backend/entrypoint.sh` | Classifies the DB probe failure. Auth failure => exits in ~1s with a diagnosis + remedy; anything else retries as before. The 30x-retry path now also prints the last real error instead of nothing. |
| `scripts/fix-db-password.sh` | **New.** Realigns the role password with `.env` over the trusted unix socket, verifies it over the network, restarts the affected services. `--check` reports only. Layout-agnostic (repo `scripts/` and the bundle's flat root). |
| `docker-compose.yml` | celery_worker healthcheck now also connects to Postgres. |
| `scripts/server-init.sh` | Warns when a data volume outlives the `.env` it just generated; TTY-guarded offer to repair. |
| `scripts/release-bundle/install.sh` | Same preflight, plus a reminder before the health wait. |
| `scripts/build-release.sh` | Ships `fix-db-password.sh` in the offline bundle. |
| `DEPLOY.md` | "Backend crashlooping on password authentication failed" + troubleshooting row. |

### Verification

- **Mechanism reproduced** before writing anything: volume built with one
  password, container recreated with another => `pg_isready` still green,
  network client gets the exact `FATAL: password authentication failed`
  from the customer log, old password still works.
- **entrypoint fail-fast:** wrong password => full diagnosis in **1 second**
  (was 60s and 30 tracebacks). Regression-checked the other path: with
  postgres stopped it kept retrying the full 40s until killed, so a
  slow-starting DB is still waited for.
- **fix-db-password.sh:** end-to-end against a throwaway stack — detects,
  repairs, verifies, restarts, and is idempotent on a second run. Also
  proved SQL-quote escaping with a password containing `'` and `"`.
- **celery healthcheck:** the DB clause genuinely executes (`DB clause
  reached and connected`), and exits **1** against a bad password where it
  previously exited 0.
- Backend suite: see below. Stack redeployed; all services healthy.

### Note on the earlier mistake

My first entrypoint test was invalid — `SECRET_KEY` was too short, so the
probe died on a Pydantic error before reaching Postgres. Caught it because the
output named the wrong error, not because the test failed. Worth remembering
that a test which fails for the wrong reason still looks like a pass when you
are only checking the exit path.

## 2026-09-21 — Corporate-host install hardening
- [ ] Execute tasks/corporate-host-install-plan.md (6 tasks, priority order; check in with Rocky first). Origin: David G. install thread 09-04→09-18.
