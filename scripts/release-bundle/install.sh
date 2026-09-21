#!/usr/bin/env bash
# PacketArch offline installer.
#
# Idempotent. Safe to re-run for upgrades (pass --upgrade to skip secret
# generation and docker-compose up). Never overwrites an existing .env
# unless --force-env is given.

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/packetarch}"
UPGRADE=0
FORCE_ENV=0

usage() {
    cat <<EOF
Usage: sudo ./install.sh [--upgrade] [--force-env] [--install-dir PATH]

  --upgrade        Load new images and restart; preserve existing .env + volumes.
  --force-env      Overwrite an existing .env (generates new secrets — breaks
                   existing logins and database access!).
  --install-dir    Where to place the PacketArch installation (default: ${INSTALL_DIR}).
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --upgrade)      UPGRADE=1 ; shift ;;
        --force-env)    FORCE_ENV=1 ; shift ;;
        --install-dir)  INSTALL_DIR="$2" ; shift 2 ;;
        -h|--help)      usage ; exit 0 ;;
        *)              echo "Unknown arg: $1" >&2 ; usage ; exit 1 ;;
    esac
done

# --- prechecks ----------------------------------------------------------
if [[ "$(id -u)" -ne 0 ]]; then
    echo "ERROR: install.sh must run as root (use sudo)." >&2
    exit 1
fi
command -v docker >/dev/null || { echo "ERROR: Docker not installed." >&2; exit 1; }
docker compose version >/dev/null 2>&1 || {
    echo "ERROR: Docker Compose plugin missing." >&2; exit 1; }

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
[[ -f "${SRC_DIR}/VERSION" ]] || {
    echo "ERROR: run install.sh from the extracted release directory." >&2
    exit 1
}
# shellcheck disable=SC1091
source "${SRC_DIR}/VERSION"

echo "================================================================"
echo "  PacketArch ${PACKETARCH_VERSION} (build ${BUILD_COMMIT})"
echo "  variant:     ${BUILD_VARIANT:-full}"
echo "  install-dir: ${INSTALL_DIR}"
echo "  mode:        $([[ ${UPGRADE} -eq 1 ]] && echo upgrade || echo fresh install)"
echo "================================================================"

mkdir -p "${INSTALL_DIR}"

# --- stage files --------------------------------------------------------
echo "[1/5] Staging files in ${INSTALL_DIR}..."
cp "${SRC_DIR}/docker-compose.yml" "${INSTALL_DIR}/docker-compose.yml"
cp "${SRC_DIR}/VERSION"            "${INSTALL_DIR}/VERSION"
cp "${SRC_DIR}/LICENSE"            "${INSTALL_DIR}/LICENSE"
cp "${SRC_DIR}/NOTICE"             "${INSTALL_DIR}/NOTICE"
[[ -f "${SRC_DIR}/THIRD_PARTY_LICENSES.md" ]] && \
    cp "${SRC_DIR}/THIRD_PARTY_LICENSES.md" "${INSTALL_DIR}/THIRD_PARTY_LICENSES.md"
mkdir -p "${INSTALL_DIR}/docker"
cp "${SRC_DIR}/docker/init-db.sql" "${INSTALL_DIR}/docker/init-db.sql"

# --- load images --------------------------------------------------------
echo "[2/5] Loading Docker images (this can take a minute)..."
for img in "${SRC_DIR}/images/"*.tar.gz; do
    [[ -f "$img" ]] || continue
    echo "  loading $(basename "$img") ..."
    gunzip -c "$img" | docker load
done

# --- generate .env (skip on upgrade unless --force-env) -----------------
ENV_FILE="${INSTALL_DIR}/.env"
if [[ -f "${ENV_FILE}" && ${FORCE_ENV} -eq 0 ]]; then
    echo "[3/5] .env exists — preserving. Use --force-env to regenerate."
elif [[ ${UPGRADE} -eq 1 && ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: --upgrade but no existing .env in ${INSTALL_DIR}." >&2
    echo "       Did you mean a fresh install? Drop --upgrade." >&2
    exit 1
else
    echo "[3/5] Generating .env with fresh secrets..."
    POSTGRES_PW="$(openssl rand -hex 16)"
    SECRET_KEY="$(openssl rand -hex 32)"
    ENCRYPTION_KEY="$(openssl rand -base64 32)"
    # No ADMIN_PASSWORD generated — the operator picks their admin
    # credentials in the first-run setup wizard at https://<server>/.

    # PCAP-only variant disables LIVE_TRAFFIC_ENABLED — no remote agents,
    # no live deployment dashboard, no live attack runtime control. Full
    # variant (default) keeps it on.
    if [[ "${BUILD_VARIANT:-full}" == "pcap-only" ]]; then
        LIVE_TRAFFIC_DEFAULT="false"
    else
        LIVE_TRAFFIC_DEFAULT="true"
    fi

    # Pin the stack's bridge subnet to a /24 this host does not already route.
    # Writing the documented default blindly would hand a VPN'd laptop a value
    # that is broken on arrival, which is the failure this pin exists to remove.
    COMPOSE_SUBNET_VALUE=""
    if command -v ip >/dev/null 2>&1; then
        for cand in 10.200.0.0/24 10.201.0.0/24 10.202.0.0/24 192.168.243.0/24; do
            if ! ip -4 route show "${cand}" 2>/dev/null | grep -q .; then
                COMPOSE_SUBNET_VALUE="${cand}"; break
            fi
        done
        if [[ -z "${COMPOSE_SUBNET_VALUE}" ]]; then
            COMPOSE_SUBNET_VALUE="10.200.0.0/24"
            echo "WARNING: every candidate COMPOSE_SUBNET is already routed on this host."
            echo "         Wrote ${COMPOSE_SUBNET_VALUE}; pick a free /24 in ${ENV_FILE} before starting."
        elif [[ "${COMPOSE_SUBNET_VALUE}" != "10.200.0.0/24" ]]; then
            echo "  10.200.0.0/24 is routed here; using ${COMPOSE_SUBNET_VALUE} for the stack network."
        fi
    else
        COMPOSE_SUBNET_VALUE="10.200.0.0/24"
        echo "  iproute2 not found; using the default COMPOSE_SUBNET ${COMPOSE_SUBNET_VALUE} unchecked."
    fi

    cat > "${ENV_FILE}" <<EOF
# Generated by install.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ).
# Treat this file like any other secret material.

POSTGRES_PASSWORD=${POSTGRES_PW}
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
# ADMIN_PASSWORD is intentionally unset for fresh installs. The first-run
# setup wizard at https://<server>/ creates the admin account. Setting it
# here is a legacy bootstrap path — leave blank unless you really want
# env-driven admin creation.
ADMIN_PASSWORD=

# Feature flags
AI_ENABLED=false
LIVE_TRAFFIC_ENABLED=${LIVE_TRAFFIC_DEFAULT}

# Offline bundles ship the agent image (loaded above) and re-serve it on boot,
# so don't reach out to the registry — this install may be air-gapped. An
# internet-connected site can set this true to auto-pull agent updates from GHCR.
AGENT_REGISTRY_PULL_ENABLED=false

# Build metadata (read by backend for /api/v1/about)
BUILD_COMMIT=${BUILD_COMMIT}
BUILD_DATE=${BUILD_DATE}

# Subnet for the stack's own bridge network. Pinned rather than taken from
# Docker's default pools (172.17-172.31.0.0/16): a VPN/site route overlapping
# those pools makes the stack come up and STILL be unreachable from the host,
# and can break Docker's embedded DNS so nginx stops resolving `backend`.
# A change here needs the network recreated: docker compose down && up -d
COMPOSE_SUBNET=${COMPOSE_SUBNET_VALUE}

# Debug off in production
DEBUG=false
EOF
    chmod 600 "${ENV_FILE}"
    GENERATED_FRESH=1

    # Postgres applies POSTGRES_PASSWORD only when it initialises an EMPTY data
    # directory. A data volume that outlived the .env we just replaced keeps its
    # ORIGINAL password, so the backend crashloops on "password authentication
    # failed" while postgres still reports healthy (pg_isready never
    # authenticates). Warn at the point the mismatch is created.
    PGVOL="$(basename "${INSTALL_DIR}")_postgres_data"
    if docker volume inspect "${PGVOL}" >/dev/null 2>&1; then
        echo ""
        echo "  !! An existing database volume was found: ${PGVOL}"
        echo "     The .env just written has a NEW POSTGRES_PASSWORD, which that"
        echo "     volume will NOT accept. Left alone the backend will crashloop"
        echo "     while postgres reports healthy."
        echo ""
        echo "     Keep the existing database:  ./fix-db-password.sh"
        echo "     Discard it and start clean:  docker volume rm ${PGVOL}   (DELETES ALL DATA)"
        echo ""
        DB_VOLUME_PREEXISTED=1
    fi
fi

# --- bring it up --------------------------------------------------------
echo "[4/5] Starting stack..."
cd "${INSTALL_DIR}"

# Clear out any previous attempt's containers before starting. Requested by the
# first outside installer, who re-attempted over two weeks and kept inheriting
# state from the runs before.
#
# It is not just tidiness. `docker compose up -d` does NOT fully recreate a
# stack that is already running: it reuses containers whose definition has not
# changed, and when the NETWORK definition has changed it recreates the network
# and REATTACHES those containers to it -- without their compose service-name
# aliases. The subnet is pinned as of v1.21.0, so this is exactly what a re-run
# over an older attempt hits: right subnet, everything attached and running,
# and `postgres` no longer resolving. (Measured on Docker 29; see DEPLOY.md.)
#
# CONTAINERS AND THE NETWORK ONLY -- never `-v`, never the volumes. The
# database lives in a volume, and a re-run of an installer is a routine thing
# to do on a working site. A pre-existing volume whose password no longer
# matches a regenerated .env is handled separately and deliberately, by telling
# the operator and handing them fix-db-password.sh, because silently deleting
# someone's database is not a thing an installer should do.
# This runs in --upgrade mode too, and should: an upgrade wants every container
# recreated from the newly loaded images, which is precisely what `up -d` alone
# does not guarantee.
if [[ -n "$(docker compose --env-file .env ps -aq 2>/dev/null)" ]]; then
    echo "  containers from a previous run are present:"
    docker compose --env-file .env ps -a --format '    {{.Name}}\t{{.Status}}' 2>/dev/null || true
    echo "  removing them (data volumes are NOT touched)"
    docker compose --env-file .env down --remove-orphans \
      || echo "  compose down reported an error; continuing" >&2
fi

docker compose --env-file .env up -d

if [[ "${DB_VOLUME_PREEXISTED:-0}" -eq 1 ]]; then
    echo "  NOTE: the pre-existing database volume still has its old password;"
    echo "        the backend will not become healthy until you run ./fix-db-password.sh"
fi

echo "[5/5] Waiting for backend healthcheck..."
for i in $(seq 1 30); do
    if docker compose ps backend 2>/dev/null | grep -q "healthy"; then
        echo "  backend healthy after ${i}0s."
        break
    fi
    sleep 10
    [[ $i -eq 30 ]] && echo "  backend not yet healthy after 5 minutes — check \`docker compose logs backend\`" >&2
done

SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo ""
echo "================================================================"
echo "  PacketArch installed at ${INSTALL_DIR}"
if [[ "${GENERATED_FRESH:-0}" -eq 1 ]]; then
    echo ""
    echo "  *** ACTION REQUIRED: Complete first-run setup ***"
    echo ""
    echo "  Open:    https://${SERVER_IP}/"
    echo "           (accept the self-signed certificate)"
    echo ""
    echo "  You'll be guided through choosing your admin username and"
    echo "  password, naming the site, and (optionally) wiring up AI"
    echo "  + Cyber Vision."
    echo ""
    echo "  IMPORTANT: setup is unprotected — the first person who"
    echo "  reaches the URL becomes admin. Complete it BEFORE anyone"
    echo "  else can browse to this server."
else
    echo ""
    echo "  Existing install detected. Log in normally at https://${SERVER_IP}/."
fi
echo ""
echo "  Logs:    docker compose -f ${INSTALL_DIR}/docker-compose.yml logs -f"
echo "  Stop:    docker compose -f ${INSTALL_DIR}/docker-compose.yml down"
echo "================================================================"
