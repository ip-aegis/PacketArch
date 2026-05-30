#!/usr/bin/env bash
#
# verify-span.sh — prove that frames injected on the agent end ($GEN_IF) of the
# local SPAN segment actually arrive on the sensor end ($MON_IF), the way a
# Scapy-injected packet from the agent must reach the CV sensor's capture NIC.
#
# Uses pure-Python AF_PACKET raw sockets — no tcpdump/scapy needed on the host.
# Sends a frame with a marker payload + experimental ethertype on $GEN_IF while
# listening on $MON_IF; passes if the marker is received.
#
# Run AFTER setup-local-span.sh up:
#   sudo ./setup-local-span.sh up && sudo ./verify-span.sh
#
set -euo pipefail

GEN_IF="${GEN_IF:-pa-gen}"
MON_IF="${MON_IF:-pa-mon}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: must run as root (AF_PACKET raw sockets need CAP_NET_RAW)." >&2
  echo "Try: sudo $0" >&2
  exit 1
fi

GEN_IF="$GEN_IF" MON_IF="$MON_IF" python3 - <<'PY'
import os, socket, struct, threading, sys, time

GEN = os.environ["GEN_IF"]
MON = os.environ["MON_IF"]
ETH_P_ALL = 0x0003
ETHERTYPE = 0x88B5            # IEEE local experimental ethertype
MAGIC = b"PACKETARCH-SPAN-TEST"
# phantom simulated MACs (like the agent uses) to prove dst-MAC-agnostic delivery
DST = bytes.fromhex("0200deadbeef")
SRC = bytes.fromhex("02000c29abcd")
FRAME = DST + SRC + struct.pack("!H", ETHERTYPE) + MAGIC
FRAME = FRAME + b"\x00" * max(0, 60 - len(FRAME))   # pad to min ethernet len

got = {"ok": False}

def listener(ready):
    r = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    r.bind((MON, 0))
    r.settimeout(4)
    ready.set()
    deadline = time.time() + 4
    while time.time() < deadline:
        try:
            data = r.recv(2048)
        except socket.timeout:
            break
        if MAGIC in data:
            got["ok"] = True
            break
    r.close()

ready = threading.Event()
t = threading.Thread(target=listener, args=(ready,), daemon=True)
t.start()
ready.wait(2)
time.sleep(0.2)  # ensure listener is in recv loop

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
s.bind((GEN, 0))
for _ in range(3):
    s.send(FRAME)
    time.sleep(0.1)
s.close()

t.join(5)

if got["ok"]:
    print(f"[+] PASS: marker frame injected on {GEN} was captured on {MON}")
    print("    -> a Scapy-injected agent packet will reach the CV sensor's capture NIC.")
    sys.exit(0)
else:
    print(f"[x] FAIL: nothing with the marker arrived on {MON}", file=sys.stderr)
    print("    Check: setup-local-span.sh up ran, both ends UP+promisc, names match.", file=sys.stderr)
    sys.exit(1)
PY
