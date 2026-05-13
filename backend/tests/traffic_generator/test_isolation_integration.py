# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""End-to-end check that the cell-isolation gate filters flows when
``_build_flow_contexts`` runs over a real scenario definition.

This is intentionally narrow: it verifies the integration point between
the orchestrator's flow ingestion and the cell_isolation module, not
the protocol engines themselves.
"""

import pytest

from app.traffic_generator.tasks import _build_flow_contexts


def _two_cell_scenario(mode: str | None) -> dict:
    """Two L1 cells (cell_a, cell_b), one L3 historian zone, three flows:
       - east-west: plc_a → plc_b   (cell_a → cell_b, blocked by strict)
       - northbound: plc_a → historian (cell_a → operations, allowed)
       - intra-cell: plc_a_io → plc_a (same zone, always allowed)
    """
    cell_isolation = {"mode": mode} if mode else None
    fingerprint = {"vendor": "Generic", "model": "Test"}
    definition = {
        "devices": {
            "plc_a": {"id": "plc_a", "vendor_fingerprint": fingerprint,
                      "network": {"ipAddress": "10.1.0.10", "macAddress": "02:00:00:00:00:0a"}},
            "plc_a_io": {"id": "plc_a_io", "vendor_fingerprint": fingerprint,
                         "network": {"ipAddress": "10.1.0.11", "macAddress": "02:00:00:00:00:0b"}},
            "plc_b": {"id": "plc_b", "vendor_fingerprint": fingerprint,
                      "network": {"ipAddress": "10.1.1.10", "macAddress": "02:00:00:00:00:0c"}},
            "historian": {"id": "historian", "vendor_fingerprint": fingerprint,
                          "network": {"ipAddress": "10.1.2.10", "macAddress": "02:00:00:00:00:0d"}},
        },
        "zones": {
            "cell_a": {"id": "cell_a", "level": 1, "deviceIds": ["plc_a", "plc_a_io"]},
            "cell_b": {"id": "cell_b", "level": 1, "deviceIds": ["plc_b"]},
            "operations": {"id": "operations", "level": 3, "deviceIds": ["historian"]},
        },
        "flows": {
            "east_west": {"id": "east_west", "sourceDeviceId": "plc_a",
                          "targetDeviceId": "plc_b", "protocol": "modbus_tcp"},
            "northbound": {"id": "northbound", "sourceDeviceId": "plc_a",
                           "targetDeviceId": "historian", "protocol": "modbus_tcp"},
            "intra_cell": {"id": "intra_cell", "sourceDeviceId": "plc_a_io",
                           "targetDeviceId": "plc_a", "protocol": "modbus_tcp"},
        },
        "conduits": {},
    }
    if cell_isolation:
        definition["cell_isolation"] = cell_isolation
    return definition


def _flow_ids(flow_contexts) -> set[str]:
    return {fc.flow_id for fc in flow_contexts}


class TestFlowGateIntegration:

    def test_off_mode_keeps_every_flow(self):
        contexts = _build_flow_contexts(_two_cell_scenario(None))
        assert _flow_ids(contexts) == {"east_west", "northbound", "intra_cell"}

    def test_strict_mode_drops_only_east_west(self):
        contexts = _build_flow_contexts(_two_cell_scenario("strict_northbound"))
        ids = _flow_ids(contexts)
        assert "east_west" not in ids
        assert "northbound" in ids
        assert "intra_cell" in ids

    def test_conduit_gated_drops_uncovered_east_west(self):
        contexts = _build_flow_contexts(_two_cell_scenario("conduit_gated"))
        ids = _flow_ids(contexts)
        assert "east_west" not in ids
        assert "northbound" in ids

    def test_conduit_gated_keeps_east_west_with_permitting_conduit(self):
        definition = _two_cell_scenario("conduit_gated")
        definition["conduits"] = {
            "ew_conduit": {
                "id": "ew_conduit",
                "sourceZoneId": "cell_a",
                "targetZoneId": "cell_b",
                "direction": "bidirectional",
                "allowedProtocols": ["modbus_tcp"],
            }
        }
        contexts = _build_flow_contexts(definition)
        assert "east_west" in _flow_ids(contexts)
