#!/usr/bin/env bash
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
#
# Collect one redacted file that answers "why is this install not working".
#
# Why this exists: supporting a remote install meant sending the operator a
# log-dump one-liner, and the one-liner assumed the OVA/bundle layout
# (/opt/packetarch, /var/log/packetarch-firstboot.log). The install was a git
# clone in ~/packetarch, so every path missed and the reply was "nothing
# there". Two weeks of back-and-forth followed. This script finds its own
# install, collects the same evidence from whichever layout it is in, and never
# asks the operator to know which one that is.
#
# It is READ-ONLY. It starts nothing, restarts nothing and changes no state.
#
# Usage:
#   ./scripts/collect-diagnostics.sh              # writes ./packetarch-diag-<utc>.txt
#   ./scripts/collect-diagnostics.sh -o FILE      # write somewhere specific
#   ./scripts/collect-diagnostics.sh --stdout     # print instead of writing
#
# Send the resulting file. Secret VALUES from .env are replaced with
# <redacted:KEY> everywhere in the output, including inside container logs, and
# .env itself is reported as key names only.

set -uo pipefail

# ---- locate the install ----------------------------------------------------
# Works from both layouts this ships in: the repo (scripts/<here>, compose one
# level up) and the offline bundle, which stages helper scripts FLAT beside
# docker-compose.yml. Find the compose file rather than assuming either shape,
# and never assume /opt/packetarch or ~/packetarch.
INVOKED_FROM="$(pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR=""
for cand in "$SCRIPT_DIR" "$SCRIPT_DIR/.." "$INVOKED_FROM" "$INVOKED_FROM/.."; do
  if [[ -f "$cand/docker-compose.yml" ]]; then REPO_DIR="$(cd "$cand" && pwd)"; break; fi
done
if [[ -z "$REPO_DIR" ]]; then
  echo "could not locate docker-compose.yml near ${SCRIPT_DIR} or ${INVOKED_FROM}" >&2
  echo "run this from inside a PacketArch install (git clone, bundle or appliance)" >&2
  exit 1
fi

OUT=""; TO_STDOUT=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output) OUT="${2:-}"; shift 2 ;;
    --stdout)    TO_STDOUT=1; shift ;;
    -h|--help)   sed -n '6,27p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)           echo "unknown arg: $1 (try --help)" >&2; exit 1 ;;
  esac
done
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
[[ -n "$OUT" ]] || OUT="${INVOKED_FROM}/packetarch-diag-${STAMP}.txt"

DC="docker compose"
docker info >/dev/null 2>&1 || DC="sudo docker compose"
DK="${DC% compose}"          # "docker" or "sudo docker"
AM_ROOT=0; [[ "$(id -u)" -eq 0 ]] && AM_ROOT=1

cd "$REPO_DIR"

# ---- redaction -------------------------------------------------------------
# Build a sed program that replaces every secret VALUE in .env with
# <redacted:KEY>. Applied to the WHOLE report, so a password that a container
# logged inside a DSN or a traceback is scrubbed too — not just the .env dump.
SED_PROG=""
SECRET_KEYS='POSTGRES_PASSWORD|SECRET_KEY|ENCRYPTION_KEY|ADMIN_PASSWORD|ANTHROPIC_API_KEY|CIRCUIT_CLIENT_SECRET|CIRCUIT_CLIENT_ID|CIRCUIT_APP_KEY|WEBEX_BOT_TOKEN|.*_TOKEN|.*_PASSWORD|.*_SECRET|.*_API_KEY'
if [[ -f .env ]]; then
  while IFS='=' read -r k v; do
    [[ -z "${k:-}" || "$k" == \#* ]] && continue
    [[ "$k" =~ ^($SECRET_KEYS)$ ]] || continue
    v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
    # Skip empties and values too short to be a meaningful secret (a 1-2 char
    # value would scrub half the report).
    (( ${#v} >= 6 )) || continue
    esc="$(printf '%s' "$v" | sed -e 's/[]\/$*.^[]/\\&/g')"
    SED_PROG="${SED_PROG}s/${esc}/<redacted:${k}>/g;"
  done < <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env 2>/dev/null)
fi
redact() { if [[ -n "$SED_PROG" ]]; then sed -e "$SED_PROG"; else cat; fi; }

# ---- report helpers --------------------------------------------------------
sec()  { printf '\n==================== %s ====================\n' "$1"; }
sub()  { printf '\n--- %s ---\n' "$1"; }
# run CMD..., labelled, never fatal, with a visible note when it is unavailable
try()  { sub "$*"; if "$@" 2>&1; then :; else echo "  (command failed or unavailable: exit $?)"; fi; }

report() {
cat <<HEADER
PacketArch diagnostics
generated : ${STAMP} (UTC)
install    : ${REPO_DIR}
invoked in : ${INVOKED_FROM}
user       : $(id -un) (uid $(id -u))$( ((AM_ROOT)) || echo "  [not root — iptables/nft sections are skipped]")
host       : $(uname -a)
HEADER

sec "INSTALL PATH AND VERSION"
if [[ -d .git ]]; then
  echo "layout     : git clone (self-upgradeable)"
  try git describe --tags --always --dirty
  try git rev-parse HEAD
  try git status --porcelain --untracked-files=no
  echo ""
  echo "local changes to TRACKED files above are the ones scripts/upgrade.sh"
  echo "stashes on upgrade — an extra_hosts or build.network hand-edit shows here."
elif [[ -f VERSION ]]; then
  echo "layout     : offline bundle / appliance"
  sub "VERSION"; cat VERSION
else
  echo "layout     : unknown (no .git, no VERSION)"
fi
sub "app_version in the shipped code"
grep -h 'app_version' backend/app/core/config.py 2>/dev/null || echo "  (backend source not present — image-only install)"

sec "CONFIGURATION (.env — KEY NAMES ONLY)"
if [[ -f .env ]]; then
  echo "keys present in ${REPO_DIR}/.env:"
  grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' .env | tr -d '=' | sed 's/^/  /'
  echo ""
  echo "non-secret values that matter for networking:"
  for k in COMPOSE_SUBNET COMPOSE_PROJECT_NAME DOCKER_BUILD_NETWORK DOCKER_GID HOST_INSTALL_DIR DEBUG \
           AI_ENABLED LIVE_TRAFFIC_ENABLED MIMIC_ENABLED MULTI_SENSOR_TOPOLOGY_ENABLED; do
    v="$(grep -E "^${k}=" .env | head -1 | cut -d= -f2-)"
    printf '  %-32s %s\n' "$k" "${v:-<unset>}"
  done
  echo ""
  echo "(COMPOSE_SUBNET unset means the compose default is in force —"
  echo " see networks.default.ipam in docker-compose.yml.)"
else
  echo "NO .env IN ${REPO_DIR} — compose will refuse to start (POSTGRES_PASSWORD is required)."
fi

sec "CONTAINER STATE"
try $DC ps -a
sub "restart counts (a high number is a crashloop, however the status reads)"
PROJ="$($DC config --format json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("name",""))' 2>/dev/null)"
$DK ps -a --filter "label=com.docker.compose.project=${PROJ:-packetarch}" \
     --format '{{.Names}}' 2>/dev/null | while read -r c; do
  printf '  %-40s restarts=%s  status=%s\n' "$c" \
    "$($DK inspect -f '{{.RestartCount}}' "$c" 2>/dev/null)" \
    "$($DK inspect -f '{{.State.Status}}{{if .State.Health}} ({{.State.Health.Status}}){{end}}' "$c" 2>/dev/null)"
done
sub "healthcheck definitions — read these before believing a green check"
for s in $($DC config --services 2>/dev/null); do
  hc="$($DC config --format json 2>/dev/null | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
t=((d.get('services') or {}).get('$s') or {}).get('healthcheck') or {}
print(' '.join(t.get('test') or []) or 'NONE DEFINED (status will be blank)')
" 2>/dev/null)"
  printf '  %-20s %s\n' "$s" "${hc:-?}"
done

sec "REACHABILITY — THE PATH A USER ACTUALLY TAKES"
sub "host -> https://localhost/health  (nginx, then its backend upstream)"
code="$(curl -sk -o /dev/null -m 10 -w '%{http_code}' https://localhost/health 2>&1)"
echo "  HTTP ${code}"
case "$code" in
  200) echo "  ok — nginx is up AND resolved+reached the backend" ;;
  502|504) echo "  nginx is up but cannot reach 'backend'. This is the DNS/subnet failure:"
           echo "  see the DNS section below and 'When the host's network overlaps Docker's'"
           echo "  in DEPLOY.md. The UI shows this as \"Backend unreachable\"." ;;
  000) echo "  nothing answered on 443 from the host. If 'curl' INSIDE the frontend"
       echo "  container (below) returns 200, the container is fine and the HOST cannot"
       echo "  reach it — a subnet collision with a site/VPN route." ;;
  503) echo "  setup not complete (expected on a fresh install before the wizard)" ;;
esac
sub "host -> http://localhost/  (should 301 to https)"
echo "  HTTP $(curl -s -o /dev/null -m 10 -w '%{http_code}' http://localhost/ 2>&1)"
sub "in-container: frontend -> https://localhost/health"
$DC exec -T frontend sh -c 'curl -sk -o /dev/null -m 10 -w "  HTTP %{http_code}\n" https://localhost/health' 2>&1 \
  || echo "  (could not exec into frontend)"
sub "in-container: frontend -> http://backend:8001/health  (the proxied hop)"
$DC exec -T frontend sh -c 'curl -s -o /dev/null -m 10 -w "  HTTP %{http_code}\n" http://backend:8001/health' 2>&1 \
  || echo "  (could not exec into frontend)"
sub "in-container: backend -> http://localhost:8001/health"
$DC exec -T backend sh -c 'curl -s -o /dev/null -m 10 -w "  HTTP %{http_code}\n" http://localhost:8001/health' 2>&1 \
  || echo "  (could not exec into backend)"

sec "DOCKER EMBEDDED DNS (127.0.0.11)"
echo "nginx re-resolves its upstream through this on every request"
echo "(frontend/nginx.conf: resolver 127.0.0.11). When it breaks, the page"
echo "loads and every /api/ call 502s."
echo ""
echo "NOTE: getent is used, not nslookup — busybox nslookup exits 0 on NXDOMAIN."
for pair in "backend:postgres" "backend:redis" "frontend:backend"; do
  from="${pair%%:*}"; name="${pair##*:}"
  sub "${from} resolves '${name}'"
  $DC exec -T "$from" getent hosts "$name" 2>&1 | sed 's/^/  /' \
    || echo "  FAILED TO RESOLVE (or could not exec into ${from})"
done
sub "resolver config inside the backend container"
$DC exec -T backend cat /etc/resolv.conf 2>&1 | sed 's/^/  /' || echo "  (could not exec)"
sub "network ALIASES per container (this is what makes a service name resolve)"
echo "  A container with an empty alias list is unreachable BY NAME even though"
echo "  it is attached, running and healthy. Docker reattaches a container to a"
echo "  recreated network WITHOUT restoring its compose aliases, so this is the"
echo "  state a bare 'docker compose up -d' leaves behind after a COMPOSE_SUBNET"
echo "  change: correct subnet, everything attached, and no name resolution."
echo "  Fix: docker compose down && docker compose up -d  (recreates them)."
echo ""
$DK ps --filter "label=com.docker.compose.project=${PROJ:-packetarch}" \
     --format '{{.Names}}' 2>/dev/null | while read -r c; do
  al="$($DK inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$v.Aliases}}{{end}}' "$c" 2>/dev/null)"
  mode="$($DK inspect -f '{{.HostConfig.NetworkMode}}' "$c" 2>/dev/null)"
  flag=""
  case "$al" in
    ""|"[]") [[ "$mode" == "host" ]] || flag="   <-- NO ALIASES: not resolvable by name" ;;
  esac
  printf '  %-30s mode=%-10s aliases=%s%s\n' "$c" "$mode" "${al:-[]}" "$flag"
done

sec "DOCKER NETWORKS"
NET="$($DC config --format json 2>/dev/null | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
n=(d.get('networks') or {}).get('default') or {}
print(n.get('name') or (str(d.get('name') or '')+'_default'))
" 2>/dev/null)"
echo "compose network: ${NET:-<could not determine>}"
sub "declared subnet (docker-compose.yml + .env)"
$DC config --format json 2>/dev/null | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
c=(((d.get('networks') or {}).get('default') or {}).get('ipam') or {}).get('config') or []
print('  ' + (c[0].get('subnet','<none>') if c else '<none declared — docker picks from its pools>'))
" 2>/dev/null
sub "live subnet + attached containers"
if [[ -n "$NET" ]]; then
  $DK network inspect "$NET" --format 'subnet : {{range .IPAM.Config}}{{.Subnet}} {{end}}
gateway: {{range .IPAM.Config}}{{.Gateway}} {{end}}
driver : {{.Driver}}
attached:{{range .Containers}}
  {{.Name}} {{.IPv4Address}}{{end}}' 2>&1 | sed 's/^/  /'
  echo ""
  echo "  A live subnet that differs from the declared one means the network"
  echo "  predates the pin and still needs recreating:"
  echo "    docker compose down && docker compose up -d"
  echo "  A container attached here that is NOT part of this compose project will"
  echo "  make that recreate fail with \"has active endpoints\"."
else
  echo "  (network not determined)"
fi
try $DK network ls

sec "HOST NETWORKING"
try ip -4 route show
try ip -4 rule show
try ip -4 addr show
sub "listeners on 80 / 443"
if command -v ss >/dev/null 2>&1; then
  ss -lntp 2>/dev/null | awk 'NR==1 || /:80 |:443 /' || echo "  (ss produced nothing)"
else
  echo "  (ss not installed)"
fi
sub "MTU (a VPN uplink below the bridge MTU makes downloads HANG, not fail)"
up="$(ip -4 route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1); exit}')"
for i in docker0 ${up:-}; do
  echo "  $i: $(ip -o link show "$i" 2>/dev/null | grep -o 'mtu [0-9]*' || echo '?')"
done
if (( AM_ROOT )); then
  sub "iptables nat — DOCKER chains"
  iptables -t nat -S 2>/dev/null | grep -E '^-A (DOCKER|PREROUTING|POSTROUTING|OUTPUT)' | head -60 \
    || echo "  (no iptables nat rules readable)"
  sub "iptables nat — 127.0.0.11 (embedded DNS DNAT)"
  iptables -t nat -S 2>/dev/null | grep '127.0.0.11' | head -20 || echo "  (none found)"
else
  sub "iptables"
  echo "  skipped — re-run with sudo to include the NAT rules"
fi

sec "PREFLIGHT (read-only re-run of check-docker-egress.sh --quick)"
if [[ -x "${SCRIPT_DIR}/check-docker-egress.sh" ]]; then
  "${SCRIPT_DIR}/check-docker-egress.sh" --quick 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
else
  echo "  check-docker-egress.sh not found beside this script"
fi

sec "LOGS (last 300 lines per service)"
for s in $($DC config --services 2>/dev/null); do
  sub "logs: ${s}"
  $DC logs --tail 300 --no-color "$s" 2>&1 || echo "  (no logs for ${s})"
done

sec "APPLIANCE FIRST-BOOT (only if this is an OVA install)"
found=0
for f in /var/log/packetarch-firstboot.log "${REPO_DIR}/.firstboot-done" /opt/packetarch/.firstboot-done; do
  if [[ -e "$f" ]]; then
    found=1
    sub "$f"
    if [[ -f "$f" && -s "$f" ]]; then tail -200 "$f" 2>&1; else ls -l "$f" 2>&1; fi
  fi
done
(( found )) || echo "  none present — this is not an appliance install (nothing is wrong)"

sec "END"
echo "Everything above is redacted for the secret values in .env."
echo "Send this file. If you were asked for something specific and it is not"
echo "here, say which section was empty rather than re-running blind."
}

if (( TO_STDOUT )); then
  report 2>&1 | redact
else
  report 2>&1 | redact > "$OUT"
  chmod 600 "$OUT" 2>/dev/null || true
  echo "Wrote $OUT"
  echo ""
  echo "  install detected : ${REPO_DIR}"
  echo "  size             : $(wc -c < "$OUT") bytes, $(wc -l < "$OUT") lines"
  echo "  redaction        : secret values from .env replaced with <redacted:KEY>"
  echo ""
  echo "Send that file. Skim it first if you like — it is plain text."
fi
