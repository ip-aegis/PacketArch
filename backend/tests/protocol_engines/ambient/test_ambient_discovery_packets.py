# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Byte-level validation of ambient discovery packet generation.

Each test calls an ambient discovery handler directly, parses the returned
``PacketEvent.packet_bytes`` with Scapy, and asserts that protocol-specific
identity fields (vendor, model, firmware, serial) are present and correct.

This is the *missing* layer of testing that sits between the scheduling/
filtering unit tests in ``test_noise_generator.py`` and the full scenario
integration tests in ``test_scenario_fingerprints.py``.  A regression here
means Cisco Cyber Vision cannot fingerprint the device.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

from scapy.all import Ether, UDP, TCP

from app.protocol_engines.ambient.noise_generator import (
    AmbientDevice,
    BackgroundNoiseGenerator,
)

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


# ======================================================================
# Helpers
# ======================================================================


def _make_device(
    device_id: str = "target-1",
    mac_address: str = "08:61:95:AA:BB:CC",
    ip_address: str = "10.1.0.10",
    **kw,
) -> AmbientDevice:
    defaults = dict(
        device_id=device_id,
        mac_address=mac_address,
        ip_address=ip_address,
        gateway_ip="10.1.0.1",
    )
    defaults.update(kw)
    return AmbientDevice(**defaults)


def _make_manager(
    device_id: str = "manager-1",
    mac_address: str = "00:1C:06:11:22:33",
    ip_address: str = "10.1.0.100",
    **kw,
) -> AmbientDevice:
    """Create a management-station device (HMI/workstation) for query source."""
    defaults = dict(
        device_type="hmi",
        vendor="Siemens",
        device_name="Engineering_HMI",
        zone_id="control",
    )
    defaults.update(kw)
    return _make_device(
        device_id=device_id,
        mac_address=mac_address,
        ip_address=ip_address,
        **defaults,
    )


def _rockwell_fingerprint() -> dict:
    """Minimal Rockwell fingerprint with EtherNet/IP + Modbus identity."""
    return {
        "vendor": "Rockwell Automation",
        "model": "1756-L83E/B LOGIX5580",
        "firmware_version": "V32.011",
        "ethernet_ip_identity": {
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 55,
            "product_name": "1756-L83E/B LOGIX5580",
            "serial_number": "0xDEADBEEF",
            "revision_major": 32,
            "revision_minor": 11,
            "state": 3,
        },
        "modbus_identity": {
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1756-L83E",
            "product_name": "1756-L83E Logix5580 Controller",
            "major_minor_revision": "V32.011",
            "vendor_url": "http://www.rockwellautomation.com",
        },
    }


def _siemens_fingerprint() -> dict:
    """Minimal Siemens fingerprint with S7 + PROFINET identity."""
    return {
        "vendor": "Siemens",
        "model": "6ES7 517-3AP00-0AB0",
        "firmware_version": "V3.0.3",
        "s7_identity": {
            "module_type": "CPU 1517-3 PN/DP",
            "order_code": "6ES7 517-3AP00-0AB0",
            "firmware_version": "V3.0.3",
            "serial_number": "S V-TEST12345",
        },
        "profinet_identity": {
            "vendor_id": 0x002A,
            "station_name_prefix": "siemens-plc",
            "device_id": 0x010D,
        },
    }


def _schneider_fingerprint() -> dict:
    """Minimal Schneider fingerprint with Modbus + SNMP identity."""
    return {
        "vendor": "Schneider Electric",
        "model": "TM251MESE",
        "firmware_version": "V5.0.7.3",
        "modbus_identity": {
            "vendor_name": "Schneider Electric",
            "product_code": "TM251MESE",
            "product_name": "Modicon M251 Logic Controller",
            "major_minor_revision": "V5.0",
        },
        "snmp_identity": {
            "sys_descr": "Schneider Electric Modicon M251 V5.0.7.3",
            "sys_object_id": "1.3.6.1.4.1.3833",
            "sys_name": "WTP_PLC_1",
            "sys_location": "Plant Floor",
        },
    }


def _bacnet_fingerprint() -> dict:
    """Minimal BACnet device fingerprint."""
    return {
        "vendor": "Johnson Controls",
        "model": "FEC2621-0",
        "firmware_version": "V5.2",
        "bacnet_identity": {
            "vendor_id": 5,
            "vendor_name": "Johnson Controls",
            "model_name": "FEC2621-0",
            "firmware_revision": "V5.2",
            "device_instance": 100001,
        },
    }


def _build_gen(*devices: AmbientDevice) -> BackgroundNoiseGenerator:
    """Build a generator from a list of devices."""
    return BackgroundNoiseGenerator(list(devices))


class FakeScheduler:
    """Records scheduled events without executing them."""

    def __init__(self):
        self.events: list[tuple[float, dict]] = []

    def schedule(self, time_ms: float, event) -> None:
        self.events.append((time_ms, event))


def _call_handler(gen, handler_name, device, current_time_ms=1000.0):
    """Call a handler by name and return PacketEvent list."""
    scheduler = FakeScheduler()
    event = {"type": handler_name, "device_id": device.device_id}
    handler = getattr(gen, f"_handle_{handler_name.replace('ambient_', '')}")
    return handler(device, current_time_ms, scheduler, event)


# ======================================================================
# SNMP Discovery Packet Tests
# ======================================================================


class TestSnmpDiscoveryPackets:
    """Validate SNMP GET/Response packet bytes contain identity fields."""

    def test_snmp_response_contains_sys_descr(self):
        """SNMP response must contain sysDescr matching fingerprint."""
        device = _make_device(
            protocols=["snmp"],
            vendor="Schneider Electric",
            device_name="WTP_PLC_1",
            vendor_fingerprint=_schneider_fingerprint(),
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_snmp_discovery", device)

        assert len(packets) >= 2, "Should have at least 1 GET + 1 Response"
        # Find response packets (even indices are requests, odd are responses)
        response_bytes = [p.packet_bytes for p in packets if p.direction == "response"]
        assert response_bytes, "No SNMP response packets found"

        # Parse first response — should contain sysDescr
        raw = response_bytes[0]
        # sysDescr value should be in the raw bytes
        assert b"Schneider Electric" in raw, (
            "sysDescr must contain vendor name 'Schneider Electric'"
        )
        assert b"Modicon M251" in raw, (
            "sysDescr must contain model reference"
        )

    def test_snmp_response_contains_sys_object_id(self):
        """SNMP response must contain sysObjectID with vendor enterprise OID."""
        device = _make_device(
            protocols=["snmp"],
            vendor="Schneider Electric",
            vendor_fingerprint=_schneider_fingerprint(),
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_snmp_discovery", device)

        response_bytes = [p.packet_bytes for p in packets if p.direction == "response"]
        assert response_bytes, "No SNMP response packets found"

        # sysObjectID response should contain Schneider PEN (3833)
        # OID 1.3.6.1.4.1.3833 BER-encodes 3833 as base-128: \x9d\x79
        all_response_bytes = b"".join(response_bytes)
        assert b"\x9d\x79" in all_response_bytes, (
            "sysObjectID must contain BER-encoded Schneider enterprise OID 3833"
        )

    def test_snmp_response_contains_sys_name(self):
        """SNMP response must contain sysName matching device name."""
        device = _make_device(
            protocols=["snmp"],
            vendor="Schneider Electric",
            device_name="WTP_PLC_1",
            vendor_fingerprint=_schneider_fingerprint(),
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_snmp_discovery", device)

        response_bytes = [p.packet_bytes for p in packets if p.direction == "response"]
        all_bytes = b"".join(response_bytes)
        assert b"WTP_PLC_1" in all_bytes, "sysName must match device name"

    def test_snmp_synthesis_when_no_explicit_identity(self):
        """Devices without snmp_identity should get synthesized SNMP responses."""
        fp = _rockwell_fingerprint()  # No snmp_identity key
        assert fp.get("snmp_identity") is None

        device = _make_device(
            protocols=["ethernet_ip"],
            vendor="Rockwell Automation",
            device_name="Main_PLC",
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)

        # Universal guardrail: device has vendor fingerprint → gets SNMP
        assert gen._should_snmp_discovery(device)

        packets = _call_handler(gen, "ambient_snmp_discovery", device)
        response_bytes = [p.packet_bytes for p in packets if p.direction == "response"]
        all_bytes = b"".join(response_bytes)

        # Synthesized sysDescr should contain vendor and model
        assert b"Rockwell Automation" in all_bytes, (
            "Synthesized sysDescr must contain vendor"
        )
        assert b"1756-L83E" in all_bytes, (
            "Synthesized sysDescr must contain model"
        )

    def test_snmp_correct_mac_addresses(self):
        """SNMP response must come FROM the target device MAC, not the manager."""
        device = _make_device(
            mac_address="08:61:95:AA:BB:CC",
            protocols=["snmp"],
            vendor_fingerprint=_schneider_fingerprint(),
            zone_id="control",
        )
        manager = _make_manager(
            mac_address="00:1C:06:11:22:33",
            zone_id="control",
        )
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_snmp_discovery", device)

        responses = [p for p in packets if p.direction == "response"]
        assert responses, "Must have response packets"

        # Parse Ethernet frame — src MAC should be the target device
        pkt = Ether(responses[0].packet_bytes)
        assert pkt.src.lower() == "08:61:95:aa:bb:cc", (
            f"Response source MAC must be device MAC, got {pkt.src}"
        )


# ======================================================================
# Modbus MEI Discovery Packet Tests
# ======================================================================


class TestModbusDiscoveryPackets:
    """Validate Modbus FC43 MEI request/response packets."""

    def test_modbus_mei_response_contains_vendor(self):
        """MEI response must contain vendor name from fingerprint."""
        fp = _rockwell_fingerprint()
        device = _make_device(
            protocols=["modbus_tcp"],
            vendor="Rockwell Automation",
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_modbus_discovery", device)

        assert len(packets) == 2, "Should have 1 request + 1 response"
        response_raw = packets[1].packet_bytes

        # Parse Ethernet/IP/TCP to get payload
        pkt = Ether(response_raw)
        assert pkt.haslayer(TCP), "Must be TCP packet"
        assert pkt[TCP].sport == 502, "Response must come from port 502"

        payload = bytes(pkt[TCP].payload)
        # MBAP header (7 bytes) + FC 43 (0x2B) + MEI type (0x0E)
        assert b"\x2b\x0e" in payload, "Must contain FC43 + MEI type 0x0E"

        # Vendor name should be in the MEI objects
        assert b"Rockwell" in payload, (
            "MEI response must contain vendor name"
        )

    def test_modbus_mei_response_contains_product(self):
        """MEI response must contain product code and name."""
        fp = _rockwell_fingerprint()
        device = _make_device(
            protocols=["modbus_tcp"],
            vendor="Rockwell Automation",
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_modbus_discovery", device)

        response_raw = packets[1].packet_bytes
        pkt = Ether(response_raw)
        payload = bytes(pkt[TCP].payload)

        assert b"1756-L83E" in payload, "Must contain product code"
        assert b"Logix5580" in payload or b"LOGIX5580" in payload, (
            "Must contain product name"
        )

    def test_modbus_no_identity_returns_empty(self):
        """Devices without modbus_identity should return no packets."""
        fp = _siemens_fingerprint()  # No modbus_identity
        device = _make_device(
            protocols=["modbus_tcp"],
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_modbus_discovery", device)
        assert packets == [], "No packets when modbus_identity is missing"


# ======================================================================
# EtherNet/IP ListIdentity Discovery Packet Tests
# ======================================================================


class TestEnipDiscoveryPackets:
    """Validate EtherNet/IP ListIdentity request/response packets."""

    def test_enip_list_identity_response_contains_product(self):
        """ListIdentity response must contain product_name from fingerprint."""
        fp = _rockwell_fingerprint()
        device = _make_device(
            protocols=["ethernet_ip"],
            vendor="Rockwell Automation",
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_enip_discovery", device)

        assert len(packets) == 2, "Should have 1 request + 1 response"
        response_raw = packets[1].packet_bytes

        # Parse Ethernet/IP/UDP packet
        pkt = Ether(response_raw)
        assert pkt.haslayer(UDP), "ListIdentity uses UDP"
        assert pkt[UDP].sport == 44818, "Must come from EtherNet/IP port"

        payload = bytes(pkt[UDP].payload)
        # ListIdentity command is 0x0063
        assert payload[:2] == b"\x63\x00", "Must be ListIdentity command (0x0063)"

        # product_name should be in the response
        assert b"1756-L83E" in payload or b"LOGIX5580" in payload, (
            "ListIdentity must contain product name"
        )

    def test_enip_list_identity_has_vendor_id(self):
        """ListIdentity response must encode vendor_id = 1 (Rockwell)."""
        fp = _rockwell_fingerprint()
        device = _make_device(
            protocols=["ethernet_ip"],
            vendor="Rockwell Automation",
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_enip_discovery", device)
        response_raw = packets[1].packet_bytes

        pkt = Ether(response_raw)
        payload = bytes(pkt[UDP].payload)

        # vendor_id is encoded as little-endian uint16 somewhere in the identity item
        # Rockwell vendor_id = 1 → b"\x01\x00"
        assert b"\x01\x00" in payload, (
            "Must contain vendor_id 1 (Rockwell) as LE uint16"
        )

    def test_enip_no_identity_returns_empty(self):
        """Devices without ethernet_ip_identity should return no packets."""
        fp = _siemens_fingerprint()  # No ethernet_ip_identity
        device = _make_device(
            protocols=["ethernet_ip"],
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_enip_discovery", device)
        assert packets == [], "No packets when ethernet_ip_identity is missing"


# ======================================================================
# S7 SZL Discovery Packet Tests
# ======================================================================


class TestS7DiscoveryPackets:
    """Validate S7 SZL query/response packets."""

    def test_s7_szl_response_contains_order_code(self):
        """SZL response must contain order_code from fingerprint."""
        fp = _siemens_fingerprint()
        device = _make_device(
            protocols=["s7comm"],
            vendor="Siemens",
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_s7_discovery", device)

        assert len(packets) == 2, "Should have 1 request + 1 response"
        response_raw = packets[1].packet_bytes

        pkt = Ether(response_raw)
        assert pkt.haslayer(TCP), "S7 uses TCP"
        assert pkt[TCP].sport == 102, "S7 port is 102"

        payload = bytes(pkt[TCP].payload)
        # TPKT header starts with 0x03 0x00
        assert payload[:2] == b"\x03\x00", "Must have TPKT header"

        # Order code should be in the SZL data
        assert b"6ES7 517-3AP00-0AB0" in payload, (
            "SZL response must contain order code"
        )

    def test_s7_szl_response_contains_module_type(self):
        """SZL response must contain module_type from fingerprint."""
        fp = _siemens_fingerprint()
        device = _make_device(
            protocols=["s7comm"],
            vendor="Siemens",
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_s7_discovery", device)

        response_raw = packets[1].packet_bytes
        pkt = Ether(response_raw)
        payload = bytes(pkt[TCP].payload)

        assert b"CPU 1517-3 PN/DP" in payload, (
            "SZL response must contain module type"
        )

    def test_s7_no_identity_returns_empty(self):
        """Devices without s7_identity should return no packets."""
        fp = _rockwell_fingerprint()  # No s7_identity
        device = _make_device(
            protocols=["s7comm"],
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_s7_discovery", device)
        assert packets == [], "No packets when s7_identity is missing"


# ======================================================================
# BACnet Who-Is / I-Am Discovery Packet Tests
# ======================================================================


class TestBacnetDiscoveryPackets:
    """Validate BACnet Who-Is / I-Am discovery packets."""

    def test_bacnet_iam_contains_vendor_name(self):
        """BACnet I-Am + ReadProperty must contain vendor_name."""
        fp = _bacnet_fingerprint()
        device = _make_device(
            protocols=["bacnet"],
            vendor="Johnson Controls",
            device_name="AHU_Controller_1",
            vendor_fingerprint=fp,
            zone_id="hvac",
        )
        manager = _make_manager(zone_id="hvac")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_bacnet_whois", device)

        # Should have Who-Is + I-Am + ReadProperty pairs
        assert len(packets) >= 2, "Must have at least Who-Is + I-Am"

        all_bytes = b"".join(p.packet_bytes for p in packets)
        assert b"Johnson Controls" in all_bytes, (
            "BACnet response must contain vendor name"
        )

    def test_bacnet_iam_contains_model(self):
        """BACnet ReadProperty response must contain model_name."""
        fp = _bacnet_fingerprint()
        device = _make_device(
            protocols=["bacnet"],
            vendor="Johnson Controls",
            vendor_fingerprint=fp,
            zone_id="hvac",
        )
        manager = _make_manager(zone_id="hvac")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_bacnet_whois", device)

        all_bytes = b"".join(p.packet_bytes for p in packets)
        assert b"FEC2621-0" in all_bytes, (
            "BACnet response must contain model name"
        )


# ======================================================================
# PROFINET DCP Discovery Packet Tests
# ======================================================================


class TestProfinetDcpDiscoveryPackets:
    """Validate PROFINET DCP Identify response packets."""

    def test_profinet_dcp_contains_vendor_id(self):
        """DCP Identify response must contain Siemens vendor_id (0x002A)."""
        fp = _siemens_fingerprint()
        device = _make_device(
            protocols=["profinet"],
            vendor="Siemens",
            device_name="PLC_Main",
            vendor_fingerprint=fp,
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)
        packets = _call_handler(gen, "ambient_profinet_dcp", device)

        # Should have identify request + response(s)
        assert len(packets) >= 2, "Must have at least request + response"

        # Find responses (from device MAC)
        responses = [p for p in packets if p.direction == "response"]
        assert responses, "Must have DCP response packets"

        # Check raw bytes for Siemens vendor_id 0x002A
        response_raw = responses[0].packet_bytes
        # DCP uses raw Ethernet (no IP/UDP)
        pkt = Ether(response_raw)
        bytes(pkt.payload) if pkt.payload else b""
        all_bytes = response_raw

        # Vendor ID 0x002A = 42 decimal, encoded as big-endian in DCP
        assert b"\x00\x2a" in all_bytes, (
            "DCP response must contain Siemens vendor_id 0x002A"
        )


# ======================================================================
# Handler Exception Isolation Tests
# ======================================================================


class TestHandlerExceptionIsolation:
    """Ensure individual handler exceptions don't propagate."""

    def test_handle_event_catches_handler_exception(self):
        """If a handler raises, handle_event returns [] instead of propagating."""
        device = _make_device(
            protocols=["snmp"],
            vendor="Test",
            vendor_fingerprint={"vendor": "Test"},
            zone_id="control",
        )
        manager = _make_manager(zone_id="control")
        gen = _build_gen(device, manager)

        # Monkey-patch a handler to raise
        original = gen._handle_snmp_discovery

        def _exploding_handler(*args, **kwargs):
            raise RuntimeError("Simulated handler crash")

        gen._handle_snmp_discovery = _exploding_handler

        scheduler = FakeScheduler()
        event = {"type": "ambient_snmp_discovery", "device_id": device.device_id}

        # Should NOT raise — should return [] and log warning
        result = gen.handle_event(event, 1000.0, scheduler)
        assert result == [], "Must return empty list on handler exception"

        # Restore
        gen._handle_snmp_discovery = original

    def test_orchestrator_ambient_event_catches_exception(self):
        """UnifiedOrchestrator._handle_ambient_event catches exceptions."""
        from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
        from app.protocol_engines.output import PcapOutput
        import tempfile
        import os

        fd, path = tempfile.mkstemp(suffix=".pcap")
        os.close(fd)
        try:
            output = PcapOutput(path)
            orch = UnifiedOrchestrator(output=output, duration_ms=1000)

            # Create a mock ambient generator that always raises
            mock_gen = MagicMock()
            mock_gen.handle_event.side_effect = RuntimeError("boom")
            orch._ambient_generator = mock_gen

            # Should NOT raise
            event = {"type": "ambient_snmp_discovery", "device_id": "test"}
            orch._handle_ambient_event(event)
            # If we get here, the exception was caught
        finally:
            output.close()
            os.unlink(path)


# ======================================================================
# Query Source Selection Tests
# ======================================================================


class TestPickQuerySource:
    """Validate _pick_query_source returns real devices, not phantoms."""

    def test_prefers_manager_type_in_same_zone(self):
        """Should prefer HMI/server/workstation in the same zone."""
        target = _make_device(
            device_id="plc-1", device_type="plc", zone_id="control",
        )
        hmi = _make_device(
            device_id="hmi-1", device_type="hmi", zone_id="control",
            ip_address="10.1.0.100", mac_address="AA:BB:CC:DD:EE:01",
        )
        sensor = _make_device(
            device_id="sensor-1", device_type="sensor", zone_id="control",
            ip_address="10.1.0.200", mac_address="AA:BB:CC:DD:EE:02",
        )
        gen = _build_gen(target, hmi, sensor)
        result = gen._pick_query_source(target)
        assert result is not None
        assert result.device_id == "hmi-1", "Should prefer HMI over sensor"

    def test_never_returns_self(self):
        """Query source must never be the target device itself."""
        target = _make_device(device_id="plc-1", zone_id="control")
        other = _make_device(
            device_id="plc-2", zone_id="control",
            ip_address="10.1.0.20", mac_address="AA:BB:CC:DD:EE:03",
        )
        gen = _build_gen(target, other)
        result = gen._pick_query_source(target)
        assert result is not None
        assert result.device_id != target.device_id

    def test_returns_none_for_single_device(self):
        """Single-device scenario returns None (no valid query source)."""
        target = _make_device(device_id="plc-1", zone_id="control")
        gen = _build_gen(target)
        result = gen._pick_query_source(target)
        assert result is None
