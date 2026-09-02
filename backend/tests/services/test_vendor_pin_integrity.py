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
from app.services.architecture.vendor_pinning import (
    _PINNING,
    _PROFILE_AGNOSTIC,
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
# 6 entries, from 31 when the ratchet was written. Everything closable by
# pinning models the catalog already had is done; what is left genuinely needs
# new device templates.
KNOWN_SINGLE_MODEL: set[tuple[str, str]] = {
    ("siemens_shop", "servo"),                   # up to 6
    ("rockwell_shop", "servo"),                  # up to 6
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
        from app.services.architecture.vendor_pinning import (
            _MULTI_VENDOR_CYCLE_NAMES,
            VendorProfile,
        )
        # MULTI_VENDOR does not resolve its own pins: the generator cycles a
        # sub-vendor per zone and looks the role up on THAT profile, falling
        # back to MULTI_VENDOR and then to the agnostic table. Checking the
        # MULTI_VENDOR profile alone reported a false offender for every
        # multi_vendor role, so evaluate the union the generator can actually
        # reach.
        if profile == "multi_vendor":
            models: set[str] = set()
            for sub in _MULTI_VENDOR_CYCLE_NAMES:
                models |= {m for _, m in get_pin_candidates(VendorProfile(sub), role)}
            models |= {m for _, m in get_pin_candidates(VendorProfile(profile), role)}
        else:
            models = {m for _, m in get_pin_candidates(VendorProfile(profile), role)}
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
    from app.services.architecture.vendor_pinning import VendorProfile

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
