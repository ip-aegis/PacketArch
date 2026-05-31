# Schneider CVE batch — verification (agent a74b469e38bd72fcd)

30 CVEs. 7 clean. Verdicts: OK=7, WRONG_PRODUCT=12, WRONG_PRODUCT+WRONG_CVSS=4, WRONG_CVSS only=1, FABRICATED=1, REJECTED=1.

## FABRICATED (not Schneider at all) — REMOVE (1)
CVE-2017-7579 = **phpMyFAQ** stored XSS (6.1), attached to TSXP57204M Premium PLC.

## REJECTED (RESERVED/unpublished) — REMOVE (1)
CVE-2023-37193 (DB claims Easergy; not in NVD)

## OK (7) — keep
CVE-2018-7760, CVE-2019-6857, CVE-2020-7537, CVE-2021-22779, CVE-2021-22787,
CVE-2022-45788 (M580 OK; but M241/M251/M262/TM5CSLC attachments over-broad — not in affected list),
CVE-2022-45789

## WRONG_CVSS only (1)
- CVE-2021-22714: 7.5→9.8 (PowerLogic ION meters; family ~ok)

## WRONG_PRODUCT + WRONG_CVSS (4)
- CVE-2019-6853: 6.5→6.1; Andover Continuum (not Premium PLC)
- CVE-2021-22772: 9.0→9.8; **Easergy T200 RTU** (not MiCOM relays)
- CVE-2022-0715: 6.8→9.1; **APC Smart-UPS** (not Rack PDU)
- CVE-2022-37300: 8.8→9.8; **Modicon M340/M580 + Control Expert** (not Easergy)

## WRONG_PRODUCT (real CVE, wrong device) (12+)
- CVE-2018-7821: Modicon M221/SoMachine Basic (not Premium)
- CVE-2019-6829: M580/M340 (not Premium)
- CVE-2020-7477: **Quantum 140CPU65** (real!) but attached to CX9680 meter
- CVE-2020-7480: Andover Continuum (DB "Traffic RTU" wrong)
- CVE-2020-7540: M340/Premium/Quantum (DB "M251" wrong)
- CVE-2020-7559: EcoStruxure Control Expert **PLC Simulator** sw (not M241/M251 hw)
- CVE-2020-7561: **Easergy T300** RTU (not M580)
- CVE-2020-7570: EcoStruxure Building Operation WebReports (not HMISTM6)
- CVE-2020-7571: EBO WebReports (not ATV630/930 drives)
- CVE-2021-22778: Control Expert/Process Expert sw (DB "Tunnel RTU" + fw V1.50.598 fabricated)
- CVE-2022-0221: SCADAPack Workbench sw (not HMISTM6)
- CVE-2022-22804: EcoStruxure Power Monitoring Expert (not ATV drives)
- CVE-2022-22805: APC SmartConnect UPS TLStorm (not Galaxy VM)
- CVE-2022-22810: spaceLYnk/Wiser KNX (not CX9680/ION8650)
- CVE-2022-37301: Modicon M340/M580 (not Easergy); 7.2→7.5
- CVE-2022-42972: APC Easy UPS Online Monitoring sw (not HMIST6700)

## Quantum 140CPU note
Real Quantum CVEs (CVE-2020-7477) got mis-assigned to non-Quantum meters — opposite of expected.
HMIGTO5310 carries none; HMI CVEs landed on HMISTM6/HMIST6700 and are all wrong-product.

### Worst
1. CVE-2017-7579 = phpMyFAQ web XSS, fabricated onto a Modicon PLC.
2. Easergy/UPS/meter CVEs systematically bolted onto unrelated devices.
3. Multiple CVSS understated vs NVD (>±0.2), DB downgrades critical meter/UPS CVEs.
