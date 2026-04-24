---
name: packetarch-fingerprint-validator
description: Validate PacketArch device fingerprints — protocol support matrix, vendor OUI rules, firmware fields, identity requirements per protocol, vulnerability variants.
version: 1.0.0
tags: fingerprint, validation, vendor, oui
---

# PacketArch Fingerprint Validator

Use this knowledge when selecting, validating, or repairing a device's
vendor fingerprint. The fingerprint drives *every* realism dimension:
Layer 2 (MAC OUI), Layer 3/4 (TCP stack tuning), protocol identities
(Modbus MEI, EIP CIP Identity, etc.), firmware metadata, and response
timing. A wrong fingerprint silently breaks detection tools.

## Source of Truth

- **Templates**: `backend/app/services/device_templates/` — 295 templates
  across 18 vendor modules. Queryable via MCP tools
  (`get_fingerprint_by_vendor_model`, `search_fingerprints`).
- **OUI data**: `backend/app/protocol_engines/vendor_oui.py`:
  - `VENDOR_OUIS` — per-vendor prefixes
  - `VENDOR_OUI_PREFIXES` — includes vendor-division aliases
  - `get_random_oui_for_vendor(vendor)` — random valid OUI
- **Vendor enterprise OIDs**: `VENDOR_ENTERPRISE_OIDS` in the same file,
  used by the SNMP discovery guardrail.

## Fingerprint Structure

Each template declares:

- `vendor`, `vendor_family`, `model`, `device_type`
- `supported_protocols` — authoritative list of protocol engines this
  fingerprint can run
- `vertical_hints` — verticals where this template is realistic
- Identity sub-objects, one per protocol the template supports:
  - `modbus_identity` — vendor name, product code, MEI object IDs
  - `ethernet_ip_identity` — CIP Identity Object (vendor ID, product code, rev, status, serial, name)
  - `profinet_identity` — station name, vendor ID, device ID
  - `s7_identity` — module name, firmware version, serial
  - `bacnet_identity` — vendor ID, object name, model name, firmware revision
  - `snmp_identity` — sysDescr, sysObjectID, sysName, sysContact
- `firmware.version` — merged into every protocol identity's firmware
  field at apply-time (see `_fingerprints.py::_apply_firmware`)
- `tcp_options` — TTL, window, MSS, window scale, nop_padding
- `response_timing` — Gaussian/lognormal params for realistic jitter

## Protocol Identity Requirements

A device cannot run a protocol unless its fingerprint has the matching
identity block. If `modbus_identity` is missing, Modbus MEI discovery
fails and Cyber Vision sees an unknown device. Mapping:

| Protocol | Required identity key | Canonical response builder |
|---|---|---|
| modbus_tcp | `modbus_identity` | MEI (fn 43) |
| ethernet_ip | `ethernet_ip_identity` | List Services + CIP Identity |
| profinet | `profinet_identity` | DCP Identify.Resp |
| s7comm | `s7_identity` | SZL IDs 0x0011, 0x001C |
| bacnet | `bacnet_identity` | I-Am + Read Property (Device Object) |
| snmp | `snmp_identity` | sysDescr, sysObjectID GET |

The canonical map lives in
`backend/app/protocol_engines/protocols.py::PROTOCOL_TO_IDENTITY_KEY`.

## Validation Algorithm

When handed a `(device, fingerprint)` pair, check in order:

1. **Vendor alignment** — `fingerprint.vendor` must match `device.vendor`
   per `vendor_normalize.normalize_vendor()` (`backend/app/core/vendor_normalize.py`).
2. **Protocol support** — every protocol in `device.protocols` must be
   listed in `fingerprint.supported_protocols`.
3. **Identity coverage** — for every protocol the device uses, the
   fingerprint must have the corresponding identity block populated.
4. **MAC OUI** — `device.mac_address` prefix must be in
   `VENDOR_OUI_PREFIXES[fingerprint.vendor]`. Wrong OUI → regenerate.
5. **Firmware consistency** — if the device declares a firmware
   requirement, ensure it matches `fingerprint.firmware.version`.

## Failure Modes & Remediations

| Failure | Remediation (MCP action) | Notes |
|---|---|---|
| Device has no fingerprint | `assign_fingerprint` | Pick best vendor/model for declared type |
| Device protocols ⊄ fingerprint.supported_protocols | `repair_protocols` | Removes unsupported, adds missing-but-supported |
| MAC OUI mismatches vendor | `regenerate_macs` | Deterministic from fingerprint OUI pool |
| Missing protocol identity | assign a fingerprint that has it; do NOT fake identity bytes | Legacy builders were removed — identity builder plugins are the only path |
| Device wants a CVE variant | `apply_cve` | Overlays vulnerable identifiers on the base fingerprint |

## Selection Heuristics

When choosing a fingerprint for a given device:

- Match **vendor** first — vendor is the hardest constraint (drives OUI,
  enterprise OID, protocol affinity).
- Match **device_type** second — `plc` to `plc`, `drive` to `drive`.
- Match **protocol intent** — if the scenario needs EtherNet/IP, pick a
  Rockwell or Honeywell template; for PROFINET/S7, Siemens.
- Match **vertical_hints** if available — a water-industry template is
  preferred over a generic manufacturing one for water scenarios.

## Vendor OUI Integrity (Realism Dimension 5)

Every device's MAC prefix must match its declared vendor using
IEEE-verified prefixes in `vendor_oui.py`. A Siemens device must start
with a Siemens OUI (e.g. `00:0E:8C`), not a Rockwell one (`00:1D:9C`).
`generate_mac_address()` now accepts an `oui_prefixes` argument — always
pass the fingerprint's OUI pool, don't rely on the random fallback.

## What NOT to do

- Do NOT invent vendor/model pairs — use the MCP fingerprint tools to
  search the catalog.
- Do NOT return the literal string `"Generic"` — pick a real template.
- Do NOT assign a protocol to a device whose fingerprint lacks the
  matching identity; that protocol will fail at agent dispatch.
- Do NOT hand-edit `mac_prefix` — generate it from the fingerprint OUI
  pool via `get_random_oui_for_vendor()`.
