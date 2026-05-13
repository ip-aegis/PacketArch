# PROFINET Realism Review

**Date:** 2026-05-07
**Reviewer:** Claude (under Rocky Smith's direction)
**Scope:** PROFINET protocol surface across `backend/app/protocol_engines/profinet/`,
  ambient PROFINET DCP, identity templates, vendor ID mapping, agent wiring,
  and validation harness.
**Method:** four lenses — wire-level capture (Scapy dissection of PCAPs from
  `validate_scenario.py`), spec compliance audit against IEC 61158-6-10,
  CV fingerprinting (deferred to static path), coverage gap catalog.

---

## Executive summary

- **One CRITICAL bug found and fixed** that affected every protocol, not just
  PROFINET: `pcap_writer.py` was passing a float `sec` to scapy's
  `PcapWriter.write_packet()` without splitting microseconds, so all PCAPs
  collapsed to integer-second timestamps. Verified: a 5s test PCAP went from
  6 unique timestamps to 1531 after the fix. Single highest-value change in
  this review.
- **Two PROFINET-specific HIGH findings landed in this PR**: (1) ambient
  PROFINET DCP now has the same early-burst pattern as SNMP/Modbus/EIP/S7
  (regression flagged in `REVIEW_2026_04.md`); (2) the silent Siemens-vendor
  fallback in DCP Identify Response now logs a warning when it fires for a
  non-Siemens fingerprint.
- **Three HIGH findings deferred** to follow-up work because they require
  engine packet-construction changes outside the "report + obvious fixes"
  scope: per-AR frame_id allocation, RT cycle emission rate, RTA alarm
  header field sizing.
- **Vendor ID expansion deferred** because the candidate values from the
  scoping plan (Hilscher 0x0170, Beckhoff 0x0008, etc.) need cross-check
  against an authoritative PNIO list before committing — wrong IDs are
  worse than missing IDs.
- **PROFINET on the wire is structurally correct** (frame IDs, multicast
  MAC, DCP block encoding, RT frame layout, RPC header). The issues are
  timing fidelity and per-flow uniqueness, not byte-level dissection.

---

## Phase 1 — Wire-level inspection

Capture: `siemens_discrete_manufacturing` template, 5000ms PCAP, 36 devices,
66 flows. 2085 packets total — 816 PROFINET L2 (EtherType 0x8892), 282
DCE-RPC (UDP 34964).

### Frame ID distribution observed

| Frame ID | Count | Purpose | Result |
|----------|------:|---------|--------|
| 0xFEFE | 103 | DCP Identify Request | OK — multicast `01:0e:cf:00:00:00`, AllSelector block |
| 0xFEFF | 243 | DCP Identify Response | OK — fingerprinted, vendor_id 0x002A (Siemens), valid station/device blocks |
| 0x8000 | 235 | RT Class 1 Output | Structurally OK, but see F-1, F-2 below |
| 0x8001 | 235 | RT Class 1 Input  | As above |
| 0xFC01 | 0   | RTA Alarm | Not exercised in the 5s capture |
| 0xFF00–0xFF41 | 0 | PTCP Sync/FollowUp/Delay | Not exercised (RT Class 3 IRT not used by this template) |

### Findings

**F-1 (HIGH) — Frame IDs not unique per AR.** All 94 distinct (src_mac,
dst_mac) RT flow tuples in the test PCAP share the same frame_id pair
(0x8000 output, 0x8001 input). Real PROFINET allocates frame_ids uniquely
per (controller, AR) within 0x8000–0xBFFF. CV uses (src_mac, dst_mac,
frame_id) as a flow identifier; sharing frame_ids across ~30 devices risks
merged or split components.
*Status:* deferred — touches engine packet construction (out of Phase 5
scope). See follow-up.

**F-2 (HIGH) — RT cyclic emission rate is 1Hz, not 1ms.** PROFINET RT
inside the test PCAP fires every 1000ms because the orchestrator's default
`flow.poll_interval_ms` is 1000ms (`scenario_builder.py:215`) and PROFINET
flows in the templates don't override `interval_ms`. Real PROFINET RT
runs at 1–10ms cycles; 1Hz is characteristic of slow signaling.
*Status:* deferred — needs scenario template changes (or protocol-aware
default in `scenario_builder.py`).

**F-3 (CRIT, all protocols) — PCAP timestamps truncated to integer
seconds.** `pcap_writer.py:56` passed `sec=<float>` to scapy without
populating `usec=`. Verified: 2085-packet PCAP showed only 6 unique
timestamps before fix, 1531 after fix.
*Status:* **FIXED in this PR** (commit: pcap_writer.py).

**F-4 (LOW) — DCP block padding correct.** NameOfStation block of length
25 (odd) gets a 1-byte pad, confirmed by offset analysis. No issue.

**F-5 (INFO) — Identity content plausible.** DCP Identify Response from
SINAMICS S120 device included: NameOfStation `x-axis-servo-drive-a960`
(synthesized at runtime by `UniqueIdentifierGenerator`), VendorID 0x002A,
DeviceID 0x0501, IPParameter 10.1.0.18, DeviceRole 0x01 (IO-Device),
DeviceOptions list, and OEM string `OrderID:6SL3130-7TE25-5AA3;
SN:A960E29C33FD2E66;Type:SINAMICS S120;HW:1;SW:V5.2`.

---

## Phase 2 — Spec compliance audit

Reference: IEC 61158-6-10 (PROFINET RT/DCP), Wireshark `pn_dcp` / `pn_io`
/ `pn_rt` dissectors as ground truth.

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| S-1 | CRIT | PCAP timestamps truncated to integer seconds (all protocols) | **Fixed** |
| S-2 | HIGH | RT frame_id allocation: all flows share 0x8000/0x8001 | Deferred |
| S-3 | HIGH | RT cyclic emission rate is 1Hz vs 1ms documented | Deferred |
| S-4 | HIGH | Startup-sequence packets share timestamp; will visibly improve once S-1 lands | Partially fixed (via S-1) |
| S-5 | HIGH (alarm flows) | RTA alarm header packs SendSeqNum/AckSeqNum as 1 byte each (`BBBB`); spec is 2 bytes each (`HH`). Total RTA-PDU header is 8 bytes vs spec 12 bytes (also missing VarPartLen) | Deferred |
| S-6 | HIGH (alarm flows) | RTA AlarmNotification missing block wrapper (BlockType/BlockLength/BlockVersion) and ModuleIdent/SubmoduleIdent fields | Deferred |
| S-7 | HIGH | `vendor_id=0x002A` Siemens default silently used when fingerprint lacks `vendor_id` — non-Siemens devices announce as Siemens | **Warn-only fix landed**: `packets.py` logs a warning when fallback fires for non-Siemens vendor; traffic unchanged |
| S-8 | MED | DCE-RPC `drep` field encoded as 4 bytes vs spec 3 bytes (the 4th byte is a benign padding zero); Wireshark dissects either way | Don't fix |
| S-9 | MED | AR Connect Request includes only 1 IOCR (Input CR); real ARs typically have 2 (input+output) | Deferred |
| S-10 | (verified OK) | DCP block BlockInfo values audited — `0x0001` for IPParameter, `0x0000` for Device sub-options, all spec-compliant | — |
| S-11 | LOW | `instance_high=0`, `instance_low=1` defaults — fine for single-instance devices | Don't fix |
| S-12 | LOW | RT cycle counter only goes 1..N over the scenario life because of S-3; will resolve when S-3 lands | — |

---

## Phase 3 — CV fingerprinting outcome

Live CV verification was not performed in this review (no CV pipeline
deployed during the session). As a substitute:

- **`backend/scripts/cv_fingerprint_test.py`**: 39/39 checks pass (post-fix)
  including PROFINET vendor/model/firmware checks against pre-built golden
  PCAPs. This confirms our PROFINET DCP packet shape is dissected
  correctly by Scapy and matches the expected fingerprint strings.
- **`backend/scripts/validate_scenario.py`** across all 19 templates:
  8342 / 8391 checks pass. None of the 49 failures are PROFINET-related —
  they're s7_identity / ethernet_ip_identity / modbus_identity gaps and
  TCP window size mismatches in non-PROFINET protocols. Every PROFINET
  identity check passes.

This static-path verification confirms PROFINET *content* is correct.
The realism issues this review uncovered (F-1, F-2, S-1) are
**timing-domain** issues that the static validators don't measure;
adding timing assertions to `pcap_validators.py` is itself a follow-up.

A future round-trip with a live CV instance is needed to confirm CV's
component-merging behavior in the presence of (a) shared frame_ids and
(b) the now-precise sub-second timestamps.

---

## Phase 4 — Coverage gap catalog

| # | Gap | Severity | Status |
|---|-----|---------:|--------|
| G-1 | `PROFINET_VENDOR_IDS` has only 6 vendors. Missing major fleets: Hilscher, Beckhoff, B&R, WAGO, Omron, Bosch Rexroth, Leuze | HIGH | **Deferred** — vendor IDs need authoritative cross-check before committing; wrong IDs are worse than missing |
| G-2 | RT Class 2 (synchronized RT, 0xC000-0xFBFF) defined but never produced by any poll cycle path | LOW | Don't fix — niche feature |
| G-3 | PROFIsafe (functional safety) has no F-CRC, F-Parameter, or F-Address framing. Agent aliases `profisafe → profinet`, so safety devices emit plain RT cyclic data | MED | Document-only |
| G-4 | I&M0 partially populated (`im0_hw_revision`, `im0_sw_revision`, `im0_serial_number` go into the OEM-ID DCP block). I&M1–I&M5 not generated | LOW | Don't fix — rarely read by CV |
| G-5 | Initial scoping suggested 32 templates missing `station_name`. **False positive**: `FingerprintApplicator.generate_profinet_station_name()` synthesizes unique station names per scenario instance from device_name + vendor + model. Architecture intentionally leaves station_name out of templates so it can be unique-per-deployment. PCAP confirms readable names like `x-axis-servo-drive-a960` are emitted | — | Don't fix |
| G-6 | `SUBOPTION_DEVICE_VENDOR` block emitted only when fingerprint sets `device_vendor` (no template does) | LOW | Don't fix — CV reads vendor from VendorID byte |
| G-7 | DCP IPParameter hardcoded subnet `255.255.255.0` and gateway `0.0.0.0` | LOW | Don't fix |

---

## Phase 5 — Fixes landed

All four fixes below land as separate edits to keep rollback granular.
Each is non-invasive (no engine packet-byte changes, no schema, no agent
version bump).

### 5e — PCAP timestamp precision (CRIT, all protocols)
**File:** `backend/app/traffic_generator/pcap_writer.py`
**Change:** split `timestamp_sec` float into integer `sec` + integer
`usec`, pass both to `ScapyPcapWriter.write_packet()`.
**Verification:** 2085-packet test PCAP went from 6 unique timestamps
(integer seconds only) to 1531 unique timestamps (sub-millisecond
precision). Inter-flow timing now visibly preserved.

### 5a — Ambient PROFINET DCP early-burst regression
**File:** `backend/app/protocol_engines/ambient/noise_generator.py:322-345`
**Change:** added an early DCP burst at warmup_ms + 0.5–1.5s plus 30s/90s
reinforcement bursts, mirroring the pattern other protocols got in commit
`de3eda1`. The `_handle_profinet_dcp` handler already understood
`event["burst"]` to skip steady-state rescheduling, so the only missing
piece was the schedule wiring. New steady-state cadence (every 120s)
remains.
**Verification:** new pytest in
`tests/protocol_engines/ambient/test_noise_generator.py` —
`test_profinet_dcp_fires_within_5s` — asserts at least one DCP event with
`burst=True` is scheduled in the first 5 seconds. All 48 ambient tests
pass.

### 5d — Vendor_id fallback warning (warn-only option)
**File:** `backend/app/protocol_engines/profinet/packets.py`
**Change:** added module-level `logger`. In
`build_dcp_identify_response_fingerprinted()`, when the fingerprint lacks
`vendor_id` AND its `vendor` field is non-Siemens, emit a `WARNING` level
log naming the vendor and model. Traffic is unchanged (still falls back
to Siemens 0x002A so existing scenarios don't break) — the warning gives
operators a diagnosable signal to fix the fingerprint.
**Verification:** all 26 PROFINET tests still pass.

### 5b — Vendor ID table expansion (DEFERRED)
The scoping plan listed candidate values (Hilscher 0x0170, Beckhoff
0x0008, B&R 0x001E, WAGO 0x0276, Omron 0x0129, Bosch Rexroth 0x0010,
Leuze 0x0025). I could not verify these against an authoritative PNIO
ID list during the review session (no internet during the run), and
committing wrong IDs would actively *worsen* CV fingerprinting compared
to the current "fall back to 0x002A" behavior — at least the warn-only
log from 5d makes the fallback diagnosable.

**Action item:** open a follow-up to cross-check each candidate against
the PROFINET conformance database and Wireshark's
`epan/dissectors/packet-pn-rt.c` vendor table before landing.

### 5c — Station_name backfill (NOT NEEDED)
Determined during the review that station_name is intentionally absent
from templates because `FingerprintApplicator.generate_profinet_station_name()`
synthesizes unique values per scenario instance. PCAP inspection
confirmed readable names like `x-axis-servo-drive-a960` are emitted.
The original gap finding was a false positive.

---

## Verification suite (post-fix)

| Check | Result |
|-------|--------|
| `pytest tests/protocol_engines/test_profinet.py` | 26/26 pass |
| `pytest tests/protocol_engines/ambient/` | 48/48 pass (incl. new DCP-fires-within-5s test) |
| `python scripts/cv_fingerprint_test.py` | 39/39 pass (must-stay-100%) |
| `python scripts/validate_scenario.py --duration-ms 5000` (all 19 templates) | 8342/8391 pass; zero PROFINET regressions; failures unchanged from pre-fix baseline (s7/eip/modbus/TCP-window in non-PROFINET protocols) |
| Wire-level: 5s `siemens_discrete_manufacturing` PCAP, post-fix | 2109 packets, 1531 unique timestamps (vs 6 pre-fix), 5236ms span, sub-ms resolution |

Live deploy spot-check (`docker compose up -d --build backend` + tshark
capture on agent mirror) **not run during this session**. Recommended
before next release tag.

---

## Open follow-ups

Ranked by impact. Each is bigger than this review's "obvious low-risk
fixes" scope and should be its own PR.

1. **F-2 / S-3 — Per-flow PROFINET cycle interval.** Add protocol-aware
   defaults in `scenario_builder.py:215` so PROFINET flows default to
   a realistic cycle (e.g. 4ms or 8ms), or surface `interval_ms` on
   PROFINET flow specs in scenario templates. Most operationally
   visible improvement after S-1.
2. **F-1 / S-2 — Per-AR frame_id allocation.** In
   `engine.py:create_initial_state()`, allocate frame_ids from a
   per-controller pool inside 0x8000–0xBFFF instead of hardcoding
   0x8000/0x8001. ~30 line change touching engine and packet
   construction.
3. **G-1 — PROFINET_VENDOR_IDS expansion.** Cross-check candidate IDs
   against authoritative PNIO list, then add. Mechanical change; just
   needs verification work.
4. **S-5 / S-6 — RTA alarm header and AlarmNotification block
   structure.** Current code wouldn't pass PROFINET conformance for
   alarm-bearing flows. Low priority because alarms aren't generated in
   default scenarios, but blocks any future "alarm-driven attack
   playbook" feature.
5. **PROFIsafe (G-3) — F-CRC, F-Parameter, F-Address blocks.** Required
   to make safety devices look real to a CV-aware reviewer. Large
   change; only undertake if a customer specifically asks.
6. **Add timing assertions to `pcap_validators.py`.** This review's
   highest-impact finding (S-1 timestamp truncation) wasn't caught by
   the validator because it doesn't check timestamp distribution. Add
   "PCAP has more than N unique timestamps" and "RT cyclic
   inter-arrival ≤ 50ms" assertions so timing regressions get caught
   automatically.
7. **Live CV round-trip.** Confirm CV's component-merging behavior with
   the new sub-second timestamps and document any phantom-component
   risk arising from F-1 (shared frame_ids).

---

## Cross-references

- Open issue tracked in `docs/REVIEW_2026_04.md` re: PROFINET DCP not
  firing in integration test window — addressed by Phase 5a in this
  review.
- Memory file `architecture_scenario_modes.md` documents the
  `clean_demo_mode` flag that suppresses ambient DCP — verified this
  review preserves that behavior (`_should_profinet_dcp` still respects
  the flag).
