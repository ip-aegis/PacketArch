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
