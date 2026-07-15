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
- **ATCS datagram** — replaced the reconstructed header with the K-II 5-octet
  network header: `QD10PPPA | logical_channel | send_seq<<1 | recv_seq<<1 |
  src_len<<4|dst_len`. The invented `gfi_group` field is gone (it was an ATCSMon
  *display* artifact, not a wire field).
- **ATCS transport header** — the real 5 octets: `msg_num<<1|more |
  part_num<<1|e2e_ack | msg_len<<1|vital | label(16-bit)`. The **vital flag lives
  in transport octet 2**, not in the network sequence header.
- **ATCS BCD** — a zero digit is carried as nibble **0xA**, not 0x0.
- **ATCS vital CRC** — no longer filler. 31-bit CRC, poly
  `x^31+x^30+x^28+x^25+x^19+x^18+x^16+x^15+x^11+x^9+x^7+1` (low mask
  `0x520D8A81`), LSB-first data ordering, register emitted least-significant-octet
  first. Coverage: address-length octet .. end of L7 data.
  **VERIFIED against the K-II mandatory vector `01 02 -> 25 ED BD 70`**, against
  the spec's self-check invariant (message+CRC reduces to zero), and by
  single-bit corruption detection at every octet.

## Confidence tiering

Spec-derived fields are labelled **`spec_legacy`**, not `spec`: the Class D
document is a **2010 draft** and MSRP K-II is the **2005 Version 4.0** revision.
Structurally authoritative; may not match current deployed revisions.

## Still open

| Item | Tier | What would close it |
|---|---|---|
| **ATCS Monitor relay container** (the ASCII-hex-over-UDP framing around the decoded datagram) | provisional | One real ATCSMon **Capture-To-File `.log`** + its Packet Display decode |
| **`relay.frame_counter`** (prefix octet; not part of the ATCS datagram) | provisional | Same as above — confirm whether it is a relay field at all |
| **Territory-specific UsrData** semantics | synthetic | Private railroad `.mcp` databases; likely permanently synthetic |
| **Current-revision drift** (Class D draft 2010, K-II 2005) | `spec_legacy` | A current S-9356 revision, or a real capture |
| **ITC application message catalog** (real message-type IDs + payload schemas) | synthetic | AAR ITC catalog, or a real BOS<->WIU capture |

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
