# T0 — Pre-exposure hardening PR

Goal: get PacketArch into a state where it's safe to expose port 443 to the public internet. Driven by the four-agent audit summarized in the chat transcript and the user's report that "session timeout is broken" (overnight bypass).

Scope is deliberately limited to **T0 blockers** from the audit. T1 hardening (rate limiting, CSP, real TLS cert, ACME) is a follow-up.

## Backend route authorization (the big risk)

- [x] `backend/app/api/routes/agents.py` — router-level admin gate (`dependencies=[AdminUser]`). The 22 routes currently hand out agent WebSocket tokens to anonymous callers; admin-only closes that.
- [x] `backend/app/api/routes/auth.py` — `POST /auth/register` becomes admin-only. First-user-becomes-admin logic stays as a no-op (after setup, an admin already exists; before setup, this route is 503 by `RequireSetupComplete`).
- [x] `backend/app/main.py` — add `Depends(get_current_user)` to `dashboard`, `architecture`, `health_monitor` routers.
- [x] `backend/app/static/agent/install.sh` — `--register` mode no longer works against a gated server; update help text + early-fail message to point operators at the UI.

## Session-timeout fix (user's reported overnight-bypass bug)

- [x] `backend/app/core/config.py` — shorten defaults: access 120m → 30m, refresh 7d → 1d.
- [x] `backend/app/core/security.py` — `create_refresh_token` now accepts `original_exp` so the absolute window doesn't slide; `decode_token` hardcodes `algorithms=["HS256"]` defensively.
- [x] `backend/app/api/routes/auth.py:refresh_token` — preserve original `exp` instead of resetting the 7-day clock every call.
- [x] `frontend/src/stores/authStore.ts` — stop persisting `isAuthenticated`; the user object alone hydrates UI, server round-trip decides whether the session is live.
- [x] `frontend/src/components/ProtectedRoute.tsx` — block render until `fetchCurrentUser` completes (don't trust persisted state for the gate).
- [x] `frontend/src/hooks/useIdleLogout.ts` — new hook: mouse/keyboard/visibility idle → logout after 30 min.
- [x] `frontend/src/components/layout/AppLayout.tsx` — wire `useIdleLogout`.

## API surface reduction

- [x] `backend/app/main.py` — `docs_url` / `redoc_url` / `openapi_url` set to `None` unless `settings.debug` is true.
- [x] `frontend/nginx.conf` — remove the `/api/docs` and `/api/openapi.json` location blocks.

## Critical dep bumps (reachable by unauth traffic on 443)

- [x] `backend/pyproject.toml` — `cryptography ^46`, `python-multipart ^0.0.27`, `fastapi` to a version that drags `starlette ≥0.47`.
- [x] `frontend/package.json` — `axios ^1.15.2`.

## Version + deploy

- [x] Bump `app_version` in `backend/app/core/config.py` to `1.4.0`.
- [x] `docker compose up -d --build` (per `feedback_always_deploy.md`).

## Out of scope for this PR (tracked for T1)

- nginx rate limiting (`limit_req_zone`) on `/auth`, `/setup`, `/ws`
- CSP / Referrer-Policy / Permissions-Policy / OCSP stapling
- Real TLS cert (Let's Encrypt or commercial) at `./certs/`
- WS token via `Sec-WebSocket-Protocol` instead of query string
- Password complexity policy bump
- SSRF guard on CV / CML test-connection endpoints
- `tokens_invalid_before` per-user revocation timestamp
- Move tokens from `localStorage` to `HttpOnly` cookie
- Postgres/Redis host-port verification with firewalld

## Review notes

Build + deploy outcome: backend, frontend, and celery_worker rebuilt and
came up healthy in `docker compose up -d --build`. No deprecation
warnings in backend startup logs despite the fastapi 0.109→0.118 and
cryptography 41→46 jumps. Live verification against `https://localhost`:

- `/api/docs` → 404 (was 200, full OpenAPI spec)
- `/api/openapi.json` → 404
- `/api/v1/agents` (any verb) → 403 (was 200; POST returned a usable agent token)
- `/api/v1/auth/register` → 403 (was 201)
- `/api/v1/dashboard/live` → 403 (was 200, fleet inventory)
- `/api/v1/architecture/verticals` → 403 (was 200)
- `/api/v1/health-monitor/status` → 403 (was 200)
- `/api/v1/about` → 200 (intentionally unauth — login page footer)
- Login as `admin` → access token expires in 1799s (~30 min ✓, was 120 min)
- Login → refresh token expires in ~23 hr (was 7 days)
- `/auth/refresh` → **new refresh token's `exp` exactly matches the
  inbound token's `exp`** — non-sliding absolute window confirmed. This
  is the structural fix for the overnight-bypass.
- Admin Bearer token still hits `/api/v1/agents` (200 with agent list) so
  the legitimate operator flow works.

What this PR does NOT do (deliberately, tracked in "out of scope" above):
nginx rate limiting, CSP, real TLS cert, SSRF guard on CV/CML, token
revocation table, HttpOnly-cookie refresh, password complexity. Those
are T1 and meaningful but not blockers for first-time exposure.

Things to know before opening 443:
1. **Complete the setup wizard before opening the firewall** (race window
   only matters on fresh installs; this one is already past the wizard).
2. Postgres + Redis verified bound to `127.0.0.1` in `docker-compose.yml`
   — no host-firewall action needed for those specific ports.
3. The self-signed cert is still in place — every public visitor will
   see a browser warning. Drop a real cert at `./certs/server.{crt,key}`
   before announcing the URL.
4. The agent install script (`/agent/install.sh`) is still served
   unauthenticated. It is harmless as a script (no secrets baked in),
   but `--register` now requires an `--admin-token`; users who relied on
   anonymous registration need to either create the agent in the UI
   first or grab an admin bearer token. Help text updated.
