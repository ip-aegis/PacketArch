# Reference Architecture: Energy Generation

*Auto-generated from the PacketArch architecture rail. Edit the source under `backend/app/services/architecture/` and re-run `scripts/export_architecture_docs.py` to regenerate.*

## Archetypes (1)

### Archetype: `energy_generation_combined_cycle` — Energy Generation — Combined Cycle Gas Turbine

Combined-cycle gas turbine plant: turbine controls per unit (GE Mark VIe / Siemens TXP / ABB Symphony / Emerson Ovation), central DCS HMI, BMS-grade SIS, dedicated electrical zone for generator protection. NERC CIP regulated.

- **Pattern**: `continuous_dcs`
- **Default vendor profile**: `dcs_emerson`
- **Supported vendor profiles**: `dcs_emerson`, `dcs_honeywell`, `dcs_abb`
- **Min scale**: `demo`
- **Default cell isolation**: `conduit_gated`

#### Zone skeleton

| Zone | Purdue | Security | Roles |
|---|---|---|---|
| `idmz` (Industrial DMZ) | L3.5 | critical | `jump_server`, `patch_staging_server`, `av_management_server`, `historian_replica`, `wan_edge_router`, `core_switch` |
| `operations` (Plant Operations) | L3.0 | high | `scada_primary`, `scada_standby`, `process_historian`, `engineering_workstation`, `alarm_event_server`, `nms_server`, `asset_management_server`, `core_switch` |
| `unit1` (Generation Unit 1 — GT1) | L1.0 | standard | `dcs_controller`, `distributed_io`, `field_instrument`, `valve_actuator`, `vfd`, `cell_switch` |
| `unit2` (Generation Unit 2 — GT2) | L1.0 | standard | `dcs_controller`, `distributed_io`, `field_instrument`, `valve_actuator`, `vfd`, `cell_switch` |
| `unit3` (Generation Unit 3 — Steam Turbine) | L1.0 | standard | `dcs_controller`, `distributed_io`, `field_instrument`, `valve_actuator`, `vfd`, `cell_switch` |
| `safety` (Safety Instrumented System) | L1.0 | critical | `safety_controller`, `cell_switch` |
| `electrical` (Electrical / Generator) | L1.0 | high | `protection_relay`, `field_instrument`, `cell_switch` |

#### Conduits (allowed cross-zone protocols)

| Conduit | Direction | Allowed protocols |
|---|---|---|
| `idmz` ↔ `operations` | bidirectional | `https`, `snmp`, `opc_ua`, `rdp`, `ssh` |
| `operations` ↔ `unit1` | bidirectional | `opc_ua`, `modbus_tcp`, `snmp` |
| `operations` ↔ `unit2` | bidirectional | `opc_ua`, `modbus_tcp`, `snmp` |
| `operations` ↔ `unit3` | bidirectional | `opc_ua`, `modbus_tcp`, `snmp` |
| `unit1` ↔ `safety` | bidirectional | `modbus_tcp` |
| `unit2` ↔ `safety` | bidirectional | `modbus_tcp` |
| `unit3` ↔ `safety` | bidirectional | `modbus_tcp` |
| `operations` ↔ `safety` | bidirectional | `opc_ua`, `ssh` |
| `operations` ↔ `electrical` | bidirectional | `iec61850`, `modbus_tcp`, `snmp` |

#### Notes

- Unit counts: DEMO=1, SMALL=2, MEDIUM/LARGE=3.
- Electrical zone hosts protection relays at SMALL+; smaller scenarios fold electrical into unit1.
- NERC CIP medium-impact assets land at MEDIUM+ scale.

## Role catalog (27 roles applicable)

| Role | Purdue | Category | Required protocols | When to include |
|---|---|---|---|---|
| `jump_server` | L3.5 | idmz | snmp, rdp, ssh | Include in any scenario with vendor remote access, operator remote work, or IT admin reach into OT. Effectively every scale >= small that has external connectivity. |
| `reverse_proxy` | L3.5 | idmz | https | Include when IT users access OT historian/HMI web UIs or when external partners reach OT via a published URL. Optional at small scale. |
| `patch_staging_server` | L3.5 | idmz | https, snmp | Include at scale >= medium when scenario models patch management traffic. Optional otherwise. |
| `av_management_server` | L3.5 | idmz | https, snmp | Include in regulated environments (NERC CIP, IEC 62443 SL3+) or when modeling endpoint security telemetry. Optional at small scale. |
| `historian_replica` | L3.5 | idmz | opc_ua, snmp | Include when IT/business consumers need process data. Common in manufacturing/oil_gas at scale >= medium. |
| `opc_ua_aggregator` | L3.5 | idmz | opc_ua, snmp | Include in multi-vendor enterprise scenarios where IT-side consumers want a single OPC UA endpoint instead of N vendor-native endpoints. |
| `remote_access_gateway` | L3.5 | idmz | https, snmp | Include when scenario models vendor remote service access. Common in small/medium utilities, manufacturing cells with OEM service contracts. |
| `dns_ntp_relay` | L3.5 | idmz | dns, ntp, snmp | Include at scale >= medium. Small sites typically use the remote-access gateway or operations server for time/DNS. |
| `email_relay` | L3.5 | idmz | smtp, snmp | Include when scenario models alarm escalation traffic. Optional at small scale. |
| `scada_primary` | L3.0 | operations | snmp | Include in every scenario except pure substation/edge deployments where a separate aggregator_rtu fills the role. Required for scale >= small in manufacturing/water/oil&gas. |
| `scada_standby` | L3.0 | operations | snmp | Include at scale >= medium for any vertical where uptime matters (manufacturing, water, energy). Optional at small. |
| `process_historian` | L3.0 | operations | snmp | Include in any scenario larger than tiny demo. Required for scale >= small in process-like verticals. |
| `engineering_workstation` | L3.0 | operations | snmp | Include in every scenario with PLCs/DCS. Vendor-pinned: a Siemens shop has TIA Portal hosts; a Rockwell shop has Studio 5000 hosts. Multi-vendor sites have one per vendor. |
| `asset_management_server` | L3.0 | operations | snmp, https | Include at scale >= medium for regulated verticals (manufacturing, oil_gas, energy). |
| `nms_server` | L3.0 | operations | snmp | Include in every scenario at scale >= small. The NMS is the canonical SNMP source — without it, switches end up orphaned for Cyber Vision discovery. |
| `alarm_event_server` | L3.0 | operations | snmp | Optional everywhere. Include for ISA-18.2 alarm-management scenarios (oil_gas, energy_generation). |
| `ot_domain_controller` | L3.0 | operations | snmp | Optional. Include at scale >= medium for centralized auth across SCADA/HMI/engineering hosts. |
| `area_hmi` | L2.0 | area | snmp | Include one per cell/area in discrete-cell manufacturing, BAS supervisor zones, oil/gas process areas. Skip in pure master-remote SCADA topologies (water/energy substation). |
| `safety_controller` | L1.0 | control | snmp | Include in scenarios with explicit safety functions: robot cells, chemical reactors, gas detection, burner management, emergency shutdown. |
| `dcs_controller` | L1.0 | control | snmp | Include in continuous-process scenarios: refineries, petrochem, power generation, pharma. Replaces cell_controller in those verticals. |
| `distributed_io` | L0.0 | process | snmp | Include in any cell with field-mounted sensors/actuators that aren't directly wired to the controller chassis. |
| `vfd` | L0.0 | process | snmp | Include in any scenario with motors. Common in manufacturing, water (pumps), oil_gas (compressors), BAS (fans). |
| `field_instrument` | L0.0 | process | snmp | Include in process verticals (manufacturing_process, oil_gas, water, energy_generation) and BAS. |
| `valve_actuator` | L0.0 | process | snmp | Include in process verticals and water/wastewater. Modeled per major valve when specifically interesting. |
| `core_switch` | L3.0 | network_infra | snmp | Required: every scenario has at least one. The L3 spine. |
| `cell_switch` | L2.0 | network_infra | snmp | Include one per cell in cell-based topologies. |
| `wan_edge_router` | L3.5 | network_infra | snmp | Include in any scenario with WAN connectivity (most). Optional for fully air-gapped demo scenarios. |

## Communication matrix (40 entries)

Each row is a typed `(src_role, tgt_role) → protocol/pattern` rule that the scenario generator uses to materialize flows. Cross-vertical SHARED entries appear at the bottom.

| Source role | Target role | Pattern | Interval (ms) | Protocols | Vertical |
|---|---|---|---|---|---|
| `scada_primary` | `dcs_controller` | poll | 1000 | `opc_ua`, `modbus_tcp` | energy_generation |
| `process_historian` | `dcs_controller` | subscription | 2000 | `opc_ua` | energy_generation |
| `engineering_workstation` | `dcs_controller` | configuration | 180000 | `opc_ua`, `ssh` | energy_generation |
| `alarm_event_server` | `scada_primary` | event | 5000 | `opc_ua` | energy_generation |
| `dcs_controller` | `distributed_io` | cyclic_io | 50 | `modbus_tcp`, `ethernet_ip` | energy_generation |
| `dcs_controller` | `field_instrument` | poll | 500 | `modbus_tcp` | energy_generation |
| `dcs_controller` | `valve_actuator` | poll | 500 | `modbus_tcp` | energy_generation |
| `dcs_controller` | `vfd` | poll | 100 | `modbus_tcp` | energy_generation |
| `safety_controller` | `dcs_controller` | safety | 50 | `modbus_tcp` | energy_generation |
| `safety_controller` | `valve_actuator` | safety | 50 | `modbus_tcp` | energy_generation |
| `protection_relay` | `protection_relay` | event | 1000 | `iec61850` | energy_generation |
| `scada_primary` | `protection_relay` | poll | 2000 | `iec61850`, `modbus_tcp` | energy_generation |
| `scada_primary` | `field_instrument` | poll | 2000 | `modbus_tcp` | energy_generation |
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
