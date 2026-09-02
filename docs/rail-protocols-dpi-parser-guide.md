# Rail Protocols — Cyber Vision DPI Parser Developer Guide

**EMP (I-ETMS / PTC over Class D) and ATCS (relay-feed codeline)**

This is the reference a developer needs to build a Cyber Vision DPI dissector for
the two North-American rail signaling protocols PacketArch generates. Cyber
Vision has no rail DPI today; PacketArch exists to emit **spec-conformant,
labeled corpora** you can train and validate a dissector against. This document
gives you (1) the labeled-corpus format, (2) byte-accurate frame layouts for both
protocols, (3) parsing algorithms, and (4) an honest map of what is
spec-authoritative vs. synthetic so you don't train the classifier on invented
bytes.

> **Fidelity, up front.** ATCS's wire structure was **validated live against a
> real ATCS Monitor 4.1.0 decoder** — the decoder accepts and correctly decodes
> PacketArch's generated frames. EMP/Class D is implemented from the public 2010
> S-9356 Class D draft + AAR MSRP K-II (2005) and is structurally authoritative
> but not yet checked against a current-revision capture. **Application-layer
> message content (message-type IDs, payload schemas) is synthetic** for both —
> the AAR ITC catalog and per-territory codeline databases are proprietary. Every
> field is tagged with a confidence tier (below); weight your training
> accordingly.

---

## 1. The labeled corpus (your training/validation data)

A PacketArch generation run with `export_labeled_corpus=true` emits three files
alongside the PCAP:

| File | Contents |
|------|----------|
| `<stem>.pcap` | The combined capture (Ethernet/IP/TCP or UDP frames). |
| `<stem>.labels.jsonl` | One JSON object **per packet**, index-aligned 1:1 with the PCAP, giving per-field ground truth. |
| `<stem>.labels.meta.json` | Run summary: schema version, counts, protocol breakdown, field vocabulary. |

### 1.1 Per-packet label record (`.labels.jsonl`)

One compact JSON object per line, in PCAP packet order:

| Key | Present | Meaning |
|-----|---------|---------|
| `pkt` | always | 0-based index into the PCAP (`packets[pkt]` is this frame). |
| `ts_ms` | always | Timestamp (ms). |
| `flow_id` | always | Originating flow. |
| `protocol` | always | `"emp"`, `"atcs"`, `"unknown"`, … |
| `type` | always | Event type, e.g. `atcs_codeline_indication`, `atcs_relay_subscribe`, `tcp_syn` (may be null). |
| `l7_offset` | if known | Byte offset in the packet where the L7 unit begins (see §1.3). |
| `encoding` | always | `"binary"` (both protocols today) or `"ascii_hex"` (see §1.2). |
| `fields` | if labeled | Array of field entries (below). Absent for unlabeled packets (TCP handshake, keep-alives). |

Each entry in `fields`:

| Key | Meaning |
|-----|---------|
| `off` | Field offset **relative to `l7_offset`** (see encoding note). |
| `len` | Field length (bytes, in the decoded frame). |
| `field` | Dotted field name, e.g. `classd.stx`, `emp.version`, `atcs.dst_addr`, `relay.rf_block_count`. |
| `value` | Decoded value (int, string, or a nested object for composite fields). |
| `synthetic` | `true` if the bytes are invented (no public source). |
| `confidence` | `spec` \| `spec_legacy` \| `provisional` \| `synthetic` (see §1.4). |
| `subfields` | (ATCS addresses only) decomposition into `{name, digits}` parts. |
| `note` | (optional) human note, e.g. CRC coverage. |

### 1.2 Mapping a field to bytes — `encoding`

- **`binary`** (both EMP and ATCS today): the field's bytes are
  `packet[l7_offset + off : l7_offset + off + len]`.
- **`ascii_hex`** (a defined alternate; not currently emitted): the L7 payload is
  ASCII-hex *text*; a field is the `2*len` hex characters starting at
  `l7_offset + 2*off`. `off`/`len` index the **decoded** frame (1 decoded byte =
  2 text chars). Handle it if you ingest older corpora, but current rail output
  is `binary`.

### 1.3 `l7_offset` — **do not hardcode 54**

`l7_offset` is *derived per packet* as `len(packet) - len(L7_payload)`. Because
PacketArch fingerprints the TCP stack, frames carry TCP options
(timestamps/MSS/window-scale), so the L7 start is frequently 66, not the classic
`14 (Eth) + 20 (IP) + 20 (TCP) = 54`. Always read `l7_offset` from the record (or
re-derive it); never assume a fixed header length. UDP frames (ATCS feed) have no
options and start at Eth14+IP20+UDP8 = 42, but still: read the field.

**Nested protocols:** offsets are relative to the *outermost* L7 unit. EMP rides
inside Class D, so `emp.*` offsets are **Class-D-relative** and EMP begins at
Class-D offset **12**. ATCS `*` offsets are relative to the ATCS frame's first
byte (the RF address-type octet).

### 1.4 Confidence tiers — train accordingly

| Tier | Meaning | How to use it |
|------|---------|---------------|
| `spec` | Verified against a current primary source **or corpus-validated against the live reference decoder**. | Safe to treat as ground truth for structure. |
| `spec_legacy` | Spec-derived from a legacy/draft revision (2010 S-9356 Class D draft; AAR MSRP K-II v4.0, 2005). Structurally authoritative; may drift from current deployments. | Trust the structure; don't assume exact current-revision values. |
| `provisional` | Reconstructed; reproduces known values, positions unconfirmed. | Use cautiously. |
| `synthetic` | Plausible but invented, no public source. | **Do NOT train the classifier to key on these byte values** (message-type IDs, payload content). Use them only as "there is a payload of length N here." |

`.meta.json` gives `schema_version` (=1), `sidecar`, `packet_count`,
`labeled_count`, `protocol_counts`, and `field_vocabulary` (sorted distinct field
names in the run) — handy for enumerating what your dissector must cover.

---

## 2. EMP (Edge Message Protocol) over AAR Class D

EMP is the AAR Interoperable Train Control (I-ETMS / PTC) application envelope
exchanged between back-office servers (BOS), wayside interface units (WIU), and
locomotive train-management computers. **EMP never rides bare on TCP** — AAR
S-9356 **Class D** is the transport, so the TCP payload is
`Class D header (12B) + body + ETX`, and for a data message the body is the EMP
envelope.

### 2.1 Transport identification

- **TCP.** Default port **3001** — but this is a documented *Siemens wayside
  vendor default and is installation-configurable*; there is no universal/IANA
  Class D port. **Do not classify on port alone.**
- **Classify on the Class D framing invariants** instead:
  - byte `[0] == 0x02` (STX) and `[1] == 0x02` (protocol version),
  - last byte `== 0x03` (ETX),
  - `[8:12]` (big-endian `data_length`) `== len(payload) - 13`,
  - for a Data message (`[6]==1`), EMP begins at `[12]` and `[12] == 0x04` (EMP
    version).
- Cross-reference: Fortinet ships an `ITCM.Class.D` application-control signature
  — a useful independent oracle for your matcher.

### 2.2 Class D frame (byte map, frame-relative offsets)

| Off | Width | Field | Meaning | Value | Tier |
|-----|-------|-------|---------|-------|------|
| 0 | 1 | `classd.stx` | Start marker | `0x02` | spec_legacy |
| 1 | 1 | `classd.protocol_version` | Class D version | `0x02` | spec_legacy |
| 2 | 4 | `classd.commid` | COMMID, uint32 **BE** | per-link counter | spec_legacy |
| 6 | 1 | `classd.message_type` | Message type | see table | spec_legacy |
| 7 | 1 | `classd.message_version` | Message version | `0x02` | spec_legacy |
| 8 | 4 | `classd.data_length` | Body length, uint32 **BE** | `len(body)` | spec_legacy |
| 12 | N | *(body)* | Data msg → full EMP envelope | — | nested |
| 12+N | 1 | `classd.etx` | End marker | `0x03` | spec_legacy |

`len(class_d_frame) == len(body) + 13` (12-byte header + 1-byte ETX).

**COMMID**: starts at 1, increments **independently per link**, rolls
`0xFFFFFFFF → 1` (never 0). A monotonically increasing per-connection COMMID is a
good session/liveness signal.

**Message types** (byte `[6]`):

| Value | Type | Body |
|-------|------|------|
| 1 | Data | Full EMP envelope |
| 2 | ACK | Acknowledged COMMID (4B BE) |
| 3 | NAK | NAK'd COMMID (4B BE) + 1-byte error code |
| 4 | Keep-alive | *(empty)* |
| 30 | Conformance test | — |
| 31 / 32 | Test echo request / response | — |
| 40 / 41 | Operational echo request / response | — |

### 2.3 EMP v4 envelope (byte map, EMP-relative offsets; all multi-byte **big-endian**)

| Off | Width | Field | Meaning | Tier |
|-----|-------|-------|---------|------|
| 0 | 1 | `emp.version` | **EMP version = 4** (the "EMP v4" marker) | spec_legacy |
| 1 | 2 | `emp.msg_type` | Message type/number | spec_legacy (values = platform convention) |
| 3 | 1 | `emp.msg_version` | Message version = 1 | spec_legacy |
| 4 | 1 | `emp.flags` | Flags (0 in this corpus) | spec_legacy |
| 5 | 3 | `emp.body_size` | 24-bit body size = `4 (CRC) + len(payload)` | spec_legacy |
| 8 | 1 | `emp.var_hdr_size` | Variable-header size = `len(sender)+len(dest)+2` | spec_legacy |
| 9 | 2 | `emp.ttl_s` | Time-to-live (s), default 120 | spec_legacy |
| 11 | 2 | `emp.qos` | Quality of service, default 0 | spec_legacy |
| 13 | len+1 | `emp.src_addr` | NUL-terminated ASCII sender (e.g. `aar.w.wiu007`) | spec_legacy |
| … | len+1 | `emp.dst_addr` | NUL-terminated ASCII destination (e.g. `aar.b.bos`) | spec_legacy |
| `13+var_hdr_size` | var | *(payload)* | Application body (WIU status / WDC / ACK / registration) | **synthetic** |
| `total-4` | 4 | `emp.crc32` | CRC-32 over all preceding EMP bytes, packed as signed `>i` (PTC-Sim semantics) | spec_legacy |

Fixed common header = 8 bytes `[0:8]`; the variable header's fixed part
(`var_hdr_size`, `ttl`, `qos`) = 5 bytes `[8:13]`; then the two NUL-terminated
ASCII addresses; then the payload; then the 4-byte CRC-32 trailer. Minimum EMP
message = 20 bytes.

**Addresses** follow an `aar.<node-class>.<name>` convention (`w`=wayside,
`b`=back-office, `l`=locomotive in this corpus). The *structure* is realistic;
exact names are derived from device identity.

### 2.4 Parsing algorithm (EMP)

```
parse_tcp_payload(buf):
    if buf[0]!=0x02 or buf[1]!=0x02 or buf[-1]!=0x03: not Class D
    commid  = u32be(buf[2:6]); mtype = buf[6]; dlen = u32be(buf[8:12])
    if dlen != len(buf) - 13: framing error (or reassembly needed)
    body = buf[12:12+dlen]
    if mtype == 1:                       # Data → EMP
        emp = body
        assert emp[0] == 4               # EMP version
        msg_type   = u16be(emp[1:3])
        body_size  = u24be(emp[5:8])
        vhdr       = emp[8]
        sender, i  = read_cstring(emp, 13)
        dest,   j  = read_cstring(emp, i)
        payload    = emp[13+vhdr : len(emp)-4]
        crc32      = s32be(emp[-4:])      # verify over emp[:-4] (optional, strong signal)
    elif mtype == 2: acked_commid = u32be(body[0:4])
    elif mtype == 3: nak_commid   = u32be(body[0:4]); err = body[4]
    elif mtype == 4: keepalive
```

### 2.5 What to trust vs. ignore (EMP)

- **Trust (spec_legacy):** all Class D + EMP-envelope *structure* — framing, STX/
  ETX, COMMID, `data_length`, EMP version, `body_size`, `var_hdr_size`, TTL, QoS,
  the NUL-terminated addresses, the CRC-32.
- **Do not overfit (synthetic):** `emp.msg_type` *values* and the payload byte
  schemas. The real AAR ITC message catalog is proprietary; PacketArch's message
  numbers and payloads are invented. Classify EMP on the *envelope*, not on
  specific application message numbers.

---

## 3. ATCS (relay-feed codeline)

ATCS (Advanced Train Control System, AAR MSRP Section K-II, formerly Spec 200) is
a legacy 900 MHz RF codeline. **The only IP-observable form is the ATCS Monitor
relay feed**: base-station relays decode the RF codeline and stream the decoded
frames over IP to dispatch/CTC subscribers. Cyber Vision never sees the RF — it
sees this feed. **This layout was validated live against a real ATCS Monitor
4.1.0 decoder.**

### 3.1 Feed transport identification

1. Subscriber opens **TCP to port 4802** (relay control listener; configurable).
2. Subscriber sends an ASCII line `ATCSMON <version>\n` (subscribe).
3. Relay replies `PORT <n>\n`, assigning a **UDP data port (30000+)**.
4. Relay streams **binary ATCS frames over UDP**, **one frame per datagram**.
5. The subscriber periodically sends its version string as a keep-alive.

Classify the **UDP codeline frames** (not the TCP control channel) on the frame's
self-consistency (§3.3–3.4): the two CRC-16/X.25 checks passing is a very strong,
low-false-positive signal. Port 4802/30000+ are configurable — don't rely on them
alone.

### 3.2 Frame structure (byte map)

A frame is a **5-byte RF header** + the **datagram** + a **2-byte datagram CRC**:

| Off | Width | Field | Meaning | Tier |
|-----|-------|-------|---------|------|
| 0 | 1 | `relay.rf_address_type` | `0x23` ground datagram (renders as `#`), `0xFF` broadcast, `0x00` CC_ID | spec |
| 1 | 1 | `relay.rf_pad_bits` | Pad bits in the last Reed-Solomon block | spec |
| 2 | 1 | `relay.rf_block_count` | **# Reed-Solomon blocks — the length field** (§3.5) | spec |
| 3 | 2 | `relay.rf_header_crc` | CRC-16/X.25 over `[0:3]`, **little-endian** | spec |
| 5 | 1 | `atcs.gfi_group` | `(GFI << 4) \| Group` | spec |
| 6 | 1 | `atcs.spare` | Reserved (0x00) | spec |
| 7 | 1 | `atcs.send_sequence` | Send seq `N(S)`, value = `byte >> 1` | spec |
| 8 | 1 | `atcs.receive_sequence` | Recv seq `N(R)`, value = `byte >> 1` | spec |
| 9 | 1 | `atcs.addr_len` | Address-length nibbles: **high = source digit count, low = destination digit count** (nibble value = digit count; `0xA`=10, `0xE`=14) | spec |
| 10 | ⌈dst/2⌉ | `atcs.dst_addr` | **Destination address FIRST** (modified BCD, §3.6) | spec |
| … | ⌈src/2⌉ | `atcs.src_addr` | Source address | spec |
| … | 1 | `atcs.facility_len` | Facility-field length (0x00; no facility emitted) | spec |
| … | 1 | `atcs.message_number` | `msg_num << 1 \| more` | spec_legacy |
| … | 1 | `atcs.part_number` | `part_num << 1 \| end_to_end_ack` | spec_legacy |
| … | 1 | `atcs.message_length_vital` | `msg_len << 1 \| vital` — **the vital flag lives here** | spec_legacy |
| … | 2 | `atcs.label` | Message label (16-bit, Spec 250) | spec_legacy |
| … | N | `atcs.usrdata` | Application user data | **synthetic** |
| … | 4 | `atcs.vital_crc` | 31-bit K-II vital CRC — **vital messages only** (§3.9) | spec_legacy |
| len-2 | 2 | `atcs.datagram_crc` | CRC-16/X.25 over `[5 : len-2]`, **little-endian** | spec |

The transport header is a fixed 5 octets (`message_number`, `part_number`,
`message_length_vital`, then the 2-byte `label`). Note the asymmetry at `[9]`: the
octet carries the **source** length in the high nibble, yet the **destination
address is transmitted first**.

### 3.3 The two CRCs — CRC-16/X.25 (your strongest classifier)

Both framing CRCs are **CRC-16/X.25** (a.k.a. CRC-16/IBM-SDLC, the HDLC FCS):
`poly=0x1021, init=0xFFFF, RefIn=true, RefOut=true, XorOut=0xFFFF`, stored
**little-endian** (low byte first).

- **Header CRC** (`[3:5]`) covers the 3 RF-header bytes `[0:3]`.
- **Datagram CRC** (last 2 bytes) covers `[5 : len-2]` — the datagram from the
  GFI octet through end of message, **excluding** the RF header and the CRC bytes.

```python
def crc16_x25(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if (crc & 1) else (crc >> 1)
    return crc ^ 0xFFFF
# stored little-endian: bytes([crc & 0xFF, crc >> 8])
# header  : crc16_x25(frame[0:3])   == frame[3] | frame[4] << 8
# datagram: crc16_x25(frame[5:-2])  == frame[-2] | frame[-1] << 8
```

Both checks passing over their exact spans is a near-zero-false-positive ATCS
signal — recommended as your primary matcher.

### 3.4 Frame-length field (`block_count` / `pad_bits`)

The RF header encodes the frame length as Reed-Solomon blocks of **60 frame-bits
each**. The real decoder rebuilds the expected length from these and rejects a
mismatch. For a total frame of `L` bytes:

```
block_count = ceil(8 * L / 60)         # = ceil(2 * L / 15)
pad_bits    = 60 * block_count - 8 * L  # always 0..59
```

A parser can use this as an integrity/plausibility check: recompute
`block_count`/`pad_bits` from the received datagram length and confirm they match
`[2]`/`[1]`.

### 3.5 Address encoding — the gotchas (all spec-confirmed)

- **Modified BCD, high nibble first.** Each octet holds two decimal digits, high
  nibble first.
- **A zero digit is nibble `0xA`, not `0x0`.** e.g. `28 A2 A6 3A A7` decodes as
  `2 8 0 2 0 6 3 0 0 7` = `2802063007`.
- **Destination first**, then source (despite `[9]` carrying source length in its
  high nibble).
- Two address forms:
  - **7-series (14 digits):** `T-RRR-CCC-AAA-XXXX` = Type, Railroad, Codeline,
    Address, eXtension. 7 bytes. `addr_len` nibble = `0xE` (14).
  - **5-series (10 digits):** `T-RRR-XX-AAAA` = Type, Railroad, eXtension,
    Address. 5 bytes. `addr_len` nibble = `0xA` (10).
- **Type digit** identifies role: `1`=locomotive, `2`=office/dispatch,
  `3`=base station, `5`/`7`=wayside (MCP). The wayside 7-series extension `0202`
  = field indications, `0101` = command & control.

```python
def decode_atcs_addr(byts):   # nibble 0xA == digit 0
    return "".join(("0" if n == 0xA else str(n))
                   for x in byts for n in (x >> 4, x & 0xF))
```

Decoded ATCS addresses are **directly usable for asset/component identity** in
Cyber Vision: railroad + codeline + serial + role. This is the most valuable
DPI output for this protocol.

### 3.6 GFI / Group and sequences

`[5] = (GFI << 4) | Group`. GFI = Group Format Identifier. Observed combinations:
`0x68`=GFI6/Grp8, `0x25`=GFI2/Grp5, `0x6C`=GFI6/Grp12, `0x2D`=GFI2/Grp13.
`send_sequence`/`receive_sequence` = the respective byte `>> 1` (LAPB-style
N(S)/N(R); low bit is 0).

### 3.7 Deriving UsrData length

The real decoder does **not** read an explicit UsrData length; it derives it from
the received datagram size (one frame per UDP datagram) minus the fixed overhead:

```
usrdata_len = total_frame_len
            - 5   (RF header)
            - 5   (network header [5:10])
            - dst_bytes - src_bytes         (from the [9] nibbles)
            - 1   (facility length)
            - 5   (transport header)
            - 2   (datagram CRC)
            - (4 if vital else 0)           (inner vital CRC)
```

Your parser should do the same: walk the fixed fields, and whatever remains
before the trailing CRC (and inner vital CRC, if the vital flag in
`message_length_vital` is set) is UsrData.

### 3.8 Vital CRC (vital messages only; `spec_legacy`)

When `message_length_vital`'s low bit (vital) is set, a **31-bit K-II vital CRC**
(4 octets) precedes the datagram CRC, inside the L7 data region. Polynomial
`x^31+x^30+x^28+x^25+x^19+x^18+x^16+x^15+x^11+x^9+x^7+1` (low mask `0x520D8A81`),
data processed **LSB-first**, register emitted least-significant-octet first.
Coverage: the address-length octet `[9]` through end of L7 data. Verified against
the K-II mandatory vector `01 02 → 25 ED BD 70`. (The outer datagram CRC-16/X.25
still wraps everything including this inner CRC.)

### 3.9 Parsing algorithm (ATCS)

```
parse_atcs_datagram(f):                      # f = one UDP payload
    if crc16_x25(f[0:3]) != le16(f[3:5]): reject (bad header CRC)
    if crc16_x25(f[5:-2]) != le16(f[-2:]): reject (bad datagram CRC)
    addr_type = f[0]                          # 0x23 ground / 0xFF bcast / 0x00 CC_ID
    gfi, group = f[5] >> 4, f[5] & 0x0F
    sseq, rseq = f[7] >> 1, f[8] >> 1
    src_digits, dst_digits = f[9] >> 4, f[9] & 0x0F
    o = 10
    dst = decode_atcs_addr(f[o : o + ceil(dst_digits/2)]); o += ceil(dst_digits/2)
    src = decode_atcs_addr(f[o : o + ceil(src_digits/2)]); o += ceil(src_digits/2)
    facility_len = f[o]; o += 1 + facility_len
    msg_num  = f[o] >> 1; part = f[o+1] >> 1; vital = f[o+2] & 1
    label    = be16(f[o+3 : o+5]); o += 5
    usr_end  = len(f) - 2 - (4 if vital else 0)
    usrdata  = f[o : usr_end]
```

### 3.10 What to trust vs. ignore (ATCS)

- **Trust (`spec`, corpus-validated live):** the 5-byte RF header, both
  CRC-16/X.25 fields, `gfi_group`, `spare`, send/recv sequences, the
  address-length octet, the dest-first BCD addresses, and the facility length.
- **Trust structure (`spec_legacy`):** the 5-byte transport header layout and the
  31-bit vital CRC (spec-derived from K-II 2005; may drift from current revisions).
- **Do not overfit (`synthetic`):** UsrData *content*. Per-territory codeline bit
  semantics live in proprietary railroad `.mcp` databases. Treat UsrData as an
  opaque, length-N blob; extract identity from the addresses, not the payload.

---

## 4. Classifier design recommendations

1. **Identify on framing invariants, not ports.** 3001 (EMP) and 4802/30000+
   (ATCS) are configurable vendor defaults.
   - EMP/Class D: `[0]==0x02 && [1]==0x02 && [-1]==0x03 && data_length matches`,
     then EMP `[12]==0x04`. Optionally verify the EMP CRC-32.
   - ATCS: both CRC-16/X.25 checks pass over their exact spans. This alone is a
     high-confidence match.
2. **Use CRCs as positive signals**, not just error detection — a frame whose
   CRCs self-verify is almost certainly the protocol.
3. **Extract asset identity, which is the DPI payoff:**
   - EMP: `emp.src_addr` / `emp.dst_addr` (`aar.<class>.<name>`) → device + role.
   - ATCS: decode the BCD addresses → railroad ID, codeline, serial, and role
     (from the type digit + extension). Each distinct wayside MCP is a component.
4. **Do not learn synthetic content as ground truth.** Ignore specific
   `emp.msg_type` values, EMP payload schemas, and ATCS UsrData bytes when
   training the *matcher*; they are invented pending the proprietary catalogs.
5. **Handle TCP reassembly** for EMP (Class D frames can span segments; use
   `data_length`). ATCS is one frame per UDP datagram — no reassembly.

---

## 5. Open items / fidelity caveats

Tracked in `backend/app/protocol_engines/atcs/SPEC_NEEDS.md`:

- **Synthetic (won't change without proprietary sources):** EMP application
  message catalog (real message-type IDs + payload schemas), ATCS
  territory-specific UsrData semantics.
- **`spec_legacy` current-revision drift:** Class D is the 2010 S-9356 *draft*;
  ATCS transport header + vital CRC are from K-II *2005 v4.0*. Structurally
  authoritative; a current-revision capture (a BOS↔WIU trace for EMP, an ATCS
  Monitor `.log` for ATCS) would promote them to `spec`.
- **Already resolved / validated:** the ATCS relay-feed framing, the two
  CRC-16/X.25 fields, the frame-length field, GFI|Group, sequences, and address
  encoding — all confirmed against the live ATCS Monitor 4.1.0 decoder.

---

## 6. Reference: generating and reading the corpus

Generate (per-PCAP flag): set `export_labeled_corpus=true` on the generation
request for the `ptc_freight_corridor` (EMP) or `atcs_signaling_territory` (ATCS)
scenario. You get `<stem>.pcap` + `<stem>.labels.jsonl` + `<stem>.labels.meta.json`.

Read (Python sketch):

```python
import json
from scapy.utils import rdpcap
pkts = rdpcap("run.pcap")
for rec in map(json.loads, open("run.labels.jsonl")):
    if not rec.get("fields"):
        continue
    raw, l7 = bytes(pkts[rec["pkt"]]), rec["l7_offset"]
    for f in rec["fields"]:                     # encoding == "binary"
        field_bytes = raw[l7 + f["off"] : l7 + f["off"] + f["len"]]
        # f["field"], f["value"], f["confidence"], f["synthetic"]
```

---

## Appendix A — Worked ATCS frame (real corpus frame, `Frame=32`)

```
23 2c 05 ad f7  68 00 46 00 aa  28 a2 a6 3a a7  18 a2 8a 4a 75  00  c6 02 02 b2 1c  01 52 49 00  cf fa
```

| Bytes | Field | Decode |
|-------|-------|--------|
| `23` | `relay.rf_address_type` | 0x23 = ground datagram (the `#`) |
| `2c` | `relay.rf_pad_bits` | 44 |
| `05` | `relay.rf_block_count` | 5 blocks (⌈8·32/60⌉=5; pad=60·5−256=44 ✓) |
| `ad f7` | `relay.rf_header_crc` | 0xF7AD = CRC-16/X.25(`23 2c 05`), little-endian ✓ |
| `68` | `atcs.gfi_group` | GFI=6, Group=8 |
| `00` | `atcs.spare` | — |
| `46` | `atcs.send_sequence` | 0x46>>1 = 35 |
| `00` | `atcs.receive_sequence` | 0 |
| `aa` | `atcs.addr_len` | src=10 digits, dst=10 digits (both 5-series-length) |
| `28 a2 a6 3a a7` | `atcs.dst_addr` | **2802063007** (dest first; 0xA=0) — "To Dispatch" |
| `18 a2 8a 4a 75` | `atcs.src_addr` | 1802804075 |
| `00` | `atcs.facility_len` | 0 |
| `c6 02 02 b2 1c` | transport | msg/part/len-vital/label (decodes to Number 89.0.28) |
| `01 52 49 00` | `atcs.usrdata` | 4 bytes (synthetic content) |
| `cf fa` | `atcs.datagram_crc` | 0xFACF = CRC-16/X.25(`68…00`), little-endian ✓ |

Real ATCS Monitor decodes this exactly as: `Frame=32 GFI=6 Group=8 SSeq=35
Rseq=0 UsrData=4 · To Dispatch: 2802063007 · Number=89.0.28`.

## Appendix B — Worked EMP + Class D frame (generated, TCP payload)

```
02 02 00000001 01 02 0000002c   <-- Class D header (12B): STX,pver,COMMID=1,type=1(Data),mver,dlen=44
04 0201 01 00 000008 17 0078 0000
61 61 72 2e 77 2e 77 69 75 30 30 37 00              <-- "aar.w.wiu007\0"  (emp.src_addr)
61 61 72 2e 62 2e 62 6f 73 00                        <-- "aar.b.bos\0"     (emp.dst_addr)
01 02 03 04                                          <-- payload (synthetic, 4B)
43 f7 40 ad                                          <-- emp.crc32
03                                                   <-- Class D ETX
```

EMP-relative: `[0]=04` version, `[1:3]=0201` msg_type, `[3]=01` msg_version,
`[4]=00` flags, `[5:8]=000008` body_size(8 = 4 CRC + 4 payload), `[8]=17`
var_hdr_size(23), `[9:11]=0078` ttl(120s), `[11:13]=0000` qos, addresses at
`[13:]`, payload at `[36:40]`, CRC-32 at `[40:44]`. `len(class_d)=57 = 44 + 13`.

---

*Generated by PacketArch. Structure sources: AAR S-9356 Class D (2010 draft),
AAR MSRP Section K-II (2005 v4.0), ATCS Monitor 4.1.0 (live validation oracle).
Application-layer content is synthetic pending the proprietary AAR ITC catalog and
per-territory codeline databases.*
