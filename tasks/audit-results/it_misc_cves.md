# IT/boundary + misc CVE batch — verification (agent a7880885a1982ad65)

70 CVEs. Verdicts: OK=18, WRONG_PRODUCT(±)=31, WRONG_CVSS(±)=11, FABRICATED=8, REJECTED=2.

## FABRICATED (not published in NVD — RESERVED/never issued) — REMOVE (8)
CVE-2022-24089 (Trane XL950), CVE-2022-29497 (Advantech ADAM-6052),
CVE-2022-30246 (Carrier 33CS2PP/i-Vu Pro), CVE-2022-30261 (Automated Logic WebCTRL),
CVE-2022-35578 (E+H CM442/Promag), CVE-2022-35586 (McCain/Siemens ITS CP-8000),
CVE-2022-37064 (Kapsch TCS 2000), CVE-2022-37065 (Axis P1448/P1455)

## REJECTED — REMOVE (2)
CVE-2020-14476 (withdrawn; was Econolite ASC/3), CVE-2022-43560 (rejected by Splunk; was KUKA KR C4)

## OK (18) — keep
CVE-2015-2867, CVE-2019-0708, CVE-2019-9569, CVE-2020-11896, CVE-2020-1472,
CVE-2021-22275, CVE-2021-34527, CVE-2021-36205, CVE-2021-36260, CVE-2021-42534,
CVE-2021-44228 (Log4Shell→ALC Java server, OK), CVE-2022-20919 (Cisco IE-4000 IOS),
CVE-2022-33971 (Omron NJ), CVE-2022-34151 (Omron), CVE-2022-37061 (FLIR, same-vendor stretch),
CVE-2023-20198 (Cisco IE IOS XE), CVE-2019-... (see list). [2017-0144 moved to WRONG_CVSS]

## WRONG_CVSS (DB score wrong; product may also be wrong) (11)
- CVE-2017-0144 EternalBlue: 9.8 → 8.8 (product OK, Windows)
- CVE-2020-12495: 6.1 → 8.8 (also product: Ecograph not Liquiline)
- CVE-2020-24650: 5.5 → 9.8 (also product: HPE iMC not SEL)
- CVE-2020-9049: 7.5 → 5.3 (also product: victor/C·CURE not FEC26)
- CVE-2021-31553: 7.5 → 6.5 (also product: MediaWiki not SEL)
- CVE-2021-31986: 9.8 → 6.8 (Axis OS; "ITS Camera" generic)
- CVE-2021-38294: 5.3 → 9.8 (also product: Apache Storm not Wavetronix)
- CVE-2021-41091: 7.5 → 6.3 (also product: Docker/Moby not E+H FieldCare)
- CVE-2023-1617: 7.5 → 9.8 (B&R VC4 not X20 CPU)
- CVE-2023-2745: 8.1 → 6.1 (also product: WordPress not SEL-751)
- CVE-2023-31170: 7.5 → 6.5/5.9 (SEL QuickSet WS sw, not relay firmware)
- CVE-2023-4804: 8.6 → 9.8 (JCI Quantum HD Unity, not Metasys)

## WRONG_PRODUCT (real CVE, wrong device) (31) — detach/relocate
CVE-2018-18472 (WD My Book→Daktronics), CVE-2019-18230 (Honeywell cam→Pelco),
CVE-2020-10292 (KUKA Visual Components→KR C4), CVE-2020-16205 (Geutebrück→Econolite),
CVE-2020-7002 (Delta CNCSoft→Carrier), CVE-2021-21003 (Phoenix FL SWITCH→Beckhoff),
CVE-2021-27654 (Pega→JCI NAE55), CVE-2021-27656 (exacqVision→FLIR),
CVE-2021-27660 (C·CURE 9000→NAE55), CVE-2021-34579 (Phoenix MGUARD DM→AXC F),
CVE-2021-35963 (Orca HCM→Automated Logic), CVE-2022-0778 (OpenSSL→SEL, fab fw R319-V0),
CVE-2022-20923 (Cisco RV routers→IE-3300), CVE-2022-21661 (WordPress→Trane SC+),
CVE-2022-25343 (Olivetti printer→Econolite), CVE-2022-28173 (Hik bridge→DS-2CD7A cam),
CVE-2022-29885 (Apache Tomcat→Kapsch), CVE-2022-30456 (Badminton CMS→Q-Free),
CVE-2022-30619 (AgilePoint→Daktronics), CVE-2022-30620 (Cellinx cam→Wavetronix),
CVE-2022-36324 (Siemens SCALANCE→Q-Free), CVE-2022-36341 (WP plugin→Pelco),
CVE-2022-37953 (GE WorkstationST; detach Carel pCO5+), CVE-2022-38408 (Adobe Illustrator→Vaisala),
CVE-2022-39144 (Siemens Parasolid→Notifier), CVE-2022-40619 (NETGEAR→Distech),
CVE-2022-41666 (Schneider EcoStruxure OTE→Lutron), CVE-2022-44019 (Total.js→Beckhoff),
CVE-2022-44028 (NetScout→Delta), CVE-2023-24523 (SAP Host Agent→Fanuc),
CVE-2023-28831 (Siemens OPC UA→Phoenix AXC F)

## Cross-batch note
CVE-2022-30312 real product = Honeywell Trend IQ, CVSS 6.5 — BOTH DB rows (Niagara 9.8, Saia/Optiflex 9.1) are WRONG_PRODUCT+WRONG_CVSS.

### Worst
1. Systematic IT/web CVE → OT-device mis-attachment (~44% of batch).
2. 10 fabricated/rejected CVEs carrying invented CVSS + firmware.
3. SEL/Beckwith relay CVEs largely bogus (generic lib/WS-sw flaws + invented R###-V# firmware).
