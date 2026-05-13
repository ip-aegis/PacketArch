# Reference Architecture: Water Utility

*Auto-generated from the PacketArch architecture rail. Edit the source under `backend/app/services/architecture/` and re-run `scripts/export_architecture_docs.py` to regenerate.*

## Archetypes (1)

### Archetype: `water_utility_master_remote` — Water Utility — Master/Remote SCADA

Municipal / regional water utility with central control room and remote pump stations / lift stations. RTAC at central aggregates field RTUs over WAN; SCADA provides operator view; vendor remote access for service techs.

- **Pattern**: `master_remote_scada`
- **Default vendor profile**: `mixed_field`
- **Supported vendor profiles**: `mixed_field`, `scadapack`, `schneider_shop`
- **Min scale**: `demo`
- **Default cell isolation**: `conduit_gated`

#### Zone skeleton

| Zone | Purdue | Security | Roles |
|---|---|---|---|
| `idmz` (Industrial DMZ) | L3.5 | critical | `jump_server`, `remote_access_gateway`, `patch_staging_server`, `wan_edge_router`, `core_switch` |
| `central` (Central Control) | L3.0 | high | `scada_primary`, `scada_standby`, `process_historian`, `aggregator_rtu`, `engineering_workstation`, `nms_server`, `core_switch` |
| `station1` (Pump Station 1) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station2` (Pump Station 2) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station3` (Pump Station 3) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station4` (Pump Station 4) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station5` (Pump Station 5) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station6` (Pump Station 6) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station7` (Pump Station 7) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station8` (Pump Station 8) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station9` (Pump Station 9) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station10` (Pump Station 10) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station11` (Pump Station 11) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `station12` (Pump Station 12) | L1.0 | standard | `field_rtu`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |

#### Conduits (allowed cross-zone protocols)

| Conduit | Direction | Allowed protocols |
|---|---|---|
| `idmz` ↔ `central` | bidirectional | `https`, `snmp`, `rdp`, `ssh` |
| `central` ↔ `station1` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station2` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station3` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station4` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station5` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station6` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station7` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station8` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station9` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station10` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station11` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |
| `central` ↔ `station12` | bidirectional | `modbus_tcp`, `dnp3`, `iec104`, `snmp` |

#### Notes

- Station counts: DEMO=1, SMALL=3, MEDIUM=5, LARGE=8, MULTI_SITE=12.
- IDMZ collapses into central at DEMO/SMALL (jump server is optional below MEDIUM).
- Field RTUs talk DNP3 / Modbus TCP to RTAC over WAN; vendor selection drives whether DNP3 or IEC 104 dominates.

## Role catalog (25 roles applicable)

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
| `nms_server` | L3.0 | operations | snmp | Include in every scenario at scale >= small. The NMS is the canonical SNMP source — without it, switches end up orphaned for Cyber Vision discovery. |
| `ot_domain_controller` | L3.0 | operations | snmp | Optional. Include at scale >= medium for centralized auth across SCADA/HMI/engineering hosts. |
| `area_hmi` | L2.0 | area | snmp | Include one per cell/area in discrete-cell manufacturing, BAS supervisor zones, oil/gas process areas. Skip in pure master-remote SCADA topologies (water/energy substation). |
| `local_historian` | L2.0 | area | snmp | Optional. Include in distributed scenarios (multi-site, remote oil&gas, distributed water). |
| `cell_controller` | L1.0 | control | snmp | Required in every discrete/cell-based scenario. One or more per cell. |
| `field_rtu` | L1.0 | control | snmp | Include in master-remote SCADA scenarios: water utility (per pump station), energy substation (per bay), oil_gas (per wellhead/compressor). |
| `aggregator_rtu` | L1.5 | control | snmp | Include one per site in master-remote SCADA scenarios. In substations, this is the SEL-3530 / SEL-3555 RTAC. |
| `distributed_io` | L0.0 | process | snmp | Include in any cell with field-mounted sensors/actuators that aren't directly wired to the controller chassis. |
| `vfd` | L0.0 | process | snmp | Include in any scenario with motors. Common in manufacturing, water (pumps), oil_gas (compressors), BAS (fans). |
| `field_instrument` | L0.0 | process | snmp | Include in process verticals (manufacturing_process, oil_gas, water, energy_generation) and BAS. |
| `valve_actuator` | L0.0 | process | snmp | Include in process verticals and water/wastewater. Modeled per major valve when specifically interesting. |
| `core_switch` | L3.0 | network_infra | snmp | Required: every scenario has at least one. The L3 spine. |
| `cell_switch` | L2.0 | network_infra | snmp | Include one per cell in cell-based topologies. |
| `wan_edge_router` | L3.5 | network_infra | snmp | Include in any scenario with WAN connectivity (most). Optional for fully air-gapped demo scenarios. |

## Communication matrix (35 entries)

Each row is a typed `(src_role, tgt_role) → protocol/pattern` rule that the scenario generator uses to materialize flows. Cross-vertical SHARED entries appear at the bottom.

| Source role | Target role | Pattern | Interval (ms) | Protocols | Vertical |
|---|---|---|---|---|---|
| `scada_primary` | `aggregator_rtu` | poll | 2000 | `modbus_tcp`, `dnp3` | water_utility |
| `process_historian` | `aggregator_rtu` | subscription | 5000 | `modbus_tcp`, `dnp3` | water_utility |
| `engineering_workstation` | `aggregator_rtu` | configuration | 120000 | `ssh`, `https` | water_utility |
| `aggregator_rtu` | `field_rtu` | poll | 5000 | `modbus_tcp`, `dnp3` | water_utility |
| `engineering_workstation` | `field_rtu` | configuration | 600000 | `ssh`, `https` | water_utility |
| `field_rtu` | `vfd` | poll | 500 | `modbus_tcp` | water_utility |
| `field_rtu` | `field_instrument` | poll | 1000 | `modbus_tcp` | water_utility |
| `field_rtu` | `valve_actuator` | poll | 500 | `modbus_tcp` | water_utility |
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
