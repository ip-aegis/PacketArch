# NTCIP over SNMP: sources, confidence and open items

**Status (2026-10-21, Phase 0 of `tasks/its-roadway-remediation-plan.md`).**
Every OID the engine emits now comes from the NTCIP MIB files, through
`_mib_table.py`, which `scripts/ntcip/gen_mib_table.py` generates. Device
behaviour is modelled, not taken from a standard, and is tiered below.

## Sources (fetched 2026-10-21; MIB text is not committed, see the copyright notes)

| Standard | File | Where | Revision |
|---|---|---|---|
| NTCIP 1201 Global | `NTCIP1201-Glo.mib`, `ntcip1201-Global.mib` | github.com/ite-org/NTCIP-1201 | LAST-UPDATED 2022-12-12 |
| NTCIP 1202 ASC | `1202ASC.mib` (ASC-MIB1, v01-era) | github.com/igorpopovicz/SnmpGetAPI `mibs/` | v01 |
| NTCIP 1203 DMS | `NTCIP1203-Dms.mib` | github.com/ite-org/NTCIP-1203 | LAST-UPDATED 2025-04-02 (v04 draft) |
| NTCIP 1204 ESS | `NTCIP1204-Ess.mib` | github.com/ite-org/NTCIP-1204 | v04 |
| NTCIP 1209 TSS | `ntcip1209-Tss.mib` | github.com/ite-org/NTCIP-1209 | no revision clause in the file |

I cross-checked everything against MnDOT IRIS (github.com/mnit-rtmc/iris), a production ATMS that talks to real controllers, signs and RWIS: `comm/ntcip/mib120{1,2,3,4}`, `MessageIDCode`, `DmsMessageCRC` and `CRCStream`.

## Confidence tiers

The tiers follow the rail convention:
- `spec`: verified against a current source.
- `spec_legacy`: taken from an older or deprecated revision.
- `provisional`: reconstructed.
- `synthetic`: invented behaviour.

| Item | Tier | Notes |
|---|---|---|
| Device arcs | spec | ASC `1206.4.2.1`, DMS `.3`, TSS `.4`, ESS `.5`, Global `.6`. The repo previously used `.2`, `.3`, `.4` and labelled `.6` "ramp metering". |
| 1202 object OIDs, table indexing | spec_legacy | Taken from the v01 MIB. The phase/detector/unit/coord nodes are unchanged through v03 (IRIS agrees). |
| 1203 object OIDs | spec | One discrepancy: the ITE v04 file declares `dms MODULE-IDENTITY ::= { devices 6 }`, but its own DESCRIPTION and every deployed sign use `1.3.6.1.4.1.1206.4.2.3`. We use `.3`, and the generator pins that root. |
| 1203 `MessageIDCode` layout (memType u8, msgNum u16 BE, CRC u16 BE) | spec | MIB TEXTUAL-CONVENTION, matching IRIS. |
| 1203 `dmsMessageCRC` | spec | CRC-16 X.25 over MULTI + beacon + pixelService octets, byte-swapped (IRIS `DmsMessageCRC`). Check vector `"123456789"` → `0x906E`. |
| 1204 humidity, wind, precip rate, pressure | spec_legacy | We answer the `essBufr*` objects (`1206.4.2.5.1.*`). v04 marks them **deprecated**, but deployed central software still polls them (IRIS `MIB1204`), so they are what a sensor sees on real networks. |
| 1201 `globalTime` as Counter32 | spec | SYNTAX `Counter`. |
| 1209 object OIDs, `sampleDataTable` indexing (zone, entry, class) | spec | From the ITE file; the OIDs match the ones written in each object's own DESCRIPTION. |
| 1209 deprecated `dataCollectionTable` kept and mirroring entry 2 / class 1 | spec | The MIB says a device that still supports it must report the same data as the new table. |
| 1209 poll pattern (central reads entry 2 of every zone once per 30 s sample period) | provisional | IRIS has no 1209 driver to cross-check against. Per-class bins are not modelled (`numSensorZoneClass` = 1). |
| 1209 lane volume / occupancy / speed | synthetic | Time-of-day demand, a seeded 30 % of stations break down at the peak, occupancy from density times a 6.5 m effective length. Not yet bound to `process_sim`. |
| Signal phase sequencing | provisional | NEMA dual-ring, eight phases, leading lefts, coordinated fixed splits, TOD plans (free at night). At a plan change the running cycle finishes, then one transition cycle (shortway when the phase minimums allow, otherwise dwell) lands the new offset. The display never jumps (guard test). No actuated gap-out or phase skip yet. |
| Site time of day | spec | `site.timezone` (IANA, DST-aware) reaches the engine as `_site_timezone` on both the PCAP and live paths. Without it the engine falls back to container-local time, which is UTC. |
| Calls, detector presence, volume/occupancy | synthetic | Derived from a time-of-day demand curve. Not yet bound to `process_sim` (Phase 1.2). |
| Phases not served at a four-phase intersection | provisional | Masked out of every status bitmap (no red bit). Real controllers vary. |
| DMS message schedule (travel times / incidents / blank) | synthetic | |
| Weather | synthetic | Seasonal, diurnal, fronts, precipitation, fog; shared per scenario. |

## Deviations

- **Unmodelled NTCIP OIDs answer NULL**, not the v2c `noSuchObject` exception. scapy has no `noSuchObject` type, and registering one hijacks scapy's global NULL decoder. Legitimate poll plans only request modelled OIDs, and a guard test enforces that. Attack actions that GET arbitrary OIDs will see NULL.
- **Phase status group 2 (phases 9–16) is not polled.** `maxPhases` = 16 and `maxPhaseGroups` = 2 are advertised for ATC realism, but the model only uses phases 1–8.

## Open items

- Confirm the 1202 v03 MIB (ANSI webstore / ITE). It adds objects under the same nodes, and we don't expect renumbering.
- NTCIP 1207 ramp meter objects are not modelled; ramp meters answer MIB-II only.
- NTCIP 1218 RSU arc (`.18`?) and the 1205 CCTV arc are unverified. Neither is modelled yet (Phases 3 and 4).
- ~~Does Cisco Cyber Vision decode NTCIP?~~ **Yes (CV 5.6, 2026-10-21 replay).** It tags ASC/DMS/ESS/TSS by kind, reads `unitFlashStatus` and `dmsMessageOwner`, and extracts no firmware version from NTCIP devices. Use these properties for CV-facing realism checks.
