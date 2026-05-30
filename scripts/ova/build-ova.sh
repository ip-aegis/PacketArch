#!/usr/bin/env bash
# Build a distributable PacketArch appliance OVA.
#
# Pipeline:
#   offline bundle (scripts/build-release.sh)  ──┐
#   Ubuntu 24.04 cloud image  ───────────────────┤
#                                                 ▼
#   virt-customize: install Docker, bake bundle + images, install the
#   one-shot first-boot unit, scrub machine identity
#                                                 ▼
#   qemu-img convert -> stream-optimized VMDK
#                                                 ▼
#   render OVF (broad-compat) + .mf manifest -> tar -> .ova
#
# The appliance does NOT generate secrets or start the stack at build
# time. On first power-on, packetarch-firstboot.service runs the bundle's
# install.sh, which mints fresh secrets, a fresh self-signed cert, and
# brings the stack up on https://<dhcp-ip>/ at the setup wizard.
#
# Usage (from repo root):
#   sudo ./scripts/ova/build-ova.sh
#
# Env overrides:
#   VERSION=1.4.2          Version string (default: app_version from config.py)
#   BUNDLE_TARBALL=path    Use an existing offline tarball instead of building
#   DISK_SIZE=60G          Virtual disk size (thin; OVA only stores used blocks)
#   VM_CPUS=4 VM_MEM=8192  Default OVF CPU / memory (MB)
#   CONSOLE_PASS=...       Console password for the 'ubuntu' user (default: packetarch)
#   UBUNTU_IMG_URL=...     Override the cloud image source
#   OUT_DIR=/some/path     Output dir (default: dist/)
#   KEEP_WORK=1            Keep the intermediate qcow2/vmdk for debugging

set -euo pipefail

cd "$(dirname "$0")/../.."
REPO_ROOT="$(pwd)"
OVA_DIR="${REPO_ROOT}/scripts/ova"

VERSION="${VERSION:-$(grep -E '^\s*app_version' backend/app/core/config.py \
    | head -1 | sed 's/.*= *"\([^"]*\)".*/\1/')}"
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
command -v curl           >/dev/null || MISSING+=("curl")
if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "ERROR: missing tools:" >&2
    printf '  - %s\n' "${MISSING[@]}" >&2
    echo "" >&2
    echo "Fedora:  sudo dnf install guestfs-tools qemu-img curl" >&2
    echo "Ubuntu:  sudo apt-get install libguestfs-tools qemu-utils curl" >&2
    exit 1
fi

mkdir -p "${OUT_DIR}" "${CACHE_DIR}" "${WORK}"

# Use the direct (appliance) backend for ALL libguestfs tools below
# (virt-filesystems, virt-resize, virt-customize). The default libvirt
# backend needs a running virtqemud socket, which a plain root shell
# doesn't have.
export LIBGUESTFS_BACKEND=direct

# --- 1. offline bundle --------------------------------------------------
log "[1/7] Locating offline bundle"
if [[ -n "${BUNDLE_TARBALL:-}" ]]; then
    [[ -f "${BUNDLE_TARBALL}" ]] || die "BUNDLE_TARBALL not found: ${BUNDLE_TARBALL}"
    TARBALL="${BUNDLE_TARBALL}"
else
    TARBALL="${OUT_DIR}/packetarch-${VERSION}-offline.tar.gz"
    if [[ ! -f "${TARBALL}" ]]; then
        echo "  no bundle at ${TARBALL} — building it (full variant)..."
        "${REPO_ROOT}/scripts/build-release.sh"
    fi
fi
echo "  using bundle: ${TARBALL}"

BUNDLE_STAGE="${WORK}/bundle"
rm -rf "${BUNDLE_STAGE}"
mkdir -p "${BUNDLE_STAGE}"
# The tarball contains a single top-level dir; flatten it into bundle/.
tar -xzf "${TARBALL}" -C "${BUNDLE_STAGE}" --strip-components=1
[[ -x "${BUNDLE_STAGE}/install.sh" ]] || die "bundle missing install.sh — bad tarball?"

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
# filesystem stays at the cloud image's ~2GB, and build-time apt + the
# baked ~1GB bundle overflow it ("No space left on device"). virt-resize
# grows the partition AND the filesystem into the larger target disk.
# --long already reports Size in bytes; pick the largest partition as root.
ROOT_PART="${ROOT_PART:-$(virt-filesystems -a "${BASE_IMG}" --partitions --long 2>/dev/null \
    | awk 'NR>1 {print $4, $1}' | sort -n | tail -1 | awk '{print $2}')}"
[[ -n "${ROOT_PART}" ]] || die "could not detect root partition in ${BASE_IMG} (set ROOT_PART=/dev/sdaN)"
echo "  root partition: ${ROOT_PART}"
rm -f "${QCOW}"
qemu-img create -f qcow2 "${QCOW}" "${DISK_SIZE}" >/dev/null
virt-resize --expand "${ROOT_PART}" "${BASE_IMG}" "${QCOW}"

# --- 3. customize -------------------------------------------------------
log "[3/7] Customizing image (Docker + bundle + first-boot unit)"
virt-customize -a "${QCOW}" --network \
    --install qemu-guest-agent,ca-certificates,curl,docker.io,docker-compose-v2 \
    --run-command 'systemctl enable docker' \
    --run-command 'systemctl enable qemu-guest-agent || true' \
    --mkdir /opt/packetarch \
    --copy-in "${BUNDLE_STAGE}:/opt/packetarch" \
    --copy-in "${OVA_DIR}/firstboot.sh:/opt/packetarch" \
    --copy-in "${OVA_DIR}/packetarch-firstboot.service:/etc/systemd/system" \
    --run-command 'chmod +x /opt/packetarch/firstboot.sh /opt/packetarch/bundle/install.sh' \
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
echo "  OVA:     ${OVA}  (${SIZE})"
echo "  Console: user 'ubuntu' / password '${CONSOLE_PASS}'  (change after first login)"
echo ""
echo "  Import into VirtualBox / VMware / ESXi, power on, then browse to"
echo "  https://<appliance-dhcp-ip>/ and complete the setup wizard."
echo "  First boot loads images + starts the stack (~2-4 min); watch"
echo "  /var/log/packetarch-firstboot.log on the console if needed."
echo "================================================================"
