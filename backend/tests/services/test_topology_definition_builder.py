# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for topology switch/core device injection."""

import copy

from app.services import topology_definition_builder as tdb
from app.services.topology_planner import derive_topology, plan_segments, preview


def _def() -> dict:
    return {
        "zones": {
            "z-cell": {"id": "z-cell", "name": "Cell", "level": 1,
                       "network": {"subnet": "10.5.1.0/24", "gateway": "10.5.1.1", "vlan": 101}},
            "z-ops": {"id": "z-ops", "name": "Ops", "level": 3,
                      "network": {"subnet": "10.5.3.0/24", "gateway": "10.5.3.1", "vlan": 103}},
        },
        "devices": {
            "plc1": {"id": "plc1", "zoneId": "z-cell",
                     "network": {"ipAddress": "10.5.1.10", "macAddress": "00:0e:8c:11:11:11"}},
            "hmi1": {"id": "hmi1", "zoneId": "z-ops",
                     "network": {"ipAddress": "10.5.3.10", "macAddress": "00:0e:8c:33:33:33"}},
        },
        "flows": {
            "f1": {"id": "f1", "sourceDeviceId": "hmi1", "targetDeviceId": "plc1", "protocol": "s7comm"},
        },
    }


def test_injects_switch_per_zone_plus_core():
    definition = _def()
    plan = derive_topology(definition, seed="s").as_dict()
    out = tdb.build_topology_definition(definition, plan)
    devs = out["devices"]
    # 2 original + 2 switches + 1 core
    assert len(devs) == 5
    for zid, sw in plan["switches"].items():
        assert sw["id"] in devs
        d = devs[sw["id"]]
        assert d["_topology_synthetic"] is True
        assert d["type"] == "network_switch"
        assert d["network"]["macAddress"] == sw["mac"]
        assert d["zoneId"] == zid
        assert "snmp" in d["protocols"]
    assert plan["core"]["id"] in devs


def test_source_definition_not_mutated():
    definition = _def()
    snapshot = copy.deepcopy(definition)
    plan = derive_topology(definition, seed="s").as_dict()
    tdb.build_topology_definition(definition, plan)
    assert definition == snapshot  # deep copy — original untouched


def test_switches_get_fingerprint_identity():
    definition = _def()
    plan = derive_topology(definition, seed="s").as_dict()
    out = tdb.build_topology_definition(definition, plan)
    sw = out["devices"][plan["switches"]["z-cell"]["id"]]
    # IE3500 template resolves to a fingerprint with SNMP identity
    fp = sw.get("vendorFingerprint")
    assert fp is not None
    assert "snmp_identity" in fp or fp.get("model")


def test_synthetic_devices_replanned_not_double_derived():
    definition = _def()
    plan0 = derive_topology(definition, seed="s").as_dict()
    out = tdb.build_topology_definition(definition, plan0)
    # Re-derive on the augmented definition: still exactly 2 switches + core,
    # synthetic devices are skipped as endpoints (no self-links).
    plan1 = derive_topology(out, seed="s").as_dict()
    assert plan1["valid"]
    assert set(plan1["switches"]) == {"z-cell", "z-ops"}
    self_links = [l for l in plan1["links"] if l["a"] == l["b"]]
    assert not self_links


def test_switch_ip_indexed_for_routing():
    definition = _def()
    plan0 = derive_topology(definition, seed="s").as_dict()
    out = tdb.build_topology_definition(definition, plan0)
    plan1 = preview(out, seed="s")
    sw = plan0["switches"]["z-cell"]
    # switch mgmt IP is in the endpoint index so its frames route to its zone
    assert plan1["endpoint_index"]["ip_to_zone"].get(sw["mgmt_ip"].lower()) == "z-cell"


def test_invalid_plan_is_noop():
    definition = {"zones": {}, "devices": {}, "flows": {}}
    plan = derive_topology(definition, seed="s").as_dict()
    assert not plan["valid"]
    out = tdb.build_topology_definition(definition, plan)
    assert out.get("devices", {}) == {}
