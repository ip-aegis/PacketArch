# PacketArch API Reference

This document is a human-readable tour of the PacketArch REST and WebSocket APIs. For the machine-readable spec (complete field lists, try-it-now UI, schema download), use the auto-generated OpenAPI docs:

- **Swagger UI**: `https://<SERVER>/api/docs`
- **ReDoc**: `https://<SERVER>/api/redoc`
- **OpenAPI JSON**: `https://<SERVER>/api/openapi.json`

This guide groups endpoints by capability and shows the common flows. For exhaustive request/response fields, follow the schema name to `/api/docs`.

---

## Conventions

### Base URL & Prefix

All versioned routes are mounted under `/api/v1`. The production frontend proxies this through nginx; direct backend access is on port `8001` in development.

| Environment | Base URL |
|---|---|
| Dev | `http://localhost:8001/api/v1` |
| Prod (nginx) | `https://<SERVER_IP>/api/v1` |

Unversioned endpoints that live outside the prefix:

- `GET /health`, `GET /health/ready` — liveness + readiness probes
- `GET /agent/install.sh`, `GET /agent/docker-compose.yml`, `GET /agent/image.tar.gz` — agent bootstrap
- `WS /ws/agent?token=...` — agent WebSocket hub

### Authentication

Most endpoints require a JWT access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained from `POST /api/v1/auth/login`. The response contains both `access_token` (short-lived) and `refresh_token` (long-lived). When the access token expires, exchange the refresh token at `POST /api/v1/auth/refresh`.

Some endpoints additionally require admin privileges (`is_admin=true` on the user record). These are noted as **admin** below. LDAP-authenticated users inherit admin rights per the LDAP settings configured by an admin.

### Error Response Shape

All custom errors raised by the backend are serialized to a consistent JSON body:

```json
{
  "error": "NOT_FOUND",
  "message": "Scenario not found",
  "details": {
    "resource": "Scenario",
    "identifier": "ab12..."
  }
}
```

Pydantic validation errors return HTTP 422 with:

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": {
    "validation_errors": [
      { "field": "devices.0.ip_address", "message": "invalid IPv4", "type": "value_error" }
    ]
  }
}
```

Status codes follow the class of error:

| Error | HTTP | When |
|---|---|---|
| `VALIDATION_ERROR` | 400 / 422 | Bad input, schema mismatch |
| `NOT_FOUND` | 404 | Resource does not exist |
| `CONFLICT` | 409 | Duplicate name, active deployment blocking delete |
| `AUTH_ERROR` | 401 | Missing or invalid token |
| `EXTERNAL_SERVICE_ERROR` | 502 | Docker, Cyber Vision, or Anthropic API failure |
| `INTERNAL_ERROR` | 500 | Uncaught exception |

### Pagination

List endpoints accept `limit` and `offset` query parameters. Responses include both the `items` array and a `total` count so clients can compute page controls without a second request.

---

## 1. Authentication & Users

### Login and token refresh

```
POST /api/v1/auth/login          { username, password }  → { access_token, refresh_token, token_type }
POST /api/v1/auth/refresh        { refresh_token }       → { access_token, refresh_token, token_type }
GET  /api/v1/auth/me                                     → UserResponse
POST /api/v1/auth/register       { username, email?, password } → UserResponse
```

`login` transparently falls back to LDAP if the username does not exist locally and LDAP is configured. `register` is open until the first user is created — that user becomes admin. After that, registration continues to work but only admins can promote users.

### User management

```
GET    /api/v1/users                                     (admin)  list users
GET    /api/v1/users/{user_id}                           (admin)  user detail
PATCH  /api/v1/users/{user_id}/toggle-active             (admin)  enable/disable account
POST   /api/v1/users/{user_id}/reset-password            (admin)  force-reset a user's password
POST   /api/v1/users/me/password                                  change own password
```

### Admin settings

System-wide settings are exposed as a key/value store grouped by category (AI, network, retention, etc.).

```
GET  /api/v1/admin/settings                              list all settings, grouped by category
GET  /api/v1/admin/settings/{key}                        single setting
PUT  /api/v1/admin/settings/{key}          { value }     update value
POST /api/v1/admin/settings/seed                         insert defaults for any missing keys
POST /api/v1/admin/settings/test-connection              probe Anthropic API with stored key
```

All admin settings endpoints require admin auth.

### LDAP / Active Directory

```
GET  /api/v1/ldap/settings                               (admin)  current config (bind password masked)
PUT  /api/v1/ldap/settings                               (admin)  partial update
POST /api/v1/ldap/test-connection    { host, bind_dn, password, ... }  (admin)  test without persisting
```

---

## 2. Scenarios

A scenario is a network definition — devices, zones, flows, IP range, deployment phases — stored as JSON and rendered in the Scenario Studio canvas.

### Core CRUD

```
GET    /api/v1/scenarios                                 list (supports filters + pagination)
POST   /api/v1/scenarios                                 create (auto-allocates /16 IP range)
GET    /api/v1/scenarios/{id}
PUT    /api/v1/scenarios/{id}                            full replace (auto-versions after 5 min since last save)
PATCH  /api/v1/scenarios/{id}                            partial update (same auto-version behavior)
DELETE /api/v1/scenarios/{id}?force=true                 force=true needed if active deployments exist
POST   /api/v1/scenarios/bulk-delete    { ids: [...] }
POST   /api/v1/scenarios/{id}/duplicate { name?, description? }  new IP range allocated
```

### Import/export

```
GET  /api/v1/scenarios/{id}/export                       JSON download
POST /api/v1/scenarios/import         { ... }            allocates new IP range on import
```

### Readiness & repair

Before deploying, scenarios should pass several realism checks (naming, protocol fit, MAC/vendor alignment, conduit compliance). These endpoints surface what's wrong and fix what can be fixed automatically.

```
GET  /api/v1/scenarios/{id}/validate                     structured readiness report
GET  /api/v1/scenarios/{id}/conduit-compliance           zone-crossing flow audit vs IEC 62443
POST /api/v1/scenarios/{id}/repair-protocols             strip protocols unsupported by fingerprint
POST /api/v1/scenarios/{id}/regenerate-names             AI pass to re-name generic devices
```

### Versioning

Every scenario has an append-only version history. Versions are created automatically (coalesced to every ~5 minutes) and can also be created explicitly.

```
GET    /api/v1/scenarios/{id}/versions                           list (newest first)
POST   /api/v1/scenarios/{id}/versions      { label? }           explicit snapshot
GET    /api/v1/scenarios/{id}/versions/{ver_id}
PATCH  /api/v1/scenarios/{id}/versions/{ver_id}  { label }
DELETE /api/v1/scenarios/{id}/versions/{ver_id}
GET    /api/v1/scenarios/{id}/versions/diff?base=A&compare=B     structured field-level diff
POST   /api/v1/scenarios/{id}/versions/diff-summary              AI plain-English summary
POST   /api/v1/scenarios/{id}/versions/rollback?version=X        safety-snapshots current, then restores
```

Retention is capped at 50 versions per scenario; oldest are pruned.

---

## 3. Templates

Pre-built scenarios for each of the six industry verticals.

```
GET  /api/v1/templates                                          list verticals
GET  /api/v1/templates/phases                                   list deployment phase presets
GET  /api/v1/templates/{vertical}                               list templates in a vertical
GET  /api/v1/templates/{vertical}/{template_name}               full definition (view before create)
POST /api/v1/templates/{vertical}/{template_name}/create-scenario  { name?, customizations? }
```

Supported verticals: `manufacturing`, `water`, `energy`, `oil_gas`, `building_automation`, `transportation`.

---

## 4. Traffic Generation (PCAP)

Offline PCAP generation jobs run as background tasks and write to the server filesystem.

```
GET  /api/v1/generation                           list jobs (filter by status)
POST /api/v1/generation          { scenario_id, duration_seconds, ... }
GET  /api/v1/generation/{job_id}                  poll for status
GET  /api/v1/generation/{job_id}/download         download the .pcap when completed
DELETE /api/v1/generation/{job_id}                cancel a running job
DELETE /api/v1/generation/{job_id}/delete         delete record + optionally purge file

GET  /api/v1/generation/protocols/supported       list protocol engines registered on the server
```

For live agent-based generation, use **Deployments** below.

### Protocol templates

Reusable protocol timing/behavior profiles decoupled from scenarios.

```
GET    /api/v1/protocols                          list (filter, paginate)
GET    /api/v1/protocols/types                    distinct protocol types
GET    /api/v1/protocols/{id}
POST   /api/v1/protocols                          (admin)
PUT    /api/v1/protocols/{id}                     (admin)
DELETE /api/v1/protocols/{id}                     (admin)
```

---

## 5. Agents & Deployments

Agents are long-lived processes running on remote hosts that connect back to PacketArch over WebSocket and inject live traffic onto a selected interface.

### Agent management

```
GET    /api/v1/agents                             list all (connected + disconnected)
GET    /api/v1/agents/connected                   only currently connected, with live metrics
POST   /api/v1/agents              { name, ... }  create record + generate auth token
GET    /api/v1/agents/{id}
PUT    /api/v1/agents/{id}                        update name/description
DELETE /api/v1/agents/{id}
POST   /api/v1/agents/{id}/token                  rotate auth token
GET    /api/v1/agents/{id}/status                 connection state + diagnostics
GET    /api/v1/agents/{id}/interfaces             probe interfaces on the remote agent
```

### Agent image build & download

Admins can rebuild the agent Docker image (with the current protocol engines) and download the resulting tarball.

```
GET  /api/v1/agents/build-image                   build status
POST /api/v1/agents/build-image                   trigger a build
GET  /api/v1/agents/image-status                  image readiness
GET  /api/v1/agents/image                         download tar.gz
```

### Agent bootstrap (no auth — script endpoints)

Served under `/agent/*`, not `/api/v1/*`. Used by the install script that new agents curl during provisioning:

```
GET /agent/install.sh                             bash installer (also accepts --register/--token flags)
GET /agent/docker-compose.yml                     compose file used by the installer
GET /agent/image.tar.gz                           pre-built image
```

### Deployments

A deployment ties a scenario to an agent and drives live packet generation on that agent's selected interface.

```
GET    /api/v1/deployments                        list (filter by scenario_id, agent_id, status)
POST   /api/v1/deployments        { scenario_id, agent_id, interface, adaptive_config?, attack_playbook? }
GET    /api/v1/deployments/{id}                   detail + live metrics
PATCH  /api/v1/deployments/{id}                   change interface / adaptive config mid-run
POST   /api/v1/deployments/{id}/stop              stop the deployment
```

`adaptive_config` and `attack_playbook` on create are merged into the scenario definition sent to the agent; see sections 6 and 7.

---

## 6. Adaptive Traffic Control

Send directives to running deployments to adjust rates, force phases, or pause phase cycling — without redeploying.

```
POST /api/v1/adaptation/{scenario_id}/directives                 catch-all directive payload
POST /api/v1/adaptation/{scenario_id}/protocol-rate              rate multiplier for a specific protocol
POST /api/v1/adaptation/{scenario_id}/schedule-phase             force to a named phase
POST /api/v1/adaptation/{scenario_id}/pause-phase-cycling        pause/resume the phase scheduler
```

Directives travel from the server to the agent via an `ADAPT_TRAFFIC` WebSocket message. The controller inside the agent performs an atomic swap at the next tick (50 ms floor), so rate changes are near-instant.

---

## 7. Attack Simulation

Library of six built-in attack playbooks (TRITON-like, PIPEDREAM-like, INDUSTROYER-like, HAVEX-like, INSIDER_THREAT, NETWORK_RECON) plus individual action injection.

### Playbook library

```
GET /api/v1/attacks/playbooks                              list summaries
GET /api/v1/attacks/playbooks/{id}                         stages, actions, MITRE mappings
GET /api/v1/attacks/playbooks/compatible/{scenario_id}     filter by scenario's protocols
```

### Runtime control

```
POST /api/v1/attacks/start              { deployment_id, playbook_id, config? }
GET  /api/v1/attacks/{deployment_id}/state                 kill-chain timeline + progress
POST /api/v1/attacks/{deployment_id}/pause
POST /api/v1/attacks/{deployment_id}/resume
POST /api/v1/attacks/{deployment_id}/inject    { action_type, params }   one-shot action
```

Attack commands flow through `START_ATTACK`, `STOP_ATTACK`, `ADVANCE_STAGE`, `PAUSE_ATTACK` WebSocket messages. The attack orchestrator runs as a composition peer alongside the adaptive controller on the agent.

---

## 8. Anomaly Injection

Anomaly campaigns add realistic-but-abnormal events (degraded device, scan noise, flapping link) to scenarios. Unlike attacks, anomalies are part of scenario definition rather than a runtime-injected playbook.

```
GET  /api/v1/anomalies/templates                           list with filters
GET  /api/v1/anomalies/templates/{id}
GET  /api/v1/anomalies/suggest/{scenario_id}               vertical/protocol-aware suggestions
POST /api/v1/anomalies/{scenario_id}/campaign              create/replace campaign on scenario
GET  /api/v1/anomalies/{scenario_id}/campaign
DELETE /api/v1/anomalies/{campaign_id}
```

---

## 9. Fingerprints & CVEs

### Device fingerprints

The fingerprint library (295 templates across 18 vendors) drives protocol identity, MAC OUI selection, and response timing realism.

```
GET /api/v1/fingerprints                                   vendor summary list
GET /api/v1/fingerprints/vendors                           all vendor names
GET /api/v1/fingerprints/by-vendor/{vendor}
GET /api/v1/fingerprints/{vendor}/{model}                  full fingerprint detail
GET /api/v1/fingerprints/suggest/{device_type}             ranked suggestions
GET /api/v1/fingerprints/device-types/{device_type}/vendors
```

### CVE lookup

```
GET /api/v1/cve                                            filter by vendor/product/severity
GET /api/v1/cve/critical                                   shortcut for critical-only
GET /api/v1/cve/vendor/{vendor}
GET /api/v1/cve/{cve_id}                                   CVSS + affected firmware + exploit metadata
GET /api/v1/cve/{cve_id}/variants                          fingerprint variants for vulnerability simulation
```

---

## 10. Cyber Vision Integration

Bidirectional bridge to a Cisco Cyber Vision center for device comparison and enrichment. Connection settings are stored on the backend; reads are per-user, writes are admin.

### Settings (admin)

```
GET  /api/v1/cyber-vision/settings                         (token masked)
PUT  /api/v1/cyber-vision/settings    { base_url, api_token, verify_ssl }
POST /api/v1/cyber-vision/test-connection                  dry-run auth probe
```

### Device comparison and enrichment

```
GET  /api/v1/cyber-vision/devices                          list CV-observed devices
GET  /api/v1/cyber-vision/devices/{id}
POST /api/v1/cyber-vision/compare/{scenario_id}            MAC (100%) + IP (95%) match report
POST /api/v1/cyber-vision/enrich/{scenario_id}             push vendor/model/firmware to CV
```

### Ancillary

```
GET /api/v1/cyber-vision/presets                           device grouping presets
GET /api/v1/cyber-vision/vulnerabilities                   CV-detected vulns
```

---

## 11. Cloud Services

Manage cloud endpoint definitions that scenarios can target (MQTT brokers, HTTPS APIs, etc.).

```
GET    /api/v1/cloud-services                              list (filter by provider)
POST   /api/v1/cloud-services
GET    /api/v1/cloud-services/{id}
PUT    /api/v1/cloud-services/{id}
DELETE /api/v1/cloud-services/{id}
POST   /api/v1/cloud-services/{id}/test                    connectivity probe
```

---

## 12. AI Features

### Scenario-aware assistant

Sessions bind a conversation history to a scenario so the assistant has canvas context.

```
POST   /api/v1/ai/sessions          { scenario_id }        create or resume
POST   /api/v1/ai/sessions/{id}/chat  { message }          streaming response
GET    /api/v1/ai/sessions/{id}                            history
DELETE /api/v1/ai/sessions/{id}
```

### AI scenario generation

Two-step generate → preview → create flow so users can review before committing.

```
POST /api/v1/ai/generate/preview       { prompt, vertical?, ... }   preview devices + flows
POST /api/v1/ai/generate/from-preview  { preview_id, name }          materialize the scenario
POST /api/v1/ai/generate/description   { ... }                       write a description for a scenario
POST /api/v1/ai/suggest                { scenario_id }               next-step suggestions
```

### Context-free help chat

Used by the in-app help button. Takes a `context` field that scopes the assistant to one of: `general`, `deployment`, `deployment_error`, `scenario_studio`, `device_config`, `protocol_selection`, `attack_config`, `cyber_vision`, `process_sim`.

```
POST /help                             { message, context, error_context? }
```

> Note: `/help` is not prefixed under `/api/v1` — it's a top-level route.

---

## 13. Monitoring

### Liveness/readiness (unauthenticated)

```
GET /health                                    basic liveness
GET /health/ready                              includes DB connectivity
```

### Agent health events

Health events are emitted when agents cross thresholds (high CPU, memory, disconnects). The monitor accumulates events and exposes acknowledge/clear operations.

```
GET    /api/v1/health-monitor/events       ?limit&offset&severity&agent_id
GET    /api/v1/health-monitor/status                          all-agent summary
GET    /api/v1/health-monitor/status/{agent_id}
POST   /api/v1/health-monitor/events/{event_id}/acknowledge
DELETE /api/v1/health-monitor/events                          clear all
GET    /api/v1/health-monitor/config
PUT    /api/v1/health-monitor/config
```

### Dashboard & stats

```
GET /api/v1/stats/overview                     totals: scenarios, templates, protocols, PCAPs
GET /api/v1/dashboard/live                     live traffic: per-agent, per-deployment, protocol breakdown, time-series
```

---

## 14. IP Management

Each scenario is auto-allocated a unique `10.{n}.0.0/16` range at creation. These endpoints expose the allocations and let you reassign when needed.

```
GET  /api/v1/ip-management                                        list all allocations
GET  /api/v1/ip-management/scenario/{id}                          range + device usage
POST /api/v1/ip-management/scenario/{id}/allocate                 allocate a new range manually
POST /api/v1/ip-management/scenario/{id}/reassign                 reassign every device within the range
GET  /api/v1/ip-management/scenario/{id}/next-ip                  next free address in range
```

---

## 15. Downloads

Static assets served by the backend (briefing decks, architecture docs, guides).

```
GET /api/v1/downloads                                             list available files
GET /api/v1/downloads/{file_id}                                   download
```

---

## 16. WebSocket: Agent Hub

Agents connect to `wss://<SERVER>/ws/agent?token=<AGENT_TOKEN>` on startup and hold the socket open. Messages are JSON.

### Agent → Server

| Type | Purpose |
|---|---|
| `HEARTBEAT` | periodic CPU/memory/version + running-scenarios snapshot |
| `STATUS` | deployment lifecycle change (`starting`, `running`, `stopping`, `stopped`, `error`) |
| `INTERFACES` | response to `LIST_INTERFACES` |
| `ERROR` | structured error from scenario execution |
| `UPDATE_STATUS` | progress during an `UPDATE_AGENT` operation |

### Server → Agent

| Type | Purpose |
|---|---|
| `START_SCENARIO` | definition payload + interface, begin live generation |
| `STOP_SCENARIO` | stop a running scenario by id |
| `UPDATE_SCENARIO` | swap definition on a running scenario |
| `ADAPT_TRAFFIC` | adaptive directives (rate multipliers, phase control) |
| `LIST_INTERFACES` | probe agent's NICs |
| `START_ATTACK` / `STOP_ATTACK` / `ADVANCE_STAGE` / `PAUSE_ATTACK` | attack orchestrator control |
| `UPDATE_AGENT` | trigger in-place agent upgrade (download tarball, docker load, restart) |
| `PING` | liveness |

On disconnect, the server deregisters the agent and any deployments it owned transition to `disconnected`.

---

## 17. Common Recipes

### Deploy a scenario from a template

```
1. POST /api/v1/templates/manufacturing/assembly_line_small/create-scenario  { name: "Demo" }
   → returns scenario_id
2. GET  /api/v1/scenarios/{scenario_id}/validate                → confirm ready
3. GET  /api/v1/agents/connected                                → pick an agent_id
4. GET  /api/v1/agents/{agent_id}/interfaces                    → pick an interface
5. POST /api/v1/deployments    { scenario_id, agent_id, interface: "eth0" }
6. GET  /api/v1/deployments/{deployment_id}                     → poll status + metrics
```

### Generate a PCAP instead of live traffic

```
1. POST /api/v1/generation    { scenario_id, duration_seconds: 300 }
   → returns job_id
2. GET  /api/v1/generation/{job_id}                             → poll until status=completed
3. GET  /api/v1/generation/{job_id}/download                    → fetch .pcap
```

### Launch an attack against a running deployment

```
1. GET  /api/v1/attacks/playbooks/compatible/{scenario_id}      → ensure protocol fit
2. POST /api/v1/attacks/start   { deployment_id, playbook_id: "TRITON_LIKE" }
3. GET  /api/v1/attacks/{deployment_id}/state                   → kill-chain progress
4. POST /api/v1/attacks/{deployment_id}/inject   { action_type, params }   (optional one-offs)
```

### Adjust traffic rate mid-deployment

```
POST /api/v1/adaptation/{scenario_id}/protocol-rate
     { protocol: "modbus_tcp", multiplier: 2.5 }
```

Applies within ~50 ms via the agent's adaptive controller.

### Compare a scenario against a live Cyber Vision environment

```
1. Admin configures CV settings once via PUT /api/v1/cyber-vision/settings
2. POST /api/v1/cyber-vision/compare/{scenario_id}
   → returns matched/unmatched device lists + insights
3. (optional) POST /api/v1/cyber-vision/enrich/{scenario_id}
   → pushes vendor/model/firmware into CV for discovered devices
```

### Roll a scenario back to a previous version

```
1. GET  /api/v1/scenarios/{id}/versions                         → find the version_id
2. GET  /api/v1/scenarios/{id}/versions/diff?base=current&compare=<ver>  (preview)
3. POST /api/v1/scenarios/{id}/versions/rollback?version=<ver>  (safety-snapshots current first)
```

---

## See Also

- `docs/ADDING_NEW_PROTOCOLS.md` — how new protocol engines become part of the API surface
- `docs/ADDING_NEW_VERTICALS.md` — adding a new vertical to the `/templates` endpoint
- `CLAUDE.md` — repo guidelines and local development setup
- `/api/docs` — live Swagger UI with try-it-now
- `/api/redoc` — ReDoc rendering of the full schema
