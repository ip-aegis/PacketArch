"""Tests for BackgroundNoiseGenerator — broadcast filtering, scheduling, handlers."""

import pytest

from app.protocol_engines.ambient.noise_generator import (
    AmbientConfig,
    AmbientDevice,
    BackgroundNoiseGenerator,
)


# ======================================================================
# Fixtures
# ======================================================================


def _make_device(**overrides) -> AmbientDevice:
    """Create an AmbientDevice with sensible defaults."""
    defaults = dict(
        device_id="dev-1",
        mac_address="00:1C:06:AA:BB:CC",
        ip_address="10.1.0.10",
        gateway_ip="10.1.0.1",
    )
    defaults.update(overrides)
    return AmbientDevice(**defaults)


class FakeScheduler:
    """Simple scheduler that records scheduled events."""

    def __init__(self):
        self.events: list[tuple[float, dict]] = []

    def schedule(self, time_ms: float, event: dict) -> None:
        self.events.append((time_ms, event))

    def event_types(self) -> list[str]:
        return [e[1].get("type", "") for e in self.events]


# ======================================================================
# Device filtering tests
# ======================================================================


class TestDeviceFiltering:
    """Test _should_* filtering methods."""

    def test_should_lldp_requires_device_type(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        # Empty device_type → no LLDP
        assert gen._should_lldp(_make_device(device_type="")) is False
        assert gen._should_lldp(_make_device(device_type="plc")) is True

    def test_should_stp_only_switches(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        assert gen._should_stp(_make_device(device_type="switch")) is True
        assert gen._should_stp(_make_device(device_type="plc")) is False
        assert gen._should_stp(_make_device(device_type="")) is False

    def test_should_dhcp_hmi_and_workstation(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        assert gen._should_dhcp(_make_device(device_type="hmi")) is True
        assert gen._should_dhcp(_make_device(device_type="workstation")) is True
        assert gen._should_dhcp(_make_device(device_type="server")) is True
        assert gen._should_dhcp(_make_device(device_type="plc")) is False

    def test_should_bacnet_requires_protocol(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        assert gen._should_bacnet_whois(_make_device(protocols=["bacnet"])) is True
        assert gen._should_bacnet_whois(_make_device(protocols=["modbus_tcp"])) is False
        assert gen._should_bacnet_whois(_make_device(protocols=[])) is False

    def test_should_profinet_requires_protocol_and_controller(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        assert gen._should_profinet_dcp(
            _make_device(protocols=["profinet"], device_type="plc")
        ) is True
        assert gen._should_profinet_dcp(
            _make_device(protocols=["profinet"], device_type="sensor")
        ) is False
        assert gen._should_profinet_dcp(
            _make_device(protocols=["modbus_tcp"], device_type="plc")
        ) is False

    def test_should_snmp_trap_managed_devices(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        assert gen._should_snmp_trap(_make_device(device_type="switch")) is True
        assert gen._should_snmp_trap(_make_device(device_type="plc")) is True
        assert gen._should_snmp_trap(_make_device(device_type="sensor")) is False

    def test_should_igmp_multicast_protocols(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        assert gen._should_igmp(_make_device(protocols=["bacnet"])) is True
        assert gen._should_igmp(_make_device(protocols=["profinet"])) is True
        assert gen._should_igmp(_make_device(protocols=["modbus_tcp"])) is False

    def test_should_cdp_cisco_only(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        assert gen._should_cdp(_make_device(vendor="Cisco")) is True
        assert gen._should_cdp(_make_device(vendor="cisco Systems")) is True
        assert gen._should_cdp(_make_device(vendor="Siemens")) is False
        assert gen._should_cdp(_make_device(vendor="")) is False

    def test_disabled_config_blocks_all(self):
        config = AmbientConfig(
            lldp_enabled=False,
            stp_enabled=False,
            dhcp_enabled=False,
            bacnet_whois_enabled=False,
            profinet_dcp_enabled=False,
            snmp_trap_enabled=False,
            igmp_enabled=False,
            cdp_enabled=False,
        )
        gen = BackgroundNoiseGenerator([_make_device()], config=config)
        device = _make_device(
            device_type="switch",
            vendor="Cisco",
            protocols=["bacnet", "profinet"],
        )
        assert gen._should_lldp(device) is False
        assert gen._should_stp(device) is False
        assert gen._should_dhcp(_make_device(device_type="hmi")) is False
        assert gen._should_bacnet_whois(device) is False
        assert gen._should_profinet_dcp(device) is False
        assert gen._should_snmp_trap(device) is False
        assert gen._should_igmp(device) is False
        assert gen._should_cdp(device) is False


# ======================================================================
# Scheduling tests
# ======================================================================


class TestScheduling:
    """Test schedule_initial_events creates expected event types."""

    def test_minimal_device_only_gets_arp_ntp(self):
        """Device with no metadata only gets ARP and NTP."""
        device = _make_device()  # no protocols, no device_type
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        types = scheduler.event_types()
        assert "ambient_gratuitous_arp" in types
        assert "ambient_ntp_query" in types
        # Should NOT have broadcast types
        assert "ambient_lldp" not in types
        assert "ambient_stp_bpdu" not in types

    def test_switch_gets_stp_and_lldp(self):
        device = _make_device(device_type="switch", vendor="Siemens")
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        types = scheduler.event_types()
        assert "ambient_stp_bpdu" in types
        assert "ambient_lldp" in types
        assert "ambient_snmp_coldstart" in types

    def test_cisco_switch_gets_cdp(self):
        device = _make_device(device_type="switch", vendor="Cisco")
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        types = scheduler.event_types()
        assert "ambient_cdp" in types

    def test_bacnet_device_gets_whois_and_igmp(self):
        device = _make_device(
            device_type="controller",
            protocols=["bacnet"],
        )
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        types = scheduler.event_types()
        assert "ambient_bacnet_whois" in types
        assert "ambient_igmp_join" in types

    def test_profinet_plc_gets_dcp(self):
        device = _make_device(
            device_type="plc",
            protocols=["profinet"],
        )
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        types = scheduler.event_types()
        assert "ambient_profinet_dcp" in types

    def test_hmi_gets_dhcp(self):
        device = _make_device(device_type="hmi")
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        types = scheduler.event_types()
        assert "ambient_dhcp_boot" in types

    def test_disabled_config_schedules_nothing(self):
        device = _make_device(device_type="switch", vendor="Cisco")
        config = AmbientConfig(enabled=False)
        gen = BackgroundNoiseGenerator([device], config=config)
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        assert len(scheduler.events) == 0


# ======================================================================
# Handler tests
# ======================================================================


class TestHandlers:
    """Test individual event handlers produce correct PacketEvents."""

    def test_gratuitous_arp_produces_packet_and_reschedules(self):
        device = _make_device()
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        event = {"type": "ambient_gratuitous_arp", "device_id": "dev-1"}

        packets = gen.handle_event(event, 1000.0, scheduler)
        assert len(packets) == 1
        assert packets[0].direction == "broadcast"
        assert packets[0].metadata["type"] == "gratuitous_arp"
        # Should have rescheduled
        assert len(scheduler.events) == 1
        assert scheduler.events[0][1]["type"] == "ambient_gratuitous_arp"
        # Rescheduled time should be ~300s later
        assert scheduler.events[0][0] > 200_000

    def test_ntp_produces_query_and_response(self):
        device = _make_device()
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        event = {"type": "ambient_ntp_query", "device_id": "dev-1"}

        packets = gen.handle_event(event, 1000.0, scheduler)
        assert len(packets) == 2
        assert packets[0].metadata["type"] == "ntp_query"
        assert packets[1].metadata["type"] == "ntp_response"
        assert packets[1].timestamp_ms > packets[0].timestamp_ms

    def test_stp_produces_bpdu_and_reschedules(self):
        device = _make_device(device_type="switch")
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        event = {"type": "ambient_stp_bpdu", "device_id": "dev-1"}

        packets = gen.handle_event(event, 1000.0, scheduler)
        assert len(packets) == 1
        assert packets[0].metadata["type"] == "stp_bpdu"
        # Reschedule ~2s later
        assert len(scheduler.events) == 1
        assert 1500 < scheduler.events[0][0] < 3500

    def test_cdp_produces_frame_and_reschedules(self):
        device = _make_device(
            vendor="Cisco",
            device_name="Switch-01",
            vendor_fingerprint={"model": "IE-4010"},
        )
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        event = {"type": "ambient_cdp", "device_id": "dev-1"}

        packets = gen.handle_event(event, 1000.0, scheduler)
        assert len(packets) == 1
        assert packets[0].metadata["type"] == "cdp"
        assert len(scheduler.events) == 1

    def test_dhcp_produces_4_packets_no_reschedule(self):
        device = _make_device(device_type="hmi", device_name="HMI-01")
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        event = {"type": "ambient_dhcp_boot", "device_id": "dev-1"}

        packets = gen.handle_event(event, 500.0, scheduler)
        assert len(packets) == 4
        types = [p.metadata["type"] for p in packets]
        assert types == ["dhcp_discover", "dhcp_offer", "dhcp_request", "dhcp_ack"]
        # Timestamps should be increasing
        for i in range(1, len(packets)):
            assert packets[i].timestamp_ms > packets[i - 1].timestamp_ms
        # One-shot: no reschedule
        assert len(scheduler.events) == 0

    def test_igmp_produces_report_and_reschedules(self):
        device = _make_device(protocols=["bacnet"])
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        event = {"type": "ambient_igmp_join", "device_id": "dev-1"}

        packets = gen.handle_event(event, 1000.0, scheduler)
        assert len(packets) == 1
        assert packets[0].metadata["type"] == "igmp_report"
        assert len(scheduler.events) == 1

    def test_unknown_device_id_returns_empty(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        scheduler = FakeScheduler()
        event = {"type": "ambient_gratuitous_arp", "device_id": "nonexistent"}

        packets = gen.handle_event(event, 1000.0, scheduler)
        assert packets == []

    def test_unknown_event_type_returns_empty(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        scheduler = FakeScheduler()
        event = {"type": "ambient_unknown", "device_id": "dev-1"}

        packets = gen.handle_event(event, 1000.0, scheduler)
        assert packets == []


# ======================================================================
# Backward compatibility tests
# ======================================================================


class TestBackwardCompatibility:
    """Ensure old-style AmbientDevice construction still works."""

    def test_old_style_4_arg_construction(self):
        """Old code creates AmbientDevice(id, mac, ip, gateway)."""
        device = AmbientDevice(
            device_id="dev-1",
            mac_address="00:1C:06:AA:BB:CC",
            ip_address="10.1.0.10",
            gateway_ip="10.1.0.1",
        )
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        types = scheduler.event_types()
        # Should only get ARP and NTP (no protocol/type metadata)
        assert "ambient_gratuitous_arp" in types
        assert "ambient_ntp_query" in types
        assert "ambient_lldp" not in types
        assert "ambient_stp_bpdu" not in types
        assert "ambient_cdp" not in types

    def test_config_defaults_unchanged(self):
        config = AmbientConfig()
        assert config.arp_gratuitous_interval_s == 300.0
        assert config.ntp_interval_s == 64.0
        assert config.ntp_server_mac == "02:00:00:00:00:01"


# ======================================================================
# Zone-aware broadcast tests
# ======================================================================


class TestZoneAwareBroadcast:
    """Test zone-based filtering for BACnet/PROFINET responses."""

    def test_zone_devices_grouped_correctly(self):
        devices = [
            _make_device(device_id="d1", zone_id="control"),
            _make_device(device_id="d2", zone_id="control"),
            _make_device(device_id="d3", zone_id="field"),
        ]
        gen = BackgroundNoiseGenerator(devices)
        assert len(gen._zone_devices["control"]) == 2
        assert len(gen._zone_devices["field"]) == 1

    def test_none_zone_grouped_together(self):
        devices = [
            _make_device(device_id="d1"),
            _make_device(device_id="d2"),
        ]
        gen = BackgroundNoiseGenerator(devices)
        assert len(gen._zone_devices[None]) == 2


# ======================================================================
# Integration test
# ======================================================================


class TestIntegration:
    """Full generator integration with mixed device population."""

    def test_mixed_population_schedules_diverse_events(self):
        """A realistic device mix should produce many broadcast types."""
        devices = [
            _make_device(
                device_id="switch-1",
                device_type="switch",
                vendor="Cisco",
                zone_id="control",
                vlan_id=100,
            ),
            _make_device(
                device_id="plc-1",
                mac_address="00:1C:06:11:22:33",
                ip_address="10.1.0.20",
                device_type="plc",
                vendor="Siemens",
                protocols=["profinet", "s7comm"],
                zone_id="control",
            ),
            _make_device(
                device_id="bac-1",
                mac_address="00:A0:AF:11:22:33",
                ip_address="10.1.1.10",
                device_type="controller",
                vendor="Honeywell",
                protocols=["bacnet"],
                zone_id="field",
            ),
            _make_device(
                device_id="hmi-1",
                mac_address="00:1C:06:44:55:66",
                ip_address="10.1.0.30",
                device_type="hmi",
                vendor="Siemens",
                protocols=["s7comm"],
                zone_id="control",
            ),
        ]
        gen = BackgroundNoiseGenerator(devices)
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        types = set(scheduler.event_types())

        # Core ambient: all devices
        assert "ambient_gratuitous_arp" in types
        assert "ambient_ntp_query" in types

        # Switch-specific
        assert "ambient_stp_bpdu" in types
        assert "ambient_cdp" in types  # Cisco switch

        # PROFINET PLC
        assert "ambient_profinet_dcp" in types
        assert "ambient_lldp" in types

        # BACnet controller
        assert "ambient_bacnet_whois" in types
        assert "ambient_igmp_join" in types

        # HMI
        assert "ambient_dhcp_boot" in types

        # Managed devices boot traps
        assert "ambient_snmp_coldstart" in types
