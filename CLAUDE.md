# PacketArch — Claude Code Guide

PacketArch is an OT traffic simulation platform (scenario studio → protocol-accurate PCAP
and live traffic → observed by Cisco Cyber Vision). This file is the **map**: how the box
works, the rules that keep the platform honest, and where the deep reference lives. Read
the linked `docs/` page for a subsystem *when you touch it*, not up front.

---

## Repository & workflow

- **GitHub:** https://github.com/ip-aegis/PacketArch (public, GPL-3.0). Default branch `master`.
- **Auth:** `gh` CLI over HTTPS as the `ip-aegis` account (`gh auth setup-git`). There is no
  SSH key on this box.
- **Branch → PR → merge.** Feature branches off `master`, PR against `master`. Don't commit
  to `master` directly. Stage paths explicitly (`git add <paths>`), never `git add -A`.
- **After every push:** `gh run list --branch <branch> --limit 1`. Red CI = reproduce the
  **full** suite locally (no `-x`) so every failure shows, then fix all of them.
- **Worktrees** are used for parallel branches (`~/PA-portfix`, `~/PacketArch-rail`). A worktree
  has no `node_modules`; symlink the main tree's (`ln -sfn ~/PacketArch/frontend/node_modules frontend/node_modules`).
- **Private sibling:** `ip-aegis/PacketArch-Vista` (`~/PacketArch-Vista`) carries the Splunk
  ops-feed work. Public identifiers stay neutral (`ops_feed_*`, never `vista_*`).

## Running the stack (dev = prod)

There is **one** environment: the Docker Compose stack in `/home/rocsmith/PacketArch`.
Nothing runs on the host with `uvicorn` or `pnpm dev`.

```bash
docker compose up -d --build backend frontend     # after most code changes
docker compose up -d --build celery_worker        # + when touching traffic generation / background jobs
docker compose up -d --build host-agent           # + when touching backend/app/mimic/ or docker/packetarch-host-agent/
docker compose ps && docker compose logs -f backend
```

**Rebuild the right containers.** A Mimic or Local-Lab change that only rebuilds `backend`
leaves a stale `host-agent` that doesn't understand the new spec kind; failures are
*silent* (teardown no-ops, reconcile stamps `error: 'mon_if'`). Same for `celery_worker`
and generation code.

Services: `postgres`, `redis`, `backend` (FastAPI), `celery_worker`, `frontend` (nginx +
built SPA), `pgadmin`, `host-agent` (privileged; the only thing that touches the host),
`updater`. To live-edit the host-agent without rebuilding, add the opt-in override
`docker-compose.host-agent-dev.yml` (see its header).

| Port | Bound to | What |
|------|----------|------|
| 443 / 80 | all interfaces | Frontend (HTTPS, self-signed; 80 redirects) |
| 8001 | compose network only | Backend, via nginx proxy |
| 5432 / 6379 | `127.0.0.1` | PostgreSQL / Redis |
| 5050 | `127.0.0.1` | pgAdmin |

**Config** is the repo-root `.env` (gitignored) over `backend/app/core/config.py` defaults.
A flag enabled only in this box's `.env` ships **default-off** to every other install; check
`config.py` defaults against the release notes before tagging.

First-run wizard, auto-graduation, wizard reset, SSL regeneration, env vars →
[docs/production-stack-ops.md](docs/production-stack-ops.md). Fresh-server install and
upgrades → [DEPLOY.md](DEPLOY.md).

## Tests & lint

There is no Poetry or venv on the host and the backend image ships only main deps, so the
backend suite runs **inside the container** after a one-off dev-dep install (ephemeral —
repeat after a rebuild):

```bash
docker compose exec backend pip install -q pytest pytest-asyncio pytest-cov aiosqlite
docker compose exec backend python -m pytest tests/        # full suite, no -x
cd frontend && pnpm lint && pnpm exec tsc --noEmit && pnpm exec vitest run
```

CI (`.github/workflows/ci.yml`) is the gate: ruff (E,F,W), ESLint + `tsc`, backend pytest
with `--cov-fail-under=45`, vitest, and a compose build + health check. Ruff's fuller config
lives in `backend/pyproject.toml`. `.pre-commit-config.yaml` exists but pre-commit is **not
installed** on this box. Tests use in-memory sqlite via `conftest.py` (no `DATABASE_URL`).

## Code standards

- TypeScript strict mode; Zustand for state; Ant Design components on the project's dark theme.
- Python type hints on every signature; Pydantic schemas for all request/response models;
  SQLAlchemy 2.0 async patterns; every endpoint documented in OpenAPI.
- Backend errors extend `PacketArchError` (`backend/app/core/exceptions.py`), never raw
  `HTTPException`: `ValidationError` 400 · `NotFoundError` 404 · `ConflictError` 409 ·
  `ExternalServiceError` 502 (Docker, CV, external APIs) · `TrafficGenerationError` 500.
  Frontend: `extractErrorMessage()` from `frontend/src/utils/errorUtils.ts`.
- **Agent versioning rule:** any change under `docker/packetarch-agent/` or
  `backend/app/protocol_engines/` (staged into the agent image) **must** bump
  `docker/packetarch-agent/app/version.py` — MAJOR for agent/server protocol breaks, MINOR for
  features, PATCH for fixes.
- GPL-3.0 header on every new source file (`scripts/add_copyright_headers.py --check|--fix`).
  Owner strings live only in `backend/app/core/version.py`. A non-GPL-compatible dependency
  (proprietary/BSL; AGPL is fine) must be flagged before merge. Bump `ACK_VERSION` to
  re-prompt the first-run EULA.

## Architecture map

1. **Scenario Studio** (frontend): `@xyflow/react` canvas, `@dnd-kit`, Zustand stores.
   Canvas nodes: `DeviceNode`, `ZoneNode` (resizable), `FlowEdge` (protocol-colored).
2. **Traffic generation** (backend): protocol engines + identity + timing systems, Celery/Redis
   jobs, PCAP output. Every engine extends `ProtocolEngine` (`generate_startup_sequence` /
   `generate_poll_cycle` / `generate_shutdown_sequence`); stateful conversations use
   `python-statemachine`.
3. **Live traffic**: remote agents phone home over WebSocket (`/ws/agent`); Local Sensor
   Labs and Mimic run on-box through the privileged `host-agent`.
4. **AI / MCP**: in-app Claude/OpenAI calls (`ai_services/`), MCP server (`mcp_server/`).

| Subsystem | Code | Read when touching it |
|-----------|------|-----------------------|
| Protocol engines (canonical list: `ProtocolType` in `protocol_engines/protocols.py`) | `backend/app/protocol_engines/` | [docs/ADDING_NEW_PROTOCOLS.md](docs/ADDING_NEW_PROTOCOLS.md) |
| Rail engines (EMP/Class D, ATCS) + labeled-corpus export | `protocol_engines/emp/`, `protocol_engines/atcs/`, `label_sidecar.py` | [docs/rail-protocol-engines.md](docs/rail-protocol-engines.md), [docs/rail-protocols-dpi-parser-guide.md](docs/rail-protocols-dpi-parser-guide.md) |
| Device templates / fingerprints (per-vendor modules; `firmware_variants` drive firmware + CVE per instance) | `backend/app/services/device_templates/` | [docs/TEMPLATE_CREATION_GUIDE.md](docs/TEMPLATE_CREATION_GUIDE.md), [docs/fingerprinting-system.md](docs/fingerprinting-system.md) |
| Verticals + reference architecture (8 template modules; roles / archetypes / comm matrix) | `backend/app/scenario_templates/`, `services/architecture/` | [docs/ADDING_NEW_VERTICALS.md](docs/ADDING_NEW_VERTICALS.md), [docs/architecture/](docs/architecture/README.md) |
| Cyber Vision integration (match MAC 100% / IP 95%; classic v3 + new-UI `cvapi/v1`) | `api/routes/cyber_vision.py`, `services/cyber_vision_service.py`, `pages/CyberVisionPage.tsx` | — |
| Remote traffic agents (install, WS protocol, central updates) | `docker/packetarch-agent/`, `api/websocket/agent_hub.py`, `services/agent_manager.py` | [docs/remote-traffic-agent.md](docs/remote-traffic-agent.md) |
| Local Sensor Labs (on-box agent + CV docker sensor over a veth SPAN) | `services/local_sensor_service.py`, `docker/packetarch-host-agent/` | [docs/local-sensor-labs.md](docs/local-sensor-labs.md) |
| Mimic (device emulation: personas bind real sockets; on-box + CML slim) | `backend/app/mimic/`, `api/routes/mimic.py` | [docs/mimic.md](docs/mimic.md) |
| Attack playbooks + kill-chain timing | `protocol_engines/attacks/` | — |
| Portable scenario format (schema, spec, LLM prompt) | `schemas/packetarch-scenario.v1.json` | [docs/SCENARIO_SPEC.md](docs/SCENARIO_SPEC.md), [docs/LLM_PROMPT.md](docs/LLM_PROMPT.md) |
| Feature flags (`AI_ENABLED`, `LIVE_TRAFFIC_ENABLED`, `MULTI_SENSOR_TOPOLOGY_ENABLED`, `MIMIC_ENABLED`) | `core/config.py`, `core/features.py` | [docs/feature-flags.md](docs/feature-flags.md) |
| Release bundles, OVA, cert injection | `scripts/build-release.sh`, `scripts/release-bundle/`, `.github/workflows/release.yml` | [docs/release-bundles.md](docs/release-bundles.md) |
| REST API | `backend/app/api/` | [docs/API_REFERENCE.md](docs/API_REFERENCE.md) |

IP management: each scenario gets a unique `10.{n}.0.0/16`, `/24` subnets, gateway `.1`,
hosts from `.10`; auto-assigned, viewable at `/ip-management`.

**New feature flag:** add to `Settings` in `config.py` → `Features` in `features.py` →
`Features` in `frontend/src/api/about.ts` → a `RequireXEnabled` dep on the router (or
`useFeatures()` / `FeatureGate` in the UI). Ship dark (default off) unless told otherwise.

## Scenario realism requirements

Every automated scenario path (templates, AI generation, quick demo) must satisfy these five
dimensions. Readiness checks, AI review, and remediation actions enforce them.

1. **Device naming** — unique, industrial, human-readable, reflecting role/vendor/zone
   (`Assembly_Line_PLC_01`). `device_001` / `PLC-1` are flagged.
2. **Protocol accuracy** — only protocols the vendor fingerprint supports (a Siemens PLC gets
   S7comm/PROFINET, not EtherNet/IP). Repair is bidirectional: unsupported removed, supported
   added; flows unsupported by both endpoints are rejected.
3. **Completeness** — every device in at least one flow so CV can fingerprint it; SNMP
   monitoring fallback if no role-compatible partner; protocol identities (sysName,
   station_name…) populated.
4. **Inter/intra-cell** — cross-zone flows justified by IEC 62443 conduits; intra-zone free.
5. **Vendor-realistic MACs** — OUI must match the declared vendor via IEEE-verified prefixes
   in `vendor_oui.py`; MACs regenerate after fingerprint changes. For a *client-only* device
   the OUI is the only vendor evidence CV has.

Also: one canonical identity per device (one hostname + deterministic MAC across protocols),
and every role needs a unique `sys_object_id` + model, or CV merges look-alikes into one asset.

## In-app AI skill bundles (runtime prompts — not Claude Code skills)

`backend/app/ai_services/skills/<name>/SKILL.md` are prompt bundles the **product** sends on
its own AI calls (`SkillRegistry`, `skills/registry.py`; attached via
`provider.chat(..., skills=[...])`; Anthropic gets each as a cacheable system block, OpenAI
gets one inlined system message; missing skills log and skip). Six ship: scenario-authoring,
fingerprint-validator, ics-attack-playbooks, device-naming, scenario-review,
vuln-data-curation. Add one by creating the directory with `name` / `description` /
`version` frontmatter and wiring the call site. Listed at `GET /api/v1/ai/skills`.
This repo currently ships **no** Claude Code skills, hooks, or subagents; `.claude/` holds
only local settings.

## Behavior rules (project-specific standing orders)

1. **Fix as you find.** Bugs and inconsistencies get fixed on the spot when the risk is
   manageable; root cause over data patch. **Never invent data** — leave the field empty and
   say why. What can't be closed gets a shrink-only ratchet test.
2. **Deploy after every change** with the rebuild rule above, then verify live (logs, UI, and
   Cyber Vision when it's a fingerprint/traffic change). "It deploys" is not "the suite passes."
3. **PCAP must match live.** Whatever the agent emits for a scenario, the PCAP generator emits
   too. Extend both paths in lockstep.
4. **Check `services/` before declaring a capability missing.** PacketArch usually already wraps
   the external API you're about to probe (CV deployment tokens, sensor compose, org hierarchy).
5. **Pin what you validated.** A native/protocol lib is pinned to the line you tested
   (`>=3.8,<3.9`), and the resolved version in `poetry.lock` is checked after locking. Node
   bootstraps repeat the pin — they inherit no lockfile.
6. **Release gate:** green `master` CI, a single alembic head, `frontend/public/release-notes.html`
   updated in the same commit as the version bump, agent `version.py` collision checked, `.env`
   flag overrides reconciled with defaults. Releases are drafts; publish by hand.
7. **UI conventions:** Purdue layouts put Level 0 at the bottom, Level 4 at the top (reuse
   `PURDUE_Y_POSITIONS`); new persistent canvas UI goes inside the `CanvasControls` toolbar,
   not a floating panel.
8. **Lessons.** After any correction, append a dated entry ending in a **Rule:** line to
   [docs/gotchas.md](docs/gotchas.md); skim its index when entering a subsystem it covers.
   Plans for multi-step work live as `tasks/<topic>-plan.md` with checkboxes and a closing
   review section.
9. **Secrets and confidential material** never enter the public repo: `.env`, `uploads/`,
   `patent/`, `private/`, `CIRCUIT/` are ignored on purpose. Cisco-internal material stays out.
