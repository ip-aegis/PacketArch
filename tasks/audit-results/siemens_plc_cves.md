# Siemens PLC/HMI/SCALANCE CVE batch — verification (agent a44754b048aaad0fe)

27 CVEs. Verdicts: OK=6, WRONG_PRODUCT(±WRONG_CVSS)=18, WRONG_CVSS only=2, REJECTED=1, FABRICATED=0.

## OK (6) — keep
CVE-2017-2681, CVE-2021-27383, CVE-2021-31337, CVE-2021-37185, CVE-2021-37205, CVE-2022-40227

## WRONG_CVSS only (product correct) (2)
- CVE-2020-15782: our 10.0 → NVD 9.8 (S7-1200/1500 OK)
- CVE-2022-38465: our 6.8 → NVD 7.8 (S7-1200/1500 OK)

## REJECTED (1)
- CVE-2023-32785: REJECTED at NVD (dup; was a LangChain prompt-injection). Stored as Siemens SIPROTEC 5 medium mapped to 7UM85. **Remove.**

## WRONG_PRODUCT (real CVE, wrong device) (18) — many catastrophic
| CVE | DB/mapped as | NVD real product | our→nvd cvss |
|-----|--------------|------------------|--------------|
| CVE-2015-5374 | SIPROTEC 5 7SS85/7VK87 | SIPROTEC **4**/Compact/EN100 (UDP 50000 DoS) | 10.0(v2) → no v3 (v2 7.8) |
| CVE-2019-10929 | S7-300/400 | S7-1200/1500 MitM (port 102) | 9.8 → 5.9 |
| CVE-2019-13103 | S7-300 | **Das U-Boot** boot loader (AV:L) | 7.5 → 7.1 |
| CVE-2019-13945 | S7-1500 | S7-1200 / S7-200 SMART (physical UART, AV:P) | 7.5 → 6.8 |
| CVE-2019-18285 | SIPROTEC 5 | **SPPA-T3000** App Server | 9.1 → 5.9 |
| CVE-2020-10055 | Siemens ITS CP-8000 | **Desigo CC** (BIRT RCE) | — → 9.8 |
| CVE-2020-15795 | SIPROTEC 5 relays | **APOGEE/TALON / Nucleus NET** DNS | 7.5 → 8.1 |
| CVE-2020-15796 | DXR2.E12 Desigo | ET200SP Open Ctrlr / S7-1500 SW Ctrlr | — → 7.5 |
| CVE-2020-25230 | M60 traffic ctrl | **LOGO! 8 BM** PLC | 7.5 → 7.5 |
| CVE-2020-8568 | SIPROTEC 5 | **Kubernetes Secrets Store CSI Driver** | 7.5 → 6.5 |
| CVE-2022-31465 | Desigo / GAMMA KNX | **Siemens Xpedition Designer** (EDA, AV:L) | 7.8 → 7.8 |
| CVE-2022-32260 | WinCC Professional | **SINEMA Remote Connect Server** | — → 9.8 |
| CVE-2022-32528 | SIPROTEC 5 relays | **Schneider Electric IGSS** (not Siemens) | 8.6 → 9.1 |
| CVE-2022-39158 | DXR2/Desigo CC | **RUGGEDCOM ROS** switches | — → 7.5 |
| CVE-2022-45092 | G120 drive | **SINEC INS** network mgmt | — → 8.8 |
| CVE-2023-28489 | "Traffic Management"/6NH3112 | **SICAM A8000 CP-8031/8050** (SICAM map plausible; DB family+advisory wrong; real SSA ssa-961938) | 9.8 → 9.8 |
| CVE-2023-30899 | SIPROTEC 5 7UM85/7VK87 | **Siveillance Video** Mgmt Server | 6.5 → 8.8 |
| CVE-2024-31486 | SIPROTEC 5 7SS85 | **OPUPI0 AMQP/MQTT** module | 7.5 → 5.3 |

### Worst
1. Systemic "SIPROTEC 5" mislabeling of unrelated CVEs (Kubernetes, LangChain, Schneider IGSS, SPPA-T3000, APOGEE, Siveillance).
2. A REJECTED CVE (CVE-2023-32785) is in the dataset.
3. Pervasive CVSS errors (often >±0.2, wrong direction) + placeholder/wrong advisory URLs.
