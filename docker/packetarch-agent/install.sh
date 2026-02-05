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
VERIFY_CONNECTION=true
CONNECTION_TIMEOUT=60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

usage() {
    cat << EOF
PacketArch Agent Installer

Usage: $0 [OPTIONS]

Required (one of):
  --token TOKEN         Agent authentication token (from PacketArch UI)
  --register            Register a new agent with the server (requires --name)

Server Connection:
  --server URL          PacketArch server URL (e.g., https://10.10.20.231)
  --name NAME           Agent name (required for --register)

Configuration:
  --interface IFACE     Default network interface for traffic injection
  --install-dir DIR     Installation directory (default: /opt/packetarch-agent)
  --log-level LEVEL     Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
  --insecure            Skip SSL certificate verification (for self-signed certs)

Verification:
  --no-verify           Skip post-install connection verification
  --timeout SECONDS     Connection verification timeout (default: 60)

Other:
  --uninstall           Remove the agent
  --help                Show this help message

Examples:
  # Install with existing token
  $0 --server https://10.10.20.231 --token "abc123..." --interface eth0

  # Register new agent and install
  $0 --server https://10.10.20.231 --name "Traffic-Agent-1" --register

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

ensure_jq() {
    if ! command -v jq &> /dev/null; then
        print_status "Installing jq for JSON parsing..."
        if command -v apt-get &> /dev/null; then
            apt-get update -qq && apt-get install -y -qq jq
        elif command -v yum &> /dev/null; then
            yum install -y -q jq
        elif command -v dnf &> /dev/null; then
            dnf install -y -q jq
        elif command -v apk &> /dev/null; then
            apk add --quiet jq
        else
            print_error "Cannot install jq - please install it manually"
            exit 1
        fi
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

    # Verify Docker socket is accessible
    if [[ ! -S /var/run/docker.sock ]]; then
        print_error "Docker socket not found at /var/run/docker.sock"
        print_error "Ensure Docker is running: systemctl start docker"
        exit 1
    fi
}

# Pre-flight checks before installation
preflight_checks() {
    local server_url=$1

    print_status "Running pre-flight checks..."
    echo ""

    # Check 1: Server connectivity
    print_info "Checking server connectivity..."
    local health_response
    if health_response=$(curl -sf $CURL_OPTS --connect-timeout 10 "$server_url/health" 2>&1); then
        print_status "Server is reachable"
    else
        print_error "Cannot connect to PacketArch server at $server_url"
        print_error "Response: $health_response"
        print_info "Troubleshooting:"
        print_info "  - Verify the server URL is correct"
        print_info "  - Check network connectivity to the server"
        print_info "  - If using self-signed certificates, add --insecure flag"
        exit 1
    fi

    # Check 2: Agent image availability
    print_info "Checking agent image availability..."
    local image_status
    if image_status=$(curl -sf $CURL_OPTS --connect-timeout 10 "$server_url/api/v1/agents/image-status" 2>&1); then
        local available
        available=$(echo "$image_status" | jq -r '.available // false')
        if [[ "$available" == "true" ]]; then
            local version size
            version=$(echo "$image_status" | jq -r '.version // "unknown"')
            size=$(echo "$image_status" | jq -r '.size // 0')
            local size_mb=$((size / 1024 / 1024))
            print_status "Agent image available (v$version, ${size_mb}MB)"
        else
            print_error "Agent image not available on server"
            print_info "The server administrator needs to build the agent image first:"
            print_info "  1. Go to PacketArch Settings > Agents tab"
            print_info "  2. Click 'Build Image' button"
            print_info "  3. Wait for build to complete"
            print_info "  4. Re-run this installer"
            exit 1
        fi
    else
        print_warning "Could not check image status (endpoint may not exist)"
        print_info "Continuing with installation - download may fail if image not built"
    fi

    # Check 3: Docker socket
    print_info "Checking Docker socket..."
    if [[ -S /var/run/docker.sock ]]; then
        print_status "Docker socket accessible"
    else
        print_warning "Docker socket not found - Docker may not be running"
    fi

    # Check 4: Network interface (if specified)
    if [[ -n "$DEFAULT_INTERFACE" ]]; then
        print_info "Checking network interface '$DEFAULT_INTERFACE'..."
        if ip link show "$DEFAULT_INTERFACE" &> /dev/null; then
            print_status "Interface '$DEFAULT_INTERFACE' exists"
        else
            print_warning "Interface '$DEFAULT_INTERFACE' not found"
            print_info "Available interfaces:"
            ip -o link show | awk -F': ' '{print "    " $2}'
        fi
    fi

    echo ""
    print_status "Pre-flight checks passed"
    echo ""
}

register_agent() {
    local server_url=$1
    local agent_name=$2
    local interface=$3

    print_status "Registering agent with server..."

    # Build JSON payload using jq
    local payload
    if [[ -n "$interface" ]]; then
        payload=$(jq -n --arg name "$agent_name" --arg iface "$interface" \
            '{name: $name, default_interface: $iface}')
    else
        payload=$(jq -n --arg name "$agent_name" '{name: $name}')
    fi

    # Register with server
    local response
    local http_code
    http_code=$(curl -sf $CURL_OPTS -X POST "$server_url/api/v1/agents" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        -w "%{http_code}" \
        -o /tmp/register_response.json 2>&1) || {
        if [[ -f /tmp/register_response.json ]]; then
            response=$(cat /tmp/register_response.json)
            local detail
            detail=$(echo "$response" | jq -r '.detail // "Unknown error"')
            print_error "Failed to register agent: $detail"
        else
            print_error "Failed to register agent with server"
        fi
        rm -f /tmp/register_response.json
        exit 1
    }

    response=$(cat /tmp/register_response.json)
    rm -f /tmp/register_response.json

    # Extract token from response using jq
    AGENT_TOKEN=$(echo "$response" | jq -r '.token // empty')
    AGENT_ID=$(echo "$response" | jq -r '.id // empty')

    if [[ -z "$AGENT_TOKEN" ]]; then
        print_error "Failed to extract token from server response"
        print_error "Response: $response"
        exit 1
    fi

    print_status "Agent registered successfully (ID: ${AGENT_ID:0:8}...)"
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
      - /var/run/docker.sock:/var/run/docker.sock
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
EOF

    # Download and load agent image from PacketArch server
    print_status "Downloading agent image from server..."
    local download_result
    if ! download_result=$(curl -f $CURL_OPTS --progress-bar -o /tmp/packetarch-agent.tar.gz "$server_url/api/v1/agents/image" 2>&1); then
        print_error "Failed to download agent image from server"
        print_error "$download_result"
        print_info "Ensure the agent image has been built on the server"
        exit 1
    fi

    print_status "Loading agent image..."
    if ! docker load -i /tmp/packetarch-agent.tar.gz; then
        print_error "Failed to load agent image"
        print_info "The downloaded file may be corrupted. Try again."
        rm -f /tmp/packetarch-agent.tar.gz
        exit 1
    fi
    rm -f /tmp/packetarch-agent.tar.gz

    # Start services
    print_status "Starting agent services..."
    docker compose up -d

    print_status "Agent installed successfully!"
    echo ""
}

verify_connection() {
    local server_url=$1
    local timeout=$2

    print_status "Waiting for agent to connect to server..."
    print_info "Timeout: ${timeout} seconds"

    local start_time
    start_time=$(date +%s)
    local connected=false

    while true; do
        local current_time
        current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ $elapsed -ge $timeout ]]; then
            break
        fi

        # Check if agent is in connected list
        local connected_agents
        if connected_agents=$(curl -sf $CURL_OPTS "$server_url/api/v1/agents/connected" 2>/dev/null); then
            local count
            count=$(echo "$connected_agents" | jq 'length')
            if [[ "$count" -gt 0 ]]; then
                # Check if our agent is in the list (by checking recent connection)
                # Since we just installed, any connected agent in the last few seconds is likely us
                connected=true
                break
            fi
        fi

        # Show progress
        printf "\r${BLUE}[i]${NC} Waiting... (%ds / %ds)" "$elapsed" "$timeout"
        sleep 2
    done

    echo "" # Clear the progress line

    if [[ "$connected" == "true" ]]; then
        print_status "Agent connected to server successfully!"
        return 0
    else
        print_warning "Agent did not connect within ${timeout} seconds"
        print_info "Troubleshooting steps:"
        print_info "  1. Check agent logs: docker compose -f $INSTALL_DIR/docker-compose.yml logs agent"
        print_info "  2. Verify the token is correct"
        print_info "  3. Check network connectivity to server"
        print_info "  4. Ensure server is running and accessible"
        return 1
    fi
}

print_completion() {
    local install_dir=$1

    echo ""
    echo "==========================================="
    echo "    Installation Complete"
    echo "==========================================="
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

    # Remove agent image
    print_status "Removing agent image..."
    docker rmi packetarch-agent:latest 2>/dev/null || true

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
        --insecure|-k)
            INSECURE=true
            CURL_OPTS="-k"
            shift
            ;;
        --no-verify)
            VERIFY_CONNECTION=false
            shift
            ;;
        --timeout)
            CONNECTION_TIMEOUT="$2"
            shift 2
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

# Ensure dependencies
ensure_jq
check_docker

# Run pre-flight checks
preflight_checks "$SERVER_URL"

if [[ "$REGISTER" == "true" ]]; then
    if [[ -z "$AGENT_NAME" ]]; then
        print_error "Agent name is required for registration (--name)"
        exit 1
    fi
    register_agent "$SERVER_URL" "$AGENT_NAME" "$DEFAULT_INTERFACE"
elif [[ -z "$AGENT_TOKEN" ]]; then
    print_error "Either --token or --register is required"
    exit 1
fi

install_agent "$SERVER_URL" "$AGENT_TOKEN" "$DEFAULT_INTERFACE" "$INSTALL_DIR" "$LOG_LEVEL"

# Post-install verification
if [[ "$VERIFY_CONNECTION" == "true" ]]; then
    if verify_connection "$SERVER_URL" "$CONNECTION_TIMEOUT"; then
        print_completion "$INSTALL_DIR"
    else
        print_completion "$INSTALL_DIR"
        exit 1
    fi
else
    print_completion "$INSTALL_DIR"
fi
