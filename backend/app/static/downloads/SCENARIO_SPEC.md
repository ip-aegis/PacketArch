# PacketArch Portable Scenario Specification

**Format version:** `1.0`
**Schema:** [`schemas/packetarch-scenario.v1.json`](../schemas/packetarch-scenario.v1.json)
**Catalog snapshot (optional):** [`schemas/fingerprint-registry.v1.json`](../schemas/fingerprint-registry.v1.json)
**Status:** Stable
**Last reviewed:** May 2026

This document is the authoring guide for the PacketArch Portable Scenario format — a stable, version-pinned JSON contract that external programs, AI tools, and human authors use to describe OT environments that PacketArch can then import, materialize, and simulate.

It is self-contained. You do not need network access to a PacketArch server to author a valid file. Everything you need ships with the install: this spec, the JSON Schema, and an optional snapshot of the device template catalog.

---

## 1. Overview

### What a portable scenario is

A portable scenario is a single JSON document (conventional extension `.pascenario.json`) that describes an OT environment at a deliberately high level of abstraction:

- A set of **network zones** aligned to the Purdue model
- A set of **devices** placed in those zones, optionally pinned to a specific vendor and model
- A set of **flows** describing how those devices talk to each other
- An optional set of **conduits** authorizing cross-zone traffic per IEC 62443

The format intentionally omits the things a scenario author should not have to think about: IP addresses, MAC addresses, vendor fingerprint blobs, protocol identity strings, and device IDs. The importer generates all of those deterministically from your inputs.

### The v1 contract

The schema `$id` is stable at `https://packetarch.io/schemas/scenario.v1.json` and `format_version` is pinned to `"1.0"`. Additive changes (new optional fields, new enum members) are minor revisions and stay on `1.x`. Breaking changes ship as a separate schema at `scenario.v2.json` with a deprecation window during which the importer accepts both.

Clients should ignore unknown fields when reading and must not introduce fields that the schema does not declare — the schema sets `additionalProperties: false` at every level.

### Where to find the schema

In order of preference:

| Source | When to use |
|--------|-------------|
| `GET /api/v1/scenarios/schema/portable.json` | Online tools running on the same network as a PacketArch server |
| `schemas/packetarch-scenario.v1.json` in this repo / install bundle | Airgapped authors |
| Release bundle: `release-bundle/schemas/packetarch-scenario.v1.json` | Site operators handing the schema to a partner |

The schema in the install always matches the importer running on that install, so there is no version-drift risk.

### How a file gets imported

```bash
# Dry-run validation, expansion preview, readiness preview
curl -X POST https://<server>/api/v1/scenarios/validate/portable \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data-binary @my_scenario.pascenario.json

# Actually create the scenario
curl -X POST https://<server>/api/v1/scenarios/import/portable \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data-binary @my_scenario.pascenario.json
```

The Studio UI exposes the same import path through the "Import Portable Scenario" button.

The validate endpoint returns the same readiness preview the importer would produce, plus a `resolved_devices` array showing exactly which vendor and model the importer would pick for any capability-mode device. Use it to iterate without polluting the database.

---

## 2. The 5 Realism Dimensions

PacketArch enforces five realism dimensions on every imported scenario. They are surfaced by readiness checks and, where possible, automatically repaired by the importer. These five rules drive every authoring decision below.

### 2.1 Device naming

Every device must have a unique, industrial-appropriate, human-understandable name that reflects its role, vendor, and zone. Generic patterns (`device_001`, `PLC-1`, `new_device`, UUID prefixes) trigger readiness warnings.

You provide names via `name_pattern` (per device spec). After import, the site naming pipeline may rename devices into a site-coherent identity (a `site_id` prefix, a consistent process-area vocabulary). Good author-supplied names look like `Assembly_Line_PLC_01`, `WTP-Filter-PLC-{n:02d}`, `BLDG-AHU-CTRL-03`.

### 2.2 Protocol accuracy

Devices may only speak protocols their vendor fingerprint actually supports. A Siemens PLC speaks S7comm and PROFINET; it does not speak EtherNet/IP. The importer runs `auto_repair_protocols()` after fingerprint resolution: protocols the device's fingerprint does not support are removed, and protocols the fingerprint requires for that role are added. Flows whose protocol is supported by neither endpoint are dropped.

See section 8 for the affinity table.

### 2.3 Completeness

Every device must participate in at least one flow — Cyber Vision cannot fingerprint a silent device. If a flow expansion leaves a device orphaned, the importer synthesises an SNMP monitoring poll so the device appears on the wire. Protocol identity blocks (`sysName`, `station_name`, `bacnet_identity`, `cip_identity`, S7 SZL fields, Modbus MEI) are auto-populated from the fingerprint so CV has enough data to classify the device.

You can rely on this safety net, but a hand-authored realistic flow is always preferable.

### 2.4 Inter/intra-cell communications (IEC 62443 conduit compliance)

Intra-zone traffic is unrestricted. Any cross-zone flow must be justified by a conduit between the two zones, and the flow's protocol must be in the conduit's `allowed_protocols` (or `allowed_protocols` must be empty, meaning "any").

If you omit `conduits` entirely, the importer auto-generates one per cross-zone flow pair. Author conduits explicitly only when you want to lock down protocols beyond what your declared flows use.

See section 7.

### 2.5 Vendor-realistic MAC OUIs

Each device's MAC OUI must match its declared vendor using IEEE-verified prefixes. Authors do not set MACs — the importer generates them from `backend/app/protocol_engines/vendor_oui.py`. A Siemens device gets a Siemens OUI (`00:0E:8C`, `28:63:36`, `74:DA:EA`, …); a Rockwell device gets a Rockwell OUI (`00:1D:9C`, `00:00:BC`, …).

If you change a device's vendor (or the importer changes it for you during resolver fallback), the MAC is regenerated to stay aligned.

### At-scale extras

For scenarios with ten or more devices, readiness adds three structural expectations:

- At least one supervisory role (`scada_primary`, `engineering_workstation`, or `area_hmi`)
- At least one infrastructure role (`nms_server`, `asset_management_server`, `jump_server`, `ot_domain_controller`, `process_historian`)
- Controller-to-supervisory ratio of 10:1 or tighter

Use the `architectural_role` field on device specs to satisfy these.

---

## 3. Three Authoring Modes

For each device entry, you choose how much to specify. The importer fills in the rest from the local catalog using a deterministic seed — the same file always produces the same scenario on the same install.

| Mode | Author writes | Importer picks | Use when |
|------|---------------|----------------|----------|
| **Capability** | `type` + `protocols` | vendor + model | Airgapped authoring, AI generation, or you don't care about a specific brand |
| **Vendor-pinned** | + `vendor` | model | You want a particular vendor (e.g., a real customer is Siemens-only) |
| **Fully-specified** | + `fingerprint_model` | nothing | You're reproducing a specific lab or PoC down to the part number |

Modes mix freely inside one file: pin the SCADA stack to Rockwell, leave the field instruments as capability-mode so the resolver chooses Endress+Hauser or Emerson based on the catalog.

### When to prefer which

**Capability mode is the recommended default.** It is the only mode that works without seeing the catalog, which is exactly the constraint an external author or LLM operates under. The resolver is tolerant: it will pick a vendor that satisfies your `type` + `protocols` constraints, honoring the `preferences` block if you provide one.

**Vendor-pinned mode** is a small step up. Set `vendor: "siemens"` when the realism story demands a particular brand but you don't want to memorize part numbers. The resolver picks a model within that vendor that supports your protocols.

**Fully-specified mode** locks the document to a specific catalog entry. It is the most precise but the least portable — if the install ships a slightly different catalog, the resolver demotes you to vendor-pinned and emits a warning rather than failing. This is the right mode when you want a particular model badge in the UI and bill of materials.

### Resolver preferences

An optional top-level `preferences` block steers the resolver for capability-mode and vendor-omitted devices:

```json
{
  "preferences": {
    "vendor_strategy": "preferred",
    "preferred_vendors": ["siemens", "rockwell", "schneider"],
    "exclude_vendors": ["honeywell"],
    "deterministic_seed": "wtp-001-v2"
  }
}
```

| `vendor_strategy` | Behavior |
|-------------------|----------|
| `preferred` (default) | Walk `preferred_vendors` in order. First vendor with a matching template wins. Fall back to any vendor if none match. |
| `diverse` | Rotate vendors across device indices to simulate a heterogeneous shop. |
| `any` | Pick deterministically across all matching templates without preference. |

`deterministic_seed` defaults to the scenario `name`. Set it explicitly when you want to keep the same name but force a different vendor draw.

### Tolerance and demotion

The resolver tries four tiers in order: fully-specified, vendor + type + protocols, type + protocols (capability), type only (last resort, with `auto_repair_protocols` cleaning up afterwards). Each demotion is reported as a warning in the validate/import response, but the file still imports. A typo in `fingerprint_model` does not fail an import — it produces a warning and the importer picks the next-best model from the same vendor.

---

## 4. Schema Reference

The complete contract is in `schemas/packetarch-scenario.v1.json`. This section is a guided tour of the shape, the required fields, and the value ranges. Where the schema and this document disagree, the schema wins.

### Top-level object

| Field | Required | Notes |
|-------|----------|-------|
| `format_version` | yes | Must be `"1.0"` exactly |
| `name` | yes | 1–255 chars |
| `vertical` | recommended | Drives default conduits, role inventory, process-sim template |
| `description` | optional | Long-form text |
| `total_duration_ms` | optional | Default 60000. Range 1000 – 86400000 (1 s to 24 h). PCAP mode runs for exactly this long; agent mode treats it as a planning hint. |
| `zones` | yes | At least one |
| `devices` | yes | At least one |
| `flows` | yes | At least one |
| `conduits` | optional | Auto-generated from flows if omitted |
| `anomalies` | optional | Advisory metadata; does not inject anomalies |
| `external_comms` | optional | C2 beacon / exfil / recon configuration |
| `phases` | optional | Default phases derived from `total_duration_ms` |
| `modes` | optional | `clean_demo_mode`, `broadcast_traffic_enabled`, `cell_isolation_mode` |
| `preferences` | optional | Resolver steering (section 3) |

### Vertical enum

```
manufacturing, water_wastewater, energy_power, oil_gas,
transportation, building_automation, distribution_logistics, testing
```

### Protocol enum

The canonical OT protocol set, plus accepted aliases the importer normalizes:

| Canonical | Aliases accepted |
|-----------|------------------|
| `modbus_tcp` | `modbus` |
| `ethernet_ip` | `enip`, `cip_safety` |
| `profinet` | `profisafe` |
| `s7comm` | `s7comm_plus` |
| `bacnet` | `bacnet_ip` |
| `snmp` | — |
| `opc_ua` | — |
| `dnp3` | — |
| `iec104` | — |

IT protocols (HTTPS, RDP, SSH, WMI, ICMP, LLDP, CDP, raw TCP, raw UDP) are rejected at schema validation. LLDP, CDP, ARP, NTP, STP, DHCP, and ICMP are still generated on the wire by the agent's ambient-noise subsystem — but they are not authored, they are emitted automatically based on which devices and zones exist.

### Zone object

```json
{
  "id": "process",
  "name": "Process Control",
  "purdue_level": 1,
  "vlan": 200,
  "security_level": "high",
  "subnet": "10.42.5.0/24"
}
```

| Field | Required | Range / Enum |
|-------|----------|--------------|
| `id` | yes | `^[a-z0-9_]+$` |
| `name` | yes | non-empty |
| `purdue_level` | yes | `0`–`5`, decimals OK (e.g., `3.5` for IDMZ) |
| `vlan` | optional | 1–4094 |
| `security_level` | optional | `minimal`, `standard` (default), `high`, `critical` |
| `subnet` | optional | CIDR string. If omitted, the importer allocates a `/24` from the scenario's auto-assigned `/16`. |

### Device object

```json
{
  "type": "plc",
  "vendor": "schneider",
  "fingerprint_model": "BMEH586040",
  "count": 3,
  "zone": "process",
  "name_pattern": "WTP-Filter-PLC-{n:02d}",
  "architectural_role": "cell_controller",
  "protocols": ["modbus_tcp"]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `type` | yes | Role keyword: `plc`, `hmi`, `rtu`, `drive`, `sensor`, `transmitter`, `flow_meter`, `valve_positioner`, `analyzer`, `historian`, `engineering_workstation`, `scada`, etc. |
| `vendor` | optional | Lowercase. Drives OUI selection and protocol set. |
| `fingerprint_model` | optional | Model ID from the catalog (e.g., `1756-L83E`, `CPU 1517-3 PN/DP`) |
| `count` | optional | Default 1 |
| `zone` | yes | Must match a declared zone `id` |
| `name_pattern` | optional | `{n}` and `{n:02d}` expand to per-spec index (1-based). Default `'{type}-{n:03d}'`. |
| `protocols` | yes | At least one. Must be vendor-compatible — see section 8. |
| `role` | optional | Free-text functional role label (cosmetic) |
| `architectural_role` | optional | Canonical role from `GET /api/v1/architecture/roles`. Used by readiness for role-inventory health. |
| `cve_ids` | optional | `^CVE-\d{4}-\d+$` for vulnerable firmware emulation |
| `error_config` | optional | Override default exception/timeout rates |

### Flow object

```json
{
  "protocol": "modbus_tcp",
  "pattern": "poll",
  "interval_ms": 2000,
  "source_types": ["hmi"],
  "target_types": ["plc"],
  "source_zones": ["scada"],
  "target_zones": ["process"],
  "jitter_ms": 200,
  "jitter_type": "gaussian"
}
```

| Field | Required | Enum |
|-------|----------|------|
| `protocol` | yes | Protocol enum |
| `pattern` | yes | `poll`, `cyclic_io`, `subscription`, `safety`, `event` |
| `interval_ms` | yes | ≥ 1 |
| `source_types` | yes | At least one device type string |
| `target_types` | yes | At least one device type string |
| `source_zones` | optional | Zone IDs (limits which sources match) |
| `target_zones` | optional | Zone IDs |
| `jitter_ms` | optional | Default 0 |
| `jitter_type` | optional | `uniform` (default), `gaussian`, `exponential` |

**Typical interval ranges:**

| Protocol | Pattern | Range |
|----------|---------|-------|
| Modbus TCP | `poll` | 500–5000 ms |
| EtherNet/IP | `cyclic_io` | 1–32 ms (RPI) |
| PROFINET | `cyclic_io` | 1–32 ms |
| S7comm | `poll` | 100–1000 ms |
| BACnet | `subscription` | 5000–30000 ms |
| SNMP | `poll` | 30000–60000 ms |
| DNP3 | `poll` | 1000–10000 ms |
| IEC 60870-5-104 | `poll` | 1000–5000 ms |

### Conduit object

```json
{
  "id": "scada_to_process",
  "name": "SCADA → Process Control",
  "source_zone": "scada",
  "target_zone": "process",
  "direction": "bidirectional",
  "allowed_protocols": ["modbus_tcp", "snmp"],
  "security_level": "high"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | `^[a-z0-9_]+$` |
| `name` | optional | Display name |
| `source_zone`, `target_zone` | yes | Zone IDs |
| `direction` | optional | `bidirectional` (default), `a_to_b`, `b_to_a` |
| `allowed_protocols` | optional | Empty list means "any protocol allowed" |
| `security_level` | optional | Default `standard` |
| `description` | optional | Documentation hint |

---

## 5. Industry Verticals

The `vertical` field drives default conduit policy, role inventory expectations, and the process-simulation template applied at runtime. Below is per-vertical guidance on the typical device mix, the protocols you'll author, and the Purdue layout that reads as realistic.

### Manufacturing

Discrete and process manufacturing — assembly lines, machine cells, packaging, CNC, food and beverage.

- **Typical mix:** PLCs (controllers per cell), HMIs (per area), drives / VFDs, flow meters, transmitters, analyzers, robots, vision systems, MES historian.
- **Protocols:** EtherNet/IP (Rockwell-heavy shops), PROFINET + S7comm (Siemens-heavy shops), Modbus TCP (instrumentation), SNMP (network gear), OPC UA (MES integration).
- **Purdue:** L0 sensors → L1 cell PLCs → L2 area HMIs → L3 MES / historian.

### Water / Wastewater

Treatment plants, lift stations, distribution networks.

- **Typical mix:** PLCs per treatment stage (intake, coagulation, filtration, chlorination), RTUs at remote sites, SCADA, HMIs, level / flow / pH transmitters, motor drives.
- **Protocols:** Modbus TCP (mainstay), DNP3 or IEC 60870-5-104 (between SCADA and remote RTUs), EtherNet/IP, BACnet (rare, for plant HVAC), SNMP.
- **Purdue:** L0 instruments → L1 stage PLCs / RTUs → L2 plant HMIs → L3 SCADA / historian.

### Energy / Power

Substations, generation, microgrids.

- **Typical mix:** Protection relays (SEL, GE, ABB, Siemens), RTUs, gateway / merging units, HMIs, station computer, SCADA front-end.
- **Protocols:** DNP3, IEC 60870-5-104, IEC 61850 (modeled here as a mix of MMS-over-TCP and GOOSE — represent at the engine layer; use `iec104` or `modbus_tcp` at the schema layer), Modbus TCP, SNMP.
- **Purdue:** L0 CTs/PTs → L1 protection relays → L2 station HMI → L3 control center SCADA.

### Oil & Gas

Wellheads, gathering systems, midstream pipelines, terminals.

- **Typical mix:** Wellhead RTUs, flow computers, ESD / safety PLCs, separators, pump-station PLCs, transmitters (pressure, temperature, level), gas analyzers, custody-transfer meters.
- **Protocols:** Modbus TCP, DNP3 (between RTUs and control center over long-haul), HART-IP, OPC UA, SNMP.
- **Purdue:** L0 field instruments → L1 wellhead RTUs / safety PLCs → L2 area HMIs → L3 pipeline SCADA.

### Building Automation

Commercial buildings, campus systems, data center HVAC.

- **Typical mix:** Building controllers, VAV / AHU controllers, chiller / boiler controllers, lighting controllers, BMS workstation, BACnet routers.
- **Protocols:** BACnet/IP (dominant), Modbus TCP (legacy / chiller plant), SNMP (network and UPS).
- **Purdue:** L1 field controllers (VAV, AHU) → L2 area controllers → L3 BMS workstation / supervisor.

### Transportation

Intelligent transportation systems, rail, ports, airports.

- **Typical mix:** Traffic signal controllers, dynamic message signs, ramp meters, ITS field cabinets, vehicle detection, video / DSRC, central management.
- **Protocols:** NTCIP over SNMP (dominant for road infrastructure), Modbus TCP (mechanical interlocks), DNP3 (rail and tunnel SCADA), BACnet (tunnel ventilation).
- **Purdue:** L1 field controllers → L2 corridor management → L3 traffic management center.

### Distribution / Logistics

Warehouses, distribution centers, sortation, conveyor systems.

- **Typical mix:** Sortation PLCs, conveyor drives, scanner cells, WMS integration host, HMIs.
- **Protocols:** EtherNet/IP, PROFINET, Modbus TCP, SNMP.

### Testing

Generic vertical for catalog exploration and engine validation. No constraints, no default conduit policy.

---

## 6. Purdue Levels & Zones

The Purdue Enterprise Reference Architecture splits an OT network into layers by function. PacketArch uses `zone.purdue_level` (numeric, `0`–`5`) to drive default conduit generation, the cross-zone-flow allow-list, and the role-inventory readiness checks.

| Level | Function | Typical devices |
|-------|----------|-----------------|
| L0 | Process / field | sensors, actuators, instrumentation, transmitters, valve positioners |
| L1 | Basic control | PLCs, RTUs, drives, safety controllers, protection relays |
| L2 | Area supervision | HMIs, area-supervisor PLCs, local historians |
| L3 | Operations | SCADA, engineering workstations, asset management, plant historians, NMS |
| L3.5 | IDMZ | jump servers, reverse proxies, patch staging, broker hosts |
| L4 | Enterprise IT | MES, ERP (typically out of scope for OT simulation) |

A zone maps to exactly one Purdue level. Several zones may share a level — a manufacturing plant might have separate L1 zones for the receiving line, the pasteurizer, and the filling line, all at `purdue_level: 1`.

### Cross-zone flows the compliant way

For a flow that crosses zone boundaries:

1. Author the flow with explicit `source_zones` and `target_zones` (don't rely on whole-vertical matching for cross-zone traffic).
2. Either declare a conduit between those zones with the flow's protocol in `allowed_protocols`, or omit `conduits` entirely and let the importer generate one.
3. Avoid skipping Purdue levels (L1 → L3) without an explicit conduit — the readiness check will accept it once a conduit exists, but it reads better if the path goes through an L2 supervisor or an L3.5 IDMZ jump host.

---

## 7. IEC 62443 Conduit Compliance

IEC 62443 models cross-zone communication as named **conduits** with explicit protocol allow-lists. PacketArch enforces this at readiness time:

- Intra-zone traffic is unrestricted. No conduit needed.
- Every cross-zone flow must be authorized by a conduit between its source and target zones, with the flow's protocol in the conduit's `allowed_protocols` (or `allowed_protocols` empty, meaning any).
- If you omit the `conduits` array entirely, the importer auto-generates one per cross-zone flow pair, with `allowed_protocols` set to the protocols actually used by your flows. This is the recommended default for most authoring.

Author conduits explicitly when you want to:

- **Restrict** protocols on a cross-zone path beyond what your flows already use (e.g., a conduit that allows Modbus but explicitly forbids SNMP from leaving an L1 cell).
- **Document** a security boundary for review or compliance reporting.
- **Pre-declare** future conduits that no flow uses yet (testing migration scenarios).

A conduit's `security_level` is informational at runtime but shows up on the canvas and in compliance reports. Use `critical` for safety-related crossings (e.g., from an SIS cell to the BPCS zone).

---

## 8. Vendor-Protocol Affinity

OT vendors have strong protocol affinities that real Cyber Vision installs use to classify devices. Violating these affinities causes CV to merge or misclassify your devices, so the importer enforces them.

| Vendor | Primary protocols | Why |
|--------|-------------------|-----|
| Siemens | `s7comm`, `profinet` (+ `profisafe`), `snmp`, sometimes `modbus_tcp` | S7 is Siemens's native CPU protocol; PROFINET is the Siemens-backed industrial Ethernet |
| Rockwell / Allen-Bradley | `ethernet_ip` (+ `cip_safety`), `modbus_tcp` (third-party bridges) | ODVA-backed EtherNet/IP is Rockwell's native fabric |
| Schneider | `modbus_tcp`, `ethernet_ip` | Modbus is a Schneider (Modicon) invention; Schneider also ships EtherNet/IP for some product lines |
| GE | `modbus_tcp`, `ethernet_ip`, `opc_ua`, `dnp3` (digital energy) | Broad — depends on product line |
| ABB | `modbus_tcp`, `profinet`, `ethernet_ip`, `iec104`, `dnp3` | Power-grid lines use IEC 60870/61850; automation lines use industrial Ethernet |
| Honeywell | `modbus_tcp`, `bacnet`, `snmp` | DCS via Modbus; building lines via BACnet |
| Yokogawa | `modbus_tcp`, `opc_ua` | DCS / process |
| Emerson | `modbus_tcp`, `ethernet_ip`, HART-IP | Fisher-Rosemount instrumentation |
| Endress+Hauser | `modbus_tcp`, HART-IP, `profinet` | Process instrumentation |
| SEL | `dnp3`, `iec104`, `modbus_tcp` | Protection relays for substations |
| Johnson Controls / Trane / Carrier | `bacnet`, `snmp` | Building automation |
| Cisco | `snmp`, `cdp`, (network gear, not authored as a protocol) | Network infrastructure |
| Econolite / Wavetronix / McCain | `snmp` (NTCIP) | Traffic / ITS |

For the full registry of vendor → model → supported-protocol tuples, consult `schemas/fingerprint-registry.v1.json` or query `GET /api/v1/fingerprints/registry`. This document does not duplicate the catalog — it changes with every device template addition.

If you pin a vendor and the protocols you ask for are not supported by that vendor in the catalog, the resolver demotes you to capability mode and emits a warning. The most common author mistake is asking a Siemens device for `ethernet_ip` — Siemens devices do not speak EtherNet/IP. Use S7comm or PROFINET instead.

---

## 9. MAC OUI Rules

Authors do not set MAC addresses. The importer generates them so that each device's first three octets (the OUI) match its declared vendor.

The source of truth is `backend/app/protocol_engines/vendor_oui.py`. Highlights:

| Vendor | Representative OUIs |
|--------|---------------------|
| Siemens | `00:0E:8C`, `00:1B:1B`, `00:1C:06`, `74:DA:EA`, `AC:64:17` |
| Rockwell | `00:00:BC`, `00:1D:9C`, `5C:88:16`, `E4:90:69`, `F4:54:33` |
| Schneider | `00:00:54`, `00:80:F4`, `00:04:74`, `64:3A:EA` |
| ABB | `00:21:99`, `00:24:2B`, `00:1F:ED`, `00:C0:53`, `C4:93:00` |
| Honeywell | `00:40:84`, `00:22:6A`, `C4:EF:DA`, `58:FC:C8` |
| GE | `00:09:45`, `00:30:C1`, `00:50:99`, `00:22:52` |
| SEL | `00:30:A7`, `00:1C:73` |
| Phoenix Contact | `00:A0:45`, `00:16:9D`, `A8:74:1D` |

All OUIs in the file are verified against the IEEE OUI registry. Some vendors (Emerson, parts of Honeywell, building-automation OEMs) often use embedded NICs from third parties (Microchip, Intel, Cisco) in real life — for those, protocol-based identification is more reliable than OUI lookup. The PacketArch importer still emits a vendor-OUI MAC where one exists, so the on-the-wire signal stays consistent with the declared vendor.

If you change a device's vendor (or the resolver does), the MAC is regenerated. You should never see a Rockwell OUI on a Siemens device in a PacketArch capture.

---

## 10. Worked Example 1 — Small Capability-Mode Scenario

A complete, importable scenario for a small water treatment plant. No vendors, no models, no conduits — the importer picks all three. This is the recommended shape for AI-generated and airgap-authored files.

```json
{
  "$schema": "https://packetarch.io/schemas/scenario.v1.json",
  "format_version": "1.0",
  "name": "Riverbend WTP — Small Plant",
  "description": "Two-stage treatment train with one SCADA workstation.",
  "vertical": "water_wastewater",
  "total_duration_ms": 600000,

  "preferences": {
    "vendor_strategy": "preferred",
    "preferred_vendors": ["schneider", "rockwell", "siemens"]
  },

  "zones": [
    { "id": "scada",       "name": "SCADA Network",      "purdue_level": 3,   "vlan": 100 },
    { "id": "supervisory", "name": "Plant Supervisory",  "purdue_level": 2,   "vlan": 110 },
    { "id": "filtration",  "name": "Filtration Stage",   "purdue_level": 1,   "vlan": 120, "security_level": "high" },
    { "id": "chlorination","name": "Chlorination Stage", "purdue_level": 1,   "vlan": 130, "security_level": "high" }
  ],

  "devices": [
    {
      "type": "scada", "count": 1, "zone": "scada",
      "name_pattern": "WTP-SCADA-01",
      "architectural_role": "scada_primary",
      "protocols": ["modbus_tcp", "snmp"]
    },
    {
      "type": "hmi", "count": 1, "zone": "supervisory",
      "name_pattern": "WTP-HMI-01",
      "architectural_role": "area_hmi",
      "protocols": ["modbus_tcp"]
    },
    {
      "type": "plc", "count": 2, "zone": "filtration",
      "name_pattern": "WTP-FILT-PLC-{n:02d}",
      "architectural_role": "cell_controller",
      "protocols": ["modbus_tcp"]
    },
    {
      "type": "plc", "count": 1, "zone": "chlorination",
      "name_pattern": "WTP-CHLOR-PLC-01",
      "architectural_role": "cell_controller",
      "protocols": ["modbus_tcp"]
    },
    {
      "type": "transmitter", "count": 3, "zone": "filtration",
      "name_pattern": "WTP-FILT-PT-{n:02d}",
      "protocols": ["modbus_tcp"]
    },
    {
      "type": "transmitter", "count": 2, "zone": "chlorination",
      "name_pattern": "WTP-CHLOR-PT-{n:02d}",
      "protocols": ["modbus_tcp"]
    }
  ],

  "flows": [
    {
      "protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
      "source_types": ["scada"], "target_types": ["plc"],
      "source_zones": ["scada"], "target_zones": ["filtration", "chlorination"],
      "jitter_ms": 200, "jitter_type": "gaussian"
    },
    {
      "protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1500,
      "source_types": ["hmi"], "target_types": ["plc"],
      "source_zones": ["supervisory"], "target_zones": ["filtration", "chlorination"],
      "jitter_ms": 150
    },
    {
      "protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
      "source_types": ["plc"], "target_types": ["transmitter"],
      "source_zones": ["filtration"], "target_zones": ["filtration"],
      "jitter_ms": 100
    },
    {
      "protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 1000,
      "source_types": ["plc"], "target_types": ["transmitter"],
      "source_zones": ["chlorination"], "target_zones": ["chlorination"],
      "jitter_ms": 100
    },
    {
      "protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
      "source_types": ["scada"], "target_types": ["plc"],
      "source_zones": ["scada"], "target_zones": ["filtration", "chlorination"]
    }
  ],

  "conduits": [
    {
      "id": "scada_to_process",
      "name": "SCADA → Process Cells",
      "source_zone": "scada",
      "target_zone": "filtration",
      "direction": "bidirectional",
      "allowed_protocols": ["modbus_tcp", "snmp"],
      "security_level": "high"
    }
  ]
}
```

What this demonstrates:

- **Capability mode end-to-end** — no `vendor`, no `fingerprint_model`. The resolver will pick Schneider first (per `preferred_vendors`); if no Schneider PLC supports Modbus TCP it falls back through Rockwell to Siemens.
- **Purdue-correct zoning** — SCADA at L3, HMI at L2, process at L1.
- **One author-declared conduit** — locks SCADA-to-filtration to Modbus and SNMP only. The importer will auto-generate the rest (SCADA-to-chlorination, supervisory-to-filtration, supervisory-to-chlorination) since they are cross-zone.
- **Intra-zone instrumentation flows** — PLC ↔ transmitter polls stay inside each L1 zone, so they don't need conduits.
- **Realistic intervals** — 2000 ms SCADA poll, 1000 ms PLC-to-instrument poll, 60 s SNMP.

---

## 11. Worked Example 2 — Vendor-Pinned Snippet

When you need specific brands locked in (because a customer asked, or you're reproducing a known reference architecture), pin the controller stack and leave the instruments capability-mode. The resolver does the rest.

```json
{
  "devices": [
    {
      "type": "scada", "vendor": "rockwell",
      "fingerprint_model": "FactoryTalk View SE",
      "count": 1, "zone": "scada",
      "name_pattern": "PLANT-FTV-01",
      "architectural_role": "scada_primary",
      "protocols": ["ethernet_ip", "snmp"]
    },
    {
      "type": "plc", "vendor": "rockwell",
      "fingerprint_model": "1756-L83E",
      "count": 4, "zone": "process",
      "name_pattern": "LINE-PLC-{n:02d}",
      "architectural_role": "cell_controller",
      "protocols": ["ethernet_ip"]
    },
    {
      "type": "drive", "vendor": "rockwell",
      "fingerprint_model": "PowerFlex 525",
      "count": 8, "zone": "process",
      "name_pattern": "LINE-VFD-{n:02d}",
      "protocols": ["ethernet_ip"]
    },
    {
      "type": "flow_meter", "vendor": "endress+hauser",
      "count": 4, "zone": "process",
      "name_pattern": "LINE-FLOW-{n:02d}",
      "protocols": ["modbus_tcp"]
    },
    {
      "type": "valve_positioner", "vendor": "emerson",
      "count": 4, "zone": "process",
      "name_pattern": "LINE-FDV-{n:02d}",
      "protocols": ["modbus_tcp"]
    }
  ]
}
```

Notes:

- The controller stack (SCADA, PLCs, drives) is fully specified to specific Rockwell models — predictable Cyber Vision badges, exact bill of materials.
- The instrumentation is vendor-pinned only (`endress+hauser`, `emerson`) — the resolver picks an appropriate flow meter and valve positioner from each vendor's catalog. This keeps realistic vendor diversity for the field layer without requiring the author to memorize model numbers.
- If `FactoryTalk View SE` or `1756-L83E` is missing from this install's catalog, the resolver demotes that device to vendor-pinned mode and picks the next best Rockwell SCADA / PLC, emitting a warning. The import still succeeds.

Always consult `fingerprint-registry.v1.json` (or `GET /api/v1/fingerprints/registry`) for valid `vendor` + `fingerprint_model` pairs. Never invent a model string and never pair a model with the wrong vendor.

---

## 12. Validation Checklist

Before you import, run the file through the dry-run endpoint:

```bash
curl -X POST https://<server>/api/v1/scenarios/validate/portable \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data-binary @my_scenario.pascenario.json
```

The response contains four sections you should review:

1. **Schema validation** — pass / fail against `packetarch-scenario.v1.json`. Failures here mean the document is structurally wrong (missing required fields, unknown properties, enum violation).
2. **Expansion preview** — counts of zones, device specs, instantiated devices, intra- and cross-zone flows, conduits (declared or auto-generated). Quick sanity check that `count: N` did what you expected.
3. **Resolver report** — per-device `resolved_devices` array showing the vendor and model the importer would pick for capability-mode entries, plus any demotion warnings.
4. **Readiness preview** — the five realism dimensions evaluated against the resolved scenario, with categorized warnings and errors.

### Common failures and how to fix them

| Failure | Cause | Fix |
|---------|-------|-----|
| `format_version must be "1.0"` | Wrong / missing top-level field | Add `"format_version": "1.0"` |
| `Additional properties are not allowed` | Schema is strict — unknown field at this level | Remove or rename the field |
| `vendor X + type Y has no match` | Pinned vendor doesn't make this device | Drop `vendor`, or change `type`, or change `protocols` |
| `Protocol Z not supported by vendor V` | Affinity violation | Use a protocol from V's affinity row in section 8 |
| `Orphan device W` | No flow involves W | Add a flow whose `source_types` or `target_types` matches W's type and zone |
| `Cross-zone flow without conduit` | A flow crosses zones but no conduit covers the protocol | Omit `conduits` entirely (auto-generate), or add the protocol to the conduit's `allowed_protocols` |
| `Generic name pattern` | `name_pattern` is `device-{n}` or similar | Use site- / process-coded names: `WTP-FILT-PLC-{n:02d}` |
| `Naming collision` | Two specs with the same literal name and `count: 1` | Use `{n}` placeholder or distinct literals |
| `No supervisory role at scale` | ≥ 10 devices, no `architectural_role` set | Set `architectural_role: scada_primary` (or similar) on at least one device |

If validate returns `valid: true` with only warnings, the import will succeed and the warnings will be visible in the scenario's readiness report.

---

## 13. Airgap Workflow

PacketArch is designed for airgapped lab networks. The portable scenario format is engineered so authors on a separate (also airgapped) network can produce valid files without ever touching the PacketArch server.

### What ships with every install

Under `release-bundle/schemas/` and `release-bundle/docs/` in the offline tarball:

| File | Purpose |
|------|---------|
| `packetarch-scenario.v1.json` | The JSON Schema. The format contract. |
| `SCENARIO_SPEC.md` | This document. |
| `fingerprint-registry.v1.json` | Static snapshot of the device template catalog (~300 entries, ~90 KB). Optional. |

### Recommended workflow

1. **Site operator** copies the schema, this spec, and (optionally) the registry snapshot to a USB drive or accessible share. These three files are the only inputs an external author needs.
2. **Author generates the JSON.** Three good paths:
    - **LLM-assisted:** paste the schema, this spec, and the registry snapshot into a Claude / GPT / Gemini chat along with a short brief ("Generate a portable scenario for a small dairy plant — pasteurizer, CIP, one filling line"). Capability mode is friendliest for LLMs; they don't need to memorize the catalog.
    - **Hand-authored from a template:** start from one of the worked examples in this document, edit zone names, device counts, flow intervals, and protocols.
    - **Tool-assisted:** any JSON Schema-aware editor (VS Code with the JSON extension, IntelliJ, etc.) gives autocomplete and inline validation against the schema.
3. **Validate locally.** Point any standard JSON Schema validator (e.g., `ajv-cli`, `check-jsonschema`, or VS Code's built-in JSON validation) at `packetarch-scenario.v1.json`. This catches structural problems before transfer:
    ```bash
    check-jsonschema --schemafile packetarch-scenario.v1.json my_scenario.pascenario.json
    ```
4. **Transfer the file** across the air gap (USB, signed share, ticket attachment, whatever the lab's procedure allows).
5. **Operator validates against the live importer:**
    ```bash
    curl -X POST https://<server>/api/v1/scenarios/validate/portable \
      -H "Authorization: Bearer <token>" \
      -H "Content-Type: application/json" \
      --data-binary @my_scenario.pascenario.json
    ```
    Review the readiness preview. Fix any errors. Iterate.
6. **Import** through the Studio UI ("Import Portable Scenario") or:
    ```bash
    curl -X POST https://<server>/api/v1/scenarios/import/portable \
      -H "Authorization: Bearer <token>" \
      -H "Content-Type: application/json" \
      --data-binary @my_scenario.pascenario.json
    ```
7. **Inspect the new scenario** in the Studio canvas. Run the readiness check. Adjust phases, attack playbooks, deployment options as needed — those are scenario-level concerns layered on top of the imported topology, not part of the portable format.

### Suggested LLM prompt

```
You are generating a PacketArch portable scenario file. Conform exactly
to the attached JSON Schema (packetarch-scenario.v1.json). Use
capability mode wherever possible: supply only `type` + `protocols` on
each device and omit `vendor` and `fingerprint_model` so the importer
can resolve them locally. Honor IEC 62443 conduit compliance for any
cross-zone flow. Use realistic Modbus poll intervals (1000–3000 ms),
cyclic_io intervals (1–32 ms), and SNMP poll intervals (30–60 s). Use
site- and process-coded names with `{n:02d}` placeholders, never
generic names like "PLC-1". Output a single valid JSON object — no
prose, no markdown fences.
```

### No version drift

The schema and registry snapshot in the install always match the importer running on that install. When the catalog grows in a later release, both the snapshot and the importer grow together. There is no scenario in which an author's file targets a registry the server can't honor — the resolver's demotion ladder ensures even outdated files import cleanly with warnings.
