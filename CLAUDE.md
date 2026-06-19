# PacketArch Development Guidelines

## Repository

- **GitHub**: https://github.com/ip-aegis/PacketArch
- **Branch**: `master` (primary branch)
- **Clone**: `git clone https://github.com/ip-aegis/PacketArch.git`
- **Auth**: `gh` CLI over HTTPS (`gh auth login` → HTTPS → `gh auth setup-git`).
  The current dev box authenticates as the `ip-aegis` account this way;
  `git push` uses the gh credential helper. (An SSH key at
  `~/.ssh/id_ed25519` is an alternative if you prefer SSH, but the box is
  set up for HTTPS+gh.)

### Git Workflow

```bash
git pull origin master
git add -A
git commit -m "Description of changes"
git push origin master
```

---

## Off-Box Access

All services bind to `0.0.0.0` (all network interfaces):
- **Frontend (Vite)**: `vite.config.ts` → `host: '0.0.0.0'`
- **Backend (FastAPI)**: `config.py` → `api_host: '0.0.0.0'`
- **Docker services**: Ports bound to `0.0.0.0` in `docker-compose.dev.yml`

### CORS Configuration
Allowed origins: `http://localhost:3001`, `http://localhost:5173`, `http://*:3001`, `http://*:5173`
Update `CORS_ORIGINS` in backend `.env` or `config.py` to add more.

---

## Port Management

**Always check ports before starting services.**

```bash
# Linux
lsof -i :8001 :3001 :5432 :6379
# Windows
netstat -ano | findstr ":8001 :3001 :5432 :6379"
```

| Service | Port |
|---------|------|
| Backend (FastAPI) | 8001 |
| Frontend (Vite) | 3001 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| pgAdmin (optional) | 5050 |

---

## Development Workflow

### Prerequisites
- **Backend**: Python 3.11+, Poetry
- **Frontend**: Node.js 18+, pnpm

### First-Time Setup

```bash
cd backend && poetry lock && poetry install
cd frontend && pnpm install
```

### Starting Services

```bash
# 1. Docker services
cd docker && docker-compose -f docker-compose.dev.yml up -d

# 2. Backend
cd backend && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# 3. Frontend
cd frontend && pnpm dev
```

Windows: use `python -m poetry run uvicorn ...` if poetry not in PATH.

### Stopping Services

```bash
cd docker && docker-compose -f docker-compose.dev.yml down
# Frontend/Backend: Ctrl+C
```

---

## Production Environment

Development and production run on the same server. "Production" is the local Docker environment.

- **URL**: `https://<SERVER_IP>` (port 443, self-signed SSL)
- **Credentials**: chosen by the operator in the first-run setup wizard
  (see "First-run Setup" below). The legacy `ADMIN_PASSWORD` env var is
  still honored if set, primarily for automated test harnesses.
- **Working Directory**: `/home/<SSH_USER>/packetarch`
- **Architecture**: Nginx reverse proxy → backend (internal only)

### First-run Setup

Fresh installs land on a setup wizard at `https://<server>/` instead of
a login page. The operator chooses admin credentials, names the site,
and optionally configures AI / Cyber Vision in one flow. Until the
wizard finishes, every API route except `/api/v1/setup/*`,
`/api/v1/about`, and `/health` returns 503.

State lives in two `system_settings` rows:
- `setup.completed` — `"false"` until the wizard finishes (or
  auto-graduation fires for an existing install with an admin user).
- `site.name`, `site.fqdn`, `site.timezone` — written by the wizard.

**Auto-graduation**: on every backend boot, `auto_graduate_setup()` in
`backend/app/services/startup.py` flips `setup.completed=true` if any
admin user already exists. This means upgrades from pre-wizard installs
do NOT show the wizard.

**To reset and re-run the wizard** (recovery from a compromised
first-claim, or just to redo onboarding):
```
docker compose exec postgres psql -U packetarch -d packetarch -c \
  "DELETE FROM users; UPDATE system_settings SET value='false' WHERE key='setup.completed';"
docker compose restart backend
```

Backend wiring: `RequireSetupComplete` dep in `backend/app/api/deps.py`
gates every router in `main.py` except setup/about/health. Frontend
wiring: top-level `<SetupGate>` in `frontend/src/components/SetupGate.tsx`
loads `/api/v1/setup/status` once and renders either the wizard or the
normal app shell.

### Deploying Changes

```bash
cd /home/rocsmith/packetarch
docker compose up -d --build backend    # most common
docker compose up -d --build frontend   # frontend only
docker compose up -d --build            # everything
```

### Container Management

```bash
docker compose ps                       # status
docker compose logs -f backend          # logs
docker compose restart                  # restart all
docker compose down                     # stop
docker compose up -d                    # start
```

### Production Ports

| Service | Internal | External | Notes |
|---------|----------|----------|-------|
| Frontend (nginx) | 443 | 443 | HTTPS with self-signed cert |
| Backend | 8001 | Not exposed | Via nginx proxy |
| PostgreSQL | 5432 | 5432 | |
| Redis | 6379 | 6379 | |

### SSL Certificate

Auto-generated on first start. Regenerate:
```bash
docker compose down && docker volume rm packetarch_ssl_certs && docker compose up -d
```

### Environment Variables

Production `.env` (generated by `scripts/server-init.sh`):
```
POSTGRES_PASSWORD=<generated>
SECRET_KEY=<generated>
ENCRYPTION_KEY=
ADMIN_PASSWORD=<generated>
DEBUG=false
```

---

## Remote Traffic Agent

Agents connect to PacketArch via WebSocket (`/ws/agent?token=<token>`) — "phone home" model, no inbound ports needed.

### Installing an Agent

```bash
# With auto-registration
curl -fsSL https://<SERVER_IP>/agent/install.sh | sudo bash -s -- \
  --server https://<SERVER_IP> --name "Agent-1" --register

# With existing token
curl -fsSL https://<SERVER_IP>/agent/install.sh | sudo bash -s -- \
  --server https://<SERVER_IP> --token "your-agent-token" --interface eth0
```

### Agent Management

```bash
docker compose -f /opt/packetarch-agent/docker-compose.yml logs -f agent   # logs
docker compose -f /opt/packetarch-agent/docker-compose.yml restart          # restart
sudo /opt/packetarch-agent/install.sh --uninstall                           # uninstall
```

### Central Agent Updates

1. "Build Image" in Settings → Agents (builds + saves tarball)
2. Open online agent details → "Update" (sends `UPDATE_AGENT` via WebSocket)
3. Agent downloads tarball, `docker load`, restarts

Requires Docker socket mounted and agent online.

### WebSocket Protocol

**Server → Agent:** `START_SCENARIO`, `STOP_SCENARIO`, `UPDATE_SCENARIO`, `ADAPT_TRAFFIC`, `LIST_INTERFACES`, `UPDATE_AGENT`, `PING`

**Agent → Server:** `STATUS`, `INTERFACES`, `ERROR`, `HEARTBEAT` (CPU/memory/version), `UPDATE_STATUS`

### Key Files

**Agent (`docker/packetarch-agent/`):** `app/main.py`, `app/websocket_client.py`, `app/orchestrator_pool.py`, `app/version.py`, `app/config.py`

**Backend:** `api/websocket/agent_hub.py`, `services/agent_manager.py`, `api/routes/agents.py`, `api/routes/adaptation.py`, `services/adaptation_service.py`

---

## Local Sensor Labs

App-managed, on-box labs that run a traffic agent **and** a Cisco Cyber Vision
docker sensor on the PacketArch host itself, wired through an isolated virtual
SPAN. This **augments** the CML integration (which stays fully functional) — it's
a second deployment target for when you don't want to stand up a CML lab.

### How it works

- **`packetarch-host-agent`** (`docker/packetarch-host-agent/`) — a long-running
  **privileged** sibling container (declared in `docker-compose.yml`,
  `restart: unless-stopped`, `network_mode: host`, `pid: host`). It is the ONLY
  component that touches the host; the backend stays unprivileged.
  - `app/state.py` — file-queue contract on the shared `host_agent_state` volume.
  - `app/hostops.py` — idempotent host ops (veth, daemon.json, compose).
  - `app/watcher.py` — drains the queue + a reconcile loop (reboot survival).
- **Per-lab virtual SPAN**: an isolated veth crossover `pa-gen-<slug>` ↔
  `pa-mon-<slug>` (no uplink — sim traffic can't leak). The agent injects on
  `pa-gen`; the CV sensor's macvlan capture parent is forced to `pa-mon`. This
  replaces CML's IOSvL2 SPAN switch on a single host.
- **Registry trust**: the host's `/etc/docker/daemon.json` gets the CV Center
  added to `insecure-registries` (SIGHUP dockerd — never restart, so the
  PacketArch stack is not bounced).
- **Backend stays unprivileged**: it parses the pasted CV compose, mints an agent
  token, persists `LocalLab` + `TrafficAgent` rows, and writes a lab *spec* (JSON,
  including the plaintext token) to the shared volume. The host-agent acts on it.

### Operator flow

Agents hub (`/agents`) → **Local Labs** tab → **New Local Lab** → paste the
docker-compose CV generates for a *docker* sensor → **Build**. The agent token is
shown once. Watch the **Topology** tab for the live agent→veth→sensor flow.
**CV provisioning tokens are single-use** — use a fresh sensor/token per lab.

### Lifecycle

- **Teardown = full delete**: stops sensor+agent containers, removes the veth and
  the per-lab macvlan network, drops the registry trust if unused, and deletes
  the `LocalLab` + `TrafficAgent` rows (UI ↔ backend stay in sync).
- **Survives restart**: the host-agent reconciles its persisted specs on its own
  boot; `startup.reconcile_local_labs()` nudges it on backend boot.

### Agent kinds

`TrafficAgent` carries `cml_lab_id` (CML) / `local_lab_id` (Local) / neither
(Manual). The Agents hub badges them and the deploy-time interface picker LOCKS
the injection interface for managed (Local/CML) agents.

### Key files

**Backend:** `models/local_lab.py`, `services/local_sensor_service.py`,
`services/host_agent_client.py`, `services/local_lab_naming.py`,
`api/routes/local_sensor.py`, `startup.reconcile_local_labs`.
**Frontend:** `pages/AgentsHubPage.tsx`, `components/agents/LocalLabsTab.tsx`,
`components/agents/AgentTopology.tsx`, `api/localSensor.ts`,
`stores/localSensorStore.ts`.
**Reference scripts** (manual equivalent): `scripts/local-sensor/`.

---

## Code Standards

- TypeScript strict mode for frontend
- Python type hints for backend
- All API endpoints documented with OpenAPI
- Pydantic schemas for all request/response models
- Zustand for frontend state management
- SQLAlchemy 2.0 async patterns for database

### Agent Versioning Rule

Any change to `docker/packetarch-agent/` or `backend/app/protocol_engines/` (copied into agent via Docker build staging) **MUST** bump `docker/packetarch-agent/app/version.py`. Use semver: MAJOR for breaking protocol changes, MINOR for new features, PATCH for bug fixes.

---

## Error Handling

Backend exceptions extend `PacketArchError` in `backend/app/core/exceptions.py`:

| Exception | HTTP Status | Use Case |
|-----------|-------------|----------|
| `PacketArchError` | 500 | Base class |
| `ValidationError` | 400 | Invalid input |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Duplicate/conflicting state |
| `ExternalServiceError` | 502 | Docker, CV, external API failures |
| `TrafficGenerationError` | 500 | Traffic generation failures |

Frontend: use `extractErrorMessage()` from `frontend/src/utils/errorUtils.ts`.

---

## Architecture Overview

PacketArch is an OT Traffic Simulation Platform:

1. **Scenario Studio (Frontend)**: @xyflow/react canvas, @dnd-kit drag-and-drop, Zustand stores, Ant Design dark theme
2. **Traffic Generation (Backend)**: Protocol engines (`protocol_engines/`), identity system, timing system, Celery + Redis background jobs, PCAP output
3. **MCP/AI Integration**: MCP server (JSON-RPC 2.0), Anthropic Claude, HTTP + SSE transport

---

## Key Patterns

### Protocol Engine Pattern
All engines extend `ProtocolEngine`: `generate_startup_sequence()`, `generate_poll_cycle()`, `generate_shutdown_sequence()`

### State Machine Pattern
`python-statemachine` for stateful conversations (Modbus, EtherNet/IP, PROFINET each have distinct state flows).

### Canvas Node/Edge Pattern
`DeviceNode` (OT devices), `ZoneNode` (resizable zone containers), `FlowEdge` (protocol connections with color coding).

---

## Supported Protocols

| Protocol | Port | Status |
|----------|------|--------|
| Modbus TCP | 502 | Production |
| EtherNet/IP | 44818 (TCP), 2222 (UDP) | Production |
| PROFINET | Layer 2 | Production |
| S7comm | 102 (TCP) | Production |
| BACnet/IP | 47808 (UDP) | Production |
| SNMP/NTCIP | 161, 162 (UDP) | Production |
| DNP3 | 20000 (TCP) | Production |
| IEC 60870-5-104 | 2404 (TCP) | Production |
| IEC 61850 (MMS/GOOSE/SV) | 102 (TCP) / L2 | Production |
| C37.118 (synchrophasor) | 4712 (TCP), 4713 (UDP) | Production |
| OPC UA | 4840 (TCP) | Production |

Additional engines exist for FINS and SLMP. Remote-access shapes (SSH/Telnet/RDP/HTTPS) share the CloudServiceEngine for TCP+TLS heartbeats.

Frontend protocol types: `frontend/src/types/protocols/` (discriminated union with type guards).

---

## Industry Verticals

6 verticals in `backend/app/scenario_templates/`: manufacturing, water, energy, oil_gas, building_automation, transportation. Each has pre-built scenario templates.

---

## IP Management

Each scenario gets a unique `/16` range: `10.{n}.0.0/16` (n = 1-254). Hosts start at offset 10. Subnets `/24`, gateway `.1`. Auto-assigned on creation. View at `/ip-management`.

---

## Device Templates

Unified fingerprint/signature data in `backend/app/services/device_templates/` package (332 templates across 20 vendor modules). Sources: `VENDOR_BUILTIN` and `USER_CREATED`. Contains network signatures, protocol identities, response timings, behavioral patterns. Each template carries `firmware_variants` (version + cves + population_weight) that drive per-instance firmware/CVE selection.

---

## Cisco Cyber Vision Integration

Connect to CV centers for device comparison, matching (MAC 100% / IP 95% confidence), and enrichment. Configure at Settings > Cyber Vision (URL + API token). Key files: `api/routes/cyber_vision.py`, `services/cyber_vision_service.py`, `pages/CyberVisionPage.tsx`.

---

## Scenario Realism Requirements

Every automated scenario creation path (templates, AI generation, quick demo) must satisfy these 5 realism dimensions. These are enforced by readiness checks, AI review, and remediation actions.

1. **Device Naming** — Every device must have a unique, industrial-appropriate, human-understandable name that reflects its role, vendor, and zone (e.g., `Assembly_Line_PLC_01`, `Water_Treatment_VFD_03`). Generic names like `device_001` or `PLC-1` are flagged by readiness.
2. **Protocol Accuracy** — Devices must only use protocols their vendor fingerprint supports. A Siemens PLC gets S7comm/PROFINET, not EtherNet/IP. Protocol repair is bidirectional: unsupported protocols are removed AND supported ones are added. Flows with protocols unsupported by both endpoints are rejected.
3. **Completeness** — Every device must participate in at least one flow so Cyber Vision can fingerprint it. No orphan devices. If no role-compatible partner exists, an SNMP monitoring fallback flow is created. Protocol identities (sysName, station_name, etc.) must be populated for CV classification.
4. **Inter/Intra-Cell Communications** — Cross-zone flows must be justified by IEC 62443 conduit definitions. Intra-zone traffic is unrestricted. Conduit compliance is checked at readiness time and enforced by the conduit compliance service.
5. **Vendor-Realistic MAC Addresses** — Each device's MAC OUI prefix must match its declared vendor using IEEE-verified prefixes from `vendor_oui.py`. A Siemens device must have a Siemens OUI (`00:0E:8C`), not a Rockwell one. MAC-vendor alignment is checked at readiness and MAC regeneration follows fingerprint changes.

---

## AI-Enhanced Features

Natural language scenario generation, context-aware AI assistant, AI-powered help system. Key files: `api/routes/ai.py`, `mcp_server/`, `ai_services/`.

### Claude Agent Skills

Domain procedural knowledge is packaged as Claude Agent Skills under
`backend/app/ai_services/skills/`. Each skill is a directory with a
`SKILL.md` (YAML-lite frontmatter + markdown body). The
`SkillRegistry` (`skills/registry.py`) loads them once per process.

Shipped skills:

- `packetarch-scenario-authoring` — Purdue levels, IEC 62443 conduits, vendor-protocol affinity, flow coverage, poll timing
- `packetarch-fingerprint-validator` — 295-template catalog, OUI rules, protocol identity matrix, remediation actions
- `packetarch-ics-attack-playbooks` — 9 playbooks, kill-chain vocabulary, action generator catalog
- `packetarch-device-naming` — process-aware naming rules + vertical vocabulary
- `packetarch-scenario-review` — scoring guide, categories, remediation action schemas
- `packetarch-vuln-data-curation` — how to curate/verify CVEs, firmware versions, attack-playbook MITRE mappings, and device-fingerprint identifiers (OUI/ODVA/PROFINET/BACnet/SNMP) so they stay realistic and internally consistent

Skills attach via `provider.chat(..., skills=["name1", "name2"])`.
`AnthropicProvider._build_system_blocks()` emits each skill as its own
cacheable text block (ephemeral cache_control) ahead of the per-call
system prompt. OpenAI fallback inlines bodies as a single system
message. Missing skills are logged and skipped — never fatal.

To add a skill: create `skills/<name>/SKILL.md` with `name`,
`description`, `version` frontmatter. Wire it at call sites via the
`skills=[...]` kwarg. Visible at `GET /api/v1/ai/skills`.

---

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One tack per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

---

## Licensing & Ownership

PacketArch is **GPL-3.0** (driven by Scapy GPLv2 dependency). Owner
strings live in `backend/app/core/version.py` — do NOT duplicate elsewhere.

- `LICENSE` — canonical GPL-3.0 text at repo root (do not modify)
- `NOTICE` — copyright + redistribution requirements
- `scripts/add_copyright_headers.py --check|--fix` — sweeps source files
  for the GPL header. Enforced on new files via pre-commit hook.
- `scripts/generate_third_party_licenses.sh` — regenerates
  `THIRD_PARTY_LICENSES.md` from poetry + pnpm dep trees.
- First-run EULA acknowledgment: bump `ACK_VERSION` in `version.py`
  to re-prompt all users.

Any PR adding a non-GPL-compatible dep (AGPL is fine, proprietary/BSL
is not) must be flagged before merge.

---

## Feature Flags

Current flags live in `backend/app/core/features.py` and surface to the
frontend via `/api/v1/about.features`.

- `AI_ENABLED` (default `true`) — when `false`:
  - Backend: `/api/v1/ai/*` and `/api/v1/mcp/*` return 503.
  - Frontend: AI wizard route redirects, AI tab in RightSidePanel
    hides, "AI Create" / "Generate Description" / "AI Scenario Review"
    / "Explain with AI" UI all hide. See `useFeatures` hook and
    `FeatureGate` component.
- `LIVE_TRAFFIC_ENABLED` (default `true`) — gates the live-agent half
  of the platform. When `false` PacketArch ships as an AI-powered
  PCAP-only generator. Behavior:
  - Backend: `/api/v1/agents`, `/deployments`, `/adaptation`,
    `/dashboard/live`, and the runtime-control half of `/attacks` (start,
    stop, advance, pause, inject, state, injection-status) return 503.
    The `/ws/agent` WebSocket and `/agent/*` install bundle are not
    mounted at all. Read endpoints (`/attacks/playbooks`, etc.) stay
    open so the PCAP-only build can populate the attack-playbook
    dropdown in `GeneratePcapModal`.
  - Frontend: `/deployments` and `/live-traffic` routes redirect.
    Sidebar omits both nav entries. Settings tab list omits "Traffic
    Agents". `AgentVersionBanner`, the agent-health bell, and
    `useDeploymentsStore.fetchDeployments()` are all skipped.
  - Attack + adaptive in PCAP: with the flag off, attack playbooks and
    adaptive timing-drift can still be requested per-PCAP via the new
    fields on `GenerationRequest` (`attack_playbook_id`,
    `attack_config`, `adaptive_config`) — `TrafficOrchestrator`
    registers `AttackOrchestrator` and `AdaptiveController` as
    composition peers on `UnifiedOrchestrator` for the PCAP run.

New flag ergonomics: add to `Settings` in `config.py`, add to
`Features` in `features.py`, add to `Features` in
`frontend/src/api/about.ts`, add a `RequireXEnabled` dep and apply to
router — or gate UI via `useFeatures()`.

---

## Release Bundles (Multi-Lab Deploys)

Releases are built as self-contained offline tarballs suitable for
air-gapped lab deployment.

- `scripts/build-release.sh` — builds backend/frontend/agent images,
  pulls postgres/redis, `docker save`s everything, stages compose +
  install script + docs + licenses, produces
  `dist/packetarch-<version>-offline.tar.gz`. Set `PCAP_ONLY=1` to
  produce the PCAP-only variant (`...-pcap-offline.tar.gz`): forces
  `SKIP_AGENT=1`, stamps `BUILD_VARIANT=pcap-only` into the bundle's
  `VERSION` file, and `install.sh` reads that to write
  `LIVE_TRAFFIC_ENABLED=false` into the generated `.env`.
- `scripts/release-bundle/` — the source-of-truth for everything that
  goes INTO the bundle: `install.sh`, `README_SITE.md`,
  `docker-compose.offline.yml`, `.env.example`.
- `.github/workflows/release.yml` — tag `v*` to trigger a CI build.
  Matrix builds both `full` and `pcap-only` variants in parallel; both
  tarballs are attached to the draft GitHub Release.
- Site operators use the bundle's `install.sh` (generates `.env` with
  fresh secrets), then `packetarch-backup.sh` / `packetarch-restore.sh`
  for snapshot/restore across the install's Postgres DB + PCAP volumes.

### Cert injection (custom TLS)

Frontend container's `docker-entrypoint.sh` checks
`/etc/nginx/custom-certs/server.{crt,key}` on every boot; if present,
copies to live cert path. Compose mounts `./certs` as the source. Drop
real cert/key there + `docker compose restart frontend` to swap.
