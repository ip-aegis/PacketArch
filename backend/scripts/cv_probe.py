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

            if what in ("devices", "matched", "all"):
                # Raw devices so we can read vulnerabilitiesCount (CVDevice drops it).
                raw = await svc._request("GET", "/devices", params={"page": 1, "size": 500})
                items = [d for d in (raw if isinstance(raw, list) else raw.get("items", [])) if d]

                def fw_of(d):
                    for p in (d.get("normalizedProperties") or []):
                        if "fw" in p.get("key", "").lower():
                            return p.get("value")
                    return None

                matched = [d for d in items if (d.get("vulnerabilitiesCount") or 0) > 0]
                print(f"\n=== DEVICES (aggregated): {len(items)} | with vulnerabilitiesCount>0: {len(matched)} ===")
                show = matched if what == "matched" else items
                for d in show[:60]:
                    vn = d.get("vulnerabilitiesCount") or 0
                    flag = f"  <-- {vn} CVE" if vn else ""
                    print(f"  {str(d.get('label') or '')[:32]:32} model={str(d.get('model') or d.get('deviceTypeDescription') or '')[:24]:24} "
                          f"fw={fw_of(d)} risk={d.get('riskScore')} vulnCount={vn}{flag}")

            if what in ("vulns", "all"):
                # NOTE: CV KB vuln records carry NO CPE/affected-version fields — matching is
                # internal to the CV Center and surfaced per-device as vulnerabilitiesCount
                # (see devices/matched). This just confirms a CVE exists in the KB.
                raw = await svc._request("GET", "/vulnerabilities", params={"limit": 5000, "offset": 0})
                kb = raw if isinstance(raw, list) else raw.get("items", [])
                print(f"\n=== VULNERABILITY KB: {len(kb)} CVEs (metadata only; no CPE in API) ===")
                want = ["CVE-2018-19282", "CVE-2021-22681", "CVE-2023-20198", "CVE-2020-15782"]
                ids = {(v.get("cve") or v.get("id")) for v in kb}
                for c in want:
                    print(f"  {c}: {'in KB' if c in ids else 'NOT in KB'}")

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
