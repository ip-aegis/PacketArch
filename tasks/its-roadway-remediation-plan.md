# ITS / Roadway Improvement and Remediation Plan

**Date**: 2026-10-21
**Source audit**: `docs/ITS_ROADWAY_AUDIT_2026_10.md`
**Goal**: spin up roadway, intersection and traffic-ops scenarios that a DPI tool (Cyber Vision, Zeek, Nozomi, Claroty) decodes as *ITS*. That means signal phases, detector data, DMS messages and SPaT, not generic SNMP identity polls. They should also hold up in front of a traffic-engineering audience.

**Ground rules**
- **Agent versions.** Every phase that touches `backend/app/protocol_engines/` or `docker/packetarch-agent/` bumps `docker/packetarch-agent/app/version.py`: MINOR for new behaviour, PATCH for fixes. PacketNodes consumes these engines as a submodule, so it should bump its pin afterwards.
- **Live and PCAP parity.** Any enrichment added to `traffic_generator/tasks.py` must also land in the agent deploy path (`api/routes/agents.py` → `orchestrator_pool.py`).
- **Verified facts only.** No CVE, PEN, OUI or NTCIP OID goes in without a primary source: NVD, the IANA PEN list, `protocol_engines/data/ieee_oui.csv`, or the NTCIP MIB files. Follow the `packetarch-vuln-data-curation` skill.

---

## Phase 0: Put correct NTCIP on the wire (P1, ship as one unit)

**Why atomic:** setting `device_type` alone yields 330 zero-valued varbinds under the ramp-meter arc (see the audit counterfactual). That is worse than today. The items below land together.

- [ ] **0.1 Confirm the arc map** against the NTCIP 1201/1202/1203/1204 MIB files before writing code. The expected map, which is the acceptance gate:

  | Arc | Standard |
  |---|---|
  | 1206.4.2.1 | ASC |
  | .2 | RMC |
  | .3 | DMS |
  | .5 | ESS |
  | .6 | Global |
  | .7 | CCTV |
  | .10 | TSS |
  | .18 | RSU |

  Record the MIB revision used in a new `protocol_engines/snmp/ntcip/SPEC_NEEDS.md`, using the rail convention with confidence tiers `spec` / `spec_legacy` / `provisional` / `synthetic`.
- [ ] **0.2 Fix the constants** in `snmp/oids.py:26-32` and the definitions in `ntcip_1202.py`, `ntcip_1203.py` and `ntcip_1204.py`. Model the objects as table columns with real indices: `phaseStatusGroupGreens.<group>`, `dmsMessageMultiString.<memType>.<msgNum>`, and so on. Replace the invented `.0` scalars.
- [ ] **0.3 Replace substring matching with exact-OID dispatch** in `engine.py:263-312`: a dict from OID to value-provider. Unknown NTCIP OIDs should return `noSuchObject`, not `INTEGER 0`. Emit the correct ASN.1 types: OCTET STRING for MULTI, Counter or Gauge where the MIB says so.
- [ ] **0.4 Derive `device_type` at runtime** in the shared enrichment layer (`services/scenario_enrichment.py`), so saved scenarios and the hand-authored template path also benefit. Use this precedence:
  1. Explicit `flow.config.device_type`
  2. The destination template's `snmp_identity.ntcip_device_type`
  3. A role/type map: traffic_controller→asc, dms→dms, weather_station/rwis→ess, radar/thermal→tss, ptz/cctv→cctv, rsu→rsu, ramp_meter→rmc

  Call it from both `tasks.py` and the agent deploy path. Add the missing ESS branch to `_get_poll_oids`. **Phase 0 covers ASC, DMS and ESS only**, because those already have object files. The TSS, CCTV, RSU and RMC branches need new object definitions, so they land with their devices in Phases 3 and 4. Until then those roles keep the MIB-II fallback.
- [ ] **0.5 Make phase displays physically consistent.** Interim step: a deterministic 8-phase dual-ring/barrier sequencer keyed on the virtual clock. Reds, yellows and greens must be mutually exclusive per phase, with exactly one green or yellow phase per ring and barrier-compatible pairs (1+5, 2+6, 3+7, 4+8). Phase 1 replaces this with the full engine.
- [ ] **0.6 Small wire fixes**:
  - Startup responses: set the response `dst_port` to the request's source port (`engine.py:398, 410`).
  - `sysUpTime` from virtual time (`engine.py:185-189`).
  - Add the `ntcip→snmp` alias. Either add `rtsp` to the types or stop the comm matrix from selecting it, so flows are not silently dropped at `orchestrator_pool.py:783`.
- [ ] **0.7 Tests**:
  - Rewrite `tests/protocol_engines/test_snmp.py:410-419` and `:1186-1215` to assert the correct arcs and that the branch was taken. A constant 0 must fail.
  - Add a phase-consistency property test: no phase is in two colours, ring and barrier rules hold.
  - Promote `tasks/audit-results/its-ntcip/e2e_ntcip.py` into `backend/tests/integration/test_its_ntcip_on_wire.py`. It should assert more than zero NTCIP varbinds per controller, DMS and ESS, and nonzero, plausible values.
- [ ] **0.8 Bump** `docker/packetarch-agent/app/version.py` (MINOR).
- [ ] **0.9 Find out what Cyber Vision actually decodes.** `docs/cyber-vision/` has no evidence either way. Replay the post-fix PCAP into one of the running CV sensors and record whether CV classifies or decodes NTCIP objects or treats them as generic SNMP. If CV does not decode them, the labeled corpus and parser guide (1.8) carry the demo, and 1.8 moves up to run right after Phase 0. This mirrors how the rail work went.

**Demoable after Phase 0:** a corridor PCAP or live deploy in which Wireshark, with the NTCIP MIBs loaded, shows controllers answering 1202 phase status, DMS signs returning their current MULTI message, and RWIS returning air and pavement readings. Whether Cyber Vision shows the same depends on the result of 0.9.

---

## Phase 0b: Identity and data cleanup (P1, runs in parallel with Phase 0)

These items don't depend on Phase 0. Each is a small, separately reviewable change.

- [ ] **CVEs** (`services/cve_data/transportation_cves.py`):
  - Remove CVE-2020-25230. It is LOGO! 8, confirmed on NVD.
  - Re-scope CVE-2023-28489 to SICAM A8000 CP-8031/8050 (confirmed on NVD) and move it out of the "traffic management" framing.
  - Remove CVE-2015-5386 and CVE-2016-7987 from `siemens/traffic/cp-8000`.
  - Move CVE-2023-0451/0452 to an Econolite Cobalt/EOS template with EOS 3.2.x firmware variants (< 3.2.23 vulnerable).
- [ ] **Duplicate template ids.** `_registry.py:17` keeps the last one registered, so duplicates silently overwrite each other. Fix `schneider/tbox/ms-cpu32`, which currently drops the real DNP3 RTU variant and its CVE-2022-45788. Also fix `schneider/tbox/lt2`, `schneider/altivar/atv320` and the three Rockwell ids. Add a registry assertion that fails on duplicate ids.
- [ ] **Mis-typed templates**:
  - SCALANCE XM-400 → network_switch.
  - The three CP-8000 templates → energy RTU, or delete the ITS-framed copies.
  - Siemens M60 → traffic_controller.
  - Siemens "C600": remove it, or replace it with a real product, and drop BACnet.
  - McCain 170E → Type 170 controller.
- [ ] **PEN and sysObjectID fixes.** Verify each against IANA before changing:
  - Pelco → 25066 (and replace the Schneider OUIs)
  - Bosch → 3967 (drop the Rexroth and automotive OUIs, drop RDP)
  - Vaisala → 16961
  - FLIR → 34674
  - Kapsch TrafficCom → 13182
  - Wavetronix and FLIR detectors → the TSS arc
  - Q-Free RSU → the RSU arc
  - Siemens ITS → Siemens Mobility or Yunex OUI/PEN
- [ ] **Firmware realism**:
  - Cobalt → EOS 3.x.
  - Daktronics: replace Venus with Vanguard VF/VX.
  - Vaisala: replace RWIS500 with RWS200.
  - Axis: drop the "V" prefix.
  - Fix `scenario_templates/transportation.py:326`, which requests a variant that doesn't exist.
- [ ] **ATMS identity.** Re-pin `scada_primary` and the TMC (`vendor_pinning.py:629-633`) from Geo SCADA and EcoStruxure to an ATMS template (Phase 3 adds them; until then, a generic Windows server labelled as the ATMS).
- [ ] **Regenerate** `static/downloads/fingerprint-registry.v1.json` with `scripts/generate_fingerprint_registry_snapshot.py`, and fix the "~300 entries" text at `downloads.py:126`.

**Demoable after Phase 0b:** asset inventories hold up in front of an ITS engineer. There are no energy RTUs posing as signal central, and the CVE list matches real advisories.

---

## Phase 1: Closed-loop intersection behaviour (P1)

- [ ] **1.1 Signal phase engine.** Add `protocol_engines/snmp/ntcip/asc_state.py` as a NEMA dual-ring model. It reads the pattern (cycle, split, offset) per intersection and handles:
  - min green, yellow and red clearance
  - ped walk / ped clear (FDW)
  - actuated gap-out and max-out driven by detector calls
  - coordinated offsets, so adjacent corridor intersections share a cycle and offsets advance down the corridor (a "green wave" that can be seen)
- [ ] **1.2 Bind the process sim.** `process_sim/templates/transportation.py` supplies demand (vehicle_count, queue, ped_demand). The phase engine consumes the demand. Detector occupancy and volume come out of the same model. Existing faults map to wire effects:
  - `signal_stuck_red`: the phase stays red past its max time
  - `coordination_loss`: localCycleCounter drifts from the master
  - `detector_failure`: detector status reports fault and that channel's volume is 0
- [ ] **1.3 Realistic central polling.** One multi-varbind GET per second for the full status block (all phase groups, overlaps, coord status, unit status). Detector volume and occupancy upload once a minute. GETBULK for log retrieval. Hourly 1201 `globalTime` SET for clock sync. Use these engine paths:
  - multi-varbind: `packets.py:199`
  - GETBULK: `packets.py:234`
  - SET: `packets.py:313`
- [ ] **1.4 Missing 1202 groups**: overlaps, preempt status, timebase/day-plan, unit alarm status, and channel/MMU status (`unitFlashStatus`, `unitControlStatus`).
- [ ] **1.5 NTCIP traps** to the TMC on UDP 162: unit alarm, MMU conflict and preempt activation.
- [ ] **1.6 DMS behaviour (1203).** Message table, MULTI strings and an incident-driven activation flow: SET `dmsMessageMultiString`, then `dmsActivateMessage`, then the status reads back. Add ambient polling of lamp, pixel and power status.
- [ ] **1.7 ESS behaviour (1204).** Drive values from a weather process model with diurnal temperature, pavement temperature lagging air temperature, and precipitation events. Polling every 5 minutes is realistic.
- [ ] **1.8 Labeled corpus.** Publish an NTCIP field map on `PacketEvent.metadata`, so `label_sidecar.py` exports ground truth (OID, decoded value, phase state) for detection validation. Write `docs/ntcip-dpi-parser-guide.md`, modelled on the rail guide.
- [ ] Bump the agent version (MINOR).

**Demoable after Phase 1:** a live corridor whose phase timeline can be plotted from captured traffic, from Wireshark/tshark decodes or from the labeled corpus. That holds whether or not CV decodes NTCIP natively. The captured traffic shows coordinated cycles, gap-outs under load, detector counts that track the process sim, and DMS messages that change when an incident is injected.

---

## Phase 2: ITS attack storylines (P1/P2)

Replace the MIB-II-only tamper stages in `its_signal_disruption` (`attacks/playbooks.py:2134, 2155`) and add focused playbooks. Each one ships with the detections it should trigger. These are for detection validation in the generator, and they stay within the existing SNMP SET action family.

- [ ] **Default-community recon, then write.** Community brute-force, a walk of the 1202/1203 subtrees, then a write test.
- [ ] **Signal timing manipulation.** SET `systemPattern` or put the unit into flash from an unexpected source. Because of Phase 1, the phase engine *reacts*: the wire shows flash or the altered pattern. Expected alerts: an SNMP SET from a non-ATMS source, and a pattern or flash state change outside the schedule.
- [ ] **DMS "zombie message" hijack.** A MULTI string write plus activate. Expected alerts: a 1203 SET from an unauthorized host, and message content outside the approved library.
- [ ] **Controller database exfiltration or tamper** over FTP/TFTP (needs the Phase 4 FTP/TFTP engine). Cite ICSA-23-026-01 (Econolite EOS) for context.
- [ ] **Preemption spoofing.** Preempt input activation that no EVP or rail source accounts for.
- [ ] **Rogue RSU / spoofed SPaT** (after Phase 3 adds the RSU).
- [ ] **Cellular-modem pivot**: an external IP, then the modem, then the cabinet controller.
- [ ] **TMC ransomware precursor.** Existing generic IT stages plus a mass SNMP SET to every field device.
- [ ] Update `ai_services/skills/packetarch-ics-attack-playbooks/SKILL.md`. Cite public research (Cerrudo 2014, Ghena et al. 2014) at storyline level only.

**Demoable after Phase 2:** an attack timeline in which the sensor alerts line up with visible changes on the wire, such as a corridor going to flash or a sign changing message.

---

## Phase 3: Device classes and scenario depth (P2)

- [ ] **Fix the scenario plumbing first**:
  - **B1.** Pick one source of truth per road template. Recommendation: archetypes, with hand templates kept only as curated pins via `overrides`. Make the list summary and the created scenario agree. Separate `highway_corridor_its` (freeway: VDS, ramp meters, DMS, CCTV) from `urban_intersection_network` (arterial coordination).
  - **B3.** Dedupe `find_entries` (`comm_matrix/_base.py:162-173`) so a vertical entry overrides the SHARED entry for the same pair.
  - **B4.** Give corridor cabinets real slots for detectors (radar, video, loop card), MMU and modem. Replace the "aux = second controller" pin at `vendor_pinning.py:622`.
- [ ] **New device templates** (verify each identity before adding):
  - MMU/CMU (EDI MMU2-16LEip)
  - V2X RSU (Kapsch RIS-9260, Cohda MK6C, Commsignia)
  - Cellular modems (Cradlepoint IBR900/R1900, Sierra RV55/XR80, Digi IX20)
  - Video detection (Iteris Vantage Next, Autoscope Vision, Miovision, GRIDSMART)
  - EVP/TSP (GTT Opticom)
  - ATC controllers (MaxTime X-1L, Cubic/Trafficware Commander, Peek ATC-1000, McCain ATC eX / Omni eX, Yunex M62)
  - ATMS central (Centracs, Kinetic Signals, Concert, TransSuite)
  - VMS (Genetec, Milestone)
  - Ramp meter on ATC (NTCIP 1207)
  - Travel-time readers (BlueTOAD, BlueARGUS)
  - Lufft and Campbell ESS
  - RUGGEDCOM field switches
  - Add their verified CVEs: MaxTime, Kapsch RIS, Iteris, ALEOS, Cradlepoint, Daktronics. Re-verify each on NVD.
- [ ] **New and deepened archetypes**:
  - Freeway management: mainline VDS, ramp meters with queue detectors, DMS travel times, CCTV.
  - Connected-vehicle corridor: controller to RSU via TSCBM SPaT, RSU to the TMC (NTCIP 1218 SNMPv3), J2735 MAP/SPaT broadcast. Needs Phase 4.
  - TSP/EVP corridor: transit AVL to central, priority requests to the controller, preempt state in 1202.
  - Rail-highway grade-crossing preemption: reuse the rail crossing devices, with a preempt input to the adjacent intersection.
  - Tunnel: restore Modbus/BACnet in the archetype, add a tunnel_controller role (S7-1500 or ControlLogix with WinCC OA), CO/visibility sensors and lane-control signals.
  - Remote access: modem or vendor-cloud backhaul for every cabinet tier, as an option.
- [ ] **Separate process-sim descriptors** for tunnel (ventilation, CO, visibility) and toll (lane throughput, transactions), instead of reusing the intersection model.
- [ ] Update the AI skills (`packetarch-scenario-authoring`, `packetarch-device-naming`) with the new roles.

**Demoable after Phase 3:** a choice of distinct roadway stories (arterial corridor, freeway, connected vehicle, TSP/EVP, grade crossing, tunnel, toll), each with the field gear a DOT would recognise.

---

## Phase 4: Protocol breadth (P2/P3)

In order of demo value:

1. [ ] **TSCBM SPaT** (controller to RSU, UDP 6053), plus **SAE J2735 MAP/SPaT** over UDP from the RSU, driven by the Phase 1 phase engine. Add the 1218 RSU MIB.
2. [ ] **HTTP/HTTPS device web UIs**: controller UI, MaxTime web, Axis VAPIX. Operator sessions from the TMC.
3. [ ] **FTP/TFTP controller database transfer**, used for legitimate nightly backups and for the Phase 2 attack.
4. [ ] **RTSP/RTP camera streams** to the VMS, plus **ONVIF / NTCIP 1205** PTZ control.
5. [ ] **Syslog and SNMP traps** from switches, modems and controllers.
6. [ ] **Cloud detection uplinks**: MQTT/HTTPS from Miovision- or GRIDSMART-class devices.
7. [ ] **NTCIP 2306 / TMDD** centre-to-centre XML/SOAP between two TMCs.
8. [ ] **Legacy transports**: NTCIP 1103 STMP and AB3418 over serial-to-IP, for older cabinets.

Each engine follows `docs/ADDING_NEW_PROTOCOLS.md`, registers in `PROTOCOL_PORTS` (see the silent-44818 gotcha), publishes a label field map, and bumps the agent version.

---

## Sequencing and effort (rough)

| Phase | Depends on | Size |
|---|---|---|
| 0 NTCIP on wire | — | ~3–5 days |
| 0b Identity cleanup | — (parallel) | ~2–3 days |
| 1 Closed-loop intersection | 0 | ~1–2 weeks |
| 2 Attack storylines | 1 (FTP stage needs 4.3) | ~1 week |
| 3 Devices and scenarios | 0b; the CV corridor needs 4.1 | ~2 weeks |
| 4 Protocol breadth | 1 for SPaT | ~1 week per engine |

**Recommended first slice:** Phase 0 plus Phase 0b, then Phases 1.1–1.3. That is the smallest change that turns "SNMP devices" into "a live, coordinated signal corridor" on a sensor.
