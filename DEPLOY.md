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
newgrp docker   # or log out/in for group membership to take effect

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
DEBUG=false
# ADMIN_PASSWORD intentionally omitted => first boot shows the setup wizard.
# Add ADMIN_PASSWORD=<value> only for a headless install (skips the wizard).
EOF
chmod 600 .env

# 4. Build and start
docker compose up -d --build
```

Or run the one-shot helper (does all of the above):

```bash
./scripts/server-init.sh         # defaults to ip-aegis/PacketArch @ master
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

## GitHub Actions Deployment (optional)

`ci.yml` runs lint/build on push/PR. `deploy.yml` can SSH to the server and
`git pull && docker compose up -d --build` on push to `master`. To use it, add
these repository secrets (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `SSH_HOST` | Production server IP/hostname |
| `SSH_USER` | SSH username on the server |
| `SSH_PRIVATE_KEY` | Deploy private key (full `-----BEGIN/END-----` block) |
| `POSTGRES_PASSWORD` / `SECRET_KEY` / `ENCRYPTION_KEY` / `ADMIN_PASSWORD` | Mirror the server `.env` |

`release.yml` (tag `v*`) builds the self-contained offline bundles for
air-gapped installs; `build-agent.yml` builds the traffic-agent image.

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

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Containers won't start | `docker compose logs` |
| Traffic generation fails silently | `DOCKER_GID` in `.env` matches `getent group docker` |
| `permission denied` on docker | `sudo usermod -aG docker $USER`, then re-login |
| Encrypted settings reset on reboot | `ENCRYPTION_KEY` is unset in `.env` |
| Reset DB (wipes data!) | `docker compose down -v && docker compose up -d --build` |

## Access URLs

| Service | URL |
|---------|-----|
| Frontend | `https://<server>/` |
| API Docs | `https://<server>/api/docs` |
| pgAdmin (tools profile, loopback) | `http://localhost:5050` via SSH tunnel |
