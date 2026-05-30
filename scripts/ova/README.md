# PacketArch Appliance OVA

Builds a distributable virtual appliance (`.ova`) of PacketArch. Power it
on, browse to `https://<appliance-ip>/`, accept the self-signed cert, and
complete the first-run setup wizard to create the admin account.

## Design — git-clone install (self-upgradeable)

The appliance is a **real git clone** of the repo, pinned to a release tag,
using the production `docker-compose.yml`. This is deliberate: it lets the
appliance use the **in-app remote upgrade** (Settings → System → Upgrade),
which git-fetches a newer tag from GitHub and rebuilds in place. So you
**rebuild the OVA only at major releases** — deployed appliances catch up
on their own via the upgrade button.

- **Build time** bakes Ubuntu 24.04 + Docker CE + a git clone at the release
  tag (origin set to the **public HTTPS** URL so the appliance can fetch
  upgrades with no credentials).
- **First boot** runs `packetarch-firstboot.service` →
  `/usr/local/sbin/packetarch-firstboot.sh`, which generates a fresh `.env`
  (per-VM secrets + `HOST_INSTALL_DIR` + `COMPOSE_PROJECT_NAME` +
  `DOCKER_GID`) and runs `docker compose up -d --build`. The frontend
  container mints a fresh self-signed cert on first start.

Nothing per-VM is baked into the shared image: secrets, TLS cert, and the
setup-wizard state are all created the first time *that* appliance boots.

### Tradeoff: first boot builds from source

Because images are built on first boot, **the appliance needs internet and
the first boot takes ~10–15 minutes** (poetry + npm). Subsequent boots reuse
the built images and start in seconds. This matches a normal production
install and is consistent with how the in-app upgrade rebuilds. If you need
an air-gapped, no-build appliance instead, use the offline tarball
(`scripts/build-release.sh`) with `install.sh` on a plain VM.

## Files

| File | Role |
|------|------|
| `build-ova.sh` | Orchestrator: clone → Ubuntu image → customize → VMDK → OVF/manifest → `.ova` |
| `firstboot.sh` | Baked to `/usr/local/sbin/packetarch-firstboot.sh`; generates `.env` + `compose up --build` once on first boot |
| `packetarch-firstboot.service` | One-shot systemd unit (guarded by `ConditionPathExists=!/opt/packetarch/.env`, 30-min timeout for the build) |
| `packetarch.ovf.template` | Broad-compat OVF 1.0 descriptor (placeholders filled by the build) |

## Prerequisites

```bash
# Fedora
sudo dnf install guestfs-tools qemu-img git curl
# Ubuntu/Debian
sudo apt-get install libguestfs-tools qemu-utils git curl
```

Build host needs network access (downloads the Ubuntu cloud image once,
cached under `dist/.ova-cache/`, and `apt`-installs Docker CE into the guest).

## Build

```bash
# From repo root. Bakes a clone pinned to the latest v* tag.
sudo ./scripts/ova/build-ova.sh
```

Output: `dist/packetarch-<version>-appliance.ova`

Useful overrides:

```bash
sudo OVA_GIT_REF=v1.6.0 \
     OVA_GIT_URL=https://github.com/ip-aegis/PacketArch.git \
     DISK_SIZE=60G VM_CPUS=4 VM_MEM=8192 \
     ./scripts/ova/build-ova.sh
```

| Var | Default | Notes |
|-----|---------|-------|
| `OVA_GIT_REF` | latest `v*` tag | tag/branch the appliance is pinned to |
| `OVA_GIT_URL` | public HTTPS repo | origin the appliance fetches upgrades from |
| `CLONE_SRC` | this repo | repo to clone FROM at build time |
| `VERSION` | `app_version` from `config.py` | OVA filename version |
| `DISK_SIZE` | `60G` | thin — the OVA only stores used blocks |
| `VM_CPUS` / `VM_MEM` | `4` / `8192` | OVF defaults the importer suggests |
| `CONSOLE_PASS` | `packetarch` | console password for the `ubuntu` user |
| `ROOT_PART` | autodetected | override root-partition detection |
| `KEEP_WORK` | `0` | keep the intermediate qcow2/vmdk |

## Deploy

1. Import the `.ova` into VirtualBox (`File → Import Appliance`), VMware
   Workstation/Player, or ESXi/vSphere.
2. Put it on a network with **DHCP and internet** and power it on.
3. First boot builds + starts the stack (~10–15 min). Watch progress on the
   console at `/var/log/packetarch-firstboot.log` if needed.
4. Browse to `https://<appliance-ip>/`, accept the self-signed cert, and
   complete the setup wizard.

> **Security:** the wizard is unprotected — the first person to reach the
> URL becomes admin. Complete setup before exposing the appliance. Also
> change the default console password (`ubuntu` / `packetarch`) after first
> login.

## Upgrading a deployed appliance

Use **Settings → System → Upgrade** in the UI. It launches the updater
container, which `git fetch`es tags from the public repo, checks out the
target release, rebuilds, migrates, and restarts — with an automatic backup
and rollback on failure. No new OVA required. (CLI equivalent on the
appliance: `cd /opt/packetarch && sudo scripts/upgrade.sh --to vX.Y.Z`.)

## Networking

The cloud image normally derives its network config from a cloud-init
*datasource*; a standalone appliance has none, so the build bakes a static
netplan (`/etc/netplan/99-appliance.yaml`) that DHCPs whatever the first
ethernet is named (`enp1s0` / `ens3` / `eth0` / …) and disables cloud-init
network management (`99-disable-network-config.cfg`). Without this the NIC
is never configured and the appliance has no network on a real hypervisor.
The appliance gets its address from your network's DHCP.

## Notes / future work

- **Cert SAN**: the self-signed cert won't match the appliance IP — that's
  the normal "accept the cert" flow. To regenerate with the DHCP IP in a
  SAN, extend `firstboot.sh` before `compose up`.
- **Fast first boot**: pre-baking project-tagged images would skip the
  first-boot build, but upgrades rebuild from source anyway, so it's not
  wired up. Build-on-first-boot keeps the image simple and small.
- **Static IP / hostname at deploy**: OVF vApp properties (ESXi) could
  inject these and be read via `qemu-guest-agent` in `firstboot.sh`. Not
  wired up — DHCP + wizard covers the common case.
