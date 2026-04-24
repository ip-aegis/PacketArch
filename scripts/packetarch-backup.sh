#!/usr/bin/env bash
# PacketArch backup — captures database, PCAP volumes, and optionally
# .env secrets into a single tarball suitable for restore on the same
# or a different host.
#
# Usage (from the install directory, i.e. wherever docker-compose.yml lives):
#   sudo ./packetarch-backup.sh                       # writes ./backups/*.tgz
#   sudo ./packetarch-backup.sh --output /mnt/a.tgz
#   sudo ./packetarch-backup.sh --with-secrets        # include raw .env
#
# By default, the backup includes a REDACTED copy of .env (structure +
# comments, secrets stripped). Pair with --with-secrets only if the
# backup file itself will be stored encrypted or on trusted media —
# otherwise restoring on a new box will need its secrets regenerated.

set -euo pipefail

OUTPUT=""
WITH_SECRETS=0
INSTALL_DIR="${INSTALL_DIR:-$PWD}"

usage() {
    cat <<EOF
Usage: $0 [--output FILE] [--with-secrets] [--install-dir DIR]

  --output FILE       Destination tarball (default: ./backups/packetarch-<ts>.tgz)
  --with-secrets      Include raw .env with database/JWT/admin secrets.
  --install-dir DIR   Where to find docker-compose.yml (default: cwd).
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)        OUTPUT="$2" ; shift 2 ;;
        --with-secrets)  WITH_SECRETS=1 ; shift ;;
        --install-dir)   INSTALL_DIR="$2" ; shift 2 ;;
        -h|--help)       usage ; exit 0 ;;
        *)               echo "Unknown arg: $1" >&2 ; usage ; exit 1 ;;
    esac
done

[[ -f "${INSTALL_DIR}/docker-compose.yml" ]] || {
    echo "ERROR: no docker-compose.yml in ${INSTALL_DIR}" >&2
    exit 1
}
[[ -f "${INSTALL_DIR}/.env" ]] || {
    echo "ERROR: no .env in ${INSTALL_DIR}" >&2
    exit 1
}

cd "${INSTALL_DIR}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -z "${OUTPUT}" ]]; then
    mkdir -p ./backups
    OUTPUT="./backups/packetarch-${TS}.tgz"
fi
OUTPUT="$(readlink -f "$OUTPUT")"

STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT

echo "================================================================"
echo "  PacketArch backup"
echo "  install-dir:  ${INSTALL_DIR}"
echo "  output:       ${OUTPUT}"
echo "  with-secrets: $([[ ${WITH_SECRETS} -eq 1 ]] && echo YES || echo no)"
echo "  staging:      ${STAGE}"
echo "================================================================"

# --- determine the compose project name (= volume name prefix) ---------
PROJECT="$(docker compose config --format json 2>/dev/null | \
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("name",""))' \
    2>/dev/null || true)"
if [[ -z "${PROJECT}" ]]; then
    PROJECT="$(basename "${INSTALL_DIR}" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')"
fi
echo "Compose project: ${PROJECT}"

# --- dump the database -------------------------------------------------
echo "[1/5] Dumping PostgreSQL..."
docker compose exec -T postgres pg_dump -U packetarch -d packetarch --format=custom \
    > "${STAGE}/postgres.dump"
echo "  $(wc -c < "${STAGE}/postgres.dump" | numfmt --to=iec) dumped"

# --- archive named volumes --------------------------------------------
echo "[2/5] Archiving Docker volumes..."
archive_volume() {
    local name="$1"
    local full="${PROJECT}_${name}"
    if docker volume inspect "${full}" >/dev/null 2>&1; then
        echo "  ${full} → ${name}.tar.gz"
        docker run --rm \
            -v "${full}:/data:ro" \
            -v "${STAGE}:/backup" \
            alpine tar czf "/backup/${name}.tar.gz" -C /data .
    else
        echo "  ${full} — not present, skipping"
    fi
}
archive_volume pcap_output
archive_volume pcap_uploads
# ssl_certs deliberately skipped — let the target host regenerate, or
# the operator drop a real cert into ./certs/. Restoring self-signed
# certs cross-host is a footgun (CN mismatch).

# --- .env handling ----------------------------------------------------
echo "[3/5] Capturing .env ..."
if [[ "${WITH_SECRETS}" -eq 1 ]]; then
    cp .env "${STAGE}/env.raw"
    echo "  .env captured with secrets (WITH_SECRETS=1)"
else
    # Redact anything that looks like a secret; preserve keys + comments so
    # restore.sh can show the operator what needs regenerating.
    sed -E 's/^(POSTGRES_PASSWORD|SECRET_KEY|ENCRYPTION_KEY|ADMIN_PASSWORD|ANTHROPIC_API_KEY)=.*/\1=<REDACTED — regenerate on restore>/' \
        .env > "${STAGE}/env.redacted"
    echo "  .env redacted"
fi

# --- version metadata -------------------------------------------------
echo "[4/5] Writing manifest..."
VERSION=""
if [[ -f VERSION ]]; then
    cp VERSION "${STAGE}/VERSION"
    # shellcheck disable=SC1091
    . ./VERSION
    VERSION="${PACKETARCH_VERSION:-unknown}"
fi

cat > "${STAGE}/manifest.json" <<EOF
{
  "format_version": "1",
  "packetarch_version": "${VERSION:-unknown}",
  "compose_project": "${PROJECT}",
  "created_at": "${TS}",
  "with_secrets": $([[ ${WITH_SECRETS} -eq 1 ]] && echo true || echo false),
  "includes": [
    "postgres.dump",
    "pcap_output.tar.gz",
    "pcap_uploads.tar.gz",
    "$([[ ${WITH_SECRETS} -eq 1 ]] && echo env.raw || echo env.redacted)"
  ]
}
EOF

# --- pack -------------------------------------------------------------
echo "[5/5] Packing ${OUTPUT} ..."
mkdir -p "$(dirname "${OUTPUT}")"
tar -C "${STAGE}" -czf "${OUTPUT}" .
SIZE="$(du -h "${OUTPUT}" | awk '{print $1}')"

echo ""
echo "================================================================"
echo "  Backup complete: ${OUTPUT}  (${SIZE})"
echo ""
echo "  Restore with:"
echo "    sudo ./packetarch-restore.sh ${OUTPUT}"
echo "================================================================"
