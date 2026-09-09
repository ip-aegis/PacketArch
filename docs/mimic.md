# PacketArch Mimic (device emulation)

> Moved out of `CLAUDE.md` on 2026-09-09 so the always-loaded file stays a map. Content unchanged.


A **separate path** from scenario traffic generation, with its own canvas, deploy
flow and runtime. A scenario **replays** traffic onto the wire; a Mimic persona
**binds a real socket and answers** as the device it imitates. A scanner, an HMI
or a Cyber Vision sensor can interrogate it and get real protocol responses,
because there is a live server on the other end rather than a recording.

**Gated by `mimic_enabled`, default `false`** (`core/config.py`). Flag off ⇒
`/api/v1/mimic/*` 503s and the `/mimic` + `/mimic/studio` routes redirect.

# Why it exists

Scenario traffic cannot be polled. Anything that *interrogates* a device — an
active scanner, a discovery tool, an HMI pointed at a PLC, DPI that reads
identity objects — needs something listening. Mimic answers reads AND writes, so
Modbus FC43, an OPC UA browse, or a BACnet device-object read return real data.
Use a scenario for volume, breadth, PCAP and attack playbooks; use Mimic when
something has to talk back.

# How it works

- **Cell** = the unit of deployment: one or more personas sharing a segment,
  able to poll each other. Personas reuse the same 332-template fingerprint
  substrate as scenarios, so OUI, identity strings and firmware match the
  claimed device.
- **Persona** (`mimic/persona.py`) binds identity + transport + process model +
  per-protocol projections + protocol servers into one running device, and
  drives the process model on a **wall-clock tick**. Personas are reactive, so
  they live on wall time — never a virtual-time heap.
- **Protocol servers** (`mimic/servers/`): Modbus TCP, OPC UA, BACnet,
  IEC 60870-5-104.
- **Live values**: registers/nodes are driven by `mimic/process_library/`
  (tank, tank_control, chemical_reactor, heat_exchanger, compressor_station,
  pump_station, power_feeder) under closed-loop PI control. Writing a setpoint
  through a protocol client moves the loop and the read-back reflects it.
- **Active personas** (`mimic/poll.py` → `ClientLoops`) poll their peers over
  the peer's NATIVE protocol, so the segment carries real request/response
  traffic with no generator involved.
- **Certification gate** (`mimic/certification.py`): "we have a server for that
  protocol" is necessary but NOT sufficient. A persona only ships if it also
  returns the correct device identity over that protocol (FC43 / OPC UA
  BuildInfo / BACnet device object — what CV actually classifies on) and the
  chosen deploy target can serve it. Only certified cells are offered for deploy.

# Two deploy targets

- **On-box** (`mimic/deploy.py`, `docker_deploy.py`) — personas run on the
  PacketArch host in a hub-bridge + netns segment inside an **existing Local
  Lab**, classified by that lab's existing CV sensor. **No CV token and no new
  sensor.** The unprivileged backend only writes a `kind="mimic"` spec to the
  host-agent file-queue; the privileged host-agent provisions it.
- **Off-box** (`mimic/slim/`, `slim_deploy.py`, `slim_author.py`) — each persona
  is its own 512 MB **bare Alpine CML node** (a real host with a real stack, no
  Docker). The backend **resolves identity from the substrate at deploy time**,
  so the node ships no template catalog. `slim_sensor.py` can auto-provision a
  CV sensor on a CML node with an IOSvL2 SPAN.

# Gotchas (all learned in anger — see `docs/gotchas.md`)

- **Rebuild BOTH backend and host-agent.** A Mimic change that only rebuilds the
  backend leaves a stale host-agent that doesn't know the `mimic` spec kind:
  teardown silently no-ops and reconcile stamps `error: 'mon_if'` every cycle
  (it routes the mimic spec into the local-sensor path, which expects a
  `mon_if` the mimic spec doesn't have). `docker compose up -d --build host-agent`.
- **CML node bootstrap: `cmd &` does not survive the boot shell**, and
  `rc-service local start` is a no-op (Alpine's `local` already ran). Launch with
  `start-stop-daemon --start --background` so it double-forks and reparents to init.
- **Pin every dep in the node bootstrap.** A bare `pip install pymodbus` on a
  fresh node grabs the latest and breaks against the pinned API. The node
  inherits no poetry/lock constraints — repeat the local pin.
- **Use an unverified SSL context for node check-ins.** The backend cert is
  self-signed; stdlib `urllib` raises `CERTIFICATE_VERIFY_FAILED` and a bare
  `except` swallows it, so the persona runs but never reports.
- **A client-only persona's vendor is its MAC OUI and nothing else** — it never
  answers a query, so CV has no other evidence to classify it on.
- **CV sensor on CML needs its capture NIC up + promiscuous**, and a
  vendor-plausible MAC.
- Slim protocol breadth uses **lazy protocol imports** (one missing wheel must
  not break the others); IEC-104 off-box still needs a musl `c104` wheel.

# Key files

**Backend:** `mimic/interfaces.py` (`PersonaSpec` / `ProtocolBinding` /
`PointBinding` — the JSON deploy contract), `mimic/persona.py`,
`mimic/certification.py`, `mimic/presets.py`, `mimic/servers/`,
`mimic/process_library/`, `mimic/projections/`, `mimic/slim/`,
`mimic/deploy.py`, `mimic/cml_deploy.py`, `api/routes/mimic.py`.
**Frontend:** `pages/MimicPage.tsx`, `pages/MimicStudioPage.tsx`.
**Help:** `content/help/mimic.tsx`.

