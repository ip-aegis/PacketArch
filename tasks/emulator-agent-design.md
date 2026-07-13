# PacketArch Mimic — Device-Emulation Workflow (Design Memo)

**Status:** Design exploration (2026-07-13). Not started. No existing code touched.
**Name:** **PacketArch Mimic** (working name). Canvas = *Mimic Studio*; agent kind =
*mimic agent* (hosts one or more *device personas*); deployment = *mimic deployment*.
Alternatives considered: Persona, Twin, Emulation Range — "Mimic" wins for being
short, distinct from "generate," and non-committal on honeypot/twin framing.
**Premise:** A *new* agent kind that binds real sockets and answers real protocol
requests as a specific industrial device — deployed N-per-cell (ideally **many
off-box agents**, on-box for dev/test) so a fleet (HMIs, PLCs, an EWS, an EWON)
actually converse with each other and with real scanners. This is an **entirely
separate canvas → deployment → agent path**; it augments and does not alter the
existing generator path.

> **Sections 1–8 are the original analysis (still valid). Section 9 is the
> 2026-07-13 review + the separate-workflow reshape — read it first.**

---

## 1. The core reframe

Everything PacketArch does today is **two-sided synthesis**: one process crafts
*both* the master's request and the slave's response as raw Ethernet bytes on a
virtual-time event heap, then injects them with `scapy.sendp(Raw(...))`. Nothing
in the platform ever binds, listens, or reacts to a received packet. A passive
SPAN/Cyber Vision sensor sees a believable bidirectional conversation between two
MAC/IPs **that don't exist as hosts**.

The emulator flips this for a chosen set of devices:

| | Generator agent (today) | Emulator agent (proposed) |
|---|---|---|
| Network role | Injects crafted frames for *both* sides | Owns an IP/MAC, binds ports, **answers** |
| Who sees it | Passive sensor on a SPAN | Any active peer — Nmap, a real HMI, CV Active Discovery, another emulator |
| Timing | Virtual clock, paced at inject | **Wall clock**, reactive |
| Device count per agent | One process = all devices | One agent = one (or a few) real endpoints |
| Interactivity | None (fire-and-forget) | Real request → real response |

The payoff is realism that passive replay can't reach: an emulated device
responds correctly to an *unscripted* query (a scanner's malformed request, an
operator's manual poll, a peer emulator's retry), and its register values move
because a process model is actually running behind them.

---

## 2. What we already have (transfers directly)

The research found the platform is unusually well-positioned because the
"how does this device answer query Y" logic is already factored out of the
injection timeline:

- **Response builders as pure functions.** `identity/` is a registry of
  `ProtocolIdentityBuilder` subclasses (modbus, ethernet_ip, profinet, s7, snmp,
  bacnet, opc_ua, dnp3, iec104) with `build_raw_response(identity, **kwargs) ->
  bytes` and `build_identity_response(...)`. Engines call these today to fabricate
  the response half of a poll. A responder calls the *same* functions, triggered
  by a real inbound packet instead of a scheduled event.
- **`FingerprintApplicator`** already exposes exactly the behaviors a live server
  needs: `get_response_delay()`, `should_inject_error()`, `get_random_exception_code()`,
  `should_timeout()`, `should_retry()`, `get_tcp_options()` (TTL/window/MSS),
  `get_identity_response(protocol, ...)`. This is the device's "personality" and
  it's reusable unchanged.
- **Deterministic identity.** `canonical_identity.py` produces byte-identical
  MAC/hostname/station-name/serials from `(device_id, scenario_id)`. Two agents
  derive the *same* identity for the same device with zero coordination — which is
  what lets one agent "be" a device while another polls it.
- **332 device templates** (`device_templates/`) carrying per-protocol identity
  dicts, `tcp_stack`, `response_timing` (gaussian mean/stddev + outlier model),
  `error_behavior` (exception/timeout probabilities), and `firmware_variants` with
  CVEs + `identity_overrides`. This is the fingerprint substrate a credible
  emulator needs (see §6).
- **The ODE process-sim** (`protocol_engines/process_sim/`) is real and running:
  `ProcessModel.step(dt)` does forward-Euler integration, `ProcessVariable` adds
  first-order lag + Gaussian noise + clamping + per-state setpoints, `controller.py`
  ticks it and pushes values into the payload generator. This is the physics that
  makes register values believable over time — the single hardest thing to fake
  (see §5).
- **Clean plug-in seams.** `register_engine`/`get_engine`, the `PacketOutput`
  Protocol, and the `topology_plan`/`span_interface_map` threading through
  `agent_manager.deploy_scenario` → `_handle_start_scenario` → `pool.start` give us
  the exact pattern to mirror for a responder registry, a server "sink," and an
  `emulation_plan`.

**Bottom line:** the "server-side serialization" and "physical state" halves
already exist. We're building the "parse the client's request" and "own the
endpoint on the wire" halves.

## 3. The gaps (what's genuinely net-new)

1. **No read path anywhere.** Every sink (`LiveOutput`, `LiveTopologyOutput`) is
   send-only `sendp`/`L2Socket.send`. No `bind`, `listen`, `recv`, `sr1` in the
   backend or agent. Confirmed by grep across the whole tree.
2. **No request parser.** Engines only *build* PDUs. We have `build_request` and
   `build_response`; we need `parse_request(bytes)`. The layouts are symmetric
   `struct` packs, so this is mechanical, not hard — but it doesn't exist.
3. **No addressable data store.** Register values today are positional/random
   (`reg_0, reg_1, …` by request order) or process-sim trend values bound by
   *sensor name heuristic*. A responder needs a real `{address: value}` bank
   (holding regs, coils, CIP tags, S7 DB areas, DNP3 points) keyed by the address
   the client actually asks for, backed by the process model.
4. **State machines are dead scaffolding.** `ModbusConversationMachine` /
   `EtherNetIPConnectionMachine` exist but are instantiated nowhere. A real
   responder must enforce connection state (reject a CIP read before
   RegisterSession, honor Modbus unit-id routing, track OPC UA sessions).
5. **Identity is "bytes in a frame," not a bound endpoint.** Today MAC/IP live only
   inside crafted header bytes. An emulator must actually *own* the IP on its
   interface and answer ARP — which forces a networking decision (§ deployment).
6. **No multi-actor deployment.** The multi-sensor topology feature multiplies
   *observation points* (one conductor fans frames to N SPANs), not *actors*.
   True agent-per-device is new deployment logic.

## 4. State of the art — where this lands

The field splits cleanly and **nothing open bridges the split**:

- **Honeypots** (Conpot, HoneyPLC, GasPot, ICSpot, LLMPot) — good fingerprints,
  bind real sockets, but passive: they answer an external scanner and mostly don't
  talk to each other. Conpot is static-XML responses (registers never move) and
  widely detected; HoneyPLC is high-interaction but S7-only.
- **Testbeds / digital twins** (GRFICS, MiniCPS, DHALSIM, OT-sim, ICSSIM,
  ICS-SimLab, FORGE, SCEPTRE) — real device-to-device conversations and real
  process models, but built for labs, not fingerprint-hardened, and mostly
  Modbus-only on the client side.

**No open framework combines believable per-device fingerprints with
self-generated multi-device conversations across the full OT protocol matrix.**
That is precisely the space this feature occupies — and PacketArch already owns
the fingerprint substrate the honeypot world guards jealously. Key patterns worth
copying, each verified in the survey:

- **GRFICS value-realism recipe:** process model → shared-state layer at model
  rate → linear scale to 16-bit counts with clamping → protocol server reads state
  at poll rate → closed-loop control writes back through registers.
- **FORGE central virtual-clock coordinator** for device-to-device conversation
  timing at scale — which maps onto PacketArch's existing virtual-clock/heartbeat
  design.
- **The anti-fingerprint checklist** (§6) — the specific tells that out real
  honeypots today.

**Library maturity (server-side, Python):** Modbus (`pymodbus` 3.14, best-in-class
writable datastore), EtherNet/IP (`cpppo`), S7comm (`python-snap7` 3.0 — new pure-
Python server), BACnet (`bacpypes3`), IEC-104 (`c104`/iec104-python), OPC UA
(`asyncua`), SNMP (`snmpsim`+`pysnmp`) are all solid. **DNP3 is the one real gap**
(only the archived `opendnp3`-based `dnp3-python`; healthy stack is Rust with no
Python binding) — budget an FFI shim or hand-roll. **PROFINET and IEC-61850
GOOSE/SV** (L2) also lack clean Python servers; hand-roll on raw sockets or defer.

## 5. Proposed architecture

### 5.1 A new agent kind, not a modified one

Add an `EMULATE_DEVICES` command alongside `START_SCENARIO` in the agent
`main.py`, branching to a **new `DeviceEmulatorPool`** parallel to
`OrchestratorPool`. The existing generator path is untouched. The command payload
carries an `emulation_plan`: which devices *this* agent owns, each with its bound
IP/port set, its `vendor_fingerprint`, and its process-variable bindings.

```
EMULATE_DEVICES {
  scenario_id,
  devices: [ { device_id, ip, mac, ports:[{proto,port}],
               vendor_fingerprint, process_bindings:[…] } ],
  clock: { mode: "wall" }        # emulators live on wall time, never the heap
}
```

### 5.2 The responder core

Per emulated device, per protocol, a small async server. Reuse the mature Python
server libs where they exist (pymodbus/cpppo/asyncua/bacpypes3/c104/snap7) and
wrap them so their datastore reads/writes go through **our** address→value store;
hand-roll the thin ones (DNP3, PROFINET, GOOSE) on raw sockets using the existing
byte builders. Each server:

1. Accepts a connection, enforces protocol connection-state (the currently-dead
   state machines finally get wired in here).
2. On a request: `parse_request(bytes)` → look up address in the data store →
   apply `FingerprintApplicator` personality (delay via `get_response_delay()`,
   occasional `should_inject_error()`/`should_timeout()`) → serialize via the
   existing `build_*_response` / `build_raw_response` → send.
3. Answers identity queries (Modbus FC43, CIP Identity, S7 SZL, SNMP sysObjectID,
   BACnet) straight from `FingerprintApplicator.get_identity_response(...)` — this
   is the part that already works.

A `register_server(ProtocolType)` registry mirrors `register_engine`.

### 5.3 The addressable data store, backed by the ODE

The new object is a per-device **`DeviceDataStore`**: `{address → value}` for
holding regs, input regs, coils, discrete inputs (Modbus); CIP tags (ENIP); DB
areas (S7); points (DNP3/104). Values come from three tiers:

- **Bound to a process variable** — an explicit `address ↔ ProcessModel variable`
  map (replacing today's name-heuristic sensor binding). The reactor pressure ODE
  writes holding register 40001; a write to coil 17 flips a valve setpoint that the
  ODE integrates. This is the GRFICS closed loop, done properly with real
  addresses.
- **Static identity/config** — serials, firmware, nameplate (from the template).
- **Free-running** — counters, uptime, heartbeat regs on wall-clock.

One `ProcessModel` can span several devices on one agent (a cell's shared
physics), or devices on different agents can each run their slice and stay
loosely coupled through the traffic itself (an HMI reads a PLC's register; the
value it gets *is* the PLC's live ODE output). The survey's noise/diurnal gap is
our differentiator: layer sensor noise + thermal/hydraulic lag + diurnal cycles on
the process variables — no surveyed open tool does all three.

### 5.4 Multi-device coordination — the interesting part

Three coupling options; recommend starting with (a), earning (c):

- **(a) Emergent via real traffic (recommended first).** Devices don't share
  state at all — an HMI emulator runs a real Modbus *client* loop polling the PLC
  emulator's real IP. The conversation is real; coordination is just "the network."
  This is the honeypot-world's unsolved problem and the highest-realism payoff for
  the least shared machinery. Requires an **active-master** side (client loops)
  in addition to responders — reuse the existing `build_request` PDUs.
- **(b) Shared state store** for devices co-located on one agent (SQLite/in-mem,
  the MiniCPS pattern) — cheap intra-cell physics coupling.
- **(c) Central virtual-clock coordinator** (the FORGE pattern) if we later want
  deterministic, faster-than-real-time, reproducible conversation timing across
  agents. Aligns with PacketArch's existing virtual clock. Defer until (a) works.

### 5.5 Networking / deployment — the hard practical question

An emulator must *own* an IP and answer ARP, which the in-frame-only model never
had to. Options, cleanest first:

- **Per-device network namespace / macvlan** on the emulator host, each with the
  device's MAC/IP, ports bound inside. This dovetails with the existing Local
  Sensor Lab machinery (`host-agent`, `hostops.py` veth/macvlan, `pa-gen`/`pa-mon`
  SPAN) — the CV sensor already watches `pa-mon`; point the emulated devices at the
  same isolated segment and CV sees a live, interactive OT cell instead of a
  replayed one. This is the natural home: **one Local Lab, but the devices are real
  responders on the SPAN rather than one conductor injecting both sides.**
- Set per-namespace TTL/window to the vendor value (see §6) — an emulator host's
  Linux default TTL of 64 is the #1 honeypot tell today.
- The deploy-time interface picker (`agent_manager`) already threads managed
  plans; add `emulation_plan` beside `topology_plan`.

## 6. Realism / anti-fingerprint requirements (non-negotiable)

Real scanners fingerprint via Nmap NSE (`modbus-discover`, `s7-info`,
`enip-info`, `bacnet-info`), Shodan, Censys cross-protocol correlation, and CV
Active Discovery. The specific tells that catch honeypots today, each with a
concrete requirement:

1. **Vendor-matched initial TTL / TCP stack** at the *host*, not the container.
   ("Time-to-Lie" fingerprinting found 64 honeypots via a leaked Linux TTL of 64.)
   We already model `tcp_stack` in templates — now it has to reach the kernel/nsapi,
   not just crafted bytes.
2. **Per-instance unique serial, consistent across ALL protocols.** Conpot ships a
   hardcoded ENIP serial `7079450` on every instance; CIP spec requires globally
   unique serials. Our `canonical_identity` serials already satisfy this — enforce
   it end-to-end.
3. **Cross-protocol identity consistency** — same vendor/model story over S7comm,
   ENIP, SNMP, HTTP (Censys indexed a Conpot in ~31 min off a Siemens-vs-Allen-
   Bradley mismatch). Our unified template identity already gives this; don't let a
   server override drift.
4. **OUI-vendor alignment** (already a PacketArch realism dimension; CV keys
   manufacturer off OUI).
5. **Complete identity objects + correct error handling on malformed requests** —
   full Modbus MEI 0x00–0x02, full CIP Identity, S7 SZL 0x001C, DNP3 Object 0; and
   a *correct* exception, not a crash or silence, on a bad PDU.
6. **Constrained-hardware latency** — a PLC answers slower and jitterier than a
   cloud VM. `response_timing` already models this; route responder delay through
   `FingerprintApplicator.get_response_delay()`.

These map almost 1:1 onto PacketArch's existing 5 realism dimensions — the
substrate is there; the new work is enforcing it at a *bound endpoint*.

## 7. Phased roadmap

- **P0 — Spike (1 protocol, 1 device).** `pymodbus` server wrapped around a
  `DeviceDataStore`, values from one `ProcessModel`, identity from
  `FingerprintApplicator`. Deploy in a network namespace on the dev box; scan it
  with `nmap --script modbus-discover` and point Cyber Vision at it. Success = CV
  classifies it as the right vendor/model and registers drift believably.
- **P1 — Two-device conversation.** Add an active Modbus *master* loop (HMI
  emulator) polling the P0 PLC. Success = a real, unscripted HMI↔PLC conversation
  on the SPAN, CV shows the flow, values move under load.
- **P2 — Protocol breadth.** ENIP (cpppo), S7comm (snap7), BACnet (bacpypes3),
  IEC-104 (c104), OPC UA (asyncua), SNMP (snmpsim). DNP3 via FFI/hand-roll.
- **P3 — The 10-device cell.** Declarative `emulation_plan` (HMIs, PLCs, EWS,
  EWON, RTUs) auto-derived from a scenario definition, deployed across one or more
  emulator hosts, wired into the Local Sensor Lab SPAN. Anti-fingerprint checklist
  enforced by a readiness check.
- **P4 — Coordination & scale.** Shared-state intra-cell physics; optional FORGE
  virtual-clock coordinator; TTL/stack hardening per namespace.

## 8. Risks & open questions

- **PCAP↔live parity is a stated platform invariant** (memory: PCAP output must
  match live for the same scenario). An interactive emulator has *no* PCAP twin by
  nature — its whole value is unscripted reactivity. Decide explicitly: emulator
  mode is **live-only** and exempt from the parity rule, OR we also render a
  representative PCAP from a recorded emulator session. Recommend: live-only,
  documented as a distinct mode (like the scenario-mode flag pattern in memory).
- **Privilege / blast radius.** Owning IPs, ARP, per-namespace TTL means more host
  interaction. Keep it inside the existing privileged `host-agent` boundary; the
  backend stays unprivileged.
- **DNP3 / PROFINET / GOOSE** have no clean Python server — scope them to P2+ and
  budget FFI or raw-socket hand-rolling.
- **Address↔variable binding** is the real modeling work: today's binding is a
  name heuristic; a believable emulator needs an explicit per-template
  register-map ↔ process-variable map. This is where the domain effort goes.
- **Agent versioning:** any change under `docker/packetarch-agent/` bumps
  `app/version.py` (project rule).
- **Detection is adversarial and moving** — treat the §6 checklist as living;
  the TTL tell was a 2024 result.

---

## 9. Review + separate-workflow reshape (2026-07-13)

### 9.1 Review of the findings — what holds, what to refine

The codebase map is trustworthy: three independent code-reading passes converged
on the same load-bearing facts (generate-then-emit, zero read/bind path, identity
factored out of the timeline). Two refinements after a critical re-read:

- **"Reuse the response builders unchanged" is true for *identity*, partial for
  *data*.** Discovery/identity responses (Modbus FC43, CIP Identity, S7 SZL, SNMP
  sysObjectID, BACnet nameplate) are query-independent and transfer verbatim from
  `FingerprintApplicator.get_identity_response(...)`. But *data* responses (read
  holding registers, read tags) take their values as an input list today — the
  builder serializes whatever it's handed; it does not look a value up by address.
  So the address→value store (§5.3) is not optional polish, it's the core new
  object, and it's the seam every data-plane read flows through.
- **Determinism-from-`(device_id, scenario_id)` is nice-to-have here, not load-
  bearing.** In the generate-both-sides model it mattered because two agents had to
  independently agree on an identity. In Mimic, each persona is authored once and a
  deployment *tells* its agent the exact identity — no independent re-derivation.
  Keep the deterministic serials for reproducibility, but the design doesn't lean
  on them for correctness.

Everything else in §1–8 stands.

### 9.2 The one thing NOT to separate

The instinct to make Mimic a separate canvas → deploy → agent path is right at the
**workflow, orchestration, deployment-tracking, agent-binary, and UI** layers.
But do **not** fork the device-knowledge substrate. These stay shared libraries,
imported by both paths:

`device_templates/` (332 templates) · `vendor_oui.py` · `canonical_identity.py` ·
`FingerprintApplicator` · `identity/` builders · `process_sim/`.

If Mimic forks the 332 templates or the OUI tables they will drift, and a Siemens
persona will fingerprint differently from a Siemens generator device — defeating
the whole point. **Separate the path; share the knowledge.**

### 9.3 The three-layer Mimic path

**1. Mimic Studio (new canvas).** Unit of authoring is the **device persona**, not
the flow. Per persona: pick template (vendor/model/firmware → identity + CVEs),
role, and — the genuinely new surface — its **data model** (register/coil/tag/point
map) with points **bound to process-model variables**, plus its **client
relationships** (which peers it polls, at what interval). Semantics differ from the
generator canvas: there an edge means "synthesize this conversation"; here an edge
means "this persona runs a real *client* that polls that persona's real *server*."
Can **import a topology from an existing Scenario Studio scenario** so operators
don't re-author from scratch — reuse at the data layer, separate at the workflow.

**2. Mimic Deployment (new deploy path).** Three artifacts that don't exist today:
- **Placement map** — persona → agent host. Off-box: ~1 persona per agent (or a
  few). On-box dev: many personas multiplexed on one host.
- **Device directory** — `device_id → reachable ip:port`, distributed to every
  agent so client loops know where to poll. Today both IPs are synthetic and
  co-located; now clients need *real, routable* targets.
- **Data-plane network** — the new hard requirement. Off-box agents that must
  converse need L3 reachability *to each other*, separate from the control-plane
  WebSocket to the backend. Options: a shared lab LAN (simplest, if the agents sit
  on one), or a server-brokered overlay (WireGuard/VXLAN) the deployment stands up.
  Live-only; the deployment tracks *running personas + health*, not a
  scenario-that-ends.

**3. Mimic Agent (new agent binary/kind).** A long-lived service, not a
run-and-stop scenario runner. Receives its persona spec(s) + the device directory.
Per persona it: binds ports and runs protocol **servers** (pymodbus / cpppo /
asyncua / bacpypes3 / c104 / snap7 / snmpsim) backed by a `DeviceDataStore` fed by
a local `ProcessModel`, applies `FingerprintApplicator` personality
(delay/error/timeout/TTL); and runs **client loops** for its poll relationships
against the directory IPs (reusing the existing `build_request` PDUs). It abstracts
"my network binding" behind a backend interface so the *same binary* runs both
deployment modes:

- **Off-box (target).** Agent is a real host/container with its own NIC and IP on a
  shared/overlay network. Natural per-host TCP stack, horizontal scale to "many
  agents." Hard parts: the data-plane overlay and per-persona TTL/stack tuning
  (a raw off-box Linux host still leaks TTL 64 — see §6.1).
- **On-box (dev/test).** Many personas via Linux **network namespaces + macvlan**
  on one box, wired into a **virtual SPAN** — reuse the Local Sensor Lab
  veth/`pa-mon` machinery so a Cyber Vision sensor watches the emulated cell live.
  One box, no overlay, everything on the isolated segment.

### 9.4 Why a separate path is actually *cleaner* here

- It resolves the PCAP↔live parity tension (§8) instead of fighting it: Mimic is a
  distinct, explicitly live-only product surface — the parity invariant simply
  doesn't apply to it, and the generator path is untouched.
- The agent lifecycle genuinely differs (long-lived bound service vs. run-a-scenario-
  then-stop), so a separate agent kind avoids overloading `OrchestratorPool` and the
  `START_SCENARIO` command with an incompatible model.
- The authoring unit genuinely differs (device-as-endpoint + process/data model vs.
  flow-as-conversation), justifying a separate canvas rather than a mode toggle.

### 9.5 Revised roadmap (dev on-box → target off-box)

- **P0 — On-box single persona.** One pymodbus PLC persona in a namespace on the
  Local Lab `pa-mon` SPAN. `DeviceDataStore` fed by one `ProcessModel`, identity
  from `FingerprintApplicator`. Success: CV classifies it as the right vendor/model
  and `nmap --script modbus-discover` reads believable, drifting registers.
- **P1 — On-box two-persona conversation.** Add an HMI persona with a real Modbus
  *client* loop polling P0 via the device directory. Success: unscripted HMI↔PLC
  flow on the SPAN, values move under load, CV shows the flow.
- **P2 — Off-box two-host.** Lift the same two personas onto two separate agents on
  a shared network / minimal overlay. Proves the genuinely hard part (data-plane
  reachability + directory distribution) early, on the smallest case.
- **P3 — Protocol breadth + the 10-device cell.** ENIP/S7/BACnet/104/OPC UA/SNMP
  servers; declarative `emulation_plan`; anti-fingerprint checklist (§6) as a
  readiness gate. DNP3/PROFINET/GOOSE via FFI/hand-roll, deferred.
- **P4 — Scale-out.** Many off-box agents, overlay hardening, per-persona TTL/stack.

### 9.6 Net-new build surface (nothing to reuse)

Request parsers (per protocol) · `DeviceDataStore` (address→value, ODE-backed) ·
address↔process-variable binding per template (the real domain work) · client-loop
runner · Mimic Studio canvas · placement + directory + overlay deployment layer ·
long-lived mimic agent with pluggable network binding · DNP3/PROFINET/GOOSE
servers.

---

## 10. Maximum-realism architecture (2026-07-13, decisions locked)

**Locked decisions:** (1) Mimic Studio is **authored fresh** — it models a device's
*internals*, not a network of flows, so it needs its own authoring model. (2) Both
paths draw from **one shared device-knowledge substrate**; Mimic *extends* the
substrate with behavioral depth, and those extensions lift the generator's realism
too (virtuous cycle — single catalog, two consumers).

### 10.1 Design against the right adversary

Realism is only meaningful relative to who's looking. We architect against **tier
3–4**, not tier 1:

1. Passive DPI (Cyber Vision) — derives components from protocol identity fields.
2. Active scanner (Nmap NSE / Redpoint / PLCScan / Shodan / Censys) — probes,
   reads identity objects, does OS/TCP fingerprinting.
3. **A real engineering workstation** (TIA/Step7, Studio 5000, UaExpert) — expects
   full protocol *semantics*: browse the tag DB / address space / block list, go
   online, read diagnostics, subscribe to changes.
4. **A skilled analyst** — probes edge cases, malformed PDUs, timing under load,
   and *consistency over time and across protocols*.

Designing for 3–4 forces every decision below.

### 10.2 The core runtime object: `DevicePersona`

A mimic agent hosts N `DevicePersona`s (off-box: 1; on-box: many). Each composes:

```
DevicePersona
├─ Identity            ← SHARED substrate (canonical_identity + FingerprintApplicator
│                        + template): serial/firmware/hostname/OUI, projected into
│                        EVERY protocol's identity responses. One source, no drift.
├─ Transport (pluggable)   ← owns the L3/L4 fingerprint: TTL, window, MSS, window-
│    ├ NamespaceKernelStack   scaling, SACK, timestamps, ISN pattern, ICMP quirks,
│    ├ UserlandStack          ARP/gratuitous-ARP, retransmit timers. See §10.3.
│    └ RealNIC (off-box)
├─ ProcessModel       ← SHARED substrate (process_sim), extended. THE SINGLE SOURCE
│                        OF TRUTH for all values. §10.4.
├─ DataFabric         ← per-protocol PROJECTIONS onto the ProcessModel, not copies:
│    ├ ModbusProjection    {reg/coil addr → process var | static | counter}
│    ├ EnipTagProjection   symbolic tag DB → process vars
│    ├ OpcUaAddressSpace   full node hierarchy → process vars
│    ├ S7BlockProjection   DB/M/I/Q areas → process vars
│    └ …                   every protocol reads the SAME state ⇒ cross-protocol
│                          value consistency is structural, not enforced. §10.5.
├─ ProtocolServers[]  ← bound on Transport. Per request:
│                        parse_request → connection-state-machine → projection
│                        lookup → personality(delay/error/timeout) → build_response
│                        (reuse existing builders). The dead state machines live here.
├─ EventEngine        ← real change reporting off the model: DNP3 class 1/2/3 events,
│                        BACnet COV, OPC UA subscriptions, SNMP traps. Buffered,
│                        deltas real. §10.6.
├─ ScanCycleEngine    ← model updates at scan boundaries; reads return last-scanned
│                        value; latency degrades under load; connection limits.
├─ ClientLoops[]      ← this persona's OUTBOUND polls (HMI→PLC) against the device
│                        directory, reusing existing build_request PDUs.
└─ VendorBehaviorPack ← family-specific quirks, private services, error semantics,
                         connection caps, boot sequence. Code, keyed to the template.
```

### 10.3 Transport: the fingerprint frontier (pluggable, escalating)

The #1 published honeypot tell is a leaked host TTL (Linux 64 on a device claiming
to be a VxWorks PLC). Crafted-byte TTL (today's model) can't help a *bound* socket
— the kernel writes the header. So Transport is pluggable and escalates:

- **NamespaceKernelStack (default).** Per-namespace sysctls
  (`ip_default_ttl`, `tcp_window_scaling`, `tcp_timestamps`, `tcp_sack`, MSS via
  route) tuned from the template's `tcp_stack`. Good against tier 1–2 for most
  devices. Limit: can't reproduce non-Linux quirks (exact initial window, TCP
  option *ordering*, ISN algorithm, retransmit curve, ICMP idiosyncrasies).
- **UserlandStack (flagship devices).** A raw-socket userland TCP/IP stack (lwIP /
  a netstack binding) that reproduces a specific vendor family's stack behavior
  end-to-end — the only way to beat Nmap OS-fingerprinting and the Time-to-Lie
  class of probes on the Siemens/Rockwell flagships analysts know by heart. This is
  the top-tier realism investment; scope it to the handful of families that matter,
  behind the same Transport interface.
- **RealNIC (off-box).** The host's own stack — real per-host L3/L4, still needs
  TTL/window tuning to the persona's vendor.

Same `ProtocolServer` code binds on any Transport. **Design this seam on day one**
even if P0 only implements NamespaceKernelStack — retrofitting a userland stack
under servers that assumed the kernel is painful.

### 10.4 Process realism: one model, closed loop, the gaps nobody fills

`process_sim` already gives coupled equations (algebraic feeding ODE), first-order
lag, Gaussian noise, per-state setpoints, and fault injection. For max realism,
extend it and — critically — **close the loop**:

- **Write-back (new coupling direction).** Today the model pushes values one-way
  into the payload generator. A client **write** to a setpoint/coil must feed *back*
  into the model as an input, and the PV must move through the process dynamics
  (valve travel time, motor ramp) — not snap. `DataFabric` write → `ProcessModel`
  input is a new seam and the thing that makes an emulated device *controllable*.
- **The unfilled gaps (our differentiator):** layered sensor noise + quantization,
  thermal/hydraulic lag, **diurnal/shift/batch cycles**, and correlated
  multivariable physics (pressure↔flow↔temperature), plus physics-consistent faults
  (stuck valve → pressure builds where a downstream sensor reads it). No surveyed
  open tool combines ODE + noise + diurnality.
- **Historical consistency.** Whatever the EventEngine and any HA/trend query report
  must be consistent with the model's actual past. The model is the arrow of time;
  buffers are windows onto it.

### 10.5 Data as projection, not storage — the consistency guarantee

The central value-realism principle: **the ProcessModel is the source of truth;
each protocol server is a read/write *projection* onto it via an address map.** If
the same tank level is exposed as Modbus 40001, OPC UA `Tank1.Level`, and an S7 DB
word, all three resolve to the same model variable — they *cannot* disagree,
because there's no second copy to drift. This is what defeats the cross-protocol
correlation that indexed a Conpot in 31 minutes, and it's why authoring the
**address↔variable map per device** (§9.6) is the real domain work.

### 10.6 Deep interaction: object dictionaries, not flat registers

A real EWS browses structure. Max realism means each persona exposes a believable
*data structure*, authored in Mimic Studio: an ENIP symbolic tag database, a full
OPC UA node hierarchy (folders, objects, variables, methods, types), an S7 block
list, a BACnet object list, DNP3 point classes. Plus real change-reporting
(EventEngine) so subscriptions/COV/events return genuine deltas, not poll-only
snapshots. This is authored data the generator never needed — the concrete reason
Mimic Studio is a different tool.

### 10.7 Every published tell → the component that closes it

| Detection tell (from §4 survey) | Closed by |
|---|---|
| Leaked host TTL / OS fingerprint | Transport (§10.3), userland stack for flagships |
| Static / colliding serials | Shared Identity substrate, per-instance serials |
| Cross-protocol identity mismatch | Single Identity → all protocol projections (§10.2) |
| OUI ≠ claimed vendor | Shared `vendor_oui` substrate |
| Static / random register values | ProcessModel projection (§10.4–10.5) |
| Incomplete protocol / crash on bad PDU | Full servers + state machines + VendorBehaviorPack + correct exceptions |
| Poll-only, no change reporting | EventEngine (§10.6) |
| Cloud-VM latency / no scan cycle | ScanCycleEngine + `response_timing` personality |
| Hosting-context (cloud IP ranges) | Off-box on real lab network |
| No object structure to browse | DataFabric object dictionaries (§10.6) |

### 10.8 Shared substrate contract (extended, not forked)

Both paths import one `DeviceKnowledge` package: `device_templates/` (332),
`vendor_oui.py`, `canonical_identity.py`, `FingerprintApplicator`, `identity/`
builders, `process_sim/`. Mimic **adds** behavioral fields to the template schema —
object dictionaries, connection limits, scan model, per-family service coverage,
process-model bindings, boot sequence. Additive and versioned; the generator can
opportunistically consume them. One catalog, two consumers, no drift.

### 10.9 Mimic Studio authoring model (fresh — what it must express)

Not a flow canvas. A device/plant authoring tool. Panels:

- **Device** — template pick → identity (vendor/model/firmware/CVEs, from substrate).
- **Data Model** — the point/tag/node namespace, data types, engineering units,
  ranges; bind each point to a process variable | static | counter | free-running.
- **Process** — pick/compose a parameterized plant model from a library (tank,
  reactor, pump station, feeder…), wire actuators↔sensors, add control loops (PID)
  that close through the points.
- **Behavior** — latency profile, fault schedule, connection caps, boot behavior.
- **Relationships** — client poll groups + scan rates (who polls whom, how often).
- **Protocols** — which servers, ports, session/security config per device.

A parameterized **process-model library** (keyed to the 6 verticals) is its own
substrate asset — worth building once, drawn on by every persona.

---

### One-line thesis
PacketArch already owns the half of interactive OT emulation that honeypots
struggle with (per-device fingerprint realism + a running process model); **Mimic**
adds the half testbeds own — bound endpoints that answer with full protocol
semantics, values that are consistent because every protocol is a *projection* of
one running process model, and devices that poll each other — on its own fresh
canvas → deploy → agent path over a shared device-knowledge substrate, architected
to withstand an active scanner and a real engineering workstation, not just a
passive sensor.
