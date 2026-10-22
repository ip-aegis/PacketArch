# Wave 3: IT protocols on the wire (plan)

**Date:** 2026-10-21. This is the transportation flagships plan, Wave 3.

## Finding that reorders the wave

Any `https` / `ssh` / `rdp` / `telnet` flow without `config.hostname` emits TCP SYN/SYN-ACK/ACK then FIN, with no TLS and no payload (`cloud_service/engine.py:142`). That covers every VMS→camera, jump-host and proxy session in every vertical.

## Order

1. **Session shapes on the existing engine** (CloudServiceEngine):
   - HTTPS: TLS by default, SNI = destination hostname, then a few ApplicationData records.
   - SSH: cleartext banner exchange, then KEXINIT, never TLS.
   - RDP: X.224 CR with an RDP negotiation request, then TLS.
   - Telnet: cleartext.
   - Banners only where sourced; otherwise generic.
   - Cloud heartbeats must stay byte-identical (test).
   - Decide the `_HEARTBEAT_PROTOCOLS` exemption on purpose.
2. **syslog** (UDP 514, RFC 5424). Devices send to the NMS. Vendor formats only where published (Cisco `%FAC-SEV-MNEMONIC`), otherwise generic.
3. **Ambient DNS** to a real scenario server, using canonical hostnames and the SiteIdentity domain. No phantom resolver; no DNS if no plausible server exists.
4. **RTSP**:
   - Control session (OPTIONS / DESCRIBE / SETUP / PLAY / keepalive) plus a sparse, capped RTP stream.
   - Measure virtual-time rate and PCAP size before and after on F1 and F3.
   - The `rtsp` flows the role catalog and archetypes already produce, which are dropped today, will start emitting.
5. **HTTP** (cleartext), only for devices whose UI is documented on port 80.

## Checklist per new ProtocolType

- [ ] Enum member + `create_conversation_state` map entry
- [ ] Engine import + `__all__` in `protocol_engines/__init__.py`
- [ ] `PROTOCOL_DEFAULT_PORTS` **and** the agent `PROTOCOL_PORTS` (parity test via `ast`)
- [ ] `template_lint._NON_ENGINE_PROTOCOLS`
- [ ] `repair_flow_protocols` generic / IT-shape placement; fingerprint `supported_protocols` only where sourced
- [ ] Flagship conduits' `allowed_protocols`; `cell_isolation._PROTOCOL_ALIASES`
- [ ] Frontend `ProtocolType` union + Record maps; run `tsc` before deploying
- [ ] Portable schema: unchanged (it excludes IT protocols deliberately)
- [ ] Agent 4.5.0

## Verification per engine

- Wire decode tests.
- All four flagships build with zero flow repairs.
- Ambient-poller test.
- Full suite.
- One commit per engine.
- One batched Cyber Vision replay at the end, only after the operator agrees to it, with fresh MACs.

## Status (2026-10-21)

- [x] 1. Session shapes: HTTPS / SSH / RDP / Telnet (`1ab3641`)
- [x] 2. syslog (`0910cc7`)
- [x] 3. Ambient DNS plus a Windows Server 2022 DC in each flagship (`1c0d3e6`)
- [x] 4. RTSP (`999d948`). Metro arterial: 5.4x before, 5.1x after real time; 6.0 MB before, 8.9 MB after per 2 min.
- [x] 5. HTTP (`b886fb2`)
- [x] Frontend: extended color/label maps plus conduit options. The `ProtocolType` union is unchanged; `tsc` is clean.
- [x] Batched Cyber Vision replay (2026-10-22): F1 + F4, 5 min each, MACs and IPs remapped to 10.97/10.96 so no component is re-used. 181 devices → 181 components.
  - RTSP: every camera tagged Video Sender, the VMS Video Receiver.
  - DNS: both domain controllers tagged DNS Server.
  - HTTP/HTTPS: cameras, ANPR and classifiers tagged Web Server; the toll host HTTP Client; heartbeat and proxy devices HTTPS Client.
  - Syslog: CV assigns no tag for it, so a replay can't confirm it.
  - Found and fixed: the template SNMP engine answered sysName with the raw display name, not the canonical hostname. CV labelled 147/181 components with it, and polled devices answered two different names. Agent 4.5.1 (e4bcdcf).
  - Still open: sysLocation falls back to "Industrial Site" (170/181), and some fingerprints carry plant-flavoured locations ("Plant Operations - NMS") in an ITS TOC.
