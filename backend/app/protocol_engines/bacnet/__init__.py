"""BACnet/IP protocol engine for Building Management Systems.

This module provides a complete BACnet/IP protocol engine for generating
realistic building automation traffic. It supports:

- Device discovery (Who-Is/I-Am broadcasts)
- Property polling (ReadProperty/ReadPropertyMultiple)
- Property writes (WriteProperty)
- Fingerprint-based device identity for security tool detection

Key components:
- BACnetEngine: Main protocol engine class
- packets: Packet building utilities
- types: BACnet constants, enums, and data structures

Usage:
    from app.protocol_engines.bacnet import BACnetEngine
    from app.protocol_engines.bacnet.types import BACNET_PORT, BACnetObjectType

Example fingerprint configuration:
    {
        "bacnet_identity": {
            "vendor_id": 5,
            "vendor_name": "Johnson Controls",
            "model_name": "NAE55 Network Automation Engine",
            "firmware_revision": "12.0.3",
            "device_instance": 1001,
            "max_apdu_length": 1476,
            "segmentation_supported": 0,
        }
    }
"""

from app.protocol_engines.bacnet.engine import BACnetEngine
from app.protocol_engines.vendor_oui import BACNET_VENDOR_IDS
from app.protocol_engines.bacnet.types import (
    BACNET_PORT,
    BACNET_BVLC_TYPE,
    BACnetAbortReason,
    BACnetApplicationTag,
    BACnetConfirmedService,
    BACnetDeviceStatus,
    BACnetErrorClass,
    BACnetErrorCode,
    BACnetFlowConfig,
    BACnetObjectIdentifier,
    BACnetObjectType,
    BACnetPDUType,
    BACnetPropertyIdentifier,
    BACnetPropertyValue,
    BACnetRejectReason,
    BACnetReliability,
    BACnetSegmentation,
    BACnetState,
    BACnetUnconfirmedService,
    BACnetUnits,
    BVLCFunction,
    BVLCResult,
    NPDUMessageType,
    NPDUNetworkPriority,
)
from app.protocol_engines.bacnet.packets import (
    build_bacnet_packet,
    build_error_apdu,
    build_i_am_apdu,
    build_i_am_packet,
    build_read_property_request_apdu,
    build_read_property_request_packet,
    build_read_property_response_apdu,
    build_read_property_response_packet,
    build_simple_ack_apdu,
    build_who_is_apdu,
    build_who_is_packet,
    build_write_property_request_apdu,
    encode_character_string,
    encode_enumerated,
    encode_object_identifier,
    encode_real,
    encode_signed,
    encode_unsigned,
)

__all__ = [
    # Main engine
    "BACnetEngine",
    # Constants
    "BACNET_PORT",
    "BACNET_BVLC_TYPE",
    "BACNET_VENDOR_IDS",
    # BVLC types
    "BVLCFunction",
    "BVLCResult",
    # NPDU types
    "NPDUNetworkPriority",
    "NPDUMessageType",
    # PDU types
    "BACnetPDUType",
    "BACnetUnconfirmedService",
    "BACnetConfirmedService",
    # Object types
    "BACnetObjectType",
    "BACnetObjectIdentifier",
    "BACnetPropertyIdentifier",
    # Enumerations
    "BACnetSegmentation",
    "BACnetDeviceStatus",
    "BACnetReliability",
    "BACnetUnits",
    # Error handling
    "BACnetErrorClass",
    "BACnetErrorCode",
    "BACnetRejectReason",
    "BACnetAbortReason",
    # Encoding
    "BACnetApplicationTag",
    # State machine
    "BACnetState",
    # Data classes
    "BACnetFlowConfig",
    "BACnetPropertyValue",
    # Packet building
    "build_bacnet_packet",
    "build_who_is_apdu",
    "build_who_is_packet",
    "build_i_am_apdu",
    "build_i_am_packet",
    "build_read_property_request_apdu",
    "build_read_property_request_packet",
    "build_read_property_response_apdu",
    "build_read_property_response_packet",
    "build_write_property_request_apdu",
    "build_simple_ack_apdu",
    "build_error_apdu",
    # Encoding utilities
    "encode_unsigned",
    "encode_signed",
    "encode_real",
    "encode_enumerated",
    "encode_character_string",
    "encode_object_identifier",
]
