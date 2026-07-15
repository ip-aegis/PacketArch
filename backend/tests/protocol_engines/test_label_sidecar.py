# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Labeled-corpus sidecar — end-to-end alignment with the emitted pcap.

The sidecar is the deliverable that makes a run usable as dissector-training
data, so the load-bearing property is that record ``pkt: N`` really describes
pcap packet N, and that each field's offset lands on the bytes it claims.
Verified here against a real orchestrator run carrying both encodings:
EMP (binary L7) and ATCS (ASCII-hex relay feed).
"""

import json

import pytest
from scapy.utils import rdpcap

from app.protocol_engines.label_sidecar import LabelSidecarWriter, extract_label_fields
from app.protocol_engines.output import PcapOutput
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator


def _dev(did, mac, ip, port, name):
    return DeviceContext(device_id=did, mac_address=mac, ip_address=ip, port=port, device_name=name)


def _run(tmp_path):
    """Run a short EMP + ATCS orchestration, returning (pcap_path, sidecar_path, result)."""
    pcap_path = tmp_path / "corpus.pcap"
    sidecar_path = tmp_path / "corpus.labels.jsonl"

    emp = FlowContext(
        flow_id="emp-1",
        source=_dev("wiu-7", "02:00:00:00:00:07", "10.20.0.7", 51000, "Wayside_IU_07"),
        destination=_dev("bos-1", "02:00:00:00:00:01", "10.20.0.1", 5361, "Back_Office_Server_01"),
        protocol=ProtocolType.EMP,
        config={"railroad": "bnsf"},
        timing_model={"poll_interval_ms": 1000.0},
    )
    atcs = FlowContext(
        flow_id="atcs-1",
        source=_dev("mon-1", "02:00:00:00:0a:01", "10.30.0.9", 51001, "ATCS_Monitor_01"),
        destination=_dev("relay-1", "02:00:00:00:0a:02", "10.30.0.2", 4802, "ATCS_Relay_01"),
        protocol=ProtocolType.ATCS,
        config={"railroad_num": 125, "codeline_num": 323},
        timing_model={"poll_interval_ms": 1000.0},
    )

    orch = UnifiedOrchestrator(output=PcapOutput(str(pcap_path)), duration_ms=5000)
    orch.set_label_sink(LabelSidecarWriter(sidecar_path))
    orch.add_flow(emp)
    orch.add_flow(atcs)
    result = orch.run()
    return pcap_path, sidecar_path, result


def _records(sidecar_path):
    return [json.loads(line) for line in sidecar_path.read_text().splitlines() if line.strip()]


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    return _run(tmp_path_factory.mktemp("corpus"))


def test_sidecar_aligns_1to1_with_pcap(corpus):
    pcap_path, sidecar_path, result = corpus
    packets = rdpcap(str(pcap_path))
    records = _records(sidecar_path)
    assert len(records) == len(packets), "sidecar/pcap packet count mismatch"
    assert len(records) == result.packets_generated
    # indices are dense and ordered
    assert [r["pkt"] for r in records] == list(range(len(records)))
    # timestamps are non-decreasing
    ts = [r["ts_ms"] for r in records]
    assert ts == sorted(ts)


def test_labeled_field_offsets_land_on_real_bytes(corpus):
    """The core guarantee: each field's offset addresses the bytes it claims."""
    pcap_path, sidecar_path, _ = corpus
    packets = rdpcap(str(pcap_path))
    records = _records(sidecar_path)

    checked_binary = checked_hex = 0
    for rec in records:
        fields = rec.get("fields")
        if not fields:
            continue
        raw = bytes(packets[rec["pkt"]])
        l7 = rec["l7_offset"]
        if rec["encoding"] == "binary":
            # EMP: packet byte at l7_offset+off
            for f in fields:
                assert l7 + f["off"] + f["len"] <= len(raw), f"{f['field']} out of bounds"
            ver = next(f for f in fields if f["field"] == "emp.version")
            assert raw[l7 + ver["off"]] == 4          # EMP v4 marker really there
            checked_binary += 1
        elif rec["encoding"] == "ascii_hex":
            # ATCS: L7 payload is hex text; fields index the DECODED frame
            frame = bytes.fromhex(raw[l7:].decode("ascii").strip())
            for f in fields:
                assert f["off"] + f["len"] <= len(frame), f"{f['field']} out of bounds"
            fc = next(f for f in fields if f["field"] == "atcs.frame_counter")
            assert frame[fc["off"]] == f_value(fc)     # frame counter really there
            checked_hex += 1
    assert checked_binary > 0, "no EMP-labeled packets checked"
    assert checked_hex > 0, "no ATCS-labeled packets checked"


def f_value(field):
    v = field["value"]
    return v if isinstance(v, int) else int(v)


def test_both_protocols_and_encodings_present(corpus):
    _, sidecar_path, _ = corpus
    records = _records(sidecar_path)
    protos = {r["protocol"] for r in records}
    assert {"emp", "atcs"} <= protos
    encodings = {r["encoding"] for r in records if r.get("fields")}
    assert {"binary", "ascii_hex"} == encodings


def test_unlabeled_packets_still_recorded(corpus):
    """TCP handshake packets carry no field map but must keep index alignment."""
    _, sidecar_path, _ = corpus
    records = _records(sidecar_path)
    bare = [r for r in records if not r.get("fields")]
    assert bare, "expected TCP control packets without field maps"
    assert all(r["type"] for r in bare)


def test_meta_summary(corpus):
    _, sidecar_path, _ = corpus
    meta = json.loads(sidecar_path.with_suffix(".meta.json").read_text())
    records = _records(sidecar_path)
    assert meta["schema_version"] == 1
    assert meta["packet_count"] == len(records)
    assert meta["labeled_count"] == len([r for r in records if r.get("fields")])
    vocab = meta["field_vocabulary"]
    assert any(v.startswith("emp.") for v in vocab)
    assert any(v.startswith("atcs.") for v in vocab)


def test_extract_label_fields_prefers_known_keys():
    assert extract_label_fields({"emp_fields": [{"a": 1}]}) == [{"a": 1}]
    assert extract_label_fields({"codeline_fields": [{"b": 2}]}) == [{"b": 2}]
    assert extract_label_fields({"type": "tcp_syn"}) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
