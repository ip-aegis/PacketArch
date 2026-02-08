# PacketArch Remote Traffic Agent
# WebSocket-based agent that connects to PacketArch server and executes traffic generation commands
#
# Before building, the build script stages shared backend code into _shared/:
#   _shared/protocol_engines/  — from backend/app/protocol_engines/
#   _shared/traffic_generator/  — selected files from backend/app/traffic_generator/

FROM python:3.12-slim

# Install system dependencies for Scapy raw sockets and Docker CLI for self-update
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev \
    tcpdump \
    iproute2 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (required for self-update via docker compose)
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.4.1.tgz | \
    tar -xz --strip-components=1 -C /usr/local/bin docker/docker && \
    chmod +x /usr/local/bin/docker

# Install docker-compose plugin
RUN mkdir -p /usr/local/lib/docker/cli-plugins && \
    curl -fsSL https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose && \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy shared protocol engines from backend (staged by build script).
# These provide all 23+ protocol implementations, identity builders,
# timing models, and the unified orchestrator for traffic generation.
COPY _shared/protocol_engines/ ./app/protocol_engines/
COPY _shared/traffic_generator/ ./app/traffic_generator/

# Environment variables (set by deployment)
ENV PACKETARCH_SERVER=""
ENV AGENT_TOKEN=""
ENV DEFAULT_INTERFACE="eth0"
ENV LOG_LEVEL="INFO"

# Note: Running as root is required for raw socket access with Scapy sendp()
# The container still needs --cap-add NET_ADMIN --cap-add NET_RAW

# Entry point
ENTRYPOINT ["python", "-m", "app.main"]
