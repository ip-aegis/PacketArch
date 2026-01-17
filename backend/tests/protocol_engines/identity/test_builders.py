"""Tests for Protocol Identity Builder plugin system."""

import pytest

from app.protocol_engines.identity import (
    BACnetIdentityBuilder,
    EtherNetIPIdentityBuilder,
    FirmwareFields,
    IdentityResponse,
    ModbusIdentityBuilder,
    ProfinetIdentityBuilder,
    S7IdentityBuilder,
    SNMPIdentityBuilder,
    build_identity_for_protocol,
    derive_all_firmware_fields,
    derive_firmware_fields_for_protocol,
    get_all_builders,
    get_builder,
    get_registered_protocols,
    has_builder,
)


class TestBuilderRegistry:
    """Tests for the builder registry."""

    def test_all_protocols_registered(self):
        """Verify all expected protocols are registered."""
        expected = {"modbus", "ethernet_ip", "profinet", "s7", "snmp", "bacnet"}
        registered = set(get_registered_protocols())
        assert expected == registered

    def test_get_builder_returns_correct_type(self):
        """Verify get_builder returns correct builder types."""
        assert isinstance(get_builder("modbus"), ModbusIdentityBuilder)
        assert isinstance(get_builder("ethernet_ip"), EtherNetIPIdentityBuilder)
        assert isinstance(get_builder("profinet"), ProfinetIdentityBuilder)
        assert isinstance(get_builder("s7"), S7IdentityBuilder)
        assert isinstance(get_builder("snmp"), SNMPIdentityBuilder)
        assert isinstance(get_builder("bacnet"), BACnetIdentityBuilder)

    def test_get_builder_unknown_protocol_raises(self):
        """Verify KeyError is raised for unknown protocols."""
        with pytest.raises(KeyError) as exc_info:
            get_builder("unknown_protocol")
        assert "unknown_protocol" in str(exc_info.value)

    def test_has_builder(self):
        """Test has_builder function."""
        assert has_builder("modbus") is True
        assert has_builder("ethernet_ip") is True
        assert has_builder("unknown") is False

    def test_get_all_builders(self):
        """Test get_all_builders returns all builder instances."""
        builders = get_all_builders()
        assert len(builders) == 6
        assert all(isinstance(b, type(get_builder("modbus")).__bases__[0])
                   for b in builders.values())


class TestModbusIdentityBuilder:
    """Tests for ModbusIdentityBuilder."""

    def test_protocol_name(self):
        """Verify protocol name."""
        builder = ModbusIdentityBuilder()
        assert builder.protocol_name == "modbus"

    def test_identity_key(self):
        """Verify identity key."""
        builder = ModbusIdentityBuilder()
        assert builder.identity_key == "modbus_identity"

    def test_override_key(self):
        """Verify override key."""
        builder = ModbusIdentityBuilder()
        assert builder.override_key == "modbus_identity_override"

    def test_derive_firmware_fields(self):
        """Test firmware field derivation."""
        builder = ModbusIdentityBuilder()
        result = builder.derive_firmware_fields("3.10")

        assert isinstance(result, FirmwareFields)
        assert result.firmware_version == "3.10"
        assert result.protocol == "modbus"
        assert result.fields["major_minor_revision"] == "3.10"

    def test_derive_firmware_fields_with_patch(self):
        """Test firmware field derivation with patch version."""
        builder = ModbusIdentityBuilder()
        result = builder.derive_firmware_fields("3.10.2")

        assert result.fields["major_minor_revision"] == "3.10.2"

    def test_build_identity_response(self):
        """Test building identity response."""
        builder = ModbusIdentityBuilder()
        base_identity = {
            "vendor_name": "Test Vendor",
            "product_code": "TEST-001",
            "major_minor_revision": "1.0",
        }

        response = builder.build_identity_response(base_identity)

        assert isinstance(response, IdentityResponse)
        assert response.protocol == "modbus"
        assert response.identity_dict["vendor_name"] == "Test Vendor"
        assert response.raw_bytes is not None
        assert len(response.raw_bytes) > 0

    def test_build_identity_response_with_firmware(self):
        """Test firmware version override in identity response."""
        builder = ModbusIdentityBuilder()
        base_identity = {
            "vendor_name": "Test Vendor",
            "major_minor_revision": "1.0",
        }

        response = builder.build_identity_response(
            base_identity,
            firmware_version="3.10",
        )

        assert response.identity_dict["major_minor_revision"] == "3.10"

    def test_build_raw_response(self):
        """Test raw MEI response building."""
        builder = ModbusIdentityBuilder()
        identity = {
            "vendor_name": "Siemens",
            "product_code": "S7-1500",
            "major_minor_revision": "3.0",
        }

        raw = builder.build_raw_response(identity, device_id_code=1)

        assert raw[0] == 0x0E  # MEI type
        assert raw[1] == 0x01  # device_id_code
        assert b"Siemens" in raw


class TestEtherNetIPIdentityBuilder:
    """Tests for EtherNetIPIdentityBuilder."""

    def test_protocol_name(self):
        """Verify protocol name."""
        builder = EtherNetIPIdentityBuilder()
        assert builder.protocol_name == "ethernet_ip"

    def test_derive_firmware_fields(self):
        """Test firmware field derivation."""
        builder = EtherNetIPIdentityBuilder()
        result = builder.derive_firmware_fields("32.11")

        assert result.fields["revision_major"] == 32
        assert result.fields["revision_minor"] == 11

    def test_build_identity_response(self):
        """Test building identity response."""
        builder = EtherNetIPIdentityBuilder()
        base_identity = {
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 55,
            "revision_major": 32,
            "revision_minor": 11,
            "product_name": "1756-L85E/B",
        }

        response = builder.build_identity_response(base_identity)

        assert response.protocol == "ethernet_ip"
        assert response.identity_dict["vendor_id"] == 1


class TestProfinetIdentityBuilder:
    """Tests for ProfinetIdentityBuilder."""

    def test_derive_firmware_fields(self):
        """Test firmware field derivation with V prefix."""
        builder = ProfinetIdentityBuilder()
        result = builder.derive_firmware_fields("3.10")

        assert result.fields["sw_release"] == "V3.10"

    def test_derive_firmware_fields_preserves_prefix(self):
        """Test that existing V prefix is preserved."""
        builder = ProfinetIdentityBuilder()
        result = builder.derive_firmware_fields("V3.10.2")

        assert result.fields["sw_release"] == "V3.10.2"


class TestS7IdentityBuilder:
    """Tests for S7IdentityBuilder."""

    def test_derive_firmware_fields(self):
        """Test firmware field derivation."""
        builder = S7IdentityBuilder()
        result = builder.derive_firmware_fields("3.0.0")

        assert result.fields["firmware_version"] == "V3.0.0"

    def test_build_szl_0011_response(self):
        """Test SZL 0x0011 response building."""
        builder = S7IdentityBuilder()
        identity = {
            "order_code": "6ES7 516-3AN01-0AB0",
            "serial_number": "S V-P92001234",
            "firmware_version": "V3.0.0",
            "module_type": "CPU 1516-3 PN/DP",
        }

        raw = builder.build_raw_response(identity, szl_id=0x0011)

        assert len(raw) > 0
        assert raw[0:2] == b"\x00\x11"  # SZL ID


class TestSNMPIdentityBuilder:
    """Tests for SNMPIdentityBuilder."""

    def test_derive_firmware_fields_with_template(self):
        """Test firmware derivation with template."""
        builder = SNMPIdentityBuilder()
        result = builder.derive_firmware_fields(
            "2.1.4",
            base_identity={"sys_descr_template": "Econolite Cobalt ATC V{firmware_version}"},
            sys_descr_template="Device Firmware V{firmware_version}",
        )

        assert result.fields["sys_descr"] == "Device Firmware V2.1.4"


class TestBACnetIdentityBuilder:
    """Tests for BACnetIdentityBuilder."""

    def test_derive_firmware_fields(self):
        """Test firmware field derivation."""
        builder = BACnetIdentityBuilder()
        result = builder.derive_firmware_fields("12.0.3")

        assert result.fields["firmware_revision"] == "12.0.3"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_build_identity_for_protocol(self):
        """Test build_identity_for_protocol function."""
        response = build_identity_for_protocol(
            "modbus",
            {"vendor_name": "Test", "product_code": "001"},
        )

        assert isinstance(response, IdentityResponse)
        assert response.protocol == "modbus"

    def test_derive_firmware_fields_for_protocol(self):
        """Test derive_firmware_fields_for_protocol function."""
        result = derive_firmware_fields_for_protocol("modbus", "3.10")

        assert isinstance(result, FirmwareFields)
        assert result.fields["major_minor_revision"] == "3.10"

    def test_derive_all_firmware_fields(self):
        """Test derive_all_firmware_fields function."""
        result = derive_all_firmware_fields("3.10")

        assert "modbus" in result
        assert "ethernet_ip" in result
        assert "profinet" in result
        assert "s7" in result
        assert "snmp" in result
        assert "bacnet" in result
