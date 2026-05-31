# Identifier corrections — CONFIRMED (agent a4bbc19e8dcb44320)

Only HIGH-confidence rows below are safe to apply. UNRESOLVED = confirmed wrong but
correct value not positively sourced → DO NOT invent; leave or open follow-up.
Caveat: sourced from reliable mirrors (bacnet.org, Wireshark packet-cip.c, oidref.com,
maclookup.app), not primary paywalled registries.

## BACnet vendor IDs — APPLY (16 HIGH; source bacnet.org/assigned-vendor-ids)
Siemens 24→7, Schneider 67→10, Automated Logic 86→24, TAC 95→11, Trane 97→2,
Delta Controls 122→8, Distech 165→332, KMC 200→28, Alerton 236→18, Carel 260→77,
Carrier 279→16, Reliable Controls 317→35, Lennox 353→255, Novar 416→91,
Computrols 438→225, Contemporary Controls 489→245.  (JCI 5, Honeywell 17 already OK)
UNRESOLVED: McQuay 381 (not found in list).

## ODVA EtherNet/IP vendor IDs — APPLY (7 HIGH; source Wireshark packet-cip.c cip_vendor_vals)
Schneider 67→243, Siemens 285→145, ABB 75→46, Honeywell 50→3, GE 82→143,
Mitsubishi 121→161, KUKA 368→121.  (Rockwell 1, Omron 47 already OK)
NOTE: current Mitsubishi=121 is actually KUKA's ID. UNRESOLVED: Emerson 90, Cisco 680, Cognex 112.

## PROFINET vendor IDs — DO NOT APPLY (all UNRESOLVED)
Authoritative profibus.com XML + felser mirror not retrievable. Prior audit's hex values
(Rockwell 2, Schneider 297, Cisco 383, ABB 5, Phoenix 176) UNCONFIRMED. Leave as-is;
open follow-up to source from PI Man_ID_Table.xml.

## SNMP enterprise OIDs (PEN) — APPLY (6 HIGH; source oidref.com/IANA)
ABB 26381→908, Emerson 3530→476, Rockwell 53148→95, Mitsubishi 18296→409,
Omron 1103→16838, Beckhoff 2510→25157.  (Siemens 4329, Schneider 3833, Cisco 9, WAGO 13576 OK)
UNRESOLVED (confirmed WRONG, correct PEN not found — do NOT guess): GE 3861, Honeywell 2879,
SEL 1027, Tridium 18943, JCI 21239, Trane 11108, Basler 16654, Beckwith 2456, Doble 7037,
Yokogawa 2745, Daktronics/Fanuc 5765(dup), Vaisala 39165(=Hikvision), HMS 8284.
NOTE: code comments claiming these are "IANA PEN verified" are FALSE.

## OUI prefixes — APPLY (HIGH; source maclookup.app/IEEE)
- Johnson Controls: remove 00:1A:17 (=Teak) → add 00:10:8D (Johnson Controls Inc)
- ABB: remove 00:21:99(Vacon)/00:24:2B(Foxconn)/00:1F:ED/00:C0:53/C4:93:00 → add 94:F6:65, 00:03:2C, 00:12:93 (ABB Switzerland)
- Basler: remove 00:1E:C9(=Dell) → add 4C:06:8A (Basler Electric)
- Emerson: remove 00:0D:3A (=Microsoft) — UNRESOLVED replacement (00:E0:86 is Emerson Network Power/Avocent, not Emerson Electric)
- Beckwith: remove 00:1A:F0 (=Alcatel-Lucent) — UNRESOLVED (no Beckwith MA-L block in IEEE)
Verified-OK (DO NOT delete): Siemens 00:0E:8C/00:1B:1B, Rockwell 00:00:BC, Schneider 00:00:54/00:80:F4,
Honeywell 00:40:84, SEL 00:30:A7, Moxa 00:90:E8, Phoenix 00:A0:45, WAGO 00:30:DE.

## APPLY SET: 16 BACnet + 7 ODVA + 6 SNMP-PEN + OUI(JCI/ABB/Basler add, 5 deletes + 2 delete-only).
## RECONCILE snmp/oids.py 2nd table to match.
