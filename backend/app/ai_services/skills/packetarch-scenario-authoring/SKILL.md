---
name: packetarch-scenario-authoring
description: Procedural knowledge for authoring realistic OT/ICS network scenarios in PacketArch — vendor-native protocols, rational source/target pairings, Purdue cell isolation, conduit gating, no-orphan coverage, flow-protocol consistency, jump-server remote-access patterns, and the readiness checks that grade scenarios.
version: 2.0.0
tags: scenario, design, ot, ics, purdue, iec-62443, rationality, coverage, flow-snap
---

# PacketArch Scenario Authoring

You are authoring complete OT/ICS network scenarios that will run on a live agent and be observed by Cisco Cyber Vision (CV) for asset classification. The system enforces 16 categories of realism rules at every save and deploy. Most rules auto-repair, but the *intent* must be right at authoring time — auto-repair can only fix what was almost-correct.

The cardinal sin: producing a scenario that "deploys" but doesn't reflect a real industrial network. CV will then misclassify, irrational flows will fire, and the operator will doubt the platform. **It is far better to refuse to author a flow than to author one that doesn't make operational sense.**

---

## When this skill applies

- AI-generated scenarios from natural-language prompts.
- Template instantiation when the template needs adaptation.
- Manual canvas authoring when the user asks for guidance.
- Pre-deploy review when something feels off.
- Any time you'd be guessing about a vendor, protocol, or pairing — consult the matrices below first.

---

## The five realism dimensions (enforced by readiness)

Every scenario is graded on these. Errors block deploy; warnings degrade score.

| # | Dimension | Severity if wrong |
|---|---|---|
| 1 | **Naming** — unique, industrial, role-reflective | error on duplicates; warning on generic |
| 2 | **Protocol accuracy** — vendor-native protocols only | warning |
| 3 | **Completeness** — every device in ≥1 flow | **error** (no-orphans rule) |
| 4 | **Cell communications** — cells talk only northbound or via conduits | warning + runtime drop |
| 5 | **MAC↔vendor** — OUI prefix matches IEEE vendor record | warning |

A sixth dimension introduced in v2.0: **flow rationality** — the source/target pairing must reflect a real industrial topology (jump servers don't directly poll PLCs, drives don't poll PLCs, etc.).

---

## Vendor → native protocol matrix

Single source of truth: `backend/app/services/device_templates/_protocol_defaults.py:VENDOR_NATIVE_PROTOCOLS`. **Do not declare protocols for a device that aren't in its vendor's native set.** The catalog audit (`backend/scripts/audit_template_protocols.py`) flags violations.

Brand match strips suffixes ("Siemens AG" → `siemens`). Case-insensitive, leading word.

| Vendor | Industrial-control protocols | Remote-access / management |
|---|---|---|
| Siemens | s7 / s7comm / s7comm_plus, profinet, profisafe, opc_ua, modbus_tcp, iec61850, bacnet | snmp, https |
| Rockwell / Allen-Bradley | ethernet_ip / enip, cip_safety, cip_motion, modbus_tcp, opc_ua | snmp, https |
| Schneider | modbus_tcp, ethernet_ip, opc_ua, bacnet, dnp3, profinet, profisafe | snmp, https |
| ABB | modbus_tcp, profinet, ethernet_ip, opc_ua, iec104, dnp3, iec61850 | snmp |
| Honeywell | modbus_tcp, opc_ua, bacnet, dnp3 | snmp |
| Yokogawa / Emerson | modbus_tcp, opc_ua | snmp |
| GE | modbus_tcp, opc_ua, dnp3, ethernet_ip, iec61850 | snmp |
| Mitsubishi | slmp, modbus_tcp | snmp |
| Omron | fins, ethernet_ip, modbus_tcp | snmp |
| Beckhoff / B&R | profinet, ethernet_ip, modbus_tcp, opc_ua, ethercat (Beckhoff), powerlink (B&R) | snmp |
| WAGO | modbus_tcp, ethernet_ip, profinet, opc_ua, codesys | snmp |
| Phoenix Contact | modbus_tcp, profinet, ethernet_ip, opc_ua | snmp |
| Cisco | profinet, ethernet_ip, profisafe (industrial switches) | snmp, lldp, cdp, ssh, telnet, https |
| HMS / Anybus | modbus_tcp, ethernet_ip, profinet | snmp, https |
| SEL | dnp3, modbus_tcp, iec61850, iec104 | snmp |
| Fanuc | ethernet_ip, modbus_tcp, fanuc (FOCAS) | snmp |
| KUKA / Bosch / Dematic | profinet, ethernet_ip | snmp |
| Endress+Hauser | modbus_tcp, profinet, ethernet_ip | snmp |
| Honeywell BMS / Johnson Controls / Trane / Carrier / Delta | bacnet, modbus_tcp | snmp |
| Microsoft (jump servers) | modbus_tcp, opc_ua (proxied) | ssh, telnet, rdp, https, snmp |
| Econolite / McCain (transportation) | ntcip | snmp |

**Don't assume a protocol just because identity blocks exist on the template.** Many catalog templates carry over-populated identity blocks (Siemens with EnIP identity, etc.) — those are catalog cruft, not capability. Trust this matrix.

---

## Device-type pairing rules

The audit flags these source→target combinations as **irrational** regardless of shared protocol:

| ❌ Don't author | Why |
|---|---|
| `jump_server` → `plc/drive/io_module/sensor` | Jump servers reach OT via a SCADA / engineering workstation, not direct polling |
| `ewon_gateway` → `plc` | EWON forwards to remote SCADA via Talk2M cloud, not local polling |
| `drive` → `plc` | Drives respond to PLC requests; PLCs don't get polled by drives |
| `drive` → `hmi`, `io_module` → `hmi`, `sensor` → `hmi` | Field devices respond, never initiate to HMIs |
| `io_module` → `plc`, `sensor` → `plc` | Field devices respond to PLC polls |
| `switch` → `plc/hmi` | Switches don't poll endpoints; NMS polls switches via SNMP |

The rational pattern, by Purdue layer:

| Source (poll initiator) | Target (responder) | Protocol family |
|---|---|---|
| HMI (L2) | PLC (L1) | vendor-native (s7, EnIP, Modbus) |
| Engineering workstation (L3) | PLC (L1-L2) | vendor-native programming protocols |
| SCADA (L3) | PLC, Historian | OPC UA, vendor-native |
| Historian (L3) | PLC, SCADA | OPC UA |
| PLC (L1-L2) | Drive / VFD / Servo / IO / Sensor | PROFINET I/O, EnIP, Modbus |
| NMS / Jump Server (L3 / L3.5) | Switch, Router | snmp, ssh, telnet |
| Jump Server (L3.5) | Engineering workstation | rdp |
| Jump Server (L3.5) | Web HMI | https |
| EWON / Remote Gateway (L3.5) | Talk2M / Azure IoT cloud (external) | https (cloud_service_link) |

When a flow's only shared protocol is generic (snmp, http, telnet) AND the source isn't an admin/management device, the audit flags it. Don't even author such flows — pick a different pairing or upgrade the device's protocols.

---

## Cell isolation modes

Three modes on `definition.cell_isolation.mode` (default `off`). Cells are zones at Purdue levels 0, 1, 2. DMZ (3.5) and L3+ are not cells.

| Mode | Behavior |
|---|---|
| `off` | All flows allowed. No filtering. |
| `conduit_gated` | Cell↔cell flows dropped at runtime UNLESS a `conduit` definition explicitly permits the (source_zone, target_zone, protocol) tuple. Cell↔non-cell flows unrestricted. |
| `strict_northbound` | All cell↔cell flows blocked unconditionally. Cells may only originate flows to L3+ zones. Cell-to-cell conduits get pruned. |

**Authoring guidance per mode:**

- **`off`**: Default for non-segmented or pedagogical scenarios. Realistic for legacy networks.
- **`conduit_gated`**: Use when modeling IEC 62443 zones-and-conduits with specific permitted protocols documented as conduits. Each cross-zone flow needs a corresponding conduit.
- **`strict_northbound`**: Use for hermetically segmented modern facilities. All cross-cell conversation flows through a Site Operations / SCADA layer. Coverage flows for orphans must terminate at L3+ devices.

**Conduit definitions** require `sourceZoneId`, `targetZoneId`, `allowedProtocols`. Match a flow to a conduit by both endpoints' zones AND the flow's resolved protocol (alias-aware: `s7comm_plus` matches a conduit with `s7comm` allowed).

---

## Coverage flows — the no-orphan guarantee

Every device must participate in ≥1 flow. Orphans break Cyber Vision's asset classification. The runtime auto-creates a coverage flow for any orphan using this priority chain:

1. **Same-zone manager** — first device in same zone whose type is in `{hmi, scada_server, historian, engineering_workstation, fleet_manager, server, workstation}`. Manager polls orphan inbound. Always intra-zone, safe in every isolation mode.
2. **Same-zone PLC for field devices** — when orphan type is in `{drive, vfd, servo, io_module, sensor, actuator, valve, transmitter, analyzer}`, find a `plc/safety_plc/rtu/controller` peer in same zone.
3. **L3 Operations zone manager** — northbound, allowed in strict mode. Type priority: `engineering_workstation > engineering_station > scada_server > historian > hmi > fleet_manager > server > workstation`.
4. **L3.5 DMZ** — last northbound resort.
5. **No rational partner found** — orphan stays orphan, readiness flags as error.

**As an author**, prefer to define every flow yourself. Coverage flows fire silently and may not match your topology intent. If you want a device to be polled by a specific peer, author that flow explicitly.

---

## Flow protocol selection (priority order)

When selecting a protocol for a flow (or when the platform snaps an inconsistent flow to a valid protocol), the order is:

```
s7comm_plus, s7comm           ← vendor-native (Siemens)
ethernet_ip, cip_safety       ← vendor-native (Rockwell / ODVA)
opc_ua                        ← cross-vendor industrial
modbus_tcp                    ← widest interop
bacnet, dnp3, iec104          ← vertical-specific
fins, slmp                    ← Asian-vendor-specific
ssh, telnet, rdp, https       ← remote access (above generic SNMP)
snmp                          ← universal monitoring (last resort)
```

**Protocols rank above SNMP if and only if both endpoints support them.** A flow whose only shared protocol is `snmp` is a strong signal that you've paired devices incorrectly — pick different endpoints.

`profinet` is intentionally **excluded** from the priority list for coverage / synthetic flows. PROFINET I/O is L2-only and doesn't carry IP, so it doesn't help CV correlate MAC↔IP. Use it only on explicitly-authored Siemens-to-Siemens or Rockwell-safety flows where the cyclic data is the point.

---

## Remote-access pattern (jump server, EWON, admin workstations)

Remote-access devices have specific traffic shapes. Author them this way.

**Jump Server (L3.5 DMZ, type `jump_server`)** — admin pivot point for OT access.
- Inbound: from enterprise/internet (out of scope for OT scenarios).
- Outbound:
  - `ssh` → cell switches (Cisco IE-3500 etc.) for CLI admin
  - `rdp` → engineering workstations for GUI tools
  - `https` → web HMIs (Siemens KTP / Rockwell PanelView+ web) for browser access
  - `modbus_tcp` / `opc_ua` → PLCs (rare, only for explicit admin tunnels) — usually pairs with a SCADA mediator
- **Always** add a `cloud_service_link` if the jump server is a Talk2M / TeamViewer relay endpoint — runtime auto-attaches when missing.

**EWON Gateway (L3.5, type `ewon_gateway`)** — industrial cloud relay.
- Outbound `https` to Talk2M endpoint via auto-attached `cloud_service_link`.
- Optional internal `modbus_tcp` polling of one or two PLCs (the gateway's primary purpose).
- Don't author flows from EWON to switches or HMIs.

**Engineering Workstation (L3, type `engineering_workstation`)** — programmer's seat.
- Outbound vendor-native programming protocols to PLCs (s7comm to Siemens, ethernet_ip to Rockwell).
- Outbound OPC UA to SCADA / Historian.
- Outbound `https` to web-managed assets.

**SCADA Server (L3, type `scada_server`)** — production monitoring.
- Outbound OPC UA / vendor-native to PLCs (one flow per PLC at minimum).
- Inbound from HMIs (rare; HMIs typically poll SCADA).
- Outbound to Historian (OPC UA HA / SQL).

---

## Default ports (what you'll see in CV)

```
modbus_tcp     502        s7comm     102      opc_ua     4840
ethernet_ip    44818      iec104     2404     dnp3       20000
profinet       34964 UDP  bacnet     47808    snmp       161 UDP
fins           9600       slmp       5007     iec61850   102
ssh            22         telnet     23       rdp        3389
https          443        cloud_*    443
```

Aliases are resolved before lookup: `s7comm_plus → s7comm → 102`, `profisafe → profinet`, `enip → ethernet_ip`, `cip_safety → ethernet_ip`. CV identifies most protocols by destination port, so authoring the right protocol guarantees the right port.

---

## Anti-patterns to refuse or rewrite

| Symptom | Why it's wrong | How to fix |
|---|---|---|
| Flow `Siemens HMI → ABB PLC` over snmp | No shared industrial protocol; SNMP fallback is degraded | Insert a SCADA mediator; flow becomes HMI→SCADA (OPC UA), SCADA→PLC (Modbus / EnIP) |
| Flow `Siemens PLC → Rockwell PLC` over modbus_tcp | Cross-vendor PLC-to-PLC over Modbus is unusual | Use OPC UA between PLCs that both support it, or route via a SCADA / OPC tunnel |
| Flow `switch → drive` | Switches don't poll endpoints | Remove the flow; PLC polls the drive instead |
| Flow `drive → PLC` | Drives respond to PLC requests | Reverse direction: PLC → drive |
| Device with `protocols: ["modbus_tcp", "ethernet_ip"]` on a Siemens S7-1500 | EnIP isn't Siemens-native | Drop EnIP or change to a vendor that supports it (Rockwell ControlLogix) |
| Device with no flows | Orphan → CV can't fingerprint | Author at least one flow involving the device |
| Cell-to-cell flow with `cell_isolation.mode = strict_northbound` | Will be runtime-dropped | Route through L3 Operations |
| Conduit allows protocol but flow uses an alias | Alias mismatch may cause drops | Use canonical protocol name OR include alias in conduit's `allowedProtocols` |

---

## Recommended patterns to author proactively

For any non-trivial scenario, author at least these flow archetypes (one per cell or per role group):

| Pattern | Source (type) | Target (type) | Protocol | Cadence |
|---|---|---|---|---|
| Operator monitoring | hmi | plc | vendor-native | 500–2000 ms |
| Programming session | engineering_workstation | plc | vendor-native | event-driven (low) |
| SCADA polling | scada_server | plc | opc_ua / vendor-native | 1000–5000 ms |
| Historian collection | historian | scada_server | opc_ua | 5000–10000 ms |
| Field control | plc | drive / io_module / sensor | profinet / enip / modbus | 10–500 ms |
| Network management | jump_server / scada | switch | snmp + ssh | 30000 ms (snmp), event (ssh) |
| Remote access | jump_server | engineering_workstation | rdp | event-driven |
| Web HMI access | jump_server | hmi | https | event-driven |
| Cloud relay | ewon_gateway | external talk2m | cloud_service | 30000 ms |

When the user asks for a manufacturing / water / energy / oil-gas scenario, expect 2-5 of each archetype scaled to scenario size.

---

## Cell-isolation interaction with coverage flows

Coverage flows respect cell isolation by partner-selection construction:

- For an orphan in a cell zone (L0–L2), the partner picker walks: same-zone manager → same-zone PLC (field devices) → L3 manager → L3.5 DMZ device. **Never picks another cell.**
- In `strict_northbound`, every coverage flow is either intra-zone (steps 1, 2) or northbound (steps 3, 4). Same-zone is always allowed; cross-zone goes only to L3+.
- The `should_drop_flow` runtime gate runs *after* coverage flows are added — defense in depth.

Don't manually author cell↔cell flows in strict mode. Either change the mode or route through L3.

---

## Authoring self-check (run before returning a scenario)

After designing a scenario, verify each item. Each failure should drive a change before you submit.

**Devices**
- [ ] Every device has a unique, industrial-appropriate name (no `device_001`, no UUIDs).
- [ ] Every device has a vendor + model that exists in the fingerprint catalog.
- [ ] Every device's `protocols` list contains only protocols in its vendor's native set.
- [ ] Every device's MAC OUI matches the vendor (regenerate if not).
- [ ] Every device has an IP address in its zone's subnet.
- [ ] No duplicate device names. No duplicate MACs.

**Flows**
- [ ] Every device participates in at least one flow.
- [ ] Every flow's `protocol` is in BOTH endpoints' `supported_protocols`.
- [ ] No flow uses a generic-only protocol (snmp/http/telnet) unless source is admin/management.
- [ ] No source/target pairing matches the irrational table (jump server → PLC, drive → PLC, etc.).
- [ ] Every cross-zone flow has a matching conduit if `cell_isolation.mode != off`.
- [ ] No flow originates from a non-cell device into a cell unless permitted by Purdue rules.

**Zones / Topology**
- [ ] Every cell zone has Purdue level set (0, 1, or 2).
- [ ] L3 zones contain operations / SCADA / historian / engineering workstations.
- [ ] L3.5 DMZ contains remote-access gateways (EWON, jump server) if the scenario needs external comms.
- [ ] Strict northbound mode: zero cell↔cell flows in the list.
- [ ] Conduit-gated mode: every cross-cell flow has a permitting conduit.

**Remote access**
- [ ] EWON / jump server / cloud connector devices have `cloud_service_link` if external comms intended (or rely on auto-attach).
- [ ] Jump server's outbound flows use ssh / rdp / https / modbus_tcp / opc_ua (NOT snmp-only).

**Final**
- [ ] At expected readiness score: errors=0, warnings reflect intentional design choices only.
- [ ] If a warning fires that you didn't intend, fix the root cause — don't suppress.

---

## Cross-references to other skills

- **`packetarch-fingerprint-validator`** — for protocol identity blocks and OUI rules. Use it when picking a fingerprint.
- **`packetarch-device-naming`** — for vertical-specific naming vocabulary. Use it when generating names.
- **`packetarch-scenario-review`** — for graded post-authoring review and remediation actions.
- **`packetarch-ics-attack-playbooks`** — orthogonal; for layering attacks onto an authored scenario.

---

## Why these rules matter (the "why")

PacketArch generates traffic that Cyber Vision and other DPI tools observe. CV builds an asset inventory by correlating MAC, IP, vendor (from OUI), model (from protocol identity), and observed flows. **Every realism rule above is a CV correlation hint.** When you violate one, CV either misclassifies, fails to classify, or creates a phantom component.

Examples of failure modes this skill prevents:
- Phantom components from PROFINET I/O without identifying frames first → see `clean_demo_mode` in scenario flags
- Cross-cell traffic crossing strict isolation → traffic is generated then dropped, wasting compute and confusing operators
- Orphan devices invisible to CV → they exist on the canvas but don't appear in the asset DB
- Vendor-protocol mismatches → CV labels device as wrong vendor or fails to fingerprint
- Irrational source/target → CV may classify the flow correctly but the topology contradicts known industrial patterns, eroding trust

Get the authoring right and the platform's value compounds: realistic traffic → accurate CV classification → meaningful demo / training / validation. Get it wrong and you're spending compute to produce noise.
