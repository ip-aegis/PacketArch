# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""BACnet vendor-ID data-integrity guards.

Every device template that speaks BACnet announces a ``vendor_id`` in its
I-Am / Device-object responses. Cyber Vision keys vendor classification off
this value, so it MUST be the manufacturer's ASHRAE-registered BACnet vendor
id — not another vendor's id and not an unregistered number.

These guards keep the per-template ``bacnet_identity["vendor_id"]`` aligned
with the curated ``BACNET_VENDOR_IDS`` registry. They exist because a prior
audit corrected the registry (e.g. Siemens 24->7, Schneider 67->10) but the
fix never propagated to the templates, leaving e.g. a Siemens Desigo
controller announcing Schneider's id 10.
"""
from __future__ import annotations

from app.protocol_engines.vendor_oui import BACNET_VENDOR_IDS, normalize_vendor
from app.services.device_templates import get_all_templates


def _bacnet_templates():
    for t in get_all_templates():
        bid = t.bacnet_identity
        if bid and "vendor_id" in bid:
            yield t


def _names_match(template_vendor: str, registry_name: str) -> bool:
    a, b = normalize_vendor(template_vendor), normalize_vendor(registry_name)
    if a == b:
        return True
    # tolerate suffix differences like "Carel" vs "Carel Industries"
    af, bf = a.replace("_", " ").split()[0], b.replace("_", " ").split()[0]
    return af == bf


def test_every_bacnet_vendor_id_is_registered():
    """No template may ship a BACnet vendor_id absent from the registry."""
    unknown = []
    for t in _bacnet_templates():
        vid = t.bacnet_identity["vendor_id"]
        if vid not in BACNET_VENDOR_IDS:
            unknown.append((t.vendor, t.model_name, vid))
    assert not unknown, (
        "BACnet vendor_id not in BACNET_VENDOR_IDS registry:\n"
        + "\n".join(f"  {v} / {m}: vendor_id={vid}" for v, m, vid in unknown)
    )


def test_bacnet_vendor_id_matches_manufacturer():
    """A template's BACnet vendor_id must resolve to ITS manufacturer, not
    a different vendor (catches copy-paste collisions like Siemens=10)."""
    mismatches = []
    for t in _bacnet_templates():
        vid = t.bacnet_identity["vendor_id"]
        reg_name = BACNET_VENDOR_IDS.get(vid)
        if reg_name is None:
            continue  # covered by the registered-id test
        if not _names_match(t.vendor or "", reg_name):
            mismatches.append((t.vendor, t.model_name, vid, reg_name))
    assert not mismatches, (
        "BACnet vendor_id maps to the wrong manufacturer:\n"
        + "\n".join(
            f"  {v} / {m}: vendor_id={vid} -> registry says '{rn}'"
            for v, m, vid, rn in mismatches
        )
    )
