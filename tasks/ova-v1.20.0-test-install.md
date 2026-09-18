# OVA v1.20.0 — check + test install

Date: 2026-09-18. Artifact: `packetarch-1.20.0-appliance.ova`
(published, non-draft, on the v1.20.0 GitHub Release).
Test host: Alpha (10.10.20.62, KVM), VM `pa-ova-test`, 4 vCPU / 8 GB,
bridged to `br0` (the lab /24, real DHCP) — a faithful "power it on and
browse to it" test rather than a NAT sandbox.

## Artifact checks (all pass)

| Check | Result |
|-------|--------|
| sha256 of the tested file vs the published release asset | `b3f608dd…1089e` — **identical** |
| OVA tar member order | `.ovf` first, then `.vmdk`, then `.mf` (spec-correct) |
| `.mf` SHA256s | match both extracted files |
| OVF placeholders | none left unsubstituted |
| `ovf:size` vs actual VMDK | 977378304 = exact |
| `ovf:capacity` vs VMDK virtual size | 64424509440 = 60 GiB = exact |
| VMDK format | `streamOptimized` (required for VMware OVA import) |
| Baked clone `HEAD` | `5e1b513` = the v1.20.0 tag commit |
| Baked `app_version` | `1.20.0` |
| Baked `remote.origin.url` | `https://github.com/ip-aegis/PacketArch.git` (public HTTPS ⇒ in-app upgrade can fetch) |
| No per-VM state baked | `.env` absent; no SSH host keys; machine-id truncated |
| Guest | Ubuntu 24.04.4, Docker 29.8.1 + Compose v5.5.1, `docker` + `packetarch-firstboot` both enabled |

## Boot test (passes end to end)

- **DHCP on a real hypervisor works.** Leased `10.10.20.129` 30 s after
  power-on; the generic `match: name: "e*"` netplan matched virtio's
  `enp1s0`. This is the failure mode the baked netplan exists to prevent,
  and it is fixed.
- **First boot: 2 min 10 s**, not the documented 10–15 min
  (13:17:36 → 13:19:46, and that *includes* 60 s of retry sleeps). On a
  fast host with a fast link the source build is ~70 s. The README's
  estimate is pessimistic, not wrong.
- Fresh self-signed cert minted per appliance (`notBefore` = boot time).
- `docker compose ps`: **6/6 up**, backend / celery_worker / postgres /
  redis all `healthy`.
- `alembic heads` → **exactly one** (`add_cv_center_ui_creds`). No
  multiple-heads regression on a fresh DB.
- `/api/v1/setup/status` → `setup_complete: false` ⇒ the wizard shows and
  auto-graduation correctly did *not* fire with no admin user.
- `/api/v1/about` → `1.20.0`, flags `ai_enabled: true`,
  `live_traffic_enabled: true`, `multi_sensor_topology_enabled: true`,
  `mimic_enabled: false` — exactly the intended shipping posture.
- **Wizard completes** (`POST /setup/complete` → 200 + auto-login
  tokens); re-login as the new admin → 200; `setup_complete` flips true.
- Template catalog intact: **37 templates / 8 verticals**.
- **Full end-to-end generation on the fresh appliance**: created a
  water/wastewater scenario (46 devices, 67 flows, 6 zones), ran a 30 s
  PCAP job → `completed`, **5299 packets / 472 705 bytes**, downloaded
  and verified a valid libpcap file carrying real EtherNet/IP
  request/response pairs.

## Findings

### 1. sshd is permanently dead on every appliance — FIXED

`sshd -t` → `sshd: no hostkeys available -- exiting`; `/etc/ssh/` has no
`ssh_host_*`. Cause: `build-ova.sh:202` deletes the host keys (correct —
a template must not ship a shared key pair), and
`cloud-init-disable-network.cfg` asserts "the rest of cloud-init (ssh
host key regen, etc.) still runs". **It does not.** With no datasource,
ds-identify disables cloud-init outright: `cloud-init status` reports
`disabled / disabled-by-generator`. So nothing ever regenerates the keys
and `ssh.service` fails `ExecStartPre` forever. This also explains the
odd port-22 behaviour observed during the test: `ssh.socket` listens (so
a probe sees 22 "open") while the service behind it fails, so every
connection is refused.

Impact: the appliance is console-only. No SSH for an operator, no
`scp` of PCAPs, no remote troubleshooting.

Fix: `ssh-keygen -A` in `firstboot.sh` before the Docker wait — per-VM
keys, generated on the appliance, never shared. The false comment is
corrected in the same commit, because that comment is what will cause
this to regress.

**The fix does NOT reach appliances already deployed.** `scripts/upgrade.sh`
only does `git fetch` + `git checkout <tag>` + rebuild + alembic; it never
re-bakes `/usr/local/sbin/packetarch-firstboot.sh`, the systemd unit or the
host keys, and the unit is sentinel-guarded by `.firstboot-done` so it never
re-runs. So every appliance built from v1.20.0 or earlier keeps a dead sshd
forever, even after a successful in-app upgrade. Only a fresh OVA carries the
fix. Operator remediation, at the console, one time:

```bash
sudo ssh-keygen -A && sudo systemctl restart ssh
```

### 2. First-boot DNS race — 2 of 3 build attempts failed — FIXED

The log shows `build attempt 1/3` and `2/3` both failing on
`lookup registry-1.docker.io on 127.0.0.53:53: server misbehaving` —
systemd-resolved had no DHCP nameserver yet. Attempt 3 succeeded.

This is not cosmetic. The three attempts are separated by fixed 30 s
sleeps, so all three can burn inside a ~90 s window. This run recovered;
a slower resolver exits FATAL, no sentinel is written, and the appliance
needs a manual reboot to retry.

Fix: a bounded DNS-readiness wait mirroring the existing `docker_ready`
loop, plus `nss-lookup.target` in the unit's `After=`/`Wants=`.

### 3. Talos/Snort rules are ALREADY PUBLISHED in a public GPL repo — most urgent

Not a queued decision — a live exposure.
`uploads/{Malware-CNC,Exploit-Kit,Malware-Backdoor,OS-Other,Experimental-Scada}_rules.txt`
are tracked at v1.20.0, so they are in the public repo, in the **published,
non-draft** v1.20.0 Release, and baked into an appliance with a public
download link, right now.

~2185 rules. The basis for "registered/subscriber Talos content, not
community": each rule carries a Talos sid + rev and a rule_docs reference —
e.g. `sid:16811; rev:8` with `reference:url,snort.org/rule_docs/1-16811`,
and `sid:44677; rev:2` — plus `metadata:impact_flag red`, which is a Talos
field. Those sids are checkable against whichever rule set they came from.
CLAUDE.md requires licensing to be flagged before merge; this is that flag.

Remediation has a long tail: history rewrite on a public repo, *plus* a new
OVA build, *plus* the v1.20.0 assets are already distributed.

Not a pure delete: `protocol_engines/attacks/snort_actions.py:41` cites
those paths as provenance, removal needs history rewrite to be effective
on the public repo, and a new appliance build to be effective in the OVA.
Rocky's call.

### 4. Repo hygiene — what else ships inside the clone

Also tracked at v1.20.0 and therefore inside every appliance:
`ss/Screenshot 2025-12-08 081043.png` (128 KB), `scratchpad/` (4 BACnet
dev scripts), and `uploads/networkNodes-2026020*.csv` — three Cyber
Vision inventory exports carrying real lab MACs, vendors and the
`CVTrafficGen01` project name. Same public-history caveat as #3; grouped
with it as one "what ships in the clone" decision.

### 5. Base image ships unpatched

The guest reports **141 pending updates, 112 of them security**.
`build-ova.sh` installs Docker CE but never `apt-get upgrade`s the cloud
image. Recommend an `apt-get -y dist-upgrade` in the `virt-customize`
run (costs image size, and it is a patch-cadence policy call, so not
applied unilaterally).

### 6. Smaller items

- `/api/v1/about` reports `build_commit: "dev"` on the appliance. The
  clone is at `5e1b513`; the running app cannot tell you that. Provenance
  is invisible in-app.
- `docker-compose.yml` pins Postgres as `timescale/timescaledb:latest-pg15`
  — a floating tag. An appliance built next month can get a different
  database engine than the one tested here.
- API-shape wart tripped over live: `GET /templates/list` items do not
  carry the `template_name` that `POST /templates/create` requires, and
  `create` silently falls back to the first template in the vertical
  rather than rejecting an unknown name. Appliance behaving as coded, not
  an OVA defect.

## Review — fixes verified on a rebuilt appliance

Both fixes were re-tested, not just read. A second VM (`pa-ova-fix`,
10.10.20.130) was built from a pristine copy of the shipped OVA's disk
with the corrected `firstboot.sh` / unit / cloud-init comment baked in
using the **same `virt-customize --copy-in` primitives `build-ova.sh`
uses**, then booted on `br0` exactly like the first test.

| | Shipped v1.20.0 | With the fixes |
|---|---|---|
| `systemctl is-active ssh` | `failed` (`no hostkeys available`) | **`active`**, `sshd -t` rc=0 |
| First-boot log | `build attempt 1/3` → `attempt 1 failed; retrying in 30s` | `[0/3] Generating this appliance's SSH host keys...` |
| DNS | attempts 1 + 2 died on `registry-1.docker.io` resolution | `waiting for DNS... (1..17/30)` → **`DNS ready.`** |
| Build attempts | 1 failed, 2 failed, 3 succeeded | **`build attempt 1/3`, succeeded** |
| Containers | 6/6 healthy | 6/6 healthy |
| App | 1.20.0, wizard shown | 1.20.0, wizard shown |

The DNS wait took **17 iterations ≈ 34 s** — the race is real and not
marginal. The old code covered a ~60–90 s window with three fixed 30 s
sleeps, so the shipped OVA recovered with little margin; a slower
resolver would have exited FATAL and required a manual reboot.

One honest limit on the SSH fix: sshd now **starts** with per-VM host
keys, which is the defect that was fixed, but the cloud image's
`60-cloudimg-settings.conf` still sets `PasswordAuthentication no`, so
`ubuntu` / `packetarch` over SSH is refused by design. That is the right
default — password SSH with a documented default password would be worse
than no SSH. The operator adds a key from the console; before the fix, no
amount of key-adding would have helped, because sshd could never start.

Fixed in `563bc1e`. Findings 3–6 are unaddressed by design and are
Rocky's call (3 and 4 touch published git history).

## State

- `pa-ova-test` (the as-shipped run, wizard completed, scenario + PCAP)
  — **destroyed and undefined**.
- `pa-ova-fix` (the fixed run, fresh wizard state) — **left running** at
  `https://10.10.20.130/` so the appliance can be clicked through.
  Tear down with:
  `sudo virsh destroy pa-ova-fix && sudo virsh undefine pa-ova-fix --remove-all-storage`
- Scratch on Alpha: `~/ova-test/` (~3.5 GB: the extracted OVA + converted
  qcow2). Safe to delete.
