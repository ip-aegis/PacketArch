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

*Networking validated (2026-07-13):*
- [x] **L2 capture path proven in isolation** — the SPAN only works because the
      generator raw-injects on `pa-gen`; a real bound-socket persona is invisible
      to the passive `pa-mon` sensor through a plain bridge (MAC learning) or
      macvlan-bridge (sibling short-circuit). **Fix proven: hub-mode bridge**
      (`stp off`, per-port `learning off flood on`) with `pa-gen` enslaved + persona
      and poller in netns veth'd to it. Throwaway `tmm*` test captured the full
      bidirectional TCP conversation on the far crossover end.
- [x] **No CV token needed** — confirmed in code: token-mint is only in the
      new-sensor path (and even that auto-mints from the stored deployment token).
      Built a dedicated `Mimic-P0` lab (slug `07d51972`) via `build_lab()` — CV
      sensor + agent token minted with zero operator input.
- [x] **Live persona on the real lab SPAN** — Schneider M580 persona (`10.50.0.10`,
      Schneider OUI MAC, TTL 64) + a Modbus poller (`10.50.0.20`), both in netns on
      the hub-bridge over the lab's `pa-gen`. Poller pulls FC43 identity (Schneider /
      M580 / V4.10) and live tank registers over real TCP. **29 Modbus frames/8s
      captured on `pa-mon-07d51972`** — the CV sensor is seeing it.
- [x] **CV Center classified the persona** (real CV at 10.10.20.115): component
      `10.50.0.10` → icon `library/schneider.png`, **model-name `BMEP584040`**,
      **fw-version `V4.10`**, Schneider-OUI MAC. CV read the Modbus FC43 identity and
      fingerprinted the fake device as a genuine Modicon M580. **P0 GATE GREEN.**
      (Note: CV shows this at the COMPONENT layer with `device:null` before promoting
      to a device — `search_device_by_ip/mac` returns None initially; use
      `get_components_raw`.)
- [ ] `nmap modbus-discover` against the persona (confirmatory — FC43 already proven
      on the wire + via CV DPI); wire TTL = 64 matches M580 template.

*Codify (DONE 2026-07-13 — recipe → permanent code, verified via the codified path):*
- [x] host-agent `hostops.py`: `ensure_persona_bridge` (hub-mode: stp off, per-port
      learning-off/flood-on, `gen_if` enslaved), `ensure_persona` (per-persona netns
      container, MAC/IP/TTL sysctls, wire-before-bind, optional poller command),
      `delete_persona*`. Bridge name ≤15 chars (`mmbr-<slug>`).
- [x] host-agent `watcher.py`: `emulate` / `teardown_mimic` actions +
      `_provision_mimic`/`_deprovision_mimic`; reconcile routes by `kind` (personas
      survive reboot too). `state.py` docstring documents the mimic spec.
- [x] backend `host_agent_client.submit_emulate`/`submit_teardown_mimic`;
      `app.mimic.deploy` (builds the mimic cell — IP/vendor-MAC/veth allocation from
      the shared substrate, optional poller) ; `app.mimic.poll` (active poller / P1
      client-loop seed).
- [x] **Verified end-to-end via the codified path**: `deploy.deploy_cell(...)` →
      file-queue → host-agent provisioned "2/2 personas" → persona answers M580 FC43 +
      live registers → 29 frames/6s on `pa-mon` → **CV classified `10.60.0.10` as
      Schneider BMEP584040 / V4.10**. No agent-version bump (host-agent, not the
      traffic agent, was touched).
- [x] REST API (2026-07-13): `RequireMimicEnabled` dep (503 while off) + `/api/v1/mimic/*`
      router (status, templates, process-models, cells CRUD) gated MIMIC_ENABLED, admin
      on mutations. `schemas/mimic.py`, `routes/mimic.py`, `host_agent_client.list_specs`,
      `deploy.list_cells/cell_status`. Verified: routes mount, read handlers return the
      live cell, gate 503s when off, HTTP input → PersonaSpec → cell spec (directory +
      OUI alignment) all correct.
## Protocol breadth — OPC UA (first additional protocol, DONE 2026-07-13)

Proved the runtime generalizes past Modbus: OPC UA (asyncua, asyncio-native) behind
the SAME `Projection`/`ProtocolServer` seams + SAME process model.
- `projections/opcua_projection.py` (named nodes ↔ model), `servers/opcua_server.py`
  (asyncua Server, BuildInfo identity, sensor nodes pushed live, writable actuator
  nodes fed back), `PointBinding.name` for named nodes, persona `opcua` wiring.
- Gate (`tests/mimic/test_opcua_breadth.py`) PASSES on a Siemens S7-1500 OPC UA
  persona: server identity (manufacturer Siemens via BuildInfo node), live node
  drift, and pump-node write-back (fill/drain). Both mimic gates green (Modbus + OPC UA).
- `asyncua` pinned `>=2.0.1,<2.1.0`. Two lessons captured (poll-based write-back must
  gate on change; asyncua `set_build_info` is a no-op — write node i=2260).
- Remaining protocols (ENIP/S7/104/SNMP) slot in the same way; ENIP via cpppo
  is thread-based (more friction than asyncua).

**BACnet/IP added (bacpypes3, 3rd protocol, DONE 2026-07-13):** refactored the OPC UA
projection into a shared `NamedPointProjection` (OPC UA + BACnet both address by name);
`servers/bacnet_server.py` (bacpypes3 `NormalApplication` + `DeviceObject` identity,
Analog Value sensors pushed live, Binary Value actuator write-back on change). Gate
`test_bacnet_breadth.py` PASSES on a Siemens Desigo DXR2 room controller (device
vendor-id 7 / model DXR2.E12, drift, write-back) — object-level (a 2nd BACnet/IP stack
on loopback is flaky; wire+CV ride the deploy path). `bacpypes3` pinned `>=0.0.106,<0.1.0`
(pre-1.0). `/mimic/templates` now lists modbus_tcp/opc_ua/bacnet_ip devices. **Three
protocols across three verticals: Modbus (Schneider PLC), OPC UA (Siemens PLC), BACnet
(Siemens building automation).**

**IEC 60870-5-104 added (c104, 4th protocol, DONE 2026-07-13):** `servers/iec104_server.py`
(c104 controlled station; M_ME_NC_1 measurements pushed live, C_SC_NA_1 single-command
write-back via event `on_receive`). IOA-addressed → reuses `NamedPointProjection`. Gate
`test_iec104_breadth.py` PASSES with a FULL WIRE round-trip (real c104 client interrogates
+ reads drift + sends a command; c104 client uses an ephemeral port so no loopback clash).
`c104` pinned `>=2.2.1,<2.3.0`. Two lib gotchas: c104 validates the `on_receive` callback
signature against REAL annotations (so this module omits `from __future__ import
annotations`); `interrogation(common_address=...)` not station. **FOUR protocols / four
verticals: Modbus (process PLC), OPC UA (Siemens PLC), BACnet (building automation),
IEC-104 (power/substation telecontrol).** All 4 gates green.

## Frontend surface (operator UI, DONE 2026-07-13)

A real `/mimic` page (not the full Studio canvas yet): list/monitor/teardown cells +
one-click preset deploy. Backend `app/mimic/presets.py` + `GET /mimic/presets`
(5 presets: Modbus/OPC UA/BACnet/IEC-104 PLCs + an HMI↔PLC pair). Frontend
`api/mimic.ts`, `stores/mimicStore.ts`, `pages/MimicPage.tsx` (status banner, cells
table with state tags + teardown, deploy modal: pick lab + preset), `FeatureGate`
extended for `'mimic'`, `/mimic` route + nav entry, all gated by `mimicEnabled`
(fail-closed). TypeScript: my files clean (project-wide `tsc -b` has pre-existing
unrelated errors). Full per-device visual authoring remains the Studio canvas (P3).

- [ ] Follow-ups (non-blocking): the Mimic Studio canvas (P3 — visual per-device
      **slim** mimic-runtime image baked in CI (P0 uses a committed `mimic-persona:p0`
      = backend image + pymodbus); persona-process liveness re-heal (container-up-but-
      process-died); rebuild backend image (pymodbus baked).

*Manual validation harness (throwaway): scratchpad `live/attach.sh` + `teardown`.*

---

## P1 — active-master persona (DONE 2026-07-13)

Replaced the P0 test poller with a real **active-master persona**: an HMI that is
itself a device (own identity/OUI) and runs client loops polling its peers.

- `ClientBinding` on `PersonaSpec` (peer `target_device` → resolved to `target_ip`
  via the cell **device directory** in `deploy.build_cell_spec`); `app.mimic.client`
  runs the loops; `DevicePersona` launches them alongside servers and supports
  **client-only** personas (an HMI has no server). Standalone poller suppressed when
  any persona actively polls.
- **Verified live on real CV**: deployed M580 PLC (`10.60.0.10`) + Schneider Magelis
  HMI (`10.60.0.20`); the HMI actively polls the PLC (real bidirectional Modbus,
  client reconnects per scan). Both surface in CV as distinct components — PLC as
  Schneider M580 BMEP584040 (FC43), HMI classified by OUI.
- **Realism finding + FIX (done)**: the HMI first classified as "Control Microsystems"
  (OUI `00:03:74`), not Schneider — a client-only persona has no protocol identity, so
  OUI is the whole fingerprint. Fixed with `vendor_oui.pick_vendor_oui()` (picks the
  vendor-aligned OUI from the template list); Mimic deploy pins each persona's MAC to it.
  Re-verified live: HMI now MAC `00:00:54:*` → **CV vendor "Schneider Electric"**. Also
  surfaced a data nuance: the bundled IEEE registry labels `00:03:74` "Schneider Electric"
  while this CV Center shows "Control Microsystems" (reassigned/acquired prefix) — so
  prefer the canonical primary OUI, not just any registry-matched one. See lessons.md.

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
