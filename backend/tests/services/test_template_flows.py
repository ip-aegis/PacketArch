# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Shared template flow expansion: legacy parity, pairing modes, config opt-in."""
import json

import pytest

from app.scenario_templates import VERTICAL_TEMPLATES
from app.services.template_flows import expand_template_flows


def _devices(template):
    devices = {}
    for spec in template.get("devices", []):
        for _ in range(spec.get("count", 1)):
            did = f"device_{len(devices) + 1:03d}"
            devices[did] = {"type": spec.get("type", "plc"), "zoneId": spec.get("zone"), "group": spec.get("group")}
    return devices


def _legacy_round_robin(template, devices):
    """The create route's expansion before it moved to template_flows."""
    flows, index, by_type, by_type_zone = {}, 0, {}, {}
    for did, dev in devices.items():
        by_type.setdefault(dev["type"], []).append(did)
        by_type_zone.setdefault((dev["type"], dev["zoneId"]), []).append(did)
    for spec in template.get("flows", []):
        timing = {"intervalMs": spec.get("interval_ms", 1000)}
        if spec.get("jitter_ms"):
            timing["jitterMs"] = spec["jitter_ms"]
        if spec.get("jitter_type"):
            timing["jitterType"] = spec["jitter_type"]
        for st in spec.get("source_types", []):
            for tt in spec.get("target_types", []):
                srcs = ([d for z in spec["source_zones"] for d in by_type_zone.get((st, z), [])]
                        if spec.get("source_zones") else by_type.get(st, []))
                dsts = ([d for z in spec["target_zones"] for d in by_type_zone.get((tt, z), [])]
                        if spec.get("target_zones") else by_type.get(tt, []))
                if not srcs or not dsts:
                    continue
                for i in range(max(len(srcs), len(dsts))):
                    s, t = srcs[i % len(srcs)], dsts[i % len(dsts)]
                    if s != t:
                        index += 1
                        flow = {"id": f"flow_{index:03d}", "sourceDeviceId": s, "targetDeviceId": t,
                                "protocol": spec.get("protocol"), "timing": timing, "config": {}}
                        if spec.get("auto_repair_skip"):
                            flow["auto_repair_skip"] = True
                        flows[flow["id"]] = flow
    return flows


ALL = [(v, k, t) for v, ts in VERTICAL_TEMPLATES.items() for k, t in ts.items() if t.get("devices")]


@pytest.mark.parametrize("vertical,name,template", ALL, ids=[f"{v}/{k}" for v, k, _ in ALL])
def test_existing_templates_expand_exactly_as_before(vertical, name, template):
    if template.get("honor_flow_config") or any(f.get("pairing") for f in template.get("flows", [])):
        pytest.skip("uses the new flow options")
    devices = _devices(template)
    new = expand_template_flows(template.get("flows", []), devices)
    assert json.dumps(new, sort_keys=True) == json.dumps(_legacy_round_robin(template, devices), sort_keys=True)


def _toy():
    devices = {
        "atms1": {"type": "atms", "zoneId": "tmc"},
        "atms2": {"type": "atms", "zoneId": "tmc"},
        "tc1": {"type": "traffic_controller", "zoneId": "hub", "group": "cab1"},
        "mmu1": {"type": "mmu", "zoneId": "hub", "group": "cab1"},
        "tc2": {"type": "traffic_controller", "zoneId": "hub", "group": "cab2"},
        "mmu2": {"type": "mmu", "zoneId": "hub", "group": "cab2"},
        "tc3": {"type": "traffic_controller", "zoneId": "hub", "group": "cab3"},
    }
    return devices


def _pairs(flows):
    return sorted((f["sourceDeviceId"], f["targetDeviceId"]) for f in flows.values())


def test_fan_out_pairs_every_source_with_every_target():
    flows = expand_template_flows(
        [{"protocol": "snmp", "source_types": ["atms"], "target_types": ["traffic_controller"], "pairing": "fan_out"}],
        _toy(),
    )
    assert _pairs(flows) == sorted((a, t) for a in ("atms1", "atms2") for t in ("tc1", "tc2", "tc3"))


def test_round_robin_splits_redundant_masters():
    flows = expand_template_flows(
        [{"protocol": "snmp", "source_types": ["atms"], "target_types": ["traffic_controller"]}], _toy(),
    )
    assert len(flows) == 3  # each controller polled by exactly one master


def test_same_group_keeps_cabinets_separate():
    flows = expand_template_flows(
        [{"protocol": "snmp", "source_types": ["traffic_controller"], "target_types": ["mmu"], "pairing": "same_group"}],
        _toy(),
    )
    assert _pairs(flows) == [("tc1", "mmu1"), ("tc2", "mmu2")]   # cab3 has no MMU → no flow


def test_flow_config_only_when_template_opts_in():
    spec = [{"protocol": "snmp", "source_types": ["atms"], "target_types": ["traffic_controller"],
             "config": {"ntcip_profile": "config"}}]
    assert all(f["config"] == {} for f in expand_template_flows(spec, _toy()).values())
    honored = expand_template_flows(spec, _toy(), honor_config=True)
    assert all(f["config"] == {"ntcip_profile": "config"} for f in honored.values())
    first, second = list(honored.values())[:2]
    assert first["config"] is not second["config"]


def test_unknown_pairing_is_rejected():
    with pytest.raises(ValueError):
        expand_template_flows(
            [{"protocol": "snmp", "source_types": ["atms"], "target_types": ["mmu"], "pairing": "mesh"}], _toy(),
        )


def _lint(template):
    from scripts.lib.template_lint import lint_template

    return {i.code for i in lint_template("t", template)}


def test_lint_flags_unknown_pairing_and_empty_same_group():
    devices = [{"type": "traffic_controller", "zone": "hub", "protocols": ["snmp"], "group": "cab1"},
               {"type": "mmu", "zone": "hub", "protocols": ["snmp"], "group": "cab2"}]
    flows = [{"protocol": "snmp", "source_types": ["traffic_controller"], "target_types": ["mmu"], "pairing": "mesh"}]
    assert "flow_pairing_unknown" in _lint({"devices": devices, "flows": flows})
    flows[0]["pairing"] = "same_group"
    assert "flow_same_group_empty" in _lint({"devices": devices, "flows": flows})


def test_lint_flags_duplicate_flows_and_unknown_firmware_pins():
    devices = [{"type": "server", "zone": "tmc", "protocols": ["snmp"]},
               {"type": "traffic_controller", "zone": "hub", "protocols": ["snmp"],
                "vendor": "econolite", "fingerprint_model": "Cobalt ATC", "firmware_version": "9.9.9"}]
    flow = {"protocol": "snmp", "source_types": ["server"], "target_types": ["traffic_controller"]}
    codes = _lint({"devices": devices, "flows": [flow, dict(flow)]})
    assert "flow_duplicate" in codes
    assert "device_firmware_no_variant" in codes
