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
