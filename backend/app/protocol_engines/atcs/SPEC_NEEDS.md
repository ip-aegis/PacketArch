# ATCS / EMP — outstanding reference needs

**STATUS (updated after the K-II + S-9356 pass).** The two headline gaps are
CLOSED. What remains is narrow and is about *validating current-revision
behaviour*, not about guessing structure.

## Resolved

- **EMP Class D framing** — implemented from the publicly available **2010 S-9356
  draft**: `STX 0x02 | protocol_version 0x02 | COMMID u32 BE | message_type |
  message_version 0x02 | data_length u32 BE | body | ETX 0x03`. EMP begins at
  Class-D offset 12; `len(classd) == len(emp) + 13`. Message types 1 Data, 2 ACK,
  3 NAK, 4 Keep-alive, 30/31/32/40/41 test+echo. COMMID starts at 1, increments
  per link, rolls 0xFFFFFFFF -> 1. Corroborated by Meteorcomm patent US10160466B1.
- **EMP port** — the invented 5361 is gone. There is no universal port (Class D
  links are installation-configured). Default is now **3001**, a real documented
  Siemens wayside default, treated as a vendor profile rather than a protocol
  constant.
- **ATCS relay-feed frame — VALIDATED LIVE against a real ATCS Monitor 4.1.0
  decoder (2026-07-16).** The decoder accepts and correctly decodes generated
  frames (GFI/Group/SSeq/RSeq/addresses/UsrData all match; "Invalid ATCS Packet
  Length" gone). This SUPERSEDES the earlier reconstructed `QD10PPPA` network
  header. The real frame is: **5-byte RF header** (`address_type | pad_bits |
  RS_block_count | header_CRC16X25(LE, over [0..2])`) then the **datagram**
  (`[5] (GFI<<4)|Group | [6] spare | [7] send_seq<<1 | [8] recv_seq<<1 |
  [9] src_len<<4|dst_len | dst_addr(BCD, dest FIRST) | src_addr(BCD) |
  facility_len | transport(5B) | UsrData | [vital CRC]`) then a **2-byte datagram
  CRC-16/X.25 (LE) over bytes [5:-2]**. `gfi_group` is a REAL wire field at
  offset [5] (verified: 0x68=GFI6/Grp8, 0x25=GFI2/Grp5, 0x6C=GFI6/Grp12) — the
  earlier "display artifact" call was wrong.
- **Both framing CRCs are CRC-16/X.25** (poly 0x1021, init/xor 0xFFFF, reflected,
  stored little-endian) — recovered from a corpus of 7 real frames and verified
  exact. Header CRC over the 3 RF-header bytes; datagram CRC over [5:-2].
- **RF length field** — ATCSMon rebuilds the expected frame length from the RF
  header's RS block-count + pad-bits and REJECTS a mismatch. Relation recovered
  (60 frame-bits/block): `block_count = ceil(8*total_len/60)`,
  `pad_bits = 60*block_count - 8*total_len`. Fits all 8 corpus frames exactly and
  confirmed live (a 1-block-off pad_bits is rejected).
- **Feed transport** — BINARY, one frame per UDP datagram; the frame's `0x23`
  RF address-type octet is the byte ATCSMon renders as `#` (no synthetic `#`
  prefix). TCP 4802 control handshake -> `PORT <n>` assigns a UDP data port
  (30000+); the client's version string doubles as the keep-alive.
- **ATCS transport header** — the real 5 octets: `msg_num<<1|more |
  part_num<<1|e2e_ack | msg_len<<1|vital | label(16-bit)`. The **vital flag lives
  in transport octet 2**, not in the network sequence header. (Spec 250 detail;
  `spec_legacy`.)
- **ATCS BCD** — a zero digit is carried as nibble **0xA**, not 0x0.
- **ATCS vital CRC** — no longer filler. 31-bit CRC, poly
  `x^31+x^30+x^28+x^25+x^19+x^18+x^16+x^15+x^11+x^9+x^7+1` (low mask
  `0x520D8A81`), LSB-first data ordering, register emitted least-significant-octet
  first. Coverage: address-length octet .. end of L7 data.
  **VERIFIED against the K-II mandatory vector `01 02 -> 25 ED BD 70`**, against
  the spec's self-check invariant (message+CRC reduces to zero), and by
  single-bit corruption detection at every octet.

## Confidence tiering

ATCS fields that were **corpus-validated against the live ATCSMon decoder** are
now `spec`: the 5-byte RF header, both CRC-16/X.25 fields, the GFI|Group octet,
spare, send/recv sequences, the address-length octet, and the dest-first BCD
addresses. The **Spec 250 transport header** and the **31-bit vital CRC** stay
`spec_legacy` (spec-derived from the 2005 K-II Version 4.0; not corpus-pinned
byte-for-byte). EMP + Class D fields are `spec_legacy` (Class D is the 2010 S-9356
draft). Territory UsrData content is `synthetic`.

## Still open

| Item | Tier | What would close it |
|---|---|---|
| **Territory-specific UsrData** semantics (per-MCP codeline bit meanings) | synthetic | Private railroad `.mcp` databases; likely permanently synthetic |
| **ITC application message catalog** (real EMP message-type IDs + payload schemas) | synthetic | AAR ITC catalog, or a real BOS<->WIU capture |
| **EMP/Class D current-revision drift** (Class D draft 2010) | `spec_legacy` | A current S-9356 revision, or a real BOS<->WIU capture |
| **ATCS transport header + vital CRC current-revision drift** (K-II 2005) | `spec_legacy` | A current K-II revision, or a real ATCSMon `.log` with vital frames |

**Resolved since the last revision:** the ATCS relay container framing (it's
binary, one frame per UDP datagram, no separate frame-counter octet) and the
frame-length field — both settled by live validation against ATCS Monitor 4.1.0.

## The remaining ask

A **real capture** — narrower now than before:
- **ATCS:** an ATCSMon `.log` (raw hex + decode) — resolves the relay container
  and the frame-counter question, and validates the datagram against current
  behaviour.
- **EMP/ITC:** a **BOS <-> WIU** capture — validates the Class D draft against
  current deployments and supplies the real ITC message catalog.

Neither is required for the structure any more; both are required to claim
*current-revision* fidelity.

## Sources

- **S-9356 Class D** (2010 draft): https://www.scribd.com/document/515832692/S-9356-Class-D-Spec
- **AAR MSRP Section K-II** (ATCS, Version 4.0): https://usermanual.wiki/Document/Standard20Manual20of20ATCS.1375682920.pdf
- Meteorcomm patent US10160466B1: https://patents.google.com/patent/US10160466B1/en
- Siemens wayside manual (documents configurable TCP 3001):
  https://assets.new.siemens.com/siemens/assets/api/uuid%3A5ddef917-9226-4830-a43e-21ae36ec54ce/sig001603a-1-wayside-inspector-a81000-i-i.pdf
- PTC-Sim (EMP v4 reference, MIT): https://github.com/dustinfast/PTC-Sim
- Fortinet `ITCM.Class.D` DPI signature (validation oracle):
  https://fortiguard.com/appcontrol/56843
- AAR MSRP purchase: https://aarpublications.com/msrp.html
