# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Rail scenarios in the transportation vertical + labeled-corpus export wiring."""

import uuid

import pytest

from app.protocol_engines.protocols import resolve_protocol
from app.scenario_templates import VERTICAL_TEMPLATES
from app.services.device_templates._registry import DEVICE_TEMPLATES
from app.traffic_generator.orchestrator import GenerationConfig, TrafficOrchestrator

RAIL_SCENARIOS = ["ptc_freight_corridor", "atcs_signaling_territory"]
TRANSPORT = VERTICAL_TEMPLATES["transportation"]


def test_rail_scenarios_registered():
    for name in RAIL_SCENARIOS:
        assert name in TRANSPORT, f"{name} missing from transportation vertical"
        assert TRANSPORT[name]["vertical"] == "transportation"


@pytest.mark.parametrize("name", RAIL_SCENARIOS)
def test_zones_referenced_exist(name):
    tpl = TRANSPORT[name]
    zone_ids = {z["id"] for z in tpl["zones"]}
    for d in tpl["devices"]:
        assert d["zone"] in zone_ids, f"{name}: device zone {d['zone']} undefined"
    for f in tpl["flows"]:
        for z in f.get("source_zones", []) + f.get("target_zones", []):
            assert z in zone_ids, f"{name}: flow zone {z} undefined"
    for c in tpl["conduits"]:
        assert c["source_zone"] in zone_ids and c["target_zone"] in zone_ids


@pytest.mark.parametrize("name", RAIL_SCENARIOS)
def test_no_orphan_devices(name):
    """Realism dim 3: every device type participates in at least one flow."""
    tpl = TRANSPORT[name]
    in_flows: set[str] = set()
    for f in tpl["flows"]:
        in_flows.update(f.get("source_types", []))
        in_flows.update(f.get("target_types", []))
    for d in tpl["devices"]:
        assert d["type"] in in_flows, f"{name}: orphan device type {d['type']}"


@pytest.mark.parametrize("name", RAIL_SCENARIOS)
def test_cross_zone_flows_have_conduits(name):
    """Realism dim 4: cross-zone traffic is justified by a conduit."""
    tpl = TRANSPORT[name]
    conduits = [
        (c["source_zone"], c["target_zone"], set(c["allowed_protocols"]))
        for c in tpl["conduits"]
    ]
    for f in tpl["flows"]:
        proto = f["protocol"]
        for sz in f.get("source_zones", []):
            for tz in f.get("target_zones", []):
                if sz == tz:
                    continue  # intra-zone is unrestricted
                ok = any(
                    {sz, tz} == {a, b} and proto in allowed
                    for a, b, allowed in conduits
                )
                assert ok, f"{name}: {proto} {sz}->{tz} has no permitting conduit"


@pytest.mark.parametrize("name", RAIL_SCENARIOS)
def test_rail_flows_resolve_to_engines(name):
    """Flow protocols must resolve to a real engine protocol value."""
    from app.protocol_engines import list_supported_protocols
    from app.protocol_engines.types import ProtocolType

    supported = {p.value for p in list_supported_protocols()}
    for f in TRANSPORT[name]["flows"]:
        resolved = resolve_protocol(f["protocol"])
        assert resolved in supported, f"{name}: {f['protocol']} -> {resolved} has no engine"
        ProtocolType(resolved)  # must be a valid enum value


@pytest.mark.parametrize("name", RAIL_SCENARIOS)
def test_rail_devices_match_shipped_templates(name):
    """Each rail device's fingerprint_model + protocols exist in the template library."""
    by_model = {t.model: t for t in DEVICE_TEMPLATES.values()}
    for d in TRANSPORT[name]["devices"]:
        protos = set(d["protocols"])
        if not protos & {"emp", "atcs"}:
            continue  # switches etc. are covered by other vendor modules
        model = d["fingerprint_model"]
        assert model in by_model, f"{name}: no template for model {model}"
        tpl = by_model[model]
        assert protos <= set(tpl.supported_protocols), (
            f"{name}: {model} declares {protos}, template supports {tpl.supported_protocols}"
        )


def test_ptc_uses_emp_and_atcs_uses_atcs():
    ptc_protos = {f["protocol"] for f in TRANSPORT["ptc_freight_corridor"]["flows"]}
    atcs_protos = {f["protocol"] for f in TRANSPORT["atcs_signaling_territory"]["flows"]}
    assert "emp" in ptc_protos and "atcs" not in ptc_protos
    assert "atcs" in atcs_protos and "emp" not in atcs_protos


class TestLabeledCorpusExportWiring:
    """GenerationConfig.export_labeled_corpus -> sidecar file + 'labels' artifact."""

    def _config(self, tmp_path, enabled: bool) -> GenerationConfig:
        return GenerationConfig(
            job_id="job-1",
            scenario_id=uuid.uuid4(),
            total_duration_ms=3000,
            output_path=str(tmp_path / "run.pcap"),
            export_labeled_corpus=enabled,
        )

    def _flow(self):
        from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType

        def dev(i, m, ip, p, n):
            return DeviceContext(device_id=i, mac_address=m, ip_address=ip, port=p, device_name=n)

        return FlowContext(
            flow_id="emp-1",
            source=dev("wiu", "02:00:00:00:00:07", "10.20.0.7", 51000, "Wayside_IU_07"),
            destination=dev("bos", "02:00:00:00:00:01", "10.20.0.1", 3001, "Back_Office_Server_01"),
            protocol=ProtocolType.EMP,
            config={},
            timing_model={"poll_interval_ms": 1000.0},
        )

    def test_enabled_emits_sidecar_and_artifact(self, tmp_path):
        orch = TrafficOrchestrator(self._config(tmp_path, enabled=True))
        orch.add_flow(self._flow())
        result = orch.generate()

        sidecar = tmp_path / "run.labels.jsonl"
        assert sidecar.exists(), "labeled corpus not written"
        assert (tmp_path / "run.labels.meta.json").exists()
        labels = [a for a in (result.artifacts or []) if a["kind"] == "labels"]
        assert len(labels) == 1
        art = labels[0]
        assert art["filename"] == "run.labels.jsonl"
        assert art["packets"] == result.packets_generated
        assert art["labeled_packets"] > 0
        assert art["size_bytes"] > 0

    def test_disabled_by_default(self, tmp_path):
        orch = TrafficOrchestrator(self._config(tmp_path, enabled=False))
        orch.add_flow(self._flow())
        result = orch.generate()
        assert not (tmp_path / "run.labels.jsonl").exists()
        assert not [a for a in (result.artifacts or []) if a["kind"] == "labels"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
