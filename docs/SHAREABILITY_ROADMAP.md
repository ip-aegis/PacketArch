# PacketArch: Shareability & Distribution Roadmap

## Context

PacketArch is a feature-complete OT Traffic Simulation Platform with 13 pages, 6 protocol engines, 295 device templates, attack simulation, process simulation, and Cisco Cyber Vision integration. The codebase is production-grade (Docker multi-stage builds, CI/CD, health checks, 45+ backend tests) but was built as an internal/single-deployment tool. This roadmap identifies what's needed to share it — whether as open-source, a commercial product, or an internal tool distributed to multiple teams.

### Audit Summary (2026-02-12)

A full-stack audit was performed across frontend (209 files), backend (150+ files), and DevOps infrastructure. Key findings:

| Area | Grade | Notes |
|------|-------|-------|
| Frontend / UX | **A** | Zero TODOs, enterprise error handling, TypeScript strict, modern stack |
| Backend Architecture | **A-** | Clean async patterns, unified exception hierarchy, 45 test files |
| Backend Security | **C** | 2 route groups completely unauthenticated, CORS too permissive |
| Secrets Management | **B+** | `.env` properly gitignored (never committed), but creds in CLAUDE.md |
| Documentation | **B+** | Excellent CLAUDE.md (550+ lines), missing LICENSE/CONTRIBUTING |
| DevOps / Docker | **A-** | Multi-stage builds, health checks, TLS 1.2+, security headers |
| CI/CD | **B** | 3 workflows, no secret scanning or pre-commit hooks |
| Frontend Testing | **D** | Only 3 test files for 209 source files |

**Bottom line:** The codebase is well-built. Phase 0 (~1 hour of security fixes) closes the critical gaps. Phases 1-3 bring it to share-ready.

---

## Phase 0 — Security Blockers (must fix before any external eyes)

*Effort: ~1-2 hours total. These are all fast, surgical fixes.*

### P0-1: Add auth to adaptation routes *(NEW from audit)*
- **File:** `backend/app/api/routes/adaptation.py`
- **Issue:** All 8 endpoints (directives, schedule-override, protocol-rate, phase skip/force/pause) have **zero** authentication
- **Risk:** Unauthenticated users can manipulate live traffic deployments
- **Fix:** Add `_user: CurrentUser` dependency parameter to every route function

### P0-2: Add auth to attack playbook routes *(NEW from audit)*
- **File:** `backend/app/api/routes/attacks.py`
- **Issue:** GET endpoints (list playbooks, get playbook, compatible playbooks) are publicly accessible
- **Risk:** Unauthenticated enumeration of attack strategies and scenario details
- **Fix:** Add `_user: CurrentUser` dependency to all route functions

### P0-3: Tighten CORS regex *(was QW-3)*
- **File:** `backend/app/main.py:74`
- **Issue:** Regex `r"^https?://.*(:443|:3001|:5173)?$"` matches ANY hostname on those ports
- **Fix:** Remove `allow_origin_regex`, use explicit `allow_origins` list + configurable `ALLOWED_ORIGINS` env var

### P0-4: Remove hardcoded default credentials *(was QW-2)*
- **Files:** `config.py` (defaults), `docker-compose.yml` (fallbacks), `server-init.sh`
- **Issue:** `C!sco123` and `your-secret-key-change-in-production...` as fallback defaults
- **Fix:** Set defaults to `None`, raise startup error if env vars not set; generate random admin password in server-init.sh

### P0-5: Scrub credentials from CLAUDE.md *(was QW-2, audit confirmed)*
- **File:** `CLAUDE.md` (committed to git)
- **Issue:** Documents literal `admin / C!sco123`, server IP `10.10.20.231`, SSH user/password
- **Fix:** Replace with `<ADMIN_PASSWORD>`, `<SERVER_IP>`, reference `.env` for actual values

---

## Phase 1 — Share-Ready Foundation (do before first external share)

*Effort: ~1 day total. Repo hygiene, legal clarity, and code cleanliness.*

### P1-1: Add LICENSE file *(was QW-1)*
- No LICENSE = no legal right to use/redistribute
- **Note:** Scapy dependency is GPLv2 — if distributing PacketArch as a combined work, verify license compatibility. Apache 2.0 is one-way compatible with GPLv2 (GPLv2 code can't be in Apache project, but Apache code can go into GPL project). Consider AGPL-3.0 or proprietary if Scapy is linked.
- Add one-line copyright header to key source files

### P1-2: Add CONTRIBUTING.md and SECURITY.md *(NEW from audit)*
- Neither file exists
- `CONTRIBUTING.md`: dev setup, coding standards, PR process
- `SECURITY.md`: how to report vulnerabilities, response timeline, scope

### P1-3: Replace 29 print() statements with logging *(NEW from audit)*
- **Files:** 15 backend files (fingerprints.py ×4, ai_scenario_designer.py ×3, timing/factory.py ×4, etc.)
- **Fix:** Replace with `logger.debug()` or `logger.info()` — all files already have `logger = logging.getLogger(__name__)`

### P1-4: Gate login page credentials behind dev check *(NEW from audit)*
- **File:** `frontend/src/pages/LoginPage.tsx`
- **Issue:** Default `admin / C!sco123` shown in footer in ALL environments including production
- **Fix:** Wrap with `{import.meta.env.DEV && <CredentialHint />}`

### P1-5: Add frontend .env.example *(was QW-4)*
- Backend has `.env.example`, frontend has none
- Create with `VITE_API_URL` and any other frontend env vars

### P1-6: Enable HTTP → HTTPS redirect *(NEW from audit)*
- **File:** nginx config in Docker frontend
- **Issue:** HTTP redirect block is commented out
- **Fix:** Uncomment the redirect server block

### P1-7: Add pre-commit hooks *(NEW from audit)*
- No `.pre-commit-config.yaml` exists
- Add hooks: `detect-secrets` (prevent credential leaks), `ruff` (Python lint), `eslint` (TS lint)

---

## Phase 2 — Professional Polish (before demos or team handoff)

*Effort: ~3-5 days total. UX improvements, testing, and security hardening.*

### P2-1: First-run setup wizard *(was M-2)*
- New users land on empty dashboard — poor first impression
- Detect first-run (no scenarios, default settings)
- Guided flow: Set admin password → Configure AI key (optional) → Create first scenario → Done

### P2-2: Force password change on first login *(was QW-5)*
- Add `must_change_password` flag to User model
- Frontend redirect to password change form when flag is set

### P2-3: Rate limiting & brute-force protection *(was M-1)*
- `/auth/login` and `/auth/register` have no rate limiting
- Add `slowapi` or Redis-backed limiter (5 attempts/min login, 3 registrations/hour/IP)
- Optional: `ALLOW_PUBLIC_REGISTRATION=false` config flag

### P2-4: Auth on agent download endpoints *(was QW-6)*
- `/agent/install.sh`, `/agent/docker-compose.yml`, `/agent/image.tar.gz` are unauthenticated
- Add token-based auth; rate limiting at minimum

### P2-5: Secret scanning in CI *(NEW from audit)*
- **File:** `.github/workflows/ci.yml`
- Add `detect-secrets` or `gitleaks` step before lint
- Prevents future credential leaks in PRs

### P2-6: Restrict DB/Redis ports in production *(NEW from audit)*
- `docker-compose.yml` exposes PostgreSQL (5432) and Redis (6379) to host
- **Fix:** Use `expose:` (internal only) in production; `ports:` only in `docker-compose.dev.yml` override

### P2-7: Proper error pages *(was M-6)*
- Currently `<Route path="*">` redirects to home
- Add custom 404 page, connection-lost overlay, maintenance mode page

### P2-8: Frontend test coverage expansion *(was M-4)*
- 3 frontend test files vs 209 source files (~1.4% coverage)
- Priority: `scenarioStore`, `agentsStore`, `DeploymentForm`, `GuidedBuilderPage`
- Goal: 15-20 test files; Vitest + MSW infrastructure already in place

### P2-9: Security hardening pass *(was M-5)*
- Move WebSocket agent auth from URL query param to first-message handshake
- Add CSRF protection for state-changing endpoints
- Audit `AdminUser` vs `CurrentUser` usage across all routes

---

## Phase 3 — Distribution Ready (before wide release)

*Effort: ~1-3 weeks total. Features for multi-user/multi-instance deployment.*

### P3-1: Export/import scenarios *(was M-7)*
- JSON export of full scenario (devices, flows, fingerprints, phases, attack config)
- Import with conflict resolution (IP range reallocation, duplicate detection)
- CLI-friendly: `curl`-downloadable export

### P3-2: Demo/sandbox mode *(was M-3)*
- `DEMO_MODE=true` env var
- Seed 2-3 sample scenarios with devices, flows, and completed PCAP on startup
- Read-only badge on demo data, allow cloning

### P3-3: Offline / air-gapped installation *(was H-5)*
- Bundle all Docker images into single `.tar.gz`
- Offline `docker load` + `docker compose up` script
- Pre-bake all pip/npm dependencies
- USB-stick deployable package

### P3-4: Let's Encrypt auto-SSL *(was H-7)*
- Certbot sidecar or ACME integration in nginx
- Auto-renewal cron
- Fallback to self-signed for air-gapped / internal deployments

### P3-5: IP protection decision *(was H-4)*
- 157 protocol engine files + 295 device templates = significant IP
- **Option A (OSS):** Protect via license terms + trademark
- **Option B (Commercial):** Compile protocol engines with Cython, ship as wheel
- **Option C (Hybrid):** Core framework open, premium templates as encrypted add-ons
- Decision depends on distribution model (see Key Decision Point below)

---

## Phase 4 — Enterprise Scale (for multi-team / commercial deployment)

*Effort: weeks to months. Only pursue after distribution model decision.*

### P4-1: Helm chart / Kubernetes deployment *(was H-1)*
- Helm chart with values.yaml for all configuration
- PVCs for postgres, redis, PCAPs
- Ingress with cert-manager for auto-TLS
- HPA for backend/celery workers
- Agent as DaemonSet or sidecar

### P4-2: Multi-tenancy / workspace isolation *(was H-2)*
- Workspace model with FK on scenarios, deployments, agents
- Workspace-scoped API queries
- Per-workspace IP range pools

### P4-3: RBAC (Role-Based Access Control) *(was H-3)*
- Roles: Viewer (read-only), Editor (create/modify), Admin (full control)
- Per-workspace role assignment
- Frontend: hide/disable controls by role
- Backend: role-checking dependency injection

### P4-4: Telemetry & usage analytics *(was H-6)*
- Opt-in anonymous usage events (scenario count, protocols, deployment frequency)
- Opt-in during first-run wizard
- No PII, no network data, no scenario content

---

## Phase 5 — Moonshots (months each, market-dependent)

### MS-1: SaaS offering with billing *(unchanged)*
- Multi-tenant (builds on P4-2), Stripe integration
- Tiered plans: Free (2 scenarios, 1 agent), Pro, Enterprise
- Usage metering (PCAP size, deployment hours, API calls)

### MS-2: Template & playbook marketplace *(unchanged)*
- Community-contributed device templates, attack playbooks, scenario templates
- Submission/review workflow, versioned packages
- Revenue share for premium content creators

### MS-3: White-label / OEM program *(unchanged)*
- Configurable branding (logo, colors, app name)
- Theme configuration via admin UI
- OEM licensing model

### MS-4: Protocol engine SDK / plugin system *(unchanged)*
- Documented `ProtocolEngine` interface with plugin discovery
- Hot-reloadable protocol plugins (Python packages)
- Developer docs + example plugin repo

### MS-5: Open-core model *(unchanged)*
- **Community (Apache 2.0 or AGPL):** Core platform, 6 engines, basic templates, PCAP generation
- **Enterprise (Commercial):** Attack sim, process sim, CV integration, premium templates, RBAC, multi-tenancy
- License key enforcement, same codebase with feature flags

---

## Summary: Priority & Effort Matrix

| Phase | Items | Effort | Blocker For |
|-------|-------|--------|-------------|
| **Phase 0** | 5 security fixes | ~1-2 hours | Any external sharing |
| **Phase 1** | 7 hygiene items | ~1 day | Demo or code review |
| **Phase 2** | 9 polish items | ~3-5 days | Team handoff or customer demo |
| **Phase 3** | 5 distribution items | ~1-3 weeks | Wide release / multiple instances |
| **Phase 4** | 4 enterprise items | ~1-3 months | Multi-team / commercial use |
| **Phase 5** | 5 moonshots | Months each | Market expansion |

---

## Key Decision Point

Before executing beyond Phase 2, the fundamental question is:

**What is the distribution model?**
- **Internal tool** (shared across Cisco teams) → Phase 0-2 + P3-1, skip IP protection
- **Open source** → Phase 0-2, Apache 2.0/AGPL license, P4-1 + MS-4 + MS-5
- **Commercial product** → Phase 0-3 fully, then P4-2/P4-3 + P3-5 + MS-1
- **Hybrid open-core** → Best of both, but highest complexity (MS-5)

This decision shapes which Phase 3+ items matter.

---

## Appendix: Audit Positive Findings (no action needed)

These items were explicitly verified during audit and represent strengths:

- **Frontend:** Zero TODO/FIXME/HACK in 209 files; enterprise error handling (287-line errorUtils.ts with 6 type guards); global ErrorBoundary with dev-only stack traces; smart API URL detection; React 19 + Vite 7 + Ant Design 5
- **Backend:** Unified exception hierarchy (16+ typed exceptions); SQLAlchemy 2.0 async patterns correct; 27 clean Alembic migrations; Pydantic Settings; `.env` properly gitignored and **never committed**
- **DevOps:** Multi-stage Docker builds; health checks on all 4 services; TLS 1.2+ with modern ciphers, HSTS, security headers; 3 GitHub Actions workflows; agent self-update via WebSocket
- **Architecture:** 6 production protocol engines; 295 device templates across 18 vendor modules; adaptive traffic with micro-variations; attack simulation with 6 ICS playbooks; process simulation with 4 vertical templates; broadcast/multicast ecosystem with 8 ambient noise types
