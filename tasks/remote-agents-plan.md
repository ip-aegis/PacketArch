# Remote Agents + Local Sensor Labs — Design & Implementation Plan

**Status:** DRAFT for review (2026-05-30, revised after decisions)
**Owner:** Rocky

## Decisions (LOCKED)
- **Dedicated Agents hub page** — all remote-agent functions move there.
- **Host-capability-first** sequencing; plan before code; purely additive.
- App owns a **persistent, reboot-surviving, always-on, privileged** host
  capability. Idles when no labs exist (min friction).
- **Multiple concurrent local labs**.
- **Transport:** file-queue over shared volume (reliability #1; progress #2).
- **Teardown:** full delete (UX ↔ backend always in sync).
- **Consolidation:** CML + Deployments + Live Traffic all fold into the hub.

---

## 0. Goal

Turn the proven manual local agent + Cyber Vision sensor flow
(`scripts/local-sensor/`, see [[local_sensor_lab]]) into a first-class,
app-managed feature, and consolidate the scattered agent/lab/deployment UX into
one **Agents hub** page. Mirrors the existing CML "build lab" stack so the local
path is a sibling, not a fork.

---

## 1. Current-state (audit summary)

### Backend control surfaces to REUSE (not rebuild)
- **Agents REST** (`api/routes/agents.py`): CRUD, `/connected` (real-time
  cpu/mem/version/running_scenarios), build-image, image download, per-agent +
  bulk update, deploy/undeploy, logs, ping.
- **Deployments REST** (`api/routes/deployments.py`): list (self-healing sync),
  delete. `AgentDeployment` = state/interface/packets_sent/error/started/stopped.
- **WS hub** (`api/websocket/agent_hub.py` + `services/agent_manager.py`):
  in-memory online registry; server→agent START/STOP/UPDATE_SCENARIO,
  ADAPT_TRAFFIC, LIST_INTERFACES, UPDATE_AGENT, GET_LOGS, PING(_TEST); agent→
  server HEARTBEAT (cpu/mem/version), STATUS (packets/protocol_breakdown/pps),
  UPDATE_STATUS, INTERFACES, LOGS, PING_RESPONSE, ERROR.
- **Live dashboard** (`/dashboard/live`): aggregated deployments + agent
  connections + health + time-series.
- **Privileged-sibling precedent** (`services/system_upgrade.py::launch_updater`):
  unprivileged backend uses Docker SDK + mounted `docker.sock` to run a
  privileged helper with host bind-mounts + shared status volume. Settings exist:
  `host_install_dir`, `compose_project_name`, `docker_gid` (config.py:32-34);
  compose passes them (docker-compose.yml:63-65).

### Frontend to LIFT
- `AgentsTab.tsx` (696), `CmlTab.tsx` (678), `DeploymentsPage.tsx` (440),
  `LiveTrafficDashboardPage.tsx` (123), `DeploymentCard.tsx`.
- Viz: `ProtocolBreakdownChart`, `PacketRateSparkline`, `AggregateStatsRow`,
  `HealthEventsFeed`, `PhaseTimeline`, `KillChainTimeline`.
- `@xyflow/react` canvas stack (Studio) → basis for topology diagram.
- Stores/APIs: `agentsStore`, `deploymentsStore`, `cmlStore`,
  `liveDashboardStore`; `api/agents.ts`, `api/deployments.ts`, `api/cml.ts`.

### Collision points blocking multi-lab (must become per-lab-unique)
| Resource | Today (fixed) | Per-lab target |
|----------|---------------|----------------|
| veth pair | `pa-gen` / `pa-mon` | `pa-gen-{slug}` / `pa-mon-{slug}` |
| agent container | `packetarch-agent` | `packetarch-agent-{slug}` |
| agent install dir | `/opt/packetarch-agent` | `/opt/packetarch-agent-{slug}` |
| CV sensor container | `ccv-sensor-1` | `ccv-sensor-{slug}` |
| CV sensor networks | `ccv-network-0-collection` / `ccv-network-capture-1` | `ccv-net-{slug}-coll` / `ccv-net-{slug}-cap` |
| CV sensor volume | `ccv-volume-1` | `ccv-vol-{slug}` |
| agent "kind" | only `cml_lab_id` | **new** `local_lab_id` |

`slug` = short stable id from the LocalLab row (first 8 of UUID).

---

## 2. Architecture

### 2.1 Persistent host capability — `packetarch-host-agent`

Long-lived, privileged, host-networked sibling container in the main
`docker-compose.yml`, `restart: unless-stopped`. The ONLY component touching the
host; the backend never holds privilege.

```yaml
# docker-compose.yml (NEW service — additive, always-on)
host-agent:
  build: ./docker/packetarch-host-agent
  image: packetarch-host-agent:latest
  container_name: ${COMPOSE_PROJECT_NAME:-packetarch}-host-agent
  restart: unless-stopped
  privileged: true
  network_mode: host
  pid: host
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - /etc/docker:/etc/docker          # daemon.json (insecure-registries)
    - host_agent_state:/state          # shared queue/status with backend
    - ./docker/packetarch-host-agent:/app:ro
  environment:
    COMPOSE_PROJECT_NAME: ${COMPOSE_PROJECT_NAME:-packetarch}
```

**Responsibilities (host-level only):**
- create/destroy per-lab veth crossovers (`ip link`, promisc, ethtool offloads off)
- manage `/etc/docker/daemon.json` insecure-registries + daemon reload (HUP via
  host pid ns; never `restart`)
- `docker compose up -d`/`down` per-lab sensor + agent (templated names)
- **reconcile** on startup + on a timer: read desired LocalLab state, make host
  match (recreate missing veths/containers) → sticky across reboots.

**Why privileged + host net + pid host:** veth needs CAP_NET_ADMIN in host netns;
daemon reload needs host pid ns. `restart: unless-stopped` = auto-return on boot.
**Idle when unused:** watcher no-ops until a lab spec exists, so always-on is
harmless on a no-lab box. (Future product knob: a `profiles:` gate could hide the
privileged container on PCAP-only/air-gapped installs — not needed here.)

**Transport — file-queue over shared volume (reliability #1, progress #2):**
- Backend writes `requests/<id>.json`; host-agent watches, executes, writes
  `results/<id>.json` + an **incremental** `labs/<slug>.status` (stage, percent,
  message, updated_at) it rewrites as it progresses. Backend polls + surfaces it —
  exactly how `system_upgrade.py` drives a progress UI across restarts.
- No port to bind (no restart races), no auth surface, survives container restart,
  no lost in-flight state.
- **Two distinct live data planes (don't conflate):**
  1. *Provisioning progress* (veth → image pull → containers up) → host-agent
     status file → progress bars. The host-agent owns only this.
  2. *Runtime telemetry* (packet counts, pps, flow direction, green/online) →
     already flows agent→server over WS into `/dashboard/live`. Host-agent is NOT
     in this path. A new topology endpoint MERGES lab-up (status file) +
     packets-flowing (agent STATUS) for the live diagram.

### 2.2 Backend: LocalLab model + per-lab naming

New `models/local_lab.py` → table `local_labs`:
```
id (UUID PK) · name (unique) · slug (unique, drives resource names)
agent_id (FK traffic_agents, nullable) · sensor_serial (nullable)
sensor_compose (Text, verbatim) · registry (nullable)
gen_if / mon_if (str) · state (pending|provisioning|running|degraded|stopped|error)
status_detail (Text, nullable) · created_at / updated_at · created_by_id (nullable)
```
`TrafficAgent`: add `local_lab_id (str | null)` (mirrors `cml_lab_id`). One
Alembic migration adds the column + `local_labs`. Agent kind:
`cml_lab_id` → CML · `local_lab_id` → Local · both null → Manual.

`services/local_lab_naming.py`: pure fns `agent_container/sensor_container/
veth_pair/sensor_net_names/install_dir(slug)` — single source of truth shared by
backend (writes specs) + host-agent (acts).

### 2.3 Backend: routes + service (mirror CML)

`api/routes/local_sensor.py`, prefix `/local-sensor`, gated
`[RequireSetupComplete, RequireLiveTrafficEnabled]`; AdminUser on mutations,
CurrentUser on reads:

- `GET  /local-sensor/host-status` — host-agent up? veth support? registries?
- `GET  /local-sensor/labs` — list (mirrors `/cml/deployments`)
- `POST /local-sensor/build` — mirrors `/cml/build-lab`
- `POST /local-sensor/{id}/teardown` — mirrors `/cml/teardown-lab`
- `GET  /local-sensor/{id}` — one lab + live status

`services/local_sensor_service.py`:
- reuse `CMLService.parse_sensor_compose()` (already `@staticmethod`) for
  token/serial/image/registry.
- reuse `generate_agent_token()` / `hash_token()` (agents.py).
- `build()`: parse compose → create LocalLab (pending) → create TrafficAgent
  (`local_lab_id`, `default_interface=gen_if`) → write lab spec to shared volume →
  return token once (like CML). host-agent provisions + writes status; backend
  reflects it.
- `teardown()` = **full delete** (sync invariant): write teardown request →
  host-agent `down`s containers + deletes veth + removes CV registry from
  daemon.json **iff no remaining lab references it** → delete LocalLab row +
  delete the agent row. The reconciler enforces "DB desired state == host
  reality" as a hard invariant.

Schemas `schemas/local_sensor.py`: `LocalLabBuildRequest` (name, sensor_compose,
agent_name?, cpus?, ram?), `LocalLabBuildResponse` (lab_id, agent_id,
agent_token, sensor_serial, state, warnings[]), `LocalLabItem`,
`LocalLabListResponse`, `LocalHostStatusResponse`. Register in `main.py` by CML.

### 2.4 Frontend: the consolidated Agents hub

**ALL remote-agent functions move to one page.** It absorbs the Settings *Traffic
Agents* tab, the entire *Modeling Labs* (CML) tab (config + build + deploy +
teardown), the `/deployments` page, and the `/live-traffic` page. Old routes
redirect into the hub. Those two Settings tabs are removed → replaced by a
"Managed in Agents →" pointer (additive: relocated, not lost).

**Stays in Settings:** only **Cyber Vision connection config** — CV is dual-use
(the standalone `/cyber-vision` device-comparison page needs the same creds,
independent of agents). The hub displays CV/sensor status but doesn't own the
credential. (Override if you want CV creds moved too.)

**New route** `/agents` → `AgentsHubPage.tsx`; one sidebar entry **"Agents"**
replaces the conditional Deployments + Live Traffic entries (gated
`liveTrafficEnabled`). Working name "Agents" (could be "Fleet"; "Remote Agents"
is off since local labs aren't remote).

Sectioned hub:
- **Overview** — `AggregateStatsRow` + `HealthEventsFeed`.
- **Toolbar** — Add Agent · New Local Lab · New CML Lab · Build Image · refresh.
- **Agents** — lift `AgentsTab` table + **Kind** badge (Manual/CML/Local) from
  `cml_lab_id`/`local_lab_id`; filterable. Detail panel per agent:
  - **Topology diagram** (new `@xyflow/react`): Agent → inject iface → veth/SPAN
    → CV Sensor → Scenario. Nodes **green when online**; inject→sensor edge
    **animated in flow direction** with **live pps**; sensor node lit when
    enrolled. Data merged from `/dashboard/live` + `/local-sensor/{id}`. Local
    draws `pa-gen↔pa-mon`; CML draws SPAN-switch; manual draws agent→scenario.
  - deployments (`DeploymentCard` + protocol pie + sparkline), health/logs/
    interfaces/ping (from `AgentDetailsDrawer`).
- **Labs** — Local + CML in one table (state + provisioning progress bar from the
  status file + teardown). Two build modals behind the toolbar.
- **Deployments** — lift `DeploymentsPage` table.
- **Live** — lift `LiveTrafficDashboardPage`.

New `api/localSensor.ts` + `stores/localSensorStore.ts` (clone cml shapes).
Reuse `agentsStore`/`deploymentsStore`/`cmlStore`/`liveDashboardStore`.

---

## 3. Phased implementation (host-capability-first)

**Phase 1 — Host capability (no UI).**
1. `docker/packetarch-host-agent/` image (alpine + iproute2 + ethtool +
   docker-cli + compose plugin + Python watcher) + Dockerfile.
2. host-agent service in `docker-compose.yml` (privileged/host/pid + state vol).
3. file-queue contract: request/result/status schema under `/state`.
4. reconcile loop + veth/daemon.json/compose ops (port `scripts/local-sensor/*`
   logic into the watcher, templated by slug; idempotent).
5. validate by hand: drop a spec → lab up → reboot → lab returns.

**Phase 2 — Backend model + routes.**
1. `local_labs` + `traffic_agents.local_lab_id` migration.
2. `local_lab_naming.py`, `local_sensor_service.py` (reuse parse/token helpers).
3. `api/routes/local_sensor.py` + schemas + main.py wire-up.
4. backend writes specs to shared volume; surfaces status; teardown=full delete.
5. validate via curl: build → agent online → CV sees devices → teardown clean.

**Phase 3 — Agents hub (lift + unify everything).**
1. `AgentsHubPage.tsx` route `/agents` + single sidebar entry; sectioned shell.
2. lift AgentsTab table (+ Kind badge), DeploymentsPage, LiveTrafficDashboard,
   DeploymentCard into the hub.
3. move FULL CML tab into Labs view; add New Local Lab modal + localSensor
   api/store; Local + CML share one Labs table with a progress bar.
4. remove Traffic Agents + Modeling Labs Settings tabs → "Managed in Agents →";
   keep CV config in Settings. Redirect `/deployments` + `/live-traffic` →
   `/agents`.

**Phase 4 — Live topology diagram.**
1. `AgentTopology.tsx` xyflow canvas + node/edge types
   (agent/iface/veth/sensor/scenario).
2. `/local-sensor/{id}` + `/dashboard/live` merge → green-online, animated
   inject→sensor edge with live pps, sensor lit when enrolled.

**Phase 5 — Hardening.**
1. reconcile on backend boot (re-emit specs for all non-stopped LocalLabs).
2. teardown correctness; orphan detection; degraded-state surfacing; the
   "DB==host" invariant tested.
3. docs (CLAUDE.md section); agent `version.py` bump iff agent/ touched; tests.

---

## 4. Reuse map
- `CMLService.parse_sensor_compose` → token/serial/image/registry (verbatim).
- `generate_agent_token` / `hash_token` (agents.py) → agent row creation.
- `launch_updater` pattern (system_upgrade.py) → backend↔privileged-sibling via
  docker.sock + state volume (host-agent is long-lived, not one-shot).
- `scripts/local-sensor/*` proven ops → ported into host-agent watcher.
- Frontend: AgentsTab table, DeploymentCard, AggregateStatsRow, viz blocks,
  CmlTab JWT-decode preview, xyflow node/edge patterns.

## 5. Risks / watch-items
- Daemon reload must be reload/HUP, NEVER restart (would bounce the PacketArch
  stack) — validated manually.
- `macvlan_mode: passthru` claims the veth mon end exclusively — fine, mon end is
  dedicated per lab.
- `/cyber-vision/devices` `search` param is a no-op (see [[local_sensor_lab]]) —
  any "find my lab's devices" UI must paginate.
- Agent versioning rule: touching `docker/packetarch-agent/` or
  `protocol_engines/` requires a `version.py` bump (CLAUDE.md). host-agent image
  is separate, not subject to that rule.
- Idempotency: every host-agent op must be safe to re-run (reconcile relies on
  it). The "DB desired == host actual" invariant is the spine of the design.

## 6. Remaining minor confirmations (non-blocking)
- **Page name**: "Agents" / "Fleet" / "Remote Agents"? (working: "Agents".)
- **CV creds**: keep in Settings (current plan) or move to the hub too?

## 7. Out of scope
- Changing the CML flow itself (only relocating its UI into the hub).
- PCAP path, attack/adaptive subsystems.
- Remote (non-host) multi-tenant sensor orchestration.
