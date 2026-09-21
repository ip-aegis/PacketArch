# Corporate-Host Install Hardening — Implementation Plan

**Origin (2026-09-21):** First outside installer (David G., Cisco-managed Ubuntu VM on a laptop,
Cisco VPN up) spent 2026-09-04 → 09-18 getting v1.18.2 → v1.20.1 running via the git path. Every
problem he hit was a product gap, not user error. Rocky's Cerebro agent reviewed the thread and
this tree (cf4841b) and wrote this plan. Check in with Rocky before building (CLAUDE.md rule).

**Goal:** A fresh git install on a VPN'd corporate laptop either works first time or tells the
installer exactly what is wrong in one command.

## What actually happened (evidence, in order)
1. Image builds failed inside RUN steps (no DNS/egress from the build network). Fixed in v1.20.1
   by `DOCKER_BUILD_NETWORK=host` + `scripts/check-docker-egress.sh`. ✔ shipped.
2. Postgres password mismatch after `.env` regen against an existing volume. Fixed in v1.20.2
   (entrypoint banner + `fix-db-password.sh`). ✔ shipped.
3. Rocky's log-dump one-liner assumed `/opt/packetarch` + `/var/log/packetarch-firstboot.log`
   (OVA/bundle paths); his install was `~/packetarch` (README/DEPLOY git path). Nothing in /var/log.
   → No diagnostics script exists (grep `diagnos|collect` hits only prose in DEPLOY.md:206,
   server-init.sh:171).
4. `docker compose up -d --build` printed no access URLs; the PDF says it does
   (`scripts/build_install_guide_pdf.py:356`). Only `server-init.sh:242-243`,
   `release-bundle/install.sh:186,198`, `ova/firstboot.sh:165-171` print them.
5. frontend + host-agent show blank health (no healthcheck defined: compose 181-196, 220-246).
   He read blank as "never became healthy".
6. Host→port 80/443 TCP reset while `curl` inside the frontend container returned 200. Root cause:
   Docker default pool 172.18.0.0/16 (compose has NO `networks:` block) overlapped the VPN's
   172.16.0.0/12 route, AND embedded DNS 127.0.0.11 stopped reverse-NATing replies on that host.
   He hacked `extra_hosts` for postgres/redis onto backend + celery_worker and rebooted.
   `check-docker-egress.sh:78-123` catches the route overlap; §3 (126-149) tests external DNS on the
   default bridge only — service-name resolution inside the compose network is untested.
7. Current state: page loads, **login instead of wizard, every login = "Server error"**, ~30 s spin.
   Diagnosis: nginx resolves `backend` via `resolver 127.0.0.11` (`frontend/nginx.conf:35-36`); his
   hack never touched frontend → every `/api/` call 502s after the resolver timeout;
   `errorUtils.ts:151-152` renders any 5xx as "Server error"; the setup gate **fails open**
   (`setupStatusStore.ts:30-38` swallows the error, `useSetupStatus.ts:19` treats null as
   complete) → LoginPage. His SQL wizard reset was correct (tables/keys verified:
   `models/user.py:19`, `models/settings.py:19,73`).

## Tasks (priority order; each is one commit + one CHANGELOG line)

### 1. Pin the compose network subnet  — the fix that removes the whole class
- [x] Add to `docker-compose.yml`:
  ```yaml
  networks:
    default:
      ipam:
        config:
          - subnet: ${COMPOSE_SUBNET:-10.200.0.0/24}
  ```
  Pick a default outside 172.16/12, 10.0/8-common-VPN ranges are also risky; document the choice.
  `host-agent` is `network_mode: host` — unaffected, leave it.
- [x] Add `COMPOSE_SUBNET` to `.env.example`, `server-init.sh` env generation, `release-bundle`
  templates, and DEPLOY.md §networking (next to `DOCKER_BUILD_NETWORK`, :226-233).
- [x] `check-docker-egress.sh`: when a site route overlaps, ALSO print "set COMPOSE_SUBNET=… in .env"
  as the compose-level fix (daemon.json `default-address-pools` stays the host-level fix).
- [x] Upgrade path: changing the subnet on an existing install needs `docker compose down` (network
  recreate). `scripts/upgrade.sh` must detect a changed `COMPOSE_SUBNET` and do down/up, not just
  `up -d`. Test: install on 172.18 default, set COMPOSE_SUBNET, run upgrade, confirm
  `docker network inspect` shows the new subnet and all containers healthy.
- Acceptance: fresh install with a fake `172.16.0.0/12 dev dummy0` route on the host works with no
  hacks; `docker network inspect packetarch_default` shows the pinned subnet.

### 2. Test embedded DNS in check-docker-egress.sh
- [x] New §4: `docker compose run --rm --no-deps backend nslookup postgres` (or `getent hosts`)
  inside the compose network; on failure print the 127.0.0.11 / conntrack explanation and the
  `COMPOSE_SUBNET` + `daemon.json` fixes. Must run with the stack down too (use a throwaway
  network: `docker network create` + `docker run --network` + busybox nslookup of a second
  container by name).
- Acceptance: on a normal host prints PASS; with embedded DNS deliberately broken
  (`--dns-opt` trick or iptables drop of 127.0.0.11) prints the named cause.

### 3. `scripts/collect-diagnostics.sh`
- [x] Locate the compose dir from the script's own path (copy the pattern in
  `fix-db-password.sh:25-30`); never assume `/opt/packetarch` or `~/packetarch`.
- [x] Dump, in labelled sections, to `./packetarch-diag-<date>.txt`: `git describe`, `.env` KEYS
  only (values redacted), `docker compose ps -a`, `docker compose logs --tail 300` per service,
  `docker network inspect` of the compose network, `ip route`, `ip rule`, `ss -lntp` for 80/443,
  `iptables -t nat -S DOCKER*` (if root), host→`https://localhost/health` code, in-container
  `frontend → http://backend:8001/health`, in-container `nslookup backend` from backend, and the
  OVA firstboot log/sentinel ONLY if they exist.
- [x] Mention it in DEPLOY.md troubleshooting, README, the PDF builder, and the entrypoint banners
  ("run scripts/collect-diagnostics.sh and send the file").
- Acceptance: run from `~/packetarch`, `/opt/packetarch`, and a random cwd; one file, no secrets.

### 4. Healthchecks for frontend and host-agent
- [x] frontend: `curl -fsk https://localhost/health` (proves nginx AND the upstream resolve), interval
  15s, start_period 30s.
- [x] host-agent: whatever its liveness signal is (grep its entrypoint for a port/ready file); if none
  exists, add a minimal one rather than leave it blank.
- [x] Update DEPLOY.md:247-262 ("frontend stays Created") for the new states.
- Acceptance: `docker compose ps` shows a status for every service; break backend DNS and confirm
  frontend flips to unhealthy within one interval. Remember `tasks/lessons.md`: a green check is a
  claim — the check must exercise the path users hit.

### 5. Setup gate: fail open loudly
- [x] Keep the fail-open (don't brick existing installs) but set a store flag `statusUnavailable`
  when `/setup/status` errors; render a persistent banner on LoginPage/SetupGate: "Backend
  unreachable (HTTP <code>). Showing login as a fallback — run scripts/collect-diagnostics.sh."
- [x] `errorUtils.ts:151`: for 502/503/504 say "Backend unreachable" instead of "Server error".
- Acceptance: stop backend, reload UI → banner visible, message names the real problem.

### 6. Docs corrections (small, do together)
- [x] `build_install_guide_pdf.py:356`: `up -d --build` does NOT print URLs — either route the git
  path through `server-init.sh` or replace with the DEPLOY.md:301-306 URL table.
- [x] README.md:43 OVA guard says `!/opt/packetarch/.env`; the service file uses
  `.firstboot-done`. Fix README.
- [x] Add one "Which install path am I on?" table: git (`~/packetarch`), bundle (`/opt/packetarch`),
  OVA (`/opt/packetarch` + firstboot log) — so support one-liners stop guessing.
- [x] "Method 4" in the guide referenced a `*.yml` that isn't in the clone (David, 2026-09-14) —
  find and fix or drop the method.
- [x] Regenerate the PDF; `scripts/upgrade.sh` docs: state plainly that `extra_hosts` edits are
  unsupported and will block/stash on upgrade (119-149).

## Not in scope
- ARM/Apple-silicon images (John M. asked; Rocky: not scoped). Note only.
- Anything in PacketArch-Core. This is 1.x maintenance for the CV demo workload.

## Verification before "done"
- Full run of `scripts/check-docker-egress.sh` + `collect-diagnostics.sh` on this VM (.231) and on a
  throwaway VM with a fake 172.16/12 route + pinned subnet. Paste outputs into the review section.
- `docker compose config` validates; CI green; CHANGELOG + version bump (v1.21.0 — task 1 changes
  network layout, so minor not patch).
- Then Rocky sends David: (a) proof commands, (b) `COMPOSE_SUBNET` instead of his extra_hosts
  hack, (c) `upgrade.sh` to v1.21.0.

## Review section (fill in as you go)

**Shipped as v1.21.0** (7 commits, `12e9b54..d8f09de`). Deployed to this box and
running; 1255 backend tests pass, `tsc --noEmit` and eslint clean,
`docker compose config` validates, `check_install_guide_version.py` passes.

| Task | Commit | Notes |
|------|--------|-------|
| 1. Pin the compose subnet | `12e9b54` | + the `compose run` hazard, found while building it |
| 2. Embedded-DNS check | `f78f08f` | probe rewritten after the first version silently passed |
| 3. `collect-diagnostics.sh` | `2a9996e` | ships in the offline bundle too |
| 4. frontend + host-agent healthchecks | `da7bee3` | host-agent needed a liveness signal written first |
| 5. Setup gate fails open loudly | `b2b66e4` | + the real "Server error" string replaced |
| 6. Docs corrections | `2d589a1` | + a troubleshooting chapter the guide never had |
| Release | `9124c77` | version, notes, 15-page guide |
| **Deploy finding** | `d8f09de` | see "What the deploy found" below |

### What the deploy found — the one thing the plan got wrong

`docker compose up -d --build` on this box recreated `packetarch_default` on
10.200.0.0/24 exactly as designed, and the backend then crashlooped on
"waiting for database". Every signal said the deploy had worked: right subnet,
all containers attached, all running, `postgres` **healthy**.

`postgres` and `redis` were the two services Compose did not have to rebuild,
so it **reattached** them to the new network *without their compose
service-name aliases*:

```
postgres aliases: []
redis    aliases: []
$ docker compose exec backend getent hosts postgres   ->  exit 2
```

Reproduced in isolation to confirm the mechanism rather than the symptom —
change only the subnet, bare `up -d`, both containers come back running with
`aliases=[]` and no resolution; `down && up -d` restores them. This is the same
end state as the VPN subnet collision (a service unreachable by name) arriving
through a different door, and it would have hit the first site that followed a
`COMPOSE_SUBNET` change with the wrong command.

Fixed in `d8f09de`: DEPLOY.md carries it as a measured warning, the preflight
says the `down` is not optional wherever it prints the fix, and
`collect-diagnostics.sh` prints each container's alias list and flags an empty
one (skipping `network_mode: host`, which legitimately has none). Nothing in
`docker compose ps` or `docker network inspect` surfaces this, which is why it
had to be added by hand. Lesson recorded in `tasks/lessons.md`: I had already
proved Compose auto-recreates a changed network inside `up -d` and wrongly
concluded the explicit `down` was belt-and-braces — I had tested that the
network ends up correct, not that the containers still work on it.

### Proof — final state of this VM (.231)

```
$ ./scripts/check-docker-egress.sh
  ok    Docker version 29.6.0, build 1.fc43
  ok    docker0 1500 <= enp1s0 1500
  ok    no site route overlaps docker's pools, the local-lab block, or 10.200.0.0/24
  ok    DNS resolves inside a bridged container
  ok    TCP+TLS out of a bridged container
  ok    a build step can reach the network — compose builds will work
  ok    "backend" resolves inside packetarch_default -> 10.200.0.5 (embedded DNS working)
No egress problems found.                                              (exit 0)

$ docker compose ps
backend        Up (healthy)      celery_worker  Up (healthy)
frontend       Up (healthy)      host-agent     Up (healthy)
postgres       Up (healthy)      redis          Up (healthy)
                        ^ all six report a state; frontend and host-agent were blank before

$ docker network inspect packetarch_default --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
10.200.0.0/24

$ docker compose exec host-agent cat /hostagent/local-labs/heartbeat.json
{"pid": 2502305, "ts": "2026-09-21T13:29:44...", "loop_ts": 1789997383.6, "loop_age_s": 1.3}

$ curl -sk -o /dev/null -w '%{http_code}' https://localhost/health
200

$ ./scripts/collect-diagnostics.sh
Wrote ./packetarch-diag-<utc>.txt  (1043 lines; declared subnet == live subnet;
                                    no secret value from .env present)
```

The 8 local sensor labs were unaffected: their agents are `network_mode: host`
and reach the backend at `https://127.0.0.1`, i.e. the host's published 443, so
the stack's subnet is irrelevant to them. Checked before bouncing anything, not
after.

### Acceptance criteria, item by item

| Criterion | Result |
|---|---|
| 1. Fresh install with a fake `172.16.0.0/12` route works with no hacks | **Partly.** The route shape was reproduced in a netns and the preflight names it, correctly reporting that the default `COMPOSE_SUBNET` is *not* among the hits (so the pin is the escape). A full install under that route was **not** run — see gaps. |
| 1. `docker network inspect` shows the pinned subnet | ✅ `10.200.0.0/24` |
| 1. Upgrade detects a changed `COMPOSE_SUBNET` and does down/up | **Code complete, not run end-to-end** — needs a `v1.21.0` tag to exist. Helpers unit-tested against the live install: declared `10.200.0.0/24` vs live `172.18.0.0/16` detected, foreign-endpoint detection discriminates correctly by project label. |
| 2. Preflight PASSes on a normal host | ✅ resolves `backend` -> `10.200.0.5` over the real stack network |
| 2. …and names the cause when DNS is broken | ✅ fires with the conntrack diagnosis, the `COMPOSE_SUBNET` fix and an explicit "do not reach for extra_hosts" |
| 3. Runs from `~/packetarch`, `/opt/packetarch`, a random cwd | ✅ repo root, unrelated cwd, and a bundle-shaped dir with the script flat beside `docker-compose.yml` |
| 3. One file, no secrets | ✅ one file. Redaction tested **positively** against a synthetic `.env` (a password inside a DSN, a JWT key in a traceback, a Fernet key full of regex metacharacters) — on this install nothing matched, which proves only that nothing leaked, not that the redaction works |
| 4. Every service shows a status | ✅ all six |
| 4. Break the backend path, frontend flips unhealthy in one interval | ✅ **46s** (15s interval x 3 retries). `docker compose stop backend`, probe exit 22 = HTTP error, nginx returning 502 — the same probe path a DNS failure exercises. Recovered in 15s on restart with no frontend restart needed |
| 5. Stop backend, reload UI -> banner naming the real problem | **Verified without a browser.** With the backend stopped, `/api/v1/setup/status` returns **502** through nginx, which is what sets `statusUnavailable` + code 502; the built bundle contains "Backend unreachable" and "collect-diagnostics.sh". Not clicked through in a browser. |
| 6. Docs corrected, PDF regenerated | ✅ guide 12 -> 15 pages; text extraction confirms every new section rendered rather than trusting exit 0 |

### Not verified — gaps, with reasons

1. **A fresh install on a real VPN'd host / throwaway VM with a
   `172.16.0.0/12` route.** The netns test proves the *detector* fires on that
   route shape; it does not prove an install *succeeds* under it. Adding such a
   route to this box was not an option — the 8 local sensor labs live in
   172.16.x and it would have broken them. This is the one remaining thing a
   throwaway VM on Alpha would settle.
2. **`upgrade.sh` end-to-end across the subnet change.** Blocked by ordering,
   not skipped: it upgrades *to a tag*, and `v1.21.0` is not tagged yet. Worth
   running deliberately on the first upgrade, because the forward path now does
   an explicit `down` and the rollback path handles pinned -> unpinned.
3. **The banner in a browser.** The state that triggers it is confirmed and the
   string is in the shipped bundle; the rendering is not eyeballed.
4. **Offline-bundle install with the new `COMPOSE_SUBNET` selection.**
   `build-release.sh` and `install.sh` changes are syntax-checked and the
   subnet-selection loop was exercised directly (it picks `10.200.0.0/24` here,
   and correctly skips a candidate the host already routes), but no bundle was
   built and installed.

### Still to do

- `git push origin master` — **not pushed**, holding for Rocky.
- Tag `v1.21.0` once pushed (triggers the offline-bundle CI build).
- Then send David: the proof commands above, `COMPOSE_SUBNET` in `.env` in place
  of his `extra_hosts` hack — with the note that `extra_hosts` could never have
  fixed the frontend anyway, since nginx resolves through `127.0.0.11` rather
  than `/etc/hosts` — and `./scripts/upgrade.sh --to v1.21.0`. Tell him to run
  `down && up -d`, not `up -d`, when the subnet changes.

