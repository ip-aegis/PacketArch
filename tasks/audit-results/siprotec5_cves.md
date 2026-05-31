# SIPROTEC 5 relay CVE dump — verification (agent a689b3e60ea0aaa93)

Corroborates siemens_plc batch. The 8 DB rows tagged product_family="SIPROTEC 5"
(firmware pairs V8.xx→V9.xx) — **0 of 8 genuinely apply to SIPROTEC 5 / 6MD85**. All 8
are real-CVE-ID year/number collisions stamped with a SIPROTEC 5 label + fabricated firmware.

| CVE | real product | verdict |
|-----|--------------|---------|
| CVE-2015-5374 | EN100 / SIPROTEC **4** & Compact / 6MU80 (real fix EN100 V4.25) | WRONG_PRODUCT (v4 not v5); CVSS v2 7.8 / CISA v3 8.6 (DB 10.0) |
| CVE-2019-18285 | SPPA-T3000 App Server | WRONG_PRODUCT; 9.1→5.3 |
| CVE-2020-8568 | **Kubernetes** Secrets Store CSI Driver | WRONG_PRODUCT (not ICS); 7.5→6.5 |
| CVE-2020-15795 | APOGEE/TALON + Nucleus NET DNS | WRONG_PRODUCT; 7.5→8.1 |
| CVE-2022-32528 | **Schneider IGSS** Data Server (not Siemens) | WRONG_PRODUCT; 8.6→9.1 |
| CVE-2023-30899 | Siveillance Video Mgmt Server | WRONG_PRODUCT; 6.5→8.8 |
| CVE-2023-32785 | **LangChain** (REJECTED, dup of CVE-2023-36189) | REJECTED |
| CVE-2024-31486 | SICAM OPUPI0 (CP-8031/8050) | WRONG_PRODUCT; 7.5→5.3 |

## Firmware note
SIPROTEC 5 V8.83 is a plausible real fw, but the per-CVE V8.xx→V9.xx pairs are fabricated
(match no real advisory).

## REAL SIPROTEC 5 CVEs to substitute (sourced from Siemens SSAs)
- CVE-2024-54017 — SIPROTEC 5 weak session IDs / session hijack (SSA-786884; lists 6MD85/CP300; ~5.3). This is the one the data was *trying* to represent.
- CVE-2019-13935 family — EN100/SIPROTEC 5 DoS via TCP/102 (SSA-104088)
- SSA-632562 — SIPROTEC 5 Ethernet plug-in module vulns
