#!/bin/bash
#
# PacketArch Agent Installer
#
# Installs the PacketArch remote traffic agent on a Linux host.
# The agent connects to the PacketArch server via WebSocket and
# executes traffic generation commands.
#
# Usage:
#   curl -fsSL https://packetarch-server/agent/install.sh | bash -s -- \
#     --server https://10.10.20.231 --token "your-agent-token"
#
# Or with agent registration:
#   curl -fsSL https://packetarch-server/agent/install.sh | bash -s -- \
#     --server https://10.10.20.231 --name "Agent-1" --register
#

set -e

# Default values
INSTALL_DIR="/opt/packetarch-agent"
IMAGE="ghcr.io/ip-aegis/packetarch-agent:latest"
LOG_LEVEL="INFO"
INSECURE=""
CURL_OPTS=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[x]${NC} $1"
}

usage() {
    cat << EOF
PacketArch Agent Installer

Usage: $0 [OPTIONS]

Recommended flow (token from UI):
  1. In the PacketArch UI: Settings → Agents → "Add Agent". Copy the
     one-time token shown after creation.
  2. Run this installer with --token "<that token>".

Required (one of):
  --token TOKEN         Agent authentication token (from PacketArch UI)
  --register            Register a new agent with the server
                        (requires --name AND --admin-token)
  --admin-token TOKEN   Admin bearer token used for --register. Get it from
                        the UI: open DevTools → Network → any API call →
                        copy the value of the Authorization header. Note
                        admin tokens are short-lived; run --register
                        promptly after generating one.

Server Connection:
  --server URL          PacketArch server URL (e.g., https://10.10.20.231)
  --name NAME           Agent name (required for --register)

Configuration:
  --interface IFACE     Default network interface for traffic injection
  --install-dir DIR     Installation directory (default: /opt/packetarch-agent)
  --log-level LEVEL     Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
  --insecure            Skip SSL certificate verification (for self-signed certs)

Other:
  --uninstall           Remove the agent
  --help                Show this help message

Examples:
  # Install with existing token (recommended — create the agent in the UI first)
  $0 --server https://10.10.20.231 --token "abc123..." --interface eth0

  # Register new agent inline (needs an admin bearer token)
  $0 --server https://10.10.20.231 --name "Traffic-Agent-1" --register \\
     --admin-token "eyJhbGciOi..."

  # Uninstall
  $0 --uninstall
EOF
    exit 0
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_status "Installing Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
    else
        print_status "Docker is already installed"
    fi
}

register_agent() {
    local server_url=$1
    local agent_name=$2
    local interface=$3

    print_status "Registering agent with server..."

    # Build JSON payload
    local payload="{\"name\": \"$agent_name\""
    if [[ -n "$interface" ]]; then
        payload+=", \"default_interface\": \"$interface\""
    fi
    payload+="}"

    # Register with server. /api/v1/agents is admin-gated as of PacketArch
    # 1.4.0, so --register requires --admin-token. (Pre-1.4 servers ignored
    # the Authorization header; this works against both.)
    if [[ -z "$ADMIN_TOKEN" ]]; then
        print_error "--register requires --admin-token (PacketArch 1.4+)."
        print_error "Either create the agent in the UI and re-run with --token,"
        print_error "or pass an admin bearer token via --admin-token."
        exit 1
    fi

    local response
    response=$(curl -sf $CURL_OPTS -X POST "$server_url/api/v1/agents" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -d "$payload" 2>&1) || {
        print_error "Failed to register agent with server"
        print_error "(401 usually means the --admin-token is expired — admin"
        print_error " tokens are short-lived; grab a fresh one from the UI.)"
        print_error "Response: $response"
        exit 1
    }

    # Extract token from response
    AGENT_TOKEN=$(echo "$response" | grep -oP '"token"\s*:\s*"\K[^"]+')

    if [[ -z "$AGENT_TOKEN" ]]; then
        print_error "Failed to extract token from server response"
        print_error "Response: $response"
        exit 1
    fi

    print_status "Agent registered successfully"
}

install_agent() {
    local server_url=$1
    local agent_token=$2
    local interface=$3
    local install_dir=$4
    local log_level=$5

    print_status "Installing PacketArch Agent..."

    # Create install directory
    mkdir -p "$install_dir"
    cd "$install_dir"

    # Create .env file
    print_status "Creating configuration..."
    cat > .env << EOF
PACKETARCH_SERVER=$server_url
AGENT_TOKEN=$agent_token
DEFAULT_INTERFACE=${interface:-eth0}
LOG_LEVEL=$log_level
SSL_VERIFY=${SSL_VERIFY:-true}
EOF

    # Set secure permissions
    chmod 600 .env

    # Create docker-compose.yml
    print_status "Creating docker-compose.yml..."
    cat > docker-compose.yml << 'EOF'
services:
  agent:
    image: packetarch-agent:latest
    container_name: packetarch-agent
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    env_file:
      - .env
    volumes:
      # Required for agent self-update (UPDATE_AGENT): the agent uses the
      # host Docker daemon to `docker load` the new image and restart
      # itself. Without this mount, updates fail with "Docker not available".
      - /var/run/docker.sock:/var/run/docker.sock
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
EOF

    # Download and load agent image from PacketArch server
    print_status "Downloading agent image from server..."
    curl -f $CURL_OPTS -o /tmp/packetarch-agent.tar.gz "$server_url/agent/image.tar.gz" || {
        print_error "Failed to download agent image from server"
        exit 1
    }

    print_status "Loading agent image..."
    gunzip -c /tmp/packetarch-agent.tar.gz | docker load || {
        print_error "Failed to load agent image"
        exit 1
    }
    rm -f /tmp/packetarch-agent.tar.gz

    # Tag the image with the local name
    docker tag ghcr.io/ip-aegis/packetarch-agent:latest packetarch-agent:latest 2>/dev/null || true

    # Start services
    print_status "Starting agent services..."
    docker compose up -d

    print_status "Agent installed successfully!"
    echo ""
    echo "Installation directory: $install_dir"
    echo ""
    echo "Useful commands:"
    echo "  View logs:     docker compose -f $install_dir/docker-compose.yml logs -f agent"
    echo "  Restart:       docker compose -f $install_dir/docker-compose.yml restart"
    echo "  Stop:          docker compose -f $install_dir/docker-compose.yml down"
    echo "  Uninstall:     $0 --uninstall"
    echo ""
}

uninstall_agent() {
    local install_dir=$1

    print_warning "Uninstalling PacketArch Agent..."

    if [[ -d "$install_dir" ]]; then
        cd "$install_dir"

        # Stop and remove containers
        if [[ -f docker-compose.yml ]]; then
            print_status "Stopping containers..."
            docker compose down --remove-orphans 2>/dev/null || true
        fi

        # Remove install directory
        print_status "Removing installation directory..."
        rm -rf "$install_dir"
    fi

    print_status "Agent uninstalled successfully"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)
            SERVER_URL="$2"
            shift 2
            ;;
        --token)
            AGENT_TOKEN="$2"
            shift 2
            ;;
        --name)
            AGENT_NAME="$2"
            shift 2
            ;;
        --interface)
            DEFAULT_INTERFACE="$2"
            shift 2
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --register)
            REGISTER=true
            shift
            ;;
        --admin-token)
            ADMIN_TOKEN="$2"
            shift 2
            ;;
        --insecure|-k)
            INSECURE=true
            CURL_OPTS="-k"
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Main logic
echo "==========================================="
echo "    PacketArch Agent Installer"
echo "==========================================="
echo ""

check_root

if [[ "$UNINSTALL" == "true" ]]; then
    uninstall_agent "$INSTALL_DIR"
    exit 0
fi

# Validate required arguments
if [[ -z "$SERVER_URL" ]]; then
    print_error "Server URL is required (--server)"
    exit 1
fi

# Remove trailing slash from server URL
SERVER_URL="${SERVER_URL%/}"

# Set SSL verification based on --insecure flag
if [[ "$INSECURE" == "true" ]]; then
    SSL_VERIFY="false"
    print_warning "SSL certificate verification disabled"
else
    SSL_VERIFY="true"
fi

if [[ "$REGISTER" == "true" ]]; then
    if [[ -z "$AGENT_NAME" ]]; then
        print_error "Agent name is required for registration (--name)"
        exit 1
    fi
    check_docker
    register_agent "$SERVER_URL" "$AGENT_NAME" "$DEFAULT_INTERFACE"
elif [[ -z "$AGENT_TOKEN" ]]; then
    print_error "Either --token or --register is required"
    exit 1
else
    check_docker
fi

install_agent "$SERVER_URL" "$AGENT_TOKEN" "$DEFAULT_INTERFACE" "$INSTALL_DIR" "$LOG_LEVEL"
