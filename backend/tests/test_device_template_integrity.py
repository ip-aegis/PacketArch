# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Guards on the device-template catalog as a whole.

Motivated by seven pairs of templates that described the same real device
twice under two id spellings — `rockwell/io/1734-AENT` alongside
`rockwell/pointio/1734-aent`, `endress-hauser/promag/400` alongside
`endress_hauser/promag/400`. Two generations of catalog seeding had used
different id conventions and the older entries were never removed.

That is worse than untidy. Templates are looked up by `(vendor, model)`, which
returns whichever of the two the registry happens to reach first, so:

* one template of each pair was unreachable dead data, including curated
  firmware variants and CVEs that could never be emitted, and
* the pair disagreed on the TCP fingerprint (one PowerFlex 525 claimed
  `ttl 64, window 16384`, its twin `ttl 128, window 64240`) and on
  `device_type`, so which fingerprint a pinned device got came down to module
  import order.
"""

from __future__ import annotations

import collections

from app.services.device_templates import (
    get_all_templates,
    get_template_by_vendor_model,
)


def test_no_two_templates_describe_the_same_vendor_and_model():
    """`(vendor, model)` is the lookup key, so it has to be unique.

    A second template under the same key is unreachable through
    `get_template_by_vendor_model`, which means its firmware variants and CVEs
    can never be emitted while it still shows up in the library UI.
    """
    by_key = collections.defaultdict(list)
    for template in get_all_templates():
        by_key[(template.vendor, template.model)].append(template.id)

    duplicates = {k: v for k, v in by_key.items() if len(v) > 1}
    assert not duplicates, (
        "these (vendor, model) keys resolve to more than one template, so "
        "which one a pinned device gets depends on import order:\n" + "\n".join(
            f"  {vendor} / {model}: {ids}"
            for (vendor, model), ids in sorted(duplicates.items())
        )
    )


def test_template_ids_are_unique():
    """The registry is keyed by id, so a collision silently drops a template."""
    ids = [t.id for t in get_all_templates()]
    dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
    assert not dupes, f"duplicate template ids: {dupes}"


def test_every_template_is_reachable_by_vendor_and_model():
    """Registered but unreachable is the failure mode the duplicates created.

    Uniqueness above is necessary but not sufficient: a vendor string the
    lookup normalizes differently would also strand a template. Assert the
    round trip for every entry rather than inferring it.
    """
    unreachable = []
    for template in get_all_templates():
        found = get_template_by_vendor_model(template.vendor, template.model)
        if found is None or found.id != template.id:
            unreachable.append(
                (template.id, found.id if found else None)
            )
    assert not unreachable, (
        "templates that cannot be looked up by their own (vendor, model):\n"
        + "\n".join(f"  {tid} -> resolved to {got}" for tid, got in unreachable)
    )
