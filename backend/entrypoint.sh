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
  TRACKED=""
  for i in $(seq 1 30); do
    if TRACKED="$(python - <<'PY'
from sqlalchemy import inspect
from app.core.database import sync_engine
print("yes" if "alembic_version" in inspect(sync_engine).get_table_names() else "no")
PY
)"; then
      break
    fi
    echo "[entrypoint] waiting for database... ($i/30)"
    if [ "$i" -eq 30 ]; then
      echo "[entrypoint] database never became reachable" >&2
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
