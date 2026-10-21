# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""repair_flow_protocols: when a generic protocol is promoted, and when not."""

from __future__ import annotations

from app.services.scenario_enrichment import repair_flow_protocols


def _definition(src_protocols: list[str], tgt_protocols: list[str], protocol: str) -> dict:
    def dev(i: str, protos: list[str]) -> dict:
        return {"id": i, "name": i, "type": "server",
                "vendorFingerprint": {"vendor": "Test", "model": f"m-{i}",
                                      "supported_protocols": protos}}
    return {
        "devices": {"a": dev("a", src_protocols), "b": dev("b", tgt_protocols)},
        "flows": [{"id": "f", "sourceDeviceId": "a", "targetDeviceId": "b", "protocol": protocol}],
    }


def _protocol(defn: dict) -> str:
    return defn["flows"][0]["protocol"]


def test_snmp_poll_is_not_promoted_to_an_it_management_shape():
    # An NMS (or an ATMS polling NTCIP) that also has a web UI must keep SNMP.
    out = repair_flow_protocols(_definition(["snmp", "https", "rdp"], ["snmp", "https", "ssh"], "snmp"))
    assert _protocol(out) == "snmp"


def test_snmp_is_still_promoted_when_an_industrial_protocol_is_shared():
    out = repair_flow_protocols(_definition(["snmp", "modbus_tcp"], ["snmp", "modbus_tcp"], "snmp"))
    assert _protocol(out) == "modbus_tcp"


def test_snmp_poll_is_not_promoted_to_syslog():
    out = repair_flow_protocols(_definition(["snmp", "https", "syslog"], ["snmp", "https", "syslog"], "snmp"))
    assert _protocol(out) == "snmp"
