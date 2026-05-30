#!/usr/bin/env bash
# Build a distributable PacketArch appliance OVA (git-clone install).
#
# Pipeline:
#   git clone @ release tag (origin = public HTTPS)  ──┐
#   Ubuntu 24.04 cloud image  ─────────────────────────┤
#                                                       ▼
#   virt-resize (grow rootfs) -> virt-customize: install Docker CE + git,
#   bake the clone at /opt/packetarch, install the one-shot first-boot unit,
#   scrub machine identity
#                                                       ▼
#   qemu-img convert -> stream-optimized VMDK
#                                                       ▼
#   render OVF (broad-compat) + .mf manifest -> tar -> .ova
#
# The appliance is a REAL git clone using the prod docker-compose.yml. On
# first power-on, packetarch-firstboot.service generates a fresh .env (per-VM
# secrets), then `docker compose up -d --build` builds + starts the stack and
# lands on the setup wizard at https://<dhcp-ip>/. Because it's a git clone,
# the in-app Settings -> System upgrade works afterwards (the updater container
# git-fetches a newer tag and rebuilds). This trades the air-gapped offline
# model for a source install: first boot needs internet and ~10-15 min to build.
#
# Usage (from repo root):
#   sudo ./scripts/ova/build-ova.sh
#
# Env overrides:
#   VERSION=1.6.0          OVA name version (default: app_version from config.py)
#   OVA_GIT_REF=v1.6.0     Tag/branch the appliance is pinned to (default: latest v* tag)
#   OVA_GIT_URL=...        origin the appliance fetches upgrades from
#                          (default: https://github.com/ip-aegis/PacketArch.git)
#   CLONE_SRC=path         Repo to clone FROM at build time (default: this repo)
#   DISK_SIZE=60G          Virtual disk size (thin; OVA only stores used blocks)
#   VM_CPUS=4 VM_MEM=8192  Default OVF CPU / memory (MB)
#   CONSOLE_PASS=...       Console password for the 'ubuntu' user (default: packetarch)
#   UBUNTU_IMG_URL=...     Override the cloud image source
#   ROOT_PART=/dev/sdaN    Override root-partition autodetection
#   OUT_DIR=/some/path     Output dir (default: dist/)
#   KEEP_WORK=1            Keep the intermediate qcow2/vmdk for debugging

set -euo pipefail

cd "$(dirname "$0")/../.."
REPO_ROOT="$(pwd)"
OVA_DIR="${REPO_ROOT}/scripts/ova"

OVA_GIT_URL="${OVA_GIT_URL:-https://github.com/ip-aegis/PacketArch.git}"
OVA_GIT_REF="${OVA_GIT_REF:-$(git tag -l 'v*' --sort=-v:refname | head -1)}"
# Name the OVA after the RELEASE it bakes (the pinned ref), NOT the in-dev
# app_version — the appliance contains OVA_GIT_REF's code, so the filename
# must match it. Strips a leading 'v' (v1.6.0 -> 1.6.0).
VERSION="${VERSION:-${OVA_GIT_REF#v}}"
CLONE_SRC="${CLONE_SRC:-${REPO_ROOT}}"
DISK_SIZE="${DISK_SIZE:-60G}"
VM_CPUS="${VM_CPUS:-4}"
VM_MEM="${VM_MEM:-8192}"
CONSOLE_PASS="${CONSOLE_PASS:-packetarch}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/dist}"
KEEP_WORK="${KEEP_WORK:-0}"

UBUNTU_IMG_URL="${UBUNTU_IMG_URL:-https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img}"
CACHE_DIR="${REPO_ROOT}/dist/.ova-cache"
BASE_IMG="${CACHE_DIR}/$(basename "${UBUNTU_IMG_URL}")"

WORK="${OUT_DIR}/.ova-work-${VERSION}"
CLONE_STAGE="${WORK}/packetarch"
QCOW="${WORK}/packetarch-${VERSION}.qcow2"
VMDK_NAME="packetarch-${VERSION}-disk1.vmdk"
VMDK="${WORK}/${VMDK_NAME}"
OVF="${WORK}/packetarch-${VERSION}.ovf"
MF="${WORK}/packetarch-${VERSION}.mf"
OVA="${OUT_DIR}/packetarch-${VERSION}-appliance.ova"

log() { echo -e "\n\033[1;36m== $* ==\033[0m"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# --- prechecks ----------------------------------------------------------
[[ "$(id -u)" -eq 0 ]] || die "must run as root (virt-customize needs it). Use sudo."

MISSING=()
command -v virt-customize >/dev/null || MISSING+=("virt-customize (guestfs-tools)")
command -v qemu-img       >/dev/null || MISSING+=("qemu-img (qemu-img)")
command -v git            >/dev/null || MISSING+=("git")
command -v curl           >/dev/null || MISSING+=("curl")
if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "ERROR: missing tools:" >&2
    printf '  - %s\n' "${MISSING[@]}" >&2
    echo "" >&2
    echo "Fedora:  sudo dnf install guestfs-tools qemu-img git curl" >&2
    echo "Ubuntu:  sudo apt-get install libguestfs-tools qemu-utils git curl" >&2
    exit 1
fi
[[ -n "${OVA_GIT_REF}" ]] || die "no release tag found; set OVA_GIT_REF=vX.Y.Z."

mkdir -p "${OUT_DIR}" "${CACHE_DIR}" "${WORK}"

# Use the direct (appliance) backend for ALL libguestfs tools below
# (virt-filesystems, virt-resize, virt-customize). The default libvirt
# backend needs a running virtqemud socket, which a plain root shell doesn't have.
export LIBGUESTFS_BACKEND=direct

# --- 1. git clone @ release tag -----------------------------------------
log "[1/7] Preparing git clone (${OVA_GIT_REF})"
echo "  cloning from: ${CLONE_SRC}"
echo "  pinned to:    ${OVA_GIT_REF}"
echo "  upgrade origin: ${OVA_GIT_URL}"
rm -rf "${CLONE_STAGE}"
# file:// (not a plain path) forces a real clone with no cross-repo hardlinks,
# so the staged tree is self-contained when copied into the guest.
git clone --quiet "file://${CLONE_SRC}" "${CLONE_STAGE}"
git -C "${CLONE_STAGE}" checkout --quiet "${OVA_GIT_REF}"
# Point the baked clone at the public HTTPS origin so the appliance can
# `git fetch` upgrades anonymously (no SSH keys needed on the appliance).
git -C "${CLONE_STAGE}" remote set-url origin "${OVA_GIT_URL}"
git -C "${CLONE_STAGE}" gc --quiet 2>/dev/null || true
[[ -f "${CLONE_STAGE}/docker-compose.yml" ]] || die "clone missing docker-compose.yml — bad ref?"
echo "  HEAD: $(git -C "${CLONE_STAGE}" describe --tags --always)"

# --- 2. base cloud image ------------------------------------------------
log "[2/7] Fetching Ubuntu cloud image"
if [[ ! -f "${BASE_IMG}" ]]; then
    echo "  downloading ${UBUNTU_IMG_URL}"
    curl -fSL --retry 3 -o "${BASE_IMG}.partial" "${UBUNTU_IMG_URL}"
    mv "${BASE_IMG}.partial" "${BASE_IMG}"
else
    echo "  cached: ${BASE_IMG}"
fi

echo "  preparing ${DISK_SIZE} target disk and expanding root filesystem"
# NOTE: a bare `qemu-img resize` grows only the DISK — the guest root
# filesystem stays at the cloud image's ~2GB, and building images on first
# boot needs far more. virt-resize grows the partition AND the filesystem.
# --long already reports Size in bytes; pick the largest partition as root.
ROOT_PART="${ROOT_PART:-$(virt-filesystems -a "${BASE_IMG}" --partitions --long 2>/dev/null \
    | awk 'NR>1 {print $4, $1}' | sort -n | tail -1 | awk '{print $2}')}"
[[ -n "${ROOT_PART}" ]] || die "could not detect root partition in ${BASE_IMG} (set ROOT_PART=/dev/sdaN)"
echo "  root partition: ${ROOT_PART}"
rm -f "${QCOW}"
qemu-img create -f qcow2 "${QCOW}" "${DISK_SIZE}" >/dev/null
virt-resize --expand "${ROOT_PART}" "${BASE_IMG}" "${QCOW}"

# --- 3. customize -------------------------------------------------------
log "[3/7] Customizing image (Docker CE + clone + first-boot unit)"
# Install Docker CE from Docker's apt repo (mirrors scripts/server-init.sh) so
# `docker compose build` works for both first boot and in-app upgrades. The
# repo is added + the engine installed entirely via ordered --run-commands so
# this does not depend on whether virt-customize hoists --install.
virt-customize -a "${QCOW}" --network \
    --install git,curl,ca-certificates,gnupg,qemu-guest-agent \
    --run-command 'install -m 0755 -d /etc/apt/keyrings' \
    --run-command 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg' \
    --run-command 'chmod a+r /etc/apt/keyrings/docker.gpg' \
    --run-command 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list' \
    --run-command 'apt-get update' \
    --run-command 'apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin' \
    --run-command 'systemctl enable docker' \
    --run-command 'systemctl enable qemu-guest-agent || true' \
    --copy-in "${CLONE_STAGE}:/opt" \
    --copy-in "${OVA_DIR}/firstboot.sh:/usr/local/sbin" \
    --run-command 'mv /usr/local/sbin/firstboot.sh /usr/local/sbin/packetarch-firstboot.sh' \
    --run-command 'chmod +x /usr/local/sbin/packetarch-firstboot.sh' \
    --copy-in "${OVA_DIR}/packetarch-firstboot.service:/etc/systemd/system" \
    --mkdir /etc/systemd/system/multi-user.target.wants \
    --link /etc/systemd/system/packetarch-firstboot.service:/etc/systemd/system/multi-user.target.wants/packetarch-firstboot.service \
    --password "ubuntu:password:${CONSOLE_PASS}" \
    --run-command 'cloud-init clean --logs || true' \
    --run-command 'truncate -s0 /etc/machine-id; rm -f /var/lib/dbus/machine-id; ln -sf /etc/machine-id /var/lib/dbus/machine-id' \
    --run-command 'rm -f /etc/ssh/ssh_host_*' \
    --run-command 'rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*' \
    --run-command 'fstrim -av || true'

# --- 4. convert to stream-optimized VMDK --------------------------------
log "[4/7] Converting to stream-optimized VMDK"
qemu-img convert -p -O vmdk -o subformat=streamOptimized,compat6 "${QCOW}" "${VMDK}"

# --- 5. render OVF ------------------------------------------------------
log "[5/7] Rendering OVF descriptor"
# Parse the plain-text "virtual size: 60 GiB (NNN bytes)" line. NOT the JSON
# output: this qemu's --output=json nests a "children" array whose inner
# "file" node ALSO has a "virtual-size", so a naive grep grabs the on-disk
# file size instead of the disk's real virtual capacity.
DISK_CAPACITY="$(qemu-img info "${QCOW}" | sed -n 's/^virtual size:.*(\([0-9]\+\) bytes).*/\1/p')"
[[ -n "${DISK_CAPACITY}" ]] || die "could not read virtual size from ${QCOW}"
VMDK_FILE_SIZE="$(stat -c%s "${VMDK}")"

sed -e "s/@VERSION@/${VERSION}/g" \
    -e "s/@VMDK_NAME@/${VMDK_NAME}/g" \
    -e "s/@VMDK_FILE_SIZE@/${VMDK_FILE_SIZE}/g" \
    -e "s/@DISK_CAPACITY@/${DISK_CAPACITY}/g" \
    "${OVA_DIR}/packetarch.ovf.template" > "${OVF}"

# Apply CPU/memory overrides into the rendered OVF.
sed -i -e "s#<rasd:VirtualQuantity>4</rasd:VirtualQuantity>#<rasd:VirtualQuantity>${VM_CPUS}</rasd:VirtualQuantity>#" \
       -e "s#<rasd:VirtualQuantity>8192</rasd:VirtualQuantity>#<rasd:VirtualQuantity>${VM_MEM}</rasd:VirtualQuantity>#" \
    "${OVF}"

# --- 6. manifest --------------------------------------------------------
log "[6/7] Writing manifest"
( cd "${WORK}"
  {
    echo "SHA256($(basename "${OVF}"))= $(sha256sum "$(basename "${OVF}")" | awk '{print $1}')"
    echo "SHA256(${VMDK_NAME})= $(sha256sum "${VMDK_NAME}" | awk '{print $1}')"
  } > "$(basename "${MF}")"
)

# --- 7. pack ------------------------------------------------------------
log "[7/7] Packing OVA"
# OVA = uncompressed tar; order matters: .ovf first, then .vmdk, then .mf.
( cd "${WORK}"
  tar -cf "${OVA}" "$(basename "${OVF}")" "${VMDK_NAME}" "$(basename "${MF}")"
)

if [[ "${KEEP_WORK}" != "1" ]]; then
    rm -rf "${WORK}"
fi

SIZE="$(du -h "${OVA}" | awk '{print $1}')"
echo ""
echo "================================================================"
echo "  Done."
echo "  OVA:      ${OVA}  (${SIZE})"
echo "  Pinned:   ${OVA_GIT_REF}  (upgrades from ${OVA_GIT_URL})"
echo "  Console:  user 'ubuntu' / password '${CONSOLE_PASS}'  (change after first login)"
echo ""
echo "  Import into VirtualBox / VMware / ESXi, power on (NEEDS INTERNET),"
echo "  then browse to https://<appliance-dhcp-ip>/ and complete the wizard."
echo "  First boot BUILDS from source (~10-15 min); watch"
echo "  /var/log/packetarch-firstboot.log on the console if needed."
echo "================================================================"
