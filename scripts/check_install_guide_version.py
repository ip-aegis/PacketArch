#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Fail if the shipped Installation Guide PDF has fallen behind app_version.

The guide is served from Settings > Downloads. It is a generated artifact
(scripts/build_install_guide_pdf.py) that has to be regenerated and committed
when the version bumps — nothing in the release pipeline does it automatically.

It silently went stale once: the app shipped 1.19.x while Downloads still
handed users a v1.10.1 PDF written before the setup wizard existed, still
telling them to clone over SSH and to use a compose file that no longer
exists. This check makes that impossible to merge unnoticed.

To fix a failure:
    cd backend && poetry run python ../scripts/build_install_guide_pdf.py
    git mv/rm the old PDF, then:
    cp dist/PacketArch-Installation-Guide-v<version>.pdf \
       backend/app/static/downloads/
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "backend" / "app" / "core" / "config.py"
DOWNLOADS = REPO / "backend" / "app" / "static" / "downloads"
PATTERN = "PacketArch-Installation-Guide-v*.pdf"


def app_version() -> str:
    m = re.search(r'app_version:\s*str\s*=\s*"([^"]+)"', CONFIG.read_text())
    if not m:
        sys.exit(f"could not read app_version from {CONFIG}")
    return m.group(1)


def main() -> int:
    want = app_version()
    guides = sorted(DOWNLOADS.glob(PATTERN))

    if not guides:
        print(f"FAIL: no install guide in {DOWNLOADS.relative_to(REPO)}/")
        print(f"      expected something matching {PATTERN}")
        return 1

    if len(guides) > 1:
        print("FAIL: more than one install guide is committed — keep exactly one:")
        for g in guides:
            print(f"      {g.name}")
        return 1

    got = re.search(r"-v(.+)\.pdf$", guides[0].name)
    got_version = got.group(1) if got else "?"

    if got_version != want:
        print(f"FAIL: install guide is v{got_version}, but app_version is {want}.")
        print(f"      {guides[0].name} is stale and is what Settings > Downloads")
        print("      hands to operators. Regenerate it:")
        print("        cd backend && poetry run python ../scripts/build_install_guide_pdf.py")
        return 1

    print(f"OK: install guide v{got_version} matches app_version {want}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
