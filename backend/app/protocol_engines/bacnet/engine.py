"""BACnet/IP protocol engine implementation.

Full-featured BACnet engine supporting:
- Device discovery (Who-Is/I-Am)
- Property reads (ReadProperty/ReadPropertyMultiple)
- Property writes (WriteProperty)
- Fingerprint-based device identity for Cyber Vision detection

This engine generates realistic BACnet/IP traffic for Building Management
Systems (BMS) including HVAC controllers, lighting systems, access control,
and building automation controllers.
"""

import random
import time
from collections.abc import Iterator
from typing import Any

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.bacnet.packets import (
    build_i_am_packet,
    build_read_property_request_packet,
    build_read_property_response_packet,
    build_who_is_packet,
)
from app.protocol_engines.vendor_oui import BACNET_VENDOR_IDS
from app.protocol_engines.bacnet.types import (
    BACNET_PORT,
    BACnetFlowConfig,
    BACnetObjectType,
    BACnetPropertyIdentifier,
    BACnetSegmentation,
    BACnetState,
    BACnetUnits,
)
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


@register_engine(ProtocolType.BACNET)
class BACnetEngine(ProtocolEngine):
    """BACnet/IP protocol engine for building automation systems.

    Generates realistic BACnet traffic including:
    - Discovery sequences (Who-Is/I-Am broadcasts)
    - Property polling cycles (ReadProperty/ReadPropertyMultiple)
    - Write operations for setpoint changes
    - Error responses with realistic behavior

    Supports fingerprint-based identity for Cyber Vision detection:
    - Vendor ID (registered BACnet vendor identifier)
    - Vendor Name
    - Model Name
    - Firmware Revision
    - Application Software Version
    - Protocol Version/Revision
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.BACNET

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state for BACnet flow.

        Note: BACnet/IP is UDP-based and largely stateless, but we track
        invoke IDs and poll cycle state for realistic simulation.
        """
        return ConversationState(
            flow_id=flow.flow_id,
            state_name=BACnetState.IDLE.value,
            transaction_id=0,  # BACnet invoke_id
            sequence_number=0,  # Poll cycle counter
            custom_data={
                "invoke_id": random.randint(1, 255),
                "device_instance": self._get_device_instance(flow),
                "start_time_ms": time.time() * 1000,
                "poll_object_index": 0,
                "discovered": False,
                "poll_property_index": 0,
            },
        )

    def _get_bacnet_config(self, flow: FlowContext) -> BACnetFlowConfig:
        """Extract BACnet configuration from flow config."""
        config = flow.config
        fingerprint = flow.destination.vendor_fingerprint or {}
        bacnet_id = fingerprint.get("bacnet_identity", {})

        return BACnetFlowConfig(
            device_instance=bacnet_id.get(
                "device_instance", random.randint(1, 4194302)
            ),
            vendor_id=bacnet_id.get("vendor_id", 0),
            poll_objects=config.get("poll_objects", self._get_default_poll_objects()),
            poll_properties=config.get("poll_properties", [
                BACnetPropertyIdentifier.PRESENT_VALUE,
                BACnetPropertyIdentifier.STATUS_FLAGS,
            ]),
            timeout_ms=config.get("timeout_ms", 3000),
            retries=config.get("retries", 3),
            max_apdu_length=bacnet_id.get("max_apdu_length", 1476),
            segmentation=BACnetSegmentation(
                bacnet_id.get(
                    "segmentation_supported",
                    BACnetSegmentation.NO_SEGMENTATION
                )
            ),
            generate_who_is=config.get("generate_who_is", True),
        )

    def _get_default_poll_objects(self) -> list[tuple[int, int]]:
        """Get default BACnet objects to poll.

        Returns common BMS object types for a typical controller:
        - Device object (instance -1 = placeholder, replaced with actual device instance)
        - Zone temperature (Analog Input)
        - Supply air temp (Analog Input)
        - Cooling valve (Analog Output)
        - Heating valve (Analog Output)
        - Fan status (Binary Input)
        - Occupancy (Binary Input)

        Note: Device object instance -1 is a sentinel value that gets replaced
        with the actual device instance in generate_poll_cycle(). This ensures
        VENDOR_NAME, MODEL_NAME, and FIRMWARE_REVISION are polled for CV detection.
        """
        return [
            (BACnetObjectType.DEVICE, -1),        # Device Object - instance replaced dynamically
            (BACnetObjectType.ANALOG_INPUT, 1),   # Zone Temperature
            (BACnetObjectType.ANALOG_INPUT, 2),   # Supply Air Temperature
            (BACnetObjectType.ANALOG_OUTPUT, 1),  # Cooling Valve
            (BACnetObjectType.ANALOG_OUTPUT, 2),  # Heating Valve
            (BACnetObjectType.BINARY_INPUT, 1),   # Fan Status
            (BACnetObjectType.BINARY_INPUT, 2),   # Occupancy Sensor
            (BACnetObjectType.ANALOG_VALUE, 1),   # Zone Setpoint
        ]

    def _get_device_instance(self, flow: FlowContext) -> int:
        """Get device instance from fingerprint or generate one."""
        fingerprint = flow.destination.vendor_fingerprint or {}
        bacnet_id = fingerprint.get("bacnet_identity") or {}
        return bacnet_id.get("device_instance", random.randint(1, 4194302))

    def _get_bacnet_identity(self, flow: FlowContext) -> dict[str, Any]:
        """Get BACnet identity from fingerprint for I-Am response.

        Returns identity fields critical for Cyber Vision detection.
        """
        fingerprint = flow.destination.vendor_fingerprint or {}
        bacnet_id = fingerprint.get("bacnet_identity") or {}

        # Check for vulnerability override (CVE-specific identity)
        vuln_override = flow.destination.vulnerability_override or {}
        bacnet_override = vuln_override.get("bacnet_identity_override", {})

        # Merge base identity with vulnerability overrides
        identity = {
            "vendor_id": bacnet_id.get("vendor_id", 0),
            "vendor_name": bacnet_id.get("vendor_name", "Unknown"),
            "model_name": bacnet_id.get("model_name", "BACnet Device"),
            "firmware_revision": bacnet_id.get("firmware_revision", "1.0"),
            "application_software_version": bacnet_id.get(
                "application_software_version", "1.0"
            ),
            "protocol_version": bacnet_id.get("protocol_version", 1),
            "protocol_revision": bacnet_id.get("protocol_revision", 19),
            "max_apdu_length": bacnet_id.get("max_apdu_length", 1476),
            "segmentation_supported": bacnet_id.get(
                "segmentation_supported",
                BACnetSegmentation.NO_SEGMENTATION
            ),
            "device_instance": bacnet_id.get(
                "device_instance", random.randint(1, 4194302)
            ),
            "system_status": bacnet_id.get("system_status", 0),  # Operational
            "object_name": bacnet_id.get(
                "object_name",
                f"BACnet-Device-{random.randint(1000, 9999)}"
            ),
            "description": bacnet_id.get("description", "BACnet/IP Device"),
        }

        # Apply vulnerability overrides (CVE-specific values)
        if bacnet_override:
            identity.update(bacnet_override)

        return identity

    def _get_response_delay(self, flow: FlowContext) -> float:
        """Get response delay from fingerprint timing.

        Returns delay in milliseconds based on device characteristics.
        """
        fingerprint = flow.destination.vendor_fingerprint or {}
        timing = fingerprint.get("response_timing", {})

        mean_ms = timing.get("mean_ms", 25.0)
        std_dev_ms = timing.get("std_dev_ms", 10.0)
        min_ms = timing.get("min_ms", 5.0)
        max_ms = timing.get("max_ms", 200.0)

        # Sample from distribution
        delay = random.gauss(mean_ms, std_dev_ms)
        return max(min_ms, min(max_ms, delay))

    def _get_property_value(
        self,
        flow: FlowContext,
        obj_type: int,
        obj_instance: int,
        prop_id: int,
        identity: dict,
    ) -> dict[str, Any]:
        """Get property value from fingerprint or generate realistic default.

        Args:
            flow: Flow context
            obj_type: BACnet object type
            obj_instance: Object instance number
            prop_id: Property identifier
            identity: Device identity dictionary

        Returns:
            Dictionary with 'value' and 'type' keys
        """
        # Device Object properties from identity
        if prop_id == BACnetPropertyIdentifier.VENDOR_NAME:
            return {"value": identity["vendor_name"], "type": "string"}
        elif prop_id == BACnetPropertyIdentifier.MODEL_NAME:
            return {"value": identity["model_name"], "type": "string"}
        elif prop_id == BACnetPropertyIdentifier.FIRMWARE_REVISION:
            return {"value": identity["firmware_revision"], "type": "string"}
        elif prop_id == BACnetPropertyIdentifier.APPLICATION_SOFTWARE_VERSION:
            return {
                "value": identity["application_software_version"],
                "type": "string"
            }
        elif prop_id == BACnetPropertyIdentifier.VENDOR_IDENTIFIER:
            return {"value": identity["vendor_id"], "type": "unsigned"}
        elif prop_id == BACnetPropertyIdentifier.SYSTEM_STATUS:
            return {"value": identity["system_status"], "type": "enumerated"}
        elif prop_id == BACnetPropertyIdentifier.PROTOCOL_VERSION:
            return {"value": identity["protocol_version"], "type": "unsigned"}
        elif prop_id == BACnetPropertyIdentifier.PROTOCOL_REVISION:
            return {"value": identity["protocol_revision"], "type": "unsigned"}
        elif prop_id == BACnetPropertyIdentifier.OBJECT_NAME:
            return {"value": identity["object_name"], "type": "string"}
        elif prop_id == BACnetPropertyIdentifier.DESCRIPTION:
            return {"value": identity["description"], "type": "string"}
        elif prop_id == BACnetPropertyIdentifier.MAX_APDU_LENGTH_ACCEPTED:
            return {"value": identity["max_apdu_length"], "type": "unsigned"}
        elif prop_id == BACnetPropertyIdentifier.SEGMENTATION_SUPPORTED:
            return {
                "value": identity["segmentation_supported"],
                "type": "enumerated"
            }

        # Object Identifier
        elif prop_id == BACnetPropertyIdentifier.OBJECT_IDENTIFIER:
            return {"value": (obj_type, obj_instance), "type": "object_identifier"}

        # Object Type
        elif prop_id == BACnetPropertyIdentifier.OBJECT_TYPE:
            return {"value": obj_type, "type": "enumerated"}

        # Present Value - generate realistic values based on object type
        elif prop_id == BACnetPropertyIdentifier.PRESENT_VALUE:
            return self._generate_present_value(obj_type, obj_instance)

        # Status Flags - typically all OK (0)
        elif prop_id == BACnetPropertyIdentifier.STATUS_FLAGS:
            return {"value": 0, "type": "bitstring"}

        # Out of Service - typically False
        elif prop_id == BACnetPropertyIdentifier.OUT_OF_SERVICE:
            return {"value": False, "type": "boolean"}

        # Reliability - typically No Fault Detected
        elif prop_id == BACnetPropertyIdentifier.RELIABILITY:
            return {"value": 0, "type": "enumerated"}

        # Event State - typically Normal
        elif prop_id == BACnetPropertyIdentifier.EVENT_STATE:
            return {"value": 0, "type": "enumerated"}

        # Units - based on object type
        elif prop_id == BACnetPropertyIdentifier.UNITS:
            return self._get_units_for_object(obj_type, obj_instance)

        # Default - return 0
        else:
            return {"value": 0, "type": "unsigned"}

    def _generate_present_value(
        self,
        obj_type: int,
        obj_instance: int,
    ) -> dict[str, Any]:
        """Generate realistic present value based on object type.

        Simulates real BMS values:
        - Temperatures: 60-80°F (typical HVAC range)
        - Valve positions: 0-100%
        - Binary states: On/Off
        """
        if obj_type == BACnetObjectType.ANALOG_INPUT:
            # Temperature sensor - typical room/supply air temps
            if obj_instance in (1, 2):  # Temperature inputs
                value = random.uniform(65.0, 78.0)
            else:
                value = random.uniform(0.0, 100.0)
            return {"value": value, "type": "real"}

        elif obj_type == BACnetObjectType.ANALOG_OUTPUT:
            # Valve position - 0-100%
            value = random.uniform(0.0, 100.0)
            return {"value": value, "type": "real"}

        elif obj_type == BACnetObjectType.ANALOG_VALUE:
            # Setpoint - typical comfort range
            if obj_instance == 1:  # Temperature setpoint
                value = random.uniform(70.0, 74.0)
            else:
                value = random.uniform(0.0, 100.0)
            return {"value": value, "type": "real"}

        elif obj_type == BACnetObjectType.BINARY_INPUT:
            # Binary sensor status
            value = random.choice([0, 1])
            return {"value": value, "type": "enumerated"}

        elif obj_type == BACnetObjectType.BINARY_OUTPUT:
            # Binary command state
            value = random.choice([0, 1])
            return {"value": value, "type": "enumerated"}

        elif obj_type == BACnetObjectType.BINARY_VALUE:
            value = random.choice([0, 1])
            return {"value": value, "type": "enumerated"}

        elif obj_type == BACnetObjectType.MULTI_STATE_INPUT:
            # Multi-state status (e.g., operating mode)
            value = random.randint(1, 4)
            return {"value": value, "type": "unsigned"}

        elif obj_type == BACnetObjectType.MULTI_STATE_OUTPUT:
            value = random.randint(1, 4)
            return {"value": value, "type": "unsigned"}

        elif obj_type == BACnetObjectType.MULTI_STATE_VALUE:
            value = random.randint(1, 4)
            return {"value": value, "type": "unsigned"}

        else:
            return {"value": 0, "type": "unsigned"}

    def _get_units_for_object(
        self,
        obj_type: int,
        obj_instance: int,
    ) -> dict[str, Any]:
        """Get engineering units for an object based on context."""
        if obj_type in (
            BACnetObjectType.ANALOG_INPUT,
            BACnetObjectType.ANALOG_VALUE,
        ):
            if obj_instance in (1, 2):  # Temperature
                return {
                    "value": BACnetUnits.DEGREES_FAHRENHEIT,
                    "type": "enumerated"
                }
            else:
                return {"value": BACnetUnits.PERCENT, "type": "enumerated"}

        elif obj_type == BACnetObjectType.ANALOG_OUTPUT:
            return {"value": BACnetUnits.PERCENT, "type": "enumerated"}

        else:
            return {"value": BACnetUnits.NO_UNITS, "type": "enumerated"}

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate BACnet discovery sequence.

        Discovery Flow:
        1. Who-Is broadcast from manager (optional)
        2. I-Am response from device (CRITICAL for Cyber Vision)

        The I-Am response contains device identity that Cyber Vision
        uses for device classification and vulnerability detection.
        """
        config = self._get_bacnet_config(flow)
        identity = self._get_bacnet_identity(flow)

        state.state_name = BACnetState.DISCOVERING.value
        current_time = start_time_ms

        # Who-Is broadcast (if enabled and source is the manager)
        if config.generate_who_is:
            who_is_packet = build_who_is_packet(flow.source)

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=who_is_packet,
                direction="request",
                metadata={
                    "type": "who_is",
                    "service": "discovery",
                    "protocol": "bacnet",
                },
            )

            # Response delay for I-Am
            current_time += random.uniform(50, 200)

        # I-Am response (CRITICAL for device detection)
        i_am_packet = build_i_am_packet(
            src=flow.destination,
            device_instance=identity["device_instance"],
            max_apdu_length=identity["max_apdu_length"],
            segmentation=identity["segmentation_supported"],
            vendor_id=identity["vendor_id"],
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=i_am_packet,
            direction="response",
            metadata={
                "type": "i_am",
                "service": "discovery",
                "protocol": "bacnet",
                "vendor_id": identity["vendor_id"],
                "vendor_name": identity["vendor_name"],
                "device_instance": identity["device_instance"],
                "model_name": identity["model_name"],
                "firmware_revision": identity["firmware_revision"],
            },
        )

        state.custom_data["discovered"] = True
        state.state_name = BACnetState.POLLING.value

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate BACnet polling cycle.

        Polls device properties using ReadProperty requests:
        - Device Object properties (identity, status)
        - Analog/Binary Input values
        - Setpoint values

        The responses include fingerprinted firmware/vendor info
        for Cyber Vision vulnerability detection.
        """
        config = self._get_bacnet_config(flow)
        identity = self._get_bacnet_identity(flow)

        state.state_name = BACnetState.POLLING.value
        current_time = cycle_time_ms
        invoke_id = state.custom_data["invoke_id"]

        # Get current poll object
        poll_objects = config.poll_objects or self._get_default_poll_objects()
        obj_index = state.custom_data.get("poll_object_index", 0)
        obj_type, obj_instance = poll_objects[obj_index % len(poll_objects)]

        # Handle Device object sentinel value (-1 means use actual device instance)
        if obj_type == BACnetObjectType.DEVICE and obj_instance == -1:
            obj_instance = identity["device_instance"]

        # Determine properties to read based on object type
        if obj_type == BACnetObjectType.DEVICE:
            # Device object - read identity properties
            properties = [
                BACnetPropertyIdentifier.VENDOR_NAME,
                BACnetPropertyIdentifier.MODEL_NAME,
                BACnetPropertyIdentifier.FIRMWARE_REVISION,
                BACnetPropertyIdentifier.SYSTEM_STATUS,
            ]
        else:
            # Regular objects - read value and status
            properties = [
                BACnetPropertyIdentifier.PRESENT_VALUE,
                BACnetPropertyIdentifier.STATUS_FLAGS,
            ]

        # Select one property per poll cycle for realistic pacing
        prop_index = state.custom_data.get("poll_property_index", 0)
        prop_id = properties[prop_index % len(properties)]

        # ReadProperty Request
        request_packet = build_read_property_request_packet(
            src=flow.source,
            dst=flow.destination,
            invoke_id=invoke_id,
            object_type=obj_type,
            object_instance=obj_instance,
            property_id=prop_id,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "read_property_request",
                "invoke_id": invoke_id,
                "object": f"{BACnetObjectType(obj_type).name}:{obj_instance}",
                "property": BACnetPropertyIdentifier(prop_id).name,
                "poll_cycle": state.sequence_number,
            },
        )

        state.state_name = BACnetState.AWAITING_RESPONSE.value

        # Response delay
        response_delay = self._get_response_delay(flow)
        current_time += response_delay

        # Get property value
        prop_value = self._get_property_value(
            flow, obj_type, obj_instance, prop_id, identity
        )

        # ReadProperty Response
        response_packet = build_read_property_response_packet(
            src=flow.destination,
            dst=flow.source,
            invoke_id=invoke_id,
            object_type=obj_type,
            object_instance=obj_instance,
            property_id=prop_id,
            property_value=prop_value["value"],
            property_type=prop_value["type"],
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "read_property_response",
                "invoke_id": invoke_id,
                "object": f"{BACnetObjectType(obj_type).name}:{obj_instance}",
                "property": BACnetPropertyIdentifier(prop_id).name,
                "value": str(prop_value["value"]),
                "response_delay_ms": response_delay,
                "poll_cycle": state.sequence_number,
            },
        )

        # Update state for next cycle
        invoke_id = (invoke_id % 255) + 1
        state.custom_data["invoke_id"] = invoke_id

        # Advance property index, and object index when properties exhausted
        prop_index += 1
        if prop_index >= len(properties):
            prop_index = 0
            obj_index = (obj_index + 1) % len(poll_objects)
            state.custom_data["poll_object_index"] = obj_index

        state.custom_data["poll_property_index"] = prop_index
        state.sequence_number += 1
        state.state_name = BACnetState.POLLING.value

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate BACnet shutdown sequence.

        BACnet/IP is UDP-based and connectionless, so there's no
        explicit shutdown sequence. This method yields nothing.
        """
        # BACnet/IP is UDP-based, no connection teardown needed
        return
        yield  # Make this a generator

    def validate_config(self, config: dict) -> list[str]:
        """Validate BACnet flow configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate device instance
        device_instance = config.get("device_instance")
        if device_instance is not None:
            if not isinstance(device_instance, int) or not (0 <= device_instance <= 4194302):
                errors.append("device_instance must be an integer 0-4194302")

        # Validate vendor ID
        vendor_id = config.get("vendor_id")
        if vendor_id is not None:
            if not isinstance(vendor_id, int) or vendor_id < 0:
                errors.append("vendor_id must be a non-negative integer")

        # Validate timeout
        timeout = config.get("timeout_ms")
        if timeout is not None:
            if not isinstance(timeout, int) or timeout < 100:
                errors.append("timeout_ms must be an integer >= 100")

        # Validate poll objects
        poll_objects = config.get("poll_objects")
        if poll_objects is not None:
            if not isinstance(poll_objects, list):
                errors.append("poll_objects must be a list")
            else:
                for i, obj in enumerate(poll_objects):
                    if not isinstance(obj, (list, tuple)) or len(obj) != 2:
                        errors.append(
                            f"poll_objects[{i}] must be (type, instance) tuple"
                        )

        return errors
