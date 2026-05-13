# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Structural assertions for the reworked strict_purdue_segmented template.

The template is hand-authored (not generated), so a tiny set of invariants
catches accidental regressions: device count, isolation mode, zero
east/west L0-L2 conduits, every device referenced by at least one flow.
"""

import pytest

from app.scenario_templates import VERTICAL_TEMPLATES


@pytest.fixture(scope="module")
def template():
    return VERTICAL_TEMPLATES["manufacturing"]["strict_purdue_segmented"]


def test_device_count_is_at_most_35(template):
    devices = template["devices"]
    total = sum(d.get("count", 1) for d in devices)
    assert total <= 35, f"Template has {total} devices, expected <= 35"


def test_cell_isolation_strict_northbound_default(template):
    isolation = template.get("cell_isolation")
    assert isolation is not None, "Template must declare cell_isolation"
    assert isolation["mode"] == "strict_northbound"
    assert sorted(isolation.get("applies_to_levels", [])) == [0, 1, 2]


def test_no_east_west_conduits_at_l0_l2(template):
    """Every conduit must terminate above the cell layer (L >= 3) at one end.

    The whole point of the strict template is that L0-L2 cells are hermetic.
    A conduit between two L0-L2 zones would contradict the design.
    """
    levels_by_zone = {
        z["id"]: float(z["level"]) for z in template["zones"] if "level" in z
    }
    offenders = []
    for c in template["conduits"]:
        src = c["source_zone"]
        tgt = c["target_zone"]
        src_level = levels_by_zone.get(src)
        tgt_level = levels_by_zone.get(tgt)
        if src_level is None or tgt_level is None:
            continue
        if src_level <= 2 and tgt_level <= 2:
            offenders.append((c["id"], src, tgt, src_level, tgt_level))
    assert not offenders, (
        f"East/west L0-L2 conduits detected: {offenders}. "
        "Strict template must have zero cell-to-cell conduits."
    )


def test_each_zone_has_devices(template):
    devices = template["devices"]
    zones_with_devices = {d.get("zone") for d in devices}
    expected_zones = {z["id"] for z in template["zones"]}
    missing = expected_zones - zones_with_devices
    assert not missing, f"Zones with no devices: {missing}"


def test_cells_have_a_switch(template):
    """Every L0-L2 cell needs a switch so SNMP infrastructure flows can target it."""
    cell_zones = {z["id"] for z in template["zones"] if z.get("level", 99) <= 2}
    cells_with_switch = {
        d["zone"] for d in template["devices"]
        if d.get("type") == "switch" and d.get("zone") in cell_zones
    }
    assert cells_with_switch == cell_zones, (
        f"Cells missing a switch: {cell_zones - cells_with_switch}"
    )


def test_every_flow_endpoint_type_exists(template):
    """No flow targets a device type that no longer exists in the template
    (e.g. a leftover `gateway` flow after the OPC Gateway was removed)."""
    available_types = {d.get("type") for d in template["devices"]}
    missing_pairs: list[tuple[str, str]] = []
    for flow in template["flows"]:
        for kind, types in (
            ("source", flow.get("source_types", [])),
            ("target", flow.get("target_types", [])),
        ):
            for t in types:
                if t not in available_types:
                    missing_pairs.append((kind, t))
    assert not missing_pairs, (
        f"Flow templates reference device types absent from the template: "
        f"{set(missing_pairs)}"
    )


def test_intra_cell_flows_stay_in_one_zone(template):
    """Every flow whose source and target zones are L0-L2 cells must use the
    same zone for both endpoints. Cross-cell flow specs would be silently
    dropped at runtime by the cell-isolation gate."""
    levels_by_zone = {
        z["id"]: float(z["level"]) for z in template["zones"] if "level" in z
    }
    cell_zone_ids = {zid for zid, lvl in levels_by_zone.items() if lvl <= 2}
    for flow in template["flows"]:
        srcs = set(flow.get("source_zones") or [])
        tgts = set(flow.get("target_zones") or [])
        cell_srcs = srcs & cell_zone_ids
        cell_tgts = tgts & cell_zone_ids
        if cell_srcs and cell_tgts:
            # Both endpoints are cells — they must be the SAME cell.
            assert cell_srcs == cell_tgts, (
                f"Cell-to-cell flow {flow.get('protocol')} crosses cells: "
                f"{cell_srcs} -> {cell_tgts}"
            )


def test_cell_isolation_propagation_path(template):
    """The plumbing in templates.py copies the template's cell_isolation
    into definition.cell_isolation. Sanity-check the field shape so the
    runtime gate can parse it."""
    from app.protocol_engines.cell_isolation import parse_config

    parsed = parse_config({"cell_isolation": template["cell_isolation"]})
    assert parsed["mode"] == "strict_northbound"
    assert parsed["cell_levels"] == {0, 1, 2}
