# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""SNMP sysLocation comes from the scenario, not a placeholder.

A 2026-10-22 Cyber Vision replay of the arterial and toll flagships showed
170 of 181 devices reporting sysLocation "Industrial Site" (the ambient
default), and catalog values such as "Plant Operations - NMS" inside a
traffic operations centre.
"""

import uuid
from collections import defaultdict

import pytest
from scapy.all import IP, rdpcap
from scapy.layers.snmp import SNMP, SNMPresponse

from app.protocol_engines.canonical_identity import device_sys_locations
from app.protocol_engines.snmp.engine import SnmpEngine
from app.protocol_engines.snmp.oids import SystemOIDs
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType
from app.services.template_definition_builder import populate_definition_from_template
from app.traffic_generator.orchestrator import GenerationConfig, TrafficOrchestrator
from app.traffic_generator.tasks import _build_flow_contexts

SYS_LOCATION = SystemOIDs.SYS_LOCATION.oid


def _definition(**dev):
    return {
        "devices": {"d1": {"id": "d1", "zoneId": "g", **dev}},
        "zones": [{"id": "g", "name": "ORT Gantry NB (MP 12.4)"}],
        "site_identity": {"plant_name": "TX-130 Toll Plaza"},
    }


def test_location_is_zone_then_site():
    assert device_sys_locations(_definition()) == {"d1": "ORT Gantry NB (MP 12.4), TX-130 Toll Plaza"}


def test_explicit_snmp_config_wins():
    d = _definition(snmp_config={"sys_location": "Cabinet 7, NB shoulder"})
    assert device_sys_locations(d)["d1"] == "Cabinet 7, NB shoulder"


def test_no_zone_and_no_site_leaves_the_device_out():
    assert device_sys_locations({"devices": [{"id": "d1"}]}) == {}


def _sys_location(dest: DeviceContext) -> str:
    src = DeviceContext(device_id="nms", mac_address="00:50:56:00:00:01", ip_address="10.1.1.10", port=50000)
    flow = FlowContext(flow_id="f", source=src, destination=dest, protocol=ProtocolType.SNMP, config={}, timing_model={})
    engine = SnmpEngine()
    return engine._generate_snmp_values(flow, engine.create_initial_state(flow), SYS_LOCATION).value


@pytest.mark.parametrize("ctx_value, fp_value, expected", [
    ("Traffic Management Center, River City TOC", "Plant Operations - NMS", "Traffic Management Center, River City TOC"),
    (None, "Main St & 1st Ave", "Main St & 1st Ave"),
    (None, None, ""),
])
def test_snmp_engine_precedence(ctx_value, fp_value, expected):
    fp = {"snmp_identity": {"sys_location": fp_value}} if fp_value else {}
    dest = DeviceContext(device_id="d", mac_address="00:0e:8c:00:00:02", ip_address="10.1.1.20", port=161,
                         vendor_fingerprint=fp, sys_location=ctx_value)
    assert _sys_location(dest) == expected


@pytest.fixture(scope="module")
def toll_capture(tmp_path_factory):
    d = populate_definition_from_template("transportation", "toll_express_lanes")
    devs = d["devices"].values() if isinstance(d["devices"], dict) else d["devices"]
    expected = device_sys_locations(d)
    by_ip = {v["network"]["ipAddress"]: expected.get(v["id"]) for v in devs}
    out = tmp_path_factory.mktemp("sysloc") / "f4.pcap"
    sid = uuid.uuid4()
    orch = TrafficOrchestrator(GenerationConfig(job_id="t", scenario_id=sid, total_duration_ms=90_000, output_path=out))
    for fc in _build_flow_contexts(d, scenario_id=str(sid), vertical="transportation"):
        orch.add_flow(fc)
    orch.generate()
    return by_ip, rdpcap(str(out))


def test_every_device_reports_its_scenario_location(toll_capture):
    """Template polls and ambient polls agree, and every value is the scenario's."""
    by_ip, pkts = toll_capture
    seen = defaultdict(set)
    for p in pkts:
        if SNMP in p and isinstance(p[SNMP].PDU, SNMPresponse):
            for vb in p[SNMP].PDU.varbindlist:
                if vb.oid.val == SYS_LOCATION:
                    seen[p[IP].src].add(vb.value.val.decode())
    assert len(seen) >= 10
    for ip, values in seen.items():
        assert values == {by_ip[ip]}, (ip, values)
