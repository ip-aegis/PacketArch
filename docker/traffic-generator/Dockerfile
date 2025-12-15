# PacketArch Traffic Generator Container
# Injects raw OT protocol packets onto a network interface

FROM python:3.12-slim

# Install system dependencies for Scapy raw sockets
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev \
    tcpdump \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Environment variables (set by deployment)
ENV SCENARIO_JSON=""
ENV NETWORK_INTERFACE="eth0"
ENV DURATION_MS="60000"
ENV DEPLOYMENT_ID=""

# Note: Running as root is required for raw socket access with Scapy sendp()
# The container still needs --cap-add NET_ADMIN --cap-add NET_RAW

# Entry point
ENTRYPOINT ["python", "-m", "app.entrypoint"]
