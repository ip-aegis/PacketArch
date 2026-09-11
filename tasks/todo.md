# Multiple Cyber Vision Centers (2026-09-11)

Goal: one PacketArch server can talk to several CV Centers. Branch `feat/multi-cv-centers`.

## Decisions (stated assumptions)
- **One center per lab, one center per scenario's CV state.** No fan-out of one
  scenario into several centers at once. `definition['cyber_vision']` stays one blob
  and gains `center_id`.
- **Conflict guard**: provisioning a scenario whose stored `center_id` is a DIFFERENT,
  still-existing center raises ConflictError (409) instead of orphaning that center's
  preset/groups/networks/OH levels. Tear down first to move it. This guard is the
  single hinge if fan-out is ever wanted.
- **Resolution chain**: `local_labs.cv_center_id` set at build, immutable (the JWT bakes
  in centerHost). A local-lab agent's center is derived from its lab and LOCKED at
  deploy. Manual/CML agents pick a center, default = the default center. Everything
  downstream (Celery task, teardown, reconcilers) reads the center from stored state,
  never from "the current default".
- **Default center**: exactly one. Routes with no `center_id` use it (back-compat for
  the setup wizard, old clients, and `/cyber-vision/settings`).
- Token store: each center carries both tokens (classic `/api/3.0` + new-UI `/cvapi/v1`).
  Ciphertext copied verbatim from the legacy settings rows (same Fernet key).

## Backend
- [x] Model `CyberVisionCenter` (table `cyber_vision_centers`) + Alembic migration
      (table, `local_labs.cv_center_id` FK)
- [x] `services/cv_centers.py`: get/default/list, `cv_client(db, center_id)`,
      `cv_v1_client(db, center_id)`, legacy settings → default center migration +
      backfill (`local_labs.cv_center_id`, `definition.cyber_vision.center_id`) at startup
- [x] Collapse the four factories onto the helper (cv_service_from_settings,
      cv_v1_service_from_settings, routes get_cv_service, mimic._cv_service)
- [x] Centers CRUD + test routes; `center_id` query param on every /cyber-vision route;
      `/cyber-vision/settings` + `/status` keep working against the default center
- [x] cv_provisioning_service: center-aware provision/groups/networks/OH/teardown,
      conflict guard, vertical roll-up filtered per center, reconcilers per center
- [x] Celery `provision_cyber_vision` carries/reads the center
- [x] Deploy: `cv_center_id` on DeploymentCreate / DeployNewLabRequest / topology deploy;
      local-lab agents locked to their lab's center
- [x] Local labs: `cv_center_id` on build; per-center deployment-token name;
      teardown uses the lab's center
- [x] Topology: all N+1 labs + preset on one center
- [x] Mimic CML: center picker; record `cvcenter:<id>` in the lab description; teardown uses it
- [x] Setup wizard writes the first (default) center; site-config reports per center
- [x] Host-agent: `_newest_cached_sensor_image` only reuses an image from the SAME
      registry (two centers on different CV versions); rebuild host-agent
- [x] Tests: new center tests; update test_admin_settings, test_local_sensor,
      test_agents_deploy, test_topology_provisioning

## Frontend
- [x] Settings → Cyber Vision: list of centers (add/edit/delete/test/set default)
- [x] CyberVisionPage: center selector in the header; store keyed/cleared per center
- [x] LocalLabsTab: center selector in New Local Lab
- [x] DeploymentForm / DeploymentPanel / MultiSensorDeploySection: center selector
      beside "Provision Cyber Vision"; locked + shown for local-lab agents
- [x] CyberVisionBadge / deployment cards: show center name
- [x] Help text

## Ship
- [x] Version bump + release notes; deploy backend + frontend + host-agent; verify live
      against the real center (10.10.20.115)

## Review (2026-09-11)
- Shipped as v1.19.0 on `feat/multi-cv-centers`. Migration `add_cyber_vision_centers`
  applied on boot; the legacy-settings move ran once:
  "migrated legacy settings into default center '10.10.20.115' (8 lab(s), 6 scenario(s) stamped)".
- Tests: backend 1182 passed / 39 xfailed; frontend vitest 119 passed; tsc error set
  identical to master (52, all pre-existing).
- Live checks: one default center; all 8 labs and all 6 provisioned scenarios carry the
  center id; legacy rows gone; `/status` connected (proves the copied ciphertext decrypts);
  all 7 deployments back to running after the restart; host-agent reconciles 8 specs clean.
  A probe second center round-tripped (create, status fails cleanly, duplicate URL 409,
  delete of the in-use default 409, delete 204).
- Per-center deployment-token name: left as is. The `-N` suffix is probed live against
  each center, so it was never global.
- Fixed before deploy (advisor review): the boot migration no longer deletes half-configured
  legacy rows; `usage()` and the vertical roll-up read `cyber_vision.center_id` in SQL
  instead of loading every definition. The celery worker must be rebuilt with the backend
  (it runs `provision_cyber_vision`).
- Rollback: the migration deletes the legacy rows and the alembic downgrade does not restore
  them. Pre-deploy dump + a `system_settings` data dump were kept in the session scratchpad.
- Known gap: CML labs built from a pasted CV compose record no center. The sensor is tied
  to whichever center issued the compose, but a deploy on a CML agent uses the picker
  (default center) and is not locked the way a local-lab agent is. Fix path: match the
  compose's registry host to a center URL at build and store it on the lab.

---

# Durable deployment resume after reboot (2026-09-11)

Context: Alpha lost power 3x (storms) 09-04..09-06; all 7 live deployments went
`disconnected` and stayed there. Auto-redeploy list was in-memory only.

- [x] Migration: `agent_deployments.deploy_config` JSONB (nullable, additive)
- [x] Model: `AgentDeployment.deploy_config`
- [x] `execute_deployment` persists the deploy options (adaptive/attack/cell-iso/topology)
- [x] `AgentManager.resume_disconnected_deployments()` — heartbeat-driven, DB-backed,
      closes the lost row BEFORE replaying, honors `auto_redeploy_on_reconnect`,
      topology rows go through `topology_provisioning_service.deploy` (re-entrant)
- [x] `agent_hub` HEARTBEAT: sync first, then resume
- [x] `health_monitor`: drop in-memory `_disconnected_deployments` path; add
      resume event hooks
- [x] Frontend: tooltip on Disconnected status ("resumes when the agent reconnects")
- [x] Version 1.18.5 + release notes entry
- [x] Unit tests (sqlite) for candidate selection / replay / topology / flag
- [x] Deploy (`docker compose up -d --build backend`) and verify the 7 rows resume live

## Review (2026-09-11)
- Shipped v1.18.5. Migration `add_deployment_deploy_config` applied on boot.
- Tests: 7 new in tests/services/test_deployment_resume.py; tests/api + tests/services = 286 passed.
- Live verification: after the backend restart all 8 agents reconnected; on
  the first heartbeat all 7 disconnected rows were closed (`stopped`) and
  replayed (7 new rows `running`, packets climbing, frames confirmed with
  tcpdump on pa-mon-5a299c7a). Pre-existing rows have deploy_config NULL and
  resumed with the scenario definition alone; rows created from now on carry
  the deploy options.
- Not committed (branch fix/ai-provider-settings-display); commit is the user's call.

---

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
