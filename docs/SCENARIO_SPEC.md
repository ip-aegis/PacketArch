# PacketArch Portable Scenario Specification

**Format version:** `1.0`
**Schema:** [`schemas/packetarch-scenario.v1.json`](../schemas/packetarch-scenario.v1.json)
**Catalog snapshot (optional):** [`schemas/fingerprint-registry.v1.json`](../schemas/fingerprint-registry.v1.json)
**Ready-to-use LLM prompt:** [`docs/LLM_PROMPT.md`](LLM_PROMPT.md)
**Status:** Stable

This document specifies the portable scenario format — the public contract that external programs and AI tools use to generate scenario files importable into PacketArch.

---

## TL;DR — fastest path to a working scenario

**If you're handing this to an AI:** download `LLM_PROMPT.md` from the same place you got this file, paste its contents into a Claude / GPT / Gemini chat with the schema and registry attached, and replace the bracketed scenario sentence. You'll get an importable JSON back in seconds. Stop reading.

**If you're authoring by hand or want to understand the format:** continue below.

---

## The 10 commandments

Break any of these and import either fails or produces a degraded scenario. Listed in priority order:

1. **`format_version` MUST be exactly `"1.0"`**. Top-level `name` is required.
2. **`vertical`** must be one of: `manufacturing`, `water_wastewater`, `energy_power`, `oil_gas`, `transportation`, `building_automation`, `distribution_logistics`, `testing`.
3. **Protocols are OT-only**: `modbus_tcp`, `ethernet_ip`, `profinet`, `s7comm`, `bacnet`, `snmp`, `opc_ua`, `dnp3`, `iec104` (plus aliases). **Never** `https`, `rdp`, `ssh`, `wmi`, `icmp`, `lldp`, `cdp`, `tcp`, `udp` — these are rejected at schema validation.
4. **Prefer capability mode**: set `type` + `protocols` only and let the importer pick vendor + model. This is the most robust path, especially for airgapped/offline authoring.
5. **If you pin `vendor` + `fingerprint_model`**, both must appear together in `fingerprint-registry.v1.json` on the same entry. Never invent model strings, never copy a model from a different vendor.
6. **Purdue levels** on each zone: L0 = field instruments / sensors, L1 = PLCs / RTUs / drives / safety controllers / transmitters / analyzers / valve positioners, L2 = area HMIs, L3 = SCADA / historians / engineering workstations / NMS, L3.5 = IDMZ jump host.
7. **No orphan devices** — every device must appear in at least one flow's `source_types` or `target_types` (and, if you used `source_zones`/`target_zones`, the device's `zone` must satisfy those filters too). Flows whose `source_types` or `target_types` match no declared device `type` are silently dropped. The importer auto-synthesises an SNMP monitoring flow for any device left orphaned after expansion — your scenario won't fail readiness — but a meaningful, hand-authored flow is more realistic. The `/validate/portable` endpoint reports zone-aware orphans before you import.
8. **Realistic intervals**: Modbus poll 1000–5000 ms, EtherNet/IP cyclic_io 1–32 ms, S7comm poll 100–1000 ms, BACnet subscription 5000–30000 ms, SNMP poll 30000–60000 ms.
9. **Site-coded names** via `name_pattern` using `{n:02d}` for replication. `WTP-Filter-PLC-{n:02d}` good; `PLC-1` bad.
10. **Omit `conduits`** — the importer auto-generates them from your flows. Author conduits only when you want to *restrict* protocols on a cross-zone path beyond what your flows already imply.

**Tolerance:** the importer auto-falls-back when a pin doesn't resolve. A bad `fingerprint_model` demotes to vendor-pinned; a bad vendor demotes to capability mode; a bad protocol set demotes to type-only. All demotions are reported as warnings in the validate/import response — your file still imports.

---

This document specifies the portable scenario format — the public contract that external programs and AI tools use to generate scenario files importable into PacketArch. The format is intentionally minimal: authors describe *what* the OT environment looks like, and PacketArch's importer fills in network addresses, MAC addresses, vendor fingerprints, and the internal representation.

**Airgapped authoring is a first-class use case.** Authors can write valid `.pascenario.json` files using only this spec + the JSON Schema — no network access to a PacketArch server required. See "Authoring modes" and "Airgapped workflow" below.

---

## Authoring modes

For each device entry, authors choose how much to specify. The importer fills in the rest from the local catalog using a deterministic seed (the scenario `name` by default), so the same file always produces the same scenario on the same install.

| Mode | What the author writes | What the importer picks |
|------|------------------------|--------------------------|
| **Capability** | `type` + `protocols` only | vendor + model |
| **Vendor-pinned** | + `vendor` | model |
| **Fully specified** | + `fingerprint_model` | nothing |

You can mix modes within a single file. Examples:

```json
{ "type": "plc", "zone": "process", "protocols": ["modbus_tcp"] }
```
Capability mode — importer picks any vendor whose PLC catalog supports Modbus TCP.

```json
{ "type": "plc", "vendor": "siemens", "zone": "process", "protocols": ["s7comm"] }
```
Vendor-pinned mode — importer picks a Siemens PLC that supports S7comm.

```json
{ "type": "plc", "vendor": "siemens", "fingerprint_model": "CPU 1517-3 PN/DP", "zone": "process", "protocols": ["s7comm", "profinet"] }
```
Fully specified — importer uses exactly that model.

**Optional top-level `preferences` block** steers the resolver for capability-mode and vendor-omitted devices:

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

- `vendor_strategy: preferred` (default) — try `preferred_vendors` in order, fall back if none can serve the protocols.
- `vendor_strategy: diverse` — spread across vendors to simulate a heterogeneous shop.
- `vendor_strategy: any` — pick whichever has the largest matching catalog.

If resolution fails (no template matches `type` + `protocols`), `/import/portable` returns an error and `/validate/portable` reports `valid: false` with a `fingerprint_resolution` error per device.

---

## Quick start

A scenario file is a single JSON document with the extension `.pascenario.json`:

```json
{
  "$schema": "https://packetarch.io/schemas/scenario.v1.json",
  "format_version": "1.0",
  "name": "Small Water Treatment Plant",
  "vertical": "water_wastewater",
  "total_duration_ms": 600000,

  "zones": [
    { "id": "scada",   "name": "SCADA Network",   "purdue_level": 3, "vlan": 100 },
    { "id": "process", "name": "Process Control", "purdue_level": 1, "vlan": 200, "security_level": "high" }
  ],

  "devices": [
    {
      "type": "hmi", "vendor": "schneider", "fingerprint_model": "HMISTM6",
      "count": 1, "zone": "scada", "name_pattern": "WTP-SCADA-01",
      "architectural_role": "scada_primary",
      "protocols": ["modbus_tcp", "snmp"]
    },
    {
      "type": "plc", "vendor": "schneider", "fingerprint_model": "BMEH586040",
      "count": 3, "zone": "process", "name_pattern": "WTP-Filter-PLC-{n:02d}",
      "architectural_role": "cell_controller",
      "protocols": ["modbus_tcp"]
    }
  ],

  "flows": [
    {
      "protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
      "source_types": ["hmi"], "target_types": ["plc"],
      "source_zones": ["scada"], "target_zones": ["process"],
      "jitter_ms": 200, "jitter_type": "gaussian"
    }
  ],

  "conduits": [
    {
      "id": "scada_to_process", "source_zone": "scada", "target_zone": "process",
      "direction": "bidirectional", "allowed_protocols": ["modbus_tcp"], "security_level": "high"
    }
  ]
}
```

**Import it:**

```bash
curl -X POST https://<server>/api/v1/scenarios/import/portable \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data-binary @small_water_plant.pascenario.json
```

**Dry-run validate without creating:**

```bash
curl -X POST https://<server>/api/v1/scenarios/validate/portable \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data-binary @small_water_plant.pascenario.json
```

The validate endpoint returns schema errors *and* a preview of the readiness check (the 5 realism dimensions) so authoring tools can iterate without polluting the database. For capability-mode devices, the response includes a `resolved_devices` array showing exactly which vendor + model the importer would pick.

### Capability-mode example (airgap-friendly)

The same scenario, written without any knowledge of the PacketArch device catalog. Every device is described by capability only:

```json
{
  "$schema": "https://packetarch.io/schemas/scenario.v1.json",
  "format_version": "1.0",
  "name": "Small Water Treatment Plant",
  "vertical": "water_wastewater",
  "total_duration_ms": 600000,

  "preferences": {
    "vendor_strategy": "preferred",
    "preferred_vendors": ["schneider", "rockwell", "siemens"]
  },

  "zones": [
    { "id": "scada",   "name": "SCADA Network",   "purdue_level": 3, "vlan": 100 },
    { "id": "process", "name": "Process Control", "purdue_level": 1, "vlan": 200, "security_level": "high" }
  ],

  "devices": [
    {
      "type": "hmi", "count": 1, "zone": "scada",
      "name_pattern": "WTP-SCADA-01",
      "architectural_role": "scada_primary",
      "protocols": ["modbus_tcp", "snmp"]
    },
    {
      "type": "plc", "count": 3, "zone": "process",
      "name_pattern": "WTP-Filter-PLC-{n:02d}",
      "architectural_role": "cell_controller",
      "protocols": ["modbus_tcp"]
    }
  ],

  "flows": [
    {
      "protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
      "source_types": ["hmi"], "target_types": ["plc"],
      "source_zones": ["scada"], "target_zones": ["process"]
    }
  ]
}
```

No `vendor`, no `fingerprint_model`, no `conduits` — the importer fills it all in. The author needs to know only the schema and the spec doc, both of which ship with the PacketArch install.

### Verified worked example — small dairy plant

This example was generated and validated against the actual catalog (zero resolver warnings, all 11 devices resolve to real templates). Use it as a pattern to imitate:

```json
{
  "$schema": "https://packetarch.io/schemas/scenario.v1.json",
  "format_version": "1.0",
  "name": "Northbrook Dairy — Small Plant",
  "description": "Small fluid-milk plant: receiving, HTST pasteurization, CIP, one filling line.",
  "vertical": "manufacturing",
  "total_duration_ms": 600000,

  "preferences": {
    "vendor_strategy": "preferred",
    "preferred_vendors": ["rockwell", "schneider", "endress+hauser", "emerson"]
  },

  "zones": [
    { "id": "supervisory", "name": "Plant Supervisory",   "purdue_level": 2, "vlan": 20 },
    { "id": "receiving",   "name": "Raw Milk Receiving",  "purdue_level": 1, "vlan": 110 },
    { "id": "pasteurizer", "name": "HTST Pasteurization", "purdue_level": 1, "vlan": 120, "security_level": "critical" },
    { "id": "cip",         "name": "Clean-In-Place",      "purdue_level": 1, "vlan": 140, "security_level": "high" },
    { "id": "filling",     "name": "Filling Line",        "purdue_level": 1, "vlan": 150 }
  ],

  "devices": [
    { "type": "hmi", "count": 1, "zone": "supervisory",
      "name_pattern": "DAIRY-HMI-PASTEUR-01",
      "architectural_role": "area_hmi",
      "protocols": ["ethernet_ip"] },
    { "type": "hmi", "count": 1, "zone": "supervisory",
      "name_pattern": "DAIRY-HMI-FILLING-01",
      "architectural_role": "area_hmi",
      "protocols": ["ethernet_ip"] },
    { "type": "plc", "count": 1, "zone": "receiving",
      "name_pattern": "DAIRY-RECV-PLC-01",
      "architectural_role": "cell_controller",
      "protocols": ["ethernet_ip"] },
    { "type": "flow_meter", "vendor": "endress+hauser",
      "count": 2, "zone": "receiving",
      "name_pattern": "DAIRY-RECV-FLOW-{n:02d}",
      "protocols": ["modbus_tcp"] },
    { "type": "plc", "count": 1, "zone": "pasteurizer",
      "name_pattern": "DAIRY-HTST-PLC-01",
      "architectural_role": "cell_controller",
      "protocols": ["ethernet_ip", "modbus_tcp"] },
    { "type": "transmitter", "count": 2, "zone": "pasteurizer",
      "name_pattern": "DAIRY-HTST-TT-{n:02d}",
      "protocols": ["modbus_tcp"] },
    { "type": "valve_positioner", "vendor": "emerson",
      "count": 2, "zone": "pasteurizer",
      "name_pattern": "DAIRY-HTST-FDV-{n:02d}",
      "protocols": ["modbus_tcp"] },
    { "type": "plc", "count": 1, "zone": "cip",
      "name_pattern": "DAIRY-CIP-PLC-01",
      "architectural_role": "cell_controller",
      "protocols": ["ethernet_ip", "modbus_tcp"] },
    { "type": "analyzer", "vendor": "endress+hauser",
      "count": 1, "zone": "cip",
      "name_pattern": "DAIRY-CIP-CONDUCTIVITY-01",
      "protocols": ["modbus_tcp"] },
    { "type": "plc", "count": 1, "zone": "filling",
      "name_pattern": "DAIRY-FILLER-PLC-01",
      "architectural_role": "cell_controller",
      "protocols": ["ethernet_ip"] },
    { "type": "drive", "count": 2, "zone": "filling",
      "name_pattern": "DAIRY-FILLER-VFD-{n:02d}",
      "protocols": ["ethernet_ip"] }
  ],

  "flows": [
    { "protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 750,
      "source_types": ["hmi"], "target_types": ["plc"],
      "source_zones": ["supervisory"],
      "target_zones": ["receiving", "pasteurizer", "filling"],
      "jitter_ms": 75 },
    { "protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
      "source_types": ["plc"], "target_types": ["drive"],
      "source_zones": ["filling"], "target_zones": ["filling"] },
    { "protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
      "source_types": ["plc"],
      "target_types": ["flow_meter", "transmitter", "valve_positioner", "analyzer"],
      "source_zones": ["receiving", "pasteurizer", "cip"],
      "target_zones": ["receiving", "pasteurizer", "cip"],
      "jitter_ms": 200, "jitter_type": "gaussian" }
  ]
}
```

**What this example demonstrates:**
- *Mixed authoring modes* — most devices are capability-mode (no vendor); a few are vendor-pinned (`endress+hauser` for flow_meter/analyzer, `emerson` for valve_positioner) to lock in realism for instrumentation that has obvious real-world vendor associations.
- *Preferred vendor steering* — `preferences.preferred_vendors` orders Rockwell first for the controls (which is what the resolver picks: PLCs → 1756-L8x ControlLogix, HMIs → PanelView, VFD → PowerFlex 525), Endress+Hauser for instrumentation, Emerson for valves.
- *Purdue-correct zoning* — supervisory HMIs at L2, all process controllers and instruments at L1.
- *Realistic flow shapes* — 750 ms HMI poll, 20 ms cyclic_io for VFD control, 2000 ms Modbus poll for instrumentation.
- *No `conduits`* — the importer generates them automatically from the three declared cross-zone flow patterns.

**Resolves to** (deterministic, given the scenario `name` as seed):
Rockwell ControlLogix PLCs, Rockwell PanelView HMIs, Rockwell PowerFlex VFDs, Endress+Hauser Promag flow meters and CM442 analyzer, Emerson 3051S transmitters and DVC6200 valve positioners.

---

## Top-level fields

| Field | Required | Description |
|-------|----------|-------------|
| `format_version` | yes | Must be `"1.0"` |
| `name` | yes | Scenario display name (1–255 chars) |
| `vertical` | recommended | One of: `manufacturing`, `water_wastewater`, `energy_power`, `oil_gas`, `transportation`, `building_automation`, `distribution_logistics`, `testing`. Drives default conduit policy and process-simulation templates. |
| `description` | optional | Long-form description |
| `total_duration_ms` | optional | Default `60000`. Range 1s – 24h. PCAP runs for exactly this long; agent treats as a planning hint. |
| `zones` | yes | At least one zone |
| `devices` | yes | At least one device |
| `flows` | yes | At least one flow |
| `conduits` | optional | Auto-generated from flows if omitted |
| `anomalies` | optional | Advisory metadata, does not inject anomalies |
| `external_comms` | optional | C2/exfil/recon configuration |
| `phases` | optional | Defaults derived from `total_duration_ms` if omitted |
| `modes` | optional | Behavioral flags (`clean_demo_mode`, `broadcast_traffic_enabled`, `cell_isolation_mode`) |

---

## Zones

A zone is a Purdue-level network segment. Every device belongs to exactly one zone.

```json
{
  "id": "process",
  "name": "Process Control",
  "purdue_level": 1,
  "vlan": 200,
  "security_level": "high"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Stable identifier (lowercase, digits, underscores). Used by devices/flows/conduits to reference this zone. |
| `name` | yes | Human-readable name |
| `purdue_level` | yes | 0–5 (decimals OK, e.g., `3.5` for IDMZ) |
| `vlan` | optional | 1–4094 |
| `security_level` | optional | `minimal` / `standard` / `high` / `critical`. Default `standard`. |
| `subnet` | optional | CIDR (e.g., `10.42.5.0/24`). If omitted, importer allocates from the scenario's auto-assigned /16. |

**Purdue level guide:**
| Level | Function | Typical devices |
|-------|----------|----------------|
| 0 | Process/field | sensors, actuators, instrumentation |
| 1 | Basic control | PLCs, RTUs, drives, safety controllers |
| 2 | Area supervision | HMIs, area-supervisor PLCs, local historians |
| 3 | Operations | SCADA, engineering workstations, asset mgmt, historians |
| 3.5 | IDMZ | jump servers, reverse proxies, patch staging |
| 4 | Enterprise IT | (typically out of scope) |

---

## Devices

A device entry is a *spec* that may produce multiple device instances via `count`.

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
| `type` | yes | Role keyword: `plc`, `hmi`, `rtu`, `drive`, `sensor`, `historian`, `engineering_workstation`, `scada`, etc. Used by flow matching. |
| `vendor` | yes | Lowercase. Drives OUI selection. |
| `fingerprint_model` | recommended | Model ID from the PacketArch catalog (e.g., `1756-L83E`, `CPU 1517-3 PN/DP`). Query `GET /api/v1/fingerprints/registry` for valid values. If omitted, a vendor default is used and realism scores drop. |
| `count` | optional | Default 1. Expands into N devices. |
| `zone` | yes | Must match a zone `id` |
| `name_pattern` | optional | Supports `{n}` and `{n:02d}` (1-based index). If `count=1`, a literal name (no placeholder) is fine. Default `'{type}-{n:03d}'`. |
| `protocols` | yes | One or more. Must be vendor-compatible — see "Realism rules" below. |
| `role` | optional | Free-text functional role (cosmetic) |
| `architectural_role` | optional but recommended | Canonical role from the role catalog. Used by readiness for role-inventory health at scale. See `GET /api/v1/architecture/roles`. |
| `cve_ids` | optional | List like `["CVE-2022-1159"]` for vulnerable firmware emulation |
| `error_config` | optional | Override default error injection rates |

**Naming patterns** — placeholder `{n}` expands to the 1-based index within the spec. Use `{n:02d}` for zero-padded two-digit, `{n:03d}` for three-digit, etc.

**The importer generates** for each instantiated device:
- A unique device ID (UUID)
- A vendor-correct MAC address (OUI selected from `vendor`)
- An IP address within the device's zone subnet
- A full vendor fingerprint blob (resolved from `fingerprint_model`)
- Protocol identity blocks (Modbus MEI strings, S7 SZL fields, BACnet object names, SNMP sysDescr/sysObjectID, etc.) consistent with the fingerprint

---

## Flows

A flow is a traffic pattern between *types* of devices. The importer expands flows to all matching device pairs.

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

| Field | Required | Notes |
|-------|----------|-------|
| `protocol` | yes | One of the enum values |
| `pattern` | yes | `poll`, `cyclic_io`, `subscription`, `safety`, `event` |
| `interval_ms` | yes | See typical intervals below |
| `source_types` | yes | Device types that initiate (e.g., `["hmi"]`) |
| `target_types` | yes | Device types that receive |
| `source_zones` | optional | Limit sources to specific zones |
| `target_zones` | optional | Limit targets to specific zones |
| `jitter_ms` | optional | Default 0 |
| `jitter_type` | optional | `uniform` (default), `gaussian`, `exponential` |

**Typical intervals:**
| Protocol | Pattern | Range |
|----------|---------|-------|
| Modbus TCP | `poll` | 500–5000 ms |
| EtherNet/IP | `cyclic_io` | 1–32 ms (RPI) |
| PROFINET | `cyclic_io` | 1–32 ms |
| S7comm | `poll` | 100–1000 ms |
| BACnet | `subscription` | 5000–30000 ms |
| SNMP | `poll` | 30000–60000 ms |
| DNP3 | `poll` | 1000–10000 ms |

---

## Conduits

Conduits express IEC 62443 zone-to-zone communication permissions. **If omitted, the importer auto-generates conduits matching the flows you declared** — you only need to author conduits explicitly when you want to lock down protocols or document security boundaries.

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
| `id` | yes | Stable identifier |
| `name` | optional | Display name |
| `source_zone` / `target_zone` | yes | Zone IDs |
| `direction` | optional | `bidirectional` (default), `a_to_b`, `b_to_a` |
| `allowed_protocols` | optional | Empty list = all protocols allowed |
| `security_level` | optional | Default `standard` |
| `description` | optional | Documentation hint |

---

## Realism rules (enforced at import)

PacketArch enforces 5 realism dimensions on every imported scenario. The `/validate/portable` endpoint surfaces violations as readiness warnings/errors before you commit.

### 1. Device naming
Every device needs a unique, industrial-appropriate, human-understandable name. Generic patterns (`device_001`, `plc-1`, `new_device`, UUID prefixes) trigger warnings. Good names reflect role, vendor, and zone — e.g., `Assembly_Line_PLC_01`, `Water_Treatment_VFD_03`.

### 2. Protocol accuracy
Devices may only use protocols their vendor supports:

| Vendor | Supported protocols |
|--------|---------------------|
| Siemens | profinet, profisafe, s7comm, s7comm_plus, modbus_tcp, snmp |
| Rockwell / Allen-Bradley | ethernet_ip, cip, modbus_tcp |
| Schneider | modbus_tcp, ethernet_ip |
| GE | modbus_tcp, ethernet_ip, opc_ua |
| Honeywell | modbus_tcp, bacnet, snmp |
| Johnson Controls / Trane / Carrier | bacnet, snmp |
| SEL | modbus_tcp, dnp3, iec104 |
| Econolite / Wavetronix / McCain | snmp |

The importer will *remove* unsupported protocols and *add* supported ones from the device's fingerprint. Flows whose protocol is supported by neither endpoint are rejected.

### 3. Completeness
- Every device must appear in at least one flow (orphan devices are rejected — Cyber Vision cannot fingerprint a silent device).
- Every protocol on a device must have a populated identity block in its fingerprint (sysDescr for SNMP, sysName for Modbus MEI, station_name for PROFINET, etc.). The importer auto-populates these from the device template.

### 4. Conduit compliance (IEC 62443)
- Intra-zone traffic is unrestricted.
- Cross-zone flows require a conduit between those zones with the flow's protocol in `allowed_protocols` (or an empty `allowed_protocols`, which means "any").
- If you omit `conduits`, the importer generates one per cross-zone flow pair. Authoring conduits explicitly lets you lock down protocols beyond what your declared flows use.

### 5. Vendor-realistic MAC OUIs
Each device's MAC OUI prefix must match its declared vendor. **Authors do not set MACs** — the importer generates them from `vendor_oui.py`. A Siemens device gets a Siemens OUI (`00:0E:8C`, `28:63:36`, …); a Rockwell device gets a Rockwell OUI (`00:1D:9C`, `00:00:BC`, …).

At scale (≥10 devices), readiness additionally requires:
- At least one supervisory role (`scada_primary`, `engineering_workstation`, `area_hmi`)
- At least one infrastructure role (`nms_server`, `asset_management_server`, `jump_server`, `ot_domain_controller`, `process_historian`)
- Controller-to-supervisory ratio ≤ 10:1

Use the `architectural_role` field to satisfy these.

---

## Airgapped workflow

PacketArch is designed to run on airgapped lab networks. The portable scenario format is engineered so authors on a *separate, also-airgapped* network can produce valid `.pascenario.json` files without ever touching the PacketArch server.

**What ships with every PacketArch install** (under `/release-bundle/schemas/` in the offline tarball):

1. **`packetarch-scenario.v1.json`** — the JSON Schema. Hand this to any author or AI tool — it's the format contract.
2. **`SCENARIO_SPEC.md`** — this document.
3. **`fingerprint-registry.v1.json`** — a static snapshot of the device template catalog (~300 entries, ~90 KB). Optional. Use only if you want to pin specific `fingerprint_model` values.

**Recommended airgap workflow:**

1. **Site operator** copies the schema + spec + (optionally) registry snapshot to a USB drive or accessible share.
2. **Author** drafts a `.pascenario.json` file using capability mode wherever possible. They consult the registry snapshot only if they need to pin specific models.
3. **Author** validates locally with any JSON Schema validator pointed at `packetarch-scenario.v1.json` — no server access needed for schema correctness.
4. **Author** transfers the file (USB, share, ticket attachment) to the PacketArch server's air gap.
5. **Operator** uploads via the Studio UI ("Import Portable Scenario") or `curl -X POST /api/v1/scenarios/import/portable`.
6. **Importer** resolves fingerprints from the local catalog, allocates IPs/MACs, runs realism repair, returns a readiness report.

**No version drift** — the schema and registry snapshot in the install always match the importer running on that install. If the catalog grows in a later release, the snapshot grows with it.

**AI-generated scenarios on an airgapped network:** point Claude / GPT / a local LLM at the schema + spec + registry snapshot. Capability mode is friendliest — the LLM doesn't need to memorize ~300 model IDs. Example LLM prompt:

```
You are generating a PacketArch scenario file. Conform exactly to the
attached JSON Schema (packetarch-scenario.v1.json). Use capability mode
(omit vendor and fingerprint_model) unless I specify otherwise; let
PacketArch's importer pick. Output a single JSON object.
```

---

## Discoverability endpoints

Authoring tools running on the same network as a PacketArch server (i.e., not airgapped) can query these:

| Endpoint | Returns |
|----------|---------|
| `GET /api/v1/scenarios/schema/portable.json` | This schema document |
| `GET /api/v1/fingerprints/registry` | Live `{vendor, model, type, protocols}` tuples (300+ entries) |
| `GET /api/v1/architecture/roles` | Canonical `architectural_role` values per Purdue level |
| `GET /api/v1/about` | Server version, format versions supported, feature flags |

Airgapped authors get the schema and registry from the static files shipped in the install bundle — same data, no network needed.

---

## Versioning policy

- The schema `$id` is stable: `https://packetarch.io/schemas/scenario.v1.json`.
- `format_version` is pinned to `"1.0"` for the current revision.
- Additive changes (new optional fields, new enum members) are minor revisions and stay on `1.x`; the schema's `$id` is unchanged, and clients should ignore unknown fields they don't recognize on read.
- Breaking changes ship as a new schema at `https://packetarch.io/schemas/scenario.v2.json` with `format_version: "2.0"`. The import endpoint accepts both for a deprecation window.

---

## Importer behavior summary

Given a valid portable scenario, the importer:

1. **Resolves unspecified fingerprints** — for each device spec, if `fingerprint_model` is missing, picks one from the local catalog matching `type` + `protocols` + (optional) `vendor`. If `vendor` is also missing, picks one honoring `preferences.vendor_strategy` and `preferences.preferred_vendors`. Selection is deterministic (seeded by scenario name + device index).
2. Allocates a unique `/16` IP range for the new scenario.
3. Allocates a `/24` subnet per zone within that range (or honors `zone.subnet` if specified).
4. For each device spec:
   - Expands `count: N` into N instances.
   - Applies `name_pattern` to generate unique names.
   - Resolves `fingerprint_model` → full vendor fingerprint blob.
   - Generates a vendor-correct MAC using OUI prefixes.
   - Assigns an IP from the zone's subnet.
   - Populates protocol identity blocks (Modbus MEI, S7 SZL, BACnet objects, SNMP sysDescr/sysObjectID, EtherNet/IP CIP identity, PROFINET station name).
   - Enriches unique serial numbers and identifiers.
5. Auto-generates conduits for any cross-zone flow that lacks one.
6. Runs `auto_repair_protocols()` to fix vendor-protocol mismatches.
7. Applies the site naming pipeline (deterministic or LLM-driven) so device names share a coherent site identity.
8. Returns the new scenario's ID + readiness summary.

The result is functionally identical to creating a scenario via the Studio UI or the template instantiation route — just sourced from a portable file rather than user clicks.
