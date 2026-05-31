# UI Cleanup — Consolidation Pass (2026-05-31)

## Decisions (from user)
- Libraries: **Nested + Overview** → `Overview | CVEs | Attacks | Device Library` (Device Library keeps Protocols/Vendors/Templates sub-tabs)
- Live Traffic: its own page holding **Live Dashboard + Deployments**; Agents hub keeps infrastructure only
- Old routes: **hard removal** (grep + fix in-app links)

## Audit findings
- **Network Defaults**: all 6 keys (`default_subnet_*`, `default_vlan_range_*`) are dead — defined in `models/settings.py` DEFAULT_SETTINGS, never read anywhere. → REMOVE tab + the 6 defaults.
- **Seed Data**: endpoint is idempotent and already runs automatically at every backend boot (`startup.py:294`). Tab is redundant. → REMOVE tab (leave backend endpoint as harmless recovery tool).
- **Traffic Agents** + **Modeling Labs** settings tabs: already just "moved to /agents" pointer stubs. → REMOVE both stubs. CML deploy/connect + local labs already live in Agents hub.
- **Downloads presentations**: 11 files in `backend/app/static/downloads/` (exec-briefing, tech-deep-dive, cisco-briefing) + dict entries in `downloads.py` AVAILABLE_DOWNLOADS. Authoring kit (4 files) + OVA (scanned dir) stay.

## Tasks
- [ ] 1. Library Hub: new `/libraries` page (Overview + CVEs + Attacks + Device Library), nav consolidation, remove old library routes, fix links
- [ ] 2. Live Traffic page: new `/live-traffic` (Live Dashboard + Deployments), remove those tabs from Agents hub, nav entry, route cleanup
- [ ] 3. Settings → AI Integrations: fold AI Provider/Usage/Costs into one tab with Provider/Usage/Costs sub-tabs
- [ ] 4. Settings: remove Network Defaults tab + drop 6 dead defaults from backend
- [ ] 5. Settings: remove Traffic Agents pointer stub tab
- [ ] 6. Settings: remove Modeling Labs pointer stub tab
- [ ] 7. Downloads: delete presentation files + AVAILABLE_DOWNLOADS entries; keep authoring kit + OVA
- [ ] 8. Settings: remove Seed Data tab (keep backend endpoint)
- [ ] 9. Build + deploy (docker compose up -d --build frontend backend), verify

## Tasks (status)
- [x] 1. Library Hub `/libraries` (Overview + CVEs + Attacks + Device Library)
- [x] 2. Live Traffic page `/live-traffic` (Live Dashboard + Deployments)
- [x] 3. Settings → AI Integrations (Provider/Usage/Costs sub-tabs)
- [x] 4. Removed Network Defaults tab + 6 dead defaults (DEFAULT_SETTINGS + live DB rows)
- [x] 5. Removed Traffic Agents + Modeling Labs stub tabs
- [x] 6. Downloads: deleted 10 presentation files + manifest entries + dead UI code
- [x] 7. Removed Seed Data tab (backend endpoint left intact)
- [x] 8. Built + deployed (frontend+backend) + verified

## Review
Shipped + deployed (`docker compose up -d --build frontend backend`), backend healthy, v1.7.0.

**Frontend nav** went from 11 entries to a tighter set: `Dashboard · Scenarios ·
Libraries · Agents · Live Traffic · IP Management · Cyber Vision · Architecture ·
Help · Settings`. The three library nav items collapsed into one **Libraries**
entry; **Live Traffic** is now its own top-level entry (gated by LIVE_TRAFFIC).

**Pattern used:** each consolidated page (LibraryHubPage, LiveTrafficPage) embeds
the existing prop-less page components as deep-linkable `?tab=` tabs — same
pattern AgentsHubPage already used. The three library pages got an `embedded`
prop that drops their own padding/title so the hub owns the chrome.

**Routes:** old `/cves`, `/fingerprints`, `/attack-library` removed (hard move);
`/libraries?tab=…` is canonical. `/devices` and `/deployments` kept as
convenience redirects into the new homes. Attack detail moved to
`/libraries/attacks/:id`. Fixed all in-app links (sidebar, command palette,
EmptyDashboard, help relatedPages, attack-detail back buttons).

**Settings** went from 15 tabs to 9: `Overview · AI Integrations · Cyber Vision ·
LDAP/AD · User Management · Downloads · Generated PCAPs · Updates · System`.
AI Provider/Usage/Costs nested under one AI Integrations tab. Network Defaults,
Traffic Agents (stub), Modeling Labs (stub), Seed Data all removed. Overview
deep-links remapped (`ai_provider`→`ai`, `agents`→/agents page).

**Verified live:** downloads endpoint now returns only authoring(4)+appliance(1),
no presentations. settings + site-config endpoints 200. SPA + assets serve.

**Follow-up (optional):** the 6 dead network settings were purged from THIS
install's DB and removed from DEFAULT_SETTINGS (so fresh installs are clean), but
other already-upgraded installs would keep the orphan rows. A tiny alembic
migration deleting those keys would clean every install — not done (rows are
provably inert; flagged for sign-off). Not committed to git yet — awaiting review.
