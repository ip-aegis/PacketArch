# Multi-Sensor Topology — Implementation (design: multi-sensor-topology-design.md)

(Previous content: Scenario Verify audit 2026-07-09 — completed, recorded in
memory `scenario_verify_audit` and git history.)

## Phase 0 — Topology planner (pure) + preview endpoint
- [x] Research: definition JSON schema as backend consumes it
- [ ] `backend/app/services/topology_planner.py` — derive_topology() + plan_segments()
      (planner input rules §3.2, segment table §3.3, L2-scope rules §3.4a)
- [ ] Unit tests (3-zone scenario: MAC/VLAN table, intra/cross-zone segments,
      validation errors: unzoned device, missing network, single-zone, L2-only cross-zone)
- [ ] `POST /api/v1/scenarios/{id}/topology/preview` route (no side effects)
      + `MULTI_SENSOR_TOPOLOGY_ENABLED` flag (default OFF) + RequireX dep
- [ ] Deploy (`docker compose up -d --build backend`) + verify endpoint live

## Phase 0a — CV cross-sensor correlation check (live Center)
- [x] Inventory: CV connected; 2 sensors ENROLLED+CONNECTED
      (docker sensor c186cf78 = local lab ce269fd7; hardware IE-3500-01)
- [ ] Craft segment-framed PCAPs of one synthetic conversation (scapy), framed
      BY the new planner's output — clearly-synthetic IPs for later cleanup
- [ ] Inject ZA view into local lab veth (pa-gen-ce269fd7) — isolated, safe
- [ ] BLOCKED-ON-OPERATOR: second sensor path — host has one physical NIC
      (enp1s0); reaching IE-3500-01 means sending frames on the real network.
      Ask Rocky how IE-3500-01's capture is wired before sending anything.
- [ ] Query CV devices/flows: one conversation or two? core merged or split?
- [ ] Write findings into design doc §5 Phase 0a

## Review
- (fill after)
