#!/bin/bash
#
# PacketArch — Docker build/runtime egress preflight
#
# `docker compose up -d --build` runs network-touching steps in EVERY image
# (poetry/pip, apt-get, npm ci, apk add). Those run inside a BRIDGED build
# sandbox, not on the host stack — so a host with perfectly good internet can
# still fail every build. This script finds out which of the usual causes you
# have, because the popular workaround (build.network: host) fixes all of the
# build-time ones equally and therefore tells you nothing.
#
# Most of them come back at RUNTIME, when the backend reaches out to a Cyber
# Vision Center, a CML server or an AI provider. A build that succeeds is not an
# install that works — and the last check here (embedded DNS) is a cause that
# NEVER shows at build time and produces a green `docker compose ps` on a stack
# where every single API call 502s.
#
# Sections: 0 daemon · 1 MTU · 2 subnet collisions (incl. COMPOSE_SUBNET) ·
#           3 bridged egress · 4 BuildKit sandbox · 5 embedded DNS
#
# Usage:  ./scripts/check-docker-egress.sh [--quick]
#         --quick   skip everything that pulls or runs a container
#                   (sections 3, 4 and 5)
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

# ---- 5. embedded DNS (container-name resolution) ---------------------------
# Section 3 proves a container can resolve the INTERNET. That is a different
# resolver from the one the stack actually depends on. Inside a user-defined
# network, Docker runs an embedded DNS server at 127.0.0.11 that resolves
# SERVICE NAMES — `postgres`, `redis`, `backend`. nginx resolves its upstream
# through it on every request (frontend/nginx.conf `resolver 127.0.0.11`), so
# when this breaks the symptom is not "no internet", it is: the page loads,
# every /api/ call 502s after the resolver timeout, and the login says
# "Backend unreachable". Nothing in `docker compose ps` shows it.
#
# It breaks on hosts where the 127.0.0.11 DNAT loses its conntrack reply path —
# a site/VPN route overlapping the bridge subnet is the cause we have actually
# seen. Note that container-name resolution NEVER works on the default `bridge`
# network, only on user-defined ones, so this probe must not run there.
head_ "Docker embedded DNS (service-name resolution)"
DNS_NET=""; DNS_TARGET=""; DNS_TEMP_NET=""; DNS_PEER=""
if (( QUICK )); then
  skip "--quick: skipped"
else
  # Prefer the REAL stack network if it is up: then we resolve a real service
  # name over the real subnet, which is the path users hit.
  for candidate in "${COMPOSE_PROJECT_NAME:-packetarch}_default" packetarch_default; do
    if $DOCKER network inspect "$candidate" >/dev/null 2>&1; then
      first_id="$($DOCKER network inspect "$candidate" \
                    --format '{{range $k,$v := .Containers}}{{$k}} {{end}}' 2>/dev/null | awk '{print $1}')"
      if [[ -n "$first_id" ]]; then
        DNS_TARGET="$($DOCKER inspect -f '{{index .Config.Labels "com.docker.compose.service"}}' "$first_id" 2>/dev/null)"
        [[ -n "$DNS_TARGET" ]] && { DNS_NET="$candidate"; break; }
      fi
    fi
  done
  if [[ -z "$DNS_NET" ]]; then
    # Stack is down (or not installed yet) — stand up a throwaway user-defined
    # network so this check is useful BEFORE the first `up`, which is exactly
    # when an operator wants it.
    DNS_TEMP_NET="pa-dnsprobe-$$"
    DNS_PEER="pa-dnspeer-$$"
    if $DOCKER network create --subnet "$COMPOSE_SUBNET" "$DNS_TEMP_NET" >/dev/null 2>&1 \
       || $DOCKER network create "$DNS_TEMP_NET" >/dev/null 2>&1; then
      if $DOCKER run -d --name "$DNS_PEER" --network "$DNS_TEMP_NET" \
           "$PROBE_IMAGE" sleep 60 >/dev/null 2>&1; then
        DNS_NET="$DNS_TEMP_NET"; DNS_TARGET="$DNS_PEER"
      fi
    fi
  fi
  cleanup_dns_probe() {
    [[ -n "$DNS_PEER" ]] && $DOCKER rm -f "$DNS_PEER" >/dev/null 2>&1
    [[ -n "$DNS_TEMP_NET" ]] && $DOCKER network rm "$DNS_TEMP_NET" >/dev/null 2>&1
    return 0
  }

  if [[ -z "$DNS_NET" || -z "$DNS_TARGET" ]]; then
    skip "could not set up a user-defined network to probe — re-run after the first build"
    cleanup_dns_probe
  else
    # getent, NOT nslookup. busybox nslookup exits 0 on NXDOMAIN — it prints
    # "server can't find <name>" and still returns success, so an exit-code
    # check on it reports PASS for the exact failure this section exists to
    # catch (confirmed on alpine:3.20). getent hosts returns 2 when the name
    # does not resolve.
    RES_OUT="$($DOCKER run --rm --network "$DNS_NET" "$PROBE_IMAGE" \
                 cat /etc/resolv.conf 2>&1)"
    EDNS_OUT="$($DOCKER run --rm --network "$DNS_NET" "$PROBE_IMAGE" \
                 getent hosts "$DNS_TARGET" 2>&1)"; EDNS_RC=$?
    if (( EDNS_RC == 0 )); then
      ok "\"$DNS_TARGET\" resolves inside $DNS_NET -> ${EDNS_OUT%% *} (embedded DNS working)"
    else
      bad "\"$DNS_TARGET\" does NOT resolve inside $DNS_NET — Docker's embedded DNS is broken on this host"
      echo "          This is the one that presents as a WORKING install: the page loads,"
      echo "          every /api/ call 502s, and the login says \"Backend unreachable\"."
      echo "          nginx re-resolves \"backend\" through 127.0.0.11 on every request."
      echo ""
      echo "          The container's resolver config was:"
      grep -E 'nameserver|ExtServers|Overrides' <<< "$RES_OUT" | sed 's/^/            /'
      echo "          On a user-defined network Docker always writes 127.0.0.11 there"
      echo "          (a daemon.json \"dns\" entry becomes its UPSTREAM, it does not"
      echo "          replace it), so a failure here means the DNAT to the embedded"
      echo "          resolver is losing its reply path — conntrack. The cause we have"
      echo "          actually seen is a site/VPN route overlapping the bridge subnet."
      echo ""
      echo "          fix, in order of preference:"
      echo "               1. move the stack off the routed range:"
      echo "                    echo 'COMPOSE_SUBNET=<free /24>' >> .env"
      echo "                    docker compose down && docker compose up -d"
      echo "               2. move ALL of docker off it (needs root + daemon restart):"
      echo "                    \"default-address-pools\" in /etc/docker/daemon.json"
      echo "               3. confirm nothing is dropping 127.0.0.11 traffic:"
      echo "                    sudo iptables -t nat -S DOCKER_OUTPUT DOCKER_POSTROUTING"
      echo ""
      echo "          Do NOT paper over this with \"extra_hosts\" entries in"
      echo "          docker-compose.yml. They pin container IPs that change on every"
      echo "          recreate, they are a local edit to a TRACKED file (so the"
      echo "          self-upgrade stashes them away), and they cannot help the"
      echo "          frontend at all — nginx resolves through 127.0.0.11, not /etc/hosts."
    fi
    cleanup_dns_probe
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
