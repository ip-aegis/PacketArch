# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for CV new-UI Organization Hierarchy level-name compaction.

CV caps OH level names at 20 ASCII characters and rejects anything longer or
non-ASCII outright (verified live against a CV 5.5.x Center). Every name
PacketArch pushes therefore has to survive ``_oh_level_name`` — these tests pin
the invariants (fits, ASCII, non-empty, stable) plus the specific reductions,
since a regression here silently breaks org-hierarchy provisioning for whichever
scenario happens to have a long name.
"""

import pytest

from app.services.cv_provisioning_service import (
    OH_LEVEL_NAME_LIMIT as LIMIT,
    _oh_level_name,
)

# Every scenario and zone name in the shipped templates that needs compaction,
# plus the awkward shapes that used to produce dangling output.
REAL_NAMES = [
    "Cold Chain Warehouse",
    "Electrical Substation IED Network",
    "Municipal Water Treatment Plant",
    "Parcel Sorting Hub - 7/13/2026",
    "Pharma — Vaccine Bioreactor Plant",
    "Pipeline SCADA Compressor Station Network",
    "Rockwell Automotive Assembly",
    "Semiconductor Fab — 300mm Wafer Line",
    "Solar Farm with Battery Energy Storage",
    "Urban Intersection Network",
    "Substation Local Area Network",
    "Point of Interconnection Protection",
    "Purification (TFF + Chromatography)",
    "Aseptic Fill / Finish",
    "Frozen Storage (-20C)",
    "Chilled Storage (2-8C)",
    "HVAC/Refrigeration Control",
    "Safety Instrumented System",
    "Remote Block Valve Stations",
    "AMHS - Material Handling",
    "Main Intersection Cabinet Network",
    "Minor Intersection Cabinet Network",
    "Environmental Monitoring",
    "Temperature Monitoring",
    "Cleanroom Environment",
    "External/Internet Gateway",
]


@pytest.mark.parametrize("raw", REAL_NAMES)
def test_fits_cv_limit(raw):
    assert len(_oh_level_name(raw)) <= LIMIT


@pytest.mark.parametrize("raw", REAL_NAMES)
def test_ascii_only(raw):
    """CV rejects any non-ASCII level name with 'Name is invalid'."""
    out = _oh_level_name(raw)
    assert out.isascii(), f"{out!r} carries non-ASCII from {raw!r}"


@pytest.mark.parametrize("raw", REAL_NAMES)
def test_non_empty(raw):
    assert _oh_level_name(raw).strip()


@pytest.mark.parametrize("raw", REAL_NAMES)
def test_no_dangling_token(raw):
    """Must not end on a connector or an opening/joining punctuation mark —
    `_match_existing_oh_level` compares these names literally, and 'Point of' /
    'Purification (TFF' are what the old word-boundary truncation produced."""
    out = _oh_level_name(raw)
    assert out[-1] not in " -_/,.:;+&([{", f"{out!r} ends on junk"
    assert out.split()[-1].lower() not in {
        "with", "of", "the", "and", "for", "a", "an", "to", "in", "on",
    }, f"{out!r} ends on a connector"
    assert out.count("(") == out.count(")"), f"{out!r} has unbalanced brackets"


@pytest.mark.parametrize("raw", REAL_NAMES)
def test_idempotent(raw):
    """Feeding a compacted name back in must be a no-op, because provisioning
    compares the freshly-derived name against the one already live in CV — an
    unstable function would rename the same level on every reconcile."""
    once = _oh_level_name(raw)
    assert _oh_level_name(once) == once


@pytest.mark.parametrize(
    "raw,expected",
    [
        # keeps the distinguishing head noun instead of stranding on word 1
        ("Electrical Substation IED Network", "Elec Substn IED"),
        ("Rockwell Automotive Assembly", "Rockwell Auto Asm"),
        # the em dash is the blocker that made this scenario unprovisionable
        ("Pharma — Vaccine Bioreactor Plant", "Pharma - Vaccine Bio"),
        # canonical multi-word abbreviation beats word-by-word whittling
        ("Substation Local Area Network", "Substation LAN"),
        # connector drop — used to yield "Point of" and "Solar Farm with"
        ("Point of Interconnection Protection", "Point Interconn Prot"),
        ("Solar Farm with Battery Energy Storage", "Solar Farm Batt Engy"),
        # generic tail noun carries no information once the head noun is present
        ("Urban Intersection Network", "Urban Intersection"),
        ("Safety Instrumented System", "Safety Instrumented"),
        # abbreviation preserves a parenthetical that truncation would have cut
        ("Frozen Storage (-20C)", "Frozen Stor (-20C)"),
        ("Purification (TFF + Chromatography)", "Purif (TFF + Chrom)"),
        # separator tightening, but only when it alone makes the name fit
        ("Semiconductor Fab — 300mm Wafer Line", "Semi Fab-300mm Wafer"),
        ("Parcel Sorting Hub - 7/13/2026", "Parcel Sort Hub"),
        # sibling zones must stay distinguishable from each other
        ("Main Intersection Cabinet Network", "Main Intersect Cab"),
        ("Minor Intersection Cabinet Network", "Minor Intersect Cab"),
    ],
)
def test_expected_compaction(raw, expected):
    assert _oh_level_name(raw) == expected


def test_short_names_pass_through_untouched():
    for raw in ["Bay 4 CMP", "Intake Zone", "External WAN", "Cold Chain Warehouse"]:
        assert _oh_level_name(raw) == raw


def test_generic_word_kept_when_load_bearing():
    """'Network' is noise in a trailing position but is the head noun here."""
    assert _oh_level_name("Network Operations Center").startswith("Network")


def test_degenerate_input_does_not_raise():
    for raw in ["", "   ", None, "———", "()"]:
        assert isinstance(_oh_level_name(raw or ""), str)
