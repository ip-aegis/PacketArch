# Lessons

## 2026-07-11 — Check the app's own services before declaring a capability missing
While scoping the multi-sensor topology feature I probed the CV Center's raw
APIs (v3 + cvapi/v1), found no sensor-provisioning endpoint, and wrote "docker
sensor composes must be operator-pasted, N+1 manual steps" into the design.
Wrong: `local_sensor_service.build_lab()` had already solved this in v1.15.0 —
it creates a reusable CV *deployment token* via `create_deployment_token()`,
mints per-sensor JWTs, and synthesizes the compose (its module docstring says
exactly this). Rocky had to correct me.

**Rule:** before concluding "X isn't possible" or designing an operator burden
around a missing capability, grep this repo's `services/` for the capability
first — PacketArch frequently wraps external APIs with exactly the automation
the design needs. Raw-API probing tells you what the vendor exposes, not what
the app has already built on top of it.

## 2026-07-13: CI was red for 4 days and nobody noticed (pytest -x masks failures)

Shipped v1.18.0/v1.18.1 while master CI had been failing since Jul 9. Two
compounding blind spots: (1) I pushed 7 commits without ever checking the CI
result — local "it deploys and works" is not "the suite passes"; (2) CI runs
`pytest -x`, so its log showed only ONE failure while five more (plus a
coverage crater) hid behind it — the visible failure was never the whole story.

**Rule:** after every push, check `gh run list --branch master --limit 1`
before declaring done — and when a run is red, reproduce with the FULL suite
(no `-x`) locally to enumerate every failure before fixing any of them. When
cutting a release, a green master CI is a pre-tag gate, same as alembic heads.

**Rule:** a feature flag that's enabled via the dev box's uncommitted `.env`
will silently ship default-off to every other install. Before tagging a
release whose headline is flag-gated, grep `.env` for overrides and confirm
the config.py default matches what the release notes promise.
