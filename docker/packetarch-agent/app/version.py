# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PacketArch Agent version information."""

# Semantic versioning: MAJOR.MINOR.PATCH
# - MAJOR: Breaking changes to agent/server protocol
# - MINOR: New features, backward compatible
# - PATCH: Bug fixes, minor improvements
VERSION = "1.26.0"

# Version history:
# 1.26.0 - CV DPI malformation fixes: PROFINET DCP BlockInfo qualifier (was missing on every response block, all Identify Responses dissected as malformed), OPC UA OPNF SecureChannelId field (4 bytes, was missing), OPC UA IP/TCP checksum recompute (was 0 / RFC 791 invalid - CV silently dropped these packets before DPI), EtherNet/IP ForwardOpen wrapped in EIP encap+CPF+CIP MR (was raw CIP service data), ForwardOpen reply struct format (vendor_id UDINT→UINT, t_to_o_api restored, 28b → 30b per CIP Vol 1 §3-5.5.4.1). Plus protocol→port routing (PROTOCOL_DEFAULT_PORTS / get_default_port) and variant alias resolution (s7comm_plus / profisafe / cip_safety) so flows actually reach their engines and land on the correct ports.
# 1.25.0 - Synchronized attack lifecycle with deployment - STOP_SCENARIO now auto-stops attack orchestrator, prevents orphaned attacks
# 1.24.0 - Add 15 Snort/Suricata rule-triggering attack actions for IDS validation (SNORT_VALIDATION playbook, ICS/OT, C2, exfiltration signatures)
# 1.23.2 - Fix attack stage stuck at 0s: wall-time stage advancement on every event loop iteration (prevents virtual-time lag), fix injection config mapping
# 1.23.1 - Fix attack state in event-driven STATUS path, trigger immediate status after injection for faster confirmation
# 1.23.0 - Hot-attach attack playbooks: INJECT_ATTACK command for mid-run playbook injection into running deployments
# 1.22.0 - CV fingerprint gap fix: 301/301 templates with explicit snmp_identity, SNMP pre-startup timing (sysName before protocol flows), fix duplicate CIP serials (SerialNumberGenerator moved to protocol_engines), sysName priority = device_name over template
# 1.21.0 - Fix OUI misattributions (KUKA/Fanuc/SICK/HMS), early-burst discovery (3 cycles in first 90s for faster CV fingerprinting)
# 1.20.0 - Universal SNMP discovery: all fingerprinted devices get SNMP GET/Response for CV fingerprinting, vendor-specific sysObjectID synthesis, merge device definition protocols into ambient discovery
# 1.19.1 - Eliminate phantom devices: all ambient handlers use real scenario devices as query sources instead of fake gateway IPs (02:00:00:00:00:01)
# 1.19.0 - Ambient discovery: self-response for BACnet/PROFINET/ENIP/S7 (source-only devices), BACnet ReadProperty identity, fix property_type encoding, fix FingerprintApplicator/DeviceContext kwargs
# 1.18.2 - Fix TCP stack fingerprinting in OPC UA/DNP3/IEC104/SLMP/FINS engines; BACnet/SNMP engine robustness for missing identity data
# 1.18.1 - Ambient SNMP discovery: periodic GET/Response for devices with SNMP protocol (CV fingerprints EWON/gateway devices)
# 1.18.0 - Fix protocol alias mapping: profisafe→profinet, s7comm_plus→s7comm, cip_safety→ethernet_ip; add scenario_id/device_name to DeviceContext
# 1.17.1 - Fix EtherNet/IP product_name: preserve template catalog string, stop overwriting with device_name
# 1.17.0 - Fix CV fingerprinting: CIP identity queries in TCP startup (timing race fix), EWON cloud field mismatch, product_name in all EtherNet/IP templates
# 1.16.0 - Fix CV fingerprinting: EtherNet/IP encapsulation header (28→24 bytes), S7 SZL + Modbus MEI in startup, BACnet firmware_revision merging
# 1.15.2 - Fix double-counted "unknown" protocol stats for ambient/attack packets
# 1.15.1 - Fix SNMP coldStart trap crash: map trap type names to numeric OIDs for Scapy ASN.1 encoding
# 1.15.0 - Broadcast/multicast ecosystem: LLDP, STP, DHCP, BACnet Who-Is, PROFINET DCP, SNMP traps, CDP, IGMP
# 1.14.0 - Process simulation engine: correlated sensor values with ODE models, state machine, 4 vertical templates
# 1.13.0 - Unified TCP builder, staggered flow startup, PROFINET AR establishment (RPC Connect/Write/Control)
# 1.12.0 - PayloadGenerator auto-wiring (realistic sensor values), background noise engine (ARP, NTP)
# 1.11.0 - Live attack simulation: attack playbook execution, kill-chain stage commands (START/STOP/ADVANCE/PAUSE_ATTACK)
# 1.10.0 - Deployment phase scheduling: sequential lifecycle phase cycling (startup → steady → maintenance → shutdown)
# 1.9.0 - Adaptive traffic: server-directed adaptation (ADAPT_TRAFFIC command, directive delivery)
# 1.8.0 - Adaptive traffic: time-of-day traffic scheduling (macro rate shaping, schedule presets)
# 1.7.0 - Adaptive traffic: micro-variations (timing drift, retransmits, vendor personality, connection resets)
# 1.6.0 - Agent health: exponential reconnect backoff (5s->120s cap), scenario thread liveness checks
# 1.5.0 - Live Traffic Dashboard: per-protocol stats, bytes tracking, packet rates, running_scenarios in heartbeat
# 1.4.2 - Synced PROTOCOL_TO_IDENTITY_KEY with canonical source (added enip, s7, bacnet_ip, opc_ua, dnp3, iec104 aliases)
# 1.4.1 - Fixed NameError in PROFINET DCP response (device.device_id -> src.device_id)
# 1.4.0 - Added fingerprint identity support for OPC UA, IEC104, and DNP3 protocols
# 1.3.0 - Added CDP/LLDP discovery for Cisco switches, fixed BACnet unicast polling, fixed protocol port mappings
# 1.2.5 - Simplified updater (no script file), fixed rw mount for self-update
# 1.2.4 - Fixed updater to use alpine with docker-cli-compose (docker:cli not available)
# 1.2.3 - Fixed self-update to spawn external updater container (survives container stop)
# 1.2.2 - Fixed self-update to use down+up instead of force-recreate (avoids name conflicts)
# 1.2.1 - Fixed self-update to mount install directory for docker compose recreate
# 1.2.0 - Added CloudTrafficScheduler for cloud service heartbeats (Talk2M, TeamViewer)
# 1.1.17 - Simplified HTTPS poll logging with !!! markers
# 1.1.15 - Added event loop debug logging for HTTPS flow poll events
# 1.1.14 - Added debug logging for HTTPS external flows
# 1.1.13 - Added Docker CLI to container for self-update support
# 1.1.12 - Fixed BER integer encoding for negative values (ESS temperature readings)
# 1.1.11 - Fixed external flow handling in orchestrator_pool (allow flows without target device)
# 1.1.10 - Added HTTPS external flow support for EWON Talk2M cloud communication
# 1.1.9 - Fixed ALL DeviceContext creations to pass device_name for unique SNMP/PROFINET identities
# 1.1.8 - Made self-update resilient to different install paths (auto-detect or docker restart fallback)
# 1.1.7 - Fixed SNMP sysName and PROFINET station_name to use device_name for unique identification
# 1.1.6 - Added VENDOR_IDENTIFIER polling for BACnet CV detection, increased poll limit to 4
# 1.1.5 - Added device_name and scenario_id fields to DeviceContext
# 1.1.4 - Fixed self-update to use docker compose (restart doesn't pick up new images)
# 1.1.3 - Fixed scenario_id reference error in orchestrator_pool
# 1.1.2 - Fixed device naming for Cyber Vision (PROFINET station_name from device_name)
# 1.1.1 - Fixed fingerprint field name compatibility (fingerprint vs vendor_fingerprint)
# 1.1.0 - Added self-update capability via UPDATE_AGENT command
# 1.0.0 - Initial release with WebSocket-based command/control
