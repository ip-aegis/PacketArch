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
# HAND-EDITS TO TRACKED FILES ARE NOT SUPPORTED, and this script is where that
# bites. A local change to docker-compose.yml — the ones sites actually reach
# for are `extra_hosts:` entries to paper over broken DNS, and a `build:
# network: host` tweak — makes the tree dirty, so the run STOPS in preflight
# unless you pass --force. With --force the change is stashed, reapplied after
# the checkout, and dropped back into the stash list if it conflicts with the
# new tag. Either way the site's fix is fragile at exactly the moment it is
# needed. Every knob those edits exist for has an .env equivalent, and .env is
# untracked, so upgrades never touch it:
#
#   extra_hosts for postgres/redis   ->  COMPOSE_SUBNET=<free /24>
#                                        (and it cannot fix the frontend anyway:
#                                        nginx resolves through 127.0.0.11, not
#                                        /etc/hosts)
#   build: network: host             ->  DOCKER_BUILD_NETWORK=host
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

 usage() { sed -n "3,37p" "$0" | sed 's/^# \{0,1\}//'; }

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

AUTOSTASH=""
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  [[ $FORCE -eq 1 ]] || fail preflight "working tree has local changes to tracked files. Commit/stash them, or use --force."
  AUTOSTASH="upgrade.sh autostash $(date -u +%FT%TZ)"
  warn "stashing local changes (--force)"
  if git stash push -m "$AUTOSTASH" >/dev/null; then
    warn "local changes stashed as: ${AUTOSTASH}"
  else
    AUTOSTASH=""
    warn "git stash push failed — continuing with the tree as-is"
  fi
fi

# Reapply the autostash after a checkout. Without this the stash was created
# and never restored, so a site carrying a needed local edit (the classic one
# is a build.network tweak in docker-compose.yml) silently lost it AND then
# failed the rebuild that follows — on exactly the host that needed the edit.
# A conflicting pop is reset away so the build still runs on a clean tree, but
# git keeps the stash (a failed pop never drops it) and we say so loudly.
restore_autostash() {
  [[ -n "$AUTOSTASH" ]] || return 0
  local ref
  ref="$(git stash list --format='%gd %gs' | grep -F -- "$AUTOSTASH" | head -1 | awk '{print $1}')"
  if [[ -z "$ref" ]]; then AUTOSTASH=""; return 0; fi
  if git stash pop "$ref" >/dev/null 2>&1; then
    warn "reapplied your stashed local changes"
    AUTOSTASH=""
  else
    git reset --hard HEAD >/dev/null 2>&1 || true
    warn "could NOT reapply your local changes — they conflict with this version."
    warn "They are preserved in the stash list as: ${AUTOSTASH}"
    warn "Reapply manually after the upgrade:  git stash list && git stash pop"
  fi
}

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

# ---- stack network subnet --------------------------------------------------
# v1.21.0 pins the stack's bridge subnet (docker-compose.yml
# `networks.default.ipam`, value from COMPOSE_SUBNET). Moving onto or off that
# pin CHANGES the declared network config, and a changed network must be
# RECREATED — not just re-`up`ed.
#
# Compose v2 does recreate it inside `up -d` on its own, in both directions
# (verified: unpinned->pinned, pinned->other-pin, pinned->unpinned). It cannot
# when a container OUTSIDE this compose project holds an endpoint on the
# network: `docker network rm` fails with "has active endpoints", compose exits
# non-zero, and it has already stopped every service — so the box is left
# DOWN. That is the case worth detecting by name, because the generic
# "compose up failed" rollback then hits the identical wall and only warns.
#
# Prints nothing and returns 0 when no recreate is needed.

# The subnet the CURRENT tree + .env will ask for ("" if none is declared).
declared_subnet() {
  $DC config --format json 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
cfg = ((d.get("networks") or {}).get("default") or {}).get("ipam") or {}
for c in cfg.get("config") or []:
    if c.get("subnet"):
        print(c["subnet"]); break
' 2>/dev/null
}

# The compose network's real name and current subnet ("" if it does not exist).
stack_network_name() {
  $DC config --format json 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
net = (d.get("networks") or {}).get("default") or {}
print(net.get("name") or (str(d.get("name") or "") + "_default"))
' 2>/dev/null
}
live_subnet() {
  ${SUDO} docker network inspect "$1" \
    --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}' 2>/dev/null | awk '{print $1}'
}
# Containers on the network that this compose project does not own.
foreign_endpoints() {
  local net="$1" proj="$2" id name p out=""
  while read -r id name; do
    [[ -z "$id" ]] && continue
    p="$(${SUDO} docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$id" 2>/dev/null)"
    [[ "$p" == "$proj" ]] || out="${out}${name} "
  done < <(${SUDO} docker network inspect "$net" \
             --format '{{range $k,$v := .Containers}}{{$k}} {{$v.Name}}
{{end}}' 2>/dev/null)
  echo "$out"
}

# Returns 0 if the stack can be brought up; 1 if a blocking condition was found.
prepare_stack_network() {
  local want have net proj foreign
  want="$(declared_subnet)"
  net="$(stack_network_name)"
  [[ -n "$net" ]] || return 0
  have="$(live_subnet "$net")"
  [[ -n "$have" ]] || return 0            # network does not exist yet — nothing to recreate
  [[ -n "$want" && "$want" != "$have" ]] || return 0
  proj="${COMPOSE_PROJECT_NAME:-$(basename "$REPO_DIR")}"
  proj="$($DC config --format json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("name",""))' 2>/dev/null || echo "$proj")"

  log "Stack network ${net}: ${have} -> ${want} (COMPOSE_SUBNET changed; network must be recreated)"
  foreign="$(foreign_endpoints "$net" "$proj")"
  if [[ -n "$foreign" ]]; then
    warn "Cannot recreate ${net}: these containers are attached but not part of"
    warn "this compose project, so removing the network will be refused:"
    warn "    ${foreign}"
    warn "Detach or remove them (docker network disconnect ${net} <name>), then re-run."
    return 1
  fi
  # Explicit down/up rather than relying on compose's implicit recreate, so a
  # failure is ours to see and roll back from. The implicit path is actively
  # unsafe mid-upgrade: `docker compose run --rm --no-deps backend alembic ...`
  # ALSO recreates a changed network, and it does so under a still-running
  # postgres — verified on Docker 29, the service stays up, gets re-addressed,
  # and stops resolving by name inside the run container. The migration then
  # fails with a name-resolution error that has nothing to do with the schema.
  $DC down --remove-orphans >/dev/null 2>&1 || warn "compose down reported an error; continuing"
  ${SUDO} docker network rm "$net" >/dev/null 2>&1 || true

  # Everything after this point (build, alembic) needs the database reachable
  # over the NEW network, so bring it back before returning.
  log "Restarting database on the new network ..."
  $DC up -d postgres redis >/dev/null || { warn "could not restart postgres/redis on ${want}"; return 1; }
  local i
  for i in $(seq 1 30); do
    $DC exec -T postgres pg_isready -U packetarch >/dev/null 2>&1 && return 0
    sleep 2
  done
  warn "postgres did not become ready on the new network"
  return 1
}

# Confirm the recreate actually landed, instead of trusting `up -d`'s exit code.
verify_stack_network() {
  local want have net
  want="$(declared_subnet)"
  net="$(stack_network_name)"
  [[ -n "$want" && -n "$net" ]] || return 0
  have="$(live_subnet "$net")"
  if [[ -n "$have" && "$have" != "$want" ]]; then
    warn "${net} is on ${have} but ${want} was declared — the network was not recreated."
    return 1
  fi
  [[ -n "$have" ]] && log "Stack network ${net} on ${have}"
  return 0
}

# ---- rollback helper -------------------------------------------------------
rollback() {
  write_status rolling_back running "Upgrade failed — rolling back to ${CURRENT_DESC}"
  warn "ROLLBACK: reverting code to ${CURRENT_DESC} (${CURRENT_REF:0:12})"
  # restore_autostash may have already reapplied the operator's changes onto
  # the new tag, leaving the tree dirty — which would make the checkout below
  # refuse and silently leave us on the FAILED version. Re-stash first.
  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    AUTOSTASH="upgrade.sh rollback autostash $(date -u +%FT%TZ)"
    git stash push -m "$AUTOSTASH" >/dev/null || AUTOSTASH=""
  fi
  git checkout --quiet "$CURRENT_REF" || warn "git checkout of previous ref failed"
  restore_autostash   # back on the ref it was taken from, so it reapplies cleanly
  # Rolling back to a tag that declares a DIFFERENT subnet (or none at all) is
  # the same network-recreate problem in reverse. Do it deliberately here: a
  # bare `up -d --build || warn` on this path would leave the box down with
  # nothing but a warning, on exactly the run that is already failing.
  prepare_stack_network || warn "stack network could not be prepared for rollback"
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
restore_autostash   # before the build, so a needed local edit is actually in effect

# The target tag may declare a different stack subnet than the running network
# (v1.21.0 pins it via COMPOSE_SUBNET). Settle that FIRST: every compose command
# from here on — including the alembic `compose run` — would otherwise trigger an
# implicit, silent network recreate at the worst possible moment.
if ! prepare_stack_network; then
  rollback
  die "the stack network could not be moved to the declared COMPOSE_SUBNET — rolled back to ${CURRENT_DESC}"
fi

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
if ! verify_stack_network; then
  rollback
  die "stack network is not on the declared COMPOSE_SUBNET — rolled back to ${CURRENT_DESC}"
fi

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
if [[ -n "$AUTOSTASH" ]]; then
  warn "REMINDER: your local changes are still stashed as '${AUTOSTASH}' (git stash list)"
fi

