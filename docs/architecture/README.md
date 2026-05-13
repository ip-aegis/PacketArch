# PacketArch Reference Architecture

PacketArch encodes a typed reference architecture for each industrial vertical it supports. This directory holds the auto-generated per-vertical reference docs — what roles exist, what archetypes are available, and which (src_role, tgt_role) pairs are valid in each vertical.

These docs are the same data the scenario generator uses to materialize templates and AI-generated scenarios. If you see a flow that doesn't appear here, the generator won't produce it — and you can use `/api/v1/architecture/check-flow` to validate any flow against the matrix.

## Verticals

- [Building Automation](building_automation.md)
- [Data Center Infra](data_center_infra.md)
- [Distribution Logistics](distribution_logistics.md)
- [Energy Generation](energy_generation.md)
- [Energy Substation](energy_substation.md)
- [Manufacturing Discrete](manufacturing_discrete.md)
- [Manufacturing Process](manufacturing_process.md)
- [Oil Gas](oil_gas.md)
- [Transportation Its](transportation_its.md)
- [Water Utility](water_utility.md)

## Source files

- `backend/app/services/architecture/role_catalog.py` — role taxonomy (44 roles)
- `backend/app/services/architecture/archetypes/` — per-vertical archetype definitions
- `backend/app/services/architecture/comm_matrix/` — communication matrix entries
- `backend/app/services/architecture/scenario_generator.py` — the materialization engine
