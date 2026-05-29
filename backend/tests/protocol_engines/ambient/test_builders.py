# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for ambient broadcast packet builders (STP, DHCP, CDP, IGMP)."""

import struct


from app.protocol_engines.ambient.stp import (
    STP_MULTICAST_MAC,
    build_rstp_bpdu,
    build_stp_config_bpdu,
)
from app.protocol_engines.ambient.dhcp import (
    build_dhcp_ack,
    build_dhcp_discover,
    build_dhcp_offer,
    build_dhcp_request,
)
from app.protocol_engines.ambient.cdp import (
    CDP_MULTICAST_MAC,
    build_cdp_frame,
)
from app.protocol_engines.ambient.igmp import (
    build_igmpv2_report,
    _multicast_mac,
)


# ======================================================================
# STP Tests
# ======================================================================


class TestSTPBuilder:
    """STP/RSTP BPDU packet builder tests."""

    def test_stp_bpdu_returns_bytes(self):
        result = build_stp_config_bpdu(src_mac="00:1C:06:AA:BB:CC")
        assert isinstance(result, bytes)
        assert len(result) > 50  # Ethernet + LLC + BPDU minimum

    def test_stp_bpdu_destination_mac(self):
        result = build_stp_config_bpdu(src_mac="00:1C:06:AA:BB:CC")
        # First 6 bytes are destination MAC
        dst_mac = ":".join(f"{b:02x}" for b in result[:6])
        assert dst_mac == STP_MULTICAST_MAC.lower()

    def test_stp_bpdu_source_mac(self):
        result = build_stp_config_bpdu(src_mac="00:1C:06:AA:BB:CC")
        src_mac = ":".join(f"{b:02x}" for b in result[6:12])
        assert src_mac == "00:1c:06:aa:bb:cc"

    def test_stp_bpdu_llc_header(self):
        result = build_stp_config_bpdu(src_mac="00:1C:06:AA:BB:CC")
        # LLC starts after Ethernet header (14 bytes)
        assert result[14] == 0x42  # DSAP
        assert result[15] == 0x42  # SSAP
        assert result[16] == 0x03  # Control

    def test_stp_bpdu_protocol_id_and_version(self):
        result = build_stp_config_bpdu(src_mac="00:1C:06:AA:BB:CC")
        # BPDU starts at offset 17 (14 Ether + 3 LLC)
        bpdu_start = 17
        protocol_id = struct.unpack(">H", result[bpdu_start:bpdu_start + 2])[0]
        version = result[bpdu_start + 2]
        bpdu_type = result[bpdu_start + 3]
        assert protocol_id == 0x0000
        assert version == 0x00  # STP
        assert bpdu_type == 0x00  # Configuration BPDU

    def test_rstp_bpdu_version_2(self):
        result = build_rstp_bpdu(src_mac="00:1C:06:AA:BB:CC")
        bpdu_start = 17
        version = result[bpdu_start + 2]
        bpdu_type = result[bpdu_start + 3]
        assert version == 0x02  # RSTP
        assert bpdu_type == 0x02  # RST BPDU

    def test_rstp_bpdu_has_port_role(self):
        result = build_rstp_bpdu(
            src_mac="00:1C:06:AA:BB:CC",
            port_role=3,  # designated
        )
        bpdu_start = 17
        flags = result[bpdu_start + 4]
        # Port role in bits 2-3
        port_role = (flags >> 2) & 0x03
        assert port_role == 3

    def test_stp_with_custom_priority(self):
        result = build_stp_config_bpdu(
            src_mac="00:1C:06:AA:BB:CC",
            bridge_priority=4096,
        )
        assert isinstance(result, bytes)


# ======================================================================
# DHCP Tests
# ======================================================================


class TestDHCPBuilder:
    """DHCP DORA sequence packet builder tests."""

    def test_discover_returns_bytes(self):
        result = build_dhcp_discover(
            client_mac="00:1C:06:AA:BB:CC", xid=12345,
        )
        assert isinstance(result, bytes)
        assert len(result) > 300  # Ethernet + IP + UDP + BOOTP minimum

    def test_discover_broadcast_destination(self):
        result = build_dhcp_discover(
            client_mac="00:1C:06:AA:BB:CC", xid=12345,
        )
        dst_mac = ":".join(f"{b:02x}" for b in result[:6])
        assert dst_mac == "ff:ff:ff:ff:ff:ff"

    def test_discover_source_ip_zero(self):
        result = build_dhcp_discover(
            client_mac="00:1C:06:AA:BB:CC", xid=12345,
        )
        # IP header starts at offset 14, src IP at offset 14+12=26
        src_ip = ".".join(str(b) for b in result[26:30])
        assert src_ip == "0.0.0.0"

    def test_discover_dest_ip_broadcast(self):
        result = build_dhcp_discover(
            client_mac="00:1C:06:AA:BB:CC", xid=12345,
        )
        dst_ip = ".".join(str(b) for b in result[30:34])
        assert dst_ip == "255.255.255.255"

    def test_offer_returns_bytes(self):
        result = build_dhcp_offer(
            server_mac="02:00:00:00:00:01",
            server_ip="10.1.0.1",
            client_mac="00:1C:06:AA:BB:CC",
            offered_ip="10.1.0.100",
            xid=12345,
        )
        assert isinstance(result, bytes)

    def test_request_returns_bytes(self):
        result = build_dhcp_request(
            client_mac="00:1C:06:AA:BB:CC",
            xid=12345,
            requested_ip="10.1.0.100",
            server_ip="10.1.0.1",
        )
        assert isinstance(result, bytes)

    def test_ack_returns_bytes(self):
        result = build_dhcp_ack(
            server_mac="02:00:00:00:00:01",
            server_ip="10.1.0.1",
            client_mac="00:1C:06:AA:BB:CC",
            assigned_ip="10.1.0.100",
            xid=12345,
        )
        assert isinstance(result, bytes)

    def test_discover_udp_ports(self):
        result = build_dhcp_discover(
            client_mac="00:1C:06:AA:BB:CC", xid=12345,
        )
        # UDP header after IP header (20 bytes) at offset 34
        src_port = struct.unpack(">H", result[34:36])[0]
        dst_port = struct.unpack(">H", result[36:38])[0]
        assert src_port == 68
        assert dst_port == 67

    def test_offer_udp_ports(self):
        result = build_dhcp_offer(
            server_mac="02:00:00:00:00:01",
            server_ip="10.1.0.1",
            client_mac="00:1C:06:AA:BB:CC",
            offered_ip="10.1.0.100",
            xid=12345,
        )
        src_port = struct.unpack(">H", result[34:36])[0]
        dst_port = struct.unpack(">H", result[36:38])[0]
        assert src_port == 67
        assert dst_port == 68

    def test_dhcp_magic_cookie_present(self):
        result = build_dhcp_discover(
            client_mac="00:1C:06:AA:BB:CC", xid=12345,
        )
        # BOOTP starts at offset 42 (14 Ether + 20 IP + 8 UDP)
        # Magic cookie at BOOTP offset 236
        magic_offset = 42 + 236
        magic = result[magic_offset:magic_offset + 4]
        assert magic == b"\x63\x82\x53\x63"

    def test_discover_with_hostname(self):
        result = build_dhcp_discover(
            client_mac="00:1C:06:AA:BB:CC",
            xid=12345,
            hostname="HMI-01",
        )
        assert isinstance(result, bytes)
        # Option 12 (hostname) should be present somewhere in options
        assert b"HMI-01" in result


# ======================================================================
# CDP Tests
# ======================================================================


class TestCDPBuilder:
    """Cisco CDP frame builder tests."""

    def test_cdp_returns_bytes(self):
        result = build_cdp_frame(
            src_mac="00:1E:14:AA:BB:CC",
            device_id="Switch-01",
            ip_address="10.1.0.1",
        )
        assert isinstance(result, bytes)
        assert len(result) > 50

    def test_cdp_destination_mac(self):
        result = build_cdp_frame(
            src_mac="00:1E:14:AA:BB:CC",
            device_id="Switch-01",
            ip_address="10.1.0.1",
        )
        dst_mac = ":".join(f"{b:02x}" for b in result[:6])
        assert dst_mac == CDP_MULTICAST_MAC.lower()

    def test_cdp_source_mac(self):
        result = build_cdp_frame(
            src_mac="00:1E:14:AA:BB:CC",
            device_id="Switch-01",
            ip_address="10.1.0.1",
        )
        src_mac = ":".join(f"{b:02x}" for b in result[6:12])
        assert src_mac == "00:1e:14:aa:bb:cc"

    def test_cdp_contains_device_id(self):
        result = build_cdp_frame(
            src_mac="00:1E:14:AA:BB:CC",
            device_id="Switch-01",
            ip_address="10.1.0.1",
        )
        assert b"Switch-01" in result

    def test_cdp_contains_platform(self):
        result = build_cdp_frame(
            src_mac="00:1E:14:AA:BB:CC",
            device_id="Switch-01",
            ip_address="10.1.0.1",
            platform="cisco IE-3400-8T2S",
        )
        assert b"cisco IE-3400" in result

    def test_cdp_contains_software_version(self):
        result = build_cdp_frame(
            src_mac="00:1E:14:AA:BB:CC",
            device_id="Switch-01",
            ip_address="10.1.0.1",
            software_version="IOS XE 17.3.3",
        )
        assert b"IOS XE 17.3.3" in result

    def test_cdp_with_vlan(self):
        result = build_cdp_frame(
            src_mac="00:1E:14:AA:BB:CC",
            device_id="Switch-01",
            ip_address="10.1.0.1",
            vlan_id=100,
        )
        assert isinstance(result, bytes)

    def test_cdp_version_2(self):
        result = build_cdp_frame(
            src_mac="00:1E:14:AA:BB:CC",
            device_id="Switch-01",
            ip_address="10.1.0.1",
        )
        # CDP payload starts after 802.3 + LLC + SNAP headers
        # Find CDPv2 marker (version byte = 0x02) in payload
        assert b"\x02" in result


# ======================================================================
# IGMP Tests
# ======================================================================


class TestIGMPBuilder:
    """IGMPv2 membership report builder tests."""

    def test_igmp_report_returns_bytes(self):
        result = build_igmpv2_report(
            src_mac="00:1C:06:AA:BB:CC",
            src_ip="10.1.0.100",
            group_ip="224.0.0.1",
        )
        assert isinstance(result, bytes)

    def test_igmp_multicast_destination_mac(self):
        result = build_igmpv2_report(
            src_mac="00:1C:06:AA:BB:CC",
            src_ip="10.1.0.100",
            group_ip="224.0.0.1",
        )
        # Multicast MAC for 224.0.0.1 = 01:00:5E:00:00:01
        dst_mac = ":".join(f"{b:02x}" for b in result[:6])
        assert dst_mac == "01:00:5e:00:00:01"

    def test_igmp_ttl_is_1(self):
        result = build_igmpv2_report(
            src_mac="00:1C:06:AA:BB:CC",
            src_ip="10.1.0.100",
            group_ip="224.0.0.1",
        )
        # IP TTL is at offset 14 + 8 = 22
        ttl = result[22]
        assert ttl == 1

    def test_igmp_protocol_is_2(self):
        result = build_igmpv2_report(
            src_mac="00:1C:06:AA:BB:CC",
            src_ip="10.1.0.100",
            group_ip="224.0.0.1",
        )
        # IP protocol at offset 14 + 9 = 23
        proto = result[23]
        assert proto == 2

    def test_multicast_mac_derivation(self):
        assert _multicast_mac("224.0.0.1") == "01:00:5E:00:00:01"
        assert _multicast_mac("239.255.255.250") == "01:00:5E:7f:ff:fa"

    def test_igmp_report_type(self):
        result = build_igmpv2_report(
            src_mac="00:1C:06:AA:BB:CC",
            src_ip="10.1.0.100",
            group_ip="224.0.0.2",
        )
        # Find IGMP payload — after IP header (which may have options)
        # IP header length is in nibble at offset 14
        ihl = (result[14] & 0x0F) * 4
        igmp_offset = 14 + ihl
        igmp_type = result[igmp_offset]
        assert igmp_type == 0x16  # IGMPv2 Membership Report
