# PacketArch

**OT Traffic Simulation Platform** - Generate realistic industrial protocol traffic for security testing, sensor validation, and network simulation.

## Overview

PacketArch is a web-based platform for creating and deploying OT (Operational Technology) network traffic scenarios. Design industrial networks visually, generate protocol-accurate PCAP files, and deploy live traffic to remote Docker hosts for real-world testing.

### Key Features

- **Visual Scenario Studio** - Drag-and-drop canvas for designing OT networks with devices and protocol flows
- **AI-Powered Design** - Natural language scenario generation using Claude AI
- **Protocol Engines** - Modbus TCP, EtherNet/IP, PROFINET with realistic timing and state machines
- **PCAP Learning** - Analyze existing captures to extract device fingerprints and traffic patterns
- **Live Traffic Injection** - Deploy scenarios to remote Docker hosts for real network testing
- **Industry Templates** - Pre-built scenarios for Manufacturing, Water/Wastewater, Energy, and Oil & Gas
- **Anomaly Injection** - Add protocol violations and timing anomalies for security testing

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ with Poetry
- Node.js 18+ with pnpm

### Development Setup

```bash
# Clone the repository
git clone git@github.com:kingsmanrocky-max/PacketArch.git
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
│  │  Protocol   │  │   Traffic   │  │   Docker Host       │  │
│  │  Engines    │  │  Generator  │  │   Management        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────────┐
        │PostgreSQL│   │  Redis   │   │ Docker Hosts │
        └──────────┘   └──────────┘   └──────────────┘
```

## Supported Protocols

| Protocol | Port | Status |
|----------|------|--------|
| Modbus TCP | 502 | Implemented |
| EtherNet/IP | 44818 | Implemented |
| PROFINET | Layer 2 | Implemented |
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
| `/api/v1/docker-hosts` | Remote Docker host management |
| `/api/v1/ai/chat` | AI-powered scenario design |
| `/api/v1/learning` | PCAP analysis and learning |
| `/api/v1/ip-management` | IP range allocation |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing key | (generate for production) |
| `ENCRYPTION_KEY` | Key for encrypting stored secrets | (auto-generated) |
| `FIRST_USER_PASSWORD` | Initial admin password | `changeme123` |

### Docker Host Setup

To deploy traffic generators to remote hosts:

1. Install Docker Engine on the target host
2. Configure TLS certificates for secure API access
3. Open port 2376 in the firewall
4. Add the host in PacketArch: **Settings > Docker Hosts**

See the in-app setup guide for detailed instructions.

## Project Structure

```
PacketArch/
├── backend/                 # FastAPI REST API
│   ├── app/
│   │   ├── api/routes/     # API endpoints
│   │   ├── protocol_engines/ # OT protocol implementations
│   │   ├── traffic_generator/ # PCAP generation
│   │   ├── ai_services/    # AI scenario generation
│   │   └── mcp_server/     # AI tool integration
│   └── alembic/            # Database migrations
├── frontend/               # React + Vite SPA
│   └── src/
│       ├── components/     # UI components
│       ├── pages/          # Route pages
│       └── stores/         # Zustand state management
├── docker/                 # Docker Compose configs
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

Proprietary - All rights reserved.

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/kingsmanrocky-max/PacketArch/issues) page.
