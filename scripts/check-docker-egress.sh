#!/bin/bash
#
# PacketArch — Docker build/runtime egress preflight
#
# `docker compose up -d --build` runs network-touching steps in EVERY image
# (poetry/pip, apt-get, npm ci, apk add). Those run inside a BRIDGED build
# sandbox, not on the host stack — so a host with perfectly good internet can
# still fail every build. This script finds out which of the four usual causes
# you have, because the popular workaround (build.network: host) fixes all four
# equally and therefore tells you nothing.
#
# Three of the four come back at RUNTIME, when the backend reaches out to a
# Cyber Vision Center, a CML server or an AI provider. A build that succeeds is
# not an install that works.
#
# Usage:  ./scripts/check-docker-egress.sh [--quick]
#         --quick   skip the real build-sandbox probe (no image pull/build)
#
# Exit:   0 = no problems found       1 = at least one problem found
#         2 = could not run the checks (no docker / daemon unreachable)
#
# Distro-agnostic: the probes are pure docker/network tests; only the suggested
# remedy adapts to whichever firewall manager is actually running.

set -uo pipefail

QUICK=0
[[ "${1:-}" == "--quick" ]] && QUICK=1

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}ok${NC}    $1"; }
bad()  { echo -e "  ${RED}FAIL${NC}  $1"; FOUND=1; }
warn() { echo -e "  ${YELLOW}warn${NC}  $1"; FOUND=1; }
skip() { echo -e "        $1"; }
head_() { echo -e "\n${BOLD}$1${NC}"; }

FOUND=0
PROBE_IMAGE="${PROBE_IMAGE:-alpine:3.20}"
DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="sudo docker"

echo "============================================"
echo "  PacketArch — Docker egress preflight"
echo "============================================"

# ---- 0. daemon reachable ---------------------------------------------------
head_ "Docker daemon"
if ! command -v docker >/dev/null 2>&1; then
  echo -e "  ${RED}FAIL${NC}  docker not installed — see DEPLOY.md 'Fresh Server Setup'"
  exit 2
fi
if ! $DOCKER info >/dev/null 2>&1; then
  echo -e "  ${RED}FAIL${NC}  cannot talk to the Docker daemon (not running, or user not in the docker group)"
  exit 2
fi
ok "$($DOCKER --version)"

# ---- 1. MTU mismatch -------------------------------------------------------
# Signature is HANGS, not errors: DNS resolves, small requests work, `npm ci`
# or `pip install` stalls mid-download. Happens behind VPNs/tunnels/some clouds
# where the uplink is 1450-ish but docker0 still advertises 1500.
head_ "MTU (docker bridge vs uplink)"
UPLINK="$(ip -4 route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1); exit}')"
BR_MTU="$(ip -o link show docker0 2>/dev/null | grep -o 'mtu [0-9]*' | awk '{print $2}')"
UP_MTU=""
[[ -n "$UPLINK" ]] && UP_MTU="$(ip -o link show "$UPLINK" 2>/dev/null | grep -o 'mtu [0-9]*' | awk '{print $2}')"
if [[ -z "$BR_MTU" ]]; then
  skip "docker0 not present yet (no containers built) — re-run after the first build"
elif [[ -z "$UP_MTU" ]]; then
  skip "no default route found; cannot compare MTU"
elif (( BR_MTU > UP_MTU )); then
  bad "docker0 MTU $BR_MTU > uplink $UPLINK MTU $UP_MTU — large downloads will HANG mid-transfer"
  echo "          fix: add  \"mtu\": $UP_MTU  to /etc/docker/daemon.json, then restart docker"
else
  ok "docker0 $BR_MTU <= $UPLINK $UP_MTU"
fi

# ---- 2. subnet collisions --------------------------------------------------
# Docker's default-address-pools are 172.17-172.31.0.0/16 + 192.168.0.0/16.
# PacketArch additionally carves local-lab /24s out of 172.16.0.0/16
# (hostops._LAB_SUBNET_BLOCK). If the SITE already routes those, containers
# will reach the wrong place, or labs will starve for free /24s.
head_ "Subnet collisions (docker pools vs site routes)"
mapfile -t HOST_ROUTES < <(ip -4 route show 2>/dev/null | awk '$1 ~ /\// {print $1}' | grep -v '^169\.254')
# The stack's own bridge subnet is PINNED via COMPOSE_SUBNET (docker-compose.yml
# `networks.default.ipam`), so check the value this install will actually use —
# not just docker's pools. A pinned subnet that the site routes fails in exactly
# the same way as an unpinned one, and silently, because the pin looks deliberate.
COMPOSE_SUBNET="${COMPOSE_SUBNET:-}"
if [[ -z "$COMPOSE_SUBNET" ]]; then
  for envf in "$(dirname "${BASH_SOURCE[0]}")/../.env" "$(dirname "${BASH_SOURCE[0]}")/.env" ./.env; do
    if [[ -f "$envf" ]]; then
      COMPOSE_SUBNET="$(grep -E '^COMPOSE_SUBNET=' "$envf" | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
      [[ -n "$COMPOSE_SUBNET" ]] && break
    fi
  done
fi
COMPOSE_SUBNET="${COMPOSE_SUBNET:-10.200.0.0/24}"   # docker-compose.yml default
# python emits "<route>|<pool label>|<overlapping pools>" per hit
COLLIDE="$(COMPOSE_SUBNET="$COMPOSE_SUBNET" python3 - "${HOST_ROUTES[@]}" <<'PY' 2>/dev/null
import ipaddress, os, sys
pools = {
    "docker default-address-pools": [ipaddress.ip_network(f"172.{n}.0.0/16") for n in range(17, 32)]
                                    + [ipaddress.ip_network("192.168.0.0/16")],
    "PacketArch local-lab block":   [ipaddress.ip_network("172.16.0.0/16")],
}
try:
    pools["PacketArch stack network (COMPOSE_SUBNET)"] = [
        ipaddress.ip_network(os.environ["COMPOSE_SUBNET"], strict=False)]
except (KeyError, ValueError):
    pass
hits = set()
for arg in sys.argv[1:]:
    try:
        route = ipaddress.ip_network(arg, strict=False)
    except ValueError:
        continue
    if route.version != 4 or route.prefixlen == 0:
        continue
    for label, nets in pools.items():
        overlap = [str(n) for n in nets if route.overlaps(n)]
        if overlap:
            hits.add(f"{route}|{label}|{', '.join(overlap)}")
print("\n".join(sorted(hits)))
PY
)"
# A docker-owned route overlapping docker's own pool is expected; only a route
# on a NON-docker interface means the site itself claims that space.
while IFS='|' read -r net label overlap; do
  [[ -z "$net" ]] && continue
  dev="$(ip -4 route show "$net" 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1); exit}')"
  case "$dev" in
    docker0|br-*|veth*|pa-*) continue ;;
  esac
  warn "$label: site route $net (dev ${dev:-?}) overlaps $overlap"
  COLLIDED=1
done <<< "$COLLIDE"
if [[ -n "${COLLIDED:-}" ]]; then
  echo "          Two fixes, at two levels — apply the one that matches the hit above:"
  echo ""
  echo "          COMPOSE-LEVEL (this stack only; no daemon restart, no root):"
  echo "               echo 'COMPOSE_SUBNET=<free /24>' >> .env"
  echo "               docker compose down && docker compose up -d"
  echo "          (currently: ${COMPOSE_SUBNET}. A subnet change needs the network"
  echo "           recreated, so 'up -d' alone is not enough. scripts/upgrade.sh"
  echo "           does the down/up for you when the value changes.)"
  echo ""
  echo "          HOST-LEVEL (every compose project and every local sensor lab):"
  echo "               set \"default-address-pools\" in /etc/docker/daemon.json to a"
  echo "               range your site does not route, then restart docker"
  echo ""
  echo "          A VPN'd corporate laptop usually routes 172.16.0.0/12, which covers"
  echo "          most of docker's pools. Symptom if you skip this: the stack comes up,"
  echo "          'curl' INSIDE the frontend returns 200, and the host still gets a TCP"
  echo "          reset on 443 — plus 'backend' can stop resolving, so every /api/ call"
  echo "          502s and the UI says \"Backend unreachable\"."
else
  ok "no site route overlaps docker's pools, the local-lab block, or ${COMPOSE_SUBNET}"
fi

# ---- 3. bridged container egress (DNS / L3+TLS) ----------------------------
# This is the layer that differs from the host. The daemon pulls images over
# the HOST stack, so pulls can succeed while every build step fails.
head_ "Bridged container egress"
if (( QUICK )); then
  skip "--quick: skipped"
elif ! $DOCKER image inspect "$PROBE_IMAGE" >/dev/null 2>&1 && ! $DOCKER pull -q "$PROBE_IMAGE" >/dev/null 2>&1; then
  bad "cannot pull probe image $PROBE_IMAGE — the DAEMON itself has no egress (host-level: proxy, DNS or offline)"
  echo "          note: this is a host problem; build.network: host will NOT help"
else
  DNS_OUT="$($DOCKER run --rm "$PROBE_IMAGE" nslookup pypi.org 2>&1)";       DNS_RC=$?
  TCP_OUT="$($DOCKER run --rm "$PROBE_IMAGE" \
              wget -q -T 8 --spider https://1.1.1.1/ 2>&1)";                 TCP_RC=$?
  if (( DNS_RC == 0 )); then ok "DNS resolves inside a bridged container"
  else
    bad "DNS fails inside a bridged container (host resolves fine)"
    echo "          cause: the host resolver is a systemd-resolved stub (127.0.0.53),"
    echo "                 which a bridged container cannot reach, and the 8.8.8.8"
    echo "                 fallback is blocked."
    echo "          fix: add  \"dns\": [\"<your resolver>\"]  to /etc/docker/daemon.json"
  fi
  if (( TCP_RC == 0 )); then ok "TCP+TLS out of a bridged container"
  else
    bad "no TCP/TLS egress from a bridged container (DNS-independent probe to 1.1.1.1)"
    echo "          cause: the bridge's FORWARD traffic is being dropped."
    # remedy adapts to whatever is actually managing the firewall
    if systemctl is-active --quiet firewalld 2>/dev/null; then
      echo "          firewalld is ACTIVE — zones: $(firewall-cmd --get-active-zones 2>/dev/null | tr '\n' ' ')"
      echo "          fix: put the bridge in the docker zone and enable masquerade:"
      echo "               sudo firewall-cmd --permanent --zone=docker --add-interface=docker0"
      echo "               sudo firewall-cmd --permanent --zone=public --add-masquerade"
      echo "               sudo firewall-cmd --reload && sudo systemctl restart docker"
    elif command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "^Status: active"; then
      echo "          ufw is active — note ufw does NOT normally block docker (docker"
      echo "          inserts ahead of it in FORWARD). Check DEFAULT_FORWARD_POLICY in"
      echo "          /etc/default/ufw and any DOCKER-USER rules:"
      echo "               sudo iptables -S DOCKER-USER"
    else
      echo "          fix: check the FORWARD chain / DOCKER-USER for drops:"
      echo "               sudo iptables -S FORWARD | head; sudo nft list ruleset | grep -i docker"
    fi
  fi
fi

# ---- 4. the real build sandbox ---------------------------------------------
# BuildKit's sandbox is not identical to `docker run`; this is the faithful test
# of what `docker compose up --build` will actually do.
head_ "BuildKit build sandbox"
if (( QUICK )); then
  skip "--quick: skipped"
else
  TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT
  printf 'FROM %s\nRUN wget -q -T 10 -O /dev/null https://pypi.org/simple/pip/\n' "$PROBE_IMAGE" > "$TMPD/Dockerfile"
  if $DOCKER build -q --no-cache "$TMPD" >/dev/null 2>&1; then
    ok "a build step can reach the network — compose builds will work"
  else
    bad "a build step CANNOT reach the network — 'docker compose up -d --build' will fail"
    echo "          Fix the cause flagged above. If you must ship before you can fix the"
    echo "          host, the supported escape hatch is an .env line (NOT a compose edit):"
    echo ""
    echo "               echo 'DOCKER_BUILD_NETWORK=host' >> .env"
    echo ""
    echo "          Every build stanza honours it. Editing docker-compose.yml by hand"
    echo "          instead will be stashed away by the self-upgrade and the next"
    echo "          upgrade will fail on this host."
  fi
fi

echo ""
if (( FOUND )); then
  echo -e "${YELLOW}Problems found — see the fixes above.${NC}"
  echo "Three of the four causes also break RUNTIME egress (Cyber Vision, CML, AI"
  echo "providers), so prefer the daemon.json fix over DOCKER_BUILD_NETWORK=host."
  exit 1
fi
echo -e "${GREEN}No egress problems found.${NC}"
exit 0
