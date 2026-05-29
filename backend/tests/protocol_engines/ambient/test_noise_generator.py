# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for BackgroundNoiseGenerator — broadcast filtering, scheduling, handlers."""


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

    def test_should_profinet_requires_protocol(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        assert gen._should_profinet_dcp(
            _make_device(protocols=["profinet"], device_type="plc")
        ) is True
        # Any device with profinet gets DCP (protocol is sufficient)
        assert gen._should_profinet_dcp(
            _make_device(protocols=["profinet"], device_type="sensor")
        ) is True
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

    def test_profinet_dcp_fires_within_5s(self):
        """An early-burst DCP must be scheduled inside the integration
        test window (≤5s) so CV sees PROFINET Identify before steady-state.
        Regression: previously DCP only scheduled at 2-10s with no t≤2s seed.
        """
        device = _make_device(
            device_type="plc",
            protocols=["profinet"],
        )
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        dcp_events = [
            (t, e) for t, e in scheduler.events
            if e.get("type") == "ambient_profinet_dcp"
        ]
        assert dcp_events, "no PROFINET DCP events scheduled"
        early = [t for t, _ in dcp_events if t <= 5_000.0]
        assert early, (
            f"no PROFINET DCP scheduled within 5s; all events at: "
            f"{[t for t, _ in dcp_events]}"
        )
        # The early event should be a one-shot burst, not the steady cadence.
        burst_early = [
            t for t, e in dcp_events if t <= 5_000.0 and e.get("burst")
        ]
        assert burst_early, "early PROFINET DCP missing burst=True flag"

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


# ======================================================================
# Universal SNMP discovery guardrail tests
# ======================================================================


class TestUniversalSnmpDiscovery:
    """Test universal SNMP discovery guardrail."""

    def test_snmp_discovery_with_explicit_snmp_protocol(self):
        gen = BackgroundNoiseGenerator([_make_device()])
        device = _make_device(protocols=["snmp"])
        assert gen._should_snmp_discovery(device) is True

    def test_snmp_discovery_with_vendor_fingerprint(self):
        """Devices with vendor fingerprint get SNMP even without SNMP protocol."""
        gen = BackgroundNoiseGenerator([_make_device()])
        device = _make_device(
            protocols=["modbus_tcp"],
            vendor_fingerprint={"vendor": "Schneider Electric"},
        )
        assert gen._should_snmp_discovery(device) is True

    def test_snmp_discovery_without_fingerprint_or_protocol(self):
        """Devices with no fingerprint and no SNMP protocol are excluded."""
        gen = BackgroundNoiseGenerator([_make_device()])
        device = _make_device(protocols=["modbus_tcp"], vendor_fingerprint={})
        assert gen._should_snmp_discovery(device) is False

    def test_snmp_discovery_with_empty_vendor(self):
        """Fingerprint with empty vendor does not trigger discovery."""
        gen = BackgroundNoiseGenerator([_make_device()])
        device = _make_device(
            protocols=["modbus_tcp"],
            vendor_fingerprint={"vendor": ""},
        )
        assert gen._should_snmp_discovery(device) is False

    def test_snmp_discovery_disabled_config(self):
        config = AmbientConfig(snmp_discovery_enabled=False)
        gen = BackgroundNoiseGenerator([_make_device()], config=config)
        device = _make_device(
            protocols=["modbus_tcp"],
            vendor_fingerprint={"vendor": "Siemens"},
        )
        assert gen._should_snmp_discovery(device) is False

    def test_source_only_device_gets_snmp_scheduled(self):
        """A SCADA server (source-only) with fingerprint gets SNMP discovery."""
        device = _make_device(
            device_type="scada_server",
            vendor="Schneider",
            protocols=["modbus_tcp"],
            vendor_fingerprint={"vendor": "Schneider Electric", "model": "ClearSCADA"},
        )
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)
        types = scheduler.event_types()
        assert "ambient_snmp_discovery" in types


# ======================================================================
# SNMP identity synthesis tests
# ======================================================================


class TestSynthesizeSnmpIdentity:
    """Test _synthesize_snmp_identity helper."""

    def test_full_fingerprint_produces_rich_descr(self):
        device = _make_device(
            vendor="Schneider",
            device_name="WTP_SCADA_Server",
            vendor_fingerprint={
                "vendor": "Schneider Electric",
                "model": "ClearSCADA",
                "firmware_version": "V3.30",
            },
        )
        gen = BackgroundNoiseGenerator([device])
        result = gen._synthesize_snmp_identity(device)
        assert "Schneider Electric" in result["sys_descr"]
        assert "ClearSCADA" in result["sys_descr"]
        assert "V3.30" in result["sys_descr"]
        # Should NOT be Cisco OID
        assert result["sys_object_id"] != "1.3.6.1.4.1.9.1.1"
        assert "3833" in result["sys_object_id"]  # Schneider PEN
        assert result["sys_name"] == "WTP_SCADA_Server"

    def test_minimal_fingerprint_still_works(self):
        device = _make_device(
            vendor="GE",
            vendor_fingerprint={"vendor": "GE"},
        )
        gen = BackgroundNoiseGenerator([device])
        result = gen._synthesize_snmp_identity(device)
        assert result["sys_descr"] == "GE"
        assert result["sys_object_id"] != "1.3.6.1.4.1.9.1.1"

    def test_firmware_without_v_prefix_gets_prefixed(self):
        device = _make_device(
            vendor_fingerprint={
                "vendor": "Siemens",
                "model": "S7-1500",
                "firmware_version": "2.9.4",
            },
        )
        gen = BackgroundNoiseGenerator([device])
        result = gen._synthesize_snmp_identity(device)
        assert "V2.9.4" in result["sys_descr"]
        assert "Siemens" in result["sys_descr"]
        assert "S7-1500" in result["sys_descr"]

    def test_model_name_preferred_over_model(self):
        device = _make_device(
            vendor_fingerprint={
                "vendor": "Siemens",
                "model": "WinCC",
                "model_name": "SIMATIC WinCC Professional",
            },
        )
        gen = BackgroundNoiseGenerator([device])
        result = gen._synthesize_snmp_identity(device)
        assert "SIMATIC WinCC Professional" in result["sys_descr"]


# ======================================================================
# Vendor enterprise OID tests
# ======================================================================


class TestVendorEnterpriseOids:
    """Test enterprise OID lookup."""

    def test_known_vendors(self):
        from app.protocol_engines.vendor_oui import get_enterprise_oid_for_vendor
        assert "4329" in get_enterprise_oid_for_vendor("Siemens")
        assert "3833" in get_enterprise_oid_for_vendor("Schneider Electric")
        assert get_enterprise_oid_for_vendor("Cisco") == "1.3.6.1.4.1.9"

    def test_unknown_vendor_returns_default(self):
        from app.protocol_engines.vendor_oui import (
            DEFAULT_ENTERPRISE_OID,
            get_enterprise_oid_for_vendor,
        )
        assert get_enterprise_oid_for_vendor("unknown_vendor_xyz") == DEFAULT_ENTERPRISE_OID

    def test_case_insensitive(self):
        from app.protocol_engines.vendor_oui import get_enterprise_oid_for_vendor
        assert get_enterprise_oid_for_vendor("SIEMENS") == get_enterprise_oid_for_vendor("siemens")


# ======================================================================
# Discovery burst tests
# ======================================================================


class TestDiscoveryBurst:
    """Test early-burst discovery scheduling for faster CV fingerprinting."""

    def test_snmp_burst_events_scheduled(self):
        """SNMP discovery gets 2 extra burst events at ~30s and ~90s."""
        device = _make_device(
            device_type="plc",
            vendor="Siemens",
            protocols=["modbus_tcp"],
            vendor_fingerprint={"vendor": "Siemens"},
        )
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        snmp_events = [
            (t, e) for t, e in scheduler.events
            if e.get("type") == "ambient_snmp_discovery"
        ]
        # 1 regular + 2 burst = 3 initial SNMP events
        assert len(snmp_events) == 3
        burst_events = [e for _, e in snmp_events if e.get("burst")]
        assert len(burst_events) == 2

    def test_modbus_burst_events_scheduled(self):
        """Modbus discovery gets 2 extra burst events."""
        device = _make_device(
            device_type="plc",
            protocols=["modbus_tcp"],
            vendor_fingerprint={"vendor": "Schneider"},
        )
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        modbus_events = [
            (t, e) for t, e in scheduler.events
            if e.get("type") == "ambient_modbus_discovery"
        ]
        assert len(modbus_events) == 3
        burst_events = [e for _, e in modbus_events if e.get("burst")]
        assert len(burst_events) == 2

    def test_burst_events_fire_before_regular_interval(self):
        """Burst events are scheduled before the 300s regular interval."""
        device = _make_device(
            device_type="plc",
            protocols=["ethernet_ip"],
            vendor_fingerprint={"vendor": "Rockwell"},
        )
        gen = BackgroundNoiseGenerator([device])
        scheduler = FakeScheduler()
        gen.schedule_initial_events(scheduler, warmup_ms=500.0)

        enip_events = [
            (t, e) for t, e in scheduler.events
            if e.get("type") == "ambient_enip_discovery"
        ]
        burst_times = [t for t, e in enip_events if e.get("burst")]
        # Burst events should be at ~30s and ~90s (well under 300s)
        for t in burst_times:
            assert t < 100_000, f"Burst event at {t}ms should be < 100s"

    def test_burst_does_not_reschedule(self):
        """_reschedule skips when event has burst=True."""
        gen = BackgroundNoiseGenerator([_make_device()])
        scheduler = FakeScheduler()
        burst_event = {"type": "ambient_snmp_discovery", "device_id": "x", "burst": True}
        gen._reschedule(scheduler, 1000.0, 300.0, burst_event)
        assert len(scheduler.events) == 0, "Burst events must not reschedule"

    def test_regular_event_reschedules_normally(self):
        """_reschedule works normally for non-burst events."""
        gen = BackgroundNoiseGenerator([_make_device()])
        scheduler = FakeScheduler()
        regular_event = {"type": "ambient_snmp_discovery", "device_id": "x"}
        gen._reschedule(scheduler, 1000.0, 300.0, regular_event)
        assert len(scheduler.events) == 1, "Regular events must reschedule"
