# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Labeled-corpus sidecar writer.

PacketArch's PCAP writer emits classic pcap with no per-packet annotation
channel, and ``PacketEvent.metadata`` (which carries per-field ground-truth
label maps for protocols that populate them — e.g. EMP and ATCS) is otherwise
discarded. This module persists that metadata as a JSON-Lines sidecar keyed to
packet index, so a run produces BOTH a pcap and a machine-readable ground-truth
file suitable for training/validating a deep-packet-inspection dissector.

The sidecar aligns 1:1 with the primary (combined) pcap: record ``pkt: N`` is
the Nth packet written to that pcap. The orchestrator calls :meth:`write` only
for packets it successfully wrote, so indices stay in lockstep.

Record schema (one compact JSON object per line)::

    {"pkt": 0, "ts_ms": 0.0, "flow_id": "f1", "protocol": "emp",
     "type": "emp_wiu_status", "l7_offset": 54, "encoding": "binary",
     "fields": [{"off": 0, "len": 1, "field": "emp.version", "value": 4,
                 "synthetic": false}, ...]}

Field offsets are relative to the decoded L7 protocol unit. ``l7_offset`` is
where that unit begins in the packet, and ``encoding`` says how to reach a
field's bytes:

- ``binary``   — packet byte for field offset ``off`` is at ``l7_offset + off``.
- ``ascii_hex`` — the L7 payload is ASCII-hex text (e.g. the ATCS Monitor relay
  feed); the field's bytes are the 2 hex chars per byte starting at
  ``l7_offset + 2*off``. ``off``/``len`` index the DECODED binary frame.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Metadata keys, in priority order, under which an engine may publish its
# per-field ground-truth label map.
_FIELD_KEYS = ("label_fields", "emp_fields", "codeline_fields")


def extract_label_fields(metadata: dict[str, Any]) -> list[dict] | None:
    """Return the per-field label map from a PacketEvent's metadata, or None."""
    for key in _FIELD_KEYS:
        fields = metadata.get(key)
        if fields:
            return fields
    return None


class LabelSidecarWriter:
    """Write a per-packet ground-truth JSONL sidecar next to a pcap.

    Attach to :class:`UnifiedOrchestrator` via ``set_label_sink``; it is fed
    each successfully-written packet's event in pcap order.
    """

    SCHEMA_VERSION = 1

    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.output_path.open("w", encoding="utf-8")
        self.packet_count = 0
        self.labeled_count = 0          # packets that carried a field map
        self._protocol_counts: dict[str, int] = {}
        self._field_vocab: set[str] = set()

    def write(self, event: Any, timestamp_ms: float) -> None:
        """Serialize one packet's ground truth. ``event`` is a PacketEvent."""
        md = event.metadata or {}
        protocol = md.get("protocol", "unknown")
        fields = extract_label_fields(md)

        record: dict[str, Any] = {
            "pkt": self.packet_count,
            "ts_ms": round(timestamp_ms, 3),
            "flow_id": event.flow_id,
            "protocol": protocol,
            "type": md.get("type"),
        }
        if "l7_offset" in md:
            record["l7_offset"] = md["l7_offset"]
        record["encoding"] = md.get("encoding", "binary")
        if fields:
            record["fields"] = fields
            self.labeled_count += 1
            for f in fields:
                self._field_vocab.add(f.get("field", ""))

        self._fh.write(json.dumps(record, separators=(",", ":"), default=str))
        self._fh.write("\n")
        self.packet_count += 1
        self._protocol_counts[protocol] = self._protocol_counts.get(protocol, 0) + 1

    def close(self) -> None:
        """Flush the JSONL and write a companion ``.meta.json`` summary."""
        if self._fh.closed:
            return
        self._fh.close()
        summary = {
            "schema_version": self.SCHEMA_VERSION,
            "sidecar": self.output_path.name,
            "packet_count": self.packet_count,
            "labeled_count": self.labeled_count,
            "protocol_counts": dict(sorted(self._protocol_counts.items())),
            "field_vocabulary": sorted(v for v in self._field_vocab if v),
        }
        meta_path = self.output_path.with_suffix(".meta.json")
        meta_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
