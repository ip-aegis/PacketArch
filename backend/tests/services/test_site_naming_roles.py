# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Site naming for template-built scenarios.

The create route stores roles as ``architecturalRole`` and hand templates put
display text there; the renamer used to miss the key and cut the display text
to six characters, producing names such as ``TX130-TOLL-TRAFFI-001`` (and
names with spaces). These tests pin the fixed behaviour.
"""
import pytest

from app.services.architecture.site_identity import SiteIdentity
from app.services.architecture.site_naming import _device_role, apply_site_identity


def _identity():
    return SiteIdentity(
        site_code="MTR", plant_name="Metro TMC", location="Metro City", operator="City DOT",
        industry_context="traffic management", domain_suffix=None, naming_style="site_role_idx",
        role_patterns={}, zone_codes={"tmc": "TMC", "hub1": "HUB1", "hub2": "HUB2"},
    )


def test_camel_case_role_key_is_read():
    assert _device_role({"architecturalRole": "jump_server"}) == "jump_server"


def test_display_text_role_falls_back_to_the_device_type():
    role = _device_role({"architecturalRole": "ATMS Coordination Master", "type": "traffic_controller"})
    assert role == "traffic_controller"


def test_generated_names_have_no_spaces_or_collisions():
    devices = {}
    for i, (zone, dtype, role) in enumerate([
        ("hub1", "camera_anpr", "ANPR Camera"), ("hub2", "camera_anpr", "ANPR Camera"),
        ("hub1", "instrument", None), ("hub1", "transmitter", None),
        ("tmc", "server", "Jump"), ("hub1", "server", "Jump"),
    ]):
        devices[f"d{i}"] = {"id": f"d{i}", "type": dtype, "zoneId": zone, "architecturalRole": role}
    apply_site_identity(definition={"devices": devices}, identity=_identity())
    names = [d["name"] for d in devices.values()]
    assert len(set(names)) == len(names)
    assert not any(" " in n for n in names)
    assert not any(n.rsplit("-", 1)[-1].isdigit() and n.rsplit("-", 2)[-2].isdigit() for n in names)


def test_curated_names_keep_the_asset_name_with_the_site_prefix():
    devices = {
        "a": {"id": "a", "type": "traffic_controller", "zoneId": "hub1",
              "name": "Main_St_and_5th_ATC", "_curated_name": "Main_St_and_5th_ATC"},
        "b": {"id": "b", "type": "traffic_controller", "zoneId": "hub1",
              "name": "Oak Ave ATC", "_curated_name": "Oak Ave ATC"},
    }
    apply_site_identity(definition={"devices": devices}, identity=_identity())
    assert devices["a"]["name"] == "MTR-Main_St_and_5th_ATC"
    assert devices["b"]["name"] == "MTR-Oak_Ave_ATC"
    # Re-running (the background LLM naming pass) keeps them stable.
    apply_site_identity(definition={"devices": devices}, identity=_identity())
    assert devices["a"]["name"] == "MTR-Main_St_and_5th_ATC"


@pytest.mark.parametrize("vertical,name", [
    ("transportation", "highway_corridor_its"),
    ("transportation", "urban_intersection_network"),
    ("manufacturing", "strict_purdue_segmented"),
])
def test_audit_builds_the_hand_list_with_clean_names(vertical, name):
    from app.scenario_templates import get_template
    from app.services.template_definition_builder import populate_definition_from_template

    template = get_template(vertical, name)
    definition = populate_definition_from_template(vertical, name)
    names = [d["name"] for d in definition["devices"].values()]
    assert len(names) == sum(d.get("count", 1) for d in template["devices"])
    assert len(set(names)) == len(names)
    assert not any(" " in n for n in names)
