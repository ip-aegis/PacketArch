# Device identifiers (OUI/ODVA/PROFINET/BACnet/SNMP) — verification (agent ab632239c20f32ffe)

⚠️ HIGH-IMPACT but REQUIRES INDEPENDENT RE-VERIFICATION before mass edits. Agent flagged
many SNMP OIDs UNVERIFIABLE; vendor_oui.py claims IEEE-verified. Re-confirm before editing.
Files: backend/app/protocol_engines/vendor_oui.py (primary) + snmp/oids.py (conflicting 2nd table).

## D) BACnet vendor IDs — 19/21 WRONG (worst table; looks invented)
OK: Johnson Controls=5, Honeywell=17.
Corrections (claimed→correct): Siemens 24→7, Schneider 67→10, Automated Logic 86→24,
TAC 95→11, Trane 97→2, Delta 122→8, Distech 165→332, KMC 200→28, Alerton 236→18,
Carel 260→77, Carrier 279→16, Reliable Controls 317→35, Lennox 353→255, McQuay 381→3,
Novar 416→91, Computrols 438→225, Contemporary Controls 489→245.
Source: bacnet.org/assigned-vendor-ids. **RE-VERIFY each before applying.**

## C) PROFINET vendor IDs — 5/6 WRONG (source: profibus.com Man_ID_Table.xml)
OK: Siemens 0x002A(42). WRONG: Rockwell 0x0001→0x0002(2), Schneider 0x0095→0x0129(297),
Cisco 0x0145→0x017F(383), ABB 0x0037→0x0005(5), Phoenix Contact 0x00B8→0x00B0(176).
**RE-VERIFY.**

## B) ODVA (EtherNet/IP) vendor IDs — 1 confirmed wrong, rest unverifiable
OK: Rockwell=1, Omron=47. WRONG: **Schneider 67→243** (confirmed via Schneider ODVA DoC).
UNVERIFIABLE (ODVA has no free list): Siemens 285, ABB 75, Honeywell 50, Emerson 90 (maybe 914),
GE 82, Mitsubishi 121 (collides w/ KUKA?), KUKA 368, Cisco 680, Cognex 112. **VERIFY against ODVA AVL.**

## A) OUI prefixes — many misattributed (IEEE registry)
Whole-vendor-wrong: Emerson's only OUI 00:0D:3A=**Microsoft**; Beckwith's only OUI 00:1A:F0=**Alcatel-Lucent**;
JCI primary 00:1A:17=**Teak**; ABB all 5 wrong (00:21:99 Vacon, 00:24:2B Foxconn, 00:1F:ED Tecan,
00:C0:53 Aspect, C4:93:00 8Devices). Other wrong: siemens 64:6E:97(TP-Link),74:DA:EA(TI),
00:0D:6B(Mita-Teknik); ge 00:30:C1(HP),00:22:52,00:50:99(3Com); sel 00:1C:73(Arista);
yokogawa 00:00:C1(Madge),00:A0:78(Marconi); omron 00:00:74(Ricoh); mitsubishi 00:00:7E,00:04:0F;
trane/carrier 00:0D:AD(Dataprobe); kapsch 00:0B:6B(WNC).
Embedded-NIC footguns (correct for NIC, misleading on PLC): 64:3A:EA=Cisco, 00:1E:C0=Microchip,
00:80:A3=Lantronix, 00:50:C2=IEEE RegAuth, VMware/Hyper-V prefixes on PLC vendors.
Verified OK: Siemens 00:0E:8C/00:1B:1B/00:1C:06/00:1F:F8/AC:64:17, Rockwell 00:00:BC/00:1D:9C,
Schneider 00:00:54/00:80:F4(Telemecanique), Honeywell 00:40:84, SEL 00:30:A7, Cisco 00:0F:34,
Phoenix/WAGO/Moxa/Zebra. **RE-VERIFY before deleting — code claims these are IEEE-checked.**

## E) SNMP enterprise OIDs (PEN) — ~18 WRONG
OK: Siemens 4329, Schneider 3833, Cisco 9, Moxa 8691, Hirschmann 248, Phoenix 4346, WAGO 13576,
Advantech 10297, Axis 368, NTCIP 1206.
WRONG: ABB 26381(=lwIP), Emerson 3530(=BlackBerry), GE 3861(=Fujitsu), Honeywell 2879(=Sonus),
Omron 1103(=Xact), Mitsubishi 18296(=Emigrant Savings Bank!), SEL 1027(=Mitel),
Beckhoff 2510(=Bear Mountain Sw), Tridium 18943(=HealthPartners), JCI 21239(=Geist),
Trane 11108(=WaveMarket), Basler 16654, Beckwith 2456(=Antec), Doble 7037, Yokogawa 2745(=LANCAST),
Rockwell 53148(should be 95?), daktronics+fanuc both 5765 (dup, German optics firm),
vaisala 39165 (collides with Hikvision).
Conflict: snmp/oids.py has a SECOND VENDOR_ENTERPRISE_OIDS disagreeing (kapsch 22706 vs 28846 etc).
**MUST look up real PEN in iana.org/assignments/enterprise-numbers for each before editing.**

### Worst
1. BACnet 19/21 wrong — mis-IDs every BACnet device except JCI/Honeywell.
2. PROFINET 5/6 wrong.
3. SNMP OIDs ~18 wrong — mis-fingerprints sysObjectID.
4. Whole-vendor OUIs wrong (Emerson/Beckwith/JCI/ABB).
5. vaisala/Hikvision OID collision; daktronics==fanuc dup.
