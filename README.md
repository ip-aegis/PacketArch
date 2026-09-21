# PacketArch

**OT Traffic Simulation Platform** - Generate realistic industrial protocol traffic for security testing, sensor validation, and network simulation.

## Overview

PacketArch is a web-based platform for creating and deploying OT (Operational Technology) network traffic scenarios. Design industrial networks visually, generate protocol-accurate PCAP files, and deploy live traffic via remote traffic agents for real-world testing.

### Key Features

- **Visual Scenario Studio** - Drag-and-drop canvas for designing OT networks with devices and protocol flows
- **AI-Powered Design** - Natural language scenario generation using Claude AI
- **Protocol Engines** - Modbus TCP, EtherNet/IP, PROFINET, S7comm, BACnet, SNMP with realistic timing and state machines
- **Device Templates** - Unified fingerprint system for vendor-accurate device emulation
- **Live Traffic Injection** - Deploy scenarios to remote traffic agents via WebSocket for real network testing
- **Remote Agent Management** - Central versioning, updates, and monitoring of distributed traffic agents
- **Industry Templates** - Pre-built scenarios for Manufacturing, Water/Wastewater, Energy, Oil & Gas, Building Automation, and Transportation
- **Anomaly Injection** - Add protocol violations and timing anomalies for security testing
- **Cisco Cyber Vision Integration** - Compare simulated devices against real-world discoveries

## Quick Start

The fastest way to a working install is the full Docker stack — it builds
everything from source and needs nothing on the host but Docker.

```bash
git clone https://github.com/ip-aegis/PacketArch.git ~/packetarch
cd ~/packetarch

# Minimum .env — see DEPLOY.md for the full table
cat > .env <<EOF
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
DOCKER_GID=$(getent group docker | cut -d: -f3)
HOST_INSTALL_DIR=$(pwd)
COMPOSE_PROJECT_NAME=packetarch
COMPOSE_SUBNET=10.200.0.0/24
DEBUG=false
EOF
chmod 600 .env

docker compose up -d --build
```

Then open `https://<server-ip>/` and complete the first-run **setup wizard**,
which creates the admin account and names the site. The certificate is
self-signed by default, so expect a browser trust warning.

**See [DEPLOY.md](DEPLOY.md) for the complete deployment runbook** — prerequisites,
firewall requirements, TLS certificates, upgrades, backup/restore and
troubleshooting.

### Prerequisites

- **Docker Engine + Compose plugin** — the only requirement for the stack above.
- For local development outside Docker: **Python 3.11+ with Poetry** and
  **Node.js 18+**.

### Development Setup

Run Postgres and Redis in Docker, and the backend/frontend on the host with
live reload:

```bash
git clone https://github.com/ip-aegis/PacketArch.git
cd PacketArch

# Dev .env. The password must match the backend's default DATABASE_URL.
# ⚠️ This OVERWRITES .env — never run it in a directory that holds a real
# install. Postgres fixes its password when the data volume is first created,
# so changing it later gives authentication failures against existing data.
cat > .env <<'EOF'
POSTGRES_PASSWORD=packetarch_dev
SECRET_KEY=dev-secret-not-for-production
EOF

# Start only the backing services from the root compose file
docker compose up -d postgres redis

# Backend (terminal 1)
cd backend
poetry install
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Frontend (terminal 2)
cd frontend
pnpm install
pnpm dev
```

Frontend on `http://localhost:3001`, backend on `http://localhost:8001`.

> **Two package managers are in play.** CI (`.github/workflows/ci.yml`) and local
> development use **pnpm 10** against the root `pnpm-workspace.yaml` /
> `pnpm-lock.yaml`. The production image build (`frontend/Dockerfile`) uses
> **`npm ci`** against `frontend/package-lock.json`. Use pnpm for development so
> you match CI; be aware the shipped image resolves from the other lockfile.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Scenario   │  │   Device    │  │   AI Assistant      │  │
│  │   Studio    │  │   Library   │  │   (Claude)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Protocol   │  │   Traffic   │  │   Agent Manager     │  │
│  │  Engines    │  │  Generator  │  │   (WebSocket Hub)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────────────┐
        │PostgreSQL│   │  Redis   │   │  Traffic Agents  │
        └──────────┘   └──────────┘   │  (WebSocket)     │
                                      └──────────────────┘
```

### Traffic Agent Architecture

Remote traffic agents connect to PacketArch via WebSocket (no inbound ports required on agent hosts):

```
PacketArch Server
       ▲
       │ WebSocket (wss://)
       │ Agent initiates connection
       ▼
┌─────────────────┐     ┌─────────────────┐
│  Agent Host 1   │     │  Agent Host N   │
│  - agent        │ ... │  - agent        │
│  - watchtower   │     │  - watchtower   │
└─────────────────┘     └─────────────────┘
```

## Supported Protocols

| Protocol | Port | Status |
|----------|------|--------|
| Modbus TCP | 502 (TCP) | Production |
| EtherNet/IP | 44818 (TCP) | Production |
| PROFINET | Layer 2 (EtherType 0x8892); 34964 (UDP) for DCE/RPC AR setup | Production |
| S7comm | 102 (TCP, ISO-on-TCP) | Production |
| BACnet/IP | 47808 (UDP) | Production |
| SNMP/NTCIP | 161 (UDP), 162 (UDP traps) | Production |
| DNP3 | 20000 (TCP) | Production |
| IEC 60870-5-104 | 2404 (TCP) | Production |
| IEC 61850 (MMS/GOOSE/SV) | 102 (TCP) / Layer 2 | Production |
| C37.118 (synchrophasor) | 4712 (TCP), 4713 (UDP) | Production |
| OPC UA | 4840 (TCP) | Production |
| EMP (ITC/PTC train control) | 3001 (TCP) — installation-configured, no universal port | Production |
| ATCS (AAR MSRP K-II codeline) | 4802 (TCP relay control) + 30000+ (UDP feed) | Production |

Additional engines: PCCC (2222 TCP legacy, or tunnelled over EtherNet/IP), FINS
(9600), SLMP (5007), CODESYS (1217), FOCAS (8193). Remote-access shapes
(SSH/Telnet/RDP/HTTPS) share the CloudServiceEngine for TCP+TLS heartbeats.

Ports above are the defaults from `PROTOCOL_DEFAULT_PORTS` in
`backend/app/protocol_engines/protocols.py`; most are overridable per flow.

## API Documentation

Interactive API documentation (Swagger UI) is served at `/api/docs`, with ReDoc at
`/api/redoc` and the schema at `/api/openapi.json`.

> **These are enabled only when `DEBUG=true`** (`backend/app/main.py:82-84`).
> Production installs set `DEBUG=false` — the documented default — which
> disables all three so an unauthenticated API schema is not exposed.
>
> **Don't flip `DEBUG=true` on a production box just to read the docs.** The
> same flag also switches logging to `DEBUG`, turns on SQLAlchemy `echo`
> (every query is logged), and returns raw exception text to API clients
> instead of a generic error. Read the schema on a dev instance instead.

The endpoint tables below are maintained by hand; `/api/openapi.json` on a
`DEBUG=true` instance is the authoritative list.

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/scenarios` | Scenario CRUD operations |
| `/api/v1/templates` | Industry templates |
| `/api/v1/agents` | Traffic agent management |
| `/api/v1/agents/build-image` | Build agent Docker image |
| `/api/v1/agents/{id}/update` | Trigger remote agent update |
| `/api/v1/ai/chat` | AI-powered scenario design |
| `/api/v1/ai/help` | AI-powered help system |
| `/api/v1/ip-management` | IP range allocation |
| `/api/v1/cyber-vision` | Cisco Cyber Vision integration |
| `/ws/agent` | WebSocket endpoint for traffic agents |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing key | (generate for production) |
| `ENCRYPTION_KEY` | Key for encrypting stored secrets | (auto-generated) |
| `ADMIN_PASSWORD` | Optional headless-install admin password. Leave unset to get the first-run setup wizard (recommended). Compose maps it to the backend's `FIRST_USER_PASSWORD`. | (unset → setup wizard) |
| `DOCKER_GID` | Host docker group id (`getent group docker \| cut -d: -f3`) | `987` |

### Traffic Agent Setup (Recommended)

Deploy traffic agents to remote hosts with one command:

```bash
curl -fsSLk https://your-server/agent/install.sh | sudo bash -s -- \
  --server https://your-server --token "your-agent-token" --insecure
```

**Features:**
- No inbound ports required (agent initiates WebSocket connection)
- Central versioning and updates from PacketArch UI
- Auto-updates via Watchtower
- Real-time status and metrics

See **Settings > Agents** in the UI for detailed instructions.

## Project Structure

```
PacketArch/
├── backend/                 # FastAPI REST API
│   ├── app/
│   │   ├── api/routes/     # API endpoints
│   │   ├── api/websocket/  # WebSocket endpoints (agent hub)
│   │   ├── protocol_engines/ # OT protocol implementations
│   │   ├── traffic_generator/ # PCAP generation
│   │   ├── services/       # Business logic (agent_manager, etc.)
│   │   ├── ai_services/    # AI scenario generation
│   │   └── mcp_server/     # AI tool integration
│   └── alembic/            # Database migrations
├── frontend/               # React + Vite SPA
│   └── src/
│       ├── components/     # UI components
│       ├── pages/          # Route pages
│       └── stores/         # Zustand state management
├── docker/                 # Docker Compose configs
│   └── packetarch-agent/   # Remote traffic agent
│       ├── app/            # Agent Python code
│       ├── Dockerfile      # Agent container image
│       └── install.sh      # One-command installer
└── docs/                   # Documentation
```

## Development

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines, including:

- Git workflow
- Port management
- Code standards
- Architecture patterns
- API reference

## License

PacketArch is free and open-source software, licensed under the
**GNU General Public License, version 3 (GPL-3.0)**. See [LICENSE](LICENSE)
for the full license text and [NOTICE](NOTICE) for copyright attributions.

PacketArch is developed and maintained by **Rocky Smith**
(<rocky.d.smith@proton.me>). Any redistribution of this software — modified
or unmodified — must preserve the copyright notices and license text, as
required by GPL-3.0.

Third-party components bundled with PacketArch are distributed under their
own respective licenses. See `THIRD_PARTY_LICENSES.md` (generated at release
time) for attributions.

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/ip-aegis/PacketArch/issues) page.
