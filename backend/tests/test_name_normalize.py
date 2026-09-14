# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Acronym-casing normalizer + CV group-label naming guards."""
from __future__ import annotations

import pytest

from app.core.name_normalize import normalize_acronyms


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Ot Dmz", "OT DMZ"),
        ("Industrial Dmz", "Industrial DMZ"),
        ("Plant Scada Network", "Plant SCADA Network"),
        ("Hmi Station", "HMI Station"),
        ("Cell 1 - Cnc Machining", "Cell 1 - CNC Machining"),
        ("Tertiary/Uv", "Tertiary/UV"),
        # left untouched: normal words, model strings, already-correct, all-lower
        ("Bioreactor Train A", "Bioreactor Train A"),
        ("BMEP586040", "BMEP586040"),
        ("Industrial DMZ", "Industrial DMZ"),
        ("it just works", "it just works"),
        ("", ""),
    ],
)
def test_normalize_acronyms(raw: str, expected: str) -> None:
    assert normalize_acronyms(raw) == expected


def test_none_is_safe() -> None:
    assert normalize_acronyms(None) == ""


def test_group_label_bare_vs_deconflicted() -> None:
    from app.services.cv_provisioning_service import _group_label

    class S:
        name = "Strict Purdue Segmented Manufacturing"
        vertical = "manufacturing"

    dups = {"Industrial DMZ"}
    # unique zone -> bare name
    assert _group_label(S(), "Bioreactor Train A", dups) == "Bioreactor Train A"
    # duplicate zone -> scenario-suffixed
    assert _group_label(S(), "Industrial DMZ", dups) == (
        "Industrial DMZ (Strict Purdue Segmented Manufacturing)"
    )
    # casing-variant of a duplicate normalizes THEN deconflicts
    assert _group_label(S(), "Industrial Dmz", dups).startswith("Industrial DMZ (")
    # 60-char hard cap respected
    assert all(len(_group_label(S(), z, dups)) <= 60 for z in ("Industrial DMZ", "X" * 80))


def test_oh_level_name_folds_non_ascii() -> None:
    """CV's OH endpoint 400s a non-ASCII level name ("Name is invalid"), which
    fails the whole batch — so the em dash the scenario namer likes must be
    folded to ASCII, not passed through."""
    from app.services.cv_provisioning_service import _oh_level_name

    # the live failure: em dash reached POST /cvapi/v1/oh and killed the phase
    assert _oh_level_name("Pharma — Vaccine Bioreactor Plant ") == "Pharma - Vaccine"
    assert _oh_level_name("Semiconductor Fab — 300mm Wafer Line") == "Semiconductor Fab"
    # a separator is preserved as ASCII rather than dropped, so words stay apart
    assert _oh_level_name("Cell 1 – Mixing") == "Cell 1 - Mixing"
    assert _oh_level_name("Bioreactor 40°C") == "Bioreactor 40 degC"
    # NB: the straight double quote is itself CV-rejected ("Name is invalid",
    # verified live on 5.6), so the smart quotes fold on to an apostrophe
    # rather than to '"'. See docs/cyber-vision/API_AUDIT_5.6.md §3.
    assert _oh_level_name("Line “A”") == "Line 'A'"
    # pure ASCII is untouched, and the 20-char cap still holds at a word boundary
    assert _oh_level_name("Cookie Bakery") == "Cookie Bakery"
    assert _oh_level_name("Process Control And Safety") == "Process Control"
    assert all(len(_oh_level_name(n)) <= 20 for n in ("X" * 80, "Pharma — " + "Y" * 40))


def test_oh_level_name_edge_cases() -> None:
    from app.services.cv_provisioning_service import _oh_level_name

    # These used to assert "" — but CV rejects an EMPTY name just as it rejects
    # a bad character (verified live on 5.6), so returning "" only moved the
    # 400 downstream and failed the whole POST /cvapi/v1/oh batch. A name that
    # folds away to nothing now falls back instead.
    assert _oh_level_name("") == "Unnamed"
    assert _oh_level_name(None) == "Unnamed"
    assert _oh_level_name("日本語") == "Unnamed"
    # ...and callers pass something identity-bearing so two such zones differ
    assert _oh_level_name("日本語", fallback="Zone abc12345") == "Zone abc12345"
    assert _oh_level_name("  spaced   out  name ") == "spaced out name"
