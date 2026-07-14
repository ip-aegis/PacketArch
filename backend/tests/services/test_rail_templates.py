# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Rail device templates — realism + registration checks.

Every rail template must satisfy the platform's realism dimensions: unique
industrial names, protocol accuracy (emp for PTC vendors, atcs for legacy
signaling), populated protocol identity, and IEEE-verified MAC/OUI alignment.
"""

import pytest

from app.core.vendor_normalize import normalize_vendor
from app.protocol_engines.vendor_oui import VENDOR_OUIS
from app.services.device_templates._protocol_defaults import PROTOCOL_TO_TEMPLATE_IDENTITY
from app.services.device_templates._registry import DEVICE_TEMPLATES


RAIL = [t for t in DEVICE_TEMPLATES.values() if "rail" in (t.vertical_hints or [])]


def test_rail_templates_registered():
    ids = {t.id for t in RAIL}
    assert {"wabtec/i-etms/bos", "wabtec/i-etms/wiu", "wabtec/i-etms/tmc",
            "ge_transportation/itcs/wayside", "alstom/atcs/mcp",
            "siemens_mobility/atcs/bcp", "hitachi_rail/atcs/wayside"} <= ids


@pytest.mark.parametrize("t", RAIL, ids=lambda t: t.id)
def test_oui_matches_vendor_ieee(t):
    """Realism dim 5: each OUI prefix is in the vendor's IEEE-verified list."""
    key = normalize_vendor(t.vendor)
    assert key in VENDOR_OUIS, f"{t.vendor} not IEEE-grounded"
    for oui in t.oui_prefixes:
        assert oui in VENDOR_OUIS[key], f"{t.id}: {oui} not a {t.vendor} OUI"


@pytest.mark.parametrize("t", RAIL, ids=lambda t: t.id)
def test_protocol_accuracy_and_identity(t):
    """Realism dims 2+3: emp/atcs only, and the matching identity is populated."""
    assert t.supported_protocols, f"{t.id}: no protocols"
    for proto in t.supported_protocols:
        assert proto in ("emp", "atcs"), f"{t.id}: unexpected protocol {proto}"
        ident_field = PROTOCOL_TO_TEMPLATE_IDENTITY[proto]
        assert getattr(t, ident_field), f"{t.id}: {ident_field} not populated"


@pytest.mark.parametrize("t", RAIL, ids=lambda t: t.id)
def test_industrial_naming_and_firmware(t):
    """Realism dim 1 + firmware variants present with a default."""
    assert t.model_name and not t.model_name[0].islower()
    assert t.instance_rules and t.instance_rules.station_name_pattern
    assert t.firmware_variants and t.get_default_firmware() is not None


def test_unique_names_and_ids():
    assert len({t.id for t in RAIL}) == len(RAIL)
    assert len({t.model_name for t in RAIL}) == len(RAIL)


def test_ptc_vs_atcs_split():
    """PTC vendors speak EMP; legacy signaling vendors speak ATCS."""
    by_vendor = {normalize_vendor(t.vendor): t.supported_protocols[0] for t in RAIL}
    assert by_vendor["wabtec"] == "emp"
    assert by_vendor["ge transportation"] == "emp"
    assert by_vendor["alstom"] == "atcs"
    assert by_vendor["siemens mobility"] == "atcs"
    assert by_vendor["hitachi rail"] == "atcs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
