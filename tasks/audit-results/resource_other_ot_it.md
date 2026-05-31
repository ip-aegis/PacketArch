# Other OT/IT CVE RE-SOURCE (agent a0cbf6c782d3efd2c) — VERIFIED replacements

Keep-correct: Omron NJ(33971/34151), Mitsubishi iQ-R(20609/40265), WAGO 750-8212(34569),
Cisco IE-4000(20919), Hikvision DS-2CD(36260), Log4Shell on Java BAS(44228).

## PLCs/controllers
- Omron CJ2M-CPU35: REMOVE CVE-2022-34151(=NX/NJ) → ADD CVE-2019-18269(9.8 FINS), CVE-2022-45790(7.5)
- Omron NJ501-1300: KEEP both; fix CVE-2022-33971 cvss→8.1
- Mitsubishi R08CPU: KEEP both; CVE-2022-40265 cvss 8.6
- Mitsubishi FX5U-32MT/ES: REMOVE CVE-2022-25164(=GX Works3 sw) → ADD CVE-2025-7405(7.3 Modbus), CVE-2022-40267(5.9)
- KUKA KR C4: REMOVE CVE-2020-10292(=Visual Components), CVE-2022-43560(=Splunk) → ADD CVE-2021-33016(9.8), CVE-2021-33014(9.8) ICSA-21-208-01
- Fanuc R-30iB Plus: REMOVE CVE-2021-38296(=Spark), CVE-2023-24523(=SAP) → ADD CVE-2021-32998(7.5), CVE-2021-32996(7.5) ICSA-21-243-02
- Fanuc 0i-TF Plus: REMOVE CVE-2023-24523 → ADD none (empty correct)
- Beckhoff CX5130: REMOVE CVE-2021-21003(=Phoenix), CVE-2022-44019(=Total.js) → ADD CVE-2024-41173(8.8), CVE-2024-41175(6.5) [TwinCAT/BSD only]
- Phoenix Contact AXC F 2152: REMOVE CVE-2021-34579(=mGuard DM), CVE-2023-28831(=Siemens) → ADD CVE-2019-10997(7.5), CVE-2019-10998(6.8 AV:P) ICSA-19-155-01
- WAGO 750-8212: KEEP CVE-2021-34569(9.8); REMOVE CVE-2020-12522, CVE-2022-45140 (PFC100/200 over-attach)
- Moxa ioLogik E1210: REMOVE CVE-2020-17409(=NETGEAR), CVE-2023-33237(=TN-5900) → ADD CVE-2016-8359(8.8), CVE-2016-8372(8.1)
- B&R X20CP1586: KEEP CVE-2021-22275(8.6); REMOVE CVE-2023-1617(=VC4)
- Advantech ADAM-6052: REMOVE CVE-2022-29497(fabricated) → ADD CVE-2008-5848(7.3 default pw)
- Carel pCO5+: REMOVE CVE-2022-37953(=GE) → ADD CVE-2019-13553(9.8 pCOWeb default creds) [if pCOWeb card]

## Cisco (IOS vs IOS XE matters!)
- IE-4000-8GT4G-E (classic IOS): KEEP CVE-2022-20919(8.6); CVE-2023-20198 does NOT apply (IOS not IOS XE)
- IE-3300/IE-3500/IE-9320 (IOS XE): KEEP CVE-2023-20198(10.0); IE-3300 also ADD CVE-2022-20919; IE-3300 REMOVE CVE-2022-20923(=RV routers)

## BAS / building
- Carrier i-Vu Pro (Java server): REMOVE CVE-2022-30246(fabricated) → ADD CVE-2021-44228(Log4Shell), CVE-2024-8527
- Carrier 33CS2PP (field ctrl): REMOVE CVE-2022-30246 → ADD none (empty correct; server CVEs don't apply)
- Automated Logic Server/WebCTRL: KEEP CVE-2021-44228; ADD CVE-2017-9650(7.8), CVE-2016-5795(7.8); REMOVE CVE-2022-30261(fabricated)
- Delta Controls enteliBUS: REMOVE CVE-2022-44028(=NetScout) → ADD CVE-2019-9569(9.8 HVACking) ICSA-19-239-01
- Trane SC+: REMOVE CVE-2022-21661(=WordPress) → ADD CVE-2021-38450(9.9), CVE-2021-42534(6.3)
- Trane XL950: REMOVE CVE-2022-24089(fabricated) → ADD CVE-2015-2867(9.8 SSH creds), CVE-2015-2868
- Notifier NFS2-3030: REMOVE CVE-2022-39144(=Siemens Parasolid) → ADD CVE-2020-6974(9.3), CVE-2020-6972(9.1) [NWS-3 gateway]
- Distech EC-BOS-8 (Niagara): REMOVE CVE-2022-40619(=NETGEAR) → ADD Niagara 2025 set CVE-2025-3936/3937/3944/3945 [confirm IDs before ingest]
- Lutron QSN-4T16-S: REMOVE CVE-2022-41666(=Schneider) → ADD none (empty correct)
- JCI NAE55: REMOVE CVE-2021-27654(=Pega), CVE-2021-27660(=C·CURE) → ADD none (CVE-2021-36205 is server-tier; empty correct for engine)
- JCI FEC26: REMOVE CVE-2020-9049(=victor/C·CURE), CVE-2021-36205(server-tier) → ADD none (empty correct)

## ITS/transport (mostly correctly empty)
- Econolite ASC/3-2100 Cobalt: REMOVE CVE-2020-14476(rejected), CVE-2022-25343(=Olivetti) → ADD CVE-2023-0452(9.8), CVE-2023-0451(7.5) [EOS sw]
- Daktronics Venus 1500/7000: REMOVE CVE-2022-30619(=AgilePoint) → ADD none (empty correct)
- Wavetronix HD/Advance: REMOVE CVE-2022-30620(=Cellinx) → ADD none (empty correct)
- FLIR TrafiOne: REMOVE CVE-2022-37061(=FLIR AX8) → ADD none (only ZSL-2018-5490, no CVE)
- Kapsch TCS 2000: REMOVE CVE-2022-37064(fabricated) → ADD none (empty correct)
- Q-Free RSU 5000: REMOVE CVE-2022-36324(=Siemens SCALANCE) → ADD none (empty correct)
- McCain 2070 ATC: REMOVE CVE-2022-35586(fabricated) → ADD none (empty correct)
- Axis P1448-LE: REMOVE CVE-2022-37065(fabricated) → ADD CVE-2018-10661(9.8), CVE-2018-10658(7.5) [confirm fw range]
- Axis P1455-LE: REMOVE CVE-2022-37065(fabricated) → ADD CVE-2023-21412(7.2 LPV ACAP)
- Hikvision DS-2CD7A26G0/P: KEEP CVE-2021-36260(9.8); REMOVE CVE-2022-28173(wrong Hik product)
- Pelco SD436-PG-E1: REMOVE CVE-2022-36341(=WordPress plugin) → ADD none strict (CVE-2018-7827 is Spectra Enhanced, not SD436)
- Vaisala RWIS500: REMOVE CVE-2022-38408(=Adobe) → ADD none (empty correct)
- E+H CM442/Promag 400: REMOVE CVE-2022-35578(fabricated) → ADD none (empty correct)

## Needs 1 more confirmation before ingest: Axis fw ranges, Tridium Niagara 2025 CVE IDs,
## whether catalog models pCO5+/NFS2-3030/NAE as network-facing tier, IE3500 ship date.
