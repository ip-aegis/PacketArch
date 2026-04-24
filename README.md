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

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ with Poetry
- Node.js 18+ with pnpm

### Development Setup

```bash
# Clone the repository
git clone git@github.com:ip-aegis/PacketArch.git
cd PacketArch

# Start database and Redis
cd docker && docker-compose -f docker-compose.dev.yml up -d

# Install and start backend
cd ../backend
poetry install
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Install and start frontend (new terminal)
cd ../frontend
pnpm install
pnpm dev
```

Access the application at `http://localhost:3001`

### Production Deployment

```bash
# Build and start all containers
docker compose up -d --build

# Access at https://localhost (self-signed certificate)
```

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
| Modbus TCP | 502 | Production |
| EtherNet/IP | 44818 | Production |
| PROFINET | Layer 2 | Production |
| S7comm | 102 | Production |
| BACnet/IP | 47808 | Production |
| SNMP/NTCIP | 161 | Production |
| OPC UA | 4840 | Planned |
| DNP3 | 20000 | Planned |
| IEC 104 | 2404 | Planned |

## API Documentation

Interactive API documentation is available at `/api/docs` when the backend is running.

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
| `FIRST_USER_PASSWORD` | Initial admin password | (set in .env, required) |

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
