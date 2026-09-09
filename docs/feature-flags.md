# Feature Flags

> Moved out of `CLAUDE.md` on 2026-09-09 so the always-loaded file stays a map. Content unchanged.


Current flags live in `backend/app/core/features.py` and surface to the
frontend via `/api/v1/about.features`.

- `AI_ENABLED` (default `true`) — when `false`:
  - Backend: `/api/v1/ai/*` and `/api/v1/mcp/*` return 503.
  - Frontend: AI wizard route redirects, AI tab in RightSidePanel
    hides, "AI Create" / "Generate Description" / "AI Scenario Review"
    / "Explain with AI" UI all hide. See `useFeatures` hook and
    `FeatureGate` component.
- `LIVE_TRAFFIC_ENABLED` (default `true`) — gates the live-agent half
  of the platform. When `false` PacketArch ships as an AI-powered
  PCAP-only generator. Behavior:
  - Backend: `/api/v1/agents`, `/deployments`, `/adaptation`,
    `/dashboard/live`, and the runtime-control half of `/attacks` (start,
    stop, advance, pause, inject, state, injection-status) return 503.
    The `/ws/agent` WebSocket and `/agent/*` install bundle are not
    mounted at all. Read endpoints (`/attacks/playbooks`, etc.) stay
    open so the PCAP-only build can populate the attack-playbook
    dropdown in `GeneratePcapModal`.
  - Frontend: `/deployments` and `/live-traffic` routes redirect.
    Sidebar omits both nav entries. Settings tab list omits "Traffic
    Agents". `AgentVersionBanner`, the agent-health bell, and
    `useDeploymentsStore.fetchDeployments()` are all skipped.
  - Attack + adaptive in PCAP: with the flag off, attack playbooks and
    adaptive timing-drift can still be requested per-PCAP via the new
    fields on `GenerationRequest` (`attack_playbook_id`,
    `attack_config`, `adaptive_config`) — `TrafficOrchestrator`
    registers `AttackOrchestrator` and `AdaptiveController` as
    composition peers on `UnifiedOrchestrator` for the PCAP run.

- `MULTI_SENSOR_TOPOLOGY_ENABLED` (default `true`) — per-zone
  IE3500 + sensor topologies and the deploy conductor.
- `MIMIC_ENABLED` (default **`false`**) — device emulation (see
  "PacketArch Mimic" above). When `false`, `/api/v1/mimic/*` returns 503 and
  the `/mimic` + `/mimic/studio` routes redirect. Ships dark: a fresh install
  gains no new surface until it is turned on.

New flag ergonomics: add to `Settings` in `config.py`, add to
`Features` in `features.py`, add to `Features` in
`frontend/src/api/about.ts`, add a `RequireXEnabled` dep and apply to
router — or gate UI via `useFeatures()`.

