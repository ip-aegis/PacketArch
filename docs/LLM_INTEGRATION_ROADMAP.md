# LLM Integration Roadmap — PacketArch

## Context

PacketArch already has solid AI integration for scenario **generation** (AI Wizard with structured outputs, AI Chat with 50+ MCP tools, AI Help). But AI touches almost nothing outside creation — validation, deployment, security testing, error handling, and day-to-day UX are all manual. This plan identifies every opportunity to inject LLM calls across the app, from trivial UX polish to transformative new capabilities.

**Constraint:** Cost is not a concern. Opus 4.6 for everything. Goal is maximum outcome quality.

**Current AI surfaces:** AI Wizard (scenario generation), AI Chat Assistant (iterative editing via MCP tools), AI Help (9 contexts with proper system message delivery), AI Description Generator, AI Device Namer (349 lines, exists but underused), Version Diff Summarizer, Deployment Error Explainer.

---

## EASY — Small, self-contained, reuses existing patterns. < 1 day each.

### ~~E1. Fix ai_help.py system prompt delivery~~ DONE (2026-02-15)
System prompt now sent as proper `role: "system"` message with ephemeral prompt caching. Extracted `_extract_response_text()` helper for reuse.

### ~~E2. Expand AI help to 9 contexts~~ DONE (2026-02-15)
Expanded from 2 to 9 contexts: general, deployment, deployment_error, scenario_studio, device_config, protocol_selection, attack_config, cyber_vision, process_sim. Added `helpChat()` frontend API method.

### ~~E3. Version diff NL summarization~~ DONE (2026-02-15)
`POST /scenarios/{id}/versions/diff-summary` endpoint. "Summarize" button in VersionDiffModal summary bar with styled AI summary card.

### ~~E4. Deployment error AI explainer~~ DONE (2026-02-15)
"?" button next to deployment errors in DeploymentCard opens modal with AI explanation via `deployment_error` help context.

### E5. CVE plain-English tooltips
**What:** CVE descriptions are dense NIST text. Add an "Explain" button in the CVE browser that translates *"Buffer overflow in Siemens SIMATIC S7-1500..."* into *"An attacker on your OT network can remotely crash or take control of this PLC by sending crafted S7 packets on TCP port 102. Exploitable from any device with network access."*
**Files:** Backend: `POST /ai/explain-cve` endpoint (~40 lines). Frontend: CVE browser drawer — add explain button (~20 lines).
**Scope:** ~60 lines total.

### E6. Vertical auto-inference from scenario name/description
**What:** When a user types "Water Treatment SCADA Network" in CreateScenarioModal, auto-populate the vertical dropdown. A lightweight AI call (or keyword matching with AI fallback) infers the vertical.
**Files:** Backend: `POST /ai/infer-vertical` (~30 lines, structured output returning one of 6 verticals). Frontend: `CreateScenarioModal` — debounced call on blur (~40 lines).
**Scope:** ~70 lines total.

### E7. Fingerprint selection assistant
**What:** When a user picks a device vendor in the property panel but hasn't selected a model, suggest the best fingerprint from the 295 available based on device type, intended protocols, and scenario vertical. Currently only the AI scenario designer does fingerprint selection internally.
**Files:** Backend: `POST /ai/suggest-fingerprint` (~50 lines). Frontend: `VendorFingerprintSection.tsx` — "Suggest" button next to model dropdown (~30 lines).
**Scope:** ~80 lines total.

### E8. Smart empty states with onboarding suggestions
**What:** When the scenarios list is empty, instead of static "No scenarios found" text, generate a contextual welcome message with 2-3 suggested starting points based on system state (agents connected? CV configured? Which verticals available?). Single AI call, cached in localStorage.
**Files:** Backend: add `onboarding` context to ai_help.py. Frontend: `ScenariosPage.tsx` empty state — call AI on first render (~50 lines).
**Scope:** ~80 lines total.

---

## MEDIUM — New endpoint or component, 3-6 files, 1-3 days each.

### M1. Readiness coach with AI fix suggestions
**What:** Enhance readiness checks beyond binary pass/fail. New `POST /scenarios/{id}/readiness-coach` endpoint takes the readiness results + scenario definition and returns step-by-step fix guidance for each failed check. *"3 flows missing endpoints → Flow 'PLC_to_RTU' has no target device. Your scenario has RTU_North (Modbus) which would be a natural target. Click the flow and set target to RTU_North."*
**Files:** `backend/app/api/routes/scenarios.py` — new endpoint. `backend/app/schemas/scenario.py` — add `fix_suggestion` field to `ReadinessCheck`. Frontend readiness component — expandable "How to fix" section.
**Scope:** ~80 lines backend, ~60 lines frontend.

### M2. Scenario review/critique endpoint
**What:** `POST /ai/scenarios/{id}/review` — analyzes a complete scenario and returns structured optimization suggestions across categories: topology (orphan devices, missing connections), timing (unrealistic intervals), protocols (vendor mismatches), realism (missing zones, hierarchy violations), and security (no CVEs applied, no attack surface). Goes beyond readiness checks into qualitative assessment. Frontend adds a "Review" button in Studio toolbar.
**Files:** `backend/app/api/routes/ai.py` — new endpoint. New `ScenarioReviewResponse` schema. Frontend: `CanvasControls.tsx` — button + review results drawer.
**Scope:** ~120 lines backend, ~150 lines frontend.

### M3. Attack playbook narrator + recommender
**What:** Two new endpoints: (a) `POST /attacks/recommend` — takes scenario definition, returns ranked playbooks with rationale (*"PIPEDREAM_LIKE is the best fit — your scenario has Schneider and Rockwell PLCs with EtherNet/IP, matching the real PIPEDREAM malware's target profile"*). (b) `POST /attacks/playbooks/{id}/narrate` — explains each stage in context of the scenario's specific devices. Frontend adds "Recommended" badges and per-stage narrative in AttackPanel.
**Files:** `backend/app/api/routes/attacks.py` — 2 new endpoints. Frontend: `AttackPlaybookLibrary.tsx`, `AttackPanel.tsx`.
**Scope:** ~100 lines backend, ~100 lines frontend.

### M4. Cyber Vision comparison narrator
**What:** The CV comparison page shows tables but no narrative. Add `POST /cyber-vision/analyze-comparison` that takes comparison results and generates AI insights: *"4 unmatched Siemens PLCs likely invisible because they use PROFINET (Layer 2). CV sensors at the aggregation switch may not see cell-level traffic. Deploy a SPAN port on the cell-level switch, or add S7comm polling to make them visible at Layer 3."*
**Files:** `backend/app/api/routes/cyber_vision.py` — new endpoint. Frontend: `CyberVisionPage.tsx` — narrative summary section.
**Scope:** ~80 lines backend, ~50 lines frontend.

### M5. Protocol recommendation for new flows
**What:** When a user creates a flow between two devices, suggest the best protocol based on both devices' vendors, fingerprints, and supported protocols. *"Recommended: EtherNet/IP — both devices are Rockwell Allen-Bradley with EtherNet/IP identity data."* Can be done client-side from fingerprint data already in the scenario definition, with AI fallback for ambiguous cases.
**Files:** Backend: `POST /ai/recommend-protocol` (~60 lines). Frontend: flow creation UI — "Suggested" badge (~40 lines).
**Scope:** ~100 lines total.

### M6. Deployment pre-flight summary
**What:** Before clicking "Deploy," show an AI-generated summary: *"This deployment will inject Modbus TCP traffic between 8 Schneider PLCs and 24 sensors at 500ms intervals on interface eth0 of Agent-1. Expected rate: ~2,400 polls/min. Phases: 5min startup → 60min steady → 15min maintenance → 5min shutdown. Total: ~80 minutes."*
**Files:** Backend: `POST /ai/deployment-summary` (~60 lines). Frontend: `DeploymentForm.tsx` — summary card above Deploy button (~80 lines).
**Scope:** ~140 lines total.

### M7. Guided Builder AI intelligence
**What:** Enhance the guided builder at three points: (a) template recommendation from NL description, (b) device role explanation tooltips during review, (c) customization suggestions (*"Consider adding a historian for realistic data archiving traffic"*).
**Files:** Backend: `POST /ai/recommend-template` endpoint. Frontend: `TemplateSelectStep.tsx`, `DeviceCustomizeStep.tsx`, `guidedBuilderStore.ts`.
**Scope:** ~80 lines backend, ~120 lines frontend.

### M8. Expand AIDeviceNamer across the app
**What:** The `AIDeviceNamer` (349 lines at `backend/app/ai_services/device_namer.py`) is only used by the AI scenario designer. Expose as: (a) "AI Rename All" button in Studio toolbar, (b) automatic naming during template creation, (c) per-device "Suggest Name" button in property panel.
**Files:** Backend: `POST /ai/name-devices` endpoint wrapping existing service (~40 lines). Frontend: canvas toolbar + property panel (~60 lines).
**Scope:** ~100 lines total.

### M9. Flow timing AI optimizer
**What:** When a scenario has all flows at default 1000ms timing, an AI call analyzes device types and flow purposes to suggest differentiated timing: safety flows at 100ms, monitoring at 2000ms, trending at 5000ms. *"Your safety PLC-to-ESD flow should poll at 50-100ms, not 1000ms. Trending historian flow can safely run at 5000ms."*
**Files:** Backend: `POST /ai/optimize-timing` (~60 lines). Frontend: flow property form or batch timing panel (~50 lines).
**Scope:** ~110 lines total.

### M10. Deployment post-mortem
**What:** After a deployment completes or fails, generate an AI summary: devices that connected, packets generated, errors encountered, phase durations, attack stages completed. Data already flows through WebSocket status messages — just needs aggregation and AI narration.
**Files:** Backend: `POST /ai/deployment-postmortem` (~80 lines). Frontend: completed deployment detail view (~60 lines).
**Scope:** ~140 lines total.

---

## HARD — Significant new feature, 6+ files, 3-7 days each.

### H1. Contextual AI copilot with proactive suggestions
**What:** The AI monitors user actions (device additions, flow creation, readiness changes) and proactively offers suggestions via non-intrusive banners: *"You added a Siemens PLC but no HMI — add a SIMATIC HMI to monitor it?"* Frontend emits action events to a lightweight suggestion endpoint. Requires careful UX to avoid being annoying (debouncing, dismissal, frequency limits).
**Files:** New `backend/app/services/ai_copilot_service.py`. New `POST /ai/copilot/suggest`. New `CopilotSuggestionBanner.tsx`. Hooks into `scenarioStore.ts` action events.
**Scope:** ~200 lines backend, ~250 lines frontend.

### H2. Custom attack playbook designer from NL
**What:** Describe an attack in natural language (*"Simulate an insider threat where a compromised HMI scans PLCs then writes unauthorized values to safety registers"*) and AI generates a complete `AttackPlaybook` with stages, actions, timing, and MITRE mappings. Uses structured outputs matching the existing `AttackPlaybook` dataclass. The action registry already has 17+ generators to compose from.
**Files:** New `backend/app/ai_services/ai_attack_designer.py` (following `ai_scenario_designer.py` pattern). `backend/app/api/routes/attacks.py` — new `POST /attacks/playbooks/generate`. Frontend: "Create Custom" tab in AttackPanel.
**Scope:** ~300 lines backend, ~150 lines frontend.

### H3. Process simulation AI designer
**What:** Describe a process (*"Water treatment train with chemical dosing, pH control, sedimentation"*) and AI generates the `ProcessModel` with variables, equations, state transitions, and fault scenarios. Uses structured outputs matching existing `ProcessVariable`, `ProcessEquation`, `FaultScenario` dataclasses in `backend/app/protocol_engines/process_sim/types.py`.
**Files:** New `backend/app/ai_services/ai_process_designer.py`. New `POST /ai/process-model/generate`. Frontend: process sim config panel.
**Scope:** ~250 lines backend, ~200 lines frontend.

### H4. Anomaly campaign planner
**What:** AI designs multi-phase detection testing campaigns: *"Phase 1 (30min) — subtle timing anomalies to test baseline drift detection. Phase 2 (15min) — unauthorized register writes to test alert thresholds. Phase 3 (10min) — full port scan for network visibility."* Orchestrates existing anomaly injection, attack playbooks, and adaptive traffic into a coordinated test plan.
**Files:** New `backend/app/ai_services/ai_campaign_planner.py`. New endpoints. Frontend: campaign planning wizard. Integration with anomaly + attack systems.
**Scope:** ~250 lines backend, ~300 lines frontend.

### H5. Real-time deployment commentary
**What:** During a live deployment, AI periodically narrates progress: *"Startup phase complete — 8 Modbus connections in 12s. Steady state: 24 poll flows at 500ms. Rate: 2,880 polls/min. Micro-variations: ±3% jitter."* Uses existing deployment status polling data as input.
**Files:** Backend: `POST /ai/deployment-commentary` (~100 lines). Frontend: commentary widget in DeploymentCard (~150 lines). Throttled to avoid excessive API calls.
**Scope:** ~250 lines total.

---

## MOONSHOT — Transformative, complex architecture, 1-3 weeks each.

### S1. Full conversational scenario builder
**What:** Replace the 6-step wizard with a pure NL conversation: *"Build me a manufacturing scenario with 3 CNC cells, each with a Siemens S7-1500. Add an HMI per cell and central SCADA. Use PROFINET for cell traffic and S7comm for HMI-to-PLC."* AI uses existing MCP tools to incrementally build the scenario, streaming progress to a live canvas preview. The infrastructure exists (50+ tools, SSE streaming) but making this the **primary** creation flow requires multi-turn refinement, undo, partial previews, and real-time canvas sync.
**Files:** Major refactor of `frontend/src/components/ai-wizard/`. Enhanced prompting in `backend/app/services/ai_chat_service.py`. Live canvas preview component. ~500+ lines across 8-10 files.

### S2. Natural language deployment control
**What:** *"Slow down the Modbus traffic to 50%"* → `POST /adaptation/{id}/protocol-rate`. *"Skip to maintenance phase"* → `POST /adaptation/{id}/phase/skip`. *"Pause the attack"* → `POST /attacks/{id}/pause`. AI parses NL commands and maps to existing adaptation/attack REST APIs. The underlying API surface already exists; the challenge is reliable NL-to-API mapping.
**Files:** New `backend/app/ai_services/ai_deployment_controller.py` (~200 lines). NL input field in deployment panel (~100 lines).

### S3. AI-powered traffic realism analyzer
**What:** After generating a PCAP or during a live deployment, AI analyzes traffic for realism issues: *"All 24 Modbus polls complete in exactly 500ms with 0 variance — real PLCs show 2-5% jitter. Micro-variation settings produce only 0.1% variance."* Requires parsing PCAP metadata or deployment statistics and comparing against real-world OT patterns.
**Files:** New `backend/app/ai_services/ai_realism_analyzer.py` (~300 lines). PCAP metadata integration. Realism score panel in deployment view (~150 lines).

### S4. Cross-scenario intelligence
**What:** AI learns from all scenarios a user has created to improve recommendations: *"Based on your 5 water/wastewater scenarios, you typically use Schneider M580 PLCs at 1000ms intervals. For this new scenario, I suggest the same but with BACnet for the building automation zone."* Requires aggregating patterns across scenarios into a user preference model.
**Files:** New backend service for pattern extraction. Enhanced AI system prompts with user history. Potential new DB table. ~400 lines backend.

### S5. Cyber Vision predictive matching
**What:** Before running a CV comparison, AI predicts match results: *"4 of your 8 Siemens devices use only PROFINET — unlikely visible to CV unless they also have S7comm or SNMP. Consider adding S7comm flows to improve match rate."* Proactive version of M4 (applied before comparison, not after).
**Files:** New endpoint in `backend/app/api/routes/cyber_vision.py`. Pre-comparison analysis panel in frontend. ~250 lines total.

---

## Recommended Implementation Order

| Phase | Items | Effort | Theme |
|-------|-------|--------|-------|
| ~~1~~ | ~~E1, E2, E3, E4~~ | ~~DONE~~ | ~~Quick wins — fix help, add contexts, diff summaries, error explainer~~ |
| 2 | E5, E6, E7, E8 | ~3 days | Polish — CVE tooltips, vertical inference, fingerprint assistant, empty states |
| 3 | M1, M6, M2 | ~5 days | Deployment intelligence — readiness coach, pre-flight, scenario review |
| 4 | M3, E5, M4 | ~4 days | Security testing — attack narrator, CVE explanations, CV narrator |
| 5 | M5, M8, M9 | ~4 days | Studio intelligence — protocol rec, device naming, timing optimizer |
| 6 | M7, M10 | ~3 days | Builder + post-mortem — guided builder AI, deployment summaries |
| 7 | H1, H2 | ~8 days | Proactive AI + attack designer |
| 8 | H3, H4, H5 | ~10 days | Advanced generation — process sim, campaigns, commentary |
| 9 | S1-S5 | Ongoing | Moonshots |

## Items to Combine
- **E1 + E2**: Same file, same PR — fix the bug and expand contexts together
- **M1 + M2**: Readiness coach and scenario review overlap — review is a superset
- **M3 + H2**: Attack narrator builds the foundation for custom playbook designer
- **E4 + M6**: Error explainer and pre-flight summary both improve deployment UX
- **S2 + H5**: NL deployment control (input) and commentary (output) are two sides of one coin
