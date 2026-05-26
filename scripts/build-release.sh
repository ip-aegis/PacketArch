#!/usr/bin/env bash
# Build a self-contained offline release tarball.
#
# Produces dist/packetarch-<version>-offline.tar.gz containing:
#   - All Docker images saved to tarballs (backend, frontend, postgres,
#     redis, agent) so `docker load` works in an air-gapped lab.
#   - An offline docker-compose.yml that references image tags (no build:
#     stanzas), paired with an .env.example template.
#   - LICENSE, NOTICE, THIRD_PARTY_LICENSES.md (if present), README_SITE.md.
#   - install.sh that docker-loads the images, generates secrets into .env,
#     and starts the stack.
#
# Usage (from repo root):
#   ./scripts/build-release.sh
#
# Env overrides:
#   SKIP_AGENT=1        Skip building the agent image (faster test builds)
#   PCAP_ONLY=1         Build the PCAP-only variant. Forces SKIP_AGENT=1,
#                       changes the tarball name to ...-pcap-offline.tar.gz,
#                       and stamps BUILD_VARIANT=pcap-only into VERSION so
#                       install.sh disables LIVE_TRAFFIC_ENABLED.
#   VERSION=0.2.0       Override the version string
#   OUT_DIR=/some/path  Override dist/ output directory

set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

# --- derive metadata ----------------------------------------------------
VERSION="${VERSION:-$(grep -E '^\s*app_version' backend/app/core/config.py \
    | head -1 | sed 's/.*= *"\([^"]*\)".*/\1/')}"
BUILD_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# PCAP-only variant implies no agent image and a different tarball name.
if [[ "${PCAP_ONLY:-0}" == "1" ]]; then
    BUILD_VARIANT="pcap-only"
    SKIP_AGENT=1
    VARIANT_SUFFIX="-pcap"
else
    BUILD_VARIANT="full"
    VARIANT_SUFFIX=""
fi

OUT_DIR="${OUT_DIR:-${REPO_ROOT}/dist}"
STAGE="${OUT_DIR}/packetarch-${VERSION}${VARIANT_SUFFIX}-offline"
TARBALL="${OUT_DIR}/packetarch-${VERSION}${VARIANT_SUFFIX}-offline.tar.gz"

BACKEND_IMAGE="packetarch/backend:${VERSION}"
FRONTEND_IMAGE="packetarch/frontend:${VERSION}"
AGENT_IMAGE="packetarch/agent:${VERSION}"
POSTGRES_IMAGE="timescale/timescaledb:latest-pg15"
REDIS_IMAGE="redis:7-alpine"

echo "========================================================"
echo "  PacketArch offline release builder"
echo "  version:     ${VERSION}"
echo "  variant:     ${BUILD_VARIANT}"
echo "  commit:      ${BUILD_COMMIT}"
echo "  date:        ${BUILD_DATE}"
echo "  staging:     ${STAGE}"
echo "  output:      ${TARBALL}"
echo "========================================================"

# --- prechecks ----------------------------------------------------------
command -v docker >/dev/null || { echo "ERROR: docker not on PATH" >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "ERROR: docker daemon not reachable" >&2; exit 1; }

rm -rf "${STAGE}"
mkdir -p "${STAGE}/images" "${STAGE}/docker"

# --- build app images ---------------------------------------------------
echo "[1/6] Building backend image ${BACKEND_IMAGE}..."
docker build \
    --tag "${BACKEND_IMAGE}" \
    --build-arg BUILD_COMMIT="${BUILD_COMMIT}" \
    --build-arg BUILD_DATE="${BUILD_DATE}" \
    "${REPO_ROOT}/backend"

echo "[2/6] Building frontend image ${FRONTEND_IMAGE}..."
docker build \
    --tag "${FRONTEND_IMAGE}" \
    --build-arg BUILD_COMMIT="${BUILD_COMMIT}" \
    --build-arg BUILD_DATE="${BUILD_DATE}" \
    "${REPO_ROOT}/frontend"

if [[ "${SKIP_AGENT:-0}" == "1" ]]; then
    echo "[3/6] SKIP_AGENT=1 — not building agent image"
    AGENT_INCLUDED=0
else
    echo "[3/6] Building agent image ${AGENT_IMAGE}..."
    docker build \
        --tag "${AGENT_IMAGE}" \
        "${REPO_ROOT}/docker/packetarch-agent"
    AGENT_INCLUDED=1
fi

# --- pull external images (so they're in the local store) ---------------
echo "[4/6] Pulling external images..."
docker pull "${POSTGRES_IMAGE}"
docker pull "${REDIS_IMAGE}"

# --- save images --------------------------------------------------------
echo "[5/6] Saving images to ${STAGE}/images/ ..."
docker save "${BACKEND_IMAGE}"  | gzip > "${STAGE}/images/backend.tar.gz"
docker save "${FRONTEND_IMAGE}" | gzip > "${STAGE}/images/frontend.tar.gz"
docker save "${POSTGRES_IMAGE}" | gzip > "${STAGE}/images/postgres.tar.gz"
docker save "${REDIS_IMAGE}"    | gzip > "${STAGE}/images/redis.tar.gz"
if [[ "${AGENT_INCLUDED}" == "1" ]]; then
    docker save "${AGENT_IMAGE}" | gzip > "${STAGE}/images/agent.tar.gz"
fi

# --- stage runtime files ------------------------------------------------
echo "[6/6] Staging compose, install script, docs, licenses..."

cp "${REPO_ROOT}/LICENSE"   "${STAGE}/LICENSE"
cp "${REPO_ROOT}/NOTICE"    "${STAGE}/NOTICE"
cp "${REPO_ROOT}/docker/init-db.sql" "${STAGE}/docker/init-db.sql"

# THIRD_PARTY_LICENSES is optional (generated separately).
if [[ -f "${REPO_ROOT}/THIRD_PARTY_LICENSES.md" ]]; then
    cp "${REPO_ROOT}/THIRD_PARTY_LICENSES.md" "${STAGE}/THIRD_PARTY_LICENSES.md"
else
    echo "WARNING: THIRD_PARTY_LICENSES.md not found; run scripts/generate_third_party_licenses.sh before release." >&2
fi

# VERSION file — machine-readable metadata for the install script.
cat > "${STAGE}/VERSION" <<EOF
PACKETARCH_VERSION=${VERSION}
BUILD_COMMIT=${BUILD_COMMIT}
BUILD_DATE=${BUILD_DATE}
BUILD_VARIANT=${BUILD_VARIANT}
AGENT_INCLUDED=${AGENT_INCLUDED}
EOF

# README_SITE and install.sh are versioned in scripts/release-bundle/.
cp "${REPO_ROOT}/scripts/release-bundle/README_SITE.md" "${STAGE}/README.md"
cp "${REPO_ROOT}/scripts/release-bundle/install.sh"      "${STAGE}/install.sh"
cp "${REPO_ROOT}/scripts/release-bundle/docker-compose.offline.yml" \
                                                         "${STAGE}/docker-compose.yml"
cp "${REPO_ROOT}/scripts/release-bundle/.env.example"    "${STAGE}/.env.example"
# Backup/restore utilities — ship alongside install.sh so operators have
# them from day one without having to hunt the repo.
cp "${REPO_ROOT}/scripts/packetarch-backup.sh"  "${STAGE}/packetarch-backup.sh"
cp "${REPO_ROOT}/scripts/packetarch-restore.sh" "${STAGE}/packetarch-restore.sh"
chmod +x "${STAGE}/install.sh" "${STAGE}/packetarch-backup.sh" "${STAGE}/packetarch-restore.sh"

# Portable scenario authoring kit — schema, registry snapshot, spec doc,
# and the ready-to-use LLM prompt. Ships in every install so airgapped
# authors (and the AI tools they use) can produce .pascenario.json files
# without touching a PacketArch server.
mkdir -p "${STAGE}/schemas" "${STAGE}/docs"
cp "${REPO_ROOT}/schemas/packetarch-scenario.v1.json"   "${STAGE}/schemas/packetarch-scenario.v1.json"
if [[ -f "${REPO_ROOT}/schemas/fingerprint-registry.v1.json" ]]; then
    cp "${REPO_ROOT}/schemas/fingerprint-registry.v1.json" "${STAGE}/schemas/fingerprint-registry.v1.json"
else
    echo "WARNING: schemas/fingerprint-registry.v1.json not found; run scripts/generate_fingerprint_registry_snapshot.py before release." >&2
fi
cp "${REPO_ROOT}/docs/SCENARIO_SPEC.md" "${STAGE}/docs/SCENARIO_SPEC.md"
cp "${REPO_ROOT}/backend/app/static/downloads/LLM_PROMPT.md" "${STAGE}/docs/LLM_PROMPT.md"

# --- pack ---------------------------------------------------------------
echo "Packing ${TARBALL} ..."
mkdir -p "${OUT_DIR}"
tar -C "${OUT_DIR}" -czf "${TARBALL}" "$(basename "${STAGE}")"

SIZE="$(du -h "${TARBALL}" | awk '{print $1}')"
echo ""
echo "========================================================"
echo "  Done."
echo "  Tarball: ${TARBALL}  (${SIZE})"
echo "  Verify:  tar -tzf ${TARBALL} | head"
echo "========================================================"
