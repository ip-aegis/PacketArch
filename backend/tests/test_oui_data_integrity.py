# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""OUI data-integrity guards.

Every OUI PacketArch ships must resolve, in the real IEEE registry, to the
device's vendor (or a documented parent / embedded-module / virtualization
owner). These guards keep the IEEE-grounded data from drifting back into the
hand-curated fabrications that made a Yokogawa analyzer show up as "Siemon".
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

from app.core.vendor_normalize import normalize_vendor
from app.protocol_engines._vendor_ouis_generated import VENDOR_OUIS
from app.services.device_templates import get_all_fingerprints

BACKEND = Path(__file__).resolve().parents[1]
CSV_PATH = BACKEND / "app" / "protocol_engines" / "data" / "ieee_oui.csv"

# Vendors with no IEEE block of their own: they ship on a parent's or an
# embedded-module maker's OUI (documented in scripts/generate_vendor_ouis.py).
# For these, the registrant name legitimately differs from the brand.
_OWNER_EXEMPT = {
    "notifier", "pelco", "york", "distech", "mir", "vaisala", "daifuku",
    "ifm", "lennox", "swisslog", "aveva", "kepware", "lansweeper",
    "paessler", "copadata", "wonderware",
}


def _registry() -> dict[str, str]:
    with CSV_PATH.open(newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return {p.upper(): c for p, c in reader if len(p) == 6}


def _company(reg: dict[str, str], oui: str) -> str:
    return reg.get(oui.replace(":", "").upper(), "<UNASSIGNED>")


def test_registry_present_and_sane() -> None:
    reg = _registry()
    assert len(reg) > 30000, "IEEE OUI registry looks truncated"
    # The exact prefix that caused the original Yokogawa->Siemon leak.
    assert reg.get("001E62") == "Siemon"
    assert reg.get("000064", "").startswith("Yokogawa")


def test_generated_module_is_fresh() -> None:
    """The committed generated module must match a fresh generation run."""
    import scripts.generate_vendor_ouis as gen

    expected = gen.build_vendor_ouis()
    assert VENDOR_OUIS == expected, (
        "VENDOR_OUIS is stale — run scripts/generate_vendor_ouis.py"
    )


def test_every_generated_oui_resolves_to_its_vendor() -> None:
    reg = _registry()
    import scripts.generate_vendor_ouis as gen

    # vendor key -> the regex patterns its OUIs must satisfy in the registry.
    failures: list[str] = []
    for vendor, patterns in gen.PATTERNS.items():
        rx = [re.compile(p, re.I) for p in patterns]
        for oui in VENDOR_OUIS[vendor]:
            company = _company(reg, oui)
            if not any(r.search(company) for r in rx):
                failures.append(f"{vendor}: {oui} -> IEEE '{company}'")
    assert not failures, "OUIs not matching their vendor:\n" + "\n".join(failures)


@pytest.mark.parametrize("oui", VENDOR_OUIS["yokogawa"])
def test_yokogawa_ouis_are_really_yokogawa(oui: str) -> None:
    """Regression for the reported CV bug: no Siemon/PRONET/etc. leakage."""
    assert _company(_registry(), oui).startswith("Yokogawa")


def test_no_template_oui_is_a_known_foreign_brand() -> None:
    """Each template's oui_prefixes must be inside its vendor's grounded set."""
    bad: list[str] = []
    for fp in get_all_fingerprints():
        vendor = normalize_vendor(fp.get("vendor") or "")
        allowed = {o.upper() for o in VENDOR_OUIS.get(vendor, [])}
        if not allowed:
            continue
        for oui in fp.get("oui_prefixes") or []:
            if oui.upper() not in allowed:
                bad.append(f"{fp.get('id', '?')} ({vendor}): {oui}")
    assert not bad, "Templates carrying off-vendor OUIs:\n" + "\n".join(bad)
