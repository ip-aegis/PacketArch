# Device models/firmware/EOL — verification (agent a390fd4c29c561053)

~40 templates sampled across 20 vendors. VERDICT: STRONG at SKU level, AGING on firmware/CVE.
Every model code maps to a REAL product (no fabricated SKUs). ~95% model_name↔SKU match.
Firmware *schemes* correct per vendor. Two systemic weaknesses: early-2024 freeze + a few
invented firmware *values*.

## (a) Garbled / mislabeled SKU (1)
- **honeywell/controledge/lcnp4m**: LCNP4M is a discontinued TDC-3000 LCN processor card
  (PN 51403776-100), NOT a "ControlEdge PLC". model_name wrong + invented R431.2 firmware.
  → relabel as legacy LCN card OR replace with real ControlEdge CPU.

## Vendor-attribution error (1)
- schneider/micom/p145 (P145, P14x Agile): MiCOM P40 Agile is now **GE Vernova**, not Schneider.
  Also FW scheme off (real "ver91"/sw v52 vs template C3.0/B2.1).

## Likely-invented firmware VALUES (SKU real, version not corroborated)
- Rockwell PowerFlex 753 (20F-D052N103): template V19/V20; public max ~v16.002 (2022)
- Schneider M241 (TM241CE40R): template 3-part V5.2.6/V4.0.5; real is 4-part (v4.0.6.41)
- SEL relays (SEL-751 R151-V4 etc.): scheme OK, specific R-revisions not corroborated

## (b) Most-stale firmware (early-2024 freeze; missing 2024-2026 fw + CVEs)
1. Rockwell ControlLogix 5580 L8xE: capped V32-V35 (2024); real current **V38** (2025) ← most consequential
2. Schneider M580 BMEP584040: V4.10 (2023) vs real **SV04.40**
3. Mitsubishi iQ-R R08CPU: V53 vs real **≥V65**
4. Siemens HMI Comfort/KTP panels: capped V18 vs real **V19/V20/V21**
Whole catalog frozen ~2024-01/02; "latest" fw all carry that date + no CVEs.

## (c) Overall: SKU realism strong (order-code grammar correct: Siemens 6ESxxxx/6AVxxxx,
Rockwell 175x/176x, Schneider BMExxxxxx/TMxxx, ABB 1SAP, GE ICxxx). Firmware schemes match
(DIGSI V9.x, Niagara N4.x, IOS-XE 17.x, TwinCAT builds, ATV IExx). IT/OT vulnerable jump-server
entries intentional + correct. Action: refresh firmware/CVE layer to 2026; fix LCNP4M + MiCOM.
EOL correctly frozen: MicroLogix 1400, TSXP57204M Premium, Win2008R2.
