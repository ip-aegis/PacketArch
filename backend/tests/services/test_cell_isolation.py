# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for the Purdue-aware cell isolation gate."""


from app.protocol_engines.cell_isolation import (
    DEFAULT_CELL_LEVELS,
    MODE_CONDUIT_GATED,
    MODE_OFF,
    MODE_STRICT_NORTHBOUND,
    classify_cell_zones,
    is_cell_to_cell,
    is_cell_to_cell_conduit,
    parse_config,
    preview_strict_northbound,
    prune_for_strict_northbound,
    should_drop_flow,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _zones():
    """Two L1 cells, one L2 cell, one L3 operations zone."""
    return {
        "cell_a": {"id": "cell_a", "name": "Cell A", "level": 1, "deviceIds": ["plc_a"]},
        "cell_b": {"id": "cell_b", "name": "Cell B", "level": 1, "deviceIds": ["plc_b"]},
        "supervisory": {"id": "supervisory", "name": "Supervisory", "level": 2, "deviceIds": ["hmi"]},
        "operations": {"id": "operations", "name": "Operations", "level": 3, "deviceIds": ["historian"]},
    }


def _devices():
    return {
        "plc_a": {"id": "plc_a", "name": "PLC A"},
        "plc_b": {"id": "plc_b", "name": "PLC B"},
        "hmi": {"id": "hmi", "name": "HMI"},
        "historian": {"id": "historian", "name": "Historian"},
    }


def _flow(fid, src, dst, protocol="modbus_tcp"):
    return {
        "id": fid,
        "sourceDeviceId": src,
        "targetDeviceId": dst,
        "protocol": protocol,
    }


def _conduit(cid, src_zone, tgt_zone, protocols=None, direction="bidirectional"):
    return {
        "id": cid,
        "sourceZoneId": src_zone,
        "targetZoneId": tgt_zone,
        "direction": direction,
        "allowedProtocols": protocols or ["modbus_tcp"],
    }


# ---------------------------------------------------------------------------
# parse_config
# ---------------------------------------------------------------------------


class TestParseConfig:
    def test_missing_block_defaults_to_off(self):
        cfg = parse_config({})
        assert cfg["mode"] == MODE_OFF
        assert cfg["cell_levels"] == set(DEFAULT_CELL_LEVELS)

    def test_none_definition_defaults(self):
        cfg = parse_config(None)
        assert cfg["mode"] == MODE_OFF
        assert cfg["cell_levels"] == {0, 1, 2}

    def test_invalid_mode_falls_back_to_off(self):
        cfg = parse_config({"cell_isolation": {"mode": "yolo"}})
        assert cfg["mode"] == MODE_OFF

    def test_explicit_modes_pass_through(self):
        for m in (MODE_OFF, MODE_CONDUIT_GATED, MODE_STRICT_NORTHBOUND):
            cfg = parse_config({"cell_isolation": {"mode": m}})
            assert cfg["mode"] == m

    def test_custom_cell_levels(self):
        cfg = parse_config({
            "cell_isolation": {
                "mode": "strict_northbound",
                "applies_to_levels": [0, 1],
            }
        })
        assert cfg["cell_levels"] == {0, 1}

    def test_garbage_levels_are_ignored(self):
        cfg = parse_config({
            "cell_isolation": {
                "mode": "off",
                "applies_to_levels": ["a", None, 2],
            }
        })
        assert cfg["cell_levels"] == {2}


# ---------------------------------------------------------------------------
# classify_cell_zones
# ---------------------------------------------------------------------------


class TestClassifyCellZones:
    def test_l0_l1_l2_classified_as_cells(self):
        zones = {
            "z0": {"level": 0},
            "z1": {"level": 1},
            "z2": {"level": 2},
            "z3": {"level": 3},
            "z3_5": {"level": 3.5},  # DMZ; floor → 3
        }
        cells = classify_cell_zones(zones)
        assert cells == {"z0", "z1", "z2"}

    def test_zones_without_level_are_skipped(self):
        zones = {"z": {"name": "no level"}, "z1": {"level": 1}}
        cells = classify_cell_zones(zones)
        assert cells == {"z1"}

    def test_custom_cell_levels_only_l0(self):
        zones = {"z0": {"level": 0}, "z1": {"level": 1}, "z2": {"level": 2}}
        cells = classify_cell_zones(zones, cell_levels=[0])
        assert cells == {"z0"}


# ---------------------------------------------------------------------------
# should_drop_flow — off mode
# ---------------------------------------------------------------------------


class TestModeOff:
    def test_off_mode_never_drops(self):
        flow = _flow("f1", "plc_a", "plc_b")
        drop, reason = should_drop_flow(
            flow, _devices(), _zones(), {},
            isolation={"mode": MODE_OFF, "cell_levels": {0, 1, 2}},
        )
        assert not drop
        assert reason is None


# ---------------------------------------------------------------------------
# should_drop_flow — strict_northbound
# ---------------------------------------------------------------------------


class TestStrictNorthbound:
    def _iso(self):
        return {"mode": MODE_STRICT_NORTHBOUND, "cell_levels": {0, 1, 2}}

    def test_blocks_l1_to_l1_cell_traffic(self):
        flow = _flow("f1", "plc_a", "plc_b")
        drop, reason = should_drop_flow(
            flow, _devices(), _zones(), {}, isolation=self._iso(),
        )
        assert drop is True
        assert "strict_northbound" in reason
        assert "L1↔L1" in reason

    def test_blocks_l1_to_l2_cell_traffic(self):
        flow = _flow("f2", "plc_a", "hmi")
        drop, _ = should_drop_flow(
            flow, _devices(), _zones(), {}, isolation=self._iso(),
        )
        assert drop is True

    def test_allows_cell_to_l3_northbound(self):
        flow = _flow("f3", "plc_a", "historian")
        drop, reason = should_drop_flow(
            flow, _devices(), _zones(), {}, isolation=self._iso(),
        )
        assert drop is False
        assert reason is None

    def test_allows_l3_to_cell_southbound(self):
        flow = _flow("f4", "historian", "plc_a")
        drop, _ = should_drop_flow(
            flow, _devices(), _zones(), {}, isolation=self._iso(),
        )
        assert drop is False

    def test_intra_cell_flows_pass(self):
        # Both endpoints in the same cell zone — never blocked.
        zones = _zones()
        zones["cell_a"]["deviceIds"] = ["plc_a", "io_module"]
        devices = _devices()
        devices["io_module"] = {"id": "io_module"}
        flow = _flow("f5", "plc_a", "io_module")
        drop, _ = should_drop_flow(flow, devices, zones, {}, isolation=self._iso())
        assert drop is False

    def test_conduit_does_not_save_cell_to_cell(self):
        # Even a permitting conduit cannot save a cell↔cell flow in strict.
        conduits = {"c": _conduit("c", "cell_a", "cell_b", ["modbus_tcp"])}
        flow = _flow("f6", "plc_a", "plc_b")
        drop, _ = should_drop_flow(
            flow, _devices(), _zones(), conduits, isolation=self._iso(),
        )
        assert drop is True

    def test_no_zones_means_permissive(self):
        flow = _flow("f7", "plc_a", "plc_b")
        drop, _ = should_drop_flow(
            flow, _devices(), {}, {}, isolation=self._iso(),
        )
        assert drop is False


# ---------------------------------------------------------------------------
# should_drop_flow — conduit_gated
# ---------------------------------------------------------------------------


class TestConduitGated:
    def _iso(self):
        return {"mode": MODE_CONDUIT_GATED, "cell_levels": {0, 1, 2}}

    def test_blocks_cell_to_cell_with_no_conduit(self):
        flow = _flow("f1", "plc_a", "plc_b")
        drop, reason = should_drop_flow(
            flow, _devices(), _zones(), {}, isolation=self._iso(),
        )
        assert drop is True
        assert "no conduit" in reason

    def test_allows_cell_to_cell_with_permitting_conduit(self):
        conduits = {"c": _conduit("c", "cell_a", "cell_b", ["modbus_tcp"])}
        flow = _flow("f2", "plc_a", "plc_b")
        drop, _ = should_drop_flow(
            flow, _devices(), _zones(), conduits, isolation=self._iso(),
        )
        assert drop is False

    def test_blocks_cell_to_cell_when_protocol_not_in_conduit(self):
        conduits = {"c": _conduit("c", "cell_a", "cell_b", ["s7comm"])}
        flow = _flow("f3", "plc_a", "plc_b", protocol="modbus_tcp")
        drop, _ = should_drop_flow(
            flow, _devices(), _zones(), conduits, isolation=self._iso(),
        )
        assert drop is True

    def test_protocol_aliases_match_conduit(self):
        # Conduit allows 's7comm' generically, flow uses 's7comm_plus' variant.
        conduits = {"c": _conduit("c", "cell_a", "cell_b", ["s7comm"])}
        flow = _flow("f4", "plc_a", "plc_b", protocol="s7comm_plus")
        drop, _ = should_drop_flow(
            flow, _devices(), _zones(), conduits, isolation=self._iso(),
        )
        assert drop is False

    def test_a_to_b_direction_blocks_reverse(self):
        conduits = {
            "c": _conduit("c", "cell_a", "cell_b", ["modbus_tcp"], direction="a_to_b"),
        }
        flow_reverse = _flow("f5", "plc_b", "plc_a")
        drop, _ = should_drop_flow(
            flow_reverse, _devices(), _zones(), conduits, isolation=self._iso(),
        )
        assert drop is True

    def test_cell_to_l3_unconstrained(self):
        # Northbound flows are not gated by conduits in conduit_gated mode.
        flow = _flow("f6", "plc_a", "historian")
        drop, _ = should_drop_flow(
            flow, _devices(), _zones(), {}, isolation=self._iso(),
        )
        assert drop is False


# ---------------------------------------------------------------------------
# is_cell_to_cell helpers (used by frontend preview generation)
# ---------------------------------------------------------------------------


class TestCellToCellHelpers:
    def test_is_cell_to_cell_true(self):
        assert is_cell_to_cell(
            _flow("f", "plc_a", "plc_b"), _devices(), _zones(),
        )

    def test_is_cell_to_cell_false_when_one_side_is_l3(self):
        assert not is_cell_to_cell(
            _flow("f", "plc_a", "historian"), _devices(), _zones(),
        )

    def test_is_cell_to_cell_false_when_same_zone(self):
        zones = _zones()
        zones["cell_a"]["deviceIds"] = ["plc_a", "plc_b"]
        assert not is_cell_to_cell(
            _flow("f", "plc_a", "plc_b"), _devices(), zones,
        )

    def test_is_cell_to_cell_conduit(self):
        assert is_cell_to_cell_conduit(
            _conduit("c", "cell_a", "cell_b"), _zones(),
        )

    def test_l1_to_l3_conduit_is_not_cell_to_cell(self):
        assert not is_cell_to_cell_conduit(
            _conduit("c", "cell_a", "operations"), _zones(),
        )


# ---------------------------------------------------------------------------
# prune_for_strict_northbound
# ---------------------------------------------------------------------------


class TestPrune:
    def test_prune_drops_cell_flows_and_conduits(self):
        definition = {
            "devices": _devices(),
            "zones": _zones(),
            "flows": {
                "east_west_1": _flow("east_west_1", "plc_a", "plc_b"),
                "east_west_2": _flow("east_west_2", "plc_a", "hmi"),
                "northbound": _flow("northbound", "plc_a", "historian"),
                "intra_cell": _flow("intra_cell", "plc_a", "plc_a"),
            },
            "conduits": {
                "cell_to_cell": _conduit("cell_to_cell", "cell_a", "cell_b"),
                "cell_to_l3": _conduit("cell_to_l3", "cell_a", "operations"),
            },
        }
        new_def, removed = prune_for_strict_northbound(definition)
        assert sorted(removed["flows"]) == ["east_west_1", "east_west_2"]
        assert removed["conduits"] == ["cell_to_cell"]
        assert "northbound" in new_def["flows"]
        assert "intra_cell" in new_def["flows"]
        assert "cell_to_l3" in new_def["conduits"]
        assert new_def["cell_isolation"]["mode"] == MODE_STRICT_NORTHBOUND

    def test_prune_with_list_format_flows(self):
        definition = {
            "devices": _devices(),
            "zones": _zones(),
            "flows": [
                _flow("ew", "plc_a", "plc_b"),
                _flow("nb", "plc_a", "historian"),
            ],
            "conduits": [],
        }
        new_def, removed = prune_for_strict_northbound(definition)
        assert removed["flows"] == ["ew"]
        assert len(new_def["flows"]) == 1

    def test_prune_does_not_mutate_original(self):
        definition = {
            "devices": _devices(),
            "zones": _zones(),
            "flows": {"ew": _flow("ew", "plc_a", "plc_b")},
            "conduits": {},
        }
        prune_for_strict_northbound(definition)
        assert "ew" in definition["flows"]


# ---------------------------------------------------------------------------
# preview_strict_northbound
# ---------------------------------------------------------------------------


class TestPreview:
    def test_preview_describes_each_removal(self):
        definition = {
            "devices": _devices(),
            "zones": _zones(),
            "flows": {"ew": _flow("ew", "plc_a", "plc_b", "modbus_tcp")},
            "conduits": {"cc": _conduit("cc", "cell_a", "cell_b", ["modbus_tcp"])},
        }
        preview = preview_strict_northbound(definition)
        assert len(preview["flows"]) == 1
        assert preview["flows"][0]["id"] == "ew"
        assert preview["flows"][0]["protocol"] == "modbus_tcp"
        assert preview["flows"][0]["source_zone"] == "cell_a"
        assert preview["flows"][0]["target_zone"] == "cell_b"
        assert len(preview["conduits"]) == 1
        assert preview["conduits"][0]["id"] == "cc"
        assert preview["conduits"][0]["allowed_protocols"] == ["modbus_tcp"]

    def test_preview_empty_when_nothing_to_remove(self):
        definition = {
            "devices": _devices(),
            "zones": _zones(),
            "flows": {"nb": _flow("nb", "plc_a", "historian")},
            "conduits": {},
        }
        preview = preview_strict_northbound(definition)
        assert preview == {"flows": [], "conduits": []}
