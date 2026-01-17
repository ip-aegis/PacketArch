"""Modbus function code handlers.

Includes standard function codes (FC01-FC16) and extended codes:
- FC07: Read Exception Status
- FC08: Diagnostics
- FC43: Read Device Identification (MEI)
"""

import struct
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import FingerprintApplicator


# Modbus exception codes
EXCEPTION_ILLEGAL_FUNCTION = 0x01
EXCEPTION_ILLEGAL_DATA_ADDRESS = 0x02
EXCEPTION_ILLEGAL_DATA_VALUE = 0x03
EXCEPTION_SLAVE_DEVICE_FAILURE = 0x04
EXCEPTION_ACKNOWLEDGE = 0x05
EXCEPTION_SLAVE_DEVICE_BUSY = 0x06
EXCEPTION_MEMORY_PARITY_ERROR = 0x08
EXCEPTION_GATEWAY_PATH_UNAVAILABLE = 0x0A
EXCEPTION_GATEWAY_TARGET_FAILED = 0x0B


def build_exception_response(function_code: int, exception_code: int) -> bytes:
    """Build a Modbus exception response PDU.

    Args:
        function_code: Original function code
        exception_code: Exception code (1-11)

    Returns:
        Exception response PDU bytes
    """
    # Exception response has function code with high bit set (0x80 | FC)
    return struct.pack(">BB", 0x80 | function_code, exception_code)


class FunctionCodeHandler(ABC):
    """Abstract base class for Modbus function code handlers."""

    @property
    @abstractmethod
    def function_code(self) -> int:
        """Return the function code this handler supports."""
        pass

    @abstractmethod
    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build a request PDU.

        Args:
            config: Request configuration (address, quantity, etc.)

        Returns:
            Request PDU bytes (without MBAP header)
        """
        pass

    @abstractmethod
    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build a response PDU.

        Args:
            config: Request configuration
            payload: Response payload data

        Returns:
            Response PDU bytes (without MBAP header)
        """
        pass

    def build_exception(self, exception_code: int) -> bytes:
        """Build an exception response for this function code.

        Args:
            exception_code: Modbus exception code (1-11)

        Returns:
            Exception response PDU bytes
        """
        return build_exception_response(self.function_code, exception_code)


class FC01ReadCoils(FunctionCodeHandler):
    """Read Coils (FC01) handler."""

    @property
    def function_code(self) -> int:
        return 0x01

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Read Coils request."""
        start_address = config.get("start_address", 0)
        quantity = config.get("quantity", 1)
        return struct.pack(">BHH", self.function_code, start_address, quantity)

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Read Coils response."""
        quantity = config.get("quantity", 1)
        values = payload.get("values", [False] * quantity)

        # Pack bits into bytes
        byte_count = (quantity + 7) // 8
        data_bytes = bytearray(byte_count)

        for i, value in enumerate(values[:quantity]):
            if value:
                byte_idx = i // 8
                bit_idx = i % 8
                data_bytes[byte_idx] |= 1 << bit_idx

        return struct.pack(">BB", self.function_code, byte_count) + bytes(data_bytes)


class FC02ReadDiscreteInputs(FunctionCodeHandler):
    """Read Discrete Inputs (FC02) handler."""

    @property
    def function_code(self) -> int:
        return 0x02

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Read Discrete Inputs request."""
        start_address = config.get("start_address", 0)
        quantity = config.get("quantity", 1)
        return struct.pack(">BHH", self.function_code, start_address, quantity)

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Read Discrete Inputs response."""
        quantity = config.get("quantity", 1)
        values = payload.get("values", [False] * quantity)

        # Pack bits into bytes
        byte_count = (quantity + 7) // 8
        data_bytes = bytearray(byte_count)

        for i, value in enumerate(values[:quantity]):
            if value:
                byte_idx = i // 8
                bit_idx = i % 8
                data_bytes[byte_idx] |= 1 << bit_idx

        return struct.pack(">BB", self.function_code, byte_count) + bytes(data_bytes)


class FC03ReadHoldingRegisters(FunctionCodeHandler):
    """Read Holding Registers (FC03) handler."""

    @property
    def function_code(self) -> int:
        return 0x03

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Read Holding Registers request."""
        start_address = config.get("start_address", 0)
        quantity = config.get("quantity", 1)
        return struct.pack(">BHH", self.function_code, start_address, quantity)

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Read Holding Registers response."""
        quantity = config.get("quantity", 1)
        values = payload.get("values", [0] * quantity)

        byte_count = quantity * 2
        pdu = struct.pack(">BB", self.function_code, byte_count)

        for value in values[:quantity]:
            pdu += struct.pack(">H", value & 0xFFFF)

        return pdu


class FC04ReadInputRegisters(FunctionCodeHandler):
    """Read Input Registers (FC04) handler."""

    @property
    def function_code(self) -> int:
        return 0x04

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Read Input Registers request."""
        start_address = config.get("start_address", 0)
        quantity = config.get("quantity", 1)
        return struct.pack(">BHH", self.function_code, start_address, quantity)

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Read Input Registers response."""
        quantity = config.get("quantity", 1)
        values = payload.get("values", [0] * quantity)

        byte_count = quantity * 2
        pdu = struct.pack(">BB", self.function_code, byte_count)

        for value in values[:quantity]:
            pdu += struct.pack(">H", value & 0xFFFF)

        return pdu


class FC05WriteSingleCoil(FunctionCodeHandler):
    """Write Single Coil (FC05) handler."""

    @property
    def function_code(self) -> int:
        return 0x05

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Write Single Coil request."""
        address = config.get("address", 0)
        value = config.get("value", False)
        coil_value = 0xFF00 if value else 0x0000
        return struct.pack(">BHH", self.function_code, address, coil_value)

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Write Single Coil response (echo request)."""
        address = config.get("address", 0)
        value = config.get("value", False)
        coil_value = 0xFF00 if value else 0x0000
        return struct.pack(">BHH", self.function_code, address, coil_value)


class FC06WriteSingleRegister(FunctionCodeHandler):
    """Write Single Register (FC06) handler."""

    @property
    def function_code(self) -> int:
        return 0x06

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Write Single Register request."""
        address = config.get("address", 0)
        value = config.get("value", 0)
        return struct.pack(">BHH", self.function_code, address, value & 0xFFFF)

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Write Single Register response (echo request)."""
        address = config.get("address", 0)
        value = config.get("value", 0)
        return struct.pack(">BHH", self.function_code, address, value & 0xFFFF)


class FC15WriteMultipleCoils(FunctionCodeHandler):
    """Write Multiple Coils (FC15) handler."""

    @property
    def function_code(self) -> int:
        return 0x0F

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Write Multiple Coils request."""
        start_address = config.get("start_address", 0)
        values = config.get("values", [False])
        quantity = len(values)
        byte_count = (quantity + 7) // 8

        # Pack bits into bytes
        data_bytes = bytearray(byte_count)
        for i, value in enumerate(values):
            if value:
                byte_idx = i // 8
                bit_idx = i % 8
                data_bytes[byte_idx] |= 1 << bit_idx

        pdu = struct.pack(">BHHB", self.function_code, start_address, quantity, byte_count)
        pdu += bytes(data_bytes)
        return pdu

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Write Multiple Coils response."""
        start_address = config.get("start_address", 0)
        values = config.get("values", [False])
        quantity = len(values)
        return struct.pack(">BHH", self.function_code, start_address, quantity)


class FC16WriteMultipleRegisters(FunctionCodeHandler):
    """Write Multiple Registers (FC16) handler."""

    @property
    def function_code(self) -> int:
        return 0x10

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Write Multiple Registers request."""
        start_address = config.get("start_address", 0)
        values = config.get("values", [0])
        quantity = len(values)
        byte_count = quantity * 2

        pdu = struct.pack(">BHHB", self.function_code, start_address, quantity, byte_count)
        for value in values:
            pdu += struct.pack(">H", value & 0xFFFF)

        return pdu

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Write Multiple Registers response."""
        start_address = config.get("start_address", 0)
        values = config.get("values", [0])
        quantity = len(values)
        return struct.pack(">BHH", self.function_code, start_address, quantity)


class FC07ReadExceptionStatus(FunctionCodeHandler):
    """Read Exception Status (FC07) handler.

    This function is used to read the exception status outputs in
    the slave device. Useful for quick diagnostics.
    """

    @property
    def function_code(self) -> int:
        return 0x07

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Read Exception Status request (no data needed)."""
        return struct.pack(">B", self.function_code)

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Read Exception Status response."""
        # Exception status is a single byte (8 outputs)
        status = payload.get("exception_status", 0x00)
        return struct.pack(">BB", self.function_code, status & 0xFF)


class FC08Diagnostics(FunctionCodeHandler):
    """Diagnostics (FC08) handler.

    This function provides diagnostic tests for the communication system
    between master and slave devices.
    """

    @property
    def function_code(self) -> int:
        return 0x08

    # Diagnostic sub-function codes
    RETURN_QUERY_DATA = 0x0000
    RESTART_COMMUNICATIONS = 0x0001
    RETURN_DIAGNOSTIC_REGISTER = 0x0002
    CLEAR_COUNTERS = 0x000A
    RETURN_BUS_MESSAGE_COUNT = 0x000B
    RETURN_BUS_COMM_ERROR_COUNT = 0x000C
    RETURN_SLAVE_MESSAGE_COUNT = 0x000E

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Diagnostics request."""
        sub_function = config.get("sub_function", self.RETURN_QUERY_DATA)
        data = config.get("data", 0)
        return struct.pack(">BHH", self.function_code, sub_function, data)

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Diagnostics response (echoes request for most sub-functions)."""
        sub_function = config.get("sub_function", self.RETURN_QUERY_DATA)
        # Response data depends on sub-function
        if sub_function == self.RETURN_QUERY_DATA:
            # Echo the data back
            data = config.get("data", 0)
        elif sub_function in [
            self.RETURN_BUS_MESSAGE_COUNT,
            self.RETURN_BUS_COMM_ERROR_COUNT,
            self.RETURN_SLAVE_MESSAGE_COUNT,
        ]:
            # Return counter value
            data = payload.get("counter_value", 0)
        elif sub_function == self.RETURN_DIAGNOSTIC_REGISTER:
            data = payload.get("diagnostic_register", 0)
        else:
            data = config.get("data", 0)

        return struct.pack(">BHH", self.function_code, sub_function, data)


class FC43ReadDeviceIdentification(FunctionCodeHandler):
    """Read Device Identification (FC43/0x2B) handler.

    This is a MEI (Modbus Encapsulated Interface) function that provides
    device identification data. This is critical for vulnerability scanners
    to identify device vendor and model.

    Device ID codes:
        0x01 = Basic identification (VendorName, ProductCode, MajorMinorRevision)
        0x02 = Regular identification (Basic + VendorUrl, ProductName, ModelName)
        0x03 = Extended identification (Regular + UserApplicationName)
        0x04 = Specific identification (single object)

    Object IDs:
        0x00 = VendorName
        0x01 = ProductCode
        0x02 = MajorMinorRevision
        0x03 = VendorUrl
        0x04 = ProductName
        0x05 = ModelName
        0x06 = UserApplicationName
        0x80-0xFF = Vendor specific
    """

    MEI_TYPE = 0x0E  # Read Device Identification

    @property
    def function_code(self) -> int:
        return 0x2B  # 43

    def build_request(self, config: dict[str, Any]) -> bytes:
        """Build Read Device Identification request."""
        # MEI type is always 0x0E for Read Device Identification
        device_id_code = config.get("device_id_code", 0x01)  # Default to basic
        object_id = config.get("object_id", 0x00)  # Start from VendorName
        return struct.pack(">BBBB", self.function_code, self.MEI_TYPE, device_id_code, object_id)

    def build_response(self, config: dict[str, Any], payload: dict[str, Any]) -> bytes:
        """Build Read Device Identification response.

        Uses fingerprint data if available, otherwise falls back to generic values.
        """
        device_id_code = config.get("device_id_code", 0x01)

        # Get identity from payload (populated from fingerprint)
        identity = payload.get("modbus_identity", {})

        # Object definitions
        objects = []

        if device_id_code >= 0x01:  # Basic identification
            if "vendor_name" in identity:
                objects.append((0x00, identity["vendor_name"]))
            else:
                objects.append((0x00, "PacketArch"))
            if "product_code" in identity:
                objects.append((0x01, identity["product_code"]))
            else:
                objects.append((0x01, "Simulated"))
            if "major_minor_revision" in identity:
                objects.append((0x02, identity["major_minor_revision"]))
            else:
                objects.append((0x02, "1.0.0"))

        if device_id_code >= 0x02:  # Regular identification
            if identity.get("vendor_url"):
                objects.append((0x03, identity["vendor_url"]))
            if identity.get("product_name"):
                objects.append((0x04, identity["product_name"]))
            if identity.get("model_name"):
                objects.append((0x05, identity["model_name"]))

        if device_id_code >= 0x03:  # Extended identification
            if identity.get("user_application_name"):
                objects.append((0x06, identity["user_application_name"]))

        # Build response
        # Conformity level (same as device_id_code typically)
        conformity = min(device_id_code, 0x03) | 0x80  # 0x81, 0x82, or 0x83

        # Response header
        more_follows = 0x00  # All data fits in one response
        next_object_id = 0x00
        num_objects = len(objects)

        response = struct.pack(
            ">BBBBBBB",
            self.function_code,
            self.MEI_TYPE,
            device_id_code,
            conformity,
            more_follows,
            next_object_id,
            num_objects,
        )

        # Add object data
        for obj_id, obj_value in objects:
            if isinstance(obj_value, str):
                obj_bytes = obj_value.encode("utf-8")
            else:
                obj_bytes = bytes(obj_value)
            response += struct.pack(">BB", obj_id, len(obj_bytes)) + obj_bytes

        return response

    def build_response_from_fingerprint(
        self,
        config: dict[str, Any],
        fingerprint_applicator: "FingerprintApplicator",
    ) -> bytes:
        """Build response using fingerprint applicator with identity builder.

        This method uses the identity builder plugin system for generating
        Modbus MEI (FC43) responses with proper CVE-vulnerable firmware versions.
        """
        device_id_code = config.get("device_id_code", 0x01)

        # Try using the new identity builder system first
        try:
            identity_response = fingerprint_applicator.get_identity_response(
                "modbus",
                device_id_code=device_id_code,
            )

            if identity_response.raw_response:
                # raw_response already includes MEI data, prepend function code
                return struct.pack(">B", self.function_code) + identity_response.raw_response
        except (KeyError, ImportError):
            # Identity builder not available, fall back to legacy method
            pass

        # Legacy fallback: use build_modbus_mei_response
        mei_response = fingerprint_applicator.build_modbus_mei_response(device_id_code)

        if mei_response:
            return struct.pack(">B", self.function_code) + mei_response
        else:
            # Final fallback to generic response
            return self.build_response(config, {})


# Registry of all function code handlers
FUNCTION_CODE_HANDLERS: dict[int, FunctionCodeHandler] = {
    0x01: FC01ReadCoils(),
    0x02: FC02ReadDiscreteInputs(),
    0x03: FC03ReadHoldingRegisters(),
    0x04: FC04ReadInputRegisters(),
    0x05: FC05WriteSingleCoil(),
    0x06: FC06WriteSingleRegister(),
    0x07: FC07ReadExceptionStatus(),
    0x08: FC08Diagnostics(),
    0x0F: FC15WriteMultipleCoils(),
    0x10: FC16WriteMultipleRegisters(),
    0x2B: FC43ReadDeviceIdentification(),
}


def get_handler(function_code: int) -> FunctionCodeHandler:
    """Get handler for a function code.

    Args:
        function_code: Modbus function code

    Returns:
        Function code handler

    Raises:
        ValueError: If function code is not supported
    """
    handler = FUNCTION_CODE_HANDLERS.get(function_code)
    if not handler:
        raise ValueError(f"Unsupported function code: {function_code}")
    return handler
