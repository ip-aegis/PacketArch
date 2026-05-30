#!/usr/bin/env bash
#
# setup-local-span.sh — create an isolated virtual SPAN segment on the
# PacketArch host so a locally-deployed Cyber Vision sensor can monitor the
# locally-deployed traffic-generation agent.
#
# This is the host-side equivalent of the CML topology in
# backend/app/services/cml_service.py:
#
#   CML:    agent ens3 -> IOSvL2 Gi0/0 --(monitor session 1)--> Gi0/1 -> sensor ens3
#   LOCAL:  agent injects on $GEN_IF ==(veth crossover)== $MON_IF <- sensor macvlan parent
#
# A veth pair is a virtual crossover cable: every frame the agent sends out
# $GEN_IF arrives on $MON_IF regardless of src/dst MAC, so it carries an
# arbitrary number of simulated devices in one segment. The sensor is passive
# (never transmits), the agent fabricates both sides of every conversation, so
# point-to-point is sufficient — no bridge / MAC-learning subtleties.
#
# CRITICAL: this segment has NO uplink to any real NIC. That is deliberate —
# it keeps simulated OT frames off your production network and ensures CV only
# ever sees the simulation.
#
# Usage:
#   sudo ./setup-local-span.sh up       # create + bring up the segment
#   sudo ./setup-local-span.sh down     # tear it down
#   sudo ./setup-local-span.sh status   # show current state
#
# Env overrides:
#   GEN_IF (default pa-gen)  MON_IF (default pa-mon)  MTU (default 1500)
#
set -euo pipefail

GEN_IF="${GEN_IF:-pa-gen}"
MON_IF="${MON_IF:-pa-mon}"
MTU="${MTU:-1500}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: must run as root (ip link / promisc need CAP_NET_ADMIN)." >&2
  echo "Try: sudo $0 $*" >&2
  exit 1
fi

cmd="${1:-up}"

up() {
  if ip link show "$GEN_IF" >/dev/null 2>&1; then
    echo "[*] $GEN_IF already exists — reusing"
  else
    echo "[*] creating veth crossover: $GEN_IF <==> $MON_IF (mtu $MTU)"
    ip link add "$GEN_IF" mtu "$MTU" type veth peer name "$MON_IF" mtu "$MTU"
  fi

  # Bring both ends up and promiscuous so the sensor's macvlan parent ($MON_IF)
  # receives frames addressed to phantom simulated MACs, not just its own.
  ip link set "$GEN_IF" up promisc on
  ip link set "$MON_IF" up promisc on

  # Best-effort: disable offloads so injected frames aren't coalesced/mangled
  # before the sensor sees them. Harmless if ethtool is absent.
  if command -v ethtool >/dev/null 2>&1; then
    for ifc in "$GEN_IF" "$MON_IF"; do
      ethtool -K "$ifc" tx off rx off gso off tso off gro off lro off 2>/dev/null || true
    done
  fi

  echo "[+] SPAN segment ready."
  status
  cat <<EOF

Next:
  - Point the agent at the injection end:   DEFAULT_INTERFACE=$GEN_IF
  - Point the CV sensor macvlan parent at:  $MON_IF
  (deploy-local-sensor.sh wires both for you.)
EOF
}

down() {
  if ip link show "$GEN_IF" >/dev/null 2>&1; then
    echo "[*] deleting $GEN_IF (its peer $MON_IF goes with it)"
    ip link del "$GEN_IF"
  else
    echo "[*] $GEN_IF not present — nothing to do"
  fi
}

status() {
  echo "--- SPAN segment status ---"
  for ifc in "$GEN_IF" "$MON_IF"; do
    if ip link show "$ifc" >/dev/null 2>&1; then
      ip -br link show "$ifc"
    else
      echo "$ifc            ABSENT"
    fi
  done
}

case "$cmd" in
  up)     up ;;
  down)   down ;;
  status) status ;;
  *) echo "usage: $0 {up|down|status}" >&2; exit 2 ;;
esac
