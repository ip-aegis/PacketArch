#!/usr/bin/env bash
#
# Realign the Postgres role password with POSTGRES_PASSWORD in .env.
#
# Why this is ever needed: postgres applies POSTGRES_PASSWORD only when it
# initialises an EMPTY data directory. A `packetarch_postgres_data` volume that
# survived a `docker compose down` therefore keeps the password it was BUILT
# with, and a regenerated .env silently stops matching it. The backend then
# crashloops on
#
#     FATAL: password authentication failed for user "packetarch"
#
# while `docker compose ps` still shows postgres healthy, because pg_isready
# never authenticates.
#
# This rewrites the ROLE's password to match .env. It keeps all data. The
# alternative — `docker compose down -v` — deletes the database.
#
# Usage:
#   ./scripts/fix-db-password.sh            # apply
#   ./scripts/fix-db-password.sh --check    # report only, change nothing
#
set -euo pipefail

# Works from both layouts this script ships in: the repo (scripts/<here>, so the
# compose file is one level up) and the offline bundle, which stages helper
# scripts FLAT beside docker-compose.yml. Find the compose file rather than
# assuming either shape.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR=""
for cand in "$SCRIPT_DIR" "$SCRIPT_DIR/.."; do
  if [[ -f "$cand/docker-compose.yml" ]]; then REPO_DIR="$(cd "$cand" && pwd)"; break; fi
done
[[ -n "$REPO_DIR" ]] || { echo "could not locate docker-compose.yml near $SCRIPT_DIR" >&2; exit 1; }
cd "$REPO_DIR"

CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[fix-db]${NC} $1"; }
warn() { echo -e "${YELLOW}[fix-db]${NC} $1"; }
die()  { echo -e "${RED}[fix-db]${NC} $1" >&2; exit 1; }

DC="docker compose"
docker info >/dev/null 2>&1 || DC="sudo docker compose"

[[ -f .env ]] || die ".env not found in ${REPO_DIR} — is this a configured install?"

# Read the value without sourcing .env (it may contain characters a shell would
# interpret, and we do not want its other variables in this process).
PW="$(grep -E '^POSTGRES_PASSWORD=' .env | head -1 | cut -d= -f2-)"
[[ -n "$PW" ]] || die "POSTGRES_PASSWORD is empty or missing in .env"

$DC ps --status running --services 2>/dev/null | grep -qx postgres \
  || die "the postgres service is not running — start it first: ${DC} up -d postgres"

# Does the CURRENT .env password already work over TCP (what the backend does)?
# The local unix socket is 'trust' in this image, so it would succeed either way
# and tell us nothing — the probe has to go over the network.
# 127.0.0.1 and the unix socket are both 'trust' in the stock pg_hba, so a probe
# through either succeeds regardless of the password and proves nothing. Probe
# the container's own bridge address, which hits the scram-sha-256 catch-all —
# the same rule the backend's connection matches.
probe_scram() {
  $DC exec -T -e PGPASSWORD="$PW" postgres \
    psql -h "$($DC exec -T postgres hostname -i | tr -d '\r' | awk '{print $1}')" \
      -p 5432 -U packetarch -d packetarch -tAc 'select 1' >/dev/null 2>&1
}

if probe_scram; then
  log "the password in .env already works — nothing to fix."
  log "If the backend is still failing, the cause is something else; check:"
  log "  ${DC} logs --tail 50 backend"
  exit 0
fi

warn "the password in .env does NOT authenticate against the running database."
warn "This matches the surviving-volume case described at the top of this script."

if (( CHECK_ONLY )); then
  warn "--check given: no changes made. Re-run without it to realign."
  exit 1
fi

# ALTER USER goes over the container's unix socket, which is 'trust' in this
# image — so no working password is needed to repair a broken one.
log "setting the packetarch role's password to the value in .env ..."
$DC exec -T postgres psql -U packetarch -d packetarch \
  -c "ALTER USER packetarch WITH PASSWORD '${PW//\'/\'\'}';" >/dev/null \
  || die "ALTER USER failed — see: ${DC} logs --tail 30 postgres"

probe_scram || die "password still does not authenticate after ALTER USER — stopping before restarting anything."
log "password realigned and verified over the network."

log "restarting the services that hold database connections ..."
$DC restart backend celery_worker >/dev/null
$DC up -d frontend >/dev/null 2>&1 || true

log "done. Watch the backend come up with:"
log "  ${DC} logs -f backend"
