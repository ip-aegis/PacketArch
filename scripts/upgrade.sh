#!/usr/bin/env bash
#
# PacketArch upgrade — move an install to a tagged release, safely.
#
# Labs track RELEASES (git tags vX.Y.Z), not bleeding-edge master. This script
# backs up, checks out the target tag, rebuilds, applies database migrations,
# verifies health, and AUTOMATICALLY ROLLS BACK (code + database) if the
# upgraded stack doesn't come up healthy.
#
# Run from anywhere inside the install — it resolves the repo root from its
# own location. Needs Docker access (uses sudo automatically if you're not in
# the docker group).
#
#   ./scripts/upgrade.sh                 # upgrade to the latest release tag
#   ./scripts/upgrade.sh --to v1.2.0     # upgrade (or downgrade) to a tag
#   ./scripts/upgrade.sh --check         # report current vs latest, do nothing
#   ./scripts/upgrade.sh --list          # list available release tags
#   ./scripts/upgrade.sh --no-backup     # skip the pre-upgrade backup (faster)
#   ./scripts/upgrade.sh --force         # proceed even with a dirty working tree
#   ./scripts/upgrade.sh --status-file F # write JSON progress to F (used by the
#                                        #   in-app one-button upgrade)
#
set -euo pipefail

# ---- locate repo + compose wrapper -----------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_DIR}"

C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_RED='\033[0;31m'; C_OFF='\033[0m'
log()  { printf "${C_GREEN}[upgrade]${C_OFF} %s\n" "$*"; }
warn() { printf "${C_YELLOW}[upgrade]${C_OFF} %s\n" "$*" >&2; }
die()  { printf "${C_RED}[upgrade] ERROR:${C_OFF} %s\n" "$*" >&2; exit 1; }

usage() { sed -n '3,21p' "$0" | sed 's/^# \{0,1\}//'; }

# ---- status file (consumed by the backend's /system/upgrade-status) --------
STATUS_FILE=""
UPGRADE_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
STARTED_AT="$(date -u +%FT%TZ)"
BACKUP_FILE=""
CURRENT_DESC="?"; TARGET="?"
# write_status PHASE STATUS MESSAGE [ERROR]
write_status() {
  [[ -n "$STATUS_FILE" ]] || return 0
  local now finished="null" err="null" bf="null"
  now="$(date -u +%FT%TZ)"
  case "$2" in success|failed|rolled_back) finished="\"$now\"" ;; esac
  [[ -n "${4:-}" ]] && err="\"${4//\"/\'}\""
  [[ -n "$BACKUP_FILE" ]] && bf="\"$BACKUP_FILE\""
  cat > "${STATUS_FILE}.tmp" <<JSON
{"schema":1,"upgrade_id":"${UPGRADE_ID}","from_version":"${CURRENT_DESC}","to_version":"${TARGET}","phase":"$1","status":"$2","message":"${3//\"/\'}","started_at":"${STARTED_AT}","updated_at":"${now}","finished_at":${finished},"backup_file":${bf},"error":${err}}
JSON
  mv -f "${STATUS_FILE}.tmp" "$STATUS_FILE"
}
# fail with a terminal "failed" status (used where there is nothing to roll back)
fail() { write_status "${1}" failed "${2}" "${2}"; die "${2}"; }

[[ -f docker-compose.yml ]] || die "docker-compose.yml not found in ${REPO_DIR}"

if docker info >/dev/null 2>&1; then SUDO=""; else SUDO="sudo"; fi
DC="${SUDO} docker compose"

# ---- args ------------------------------------------------------------------
DO_BACKUP=1; FORCE=0; MODE="upgrade"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --to)          TARGET="${2:-}"; shift 2 ;;
    --check)       MODE="check"; shift ;;
    --list)        MODE="list"; shift ;;
    --no-backup)   DO_BACKUP=0; shift ;;
    --force)       FORCE=1; shift ;;
    --status-file) STATUS_FILE="${2:-}"; shift 2 ;;
    -h|--help)     usage; exit 0 ;;
    *)             die "unknown arg: $1 (try --help)" ;;
  esac
done
[[ "$TARGET" == "?" ]] && TARGET=""

# ---- version discovery -----------------------------------------------------
log "Fetching release tags..."
git fetch --tags --force --quiet origin || warn "git fetch failed (offline?); using local tags"

CURRENT_REF="$(git rev-parse HEAD)"
CURRENT_DESC="$(git describe --tags --always 2>/dev/null || echo "${CURRENT_REF:0:12}")"

if [[ "$MODE" == "list" ]]; then
  echo "Available release tags (newest first):"
  git tag -l 'v*' --sort=-v:refname | head -20
  exit 0
fi

LATEST_TAG="$(git tag -l 'v*' --sort=-v:refname | head -1 || true)"
[[ -n "$LATEST_TAG" ]] || die "no release tags (v*) found. Cut one with: git tag vX.Y.Z && git push origin vX.Y.Z"
TARGET="${TARGET:-$LATEST_TAG}"
git rev-parse -q --verify "refs/tags/${TARGET}^{commit}" >/dev/null 2>&1 \
  || die "tag '${TARGET}' not found. Try: $0 --list"
TARGET_REF="$(git rev-parse "refs/tags/${TARGET}^{commit}")"

log "Current : ${CURRENT_DESC}"
log "Target  : ${TARGET}   (latest available: ${LATEST_TAG})"

if [[ "$MODE" == "check" ]]; then
  if [[ "$TARGET_REF" == "$CURRENT_REF" ]]; then log "Already up to date."
  else log "Update available: ${CURRENT_DESC} -> ${TARGET}"; fi
  exit 0
fi

# ---- preflight -------------------------------------------------------------
write_status preflight running "Preparing to upgrade ${CURRENT_DESC} -> ${TARGET}"

if [[ "$TARGET_REF" == "$CURRENT_REF" && $FORCE -ne 1 ]]; then
  log "Already on ${TARGET}. Use --force to rebuild anyway."
  write_status success success "Already on ${TARGET}"
  exit 0
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  [[ $FORCE -eq 1 ]] || fail preflight "working tree has local changes to tracked files. Commit/stash them, or use --force."
  warn "stashing local changes (--force)"
  git stash push -m "upgrade.sh autostash $(date -u +%FT%TZ)" >/dev/null || true
fi

[[ -f .env ]] || fail preflight ".env missing — is this a configured install?"

log "Ensuring database is up..."
$DC up -d postgres redis >/dev/null
for i in $(seq 1 30); do
  if $DC exec -T postgres pg_isready -U packetarch >/dev/null 2>&1; then break; fi
  if [[ $i -eq 30 ]]; then fail preflight "postgres did not become ready"; fi
  sleep 2
done

# ---- alembic tracking bootstrap --------------------------------------------
# create_all is the schema baseline; the migration chain is incremental. For an
# untracked DB, stamp the CURRENT (old) code's head BEFORE checkout so the
# post-checkout `upgrade head` applies only the new deltas (never replays the
# historical chain). The backend entrypoint does the same per-boot, but doing it
# here gives the correct cross-version stamp and lets a failure roll back early.
psql_q() { $DC exec -T postgres psql -U packetarch -d packetarch -tAc "$1" 2>/dev/null | tr -d '[:space:]'; }
TRACKED="$(psql_q "SELECT to_regclass('public.alembic_version') IS NOT NULL" || echo f)"
if [[ "$TRACKED" != "t" ]]; then
  OLD_HEAD="$($DC run --rm --no-deps backend alembic heads 2>/dev/null | awk 'NR==1{print $1}' || true)"
  if [[ -n "$OLD_HEAD" ]]; then
    log "DB not alembic-tracked; stamping current head ${OLD_HEAD} before upgrade."
    if $DC run --rm --no-deps backend alembic stamp "$OLD_HEAD"; then
      TRACKED=t
    else
      warn "alembic stamp failed; create_all will keep the baseline this run"
    fi
  else
    warn "could not determine current alembic head; relying on create_all this run"
  fi
fi

# ---- backup ----------------------------------------------------------------
if [[ $DO_BACKUP -eq 1 ]]; then
  # Create the dir first: packetarch-backup.sh canonicalizes --output with
  # `readlink -f`, which fails (silently, under set -e) if the parent is absent.
  mkdir -p "${REPO_DIR}/backups"
  BACKUP_FILE="${REPO_DIR}/backups/pre-upgrade-$(date -u +%Y%m%dT%H%M%SZ).tgz"
  write_status backup running "Backing up database + volumes"
  log "Backing up to ${BACKUP_FILE} ..."
  ${SUDO} bash "${SCRIPT_DIR}/packetarch-backup.sh" --install-dir "${REPO_DIR}" --output "${BACKUP_FILE}" \
    || { BACKUP_FILE=""; fail backup "backup failed; aborting before any changes were made"; }
fi

# ---- rollback helper -------------------------------------------------------
rollback() {
  write_status rolling_back running "Upgrade failed — rolling back to ${CURRENT_DESC}"
  warn "ROLLBACK: reverting code to ${CURRENT_DESC} (${CURRENT_REF:0:12})"
  git checkout --quiet "$CURRENT_REF" || warn "git checkout of previous ref failed"
  $DC up -d --build || warn "rebuild during rollback failed"
  if [[ -n "$BACKUP_FILE" && -f "$BACKUP_FILE" ]]; then
    warn "restoring database from pre-upgrade backup"
    ${SUDO} bash "${SCRIPT_DIR}/packetarch-restore.sh" --yes --install-dir "${REPO_DIR}" "$BACKUP_FILE" \
      || warn "DB restore FAILED — backup preserved at ${BACKUP_FILE}"
  fi
  $DC up -d || true
  $DC restart frontend >/dev/null 2>&1 || true
  write_status rolled_back rolled_back "Rolled back to ${CURRENT_DESC}"
}

# ---- apply -----------------------------------------------------------------
write_status checkout running "Checking out ${TARGET}"
log "Checking out ${TARGET} ..."
git checkout --quiet "refs/tags/${TARGET}" || fail checkout "git checkout ${TARGET} failed"

write_status building running "Building images for ${TARGET}"
log "Building images for ${TARGET} (this can take a few minutes) ..."
if ! $DC build; then rollback; die "image build failed — rolled back to ${CURRENT_DESC}"; fi

# Apply migrations BEFORE booting the app (a failure here rolls back cleanly).
if [[ "$TRACKED" == "t" ]]; then
  write_status migrating running "Applying database migrations"
  log "Applying database migrations (alembic upgrade head) ..."
  if ! $DC run --rm --no-deps backend alembic upgrade head; then
    rollback; die "database migration failed — rolled back to ${CURRENT_DESC}"
  fi
else
  warn "skipping alembic migrations (DB not tracked); create_all keeps the baseline"
fi

write_status starting running "Starting upgraded stack"
log "Starting upgraded stack ..."
if ! $DC up -d; then rollback; die "compose up failed — rolled back to ${CURRENT_DESC}"; fi

# Re-resolve nginx's backend upstream: a recreated backend gets a new container
# IP, and the (possibly unchanged) frontend's nginx caches the old one -> 502.
$DC restart frontend >/dev/null 2>&1 || warn "frontend restart failed (nginx may serve 502 until restarted)"

# ---- verify ----------------------------------------------------------------
write_status verifying running "Waiting for backend health"
log "Waiting for backend health ..."
HEALTHY=0
for i in $(seq 1 60); do
  if $DC exec -T backend curl -fsS http://localhost:8001/health >/dev/null 2>&1; then HEALTHY=1; break; fi
  sleep 5
done
if [[ $HEALTHY -ne 1 ]]; then
  rollback
  die "backend did not become healthy after upgrade — rolled back to ${CURRENT_DESC}"
fi

write_status success success "Upgrade complete: now on ${TARGET}"
log "Upgrade complete: ${CURRENT_DESC} -> ${TARGET}"
[[ -n "$BACKUP_FILE" ]] && log "Pre-upgrade backup kept at ${BACKUP_FILE}"
log "Previous images are retained for fast rollback — run 'docker image prune' to reclaim space."
