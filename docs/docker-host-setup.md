# Remote Docker Host Setup Guide (Ubuntu)

This guide explains how to configure an Ubuntu server to accept remote Docker API connections for use with PacketArch traffic deployment.

## Prerequisites

- Ubuntu 20.04+ server
- Root or sudo access
- Docker installed (`apt install docker.io` or Docker CE)

---

## Option A: Simple Setup (No TLS) - Recommended for Lab

This is the quickest setup for isolated lab environments.

### Step 1: Configure Docker Daemon

```bash
sudo nano /etc/docker/daemon.json
```

Add:

```json
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
```

### Step 2: Fix Docker Service

```bash
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo nano /etc/systemd/system/docker.service.d/override.conf
```

Add:

```ini
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
```

### Step 3: Restart Docker

```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### Step 4: Open Firewall

```bash
sudo ufw allow 2375/tcp
```

### Step 5: Build Traffic Generator Image

```bash
cd /path/to/PacketArch/docker/traffic-generator
sudo docker build -t packetarch/traffic-generator:latest .
```

### Step 6: Configure in PacketArch

1. Go to **Settings > Docker Hosts**
2. Click **Add Docker Host**
3. Fill in:
   - **Name**: Lab Server
   - **Docker API URL**: `tcp://192.168.1.100:2375` (use your server's IP)
   - **TLS Enabled**: **Off**
   - **Default Interface**: `eth0` (or your interface name)
4. Click **Create**, then **Test Connection**

Done! That's all you need for a lab setup.

---

## Option B: Secure Setup (TLS) - For Production

For production or shared networks, use TLS authentication.

### Step 1: Create TLS Certificates

Run these commands on the **remote Docker host**:

```bash
# Create a directory for certificates
sudo mkdir -p /etc/docker/certs
cd /etc/docker/certs

# Set your Docker host's IP or hostname
HOST_IP="192.168.1.100"  # Change this to your server's IP

# Generate CA private key
sudo openssl genrsa -out ca-key.pem 4096

# Generate CA certificate (valid for 10 years)
sudo openssl req -new -x509 -days 3650 -key ca-key.pem -sha256 -out ca.pem \
  -subj "/CN=Docker CA"

# Generate server private key
sudo openssl genrsa -out server-key.pem 4096

# Generate server CSR
sudo openssl req -subj "/CN=$HOST_IP" -sha256 -new -key server-key.pem -out server.csr

# Create extensions file for server cert
echo "subjectAltName = DNS:localhost,IP:$HOST_IP,IP:127.0.0.1" | sudo tee extfile.cnf
echo "extendedKeyUsage = serverAuth" | sudo tee -a extfile.cnf

# Generate server certificate
sudo openssl x509 -req -days 3650 -sha256 -in server.csr -CA ca.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem -extfile extfile.cnf

# Generate client private key
sudo openssl genrsa -out client-key.pem 4096

# Generate client CSR
sudo openssl req -subj "/CN=client" -new -key client-key.pem -out client.csr

# Create extensions file for client cert
echo "extendedKeyUsage = clientAuth" | sudo tee extfile-client.cnf

# Generate client certificate
sudo openssl x509 -req -days 3650 -sha256 -in client.csr -CA ca.pem -CAkey ca-key.pem \
  -CAcreateserial -out client-cert.pem -extfile extfile-client.cnf

# Clean up CSR files
sudo rm -f server.csr client.csr extfile.cnf extfile-client.cnf

# Set proper permissions
sudo chmod 400 ca-key.pem server-key.pem client-key.pem
sudo chmod 444 ca.pem server-cert.pem client-cert.pem
```

## Step 2: Configure Docker Daemon

Create or edit the Docker daemon configuration:

```bash
sudo nano /etc/docker/daemon.json
```

Add the following content:

```json
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"],
  "tls": true,
  "tlscacert": "/etc/docker/certs/ca.pem",
  "tlscert": "/etc/docker/certs/server-cert.pem",
  "tlskey": "/etc/docker/certs/server-key.pem",
  "tlsverify": true
}
```

## Step 3: Fix Docker Service Configuration

The Docker systemd service needs adjustment to avoid conflicts with the hosts setting:

```bash
# Create override directory
sudo mkdir -p /etc/systemd/system/docker.service.d

# Create override file
sudo nano /etc/systemd/system/docker.service.d/override.conf
```

Add this content:

```ini
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
```

## Step 4: Restart Docker

```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

Verify Docker is listening on port 2376:

```bash
sudo ss -tlnp | grep 2376
```

You should see output like:
```
LISTEN  0  4096  *:2376  *:*  users:(("dockerd",pid=...))
```

## Step 5: Configure Firewall

Allow Docker API port through the firewall:

```bash
sudo ufw allow 2376/tcp
```

## Step 6: Copy Client Certificates

Copy these three files to your local machine (where PacketArch is running):

- `/etc/docker/certs/ca.pem` - CA Certificate
- `/etc/docker/certs/client-cert.pem` - Client Certificate
- `/etc/docker/certs/client-key.pem` - Client Key

You can use `scp` to copy them:

```bash
# Run this from your local machine
scp user@remote-host:/etc/docker/certs/ca.pem ./
scp user@remote-host:/etc/docker/certs/client-cert.pem ./
scp user@remote-host:/etc/docker/certs/client-key.pem ./
```

Or display them for copy-paste:

```bash
# On the remote host
sudo cat /etc/docker/certs/ca.pem
sudo cat /etc/docker/certs/client-cert.pem
sudo cat /etc/docker/certs/client-key.pem
```

## Step 7: Test Connection

Test the connection from your local machine:

```bash
docker --tlsverify \
  --tlscacert=ca.pem \
  --tlscert=client-cert.pem \
  --tlskey=client-key.pem \
  -H=tcp://192.168.1.100:2376 \
  info
```

## Step 8: Configure in PacketArch

1. Go to **Settings > Docker Hosts**
2. Click **Add Docker Host**
3. Fill in:
   - **Name**: A friendly name (e.g., "Lab Server")
   - **Docker API URL**: `tcp://192.168.1.100:2376`
   - **TLS Enabled**: On
   - **CA Certificate**: Paste contents of `ca.pem`
   - **Client Certificate**: Paste contents of `client-cert.pem`
   - **Client Key**: Paste contents of `client-key.pem`
   - **Default Interface**: The network interface for packet injection (e.g., `eth0`, `ens192`)
4. Click **Create**
5. Click the **Test Connection** button to verify

## Step 9: Build the Traffic Generator Image

On the remote Docker host, build the traffic generator image:

```bash
# Clone or copy the PacketArch repository to the remote host
cd /path/to/PacketArch/docker/traffic-generator

# Build the image
sudo docker build -t packetarch/traffic-generator:latest .
```

Or pull from a registry if you've published it.

## Troubleshooting

### Connection Refused
- Check firewall: `sudo ufw status`
- Check Docker is listening: `sudo ss -tlnp | grep 2376`
- Check Docker logs: `sudo journalctl -u docker -f`

### Certificate Errors
- Ensure the IP in the server certificate matches the connection IP
- Check certificate dates: `openssl x509 -in cert.pem -noout -dates`
- Verify CA chain: `openssl verify -CAfile ca.pem client-cert.pem`

### Permission Denied for Raw Sockets
The traffic generator container needs `NET_ADMIN` and `NET_RAW` capabilities. These are automatically added by PacketArch when deploying.

### Interface Not Found
List available interfaces on the remote host:
```bash
ip link show
```

Common interface names:
- `eth0`, `eth1` - Traditional naming
- `ens192`, `ens160` - VMware
- `enp0s3` - VirtualBox
- `eno1`, `eno2` - Onboard NICs

## Security Notes

- Keep the CA key (`ca-key.pem`) secure - it can sign new client certificates
- Client certificates grant full Docker API access - treat them like passwords
- Consider using a dedicated VLAN for OT traffic simulation
- The traffic generator runs with `--network host` mode for raw socket access
