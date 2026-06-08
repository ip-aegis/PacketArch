"""Reachability audit: for every seeded CVE, can ANY device template actually
emit a firmware version inside the CVE's vulnerable range? If not, the CVE is
present in the DB / CVE Browser but can NEVER be detected by Cyber Vision,
because no device the tool builds will emit matching firmware.

Classifies each CVE as:
  REACHABLE        - a matching template has >=1 firmware variant in range
  UNREACHABLE_FW   - a matching template exists, but ALL its firmware is out of range
  NO_TEMPLATE      - no device template matches any affected_model at all
"""
import re
from collections import defaultdict

from app.services.cve_data import ALL_CVES
from app.services.device_templates import get_all_templates


def vtuple(s):
    """Crude version -> comparable tuple. Extracts numeric groups, drops letters.
    'V6.003' -> (6,3); '5.001' -> (5,1); 'D4.0' -> (4,0); '14.00.00 (CPR..)'->(14,0,0)."""
    if not s:
        return None
    nums = re.findall(r"\d+", str(s))
    if not nums:
        return None
    return tuple(int(n) for n in nums[:3])


def le(a, b):
    """a <= b with ragged tuples (pad shorter with zeros)."""
    if a is None or b is None:
        return True  # unbounded side
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    return a <= b


# index templates by both model and model_name
tpl_by_model = defaultdict(list)
for t in get_all_templates():
    model = getattr(t, "model", None)
    model_name = getattr(t, "model_name", None)
    fws = []
    for fv in (getattr(t, "firmware_variants", None) or []):
        fws.append(getattr(fv, "version", None))
    rec = {"vendor": getattr(t, "vendor", "?"), "model": model,
           "model_name": model_name, "fws": fws}
    if model:
        tpl_by_model[model].append(rec)
    if model_name:
        tpl_by_model[model_name].append(rec)

results = []
for cve in ALL_CVES:
    cid = cve.get("cve_id")
    vendor = cve.get("vendor", "?")
    models = cve.get("affected_models") or []
    fmin = vtuple(cve.get("affected_firmware_min"))
    fmax = vtuple(cve.get("affected_firmware_max"))
    # also consider vulnerable_variant firmware versions as explicit in-range points
    vv_fws = [vtuple(v.get("firmware_version")) for v in (cve.get("vulnerable_variants") or [])]

    matched = []
    for m in models:
        matched.extend(tpl_by_model.get(m, []))
    if not matched:
        results.append((vendor, cid, "NO_TEMPLATE", models, None))
        continue

    in_range = False
    sample = []
    for rec in matched:
        for fw in rec["fws"]:
            fv = vtuple(fw)
            sample.append(fw)
            # in range if fmin <= fv <= fmax
            if le(fmin, fv) and le(fv, fmax):
                in_range = True
            # or exactly equals a declared vulnerable variant firmware
            if fv in vv_fws:
                in_range = True
    status = "REACHABLE" if in_range else "UNREACHABLE_FW"
    results.append((vendor, cid, status, f"max={cve.get('affected_firmware_max')}",
                    f"tpl_fws={sorted(set(sample))}"))

# aggregate
per_vendor = defaultdict(lambda: defaultdict(int))
for vendor, cid, status, *_ in results:
    per_vendor[vendor][status] += 1

print("=== CVE REACHABILITY BY VENDOR (can any device emit in-range firmware?) ===")
print(f"{'vendor':<18} {'REACHABLE':>10} {'UNREACH_FW':>11} {'NO_TEMPLATE':>12} {'total':>6}")
gtot = defaultdict(int)
for vendor in sorted(per_vendor):
    d = per_vendor[vendor]
    tot = sum(d.values())
    for k, v in d.items():
        gtot[k] += v
    print(f"{vendor:<18} {d['REACHABLE']:>10} {d['UNREACHABLE_FW']:>11} {d['NO_TEMPLATE']:>12} {tot:>6}")
print("-" * 60)
tot = sum(gtot.values())
print(f"{'TOTAL':<18} {gtot['REACHABLE']:>10} {gtot['UNREACHABLE_FW']:>11} {gtot['NO_TEMPLATE']:>12} {tot:>6}")

print("\n=== UNREACHABLE (matching template, but firmware out of range) ===")
for vendor, cid, status, a, b in results:
    if status == "UNREACHABLE_FW":
        print(f"  {vendor:<14} {cid:<18} {a:<16} {b}")
