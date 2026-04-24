#!/usr/bin/env python3
"""Add / verify GPL-3.0 copyright headers on source files.

Two modes:
  --check   (default)   exit non-zero if any matching file is missing the
                        header; print the list. Suitable as a pre-commit
                        hook.
  --fix                 insert the header into every missing file, in
                        place. Preserves shebang lines (#!…) and, for
                        Python, any leading __future__ annotations or
                        encoding declarations.

File types:
  Python:      .py     (comment prefix: "# ")
  TypeScript:  .ts, .tsx, .js, .jsx   (block comment /* … */)

Skip rules:
  - vendored / generated paths: node_modules, dist, build, __pycache__,
    .venv, alembic/versions (migrations are auto-generated), migrations,
    *.pyi, *.min.js
  - any file that already contains "Copyright (c) 2026 Rocky Smith" in
    its first 30 lines.

Usage:
  python scripts/add_copyright_headers.py --check
  python scripts/add_copyright_headers.py --fix
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

OWNER = "Rocky Smith <rocky.d.smith@proton.me>"
COPYRIGHT_LINE = f"Copyright (c) 2026 {OWNER}"
MARKER = "Copyright (c) 2026 Rocky Smith"  # used to detect existing headers

PY_HEADER = f"""# PacketArch — OT Traffic Simulation Platform
# {COPYRIGHT_LINE}
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""

JS_HEADER = f"""/*
 * PacketArch — OT Traffic Simulation Platform
 * {COPYRIGHT_LINE}
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
"""

SKIP_DIR_PARTS = {
    "node_modules", "dist", "build", "__pycache__", ".venv", "venv",
    ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "coverage",
    "versions",  # alembic migrations are auto-generated
}

SKIP_FILE_SUFFIXES = {".pyi", ".min.js", ".d.ts"}

PY_EXTS = {".py"}
JS_EXTS = {".ts", ".tsx", ".js", ".jsx"}


def should_skip(path: Path, repo_root: Path) -> bool:
    rel = path.relative_to(repo_root)
    if any(part in SKIP_DIR_PARTS for part in rel.parts):
        return True
    if path.suffix in SKIP_FILE_SUFFIXES:
        return True
    # Skip generated alembic versions specifically
    if "alembic" in rel.parts and "versions" in rel.parts:
        return True
    return False


def already_has_header(text: str) -> bool:
    # Only check the first 30 lines — headers are always near the top.
    return MARKER in "\n".join(text.splitlines()[:30])


def insert_python_header(text: str) -> str:
    """Insert after shebang/encoding/module-docstring if present."""
    lines = text.splitlines(keepends=True)
    insert_at = 0
    # Preserve shebang
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    # Preserve encoding declaration
    if (
        insert_at < len(lines)
        and lines[insert_at].strip().startswith("#")
        and "coding" in lines[insert_at]
    ):
        insert_at += 1
    return "".join(lines[:insert_at]) + PY_HEADER + "".join(lines[insert_at:])


def insert_js_header(text: str) -> str:
    """Insert at top. JS/TS files don't need shebang preservation for us."""
    return JS_HEADER + text


def iter_source_files(repo_root: Path):
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in PY_EXTS | JS_EXTS:
            continue
        if should_skip(path, repo_root):
            continue
        yield path


def process(repo_root: Path, fix: bool) -> int:
    missing: list[Path] = []
    fixed: list[Path] = []

    for path in iter_source_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if already_has_header(text):
            continue

        missing.append(path.relative_to(repo_root))

        if fix:
            if path.suffix in PY_EXTS:
                path.write_text(insert_python_header(text), encoding="utf-8")
            else:
                path.write_text(insert_js_header(text), encoding="utf-8")
            fixed.append(path.relative_to(repo_root))

    if fix:
        print(f"Inserted header into {len(fixed)} file(s):")
        for p in fixed:
            print(f"  + {p}")
        return 0

    if missing:
        print(f"Missing copyright header in {len(missing)} file(s):")
        for p in missing:
            print(f"  - {p}")
        print("\nRun `python scripts/add_copyright_headers.py --fix` to insert.")
        return 1

    print("All source files carry the GPL-3.0 copyright header.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix", action="store_true",
        help="Insert the header into files that are missing it.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Report missing headers and exit non-zero (default).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    return process(repo_root, fix=args.fix)


if __name__ == "__main__":
    sys.exit(main())
