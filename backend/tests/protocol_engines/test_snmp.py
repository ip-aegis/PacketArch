# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for SNMP/NTCIP protocol engine."""

import pytest
from unittest.mock import MagicMock, patch

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.types import (
    ConversationState,
    DeviceContext,
    FlowContext,
    PacketEvent,
    ProtocolType,
)
from app.protocol_engines.snmp.engine import SnmpEngine
from app.protocol_engines.snmp.types import (
    SNMP_AGENT_PORT,
    SNMP_TRAP_PORT,
    SNMPErrorStatus,
    SNMPFlowConfig,
    SNMPOperation,
    SNMPState,
    SNMPValueType,
    SNMPVersion,
    VarBind,
    GenericTrapType,
    SNMPv3Credentials,
    SNMPv3SecurityLevel,
    SNMPv3AuthProtocol,
    SNMPv3PrivProtocol,
)
from app.protocol_engines.snmp.oids import (
    DISCOVERY_OIDS,
    DMS_POLL_OIDS,
    TRAFFIC_CONTROLLER_POLL_OIDS,
    SystemOIDs,
    encode_oid,
    decode_oid,
    is_child_of,
    get_next_oid,
    MIB2,
    NTCIP_ASC,
    NTCIP_DMS,
)
from app.protocol_engines.snmp.packets import (
    build_snmp_get_request,
    build_snmp_get_response,
    build_snmp_get_request_packet,
    build_snmp_get_response_packet,
    build_snmp_trap_packet,
    build_snmp_trap_v1,
    build_snmp_trap_v2c,
    build_snmp_get_next_request,
    build_snmp_get_bulk_request,
    build_snmp_set_request,
    generate_engine_id,
    build_snmpv3_header,
    build_snmpv3_usm_params,
    build_snmpv3_scoped_pdu,
    build_snmpv3_message,
    build_snmpv3_get_request,
    build_snmpv3_get_response,
    build_snmpv3_get_request_packet,
    build_snmpv3_get_response_packet,
    _value_to_asn1,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def engine():
    """Create SNMP engine instance."""
    return SnmpEngine()


@pytest.fixture
def mock_applicator():
    """Create a mock fingerprint applicator."""
    applicator = MagicMock()
    applicator.get_sys_descr.return_value = "Econolite ASC/3-2100 Version 3.28.1"
    applicator.get_sys_object_id.return_value = "1.3.6.1.4.1.1206.4.2.2"
    applicator.should_timeout.return_value = False

    # Mock response delay
    delay_sample = MagicMock()
    delay_sample.delay_ms = 15.0
    delay_sample.is_timeout = False
    applicator.get_response_delay.return_value = delay_sample

    return applicator


@pytest.fixture
def source_device():
    """Create source device (SNMP manager)."""
    return DeviceContext(
        device_id="manager-01",
        mac_address="00:11:22:33:44:55",
        ip_address="10.1.0.10",
        port=49152,
        vendor_fingerprint={
            "vendor": "PacketArch",
            "tcp_stack": {"ttl": 64, "window_size": 65535},
        },
    )


@pytest.fixture
def destination_device(mock_applicator):
    """Create destination device (SNMP agent)."""
    device = DeviceContext(
        device_id="tc-001",
        mac_address="00:AA:BB:CC:DD:EE",
        ip_address="10.1.0.100",
        port=SNMP_AGENT_PORT,
        device_name="TC-Intersection-Main",
        vendor_fingerprint={
            "vendor": "Econolite",
            "model": "ASC/3-2100",
            "firmware_version": "3.28.1",
            "snmp_identity": {
                "sys_descr": "Econolite ASC/3-2100 Version 3.28.1",
                "sys_object_id": "1.3.6.1.4.1.1206.4.2.2",
                "sys_name": "TC-Intersection-Main",
                "sys_location": "Main St & 1st Ave",
                "sys_contact": "traffic-ops@city.gov",
            },
            "tcp_stack": {"ttl": 64, "window_size": 8192},
        },
    )
    device._fingerprint_applicator = mock_applicator
    return device


@pytest.fixture
def flow_context(source_device, destination_device):
    """Create SNMP flow context with default v2c config."""
    return FlowContext(
        flow_id="snmp-flow-01",
        source=source_device,
        destination=destination_device,
        protocol=ProtocolType.SNMP,
        config={
            "community": "public",
            "snmp_version": "v2c",
            "device_type": "traffic_controller",
            "timeout_ms": 5000,
        },
        timing_model={"type": "gaussian", "mean_ms": 15, "std_ms": 3},
    )


@pytest.fixture
def v3_flow_context(source_device, destination_device):
    """Create SNMP flow context with SNMPv3 config."""
    return FlowContext(
        flow_id="snmp-v3-flow-01",
        source=source_device,
        destination=destination_device,
        protocol=ProtocolType.SNMP,
        config={
            "snmp_version": "v3",
            "device_type": "traffic_controller",
            "timeout_ms": 5000,
            "v3_credentials": {
                "username": "admin",
                "security_level": "authPriv",
                "auth_protocol": "sha",
                "auth_password": "authpass123",
                "priv_protocol": "aes",
                "priv_password": "privpass123",
            },
        },
        timing_model={"type": "gaussian", "mean_ms": 15, "std_ms": 3},
    )


# =============================================================================
# Engine Registration Tests
# =============================================================================


class TestSnmpEngineRegistry:
    """Test SNMP engine registration."""

    def test_snmp_registered(self):
        """Test that SNMP engine is registered."""
        protocols = list_supported_protocols()
        assert ProtocolType.SNMP in protocols

    def test_get_snmp_engine(self):
        """Test getting SNMP engine instance."""
        engine = get_engine(ProtocolType.SNMP)
        assert isinstance(engine, SnmpEngine)
        assert engine.protocol_type == ProtocolType.SNMP


# =============================================================================
# SNMP Types Tests
# =============================================================================


class TestSnmpTypes:
    """Test SNMP type definitions and constants."""

    def test_snmp_version_values(self):
        """Test SNMP version enum integer values."""
        assert SNMPVersion.V1 == 0
        assert SNMPVersion.V2C == 1
        assert SNMPVersion.V3 == 3

    def test_snmp_operation_values(self):
        """Test SNMP operation PDU type tags."""
        assert SNMPOperation.GET_REQUEST == 0xA0
        assert SNMPOperation.GET_NEXT_REQUEST == 0xA1
        assert SNMPOperation.GET_RESPONSE == 0xA2
        assert SNMPOperation.SET_REQUEST == 0xA3
        assert SNMPOperation.TRAP_V1 == 0xA4
        assert SNMPOperation.GET_BULK_REQUEST == 0xA5
        assert SNMPOperation.TRAP_V2 == 0xA7

    def test_snmp_error_status_values(self):
        """Test SNMP error status codes."""
        assert SNMPErrorStatus.NO_ERROR == 0
        assert SNMPErrorStatus.TOO_BIG == 1
        assert SNMPErrorStatus.NO_SUCH_NAME == 2
        assert SNMPErrorStatus.BAD_VALUE == 3
        assert SNMPErrorStatus.GEN_ERR == 5

    def test_snmp_state_values(self):
        """Test SNMP conversation state values."""
        assert SNMPState.IDLE == "idle"
        assert SNMPState.DISCOVERING == "discovering"
        assert SNMPState.POLLING == "polling"
        assert SNMPState.AWAITING_RESPONSE == "awaiting"
        assert SNMPState.TRAP_SENDING == "trap_sending"

    def test_port_constants(self):
        """Test SNMP port constants."""
        assert SNMP_AGENT_PORT == 161
        assert SNMP_TRAP_PORT == 162

    def test_generic_trap_types(self):
        """Test SNMPv1 generic trap type values."""
        assert GenericTrapType.COLD_START == 0
        assert GenericTrapType.WARM_START == 1
        assert GenericTrapType.LINK_DOWN == 2
        assert GenericTrapType.LINK_UP == 3
        assert GenericTrapType.AUTHENTICATION_FAILURE == 4
        assert GenericTrapType.ENTERPRISE_SPECIFIC == 6


class TestVarBind:
    """Test SNMP VarBind dataclass auto-detection."""

    def test_auto_detect_integer(self):
        """Test auto-detection of integer values."""
        vb = VarBind(oid="1.3.6.1.2.1.1.7.0", value=72)
        assert vb.value_type == "integer"

    def test_auto_detect_string(self):
        """Test auto-detection of string values."""
        vb = VarBind(oid="1.3.6.1.2.1.1.1.0", value="Econolite ASC/3-2100")
        assert vb.value_type == "string"

    def test_auto_detect_null(self):
        """Test auto-detection of null values."""
        vb = VarBind(oid="1.3.6.1.2.1.1.1.0", value=None)
        assert vb.value_type == "null"

    def test_auto_detect_ip_address(self):
        """Test auto-detection of IP address values."""
        vb = VarBind(oid="1.3.6.1.2.1.4.20.1.1.10.1.0.100", value="10.1.0.100")
        assert vb.value_type == "ipaddress"

    def test_auto_detect_oid(self):
        """Test auto-detection of OID values (not IP-like)."""
        vb = VarBind(oid="1.3.6.1.2.1.1.2.0", value="1.3.6.1.4.1.1206.4.2.2")
        assert vb.value_type == "oid"

    def test_explicit_type_override(self):
        """Test that explicit type overrides auto-detection."""
        vb = VarBind(oid="1.3.6.1.2.1.1.3.0", value=12345, value_type="timeticks")
        assert vb.value_type == "timeticks"

    def test_auto_detect_bytes(self):
        """Test auto-detection of bytes values."""
        vb = VarBind(oid="1.3.6.1.2.1.2.2.1.6.1", value=b"\x00\xAA\xBB\xCC\xDD\xEE")
        assert vb.value_type == "opaque"


class TestSNMPv3Types:
    """Test SNMPv3-specific type definitions."""

    def test_security_levels(self):
        """Test SNMPv3 security level values."""
        assert SNMPv3SecurityLevel.NO_AUTH_NO_PRIV == 1
        assert SNMPv3SecurityLevel.AUTH_NO_PRIV == 2
        assert SNMPv3SecurityLevel.AUTH_PRIV == 3

    def test_auth_protocols(self):
        """Test SNMPv3 auth protocol values."""
        assert SNMPv3AuthProtocol.NONE == "none"
        assert SNMPv3AuthProtocol.MD5 == "md5"
        assert SNMPv3AuthProtocol.SHA == "sha"
        assert SNMPv3AuthProtocol.SHA256 == "sha256"

    def test_priv_protocols(self):
        """Test SNMPv3 privacy protocol values."""
        assert SNMPv3PrivProtocol.NONE == "none"
        assert SNMPv3PrivProtocol.DES == "des"
        assert SNMPv3PrivProtocol.AES128 == "aes128"
        assert SNMPv3PrivProtocol.AES256 == "aes256"

    def test_credentials_validation_valid(self):
        """Test valid SNMPv3 credentials pass validation."""
        creds = SNMPv3Credentials(
            username="admin",
            security_level=SNMPv3SecurityLevel.AUTH_NO_PRIV,
            auth_protocol=SNMPv3AuthProtocol.SHA,
            auth_password="authpass123",
        )
        errors = creds.validate()
        assert errors == []

    def test_credentials_validation_missing_username(self):
        """Test that empty username fails validation."""
        creds = SNMPv3Credentials(
            username="",
            security_level=SNMPv3SecurityLevel.NO_AUTH_NO_PRIV,
        )
        errors = creds.validate()
        assert any("username" in e for e in errors)

    def test_credentials_validation_missing_auth_password(self):
        """Test that auth level without password fails validation."""
        creds = SNMPv3Credentials(
            username="admin",
            security_level=SNMPv3SecurityLevel.AUTH_NO_PRIV,
            auth_protocol=SNMPv3AuthProtocol.SHA,
            auth_password=None,
        )
        errors = creds.validate()
        assert any("auth_password" in e for e in errors)

    def test_credentials_validation_missing_priv_password(self):
        """Test that authPriv level without priv password fails validation."""
        creds = SNMPv3Credentials(
            username="admin",
            security_level=SNMPv3SecurityLevel.AUTH_PRIV,
            auth_protocol=SNMPv3AuthProtocol.SHA,
            auth_password="authpass",
            priv_protocol=SNMPv3PrivProtocol.AES128,
            priv_password=None,
        )
        errors = creds.validate()
        assert any("priv_password" in e for e in errors)

    def test_credentials_noauth_nopriv_valid(self):
        """Test noAuthNoPriv credentials pass validation."""
        creds = SNMPv3Credentials(
            username="readonly",
            security_level=SNMPv3SecurityLevel.NO_AUTH_NO_PRIV,
        )
        errors = creds.validate()
        assert errors == []

    def test_flow_config_defaults(self):
        """Test SNMPFlowConfig default values."""
        config = SNMPFlowConfig()
        assert config.community == "public"
        assert config.version == SNMPVersion.V2C
        assert config.timeout_ms == 5000
        assert config.retries == 2
        assert config.poll_oids == []
        assert config.bulk_max_repetitions == 10
        assert config.v3_credentials is None


# =============================================================================
# OID Tests
# =============================================================================


class TestOIDs:
    """Test OID definitions and utilities."""

    def test_system_oid_values(self):
        """Test standard MIB-II system OID values."""
        assert SystemOIDs.SYS_DESCR.oid == f"{MIB2}.1.1.0"
        assert SystemOIDs.SYS_OBJECT_ID.oid == f"{MIB2}.1.2.0"
        assert SystemOIDs.SYS_UPTIME.oid == f"{MIB2}.1.3.0"
        assert SystemOIDs.SYS_NAME.oid == f"{MIB2}.1.5.0"
        assert SystemOIDs.SYS_LOCATION.oid == f"{MIB2}.1.6.0"
        assert SystemOIDs.SYS_SERVICES.oid == f"{MIB2}.1.7.0"

    def test_discovery_oids_content(self):
        """Test discovery OIDs list contains expected OIDs."""
        assert SystemOIDs.SYS_DESCR.oid in DISCOVERY_OIDS
        assert SystemOIDs.SYS_OBJECT_ID.oid in DISCOVERY_OIDS
        assert SystemOIDs.SYS_UPTIME.oid in DISCOVERY_OIDS
        assert SystemOIDs.SYS_NAME.oid in DISCOVERY_OIDS
        assert SystemOIDs.SYS_LOCATION.oid in DISCOVERY_OIDS
        assert len(DISCOVERY_OIDS) == 5

    def test_traffic_controller_poll_oids(self):
        """Test NTCIP 1202 traffic controller OIDs are defined."""
        assert len(TRAFFIC_CONTROLLER_POLL_OIDS) > 0
        for oid in TRAFFIC_CONTROLLER_POLL_OIDS:
            assert oid.startswith("1.3.6.1.4.1.1206.4.2.2")

    def test_dms_poll_oids(self):
        """Test NTCIP 1203 DMS OIDs are defined."""
        assert len(DMS_POLL_OIDS) > 0
        for oid in DMS_POLL_OIDS:
            assert oid.startswith("1.3.6.1.4.1.1206.4.2.3")

    def test_encode_oid_simple(self):
        """Test OID encoding for a simple OID."""
        encoded = encode_oid("1.3.6.1.2.1.1.1.0")
        assert isinstance(encoded, bytes)
        assert len(encoded) > 0
        # First byte = 1*40 + 3 = 43 = 0x2B
        assert encoded[0] == 0x2B

    def test_encode_oid_with_large_value(self):
        """Test OID encoding with values >= 128."""
        encoded = encode_oid("1.3.6.1.4.1.1206")
        assert isinstance(encoded, bytes)
        # 1206 requires multi-byte encoding
        assert len(encoded) > 6

    def test_encode_decode_roundtrip(self):
        """Test OID encode/decode roundtrip preserves value."""
        oid = "1.3.6.1.2.1.1.1.0"
        encoded = encode_oid(oid)
        decoded = decode_oid(encoded)
        assert decoded == oid

    def test_encode_decode_roundtrip_large(self):
        """Test OID encode/decode roundtrip with large values."""
        oid = "1.3.6.1.4.1.1206.4.2.2"
        encoded = encode_oid(oid)
        decoded = decode_oid(encoded)
        assert decoded == oid

    def test_encode_oid_invalid(self):
        """Test OID encoding rejects invalid OIDs."""
        with pytest.raises(ValueError):
            encode_oid("1")

    def test_is_child_of_true(self):
        """Test is_child_of returns True for actual children."""
        assert is_child_of("1.3.6.1.2.1.1.1.0", "1.3.6.1.2.1.1")
        assert is_child_of("1.3.6.1.4.1.1206.4.2.2.1.4.1.0", "1.3.6.1.4.1.1206")

    def test_is_child_of_false(self):
        """Test is_child_of returns False for non-children."""
        assert not is_child_of("1.3.6.1.4.1", "1.3.6.1.2.1")
        assert not is_child_of("1.3.6.1.2.1.2", "1.3.6.1.2.1.1")

    def test_is_child_of_same(self):
        """Test is_child_of returns True for equal OIDs."""
        assert is_child_of("1.3.6.1.2.1.1", "1.3.6.1.2.1.1")

    def test_get_next_oid(self):
        """Test get_next_oid returns lexicographically next OID."""
        tree = [
            "1.3.6.1.2.1.1.1.0",
            "1.3.6.1.2.1.1.2.0",
            "1.3.6.1.2.1.1.3.0",
        ]
        result = get_next_oid("1.3.6.1.2.1.1.1.0", tree)
        assert result == "1.3.6.1.2.1.1.2.0"

    def test_get_next_oid_end(self):
        """Test get_next_oid returns None at end of tree."""
        tree = ["1.3.6.1.2.1.1.1.0", "1.3.6.1.2.1.1.2.0"]
        result = get_next_oid("1.3.6.1.2.1.1.2.0", tree)
        assert result is None


# =============================================================================
# Packet Building Tests
# =============================================================================


class TestSnmpPackets:
    """Test SNMP packet building functions."""

    def test_build_snmp_get_request(self):
        """Test building raw SNMP GetRequest PDU."""
        pdu_bytes = build_snmp_get_request(
            community="public",
            request_id=12345,
            oids=["1.3.6.1.2.1.1.1.0"],
            version=SNMPVersion.V2C,
        )
        assert isinstance(pdu_bytes, bytes)
        assert len(pdu_bytes) > 0
        # SNMP messages start with SEQUENCE tag (0x30)
        assert pdu_bytes[0] == 0x30

    def test_build_snmp_get_request_v1(self):
        """Test building SNMPv1 GetRequest PDU."""
        pdu_bytes = build_snmp_get_request(
            community="public",
            request_id=1,
            oids=["1.3.6.1.2.1.1.1.0"],
            version=SNMPVersion.V1,
        )
        assert isinstance(pdu_bytes, bytes)
        assert pdu_bytes[0] == 0x30

    def test_build_snmp_get_request_multiple_oids(self):
        """Test building GetRequest with multiple OIDs."""
        oids = [
            "1.3.6.1.2.1.1.1.0",
            "1.3.6.1.2.1.1.2.0",
            "1.3.6.1.2.1.1.3.0",
        ]
        pdu_bytes = build_snmp_get_request(
            community="public",
            request_id=100,
            oids=oids,
        )
        assert isinstance(pdu_bytes, bytes)
        assert len(pdu_bytes) > 0

    def test_build_snmp_get_response(self):
        """Test building raw SNMP GetResponse PDU."""
        varbinds = [
            VarBind(oid="1.3.6.1.2.1.1.1.0", value="Test Device", value_type="string"),
        ]
        pdu_bytes = build_snmp_get_response(
            community="public",
            request_id=12345,
            varbinds=varbinds,
        )
        assert isinstance(pdu_bytes, bytes)
        assert pdu_bytes[0] == 0x30

    def test_build_snmp_get_response_with_error(self):
        """Test building GetResponse with error status."""
        varbinds = [
            VarBind(oid="1.3.6.1.2.1.1.1.0", value=None, value_type="null"),
        ]
        pdu_bytes = build_snmp_get_response(
            community="public",
            request_id=12345,
            varbinds=varbinds,
            error_status=2,  # noSuchName
            error_index=1,
        )
        assert isinstance(pdu_bytes, bytes)
        assert len(pdu_bytes) > 0

    def test_build_snmp_get_next_request(self):
        """Test building SNMP GetNextRequest PDU."""
        pdu_bytes = build_snmp_get_next_request(
            community="public",
            request_id=100,
            oids=["1.3.6.1.2.1.1"],
        )
        assert isinstance(pdu_bytes, bytes)
        assert pdu_bytes[0] == 0x30

    def test_build_snmp_get_bulk_request(self):
        """Test building SNMP GetBulkRequest PDU."""
        pdu_bytes = build_snmp_get_bulk_request(
            community="public",
            request_id=200,
            oids=["1.3.6.1.2.1.2.2.1"],
            non_repeaters=0,
            max_repetitions=10,
        )
        assert isinstance(pdu_bytes, bytes)
        assert pdu_bytes[0] == 0x30

    def test_build_snmp_set_request(self):
        """Test building SNMP SetRequest PDU."""
        varbinds = [
            VarBind(oid="1.3.6.1.2.1.1.5.0", value="NewName", value_type="string"),
        ]
        pdu_bytes = build_snmp_set_request(
            community="private",
            request_id=300,
            varbinds=varbinds,
        )
        assert isinstance(pdu_bytes, bytes)
        assert pdu_bytes[0] == 0x30

    def test_build_snmp_get_request_packet(self):
        """Test building complete SNMP GetRequest packet with headers."""
        packet = build_snmp_get_request_packet(
            src_mac="00:11:22:33:44:55",
            dst_mac="00:AA:BB:CC:DD:EE",
            src_ip="10.1.0.10",
            dst_ip="10.1.0.100",
            src_port=49152,
            dst_port=SNMP_AGENT_PORT,
            community="public",
            request_id=12345,
            oids=["1.3.6.1.2.1.1.1.0"],
        )
        assert isinstance(packet, bytes)
        # Should have Ethernet(14) + IP(20) + UDP(8) + SNMP payload
        assert len(packet) > 42

    def test_build_snmp_get_response_packet(self):
        """Test building complete SNMP GetResponse packet with headers."""
        var_binds = [
            VarBind(oid="1.3.6.1.2.1.1.1.0", value="Test Device", value_type="string"),
        ]
        packet = build_snmp_get_response_packet(
            src_mac="00:AA:BB:CC:DD:EE",
            dst_mac="00:11:22:33:44:55",
            src_ip="10.1.0.100",
            dst_ip="10.1.0.10",
            src_port=SNMP_AGENT_PORT,
            dst_port=49152,
            community="public",
            request_id=12345,
            var_binds=var_binds,
        )
        assert isinstance(packet, bytes)
        assert len(packet) > 42

    @pytest.mark.xfail(
        reason="Scapy SNMPtrapv1 time_stamp requires ASN1_TIME_TICKS, not ASN1_INTEGER"
    )
    def test_build_snmp_trap_v1(self):
        """Test building SNMPv1 trap PDU."""
        trap_bytes = build_snmp_trap_v1(
            community="public",
            enterprise_oid="1.3.6.1.4.1.1206.4.2.2",
            agent_addr="10.1.0.100",
            generic_trap=3,  # linkUp
            specific_trap=0,
            timestamp=100000,
        )
        assert isinstance(trap_bytes, bytes)
        assert trap_bytes[0] == 0x30

    def test_build_snmp_trap_v2c(self):
        """Test building SNMPv2c trap PDU."""
        trap_bytes = build_snmp_trap_v2c(
            community="public",
            request_id=500,
            uptime=100000,
            trap_oid="1.3.6.1.6.3.1.1.5.4",  # linkUp
        )
        assert isinstance(trap_bytes, bytes)
        assert trap_bytes[0] == 0x30

    def test_build_snmp_trap_v2c_with_varbinds(self):
        """Test building SNMPv2c trap with additional varbinds."""
        extra_varbinds = [
            VarBind(oid="1.3.6.1.2.1.2.2.1.8.1", value=1, value_type="integer"),
        ]
        trap_bytes = build_snmp_trap_v2c(
            community="public",
            request_id=501,
            uptime=100000,
            trap_oid="1.3.6.1.6.3.1.1.5.4",
            varbinds=extra_varbinds,
        )
        assert isinstance(trap_bytes, bytes)
        assert len(trap_bytes) > 0

    @pytest.mark.xfail(
        reason="Scapy SNMPtrapv1 time_stamp requires ASN1_TIME_TICKS, not ASN1_INTEGER"
    )
    def test_build_snmp_trap_packet_v1(self):
        """Test building complete SNMPv1 trap packet."""
        packet = build_snmp_trap_packet(
            src_mac="00:AA:BB:CC:DD:EE",
            dst_mac="00:11:22:33:44:55",
            src_ip="10.1.0.100",
            dst_ip="10.1.0.10",
            community="public",
            trap_type="linkUp",
            enterprise_oid="1.3.6.1.4.1.1206.4.2.2",
            uptime_ticks=100000,
            version=SNMPVersion.V1,
        )
        assert isinstance(packet, bytes)
        assert len(packet) > 42

    def test_build_snmp_trap_packet_v2c(self):
        """Test building complete SNMPv2c trap packet."""
        packet = build_snmp_trap_packet(
            src_mac="00:AA:BB:CC:DD:EE",
            dst_mac="00:11:22:33:44:55",
            src_ip="10.1.0.100",
            dst_ip="10.1.0.10",
            community="public",
            trap_type="1.3.6.1.6.3.1.1.5.4",
            enterprise_oid="1.3.6.1.4.1.1206.4.2.2",
            uptime_ticks=100000,
            version=SNMPVersion.V2C,
        )
        assert isinstance(packet, bytes)
        assert len(packet) > 42


class TestSnmpValueConversion:
    """Test SNMP value to ASN.1 conversion."""

    def test_convert_null(self):
        """Test null value conversion."""
        result = _value_to_asn1(None, "null")
        assert result is not None

    def test_convert_integer(self):
        """Test integer value conversion."""
        result = _value_to_asn1(42, "integer")
        assert result is not None

    def test_convert_string(self):
        """Test string value conversion."""
        result = _value_to_asn1("test device", "string")
        assert result is not None

    def test_convert_oid(self):
        """Test OID value conversion."""
        result = _value_to_asn1("1.3.6.1.4.1.1206", "oid")
        assert result is not None

    def test_convert_ipaddress(self):
        """Test IP address value conversion."""
        result = _value_to_asn1("10.1.0.100", "ipaddress")
        assert result is not None

    def test_convert_timeticks(self):
        """Test timeticks value conversion."""
        result = _value_to_asn1(100000, "timeticks")
        assert result is not None

    def test_convert_counter(self):
        """Test counter value conversion."""
        result = _value_to_asn1(999, "counter")
        assert result is not None

    def test_convert_gauge(self):
        """Test gauge value conversion."""
        result = _value_to_asn1(50, "gauge")
        assert result is not None

    def test_convert_auto_integer(self):
        """Test auto-detection of integer for conversion."""
        result = _value_to_asn1(42, "auto")
        assert result is not None

    def test_convert_auto_string(self):
        """Test auto-detection of string for conversion."""
        result = _value_to_asn1("hello", "auto")
        assert result is not None


# =============================================================================
# SNMPv3 Packet Tests
# =============================================================================


class TestSnmpV3Packets:
    """Test SNMPv3-specific packet building."""

    def test_generate_engine_id(self):
        """Test engine ID generation from IP address."""
        engine_id = generate_engine_id("10.1.0.100")
        assert isinstance(engine_id, bytes)
        # Enterprise (4 bytes) + Format (1 byte) + IP (4 bytes) = 9 bytes
        assert len(engine_id) == 9
        # High bit set in enterprise number
        assert engine_id[0] & 0x80 == 0x80
        # Format byte = 0x01 (IPv4)
        assert engine_id[4] == 0x01
        # IP address bytes at the end
        assert engine_id[5] == 10
        assert engine_id[6] == 1
        assert engine_id[7] == 0
        assert engine_id[8] == 100

    def test_generate_engine_id_different_ips(self):
        """Test engine IDs are different for different IPs."""
        eid1 = generate_engine_id("10.1.0.1")
        eid2 = generate_engine_id("10.1.0.2")
        assert eid1 != eid2

    def test_build_snmpv3_header(self):
        """Test SNMPv3 header building."""
        header = build_snmpv3_header(
            message_id=1000,
            max_size=65507,
            flags=0x05,  # auth + reportable
            security_model=3,
        )
        assert isinstance(header, bytes)
        # Should be a SEQUENCE (0x30)
        assert header[0] == 0x30

    def test_build_snmpv3_usm_params(self):
        """Test SNMPv3 USM security parameters building."""
        engine_id = generate_engine_id("10.1.0.100")
        params = build_snmpv3_usm_params(
            engine_id=engine_id,
            engine_boots=1,
            engine_time=1000,
            username="admin",
        )
        assert isinstance(params, bytes)
        # Should be an OCTET STRING (0x04)
        assert params[0] == 0x04

    def test_build_snmpv3_scoped_pdu(self):
        """Test SNMPv3 scoped PDU building."""
        engine_id = generate_engine_id("10.1.0.100")
        pdu = build_snmpv3_scoped_pdu(
            context_engine_id=engine_id,
            context_name="",
            pdu=b"\xa0\x0c\x02\x01\x00\x02\x01\x00\x02\x01\x00\x30\x00",
        )
        assert isinstance(pdu, bytes)
        # Should be a SEQUENCE (0x30)
        assert pdu[0] == 0x30

    def test_build_snmpv3_get_request(self):
        """Test building complete SNMPv3 GetRequest."""
        creds = SNMPv3Credentials(
            username="admin",
            security_level=SNMPv3SecurityLevel.NO_AUTH_NO_PRIV,
            auth_protocol=SNMPv3AuthProtocol.NONE,
            priv_protocol=SNMPv3PrivProtocol.NONE,
            engine_id=generate_engine_id("10.1.0.100"),
        )
        msg = build_snmpv3_get_request(
            credentials=creds,
            request_id=1000,
            oids=["1.3.6.1.2.1.1.1.0"],
        )
        assert isinstance(msg, bytes)
        # SNMPv3 message starts with SEQUENCE
        assert msg[0] == 0x30

    def test_build_snmpv3_get_response(self):
        """Test building complete SNMPv3 GetResponse."""
        creds = SNMPv3Credentials(
            username="admin",
            security_level=SNMPv3SecurityLevel.NO_AUTH_NO_PRIV,
            auth_protocol=SNMPv3AuthProtocol.NONE,
            priv_protocol=SNMPv3PrivProtocol.NONE,
            engine_id=generate_engine_id("10.1.0.100"),
        )
        var_binds = [
            VarBind(oid="1.3.6.1.2.1.1.1.0", value="Test Device", value_type="string"),
        ]
        msg = build_snmpv3_get_response(
            credentials=creds,
            request_id=1000,
            varbinds=var_binds,
        )
        assert isinstance(msg, bytes)
        assert msg[0] == 0x30

    def test_build_snmpv3_get_request_packet(self):
        """Test building complete SNMPv3 GetRequest packet with headers."""
        creds = SNMPv3Credentials(
            username="admin",
            security_level=SNMPv3SecurityLevel.NO_AUTH_NO_PRIV,
            engine_id=generate_engine_id("10.1.0.100"),
        )
        packet = build_snmpv3_get_request_packet(
            src_mac="00:11:22:33:44:55",
            dst_mac="00:AA:BB:CC:DD:EE",
            src_ip="10.1.0.10",
            dst_ip="10.1.0.100",
            src_port=49152,
            dst_port=SNMP_AGENT_PORT,
            credentials=creds,
            request_id=1000,
            oids=["1.3.6.1.2.1.1.1.0"],
        )
        assert isinstance(packet, bytes)
        assert len(packet) > 42

    def test_build_snmpv3_get_response_packet(self):
        """Test building complete SNMPv3 GetResponse packet with headers."""
        creds = SNMPv3Credentials(
            username="admin",
            security_level=SNMPv3SecurityLevel.NO_AUTH_NO_PRIV,
            engine_id=generate_engine_id("10.1.0.100"),
        )
        var_binds = [
            VarBind(oid="1.3.6.1.2.1.1.1.0", value="Test Device", value_type="string"),
        ]
        packet = build_snmpv3_get_response_packet(
            src_mac="00:AA:BB:CC:DD:EE",
            dst_mac="00:11:22:33:44:55",
            src_ip="10.1.0.100",
            dst_ip="10.1.0.10",
            src_port=SNMP_AGENT_PORT,
            dst_port=49152,
            credentials=creds,
            request_id=1000,
            var_binds=var_binds,
        )
        assert isinstance(packet, bytes)
        assert len(packet) > 42

    def test_build_snmpv3_auth_request(self):
        """Test building SNMPv3 request with authentication."""
        engine_id = generate_engine_id("10.1.0.100")
        creds = SNMPv3Credentials(
            username="admin",
            security_level=SNMPv3SecurityLevel.AUTH_NO_PRIV,
            auth_protocol=SNMPv3AuthProtocol.SHA,
            auth_password="authpass123",
            engine_id=engine_id,
            engine_boots=1,
            engine_time=1000,
        )
        msg = build_snmpv3_get_request(
            credentials=creds,
            request_id=2000,
            oids=["1.3.6.1.2.1.1.1.0"],
        )
        assert isinstance(msg, bytes)
        assert len(msg) > 50  # Auth message is larger


# =============================================================================
# Engine Tests
# =============================================================================


class TestSnmpEngine:
    """Test SNMP engine lifecycle methods."""

    def test_create_initial_state(self, engine, flow_context):
        """Test initial state creation."""
        state = engine.create_initial_state(flow_context)
        assert isinstance(state, ConversationState)
        assert state.flow_id == "snmp-flow-01"
        assert state.state_name == SNMPState.IDLE.value
        assert state.transaction_id >= 1
        assert state.sequence_number == 0
        assert "start_time_ms" in state.custom_data
        assert "sys_uptime_ticks" in state.custom_data
        assert "oid_index" in state.custom_data

    def test_generate_startup_sequence(self, engine, flow_context):
        """Test SNMP discovery startup sequence generates correct events."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Discovery polls each DISCOVERY_OID: GetRequest + GetResponse per OID
        expected_events = len(DISCOVERY_OIDS) * 2
        assert len(events) == expected_events

        # Check that events alternate request/response
        for i, event in enumerate(events):
            assert isinstance(event, PacketEvent)
            assert isinstance(event.packet_bytes, bytes)
            assert len(event.packet_bytes) > 0
            if i % 2 == 0:
                assert event.direction == "request"
                assert event.metadata["type"] == "snmp_get_request"
                assert event.metadata.get("operation") == "discovery"
            else:
                assert event.direction == "response"
                assert event.metadata["type"] == "snmp_get_response"
                assert "oid" in event.metadata

        # State should transition to POLLING after discovery
        assert state.state_name == SNMPState.POLLING.value

    def test_startup_sequence_timestamps_increase(self, engine, flow_context):
        """Test that timestamps increase monotonically in startup."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 1000.0))

        for i in range(1, len(events)):
            assert events[i].timestamp_ms >= events[i - 1].timestamp_ms

    def test_generate_poll_cycle(self, engine, flow_context):
        """Test SNMP poll cycle generates request/response pair."""
        state = engine.create_initial_state(flow_context)
        state.state_name = SNMPState.POLLING.value

        events = list(engine.generate_poll_cycle(flow_context, state, 5000.0))

        # Normal poll: GetRequest + GetResponse = 2 events
        assert len(events) == 2
        assert events[0].direction == "request"
        assert events[0].metadata["type"] == "snmp_get_request"
        assert events[1].direction == "response"
        assert events[1].metadata["type"] == "snmp_get_response"

        # Response should be after request
        assert events[1].timestamp_ms > events[0].timestamp_ms

        # State should return to POLLING
        assert state.state_name == SNMPState.POLLING.value

    def test_poll_cycle_increments_sequence(self, engine, flow_context):
        """Test that poll cycles increment the sequence number."""
        state = engine.create_initial_state(flow_context)
        state.state_name = SNMPState.POLLING.value

        assert state.sequence_number == 0
        list(engine.generate_poll_cycle(flow_context, state, 5000.0))
        assert state.sequence_number == 1
        list(engine.generate_poll_cycle(flow_context, state, 6000.0))
        assert state.sequence_number == 2

    def test_poll_cycle_increments_transaction_id(self, engine, flow_context):
        """Test that transaction_id increments between poll cycles."""
        state = engine.create_initial_state(flow_context)
        state.state_name = SNMPState.POLLING.value

        initial_txn_id = state.transaction_id
        list(engine.generate_poll_cycle(flow_context, state, 5000.0))
        assert state.transaction_id == (initial_txn_id + 1) % 2147483647

    def test_poll_cycle_rotates_oids(self, engine, flow_context):
        """Test that poll cycles rotate through configured OIDs."""
        state = engine.create_initial_state(flow_context)
        state.state_name = SNMPState.POLLING.value

        # Track OIDs used across multiple cycles
        used_oids = []
        for i in range(len(TRAFFIC_CONTROLLER_POLL_OIDS) + 1):
            events = list(engine.generate_poll_cycle(flow_context, state, 5000.0 + i * 1000))
            oid = events[0].metadata["oids"][0]
            used_oids.append(oid)

        # Should have rotated back to the first OID
        assert used_oids[0] == used_oids[len(TRAFFIC_CONTROLLER_POLL_OIDS)]

    def test_generate_shutdown_sequence(self, engine, flow_context):
        """Test SNMP shutdown generates no events (UDP-based)."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_shutdown_sequence(flow_context, state, 10000.0))
        assert len(events) == 0

    def test_generate_trap(self, engine, flow_context):
        """Test trap generation with standard trap OID."""
        state = engine.create_initial_state(flow_context)
        # Use actual OID for linkUp trap (1.3.6.1.6.3.1.1.5.4)
        events = list(
            engine.generate_trap(
                flow_context, state, 7000.0,
                trap_type="1.3.6.1.6.3.1.1.5.4",
            )
        )

        assert len(events) == 1
        event = events[0]
        assert event.direction == "response"  # Trap goes from agent to manager
        assert "snmp_trap_" in event.metadata["type"]
        assert event.metadata["trap_type"] == "1.3.6.1.6.3.1.1.5.4"
        assert isinstance(event.packet_bytes, bytes)
        assert len(event.packet_bytes) > 0

    def test_generate_trap_with_varbinds(self, engine, flow_context):
        """Test trap generation with additional varbinds."""
        state = engine.create_initial_state(flow_context)
        extra_varbinds = [
            VarBind(oid="1.3.6.1.2.1.2.2.1.8.1", value=1, value_type="integer"),
        ]
        events = list(
            engine.generate_trap(
                flow_context, state, 7000.0,
                trap_type="1.3.6.1.6.3.1.1.5.4",
                var_binds=extra_varbinds,
            )
        )
        assert len(events) == 1

    def test_snmpv3_startup_sequence(self, engine, v3_flow_context):
        """Test SNMPv3 startup sequence."""
        state = engine.create_initial_state(v3_flow_context)
        events = list(engine.generate_startup_sequence(v3_flow_context, state, 0.0))

        # Same pattern: request/response per discovery OID
        expected_events = len(DISCOVERY_OIDS) * 2
        assert len(events) == expected_events

        # Check metadata mentions SNMPv3
        for event in events:
            if event.direction == "response":
                assert event.metadata.get("snmp_version") == "V3"

    def test_snmpv3_poll_cycle(self, engine, v3_flow_context):
        """Test SNMPv3 poll cycle."""
        state = engine.create_initial_state(v3_flow_context)
        state.state_name = SNMPState.POLLING.value

        events = list(engine.generate_poll_cycle(v3_flow_context, state, 5000.0))
        assert len(events) == 2
        # Check metadata mentions SNMPv3
        assert events[1].metadata.get("snmp_version") == "V3"


class TestSnmpEngineDeviceTypes:
    """Test SNMP engine with different device types."""

    def test_traffic_controller_oids(self, engine, source_device, destination_device, mock_applicator):
        """Test that traffic controller device type selects correct OIDs."""
        flow = FlowContext(
            flow_id="tc-flow",
            source=source_device,
            destination=destination_device,
            protocol=ProtocolType.SNMP,
            config={
                "community": "public",
                "snmp_version": "v2c",
                "device_type": "traffic_controller",
            },
            timing_model={},
        )
        poll_oids = engine._get_poll_oids(flow)
        assert poll_oids == TRAFFIC_CONTROLLER_POLL_OIDS

    def test_dms_oids(self, engine, source_device, destination_device, mock_applicator):
        """Test that DMS device type selects correct OIDs."""
        flow = FlowContext(
            flow_id="dms-flow",
            source=source_device,
            destination=destination_device,
            protocol=ProtocolType.SNMP,
            config={
                "community": "public",
                "snmp_version": "v2c",
                "device_type": "dms",
            },
            timing_model={},
        )
        poll_oids = engine._get_poll_oids(flow)
        assert poll_oids == DMS_POLL_OIDS

    def test_generic_device_oids(self, engine, source_device, destination_device, mock_applicator):
        """Test that generic device type selects discovery OIDs."""
        flow = FlowContext(
            flow_id="generic-flow",
            source=source_device,
            destination=destination_device,
            protocol=ProtocolType.SNMP,
            config={
                "community": "public",
                "snmp_version": "v2c",
                "device_type": "generic",
            },
            timing_model={},
        )
        poll_oids = engine._get_poll_oids(flow)
        assert poll_oids == DISCOVERY_OIDS

    def test_custom_poll_oids_override(self, engine, source_device, destination_device, mock_applicator):
        """Test that explicit poll_oids override device type selection."""
        custom_oids = ["1.3.6.1.2.1.2.2.1.10.1", "1.3.6.1.2.1.2.2.1.16.1"]
        flow = FlowContext(
            flow_id="custom-flow",
            source=source_device,
            destination=destination_device,
            protocol=ProtocolType.SNMP,
            config={
                "community": "public",
                "snmp_version": "v2c",
                "device_type": "traffic_controller",
                "poll_oids": custom_oids,
            },
            timing_model={},
        )
        poll_oids = engine._get_poll_oids(flow)
        assert poll_oids == custom_oids


class TestSnmpEngineNtcipValues:
    """Test NTCIP-specific value generation."""

    def test_ntcip_asc_phase_status(self, engine, flow_context):
        """Test NTCIP 1202 phase status value generation."""
        state = engine.create_initial_state(flow_context)
        oid = f"{NTCIP_ASC}.1.4.1.0"
        varbind = engine._generate_ntcip_value(flow_context, state, oid)
        assert isinstance(varbind, VarBind)
        assert varbind.oid == oid
        assert varbind.value_type == "integer"
        assert 0 <= varbind.value <= 255

    def test_ntcip_asc_value_is_integer(self, engine, flow_context):
        """Test NTCIP 1202 ASC OIDs return integer values."""
        state = engine.create_initial_state(flow_context)
        # Use a clear NTCIP ASC OID that won't be ambiguous with substring matching
        oid = f"{NTCIP_ASC}.1.4.1.0"  # phaseStatusGroupReds
        varbind = engine._generate_ntcip_value(flow_context, state, oid)
        assert isinstance(varbind, VarBind)
        assert varbind.value_type == "integer"
        assert 0 <= varbind.value <= 255

    def test_ntcip_asc_returns_integer_values(self, engine, flow_context):
        """Test NTCIP 1202 ASC OIDs consistently return integer values."""
        state = engine.create_initial_state(flow_context)
        # All NTCIP ASC OIDs should return integer types
        for oid in TRAFFIC_CONTROLLER_POLL_OIDS:
            varbind = engine._generate_ntcip_value(flow_context, state, oid)
            assert isinstance(varbind, VarBind)
            assert varbind.value_type == "integer"
            assert isinstance(varbind.value, int)

    def test_ntcip_dms_returns_values(self, engine, flow_context):
        """Test NTCIP 1203 DMS OIDs return valid values."""
        state = engine.create_initial_state(flow_context)
        for oid in DMS_POLL_OIDS:
            varbind = engine._generate_ntcip_value(flow_context, state, oid)
            assert isinstance(varbind, VarBind)
            assert varbind.oid == oid

    def test_ntcip_unknown_oid_returns_zero(self, engine, flow_context):
        """Test that unknown NTCIP OIDs return default zero value."""
        state = engine.create_initial_state(flow_context)
        oid = "1.3.6.1.4.1.9999.1.2.3"
        varbind = engine._generate_ntcip_value(flow_context, state, oid)
        assert varbind.value == 0
        assert varbind.value_type == "integer"


class TestSnmpEngineIdentityValues:
    """Test fingerprint-based SNMP identity value generation."""

    def test_sys_descr_from_applicator(self, engine, flow_context):
        """Test sysDescr is retrieved from fingerprint applicator."""
        state = engine.create_initial_state(flow_context)
        varbind = engine._generate_snmp_values(flow_context, state, SystemOIDs.SYS_DESCR.oid)
        assert varbind.value == "Econolite ASC/3-2100 Version 3.28.1"
        assert varbind.value_type == "string"

    def test_sys_object_id_from_applicator(self, engine, flow_context):
        """Test sysObjectID is retrieved from fingerprint applicator."""
        state = engine.create_initial_state(flow_context)
        varbind = engine._generate_snmp_values(flow_context, state, SystemOIDs.SYS_OBJECT_ID.oid)
        assert varbind.value == "1.3.6.1.4.1.1206.4.2.2"
        assert varbind.value_type == "oid"

    def test_sys_uptime_returns_timeticks(self, engine, flow_context):
        """Test sysUpTime returns timeticks value."""
        state = engine.create_initial_state(flow_context)
        varbind = engine._generate_snmp_values(flow_context, state, SystemOIDs.SYS_UPTIME.oid)
        assert isinstance(varbind.value, int)
        assert varbind.value_type == "timeticks"

    def test_sys_name_from_device_name(self, engine, flow_context):
        """Test sysName uses device_name when available."""
        state = engine.create_initial_state(flow_context)
        varbind = engine._generate_snmp_values(flow_context, state, SystemOIDs.SYS_NAME.oid)
        assert varbind.value == "TC-Intersection-Main"
        assert varbind.value_type == "string"

    def test_sys_location_from_fingerprint(self, engine, flow_context):
        """Test sysLocation is retrieved from fingerprint data."""
        state = engine.create_initial_state(flow_context)
        varbind = engine._generate_snmp_values(flow_context, state, SystemOIDs.SYS_LOCATION.oid)
        assert varbind.value == "Main St & 1st Ave"
        assert varbind.value_type == "string"

    def test_sys_contact_from_fingerprint(self, engine, flow_context):
        """Test sysContact is retrieved from fingerprint data."""
        state = engine.create_initial_state(flow_context)
        varbind = engine._generate_snmp_values(flow_context, state, SystemOIDs.SYS_CONTACT.oid)
        assert varbind.value == "traffic-ops@city.gov"
        assert varbind.value_type == "string"

    def test_sys_services_returns_default(self, engine, flow_context):
        """Test sysServices returns default value of 72."""
        state = engine.create_initial_state(flow_context)
        varbind = engine._generate_snmp_values(flow_context, state, SystemOIDs.SYS_SERVICES.oid)
        assert varbind.value == 72
        assert varbind.value_type == "integer"


# =============================================================================
# Config Validation Tests
# =============================================================================


class TestSnmpConfigValidation:
    """Test SNMP configuration validation."""

    def test_valid_v2c_config(self, engine):
        """Test valid SNMPv2c configuration passes validation."""
        config = {
            "community": "public",
            "snmp_version": "v2c",
            "timeout_ms": 5000,
        }
        errors = engine.validate_config(config)
        assert errors == []

    def test_valid_v1_config(self, engine):
        """Test valid SNMPv1 configuration passes validation."""
        config = {
            "community": "public",
            "snmp_version": "v1",
            "timeout_ms": 3000,
        }
        errors = engine.validate_config(config)
        assert errors == []

    def test_valid_v3_config(self, engine):
        """Test valid SNMPv3 configuration passes validation."""
        config = {
            "snmp_version": "v3",
            "v3_credentials": {
                "username": "admin",
                "security_level": "authPriv",
                "auth_protocol": "sha",
                "auth_password": "authpass123",
                "priv_protocol": "aes",
                "priv_password": "privpass123",
            },
        }
        errors = engine.validate_config(config)
        assert errors == []

    def test_invalid_community_type(self, engine):
        """Test community must be a string."""
        config = {"community": 123}
        errors = engine.validate_config(config)
        assert any("community must be a string" in e for e in errors)

    def test_invalid_snmp_version_string(self, engine):
        """Test invalid SNMP version string is rejected."""
        config = {"snmp_version": "v4"}
        errors = engine.validate_config(config)
        assert any("snmp_version" in e for e in errors)

    def test_invalid_snmp_version_int(self, engine):
        """Test invalid SNMP version integer is rejected."""
        config = {"snmp_version": 2}
        errors = engine.validate_config(config)
        assert any("snmp_version" in e for e in errors)

    def test_valid_snmp_version_int(self, engine):
        """Test valid SNMP version integers are accepted."""
        for version_int in [0, 1, 3]:
            config = {"snmp_version": version_int}
            if version_int == 3:
                config["v3_credentials"] = {
                    "username": "admin",
                    "security_level": "noAuthNoPriv",
                }
            errors = engine.validate_config(config)
            version_errors = [e for e in errors if "snmp_version" in e]
            assert len(version_errors) == 0, f"Version {version_int} should be valid"

    def test_v3_missing_credentials(self, engine):
        """Test SNMPv3 without credentials fails validation."""
        config = {"snmp_version": "v3"}
        errors = engine.validate_config(config)
        assert any("v3_credentials required" in e for e in errors)

    def test_v3_missing_username(self, engine):
        """Test SNMPv3 without username fails validation."""
        config = {
            "snmp_version": "v3",
            "v3_credentials": {
                "security_level": "noAuthNoPriv",
            },
        }
        errors = engine.validate_config(config)
        assert any("username" in e for e in errors)

    def test_v3_invalid_security_level(self, engine):
        """Test SNMPv3 with invalid security level fails validation."""
        config = {
            "snmp_version": "v3",
            "v3_credentials": {
                "username": "admin",
                "security_level": "superSecret",
            },
        }
        errors = engine.validate_config(config)
        assert any("security_level" in e for e in errors)

    def test_v3_auth_missing_password(self, engine):
        """Test SNMPv3 authNoPriv without auth_password fails."""
        config = {
            "snmp_version": "v3",
            "v3_credentials": {
                "username": "admin",
                "security_level": "authNoPriv",
            },
        }
        errors = engine.validate_config(config)
        assert any("auth_password" in e for e in errors)

    def test_v3_auth_invalid_protocol(self, engine):
        """Test SNMPv3 with invalid auth protocol fails."""
        config = {
            "snmp_version": "v3",
            "v3_credentials": {
                "username": "admin",
                "security_level": "authNoPriv",
                "auth_password": "pass123",
                "auth_protocol": "blowfish",
            },
        }
        errors = engine.validate_config(config)
        assert any("auth_protocol" in e for e in errors)

    def test_v3_priv_missing_password(self, engine):
        """Test SNMPv3 authPriv without priv_password fails."""
        config = {
            "snmp_version": "v3",
            "v3_credentials": {
                "username": "admin",
                "security_level": "authPriv",
                "auth_password": "authpass",
                "auth_protocol": "sha",
            },
        }
        errors = engine.validate_config(config)
        assert any("priv_password" in e for e in errors)

    def test_v3_priv_invalid_protocol(self, engine):
        """Test SNMPv3 with invalid priv protocol fails."""
        config = {
            "snmp_version": "v3",
            "v3_credentials": {
                "username": "admin",
                "security_level": "authPriv",
                "auth_password": "authpass",
                "auth_protocol": "sha",
                "priv_password": "privpass",
                "priv_protocol": "3des",
            },
        }
        errors = engine.validate_config(config)
        assert any("priv_protocol" in e for e in errors)

    def test_invalid_timeout_too_low(self, engine):
        """Test timeout_ms below 100 is rejected."""
        config = {"timeout_ms": 50}
        errors = engine.validate_config(config)
        assert any("timeout_ms" in e for e in errors)

    def test_invalid_timeout_type(self, engine):
        """Test non-integer timeout_ms is rejected."""
        config = {"timeout_ms": "fast"}
        errors = engine.validate_config(config)
        assert any("timeout_ms" in e for e in errors)

    def test_invalid_poll_oids_type(self, engine):
        """Test non-list poll_oids is rejected."""
        config = {"poll_oids": "1.3.6.1.2.1.1.1.0"}
        errors = engine.validate_config(config)
        assert any("poll_oids must be a list" in e for e in errors)

    def test_invalid_poll_oid_format(self, engine):
        """Test invalid OID format in poll_oids is rejected."""
        config = {"poll_oids": ["not-an-oid"]}
        errors = engine.validate_config(config)
        assert any("Invalid OID" in e for e in errors)

    def test_valid_poll_oids(self, engine):
        """Test valid poll_oids pass validation."""
        config = {
            "poll_oids": [
                "1.3.6.1.2.1.1.1.0",
                "1.3.6.1.4.1.1206.4.2.2.1.4.1.0",
            ],
        }
        errors = engine.validate_config(config)
        assert errors == []

    def test_empty_config_valid(self, engine):
        """Test that empty config is valid (all optional)."""
        errors = engine.validate_config({})
        assert errors == []


class TestSnmpVersionParsing:
    """Test SNMP version parsing in engine config extraction."""

    def test_version_string_v1(self, engine, source_device, destination_device, mock_applicator):
        """Test parsing version string 'v1'."""
        flow = FlowContext(
            flow_id="test-v1",
            source=source_device,
            destination=destination_device,
            protocol=ProtocolType.SNMP,
            config={"snmp_version": "v1"},
            timing_model={},
        )
        config = engine._get_snmp_config(flow)
        assert config.version == SNMPVersion.V1

    def test_version_string_v2c(self, engine, source_device, destination_device, mock_applicator):
        """Test parsing version string 'v2c'."""
        flow = FlowContext(
            flow_id="test-v2c",
            source=source_device,
            destination=destination_device,
            protocol=ProtocolType.SNMP,
            config={"snmp_version": "v2c"},
            timing_model={},
        )
        config = engine._get_snmp_config(flow)
        assert config.version == SNMPVersion.V2C

    def test_version_string_v3(self, engine, source_device, destination_device, mock_applicator):
        """Test parsing version string 'v3' with credentials."""
        flow = FlowContext(
            flow_id="test-v3",
            source=source_device,
            destination=destination_device,
            protocol=ProtocolType.SNMP,
            config={
                "snmp_version": "v3",
                "v3_credentials": {
                    "username": "admin",
                    "security_level": "authNoPriv",
                    "auth_protocol": "sha",
                    "auth_password": "pass123",
                },
            },
            timing_model={},
        )
        config = engine._get_snmp_config(flow)
        assert config.version == SNMPVersion.V3
        assert config.v3_credentials is not None
        assert config.v3_credentials.username == "admin"
        assert config.v3_credentials.security_level == SNMPv3SecurityLevel.AUTH_NO_PRIV

    def test_version_integer(self, engine, source_device, destination_device, mock_applicator):
        """Test parsing version as integer."""
        flow = FlowContext(
            flow_id="test-int",
            source=source_device,
            destination=destination_device,
            protocol=ProtocolType.SNMP,
            config={"snmp_version": 1},  # V2C as integer
            timing_model={},
        )
        config = engine._get_snmp_config(flow)
        assert config.version == SNMPVersion.V2C

    def test_default_version(self, engine, source_device, destination_device, mock_applicator):
        """Test default version is V2C when not specified."""
        flow = FlowContext(
            flow_id="test-default",
            source=source_device,
            destination=destination_device,
            protocol=ProtocolType.SNMP,
            config={},
            timing_model={},
        )
        config = engine._get_snmp_config(flow)
        assert config.version == SNMPVersion.V2C
