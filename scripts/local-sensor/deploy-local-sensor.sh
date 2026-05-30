#!/usr/bin/env bash
#
# deploy-local-sensor.sh — stand up a LOCAL traffic-agent + Cyber Vision sensor
# pair on the PacketArch host, wired through an isolated virtual SPAN segment.
#
# This is the same wiring PacketArch already does in CML (cml_service.build_lab),
# minus the CML lab: the IOSvL2 SPAN switch is replaced by a host veth crossover,
# and the sensor's macvlan parent is forced to the local monitor interface
# instead of the CML node's ens3.
#
#   agent (DEFAULT_INTERFACE=$GEN_IF)  ==veth==>  $MON_IF  <- CV sensor macvlan parent
#
# PREREQUISITES (done once in the Cyber Vision Center UI, exactly as for CML):
#   1. Add a sensor of type "docker", capture mode "all".
#   2. Download the docker-compose.yml CV generates for it (it embeds
#      SERIAL_NUMBER + PROVISIONING_TOKEN and a macvlan network).
#   3. Pass that file here via --sensor-compose. We DON'T mint the token; CV does.
#
# Usage:
#   sudo ./deploy-local-sensor.sh \
#       --server   https://10.10.20.231 \
#       --token    <agent-token-from-PacketArch-UI> \
#       --sensor-compose ./cv-sensor-compose.yml \
#       --insecure
#
# Teardown:
#   sudo ./deploy-local-sensor.sh --down
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEN_IF="${GEN_IF:-pa-gen}"
MON_IF="${MON_IF:-pa-mon}"
SENSOR_DIR="${SENSOR_DIR:-/opt/packetarch-local-sensor}"
AGENT_NAME="${AGENT_NAME:-Local-Agent}"
INSECURE=""

SERVER="" ; TOKEN="" ; SENSOR_COMPOSE="" ; DOWN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server)          SERVER="$2"; shift 2 ;;
    --token)           TOKEN="$2"; shift 2 ;;
    --sensor-compose)  SENSOR_COMPOSE="$2"; shift 2 ;;
    --name)            AGENT_NAME="$2"; shift 2 ;;
    --gen-if)          GEN_IF="$2"; shift 2 ;;
    --mon-if)          MON_IF="$2"; shift 2 ;;
    --insecure|-k)     INSECURE="--insecure"; shift ;;
    --down)            DOWN=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root. Try: sudo $0 $*" >&2
  exit 1
fi

if [[ -n "$DOWN" ]]; then
  echo "[*] tearing down local sensor + agent + SPAN segment"
  if [[ -f "$SENSOR_DIR/docker-compose.yml" ]]; then
    ( cd "$SENSOR_DIR" && docker compose down --remove-orphans 2>/dev/null || true )
  fi
  bash "$HERE/../../backend/app/static/agent/install.sh" --uninstall 2>/dev/null || true
  GEN_IF="$GEN_IF" MON_IF="$MON_IF" bash "$HERE/setup-local-span.sh" down
  echo "[+] done."
  exit 0
fi

[[ -n "$SERVER" ]]          || { echo "--server is required" >&2; exit 2; }
[[ -n "$TOKEN" ]]           || { echo "--token is required (create the agent in the PacketArch UI first)" >&2; exit 2; }
[[ -f "$SENSOR_COMPOSE" ]]  || { echo "--sensor-compose FILE not found: $SENSOR_COMPOSE" >&2; exit 2; }

# 1) isolated virtual SPAN segment ---------------------------------------------
echo "=== 1/3  SPAN segment ==="
GEN_IF="$GEN_IF" MON_IF="$MON_IF" bash "$HERE/setup-local-span.sh" up

# 2) CV sensor: rewrite macvlan parent -> $MON_IF, then bring it up ------------
# Mirrors cml_service._build_cv_sensor_cloud_init():
#   compose = re.sub(r"parent:\s*\S+", "parent: ens3", sensor_compose)
echo "=== 2/3  CV sensor ==="
mkdir -p "$SENSOR_DIR"

# 2a) Trust the CV Center registry on the HOST daemon. Unlike CML (where the
# sensor runs in its own VM with its own cloud-init daemon.json), the local
# sensor shares this host's Docker daemon, so the *host* must trust the
# registry or `pull_policy: always` fails on the self-signed cert.
# `image: <host:port>/sensor` -> registry = the part before the last "/".
REGISTRY="$(grep -oE 'image:[[:space:]]*[^[:space:]]+' "$SENSOR_COMPOSE" | head -1 \
            | sed -E 's/image:[[:space:]]*//' | sed -E 's#/[^/]*$##')"
if [[ -n "$REGISTRY" ]]; then
  echo "[*] ensuring host Docker trusts insecure registry: $REGISTRY"
  REGISTRY="$REGISTRY" python3 - <<'PY'
import json, os
path = "/etc/docker/daemon.json"
reg = os.environ["REGISTRY"]
try:
    with open(path) as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
regs = cfg.get("insecure-registries") or []
if reg not in regs:
    regs.append(reg)
    cfg["insecure-registries"] = regs
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"    added {reg} -> {path}")
else:
    print(f"    {reg} already trusted")
PY
  # Live-reload picks up insecure-registries WITHOUT restarting containers.
  systemctl reload docker 2>/dev/null || kill -HUP "$(pidof dockerd | awk '{print $1}')" 2>/dev/null || true
  sleep 1
fi

sed -E "s/parent:[[:space:]]*[^[:space:]]+/parent: ${MON_IF}/g" \
    "$SENSOR_COMPOSE" > "$SENSOR_DIR/docker-compose.yml"
if grep -q "parent: ${MON_IF}" "$SENSOR_DIR/docker-compose.yml"; then
  echo "[+] forced macvlan capture parent -> ${MON_IF}"
else
  echo "[!] WARNING: no 'parent:' line found in the CV compose — verify the YAML"
  echo "    has a macvlan network. The sensor may not capture without it."
fi
echo "[*] starting CV sensor (it ZTP-enrolls with the Center via its token)"
( cd "$SENSOR_DIR" && docker compose up -d )
echo "[*] sensor container state:"
docker ps --filter name=ccv-sensor --format '    {{.Names}}  {{.Status}}' 2>/dev/null || true

# 3) traffic agent: reuse the single-source-of-truth installer ----------------
# install.sh runs network_mode host, so DEFAULT_INTERFACE=$GEN_IF (a host veth)
# is directly usable for Scapy sendp injection.
echo "=== 3/3  traffic agent ==="
bash "$HERE/../../backend/app/static/agent/install.sh" \
    --server "$SERVER" \
    --token "$TOKEN" \
    --name "$AGENT_NAME" \
    --interface "$GEN_IF" \
    $INSECURE

cat <<EOF

=== local sensor lab is up ===
  agent injects on : $GEN_IF   (DEFAULT_INTERFACE)
  sensor captures  : $MON_IF   (macvlan parent)
  sensor config    : $SENSOR_DIR/docker-compose.yml

Verify the wire:   sudo $HERE/verify-span.sh
Agent logs:        docker compose -f /opt/packetarch-agent/docker-compose.yml logs -f agent
Sensor logs:       docker compose -f $SENSOR_DIR/docker-compose.yml logs -f
Tear down:         sudo $0 --down

Now deploy/run a scenario from PacketArch onto "$AGENT_NAME" and watch the
devices populate in the Cyber Vision Center.
EOF
