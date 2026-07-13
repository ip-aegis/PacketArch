# PacketArch Mimic — Build Plan & Operating Model

Companion to the design memo (`tasks/emulator-agent-design.md`). The memo is the
north star (what & why); this file is how we build it and how to use Claude across
the effort. Confirmed direction (2026-07-13): fresh Mimic Studio canvas, shared
device-knowledge substrate, **maximum realism** (design vs. a real engineering
workstation + a skilled analyst), process-model library and userland TCP stack both
in scope as named goals.

---

## Part A — Operating model: how to best use Claude on this lift

### A.1 Three-level plan hierarchy (don't over-plan upfront)

- **L0 — design memo.** The architecture/north star. Changes rarely.
- **L1 — per-phase plan** (`tasks/mimic-pN-plan.md`). Authored in **plan mode**,
  you sign off before any code. One phase = one coherent vertical.
- **L2 — task checklist** inside each phase plan. Marked off as we go; a review
  section appended at phase end (CLAUDE.md task-management convention).

We only plan the *next* phase in implementation detail. P1–P4 stay as the memo's
roadmap sketch until their turn.

### A.2 Vertical-slice-first, seam-deep

The cardinal rule for a lift this size: **P0 is one thin end-to-end slice that
exercises every architectural seam** (Transport, ProcessModel, DataFabric
projection, ProtocolServer, DevicePersona, agent kind, deployment) — each stubbed
to its simplest *real* implementation, none faked. We get bytes on the wire and CV
classifying a real persona before building any breadth. This de-risks the
architecture while it's still cheap to change. Breadth (more protocols, the canvas,
off-box, the userland stack) is added *onto proven seams*, never alongside unproven
ones.

### A.3 Division of labor — where each mode of "me" earns its keep

| Work | Mode | Why |
|---|---|---|
| Architecture, seams/interfaces, integration, the novel risks (userland stack, projection consistency, write-back loop), decisions, verification | **Main thread (you + me)** | High context, hard reasoning — keep it where you can see and steer it |
| Research spikes: userland-stack lib bake-off, per-vendor TCP fingerprint data, protocol-server lib API surface | **Fresh subagent** (Explore/general-purpose) | Isolated, one tack, keeps my context clean; returns a conclusion not a file dump |
| Isolated implementation *after an interface is frozen* (e.g. "implement the BACnet projection against this interface"), test authoring, focused review | **Fresh subagent** | Parallelizable, well-scoped, low cross-talk |
| A parallel worker that must already know the whole design (e.g. draft P1 plan while I build P0) | **Fork** | Inherits my full context |
| The **breadth phase** (P3): implement N protocol projections + servers in parallel once the interface is locked; big-diff review | **Workflow (multi-agent)** | Embarrassingly parallel — but costs tokens and **needs your explicit "use a workflow" go-ahead**. Not before P3. |

**Not a workflow for P0** — it's a single integrated vertical, nothing to fan out.

### A.4 Cadence & repo hygiene

- **Feature branch** `mimic` — not master-direct. Big lift; keep master shippable.
- **Feature flag `MIMIC_ENABLED`** (follow the `features.py` / `config.py` /
  `about.ts` pattern) — Mimic stays dark until it's real.
- **New module tree**, zero entanglement with the generator path. Shared substrate
  is *imported*, never copied (memo §10.8).
- **Bump `docker/packetarch-agent/app/version.py`** on any agent change (project
  rule) — P0 touches the agent, so this applies.
- Each session ends on a **durable artifact**: a signed-off plan file, or a
  committed working slice. Never leave a phase half-built with nothing on disk.
- **Verify on the real app + real CV** every phase (`/verify`, `/run`); update
  `tasks/lessons.md` on any correction.

### A.5 Per-phase rhythm

```
plan mode → you sign off → I build the vertical → I verify on real CV/nmap
 → I demo the observable gate → commit on `mimic` → we review → next phase
```
Human checkpoints: plan sign-off, and post-verify demo.

### A.6 What I'll need from you (human-only)

- Ability to point a **real CV sensor / Local Lab** at the persona for verification,
  and a **fresh CV provisioning token** per lab (single-use — memory note).
- Decisions at each plan-mode checkpoint.
- Lab constraints for P2 (how many off-box hosts you can give me).
- Your **"use a workflow"** word when we hit P3 breadth (token cost is yours to OK).

---

## Part B — P0 plan: one Modbus persona, on-box, fooling real CV

**Deliberate scope call: P0 is headless (spec-driven, no canvas).** The highest
architectural risk is "does a bound emulated device on a namespace on the SPAN
actually behave like a real PLC to CV/nmap and evolve believable values" — that's
engine + network, not UI. Prove it first; build Mimic Studio in P1 on top of a
runtime that already works.

### B.1 Device choice (realism-correct)

A **Modbus-TCP-native** vendor so we don't violate protocol-accuracy (a Siemens PLC
would speak S7comm, not Modbus). Pick a **Schneider Modicon M580** (or M340)
template from the substrate — Modbus TCP native, and `pymodbus` is the most mature
server lib, so the protocol and the tooling line up.

### B.2 Seams to define correctly (so nothing re-architects later)

Even though P0 implements only the simplest branch of each, the **interface** is
frozen here:

1. `Transport` — `bind()/serve()`; owns TTL/window/MSS/ARP. P0 impl:
   `NamespaceKernelStack` (netns + veth/macvlan onto `pa-mon`, assign persona
   MAC/IP, set `ip_default_ttl` etc. from template `tcp_stack`). `UserlandStack`
   and `RealNIC` are declared, unimplemented.
2. `Projection` — `read(addr)/write(addr,val)` resolving against the ProcessModel.
   P0 impl: `ModbusProjection`. ENIP/S7/OPCUA projections are the same interface.
3. `ProtocolServer` — `parse_request → connection-state → projection → personality
   → build_response`. P0 impl: `ModbusServer` (wrap pymodbus; datastore delegates
   to the projection; FC43 identity from `FingerprintApplicator`; delay from
   `get_response_delay()`).
4. `DevicePersona` — the composition root binding Identity + Transport +
   ProcessModel + DataFabric + ProtocolServer(s) + (later) EventEngine/ClientLoops.
5. `PersonaSpec` (JSON) — the deploy contract the future canvas will emit. Author it
   by hand for P0.

### B.3 Process-model library — seed it here

Stand up the parameterized process-model library (a named goal) with its **first
model: a tank** (level ODE + first-order lag + Gaussian noise, one pump actuator).
Built on the existing `process_sim`. This is the library's first entry, not a
one-off — structured so reactor/pump-station/feeder models slot in later.

### B.4 Write-back loop (prove it in P0, minimally)

Wire **one** control point end-to-end: a Modbus write to the pump coil feeds the
ProcessModel as an input; the tank level then moves through the dynamics (not a
snap). This proves the hardest new coupling direction on the smallest case.

### B.5 Deployment (reuse Local Lab machinery)

Backend route takes a `PersonaSpec`, mints an agent token, writes a persona spec to
the shared `host_agent_state` volume; the privileged `host-agent` creates the netns
and launches the persona. Add an `EMULATE_DEVICES` command + a `DeviceEmulatorPool`
in the agent (own module tree, so it can later fork into a separate mimic-agent
binary). Backend stays unprivileged (memo + Local Lab pattern).

### B.6 Observable success gate (all must pass on real CV/nmap)

1. CV sensor classifies the persona as **Schneider Modicon M580** (via FC43).
2. `nmap -p502 --script modbus-discover` returns the correct device-ID string.
3. A Modbus client (`mbpoll`/pymodbus) reads holding registers showing values that
   **drift smoothly** per the tank ODE — not static, not random-per-poll.
4. Writing the pump coil **visibly changes** the level trend (write-back proven).
5. Observed **TTL on the wire matches the template**, not the host's Linux 64.
6. A malformed Modbus PDU returns a **correct exception**, not a crash/hang.

### B.7 P0 task checklist

**Sub-phase 1 — runtime core (lab-independent, DONE 2026-07-13):**
- [x] Branch `mimic`; add `MIMIC_ENABLED` flag (off) end-to-end (config → features
      → about.ts → useFeatures).
- [x] New module tree `backend/app/mimic/`; import — not copy — the shared substrate.
- [x] Define & freeze the 5 interfaces (B.2) in `interfaces.py` + `transport.py`.
- [x] Process-model library scaffold + tank model (`process_library/`).
- [x] `ModbusProjection` (address↔variable map) + write-back (pump coil, write-through
      bit state for read-back consistency).
- [x] `ModbusPersonaServer` on pymodbus 3.8, live datastore → projection, FC43
      identity from fingerprint. (Response-delay/error via applicator = later refinement.)
- [x] `DevicePersona` composition root + `PersonaSpec` JSON schema + `run.py` entrypoint.
- [x] Self-test gate (`tests/mimic/`): identity, drift, write-back, out-of-range
      exception — **all PASS** against a live loopback persona.
- [x] pymodbus added to backend `pyproject.toml`.

**Sub-phase 2 — deployment + real-CV verification (needs the lab):**
- [ ] `NamespaceKernelStack` Transport: add netns primitive to host-agent
      `hostops.py` (netns + veth/macvlan onto `pa-mon`, MAC/IP, `tcp_stack` sysctls
      incl. TTL); host-agent `emulate` action; `run.py` launched inside the netns.
- [ ] Deployment: backend route → host-agent spec (persona spec on shared volume);
      agent `EMULATE_DEVICES` + `DeviceEmulatorPool`; bump agent `version.py`.
- [ ] Verify remaining B.6 gate on real CV + `nmap modbus-discover` + wire TTL; demo.
- [ ] Review section + lessons; rebuild backend image (pymodbus baked in).

*Commit checkpoint: sub-phase 1 committed on `mimic`.*

**Tracked follow-ups (not P0-blocking):**
- pymodbus pinned to `>=3.8.0,<3.9.0` (validated). 3.9+ reworked the
  datastore/context API (`ModbusSlaveContext`→`ModbusDeviceContext`, custom
  datablock `getValues/setValues/validate` removed for a new extension model).
  Migrating `_LiveBlock` + `ModbusPersonaServer` to 3.14 needs re-validation
  against the gate — do it deliberately, not via an unpinned bump.
- Response-delay + error-injection through `FingerprintApplicator`
  (`get_response_delay`/`should_inject_error`) at the Modbus layer — realism
  refinement deferred from the P0 core.
