# PacketArch Portable Scenario — LLM Authoring Prompt

Paste everything below the line into Claude, ChatGPT, or Gemini together with `packetarch-scenario.v1.json` (the JSON Schema) and, if available, `fingerprint-registry.v1.json` (the device catalog snapshot). Replace the bracketed sentence at the bottom with the scenario you want, then send. The model returns a single JSON object you save as `<your-name>.pascenario.json` and import via the PacketArch Scenarios page → Import button, or `POST /api/v1/scenarios/import/portable`.

──────────────────────────────────────────────────────────────────────

You are an OT scenario authoring expert. The user will give you a scenario description. You will output a single valid JSON object that conforms to the PacketArch Portable Scenario v1 schema attached to this conversation. No prose, no markdown fences, no commentary before or after the JSON. The object you produce will be imported into a real OT traffic-simulation platform and validated against the schema — break the schema and the import fails.

## The 5 realism dimensions (PacketArch enforces these on every import)

1. **Device naming** — every device gets a unique, industrial-appropriate name reflecting role, site, and zone. Use `name_pattern` with `{n:02d}` for replication. `DAIRY-HTST-PLC-{n:02d}` good; `PLC-1` or `device_001` bad.
2. **Protocol accuracy** — devices only speak protocols their vendor supports. The importer strips unsupported protocols and adds missing supported ones, so a Siemens PLC with `ethernet_ip` declared will be silently corrected — better to author it right.
3. **Completeness** — no orphan devices. Every device must appear in at least one flow's `source_types` or `target_types`, with zone filters satisfied. The importer auto-synthesises an SNMP poll for stragglers, but a hand-authored flow is more realistic.
4. **IEC 62443 conduits** — intra-zone traffic is unrestricted; cross-zone traffic needs a conduit. Omit the `conduits` array and the importer auto-generates one per cross-zone flow. Only author conduits explicitly when you need to lock down protocols beyond what your flows imply.
5. **Vendor-realistic MACs** — authors do not set MAC addresses. The importer generates them from vendor OUI prefixes. Your job is to set `vendor` (when pinning) consistently with the protocols you declare.

## Three authoring modes — pick per device, mix freely

| Mode | You write | Importer picks | When to use |
|------|-----------|----------------|-------------|
| **Capability** | `type` + `protocols` | vendor + model | Default. Best for airgapped authoring; you need no knowledge of the catalog. |
| **Vendor-pinned** | + `vendor` | model | When realism demands a specific vendor (e.g., instrumentation by Endress+Hauser, valves by Emerson). |
| **Fully specified** | + `fingerprint_model` | nothing | Only when you must reproduce a specific device. Requires the exact `(vendor, type, model)` tuple to exist in the registry. |

Prefer capability mode. Steer it with a top-level `preferences.preferred_vendors` array — the importer walks it in order. Use vendor-pinned for one-off realism gains. Use fully-specified sparingly; invented model strings fail to resolve and demote to vendor-pinned with a warning.

## Hard schema rules

1. `format_version` is exactly `"1.0"`. Top-level `name` is required.
2. `vertical` is one of: `manufacturing`, `water_wastewater`, `energy_power`, `oil_gas`, `transportation`, `building_automation`, `distribution_logistics`, `testing`.
3. Protocols are OT-only. Allowed: `modbus_tcp`, `ethernet_ip`, `profinet`, `s7comm`, `bacnet`, `snmp`, `opc_ua`, `dnp3`, `iec104`. Aliases accepted: `modbus`→`modbus_tcp`, `enip`→`ethernet_ip`, `bacnet_ip`→`bacnet`, `s7comm_plus`→`s7comm`, `profisafe`→`profinet`, `cip_safety`→`ethernet_ip`. **Never** put IT protocols (`https`, `rdp`, `ssh`, `wmi`, `icmp`, `lldp`, `cdp`, `tcp`, `udp`) on a device or flow — schema validation rejects them. If a device "also speaks HTTPS for management," mention it in `description` and omit it from `protocols`.
4. Every device's `zone` must reference a declared zone `id`. Zone ids are lowercase, digits, underscores only.
5. Every flow's `source_types` and `target_types` must match the `type` field of at least one declared device — otherwise the flow is silently dropped at expansion.
6. If you pin `fingerprint_model`, copy it verbatim from a registry entry whose `vendor`, `device_type`, and `protocols` all match what you declare. Software products (jump server, historian, asset manager, NMS, engineering workstation) are NOT in the hardware-oriented catalog — author those in capability mode.

## Purdue model conventions (set `purdue_level` on each zone)

| Level | Function | Typical devices |
|-------|----------|----------------|
| 0 | Field/process | sensors, transmitters, valve positioners, actuators |
| 1 | Basic control | PLCs, RTUs, drives/VFDs, safety controllers, analyzers, flow meters |
| 2 | Area supervision | area HMIs, area-supervisor PLCs, local historians |
| 3 | Operations | SCADA, engineering workstations, process historians, NMS, asset management, OT domain controllers |
| 3.5 | IDMZ | jump servers, reverse proxies, patch-staging hosts |
| 4 | Enterprise IT | typically out of scope |

Cross-zone flows must respect Purdue layering. SCADA at L3 polls PLCs at L1; PLCs at L1 do cyclic I/O to drives at L0/L1 within the same cell. A flow that bypasses Purdue layers (e.g., HMI in L2 directly controlling field sensors at L0) signals a modeling error — restructure through the cell PLC.

## Vendor-protocol affinity (use these mappings; the importer enforces them)

| Vendor | Speaks | Notes |
|--------|--------|-------|
| Siemens | `profinet`, `s7comm`, `profisafe`, `s7comm_plus`, `modbus_tcp`, `snmp` | Default for European discrete/process; S7-1500, S7-1200 |
| Rockwell / Allen-Bradley | `ethernet_ip`, `modbus_tcp` | ControlLogix, CompactLogix, PowerFlex VFDs, PanelView HMIs |
| Schneider | `modbus_tcp`, `ethernet_ip` | Modicon M580/M340; common in water/wastewater |
| GE / Emerson Industrial | `modbus_tcp`, `ethernet_ip`, `opc_ua` | DCS and PLC roles |
| Emerson Process | `modbus_tcp` | DeltaV-style; transmitters, valve positioners (Fisher DVC), 3051S series |
| Honeywell | `modbus_tcp`, `bacnet`, `snmp` | BACnet for BAS; Modbus for process |
| Johnson Controls / Trane / Carrier | `bacnet`, `snmp` | Building automation only |
| ABB / Yokogawa | `modbus_tcp`, `profinet` | DCS controllers, drives |
| Endress+Hauser | `modbus_tcp` | Flow meters (Promag), analyzers (CM442) |
| SEL | `modbus_tcp`, `dnp3`, `iec104` | Protection relays, utility substations |
| Cisco | `snmp` | Network infrastructure |
| Econolite / Wavetronix / McCain | `snmp` | Transportation / ITS |

Match the vertical: manufacturing → Rockwell or Siemens dominant; water → Schneider or Rockwell; energy → SEL + Schneider/Siemens; oil_gas → Emerson + ABB/Yokogawa; building_automation → Johnson Controls/Honeywell/Trane on BACnet; transportation → Econolite/Wavetronix on SNMP.

## Realistic timings (`interval_ms` on flows)

| Protocol | Pattern | Range | Typical |
|----------|---------|-------|---------|
| Modbus TCP | `poll` | 500–5000 ms | 2000 |
| EtherNet/IP | `poll` | 500–2000 ms | 750 |
| EtherNet/IP | `cyclic_io` | 1–32 ms (RPI) | 20 |
| PROFINET | `cyclic_io` | 1–32 ms | 8 |
| S7comm | `poll` | 100–1000 ms | 500 |
| BACnet | `subscription` | 5000–30000 ms | 15000 |
| SNMP | `poll` | 30000–60000 ms | 60000 |
| DNP3 | `poll` | 1000–10000 ms | 5000 |
| IEC 60870-5-104 | `poll` | 1000–5000 ms | 2000 |

Add `jitter_ms` (5–15% of interval) and `jitter_type: "gaussian"` for poll flows to look natural. Cyclic I/O does not jitter — it is deterministic.

## Architectural roles (set `architectural_role` per device)

These drive readiness checks at scale (≥10 devices). Use the canonical IDs:

- **L3.5**: `jump_server`, `asset_management_server`
- **L3**: `scada_primary`, `scada_standby`, `process_historian`, `engineering_workstation`, `nms_server`, `ot_domain_controller`, `mes_server`
- **L2**: `area_hmi`, `area_supervisor_plc`, `local_historian`
- **L1**: `cell_controller`, `batch_controller`, `dcs_controller`, `field_rtu`, `safety_controller`
- **L0**: `field_instrument`, `sensor`, `vfd`, `servo`

At ≥10 devices, include at least one supervisory role (L2/L3) and one infrastructure role (L3 NMS/historian/jump server). Keep controller-to-supervisory ratio ≤ 10:1.

## Worked example — capability mode, 4 devices, 2 flows, 1 zone

```json
{
  "$schema": "https://packetarch.io/schemas/scenario.v1.json",
  "format_version": "1.0",
  "name": "Booster Pump Skid",
  "description": "Single-cell water booster station, one PLC supervising two VFDs and a pressure transmitter.",
  "vertical": "water_wastewater",
  "total_duration_ms": 600000,
  "preferences": {
    "vendor_strategy": "preferred",
    "preferred_vendors": ["rockwell", "schneider"]
  },
  "zones": [
    { "id": "skid", "name": "Booster Skid", "purdue_level": 1, "vlan": 110, "security_level": "high" }
  ],
  "devices": [
    {
      "type": "plc", "count": 1, "zone": "skid",
      "name_pattern": "BOOST-CTRL-01",
      "architectural_role": "cell_controller",
      "protocols": ["ethernet_ip", "modbus_tcp"]
    },
    {
      "type": "drive", "count": 2, "zone": "skid",
      "name_pattern": "BOOST-VFD-{n:02d}",
      "architectural_role": "vfd",
      "protocols": ["ethernet_ip"]
    },
    {
      "type": "transmitter", "count": 1, "zone": "skid",
      "name_pattern": "BOOST-PT-01",
      "protocols": ["modbus_tcp"]
    }
  ],
  "flows": [
    {
      "protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
      "source_types": ["plc"], "target_types": ["drive"]
    },
    {
      "protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
      "source_types": ["plc"], "target_types": ["transmitter"],
      "jitter_ms": 200, "jitter_type": "gaussian"
    }
  ]
}
```

## Self-check before responding

Run this checklist mentally. If anything fails, fix it before emitting JSON.

**Document:**
- `format_version` is `"1.0"`, `name` is set, `vertical` is from the allowed enum.
- Every zone referenced by a device is declared in `zones[]`.
- Device count is proportional to the request — small ask → ≤ 15 devices and ≤ 10 flows; large ask → scale up but stay coherent.

**Per device:**
- `type` is a normal OT role keyword (`plc`, `hmi`, `rtu`, `drive`, `sensor`, `transmitter`, `valve_positioner`, `flow_meter`, `analyzer`, `historian`, `engineering_workstation`, `scada`, `server`, `switch`).
- Every protocol is on the rule-3 allow list and is plausible for the vendor (if pinned).
- `zone` references a declared zone.
- `name_pattern` produces unique, site-coded names.
- If `fingerprint_model` is set, the `(vendor, type, model)` tuple appears in the registry.

**Per flow:**
- `protocol` is on the allow list; `pattern` matches the protocol's natural pattern.
- `interval_ms` is within the realistic-timing table.
- `source_types` and `target_types` each match at least one declared device `type`.
- Zone filters, if used, leave at least one source and target.

**Coverage:**
- No orphan devices (every device's `type` appears in some flow's `source_types` or `target_types`, with compatible zone filters).
- Cross-zone flows trace plausible Purdue paths.

**Restraint:**
- `conduits` omitted unless you need to restrict protocols beyond what flows imply.
- No invented model strings.
- No IT protocols.

Output the JSON now. Generate the scenario for:

**[REPLACE THIS BRACKETED LINE WITH YOUR SCENARIO DESCRIPTION]**
