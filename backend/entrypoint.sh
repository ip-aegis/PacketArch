#!/usr/bin/env bash
#
# Backend container entrypoint. When RUN_MIGRATIONS=true (set on the backend
# service, NOT on celery_worker), reconcile alembic state before the app boots,
# then exec the container CMD (uvicorn). celery_worker shares this image but
# leaves RUN_MIGRATIONS unset, so exactly one process touches migrations.
#
# Schema model for this project (important):
#   - create_all (in the app's init_db) is the schema BASELINE and runs every
#     boot. The alembic chain is INCREMENTAL — it patches a create_all-built
#     schema and does NOT rebuild from scratch, so we never `upgrade` from base.
#   - This entrypoint only applies FORWARD deltas (column/data migrations that
#     create_all can't do) to already-tracked DBs, and stamps untracked DBs so
#     future deltas apply.
#
# Tracking logic:
#   - alembic_version present  -> `alembic upgrade head` (apply pending deltas;
#                                  no-op when already at head).
#   - alembic_version absent    -> `alembic stamp head`. ASSUMPTION: the DB's
#                                  schema matches THIS image's head — true for a
#                                  fresh install and for a legacy create_all DB
#                                  booting the same version that built it.
#                                  Cross-version transitions must go through
#                                  scripts/upgrade.sh, which stamps the OLD head
#                                  before checkout so intermediate deltas apply.
#
set -euo pipefail

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "[entrypoint] RUN_MIGRATIONS=true — reconciling alembic state"

  # Wait for the DB to accept connections and report whether it is tracked.
  # depends_on: service_healthy covers a cold start, but an `up -d --build`
  # recreate can still leave a brief window where the first connect is refused.
  #
  # Two failure modes look identical through a bare retry loop, and only one of
  # them resolves by waiting:
  #   - "connection refused" / "starting up" -> postgres is still coming up. Retry.
  #   - "password authentication failed"     -> the role's password does not match
  #     POSTGRES_PASSWORD. Retrying 30x cannot fix that; it just buries the cause
  #     under 30 SQLAlchemy tracebacks while the operator watches the backend
  #     crashloop. That is a real incident: a surviving packetarch_postgres_data
  #     volume keeps its ORIGINAL password (postgres only applies
  #     POSTGRES_PASSWORD when it initialises an EMPTY data dir), so a
  #     regenerated .env silently desynchronises the two. pg_isready still
  #     reports the server healthy, because it never authenticates.
  # So: classify the error, fail fast on the one that cannot self-heal.
  #
  TRACKED=""
  DB_ERR=""
  for i in $(seq 1 30); do
    if TRACKED="$(python - 2>/tmp/dbprobe.err <<'PY'
from sqlalchemy import inspect
from app.core.database import sync_engine
print("yes" if "alembic_version" in inspect(sync_engine).get_table_names() else "no")
PY
)"; then
      break
    fi
    DB_ERR="$(cat /tmp/dbprobe.err 2>/dev/null || true)"

    if printf '%s' "$DB_ERR" | grep -qi "password authentication failed"; then
      cat >&2 <<'MSG'

[entrypoint] ============================================================
[entrypoint] DATABASE PASSWORD MISMATCH — this will not fix itself.
[entrypoint] ============================================================
[entrypoint]
[entrypoint] Postgres rejected the credentials in POSTGRES_PASSWORD:
[entrypoint]   FATAL: password authentication failed for user "packetarch"
[entrypoint]
[entrypoint] Almost always this means the database volume is OLDER than the
[entrypoint] .env file. Postgres only applies POSTGRES_PASSWORD when it
[entrypoint] initialises an EMPTY data directory, so a volume that survived a
[entrypoint] `docker compose down` keeps whatever password it was built with,
[entrypoint] and a regenerated .env no longer matches it.
[entrypoint]
[entrypoint] Note that `docker compose ps` is misleading here: postgres reports
[entrypoint] healthy because pg_isready never authenticates.
[entrypoint]
[entrypoint] To realign the password with .env (keeps all data):
[entrypoint]
[entrypoint]     ./scripts/fix-db-password.sh
[entrypoint]
[entrypoint] Or, to discard the database and start clean (DELETES ALL DATA):
[entrypoint]
[entrypoint]     docker compose down -v && docker compose up -d
[entrypoint]
[entrypoint] If that is not it, collect everything in one redacted file and
[entrypoint] send that instead of guessing:
[entrypoint]
[entrypoint]     ./scripts/collect-diagnostics.sh
[entrypoint]
[entrypoint] ============================================================

MSG
      exit 1
    fi

    echo "[entrypoint] waiting for database... ($i/30)"
    if [ "$i" -eq 30 ]; then
      echo "[entrypoint] database never became reachable after 60s" >&2
      echo "[entrypoint] last error from the connection attempt:" >&2
      printf '%s\n' "$DB_ERR" | tail -5 >&2
      echo "[entrypoint]" >&2
      echo "[entrypoint] 'postgres' not resolving is the usual cause on a VPN'd host." >&2
      echo "[entrypoint] Collect the evidence in one redacted file:" >&2
      echo "[entrypoint]     ./scripts/collect-diagnostics.sh" >&2
      exit 1
    fi
    sleep 2
  done

  if [ "$TRACKED" = "yes" ]; then
    echo "[entrypoint] alembic-tracked DB — applying any pending deltas (upgrade head)"
    alembic upgrade head
  else
    echo "[entrypoint] untracked DB — stamping head (create_all owns the baseline schema)"
    alembic stamp head
  fi
  echo "[entrypoint] alembic at head"
fi

exec "$@"
