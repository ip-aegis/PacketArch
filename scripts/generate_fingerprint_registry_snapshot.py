#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Regenerate schemas/fingerprint-registry.v1.json from the live catalog.

The portable scenario standard ships with both a JSON Schema (the format
contract) and a fingerprint registry snapshot (the catalog of valid
`fingerprint_model` values). Airgapped portable-scenario authors use
both files offline.

This script reads the in-process device template catalog and writes
a fresh registry snapshot. Run it whenever templates are added or
modified.

Usage:
    cd backend && poetry run python ../scripts/generate_fingerprint_registry_snapshot.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make backend importable when run from repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

# Avoid pydantic-settings choking on a missing SECRET_KEY when this
# script is invoked outside the running backend container.
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("DEBUG", "true")

from app.services.device_templates import get_all_templates  # noqa: E402

OUTPUT = REPO_ROOT / "schemas" / "fingerprint-registry.v1.json"
# Mirror into the backend's downloads dir so the running container can
# serve the snapshot from /api/v1/downloads — keeps both copies in
# lockstep so the UI's "Download" button and the release bundle never
# disagree.
BACKEND_MIRROR = (
    REPO_ROOT / "backend" / "app" / "static" / "downloads"
    / "fingerprint-registry.v1.json"
)


def main() -> int:
    templates = get_all_templates()
    entries = [
        {
            "vendor": t.vendor.lower(),
            "model": t.model,
            "model_name": t.model_name,
            "device_type": t.device_type,
            "protocols": list(t.supported_protocols),
            "description": t.description or None,
        }
        for t in templates
    ]
    entries.sort(key=lambda e: (e["vendor"], e["device_type"], e["model"]))

    registry = {
        "$schema": "https://packetarch.io/schemas/fingerprint-registry.v1.json",
        "format_version": "1.0",
        "description": (
            "Static snapshot of the PacketArch device template catalog "
            "for offline / airgapped portable scenario authoring. Use "
            "entries here to populate `fingerprint_model` in a "
            ".pascenario.json file. The live equivalent is "
            "GET /api/v1/fingerprints/registry."
        ),
        "entry_count": len(entries),
        "vendors": sorted({e["vendor"] for e in entries}),
        "device_types": sorted({e["device_type"] for e in entries}),
        "entries": entries,
    }

    payload = json.dumps(registry, indent=2) + "\n"
    OUTPUT.write_text(payload, encoding="utf-8")
    BACKEND_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    BACKEND_MIRROR.write_text(payload, encoding="utf-8")
    print(
        f"Wrote {OUTPUT.relative_to(REPO_ROOT)} "
        f"+ {BACKEND_MIRROR.relative_to(REPO_ROOT)}: "
        f"{len(entries)} entries / "
        f"{len(registry['vendors'])} vendors / "
        f"{len(registry['device_types'])} device types"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
