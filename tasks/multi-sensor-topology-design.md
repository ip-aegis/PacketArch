# Multi-Sensor Topology Workflow — Design & Plan

**Status:** Design draft (design-first; no code yet)
**Date:** 2026-07-10
**Owner:** rocsmith

## 1. Goal

A **new, additive workflow** that deploys a single scenario across **multiple
Cyber Vision sensors — one per zone plus one at a hierarchical core** — so that
traffic is injected the way a real multi-sensor CV deployment would observe it:

- Each zone has a Cisco **IE3500** aggregation switch; every device in the zone
  hangs off it (L1 topology).
- The system is **L1-aware**: it knows the physical path each flow takes
  (`device → zone-switch → core → zone-switch → device`).
- Traffic is injected so that **any flow that physically crosses a zone's switch
  is seen by that zone's sensor**. Intra-zone flows hit one sensor; **cross-zone
  flows are seen by both endpoint sensors and the core sensor**, each with the
  correct per-segment L2 framing.

This **augments** the existing single-agent deploy and the existing Local
Sensor Lab. Shared agent code is touched only behind a `topology_mode` flag —
**behavior-identical when the flag is off**, verified by an explicit Phase 1
regression check. This is a separate opt-in "Multi-Sensor Topology" mode.

### Locked decisions (from interview, 2026-07-10)

| Decision | Choice |
|---|---|
| Deliverable | Design + plan first |
| Switch realism | Modeled asset + topology metadata (IE3500 fingerprinted; keep veth SPAN — no L2 dataplane sim) |
| Cross-zone frame semantics | **Gateway-rewritten (L3)**: IPs preserved end-to-end, MACs per-segment |
| Path model | **Hierarchical** with a core tier |
| Conversation coherence | **Generate-once, render-many** |
| Core | **Core gets its own agent/sensor pair** (sees all inter-zone traffic) |
| Entry point | **"Advanced Deployment" option** — a new option alongside existing deploy targets, never replacing them (guided wizard, §4.2/§4.4) |
| L1 topology | **Derived** from zone membership + hierarchy, **editable** (edit = later phase) |
| Injector count (2026-07-11) | **Single conductor** — one injector, one sensor per zone + core (§3.1) |

### Stated assumptions (flag if wrong)

- Every conduit / zone boundary = an **L3 boundary**. Two cells sharing a VLAN
  (L2-adjacent) is an exception we can add later.
- All sensors/agents are **co-located on the PacketArch host** (Local Sensor Lab
  model). This is what makes the clean single-conductor design below possible.

### Costs on the record

- **CV sensor auto-provisioning is already solved** (corrected 2026-07-11):
  `local_sensor_service.build_lab()` creates a **reusable CV deployment token**
  via the Center API (`create_deployment_token`, rotated near its usage cap),
  mints per-sensor JWTs, and synthesizes the compose — **no operator paste
  steps**. The topology provisioning service reuses this machinery N+1 times,
  so "one-click" is genuinely one click (CV settings must be configured, and
  the deployment token's usage headroom must cover N+1 enrollments).
- **RAM**: each sensor holds a ~1.26 GB capture ring buffer
  (`local_sensor_lab_memory_sizing` memory) → a 5-zone scenario is **~7.5 GB
  before any traffic**. Belongs in host-sizing docs + a pre-flight check.
- **Synergy**: shipped CV org-hierarchy provisioning already mirrors zones into
  the OH tree — one sensor per zone pairs 1:1 with one OH node per zone. Selling
  point, not a cost.

---

## 2. Current state (grounded)

- **No L1/port/link topology.** Scenario is logical only: devices, zones, and
  `device→device` flows stored as an opaque JSON `definition`
  (`backend/app/models/scenario.py:56-61`; types in
  `frontend/src/types/index.ts` — `ScenarioFlow` is source/target device IDs +
  protocol).
- **Zones** (`ScenarioZone`, `index.ts:180-194`) already carry Purdue `level`,
  `network { subnet, vlanId, gateway }`, `deviceIds[]`. **Conduits**
  (`ScenarioConduit`) carry zone pair + direction + allowed protocols.
- **A deployment is one-agent / one-scenario / one-interface**
  (`AgentDeployment`, `traffic_agent.py:151-211`; `agent_manager.py:842-868`).
  The whole definition is injected on a single `ctx.interface` on the agent
  (`docker/packetarch-agent/app/orchestrator_pool.py:173-213, 344-375`,
  `sendp(..., iface=...)` at `:983`). **No fan-out, no flow replication.**
- **The agent already DROPS cross-zone flows at runtime** via
  `should_drop_for_isolation` (`orchestrator_pool.py:353-362`,
  `protocol_engines/cell_isolation.py`). ⚠️ Cross-zone flows are this feature's
  headline traffic — the new mode must **replace** isolation-drop with
  path-aware routing.
- **Local Sensor Lab** = per-lab veth crossover `pa-gen-<slug>` ↔
  `pa-mon-<slug>` (`local_lab_naming.py:41-48`, `hostops.py:59-71`); agent
  injects on `pa-gen`, CV sensor's macvlan capture parent forced to `pa-mon`
  (`hostops.py:181-202`, `local_sensor_service.py:105-155,239`). `LocalLab` is
  desired state; privileged host-agent reconciles.
- **IE3500 fingerprints already exist** (`device_templates/vendors/cisco.py`:
  `cisco/ie3500/8p3s` @552, `8t3s` @657, `8u3x` @753; `ie3505/8p3s` @849), plus
  IE9320/IE9310 (@173-460) suitable for the **core**. All emit
  `snmp/lldp/cdp/profinet` management identities, backed by real engines
  (`protocol_engines/snmp|lldp|ambient/cdp`, plus STP/ARP).

**Net:** the raw ingredients (switch fingerprints, ambient engines, per-lab
SPAN, zone metadata) exist; what's missing is (a) an L1 topology + path model,
(b) a fan-out injection layer, and (c) provisioning + UI for N+1 labs.

---

## 3. Target architecture

### 3.1 Injector count — DECIDED: single conductor (operator, 2026-07-11)

**Coherence does not depend on this choice.** Coherence comes from
*generate-once* (one canonical stream); both options below emit **identical
frames on every sensor with identical coherence**. The number of *injector*
processes is invisible to Cyber Vision — CV only sees per-zone SPANs. The
operator chose **(a)**:

- **(a) Single conductor — CHOSEN** — one injector process generates once and
  injects each per-segment-reframed copy directly onto the correct
  `pa-gen-<zone>` / `pa-gen-core` veth (needs `network_mode: host` for netns
  access to all veths). Fewer moving parts, no per-packet transport, one clock.
  Reinterprets "an agent per zone" as "a **sensor** per zone, one injector."
- **(b) Conductor + thin per-zone injector agents** — rejected for v1; kept as
  §7 fallback. Matches literal process-per-zone at the cost of a per-packet
  local transport and a timing-sync surface.

Either way we create a **`TrafficAgent` row per zone** for UI badging, topology
display, and CV OH mapping — under (a) these are logical identities served by
the one conductor.

### 3.2 Topology model (derived, editable later)

Introduce an explicit L1 topology derived from the existing logical scenario:

- **Zone switch**: one IE3500 per zone. Every `deviceId` in the zone gets an L1
  link `device → zone-switch`.
- **Core**: one aggregation switch (IE9300-class). Each zone-switch gets an L1
  link `zone-switch → core`.
- **Gateways as core SVIs**: the core owns one **SVI per zone VLAN**; `SVI-Z.ip`
  = `zone.network.gateway`, `SVI-Z.mac` = deterministic seeded MAC
  (`canonical_identity_and_oui` memory / `vendor_oui.py`). The core **is** the
  L3 gateway for every zone — this avoids inventing N separate firewall devices.

The topology is **derived** from zone membership + the declared hierarchy; v1
renders it read-only (reusing the `AgentTopology` view). Editing (move a device
to another switch, second switch per zone) is a later phase.

**Planner input rules** (preview-time validation, not silent defaults):

- Zone missing `network.subnet`/`gateway`/`vlanId`: derive from the scenario's
  IP-management convention (`/24` subnets, gateway `.1`) when the zone's devices
  share a subnet; otherwise a preview validation error.
- **Zone switches join their zone's `deviceIds`** in the derived definition (so
  the intra/cross-zone classifier places them); the core belongs to a synthetic
  "core" scope, not any zone.
- Unzoned devices: preview validation error in v1 — every device must be in
  exactly one zone; multi-zone membership is likewise rejected.
- Single-zone scenario: valid but degenerate — no core is created (nothing to
  aggregate); it collapses to a single Local Sensor Lab and the preview says so.

### 3.3 Path & segment model

For flow `F: DA(zone ZA) → DB(zone ZB)`:

- **Intra-zone (ZA == ZB):** segments = `[ZA-SPAN]`. No L2 rewrite — sensor sees
  true `DA-MAC → DB-MAC`.
- **Cross-zone (ZA != ZB):** physical path `ZA-switch → core → ZB-switch`.
  Segments and their L2 framing (IPs `DA→DB` unchanged throughout):

  | Segment (SPAN) | src MAC | dst MAC | VLAN | What CV sees |
  |---|---|---|---|---|
  | `ZA-SPAN` | `DA-MAC` | `SVI-A-MAC` | A | DA (real) talking to its gateway |
  | `core-SPAN` (ingress) | `DA-MAC` | `SVI-A-MAC` | A | trunked copy of ZA side |
  | `core-SPAN` (egress) | `SVI-B-MAC` | `DB-MAC` | B | trunked copy of ZB side |
  | `ZB-SPAN` | `SVI-B-MAC` | `DB-MAC` | B | gateway delivering to DB (real) |

  Replies mirror. **TTL fidelity:** the core is a routed hop, so the IP TTL is
  decremented by 1 on the far-zone segments (`core-SPAN` egress and `ZB-SPAN`)
  relative to the near-zone segments — identical TTL on both sides of a router
  is a realism tell.

  Result: sensor-A fingerprints `DA` + the core (via SVI-A); sensor-B
  fingerprints `DB` + the core (via SVI-B); the **core sensor sees the whole
  conversation** (both VLAN-tagged framings). The expectation is that CV
  correlates the conversation across all three sensors by the preserved
  **IP pair**, and fingerprints the core as a Cisco L3 switch — this is exactly
  real routed multi-sensor behavior. ⚠️ *This correlation behavior is the
  feature's headline claim and is unverified — see §5 Phase 0a.
  Even if CV shows per-sensor duplicates instead of a merged view, that too is
  authentic multi-sensor behavior; it refines expectations, not the design.*

Two additional framing rules:

- **Per-SPAN tagging policy** (stated once): zone SPANs behave as trunks toward
  the sensor — intra-zone frames are untagged (access traffic); frames that
  traverse the core carry their zone's Dot1Q tag; the core SPAN carries all
  frames tagged.
- **Flows targeting a switch/SVI itself** (e.g., SNMP poll of a zone switch or
  the core): the switch's management IP is the flow target and segments are
  planned exactly like a device flow — intra-zone to its own switch = one SPAN
  with true MACs; to the core or a remote-zone switch = routed per the table.

The **path planner** is a pure function `scenario → { per-flow: [segment]}` plus
a MAC/VLAN table. No packet touching — just topology math. Independently
testable.

### 3.4 Generate-once, render-many injection

The true choke point (verified against code) is `UnifiedOrchestrator.run()` →
`self.output.write_packet(...)` (`unified_orchestrator.py:361, 404`): OT flows,
ambient, and attack packets all ride the same event heap into that one call. In
topology mode a **`TopologyOutputRouter`** implements the existing
`PacketOutput` protocol and **wraps** the real outputs (it does not replace
them). There are exactly two wiring sites: `LiveOutput` on the agent
(`orchestrator_pool.py:344-346`) and `PcapOutput`/`SplitPcapOutput` on the
backend (`traffic_generator/orchestrator.py:114-121`). Per packet it:

1. Identifies the owning flow by **`flow_id`** — `PacketOutput.write_packet`
   gains a `flow_id` parameter; the run loop already holds `event.flow_id` for
   every packet (including `ambient_*` and `__attack__` prefixes). 5-tuple
   parsing is **not viable**: source ports default to 50000 for every flow
   (`orchestrator_pool.py:758`) so tuples are ambiguous, and attack packets
   (scans, spoofed sources, rogue devices) match no planned flow.
   **Attack-packet fallback rule**: attribute by the attack's configured
   source/target device zones; if unresolvable, render on the target device's
   zone SPAN + core.
2. Looks up the segment list from the path plan (or the L2-scope rule, §3.4a).
3. For each segment: clones the packet, rewrites only the **Ether** layer
   (src/dst MAC), applies the **Dot1Q**/TTL rules of §3.3, and emits to that
   segment's underlying output (live: per-veth socket; PCAP: per-SPAN file).

Because generation is untouched, **TCP seq/ack, protocol state (Modbus txn IDs,
ENIP session handles), and payload are identical across every segment** —
coherence is guaranteed, not coordinated. PCAP-matches-live holds because both
paths wrap the same router. Note `SplitPcapOutput`'s combined/baseline/attack
fan-out (`output.py:88-135`) composes with per-SPAN fan-out — up to 3×(N+1)
files per run.

⚠️ **Second send path — cloud heartbeats.** Remote-access heartbeats
(SSH/RDP/HTTPS/EWON) bypass the output abstraction entirely: they `sendp`
directly from their wall-clock daemon thread (`orchestrator_pool.py:898-1007`;
the `:983` sendp is this bypass, not `LiveOutput`). Topology mode must route
them through the same router (or add a per-segment hook to that thread), or
cross-zone remote-access traffic silently misses the SPANs.

**Throughput.** Injection today is `sendp`-per-packet at ~60 pps, with virtual
time documented to fall ~10× behind wall clock (`orchestrator_pool.py:384-396`);
per-segment fan-out multiplies sends 2-4×. The conductor needs **persistent
per-veth L2 sockets** (open once, reuse) as a floor; measured in Phase 3.

**Ambient traffic per segment** (big CV win): ARP resolves each device→gateway
on its zone SPAN; **LLDP/CDP** between zone-switch↔core appears on both that zone
SPAN and the core SPAN → **CV reconstructs the exact switch topology we derived**;
STP BPDUs between switches; SNMP management polls to switches cross zones and are
seen by multiple sensors. The switch fingerprints already carry
`snmp/lldp/cdp_identity`, so the switches classify correctly in CV.

### 3.4a Non-routed / L2 frame routing (second assignment rule)

The 5-tuple lookup in §3.4 only covers **routed unicast IP** flows. The ambient
traffic above — and several OT protocols — has no IP 5-tuple at all, so the
router needs a **second assignment rule keyed by L2 scope** (which
VLAN/segment a frame belongs to), applied before the IP lookup:

- **ARP** → the zone SPAN of the requesting device (device↔gateway resolution
  never leaves its VLAN).
- **IP broadcast / subnet-directed broadcast** (e.g., BACnet Who-Is on 47808)
  → confined to the source device's zone SPAN; never routed.
- **LLDP/CDP/STP** → the SPANs on both ends of the L1 link they ride
  (zone-switch↔core adjacencies land on that zone SPAN *and* the core SPAN).
- **L2 OT protocols (GOOSE/SV multicast, PROFINET RT)** → confined to their
  VLAN: replicated to the SPANs of that VLAN only.

⚠️ **This is new generator work, not just router-side replication.** Today's
ambient engines emit one *global* self-advertisement per device with `port_id`
hardcoded to `"eth0"` (`noise_generator.py:596`), and only *gratuitous* ARP
exists. Per-link LLDP/CDP (distinct port IDs per L1 link, emitted on both
link-end SPANs) and device→gateway ARP request/reply are **Phase 2 engine
capabilities to build** — "CV reconstructs our topology from LLDP" depends on
them.

Hard planner rule that follows from "every conduit = an L3 boundary": a
**cross-zone L2 flow is physically impossible** — it cannot traverse a router.
`topology_planner.plan_segments()` must **detect and reject** any cross-zone
flow whose protocol is L2-only (GOOSE/SV/PROFINET RT), or require the operator
to co-locate those endpoints in one zone/VLAN. This is a planner validation
error surfaced in the preview, not a silent drop. (Real substations solve this
with L2 process-bus VLANs spanning specific switches — modeling that is the
same "L2-adjacent zones" exception already deferred in §1 assumptions.)

This subsection gates Phase 1: the per-SPAN PCAP test hits ARP/LLDP in its
first second, so the L2-scope rule ships with the first router cut.

### 3.5 Cell-isolation replacement

`should_drop_for_isolation` must **not** run in topology mode — it would drop
the cross-zone flows this feature exists to render. There are **three gate
sites**, and the `topology_mode` flag must cover all of them or live/PCAP
behavior diverges: per-flow setup (`orchestrator_pool.py:353-362`), the
`BackgroundNoiseGenerator` isolation input (`orchestrator_pool.py:584`), and
the PCAP path's `cell_isolation_override` (`api/routes/generation.py:170`).
When set, cross-zone flows are **routed by the path plan** instead of dropped.
Existing (non-topology) deployments keep isolation as-is — verified by the
Phase 1 regression check.

---

## 4. Component design

### 4.1 Data model (all additive)

- `TopologyDeployment` (new model, sibling of `LocalLab`): FK `scenario_id`;
  the derived/edited topology JSON (zone-switch assignments, core, SVIs/VLANs,
  L1 links, per-flow segment plan); provisioning status; children:
- `TopologySensor` rows (one per zone + core): the CV sensor half — reuses the
  Local Sensor Lab veth/sensor machinery (`pa-gen-<slug>` / `pa-mon-<slug>`,
  macvlan capture parent) via `local_lab_naming` + host-agent `ensure_veth` /
  `rewrite_sensor_compose`.
- One conductor `TrafficAgent` (+ N logical per-zone `TrafficAgent` rows for UI
  badging / CV OH mapping per §3.1). Logical rows get a **new agent kind
  excluded from WebSocket health checks / offline badging** (they never
  connect) and carry no tokens — only the conductor mints one.
- The **IE3500 zone switches and IE9300 core are real `ScenarioDevice`s** added
  to a *derived working copy* of the definition (so the source scenario is not
  mutated) — they get fingerprints, MACs, and management flows. The deploy
  pipeline already ships a modified copy without writing back
  (`agent_manager.py:873-908`), but those copies are **shallow**
  (`{**definition}`) — injecting switches must deep-copy the `devices`/`flows`
  containers it mutates.

Nothing above touches `AgentDeployment`, `LocalLab`, or the existing deploy
route.

### 4.2 Backend services (new)

- `topology_planner.py` — pure: `derive_topology(scenario)` + `plan_segments()`
  → topology + MAC/VLAN table + per-flow segment lists. Reuses
  `conduit_service`/`conduit_compliance` to know which zone pairs are legal
  conduits.
- `topology_provisioning_service.py` — the one-click deploy: derive topology,
  build the derived definition (inject switches/core + management flows), mint
  the **one** conductor agent token, and **auto-provision N+1 CV sensors**
  exactly the way `local_sensor_service.build_lab()` does (reusable deployment
  token → per-sensor JWT → synthesized compose; reuse
  `_resolve_cv_deployment_name`/`_synthesize_sensor_compose` or extract them
  into a shared helper), write N+1 sensor specs to the host-agent file-queue
  (reusing `host_agent_client`), start the conductor. Mirrors zones→CV OH via
  the shipped provisioning path.
  **Registry-trust refcount**: the "drop insecure-registry trust if unused"
  teardown logic is shared with Local Labs — teardown must refcount across
  BOTH features' labs before dropping trust.
- `api/routes/topology_sensor.py` — `POST /scenarios/{id}/topology/preview`
  (returns derived topology + segment plan; no side effects), `POST .../deploy`,
  `GET .../status`, `DELETE .../{id}` (full teardown, same pattern as Local Lab).

### 4.3 Agent / conductor

- New `TopologyOutputRouter` (§3.4) in the agent package. **Bump
  `docker/packetarch-agent/app/version.py`** per the Agent Versioning Rule —
  MINOR at least; the `PacketOutput.write_packet` signature change may argue
  MAJOR.
- **WS protocol extension**: `START_SCENARIO` today validates exactly ONE
  `interface` (`agent/app/main.py:323-344`); topology mode adds the segment
  plan + per-SPAN interface map to the deploy payload.
- Conductor runs multi-interface: needs the `pa-gen-*` veths in its netns
  (`network_mode: host`, which local-lab agents already use). **Persistent
  per-veth L2 sockets** replace sendp-per-packet (throughput floor, §3.4).
  Host-agent creates all veths; conductor injects.
- **Topology-mode veths are created MTU 1504** (1500 + Dot1Q) or full-size
  tagged frames hit EMSGSIZE — `hostops.py:59,64` hardcodes 1500 today. And
  `rewrite_sensor_compose` must **force `macvlan_mode: passthru`** (today it
  only forces `parent`, `hostops.py:200-203`) or a bridge-mode paste won't see
  foreign-MAC frames.

### 4.4 Frontend

- Surfaced as an **"Advanced Deployment"** option: wherever the operator picks a
  deploy target today (agent picker / deploy-to-new-lab), a new "Advanced:
  Multi-Sensor Topology" choice appears **alongside** the existing options —
  existing deploy flows are untouched and remain the default. Selecting it opens
  the guided wizard: **Preview → Deploy** using the preview endpoint to show the
  derived L1 topology (reuse `AgentTopology.tsx`), the N+1 sensor list with
  per-sensor CV compose paste steps, and a **RAM pre-flight** (N+1 × 1.26 GB vs
  host free).
- v1 topology view is read-only. **Editable topology** = later phase (drag device
  between switches, add switch) writing back to `TopologyDeployment.topology`.
- Gate behind `LIVE_TRAFFIC_ENABLED` (it's a live-agent feature) and likely a new
  `MULTI_SENSOR_TOPOLOGY` feature flag (default off) while it matures.

### 4.5 Cyber Vision

- N+1 sensors register independently against the CV Center (existing sensor
  compose path). Each zone sensor → its zone's OH node (shipped
  `cv_org_hierarchy_provisioning`); core sensor → a "Core/Aggregation" OH node.
- Expected CV result to verify: each device fingerprinted by its zone sensor;
  cross-zone conversations correlated by IP across sensors; switches classified
  as Cisco IE-series; **CV's own topology map matches ours via LLDP/CDP**.

---

## 5. Phased plan (each phase independently verifiable)

**Phase 0 — Topology & path model (backend, pure).**
`topology_planner`, data model, `POST .../topology/preview`. Verify: preview API
returns correct L1 topology + segment table for a 3-zone scenario (unit tests on
the MAC/VLAN table).

**Phase 0a (parallel with Phases 0-1) — Verify CV cross-sensor correlation on a
live Center.**
The claim "CV correlates one conversation across sensors by IP pair, and merges
the core given a shared chassis identity" is the feature's premise and is
unverified. We have live CV API access via the backend
(`/api/v1/cyber-vision/*`) — before building Phases 3-4, hand-feed two existing
sensors (or two throwaway labs) segment-framed PCAPs of one synthetic
conversation and observe in CV: one conversation or two? one core device or two
router interfaces? Cheap, and it calibrates Phase 2's identity design and
Phase 4's acceptance criteria. Either outcome keeps the feature valid (duplicate
views ARE real multi-sensor behavior) — this refines expectations, not the
design.

*Interim findings (2026-07-11, single-sensor half done):* injected the zone-A
segment view (VLAN-101-tagged Modbus conversation 10.199.1.10↔10.199.2.10,
gateway-rewritten per §3.3) into the live local lab's SPAN. Results:
(1) **Dot1Q survives veth→macvlan capture** — sensor-side sniff saw tags
intact (risk 4's tag question retired; MTU-1504 for full-size frames still
pending). (2) CV created components exactly as the design predicts: the local
device with its **true MAC**, the **SVI as a Cisco device** at the gateway IP,
and the remote device's IP attributed to the **gateway MAC** — the classic
behind-a-router view. (3) Constraint from operator: the test bed is
**docker-only** — the hardware IE-3500 sensor on the Center is a real switch
and must NOT be used for injection. (4) ~~No CV API to mint sensors~~ —
**corrected by operator**: `local_sensor_service.build_lab()` auto-provisions
sensors via a reusable CV deployment token (v1.15.0); the N+1-paste claim was
wrong and §4.2 now reuses that machinery (see tasks/lessons.md).

*FINAL RESULTS (2026-07-11, two sensors, same conversation injected as za- and
zb-framed views simultaneously):*

1. **Components are keyed by (MAC, IP) per sensor view — CV does NOT merge by
   IP alone.** 6 components: each sensor sees its local device with its TRUE
   MAC, its gateway SVI as a Cisco device, and the remote endpoint attributed
   to the gateway MAC. `10.199.2.10` exists twice (SVI-A MAC via sensor A;
   true MAC via sensor B).
2. **DPI classification is solid across both sensors**: both views produced
   Modbus "Read Var" flow records on port 502, ARP tagged correctly, and the
   true-MAC endpoints vendor-classified by OUI (Siemens icon) — the
   VLAN-tagged, gateway-rewritten framing parses cleanly end-to-end.
3. **The conversation appears as TWO flow records** (one per sensor) with the
   same IP-pair labels — authentic routed multi-sensor behavior, exactly the
   caveat the design anticipated. Cross-sensor unification happens at
   device-aggregation level, not automatically at component level.
4. **No devices were aggregated** from the components — anonymous Modbus
   carries no protocol identity. Experimentally confirms Phase 2 is
   load-bearing: protocol identities (S7 names, SNMP sysName, PROFINET
   station names) drive CV's component→device aggregation, and the core's
   SVIs (separate MACs = separate components today) need the shared chassis
   identity (LLDP chassis-id + SNMP sysName) to merge into ONE core device.

Verdict: the design's frame semantics are validated on a live Center; Phase 2
identity work is confirmed as the mechanism that turns per-sensor views into a
unified inventory. Provisioning cost of the eventual feature: ~1 min per
sensor, fully hands-free.

**Phase 1 — Generate-once/render-many in PCAP first. ✅ DONE (commit b4bb725).**
`TopologyRouter` (`protocol_engines/topology_router.py`, staged to agent) +
`SpanPcapOutput`; `topology_mode` on GenerationRequest→celery forces isolation
off. Live 6-zone run validated **31/31 per-SPAN invariants**: per-zone VLAN
purity, untagged true-MAC intra-zone frames, gateway-rewritten arrivals all
TTL-decremented (relative — preserves OS TTL fingerprint), **core TTL
differential ingress=egress+1** (direct proof of the single routed hop),
cross-flow present on both endpoint zones + core. Regression: topology OFF =
one combined PCAP, no spans. 22 unit tests.
Original plan:
`TopologyOutputRouter` wired to emit **one PCAP per SPAN**. Verify with tshark:
intra-zone flow appears only in its zone PCAP with true MACs; cross-zone flow
appears in ZA/ZB/core PCAPs with the exact per-segment framing of §3.3; TCP
seq/payload identical across the three; **TTL decrements across the core**;
ARP/broadcast confined per §3.4a. Plus the **isolation regression check**:
with topology mode OFF, PCAP/live behavior is unchanged (cross-zone flows
still dropped under isolation modes). This proves coherence with zero infra.

**Phase 2 — Switch/core assets + ambient.**
Inject IE3500/IE9300 devices + management flows into the derived definition;
per-segment LLDP/CDP/STP/SNMP/ARP (per §3.4a). **Core identity coherence:** the
core appears as SVI-A (own MAC+IP) on sensor A and SVI-B on sensor B; for CV to
merge these into ONE core device, all SVIs must share the core's chassis
identity — same LLDP chassis-id, same SNMP sysName/sysObjectID — decided and
implemented here, not discovered in Phase 4 (per `fingerprint_uniqueness_cv_merge`,
CV merges by fingerprint/identity). Verify in PCAP: switches emit correct
management identities; LLDP adjacencies encode our topology; SVIs carry the
shared chassis identity.

**Phase 3 — Live multi-sensor provisioning.**
Host-agent provisions N+1 veths + sensors; conductor injects live. One-click
deploy + full teardown. Verify: `docker compose ps` shows N+1 sensors + 1
conductor; each `pa-mon` sees only its segment and **Dot1Q-tagged frames arrive
intact** (tcpdump per veth); measure fan-out throughput against the §3.4
persistent-socket floor.

**Phase 4 — Frontend (read-only) + CV verification.**
Preview/Deploy UI, RAM pre-flight, topology view, OH mapping. Verify end-to-end
against a live CV Center (device fingerprinting per sensor; cross-sensor
correlation; CV topology map matches).

**Phase 5 — Editable topology + polish.** Deferred per "editable = later."

---

## 6. Risks / open questions

1. ~~Decide §3.1 injector count~~ — **DECIDED 2026-07-11: single conductor.**
2. **CV cross-sensor correlation is unverified** — addressed by early
   verification (§5 Phase 0a) before Phases 3-4; either outcome keeps the
   feature valid.
3. **Core SPAN fidelity** — v1 models the core sensor as an aggregation SPAN
   seeing both VLAN-tagged framings. If a routed point-to-point core (distinct
   router-interface MACs) is wanted, the segment table grows a hop. Fine to defer.
4. **VLAN on the SPAN** — largely retired by code review: the synthesized
   sensor compose uses `macvlan_mode: passthru`, which passes Dot1Q and
   foreign-MAC frames. Remaining actions: MTU-1504 veths and forcing passthru
   in `rewrite_sensor_compose` (§4.3); verified in Phase 3.
5. **Injector netns access to all veths** — validated in principle (local-lab
   agents already run `network_mode: host`); confirmed live in Phase 3.
6. **Scale ceiling** — RAM (N+1 × 1.26 GB) and CV token burden bound practical
   zone count; pre-flight + docs.
7. **Cross-zone L2-only flows are physically impossible** under the L3-boundary
   assumption — planner rejects them with a preview-time validation error
   (§3.4a); the "L2-adjacent zones" exception is deferred.
8. **Injection throughput** — sendp-per-packet is ~60 pps with documented
   virtual-time starvation; per-segment fan-out multiplies sends 2-4×.
   Persistent per-veth L2 sockets are the floor (§3.4); measured in Phase 3.

## 7. Fallback: option (b) — per-zone injector agents (rejected for v1)

Only §4.3 changes: the conductor still generates once, but pushes per-segment
framed packets to a thin injector agent per zone over a local file-queue/IPC
(all on one host). §3.3 framing, §3.4/§3.4a routing rules, data model, and
provisioning are identical.
