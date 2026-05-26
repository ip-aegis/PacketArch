#!/bin/bash
#
# PacketArch Server Initialization Script
# Run this ONCE on a new production server to set up GitHub-based deployments.
#
# Usage: curl -sSL https://raw.githubusercontent.com/YOUR_ORG/PacketArch/main/scripts/server-init.sh | bash
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

# Step 4: Create .env file
info "Step 4/5: Creating .env file..."
if [ ! -f .env ]; then
    # Generate secure random values
    SECRET_KEY=$(openssl rand -hex 32)
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
    # Fernet key (url-safe base64 of 32 bytes) — persists encrypted settings
    # (CV token, AI keys) across restarts. Without it they'd break on reboot.
    ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
    # Match the host docker group so the backend can use the Docker socket.
    DOCKER_GID=$(getent group docker | cut -d: -f3)

    cat > .env << ENVEOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
DOCKER_GID=${DOCKER_GID}
DEBUG=false
ENVEOF

    chmod 600 .env
    info ".env created with secure random values"
else
    info ".env already exists, skipping"
fi

# Step 5: Build and start
info "Step 5/5: Building and starting containers..."
sudo docker compose up -d --build

# Wait for startup
info "Waiting for services to start..."
sleep 20

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
