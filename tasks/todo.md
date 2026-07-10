# Scenario Verify audit + rework (2026-07-09)

Goal: every live scenario's Studio-v2 **Verify** panel shows **zero critical +
zero warning** across all 4 sources (readiness, conduit, architecture, AI
review). Rework rationally — never tear down. Persist to DB **and** backport to
templates.

## Phase 0 — Orient (DONE)
- [x] Mapped the 4 Verify sources; built a faithful backend verify harness
      (`scratchpad/verify.py`, `--ai` for the live LLM review).
- [x] Baseline: 1 scenario clean, 10 warnings, 1 critical (Solar orphans).
- [x] Found the dominant issue is the comm-matrix (architecture source).

## Phase 1 — Comm matrix completion (DONE, shared code)
- [x] Added the missing control rail to `comm_matrix/shared.py`. Cleared ~92%
      of architecture off-rail across all scenarios.

## Phase 2 — AI-review context bug (DONE, shared code)
- [x] Fixed vendor-name mismatch in `_build_review_context` that made the LLM
      emit a false "catalog gap" CRITICAL on every scenario.

## Phase 3 — Per-scenario DB rework (DONE)
- [x] All 12 live scenarios reworked to deterministic-clean (readiness 100/ready,
      conduit 0, architecture 0). Sub-agents + coordinator (Municipal, Commercial,
      EU-tenant, Urban done directly after agent API stalls).
- [x] Review skill tuned (telnet/http/CVE = observations; false-positive guardrails).
- [x] Catalog thin-fingerprint fixes: Honeywell Experion opc_ua, Schneider T300 iec104.
- [x] Added `nms`/`nms_server` to flow-rationality generic-OK source types.

## Phase 4 — Template backport (DONE)
- [x] All 12 templates edited so FRESH instantiation is deterministic-clean
      (verified via build_verify against fully-baked code): manufacturing×3,
      building×3, water, energy, oil_gas, transportation, distribution.

## Phase 5 — Finalize (DONE / in progress)
- [x] Rebuilt backend + celery_worker (all changes live). No protocol_engines/
      change → no agent version bump needed.
- [x] Re-verified all 12 live scenarios + all 12 fresh instantiations: 100/0/0.
- [ ] Final AI sweep on 12 live scenarios (running). Not committed (dev=prod via
      rebuild; commit only on request).

## Notes
- Backups: container `/tmp/scn_backup`, host `scratchpad/scn_backup.tgz`.
- Tooling: `scratchpad/{verify.py,fixlib.py,AGENT_PLAYBOOK.md}`.
