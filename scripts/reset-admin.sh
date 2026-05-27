#!/usr/bin/env bash
#
# Reset (or create) a local PacketArch admin password — recovery for when the
# admin password is lost (no DB surgery, no wizard reset). Runs the management
# command inside the running backend container and prompts securely for the
# password (so it never lands in shell history or the process list).
#
#   ./scripts/reset-admin.sh                 # resets "admin"
#   ./scripts/reset-admin.sh --username bob  # resets/creates "bob" as admin
#
# Requires the stack to be running (docker compose up -d).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

if docker info >/dev/null 2>&1; then DC="docker compose"; else DC="sudo docker compose"; fi

# -it gives the management command a TTY so getpass can prompt for the password.
exec $DC exec -it backend python -m app.cli.reset_admin "$@"
