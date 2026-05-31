# Rockwell/GE/Emerson CVE batch — verification (agent a1e324b8783902cdc)

39 CVEs. 6 clean. Verdicts: OK=6, WRONG_PRODUCT=24, WRONG_PRODUCT+WRONG_CVSS=8, WRONG_CVSS only=3, STALE=1.

## OK (6) — keep
CVE-2020-6084 (minor: 1734-AENT vs 1794-AENT family), CVE-2022-1161 (10.0/9.8 defensible),
CVE-2022-30264 (Emerson ROC), CVE-2022-3157 (ControlLogix), CVE-2023-3595 (ControlLogix EN2T),
CVE-2021-22681 (cvss aside, product OK)

## STALE/unverifiable (1)
CVE-2022-29966 (NVD still RESERVED; CISA ICSA-22-179-04 does cover Emerson DeltaV — plausible but score unverifiable)

## WRONG_CVSS only (product OK) (3)
- CVE-2021-22681: 10.0→9.8 (Rockwell Logix)
- CVE-2022-1159: 9.8→7.2 NVD / 7.7 CISA (LOCAL admin AV:L/PR:H — huge overstatement)  ← I confirmed this via NVD
- CVE-2022-46660: 9.8→6.5 (GE Proficy Historian, authn'd file-write)

## WRONG_PRODUCT + WRONG_CVSS (8)
- CVE-2019-10954: 9.8→7.5; MicroLogix→CompactLogix 5370
- CVE-2020-16233: 9.8→7.5; Emerson DeltaV→**Wibu CodeMeter**
- CVE-2021-27426: 9.1→9.8; GE MarkVIe→GE UR relays (B30/D60/F60)
- CVE-2021-27478: 9.1→7.5; GE MarkVIe→**EIPStackGroup OpENer** stack
- CVE-2022-21805: 8.1→6.1; GE relays→**php_mailform** XSS
- CVE-2022-23925: 9.8→8.2; GE PACSystems→**HP PC BIOS**
- CVE-2022-30262: 9.8→7.8; Emerson DeltaV→**Emerson ControlWave** RTU
- CVE-2023-46687: 8.8→9.8; Emerson ROC800→**Rosemount gas chromatograph**

## WRONG_PRODUCT (real CVE, wrong device) (24)
CVE-2017-7924 (MicroLogix 1100 not 1400), CVE-2018-10936 (**PostgreSQL JDBC**; 2 dup DB rows GE Multilin/RX3i),
CVE-2019-10935 (**Siemens WinCC** not GE; 8.6→7.2), CVE-2019-10955 (MicroLogix/CompactLogix 5370 not ControlLogix 5580),
CVE-2019-10971 (**Omron** not Emerson ROC), CVE-2019-13559 (GE MarkVIe ctrl, borderline I/O pack),
CVE-2020-12009 (**Mitsubishi/ICONICS** not GE 850), CVE-2020-12525 (**M&M fdtCONTAINER** not GE),
CVE-2020-14480 (Rockwell **FactoryTalk View** not PanelView), CVE-2020-6088 (Flex I/O 1794-AENT not MicroLogix 1400),
CVE-2020-6949 (**HashBrown CMS** not GE T60), CVE-2020-6998 (CompactLogix 5370/5570 not ControlLogix 5580),
CVE-2021-22682 (**Horner Cscape** not PowerFlex), CVE-2021-44477 (GE **ToolBoxST** sw not B30/D60/F60 relays),
CVE-2022-23127 (**Mitsubishi/ICONICS** not GE Proficy), CVE-2022-2848 (**Kepware KEPServerEX** not PanelView),
CVE-2022-2893 (**RONDS EPM** not GE IC695CPE400), CVE-2022-3079 (**Festo** not GE),
CVE-2022-3156 (Rockwell Studio 5000 Logix Emulate sw not Flex I/O), CVE-2022-3158 (FactoryTalk VantagePoint not PowerFlex),
CVE-2022-3166 (MicroLogix 1100/1400 not CompactLogix/PowerFlex), CVE-2023-3463 (GE **CIMPLICITY** HMI not relays)

### Worst
1. CVE-2022-21805 = php_mailform XSS, on GE protection relays.
2. CVE-2022-23925 = HP PC BIOS, on GE PACSystems RX3i at 9.8.
3. Systemic GE relay/PACSystems mis-mapping (ToolBoxST, OpENer, RONDS, Festo, CIMPLICITY all on GE relays/PLCs).
Plus: pervasive CVSS inflation to 9.8/10.0; dup CVE-2018-10936 (real = postgresql-jdbc).
