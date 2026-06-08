# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""CVE data-integrity guards.

These tests lock in the 2026-05-31 CVE/device realism audit so the
bulk-paste rot it removed cannot silently return. See
``tasks/cve-attack-device-audit.md``.

There are two disjoint CVE systems that must stay consistent:
1. The curated CVE DB: ``app.services.cve_data.ALL_CVES``.
2. Device templates: ``firmware_variants[].cves`` on each
   ``DeviceTemplate``. Every CVE a template references MUST resolve to a
   row in the CVE DB (or be on the explicit, documented whitelist below).
"""

import re

from app.services.cve_data import ALL_CVES
from app.services.device_templates import get_all_templates
from app.scenario_templates import VERTICAL_TEMPLATES


def _iter_cve_id_lists(obj):
    """Yield every ``cve_ids`` list found anywhere in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "cve_ids" and isinstance(v, list):
                yield v
            else:
                yield from _iter_cve_id_lists(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            yield from _iter_cve_id_lists(item)

# CVE IDs referenced by a template but intentionally NOT carried in the DB.
# Keep this EMPTY. Any addition must come with a written justification —
# an empty whitelist is the whole point of the template->DB guard.
TEMPLATE_CVE_DB_WHITELIST: set[str] = set()

_PLACEHOLDER_URL = re.compile(r"icsa-\d\d-XXX-XX", re.IGNORECASE)
_SEE_ADVISORY = re.compile(r"see .*advisor", re.IGNORECASE)
_CVE_ID = re.compile(r"^CVE-\d{4}-\d{4,}$")


def test_no_duplicate_cve_ids():
    """Every CVE appears exactly once in the curated DB."""
    seen: dict[str, int] = {}
    for c in ALL_CVES:
        seen[c["cve_id"]] = seen.get(c["cve_id"], 0) + 1
    dups = {k: v for k, v in seen.items() if v > 1}
    assert not dups, f"Duplicate CVE rows in DB: {dups}"


def test_cve_ids_well_formed():
    for c in ALL_CVES:
        assert _CVE_ID.match(c["cve_id"]), f"Malformed CVE id: {c['cve_id']!r}"


def test_no_placeholder_advisory_urls():
    """No icsa-YY-XXX-XX placeholder advisory URLs (guaranteed 404s)."""
    bad = [c["cve_id"] for c in ALL_CVES if _PLACEHOLDER_URL.search(c.get("advisory_url") or "")]
    assert not bad, f"Placeholder advisory URLs on: {bad}"


def test_no_see_advisory_fixed_firmware():
    """No 'see <vendor> advisory' fixed-firmware placeholders."""
    bad = [
        c["cve_id"]
        for c in ALL_CVES
        if _SEE_ADVISORY.search(str(c.get("fixed_firmware_version") or ""))
    ]
    assert not bad, f"Placeholder fixed_firmware_version on: {bad}"


def test_cvss_scores_in_range():
    for c in ALL_CVES:
        s = c.get("cvss_score")
        assert isinstance(s, (int, float)) and 0.0 <= s <= 10.0, (
            f"{c['cve_id']} has out-of-range cvss_score {s!r}"
        )


def test_every_template_cve_exists_in_db():
    """The cross-system invariant: every template-referenced CVE resolves
    to a curated DB row (or is explicitly whitelisted)."""
    db_ids = {c["cve_id"] for c in ALL_CVES}
    missing: dict[str, list[str]] = {}
    for t in get_all_templates():
        for fv in t.firmware_variants:
            for cid in fv.cves or []:
                if cid not in db_ids and cid not in TEMPLATE_CVE_DB_WHITELIST:
                    missing.setdefault(cid, []).append(t.id)
    assert not missing, (
        "Template CVEs absent from the CVE DB (add a DB record or whitelist "
        f"with justification): {sorted(missing)}"
    )


def test_every_scenario_template_cve_exists_in_db():
    """Same cross-system invariant for the vertical scenario templates:
    every device ``cve_ids`` entry must resolve to a curated DB row.

    (Vertical scenarios now pin ``firmware_version`` and derive CVEs from the
    device-template menu, so this is usually vacuous — but it still guards any
    explicit legacy ``cve_ids`` that remain or get re-added.)"""
    db_ids = {c["cve_id"] for c in ALL_CVES}
    missing: set[str] = set()
    for vertical in VERTICAL_TEMPLATES.values():
        for cve_list in _iter_cve_id_lists(vertical):
            for cid in cve_list:
                if cid not in db_ids and cid not in TEMPLATE_CVE_DB_WHITELIST:
                    missing.add(cid)
    assert not missing, (
        f"Scenario-template CVEs absent from the CVE DB: {sorted(missing)}"
    )


# --- Menu reachability / emittability / firmware-agreement -----------------
# These lock in the 2026-06-08 device-menu curation: the device template is the
# flexible CVE menu and the scenario pins a firmware_version, so a CVE only
# shows in Cyber Vision if SOME template firmware variant emits a version inside
# the CVE's real vulnerable range. Promoted from scripts/cve_template_consistency.py.

def _vtuple(s):
    """Crude firmware version -> comparable int tuple (digits only)."""
    if not s:
        return None
    nums = re.findall(r"\d+", str(s))
    return tuple(int(n) for n in nums[:3]) if nums else None


def _le(a, b):
    """a <= b over ragged tuples; None on either side means 'unbounded'."""
    if a is None or b is None:
        return True
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) <= b + (0,) * (n - len(b))


def _templates_by_model():
    from collections import defaultdict
    idx = defaultdict(list)
    for t in get_all_templates():
        for key in (t.model, t.model_name):
            if key:
                idx[key].append(t)
    return idx


def test_cve_reachability():
    """Every CVE whose affected_models matches a device template must have >=1
    template firmware variant inside its vulnerable range — else the CVE is in
    the DB/Browser but no device the tool builds can ever emit it."""
    by_model = _templates_by_model()
    fw_versions = {
        c["cve_id"]: [_vtuple(v.get("firmware_version")) for v in (c.get("vulnerable_variants") or [])]
        for c in ALL_CVES
    }
    unreachable: list[str] = []
    for c in ALL_CVES:
        models = c.get("affected_models") or []
        matched = [t for m in models for t in by_model.get(m, [])]
        if not matched:
            continue  # NO_TEMPLATE — unmodeled / IT CVE, acceptable
        fmin, fmax = _vtuple(c.get("affected_firmware_min")), _vtuple(c.get("affected_firmware_max"))
        ok = any(
            (_le(fmin, _vtuple(fv.version)) and _le(_vtuple(fv.version), fmax))
            or _vtuple(fv.version) in fw_versions.get(c["cve_id"], [])
            for t in matched for fv in t.firmware_variants
        )
        if not ok:
            unreachable.append(c["cve_id"])
    assert not unreachable, (
        "CVEs whose vulnerable range no matching template firmware can emit "
        f"(unreachable in Cyber Vision): {sorted(unreachable)}"
    )


def test_template_cves_are_emittable():
    """Every CVE a template firmware variant carries must have a non-empty
    vulnerable_variants[] in the DB (display-only CVEs cannot be emitted)."""
    has_variants = {c["cve_id"]: bool(c.get("vulnerable_variants")) for c in ALL_CVES}
    bad: list[str] = []
    for t in get_all_templates():
        for fv in t.firmware_variants:
            for cid in fv.cves or []:
                if cid in has_variants and not has_variants[cid]:
                    bad.append(f"{t.model}:{cid}")
    assert not bad, f"Template CVEs with no emittable DB vulnerable_variant: {sorted(bad)}"


def test_template_firmware_agrees_with_cve_range():
    """A template variant carrying cves=[C] must have a version inside C's real
    vulnerable range, so the emitted fingerprint firmware and the CVE override
    firmware agree on the wire (and CV actually matches)."""
    cve_by_id = {c["cve_id"]: c for c in ALL_CVES}
    fw_versions = {
        c["cve_id"]: [_vtuple(v.get("firmware_version")) for v in (c.get("vulnerable_variants") or [])]
        for c in ALL_CVES
    }
    bad: list[str] = []
    for t in get_all_templates():
        for fv in t.firmware_variants:
            for cid in fv.cves or []:
                c = cve_by_id.get(cid)
                if c is None:
                    continue  # covered by test_every_template_cve_exists_in_db
                fwv = _vtuple(fv.version)
                fmin, fmax = _vtuple(c.get("affected_firmware_min")), _vtuple(c.get("affected_firmware_max"))
                in_range = (_le(fmin, fwv) and _le(fwv, fmax)) or fwv in fw_versions.get(cid, [])
                if not in_range:
                    bad.append(f"{t.model} fw={fv.version} carries {cid} (range<= {c.get('affected_firmware_max')})")
    assert not bad, f"Template firmware out of its CVE's vulnerable range: {sorted(bad)}"
