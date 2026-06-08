"""Cyber Vision review probe — query CV at BOTH the component and device level.

CV ingests raw observed entities as *components* (per MAC/IP) first, then
aggregates/classifies them into *devices*. The PacketArch UI + /cyber-vision/devices
route show the DEVICE level (aggregated, lags); to see what CV is currently
OBSERVING (incl. still-ingesting OT entities), look at components.

Run inside the backend container:
    docker compose exec -T backend python /app/scripts/cv_probe.py [components|devices|vulns|presets|groups|all]
"""
import asyncio
import sys
from collections import Counter

from app.core.database import async_session_maker
from app.api.routes.cyber_vision import get_cv_service


def _tally(rows, vendor_key, fw_key=None):
    vc = Counter()
    for r in rows:
        v = (r.get(vendor_key) or "?") if isinstance(r, dict) else (getattr(r, vendor_key, None) or "?")
        vc[str(v).split(",")[0]] += 1
    return vc


async def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    async with async_session_maker() as db:
        svc = await get_cv_service(db)
        try:
            if what in ("components", "all"):
                comps = await svc.get_components()
                print(f"\n=== COMPONENTS (raw, pre-aggregation): {len(comps)} ===")
                vc = Counter()
                for c in comps:
                    vc[str(c.get("vendor") or c.get("manufacturer") or "?").split(",")[0]] += 1
                print("vendor tally:", dict(vc.most_common(20)))
                # sample with model/fw/ip/mac
                for c in comps[:40]:
                    print(f"  {str(c.get('name') or c.get('label') or '')[:34]:34} "
                          f"v={str(c.get('vendor') or '')[:18]:18} "
                          f"model={c.get('model')} fw={c.get('firmwareVersion') or c.get('firmware')} "
                          f"ip={c.get('ip')} mac={c.get('mac')}")

            if what in ("devices", "all"):
                devs = await svc.get_devices(size=500)
                print(f"\n=== DEVICES (aggregated): {len(devs)} ===")
                vc = Counter((d.vendor or "?").split(",")[0] for d in devs)
                print("vendor tally:", dict(vc.most_common(20)))
                for d in devs[:40]:
                    print(f"  {str(d.name or '')[:34]:34} v={str(d.vendor or '')[:18]:18} "
                          f"model={d.model} fw={d.firmware} ip={d.ip} risk={d.risk_score}")

            if what in ("vulns", "all"):
                vulns = await svc.get_vulnerabilities(limit=500)
                # CVVulnerability dataclass objects (not dicts)
                hits = [v for v in vulns if (getattr(v, "affected_device_count", 0) or 0) > 0]
                print(f"\n=== VULNERABILITIES: {len(vulns)} in KB | {len(hits)} matched to >=1 device ===")
                for v in sorted(hits, key=lambda x: -(x.affected_device_count or 0)):
                    print(f"  {getattr(v, 'cve_id', '?'):20} n={v.affected_device_count} "
                          f"sev={getattr(v, 'severity', '?')!s:9} {str(getattr(v, 'title', ''))[:55]}")

            if what in ("presets", "all"):
                presets = await svc.get_presets()
                print(f"\n=== PRESETS: {len(presets)} ===")
                for p in presets[:30]:
                    print(f"  id={p.get('id')} name={p.get('label') or p.get('name')}")

            if what in ("groups", "all"):
                groups = await svc.get_groups()
                print(f"\n=== GROUPS: {len(groups)} ===")
                for g in groups[:30]:
                    print(f"  id={g.get('id')} name={g.get('label') or g.get('name')}")
        finally:
            await svc.close()


asyncio.run(main())
