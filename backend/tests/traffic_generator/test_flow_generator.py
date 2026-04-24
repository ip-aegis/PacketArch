# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for Smart Flow Generator."""

import pytest

from app.traffic_generator.flow_generator import (
    DeviceRole,
    DeviceSpec,
    FlowPattern,
    GeneratedFlow,
    ROLE_CONNECTIONS,
    SmartFlowGenerator,
    generate_flows_for_scenario,
)


class TestDeviceRole:
    """Tests for DeviceRole enum."""

    def test_all_roles_defined(self):
        """Test all expected roles are defined."""
        expected = {
            "scada", "hmi", "controller", "field_device",
            "gateway", "historian", "engineering", "safety"
        }
        actual = {r.value for r in DeviceRole}
        assert expected == actual


class TestDeviceSpec:
    """Tests for DeviceSpec dataclass."""

    def test_from_dict_basic(self):
        """Test creating DeviceSpec from dictionary."""
        data = {
            "device_id": "plc-001",
            "role": "controller",
            "ip_address": "192.168.1.100",
            "mac_address": "00:11:22:33:44:55",
            "vendor": "Siemens",
        }

        spec = DeviceSpec.from_dict(data)

        assert spec.device_id == "plc-001"
        assert spec.role == DeviceRole.CONTROLLER
        assert spec.ip_address == "192.168.1.100"
        assert spec.vendor == "Siemens"

    def test_from_dict_role_inference(self):
        """Test role inference from device type."""
        # PLC should be controller
        plc_data = {"device_id": "1", "device_type": "plc", "ip_address": "1.1.1.1"}
        plc_spec = DeviceSpec.from_dict(plc_data)
        assert plc_spec.role == DeviceRole.CONTROLLER

        # HMI should be HMI
        hmi_data = {"device_id": "2", "device_type": "hmi", "ip_address": "1.1.1.2"}
        hmi_spec = DeviceSpec.from_dict(hmi_data)
        assert hmi_spec.role == DeviceRole.HMI

        # SCADA should be SCADA
        scada_data = {"device_id": "3", "device_type": "scada", "ip_address": "1.1.1.3"}
        scada_spec = DeviceSpec.from_dict(scada_data)
        assert scada_spec.role == DeviceRole.SCADA

        # Unknown should be field device
        unknown_data = {"device_id": "4", "device_type": "sensor", "ip_address": "1.1.1.4"}
        unknown_spec = DeviceSpec.from_dict(unknown_data)
        assert unknown_spec.role == DeviceRole.FIELD_DEVICE

    def test_from_dict_case_insensitive_role(self):
        """Test role parsing is case-insensitive."""
        data = {"device_id": "1", "role": "CONTROLLER", "ip_address": "1.1.1.1"}
        spec = DeviceSpec.from_dict(data)
        assert spec.role == DeviceRole.CONTROLLER


class TestGeneratedFlow:
    """Tests for GeneratedFlow dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        source = DeviceSpec(
            device_id="src-001",
            role=DeviceRole.CONTROLLER,
            ip_address="192.168.1.10",
        )
        dest = DeviceSpec(
            device_id="dst-001",
            role=DeviceRole.FIELD_DEVICE,
            ip_address="192.168.1.20",
        )

        flow = GeneratedFlow(
            flow_id="flow_001",
            source=source,
            destination=dest,
            protocol="modbus_tcp",
            poll_rate=60.0,
            priority=8,
        )

        result = flow.to_dict()

        assert result["flow_id"] == "flow_001"
        assert result["source_id"] == "src-001"
        assert result["destination_id"] == "dst-001"
        assert result["protocol"] == "modbus_tcp"
        assert result["poll_rate"] == 60.0
        assert result["priority"] == 8


class TestSmartFlowGenerator:
    """Tests for SmartFlowGenerator."""

    def test_init_defaults(self):
        """Test default initialization."""
        gen = SmartFlowGenerator()
        assert gen.min_flows_per_device == 1
        assert gen.max_flows_per_device == 20
        assert gen.default_protocol == "modbus_tcp"

    def test_empty_devices(self):
        """Test with empty device list."""
        gen = SmartFlowGenerator()
        flows = gen.generate_flows([], FlowPattern.REALISTIC)
        assert flows == []

    def test_single_device(self):
        """Test with single device."""
        gen = SmartFlowGenerator()
        devices = [
            DeviceSpec("plc-001", DeviceRole.CONTROLLER, "192.168.1.100")
        ]
        flows = gen.generate_flows(devices, FlowPattern.REALISTIC)
        # Single device can't have flows to itself
        assert len(flows) == 0

    def test_hierarchical_pattern(self):
        """Test hierarchical flow pattern."""
        gen = SmartFlowGenerator()
        devices = [
            DeviceSpec("scada-001", DeviceRole.SCADA, "192.168.1.10"),
            DeviceSpec("plc-001", DeviceRole.CONTROLLER, "192.168.1.20"),
            DeviceSpec("io-001", DeviceRole.FIELD_DEVICE, "192.168.1.30"),
        ]

        flows = gen.generate_flows(devices, FlowPattern.HIERARCHICAL)

        assert len(flows) > 0
        # Should have SCADA -> Controller and Controller -> Field Device
        flow_pairs = [(f.source.role, f.destination.role) for f in flows]
        assert (DeviceRole.SCADA, DeviceRole.CONTROLLER) in flow_pairs or \
               (DeviceRole.CONTROLLER, DeviceRole.FIELD_DEVICE) in flow_pairs

    def test_mesh_pattern(self):
        """Test mesh flow pattern (all-to-all)."""
        gen = SmartFlowGenerator()
        devices = [
            DeviceSpec("d1", DeviceRole.CONTROLLER, "192.168.1.1"),
            DeviceSpec("d2", DeviceRole.CONTROLLER, "192.168.1.2"),
            DeviceSpec("d3", DeviceRole.CONTROLLER, "192.168.1.3"),
        ]

        flows = gen.generate_flows(devices, FlowPattern.MESH)

        # 3 devices, each connects to 2 others = 6 flows
        assert len(flows) == 6

    def test_star_pattern(self):
        """Test star topology pattern."""
        gen = SmartFlowGenerator()
        devices = [
            DeviceSpec("scada-001", DeviceRole.SCADA, "192.168.1.10"),
            DeviceSpec("plc-001", DeviceRole.CONTROLLER, "192.168.1.20"),
            DeviceSpec("plc-002", DeviceRole.CONTROLLER, "192.168.1.21"),
            DeviceSpec("io-001", DeviceRole.FIELD_DEVICE, "192.168.1.30"),
        ]

        flows = gen.generate_flows(devices, FlowPattern.STAR)

        # Central (SCADA) connects to all others = 3 flows
        assert len(flows) == 3
        # All flows should originate from SCADA
        assert all(f.source.role == DeviceRole.SCADA for f in flows)

    def test_realistic_pattern(self):
        """Test realistic OT pattern."""
        gen = SmartFlowGenerator()
        devices = [
            DeviceSpec("scada-001", DeviceRole.SCADA, "192.168.1.10"),
            DeviceSpec("hmi-001", DeviceRole.HMI, "192.168.1.11"),
            DeviceSpec("plc-001", DeviceRole.CONTROLLER, "192.168.1.20"),
            DeviceSpec("plc-002", DeviceRole.CONTROLLER, "192.168.1.21"),
            DeviceSpec("io-001", DeviceRole.FIELD_DEVICE, "192.168.1.30"),
            DeviceSpec("io-002", DeviceRole.FIELD_DEVICE, "192.168.1.31"),
        ]

        flows = gen.generate_flows(devices, FlowPattern.REALISTIC)

        assert len(flows) > 0

        # Field devices should only be destinations, not sources
        for flow in flows:
            if flow.source.role == DeviceRole.FIELD_DEVICE:
                pytest.fail("Field device should not initiate flows")

    def test_all_devices_participate(self):
        """Test that all devices participate in at least one flow."""
        gen = SmartFlowGenerator(min_flows_per_device=1)
        devices = [
            DeviceSpec("scada-001", DeviceRole.SCADA, "192.168.1.10"),
            DeviceSpec("plc-001", DeviceRole.CONTROLLER, "192.168.1.20"),
            DeviceSpec("io-001", DeviceRole.FIELD_DEVICE, "192.168.1.30"),
            DeviceSpec("io-002", DeviceRole.FIELD_DEVICE, "192.168.1.31"),
            DeviceSpec("io-003", DeviceRole.FIELD_DEVICE, "192.168.1.32"),
        ]

        flows = gen.generate_flows(devices, FlowPattern.REALISTIC)

        # Collect participating devices
        participants = set()
        for flow in flows:
            participants.add(flow.source.device_id)
            participants.add(flow.destination.device_id)

        # All devices should participate
        all_device_ids = {d.device_id for d in devices}
        assert participants == all_device_ids

    def test_protocol_selection(self):
        """Test protocol selection based on device capabilities."""
        gen = SmartFlowGenerator()
        devices = [
            DeviceSpec(
                "plc-001", DeviceRole.CONTROLLER, "192.168.1.20",
                protocols=["modbus_tcp", "ethernet_ip"]
            ),
            DeviceSpec(
                "io-001", DeviceRole.FIELD_DEVICE, "192.168.1.30",
                protocols=["modbus_tcp"]
            ),
        ]

        flows = gen.generate_flows(devices, FlowPattern.REALISTIC)

        # Should select modbus_tcp (common protocol)
        if flows:
            assert flows[0].protocol == "modbus_tcp"

    def test_priority_calculation(self):
        """Test flow priority based on roles."""
        gen = SmartFlowGenerator()
        devices = [
            DeviceSpec("safety-001", DeviceRole.SAFETY, "192.168.1.10"),
            DeviceSpec("plc-001", DeviceRole.CONTROLLER, "192.168.1.20"),
            DeviceSpec("io-001", DeviceRole.FIELD_DEVICE, "192.168.1.30"),
        ]

        flows = gen.generate_flows(devices, FlowPattern.REALISTIC)

        # Safety flows should have highest priority
        safety_flows = [f for f in flows if f.source.role == DeviceRole.SAFETY
                        or f.destination.role == DeviceRole.SAFETY]
        if safety_flows:
            assert all(f.priority == 10 for f in safety_flows)


class TestRoleConnections:
    """Tests for role connection definitions."""

    def test_field_devices_dont_initiate(self):
        """Test that field devices don't initiate connections."""
        assert ROLE_CONNECTIONS[DeviceRole.FIELD_DEVICE] == []

    def test_scada_connects_to_controllers(self):
        """Test SCADA can connect to controllers."""
        assert DeviceRole.CONTROLLER in ROLE_CONNECTIONS[DeviceRole.SCADA]

    def test_controller_connects_to_field_devices(self):
        """Test controllers can connect to field devices."""
        assert DeviceRole.FIELD_DEVICE in ROLE_CONNECTIONS[DeviceRole.CONTROLLER]


class TestConvenienceFunction:
    """Tests for generate_flows_for_scenario function."""

    def test_from_dict_list(self):
        """Test generating flows from dictionary list."""
        devices = [
            {"device_id": "plc-001", "role": "controller", "ip_address": "192.168.1.20"},
            {"device_id": "io-001", "role": "field_device", "ip_address": "192.168.1.30"},
        ]

        flows = generate_flows_for_scenario(devices)

        assert isinstance(flows, list)
        if flows:
            assert isinstance(flows[0], dict)
            assert "flow_id" in flows[0]

    def test_pattern_parsing(self):
        """Test pattern string parsing."""
        devices = [
            {"device_id": "d1", "role": "controller", "ip_address": "1.1.1.1"},
            {"device_id": "d2", "role": "controller", "ip_address": "1.1.1.2"},
        ]

        # Test different pattern strings
        for pattern in ["hierarchical", "mesh", "star", "realistic", "REALISTIC"]:
            flows = generate_flows_for_scenario(devices, pattern=pattern)
            assert isinstance(flows, list)

    def test_protocols_filter(self):
        """Test protocol filtering."""
        devices = [
            {"device_id": "d1", "role": "controller", "ip_address": "1.1.1.1",
             "protocols": ["modbus_tcp", "ethernet_ip"]},
            {"device_id": "d2", "role": "field_device", "ip_address": "1.1.1.2",
             "protocols": ["modbus_tcp", "ethernet_ip"]},
        ]

        flows = generate_flows_for_scenario(
            devices,
            protocols=["ethernet_ip"],
        )

        if flows:
            assert all(f["protocol"] == "ethernet_ip" for f in flows)
