# Traffic Realism Audit

**Date**: 2026-02-08
**Scope**: Protocol-vendor fidelity, zone/network realism, on-wire packet quality

## Summary

PacketArch generates OT/ICS traffic for security tool testing. The current system has strong vendor identity data (295 templates, correct ODVA/PROFINET/BACnet vendor IDs), proper client/server role modeling, and multi-protocol coverage. However, an expert examining generated PCAPs in Wireshark would spot several tells. This document catalogues every gap found and sorts them into implementation tiers.

### What PacketArch Does Well

- **Vendor identity data** is high quality and realistic across 295 device templates with real ODVA, PROFINET, and BACnet vendor IDs
- **Client/server role modeling** is correct — PLCs are servers, HMIs/SCADA are clients, field devices never initiate
- **Cross-zone restrictions** in SmartFlowGenerator correctly enforce Purdue cell isolation (controllers and field devices stay in-zone)
- **Protocol-role mapping** is accurate: Siemens -> PROFINET/S7, Rockwell -> EtherNet/IP, BMS -> BACnet, ITS -> SNMP
- **Timing system** is sophisticated: multi-distribution models, per-vendor personality traits, adaptive micro-variations
- **PayloadGenerator** exists with industry-specific process simulation profiles (manufacturing, water, energy, oil/gas)
- **TCP data packets** are properly fingerprinted with vendor TTL, window size, MSS, and options
- **Full TCP handshakes** (SYN/SYN-ACK/ACK) are generated for all TCP-based protocols
- **PROFINET** has correct Layer 2 framing, DCP discovery, RT cyclic I/O, IRT support, and PTCP sync

---

## Tier 1: Easy / Quick Wins (1-2 hours each)

### ~~Q1. TCP SYN/SYN-ACK packets lack fingerprinted options~~ DONE
**Impact: HIGH** — SYN is the #1 packet for OS fingerprinting (p0f, Nmap)
- **Fixed**: Added `tcp_options` parameter to `build_tcp_handshake_syn()` and `build_tcp_handshake_syn_ack()` in `modbus/packets.py`
- SYN/SYN-ACK now apply fingerprinted TTL, window, MSS, WScale, SAckOK, timestamps, and DF flag
- Modbus and EtherNet/IP engines pass client/server `tcp_options` from `fingerprint_applicator.get_tcp_options()`
- BACnet and SNMP are UDP-based — no TCP handshakes to fix

### ~~Q2. S7 engine hardcodes TTL=128, ignores fingerprint~~ DONE
**Impact: HIGH** — Siemens PLCs have TTL=64; this is the wrong OS family signature
- **Fixed**: Refactored all 5 S7 TCP builders (`_build_tcp_packet`, `_build_tcp_syn`, `_build_tcp_syn_ack`, `_build_tcp_ack`, `_build_tcp_fin`) to accept `TcpOptions`
- Added shared `_apply_tcp_options()` helper for consistent option extraction
- Updated all 20 call sites across startup, SZL query, poll cycle, and shutdown sequences
- Siemens templates' `"ttl": 64` is now correctly applied

### ~~Q3. TCP initial sequence numbers unrealistically small~~ DONE
**Impact: MEDIUM** — Any analyst viewing SEQ numbers would notice
- **Fixed**: Changed ISN generation to `random.randint(100_000_000, 4_000_000_000)` in Modbus, EtherNet/IP, and S7 engines
- BACnet and SNMP are UDP-based — no TCP sequence numbers

### ~~Q4. PCAP timestamps start at epoch 0 (January 1, 1970)~~ DONE
**Impact: LOW** — Cosmetic but immediately visible in Wireshark
- **Fixed**: Added wall-clock anchor in `pcap_writer.py` — first packet write captures `time.time()` and all timestamps offset from that anchor
- Orchestrator's relative timing preserved; only PCAP output is affected (live injection unchanged)

### ~~Q5. Protocol name inconsistency in later device templates~~ DONE
**Impact: MEDIUM** — Could cause `ValueError` in `ProtocolType()` enum
- **Fixed**: Normalized all `supported_protocols` across 10 vendor template files (siemens, rockwell, schneider, yokogawa, honeywell, hms, ge, abb, process_instruments, robotics_logistics)
- `'modbus'` -> `'modbus_tcp'`, `'s7'` -> `'s7comm'` to match canonical `types.ProtocolType` enum values

### ~~Q6. Empty protocol lists in scenario templates~~ DONE
**Impact: MEDIUM** — Devices appear on canvas but generate zero traffic
- **Fixed**: Assigned protocols to 16 devices across 4 template files (transportation, building_automation, manufacturing, distribution_logistics)
- SNMP for ITS devices (master stations, signal controllers, RSUs), BACnet for BMS controllers, EtherNet/IP for vision cameras/scanners, S7comm/Modbus for historians

### ~~Q7. Default OUI fallback includes VMware MAC prefix~~ DONE
**Impact: LOW** — VMware MACs in an OT environment are suspicious
- **Fixed**: Removed VMware OUI from `DEFAULT_OUIS`, replaced with single `DEFAULT_OUI = "02:00:00"` (locally administered)
- All 3 fallback paths in `vendor_oui.py` now use locally administered prefix

---

## Tier 2: Medium Effort (4-8 hours each)

### ~~M1. Wire PayloadGenerator into default code paths~~ DONE
**Impact: HIGH** — Currently Modbus returns all-zero registers, S7 returns `os.urandom()`
- **Fixed**: Added `payload_generator` field to `FlowContext`, created `payload_defaults.py` factory
- Auto-creates PayloadGenerator in `UnifiedOrchestrator.add_flow()` for Modbus, S7, EtherNet/IP flows
- Selects industry-appropriate sensor profiles via `get_profiles_for_vertical()` (manufacturing, water, energy, oil_gas)
- Modbus FC03/FC04: register values now evolve with sinusoidal, random-walk, stable trends
- S7 read responses: FLOAT32 sensor data replaces `os.urandom()` with correlated values
- EtherNet/IP I/O: UINT16 values replace zero bytes with trending process data
- Falls back to previous behavior when `payload_template` has explicit values

### ~~M2. Background noise generator (ARP, NTP)~~ DONE
**Impact: MEDIUM** — Real networks always have ambient traffic
- **Fixed**: Created `protocol_engines/ambient/` package (arp.py, ntp.py, noise_generator.py)
- `BackgroundNoiseGenerator` registered as composition peer (like AdaptiveController)
- Gratuitous ARP at boot for all devices, then every 5 minutes with jitter
- NTP queries every 64 seconds per device (NTPv4 mode 3/4 with server response)
- Wired into both PCAP mode (TrafficOrchestrator) and live agent mode (orchestrator_pool.py)
- LLDP deferred — engine already exists, needs device-role awareness for auto-creation

### ~~M3. Activate dead protocol-vendor validation code~~ DONE
**Impact: MEDIUM** — Prevents unrealistic manual canvas combinations
- **Fixed**: Wired `validate_protocol_vendor_affinity()` into `compute_scenario_readiness()` as a warning-severity check
- Frontend: created `protocolVendorAffinity.ts` client-side mirror; `ScenarioCanvas.onConnect` shows `message.warning()` on unusual combos
- Warnings only (not blocking) — allows override but flags unrealistic combos

### ~~M4a. Add `level` field to frontend ScenarioZone type~~ DONE
**Impact: MEDIUM** — Purdue level data exists in backend but is lost in frontend roundtrip
- **Fixed**: Added `level?: number` to `ScenarioZone` interface in `types/index.ts`
- Updated `inferPurdueLevel()` to check `zone.level` first, falling back to name heuristic for legacy scenarios

### ~~M4b. Zone property editor panel~~ DONE
**Impact: MEDIUM** — Users currently cannot edit zone properties (name, VLAN, subnet, Purdue level)
- **Fixed**: Created `ZonePropertyForm.tsx` with fields: name, type, Purdue level, subnet, VLAN ID, gateway, color, device count
- Wired into `PropertyPanel.tsx` for zone selection context

### ~~M4. Staggered flow startup times~~ DONE
**Impact: LOW-MEDIUM** — All flows currently start at t=0
- **Fixed**: Added role-based startup offsets in `unified_orchestrator.py:_schedule_startup_sequences()`
- `_STARTUP_OFFSETS` dict maps device roles to offset ranges: SCADA/HMI (0-2s), PLCs/controllers (2-10s), field devices/sensors (5-20s)
- `_compute_startup_offset()` infers role from `vendor_fingerprint.device_type` or protocol type
- Timed mode (PCAP) caps offsets to 10% of duration to prevent short PCAPs being consumed by stagger
- Added `startup_offset_ms: float` field to `FlowContext` in `types.py`

### ~~M5. Add `level` field to frontend ScenarioZone type~~ DONE
**Impact: MEDIUM** — Purdue level data exists in backend but is lost in frontend roundtrip
- **Fixed**: See M4a above (merged into Phase C execution)

### ~~M6. Zone property editor panel~~ DONE
**Impact: MEDIUM** — Users currently cannot edit zone properties (name, VLAN, subnet, Purdue level)
- **Fixed**: See M4b above (merged into Phase C execution)

---

## Tier 3: Hard (1-3 days each)

### ~~H1. Unified TCP stack builder shared across all protocol engines~~ DONE
**Impact: HIGH** — Currently each engine (Modbus, S7, EtherNet/IP, PROFINET) builds TCP independently
- **Fixed**: Created `protocol_engines/tcp_builder.py` (~170 lines) with centralized TCP construction
- `extract_tcp_options()` — single implementation of SYN-only options logic (MSS, SAckOK, WScale in SYN only, timestamps always)
- `build_tcp_packet()`, `build_tcp_syn()`, `build_tcp_syn_ack()`, `build_tcp_ack()`, `build_tcp_fin()`, `build_tcp_fin_ack()`, `build_tcp_packet_fingerprinted()`
- Deleted ~280 lines from `modbus/packets.py` (7 TCP functions), added re-exports for backward compat
- Deleted ~140 lines from `s7/engine.py` (6 TCP functions + `_apply_tcp_options`), imported from tcp_builder
- `ethernet_ip/engine.py` changed import source from `modbus.packets` to `tcp_builder`
- `ethernet_ip/packets.py` replaced inline options extraction with `extract_tcp_options()` call

### ~~H2. TCP retransmission simulation~~ DISCARDED
**Impact: MEDIUM** — Zero retransmissions is unrealistic for any real network
- **Discarded**: Unnecessary complexity. MicroVariationEngine already handles retransmit events at the timing level (0.2% rate). Full TCP-level retransmission simulation with duplicate SEQ tracking adds significant state management burden for marginal realism gain.

### ~~H3. PROFINET AR establishment (RPC-based connection setup)~~ DONE
**Impact: MEDIUM** — Current impl skips from DCP discovery straight to RT data exchange
- **Fixed**: Added full DCE/RPC over UDP (port 34964) Application Relationship setup in `profinet/packets.py`
- 6 new packet builders: `build_rpc_connect_request/response`, `build_rpc_write_request/response`, `build_rpc_control_request/response`
- Each RPC frame: Ethernet + IP + UDP + 80-byte DCE/RPC connectionless header + PROFINET blocks
- `profinet/engine.py`: replaced skip comment with `_generate_ar_setup()` method (~130 lines)
- Startup sequence now: DCP Identify → RPC Connect → RPC Write → RPC Control → RT cyclic I/O
- AR UUID generated via `uuid.uuid4()`, session key via `random.randint(1, 65535)`
- State tracked via existing `ProfinetConversationState.establish_ar()`

### H4. Cross-zone validation with Purdue level enforcement
**Impact: MEDIUM** — Currently role-based only, not level-based
- Add level-based rules: Level N can only directly communicate with Level N-1 and N+1
- SCADA (L3) should not directly poll field devices (L0)
- Apply both in SmartFlowGenerator AND as warnings on manual canvas connections
- DMZ (L3.5) should only accept connections from both sides, never bridge them

### H5. EtherNet/IP UDP implicit I/O messaging
**Impact: MEDIUM** — Real EtherNet/IP uses UDP for high-frequency I/O after ForwardOpen
- Currently only TCP explicit messaging is modeled
- After ForwardOpen, switch to UDP multicast/unicast I/O with CIP sequence counts
- Configurable RPI (Requested Packet Interval)

---

## Tier 4: Moonshot (1+ week each)

### ~~X1. Process simulation engine (correlated sensor values)~~ DONE
**Impact: HIGH for long-duration captures** — Independent random values look fake over time
- **Fixed**: Created `protocol_engines/process_sim/` package (14 files, ~2,200 lines)
- Forward Euler ODE solver + algebraic equations for physical relationships
- ProcessStateMachine: COLD_START → WARMING_UP → STEADY_STATE → LOAD_CHANGE → ALARM → MAINTENANCE → SHUTDOWN
- ProcessVariable with first-order lag dynamics, Gaussian noise, per-state setpoints
- VariableBinder pushes correlated values into PayloadGenerator.states (no engine changes needed)
- 4 vertical templates: manufacturing (CNC), water treatment, building automation (HVAC), oil/gas (wellhead)
- Causal fault propagation with delay chains (e.g., pump_failure → flow_drop@500ms → tank_drain@5s)
- Composition peer on UnifiedOrchestrator (like AdaptiveController), 100ms tick interval
- Auto-enables when vertical has a template (both PCAP and agent modes)
- Deployment phase mapping: startup→WARMING_UP, steady→STEADY_STATE, etc.
- 58 tests all passing

### X2. Full network stack simulation (ARP tables, routing, VLAN tags)
**Impact: HIGH for detection tool testing**
- 802.1Q VLAN tags in packets for zone-segmented traffic
- Simulated routers with MAC rewrite at zone boundaries (TTL decrement, different src MAC)
- ARP table building with proper request/reply before first communication
- Gateway devices with their own MAC addresses

### X3. Passive OS fingerprint consistency (p0f/Nmap evasion)
**Impact: SPECIALIST** — For fooling security tools doing TCP stack analysis
- Generate TCP options in exact order matching real device OS stacks
- Model TCP timestamp clock skew (each device has its own clock rate)
- Window scaling behavior post-handshake
- IP ID field patterns (incremental, random, zero — varies by OS)
- DF bit consistency, IP options

### ~~X4. Realistic broadcast/multicast ecosystem~~ DONE
**Impact: MEDIUM-HIGH**
- **Fixed**: Extended `BackgroundNoiseGenerator` with 8 new broadcast types, all integrated as ambient events
- **AmbientDevice** extended with protocol/role/zone metadata (backward-compatible defaults)
- **Existing builders reused**: LLDP (`build_lldpdu`), BACnet (`build_who_is_packet`/`build_i_am_packet`), PROFINET DCP (`build_dcp_identify_request_packet`), SNMP (`build_snmp_trap_packet`)
- **New builders**: `ambient/stp.py` (STP/RSTP BPDUs), `ambient/dhcp.py` (DHCP DORA), `ambient/cdp.py` (Cisco CDP), `ambient/igmp.py` (IGMPv2)
- **Device filtering**: Only appropriate devices emit each type (switches→STP/CDP, BACnet devices→Who-Is, Cisco→CDP, HMIs→DHCP)
- **Zone-aware**: BACnet I-Am and PROFINET DCP responses come from zone peers
- **Boot one-shots**: DHCP DORA and SNMP coldStart emit once at startup, no reschedule
- **Periodic**: LLDP (30s), STP (2s), CDP (60s), BACnet Who-Is (10min), PROFINET DCP (2min), IGMP (125s)
- Wired into both PCAP mode (`orchestrator.py`) and agent mode (`orchestrator_pool.py`)
- 62 tests all passing

### X5. Energy and Oil/Gas scenario templates
**Impact: COVERAGE** — These verticals are documented but have no templates
- `scenario_templates/energy.py` and `oil_gas.py` don't exist
- Energy: substation automation (SEL relays + IEC 61850/Modbus), DER management, power quality
- Oil/Gas: pipeline SCADA (Modbus RTU/TCP), wellhead monitoring, gas chromatographs, ESD systems

---

## Recommended Execution Order

**Phase A — Quick Wins: COMPLETE (Q1-Q5)**
All five quick wins shipped. TCP SYN/SYN-ACK fingerprinting, S7 TTL, ISN ranges, PCAP timestamps, and protocol name normalization all fixed.

**Phase B — Payload & Noise: COMPLETE (M1, M2, Q6)**
PayloadGenerator wired into Modbus/S7/EtherNet-IP, background noise engine (ARP+NTP), and 16 silent devices fixed.

**Phase C — Validation & UI: COMPLETE (M3, M5, M6, Q7)**
VMware OUI removed, protocol-vendor affinity validation activated, Purdue level field added, zone property editor built.

**Phase D — Deep Protocol Work: COMPLETE (H1, H3, M4; H2 discarded)**
Unified TCP builder consolidating ~420 lines of duplicated code, PROFINET AR establishment (DCE/RPC Connect/Write/Control), staggered flow startups by device role. H2 (TCP retransmission simulation) discarded as unnecessary complexity.

**Phase E — Network Fidelity:** H4, H5
Purdue enforcement, UDP implicit I/O.

**Phase F — Process Simulation: COMPLETE (X1)**
Correlated sensor values with ODE models, state machines, 4 vertical templates (manufacturing, water, building automation, oil/gas), causal fault propagation. Auto-enables in both PCAP and agent modes.

**Phase G — Broadcast/Multicast: COMPLETE (X4)**
8 broadcast types (LLDP, STP, DHCP, BACnet Who-Is/I-Am, PROFINET DCP, SNMP traps, CDP, IGMP) added to BackgroundNoiseGenerator. Device-role filtering, zone-aware responses, boot one-shots. 62 tests passing.

**Remaining Moonshots:** X2, X3, X5 as capacity allows.

---

## Verification

After each phase:
1. Generate a PCAP with the Siemens manufacturing template
2. Open in Wireshark — verify TCP SYN packets show correct TTL/MSS/window per device
3. Check `tcp.analysis.retransmission` filter (Phase D)
4. Verify Modbus register values are non-zero (Phase B)
5. Check for ARP traffic before first TCP connection (Phase B)
6. Run Nmap OS detection against live agent traffic (Phase D+)
7. Test Cyber Vision device discovery against generated traffic

---

## Key Files Reference

| Area | File | Notes |
|------|------|-------|
| Unified TCP builder | `backend/app/protocol_engines/tcp_builder.py` | Shared TCP construction for all engines (H1 DONE) |
| TCP re-exports (Modbus) | `backend/app/protocol_engines/modbus/packets.py` | Re-exports from tcp_builder for backward compat |
| S7 engine | `backend/app/protocol_engines/s7/engine.py` | Imports from tcp_builder (H1 DONE) |
| Fingerprint TCP options | `backend/app/protocol_engines/fingerprint_applicator.py` | `get_tcp_options()` |
| Payload generator | `backend/app/protocol_engines/payload_generator.py` | Wired in by default (M1 DONE) |
| Process simulation | `backend/app/protocol_engines/process_sim/` | 14 files, correlated sensor values (X1 DONE) |
| Orchestrator | `backend/app/protocol_engines/unified_orchestrator.py` | Flow scheduling + process sim tick |
| Vendor OUI database | `backend/app/protocol_engines/vendor_oui.py` | MAC generation |
| Ambient broadcast/multicast | `backend/app/protocol_engines/ambient/` | 8 files: noise_generator, arp, ntp, stp, dhcp, cdp, igmp (X4 DONE) |
| Protocol-vendor validation | `backend/app/protocol_engines/protocols.py` | Dead code at line 184 |
| Device templates | `backend/app/services/device_templates/vendors/` | 18 vendor modules, protocol names normalized (Q5 DONE) |
| Scenario templates | `backend/app/scenario_templates/` | Industry verticals |
| Frontend zone type | `frontend/src/types/index.ts` | Missing `level` field |
| Zone property panel | `frontend/src/components/panels/PropertyPanel.tsx` | Returns null for zones |
| Canvas connection | `frontend/src/components/canvas/ScenarioCanvas.tsx` | No validation on connect |
| Purdue level inference | `frontend/src/utils/clusterGrouping.ts` | Fragile name heuristic |
| PCAP writer | `backend/app/traffic_generator/pcap_writer.py` | Wall-clock anchored (Q4 DONE) |
