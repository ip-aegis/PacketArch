# PacketArch Improvement Roadmap

PacketArch exists to simulate realistic OT/ICS environments and generate traffic that Cisco Cyber Vision discovers, classifies, and monitors — showcasing CV's capabilities in demos and PoCs. Every improvement should be evaluated through that lens: **does it make the demo more convincing, faster to set up, or harder to distinguish from a real plant?**

---

## Quick Wins (1-3 days each)

### 1. One-Click Demo Scenarios — COMPLETE
**Problem:** Setting up a convincing demo takes too many steps — create scenario, add devices, configure protocols, configure flows, deploy.
**Solution:** Added "Quick Demo" button (yellow thunderbolt) on the Scenarios page that opens a streamlined modal. Users pick an industry vertical from a 2x3 card grid, an online agent is auto-selected, and clicking "Launch Demo" creates a scenario from the best template, deploys it to the agent, and navigates to the Live Traffic dashboard. 2-3 clicks total. Verticals without templates (Energy, Oil & Gas) are shown disabled with "Coming soon" tooltip.
**Files:** `QuickDemoModal.tsx` (new), `ScenariosPage.tsx`

### 2. Scenario Readiness Indicator — COMPLETE
**Problem:** Users can't tell if a scenario is deployment-ready. Missing configs cause silent failures.
**Solution:** Added `compute_scenario_readiness()` backend helper that evaluates 8 checks (has devices, has flows, flow endpoints, unique names, unique MACs, IPs assigned, no orphans, protocol/fingerprint consistency) and returns a 0-100 score with `ready`/`warnings`/`not_ready` status. Readiness is computed inline in the scenario list endpoint — no extra API calls. Scenario cards show color-coded badges (green "Ready", yellow "N warnings", red "Not Ready") with a tooltip listing all checks. Studio deployment panel shows a `ReadinessChecklist` with progress bar, per-check pass/fail icons, "Repair" button for protocol mismatches, and "Re-validate" button. Deploy button is disabled when errors exist.
**Impact:** Users see at a glance which scenarios need attention. Deployment errors are caught before the deploy attempt, not after.
**Files:** `schemas/scenario.py` (ReadinessCheck, ReadinessSummary), `api/routes/scenarios.py` (compute_scenario_readiness), `api/scenarios.ts`, `ScenarioCard.tsx`, `ReadinessChecklist.tsx` (new), `DeploymentPanel.tsx`, `DeploymentForm.tsx`

### 3. Deployment Status on Scenario Cards — COMPLETE
**Problem:** Users must navigate to a separate Deployments page to see if traffic is running.
**Solution:** ScenariosPage polls `GET /api/v1/dashboard/live` every 5 seconds and builds a deployment lookup map by scenario ID. Cards with active deployments show a pulsing green dot with "Running on {agent_name}" and packets-per-second. Non-deployed cards are unchanged. Uses existing dashboard API — no backend changes.
**Files:** `ScenariosPage.tsx`, `ScenarioCard.tsx`

### 4. Copy Device Configuration — COMPLETE
**Problem:** Configuring 10 similar PLCs means repeating the same form 10 times.
**Solution:** Right-click any device on the canvas to open a context menu with three actions: "Duplicate Device" (creates a copy with cleared IP/MAC), "Copy Config to N Similar {Type}s" (applies vendor, model, firmware, timing, protocols, CVE config to all devices of the same type — with confirmation modal and full undo support), and "Delete Device". Uses CustomEvent dispatch from DeviceNode to avoid threading callbacks through React Flow's node data system. Menu closes on click-outside or Escape.
**Files:** `DeviceContextMenu.tsx` (new), `DeviceNode.tsx`, `ScenarioCanvas.tsx`

### 5. Protocol Config Presets with Plain-English Labels — COMPLETE
**Problem:** Fields like `jitterMs`, `burstIntervalMs`, `exceptionRate: 0.001` are meaningless to most users.
**Solution:** Added a "Traffic Profile" `Segmented` selector to `FlowPropertyForm` with four presets per protocol: Normal, High-Speed, Maintenance, Degraded. Preset timing values are sourced from backend `LEARNED_DEFAULTS`. Selecting a preset fills in timing values; manually editing a timing field switches to "Custom". Raw timing fields are collapsed behind an "Advanced Timing" toggle. Presets are protocol-aware (e.g., Modbus Normal = 100ms, PROFINET Normal = 4ms, BACnet Normal = 5000ms) with a `_default` fallback.
**Files:** `trafficPresets.ts` (new), `FlowPropertyForm.tsx`

### 6. Agent Version Warning Banner — COMPLETE
**Problem:** Outdated agents cause subtle traffic generation bugs. Version mismatch is buried in a details drawer.
**Solution:** Added a global dismissable `Alert` banner rendered between the Header and Content in `AppLayout`. On mount, fetches agents once from the store. Computes outdated online agents (version !== standardVersion). Shows "{N} agent(s) running outdated versions" with "View Agents" link (navigates to Settings) and "Update All to v{version}" button that triggers `Promise.allSettled` updates on all outdated agents. Banner disappears when all agents are current or user dismisses it.
**Files:** `AgentVersionBanner.tsx` (new), `AppLayout.tsx`

### 7. Delete Deprecated Models & Dead Code — COMPLETE
**Problem:** `VendorFingerprint` and `LearnedDeviceFingerprint` models are deprecated but still in code.
**Solution:** Deleted both deprecated model files (`vendor_fingerprint.py`, `learned_device_fingerprint.py`), the dead schema file (`schemas/vendor_fingerprint.py`), and a broken utility script (`scripts/generate_missing_templates.py`). Updated stale docstrings/comments in `vulnerable_fingerprint.py`, `scenario_templates/base.py`, and `fingerprint_cache.py` to reference `DeviceTemplate` instead of `VendorFingerprint`. Alembic migration `20260205_drop_legacy_fingerprint_tables.py` handles the DB table drops. Net removal: ~1,001 lines of dead code.
**Impact:** Cleaner codebase, no more deprecated models confusing developers. All fingerprint data consolidated in `DeviceTemplate`.
**Files:** `models/vendor_fingerprint.py` (deleted), `models/learned_device_fingerprint.py` (deleted), `schemas/vendor_fingerprint.py` (deleted), `scripts/generate_missing_templates.py` (deleted), `models/vulnerable_fingerprint.py`, `scenario_templates/base.py`, `services/fingerprint_cache.py`

---

## Moderate Ideas (1-2 weeks each)

### 8. Live Traffic Dashboard — COMPLETE
**Problem:** Once traffic is deployed, users have zero visibility into what's being generated. They just trust it's working.
**Solution:** Built a real-time `/live-traffic` dashboard with per-protocol packet rates, bandwidth utilization, active flows, and per-agent status. Added `TrafficStats` collection at the `UnifiedOrchestrator` dispatch layer (per-protocol packets/bytes with rolling rate window). Enhanced agent STATUS messages with `bytes_sent`, `protocol_breakdown`, `flow_count`, `packets_per_second`, `bytes_per_second`. Server-side `TrafficDashboardService` aggregates stats in-memory with 5-minute time-series. Frontend uses recharts for protocol breakdown pie charts and packet-rate sparklines, polling every 3 seconds. Backward-compatible with old agents.
**Impact:** The "wow" screen for demos — live per-protocol traffic visualization, agent health monitoring, and real-time bandwidth metrics.
**Files:** `protocol_engines/traffic_stats.py`, `protocol_engines/output.py`, `protocol_engines/unified_orchestrator.py`, `services/traffic_dashboard.py`, `api/routes/dashboard.py`, `agent_hub.py`, `orchestrator_pool.py`, `websocket_client.py`, `LiveTrafficDashboardPage.tsx`, `components/dashboard/*`

### 9. CV Comparison Feedback Loop — COMPLETE
**Problem:** The Cyber Vision comparison page shows matches/mismatches but doesn't close the loop. Users don't know what to do next.
**Solution:** Added actionable comparison insights generated server-side: match quality summary, Layer 2 protocol visibility warnings (PROFINET devices need same-VLAN sensor), enrichment suggestions, and CV-only device notes. Comparison now populates the `cv_only` field (was always empty) showing CV-discovered devices not in the scenario. Single-device enrichment modal shows before/after property preview (CV current vs PacketArch proposed). After any enrichment, a "Re-compare" prompt appears with one-click re-comparison. Bulk enrichment "Done" footer now offers "Re-compare" to verify changes took effect. Store tracks `enrichedSinceCompare` flag to drive the prompt.
**Impact:** Users get clear guidance on why devices are missing, what to do about it, and can verify enrichment worked — all without leaving the page.
**Files:** `schemas/cyber_vision.py` (ComparisonInsight schema), `api/routes/cyber_vision.py` (generate_comparison_insights, cv_only population), `api/cyberVision.ts`, `cyberVisionStore.ts`, `CyberVisionPage.tsx`

### 10. Guided Scenario Builder (Wizard Mode)
**Problem:** Blank canvas is intimidating. Template wizard exists but doesn't guide device-level configuration.
**Idea:** Step-by-step wizard: (1) Pick vertical → (2) Pick template → (3) Review auto-generated devices → (4) Customize specific devices → (5) Review flows → (6) Deploy. Each step validates before proceeding. Replaces the current "dump everything on canvas and hope" workflow.
**Files:** New `ScenarioWizard.tsx`, `TemplateWizardModal.tsx` (extend), `scenarioStore.ts`

### 11. Multi-Agent Coordinated Deployment
**Problem:** Each agent runs independently. Real plants have traffic from multiple network segments.
**Idea:** Allow a single scenario to span multiple agents. Zone A runs on Agent-1 (OT network), Zone B runs on Agent-2 (DMZ). Server coordinates synchronized start/stop. Cross-zone flows generate traffic visible from both segments — making CV's cross-network correlation features shine.
**Files:** `agent_manager.py`, `agent_hub.py`, `DeploymentPanel.tsx`, `orchestrator_pool.py`

### 12. Traffic Phase Scheduling — COMPLETE
**Problem:** Real plants have distinct traffic phases (startup, normal ops, shift change, maintenance). Current traffic is monotone.
**Solution:** Built `PhaseScheduler` in `protocol_engines/adaptive/phase_scheduler.py` that cycles through deployment phases (startup → steady_state → maintenance → shutdown) based on elapsed time. Each phase applies a distinct rate multiplier (e.g., startup=0.1x, steady=1.0x, maintenance=0.3x). Composition order: phase (lifecycle) → schedule (time-of-day) → directives → micro. Agent auto-populates phase schedule from `definition.phases` — zero configuration needed for existing scenarios. Phase control (skip/force/pause) via REST API at `/api/v1/adaptation/{id}/phase/`. Frontend: collapsible Phase Schedule config in DeploymentForm with per-phase duration inputs, PhaseTimeline component in DeploymentCard with colored timeline bar, progress indicator, skip/pause controls. 73 tests passing. Agent bumped to v1.10.0.
**Impact:** Long-running demos now look realistic over time — traffic ramps up during startup, settles into steady state, briefly dips during maintenance windows, and gracefully shuts down. Phase cycling is automatic and repeating.
**Files:** `protocol_engines/adaptive/phase_scheduler.py` (new), `adaptive/types.py`, `adaptive/controller.py`, `adaptive/__init__.py`, `scenario_templates/phases.py`, `api/routes/adaptation.py`, `services/adaptation_service.py`, `schemas/agent.py`, `api/routes/agents.py`, `orchestrator_pool.py`, `agent/version.py`, `DeploymentForm.tsx`, `DeploymentPanel.tsx`, `PhaseTimeline.tsx` (new), `api/adaptation.ts` (new), `types/agent.ts`

### 13. Bandwidth & Rate Control
**Problem:** Agents inject packets as fast as possible. No way to simulate realistic bandwidth constraints.
**Idea:** Add configurable rate limiting per deployment: target bandwidth (e.g., 5 Mbps), max packets/sec, burst allowance. Agent throttles injection to match. Prevents saturating demo networks.
**Files:** `live_orchestrator.py`, `orchestrator_pool.py`, `DeploymentForm.tsx`

### 14. Increase Test Coverage to 75%+
**Problem:** 5.7% test coverage. Changes are high-risk with no safety net.
**Idea:** Add integration tests for the core workflow: create scenario → add devices → generate traffic → verify PCAP output. Add protocol engine consistency tests (every engine must implement the same interface). Add CV integration mocks.
**Files:** `tests/` directory, `ci.yml` (raise threshold)

---

## Hard Ideas (1-2 months each)

### 15. Unified Traffic Engine (Backend + Agent Parity) — COMPLETE
**Problem:** Backend generates PCAPs with `TrafficOrchestrator` + full fingerprint applicator. Agent uses `LiveTrafficOrchestrator` with hardcoded protocol constants. They diverge — agent traffic is less realistic than PCAP output.
**Solution:** Created `UnifiedOrchestrator` with `PacketOutput` protocol abstraction (`PcapOutput` for files, `LiveOutput` for live injection). Agent now imports shared `protocol_engines/` package via Docker build staging. Added `CloudServiceEngine` for TLS heartbeats (replacing standalone scheduler). Deleted agent's `live_orchestrator.py` (4,957 lines) and `cloud_traffic_scheduler.py` (354 lines). Net result: -3,950 lines, 22 registered protocols, full parity between PCAP and live output.
**Impact:** Traffic from live agents is now indistinguishable from PCAP files. CV sees the same device identities regardless of how traffic was generated.
**Files:** `protocol_engines/unified_orchestrator.py`, `protocol_engines/output.py`, `protocol_engines/cloud_service/`, `orchestrator_pool.py` (rewritten)

### 16. Adaptive Traffic Generation — COMPLETE
**Problem:** Traffic patterns are static — defined at scenario creation time and never change. Perfectly periodic polling is detectable as synthetic.
**Solution:** Built a 3-phase adaptive traffic system in `protocol_engines/adaptive/` package. **Phase 1 (Micro-Variations):** `MicroVariationEngine` applies bounded random walk timing drift (±5%), probabilistic retransmissions (0.2%), periodic TCP connection resets (1-2h), and per-vendor personality traits (15 vendors with consistency/warmup/eager parameters). ON by default for all deployments — zero configuration required. **Phase 2 (Traffic Scheduling):** `TrafficSchedule` with 4 presets (industrial_24h, office_hours, data_center, constant) for time-of-day macro shaping. Smooth-step interpolation at phase boundaries. Consistent-hash flow activation for deterministic dormancy. **Phase 3 (Server Directives):** `ADAPT_TRAFFIC` WebSocket command enables mid-deployment adjustments. REST API at `/api/v1/adaptation/` for protocol rate adjustment, flow rate adjustment, schedule phase override, and directive reset. Directives use atomic reference swap for thread safety with automatic TTL expiry. `AdaptiveController` composes all three layers: schedule (macro) → directives → micro (fine), with 50ms floor. 73 tests (64 unit + 9 integration) all passing. Agent bumped to v1.9.0.
**Impact:** Every deployment now generates non-robotic traffic indistinguishable from real plants. Server can tune traffic mid-deployment for demo scenarios. CV-informed adaptation (Phase 4) and dashboard UI (Phase 5) deferred.
**Files:** `protocol_engines/adaptive/` (types.py, micro_variations.py, controller.py, schedule.py, __init__.py), `unified_orchestrator.py`, `orchestrator_pool.py`, `services/adaptation_service.py`, `api/routes/adaptation.py`, `agent/main.py`, `websocket_client.py`, `agent_manager.py`, `traffic_dashboard.py`

### 17. PCAP Replay + Augmentation
**Problem:** Customers sometimes have real PCAPs from their environment. They want to replay them with modifications.
**Idea:** Upload a real PCAP → PacketArch analyzes it → user can augment: add more devices, inject anomalies, extend duration, change IP ranges. Then deploy the augmented traffic live. Bridge between real captures and simulated environments.
**Files:** Learning pipeline (extend), new `pcap_replay.py`, `flow_generator.py`

### 18. Agent Health Monitoring & Auto-Recovery — COMPLETE
**Problem:** If an agent's traffic generation stalls or the agent becomes unhealthy, nobody knows until the demo breaks.
**Solution:** Built server-side `HealthMonitorService` with asyncio background loop (10s interval) that detects heartbeat timeouts, packet stalls, resource exhaustion, and scenario errors. In-memory event ring buffer (200 events) with severity levels (info/warning/critical). Auto-recovery stops and restarts stalled scenarios with rate limiting (max 3/hr, 60s cooldown). Auto-redeploy saves disconnected deployments and restores them when agents reconnect (24h TTL). REST API with 7 endpoints under `/health-monitor` for events, status, config. Frontend: HealthEventsFeed on Live Traffic dashboard, health-aware agent badges (healthy/warning/critical/offline), bell icon badge in app header polling every 15s. Agent-side: exponential backoff reconnect (5s → 120s cap), thread liveness checks every 15s. Agent bumped to v1.6.0.
**Impact:** Demos are self-healing — stalled scenarios auto-recover, disconnected agents auto-redeploy, and users get real-time visibility into agent health without manual intervention.
**Files:** `services/health_monitor.py`, `api/routes/health_monitor.py`, `agent_hub.py`, `traffic_dashboard.py`, `api/routes/dashboard.py`, `main.py`, `websocket_client.py`, `orchestrator_pool.py`, `agent/main.py`, `HealthEventsFeed.tsx`, `AgentStatusCards.tsx`, `AgentsTab.tsx`, `AppLayout.tsx`, `healthMonitor.ts`

### 19. Scenario Version Control — COMPLETE
**Problem:** Scenarios are mutable. No history, no undo beyond the canvas, no way to compare two versions.
**Solution:** Built Git-like versioning for scenarios with a `ScenarioVersion` model storing full definition snapshots. Dual versioning strategy: auto-coalescing creates silent snapshots every 5 minutes of editing activity, while explicit "Save Version" button (+ Ctrl+S shortcut) lets users create named checkpoints. Version History drawer shows a timeline of all versions with relative timestamps, source tags (Manual/Auto-saved/Pre-rollback), device/flow counts, inline label editing, and per-version actions. Compare any two versions with a structured diff modal showing field-level changes grouped by category (devices, flows, zones, phases, metadata) with color-coded added/removed/modified entries. Restore to any previous version with automatic safety snapshot. 50-version retention cap with auto-pruning of oldest versions. Position-only changes (device drags) are filtered from diffs. Cascade delete cleans up all versions when a scenario is deleted.
**Impact:** Users can safely iterate on scenarios during demo prep, compare changes between editing sessions, and restore previous states with zero risk of data loss.
**Files:** `models/scenario_version.py` (new), `alembic/versions/20260207_add_scenario_versions.py` (new), `services/scenario_diff.py` (new), `schemas/scenario_version.py` (new), `api/routes/scenario_versions.py` (new, 7 endpoints), `api/routes/scenarios.py` (auto-coalescing), `main.py`, `api/scenarioVersions.ts` (new), `VersionHistoryDrawer.tsx` (new), `VersionDiffModal.tsx` (new), `CanvasControls.tsx`, `ScenarioStudioPage.tsx`

---

## Moonshot Ideas (3+ months, paradigm shifts)

### 20. Digital Twin Mode — Mirrored Real Environment
**Problem:** Demos use simulated environments. Customers want to see CV handle *their* actual environment.
**Idea:** Connect PacketArch to a customer's real network (read-only span port). PacketArch learns every device, protocol, and flow pattern automatically. Then generates a complete digital twin that can run independently. Customer sees CV discover an exact replica of their plant — without touching production. The ultimate "what if we deployed CV" demo.
**Impact:** Transforms PacketArch from "traffic generator" into "environment cloning platform."

### 21. CV Feature Coverage Map
**Problem:** Demos showcase whatever the SE remembers to show. No systematic way to exercise all CV features.
**Idea:** PacketArch maintains a matrix of Cyber Vision capabilities (device discovery, protocol decoding, vulnerability detection, anomaly detection, baseline monitoring, etc.). For each deployed scenario, it shows which CV features are being exercised and which aren't. "Your demo covers 7 of 15 CV features. Add a BACnet device to showcase building automation discovery. Inject CVE-2024-1234 to trigger vulnerability alerting."
**Impact:** Every demo becomes a comprehensive CV capability showcase. SEs never miss a feature.

### 22. Multi-Tenant Cloud-Hosted PacketArch
**Problem:** Every SE installs and maintains their own PacketArch instance.
**Idea:** Cloud-hosted PacketArch (SaaS). SEs log in, build scenarios in the browser, and deploy agents to customer sites via one-liner install. Scenarios are shared across the team. Central template library updated by product team. Remote agents phone home to cloud instance.
**Impact:** Zero setup for SEs. Consistent experience. Centrally managed templates.

### 23. AI Scenario Generation from Customer Documentation
**Problem:** Building scenarios requires OT knowledge. SEs often have customer network diagrams (Visio, PDFs) but must manually recreate them.
**Idea:** Upload a customer's network diagram (image/PDF/Visio) → AI vision model extracts devices, network topology, protocols → generates a complete PacketArch scenario. "Here's the Visio from the customer's water plant — PacketArch built the scenario automatically."
**Impact:** Minutes instead of hours for scenario creation. Non-technical SEs can build complex scenarios.

### 24. Competitive Shootout Mode
**Problem:** Customers evaluate multiple OT security vendors simultaneously.
**Idea:** PacketArch generates identical traffic visible to multiple security tools simultaneously. Built-in comparison framework: "Nozomi detected 8 devices, Claroty detected 10, Cyber Vision detected 14." Traffic includes increasingly subtle scenarios to test detection depth. Automatically generates a comparison report.
**Impact:** Structured competitive advantage. Data-driven proof CV is superior.

### 25. Live Attack Simulation
**Problem:** Anomaly injection exists but is basic (protocol violations, timing anomalies). Real attacks are multi-stage.
**Idea:** Full attack kill-chain simulation: reconnaissance (port scans, device enumeration) → initial access (default credentials, known exploits) → lateral movement (protocol abuse, session hijacking) → impact (register manipulation, firmware modification attempts). CV should detect each stage. Playbook-based: "Run Triton attack scenario", "Run PIPEDREAM scenario."
**Impact:** Demonstrates CV's detection depth against real-world ICS attack frameworks. The most compelling demo possible for security-focused buyers.

---

## Suggested Priority Order

**Immediate impact for demos (do first):**
1. ~~One-Click Demo Scenarios (#1) — COMPLETE~~
2. ~~Live Traffic Dashboard (#8) — COMPLETE~~
3. ~~Deployment Status on Cards (#3) — COMPLETE~~
4. ~~Scenario Readiness Indicator (#2) — COMPLETE~~
5. ~~Protocol Config Presets (#5) — COMPLETE~~
6. ~~Copy Device Configuration (#4) — COMPLETE~~
7. ~~Agent Version Warning Banner (#6) — COMPLETE~~

**Realism improvements (makes CV see more convincing traffic):**
6. ~~Traffic Phase Scheduling (#12) — COMPLETE~~
7. ~~Unified Traffic Engine (#15) — COMPLETE~~
8. ~~Adaptive Traffic Generation (#16) — COMPLETE~~
9. Bandwidth & Rate Control (#13)

**CV integration tightening:**
9. ~~CV Comparison Feedback Loop (#9) — COMPLETE~~
10. CV Feature Coverage Map (#21)

**Operational resilience:**
11. ~~Agent Health Monitoring & Auto-Recovery (#18) — COMPLETE~~

**Platform maturity:**
12. Guided Scenario Builder (#10)
13. Multi-Agent Coordination (#11)
14. Test Coverage (#14)
15. ~~Dead Code Cleanup (#7) — COMPLETE~~
16. ~~Scenario Version Control (#19) — COMPLETE~~
