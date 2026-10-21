# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Ambient discovery polls come from real managers on the PCAP path.

Cyber Vision tags any host that sends SNMP GETs as a network-management
server and any host answering NTP as a time server. In a 2026-10 replay of
the metro arterial flagship, ambient discovery made signal controllers poll
the ATMS and answer its NTP queries, because the PCAP path built ambient
devices with no zone, level or scenario type (the live agent passes all
three).
"""

import uuid

import pytest
from scapy.all import IP, UDP, rdpcap
from scapy.layers.snmp import SNMP, SNMPget

from app.services.template_definition_builder import populate_definition_from_template
from app.traffic_generator.orchestrator import GenerationConfig, TrafficOrchestrator
from app.traffic_generator.tasks import _build_flow_contexts

FIELD_TYPES = {"traffic_controller", "radar_detector", "network_switch", "camera", "ptz_camera", "cellular_router"}


@pytest.fixture(scope="module")
def capture(tmp_path_factory):
    d = populate_definition_from_template("transportation", "metro_arterial_signal_system")
    devs = d["devices"].values() if isinstance(d["devices"], dict) else d["devices"]
    types = {v["network"]["ipAddress"]: v["type"] for v in devs}
    out = tmp_path_factory.mktemp("ambient") / "f1.pcap"
    sid = uuid.uuid4()
    orch = TrafficOrchestrator(GenerationConfig(job_id="t", scenario_id=sid, total_duration_ms=30_000, output_path=out))
    for fc in _build_flow_contexts(d, scenario_id=str(sid), vertical="transportation"):
        orch.add_flow(fc)
    orch.generate()
    return types, rdpcap(str(out))


def test_field_devices_never_poll_over_snmp(capture):
    types, pkts = capture
    pollers = {types.get(p[IP].src) for p in pkts if SNMP in p and isinstance(p[SNMP].PDU, SNMPget)}
    assert pollers and not pollers & FIELD_TYPES, pollers


def test_field_devices_are_never_asked_for_the_time(capture):
    types, pkts = capture
    ntp_servers = {types.get(p[IP].dst) for p in pkts if UDP in p and p[UDP].dport == 123}
    assert not ntp_servers & FIELD_TYPES, ntp_servers
