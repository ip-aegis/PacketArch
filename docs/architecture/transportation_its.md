# Reference Architecture: Transportation Its

*Auto-generated from the PacketArch architecture rail. Edit the source under `backend/app/services/architecture/` and re-run `scripts/export_architecture_docs.py` to regenerate.*

## Archetypes (1)

### Archetype: `transportation_atms_corridor` — Transportation — ATMS Corridor

Advanced Traffic Management System for an urban corridor or highway: central TMC with ATMS master + operator HMI + NMS, and per-intersection roadside cabinets running ATC/2070-class controllers. Communication is NTCIP-over-SNMP; a single operator manages tens to hundreds of intersections.

- **Pattern**: `atms_corridor`
- **Default vendor profile**: `atms_ntcip`
- **Supported vendor profiles**: `atms_ntcip`
- **Min scale**: `demo`
- **Default cell isolation**: `off`

#### Zone skeleton

| Zone | Purdue | Security | Roles |
|---|---|---|---|
| `idmz` (IT/Traffic Boundary) | L3.5 | critical | `jump_server`, `reverse_proxy`, `wan_edge_router`, `core_switch` |
| `operations` (Traffic Management Center) | L3.0 | high | `scada_primary`, `process_historian`, `engineering_workstation`, `nms_server`, `core_switch` |
| `intersection1` (Intersection 1) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection2` (Intersection 2) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection3` (Intersection 3) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection4` (Intersection 4) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection5` (Intersection 5) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection6` (Intersection 6) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection7` (Intersection 7) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection8` (Intersection 8) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection9` (Intersection 9) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection10` (Intersection 10) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection11` (Intersection 11) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection12` (Intersection 12) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection13` (Intersection 13) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection14` (Intersection 14) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection15` (Intersection 15) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |
| `intersection16` (Intersection 16) | L1.0 | standard | `traffic_controller`, `cabinet_controller`, `cell_switch` |

#### Conduits (allowed cross-zone protocols)

| Conduit | Direction | Allowed protocols |
|---|---|---|
| `idmz` ↔ `operations` | bidirectional | `https`, `snmp`, `ssh` |
| `operations` ↔ `intersection1` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection2` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection3` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection4` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection5` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection6` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection7` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection8` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection9` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection10` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection11` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection12` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection13` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection14` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection15` | bidirectional | `snmp`, `https` |
| `operations` ↔ `intersection16` | bidirectional | `snmp`, `https` |

#### Notes

- Intersection counts: DEMO=1, SMALL=3, MEDIUM=6, LARGE=10, MULTI_SITE=16.
- NTCIP rides on SNMP — that's why SNMP from the ATMS master is operationally legitimate (not just admin-style).

## Role catalog (21 roles applicable)

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
| `field_rtu` | L1.0 | control | snmp | Include in master-remote SCADA scenarios: water utility (per pump station), energy substation (per bay), oil_gas (per wellhead/compressor). |
| `traffic_controller` | L1.0 | control | snmp | Required in transportation_its. One per intersection / ramp meter / DMS. |
| `cabinet_controller` | L1.0 | control | snmp | Optional. Include when scenario models DMS, CCTV, or RWIS. |
| `distributed_io` | L0.0 | process | snmp | Include in any cell with field-mounted sensors/actuators that aren't directly wired to the controller chassis. |
| `vfd` | L0.0 | process | snmp | Include in any scenario with motors. Common in manufacturing, water (pumps), oil_gas (compressors), BAS (fans). |
| `core_switch` | L3.0 | network_infra | snmp | Required: every scenario has at least one. The L3 spine. |
| `cell_switch` | L2.0 | network_infra | snmp | Include one per cell in cell-based topologies. |
| `wan_edge_router` | L3.5 | network_infra | snmp | Include in any scenario with WAN connectivity (most). Optional for fully air-gapped demo scenarios. |

## Communication matrix (31 entries)

Each row is a typed `(src_role, tgt_role) → protocol/pattern` rule that the scenario generator uses to materialize flows. Cross-vertical SHARED entries appear at the bottom.

| Source role | Target role | Pattern | Interval (ms) | Protocols | Vertical |
|---|---|---|---|---|---|
| `scada_primary` | `traffic_controller` | poll | 1000 | `snmp` | transportation_its |
| `scada_primary` | `cabinet_controller` | poll | 5000 | `snmp`, `https` | transportation_its |
| `process_historian` | `traffic_controller` | subscription | 60000 | `snmp` | transportation_its |
| `engineering_workstation` | `traffic_controller` | configuration | 600000 | `ssh`, `https`, `snmp` | transportation_its |
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
