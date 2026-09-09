# Rail Protocol Engines (EMP / ATCS) and Labeled Corpus Export

> Moved out of `CLAUDE.md` on 2026-09-09 so the always-loaded file stays a map. Content unchanged.


Two rail engines back the `ptc_freight_corridor` and `atcs_signaling_territory`
scenarios. Both were built to generate **labeled corpora** — Cisco Cyber Vision
has no rail DPI today, so the goal is spec-conformant traffic Cisco can train a
dissector on (see `--export-labeled-corpus` below).

- **EMP** (`protocol_engines/emp/`) — the AAR Interoperable Train Control message
  envelope (I-ETMS / PTC). **EMP never rides bare on TCP**: AAR S-9356 **Class D**
  (`protocol_engines/emp/class_d.py`) is the mandatory transport, so the TCP
  payload is `Class D header (12B) + EMP + ETX` and EMP begins at Class-D offset
  12. Both the EMP v4 envelope and the Class D framing are byte-accurate. The ITC
  application-message catalog is still unavailable, so message-type IDs and
  payloads are synthetic. There is **no universal port** (Class D links are
  installation-configured); 3001 is a documented Siemens wayside default used as
  the platform's vendor profile.
- **ATCS** (`protocol_engines/atcs/`) — legacy radio codeline (AAR MSRP Section
  K-II, formerly Spec 200), emitted as the **ATCS Monitor relay feed** (the only
  IP-observable form; CV never sees the 900 MHz RF). Models the decoded RF path —
  radio datagram (Appendix G) over radio link (Appendix L) — NOT wireline LAPB.

Both engines publish a **per-field confidence tier** in their label maps so a
training corpus never misrepresents an assumed byte as authoritative:
`spec` (verified against a current source) / `spec_legacy` (spec-derived from a
legacy/draft revision — the 2010 S-9356 Class D draft, AAR MSRP K-II v4.0 2005) /
`provisional` (reconstructed) / `synthetic` (invented). Open items are tracked in
`protocol_engines/atcs/SPEC_NEEDS.md`.

**ATCS gotchas** (all learned the hard way, all spec-confirmed): a zero address
digit is BCD nibble **0xA**, not 0x0; the **vital flag lives in transport octet 2**,
not the network header; the **destination address precedes the source** even though
the length octet carries source length in the *high* nibble; the vital CRC is a
**31-bit** CRC (poly low-mask `0x520D8A81`, LSB-first data, register emitted
LSB-octet-first) covering the address-length octet through end of L7 data —
verified against the K-II vector `01 02 -> 25 ED BD 70`. `gfi_group` was an
ATCSMon *display* artifact and is not a wire field. The relay frame counter is
labelled `relay.frame_counter`, not `atcs.*`, because it belongs to the ATCSMon
container rather than the protocol.

**Gotcha:** never hardcode an L7 offset. Fingerprinted TCP carries options
(timestamps/MSS), so a frame's payload rarely starts at Eth14+IP20+TCP20=54.
Derive it: `len(packet) - len(payload)`.

# Labeled corpus export

`GenerationRequest.export_labeled_corpus=true` makes a run emit
`<stem>.labels.jsonl` + `.meta.json` alongside the PCAP — per-packet ground
truth (protocol, type, `l7_offset`, `encoding`, and the field map) aligned 1:1
with the combined PCAP. Two encodings: `binary` (field bytes at
`l7_offset + off`) and `ascii_hex` (ATCS relay feed — `off`/`len` index the
DECODED frame; bytes are 2 hex chars at `l7_offset + 2*off`). Implemented by
`protocol_engines/label_sidecar.py`; engines opt in by publishing a field map on
`PacketEvent.metadata`.

Frontend protocol types: `frontend/src/types/protocols/` (discriminated union with type guards).

