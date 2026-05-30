#!/usr/bin/env bash
# PacketArch appliance first-boot initializer.
#
# Baked into the OVA and run ONCE by packetarch-firstboot.service the first
# time the appliance powers on. It defers all per-VM state to boot time so
# every cloned/deployed appliance gets its OWN fresh secrets and its OWN
# self-signed TLS cert (instead of baking those into the shared image).
#
# All the real work — docker-load the baked images, generate .env with
# fresh secrets, `docker compose up`, wait for healthy — lives in the
# offline bundle's install.sh. We just invoke it. This keeps a single
# source of truth for "stand up the stack" shared with manual installs.
#
# The systemd unit guards re-runs with ConditionPathExists=!/opt/packetarch/.env,
# so once install.sh has written .env this never fires again.

set -euo pipefail

INSTALL_DIR="/opt/packetarch"
BUNDLE_DIR="${INSTALL_DIR}/bundle"
LOG="/var/log/packetarch-firstboot.log"

# Tee everything to a log the operator can inspect from the console.
exec > >(tee -a "${LOG}") 2>&1

echo "================================================================"
echo "  PacketArch first-boot init  ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
echo "================================================================"

if [[ ! -x "${BUNDLE_DIR}/install.sh" ]]; then
    echo "FATAL: ${BUNDLE_DIR}/install.sh missing or not executable." >&2
    echo "       The OVA was built incorrectly. See scripts/ova/README.md." >&2
    exit 1
fi

# Wait for the Docker daemon (the unit orders us After=docker.service, but
# socket readiness can still lag a beat on a cold VM).
for i in $(seq 1 30); do
    if docker info >/dev/null 2>&1; then break; fi
    echo "  waiting for docker daemon... (${i}/30)"
    sleep 2
done

# Hand off to the canonical installer. It stages compose/init-db into
# INSTALL_DIR, loads images from ${BUNDLE_DIR}/images, generates .env with
# fresh openssl secrets (no ADMIN_PASSWORD -> wizard path), and brings the
# stack up. The frontend container mints the self-signed cert on first
# start, so the appliance lands on the setup wizard at https://<ip>/.
"${BUNDLE_DIR}/install.sh" --install-dir "${INSTALL_DIR}"

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo ""
echo "================================================================"
echo "  PacketArch appliance is up."
echo "  Open https://${IP:-<this-host-ip>}/  (accept the self-signed cert)"
echo "  and complete the first-run setup wizard to create the admin user."
echo "================================================================"
