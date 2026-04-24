# PacketArch — Site Installation

This bundle contains everything needed to stand up PacketArch on a new
server, including in air-gapped environments.

PacketArch is © 2026 Rocky Smith (<rocky.d.smith@proton.me>) and is
licensed under **GPL-3.0**. See `LICENSE`, `NOTICE`, and
`THIRD_PARTY_LICENSES.md` for details.

---

## Prerequisites

- **OS**: Linux with `x86_64` (tested on Ubuntu 22.04+, RHEL 9, Fedora)
- **Docker**: 24.0+ with Docker Compose plugin
- **Memory**: 8 GB RAM minimum (16 GB recommended)
- **Disk**: 20 GB free (images + database + PCAP output)
- **Privileges**: `sudo` to write to `/opt/packetarch` and bind port 443

## Ports

| Port  | Purpose                            | Direction       |
|-------|------------------------------------|-----------------|
| 443   | Web UI (HTTPS, self-signed)        | Admin → server  |
| 5432  | PostgreSQL                         | Localhost only  |
| 6379  | Redis                              | Localhost only  |
| 443   | Agent ↔ server WebSocket           | Agent → server  |

## Optional egress (outside the lab)

PacketArch runs fully offline. If you want to enable AI-powered scenario
generation, the backend needs outbound HTTPS to `api.anthropic.com`. You
can leave AI off by setting `AI_ENABLED=false` in `.env`; the UI hides
AI-related features automatically.

---

## Installation

```bash
tar xzf packetarch-*-offline.tar.gz
cd packetarch-*-offline
sudo ./install.sh
```

The installer will:

1. Load all bundled Docker images into the local Docker daemon.
2. Generate `.env` with random passwords (PostgreSQL, JWT secret,
   admin password). These are printed **once** at the end of install;
   save them.
3. Start the stack with `docker compose up -d`.
4. Wait for the backend healthcheck to pass.

When it finishes, open `https://<server-ip>/` in a browser. Accept the
self-signed certificate. Log in with username `admin` and the password
printed by the installer.

## First login

You will be asked to acknowledge the GPL-3.0 license and ownership. This
is recorded per-user; the text can be re-read later under the user menu
→ About PacketArch.

## Turning AI on or off

Edit `.env`, set:

```
AI_ENABLED=false   # default true
```

Then `docker compose up -d backend` to apply. The UI will hide AI
surfaces within a page reload.

If `AI_ENABLED=true`, also set an `ANTHROPIC_API_KEY` in the admin
Settings page (Settings → AI Provider) — keys are encrypted at rest.

## Providing your own TLS certificate

By default, the frontend generates a self-signed cert. To use a real
one:

```bash
sudo mkdir -p /opt/packetarch/certs
sudo cp /path/to/server.crt /opt/packetarch/certs/server.crt
sudo cp /path/to/server.key /opt/packetarch/certs/server.key
sudo chmod 600 /opt/packetarch/certs/server.key
sudo docker compose restart frontend
```

The compose file mounts `./certs` into nginx if present.

## Upgrades

When a new release tarball arrives:

```bash
cd /opt/packetarch
sudo docker compose down
sudo ./install.sh --upgrade    # loads new images, preserves .env and volumes
sudo docker compose up -d
```

The installer never overwrites an existing `.env` unless you pass
`--force-env`.

## Backups

The bundle ships two scripts that wrap database + volume snapshots into
a single tarball suitable for restore on the same or a different host.

```bash
cd /opt/packetarch

# Take a backup. Redacts .env secrets by default.
sudo ./packetarch-backup.sh

# Backup to a specific location, include raw secrets (encrypt the tarball
# yourself if you store it anywhere you wouldn't store .env).
sudo ./packetarch-backup.sh --output /mnt/safe/pa.tgz --with-secrets

# Restore. Prompts for confirmation; pass --yes in automation.
sudo ./packetarch-restore.sh /mnt/safe/pa.tgz
```

Back up before every upgrade. The tarball contains:
`postgres.dump` (pg_dump custom format), `pcap_output.tar.gz`,
`pcap_uploads.tar.gz`, a redacted or raw `.env`, and a `manifest.json`
recording the PacketArch version + creation timestamp.

## Remote traffic agents

Agents connect to PacketArch over an outbound WebSocket (TLS on 443).
No inbound ports are required on the agent host. Install on each agent
box with:

```bash
curl -fsSLk https://<your-server>/agent/install.sh | sudo bash -s -- \
    --server https://<your-server> --token <agent-token> --insecure
```

Generate agent tokens in the UI under Settings → Agents.

## Support

PacketArch is owned and maintained by **Rocky Smith**
(<rocky.d.smith@proton.me>). Bug reports and questions:
<https://github.com/ip-aegis/PacketArch/issues>

## Uninstall

```bash
sudo docker compose down -v   # -v removes volumes (DATA LOSS)
sudo rm -rf /opt/packetarch
```
