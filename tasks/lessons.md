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

## Pin native-protocol libs to the version you VALIDATED, not the range you typed (2026-07-13)

Adding `pymodbus = "^3.6.0"` for Mimic P0, I pip-installed 3.8.6 into the
container to introspect and validate the persona server. But `poetry lock`
resolved the caret range to **3.14.0** — and pymodbus 3.9+ made breaking datastore
changes (`ModbusSlaveContext`→`ModbusDeviceContext`, the custom-datablock
`getValues/setValues/validate` override pattern removed). The gate would have
passed in my probe env and then broken in the built image.

**Rule:** when you validate against a specific version of a native/protocol lib,
pin the constraint to THAT line (`>=3.8.0,<3.9.0`), and after `poetry lock` grep
the lock for the resolved version to confirm it matches what you tested. A caret
range on a fast-moving lib silently upgrades under you. Treat a major-version
migration as its own re-validated task, never an unpinned bump.

## A client-only persona's vendor is its MAC OUI — nothing else (2026-07-13, Mimic P1)

P1 stood up an HMI persona (Modbus client) polling a PLC persona (Modbus server).
CV classified the PLC as Schneider M580 (from FC43 device identification) but the
HMI as "Control Microsystems" — because a pure Modbus *client* exposes no protocol
identity, so CV falls back to the MAC OUI, and the OUI it drew (`00:03:74`) is
IEEE-registered to Control Microsystems (a Schneider sub), not "Schneider Electric".
The PLC drew the same OUI but FC43 overrode it.

**Rule:** for active-master / client-only personas, OUI-vendor alignment (realism
dimension #5) is the ONLY lever — there's no protocol identity to override a wrong
OUI. A persona template's `oui_prefixes[0]` must map to the INTENDED vendor label in
IEEE/CV's OUI DB, or client-only devices will surface the wrong manufacturer.
Server personas are forgiving here (FC43/CIP/SZL identity wins); clients are not.

**Fix shipped:** `vendor_oui.pick_vendor_oui(vendor, oui_prefixes)` returns the first
prefix whose IEEE registrant matches the vendor; Mimic deploy pins each persona MAC to
it. HMI now reads "Schneider Electric" in CV.

**Data-version gotcha:** the bundled `ieee_oui.csv` and a given CV Center's OUI DB can
DISAGREE for reassigned prefixes — `00:03:74` is "Schneider Electric" in our bundle but
"Control Microsystems" (the pre-acquisition registrant) in this CV. So don't trust any
registry-matched prefix blindly; prefer the vendor's canonical PRIMARY OUI (templates
list it first — here `00:00:54`), which is stable across data versions.
