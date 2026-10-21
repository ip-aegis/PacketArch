# NTCIP-on-the-wire validation (2026-10-21)

These are the evidence scripts for `docs/ITS_ROADWAY_AUDIT_2026_10.md` §1.

- `e2e_ntcip.py`: runs the pipeline exactly as shipped. Steps: archetype → `auto_repair_protocols`/`repair_flow_protocols` → `_build_flow_contexts` → `UnifiedOrchestrator` + `PcapOutput` (30 s virtual) → scapy decode of SNMP response OIDs, grouped by destination role.
- `e2e_forced.py`: the same run, with `device_type="asc"` forced onto the controller flows. It shows what Phase 0.4 alone would emit.

## Run

The host has no poetry. Use a throwaway venv with the backend dependencies from `backend/pyproject.toml`: scapy, sqlalchemy[asyncio], asyncpg, psycopg2-binary, celery[redis], pydantic-settings, python-statemachine, numpy, scipy, httpx, python-jose and passlib.

```bash
SECRET_KEY=$(openssl rand -hex 32) venv/bin/python -I tasks/audit-results/its-ntcip/e2e_ntcip.py transportation_atms_corridor /tmp/its.pcap
SECRET_KEY=$(openssl rand -hex 32) venv/bin/python -I tasks/audit-results/its-ntcip/e2e_forced.py transportation_atms_corridor /tmp/its_forced.pcap
```

A Postgres `OperationalError` traceback appears during flow building. It comes from a fingerprint lookup trying the DB, and it is expected and harmless: the run continues and the results print afterwards.

## Results on master 475fbb8

| Run | Packets | NTCIP varbinds (`1.3.6.1.4.1.1206.4.*`) |
|---|---|---|
| As shipped | 3,058 | **0**. Controllers return only `1.3.6.1.2.1.1.{1,2,3,5,6}.0` |
| Forced `device_type=asc` | 3,078 | 330, **all value 0**, all under `1206.4.2.2.*` (wrong arc), `.0` scalars |

After Phase 0, the as-shipped run should show NTCIP varbinds for every controller, DMS and ESS, with nonzero and phase-consistent values.
