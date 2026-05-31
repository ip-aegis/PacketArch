---
name: packetarch-vuln-data-curation
description: How to curate and verify PacketArch vulnerability data — CVEs, firmware versions, attack-playbook MITRE mappings, and device-fingerprint identifiers (OUI/ODVA/PROFINET/BACnet/SNMP) — so it is realistic, current, and internally consistent. Use when adding/editing CVEs, device templates, attack playbooks, or vendor identifier tables.
version: 1.0.0
---

# PacketArch Vulnerability-Data Curation

PacketArch is judged on **fingerprint realism** — Cyber Vision and IDS tooling must
see plausible vendor/firmware/CVE/attack data. Wrong data is worse than no data: it
produces confidently-incorrect fingerprints. The cardinal rule: **never trust a
CVE ID, firmware string, OID, or vendor ID without verifying it against the
authoritative source.** A well-formed schema does not imply correct content — the
2026-05-31 audit found ~75% of CVE→device assignments were real CVEs bolted onto the
wrong product (many not even ICS), bulk-pasted by ID/number-collision.

## The two CVE systems (keep them consistent)
1. **CVE DB** — `backend/app/services/cve_data/*.py` (`<VENDOR>_CVES: list[dict]`).
   Fields: cve_id, title, description, severity, cvss_score, cvss_vector, vendor,
   product_family, affected_models, affected_firmware_min/max, fixed_firmware_version,
   cyber_vision_detectable, detection_method, advisory_url, references,
   mitre_techniques, exploit_available, published_date, `vulnerable_variants[]`
   (protocol identity overrides). Seeded → `CVEVulnerability` +
   `VulnerableFingerprintVariant`; emitted by `cve_fingerprint_service.py`; shown in
   the CVE Browser.
2. **Device-template CVEs** — `firmware_variants[].cves` in
   `backend/app/services/device_templates/vendors/*.py` (display/metadata).
**Every CVE referenced by a template must also exist in the CVE DB**, or it can neither
resolve a vulnerable variant nor appear in the Browser. When you add a CVE to a
template, add the matching DB row (and vice-versa).

## Verifying a CVE (do this for EVERY id)
- Authoritative: NVD REST API
  `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=<ID>` → exact CVSS v3.1
  base score + vector, affected CPE/products, and `vulnStatus` (REJECTED/Awaiting/
  Modified). Cross-check CISA ICS advisories and the vendor PSIRT (Siemens
  cert-portal, Schneider SEVD, Rockwell PSIRT, ABB, etc.).
- Reject if: NVD returns "not found" (RESERVED/unpublished) or `vulnStatus` is
  REJECTED. Such IDs must not ship.
- Confirm the **product** in NVD's affected list actually matches the device you are
  attaching it to. A CVE for engineering-workstation software (Studio 5000, GX Works,
  PCM600, ToolBoxST, QuickSet) is NOT a controller-firmware CVE. A CVE for a different
  vendor/product line is a mis-assignment, not a fingerprint.
- Use NVD's CVSS, not a rounded-up guess. Don't inflate to 9.8/10.0. Note when the
  CNA score differs from NVD and prefer NVD unless there's reason not to.
- `affected_firmware_max` / `fixed_firmware_version` must come from the advisory, in
  the vendor's real scheme. No placeholder URLs (`icsa-YY-XXX-XX`) and no
  "see advisory" fixed-firmware placeholders.
- It is correct and realistic for many field devices (relays, ITS sensors, BAS
  controllers) to have **few or zero** published CVEs. Leave the list empty rather
  than padding it.

## Firmware realism
- Model codes must be real SKUs in the vendor's order-code grammar (Siemens
  6ESxxxx/6AVxxxx, Rockwell 175x/176x, Schneider BMExxxxxx/TMxxx, ABB 1SAP, GE ICxxx).
- Firmware **values** must be real, not just the right scheme — verify against vendor
  release notes (don't invent e.g. PowerFlex 753 V19/V20 when public max is ~v16).
- Keep "latest" firmware current; refresh fw + CVE layer periodically (the catalog
  drifts stale — flagship PLCs were 3-4 majors behind at audit time).
- Vendor attribution changes over time (e.g. MiCOM P14x Agile is now GE Vernova, not
  Schneider; PACSystems is now Emerson). EOL products correctly freeze at their last fw.

## Attack playbooks (MITRE ATT&CK)
- Every technique ID must exist in current ATT&CK and use the right matrix: ICS
  (T0xxx) for OT actions, Enterprise (T1xxx) for IT. Don't use a Mobile-matrix ID
  (e.g. T1437.001) on an IT/OT host — use Enterprise T1071.001.
- Mind technique direction: pushing logic TO a controller is **T0843 Program
  Download** (Lateral Movement); **T0845 Program Upload** is pulling logic OFF (Collection).
- Verify software/group IDs and real-world facts (target, year, protocols): TRITON
  S0609, PIPEDREAM S1045, INDUSTROYER S0604, HAVEX S0093, INDUSTROYER2 S1072, VOLT
  TYPHOON G1017. Match protocols/industries to the real attack (INDUSTROYER2 = IEC-104).
- Snort SIDs must correspond to the named malware's real Talos rule (e.g. TRITON ≈
  45260/45477/45478). Don't claim a SID is a verified Talos rule unless it is.

## Device identifiers (`protocol_engines/vendor_oui.py`, `snmp/oids.py`)
Verify against the registry that owns each namespace; do not assume existing values
are right (audit found BACnet 19/21, PROFINET 5/6, ~18 SNMP OIDs, and several OUIs wrong):
- **OUI** prefixes → IEEE registry (maclookup / Wireshark manuf). Beware embedded-NIC
  footguns (Microchip/Lantronix/Cisco/VMware OUIs on a PLC).
- **ODVA** EtherNet/IP vendor IDs → ODVA Authorized Vendor List (Rockwell=1, Schneider=243).
- **PROFINET** vendor IDs → profibus.com manufacturer ID table (Siemens=42, Rockwell=2).
- **BACnet** vendor IDs → bacnet.org/assigned-vendor-ids (JCI=5, Honeywell=17, Siemens=7).
- **SNMP** enterprise OIDs → IANA Private Enterprise Numbers (iana.org). Keep
  `vendor_oui.py` and `snmp/oids.py` reconciled (no conflicting values).

## Guard rails
Maintain a test asserting: no duplicate CVE IDs in the DB; no placeholder advisory
URLs; no "see advisory" fixed-firmware; every template CVE exists in the DB. This
prevents bulk-paste rot from silently returning.

## Editing safety
When the file-display channel is unreliable, read exact bytes via base64, edit via a
script with `assert count == expected`, and verify with `python -m py_compile` plus
token counts — never blind-edit large generated data files.
