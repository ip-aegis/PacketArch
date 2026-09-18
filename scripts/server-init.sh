#!/bin/bash
#
# PacketArch Server Initialization Script
# Run this ONCE on a new production server to set up GitHub-based deployments.
#
# Usage: curl -sSL https://raw.githubusercontent.com/ip-aegis/PacketArch/master/scripts/server-init.sh | bash
#    or: ./server-init.sh
#

set -e

echo "============================================"
echo "  PacketArch Server Initialization"
echo "============================================"

# Configuration (override via env vars if needed)
GITHUB_REPO="${GITHUB_REPO:-ip-aegis/PacketArch}"
BRANCH="${BRANCH:-master}"
INSTALL_DIR="$HOME/packetarch"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    error "Do not run as root. Run as a regular user with sudo privileges."
fi

# Prompt for GitHub repo if the default placeholder is still in place
if [ "$GITHUB_REPO" = "ORG/REPO" ]; then
    read -p "Enter GitHub repository (org/repo): " GITHUB_REPO
fi

echo ""
info "Repository: $GITHUB_REPO"
info "Branch: $BRANCH"
info "Install directory: $INSTALL_DIR"
echo ""

# Step 1: Install Docker if needed
info "Step 1/5: Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    info "Installing Docker..."

    sudo apt-get update -qq
    sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release

    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    sudo usermod -aG docker $USER
    info "Docker installed. You may need to log out and back in for group changes."
else
    info "Docker already installed: $(docker --version)"
fi

# Step 2: Install Git if needed
info "Step 2/5: Checking Git installation..."
if ! command -v git &> /dev/null; then
    info "Installing Git..."
    sudo apt-get install -y git
else
    info "Git already installed: $(git --version)"
fi

# Step 3: Clone repository
info "Step 3/5: Cloning repository..."
if [ -d "$INSTALL_DIR" ]; then
    warn "Directory $INSTALL_DIR already exists."
    read -p "Remove and re-clone? (y/n): " confirm
    if [ "$confirm" = "y" ]; then
        rm -rf "$INSTALL_DIR"
    else
        info "Keeping existing directory. Pulling latest..."
        cd "$INSTALL_DIR"
        git fetch origin
        git reset --hard origin/$BRANCH
    fi
fi

if [ ! -d "$INSTALL_DIR" ]; then
    git clone "https://github.com/$GITHUB_REPO.git" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    git checkout "$BRANCH"
fi

cd "$INSTALL_DIR"


# --- volume/.env desync preflight ------------------------------------------
# Postgres applies POSTGRES_PASSWORD only when it initialises an EMPTY data
# directory. If the data volume outlives the .env we are about to generate, the
# volume keeps its ORIGINAL password and the backend crashloops on
# "password authentication failed" — while postgres still reports healthy,
# because pg_isready never authenticates. Catch it here instead.
check_db_volume_desync() {
    local vol="${COMPOSE_PROJECT_NAME:-packetarch}_postgres_data"
    sudo docker volume inspect "$vol" >/dev/null 2>&1 || return 0

    warn "An existing database volume was found: ${vol}"
    warn "The .env just generated has a NEW random POSTGRES_PASSWORD, which that"
    warn "volume will NOT accept — postgres keeps the password it was built with."
    warn "Left alone, the backend will crashloop while postgres reports healthy."
    echo ""
    warn "Two ways forward:"
    warn "  KEEP the existing database  -> ./scripts/fix-db-password.sh"
    warn "     (realigns the role's password with the new .env; data preserved)"
    warn "  DISCARD it and start clean  -> sudo docker volume rm ${vol}"
    warn "     (DELETES every scenario, PCAP and user in that database)"
    echo ""
    DB_VOLUME_PREEXISTED=1
}

# Step 4: Create .env file
info "Step 4/5: Creating .env file..."
if [ ! -f .env ]; then
    # Generate secure random values
    SECRET_KEY=$(openssl rand -hex 32)
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    # Fernet key (url-safe base64 of 32 bytes) — persists encrypted settings
    # (CV token, AI keys) across restarts. Without it they'd break on reboot.
    ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
    # Match the host docker group so the backend can use the Docker socket.
    DOCKER_GID=$(getent group docker | cut -d: -f3)

    cat > .env << ENVEOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
DOCKER_GID=${DOCKER_GID}
DEBUG=false
# Self-upgrade (one-button UI upgrade): this install's host path + pinned
# compose project name so the updater container targets the right repo/project.
HOST_INSTALL_DIR=${INSTALL_DIR}
COMPOSE_PROJECT_NAME=packetarch
# Build-time network for image builds. Leave unset on a healthy host.
# Set to host ONLY if this host's bridged container egress is broken and
# you cannot fix /etc/docker/daemon.json — see ./scripts/check-docker-egress.sh.
# Keep it HERE rather than editing docker-compose.yml: .env is untracked, so
# the self-upgrade won't stash your change away and fail the next rebuild.
# DOCKER_BUILD_NETWORK=host
# ADMIN_PASSWORD unset => first boot shows the setup wizard (create admin there).
# Uncomment + set for a headless install that auto-creates admin and skips it:
# ADMIN_PASSWORD=changeme
ENVEOF

    chmod 600 .env
    info ".env created with secure random values"
    # A fresh .env means a fresh password — which an older volume will reject.
    check_db_volume_desync
else
    info ".env already exists, skipping"
fi

# Step 5: Build and start
# Every image runs network-touching steps (poetry/pip, apt-get, npm ci, apk) in
# a BRIDGED build sandbox, so a host with fine internet can still fail every
# build. Diagnose that up front instead of surfacing a raw pip/npm error.
if [ -x ./scripts/check-docker-egress.sh ]; then
    info "Step 5/5: Checking Docker egress before building..."
    if ! ./scripts/check-docker-egress.sh; then
        warn "Egress problems found (see above)."
        warn "Fixing /etc/docker/daemon.json is the durable answer — three of the"
        warn "four causes also break RUNTIME egress (Cyber Vision, CML, AI providers)."
        # server-init.sh is documented as `curl ... | bash`, where stdin is
        # the SCRIPT, not a terminal. A `read` there hits EOF, returns
        # non-zero, and under `set -e` would abort the whole install. Only
        # prompt on a real TTY, and never let the read itself be fatal.
        use_host_net=""
        if [ -t 0 ]; then
            read -p "Build anyway with DOCKER_BUILD_NETWORK=host as a stopgap? (y/n): " use_host_net || use_host_net=""
        else
            warn "Non-interactive install — not enabling the stopgap automatically."
            warn "If the build fails: echo 'DOCKER_BUILD_NETWORK=host' >> .env && docker compose up -d --build"
        fi
        if [ "$use_host_net" = "y" ]; then
            if grep -q '^DOCKER_BUILD_NETWORK=' .env; then
                sed -i 's/^DOCKER_BUILD_NETWORK=.*/DOCKER_BUILD_NETWORK=host/' .env
            else
                echo 'DOCKER_BUILD_NETWORK=host' >> .env
            fi
            warn "DOCKER_BUILD_NETWORK=host written to .env (build-time only)."
            warn "Remove it once the host is fixed."
        fi
    fi
fi

info "Building and starting containers..."
sudo docker compose up -d --build

# Wait for startup
info "Waiting for services to start..."
sleep 20

# A pre-existing volume rejects the freshly generated password (see
# check_db_volume_desync). Offer the non-destructive repair rather than leaving
# the operator with a crashlooping backend and four green healthchecks.
if [ "${DB_VOLUME_PREEXISTED:-0}" = "1" ]; then
    warn "The database volume predates this .env — the backend cannot authenticate yet."
    if [ -t 0 ]; then
        read -p "Realign the database password with the new .env now? (y/n): " fix_db || fix_db=""
        if [ "$fix_db" = "y" ]; then
            ./scripts/fix-db-password.sh || warn "fix-db-password.sh failed — run it manually."
        else
            warn "Skipped. Run ./scripts/fix-db-password.sh when ready."
        fi
    else
        warn "Non-interactive install — not changing the database password automatically."
        warn "Run this to finish:  ./scripts/fix-db-password.sh"
    fi
fi

# Show status
echo ""
echo "============================================"
echo "  Container Status"
echo "============================================"
sudo docker compose ps

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "Access URLs (HTTPS on 443, self-signed cert):"
echo "  Frontend:  https://${SERVER_IP}/"
echo "  API Docs:  https://${SERVER_IP}/api/docs"
echo ""
echo "First boot lands on the setup wizard — create the admin there."
echo "(ADMIN_PASSWORD in .env is the fallback for automated harnesses.)"
echo ""
echo "Off-box access: open inbound 443 (and 80) in your cloud/network firewall."
echo ""
echo "GitHub Actions Secrets Required:"
echo "  SSH_HOST:          ${SERVER_IP}"
echo "  SSH_USER:          ${USER}"
echo "  SSH_PRIVATE_KEY:   (your SSH private key)"
echo "  POSTGRES_PASSWORD: (from .env file)"
echo "  SECRET_KEY:        (from .env file)"
echo "  ADMIN_PASSWORD:    (from .env file)"
echo ""
echo "To view .env values: cat $INSTALL_DIR/.env"
echo ""
