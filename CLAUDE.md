# PacketArch Development Guidelines

## Repository

- **GitHub**: https://github.com/ip-aegis/PacketArch
- **Branch**: `master` (primary branch)
- **Clone**: `git clone git@github.com:ip-aegis/PacketArch.git`

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
- **Credentials**: admin / C!sco123
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
ADMIN_PASSWORD=C!sco123
DEBUG=false
```

---

## Remote Traffic Agent

Traffic agents connect to PacketArch via WebSocket and execute traffic generation commands. This "phone home" model requires no inbound ports on agent hosts.

### Architecture

```
PacketArch Server (10.10.20.231)
       ▲
       │ WebSocket (wss://)
       │ Agent initiates connection
       ▼
┌─────────────────┐
│ Agent Host      │
│ - packetarch-agent container
│ - watchtower (auto-updates)
└─────────────────┘
```

### Deployed Agent Hosts

| Agent Name | Host IP | SSH User | Notes |
|------------|---------|----------|-------|
| TrafficGen02 | 10.10.20.138 | cisco | Password: cisco, SSH key installed |

**SSH Access:**
```bash
ssh cisco@10.10.20.138
```

### Installing an Agent

One-command installation on any Linux host:

```bash
# Install with registration (creates new agent, returns token)
curl -fsSL https://10.10.20.231/agent/install.sh | sudo bash -s -- \
  --server https://10.10.20.231 --name "Agent-1" --register

# Or install with existing token (from PacketArch UI)
curl -fsSL https://10.10.20.231/agent/install.sh | sudo bash -s -- \
  --server https://10.10.20.231 --token "your-agent-token" --interface eth0
```

### Agent Management

```bash
# View logs
docker compose -f /opt/packetarch-agent/docker-compose.yml logs -f agent

# Restart agent
docker compose -f /opt/packetarch-agent/docker-compose.yml restart

# Uninstall
sudo /opt/packetarch-agent/install.sh --uninstall
```

### Agent Versioning

Agents report their version via heartbeat messages. The UI shows version comparison to help identify outdated agents.

**Version Format:** Semantic versioning (MAJOR.MINOR.PATCH)
- **MAJOR**: Breaking changes to agent/server protocol
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, minor improvements

**Version File:** `docker/packetarch-agent/app/version.py`
```python
VERSION = "1.1.0"
```

**UI Indicators:**
- **Green "Latest" tag**: Agent matches the standard version
- **Orange upgrade indicator**: Agent is outdated, shows target version
- **Standard version badge**: Displayed in Agents tab header

### Central Agent Updates

Agents can be updated centrally from the PacketArch UI without SSH access to agent hosts.

**Update Flow:**
1. Click "Build Image" in Settings → Agents to build the latest agent Docker image
2. The server saves the image as a tarball and records the version
3. Open an online agent's details and click "Update"
4. Server sends `UPDATE_AGENT` command via WebSocket
5. Agent downloads the image tarball, loads it with `docker load`, and restarts

**Requirements:**
- Agent must have Docker socket mounted (`/var/run/docker.sock`)
- Agent must be online (connected via WebSocket)
- Image must be built first (via "Build Image" button)

**API Endpoints for Updates:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/agents/build-image` | Build agent image (background task) |
| GET | `/api/v1/agents/image-status` | Check if image is available + version |
| GET | `/api/v1/agents/image` | Download agent image tarball |
| POST | `/api/v1/agents/{id}/update` | Trigger update on connected agent |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/agents` | List all agents (includes `standard_version`) |
| POST | `/api/v1/agents` | Register new agent (returns token) |
| GET | `/api/v1/agents/{id}` | Get agent details |
| DELETE | `/api/v1/agents/{id}` | Delete agent |
| POST | `/api/v1/agents/{id}/token` | Regenerate token |
| GET | `/api/v1/agents/{id}/interfaces` | List network interfaces |
| POST | `/api/v1/agents/{id}/deploy` | Deploy scenario |
| GET | `/api/v1/agents/{id}/deployments` | List agent deployments |
| GET | `/api/v1/agents/connected` | List connected agents |
| POST | `/api/v1/agents/build-image` | Build agent Docker image |
| GET | `/api/v1/agents/image-status` | Get image availability and version |
| GET | `/api/v1/agents/image` | Download agent image tarball |
| POST | `/api/v1/agents/{id}/update` | Trigger agent update |

### Adaptation API Endpoints

Adaptive traffic controls including deployment phase scheduling.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/adaptation/{scenario_id}/state` | Get current adaptation state |
| POST | `/api/v1/adaptation/{scenario_id}/directives` | Send adaptation directives |
| POST | `/api/v1/adaptation/{scenario_id}/schedule-override` | Force a schedule phase |
| POST | `/api/v1/adaptation/{scenario_id}/protocol-rate` | Adjust protocol traffic rate |
| DELETE | `/api/v1/adaptation/{scenario_id}/directives` | Clear all active directives |
| POST | `/api/v1/adaptation/{scenario_id}/phase/skip` | Skip to next deployment phase |
| POST | `/api/v1/adaptation/{scenario_id}/phase/force` | Force a specific deployment phase |
| POST | `/api/v1/adaptation/{scenario_id}/phase/pause` | Pause or resume phase cycling |

### WebSocket Protocol

Agents connect to `/ws/agent?token=<token>` and exchange JSON messages:

**Server → Agent:**
- `START_SCENARIO` - Start traffic generation
- `STOP_SCENARIO` - Stop traffic generation
- `UPDATE_SCENARIO` - Update running scenario
- `ADAPT_TRAFFIC` - Send adaptation directives (rate adjustments, phase controls)
- `LIST_INTERFACES` - Request interface list
- `UPDATE_AGENT` - Trigger self-update (download new image and restart)
- `PING` - Heartbeat

**Agent → Server:**
- `STATUS` - Scenario status (state, packets_sent, adaptation state including deployment phase info)
- `INTERFACES` - Interface list response
- `ERROR` - Error report
- `HEARTBEAT` - System stats (CPU, memory, hostname, platform, version)
- `UPDATE_STATUS` - Update progress (downloading, loading, restarting, error)

### Key Files

**Agent Container (`docker/packetarch-agent/`):**
- `app/main.py` - Entry point, WebSocket connection, command handlers
- `app/websocket_client.py` - WebSocket client with auto-reconnect
- `app/orchestrator_pool.py` - Concurrent scenario management (uses shared `protocol_engines/`)
- `app/version.py` - Agent version constant
- `app/config.py` - Agent configuration from environment
- `docker-compose.agent.yml` - Agent stack with Watchtower
- `install.sh` - One-command installer

**Backend:**
- `backend/app/api/websocket/agent_hub.py` - WebSocket endpoint
- `backend/app/services/agent_manager.py` - Agent tracking and command routing
- `backend/app/api/routes/agents.py` - REST API including update endpoints
- `backend/app/api/routes/adaptation.py` - Adaptive traffic and phase control endpoints
- `backend/app/services/adaptation_service.py` - Adaptation state and directive management
- `backend/app/models/traffic_agent.py` - Database models
- `backend/app/schemas/agent.py` - Pydantic schemas

**Frontend:**
- `frontend/src/components/admin/AgentsTab.tsx` - Agent list with version display
- `frontend/src/components/admin/AgentDetailsDrawer.tsx` - Agent details with Update button
- `frontend/src/stores/agentsStore.ts` - Zustand state including standardVersion
- `frontend/src/api/agents.ts` - API client with update functions

### Legacy Docker API Method (Deprecated)

The old Docker API approach (`DockerHost` model) is still available but deprecated. New deployments should use the WebSocket agent model.

---

## Code Standards

- TypeScript strict mode for frontend
- Python type hints for backend
- All API endpoints documented with OpenAPI
- Pydantic schemas for all request/response models
- Zustand for frontend state management
- SQLAlchemy 2.0 async patterns for database

### Agent Versioning Rule

Any change to files under `docker/packetarch-agent/` or to shared code in `backend/app/protocol_engines/` (which is copied into the agent via Docker build staging) **MUST** include a version bump in `docker/packetarch-agent/app/version.py`. Use semver: MAJOR for breaking protocol changes, MINOR for new features, PATCH for bug fixes. Add a one-line changelog entry at the top of the version history comment.

---

## Error Handling

PacketArch uses a unified error handling system across backend and frontend.

### Backend Exception Hierarchy

All custom exceptions extend `PacketArchError` in `backend/app/core/exceptions.py`:

```python
from app.core.exceptions import ValidationError, NotFoundError

# Raise typed exceptions
raise NotFoundError("Scenario not found", details={"id": scenario_id})
raise ValidationError("Invalid protocol configuration", code="INVALID_PROTOCOL")
```

| Exception | HTTP Status | Use Case |
|-----------|-------------|----------|
| `PacketArchError` | 500 | Base class for all errors |
| `ValidationError` | 400 | Invalid input data |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Duplicate or conflicting state |
| `ExternalServiceError` | 502 | Docker, Cyber Vision, external API failures |
| `TrafficGenerationError` | 500 | Traffic generation failures |

### Frontend Error Utilities

Use `extractErrorMessage()` from `frontend/src/utils/errorUtils.ts`:

```typescript
import { extractErrorMessage, createErrorHandler } from '@/utils/errorUtils';

// In async operations
try {
  await api.createScenario(data);
} catch (error) {
  const message = extractErrorMessage(error, 'Failed to create scenario');
  notification.error({ message });
}

// Or use the handler factory
const handleError = createErrorHandler('Scenario', 'Operation failed', (msg) => {
  notification.error({ message: msg });
});
```

### Key Files
- `backend/app/core/exceptions.py` - Exception class definitions
- `backend/app/main.py` - Global exception handlers
- `frontend/src/utils/errorUtils.ts` - Error extraction utilities

---

## Architecture Overview

PacketArch is an OT Traffic Simulation Platform with three main subsystems:

### 1. Scenario Studio (Frontend)
- **Canvas**: @xyflow/react for visual scenario building
- **DnD**: @dnd-kit for palette-to-canvas drag and drop
- **State**: Zustand stores (`scenarioStore`, `historyStore`, `aiAssistantStore`)
- **Styling**: Ant Design with Cisco-inspired dark theme

### 2. Traffic Generation (Backend)
- **Protocol Engines**: `backend/app/protocol_engines/` - Modbus, EtherNet/IP, PROFINET, S7comm, BACnet, SNMP
- **Identity System**: `backend/app/protocol_engines/identity/` - Protocol-specific device identification
- **Timing System**: `backend/app/protocol_engines/timing/` - Realistic response delay simulation
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

### Protocol Identity System
Centralized identity management for protocol-specific device identification responses.

**Architecture:**
- `ProtocolIdentityBuilder` - Base class for protocol-specific identity builders
- Registry pattern with `@register_builder` decorator
- Supports firmware version derivation across protocols
- Centralized MAC address generation with vendor OUI support

**Supported Protocols:**
- Modbus: Device identification (MEI function 0x2B)
- EtherNet/IP: Identity object attributes
- PROFINET: DCP identify response fields
- S7comm: SZL system information
- BACnet: Device object properties
- SNMP: System MIB OIDs

**MAC Address Generation:**
```python
from app.protocol_engines.identity import generate_mac, generate_mac_from_fingerprint

# Generate MAC with vendor OUI
mac = generate_mac(vendor="Siemens", device_type="PLC")
# Returns: "00:1C:06:XX:XX:XX" (Siemens OUI + random suffix)

# Generate from fingerprint/template
mac = generate_mac_from_fingerprint(device.vendor_fingerprint)
```

**Key Files:**
- `backend/app/protocol_engines/identity/` - Identity builder system
- `backend/app/protocol_engines/identity/__init__.py` - Registry and MAC generation
- `backend/app/protocol_engines/identity/base.py` - Base builder class
- `backend/app/protocol_engines/identity/*_builder.py` - Protocol-specific builders

### Timing System
Realistic response delay simulation using statistical distributions.

**Supported Distributions:**
- Gaussian: Normal distribution (most common for devices)
- Lognormal: Skewed distribution (network delays)
- Uniform: Even distribution within bounds
- Exponential: Memoryless arrivals
- Gamma: Flexible shape (response times)
- Learned: Replay from captured samples

**Pre-configured Models:**
- `DEFAULT_TIMING_CONFIG` - Standard device timing (~15ms mean)
- `FAST_DEVICE_TIMING_CONFIG` - High-performance devices (~5ms mean)
- `SLOW_DEVICE_TIMING_CONFIG` - Legacy/slow devices (~50ms mean)
- `NOISY_NETWORK_TIMING_CONFIG` - Congested networks (~25ms mean, high variance)

**Usage:**
```python
from app.protocol_engines.timing import timing_model_from_fingerprint

model = timing_model_from_fingerprint(device.vendor_fingerprint)
sample = model.sample()
delay_ms = sample.delay_ms
```

**Key Files:**
- `backend/app/protocol_engines/timing/` - Timing model system
- `backend/app/protocol_engines/timing/interface.py` - TimingConfig, TimingModel protocol
- `backend/app/protocol_engines/timing/models.py` - Distribution implementations
- `backend/app/protocol_engines/timing/factory.py` - Model creation functions

---

## Supported Protocols

| Protocol | Port | Engine Status |
|----------|------|---------------|
| Modbus TCP | 502 | Production |
| EtherNet/IP | 44818 (TCP), 2222 (UDP) | Production |
| PROFINET | N/A (Layer 2) | Production |
| S7comm | 102 (TCP) | Production |
| BACnet/IP | 47808 (UDP) | Production |
| SNMP/NTCIP | 161, 162 (UDP) | Production |
| OPC UA | 4840 | Future |
| DNP3 | 20000 | Future |
| IEC 104 | 2404 | Future |

### Frontend Protocol Types

Type-safe protocol configuration types are available in `frontend/src/types/protocols/`:

```typescript
import { ProtocolConfig, isModbusConfig, getDefaultConfig } from '@/types/protocols';

// Discriminated union for type-safe configs
const config: ProtocolConfig = {
  protocol: 'modbus_tcp',
  config: {
    unitId: 1,
    functionCodes: [0x03, 0x04],
    registerRanges: [{ start: 0, count: 10 }],
    pollIntervalMs: 1000,
  }
};

// Type guards for runtime checking
if (isModbusConfig(config)) {
  console.log(config.config.unitId); // TypeScript knows this is ModbusConfig
}

// Get default config for a protocol
const defaultConfig = getDefaultConfig('ethernet_ip');
```

**Available Protocol Types:**
- `ModbusConfig` - Modbus TCP configuration
- `EtherNetIPConfig` - EtherNet/IP CIP configuration
- `ProfinetConfig` - PROFINET RT/IRT configuration
- `S7Config` - S7comm configuration
- `BACnetConfig` - BACnet/IP configuration
- `SNMPConfig` - SNMP/NTCIP configuration

**Key Files:**
- `frontend/src/types/protocols/index.ts` - Discriminated union and type guards
- `frontend/src/types/protocols/modbus.ts` - Modbus types
- `frontend/src/types/protocols/ethernet-ip.ts` - EtherNet/IP types
- `frontend/src/types/protocols/profinet.ts` - PROFINET types
- `frontend/src/types/protocols/s7.ts` - S7comm types
- `frontend/src/types/protocols/bacnet.ts` - BACnet types
- `frontend/src/types/protocols/snmp.ts` - SNMP types

---

## Industry Verticals

- **Manufacturing**: High-speed Profinet/EtherNet/IP, PLCs, HMIs, drives
- **Water/Wastewater**: SCADA, RTUs, DNP3/Modbus polling
- **Energy/Power**: Substation RTUs, IEC-104, event bursts
- **Oil & Gas**: Pipeline SCADA, Modbus/OPC UA, sparse polling
- **Building Automation/BMS**: Commercial buildings, campus BMS, data centers with BACnet/IP, Modbus TCP
- **Transportation/ITS**: Highway corridors, urban intersections, tunnels, toll plazas with SNMP/NTCIP

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

## Device Templates

Device templates provide unified fingerprint/signature data for realistic traffic generation.

### Template Sources
- **VENDOR_BUILTIN**: Pre-packaged fingerprints for known vendors (Siemens, Rockwell, etc.)
- **USER_CREATED**: Custom templates created/modified by users

### Template Contents
- **Network Signatures**: OUI patterns, TCP stack characteristics (TTL, window size, MSS)
- **Protocol Identities**: Modbus, EtherNet/IP, PROFINET, S7comm, BACnet, SNMP identity data
- **Response Timings**: Statistical distributions for realistic delay simulation
- **Behavioral Patterns**: Device role, supported protocols, typical ports

### Key Files
- `backend/app/models/device_template.py` - Unified `DeviceTemplate` model
- `backend/app/services/learned_pattern_service.py` - Template queries and matching

### Usage
```python
from app.models.device_template import DeviceTemplate, TemplateSource

# Query templates by vendor
templates = await db.execute(
    select(DeviceTemplate).where(
        DeviceTemplate.vendor == "Siemens",
        DeviceTemplate.source == TemplateSource.VENDOR_BUILTIN.value
    )
)

# Get protocol identity
identity = template.get_protocol_identity("modbus")
timing = template.get_timing_for_protocol("modbus")
```

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
- `building_automation.py` - Building Automation/BMS templates
- `transportation.py` - Transportation/ITS templates
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

## Docker Hosts Management

Configure and manage remote Docker hosts for distributed traffic generation.

### Overview
PacketArch can deploy traffic generators to remote Docker hosts, allowing traffic injection from multiple network locations. Hosts are configured with TLS certificates for secure API communication.

### Features
- **TLS Authentication**: Secure connection using CA, client cert, and client key
- **Connection Testing**: Verify connectivity before deployment
- **Interface Discovery**: List available network interfaces on remote hosts
- **Encrypted Storage**: Client keys are encrypted at rest

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/docker-hosts` | List all Docker hosts |
| POST | `/api/v1/docker-hosts` | Create a new Docker host |
| GET | `/api/v1/docker-hosts/{id}` | Get Docker host details |
| PUT | `/api/v1/docker-hosts/{id}` | Update Docker host |
| DELETE | `/api/v1/docker-hosts/{id}` | Delete Docker host |
| POST | `/api/v1/docker-hosts/{id}/test` | Test connection |
| GET | `/api/v1/docker-hosts/{id}/interfaces` | List network interfaces |

### Setting Up a Docker Host
1. Install Docker Engine on the target Linux host
2. Generate TLS certificates (CA, server, client)
3. Configure Docker daemon for remote TCP access on port 2376
4. Configure firewall to allow port 2376 from PacketArch server
5. Add host in PacketArch: Settings > Docker Hosts

### Key Files
- `backend/app/api/routes/docker_hosts.py` - API endpoints
- `backend/app/models/docker_host.py` - Database model
- `backend/app/services/docker_service.py` - Docker API client
- `frontend/src/components/admin/DockerHostsTab.tsx` - Admin UI
- `frontend/src/content/help/docker-host-setup.tsx` - Setup guide

---

## Cisco Cyber Vision Integration

Integrate with Cisco Cyber Vision for device discovery, comparison, and enrichment.

### Overview
PacketArch can connect to Cisco Cyber Vision centers to compare simulated devices against real discovered devices, match by MAC/IP address, and push enrichment data back to CV.

### Features
- **Device Discovery**: Fetch devices, presets, and vulnerabilities from Cyber Vision
- **Scenario Comparison**: Compare PacketArch scenario devices against CV-discovered devices
- **Device Matching**: Match by MAC address (100% confidence) or IP address (95% confidence)
- **Device Enrichment**: Push vendor, model, firmware, and custom properties to CV devices with before/after preview
- **Comparison Insights**: Actionable feedback explaining why devices are missing (Layer 2 visibility, network segments) and suggesting next steps (enrichment, re-compare)
- **CV-Only Devices**: Shows devices discovered by CV that aren't in the scenario
- **Re-compare Workflow**: After enrichment, one-click re-comparison to verify changes took effect
- **Vulnerability Tracking**: View vulnerabilities detected by Cyber Vision

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/cyber-vision/settings` | Get CV connection settings |
| PUT | `/api/v1/cyber-vision/settings` | Update CV connection settings |
| GET | `/api/v1/cyber-vision/status` | Check CV connection status |
| POST | `/api/v1/cyber-vision/test-connection` | Test connection with credentials |
| GET | `/api/v1/cyber-vision/presets` | List CV presets |
| GET | `/api/v1/cyber-vision/devices` | List CV devices (paginated) |
| GET | `/api/v1/cyber-vision/devices/{id}` | Get device details |
| GET | `/api/v1/cyber-vision/vulnerabilities` | List CV vulnerabilities |
| POST | `/api/v1/cyber-vision/compare/{scenario_id}` | Compare scenario against CV |
| POST | `/api/v1/cyber-vision/enrich` | Push device data to CV |

### Configuration
1. Navigate to Settings > Cyber Vision
2. Enter your Cyber Vision center URL (e.g., `https://cv-center.example.com`)
3. Provide an API token with appropriate permissions
4. Configure SSL verification (disable for self-signed certificates)

### Key Files
- `backend/app/api/routes/cyber_vision.py` - API endpoints
- `backend/app/services/cyber_vision_service.py` - CV API client
- `backend/app/schemas/cyber_vision.py` - Pydantic schemas
- `frontend/src/pages/CyberVisionPage.tsx` - CV comparison UI
- `frontend/src/api/cyberVision.ts` - Frontend API client
- `frontend/src/stores/cyberVisionStore.ts` - Zustand state

---

## AI-Enhanced Features

### Natural Language Scenario Generation
Describe scenarios in plain English and let AI generate the configuration.

### AI Assistant
- Context-aware suggestions for device placement
- Protocol configuration recommendations
- Traffic pattern optimization

### AI-Powered Help System
Context-aware help with AI chat for troubleshooting and setup guidance.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ai/help` | Get AI-powered help for a question |

Supported contexts:
- `docker_host_setup` - Docker host configuration help
- `general` - General PacketArch usage help

### API Integration
- MCP Server at `backend/app/mcp_server/`
- Anthropic Claude for AI provider
- HTTP + SSE transport

### Key AI Files
- `backend/app/api/routes/ai.py` - AI endpoints (chat, help, preview)
- `backend/app/mcp_server/` - MCP tool server
- `backend/app/ai_services/` - AI scenario generation
- `frontend/src/components/admin/DockerHostHelpDrawer.tsx` - Help drawer with AI chat

---

## Project Structure

```
/home/rocsmith/PacketArch/
├── backend/                    # FastAPI REST API
│   ├── app/
│   │   ├── api/routes/        # API endpoints
│   │   │   ├── scenarios.py   # Scenario CRUD
│   │   │   ├── templates.py   # Template creation
│   │   │   ├── ip_management.py # IP range allocation
│   │   │   ├── anomalies.py   # Anomaly injection
│   │   │   ├── docker_hosts.py # Docker host management
│   │   │   ├── cyber_vision.py # Cisco CV integration
│   │   │   ├── ai.py          # AI assistant endpoints
│   │   │   ├── ai_help.py     # AI-powered help system
│   │   │   └── ...
│   │   ├── core/              # Config, DB, security
│   │   │   ├── config.py      # Application settings
│   │   │   ├── database.py    # Async SQLAlchemy setup
│   │   │   ├── exceptions.py  # Custom exception hierarchy
│   │   │   └── security.py    # Auth utilities
│   │   ├── models/            # SQLAlchemy models
│   │   │   ├── scenario.py    # Scenario model
│   │   │   ├── device_template.py # Unified device template
│   │   │   ├── ip_range_allocation.py # IP allocation model
│   │   │   ├── docker_host.py # Docker host model
│   │   │   └── ...
│   │   ├── schemas/           # Pydantic schemas
│   │   │   ├── cyber_vision.py # CV API schemas
│   │   │   └── ...
│   │   ├── services/          # Business logic
│   │   │   ├── ip_management.py # IP allocation functions
│   │   │   ├── docker_service.py # Docker API client
│   │   │   ├── cyber_vision_service.py # CV API client
│   │   │   └── ...
│   │   ├── scenario_templates/ # Industry vertical templates
│   │   │   ├── manufacturing.py
│   │   │   ├── water.py
│   │   │   ├── energy.py
│   │   │   ├── oil_gas.py
│   │   │   ├── building_automation.py # BMS templates
│   │   │   ├── transportation.py # ITS templates
│   │   │   └── phases.py
│   │   ├── protocol_engines/  # OT protocol implementations
│   │   │   ├── modbus/        # Modbus TCP engine
│   │   │   ├── ethernet_ip/   # EtherNet/IP engine
│   │   │   ├── profinet/      # PROFINET engine
│   │   │   ├── s7/            # S7comm engine
│   │   │   ├── bacnet/        # BACnet/IP engine
│   │   │   ├── snmp/          # SNMP/NTCIP engine
│   │   │   ├── identity/      # Protocol identity + MAC generation
│   │   │   ├── timing/        # Timing model system
│   │   │   └── adaptive/      # Adaptive traffic (micro-variations, scheduling, phase cycling)
│   │   ├── traffic_generator/ # PCAP generation
│   │   ├── ai_services/       # AI scenario generation
│   │   └── mcp_server/        # AI integration
│   └── alembic/               # DB migrations
├── frontend/                   # React + Vite
│   └── src/
│       ├── api/               # Axios API client
│       │   ├── scenarios.ts   # Scenario API
│       │   ├── ipManagement.ts # IP management API
│       │   ├── cyberVision.ts # CV API client
│       │   └── ...
│       ├── components/        # UI components
│       │   ├── canvas/        # React Flow canvas
│       │   ├── layout/        # App layout
│       │   ├── panels/        # Side panels
│       │   ├── anomalies/     # Anomaly components
│       │   └── admin/         # Admin components
│       │       ├── DockerHostsTab.tsx     # Docker hosts UI
│       │       ├── CyberVisionTab.tsx     # CV settings UI
│       │       └── DockerHostHelpDrawer.tsx # Help with AI chat
│       ├── content/help/      # Help system content
│       │   ├── index.ts       # Help registry
│       │   └── docker-host-setup.tsx # Docker setup guide
│       ├── pages/             # Route pages
│       │   ├── ScenariosPage.tsx
│       │   ├── IPManagementPage.tsx
│       │   ├── CyberVisionPage.tsx # CV comparison UI
│       │   └── ...
│       ├── stores/            # Zustand state
│       │   ├── cyberVisionStore.ts # CV state management
│       │   └── ...
│       ├── types/             # TypeScript types
│       │   ├── protocols/     # Protocol-specific types
│       │   │   ├── index.ts   # Discriminated union + guards
│       │   │   ├── modbus.ts  # Modbus config types
│       │   │   ├── ethernet-ip.ts # EtherNet/IP types
│       │   │   ├── profinet.ts # PROFINET types
│       │   │   ├── s7.ts      # S7comm types
│       │   │   ├── bacnet.ts  # BACnet types
│       │   │   └── snmp.ts    # SNMP types
│       │   └── index.ts       # Main type exports
│       └── utils/             # Utility functions
│           └── errorUtils.ts  # Error handling utilities
├── docker/                     # Docker Compose
│   └── packetarch-agent/       # Remote traffic agent
│       ├── app/
│       │   ├── main.py         # Entry point, command handlers
│       │   ├── websocket_client.py # WebSocket with auto-reconnect
│       │   ├── orchestrator_pool.py # Scenario management
│       │   ├── version.py      # Agent version constant
│       │   └── config.py       # Environment configuration
│       ├── Dockerfile          # Agent container image
│       ├── requirements.txt    # Python dependencies
│       ├── docker-compose.agent.yml # Agent + Watchtower stack
│       └── install.sh          # One-command installer
└── docs/                       # Documentation
```
