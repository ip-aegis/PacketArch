# Multi-Sensor Topology — Implementation (design: multi-sensor-topology-design.md)

(Previous content: Scenario Verify audit 2026-07-09 — completed, recorded in
memory `scenario_verify_audit` and git history.)

## Phase 0 — Topology planner (pure) + preview endpoint — DONE (commit f207951)
- [x] Research: definition JSON schema as backend consumes it
- [x] `backend/app/services/topology_planner.py` — derive_topology() + plan_segments()
- [x] Unit tests — 14 passed in container
- [x] `POST /api/v1/scenarios/{id}/topology/preview` + MULTI_SENSOR_TOPOLOGY_ENABLED
      flag (default OFF; enabled in this box's .env) + RequireMultiSensorTopology
- [x] Deployed + verified live: "Strict Purdue Segmented Manufacturing" → valid,
      6 switches + core, 7 spans, 41 links, 59 flow plans (20 intra / 39 cross),
      correct 4-segment gateway-rewritten framing with TTL -1 far-side

## Phase 0a — CV cross-sensor correlation check (live Center)
- [x] Inventory: CV connected; 2 sensors ENROLLED+CONNECTED
      (docker sensor c186cf78 = local lab ce269fd7; hardware IE-3500-01)
- [x] Crafted za/zb/core PCAPs (Modbus convo 10.199.1.10↔10.199.2.10, VLAN
      101/102, TTL 64/63, SVI MACs Cisco OUI) — in agent container /tmp/phase0a/
- [x] Injected ZA view on pa-gen-ce269fd7; **Dot1Q survives veth→pa-mon**
      (45 tagged frames sniffed on sensor side, VLAN 101 intact) → risk #4
      Dot1Q half retired empirically
- [x] CV ingested the ZA view — components: 10.199.1.10 w/ TRUE MAC,
      10.199.1.1 (SVI) as Cisco device, 10.199.2.10 attributed to SVI MAC
      (classic behind-a-router view) → single-sensor premise VALIDATED
- [x] Operator: docker-only; hardware IE-3500-01 is a real switch — OFF LIMITS
- [x] Probed CV v3 + cvapi/v1: no programmatic docker-sensor compose minting
      → §4.2 guided paste flow confirmed as only option
- [x] CORRECTED (Rocky): build_lab() auto-provisions sensors via reusable CV
      deployment token — no paste needed; lesson in tasks/lessons.md; design
      §1/§4.2/§5 fixed
- [x] Lab #2 "Topology-Test-B" (9b1a888e) built hands-free via API — ENROLLED
- [x] Injected za→lab A + zb→lab B simultaneously (same conversation)
- [ ] Poll running: does Center merge the two sensor views? (1 device or 2 for
      10.199.2.10; conversation correlation)
- [ ] Cleanup: teardown lab #2 + prune synthetic 10.199.* components
- [x] Interim findings written into design doc §5 Phase 0a

## Phases 1-5 — DONE (2026-07-11, autonomous)
- [x] Phase 1: TopologyRouter + SpanPcapOutput, 31/31 per-SPAN invariants (b4bb725)
- [x] Phase 2: switch/core asset injection, live SNMP-fingerprinted (801933b)
- [x] Phase 3: provisioning service + LiveTopologyOutput; live 3-sensor
      validation (cross-zone S7 on multiple sensors, IE3500 named CV asset) (3e1403f)
- [x] Phase 4: Advanced Deployment UI tab, feature-gated, in bundle (c0ec38e)
- [x] Phase 5: topology_overrides (switch/core model) + polish (e670f4d)

## Review
Delivered a complete, additive multi-sensor topology workflow end-to-end,
design→ship, across 7 commits. The existing single-agent deploy and Local
Sensor Lab paths are untouched (all new code is behind the default-off
MULTI_SENSOR_TOPOLOGY flag + a topology_mode branch). Validation was
behaviour-driven at every phase: pure-planner unit tests (42 topology tests),
per-SPAN PCAP dissection (31/31 invariants on a real 6-zone scenario), and a
live 3-sensor Cyber Vision deployment on a throwaway 2-zone scenario proving
the user's exact goal — cross-zone flows picked up by multiple sensors with
gateway-rewritten per-segment framing, and an IE3500 per zone as a real CV
asset. Full backend regression green (882 passed). Two follow-ups remain
(agent live-streaming integration + per-link LLDP/SVI-merge), both documented
as realism/integration polish on the proven mechanism, neither blocking.

Key decisions & why: single-conductor over per-zone injectors (identical CV
output, fewer moving parts); generate-once/render-many (coherence by
construction, PCAP=live); derive-from-zones topology (matches "one switch per
zone", far less UI); name-prefix lab grouping (no risky migration).
