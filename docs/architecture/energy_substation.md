# Reference Architecture: Energy Substation

*Auto-generated from the PacketArch architecture rail. Edit the source under `backend/app/services/architecture/` and re-run `scripts/export_architecture_docs.py` to regenerate.*

## Archetypes (1)

### Archetype: `energy_substation` — Energy — IEC 61850 Substation

Electrical substation following IEC 61850. Per-bay protection relays exchange GOOSE multicast at the bay; MMS reports flow north to a station-level RTAC; the RTAC presents DNP3 / IEC 104 north to the utility EMS over WAN. Engineering and local HMI live in a station-ops zone alongside NMS and asset management.

- **Pattern**: `distributed_substation`
- **Default vendor profile**: `sel_protection`
- **Supported vendor profiles**: `sel_protection`, `mixed_field`, `abb_shop`
- **Min scale**: `demo`
- **Default cell isolation**: `conduit_gated`

#### Zone skeleton

| Zone | Purdue | Security | Roles |
|---|---|---|---|
| `station_ops` (Station Operations) | L3.0 | high | `scada_primary`, `engineering_workstation`, `nms_server`, `asset_management_server`, `local_historian`, `core_switch` |
| `station_bus` (Station Bus) | L1.5 | high | `aggregator_rtu` |
| `bay1` (Bay 1 — Feeder Protection) | L1.0 | critical | `protection_relay`, `bay_switch` |
| `bay2` (Bay 2 — Bus Protection) | L1.0 | critical | `protection_relay`, `bay_switch` |
| `bay3` (Bay 3 — Transformer Protection) | L1.0 | critical | `protection_relay`, `bay_switch` |
| `bay4` (Bay 4 — Line Protection) | L1.0 | critical | `protection_relay`, `bay_switch` |
| `bay5` (Bay 5 — Capacitor Bank) | L1.0 | critical | `protection_relay`, `bay_switch` |
| `bay6` (Bay 6 — Reactor) | L1.0 | critical | `protection_relay`, `bay_switch` |
| `wan_uplink` (Utility WAN Uplink) | L4.0 | external | `wan_edge_router` |

#### Conduits (allowed cross-zone protocols)

| Conduit | Direction | Allowed protocols |
|---|---|---|
| `station_ops` ↔ `station_bus` | bidirectional | `modbus_tcp`, `iec104`, `iec61850`, `snmp` |
| `station_bus` ↔ `bay1` | bidirectional | `iec61850`, `modbus_tcp`, `snmp` |
| `station_bus` ↔ `bay2` | bidirectional | `iec61850`, `modbus_tcp`, `snmp` |
| `station_bus` ↔ `bay3` | bidirectional | `iec61850`, `modbus_tcp`, `snmp` |
| `station_bus` ↔ `bay4` | bidirectional | `iec61850`, `modbus_tcp`, `snmp` |
| `station_bus` ↔ `bay5` | bidirectional | `iec61850`, `modbus_tcp`, `snmp` |
| `station_bus` ↔ `bay6` | bidirectional | `iec61850`, `modbus_tcp`, `snmp` |
| `station_ops` ↔ `bay1` | bidirectional | `snmp`, `https`, `ssh` |
| `station_ops` ↔ `bay2` | bidirectional | `snmp`, `https`, `ssh` |
| `station_ops` ↔ `bay3` | bidirectional | `snmp`, `https`, `ssh` |
| `station_ops` ↔ `bay4` | bidirectional | `snmp`, `https`, `ssh` |
| `station_ops` ↔ `bay5` | bidirectional | `snmp`, `https`, `ssh` |
| `station_ops` ↔ `bay6` | bidirectional | `snmp`, `https`, `ssh` |
| `station_ops` ↔ `wan_uplink` | bidirectional | `iec104`, `dnp3`, `https`, `snmp` |

#### Notes

- Bay counts: DEMO=1, SMALL=2, MEDIUM=3, LARGE=4, MULTI_SITE=6.
- GOOSE multicast is intra-bay; the comm matrix synthesizes those as bay-internal flows from protection_relay→protection_relay.
- DNP3 / IEC 104 north-uplink is generated from the WAN conduit.
- Substations omit IDMZ (the station_ops zone fills that role for remote utility access).

## Role catalog (24 roles applicable)

| Role | Purdue | Category | Required protocols | When to include |
|---|---|---|---|---|
| `jump_server` | L3.5 | idmz | snmp, rdp, ssh | Include in any scenario with vendor remote access, operator remote work, or IT admin reach into OT. Effectively every scale >= small that has external connectivity. |
| `reverse_proxy` | L3.5 | idmz | https | Include when IT users access OT historian/HMI web UIs or when external partners reach OT via a published URL. Optional at small scale. |
| `patch_staging_server` | L3.5 | idmz | https, snmp | Include at scale >= medium when scenario models patch management traffic. Optional otherwise. |
| `av_management_server` | L3.5 | idmz | https, snmp | Include in regulated environments (NERC CIP, IEC 62443 SL3+) or when modeling endpoint security telemetry. Optional at small scale. |
| `remote_access_gateway` | L3.5 | idmz | https, snmp | Include when scenario models vendor remote service access. Common in small/medium utilities, manufacturing cells with OEM service contracts. |
| `dns_ntp_relay` | L3.5 | idmz | dns, ntp, snmp | Include at scale >= medium. Small sites typically use the remote-access gateway or operations server for time/DNS. |
| `email_relay` | L3.5 | idmz | smtp, snmp | Include when scenario models alarm escalation traffic. Optional at small scale. |
| `scada_primary` | L3.0 | operations | snmp | Include in every scenario except pure substation/edge deployments where a separate aggregator_rtu fills the role. Required for scale >= small in manufacturing/water/oil&gas. |
| `scada_standby` | L3.0 | operations | snmp | Include at scale >= medium for any vertical where uptime matters (manufacturing, water, energy). Optional at small. |
| `process_historian` | L3.0 | operations | snmp | Include in any scenario larger than tiny demo. Required for scale >= small in process-like verticals. |
| `engineering_workstation` | L3.0 | operations | snmp | Include in every scenario with PLCs/DCS. Vendor-pinned: a Siemens shop has TIA Portal hosts; a Rockwell shop has Studio 5000 hosts. Multi-vendor sites have one per vendor. |
| `asset_management_server` | L3.0 | operations | snmp, https | Include at scale >= medium for regulated verticals (manufacturing, oil_gas, energy). |
| `nms_server` | L3.0 | operations | snmp | Include in every scenario at scale >= small. The NMS is the canonical SNMP source — without it, switches end up orphaned for Cyber Vision discovery. |
| `ot_domain_controller` | L3.0 | operations | snmp | Optional. Include at scale >= medium for centralized auth across SCADA/HMI/engineering hosts. |
| `local_historian` | L2.0 | area | snmp | Optional. Include in distributed scenarios (multi-site, remote oil&gas, distributed water). |
| `field_rtu` | L1.0 | control | snmp | Include in master-remote SCADA scenarios: water utility (per pump station), energy substation (per bay), oil_gas (per wellhead/compressor). |
| `aggregator_rtu` | L1.5 | control | snmp | Include one per site in master-remote SCADA scenarios. In substations, this is the SEL-3530 / SEL-3555 RTAC. |
| `protection_relay` | L1.0 | control | iec61850, snmp | Required in energy_substation. Multiple per bay. |
| `distributed_io` | L0.0 | process | snmp | Include in any cell with field-mounted sensors/actuators that aren't directly wired to the controller chassis. |
| `vfd` | L0.0 | process | snmp | Include in any scenario with motors. Common in manufacturing, water (pumps), oil_gas (compressors), BAS (fans). |
| `core_switch` | L3.0 | network_infra | snmp | Required: every scenario has at least one. The L3 spine. |
| `cell_switch` | L2.0 | network_infra | snmp | Include one per cell in cell-based topologies. |
| `bay_switch` | L1.0 | network_infra | snmp | Include in energy_substation (per bay) and large manufacturing_process scenarios (per skid). |
| `wan_edge_router` | L3.5 | network_infra | snmp | Include in any scenario with WAN connectivity (most). Optional for fully air-gapped demo scenarios. |

## Communication matrix (35 entries)

Each row is a typed `(src_role, tgt_role) → protocol/pattern` rule that the scenario generator uses to materialize flows. Cross-vertical SHARED entries appear at the bottom.

| Source role | Target role | Pattern | Interval (ms) | Protocols | Vertical |
|---|---|---|---|---|---|
| `protection_relay` | `protection_relay` | event | 1000 | `iec61850` | energy_substation |
| `aggregator_rtu` | `protection_relay` | poll | 2000 | `iec61850`, `modbus_tcp` | energy_substation |
| `scada_primary` | `aggregator_rtu` | poll | 1000 | `iec104`, `modbus_tcp` | energy_substation |
| `scada_primary` | `protection_relay` | poll | 5000 | `iec61850` | energy_substation |
| `engineering_workstation` | `aggregator_rtu` | configuration | 120000 | `iec61850`, `ssh`, `https` | energy_substation |
| `engineering_workstation` | `protection_relay` | configuration | 300000 | `iec61850`, `ssh` | energy_substation |
| `local_historian` | `aggregator_rtu` | subscription | 1000 | `iec61850`, `modbus_tcp` | energy_substation |
| `aggregator_rtu` | `wan_edge_router` | poll | 2000 | `iec104`, `dnp3` | energy_substation |
| `nms_server` | `core_switch` | poll | 60000 | `snmp` | SHARED |
| `nms_server` | `cell_switch` | poll | 60000 | `snmp` | SHARED |
| `nms_server` | `bay_switch` | poll | 60000 | `snmp` | SHARED |
| `nms_server` | `wan_edge_router` | poll | 60000 | `snmp` | SHARED |
| `jump_server` | `scada_primary` | poll | 120000 | `snmp` | SHARED |
| `jump_server` | `cell_controller` | poll | 300000 | `snmp` | SHARED |
| `jump_server` | `aggregator_rtu` | poll | 300000 | `snmp` | SHARED |
| `jump_server` | `core_switch` | poll | 300000 | `snmp` | SHARED |
| `historian_replica` | `process_historian` | replication | 5000 | `opc_ua` | SHARED |
| `opc_ua_aggregator` | `cell_controller` | subscription | 1000 | `opc_ua` | SHARED |
| `opc_ua_aggregator` | `dcs_controller` | subscription | 1000 | `opc_ua` | SHARED |
| `av_management_server` | `engineering_workstation` | heartbeat | 900000 | `https` | SHARED |
| `av_management_server` | `scada_primary` | heartbeat | 900000 | `https` | SHARED |
| `patch_staging_server` | `engineering_workstation` | poll | 3600000 | `https` | SHARED |
| `remote_access_gateway` | `cell_controller` | poll | 10000 | `modbus_tcp`, `ethernet_ip`, `snmp` | SHARED |
| `dns_ntp_relay` | `scada_primary` | event | 64000 | `ntp` | SHARED |
| `scada_primary` | `scada_standby` | replication | 2000 | `https`, `snmp` | SHARED |
| `remote_access_gateway` | `scada_primary` | heartbeat | 30000 | `https`, `snmp` | SHARED |
| `asset_management_server` | `cell_controller` | poll | 3600000 | `https`, `snmp` | SHARED |
| `asset_management_server` | `dcs_controller` | poll | 3600000 | `https`, `snmp` | SHARED |
| `asset_management_server` | `aggregator_rtu` | poll | 3600000 | `https`, `snmp` | SHARED |
| `asset_management_server` | `protection_relay` | poll | 3600000 | `https`, `snmp` | SHARED |
| `mes_server` | `process_historian` | subscription | 10000 | `opc_ua`, `https` | SHARED |
| `mes_server` | `scada_primary` | poll | 60000 | `https`, `opc_ua` | SHARED |
| `opc_ua_aggregator` | `process_historian` | subscription | 2000 | `opc_ua` | SHARED |
| `reverse_proxy` | `scada_primary` | heartbeat | 60000 | `https` | SHARED |
| `reverse_proxy` | `process_historian` | heartbeat | 60000 | `https` | SHARED |
