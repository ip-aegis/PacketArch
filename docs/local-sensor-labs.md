# Local Sensor Labs

> Moved out of `CLAUDE.md` on 2026-09-09 so the always-loaded file stays a map. Content unchanged.


App-managed, on-box labs that run a traffic agent **and** a Cisco Cyber Vision
docker sensor on the PacketArch host itself, wired through an isolated virtual
SPAN. This **augments** the CML integration (which stays fully functional) — it's
a second deployment target for when you don't want to stand up a CML lab.

# How it works

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

# Operator flow

Agents hub (`/agents`) → **Local Labs** tab → **New Local Lab** → paste the
docker-compose CV generates for a *docker* sensor → **Build**. The agent token is
shown once. Watch the **Topology** tab for the live agent→veth→sensor flow.
**CV provisioning tokens are single-use** — use a fresh sensor/token per lab.

# Lifecycle

- **Teardown = full delete**: stops sensor+agent containers, removes the veth and
  the per-lab macvlan network, drops the registry trust if unused, and deletes
  the `LocalLab` + `TrafficAgent` rows (UI ↔ backend stay in sync).
- **Survives restart**: the host-agent reconciles its persisted specs on its own
  boot; `startup.reconcile_local_labs()` nudges it on backend boot.

# Agent kinds

`TrafficAgent` carries `cml_lab_id` (CML) / `local_lab_id` (Local) / neither
(Manual). The Agents hub badges them and the deploy-time interface picker LOCKS
the injection interface for managed (Local/CML) agents.

# Key files

**Backend:** `models/local_lab.py`, `services/local_sensor_service.py`,
`services/host_agent_client.py`, `services/local_lab_naming.py`,
`api/routes/local_sensor.py`, `startup.reconcile_local_labs`.
**Frontend:** `pages/AgentsHubPage.tsx`, `components/agents/LocalLabsTab.tsx`,
`components/agents/AgentTopology.tsx`, `api/localSensor.ts`,
`stores/localSensorStore.ts`.
**Reference scripts** (manual equivalent): `scripts/local-sensor/`.

