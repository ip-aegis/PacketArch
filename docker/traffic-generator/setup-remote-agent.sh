#!/bin/bash
# PacketArch Remote Traffic Agent Setup Script
# Run this on the remote Docker host (10.10.20.113)

set -e

echo "=========================================="
echo "PacketArch Remote Traffic Agent Setup"
echo "=========================================="

# Step 1: Install Docker
echo ""
echo "[1/5] Installing Docker..."
if command -v docker &> /dev/null; then
    echo "Docker is already installed: $(docker --version)"
else
    # Install Docker using the official convenience script
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh

    # Add current user to docker group
    sudo usermod -aG docker $USER
    echo "Docker installed. You may need to log out and back in for group changes."
fi

# Step 2: Start and enable Docker service
echo ""
echo "[2/5] Enabling Docker service..."
sudo systemctl enable docker
sudo systemctl start docker

# Step 3: Configure Docker for remote API access (no TLS - lab setup)
echo ""
echo "[3/5] Configuring Docker for remote API access..."

# Create daemon.json
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
EOF

# Create systemd override to prevent conflict
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf > /dev/null << 'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
EOF

# Reload and restart Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# Step 4: Configure firewall
echo ""
echo "[4/5] Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 2375/tcp
    echo "UFW: Port 2375 allowed"
else
    echo "UFW not installed, skipping firewall config"
fi

# Step 5: Create traffic generator directory
echo ""
echo "[5/5] Setting up traffic generator..."
mkdir -p ~/traffic-generator/app

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy the traffic generator files from PacketArch server"
echo "2. Build the Docker image"
echo "3. Configure the Docker host in PacketArch UI"
echo ""
echo "Verify Docker API is accessible:"
echo "  curl http://localhost:2375/version"
echo ""
echo "List network interfaces:"
ip link show | grep -E '^[0-9]+:' | awk -F: '{print $2}' | tr -d ' '
