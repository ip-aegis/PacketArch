# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Guards on the archetype vendor-pinning table.

Two defects motivated these, both found by generating scenarios and counting
what came out rather than by reading the table:

1. **A pin naming a model the device catalog does not contain** resolves to no
   template, so the device gets a model string with no fingerprint behind it.
   ``(DCS_HONEYWELL, "field_instrument") -> ("honeywell", "STT850")`` did this.

2. **A single pinned model on a role that appears many times** makes every
   instance fingerprint-identical. Cyber Vision MERGES
   identically-fingerprinted devices, so 44 identical transmitters can collapse
   into far fewer CV assets than the scenario declares — and a device present
   in one view and absent from the other is exactly what breaks an inventory
   comparison.

The second check is a RATCHET. ``KNOWN_SINGLE_MODEL`` lists the gaps that
remain because the device catalog has no alternative to offer (it holds exactly
one valve positioner, and no Honeywell or Yokogawa drives or I/O at all).
Closing those needs new device templates — real OUIs, firmware variants, CVEs —
which is curation work, not a pinning change. Entries may be REMOVED from this
list, never added: a new offender is a regression.
"""

from __future__ import annotations

import collections

import pytest

from app.scenario_templates import VERTICAL_TEMPLATES
from app.services.architecture.legacy_template_archetypes import (
    get_archetype_config,
)
from app.services.architecture.scenario_generator import (
    _INSTRUMENT_MEASUREMENTS,
)
from app.services.architecture.vendor_pinning import (
    _MULTI_VENDOR_CYCLE_NAMES,
    _PIN_MEASUREMENTS,
    _PINNING,
    _PROFILE_AGNOSTIC,
    VendorProfile,
    filter_by_measurement,
    get_pin_candidates,
)
from app.services.device_templates import get_template_by_vendor_model
from app.services.template_definition_builder import (
    populate_definition_from_template,
)

# Roles that stay single-model until the device catalog gains alternatives.
# Shrink this list; never grow it.
# Single-model by DESIGN, not by omission. A DCS ships its own I/O and its own
# operator console; a Honeywell Series C rack full of Rockwell I/O, or an
# Experion plant driven from a third-party console, would be LESS realistic
# than the repetition. These are excluded from the ratchet permanently, and
# adding models here would be a regression rather than a fix.
CORRECTLY_SINGLE_VENDOR: set[tuple[str, str]] = {
    ("dcs_honeywell", "distributed_io"),         # Series C I/O
    ("dcs_honeywell", "area_hmi"),               # Experion Station
    ("dcs_emerson", "area_hmi"),                 # DeltaV console
    ("dcs_yokogawa", "distributed_io"),          # DCS-native I/O
}

# Single-model because the device catalog has nothing else to offer. Each of
# these needs a NEW device template — a verified IEEE OUI, a real order code,
# NVD-checked CVEs — which is curation work, not a pinning change.
#
# Shrink this list; never grow it. A new entry is a regression.
#
# 4 entries, from 31 when the ratchet was written. Everything closable by
# pinning models the catalog already had is done; what is left genuinely needs
# new device templates.
KNOWN_SINGLE_MODEL: set[tuple[str, str]] = {
    ("multi_vendor", "cnc_controller"),          # up to 4
    ("atms_ntcip", "toll_lane_controller"),      # up to 4
    ("atms_ntcip", "toll_rsu"),                  # up to 4
    ("dcim_cisco", "crac_unit"),                 # up to 4
}

MIN_INSTANCES = 4


def _all_pins():
    for (profile, role), pins in _PINNING.items():
        yield profile.value, role, pins
    for role, pins in _PROFILE_AGNOSTIC.items():
        yield "<agnostic>", role, pins
    # _PIN_MEASUREMENTS is a third pin source: a typo in one of its keys would
    # silently make that entry dead, so the model it names must exist in the
    # catalog too. Without this the measurement table would be the one pin
    # table the catalog check never saw.
    yield "<measurements>", "field_instrument", tuple(_PIN_MEASUREMENTS)


def _reachable_pins(profile_value: str, role: str) -> tuple:
    """The pins the generator can actually reach for a (profile, role).

    MULTI_VENDOR does not resolve its own pins — the generator cycles a
    sub-vendor per zone and looks the role up on THAT profile, falling back to
    MULTI_VENDOR and then to the agnostic table. Reading the (empty)
    MULTI_VENDOR table instead reported a false offender for every
    multi_vendor role, so mirror what the generator actually reaches.
    """
    if profile_value == "multi_vendor":
        pins: list = []
        for sub in _MULTI_VENDOR_CYCLE_NAMES:
            pins.extend(get_pin_candidates(VendorProfile(sub), role))
        pins.extend(get_pin_candidates(VendorProfile(profile_value), role))
        return tuple(pins)
    return get_pin_candidates(VendorProfile(profile_value), role)


def test_every_pinned_model_exists_in_the_device_catalog():
    """A pin that resolves to nothing yields a device with no fingerprint."""
    missing = [
        (profile, role, vendor, model)
        for profile, role, pins in _all_pins()
        for vendor, model in pins
        if get_template_by_vendor_model(vendor, model) is None
    ]
    assert not missing, "pins with no catalog template:\n" + "\n".join(
        f"  ({p}, {r}) -> ({v}, {m})" for p, r, v, m in missing
    )


def _high_multiplicity_roles():
    """(profile, role) pairs that a real generated scenario emits >= 4 of."""
    seen: dict[tuple[str, str], int] = {}
    for vertical, templates in VERTICAL_TEMPLATES.items():
        for name in templates:
            cfg = get_archetype_config(vertical, name)
            if cfg is None:
                continue
            defn = populate_definition_from_template(vertical, name)
            if not defn:
                continue
            counts = collections.Counter(
                d.get("architectural_role")
                for d in defn["devices"].values()
            )
            for role, n in counts.items():
                if not role or n < MIN_INSTANCES:
                    continue
                key = (cfg.vendor_profile.value, role)
                seen[key] = max(seen.get(key, 0), n)
    return seen


@pytest.mark.integration
def test_the_survey_is_not_vacuous():
    """Silence must not look like success.

    Everything below is "no offenders found -> pass". If the survey ever
    returned nothing — a refactor, a moved template registry, a swallowed
    exception — the ratchet would pass while checking nothing at all. So assert
    the survey still sees a realistic population before trusting its verdict.
    """
    surveyed = _high_multiplicity_roles()
    assert len(surveyed) >= 50, (
        f"survey found only {len(surveyed)} high-multiplicity (profile, role) "
        f"pairs; it saw ~90 when written, so it is probably not running"
    )
    assert max(surveyed.values()) >= 20, "no role emits >=20 devices — suspicious"


@pytest.mark.integration
def test_high_multiplicity_roles_have_more_than_one_model():
    """Ratchet: no NEW role may emit many devices from one fingerprint."""
    offenders = {}
    for (profile, role), n in _high_multiplicity_roles().items():
        if (profile, role) in KNOWN_SINGLE_MODEL | CORRECTLY_SINGLE_VENDOR:
            continue
        models = {m for _, m in _reachable_pins(profile, role)}
        if len(models) <= 1:
            offenders[(profile, role)] = n
    assert not offenders, (
        "roles emitting >=4 devices from a single fingerprint (Cyber Vision "
        "will merge them):\n" + "\n".join(
            f"  {p}/{r}: up to {n} instances" for (p, r), n in
            sorted(offenders.items())
        )
    )


@pytest.mark.integration
def test_known_single_model_list_has_no_stale_entries():
    """Keep the ratchet honest — a fixed gap must leave the allowlist."""
    stale = []
    for profile, role in sorted(KNOWN_SINGLE_MODEL):
        try:
            candidates = get_pin_candidates(VendorProfile(profile), role)
        except ValueError:
            continue
        if len({m for _, m in candidates}) > 1:
            stale.append((profile, role))
    assert not stale, (
        "these now have multiple models and should be removed from "
        f"KNOWN_SINGLE_MODEL: {stale}"
    )


# ---------------------------------------------------------------------------
# Measurement-aware instrument selection
# ---------------------------------------------------------------------------
#
# The generator stamps every field instrument with a measurement (level / flow
# / pressure) but the pin rotation ignored it, so a tag labelled `level` landed
# on whatever model the rotation reached — a Promag 400 in the water archetype,
# which is an electromagnetic FLOW meter and cannot measure level at all. These
# guard the fix in both directions: the model must suit the measurement, AND
# narrowing the candidate list must not undo the fingerprint diversity the
# ratchet above protects.


def _emitted_instruments():
    """Every field instrument from every real generated scenario.

    Yields (vertical, template, profile_value, zone_id, measurement, pin).
    """
    for vertical, templates in VERTICAL_TEMPLATES.items():
        for name in templates:
            cfg = get_archetype_config(vertical, name)
            if cfg is None:
                continue
            defn = populate_definition_from_template(vertical, name)
            if not defn:
                continue
            for dev in defn["devices"].values():
                if dev.get("architectural_role") != "field_instrument":
                    continue
                model = dev.get("fingerprintModel")
                if not model:
                    continue
                yield (
                    vertical, name, cfg.vendor_profile.value,
                    dev.get("zoneId"), dev.get("measurement"),
                    (dev.get("vendor"), model),
                )


@pytest.mark.integration
def test_the_instrument_survey_is_not_vacuous():
    """Silence must not look like success — same reasoning as the ratchet."""
    rows = list(_emitted_instruments())
    assert len(rows) >= 200, (
        f"only {len(rows)} field instruments surveyed; ~400 were emitted when "
        f"this was written, so the survey is probably not running"
    )
    assert {m for *_, m, _ in rows} == set(_INSTRUMENT_MEASUREMENTS), (
        "every measurement must appear, or a whole branch goes unchecked"
    )


@pytest.mark.integration
def test_every_instrument_can_make_the_measurement_it_is_stamped_with():
    """A level tag must not land on an electromagnetic flow meter."""
    offenders = []
    for vertical, name, profile, _zone, measurement, pin in _emitted_instruments():
        if not measurement:
            continue
        capable = _PIN_MEASUREMENTS.get(pin)
        if capable is None or measurement in capable:
            continue
        # A mismatch is only legitimate where the profile's own pins cannot
        # cover this measurement at all — the documented widening in
        # filter_by_measurement, which prefers a less-apt instrument over a
        # device with no fingerprint. If the profile COULD have picked a
        # suitable model and didn't, that is the bug this test exists for.
        reachable = _reachable_pins(profile, "field_instrument")
        if any(
            measurement in _PIN_MEASUREMENTS.get(c, {measurement})
            for c in reachable
        ):
            offenders.append((vertical, name, pin, measurement))
    assert not offenders, (
        "instruments stamped with a measurement their model cannot make, "
        "where the profile had a suitable model available:\n" + "\n".join(
            f"  {v}/{n}: {p[0]}/{p[1]} stamped {m}"
            for v, n, p, m in sorted(offenders)
        )
    )


@pytest.mark.integration
def test_each_measurement_keeps_more_than_one_model():
    """Ratchet, applied to the new dimension.

    Narrowing candidates by measurement splits one pin list into three smaller
    ones, so the ratchet above — which counts models in the whole list — can
    pass while every level tag in the plant resolves to a single fingerprint.
    Cyber Vision merges identically-fingerprinted devices either way, so the
    diversity requirement has to hold per measurement, not just per role.
    """
    per_measurement = collections.defaultdict(collections.Counter)
    for _v, _n, profile, _zone, measurement, pin in _emitted_instruments():
        if measurement:
            per_measurement[(profile, measurement)][pin[1]] += 1

    offenders = {
        key: dict(models)
        for key, models in per_measurement.items()
        if sum(models.values()) >= MIN_INSTANCES and len(models) <= 1
    }
    assert not offenders, (
        "measurements emitting >=4 instruments from a single fingerprint:\n"
        + "\n".join(
            f"  {p}/{m}: {models}" for (p, m), models in sorted(offenders.items())
        )
    )


@pytest.mark.integration
def test_instruments_sharing_a_zone_and_measurement_are_not_identical():
    """Catches a rotation index that steps in lockstep with the measurement.

    Instruments of the same measurement sit len(_INSTRUMENT_MEASUREMENTS)
    apart in instance_index. Rotating on instance_index therefore steps by 3
    through a 3-model list and returns the same model every time — every flow
    meter in the zone identical. The scenario-wide count in the test above can
    still look healthy in that state, because different ZONES land on
    different models; only a per-zone check sees it.
    """
    per_zone = collections.defaultdict(collections.Counter)
    for _v, name, _p, zone, measurement, pin in _emitted_instruments():
        if measurement and zone:
            per_zone[(name, zone, measurement)][pin[1]] += 1

    offenders = {
        key: dict(models)
        for key, models in per_zone.items()
        if sum(models.values()) >= 2 and len(models) == 1
    }
    assert not offenders, (
        "zones where every instrument of one measurement is the same model:\n"
        + "\n".join(
            f"  {t}/{z}/{m}: {models}"
            for (t, z, m), models in sorted(offenders.items())
        )
    )


def test_filter_by_measurement_leaves_non_instruments_alone():
    """Every role but field_instrument passes None and must be untouched."""
    candidates = (("emerson", "5700"), ("endress_hauser", "Promag 400"))
    assert filter_by_measurement(candidates, None) == candidates
    assert filter_by_measurement(candidates, "") == candidates


def test_filter_by_measurement_narrows_to_suitable_models():
    candidates = (
        ("emerson", "3051S"),               # pressure + level + flow
        ("endress_hauser", "Promag 400"),   # flow only
        ("endress_hauser", "FMP50"),        # level only
    )
    assert filter_by_measurement(candidates, "level") == (
        ("emerson", "3051S"), ("endress_hauser", "FMP50"),
    )
    assert filter_by_measurement(candidates, "flow") == (
        ("emerson", "3051S"), ("endress_hauser", "Promag 400"),
    )
    assert filter_by_measurement(candidates, "pressure") == (
        ("emerson", "3051S"),
    )


def test_filter_by_measurement_widens_rather_than_returning_nothing():
    """No suitable model must yield the full list, never an empty one.

    An empty result would make round_robin_pick return None and the generator
    emit a device with no fingerprint at all — strictly worse than a less-apt
    instrument, and the caller is written to assume this never happens.
    """
    only_flow = (("endress_hauser", "Promag 400"), ("emerson", "5700"))
    assert filter_by_measurement(only_flow, "level") == only_flow


def test_a_pin_absent_from_the_measurement_table_is_unconstrained():
    """Forgetting an entry must degrade to the old behavior, not hide a pin.

    A new instrument pin with no measurement entry stays eligible for every
    measurement. The failure mode of an omission is then the rotation we had
    before the table existed — not an instrument that can never be picked.
    """
    unknown = ("acme", "Widget 1")
    assert unknown not in _PIN_MEASUREMENTS
    assert filter_by_measurement((unknown,), "level") == (unknown,)
    mixed = (("endress_hauser", "FMP50"), unknown)
    assert filter_by_measurement(mixed, "pressure") == (unknown,)
