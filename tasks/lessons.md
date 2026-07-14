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

## Poll-based vs event-based write-back differ across protocols (2026-07-13, Mimic OPC UA)

Adding OPC UA (asyncua) as the 2nd protocol: Modbus write-back fires on the
server's setValues EVENT (only when a client writes). OPC UA nodes are POLLED by a
sync loop, so applying the actuator node's value every cycle continuously forced
the model input to the resting-state mapping (pump-off → inflow 0), draining the
tank before any client touched it. Fix: apply write-back only on CHANGE (track
last-applied per node), which matches Modbus semantics — at rest the model keeps
its nominal input. **Rule:** when a projection is poll-based, gate write-back on
value change, not on every poll, or the resting node value overrides the model.

Also: asyncua 2.0 `set_build_info()` is a no-op — write the composite BuildInfo
node (ns=0;i=2260) directly after `start()` so clients/CV read the real manufacturer.

## process_sim set_value doesn't set the target — use set_target for inputs (2026-07-13)

Building the PI-controlled process models, my test wrote a new setpoint with
`ProcessVariable.set_value(70)` and the value snapped back to 50 next step. Reason:
`set_value` forces the current value but NOT the target, so a variable with
`time_constant_s=0` re-snaps to its (unchanged) target on the next `step()`. The
real write-back path (`NamedPointProjection.apply_write`) correctly uses
`set_target`. **Rule:** to inject an external input/setpoint into a running
process model, call `set_target(x)` (persists), not `set_value(x)` (transient
unless the caller also re-targets).

## Off-box Alpine persona deploy on CML: 3 gotchas (2026-07-14, Mimic slim)

Shipping the slim persona to a bare Alpine CML node surfaced three traps, each of
which produced a *silent* failure (node boots, hostname sets, but nothing listens):

1. **Backgrounded processes don't survive the sourced boot config, and
   `rc-service local start` is a no-op.** CML sources the node "configuration" as a
   shell at boot. A `cmd &` / `setsid` child dies with the shell. And by the time
   the config runs, Alpine's `local` service (which runs `/etc/local.d/*.start`)
   has ALREADY executed — so writing `mimic.start` + `rc-service local start`
   silently does nothing (service already "started"). **Fix:** launch the long
   setup script with `start-stop-daemon --start --background --exec /bin/sh -- setup.sh`
   — it double-forks and reparents to init, surviving the boot shell. The persona
   itself is launched the same way (with `--stdout/--stderr` to a log for diag).

2. **`pip install <pkg>` grabs the LATEST version — pin it, same as locally.** A
   fresh node has no lockfile; `pip install pymodbus` pulled 3.14.0, whose
   datastore/device API the slim runtime doesn't build against → ImportError, no
   bind. The local pin (`pymodbus>=3.8.0,<3.9.0`) MUST be repeated in the remote
   install command. **Rule:** any dep the code pins locally must be pinned in the
   node bootstrap too — the node doesn't inherit poetry/lock constraints.

3. **A stdlib `urllib` check-in against the self-signed backend fails verification.**
   `urllib.request.urlopen('https://<backend>/...')` raises CERTIFICATE_VERIFY_FAILED
   (backend cert is self-signed) and a bare `except` swallows it → persona runs but
   never reports. **Fix:** pass an unverified `ssl` context for liveness pings.
   (busybox `wget --no-check-certificate` from shell already handles this.)

**Diagnosis technique that worked:** CML's API console is READ-only (`console_logs`),
and a daemon's stderr goes nowhere. To see inside a headless node, have the bootstrap
script `wget` a check-in endpoint with progress markers (`&stage=net&ip=...`,
`&stage=pip&rc=...`, `&stage=final&pymodbus=$ver&listen502=$n&err=$logtail`). The
staged check-ins pinpointed the pymodbus-3.14 ImportError without any shell access.
Keep a *failure-only* variant in production (ping back only if the port didn't bind).

## Slim off-box protocol breadth: lazy imports + the c104/musl wall (2026-07-14)

Porting OPC UA / BACnet / IEC-104 into the slim (off-box Alpine) runtime surfaced
two things worth keeping:

1. **A multi-protocol runtime whose deps are installed PER NODE must import every
   protocol lib lazily.** Each slim node installs only its own protocol's pip dep
   (pymodbus OR asyncua OR bacpypes3 OR c104). `persona.py` had `from .modbus import
   ...` at module top — so an OPC UA node (no pymodbus) ImportError'd on load, before
   any dispatch, and reported a useless `err=/run.py`. Fix: import the server/
   projection INSIDE each protocol branch of `build()`. Verify with: import the
   entrypoint and assert none of the protocol libs landed in `sys.modules`.

2. **`c104` (IEC-104) has no musllinux wheel — it can't go on a slim Alpine node.**
   pymodbus/asyncua/bacpypes3 install from wheels (asyncua's `cryptography` has musl
   wheels); c104 is a pybind11/C++ extension that builds from source, and that build
   OOMs a 1-CPU/512 MB node (and takes many minutes even at 2 GB). So `netstat`-based
   liveness never fires. Options: bump the node (done — 2 GB/2 CPU for compile
   protocols) or, better, **serve a prebuilt musl c104 wheel** so the node just
   `pip install`s it. Rule: before committing to "install dep X on a slim musl node,"
   check it ships a `musllinux_*` wheel — a C extension without one silently turns a
   fast deploy into a multi-minute (or OOM-ing) source build.

Also: a UDP protocol's bind is invisible to `netstat -ltn` (TCP-only) — use
`netstat -ln` so BACnet (UDP/47808) doesn't false-alarm as bootstrap-failed. And a
BACnet Who-Is probe from the NAT'd backend container can't reach a lab-subnet node
(broadcast + return traffic don't survive NAT) — BACnet's real proof is CV on-segment.

## Off-box CV sensor on CML: capture NIC + vendor MAC (2026-07-14, Mimic capstone)

The full off-box proof — a slim persona cell whose OT segment is SPAN'd to a CV
docker sensor running on a CML Ubuntu node — worked end to end (CV classified the
PLC as Schneider Modicon M580 from the captured FC43). Two things that mattered:

1. **The SPAN-destination NIC has no DHCP, so netplan leaves it DOWN — bring it up
   or you capture nothing.** The sensor's capture interface (ens3) connects to the
   IOSvL2 monitor-session destination; it never gets an address, so cloud-init's
   default netplan never brings it up, and the macvlan-passthru capture sees zero
   frames. Fix in the sensor cloud-init: `ip link set ens3 up && ip link set ens3
   promisc on` BEFORE `docker compose up`. (The on-box Local Sensor Lab already
   brings its capture parent up in hostops; the CML node needs the same.) Symptom
   was: sensor ENROLLED+CONNECTED but no components appeared for the OT IPs. Once
   ens3 was up, components appeared in ~2 min.

2. **Off-box persona MACs are CML's (`52:54:00:*` = "Virtual Machine"), not vendor
   OUIs — a server persona still classifies via protocol identity, but a client-only
   one doesn't.** CV tagged the PLC (10.99.0.10) as Schneider M580 from its Modbus
   FC43 (FC43 overrides the local MAC — same as the on-box P1 finding), but the
   client-only HMI (10.99.0.20) has no protocol identity, so CV read its CML MAC as
   vendor "Virtual Machine" (it still correctly inferred "Engineering Station" from
   the polling behavior). FOLLOW-UP: the off-box deploy should set the persona's
   eth1 (data-seg) MAC to a vendor-aligned OUI at boot (`ip link set eth1 address
   <oui>` before bringing it up), mirroring `vendor_oui.pick_vendor_oui` on-box, so
   client-only personas classify by vendor too and the LOCAL_MAC tag clears.

Bonus: the CV docker-sensor auto-provisioning API (deployment token -> per-sensor
JWT via cyber_vision_service) works headless against a real Center — no operator
compose paste needed. The Center's registry (`{host}:443/sensor`) must be in the
node's daemon.json `insecure-registries` for the anonymous image pull.
