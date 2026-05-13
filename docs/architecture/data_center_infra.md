# Reference Architecture: Data Center Infra

*Auto-generated from the PacketArch architecture rail. Edit the source under `backend/app/services/architecture/` and re-run `scripts/export_architecture_docs.py` to regenerate.*

## Archetypes (1)

### Archetype: `data_center_infra_dcim` — Data Center — DCIM Facility

Facility-side OT for a colocation / hyperscale data center: DCIM server polls PDUs, UPSes, CRAC units, branch-circuit monitors, and chiller plant. No DCS, no PLC cells — it's network gear and power/cooling field equipment.

- **Pattern**: `dcim_facility`
- **Default vendor profile**: `dcim_cisco`
- **Supported vendor profiles**: `dcim_cisco`, `bas_tridium`
- **Min scale**: `demo`
- **Default cell isolation**: `conduit_gated`

#### Zone skeleton

| Zone | Purdue | Security | Roles |
|---|---|---|---|
| `idmz` (IT/Facility Boundary) | L3.5 | critical | `jump_server`, `wan_edge_router`, `core_switch` |
| `operations` (DCIM Operations) | L3.0 | high | `scada_primary`, `process_historian`, `nms_server`, `engineering_workstation`, `core_switch` |
| `rack1` (Rack Row 1) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack2` (Rack Row 2) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack3` (Rack Row 3) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack4` (Rack Row 4) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack5` (Rack Row 5) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack6` (Rack Row 6) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack7` (Rack Row 7) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack8` (Rack Row 8) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack9` (Rack Row 9) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack10` (Rack Row 10) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack11` (Rack Row 11) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack12` (Rack Row 12) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack13` (Rack Row 13) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack14` (Rack Row 14) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack15` (Rack Row 15) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `rack16` (Rack Row 16) | L1.0 | standard | `vfd`, `field_instrument`, `cell_switch` |
| `cooling` (Mechanical / Cooling) | L1.0 | standard | `bms_field_controller`, `vfd`, `field_instrument`, `cell_switch` |
| `power` (Power Plant (UPS / Generators)) | L1.0 | high | `cell_controller`, `vfd`, `field_instrument`, `cell_switch` |

#### Conduits (allowed cross-zone protocols)

| Conduit | Direction | Allowed protocols |
|---|---|---|
| `idmz` ↔ `operations` | bidirectional | `https`, `snmp`, `rdp`, `ssh` |
| `operations` ↔ `rack1` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack2` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack3` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack4` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack5` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack6` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack7` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack8` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack9` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack10` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack11` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack12` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack13` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack14` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack15` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `rack16` | bidirectional | `snmp`, `modbus_tcp`, `https` |
| `operations` ↔ `cooling` | bidirectional | `bacnet`, `modbus_tcp`, `snmp` |
| `operations` ↔ `power` | bidirectional | `modbus_tcp`, `snmp`, `https` |

#### Notes

- Rack-row counts: DEMO=1, SMALL=2, MEDIUM=4, LARGE=8, MULTI_SITE=16.
- PDUs are modeled under the `vfd` role (catalog stand-in for smart power devices). Future: dedicated `power_distribution_unit` role with its own SNMP-only catalog entries.

## Role catalog (19 roles applicable)

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
| `cell_controller` | L1.0 | control | snmp | Required in every discrete/cell-based scenario. One or more per cell. |
| `distributed_io` | L0.0 | process | snmp | Include in any cell with field-mounted sensors/actuators that aren't directly wired to the controller chassis. |
| `vfd` | L0.0 | process | snmp | Include in any scenario with motors. Common in manufacturing, water (pumps), oil_gas (compressors), BAS (fans). |
| `core_switch` | L3.0 | network_infra | snmp | Required: every scenario has at least one. The L3 spine. |
| `cell_switch` | L2.0 | network_infra | snmp | Include one per cell in cell-based topologies. |
| `wan_edge_router` | L3.5 | network_infra | snmp | Include in any scenario with WAN connectivity (most). Optional for fully air-gapped demo scenarios. |

## Communication matrix (39 entries)

Each row is a typed `(src_role, tgt_role) → protocol/pattern` rule that the scenario generator uses to materialize flows. Cross-vertical SHARED entries appear at the bottom.

| Source role | Target role | Pattern | Interval (ms) | Protocols | Vertical |
|---|---|---|---|---|---|
| `scada_primary` | `vfd` | poll | 30000 | `snmp`, `modbus_tcp` | data_center_infra |
| `scada_primary` | `field_instrument` | poll | 60000 | `snmp`, `modbus_tcp`, `bacnet` | data_center_infra |
| `scada_primary` | `bms_field_controller` | poll | 10000 | `bacnet`, `modbus_tcp`, `snmp` | data_center_infra |
| `scada_primary` | `cell_controller` | poll | 5000 | `modbus_tcp`, `snmp` | data_center_infra |
| `cell_controller` | `vfd` | poll | 1000 | `modbus_tcp` | data_center_infra |
| `cell_controller` | `field_instrument` | poll | 2000 | `modbus_tcp` | data_center_infra |
| `bms_field_controller` | `vfd` | poll | 2000 | `bacnet`, `modbus_tcp` | data_center_infra |
| `bms_field_controller` | `field_instrument` | poll | 5000 | `bacnet`, `modbus_tcp` | data_center_infra |
| `process_historian` | `vfd` | subscription | 60000 | `snmp`, `modbus_tcp` | data_center_infra |
| `process_historian` | `bms_field_controller` | subscription | 60000 | `bacnet`, `modbus_tcp` | data_center_infra |
| `engineering_workstation` | `bms_field_controller` | configuration | 600000 | `https`, `ssh`, `bacnet` | data_center_infra |
| `engineering_workstation` | `cell_controller` | configuration | 600000 | `https`, `ssh`, `modbus_tcp` | data_center_infra |
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
