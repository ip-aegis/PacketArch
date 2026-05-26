# PacketArch Portable Scenario — Ready-to-Use LLM Prompt

Hand this file to any capable LLM (Claude Opus 4.x, GPT-5, Gemini 2.x)
alongside the other three files in the Authoring Kit:

  * `packetarch-scenario.v1.json` — JSON Schema (the contract)
  * `SCENARIO_SPEC.md`           — full authoring guide
  * `fingerprint-registry.v1.json` — local device catalog (~300 entries)

Paste everything below the `══` line into the chat, swap the bracketed
scenario sentence for what you want, and send. The LLM should respond
with one valid JSON object you can save as `<your-name>.pascenario.json`
and import via the PacketArch Scenarios page → **Import** button.

══════════════════════════════════════════════════════════════════════

You are generating a PacketArch portable scenario file. PacketArch is an
OT/ICS traffic simulation platform. The file you produce will be
imported via `POST /api/v1/scenarios/import/portable`. You have four
artifacts attached: a JSON Schema (the contract), an authoring guide,
this prompt, and a static catalog of all valid device templates the
PacketArch install will resolve.

## My request

Generate a scenario for:

  **[REPLACE THIS BRACKETED SENTENCE: a small dairy processing plant
  with raw milk receiving, HTST pasteurization, CIP, and one filling
  line.]**

## How to respond

Output **a single valid JSON object** that conforms to the attached
JSON Schema. No prose. No markdown fences. No comments before or after.

## The 10 rules (in priority order — break any of these and import fails)

1. **`format_version` is exactly `"1.0"`**. Top-level `name` is required.

2. **`vertical`** must be one of: `manufacturing`, `water_wastewater`,
   `energy_power`, `oil_gas`, `transportation`, `building_automation`,
   `distribution_logistics`, `testing`.

3. **Protocols must come from this list (exact strings)**:
   `modbus_tcp`, `ethernet_ip`, `profinet`, `s7comm`, `bacnet`, `snmp`,
   `opc_ua`, `dnp3`, `iec104`. Aliases accepted: `modbus`→`modbus_tcp`,
   `enip`→`ethernet_ip`, `bacnet_ip`→`bacnet`, `s7comm_plus`→`s7comm`,
   `profisafe`→`profinet`, `cip_safety`→`ethernet_ip`. **NEVER use IT
   protocols** (`https`, `rdp`, `ssh`, `wmi`, `icmp`, `lldp`, `cdp`,
   `tcp`, `udp`) on devices or flows — they'll be rejected at
   schema-validation time. If a device "also speaks HTTPS for management,"
   leave that out of `protocols`; mention it in `description` if needed.

4. **Prefer CAPABILITY MODE** — for each device, set `type` and
   `protocols` only and OMIT `vendor` and `fingerprint_model`. The
   PacketArch importer picks an appropriate model from its local catalog.
   This is the simplest, most reliable path. Set top-level
   `preferences.preferred_vendors` to a few realistic vendors for the
   vertical to steer the picker (lowercase, drawn from the registry's
   `vendors` array).

5. **If you DO pin `vendor` + `fingerprint_model`**, the exact tuple
   `(vendor, device_type, model, supported protocols)` MUST appear as
   an entry in `fingerprint-registry.v1.json`. Open the registry, find
   an entry where `vendor` AND `device_type` AND your declared
   `protocols` all match, then COPY its `model` field into
   `fingerprint_model`. Never invent a model string. Never copy a model
   from a different vendor. Never copy a model whose `protocols` array
   in the registry is missing what you want to declare.

   **Special trap to avoid**: software products (jump server, historian,
   asset manager, NMS) are NOT in the hardware-oriented catalog. Use
   capability mode for those. The importer will assign a generic
   fingerprint.

6. **Purdue levels** (the `purdue_level` on each zone, 0–5):
   * L0 — field instruments, sensors
   * L1 — PLCs, RTUs, drives, safety controllers, valve positioners,
     analyzers, transmitters
   * L2 — area HMIs, local supervisor PLCs
   * L3 — SCADA, engineering workstations, historians, NMS, asset
     management
   * L3.5 — IDMZ (jump server, reverse proxy)

7. **No orphan devices**. Every device must appear in at least one flow
   (as `source_types` or `target_types`). Cyber Vision can't fingerprint
   a silent device. **Zone filters count** — if you use `source_zones`
   / `target_zones` on a flow, the device's `zone` must satisfy them
   too. Common trap: a jump server in an `idmz` zone with no flow
   targeting `idmz` becomes orphaned even if `server` is in some flow's
   `source_types`. The importer will auto-synthesise an SNMP
   monitoring flow for orphans (so import still succeeds), but you'll
   get more realistic traffic if you author one yourself — e.g. an SNMP
   poll from your NMS to every server you create.

8. **Realistic timings**:
   * Modbus TCP `poll`:        1000–5000 ms (typical 2000)
   * S7comm `poll`:             100–1000 ms
   * EtherNet/IP `cyclic_io`:    1–32 ms (RPI)
   * EtherNet/IP `poll`:       500–2000 ms
   * BACnet `subscription`:   5000–30000 ms
   * SNMP `poll`:           30000–60000 ms
   * DNP3 `poll`:           1000–10000 ms

9. **Naming**: every device gets a unique, site-coded name via
   `name_pattern`. Use `{n:02d}` for replication. Examples:
   `WTP-Filter-PLC-{n:02d}`, `SUB-Relay-{n:02d}`,
   `DAIRY-HTST-PLC-{n:02d}`. Never `PLC-1`, never `device-001`.

10. **Keep it scoped to the request**. Total devices ≤ 15, total flows
    ≤ 10 for small scenarios unless I ask for bigger. Omit `conduits` —
    the importer auto-generates them from your flows.

## Architectural-role values (set `architectural_role` per device)

These drive readiness checks. Use the canonical IDs:

  * Purdue L3.5: `jump_server`, `asset_management_server`
  * Purdue L3:   `scada_primary`, `scada_standby`, `process_historian`,
                 `engineering_workstation`, `nms_server`,
                 `ot_domain_controller`, `mes_server`
  * Purdue L2:   `area_hmi`, `area_supervisor_plc`, `local_historian`
  * Purdue L1:   `cell_controller`, `batch_controller`, `dcs_controller`,
                 `field_rtu`, `safety_controller`
  * Purdue L0:   `field_instrument`, `sensor`, `vfd`, `servo`

## Verification checklist — run through this before responding

For EACH device:
  □ `type` exists in the registry's `device_types` array
  □ Every `protocol` is on the rule-3 allowed list
  □ If you set `vendor` and `fingerprint_model`, the exact tuple
    `(vendor, device_type, model)` appears in the registry, and that
    entry's `protocols` array is a superset of what you declared

For EACH flow:
  □ `protocol` is on the rule-3 allowed list
  □ Every value in `source_types` and `target_types` matches at least
    one declared device `type` (otherwise the flow is dropped)
  □ `pattern` and `interval_ms` are realistic for the protocol (rule 8)

For the document:
  □ `format_version` is `"1.0"`, `name` set, `vertical` is on the rule-2 list
  □ Every `zone` referenced by devices is declared in `zones[]`
  □ Device count ≤ 15, flow count ≤ 10 (unless I asked for bigger)
  □ No orphan devices

Output the JSON now.
