# PacketArch Appliance OVA

Builds a distributable virtual appliance (`.ova`) of PacketArch. Power it
on, browse to `https://<appliance-ip>/`, accept the self-signed cert, and
complete the first-run setup wizard to create the admin account.

## Design

The OVA is a thin wrapper over the existing offline release flow:

- **Build time** bakes Ubuntu 24.04 + Docker + your offline bundle (all
  Docker image tarballs + `install.sh` + compose) into the disk.
- **First boot** runs `packetarch-firstboot.service` → `firstboot.sh` →
  the bundle's `install.sh`, which `docker load`s the baked images,
  generates **fresh per-VM secrets** into `.env`, and `docker compose up`s
  the stack. The frontend container mints a **fresh self-signed cert** on
  its first start.

Nothing per-VM is baked into the shared image: secrets, TLS cert, and the
setup-wizard state are all created the first time *that* appliance boots,
so every deployed copy is unique and lands on the wizard.

This reuses `scripts/build-release.sh` and `scripts/release-bundle/install.sh`
as the single source of truth for "stand up the stack" — the OVA does not
fork that logic.

## Files

| File | Role |
|------|------|
| `build-ova.sh` | Orchestrator: bundle → Ubuntu image → customize → VMDK → OVF/manifest → `.ova` |
| `firstboot.sh` | Baked to `/opt/packetarch/firstboot.sh`; runs the bundle installer once on first boot |
| `packetarch-firstboot.service` | One-shot systemd unit (guarded by `ConditionPathExists=!/opt/packetarch/.env`) |
| `packetarch.ovf.template` | Broad-compat OVF 1.0 descriptor (placeholders filled by the build) |

## Prerequisites

```bash
# Fedora
sudo dnf install guestfs-tools qemu-img curl
# Ubuntu/Debian
sudo apt-get install libguestfs-tools qemu-utils curl
```

Build host needs network access (downloads the Ubuntu cloud image once,
cached under `dist/.ova-cache/`, and `apt`-installs Docker into the guest).

## Build

```bash
# From repo root. Builds the offline bundle first if dist/ doesn't have one.
sudo ./scripts/ova/build-ova.sh
```

Output: `dist/packetarch-<version>-appliance.ova`

Useful overrides:

```bash
sudo VERSION=1.4.2 \
     BUNDLE_TARBALL=dist/packetarch-1.4.2-offline.tar.gz \
     DISK_SIZE=80G VM_CPUS=4 VM_MEM=8192 \
     ./scripts/ova/build-ova.sh
```

| Var | Default | Notes |
|-----|---------|-------|
| `VERSION` | `app_version` from `config.py` | |
| `BUNDLE_TARBALL` | auto (`dist/...-offline.tar.gz`) | reuse a prebuilt bundle |
| `DISK_SIZE` | `60G` | thin — the OVA only stores used blocks |
| `VM_CPUS` / `VM_MEM` | `4` / `8192` | OVF defaults the importer suggests |
| `CONSOLE_PASS` | `packetarch` | console password for the `ubuntu` user |
| `KEEP_WORK` | `0` | keep the intermediate qcow2/vmdk |

## Deploy

1. Import the `.ova` into VirtualBox (`File → Import Appliance`), VMware
   Workstation/Player, or ESXi/vSphere.
2. Put it on a network with DHCP and power it on.
3. First boot loads images + starts the stack (~2–4 min). Watch progress
   on the console at `/var/log/packetarch-firstboot.log` if needed.
4. Browse to `https://<appliance-ip>/`, accept the self-signed cert, and
   complete the setup wizard (choose admin username/password, name the
   site, optionally wire AI / Cyber Vision).

> **Security:** the wizard is unprotected — the first person to reach the
> URL becomes admin. Complete setup before exposing the appliance. Also
> change the default console password (`ubuntu` / `packetarch`) after first
> login.

## Variant

This builds the **full** variant (`LIVE_TRAFFIC_ENABLED=true`). To ship a
PCAP-only appliance, build a PCAP-only bundle first and point at it:

```bash
PCAP_ONLY=1 ./scripts/build-release.sh
sudo BUNDLE_TARBALL=dist/packetarch-<version>-pcap-offline.tar.gz \
     ./scripts/ova/build-ova.sh
```

## Notes / future work

- **Cert SAN**: the self-signed cert won't match the appliance IP — that's
  the normal "accept the cert" flow. To regenerate with the DHCP IP in a
  SAN, extend `firstboot.sh` before it calls `install.sh`.
- **Static IP / hostname at deploy**: OVF vApp properties (ESXi) could
  inject these and be read via `qemu-guest-agent`/`vmtoolsd` in
  `firstboot.sh`. Not wired up — DHCP + wizard covers the common case.
- **Disk reclaim**: the baked image tarballs under
  `/opt/packetarch/bundle/images` remain after first boot (allows re-load).
  Delete them in `firstboot.sh` if you want the space back.
