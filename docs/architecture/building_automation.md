# Reference Architecture: Building Automation

*Auto-generated from the PacketArch architecture rail. Edit the source under `backend/app/services/architecture/` and re-run `scripts/export_architecture_docs.py` to regenerate.*

## Archetypes (1)

### Archetype: `building_automation_bas_supervisor` — Building Automation — BAS Supervisor

BACnet/IP building automation: a BAS supervisor (Niagara JACE / Distech / Honeywell EBI) at L3 supervises per-zone field controllers handling HVAC, lighting, and access control. Standard for commercial offices, university campuses, data-center facility-side BAS.

- **Pattern**: `bas_supervisor`
- **Default vendor profile**: `bas_tridium`
- **Supported vendor profiles**: `bas_tridium`
- **Min scale**: `demo`
- **Default cell isolation**: `conduit_gated`

#### Zone skeleton

| Zone | Purdue | Security | Roles |
|---|---|---|---|
| `idmz` (IT/BAS Boundary) | L3.5 | critical | `jump_server`, `remote_access_gateway`, `wan_edge_router`, `core_switch` |
| `operations` (BAS Supervisor) | L3.0 | high | `scada_primary`, `process_historian`, `engineering_workstation`, `nms_server`, `core_switch` |
| `zone1` (BAS Zone 1) | L1.0 | standard | `bms_field_controller`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `zone2` (BAS Zone 2) | L1.0 | standard | `bms_field_controller`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `zone3` (BAS Zone 3) | L1.0 | standard | `bms_field_controller`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |
| `zone4` (BAS Zone 4) | L1.0 | standard | `bms_field_controller`, `vfd`, `field_instrument`, `valve_actuator`, `cell_switch` |

#### Conduits (allowed cross-zone protocols)

| Conduit | Direction | Allowed protocols |
|---|---|---|
| `idmz` ↔ `operations` | bidirectional | `https`, `snmp`, `rdp`, `ssh` |
| `operations` ↔ `zone1` | bidirectional | `bacnet`, `modbus_tcp`, `snmp` |
| `operations` ↔ `zone2` | bidirectional | `bacnet`, `modbus_tcp`, `snmp` |
| `operations` ↔ `zone3` | bidirectional | `bacnet`, `modbus_tcp`, `snmp` |
| `operations` ↔ `zone4` | bidirectional | `bacnet`, `modbus_tcp`, `snmp` |

#### Notes

- Zone counts: DEMO=1, SMALL=2, MEDIUM=3, LARGE/MULTI_SITE=4.
- BACnet/IP is the default; vendor profile drives whether MS/TP fallback or pure /IP is used.

## Role catalog (22 roles applicable)

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
| `cell_controller` | L1.0 | control | snmp | Required in every discrete/cell-based scenario. One or more per cell. |
| `bms_field_controller` | L1.0 | control | bacnet, snmp | Required in building_automation. One per zone or AHU. |
| `distributed_io` | L0.0 | process | snmp | Include in any cell with field-mounted sensors/actuators that aren't directly wired to the controller chassis. |
| `vfd` | L0.0 | process | snmp | Include in any scenario with motors. Common in manufacturing, water (pumps), oil_gas (compressors), BAS (fans). |
| `field_instrument` | L0.0 | process | snmp | Include in process verticals (manufacturing_process, oil_gas, water, energy_generation) and BAS. |
| `core_switch` | L3.0 | network_infra | snmp | Required: every scenario has at least one. The L3 spine. |
| `cell_switch` | L2.0 | network_infra | snmp | Include one per cell in cell-based topologies. |
| `wan_edge_router` | L3.5 | network_infra | snmp | Include in any scenario with WAN connectivity (most). Optional for fully air-gapped demo scenarios. |

## Communication matrix (33 entries)

Each row is a typed `(src_role, tgt_role) → protocol/pattern` rule that the scenario generator uses to materialize flows. Cross-vertical SHARED entries appear at the bottom.

| Source role | Target role | Pattern | Interval (ms) | Protocols | Vertical |
|---|---|---|---|---|---|
| `scada_primary` | `bms_field_controller` | poll | 5000 | `bacnet`, `modbus_tcp` | building_automation |
| `process_historian` | `bms_field_controller` | subscription | 30000 | `bacnet` | building_automation |
| `engineering_workstation` | `bms_field_controller` | configuration | 300000 | `https`, `ssh`, `bacnet` | building_automation |
| `bms_field_controller` | `vfd` | poll | 2000 | `bacnet`, `modbus_tcp` | building_automation |
| `bms_field_controller` | `field_instrument` | poll | 5000 | `bacnet`, `modbus_tcp` | building_automation |
| `bms_field_controller` | `valve_actuator` | poll | 5000 | `bacnet`, `modbus_tcp` | building_automation |
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
