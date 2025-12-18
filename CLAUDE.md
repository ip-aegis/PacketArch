# PacketArch Development Guidelines

## Repository

- **GitHub**: https://github.com/kingsmanrocky-max/PacketArch
- **Branch**: `master` (primary branch)
- **Clone**: `git clone git@github.com:kingsmanrocky-max/PacketArch.git`

### Git Workflow

```bash
# Pull latest changes
git pull origin master

# After making changes, commit and push
git add -A
git commit -m "Description of changes"
git push origin master
```

### SSH Key Setup

The server uses SSH authentication for GitHub. The SSH key is located at:
- Private: `~/.ssh/id_ed25519`
- Public: `~/.ssh/id_ed25519.pub`

If you need to set up on a new machine, add the public key to GitHub:
1. Copy the public key: `cat ~/.ssh/id_ed25519.pub`
2. Add to GitHub: Settings → SSH and GPG keys → New SSH key

---

## Off-Box Access

This application is configured for **off-box access** - meaning it can be accessed from other machines on the network, not just localhost.

### Network Binding
All services bind to `0.0.0.0` (all network interfaces):
- **Frontend (Vite)**: Configured in `vite.config.ts` with `host: '0.0.0.0'`
- **Backend (FastAPI)**: Configured in `config.py` with `api_host: '0.0.0.0'`
- **Docker services**: Ports bound to `0.0.0.0` in `docker-compose.dev.yml`

### Accessing from Another Machine
1. Find the host machine's IP address:
   ```powershell
   ipconfig  # Windows
   ip addr   # Linux
   ```
2. Access services using the IP:
   - Frontend: `http://<host-ip>:3001`
   - Backend API: `http://<host-ip>:8001`
   - API Docs: `http://<host-ip>:8001/api/docs`

### CORS Configuration
The backend allows CORS from:
- `http://localhost:3001`
- `http://localhost:5173`
- `http://*:3001` (any host on port 3001)
- `http://*:5173` (any host on port 5173)

To add specific origins, update `CORS_ORIGINS` in backend `.env` or `config.py`.

---

## Port Management

### CRITICAL: Always Check Ports Before Starting Services

Before starting any development services, ALWAYS check if the required ports are available.

**Windows Commands:**
```powershell
# Check specific port
netstat -ano | findstr :8001
netstat -ano | findstr :3001
netstat -ano | findstr :5432
netstat -ano | findstr :6379

# Kill process by PID (if needed)
taskkill /PID <pid> /F
```

**Linux/Mac Commands:**
```bash
# Check specific port
lsof -i :8001
lsof -i :3001
lsof -i :5432
lsof -i :6379

# Kill process by PID (if needed)
kill -9 <pid>
```

### Required Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend (FastAPI) | 8001 | REST API server |
| Frontend (Vite) | 3001 | React development server |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache and message broker |
| pgAdmin (optional) | 5050 | Database admin UI |

### Before Starting Development

1. **Check all ports are free:**
   ```powershell
   netstat -ano | findstr ":8001 :3001 :5432 :6379"
   ```

2. **If ports are in use, identify the process:**
   ```powershell
   # Get process name from PID
   tasklist /FI "PID eq <pid>"
   ```

3. **Decide whether to:**
   - Stop the conflicting process
   - Use alternative ports (update docker-compose and configs)

## Development Workflow

### Prerequisites

**Backend (Python):**
- Python 3.11+
- Poetry package manager
- Required dependencies in `pyproject.toml`:
  - `anthropic` - AI provider integration
  - `docker` - Docker API client for container management

**Frontend (Node.js):**
- Node.js 18+
- pnpm package manager

### First-Time Setup

1. **Install backend dependencies:**
   ```bash
   cd backend && poetry lock && poetry install
   ```

2. **Install frontend dependencies:**
   ```bash
   cd frontend && pnpm install
   ```

### Starting Services

1. Start Docker services first:
   ```bash
   cd docker && docker-compose -f docker-compose.dev.yml up -d
   ```

2. Start backend:
   ```bash
   cd backend && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

3. Start frontend:
   ```bash
   cd frontend && pnpm dev
   ```

### Windows-Specific Notes

If `poetry` is not in your PATH on Windows, use:
```powershell
python -m poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Stopping Services

```bash
# Stop Docker services
cd docker && docker-compose -f docker-compose.dev.yml down

# Frontend/Backend: Ctrl+C in their respective terminals
```

---

## Production Environment

### Overview
Development and production run on the same server (10.10.20.231). "Production" is the local Docker environment.

- **Server**: 10.10.20.231 (this machine)
- **User**: rocsmith
- **URL**: https://10.10.20.231
- **Credentials**: admin / PacketArch_Admin!
- **Working Directory**: `/home/rocsmith/packetarch`

### Architecture
- **HTTPS** on port 443 with self-signed SSL certificates
- **Nginx** reverse proxy terminates TLS and proxies API calls to backend
- **All traffic** (frontend + API) served through single HTTPS endpoint
- **Backend** not directly exposed (internal Docker network only)

### Deploying Changes

After making code changes, rebuild the affected container(s):

```bash
# Rebuild backend only (most common)
cd /home/rocsmith/packetarch && docker compose up -d --build backend

# Rebuild frontend only
cd /home/rocsmith/packetarch && docker compose up -d --build frontend

# Rebuild everything
cd /home/rocsmith/packetarch && docker compose up -d --build
```

### Container Management

```bash
# Check status
docker compose ps

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart services
docker compose restart

# Stop everything
docker compose down

# Start everything
docker compose up -d
```

### Production Ports

| Service | Internal Port | External Port | Notes |
|---------|---------------|---------------|-------|
| Frontend (nginx) | 443 | 443 | HTTPS with self-signed cert |
| Backend | 8001 | Not exposed | Accessed via nginx proxy |
| PostgreSQL | 5432 | 5432 | Database |
| Redis | 6379 | 6379 | Cache and message broker |

### SSL Certificate

Self-signed certificate auto-generated on first container start:
- **Location**: Docker volume `ssl_certs` → `/etc/nginx/ssl/`
- **Validity**: 365 days
- **Regenerate**: Delete volume and restart frontend container

```bash
# Force regenerate SSL cert
docker compose down && docker volume rm packetarch_ssl_certs && docker compose up -d
```

### Environment Variables

Production `.env` file (`/home/rocsmith/packetarch/.env`):
```
POSTGRES_PASSWORD=PacketArch_Prod_2024!
SECRET_KEY=<generated-secret>
ENCRYPTION_KEY=
ADMIN_PASSWORD=PacketArch_Admin!
DEBUG=false
```

---

## Remote Traffic Agent

A separate traffic injection host runs scenario traffic on the network.

### Agent Details
- **IP**: 10.10.20.113
- **User**: cisco / cisco
- **Docker Image**: `packetarch/traffic-generator:latest`
- **Code Location**: `/home/cisco/traffic-generator/`

### How It Works
1. PacketArch backend sends scenario data to the remote agent
2. Agent launches a Docker container with `packetarch/traffic-generator:latest`
3. Container runs `live_orchestrator.py` which injects packets onto the network interface
4. Cisco Cyber Vision (or other sensors) see the traffic and detect devices/vulnerabilities

### Updating the Agent

After modifying `live_orchestrator.py`, rebuild the Docker image:

```bash
# SSH to remote agent
ssh cisco@10.10.20.113

# Rebuild image
cd /home/cisco/traffic-generator
docker build -t packetarch/traffic-generator:latest .

# Restart any running containers (or restart scenario from PacketArch UI)
docker stop $(docker ps -q --filter "name=packetarch-generator")
```

### Key Files
- `app/live_orchestrator.py` - Main traffic generation logic
- `app/entrypoint.py` - Container entrypoint, receives scenario config
- `Dockerfile` - Container build definition

---

## Code Standards

- TypeScript strict mode for frontend
- Python type hints for backend
- All API endpoints documented with OpenAPI
- Pydantic schemas for all request/response models
- Zustand for frontend state management
- SQLAlchemy 2.0 async patterns for database

---

## Architecture Overview

PacketArch is an OT Traffic Simulation Platform with three main subsystems:

### 1. Scenario Studio (Frontend)
- **Canvas**: @xyflow/react for visual scenario building
- **DnD**: @dnd-kit for palette-to-canvas drag and drop
- **State**: Zustand stores (`scenarioStore`, `historyStore`, `aiAssistantStore`)
- **Styling**: Ant Design with Cisco-inspired dark theme

### 2. Traffic Generation (Backend)
- **Protocol Engines**: `backend/app/protocol_engines/` - Modbus, EtherNet/IP, PROFINET
- **Orchestrator**: `backend/app/traffic_generator/` - Coordinates engines, timing, PCAP output
- **Background Jobs**: Celery with Redis for long-running generation tasks
- **Output**: PCAP files in `./output/pcap/`

### 3. MCP/AI Integration
- **MCP Server**: `backend/app/mcp_server/` - JSON-RPC 2.0 tool server
- **AI Provider**: Anthropic Claude (API key in system settings)
- **Transport**: HTTP + Server-Sent Events

---

## Key Patterns

### Protocol Engine Pattern
All protocol engines extend `ProtocolEngine` base class:
- `generate_startup_sequence()` - Protocol initialization
- `generate_poll_cycle()` - Single request/response cycle
- `generate_shutdown_sequence()` - Clean disconnect

### State Machine Pattern
Use `python-statemachine` for stateful protocol conversations:
- Modbus: idle -> request_sent -> awaiting_response -> response_received
- EtherNet/IP: unconnected -> registered -> connected -> io_active
- PROFINET: power_on -> dcp_identify -> ar_establishing -> data_exchange

### Canvas Node/Edge Pattern
React Flow custom components:
- `DeviceNode` - OT devices with protocol handles
- `ZoneNode` - Resizable network zone containers
- `FlowEdge` - Protocol connections with color coding

---

## Supported Protocols

| Protocol | Port | Engine Status |
|----------|------|---------------|
| Modbus TCP | 502 | Priority 1 |
| EtherNet/IP | 44818 (TCP), 2222 (UDP) | Priority 2 |
| PROFINET | N/A (Layer 2) | Priority 3 |
| OPC UA | 4840 | Future |
| DNP3 | 20000 | Future |
| IEC 104 | 2404 | Future |

---

## Industry Verticals

- **Manufacturing**: High-speed Profinet/EtherNet/IP, PLCs, HMIs, drives
- **Water/Wastewater**: SCADA, RTUs, DNP3/Modbus polling
- **Energy/Power**: Substation RTUs, IEC-104, event bursts
- **Oil & Gas**: Pipeline SCADA, Modbus/OPC UA, sparse polling

---

## IP Management

PacketArch automatically assigns unique `/16` IP ranges to each scenario to prevent IP conflicts.

### How It Works
- Each scenario gets a unique range: `10.{n}.0.0/16` where n = 1-254
- IP ranges are auto-assigned on scenario creation (both manual and from templates)
- Devices auto-populate IPs from their scenario's range when added to the canvas
- The IP Management page (`/ip-management`) shows all allocations

### IP Assignment Logic
- Range: `10.{n}.0.0/16` where n = 1-254
- Hosts start at offset 10: `10.{n}.0.10`, `10.{n}.0.11`, etc.
- Subnets: `/24` within the `/16`, gateway is `.1`
- Reserved: `.0` (network) and `.255` (broadcast) addresses

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ip-management` | List all IP allocations |
| GET | `/api/v1/ip-management/scenario/{id}` | Get scenario IP info |
| GET | `/api/v1/ip-management/scenario/{id}/next-ip` | Get next available IP |

---

## PCAP Learning Pipeline

Learn traffic patterns from existing PCAP files to create realistic scenarios.

### Features
- Upload PCAP files for analysis
- Extract device fingerprints and communication patterns
- Generate scenario templates from learned patterns
- Support for Modbus, EtherNet/IP, and PROFINET protocols

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/learning/upload` | Upload PCAP for analysis |
| GET | `/api/v1/learning/sessions` | List learning sessions |
| GET | `/api/v1/learning/sessions/{id}` | Get session details |
| POST | `/api/v1/learning/sessions/{id}/apply` | Apply learned patterns |

---

## Scenario Templates

Pre-built scenario templates for rapid deployment across industry verticals.

### Template API
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/templates/verticals` | List industry verticals |
| GET | `/api/v1/templates/list` | List all templates |
| GET | `/api/v1/templates/detail/{vertical}/{name}` | Get template details |
| POST | `/api/v1/templates/create` | Create scenario from template |
| GET | `/api/v1/templates/phases` | List phase templates |
| GET | `/api/v1/templates/phases/presets` | List phase presets |

### Template Location
Templates are defined in `backend/app/scenario_templates/`:
- `manufacturing.py` - Manufacturing vertical templates
- `water.py` - Water/Wastewater templates
- `energy.py` - Energy/Power templates
- `oil_gas.py` - Oil & Gas templates
- `phases.py` - Traffic phase definitions

---

## Anomaly Injection

Inject anomalies into generated traffic for security testing and detection validation.

### Anomaly Types
- **Protocol Violations**: Invalid function codes, malformed packets
- **Timing Anomalies**: Unusual polling intervals, burst traffic
- **Address Anomalies**: Out-of-range addresses, broadcast storms
- **Behavioral Anomalies**: Unexpected command sequences

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/anomalies/types` | List anomaly types |
| POST | `/api/v1/anomalies/inject` | Inject anomaly into scenario |

---

## AI-Enhanced Features

### Natural Language Scenario Generation
Describe scenarios in plain English and let AI generate the configuration.

### AI Assistant
- Context-aware suggestions for device placement
- Protocol configuration recommendations
- Traffic pattern optimization

### API Integration
- MCP Server at `backend/app/mcp_server/`
- Anthropic Claude for AI provider
- HTTP + SSE transport

---

## Project Structure

```
/home/rocsmith/packetarch/
├── backend/                    # FastAPI REST API
│   ├── app/
│   │   ├── api/routes/        # API endpoints
│   │   │   ├── scenarios.py   # Scenario CRUD
│   │   │   ├── templates.py   # Template creation
│   │   │   ├── ip_management.py # IP range allocation
│   │   │   ├── learning.py    # PCAP learning
│   │   │   ├── anomalies.py   # Anomaly injection
│   │   │   └── ...
│   │   ├── core/              # Config, DB, security
│   │   ├── models/            # SQLAlchemy models
│   │   │   ├── scenario.py    # Scenario model
│   │   │   ├── ip_range_allocation.py # IP allocation model
│   │   │   └── ...
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   │   ├── ip_management.py # IP allocation service
│   │   │   └── ...
│   │   ├── scenario_templates/ # Industry vertical templates
│   │   │   ├── manufacturing.py
│   │   │   ├── water.py
│   │   │   ├── energy.py
│   │   │   ├── oil_gas.py
│   │   │   └── phases.py
│   │   ├── protocol_engines/  # OT protocol implementations
│   │   ├── traffic_generator/ # PCAP generation
│   │   ├── ai_services/       # AI scenario generation
│   │   └── mcp_server/        # AI integration
│   └── alembic/               # DB migrations
├── frontend/                   # React + Vite
│   └── src/
│       ├── api/               # Axios API client
│       │   ├── scenarios.ts   # Scenario API
│       │   ├── ipManagement.ts # IP management API
│       │   ├── learning.ts    # Learning API
│       │   └── ...
│       ├── components/        # UI components
│       │   ├── canvas/        # React Flow canvas
│       │   ├── layout/        # App layout
│       │   ├── panels/        # Side panels
│       │   ├── anomalies/     # Anomaly components
│       │   └── learning/      # Learning components
│       ├── pages/             # Route pages
│       │   ├── ScenariosPage.tsx
│       │   ├── IPManagementPage.tsx
│       │   ├── LearningPage.tsx
│       │   └── ...
│       ├── stores/            # Zustand state
│       └── types/             # TypeScript types
├── docker/                     # Docker Compose
└── docs/                       # Documentation
```
