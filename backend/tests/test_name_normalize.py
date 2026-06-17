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
