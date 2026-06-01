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
    every device ``cve_ids`` entry must resolve to a curated DB row."""
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
