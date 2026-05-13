#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Audit the device-template catalog for protocol declaration issues.

Surfaces:
  - Templates that declare a protocol the vendor doesn't natively serve
    (e.g. Siemens S7 with `ethernet_ip`).
  - Templates that declare a protocol with no identity block to back it.

Default is read-only. `--fix-source` mutates source files to drop the
flagged protocols from each affected template's `supported_protocols=[...]`
declaration. Use with version control.

Usage:
    python -m backend.scripts.audit_template_protocols [--json] [--vendor NAME]
    python -m backend.scripts.audit_template_protocols --fix-source

Examples:
    python -m backend.scripts.audit_template_protocols
    python -m backend.scripts.audit_template_protocols --vendor siemens
    python -m backend.scripts.audit_template_protocols --json > audit.json
    python -m backend.scripts.audit_template_protocols --fix-source --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Allow running from repo root or from backend/
HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.template_audit import (
    audit_templates,
    finding_to_dict,
    summarize,
)


VENDORS_DIR = BACKEND_DIR / "app" / "services" / "device_templates" / "vendors"


def _patch_template_in_source(
    text: str, template_id: str, drop: set[str]
) -> tuple[str, list[str], list[str]]:
    """Remove protocols from EVERY occurrence of a template_id's
    supported_protocols list. The catalog has a handful of duplicate
    template-id registrations; the registry uses the last one to win,
    so we must patch them all.

    Returns (new_text, last_kept, last_removed). If the template_id
    isn't present or nothing changes, returns (text, [], []).
    """
    id_marker = f'id="{template_id}"'
    sp_re = re.compile(r"supported_protocols=\[([^\]]*)\]")

    last_kept: list[str] = []
    last_removed: list[str] = []

    cursor = 0
    while True:
        pos = text.find(id_marker, cursor)
        if pos < 0:
            break

        # Find the end of this template — next `id="` after the marker
        # or end of file.
        next_pos = text.find('id="', pos + len(id_marker))
        end = next_pos if next_pos > 0 else len(text)

        sp_match = sp_re.search(text, pos, end)
        if not sp_match:
            cursor = pos + len(id_marker)
            continue

        items_raw = sp_match.group(1)
        protocols = [
            p.strip().strip("\"'")
            for p in items_raw.split(",")
            if p.strip() and p.strip().strip("\"'")
        ]
        new_protocols = [p for p in protocols if p not in drop]

        if set(protocols) != set(new_protocols):
            removed = [p for p in protocols if p in drop]
            new_list_str = ", ".join(f'"{p}"' for p in new_protocols)
            replacement = f"supported_protocols=[{new_list_str}]"
            text = (
                text[: sp_match.start()]
                + replacement
                + text[sp_match.end():]
            )
            last_kept = new_protocols
            last_removed = removed
            # Advance cursor past the replacement to avoid infinite loop.
            cursor = sp_match.start() + len(replacement)
        else:
            cursor = sp_match.end()

    return text, last_kept, last_removed


def apply_source_fixes(findings, dry_run: bool = False) -> dict:
    """Apply source-file fixes for off-vendor + missing-identity findings.

    Returns a summary dict with per-file edit counts and a per-template
    audit trail.
    """
    fixes_by_id: dict[str, set[str]] = {}
    for f in findings:
        drop = set(f.off_vendor) | set(f.missing_identity)
        if drop:
            fixes_by_id[f.template_id] = drop

    if not fixes_by_id:
        return {"files_changed": 0, "templates_fixed": 0, "audit": []}

    audit_trail: list[dict] = []
    files_changed = 0
    templates_fixed = 0

    for vfile in sorted(VENDORS_DIR.glob("*.py")):
        original = vfile.read_text()
        text = original
        file_fixes: list[dict] = []
        for tid, drop in fixes_by_id.items():
            new_text, kept, removed = _patch_template_in_source(text, tid, drop)
            if removed:
                text = new_text
                templates_fixed += 1
                file_fixes.append({
                    "template_id": tid,
                    "removed": removed,
                    "kept": kept,
                })
        if text != original:
            files_changed += 1
            if not dry_run:
                vfile.write_text(text)
            audit_trail.append({"file": str(vfile.relative_to(BACKEND_DIR)),
                                "fixes": file_fixes})

    return {
        "files_changed": files_changed,
        "templates_fixed": templates_fixed,
        "dry_run": dry_run,
        "audit": audit_trail,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit device-template supported_protocols declarations."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a human report.",
    )
    parser.add_argument(
        "--vendor",
        help="Filter findings to a single vendor (case-insensitive substring match).",
    )
    parser.add_argument(
        "--fix-source",
        action="store_true",
        help="Mutate vendor template source files to drop flagged protocols.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --fix-source, print what would change without writing.",
    )
    args = parser.parse_args()

    # Trigger registry load
    from app.services.device_templates._registry import DEVICE_TEMPLATES  # noqa: F401
    from app.services.device_templates import vendors  # noqa: F401  side-effect: registers all templates

    findings = audit_templates()

    if args.vendor:
        needle = args.vendor.lower()
        findings = [f for f in findings if needle in f.vendor.lower()]

    if args.fix_source:
        result = apply_source_fixes(findings, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            mode = "DRY RUN — " if args.dry_run else ""
            print()
            print(f"{mode}Source fix complete")
            print("=" * 72)
            print(f"  Files changed:    {result['files_changed']}")
            print(f"  Templates fixed:  {result['templates_fixed']}")
            print()
            for entry in result["audit"]:
                print(f"  {entry['file']}:")
                for fix in entry["fixes"]:
                    print(f"    - {fix['template_id']}: removed {fix['removed']}")
            print()
            if not args.dry_run and result["files_changed"]:
                print("Restart backend to pick up the source changes.")
        return 0

    summary = summarize(findings)

    if args.json:
        print(
            json.dumps(
                {
                    "summary": summary,
                    "findings": [finding_to_dict(f) for f in findings],
                },
                indent=2,
            )
        )
        return 0

    # Human-readable report
    print()
    print("Template-protocol audit")
    print("=" * 72)
    print()
    print(f"Total findings: {summary['total_findings']}")
    print(f"  Off-vendor only: {summary['off_vendor_only']}")
    print(f"  Missing-identity only: {summary['missing_identity_only']}")
    print(f"  Both issues: {summary['both_issues']}")
    print(f"  Unknown vendor (skipped): {summary['unknown_vendor']}")
    print()

    if not findings:
        print("No catalog issues found.")
        return 0

    off_vendor_findings = [f for f in findings if f.off_vendor]
    if off_vendor_findings:
        print("-" * 72)
        print("OFF-VENDOR DECLARATIONS")
        print("(declared protocols not in vendor-native set — likely incorrect)")
        print("-" * 72)
        for f in off_vendor_findings:
            print()
            print(f"  {f.template_id}")
            print(f"    vendor: {f.vendor}")
            print(f"    model:  {f.model} ({f.model_name})")
            print(f"    type:   {f.device_type}")
            print(f"    declared:       {', '.join(f.declared)}")
            print(f"    vendor natives: {', '.join(f.vendor_natives)}")
            print(f"    off-vendor:     {', '.join(f.off_vendor)}  ← review")
        print()

    missing_identity_findings = [f for f in findings if f.missing_identity]
    if missing_identity_findings:
        print("-" * 72)
        print("MISSING-IDENTITY DECLARATIONS")
        print("(declared but no identity block populated — engine can't generate)")
        print("-" * 72)
        for f in missing_identity_findings:
            print()
            print(f"  {f.template_id}")
            print(f"    vendor: {f.vendor}")
            print(f"    model:  {f.model} ({f.model_name})")
            print(f"    declared:        {', '.join(f.declared)}")
            print(f"    populated blocks: {', '.join(f.populated_identity_blocks) or '(none)'}")
            print(f"    missing identity: {', '.join(f.missing_identity)}  ← either populate or remove")
        print()

    print("=" * 72)
    print(f"END — {summary['total_findings']} finding(s)")
    return 0 if summary["total_findings"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
