# ATCS engine — outstanding reference needed to certify byte-accuracy

**Purpose.** PacketArch's ATCS engine generates spec-conformant, labeled ATCS
codeline traffic (the ATCS Monitor relay feed) so it can serve as a training
corpus for a Cisco Cyber Vision rail dissector. This document states exactly
what is still needed so it can be forwarded to someone with AAR standards access.

**STATUS (updated).** The authoritative source has been LOCATED: a free scan of
**AAR MSRP Section K-II** (formerly ATCS Spec 200 = S-5800, plus S-5810/5825/5830
and references to Spec 250) at
`https://usermanual.wiki/Document/Standard20Manual20of20ATCS.1375682920/help`.
Findings from it have already been applied — the frame was **re-layered** from a
wrong wireline-LAPB model to the correct RF model (radio datagram / Appendix G
over radio link / Appendix L), the wireline LAPB byte and HDLC 0x7E flags were
removed, the address encoding was corrected (address-length octet + destination-
first ordering, Appendix D §2.3-2.4), and the 32-bit vital CRC (Appendix Y) was
added for vital messages. **The build host cannot reach the scan directly**
(Cloudflare returns HTTP 521 to datacenter IPs; the ATCSMon wiki host SERVFAILs
even at public DNS resolvers), so the re-layering encodes RELAYED findings.

**Appendix-D transport-packet structure now applied** (from a second, deeper
read of the K-II scan): the packet octet ORDER is modeled — 4-octet prefix
(QD10PPPA + 3 zero octets), address-length octet, **destination address before
source**, facility-length octet, 3-octet transport header (with the transport
vital bit as the LSB of its 3rd octet, §2.11), 2-octet label, UsrData, then the
**internal** 32-bit vital CRC as the last 4 octets (over the address-length
octet .. end of UsrData). Corrections applied: removed the spurious literal
UsrData-length octet (ATCSMon's UsrData=N is derived, not on-wire); removed the
wireline HDLC FCS/0x7E flags (RF integrity is FEC/85-bit blocks, Appendix W,
stripped before the relay); the vital CRC is now INTERNAL and populated with
labelled FILLER (not a fake-valid checksum).

**Wire-format target (DECISION):** the engine emits the **ATCS Monitor server
feed** — an IP monitoring stream (TCP control on 4802 + UDP ASCII-hex frames on
30000+), which is what a Cyber Vision sensor could actually observe. CV never
sees the raw 900 MHz RF. The inner hex is the decoded RF logical frame above.

**REMAINING open items (narrow):**
1. Exact bit widths/positions of the **radio-datagram header** (GFI/Group/SSeq/
   RSeq/Vital, **Appendix G ~K-II-57**) and the **radio-link frame counter**
   (**Appendix L ~K-II-70**) — pages past the extracted scan text. Intra-octet
   packing is provisional; octet order is set.
2. The **vital-CRC polynomial/init/reflection** (**Spec 250 §3.2.1.1 /
   Appendix Y ~K-II-321**) — currently filler.
3. The exact intra-octet layout of the **transport header** octets
   (message#/more, part#/e2e, length) — octet positions set, bit fields provisional.
4. Confirmation of the **ATCS Monitor server-feed container** framing (its own
   normalized protocol) vs. the assumed ASCII-hex-over-UDP model.

The single artifact that resolves 1-3 at once: **one real ATCS Monitor
Capture-To-File (.log) frame — raw hex + the ATCSMon decode of that same frame**
(the Packet Display window). Reverse the bit positions from the byte↔value map.

---

## What we need (in priority order)

### 1. PRIMARY — ATCS codeline frame byte layout (data-link + network header)

**Document:** **AAR ATCS Specification 200 — "Communications System
Architecture," Version 4.0** (in AAR MSRP Section K, Part IV). Specifically the
data-link and network-layer framing sections. Spec **230** ("Base Communications
Package") may also carry the RF codeline framing detail.

**The exact bytes we need pinned down** — the on-wire bit layout of the ATCS
codeline (HDLC) frame's network header. We know the *field set* and sample
*values*; we do NOT have the authoritative *bit positions*:

| Field | What we need | What we currently assume (PROVISIONAL) |
|---|---|---|
| GFI (Group Format Identifier) | bit width + byte offset | 4 bits, high nibble of header byte 0 |
| Group (logical channel) | bit width + byte offset | 4 bits, low nibble of header byte 0 |
| SSeq (send sequence) | bit width + position | 7 bits, header byte 1 (modulo-128) |
| Beacon | bit position | bit 0 of header byte 1 |
| RSeq (receive sequence) | bit width + position | 7 bits, header byte 2 (modulo-128) |
| Vital | bit position | bit 0 of header byte 2 |
| LAPB address/control | exact values + the "Frame=NN" counter mapping | address 0x03, control = counter<<1 |
| ATCS address on-wire encoding | packed BCD? binary? field order | packed BCD, 2 digits/byte |
| UsrData length field | width + position (or is it implicit?) | 1 byte, before UsrData |
| FCS | confirm CRC-16/X.25 (poly 0x1021, init/xorout 0xFFFF, reflected) | assumed CRC-16/X.25 |

A single **fully annotated example frame** (raw hex bytes with each field's
offset/width called out) would resolve all of the above at once.

### 2. SECONDARY — ATCS application message formats (UsrData semantics)

**Document:** **AAR ATCS Specification 250 — "Message Formats" (and data
dictionaries), Version 4.0** (AAR MSRP Section K, Part IV). This defines the
standard codeline message/indication/control payloads that ride in UsrData.
Today those payload bytes are `synthetic` (plausible but invented) because
per-territory bit meanings live in private railroad `.mcp` databases. Spec 250
would let us model realistic standard message formats instead.

---

## What we already have (so the gap is precise — do NOT need these again)

Resolved and byte-accurate (`spec` tier) or confirmed:
- **HDLC framing** — 0x7E flags, no bit-stuffing in the relay's de-stuffed feed.
- **CRC-16/X.25 FCS** — implemented and verified against the standard check
  value (0x906E for "123456789").
- **ATCS address decimal structure** — from the ATCSMon "RF Codeline Protocol
  Reference": 5-series `T-RRR-XX-AAAA` (10 digits) and 7-series
  `T-RRR-CCC-AAA-XXXX` (14 digits), with extension semantics (0202 = field
  indication, 0101 = command & control). Correctly modeled.
- **Protocol behavior** — ATCS is random-access (MCPs transmit spontaneously);
  relay transport is TCP control on ~4802 → UDP feed on 30000+ as ASCII-hex
  frames + version keep-alive. Modeled.

The ONLY provisional pieces are the network-header **bit-packing** (#1) and the
UsrData **application semantics** (#2). Everything else is done.

---

## References / links

**Primary (authoritative, paywalled):**
- AAR MSRP publications (purchase): https://aarpublications.com/msrp.html
- AAR MSRP Section K, Part IV — 2014 index (lists the ATCS 2xx specs):
  https://www.aar.com/standards/MSRPs/MSRP-K-IV.2014Index.pdf
- AAR Technical Services / publications: https://aar.com/standards/publications.html
- Spec set (V4.0): ATCS **200** Communications System Architecture · **210**
  Mobile Communications Package · **220** Front End Processor · **225** Cluster
  Controller · **230** Base Communications Package · **250** Message Formats.

**Community reference (has addressing + behavior; NOT the byte layout):**
- ATCSMon Wiki "RF Codeline Protocol Reference":
  http://atcswiki-beta.greatlakesnetworking.net/index.php/RF_Codeline_Protocol_Reference
  (NOTE: this host's authoritative DNS has been failing globally — SERVFAIL —
  during our work; may be intermittently unreachable.)
- ATCS address breakdown: http://www.atcsmon.com/addresses.html
- ATCS Monitor protocol page: http://www.atcsmon.com/100_4_0.htm
- ATCS Monitor setup + a decoded sample frame + relay ports:
  http://morscher.com/atcs/ATCSmonitoring.html
- Signal Identification Wiki (ATCS RF params + the sample frame
  `5125013826 Frame=34 GFI=2 Group=5 SSeq=77 RSeq=45`):
  https://www.sigidwiki.com/wiki/Automated_Train_Control_System_(ATCS)
- A scanned "Manual Standard of ATCS" (may be MSRP-K excerpt):
  https://usermanual.wiki/Document/Standard20Manual20of20ATCS.1375682920/help

**Background:**
- Wikipedia, Advanced Train Control System:
  https://en.wikipedia.org/wiki/Advanced_Train_Control_System

---

## Acceptable alternatives to the paywalled spec (any ONE resolves #1)

1. The ATCSMon "RF Codeline Protocol Reference" **frame-format** section (if a
   reachable copy exists — the addressing section we already have; we need the
   part that documents the codeline frame bytes, if it exists).
2. An open **Wireshark/decoder** for ATCS codeline (none found publicly to date).
3. **One fully annotated raw frame** — the exact hex bytes of a real ATCS
   codeline frame with each field's offset and bit-width labeled. This alone
   lets us certify `_build_network_header` in
   `backend/app/protocol_engines/atcs/codeline.py`.
4. Vendor documentation (Wabtec/GE, Siemens Mobility, Alstom, Meteorcomm) that
   specifies the ATCS codeline frame byte layout.

---

## Where the fix lands

The provisional layout is isolated in one function,
`_build_network_header()` in
`backend/app/protocol_engines/atcs/codeline.py`, expressly so that certifying it
against the reference above is a one-function change. Until then, every affected
field is labeled `confidence: "provisional"` in the ground-truth output so the
corpus never misrepresents an assumed byte as authoritative.
