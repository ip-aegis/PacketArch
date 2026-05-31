# Multi-vendor OT CVE batch — verification (agent aaacd282e7d21e4a4)

42 CVEs. ~6 clean. Verdicts: OK=6, WRONG_PRODUCT=18, WRONG_PRODUCT+WRONG_CVSS=11, WRONG_CVSS only=5, REJECTED=2.

## REJECTED (not in NVD — RESERVED/unpublished) — REMOVE (2)
CVE-2021-22287 (DB:ABB Relion 9.1), CVE-2021-27510 (Yokogawa AFV10D)

## OK (6) — keep
CVE-2021-20609 (Mitsubishi iQ-R), CVE-2021-34569 (WAGO 750-81xx — confirm 750-8212),
CVE-2021-38395 (Honeywell Experion C200/C300), CVE-2021-38397 (Honeywell Experion),
CVE-2022-30315 (Honeywell Safety Manager FSC), CVE-2022-40265 (Mitsubishi iQ-R)

## WRONG_CVSS only (product OK) (5)
- CVE-2019-18253: 9.8→10.0 (ABB Relion 670)
- CVE-2019-6008: 8.6→7.8 (Yokogawa Exa* Windows sw; DB "CENTUM" partly off)
- CVE-2020-8477: 9.8→8.8 (ABB 800xA)
- CVE-2022-21177: 9.8→8.1 (Yokogawa CENTUM)
- CVE-2023-25078: 9.8→7.5 NVD (Honeywell Experion; CNA says 9.8 — note conflict)

## WRONG_CVSS + WRONG_PRODUCT (11)
- CVE-2020-10628: 9.8→7.5; Experion PKS→**ControlEdge PLC/RTU**
- CVE-2020-6959: 7.5→9.8; Experion→**MAXPRO VMS/NVR** video
- CVE-2020-8481: 7.5→9.8; REF615 not in affected list (ABB 800xA/Symphony)
- CVE-2021-22276: 8.2→5.5; Relion→**free@home System Access Point**
- CVE-2021-22278: 9.1→6.7; ACS880→**PCM600 Update Manager** sw
- CVE-2021-22285: 9.1→7.5; AC500→**SPIET800/PNI800**; advisory ICSA-22-097-02
- CVE-2022-26057: 8.6→7.8; →**ABB Mint WorkBench** installer (local)
- CVE-2022-26143: 8.6→9.8; ABB→**Mitel** MiCollab VoIP DDoS (TP240PhoneHome)
- CVE-2022-30312: 9.8/9.1→6.5; →**Honeywell Trend IQ** (3 conflicting DB rows!)
- CVE-2023-26517: 7.8→4.8; ABB relays→**WordPress "Dashboard Widgets Suite" plugin**
- CVE-2023-26593: 9.8→7.8; ProSafe-RS→Yokogawa **CENTUM** (cleartext pw, local)

## WRONG_PRODUCT (real CVE, wrong device) (18)
CVE-2020-12522 (WAGO PFC100/200→750-8212 coupler), CVE-2020-17409 (**NETGEAR consumer router**→Moxa ioLogik),
CVE-2020-24680 (ABB S+ Operations sw→AC500 PLC), CVE-2020-6960 (MAXPRO video→LCNP4M/SafetyMgr),
CVE-2020-6968 (INNCOM INNControl 3→XL Web), CVE-2020-6994 (**Hirschmann/Belden switch**→Optiflex),
CVE-2021-26264 (Emerson DeltaV→Honeywell JACE), CVE-2022-25164 (Mitsubishi GX Works3 sw→FX5U PLC),
CVE-2022-26006 (**Intel CPU BIOS**→ABB ACS580/CP620), CVE-2022-26007 (**InHand InRouter302**→ABB PM5630/RTU560),
CVE-2022-28613 (Hitachi RTU500→ABB REF615), CVE-2022-30244 (Alerton ACM→XL Web),
CVE-2022-30317 (Experion LX-only→over-attached to 14 Honeywell models),
CVE-2022-30997 (Yokogawa STARDOM→AFV10D analyzers), CVE-2022-40145 (**Apache Karaf**→Honeywell JACE),
CVE-2022-45140 (WAGO PFC100/200→750-8212 coupler), CVE-2023-2184 (**WordPress plugin**→ABB REX640),
CVE-2023-33237 (Moxa TN-5900 router→ioLogik E1210)

### Worst
1. Non-OT/unrelated CVEs on OT devices (NETGEAR, Intel BIOS, Mitel VoIP, Apache Karaf, WordPress plugins).
2. Systematic CVSS inflation to 9.8 (Honeywell/ABB/Yokogawa), ≥16 wrong scores.
3. 2 non-existent CVEs + over-attachment anti-pattern (Experion LX on 14 models; WAGO coupler loaded with PFC-only CVEs).
