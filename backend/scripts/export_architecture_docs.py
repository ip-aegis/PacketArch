#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Export per-vertical reference architecture docs as Markdown.

Output: `docs/architecture/<vertical>.md` for each supported vertical,
plus a top-level `docs/architecture/README.md` index. Pulls all data
from the architecture rail's role catalog, archetypes, and comm matrix
— the docs are derived from code, not duplicated by hand.

Usage:
    docker compose exec backend python3 /app/scripts/export_architecture_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.architecture import (  # noqa: E402
    Vertical,
    list_archetypes_for_vertical,
    list_entries_for_vertical,
    list_roles_for_vertical,
)


REPO_ROOT = BACKEND_DIR.parent
DOCS_DIR = REPO_ROOT / "docs" / "architecture"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def _md_pretty_vertical(v: str) -> str:
    return v.replace("_", " ").title()


def _emit_role_table(roles: list, fp) -> None:
    fp.write("| Role | Purdue | Category | Required protocols | When to include |\n")
    fp.write("|---|---|---|---|---|\n")
    for r in roles:
        proto = ", ".join(r.required_protocols) or "-"
        when = r.when_to_include.replace("\n", " ")
        fp.write(
            f"| `{r.id}` | L{r.purdue_level} | {r.category.value} | "
            f"{proto} | {when} |\n"
        )


def _emit_archetype_section(arch, fp) -> None:
    fp.write(f"### Archetype: `{arch.id}` — {arch.name}\n\n")
    fp.write(f"{arch.description}\n\n")
    fp.write(
        f"- **Pattern**: `{arch.pattern.value}`\n"
        f"- **Default vendor profile**: `{arch.default_vendor_profile.value}`\n"
        f"- **Supported vendor profiles**: "
        + ", ".join(f"`{v.value}`" for v in arch.supported_vendor_profiles)
        + "\n"
        f"- **Min scale**: `{arch.min_scale.value}`\n"
        f"- **Default cell isolation**: `{arch.cell_isolation_default}`\n\n"
    )

    fp.write("#### Zone skeleton\n\n")
    fp.write("| Zone | Purdue | Security | Roles |\n|---|---|---|---|\n")
    for z in arch.zones:
        roles = ", ".join(f"`{s.role_id}`" for s in z.role_slots)
        fp.write(
            f"| `{z.id}` ({z.name}) | L{z.purdue_level} | "
            f"{z.security_level} | {roles} |\n"
        )
    fp.write("\n")

    fp.write("#### Conduits (allowed cross-zone protocols)\n\n")
    fp.write("| Conduit | Direction | Allowed protocols |\n|---|---|---|\n")
    for c in arch.conduits:
        protos = ", ".join(f"`{p}`" for p in c.allowed_protocols) or "-"
        fp.write(
            f"| `{c.source_zone}` ↔ `{c.target_zone}` | {c.direction} | {protos} |\n"
        )
    fp.write("\n")

    if arch.notes:
        fp.write("#### Notes\n\n")
        for n in arch.notes:
            fp.write(f"- {n}\n")
        fp.write("\n")


def _emit_matrix_table(entries: list, fp) -> None:
    fp.write(
        "| Source role | Target role | Pattern | Interval (ms) | "
        "Protocols | Vertical |\n"
    )
    fp.write("|---|---|---|---|---|---|\n")
    for e in entries:
        ivl = (
            f"{e.interval_ms[0]}"
            if e.interval_ms[0] == e.interval_ms[1]
            else f"{e.interval_ms[0]}-{e.interval_ms[1]}"
        )
        protos = ", ".join(f"`{p}`" for p in e.protocol_options) or "-"
        vertical = "SHARED" if e.vertical == "*" else e.vertical
        fp.write(
            f"| `{e.src_role}` | `{e.tgt_role}` | {e.pattern} | "
            f"{ivl} | {protos} | {vertical} |\n"
        )


def export_vertical_doc(vertical: str) -> Path:
    out_path = DOCS_DIR / f"{vertical}.md"
    arches = list_archetypes_for_vertical(vertical)
    roles = list_roles_for_vertical(vertical)
    entries = list_entries_for_vertical(vertical)

    with out_path.open("w") as fp:
        fp.write(f"# Reference Architecture: {_md_pretty_vertical(vertical)}\n\n")
        fp.write(
            "*Auto-generated from the PacketArch architecture rail. "
            "Edit the source under `backend/app/services/architecture/` "
            "and re-run `scripts/export_architecture_docs.py` to "
            "regenerate.*\n\n"
        )

        fp.write(f"## Archetypes ({len(arches)})\n\n")
        if not arches:
            fp.write("_No archetypes defined for this vertical yet._\n\n")
        for a in arches:
            _emit_archetype_section(a, fp)

        fp.write(f"## Role catalog ({len(roles)} roles applicable)\n\n")
        _emit_role_table(roles, fp)
        fp.write("\n")

        fp.write(f"## Communication matrix ({len(entries)} entries)\n\n")
        fp.write(
            "Each row is a typed `(src_role, tgt_role) → protocol/pattern` "
            "rule that the scenario generator uses to materialize flows. "
            "Cross-vertical SHARED entries appear at the bottom.\n\n"
        )
        _emit_matrix_table(entries, fp)

    return out_path


def export_index(vertical_paths: list[Path]) -> Path:
    out_path = DOCS_DIR / "README.md"
    with out_path.open("w") as fp:
        fp.write("# PacketArch Reference Architecture\n\n")
        fp.write(
            "PacketArch encodes a typed reference architecture for each "
            "industrial vertical it supports. This directory holds the "
            "auto-generated per-vertical reference docs — what roles "
            "exist, what archetypes are available, and which "
            "(src_role, tgt_role) pairs are valid in each vertical.\n\n"
            "These docs are the same data the scenario generator uses to "
            "materialize templates and AI-generated scenarios. If you "
            "see a flow that doesn't appear here, the generator won't "
            "produce it — and you can use `/api/v1/architecture/check-flow` "
            "to validate any flow against the matrix.\n\n"
        )
        fp.write("## Verticals\n\n")
        for vp in sorted(vertical_paths):
            v = vp.stem
            fp.write(f"- [{_md_pretty_vertical(v)}]({vp.name})\n")
        fp.write("\n")
        fp.write("## Source files\n\n")
        fp.write(
            "- `backend/app/services/architecture/role_catalog.py` — "
            "role taxonomy (44 roles)\n"
            "- `backend/app/services/architecture/archetypes/` — "
            "per-vertical archetype definitions\n"
            "- `backend/app/services/architecture/comm_matrix/` — "
            "communication matrix entries\n"
            "- `backend/app/services/architecture/scenario_generator.py` — "
            "the materialization engine\n"
        )
    return out_path


def main() -> int:
    print(f"Writing docs to: {DOCS_DIR}")
    paths = []
    for v in Vertical:
        p = export_vertical_doc(v.value)
        print(f"  {p.name} ({p.stat().st_size:,} bytes)")
        paths.append(p)
    idx = export_index(paths)
    print(f"  {idx.name} (index)")
    print(f"\nDone. {len(paths) + 1} files written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
