"""OPC UA protocol extractor for deep packet analysis.

Extracts service types, node IDs, endpoint information, and timing patterns.
"""

import logging
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from scapy.layers.inet import IP, TCP
from scapy.packet import Packet, Raw

from app.ai_services.extractors.base import (
    ExtractedPacketInfo,
    ProtocolExtractor,
)

logger = logging.getLogger(__name__)

# OPC UA message types
MSG_TYPE_HELLO = b"HEL"
MSG_TYPE_ACKNOWLEDGE = b"ACK"
MSG_TYPE_ERROR = b"ERR"
MSG_TYPE_OPEN_SECURE_CHANNEL = b"OPN"
MSG_TYPE_CLOSE_SECURE_CHANNEL = b"CLO"
MSG_TYPE_MESSAGE = b"MSG"

# OPC UA service identifiers (type IDs for common services)
SERVICE_IDS = {
    # Session services
    461: "CreateSessionRequest",
    464: "CreateSessionResponse",
    467: "ActivateSessionRequest",
    470: "ActivateSessionResponse",
    473: "CloseSessionRequest",
    476: "CloseSessionResponse",
    # Attribute services
    631: "ReadRequest",
    634: "ReadResponse",
    673: "WriteRequest",
    676: "WriteResponse",
    # View services
    527: "BrowseRequest",
    530: "BrowseResponse",
    533: "BrowseNextRequest",
    536: "BrowseNextResponse",
    # Subscription services
    787: "CreateSubscriptionRequest",
    790: "CreateSubscriptionResponse",
    826: "PublishRequest",
    829: "PublishResponse",
    793: "ModifySubscriptionRequest",
    796: "ModifySubscriptionResponse",
    799: "SetPublishingModeRequest",
    802: "SetPublishingModeResponse",
    # Monitored Item services
    751: "CreateMonitoredItemsRequest",
    754: "CreateMonitoredItemsResponse",
    763: "ModifyMonitoredItemsRequest",
    766: "ModifyMonitoredItemsResponse",
    781: "DeleteMonitoredItemsRequest",
    784: "DeleteMonitoredItemsResponse",
    # SecureChannel services
    446: "OpenSecureChannelRequest",
    449: "OpenSecureChannelResponse",
    452: "CloseSecureChannelRequest",
    455: "CloseSecureChannelResponse",
    # Discovery services
    422: "FindServersRequest",
    425: "FindServersResponse",
    428: "GetEndpointsRequest",
    431: "GetEndpointsResponse",
}

# OPC UA data types
DATA_TYPES = {
    0: "Null",
    1: "Boolean",
    2: "SByte",
    3: "Byte",
    4: "Int16",
    5: "UInt16",
    6: "Int32",
    7: "UInt32",
    8: "Int64",
    9: "UInt64",
    10: "Float",
    11: "Double",
    12: "String",
    13: "DateTime",
    14: "Guid",
    15: "ByteString",
    16: "XmlElement",
    17: "NodeId",
}


@dataclass
class OpcUaPacketData:
    """Parsed OPC UA packet data."""

    msg_type: bytes
    chunk_type: bytes  # F=Final, C=Continuation, A=Abort
    msg_size: int
    secure_channel_id: int | None = None
    security_token_id: int | None = None
    sequence_number: int | None = None
    request_id: int | None = None

    # Service info (for MSG type)
    service_id: int | None = None
    service_name: str | None = None

    # Endpoint info (for HEL/ACK)
    endpoint_url: str | None = None
    protocol_version: int | None = None
    receive_buffer_size: int | None = None
    send_buffer_size: int | None = None
    max_message_size: int | None = None
    max_chunk_count: int | None = None

    # Session info
    session_id: bytes | None = None
    authentication_token: bytes | None = None

    # Node IDs (for Read/Write/Browse)
    node_ids: list[str] = field(default_factory=list)

    # Server info (from GetEndpoints response)
    server_info: dict | None = None


@dataclass
class EndpointInfo:
    """Discovered endpoint information."""

    url: str
    security_policy: str = ""
    security_mode: int = 0
    server_certificate: bytes | None = None
    application_uri: str = ""
    product_uri: str = ""
    application_name: str = ""


class OpcUaExtractor(ProtocolExtractor):
    """Extract patterns from OPC UA traffic.

    Analyzes:
    - Message type distribution (HEL, ACK, OPN, MSG, CLO)
    - Service type frequency
    - Node ID access patterns
    - Endpoint information
    - Session management patterns
    - Timing characteristics
    """

    OPC_UA_PORT = 4840

    def __init__(self):
        self.packets: list[OpcUaPacketData] = []
        self.msg_type_counts: dict[str, int] = defaultdict(int)
        self.service_counts: dict[int, int] = defaultdict(int)
        self.node_id_accesses: dict[str, int] = defaultdict(int)
        self.endpoints: dict[str, EndpointInfo] = {}  # url -> endpoint info
        self.server_info: dict[str, dict] = {}  # ip -> server info
        self.request_counts = 0
        self.response_counts = 0
        self.session_count = 0
        self.subscription_count = 0

    @property
    def protocol_name(self) -> str:
        return "opc_ua"

    @property
    def well_known_ports(self) -> list[int]:
        return [4840]

    def reset(self):
        """Reset extractor state for new analysis."""
        self.packets = []
        self.msg_type_counts = defaultdict(int)
        self.service_counts = defaultdict(int)
        self.node_id_accesses = defaultdict(int)
        self.endpoints = {}
        self.server_info = {}
        self.request_counts = 0
        self.response_counts = 0
        self.session_count = 0
        self.subscription_count = 0

    def can_handle(self, packet: Packet) -> bool:
        """Check if packet is OPC UA Binary Protocol."""
        if not packet.haslayer(TCP):
            return False

        tcp = packet[TCP]

        # Check for OPC UA port
        if tcp.sport != self.OPC_UA_PORT and tcp.dport != self.OPC_UA_PORT:
            return False

        # Check for payload
        if not packet.haslayer(Raw):
            return False

        payload = bytes(packet[Raw].load)
        if len(payload) < 8:  # Minimum header size
            return False

        # Check for valid OPC UA message type
        msg_type = payload[0:3]
        valid_types = [
            MSG_TYPE_HELLO,
            MSG_TYPE_ACKNOWLEDGE,
            MSG_TYPE_ERROR,
            MSG_TYPE_OPEN_SECURE_CHANNEL,
            MSG_TYPE_CLOSE_SECURE_CHANNEL,
            MSG_TYPE_MESSAGE,
        ]
        return msg_type in valid_types

    def extract_packet_info(self, packet: Packet) -> ExtractedPacketInfo | None:
        """Extract OPC UA packet information."""
        if not self.can_handle(packet):
            return None

        try:
            parsed = self._parse_opc_ua_packet(packet)
            if not parsed:
                return None

            ip = packet[IP]
            tcp = packet[TCP]

            # Track statistics
            self.packets.append(parsed)
            self.msg_type_counts[parsed.msg_type.decode("ascii", errors="ignore")] += 1

            if parsed.service_id:
                self.service_counts[parsed.service_id] += 1

            # Track node IDs
            for node_id in parsed.node_ids:
                self.node_id_accesses[node_id] += 1

            # Determine direction
            is_request = tcp.dport == self.OPC_UA_PORT
            if is_request:
                self.request_counts += 1
            else:
                self.response_counts += 1

            # Track endpoint info
            if parsed.endpoint_url:
                if parsed.endpoint_url not in self.endpoints:
                    self.endpoints[parsed.endpoint_url] = EndpointInfo(
                        url=parsed.endpoint_url
                    )

            # Track server info
            if parsed.server_info:
                server_ip = ip.src if not is_request else ip.dst
                self.server_info[server_ip] = parsed.server_info

            # Track session creation
            if parsed.service_id in [464, 470]:  # CreateSessionResponse, ActivateSessionResponse
                self.session_count += 1

            # Track subscription creation
            if parsed.service_id == 790:  # CreateSubscriptionResponse
                self.subscription_count += 1

            return ExtractedPacketInfo(
                timestamp=float(packet.time),
                src_ip=ip.src,
                dst_ip=ip.dst,
                src_port=tcp.sport,
                dst_port=tcp.dport,
                protocol=self.protocol_name,
                direction="request" if is_request else "response",
                function_code=parsed.service_id,
                payload_size=len(packet[Raw].load),
                metadata={
                    "msg_type": parsed.msg_type.decode("ascii", errors="ignore"),
                    "service_name": parsed.service_name,
                    "secure_channel_id": parsed.secure_channel_id,
                    "request_id": parsed.request_id,
                    "node_ids": parsed.node_ids[:10] if parsed.node_ids else None,  # Limit for metadata
                    "endpoint_url": parsed.endpoint_url,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to parse OPC UA packet: {e}")
            return None

    def is_request(self, packet: Packet) -> bool:
        """Check if packet is an OPC UA request."""
        if not packet.haslayer(TCP):
            return False
        return packet[TCP].dport == self.OPC_UA_PORT

    def extract_identity_info(self, packet: Packet) -> dict | None:
        """Extract server identity from GetEndpoints response."""
        if not self.can_handle(packet):
            return None

        parsed = self._parse_opc_ua_packet(packet)
        if parsed and parsed.server_info:
            return parsed.server_info
        return None

    def _parse_opc_ua_packet(self, packet: Packet) -> OpcUaPacketData | None:
        """Parse OPC UA packet into structured data."""
        payload = bytes(packet[Raw].load)

        if len(payload) < 8:
            return None

        # Parse message header
        msg_type = payload[0:3]
        chunk_type = payload[3:4]
        msg_size = struct.unpack("<I", payload[4:8])[0]

        data = OpcUaPacketData(
            msg_type=msg_type,
            chunk_type=chunk_type,
            msg_size=msg_size,
        )

        try:
            if msg_type == MSG_TYPE_HELLO:
                self._parse_hello(data, payload[8:])
            elif msg_type == MSG_TYPE_ACKNOWLEDGE:
                self._parse_acknowledge(data, payload[8:])
            elif msg_type == MSG_TYPE_OPEN_SECURE_CHANNEL:
                self._parse_open_secure_channel(data, payload[8:])
            elif msg_type == MSG_TYPE_MESSAGE:
                self._parse_message(data, payload[8:])
            elif msg_type == MSG_TYPE_CLOSE_SECURE_CHANNEL:
                self._parse_close_secure_channel(data, payload[8:])
        except Exception as e:
            logger.debug(f"Error parsing OPC UA message body: {e}")

        return data

    def _parse_hello(self, data: OpcUaPacketData, body: bytes):
        """Parse Hello message."""
        if len(body) < 20:
            return

        data.protocol_version = struct.unpack("<I", body[0:4])[0]
        data.receive_buffer_size = struct.unpack("<I", body[4:8])[0]
        data.send_buffer_size = struct.unpack("<I", body[8:12])[0]
        data.max_message_size = struct.unpack("<I", body[12:16])[0]
        data.max_chunk_count = struct.unpack("<I", body[16:20])[0]

        # Parse endpoint URL
        if len(body) >= 24:
            url_len = struct.unpack("<I", body[20:24])[0]
            if url_len > 0 and len(body) >= 24 + url_len:
                data.endpoint_url = body[24:24 + url_len].decode("utf-8", errors="ignore")

    def _parse_acknowledge(self, data: OpcUaPacketData, body: bytes):
        """Parse Acknowledge message."""
        if len(body) < 20:
            return

        data.protocol_version = struct.unpack("<I", body[0:4])[0]
        data.receive_buffer_size = struct.unpack("<I", body[4:8])[0]
        data.send_buffer_size = struct.unpack("<I", body[8:12])[0]
        data.max_message_size = struct.unpack("<I", body[12:16])[0]
        data.max_chunk_count = struct.unpack("<I", body[16:20])[0]

    def _parse_open_secure_channel(self, data: OpcUaPacketData, body: bytes):
        """Parse OpenSecureChannel message."""
        # Variable length due to security policy - extract what we can
        # Find sequence header after asymmetric security header
        pos = 0

        # Security policy URI length
        if len(body) < 4:
            return
        policy_len = struct.unpack("<I", body[pos:pos + 4])[0]
        if policy_len > 0 and policy_len < 0xFFFFFFFF:
            pos += 4 + policy_len
        else:
            pos += 4

        # Sender certificate (null for None security)
        if len(body) < pos + 4:
            return
        cert_len = struct.unpack("<I", body[pos:pos + 4])[0]
        if cert_len > 0 and cert_len < 0xFFFFFFFF:
            pos += 4 + cert_len
        else:
            pos += 4

        # Receiver certificate thumbprint
        if len(body) < pos + 4:
            return
        thumb_len = struct.unpack("<I", body[pos:pos + 4])[0]
        if thumb_len > 0 and thumb_len < 0xFFFFFFFF:
            pos += 4 + thumb_len
        else:
            pos += 4

        # Sequence header
        if len(body) >= pos + 8:
            data.sequence_number = struct.unpack("<I", body[pos:pos + 4])[0]
            data.request_id = struct.unpack("<I", body[pos + 4:pos + 8])[0]

    def _parse_message(self, data: OpcUaPacketData, body: bytes):
        """Parse secure MSG message."""
        if len(body) < 8:
            return

        # Symmetric security header
        data.secure_channel_id = struct.unpack("<I", body[0:4])[0]
        data.security_token_id = struct.unpack("<I", body[4:8])[0]

        # Sequence header
        if len(body) >= 16:
            data.sequence_number = struct.unpack("<I", body[8:12])[0]
            data.request_id = struct.unpack("<I", body[12:16])[0]

        # Try to parse service type ID
        if len(body) >= 18:
            # Service type is encoded as NodeId
            # Typically as TwoByteNodeId (0x00) + ID or FourByteNodeId (0x01) + NS + ID
            encoding = body[16]
            if encoding == 0x00 and len(body) >= 18:
                # TwoByteNodeId
                service_id = body[17]
                data.service_id = service_id
                data.service_name = SERVICE_IDS.get(service_id, f"Unknown_{service_id}")
            elif encoding == 0x01 and len(body) >= 20:
                # FourByteNodeId
                service_id = struct.unpack("<H", body[18:20])[0]
                data.service_id = service_id
                data.service_name = SERVICE_IDS.get(service_id, f"Unknown_{service_id}")

        # Try to extract node IDs from Read/Write/Browse requests
        if data.service_id in [631, 673, 527]:  # Read, Write, Browse
            self._extract_node_ids(data, body[16:])

        # Extract server info from GetEndpoints response
        if data.service_id == 431:  # GetEndpointsResponse
            self._extract_server_info(data, body[16:])

    def _parse_close_secure_channel(self, data: OpcUaPacketData, body: bytes):
        """Parse CloseSecureChannel message."""
        if len(body) >= 4:
            data.secure_channel_id = struct.unpack("<I", body[0:4])[0]

    def _extract_node_ids(self, data: OpcUaPacketData, body: bytes):
        """Extract node IDs from Read/Write/Browse request."""
        # This is a simplified extraction - full parsing would be complex
        # Look for common NodeId patterns
        node_ids = []
        pos = 0

        while pos < len(body) - 2 and len(node_ids) < 100:
            encoding = body[pos]

            try:
                if encoding == 0x00:  # TwoByteNodeId
                    identifier = body[pos + 1]
                    node_ids.append(f"i={identifier}")
                    pos += 2
                elif encoding == 0x01:  # FourByteNodeId
                    if pos + 4 <= len(body):
                        ns = body[pos + 1]
                        identifier = struct.unpack("<H", body[pos + 2:pos + 4])[0]
                        node_ids.append(f"ns={ns};i={identifier}")
                        pos += 4
                    else:
                        pos += 1
                elif encoding == 0x02:  # NumericNodeId
                    if pos + 6 <= len(body):
                        ns = struct.unpack("<H", body[pos + 1:pos + 3])[0]
                        identifier = struct.unpack("<I", body[pos + 3:pos + 7])[0]
                        node_ids.append(f"ns={ns};i={identifier}")
                        pos += 7
                    else:
                        pos += 1
                elif encoding == 0x03:  # StringNodeId
                    if pos + 3 <= len(body):
                        ns = body[pos + 1]
                        str_len = struct.unpack("<I", body[pos + 2:pos + 6])[0]
                        if str_len > 0 and str_len < 256 and pos + 6 + str_len <= len(body):
                            identifier = body[pos + 6:pos + 6 + str_len].decode("utf-8", errors="ignore")
                            node_ids.append(f"ns={ns};s={identifier}")
                            pos += 6 + str_len
                        else:
                            pos += 1
                    else:
                        pos += 1
                else:
                    pos += 1
            except Exception:
                pos += 1

        data.node_ids = node_ids

    def _extract_server_info(self, data: OpcUaPacketData, body: bytes):
        """Extract server information from GetEndpoints response."""
        # This is simplified - full ApplicationDescription parsing is complex
        server_info = {}

        # Look for readable strings that might be server info
        strings = []
        pos = 0
        while pos < len(body) - 4:
            try:
                str_len = struct.unpack("<i", body[pos:pos + 4])[0]
                if 0 < str_len < 256:
                    if pos + 4 + str_len <= len(body):
                        text = body[pos + 4:pos + 4 + str_len].decode("utf-8", errors="ignore")
                        if text.isprintable():
                            strings.append(text)
                        pos += 4 + str_len
                    else:
                        pos += 1
                else:
                    pos += 1
            except Exception:
                pos += 1

        # Try to identify key strings
        for s in strings:
            if s.startswith("urn:") and "application_uri" not in server_info:
                if "server" in s.lower():
                    server_info["application_uri"] = s
                elif "product" in s.lower():
                    server_info["product_uri"] = s
            elif s.startswith("opc.tcp://") and "endpoint_url" not in server_info:
                server_info["endpoint_url"] = s
            elif "SecurityPolicy" in s:
                server_info["security_policy"] = s

        if strings and "application_name" not in server_info:
            # First non-URN string is often application name
            for s in strings:
                if not s.startswith(("urn:", "opc.", "http")):
                    server_info["application_name"] = s
                    break

        if server_info:
            data.server_info = server_info

    def build_patterns(self, packets: list[ExtractedPacketInfo] = None) -> dict[str, Any]:
        """Build learned patterns from extracted data.

        Returns:
            Dictionary with pattern data for LearnedProtocolPattern model
        """
        total_samples = len(self.packets)
        if total_samples == 0:
            return {}

        # Message type distribution
        total_msg_count = sum(self.msg_type_counts.values())
        msg_type_distribution = {}
        for msg_type, count in self.msg_type_counts.items():
            msg_type_distribution[msg_type] = {
                "count": count,
                "frequency": count / total_msg_count if total_msg_count > 0 else 0,
            }

        # Service type distribution
        total_service_count = sum(self.service_counts.values())
        service_distribution = {}
        for service_id, count in self.service_counts.items():
            service_name = SERVICE_IDS.get(service_id, f"Unknown_{service_id}")
            service_distribution[service_id] = {
                "name": service_name,
                "count": count,
                "frequency": count / total_service_count if total_service_count > 0 else 0,
            }

        # Node ID access patterns
        total_node_accesses = sum(self.node_id_accesses.values())
        node_id_patterns = {
            "unique_nodes": len(self.node_id_accesses),
            "total_accesses": total_node_accesses,
            "top_nodes": sorted(
                [
                    {"node_id": nid, "count": count}
                    for nid, count in self.node_id_accesses.items()
                ],
                key=lambda x: x["count"],
                reverse=True,
            )[:20],  # Top 20 most accessed nodes
        }

        # Endpoint information
        endpoint_patterns = [
            {
                "url": ep.url,
                "security_policy": ep.security_policy,
                "security_mode": ep.security_mode,
                "application_uri": ep.application_uri,
                "application_name": ep.application_name,
            }
            for ep in self.endpoints.values()
        ]

        # Calculate confidence
        confidence = self.calculate_confidence(
            total_samples,
            pattern_consistency=min(1.0, len(self.service_counts) / 10)
        )

        return {
            "protocol": self.protocol_name,
            "msg_type_distribution": msg_type_distribution,
            "service_distribution": service_distribution,
            "node_id_patterns": node_id_patterns,
            "endpoints": endpoint_patterns,
            "server_info": self.server_info if self.server_info else None,
            "sample_count": total_samples,
            "request_count": self.request_counts,
            "response_count": self.response_counts,
            "session_count": self.session_count,
            "subscription_count": self.subscription_count,
            "confidence": confidence,
            "protocol_metadata": {
                "unique_msg_types": len(self.msg_type_counts),
                "unique_services": len(self.service_counts),
                "unique_node_ids": len(self.node_id_accesses),
                "has_server_info": len(self.server_info) > 0,
            },
        }
