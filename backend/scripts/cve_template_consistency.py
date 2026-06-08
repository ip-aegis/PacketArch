"""CVE <-> device-template consistency checker (gates the curation sweep).

Three invariants, reported per violation. This is the source the Phase B pytest
guard is promoted from; run it standalone to gate each vendor during curation.

  1. REACHABILITY     — every CVE whose affected_models matches a template must
                        have >=1 template firmware_variant inside its vulnerable
                        range. Else the CVE is in the DB/Browser but no device
                        can ever emit it.
  2. EMITTABILITY     — every template firmware_variant.cves entry must resolve
                        to a DB CVE that has a non-empty vulnerable_variants[]
                        (display-only CVEs can't be emitted).
  3. FIRMWARE-AGREEMENT— a template variant carrying cves=[C] must have a
                        `version` that equals (or falls within range of) C's DB
                        vulnerable_variants[].firmware_version, so the emitted
                        fingerprint firmware and the CVE override firmware agree.
"""
import re
from collections import defaultdict

from app.services.cve_data import ALL_CVES
from app.services.device_templates import get_all_templates


def vt(s):
    if not s:
        return None
    nums = re.findall(r"\d+", str(s))
    return tuple(int(n) for n in nums[:3]) if nums else None


def le(a, b):
    if a is None or b is None:
        return True
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) <= b + (0,) * (n - len(b))


cve_by_id = {c["cve_id"]: c for c in ALL_CVES}
cve_fw_versions = {
    c["cve_id"]: [vt(v.get("firmware_version")) for v in (c.get("vulnerable_variants") or [])]
    for c in ALL_CVES
}
cve_has_variants = {c["cve_id"]: bool(c.get("vulnerable_variants")) for c in ALL_CVES}

tpl_by_model = defaultdict(list)
for t in get_all_templates():
    for key in (t.model, t.model_name):
        if key:
            tpl_by_model[key].append(t)

reach_fail, emit_fail, agree_fail = [], [], []

# 1. reachability
for c in ALL_CVES:
    cid = c["cve_id"]
    models = c.get("affected_models") or []
    fmin, fmax = vt(c.get("affected_firmware_min")), vt(c.get("affected_firmware_max"))
    matched = [t for m in models for t in tpl_by_model.get(m, [])]
    if not matched:
        continue  # NO_TEMPLATE — not a reachability failure (IT/unmodeled)
    ok = False
    for t in matched:
        for fv in t.firmware_variants:
            f = vt(fv.version)
            if (le(fmin, f) and le(f, fmax)) or f in cve_fw_versions.get(cid, []):
                ok = True
    if not ok:
        sample = sorted({fv.version for t in matched for fv in t.firmware_variants})
        reach_fail.append((c.get("vendor"), cid, f"max={c.get('affected_firmware_max')}", sample))

# 2. emittability + 3. firmware-agreement
for t in get_all_templates():
    for fv in t.firmware_variants:
        for cid in fv.cves:
            c = cve_by_id.get(cid)
            if c is None:
                continue  # template-cve-not-in-DB is the EXISTING guard's job
            if not cve_has_variants.get(cid):
                emit_fail.append((t.vendor, t.model, fv.version, cid))
                continue
            fwv = vt(fv.version)
            db_fws = cve_fw_versions.get(cid, [])
            fmin, fmax = vt(c.get("affected_firmware_min")), vt(c.get("affected_firmware_max"))
            in_range = (le(fmin, fwv) and le(fwv, fmax)) or fwv in db_fws
            if not in_range:
                agree_fail.append((t.vendor, t.model, fv.version, cid,
                                   f"db_fw={[v for v in db_fws]} range<= {c.get('affected_firmware_max')}"))

print(f"REACHABILITY failures: {len(reach_fail)}")
for v in reach_fail:
    print(f"  {v[0]:<16} {v[1]:<18} {v[2]:<14} tpl_fws={v[3]}")
print(f"\nEMITTABILITY failures (template cve has no DB vulnerable_variant): {len(emit_fail)}")
for v in emit_fail:
    print(f"  {v[0]:<16} {v[1]:<22} fw={v[2]:<10} {v[3]}")
print(f"\nFIRMWARE-AGREEMENT failures (variant fw not in CVE range): {len(agree_fail)}")
for v in agree_fail:
    print(f"  {v[0]:<16} {v[1]:<22} tpl_fw={v[2]:<10} {v[3]:<18} {v[4]}")

total = len(reach_fail) + len(emit_fail) + len(agree_fail)
print(f"\nTOTAL violations: {total}")
