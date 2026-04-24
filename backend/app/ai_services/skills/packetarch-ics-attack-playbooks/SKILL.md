---
name: packetarch-ics-attack-playbooks
description: PacketArch attack playbook catalog, kill-chain stages, action generators, and guidance for configuring realistic ICS attack simulations.
version: 1.0.0
tags: attack, playbooks, mitre, ics, kill-chain
---

# PacketArch ICS Attack Playbooks

Use this knowledge when the user asks to configure, explain, or select
an attack simulation in PacketArch. Playbooks are Python-coded
(`backend/app/protocol_engines/attacks/playbooks.py`), addressable via
the `AttackService` REST API (`/api/v1/attacks/*`), and run on remote
agents through the `START_ATTACK` WebSocket command.

## Playbook Catalog

9 playbooks ship in `PLAYBOOK_REGISTRY`. Recommend by scenario vendor,
protocol, and intended lesson:

| playbook_id | Best for | Key stages |
|---|---|---|
| `triton_like` | Siemens/Schneider SIS, safety-critical manufacturing | C2 → recon → lateral → SIS discovery → payload → safety disable |
| `pipedream_like` | Mixed Rockwell + Schneider environments | Initial access → multi-proto scan → profiling → config tamper → disruption → DoS |
| `industroyer_like` | Power grid, substations, IEDs | C2 → substation discovery → staging → breaker manipulation → protection disable → wiper |
| `havex_like` | IT-to-OT reconnaissance, OPC-heavy plants | Supply-chain foothold → OPC enumeration → protocol probing → slow exfil |
| `insider_threat` | Authorized-user abuse scenarios | Legitimate auth → unauthorized writes → cover-up |
| `network_recon` | Baseline red-team discovery | Port scans, Modbus unit enumeration, EIP discovery, SNMP walk |
| `snort_validation` | IDS/IPS signature coverage testing | Fires known-signature payloads for detection-rule validation |
| `bas_compromise` | Building automation (BACnet/Modbus) | Who-Is flood → property writes → HVAC disruption |
| `its_signal_disruption` | Transportation/ITS (NTCIP/SNMP) | Controller enumeration → phase manipulation → signal chaos |

Fetch the authoritative kill-chain tree via
`GET /api/v1/attacks/playbooks/{playbook_id}`.

## Kill-Chain Vocabulary

Playbooks are trees of `AttackStage` → `AttackStep` → `AttackAction`.
Stages roughly map to MITRE ATT&CK for ICS tactics:

- **reconnaissance** — passive/active discovery of topology, devices, protocols
- **initial_access** — foothold, exploit, supply-chain compromise
- **execution** — running code or commands on a target
- **persistence** — staying after reboot (C2 beaconing)
- **privilege_escalation** — gaining elevated rights
- **lateral_movement** — hopping between zones or devices
- **collection** — reading process data, configs, network maps
- **command_and_control** — beacon/heartbeat traffic
- **impact** — the damaging payload (safety disable, setpoint write, breaker open)

Every stage has `duration_seconds`, `intensity` (0.0–1.0), and an
optional `pause_between_steps_ms`. The `AttackOrchestrator` schedules
`attack_stage_tick` events on the shared event heap, so attack traffic
composes cleanly with adaptive/phase-scheduled normal traffic.

## Action Generators

Actions are registered via `@register_action("action_type")` in
`backend/app/protocol_engines/attacks/ics_actions.py`. Supported types
include:

- Generic: `port_scan`, `c2_beacon`, `icmp_sweep`, `dns_tunneling`
- Modbus: `modbus_discovery`, `modbus_read`, `modbus_write`,
  `modbus_coil_flood`, `modbus_force_listen_only`
- S7: `s7_discovery`, `s7_szl_query`, `s7_read`, `s7_write`,
  `s7_stop_cpu`
- EtherNet/IP: `enip_list_services`, `enip_list_identity`, `enip_read`,
  `enip_write`
- SNMP: `snmp_walk`, `snmp_set`
- BACnet: `bacnet_whois_flood`, `bacnet_write_property`
- ICMP: `icmp_echo_flood`

Every action builder produces Scapy packets, which are bridged into
`PacketEvent(timestamp_ms, flow_id, packet_bytes)` by
`_scapy_to_packet_event()` before emission.

## Recommending a Playbook

When a user describes a scenario and asks "what attack should I run?",
apply this decision tree:

1. **Safety PLC / SIS present?** → `triton_like`
2. **Power grid / IEDs / protection relays?** → `industroyer_like`
3. **Multi-vendor (Rockwell + Schneider) PLCs?** → `pipedream_like`
4. **OPC / IT-boundary emphasis?** → `havex_like`
5. **BACnet-heavy BAS scenario?** → `bas_compromise`
6. **Transportation/ITS (signals, DMS)?** → `its_signal_disruption`
7. **IDS/Snort rule testing?** → `snort_validation`
8. **Need to baseline detection tools?** → `network_recon`
9. **Authorized-user abuse / HR training?** → `insider_threat`

## Configuration Tips

- **Intensity**: 0.1–0.3 for stealth (HAVEX-style slow-burn), 0.7–1.0 for
  disruptive impact stages.
- **Timing relative to deployment phases**: start attacks after the
  `steady_state` phase so the agent has a realistic traffic baseline for
  the attack to hide in.
- **ADVANCE_STAGE / PAUSE_ATTACK** commands let operators pause mid-run
  for observability — mention these when the user asks about controlling
  a running attack.
- **DeploymentCreate.attack_playbook** (dict) gets merged into the
  scenario definition on deploy and sent to the agent, so attacks
  persist across agent reconnects within a deployment.

## Safety / Ethics Reminder

These playbooks simulate ICS attacks for defensive testing, Cyber
Vision validation, and operator training on isolated lab networks. They
are shaped to mimic real adversary behavior for detection-tool
development. Do not recommend running attack playbooks against
production OT networks or any system the user does not own or have
authorization to test.
