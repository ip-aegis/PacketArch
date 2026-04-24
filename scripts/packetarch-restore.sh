#!/usr/bin/env bash
# PacketArch restore — reverses a backup produced by packetarch-backup.sh.
#
# Destroys existing data. You will be prompted to type RESTORE to confirm
# unless --yes is passed.
#
# Usage (from the install directory):
#   sudo ./packetarch-restore.sh packetarch-20260425T120000Z.tgz
#   sudo ./packetarch-restore.sh --yes packetarch-*.tgz
#
# Version-mismatch handling: the restore warns if the backup's
# packetarch_version differs from the currently-installed VERSION file,
# but does not block — Alembic migrations are re-run against the
# restored DB on backend startup, so forward migrations are safe.
# Downgrades are NOT safe and should be avoided.

set -euo pipefail

ASSUME_YES=0
INSTALL_DIR="${INSTALL_DIR:-$PWD}"
BACKUP=""

usage() {
    cat <<EOF
Usage: $0 [--yes] [--install-dir DIR] <backup.tgz>

  --yes            Skip the interactive RESTORE confirmation prompt.
  --install-dir    Where docker-compose.yml lives (default: cwd).
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes)           ASSUME_YES=1 ; shift ;;
        --install-dir)   INSTALL_DIR="$2" ; shift 2 ;;
        -h|--help)       usage ; exit 0 ;;
        *)
            [[ -z "${BACKUP}" ]] || { echo "Unexpected arg: $1" >&2 ; usage ; exit 1 ; }
            BACKUP="$1"
            shift
            ;;
    esac
done

[[ -n "${BACKUP}" ]] || { usage ; exit 1 ; }
[[ -f "${BACKUP}" ]] || { echo "ERROR: ${BACKUP} not found" >&2 ; exit 1 ; }
[[ -f "${INSTALL_DIR}/docker-compose.yml" ]] || {
    echo "ERROR: no docker-compose.yml in ${INSTALL_DIR}" >&2 ; exit 1 ; }

BACKUP="$(readlink -f "$BACKUP")"
cd "${INSTALL_DIR}"

STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT

echo "================================================================"
echo "  PacketArch restore"
echo "  backup:       ${BACKUP}"
echo "  install-dir:  ${INSTALL_DIR}"
echo "  staging:      ${STAGE}"
echo "================================================================"

# --- unpack + validate -------------------------------------------------
echo "[1/6] Unpacking backup..."
tar -C "${STAGE}" -xzf "${BACKUP}"
[[ -f "${STAGE}/manifest.json" ]] || {
    echo "ERROR: ${BACKUP} missing manifest.json — not a PacketArch backup" >&2
    exit 1
}
python3 -c "import json; json.load(open('${STAGE}/manifest.json'))" || {
    echo "ERROR: manifest.json is not valid JSON" >&2 ; exit 1 ; }

BACKUP_VERSION="$(python3 -c "
import json
print(json.load(open('${STAGE}/manifest.json')).get('packetarch_version','?'))
")"
CURRENT_VERSION="?"
if [[ -f VERSION ]]; then
    # shellcheck disable=SC1091
    . ./VERSION
    CURRENT_VERSION="${PACKETARCH_VERSION:-?}"
fi
echo "  backup version:  ${BACKUP_VERSION}"
echo "  current version: ${CURRENT_VERSION}"
if [[ "${BACKUP_VERSION}" != "${CURRENT_VERSION}" && "${BACKUP_VERSION}" != "?" ]]; then
    echo "  WARNING: version mismatch — alembic will forward-migrate, but downgrade is UNSUPPORTED." >&2
fi

PROJECT="$(python3 -c "
import json
print(json.load(open('${STAGE}/manifest.json')).get('compose_project',''))
")"
if [[ -z "${PROJECT}" ]]; then
    PROJECT="$(basename "${INSTALL_DIR}" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')"
fi

# --- confirm -----------------------------------------------------------
if [[ ${ASSUME_YES} -ne 1 ]]; then
    echo ""
    echo "THIS WILL OVERWRITE ALL DATA IN ${INSTALL_DIR}:"
    echo "  - PostgreSQL database (packetarch)"
    echo "  - pcap_output, pcap_uploads volumes"
    if [[ -f "${STAGE}/env.raw" ]]; then
        echo "  - .env (with secrets from backup)"
    fi
    echo ""
    read -r -p "Type RESTORE to continue: " CONFIRM
    [[ "${CONFIRM}" == "RESTORE" ]] || { echo "Aborted." ; exit 1 ; }
fi

# --- stop stack ---------------------------------------------------------
echo "[2/6] Stopping stack..."
docker compose down

# --- restore volumes ---------------------------------------------------
echo "[3/6] Restoring volumes..."
restore_volume() {
    local name="$1"
    local archive="${STAGE}/${name}.tar.gz"
    local full="${PROJECT}_${name}"
    if [[ ! -f "${archive}" ]]; then
        echo "  ${name}: not in backup, skipping"
        return
    fi
    # Ensure volume exists, then wipe and re-populate.
    docker volume create "${full}" >/dev/null
    docker run --rm -v "${full}:/data" alpine sh -c 'rm -rf /data/* /data/..?* /data/.[!.]*' >/dev/null 2>&1 || true
    docker run --rm -v "${full}:/data" -v "${STAGE}:/backup:ro" \
        alpine tar xzf "/backup/${name}.tar.gz" -C /data
    echo "  ${full} restored"
}
restore_volume pcap_output
restore_volume pcap_uploads

# --- restore postgres ---------------------------------------------------
echo "[4/6] Restoring PostgreSQL..."
# Ensure .env has credentials postgres needs to come up. If the backup
# carried raw secrets, apply them first so the postgres container comes
# up with the same password the pg_dump was taken against.
if [[ -f "${STAGE}/env.raw" ]]; then
    cp "${STAGE}/env.raw" .env
    chmod 600 .env
    echo "  .env restored with secrets from backup"
elif [[ -f "${STAGE}/env.redacted" ]]; then
    echo "  backup carried redacted .env; keeping existing .env on this host"
fi

docker compose up -d postgres
echo "  waiting for postgres to accept connections..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U packetarch >/dev/null 2>&1; then
        break
    fi
    sleep 2
    [[ $i -eq 30 ]] && { echo "ERROR: postgres did not come up" >&2 ; exit 1 ; }
done

# Drop and recreate the DB to ensure a clean restore.
docker compose exec -T postgres psql -U packetarch -d postgres <<'SQL'
DROP DATABASE IF EXISTS packetarch;
CREATE DATABASE packetarch;
SQL
docker compose exec -T postgres pg_restore -U packetarch -d packetarch \
    --no-owner --no-privileges < "${STAGE}/postgres.dump"
echo "  database restored"

# --- start everything --------------------------------------------------
echo "[5/6] Starting full stack..."
docker compose up -d

echo "[6/6] Waiting for backend healthcheck..."
for i in $(seq 1 30); do
    if docker compose ps backend 2>/dev/null | grep -q "healthy"; then
        echo "  backend healthy."
        break
    fi
    sleep 10
    [[ $i -eq 30 ]] && echo "  WARNING: backend did not report healthy after 5 minutes — check logs" >&2
done

echo ""
echo "================================================================"
echo "  Restore complete."
if [[ -f "${STAGE}/env.redacted" ]]; then
    echo ""
    echo "  Backup carried a REDACTED .env. Verify these .env fields on"
    echo "  this host match your expectations (admin password, API keys):"
    echo ""
    grep -E '^(POSTGRES_PASSWORD|SECRET_KEY|ENCRYPTION_KEY|ADMIN_PASSWORD|ANTHROPIC_API_KEY)=' .env | \
        sed 's/=.*/=<set>/'
fi
echo "================================================================"
