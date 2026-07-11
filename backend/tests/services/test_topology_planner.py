# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for the multi-sensor topology planner (pure functions)."""

from app.services.topology_planner import (
    CORE_SPAN,
    derive_topology,
    plan_segments,
    preview,
)


def _device(did: str, zone_id: str, ip: str, mac: str, name: str | None = None) -> dict:
    return {
        "id": did,
        "name": name or did,
        "type": "plc",
        "zoneId": zone_id,
        "network": {"ipAddress": ip, "macAddress": mac},
    }


def _three_zone_definition() -> dict:
    return {
        "zones": {
            "z-cell": {
                "id": "z-cell",
                "name": "Assembly Cell",
                "level": 1,
                "network": {"subnet": "10.5.1.0/24", "gateway": "10.5.1.1", "vlan": 101},
            },
            "z-sup": {
                "id": "z-sup",
                "name": "Supervisory",
                "level": 2,
                "network": {"subnet": "10.5.2.0/24", "gateway": "10.5.2.1", "vlan": 102},
            },
            "z-ops": {
                "id": "z-ops",
                "name": "Site Ops",
                "level": 3,
                "network": {"subnet": "10.5.3.0/24", "gateway": "10.5.3.1", "vlan": 103},
            },
        },
        "devices": {
            "plc1": _device("plc1", "z-cell", "10.5.1.10", "00:0e:8c:11:11:11"),
            "plc2": _device("plc2", "z-cell", "10.5.1.11", "00:0e:8c:22:22:22"),
            "hmi1": _device("hmi1", "z-sup", "10.5.2.10", "00:0e:8c:33:33:33"),
            "hist": _device("hist", "z-ops", "10.5.3.10", "00:0e:8c:44:44:44"),
        },
        "flows": {
            "f-intra": {
                "id": "f-intra",
                "sourceDeviceId": "plc1",
                "targetDeviceId": "plc2",
                "protocol": "modbus_tcp",
            },
            "f-cross": {
                "id": "f-cross",
                "sourceDeviceId": "hmi1",
                "targetDeviceId": "plc1",
                "protocol": "s7comm",
            },
        },
    }


class TestDeriveTopology:
    def test_three_zone_topology(self):
        plan = derive_topology(_three_zone_definition(), seed="scn-1")
        assert plan.valid
        assert set(plan.switches) == {"z-cell", "z-sup", "z-ops"}
        assert plan.core is not None
        # SVIs are the zone gateways with per-zone VLANs
        assert plan.core["svis"]["z-cell"]["ip"] == "10.5.1.1"
        assert plan.core["svis"]["z-cell"]["vlan"] == 101
        # Switch mgmt IP follows the .2 convention
        assert plan.switches["z-sup"]["mgmt_ip"] == "10.5.2.2"
        # Core mgmt rides the highest-level zone's SVI
        assert plan.core["mgmt_ip"] == "10.5.3.1"
        # Links: 4 access (device->switch) + 3 trunk (switch->core)
        access = [l for l in plan.links if l["kind"] == "access"]
        trunk = [l for l in plan.links if l["kind"] == "trunk"]
        assert len(access) == 4 and len(trunk) == 3
        # Spans: one per zone + core
        assert {s["id"] for s in plan.spans} == {"zone:z-cell", "zone:z-sup", "zone:z-ops", CORE_SPAN}

    def test_macs_deterministic_and_cisco(self):
        a = derive_topology(_three_zone_definition(), seed="scn-1")
        b = derive_topology(_three_zone_definition(), seed="scn-1")
        c = derive_topology(_three_zone_definition(), seed="scn-2")
        assert a.core["mac"] == b.core["mac"]
        assert a.switches["z-cell"]["mac"] == b.switches["z-cell"]["mac"]
        assert a.core["mac"] != c.core["mac"]
        # All generated MACs are distinct
        macs = [s["mac"] for s in a.switches.values()] + [a.core["mac"]] + [
            svi["mac"] for svi in a.core["svis"].values()
        ]
        assert len(set(macs)) == len(macs)

    def test_unzoned_device_rejected(self):
        definition = _three_zone_definition()
        definition["devices"]["ghost"] = {
            "id": "ghost",
            "name": "Ghost",
            "network": {"ipAddress": "10.5.9.9", "macAddress": "00:0e:8c:99:99:99"},
        }
        plan = derive_topology(definition, seed="s")
        assert not plan.valid
        assert any(e.code == "UNZONED_DEVICE" for e in plan.errors)

    def test_multi_zone_device_rejected(self):
        definition = _three_zone_definition()
        # plc1 has zoneId z-cell; also claim it via z-sup membership list
        definition["zones"]["z-sup"]["deviceIds"] = ["plc1", "hmi1"]
        plan = derive_topology(definition, seed="s")
        assert any(e.code == "MULTI_ZONE_DEVICE" for e in plan.errors)

    def test_zone_network_derived_from_devices(self):
        definition = _three_zone_definition()
        definition["zones"]["z-cell"]["network"] = {}
        plan = derive_topology(definition, seed="s")
        assert plan.valid
        assert plan.switches["z-cell"]["subnet"] == "10.5.1.0/24"
        assert plan.switches["z-cell"]["gateway"] == "10.5.1.1"

    def test_zone_network_underivable_rejected(self):
        definition = _three_zone_definition()
        definition["zones"]["z-cell"]["network"] = {}
        definition["devices"]["plc2"]["network"]["ipAddress"] = "10.99.1.11"  # different /24
        plan = derive_topology(definition, seed="s")
        assert any(e.code == "ZONE_NETWORK_UNDERIVABLE" for e in plan.errors)

    def test_single_zone_degenerate_no_core(self):
        definition = _three_zone_definition()
        for zid in ("z-sup", "z-ops"):
            del definition["zones"][zid]
        for did in ("hmi1", "hist"):
            del definition["devices"][did]
        del definition["flows"]["f-cross"]
        plan = derive_topology(definition, seed="s")
        assert plan.valid
        assert plan.core is None
        assert any(w.code == "SINGLE_ZONE_DEGENERATE" for w in plan.warnings)

    def test_zone_membership_via_device_ids_list(self):
        definition = _three_zone_definition()
        del definition["devices"]["plc1"]["zoneId"]
        definition["zones"]["z-cell"]["deviceIds"] = ["plc1", "plc2"]
        plan = derive_topology(definition, seed="s")
        assert plan.valid


class TestOverrides:
    def test_default_templates(self):
        plan = derive_topology(_three_zone_definition(), seed="s")
        assert plan.switches["z-cell"]["template_id"] == "cisco/ie3500/8p3s"
        assert plan.core["template_id"] == "cisco/ie9320/26s2c"

    def test_zone_switch_template_override(self):
        definition = _three_zone_definition()
        definition["topology_overrides"] = {"zone_switch_template": "cisco/ie3300/8t2x"}
        plan = derive_topology(definition, seed="s")
        for sw in plan.switches.values():
            assert sw["template_id"] == "cisco/ie3300/8t2x"
            assert "IE3300" in sw["name"]

    def test_per_zone_switch_template_override(self):
        definition = _three_zone_definition()
        definition["topology_overrides"] = {
            "zone_switch_templates": {"z-cell": "cisco/ie4000/16gt4g"}
        }
        plan = derive_topology(definition, seed="s")
        assert plan.switches["z-cell"]["template_id"] == "cisco/ie4000/16gt4g"
        # other zones keep the default
        assert plan.switches["z-sup"]["template_id"] == "cisco/ie3500/8p3s"

    def test_core_template_override(self):
        definition = _three_zone_definition()
        definition["topology_overrides"] = {"core_template": "cisco/ie9310/26s2c"}
        plan = derive_topology(definition, seed="s")
        assert plan.core["template_id"] == "cisco/ie9310/26s2c"
        assert "IE9310" in plan.core["name"]


class TestPlanSegments:
    def test_intra_zone_single_span_true_macs(self):
        definition = _three_zone_definition()
        result = preview(definition, seed="scn-1")
        fp = result["flow_plans"]["f-intra"]
        assert fp["kind"] == "intra"
        assert len(fp["segments_forward"]) == 1
        seg = fp["segments_forward"][0]
        assert seg["span"] == "zone:z-cell"
        assert seg["src_mac"] == "00:0e:8c:11:11:11"
        assert seg["dst_mac"] == "00:0e:8c:22:22:22"
        assert seg["vlan"] is None and seg["ttl_delta"] == 0

    def test_cross_zone_four_segments_gateway_rewritten(self):
        definition = _three_zone_definition()
        plan = derive_topology(definition, seed="scn-1")
        plan = plan_segments(definition, plan)
        fp = plan.flow_plans["f-cross"]
        assert fp["kind"] == "cross"
        fwd = fp["segments_forward"]
        assert [s["span"] for s in fwd] == ["zone:z-sup", CORE_SPAN, CORE_SPAN, "zone:z-cell"]
        svi_sup = plan.core["svis"]["z-sup"]
        svi_cell = plan.core["svis"]["z-cell"]
        # Near side: true source MAC -> source zone SVI, source VLAN, TTL intact
        assert fwd[0]["src_mac"] == "00:0e:8c:33:33:33"
        assert fwd[0]["dst_mac"] == svi_sup["mac"]
        assert fwd[0]["vlan"] == 102 and fwd[0]["ttl_delta"] == 0
        # Far side: target zone SVI -> true target MAC, target VLAN, TTL -1
        assert fwd[3]["src_mac"] == svi_cell["mac"]
        assert fwd[3]["dst_mac"] == "00:0e:8c:11:11:11"
        assert fwd[3]["vlan"] == 101 and fwd[3]["ttl_delta"] == -1
        # Reverse mirrors with roles swapped
        rev = fp["segments_reverse"]
        assert [s["span"] for s in rev] == ["zone:z-cell", CORE_SPAN, CORE_SPAN, "zone:z-sup"]
        assert rev[0]["src_mac"] == "00:0e:8c:11:11:11"
        assert rev[3]["dst_mac"] == "00:0e:8c:33:33:33"
        assert rev[3]["ttl_delta"] == -1

    def test_l2_only_cross_zone_rejected(self):
        definition = _three_zone_definition()
        definition["flows"]["f-goose"] = {
            "id": "f-goose",
            "sourceDeviceId": "hmi1",
            "targetDeviceId": "plc1",
            "protocol": "goose",
        }
        plan = derive_topology(definition, seed="s")
        plan = plan_segments(definition, plan)
        assert any(e.code == "L2_CROSS_ZONE" for e in plan.errors)

    def test_l2_intra_zone_allowed(self):
        definition = _three_zone_definition()
        definition["flows"]["f-pn"] = {
            "id": "f-pn",
            "sourceDeviceId": "plc1",
            "targetDeviceId": "plc2",
            "protocol": "profinet",
        }
        plan = derive_topology(definition, seed="s")
        plan = plan_segments(definition, plan)
        assert plan.valid
        assert plan.flow_plans["f-pn"]["kind"] == "intra"

    def test_missing_mac_flow_skipped_with_warning(self):
        definition = _three_zone_definition()
        definition["devices"]["plc1"]["network"]["macAddress"] = ""
        plan = derive_topology(definition, seed="s")
        plan = plan_segments(definition, plan)
        assert "f-cross" not in plan.flow_plans
        assert any(w.code == "DEVICE_MISSING_NET" for w in plan.warnings)

    def test_list_shaped_collections_supported(self):
        definition = _three_zone_definition()
        definition["zones"] = list(definition["zones"].values())
        definition["devices"] = list(definition["devices"].values())
        definition["flows"] = list(definition["flows"].values())
        result = preview(definition, seed="s")
        assert result["valid"]
        assert set(result["flow_plans"]) == {"f-intra", "f-cross"}
