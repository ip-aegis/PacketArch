#!/usr/bin/env bash
#
# Audit — and repair — Cyber Vision networks that CV 5.6 registered without an
# asset group, which is what makes the new UI's communications map come up
# empty. See docs/cyber-vision/CV-5.6-Communications-Map-Remediation.md.
#
#   ./scripts/cv-repair-networks.sh                            # read-only report
#   ./scripts/cv-repair-networks.sh --scenario <id|name> --apply
#
# The report is safe to run any time, and is worth re-running after every CV
# upgrade: it is the only check that detects this class of defect. --apply is
# DESTRUCTIVE (it deletes and recreates networks, and the Organization
# Hierarchy is re-applied afterwards) and takes one scenario at a time.
#
# Requires the stack to be running (docker compose up -d) and the Center to
# have CV UI credentials configured under Settings > Cyber Vision — the
# asset-group check needs a UI session, which no API token can obtain.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

if docker info >/dev/null 2>&1; then DC="docker compose"; else DC="sudo docker compose"; fi

# -it so the output streams as each scenario is checked.
exec $DC exec -it backend python -m app.cli.repair_cv_networks "$@"
