# Local agent + Cyber Vision sensor (single-host) — prototype

Run **both** the PacketArch traffic-generation agent and a Cisco Cyber Vision
docker sensor on the PacketArch host itself, wired so the agent's generated
traffic is mirrored to the sensor's capture interface. This is a *secondary*
deployment option (CML remains primary) for demos / dev / air-gapped labs where
you don't want to stand up a CML lab.

## How it works

It reproduces the proven CML topology
(`backend/app/services/cml_service.py::build_lab`) on one Linux host, swapping
the virtual IOSvL2 SPAN switch for a host **veth crossover**:

```
   CML:    agent ens3 ─► IOSvL2 Gi0/0 ──monitor session 1──► Gi0/1 ─► sensor ens3
   LOCAL:  agent ─inject(pa-gen) ═══════ veth crossover ═══════ (pa-mon) capture─► sensor
                  DEFAULT_INTERFACE                              macvlan parent
```

A veth pair is a virtual crossover cable: every frame the agent injects on
`pa-gen` (Scapy `sendp`, see `orchestrator_pool.py`) arrives on `pa-mon`,
**regardless of src/dst MAC**, so one segment carries any number of simulated
devices. The sensor is passive and the agent fabricates both sides of every
conversation, so a point-to-point cable is sufficient — no bridge, no
MAC-learning gotchas. The segment has **no uplink**, so simulated OT frames
never leak onto your real network and CV only ever sees the simulation.

## Files

| File | Purpose |
|------|---------|
| `setup-local-span.sh` | create/tear down the isolated `pa-gen`↔`pa-mon` veth SPAN segment |
| `verify-span.sh` | prove a frame injected on `pa-gen` is captured on `pa-mon` (pure-Python AF_PACKET, no deps) |
| `deploy-local-sensor.sh` | one-shot: SPAN up → CV sensor (parent rewritten to `pa-mon`) → agent (`DEFAULT_INTERFACE=pa-gen`) |
| `docker-compose.agent.local.yml` | reference agent compose showing the only delta vs a remote agent |

## "What do I tell CV the sensor interface is?"

When you create the **docker sensor** in the Cyber Vision Center and it generates
a `docker-compose.yml`, the interface that matters is the **macvlan `parent:`**:

```yaml
networks:
  capture:
    driver: macvlan
    driver_opts:
      parent: eth1        # ◄── the capture interface
```

You don't have to get this right in the CV UI — `deploy-local-sensor.sh`
**rewrites `parent:` to the local monitor interface** (`pa-mon`) for you, exactly
like PacketArch already does for CML (`re.sub(r"parent:\s*\S+", "parent: ens3", ...)`).
The sensor's *other* interface (collection/management) stays on normal routed
networking so it can reach the CV Center and enroll with its provisioning token.

## Runbook

**0. (once) In the Cyber Vision Center UI:** add a sensor, type *docker*, capture
mode *all*. Download the `docker-compose.yml` it generates (embeds
`SERIAL_NUMBER` + `PROVISIONING_TOKEN`). Save it as e.g. `./cv-sensor-compose.yml`.

**1. (once) In the PacketArch UI:** Settings → Agents → Add Agent. Copy the token.

**2. Verify the plumbing (no CV/agent needed yet):**

```bash
sudo scripts/local-sensor/setup-local-span.sh up
sudo scripts/local-sensor/verify-span.sh        # expect: PASS
```

**3. Deploy both:**

```bash
sudo scripts/local-sensor/deploy-local-sensor.sh \
    --server https://<this-host-ip> \
    --token  <agent-token> \
    --sensor-compose ./cv-sensor-compose.yml \
    --insecure                                   # self-signed origin cert
```

**4. Run a scenario** from PacketArch onto the `Local-Agent`. Watch devices
populate in the Cyber Vision Center.

**Tear down:** `sudo scripts/local-sensor/deploy-local-sensor.sh --down`

## Caveats / notes

- **Root required** — veth creation, promisc, and raw sockets need
  `CAP_NET_ADMIN`/`CAP_NET_RAW`.
- **Promiscuous capture** — both veth ends are set promisc; the CV sensor also
  sets its macvlan child promisc (standard for capture). If the sensor still sees
  nothing, confirm its capture mode is *all*.
- **One agent → one sensor** uses the veth crossover. For multiple agent
  containers or sensors on one segment, replace the crossover with a Linux bridge
  that has MAC learning disabled (`bridge link set dev <port> learning off flood on`)
  so it behaves as a hub — otherwise the bridge learns both phantom MACs on the
  agent port and stops flooding to the sensor.
- **L2 protocols** (PROFINET, VLAN tags) ride the veth fine.
- This is a **prototype**. If it proves out, the natural productization is a
  backend "Local Sensor Lab" deploy path mirroring `cml.py::build_lab`: reuse
  `CMLService.parse_sensor_compose()`, run these scripts via the already-mounted
  Docker socket, and register the `TrafficAgent` row locally.
