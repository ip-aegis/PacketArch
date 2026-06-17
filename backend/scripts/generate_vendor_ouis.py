#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Generate IEEE-grounded vendor OUI data.

Every OUI PacketArch attaches to a device MUST resolve, in the real IEEE OUI
registry, to that device's vendor (or a defensible parent / embedded-module /
virtualization owner). Hand-curated lists drifted badly (47% of shipped OUIs
were misassigned — e.g. a Yokogawa analyzer carrying Siemon's ``00:1E:62``),
so the OUI lists are now *derived* from the bundled IEEE registry instead.

Source of truth: ``app/protocol_engines/data/ieee_oui.csv`` (slim copy of
https://standards-oui.ieee.org/oui/oui.csv — refresh with ``scripts/refresh_oui.py``).

Outputs:
- ``app/protocol_engines/_vendor_ouis_generated.py`` — a static ``VENDOR_OUIS``
  literal (committed so the agent's Docker-staged copy needs no CSV at runtime).
- Rewrites ``oui_prefixes=[...]`` in ``app/services/device_templates/vendors/*.py``
  to each template's vendor's IEEE OUIs.

Usage:
    poetry run python scripts/generate_vendor_ouis.py            # write module + fix templates
    poetry run python scripts/generate_vendor_ouis.py --check    # CI guard: fail if stale
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "app" / "protocol_engines" / "data" / "ieee_oui.csv"
GEN_PATH = ROOT / "app" / "protocol_engines" / "_vendor_ouis_generated.py"
VENDORS_DIR = ROOT / "app" / "services" / "device_templates" / "vendors"

MAX_PER_VENDOR = 6          # cap VENDOR_OUIS entries per vendor
MAX_PER_TEMPLATE = 4        # cap template oui_prefixes

# --- curated vendor key -> IEEE registrant-name regex patterns (case-insensitive).
# Word boundaries kill substring noise ("Abbott" for abb, "Salutron" for lutron,
# "Orange Digital" for "ge digital"). Verified against the registry.
PATTERNS: dict[str, list[str]] = {
    "siemens": [r"\bsiemens ag\b", r"siemens industrial", r"siemens numerical"],
    "siemens its": [r"\bsiemens ag\b", r"siemens industrial"],
    "rockwell": [r"rockwell automation", r"allen-bradley"],
    "schneider": [r"schneider electric", r"telemecanique", r"\bmodicon\b", r"square d company"],
    "abb": [r"\babb\b"],
    "ge": [r"general electric", r"\bge fanuc\b", r"ge multilin", r"ge intelligent",
           r"ge grid", r"ge digital energy"],
    "honeywell": [r"honeywell"],
    "yokogawa": [r"yokogawa"],
    "emerson": [r"\bemerson\b", r"rosemount", r"fisher-rosemount"],
    "mitsubishi": [r"mitsubishi electric corporation"],
    "omron": [r"omron corporation", r"omron tateisi"],
    "endress_hauser": [r"endress"],
    "sick": [r"\bsick ag\b", r"sick stegmann"],
    "phoenix contact": [r"phoenix contact"],
    "wago": [r"\bwago\b"],
    "beckhoff": [r"beckhoff"],
    "b&r": [r"b&r industrial", r"bernecker"],
    "hms": [r"hms industrial"],
    "moxa": [r"\bmoxa\b"],
    "advantech": [r"advantech"],
    "cisco": [r"cisco systems"],
    "sel": [r"schweitzer engineering"],
    "beckwith electric": [r"beckwith electric"],
    "kuka": [r"\bkuka\b"],
    "fanuc": [r"\bfanuc\b"],
    "cognex": [r"cognex"],
    "carel": [r"\bcarel\b"],
    "delta_controls": [r"delta controls"],
    "automated_logic": [r"automatedlogic"],
    "carrier": [r"carrier corporation", r"carrier fire"],
    "trane": [r"\btrane\b"],
    "johnson_controls": [r"johnson controls"],
    "lutron": [r"lutron electronics"],
    "daktronics": [r"daktronics"],
    "econolite": [r"econolite"],
    "mccain": [r"mccain inc"],
    "wavetronix": [r"wavetronix"],
    "kapsch": [r"kapsch"],
    "q-free": [r"q-free"],
    "axis": [r"axis communications"],
    "flir": [r"\bflir\b"],
    "hikvision": [r"hikvision"],
    "bosch": [r"bosch"],
    "impinj": [r"impinj"],
    "zebra": [r"zebra technologies"],
    "dematic": [r"dematic"],
    "f5 networks": [r"\bf5 inc"],
    "broadcom": [r"\bbroadcom\b"],
    "microsoft": [r"microsoft corporation"],
    # Additional real OT vendors referenced by DEVICE_TYPE_VENDORS / generators.
    "alerton": [r"alerton technologies"],
    "basler": [r"basler electric"],
    "belden": [r"\bbelden\b"],
    "harting": [r"harting"],
    "hirschmann": [r"hirschmann automation"],
    "kmc_controls": [r"kmc controls"],
    "pilz": [r"pilz gmbh"],
    "reliable_controls": [r"reliable controls"],
    "tridium": [r"tridium"],
    "turck": [r"\bturck\b"],
}

# Alias spellings -> canonical key. Emitted as duplicate entries so direct
# ``VENDOR_OUIS.get(alias)`` lookups (DEVICE_TYPE_VENDORS, division names, etc.)
# keep resolving without depending on normalize_vendor at every call site.
ALIASES: dict[str, str] = {
    "b_and_r": "b&r",
    "phoenix_contact": "phoenix contact",
    "qfree": "q-free",
    "q_free": "q-free",
    "siemens_its": "siemens its",
    "beckwith": "beckwith electric",
    "f5-networks": "f5 networks",
    "f5_networks": "f5 networks",
    "distech_controls": "distech",
    "ge_multilin": "ge",
    "endress+hauser": "endress_hauser",
    "siemens_building": "siemens",
    "siemens_protection": "siemens",
    "schneider_bms": "schneider",
    "allen_bradley": "rockwell",
}

# Vendors with no IEEE block of their own -> defensible owner.
#   parent: brand of a larger registrant (Notifier=Honeywell, Pelco=Schneider).
#   "_lantronix": small OT vendors that ship embedded serial-to-Ethernet modules;
#                 on the wire they appear as the module maker (Lantronix), which is
#                 how they really show up in Cyber Vision.
ORPHANS: dict[str, str] = {
    "notifier": "honeywell",
    "pelco": "schneider",
    "york": "johnson_controls",
    "distech": "_lantronix",
    "mir": "_lantronix",
    "vaisala": "_lantronix",
    "daifuku": "_lantronix",
    "ifm": "_lantronix",
    "lennox": "_lantronix",
    "swisslog": "_lantronix",
}

# Software products (no NIC of their own) run on hypervisors -> VM OUIs are the
# realistic on-wire identity (VMware + Microsoft Hyper-V).
SOFTWARE_VENDORS = {"aveva", "kepware", "lansweeper", "paessler", "copadata", "wonderware"}
VIRTUALIZATION_OUIS = ["00:50:56", "00:0C:29", "00:15:5D"]  # VMware x2, Hyper-V


def _load_ieee() -> list[tuple[str, str]]:
    with CSV_PATH.open() as f:
        reader = csv.reader(f)
        next(reader, None)
        return [(p, c) for p, c in reader if len(p) == 6]


def _fmt(prefix6: str) -> str:
    p = prefix6.upper()
    return f"{p[0:2]}:{p[2:4]}:{p[4:6]}"


def _match(ieee: list[tuple[str, str]], patterns: list[str], cap: int) -> list[str]:
    rx = [re.compile(p, re.I) for p in patterns]
    out: list[str] = []
    seen: set[str] = set()
    for prefix, company in ieee:
        if any(r.search(company) for r in rx):
            f = _fmt(prefix)
            if f not in seen:
                seen.add(f)
                out.append(f)
    return sorted(out)[:cap]


def build_vendor_ouis() -> dict[str, list[str]]:
    ieee = _load_ieee()
    lantronix = sorted({_fmt(p) for p, c in ieee if "lantronix" in c.lower()})[:4]
    result: dict[str, list[str]] = {}
    keys = set(PATTERNS) | set(ORPHANS) | SOFTWARE_VENDORS
    for v in sorted(keys):
        if v in SOFTWARE_VENDORS:
            result[v] = list(VIRTUALIZATION_OUIS)
        elif v in ORPHANS:
            tgt = ORPHANS[v]
            result[v] = list(lantronix) if tgt == "_lantronix" else _match(ieee, PATTERNS[tgt], MAX_PER_VENDOR)
        else:
            result[v] = _match(ieee, PATTERNS[v], MAX_PER_VENDOR)
        if not result[v]:
            raise SystemExit(f"ERROR: no IEEE OUIs resolved for vendor '{v}'")
    # Emit alias spellings pointing at the canonical vendor's grounded list.
    for alias, canonical in ALIASES.items():
        if canonical not in result:
            raise SystemExit(f"ERROR: alias '{alias}' -> unknown canonical '{canonical}'")
        result[alias] = list(result[canonical])
    return result


def render_module(vendor_ouis: dict[str, list[str]]) -> str:
    lines = [
        "# PacketArch — OT Traffic Simulation Platform",
        "# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>",
        "# Licensed under GPL-3.0. See LICENSE at the repo root.",
        '"""AUTO-GENERATED — do not edit by hand.',
        "",
        "Generated by ``scripts/generate_vendor_ouis.py`` from the bundled IEEE OUI",
        "registry (``data/ieee_oui.csv``). Every prefix resolves to its vendor (or a",
        "documented parent / embedded-module / virtualization owner) in the real IEEE",
        "registry. Regenerate after refreshing the CSV; a CI guard enforces freshness.",
        '"""',
        "",
        "VENDOR_OUIS: dict[str, list[str]] = {",
    ]
    for v in sorted(vendor_ouis):
        ouis = ", ".join(f'"{o}"' for o in vendor_ouis[v])
        lines.append(f'    "{v}": [{ouis}],')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def fix_templates(vendor_ouis: dict[str, list[str]]) -> int:
    """Rewrite oui_prefixes=[...] in each vendor template file to the vendor's IEEE OUIs."""
    sys.path.insert(0, str(ROOT))
    from app.core.vendor_normalize import normalize_vendor  # noqa: E402

    changed = 0
    # match a DeviceTemplate's vendor=... and the nearest oui_prefixes=[...] pair.
    block_re = re.compile(
        r"(vendor\s*=\s*[\"']([^\"']+)[\"'][\s\S]{0,4000}?oui_prefixes\s*=\s*)\[[^\]]*\]"
    )

    def repl(m: re.Match) -> str:
        vendor_raw = m.group(2)
        key = normalize_vendor(vendor_raw)
        ouis = vendor_ouis.get(key)
        if not ouis:
            return m.group(0)  # leave unknown vendors untouched
        joined = ", ".join(f'"{o}"' for o in ouis[:MAX_PER_TEMPLATE])
        return f"{m.group(1)}[{joined}]"

    for path in sorted(VENDORS_DIR.glob("*.py")):
        text = path.read_text()
        new = block_re.sub(repl, text)
        if new != text:
            path.write_text(new)
            changed += 1
    return changed


def main() -> None:
    check = "--check" in sys.argv
    vendor_ouis = build_vendor_ouis()
    rendered = render_module(vendor_ouis)
    if check:
        current = GEN_PATH.read_text() if GEN_PATH.exists() else ""
        if current.strip() != rendered.strip():
            print("STALE: _vendor_ouis_generated.py is out of date — run generate_vendor_ouis.py")
            sys.exit(1)
        print(f"OK: {len(vendor_ouis)} vendors, IEEE-grounded, up to date.")
        return
    GEN_PATH.write_text(rendered)
    n = fix_templates(vendor_ouis)
    print(f"Wrote {GEN_PATH.relative_to(ROOT)} ({len(vendor_ouis)} vendors).")
    print(f"Rewrote oui_prefixes in {n} template files.")


if __name__ == "__main__":
    main()
