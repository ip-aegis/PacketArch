# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Ambient DNS: only with a real DNS server; answers name real peers."""

import uuid

from scapy.all import DNS, IP, UDP, rdpcap

from app.services.template_definition_builder import populate_definition_from_template
from app.traffic_generator.orchestrator import GenerationConfig, TrafficOrchestrator
from app.traffic_generator.tasks import _build_flow_contexts


def _capture(template: str, tmp_path, strip_dns_server: bool = False):
    d = populate_definition_from_template("transportation", template)
    devs = list(d["devices"].values() if isinstance(d["devices"], dict) else d["devices"])
    if strip_dns_server:
        for v in devs:
            fp = v.get("vendorFingerprint") or {}
            fp["supported_protocols"] = [p for p in fp.get("supported_protocols", []) if p != "dns"]
    ips = {v["network"]["ipAddress"]: v for v in devs}
    out = tmp_path / f"{template}.pcap"
    sid = uuid.uuid4()
    orch = TrafficOrchestrator(GenerationConfig(job_id="t", scenario_id=sid, total_duration_ms=40_000, output_path=out))
    for fc in _build_flow_contexts(d, scenario_id=str(sid), vertical="transportation"):
        orch.add_flow(fc)
    orch.generate()
    return d, ips, [p for p in rdpcap(str(out)) if DNS in p and UDP in p]


def test_dns_answers_resolve_real_peers_in_the_site_domain(tmp_path):
    d, ips, pkts = _capture("toll_express_lanes", tmp_path)
    domain = (d.get("site_identity") or {}).get("domain_suffix")
    answers = [p for p in pkts if p[DNS].qr == 1 and p[DNS].ancount]
    assert answers
    server_ips = {p[IP].src for p in answers}
    assert len(server_ips) == 1 and ips[server_ips.pop()]["type"] == "domain_controller"
    for p in answers:
        rr = p[DNS].an
        if rr.type == 1:   # A
            assert rr.rdata in ips
            if domain:
                assert rr.rrname.decode().rstrip(".").endswith(domain)
    assert all(ips[p[IP].src]["type"] not in {"toll_controller", "toll_rsu", "anpr_camera", "network_switch"}
               for p in pkts if p[DNS].qr == 0)


def test_no_dns_without_a_dns_server(tmp_path):
    _, _, pkts = _capture("toll_express_lanes", tmp_path, strip_dns_server=True)
    assert not pkts
