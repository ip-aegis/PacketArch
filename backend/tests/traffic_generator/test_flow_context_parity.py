# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PCAP flow building keeps the scenario's timing and device types.

Before this, ``_build_flow_contexts`` read only ``flow["timing_model"]``,
which saved scenarios never carry (they store ``timing.intervalMs``), so
every PCAP flow polled at the 1 s default while the live agent honoured
the configured rate.
"""
from app.protocol_engines.protocols import flow_timing_model, resolve_protocol
from app.traffic_generator.tasks import _build_flow_contexts


def _scenario() -> dict:
    fp = {"vendor": "Generic", "model": "Test"}
    return {
        "devices": {
            "atms": {"id": "atms", "type": "scada_server", "vendor_fingerprint": fp,
                     "network": {"ipAddress": "10.1.0.10", "macAddress": "02:00:00:00:00:0a"}},
            "tc": {"id": "tc", "type": "traffic_controller", "vendor_fingerprint": fp,
                   "network": {"ipAddress": "10.1.1.10", "macAddress": "02:00:00:00:00:0b"}},
        },
        "zones": {},
        "flows": {
            "poll": {"id": "poll", "sourceDeviceId": "atms", "targetDeviceId": "tc",
                     "protocol": "snmp", "timing": {"intervalMs": 60000, "jitterMs": 200}},
            "alias": {"id": "alias", "sourceDeviceId": "atms", "targetDeviceId": "tc",
                      "protocol": "ntcip", "timing": {"intervalMs": 1000}},
        },
        "conduits": {},
    }


def test_pcap_flows_use_the_scenario_poll_interval():
    by_id = {fc.flow_id: fc for fc in _build_flow_contexts(_scenario())}
    assert by_id["poll"].timing_model["poll_interval_ms"] == 60000
    assert by_id["poll"].timing_model["jitter"]["max_ms"] == 100


def test_explicit_timing_model_still_wins():
    assert flow_timing_model({"timing_model": {"poll_interval_ms": 5}, "timing": {"intervalMs": 9}}) == {
        "poll_interval_ms": 5
    }


def test_device_types_reach_the_engines():
    fc = next(fc for fc in _build_flow_contexts(_scenario()) if fc.flow_id == "poll")
    assert fc.source.device_type == "scada_server"
    assert fc.destination.device_type == "traffic_controller"


def test_ntcip_alias_resolves_to_the_snmp_engine():
    assert resolve_protocol("ntcip") == "snmp"
    ids = {fc.flow_id: fc for fc in _build_flow_contexts(_scenario())}
    assert ids["alias"].protocol.value == "snmp"
    assert ids["alias"].destination.port == 161
