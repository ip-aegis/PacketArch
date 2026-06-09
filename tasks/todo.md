# Help System Overhaul (2026-06-09)

Review found help content badly drifted from the app. Plan approved by user.

## Phase 1 — Fix wrong content
- [x] `admin-settings.tsx` — actual tabs (Overview, AI Integrations [Provider/Usage/Costs], System, Cyber Vision, LDAP/AD, User Management, Downloads, Generated PCAPs, Updates), 3 AI providers incl. CIRCUIT, model routing, agents moved to /agents
- [x] `getting-started.tsx` — 9 UI protocols, 7 verticals, workflow incl. AI create / attacks / Cyber Vision
- [x] `templates.tsx` — 7 verticals + real template names from backend catalog, correct phase names
- [x] `scenario-studio.tsx` — 4 right-panel tabs, toolbar groups, shortcuts (Ctrl+K/Ctrl+S/G), readiness checklist

## Phase 2 — New articles
- [x] `agents-hub.tsx` — Agents / Topology / Local Labs / Modeling Labs (route /agents)
- [x] `attack-simulation.tsx` — 11 playbooks, library, studio Attack tab states, after-action reports, PCAP injection
- [x] `scenario-versions.tsx` — Ctrl+S, auto-versions, labels, diff (+AI summary), rollback safety snapshot
- [x] Register all three in index.ts

## Phase 3 — Expose AI help
- [x] HelpAiAssistant component (aiApi.helpChat, route-derived context, AI_ENABLED gated) in HelpDrawer + HelpPage

## Phase 4 — Guardrails
- [x] index.ts: prefix-match fallback in getArticleForRoute
- [x] Dedupe relatedPages (also found pre-existing /scenarios dual claim by templates) and drop dead /setup mapping
- [x] Vitest: routes covered, unique relatedPages, no dead-route claims, prefix matching, valid cross-links

## Phase 5 — Ship
- [x] tsc clean, 119/119 frontend tests pass
- [x] docker compose up -d --build frontend — container healthy, HTTP 200
- [x] Commit to master

## Review
- 4 articles rewritten against code-verified facts; 3 new articles (agents-hub,
  attack-simulation, scenario-versions) bring registry to 20 articles + glossary.
- AI help endpoint's 9 contexts now reachable: HelpAiAssistant in drawer + /help,
  context derived from route (helpContextForRoute).
- getArticleForRoute gained longest-prefix fallback so /libraries/attacks/:id maps.
- Guardrail test (help.test.ts) parses App.tsx routes; will fail CI if a new page
  ships without help coverage or an article claims a dead/duplicate route.
- Known remaining gaps (deliberate, smaller): no articles yet for process sim,
  adaptive traffic/phases detail, portable scenario format; deployments article
  text could mention phase scheduling. Candidates for a follow-up pass.
