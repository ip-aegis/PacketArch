# PacketArch Deployment Guide

PacketArch deploys as a Docker Compose stack that **builds from source** — the
only host requirement is Docker Engine + the compose plugin. The frontend
serves the whole platform over **HTTPS on port 443** (nginx, self-signed cert
by default); the backend is reached only through that nginx proxy.

- **Repository:** https://github.com/ip-aegis/PacketArch (public)
- **Default branch:** `master`

---

## Fresh Server Setup (clean Ubuntu)

```bash
# 1. Install Docker Engine + compose plugin
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
# Log out and back in (or open a new SSH session) so the docker group applies.
# `newgrp docker` also works, but it starts a subshell — don't paste it as part
# of a larger block, or everything after it runs inside that subshell.

# 2. Clone (public repo, HTTPS — no SSH key needed)
git clone https://github.com/ip-aegis/PacketArch.git ~/packetarch
cd ~/packetarch

# 3. Create .env with fresh secrets
cat > .env <<EOF
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
DOCKER_GID=$(getent group docker | cut -d: -f3)
HOST_INSTALL_DIR=$(pwd)
COMPOSE_PROJECT_NAME=packetarch
COMPOSE_SUBNET=10.200.0.0/24
DEBUG=false
# ADMIN_PASSWORD intentionally omitted => first boot shows the setup wizard.
# Add ADMIN_PASSWORD=<value> only for a headless install (skips the wizard).
EOF
chmod 600 .env

# 4. Build and start
docker compose up -d --build
```

Or run the one-shot helper (does all of the above — installs Docker, clones to
`~/packetarch`, generates `.env`, builds and starts):

```bash
# Straight from GitHub, no clone needed first:
curl -sSL https://raw.githubusercontent.com/ip-aegis/PacketArch/master/scripts/server-init.sh | bash

# Or from an existing clone:
bash scripts/server-init.sh      # defaults to ip-aegis/PacketArch @ master
```

Then open `https://<server-ip>/` and complete the first-run **setup wizard** —
create the admin and name the site. (Set `ADMIN_PASSWORD` in `.env` only for a
headless install: it auto-creates the `admin` user and skips the wizard.)

### Required / recommended `.env` values

| Var | Required | Notes |
|-----|----------|-------|
| `POSTGRES_PASSWORD` | ✅ | Compose refuses to start without it |
| `SECRET_KEY` | ✅ | `openssl rand -hex 32` |
| `ADMIN_PASSWORD` | optional | **Unset = setup wizard (recommended).** Set = auto-create `admin` with this password and skip the wizard (headless installs). |
| `ENCRYPTION_KEY` | optional | If unset, it's derived deterministically from `SECRET_KEY` and is stable across reboots. Set an explicit Fernet key only to rotate it independently of `SECRET_KEY`. |
| `DOCKER_GID` | recommended | Must match the host docker group (`getent group docker \| cut -d: -f3`) or the backend can't reach the Docker socket to spawn traffic containers. Varies by distro (988 on Ubuntu 24.04); falls back to 987 if unset. |
| `DEBUG` | optional | `false` in production |
| `COMPOSE_SUBNET` | recommended | Subnet for the stack's own bridge network. **Pinned** by default (`10.200.0.0/24`) instead of taken from Docker's pools, because a VPN/site route that overlaps those pools makes the stack come up and still be unreachable. Change it only if your site routes that /24 — and see "When the host's network overlaps Docker's" below, a change needs the network recreated. |
| `DOCKER_BUILD_NETWORK` | optional | Leave unset on a healthy host. `host` makes every image build (including the socket-built agent and updater images) use the host network stack — a stopgap for a host whose bridged build sandbox has no egress. See "When the build can't reach the network". |

---

## Off-Box HTTPS Access

The stack is built for off-box access out of the box: nginx listens on 443
with `server_name _` (any IP/hostname), redirects port 80 → 443, and the
frontend talks to the API same-origin through the proxy (no CORS config
needed).

**What you must do:** allow inbound **443** (and **80** for the redirect) at
your network boundary — cloud security group (AWS/GCP/Azure) or hardware
firewall.

> ⚠️ Docker publishes ports via iptables and **bypasses `ufw`**. Two
> consequences: (1) 443 is reachable from off-box even under `ufw` default-deny,
> so the cloud/network firewall is the real gate; (2) `ufw deny` will **not**
> protect other ports. This compose already binds Postgres (5432), Redis
> (6379), and pgAdmin (5050) to `127.0.0.1`, so they are not internet-exposed —
> reach them via SSH tunnel if needed (`ssh -L 5432:localhost:5432 <server>`).

### TLS certificate

- **Self-signed (default):** auto-generated on first boot. Works immediately;
  browsers show a trust warning. Fine for a lab.
- **Real cert (no warning):** drop `server.crt` + `server.key` into `./certs/`
  on the server and `docker compose restart frontend`. The frontend entrypoint
  copies them in on every boot. Use Let's Encrypt for a public DNS name or your
  internal CA for an internal hostname.

---

## GitHub Actions

Two workflows are committed:

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `ci.yml` | push / PR | Backend + frontend lint and tests |
| `release.yml` | tag `v*` | Builds the self-contained offline bundles (full and PCAP-only variants) and attaches them to a **draft** GitHub Release |

> Releases are created as **drafts** — publish the draft manually for it to
> become visible (and to become "Latest") to anyone outside the repo.

There is no automated SSH deploy workflow; production boxes pull and rebuild
themselves via `scripts/upgrade.sh` or the **Settings → Updates** UI button.

---

## Day-2 Operations

```bash
docker compose ps                  # status
docker compose logs -f backend     # logs
docker compose up -d --build       # redeploy after a git pull
docker compose restart             # restart all
docker compose down                # stop (keeps volumes/data)
```

### Upgrading (release-tracked)

Labs track tagged **releases** (`vX.Y.Z`), not bleeding-edge `master`. Cut a
release from the dev box with `git tag vX.Y.Z && git push origin vX.Y.Z` (this
also triggers the offline-bundle build in `release.yml`). On each lab box:

```bash
cd ~/packetarch
./scripts/upgrade.sh --check     # what's installed vs latest release
./scripts/upgrade.sh             # upgrade to the latest release tag
./scripts/upgrade.sh --to v1.2.0 # pin a specific version
```

`upgrade.sh` backs up first, checks out the target tag, rebuilds, runs
`alembic upgrade head`, verifies backend health, and **auto-rolls back code +
database** if the new stack doesn't come up healthy. The pre-upgrade backup is
kept under `./backups/`.

**One-button upgrade (UI):** admins can also upgrade from **Settings →
Updates** — it shows the installed vs latest release and runs the same
`upgrade.sh` inside a detached updater container (so the backend can restart
itself), streaming progress that survives the restart. Requires
`HOST_INSTALL_DIR` + `COMPOSE_PROJECT_NAME` in `.env` (the runbook above and
`server-init.sh` set these). Boot-time migrations: the backend entrypoint runs
`alembic upgrade head` on every start (gated by `RUN_MIGRATIONS=true`), so a
schema delta lands even on a plain `docker compose up`.

> Note: the app currently builds tables via `create_all` on boot *and* ships
> alembic migrations. `upgrade.sh` bootstraps alembic tracking (stamps the
> current head) on first run so schema migrations apply correctly. The clean
> long-term fix is to run `alembic upgrade head` in the backend entrypoint and
> drop `create_all`; until then, `upgrade.sh` is the supported upgrade path.

**Manual rollback** (if you're not using `upgrade.sh`):
```bash
cd ~/packetarch
git log --oneline -10
git reset --hard <commit-hash>
docker compose up -d --build
```

**Backup / restore** (Postgres + PCAP volumes):
```bash
./scripts/packetarch-backup.sh
./scripts/packetarch-restore.sh <snapshot>
```

---

## Traffic Agents (optional)

The live-traffic agent runs on whatever hosts should generate traffic — not
required to bring the platform up:

```bash
curl -fsSL https://<server>/agent/install.sh | sudo bash -s -- \
  --server https://<server> --name "Agent-1" --register
```

---

## Collecting diagnostics

One command, one redacted file, no need to know which install layout you are
on:

```bash
./scripts/collect-diagnostics.sh          # offline bundle: ./collect-diagnostics.sh
```

It writes `packetarch-diag-<utc>.txt` into the current directory and prints
the path. It is **read-only** — it starts nothing and restarts nothing.

What it collects: install layout and version (`git describe`, or the bundle's
`VERSION`), `.env` **key names only**, container states with **restart
counts** and the *text of every healthcheck* (so you can see what a green check
actually executes), the reachability chain a user takes (host → 443 → nginx →
`backend:8001`), Docker embedded-DNS resolution between services, declared vs
live network subnet, host routes/rules/listeners, the NAT rules if run with
`sudo`, a re-run of the egress preflight, the last 300 log lines per service,
and the appliance first-boot log *only if this is an appliance*.

**Secrets:** every secret value in `.env` is replaced with
`<redacted:KEY>` throughout the file — including inside container logs, so a
password a traceback printed in a DSN is scrubbed too. Skim it before sending;
it is plain text.

### Which install path am I on?

Support one-liners keep guessing at this, so check it first — the three layouts
put things in different places.

| Layout | Install dir | Tell | Helper scripts | Upgrade |
|--------|-------------|------|----------------|---------|
| **Git clone** (README / this guide, `server-init.sh`) | wherever you cloned — usually `~/packetarch` | `.git/` present | `./scripts/<name>.sh` | `./scripts/upgrade.sh`, or **Settings → Updates** |
| **Offline bundle** (`install.sh` from a release tarball) | `/opt/packetarch` by default (`--install-dir` overrides) | `VERSION` file, no `.git/` | `./<name>.sh` — staged **flat** beside `docker-compose.yml` | re-run `install.sh --upgrade` from a newer bundle |
| **Virtual appliance (OVA)** | `/opt/packetarch` | `/var/log/packetarch-firstboot.log` and `/opt/packetarch/.firstboot-done` | as the bundle | as the bundle |

`collect-diagnostics.sh`, `fix-db-password.sh` and `upgrade.sh` all locate the
install from their own path, so they work in any of the three without being
told. `collect-diagnostics.sh` prints which one it detected in the report
header.

## When the host's network overlaps Docker's

This is the failure that looks like nothing is wrong. On a VPN'd corporate
laptop the tunnel typically routes **172.16.0.0/12**, which covers almost all of
Docker's default address pools (172.17–172.31.0.0/16). When Docker hands the
stack's bridge a subnet inside that block:

- every container starts, and `docker compose ps` is green;
- `curl https://localhost/health` **inside** the frontend container returns
  `200`;
- the host still gets a **TCP reset** on 80/443, because the reply routes out
  through the VPN instead of back to the bridge;
- and Docker's embedded DNS resolver (`127.0.0.11`) can stop reverse-NATing
  replies on the same host, so the name `backend` stops resolving. nginx
  resolves its upstream per request (`frontend/nginx.conf`), so **every
  `/api/` call 502s** after the resolver timeout and the UI reports
  "Backend unreachable".

**PacketArch pins the subnet** so this cannot happen by accident. The stack's
network is declared in `docker-compose.yml` as
`networks.default.ipam.config[].subnet` = `${COMPOSE_SUBNET:-10.200.0.0/24}`.
The default avoids 172.16.0.0/12 (the usual site block), 172.16.0.0/16
specifically (PacketArch's own local-lab pool) and 192.168.0.0/16
(home/branch LANs). Scenario IP ranges (`10.{n}.0.0/16`) are simulated traffic
on isolated veths, never host routes, so they do not conflict with it.

Check before you install — the preflight flags a collision with Docker's
pools, the local-lab pool, **and** your configured `COMPOSE_SUBNET`:

```bash
./scripts/check-docker-egress.sh
```

If your site routes `10.200.0.0/24` too, pick a free /24:

```bash
echo 'COMPOSE_SUBNET=10.201.0.0/24' >> .env
docker compose down && docker compose up -d      # a subnet change needs the
                                                 # network RECREATED
```

`docker compose up -d` on its own is not enough, and worse than not enough: a
changed network config makes Compose remove and recreate the network
mid-command. It will do that even under a `docker compose run` (the upgrade's
`alembic` step), leaving a still-running Postgres re-addressed and no longer
resolvable by name. `scripts/upgrade.sh` detects a changed `COMPOSE_SUBNET` and
does the down/restart explicitly for this reason. If a container from outside
this compose project is attached to the network, removal is refused and
Compose exits **having already stopped the stack** — `upgrade.sh` names those
containers instead of leaving you with a dead box.

The host-level alternative, which fixes every compose project and every local
sensor lab at once, is `"default-address-pools"` in `/etc/docker/daemon.json`
(needs root and a daemon restart).

Verify what you actually got:

```bash
docker network inspect packetarch_default --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

## When the build can't reach the network

Every image builds network-touching steps (`poetry install`, `apt-get`,
`npm ci`, `apk add`) inside a **bridged build sandbox**, not on the host
network stack. A host with perfectly good internet can therefore fail every
build — the daemon pulls base images over the host stack and succeeds, then
the first `RUN` fails.

Diagnose before you reach for a workaround:

```bash
./scripts/check-docker-egress.sh
```

It separates the causes, because the popular fix (host networking for the
build) papers over the build-time ones equally and so tells you nothing about
which one you have:

| Cause | Signature | Durable fix |
|-------|-----------|-------------|
| Firewall drops the bridge's FORWARD traffic | no TCP egress from any container | firewalld: add `docker0` to the `docker` zone + masquerade. On Ubuntu ufw does **not** normally block Docker — check `DEFAULT_FORWARD_POLICY` and `iptables -S DOCKER-USER` |
| MTU mismatch (VPN/tunnel uplink below 1500) | **hangs**, not errors — DNS resolves, small requests work, downloads stall mid-transfer | `"mtu": <uplink mtu>` in `/etc/docker/daemon.json` |
| DNS unreachable from a container | host resolves fine, container `nslookup` fails (systemd-resolved's 127.0.0.53 stub isn't reachable from a bridge) | `"dns": ["<resolver>"]` in `/etc/docker/daemon.json` |
| Docker's subnets collide with the site's | containers reach the wrong host | `COMPOSE_SUBNET` in `.env` for this stack, or `"default-address-pools"` in `/etc/docker/daemon.json` for the whole host |
| Embedded DNS (127.0.0.11) broken | **no build symptom at all** — everything builds and starts, then every `/api/` call 502s and login says "Backend unreachable" | Same as above: it is the subnet collision showing up at runtime. Section 5 of the preflight names it. |

**Prefer the `daemon.json` fix.** Most of these also break *runtime* egress,
when the backend reaches a Cyber Vision Center, a CML server or an AI provider.
A build that succeeds is not an install that works.

If you must ship before the host can be fixed, the supported stopgap is an
`.env` line — **not** an edit to `docker-compose.yml`:

```bash
echo 'DOCKER_BUILD_NETWORK=host' >> .env
docker compose up -d --build
```

Every build stanza honours it, and it is carried into the backend so the agent
and updater images (built through the Docker socket, which Compose's
`build.network` cannot reach) use it too. It affects the build sandbox only —
the running stack is unchanged and the resulting images are identical.

Keep it in `.env` because `.env` is untracked. A hand-edit to
`docker-compose.yml` is a local change to a *tracked* file, and the release
upgrade (`scripts/upgrade.sh`) stashes those before checking out the new tag.
Remove the line once the host is fixed.

## Backend crashlooping on "password authentication failed"

Symptom: the backend restarts every ~70 seconds and never goes healthy, the
frontend stays in `Created` (it waits for a healthy backend), and
`docker compose logs backend` shows

```
FATAL:  password authentication failed for user "packetarch"
```

**`docker compose ps` will not help you here, and is actively misleading:**

| Container | Reports | Actually |
|-----------|---------|----------|
| `postgres` | healthy | `pg_isready` never authenticates — it only asks whether the server accepts connections |
| `celery_worker` | healthy | fixed in v1.20.2; before that its healthcheck only pinged Redis |
| `backend` | unhealthy | the only service that actually checks the database |
| `frontend` | `Created` | blocked on `backend: service_healthy` |

**Cause.** Postgres applies `POSTGRES_PASSWORD` *only* when it initialises an
empty data directory. A `packetarch_postgres_data` volume that survived a
`docker compose down` keeps the password it was **built** with, so a
regenerated `.env` silently stops matching it. Anything that replaces `.env`
while leaving the volume in place produces this: re-cloning into a fresh
directory, deleting `.env`, or `install.sh --force-env`.

**Fix, keeping the data:**

```bash
./scripts/fix-db-password.sh          # offline bundle: ./fix-db-password.sh
```

It rewrites the role's password to match `.env` over the container's unix
socket (which is `trust`, so no working password is needed), verifies the new
one authenticates over the network, then restarts the affected services.
`--check` reports without changing anything.

**Or discard the database and start clean — this deletes every scenario,
PCAP and user in it:**

```bash
docker compose down -v && docker compose up -d
```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Containers won't start | `docker compose logs` |
| Backend crashloops, `password authentication failed` | `./scripts/fix-db-password.sh` — see "Backend crashlooping" above. Ignore the green `postgres` healthcheck; it does not authenticate. |
| Build fails on pip/apt/npm/apk | `./scripts/check-docker-egress.sh` — see "When the build can't reach the network" above |
| Page loads but every login says "Backend unreachable" / "Server error" | nginx cannot resolve or reach `backend`. `./scripts/collect-diagnostics.sh` and read the DNS + in-container sections; the usual cause is a subnet/VPN overlap — see "When the host's network overlaps Docker's" |
| Containers healthy but the host gets a TCP reset on 443 | Subnet overlap with a site/VPN route. `./scripts/check-docker-egress.sh`, then set `COMPOSE_SUBNET` |
| Anything you can't place | `./scripts/collect-diagnostics.sh` writes one redacted file — send that |
| Traffic generation fails silently | `DOCKER_GID` in `.env` matches `getent group docker` |
| `permission denied` on docker | `sudo usermod -aG docker $USER`, then re-login |
| Encrypted settings reset on reboot | `ENCRYPTION_KEY` is unset in `.env` |
| Reset DB (wipes data!) | `docker compose down -v && docker compose up -d --build` |

## Access URLs

| Service | URL |
|---------|-----|
| Frontend | `https://<server>/` |
| API Docs (Swagger) | `https://<server>/api/docs` — **only when `DEBUG=true`**; disabled on a stock install |
| pgAdmin (tools profile, loopback) | `http://localhost:5050` via SSH tunnel |
