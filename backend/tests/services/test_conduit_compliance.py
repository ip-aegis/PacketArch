# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for conduit compliance validation service."""

import pytest

from app.services.conduit_compliance import (
    PROTOCOL_ALIASES,
    _resolve_protocol,
    _get_device_zone,
    _find_matching_conduit,
    validate_conduit_compliance,
)
from app.schemas.conduit import ComplianceFindingReason


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_definition(
    devices=None, flows=None, zones=None, conduits=None,
) -> dict:
    return {
        "devices": devices or {},
        "flows": flows or {},
        "zones": zones or {},
        "conduits": conduits or {},
    }


def make_conduit(
    cid="c1",
    src_zone="zone_a",
    tgt_zone="zone_b",
    direction="bidirectional",
    protocols=None,
):
    return {
        cid: {
            "id": cid,
            "sourceZoneId": src_zone,
            "targetZoneId": tgt_zone,
            "direction": direction,
            "allowedProtocols": protocols or ["modbus_tcp"],
        }
    }


# ---------------------------------------------------------------------------
# Protocol alias resolution
# ---------------------------------------------------------------------------

class TestProtocolAliases:
    def test_known_aliases(self):
        assert _resolve_protocol("profisafe") == "profinet"
        assert _resolve_protocol("s7comm_plus") == "s7comm"
        assert _resolve_protocol("cip_safety") == "ethernet_ip"
        assert _resolve_protocol("modbus") == "modbus_tcp"
        assert _resolve_protocol("enip") == "ethernet_ip"
        assert _resolve_protocol("bacnet_ip") == "bacnet"

    def test_unknown_passthrough(self):
        assert _resolve_protocol("modbus_tcp") == "modbus_tcp"
        assert _resolve_protocol("snmp") == "snmp"
        assert _resolve_protocol("custom") == "custom"


# ---------------------------------------------------------------------------
# Device zone lookup
# ---------------------------------------------------------------------------

class TestGetDeviceZone:
    def test_device_with_zone_id(self):
        devices = {"d1": {"zoneId": "zone_a"}}
        assert _get_device_zone("d1", devices, {}) == "zone_a"

    def test_device_zone_from_zone_device_ids(self):
        devices = {"d1": {}}
        zones = {"zone_a": {"deviceIds": ["d1", "d2"]}}
        assert _get_device_zone("d1", devices, zones) == "zone_a"

    def test_device_zone_snake_case_fallback(self):
        devices = {"d1": {"zone_id": "zone_b"}}
        assert _get_device_zone("d1", devices, {}) == "zone_b"

    def test_device_not_found(self):
        assert _get_device_zone("nonexistent", {}, {}) is None

    def test_device_in_no_zone(self):
        devices = {"d1": {}}
        zones = {"zone_a": {"deviceIds": ["d2"]}}
        assert _get_device_zone("d1", devices, zones) is None


# ---------------------------------------------------------------------------
# Conduit matching
# ---------------------------------------------------------------------------

class TestFindMatchingConduit:
    def test_bidirectional_forward(self):
        conduits = make_conduit("c1", "za", "zb", "bidirectional", ["modbus_tcp"])
        cid, reason = _find_matching_conduit("za", "zb", "modbus_tcp", conduits)
        assert cid == "c1"
        assert reason is None  # compliant

    def test_bidirectional_reverse(self):
        conduits = make_conduit("c1", "za", "zb", "bidirectional", ["modbus_tcp"])
        cid, reason = _find_matching_conduit("zb", "za", "modbus_tcp", conduits)
        assert cid == "c1"
        assert reason is None

    def test_a_to_b_forward(self):
        conduits = make_conduit("c1", "za", "zb", "a_to_b", ["modbus_tcp"])
        cid, reason = _find_matching_conduit("za", "zb", "modbus_tcp", conduits)
        assert cid == "c1"
        assert reason is None

    def test_a_to_b_reverse_blocked(self):
        conduits = make_conduit("c1", "za", "zb", "a_to_b", ["modbus_tcp"])
        cid, reason = _find_matching_conduit("zb", "za", "modbus_tcp", conduits)
        assert cid == "c1"
        assert reason == ComplianceFindingReason.WRONG_DIRECTION

    def test_b_to_a_forward_blocked(self):
        conduits = make_conduit("c1", "za", "zb", "b_to_a", ["modbus_tcp"])
        cid, reason = _find_matching_conduit("za", "zb", "modbus_tcp", conduits)
        assert cid == "c1"
        assert reason == ComplianceFindingReason.WRONG_DIRECTION

    def test_b_to_a_reverse_allowed(self):
        conduits = make_conduit("c1", "za", "zb", "b_to_a", ["modbus_tcp"])
        cid, reason = _find_matching_conduit("zb", "za", "modbus_tcp", conduits)
        assert cid == "c1"
        assert reason is None

    def test_protocol_not_allowed(self):
        conduits = make_conduit("c1", "za", "zb", "bidirectional", ["modbus_tcp"])
        cid, reason = _find_matching_conduit("za", "zb", "ethernet_ip", conduits)
        assert cid == "c1"
        assert reason == ComplianceFindingReason.PROTOCOL_NOT_ALLOWED

    def test_protocol_alias_resolution(self):
        """profisafe resolves to profinet in allowed list."""
        conduits = make_conduit("c1", "za", "zb", "bidirectional", ["profinet"])
        cid, reason = _find_matching_conduit("za", "zb", "profisafe", conduits)
        assert cid == "c1"
        assert reason is None

    def test_protocol_alias_in_allowed_list(self):
        """Variant in allowed list matches parent in flow."""
        conduits = make_conduit("c1", "za", "zb", "bidirectional", ["profisafe"])
        cid, reason = _find_matching_conduit("za", "zb", "profinet", conduits)
        assert cid == "c1"
        assert reason is None

    def test_no_conduit_found(self):
        conduits = make_conduit("c1", "za", "zb", "bidirectional", ["modbus_tcp"])
        cid, reason = _find_matching_conduit("za", "zc", "modbus_tcp", conduits)
        assert cid is None
        assert reason == ComplianceFindingReason.NO_CONDUIT

    def test_empty_conduits(self):
        cid, reason = _find_matching_conduit("za", "zb", "modbus_tcp", {})
        assert cid is None
        assert reason == ComplianceFindingReason.NO_CONDUIT


# ---------------------------------------------------------------------------
# Full compliance validation
# ---------------------------------------------------------------------------

class TestValidateConduitCompliance:
    """Integration tests for validate_conduit_compliance()."""

    def _make_scenario(self):
        """Build a minimal scenario with two zones, two devices, one flow."""
        return make_definition(
            devices={
                "d1": {"id": "d1", "zoneId": "zone_ctrl"},
                "d2": {"id": "d2", "zoneId": "zone_field"},
            },
            flows={
                "f1": {
                    "id": "f1",
                    "name": "PLC→IO",
                    "sourceDeviceId": "d1",
                    "targetDeviceId": "d2",
                    "protocol": "modbus_tcp",
                },
            },
            zones={
                "zone_ctrl": {"id": "zone_ctrl", "name": "Control", "level": 2},
                "zone_field": {"id": "zone_field", "name": "Field", "level": 1},
            },
        )

    def test_same_zone_always_compliant(self):
        defn = make_definition(
            devices={
                "d1": {"id": "d1", "zoneId": "zone_a"},
                "d2": {"id": "d2", "zoneId": "zone_a"},
            },
            flows={
                "f1": {
                    "sourceDeviceId": "d1",
                    "targetDeviceId": "d2",
                    "protocol": "modbus_tcp",
                },
            },
            zones={"zone_a": {"id": "zone_a"}},
        )
        result = validate_conduit_compliance(defn)
        assert result.total_flows == 1
        assert result.compliant_flows == 1
        assert result.non_compliant_flows == 0
        assert result.findings == []

    def test_no_zone_info_emits_warning(self):
        """Devices without zone assignments produce a warning finding."""
        defn = make_definition(
            devices={
                "d1": {"id": "d1"},
                "d2": {"id": "d2"},
            },
            flows={
                "f1": {
                    "sourceDeviceId": "d1",
                    "targetDeviceId": "d2",
                    "protocol": "modbus_tcp",
                },
            },
        )
        result = validate_conduit_compliance(defn)
        assert result.compliant_flows == 0
        assert result.non_compliant_flows == 1
        assert result.findings[0].reason == ComplianceFindingReason.NO_CONDUIT
        assert result.findings[0].source_zone_id == "(none)"

    def test_cross_zone_no_conduits(self):
        defn = self._make_scenario()
        # No conduits defined → cross-zone flow is non-compliant
        result = validate_conduit_compliance(defn)
        assert result.total_flows == 1
        assert result.non_compliant_flows == 1
        assert result.findings[0].reason == ComplianceFindingReason.NO_CONDUIT

    def test_cross_zone_with_matching_conduit(self):
        defn = self._make_scenario()
        defn["conduits"] = make_conduit(
            "c1", "zone_ctrl", "zone_field", "bidirectional", ["modbus_tcp"]
        )
        result = validate_conduit_compliance(defn)
        assert result.compliant_flows == 1
        assert result.non_compliant_flows == 0

    def test_cross_zone_wrong_protocol(self):
        defn = self._make_scenario()
        defn["conduits"] = make_conduit(
            "c1", "zone_ctrl", "zone_field", "bidirectional", ["ethernet_ip"]
        )
        result = validate_conduit_compliance(defn)
        assert result.non_compliant_flows == 1
        assert result.findings[0].reason == ComplianceFindingReason.PROTOCOL_NOT_ALLOWED

    def test_cross_zone_wrong_direction(self):
        defn = self._make_scenario()
        # Conduit goes field→ctrl (b_to_a), flow goes ctrl→field (forward)
        defn["conduits"] = make_conduit(
            "c1", "zone_ctrl", "zone_field", "b_to_a", ["modbus_tcp"]
        )
        result = validate_conduit_compliance(defn)
        assert result.non_compliant_flows == 1
        assert result.findings[0].reason == ComplianceFindingReason.WRONG_DIRECTION

    def test_protocol_alias_compliance(self):
        """profisafe flow through profinet conduit is compliant."""
        defn = make_definition(
            devices={
                "d1": {"id": "d1", "zoneId": "zone_a"},
                "d2": {"id": "d2", "zoneId": "zone_b"},
            },
            flows={
                "f1": {
                    "sourceDeviceId": "d1",
                    "targetDeviceId": "d2",
                    "protocol": "profisafe",
                },
            },
            zones={
                "zone_a": {"id": "zone_a"},
                "zone_b": {"id": "zone_b"},
            },
            conduits=make_conduit(
                "c1", "zone_a", "zone_b", "bidirectional", ["profinet"]
            ),
        )
        result = validate_conduit_compliance(defn)
        assert result.compliant_flows == 1
        assert result.non_compliant_flows == 0

    def test_multiple_flows_mixed_compliance(self):
        defn = make_definition(
            devices={
                "d1": {"id": "d1", "zoneId": "zone_a"},
                "d2": {"id": "d2", "zoneId": "zone_b"},
            },
            flows={
                "f_ok": {
                    "sourceDeviceId": "d1",
                    "targetDeviceId": "d2",
                    "protocol": "modbus_tcp",
                },
                "f_bad": {
                    "sourceDeviceId": "d1",
                    "targetDeviceId": "d2",
                    "protocol": "ethernet_ip",
                },
            },
            zones={
                "zone_a": {"id": "zone_a"},
                "zone_b": {"id": "zone_b"},
            },
            conduits=make_conduit(
                "c1", "zone_a", "zone_b", "bidirectional", ["modbus_tcp"]
            ),
        )
        result = validate_conduit_compliance(defn)
        assert result.total_flows == 2
        assert result.compliant_flows == 1
        assert result.non_compliant_flows == 1

    def test_empty_definition(self):
        result = validate_conduit_compliance({})
        assert result.total_flows == 0
        assert result.compliant_flows == 0
        assert result.non_compliant_flows == 0

    def test_device_zone_via_zone_membership(self):
        """Device zone resolved via zone.deviceIds when device has no zoneId."""
        defn = make_definition(
            devices={
                "d1": {"id": "d1"},
                "d2": {"id": "d2"},
            },
            flows={
                "f1": {
                    "sourceDeviceId": "d1",
                    "targetDeviceId": "d2",
                    "protocol": "modbus_tcp",
                },
            },
            zones={
                "zone_a": {"id": "zone_a", "deviceIds": ["d1"]},
                "zone_b": {"id": "zone_b", "deviceIds": ["d2"]},
            },
            conduits=make_conduit(
                "c1", "zone_a", "zone_b", "bidirectional", ["modbus_tcp"]
            ),
        )
        result = validate_conduit_compliance(defn)
        assert result.compliant_flows == 1
        assert result.non_compliant_flows == 0

    def test_finding_has_correct_fields(self):
        defn = self._make_scenario()
        result = validate_conduit_compliance(defn)
        finding = result.findings[0]
        assert finding.flow_id == "f1"
        assert finding.flow_name == "PLC→IO"
        assert finding.protocol == "modbus_tcp"
        assert finding.source_zone_id == "zone_ctrl"
        assert finding.target_zone_id == "zone_field"
