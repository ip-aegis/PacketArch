# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Guards for Cyber Vision Organization-Hierarchy level naming.

Every rule here was verified against a live CV 5.6 Center by PATCH-renaming a
level and restoring it — see ``docs/cyber-vision/API_AUDIT_5.6.md`` §3. CV
rejects a bad name with a 400 that fails the WHOLE ``POST /cvapi/v1/oh`` batch,
taking down a scenario's entire org-hierarchy phase, so these are correctness
guards rather than cosmetics.
"""
from __future__ import annotations

import string

import pytest

from app.services.cv_provisioning_service import (
    OH_LEVEL_NAME_LIMIT,
    _oh_ascii,
    _oh_level_name,
    _oh_level_names_for_siblings,
)

# Confirmed live on CV 5.6: rejected with {"message":"Name is invalid"}.
# Every one of these is plain ASCII, which is why an ascii-only fold missed them.
CV_REJECTED_ASCII = '!";<=>?[\\]^`{|}~'

# Confirmed live on CV 5.6: accepted.
CV_ALLOWED_PUNCT = "#$%&'()*+,-./:@_ "


def test_limit_matches_the_live_cap():
    """20 accepted / 21 rejected, verified live. Don't 'optimize' this upward."""
    assert OH_LEVEL_NAME_LIMIT == 20


@pytest.mark.parametrize("ch", list(CV_REJECTED_ASCII))
def test_rejected_characters_never_survive(ch):
    assert ch not in _oh_ascii(f"Zone{ch}End")
    assert ch not in _oh_level_name(f"Zone{ch}End")


@pytest.mark.parametrize("ch", list(CV_ALLOWED_PUNCT))
def test_allowed_punctuation_is_preserved(ch):
    """A whitelist that is too aggressive would mangle 'Heat & Hot-Water'."""
    assert ch in _oh_ascii(f"Zone{ch}End")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Zone [A] {primary}", "Zone (A) (primary)"),   # brackets/braces -> parens
        ("Line A | B \\ C", "Line A / B / C"),           # pipe/backslash -> slash
        ('HMI "Op" Console', "HMI 'Op' Console"),        # quotes -> apostrophe
        ("Heat & Hot-Water", "Heat & Hot-Water"),        # allowed punct untouched
        ("Pharma — Vaccine", "Pharma - Vaccine"),        # em dash folded, not dropped
        ("Ünïcödé Ström", "Unicode Strom"),              # accents folded
    ],
)
def test_substitutions_keep_names_readable(raw, expected):
    assert _oh_ascii(raw) == expected


@pytest.mark.parametrize(
    "raw", ["日本語ゾーン", "", "   ", "~~~", "<<>>", string.punctuation, "\x00\x01"]
)
def test_name_is_never_empty_and_never_too_long(raw):
    """CV rejects "" as surely as a bad character."""
    name = _oh_level_name(raw, fallback="Zone abc12345")
    assert name
    assert len(name) <= OH_LEVEL_NAME_LIMIT


def test_fully_non_ascii_name_uses_the_fallback():
    assert _oh_level_name("日本語ゾーン", fallback="Zone abc12345") == "Zone abc12345"


def test_word_boundary_cut_does_not_leave_a_dangling_separator():
    assert _oh_level_name("Process Control / Operations") == "Process Control"


def test_siblings_stay_distinct_when_the_dedup_suffix_is_truncated_away():
    """_group_label deconflicts with " (scenario)"; a 20-char word-boundary cut
    deletes that suffix wholesale. Both zones would then resolve to the SAME
    level id — one level missing, both networks assigned into the other."""
    out = _oh_level_names_for_siblings({
        "z1": "External/Internet (Data Center Infrastructure)",
        "z2": "External/Internet (Heat & Hot-Water Retrofit)",
    })
    assert len(set(out.values())) == 2


def test_siblings_stay_distinct_when_the_whitelist_collapses_them():
    """The charset fix can itself erase the only difference between two names
    ('Zone [A]' and 'Zone {A}' both fold to 'Zone (A)'), so the hard-cut step
    cannot separate them and the numeric-suffix step must."""
    out = _oh_level_names_for_siblings({"a": "Zone [A]", "b": "Zone {A}", "c": "Zone <A>"})
    assert len(set(out.values())) == 3


def test_sibling_names_respect_the_cap_and_are_deterministic():
    src = {
        "a": "Process Control [Ops] Primary",
        "b": "Process Control {Ops} Primary",
        "c": "日本語",
        "d": "한국어",
    }
    first = _oh_level_names_for_siblings(src)
    assert first == _oh_level_names_for_siblings(src)   # re-provisioning must not churn
    assert len(set(first.values())) == len(src)
    assert all(v and len(v) <= OH_LEVEL_NAME_LIMIT for v in first.values())
